"""
Match operations shared by the Discord bot, AN-API and the command line:
submitting a match, processing new matches, undoing a match and correcting one.

Undo and correction work per game mode, by rolling back and replaying:

1. every processed match of the mode from the target onwards (in processing
   order) is rolled back, newest first, by subtracting the rating change it
   recorded on each player (``mmrchange``) and reversing its game and stat
   counters;
2. the target is removed (undo) or changed (correction);
3. the remaining matches are replayed, oldest first, through the normal
   rating code (eloupdate / eloupdate_ffa), which records fresh ``mmrchange``
   values.

Because the rollback subtracts recorded changes instead of recomputing
ratings from zero, anything else that moved a rating in between - decay, the
decay pool, manual corrections - is kept. Afterwards the map counters, high
scores, daily MMR history points and ranks of the mode are brought in line.
The map host rating is left alone: it is not recorded per match, so it cannot
be rolled back.

Every write operation holds a lock shared by all processes on the host,
snapshots what it touches and restores it if anything fails, and leaves an
entry in ``match_edits``. Undone matches move to ``matches_undone``.

Command line (prints a JSON result; used by AN-API)::

    python3 matchops.py submit [--host NAME] < match.json
    python3 matchops.py process
    python3 matchops.py undo MATCH_ID
    python3 matchops.py edit MATCH_ID < changes.json
    (all take --actor NAME, --source NAME, --operation ID; undo/edit take --dry-run)
"""

import argparse
import contextlib
import copy
import json
import os
import sys
import time
import traceback
from datetime import date, datetime, timezone

from bson import ObjectId

import eloupdate
import eloupdate_ffa
import historyupdate
import maps
import ranks
from util import FFA_MODES, MODE_NAMES, check_mode, connect, identify_player, is_aa

LOCK_PATH = os.environ.get(
    "AN_MATCHOPS_LOCK", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".matchops.lock")
)
LOCK_TIMEOUT = 120

TEAM_STAT_FIELDS = ("score", "kills", "deaths")
EDITABLE = {"team1", "team2", "players", "outcome", "map", "host"}
RATING_FIELDS = {"team1", "team2", "players", "outcome"}


class MatchOpError(Exception):
    """A request that can't be carried out; nothing was changed."""


# --- locking ------------------------------------------------------------------

@contextlib.contextmanager
def locked(timeout=LOCK_TIMEOUT):
    """Serialise match writes across the bot, AN-API and cron jobs on this host."""
    try:
        import fcntl
    except ImportError:  # not on Linux: nothing else runs concurrently there
        yield
        return
    with open(LOCK_PATH, "a+") as f:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() > deadline:
                    raise MatchOpError("another match update is still running; try again shortly")
                time.sleep(0.2)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


# --- helpers --------------------------------------------------------------------

def short_mode(match):
    return check_mode(match["mode"], short=True)


def is_ffa(match):
    return short_mode(match) in FFA_MODES


def rank_modes(modes):
    out = []
    for m in modes:
        out += [m + "r", m + "d"] if is_aa(m) else [m]
    return out


def as_id(match_id):
    try:
        return ObjectId(match_id)
    except Exception:
        raise MatchOpError(f"not a match id: {match_id!r}")


def participants(match):
    """(player entry, team number or None) for everyone in a match."""
    if is_ffa(match):
        return [(p, None) for p in (match.get("players") or [])]
    return [(p, t) for t in (1, 2) for p in match.get(f"team{t}", [])]


def ffa_position(players, index):
    """Finishing position with ties, exactly as eloupdate_ffa.player_ratings counts it."""
    pos = index + 1
    j = index - 1
    while j >= 0 and players[j]["score"] == players[index]["score"]:
        pos -= 1
        j -= 1
    return pos


def team_result(match, team):
    """(won, lost) increments for a team, as eloupdate counts them."""
    if match["outcome"] == 1:
        return (1, 0) if team == 1 else (0, 1)
    if match["outcome"] == 2:
        return (0, 1) if team == 1 else (1, 0)
    return (0, 0)


def rating_key(match, entry):
    """The player field holding the rating this entry changed, e.g. 'emmr' or 'acraarmmr'."""
    mode = short_mode(match)
    if is_aa(mode):
        return f"{mode}{entry['role']}mmr"
    return f"{mode}mmr"


def history_key(match, entry):
    mode = short_mode(match)
    return f"{mode}{entry['role']}history" if is_aa(mode) else f"{mode}history"


def match_day(match):
    """The calendar day a match counts for in the MMR history."""
    raw = match.get("date")
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, str):
        for fmt in ("%Y-%m-%d", "%y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw[:10], fmt).date()
            except ValueError:
                pass
    processed = match.get("processed_at")
    if isinstance(processed, datetime):
        return processed.date()
    return match["_id"].generation_time.date()


def order_key(match):
    """Processing order: legacy matches by date then insertion, newer ones by processed_at."""
    processed = match.get("processed_at")
    if isinstance(processed, datetime):
        return (1, processed.replace(tzinfo=None).isoformat(), match["_id"])
    return (0, str(match.get("date", "")), match["_id"])


def reverse_increments(match):
    """{player name: {field: delta}} that undoes what processing this match added."""
    mode = short_mode(match)
    out = {}
    if is_ffa(match):
        players = match["players"]
        for i, p in enumerate(players):
            pos = ffa_position(players, i)
            out[p["player"]] = {
                f"{mode}mmr": -p["mmrchange"],
                f"{mode}games.total": -1,
                f"{mode}games.won": -(1 if pos == 1 else 0),
                f"{mode}games.lost": -(1 if pos != 1 else 0),
                f"{mode}games.podium": -(1 if pos <= 3 else 0),
                f"{mode}games.finishes": -pos,
                f"{mode}stats.totalscore": -p["score"],
                f"{mode}stats.kills": -p["kills"],
                f"{mode}stats.deaths": -p["deaths"],
            }
        return out
    if is_aa(mode):
        conceded = [sum(p["scored"] for p in match["team2"]), sum(p["scored"] for p in match["team1"])]
        for team in (1, 2):
            won, lost = team_result(match, team)
            for p in match[f"team{team}"]:
                key = f"{mode}{p['role']}"
                out[p["player"]] = {
                    f"{key}mmr": -p["mmrchange"],
                    f"{key}games.total": -1,
                    f"{key}games.won": -won,
                    f"{key}games.lost": -lost,
                    f"{key}stats.totalscore": -p["score"],
                    f"{key}stats.kills": -p["kills"],
                    f"{key}stats.deaths": -p["deaths"],
                    f"{key}stats.conceded": -conceded[team - 1],
                    f"{key}stats.scored": -p["scored"],
                }
        return out
    for team in (1, 2):
        won, lost = team_result(match, team)
        for p in match[f"team{team}"]:
            out[p["player"]] = {
                f"{mode}mmr": -p["mmrchange"],
                f"{mode}games.total": -1,
                f"{mode}games.won": -won,
                f"{mode}games.lost": -lost,
                f"{mode}stats.totalscore": -p["score"],
                f"{mode}stats.kills": -p["kills"],
                f"{mode}stats.deaths": -p["deaths"],
            }
    return out


def check_replayable(matches):
    for m in matches:
        if is_ffa(m) and not m.get("players"):
            raise MatchOpError(f"match {m['_id']} has no player list; it can't be recalculated")
        for p, _ in participants(m):
            if "mmrchange" not in p:
                raise MatchOpError(
                    f"match {m['_id']} ({m.get('date')}) has no recorded rating change for {p.get('player')}; "
                    "matches from before rating changes were recorded can't be recalculated"
                )
            if is_aa(short_mode(m)) and "role" not in p:
                raise MatchOpError(f"match {m['_id']} has no Artifact assault roles recorded")


# --- heatmaps (merged into player docs at submission) ------------------------------

def apply_heatmaps(db, match, sign=1):
    """Add (sign=1) or remove (sign=-1) a match's heatmaps from the players' running averages."""
    if "map" not in match:
        return
    mode_key = short_mode(match)
    map_key = match["map"].lower()
    for p, _ in participants(match):
        heatmap = p.get("heatmap")
        if heatmap is None:
            continue
        cells = {f"{gx},{gy}": ms for gx, gy, ms in heatmap}
        player_doc = identify_player(db, p["player"])
        existing = (player_doc.get(f"{mode_key}heatmap") or {}).get(map_key, {})
        count = existing.get("count", 0)
        old = existing.get("heatmap", {})
        field = f"{mode_key}heatmap.{map_key}"
        if sign > 0:
            merged = {k: (old.get(k, 0) * count + cells.get(k, 0)) / (count + 1) for k in old.keys() | cells.keys()}
            db.players.update_one({"_id": player_doc["_id"]},
                                  {"$set": {f"{field}.heatmap": merged, f"{field}.count": count + 1}})
        elif count <= 1:
            db.players.update_one({"_id": player_doc["_id"]}, {"$unset": {field: ""}})
        else:
            removed = {}
            for k, v in old.items():
                value = (v * count - cells.get(k, 0)) / (count - 1)
                if k in cells and abs(value) < 1e-9:
                    continue  # the cell only existed because of this match
                removed[k] = value
            db.players.update_one({"_id": player_doc["_id"]},
                                  {"$set": {f"{field}.heatmap": removed, f"{field}.count": count - 1}})


# --- building a match document -------------------------------------------------------

def outcome_scores(match, team1, team2):
    """Team totals the outcome is judged on: artifacts in Artifact assault, score otherwise
    (eloupdate's sanity check uses the same)."""
    key = "scored" if is_aa(short_mode(match)) and all("scored" in p for p in team1 + team2) else "score"
    return sum(p[key] for p in team1), sum(p[key] for p in team2)


def _assign_teams_and_outcome(match, players, host):
    if "team" in players[0].keys() and players[0]["team"] != -1:
        players.sort(key=lambda p: p["team"])
    else:
        players.sort(key=lambda p: p["character"])
    match["team1"] = players[:len(players) // 2]
    match["team2"] = players[len(players) // 2:]
    match.pop("players", None)
    scores = outcome_scores(match, match["team1"], match["team2"])
    match["outcome"] = 0 if scores[0] == scores[1] else (1 if scores[0] > scores[1] else 2)
    if host:
        match["hostteam"] = 1 if any(p["player"] == host for p in match["team1"]) else 2


def build_match(db, raw, host=None, date_str=None, time_str=None):
    """
    Turn an extracted match (the patch's JSON: mode, map, players[...]) into a
    match document, as the bot's ``submit`` always did.
    """
    if not isinstance(raw, dict) or "mode" not in raw or not raw.get("players"):
        raise MatchOpError("a match needs a mode and a list of players")
    match = copy.deepcopy(raw)
    try:
        mode_key = check_mode(match["mode"], short=True)
    except ValueError as exc:
        raise MatchOpError(str(exc))
    now = datetime.now(timezone.utc)
    match["date"] = date_str or match.get("date") or now.strftime("%Y-%m-%d")
    match["time"] = time_str or match.get("time") or now.strftime("%H-%M-%S")
    match["mode"] = MODE_NAMES[mode_key]
    match["new"] = True
    match["inhist"] = False
    match["announced"] = False
    if host:
        match["host"] = host
    players = match["players"]
    for p in players:
        for field in ("player",) + TEAM_STAT_FIELDS:
            if field not in p:
                raise MatchOpError(f"every player needs {field!r}")
        try:
            p["player"] = identify_player(db, p["player"])["name"]
        except ValueError as exc:
            raise MatchOpError(str(exc))
    if mode_key in FFA_MODES:
        match["players"] = [{k: v for k, v in p.items() if k != "team"} for p in players]
    else:
        if len(players) % 2:
            raise MatchOpError("team modes need the same number of players on both teams")
        _assign_teams_and_outcome(match, players, match.get("host"))
    return match


# --- operations -------------------------------------------------------------------------

def submit(db, raw, host=None, date_str=None, time_str=None):
    """Insert an extracted match (unprocessed) and merge its heatmaps. Returns the new id."""
    match = build_match(db, raw, host, date_str, time_str)
    apply_heatmaps(db, match, 1)
    return db.matches.insert_one(match).inserted_id


def process(db):
    """Process every new match: map stats, ratings, history and ranks (read_and_update.main without the text file)."""
    pending = list(db.matches.find({"new": True}))
    if not pending:
        return {"processed": []}
    modes = sorted({short_mode(m) for m in pending})
    maps.update_maps(db)
    eloupdate.new_matches(db)
    eloupdate_ffa.new_matches(db)
    historyupdate.update()
    ranks.main(rank_modes(modes))
    processed = [db.matches.find_one({"_id": m["_id"]}) for m in pending]
    return {"processed": [summary(m) for m in processed if m]}


def summary(match):
    return {
        "id": str(match["_id"]),
        "mode": match.get("mode"),
        "map": match.get("map"),
        "date": match.get("date"),
        "outcome": match.get("outcome"),
        "players": [
            {"player": p.get("player"), "team": t, "score": p.get("score"), "kills": p.get("kills"),
             "deaths": p.get("deaths"), "mmrchange": p.get("mmrchange")}
            for p, t in participants(match)
        ],
    }


def _normalise_players(db, entries, old_entries, ffa):
    if not isinstance(entries, list) or not entries:
        raise MatchOpError("player lists must be non-empty lists")
    old_by_name = {e["player"]: e for e in old_entries}
    out = []
    for entry in entries:
        if not isinstance(entry, dict) or "player" not in entry:
            raise MatchOpError("every player entry needs 'player'")
        try:
            name = identify_player(db, entry["player"])["name"]
        except ValueError as exc:
            raise MatchOpError(str(exc))
        new = {k: v for k, v in old_by_name.get(name, {}).items() if k not in ("mmrchange", "role")}
        new.update({k: v for k, v in entry.items() if k not in ("mmrchange", "role")})
        new["player"] = name
        for field in TEAM_STAT_FIELDS:
            if not isinstance(new.get(field), (int, float)):
                raise MatchOpError(f"{name}: {field!r} must be a number")
        out.append(new)
    names = [e["player"] for e in out]
    if len(set(names)) != len(names):
        raise MatchOpError("a player appears twice")
    if ffa:
        out.sort(key=lambda e: e["score"], reverse=True)
    return out


def apply_changes(db, match, changes):
    """The corrected match document (not saved). Validates the changes."""
    unknown = set(changes) - EDITABLE
    if unknown:
        raise MatchOpError(f"can't change {', '.join(sorted(unknown))}; editable: {', '.join(sorted(EDITABLE))}")
    new = copy.deepcopy(match)
    ffa = is_ffa(match)
    if ffa:
        if "team1" in changes or "team2" in changes:
            raise MatchOpError("free-for-all matches have 'players', not teams")
        if "players" in changes:
            new["players"] = _normalise_players(db, changes["players"], match.get("players") or [], True)
    else:
        if "players" in changes:
            raise MatchOpError("team matches have 'team1' and 'team2'")
        for team in ("team1", "team2"):
            if team in changes:
                new[team] = _normalise_players(db, changes[team], match[team], False)
        if len(new["team1"]) != len(new["team2"]):
            raise MatchOpError("both teams need the same number of players")
        both = [p["player"] for p in new["team1"] + new["team2"]]
        if len(set(both)) != len(both):
            raise MatchOpError("a player is on both teams")
        if is_aa(short_mode(new)):
            for team in ("team1", "team2"):
                for p in new[team]:
                    if not isinstance(p.get("scored"), (int, float)):
                        raise MatchOpError(f"{p['player']}: Artifact assault needs 'scored'")
        scores = outcome_scores(new, new["team1"], new["team2"])
        derived = 0 if scores[0] == scores[1] else (1 if scores[0] > scores[1] else 2)
        outcome = changes.get("outcome", derived if ("team1" in changes or "team2" in changes) else new["outcome"])
        if outcome not in (0, 1, 2):
            raise MatchOpError("outcome must be 0 (tie), 1 or 2")
        if short_mode(new) != "do" and outcome != derived:
            raise MatchOpError(f"outcome {outcome} contradicts the scores {scores[0]} - {scores[1]}")
        new["outcome"] = outcome
    if "map" in changes:
        new["map"] = changes["map"]
    if "host" in changes:
        if changes["host"]:
            new["host"] = identify_player(db, changes["host"])["name"]
        else:
            new.pop("host", None)
    if not ffa:
        if new.get("host"):
            new["hostteam"] = 1 if any(p["player"] == new["host"] for p in new["team1"]) else 2
        else:
            new.pop("hostteam", None)
    return new


class _Snapshot:
    """What an operation may touch, to restore it if the operation fails part-way."""

    def __init__(self, db):
        self.db = db
        self.players = {}
        self.matches = {}
        self.maps = {}
        self.inserted = []

    def player(self, name):
        doc = identify_player(self.db, name)
        self.players.setdefault(doc["_id"], copy.deepcopy(doc))

    def match(self, doc):
        self.matches.setdefault(doc["_id"], copy.deepcopy(doc))

    def map(self, name):
        if name and name not in self.maps:
            self.maps[name] = copy.deepcopy(self.db.maps.find_one({"name": name}))

    def restore(self):
        for _id, doc in self.players.items():
            self.db.players.replace_one({"_id": _id}, doc)
        for _id, doc in self.matches.items():
            self.db.matches.replace_one({"_id": _id}, doc, upsert=True)
        for name, doc in self.maps.items():
            if doc is not None:
                self.db.maps.replace_one({"_id": doc["_id"]}, doc)
        for coll, _id in self.inserted:
            self.db[coll].delete_one({"_id": _id})


def _ratings(db, names, keys):
    out = {}
    for name in names:
        doc = identify_player(db, name)
        for key in keys:
            if key in doc:
                out[(doc["name"], key)] = doc[key]
    return out


def _fix_history(db, before, after):
    """Shift daily MMR history points by how much the replay changed each player's matches."""
    def deltas(matches):
        out = {}
        for m in matches:
            day = match_day(m)
            for p, _ in participants(m):
                key = (p["player"], history_key(m, p))
                out.setdefault(key, []).append((day, p.get("mmrchange", 0)))
        return out

    old, new = deltas(before), deltas(after)
    for (name, hkey) in set(old) | set(new):
        try:
            doc = identify_player(db, name)
        except ValueError:
            continue
        hist = doc.get(hkey)
        if not hist or not hist.get("dates"):
            continue
        mmrs = list(hist["mmrs"])
        changed = False
        for k, raw_day in enumerate(hist["dates"]):
            try:
                day = datetime.strptime(raw_day, "%y-%m-%d").date()
            except (TypeError, ValueError):
                continue
            diff = sum(c for d, c in new.get((name, hkey), []) if d <= day) \
                - sum(c for d, c in old.get((name, hkey), []) if d <= day)
            if abs(diff) > 1e-9:
                mmrs[k] = round(mmrs[k] + diff)
                changed = True
        if changed:
            db.players.update_one({"_id": doc["_id"]}, {"$set": {f"{hkey}.mmrs": mmrs}})


def _fix_highscores(db, mode, old_target, new_target):
    """Recompute high scores the target match may have set (not tracked for Artifact assault)."""
    if is_aa(mode):
        return
    field = f"{mode}stats.highscore"
    names = {p["player"] for p, _ in participants(old_target)}
    if new_target is not None:
        names |= {p["player"] for p, _ in participants(new_target)}
    same_mode = [m for m in db.matches.find({"new": False}) if short_mode(m) == mode]
    for name in names:
        best = None
        for m in same_mode:
            for p, _ in participants(m):
                if p["player"] == name:
                    best = p["score"] if best is None else max(best, p["score"])
        doc = identify_player(db, name)
        current = (doc.get(f"{mode}stats") or {}).get("highscore")
        old_scores = [p["score"] for p, _ in participants(old_target) if p["player"] == name]
        if best is None:
            continue
        # only lower a high score this match may have set; raising is always right
        if current is None or best > current or (old_scores and current == old_scores[0] and best < current):
            db.players.update_one({"_id": doc["_id"]}, {"$set": {field: best}})


def _recalculate(db, target, new_target, actor, source, dry_run):
    """Roll back the mode from the target onwards, apply the change, replay. new_target None = undo."""
    mode = short_mode(target)
    if new_target is not None and short_mode(new_target) != mode:
        raise MatchOpError("the game mode can't be changed; undo the match and submit it again")

    if target.get("new", False):
        # not processed yet: no ratings to repair
        if dry_run:
            return {"match": str(target["_id"]), "mode": mode, "replayed": 0, "processed": False, "dry_run": True}
        if new_target is None:
            apply_heatmaps(db, target, -1)
            db.matches_undone.insert_one(dict(target, undone_by=actor, undone_at=datetime.now(timezone.utc),
                                              undone_via=source))
            db.matches.delete_one({"_id": target["_id"]})
        else:
            db.matches.replace_one({"_id": target["_id"]}, new_target)
        return {"match": str(target["_id"]), "mode": mode, "replayed": 0, "processed": False, "changes": []}

    same_mode = [m for m in db.matches.find({"new": False}) if short_mode(m) == mode]
    same_mode.sort(key=order_key)
    index = next(i for i, m in enumerate(same_mode) if m["_id"] == target["_id"])
    affected = same_mode[index:]
    check_replayable(affected)
    later = affected[1:]
    names = {p["player"] for m in affected for p, _ in participants(m)}
    if new_target is not None:
        names |= {p["player"] for p, _ in participants(new_target)}
    keys = [f"{mode}rmmr", f"{mode}dmmr"] if is_aa(mode) else [f"{mode}mmr"]
    if dry_run:
        return {"match": str(target["_id"]), "mode": mode, "replayed": len(later), "players": sorted(names),
                "dry_run": True}

    snap = _Snapshot(db)
    for name in names:
        snap.player(name)
    for m in affected:
        snap.match(m)
    snap.map(target.get("map"))
    if new_target is not None:
        snap.map(new_target.get("map"))
    ratings_before = _ratings(db, names, keys)
    try:
        # 1. roll back, newest first
        for m in reversed(affected):
            for name, inc in reverse_increments(m).items():
                db.players.update_one({"_id": identify_player(db, name)["_id"]}, {"$inc": inc})
        # 2. remove or change the target (map counters follow it; the host rating stays)
        maps.update_maps(db, [target], sign=-1)
        if new_target is None:
            apply_heatmaps(db, target, -1)
            undone = dict(target, undone_by=actor, undone_at=datetime.now(timezone.utc), undone_via=source)
            db.matches_undone.insert_one(undone)
            snap.inserted.append(("matches_undone", undone["_id"]))
            db.matches.delete_one({"_id": target["_id"]})
            replay = later
        else:
            db.matches.replace_one({"_id": target["_id"]}, new_target)
            maps.update_maps(db, [new_target], sign=1)
            replay = [new_target] + later
        # 3. replay, oldest first, through the normal rating code
        fresh = [db.matches.find_one({"_id": m["_id"]}) for m in replay]
        if mode in FFA_MODES:
            eloupdate_ffa.new_matches(db, matches=fresh)
        else:
            eloupdate.new_matches(db, matches=fresh, update_map_rating=False)
        replayed = [db.matches.find_one({"_id": m["_id"]}) for m in replay]
        _fix_history(db, affected, replayed)
        _fix_highscores(db, mode, target, new_target)
        ranks.main(rank_modes([mode]))
    except Exception:
        snap.restore()
        raise
    ratings_after = _ratings(db, names, keys)
    changes = [
        {"player": name, "field": key, "before": ratings_before[(name, key)], "after": ratings_after[(name, key)]}
        for (name, key) in sorted(ratings_before)
        if (name, key) in ratings_after and abs(ratings_after[(name, key)] - ratings_before[(name, key)]) > 1e-9
    ]
    return {"match": str(target["_id"]), "mode": mode, "replayed": len(later), "processed": True, "changes": changes}


def _record(db, op, target, new_target, actor, source, result):
    db.match_edits.insert_one({
        "op": op,
        "match": target["_id"],
        "mode": target.get("mode"),
        "actor": actor,
        "source": source,
        "at": datetime.now(timezone.utc),
        "before": target,
        "after": new_target,
        "result": result,
        # the bot posts a note in the match channel for changes made elsewhere
        "notified": source == "discord",
    })


def undo(db, match_id, actor="", source="cli", dry_run=False):
    """Remove a match and repair every rating it touched."""
    target = db.matches.find_one({"_id": as_id(match_id)})
    if target is None:
        raise MatchOpError(f"no match {match_id}")
    result = _recalculate(db, target, None, actor, source, dry_run)
    if not dry_run:
        _record(db, "undo", target, None, actor, source, result)
    return result


def edit(db, match_id, changes, actor="", source="cli", dry_run=False):
    """Correct a match (players, stats, outcome, map, host) and repair the ratings."""
    if not isinstance(changes, dict) or not changes:
        raise MatchOpError("nothing to change")
    target = db.matches.find_one({"_id": as_id(match_id)})
    if target is None:
        raise MatchOpError(f"no match {match_id}")
    new_target = apply_changes(db, target, changes)
    new_target["corrected"] = True
    if not (set(changes) & RATING_FIELDS) and not target.get("new", False):
        # map or host only: no rating depends on these (the host rating isn't replayed)
        if dry_run:
            return {"match": str(target["_id"]), "mode": short_mode(target), "replayed": 0, "dry_run": True}
        maps.update_maps(db, [target], sign=-1)
        db.matches.replace_one({"_id": target["_id"]}, new_target)
        maps.update_maps(db, [new_target], sign=1)
        result = {"match": str(target["_id"]), "mode": short_mode(target), "replayed": 0, "changes": []}
    else:
        result = _recalculate(db, target, new_target, actor, source, dry_run)
    if not dry_run:
        _record(db, "edit", target, new_target, actor, source, result)
    return result


# --- command line (AN-API runs this) ----------------------------------------------------------

def _set_operation(db, op_id, **fields):
    if op_id:
        db.match_operations.update_one({"_id": ObjectId(op_id)}, {"$set": dict(fields, updated_at=datetime.now(timezone.utc))},
                                       upsert=True)


def _json_default(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Submit, process, undo or correct AN matches.")
    parser.add_argument("command", choices=["submit", "process", "undo", "edit"])
    parser.add_argument("match_id", nargs="?")
    parser.add_argument("--host", help="submit: the match host")
    parser.add_argument("--actor", default="", help="who asked for this (kept in match_edits)")
    parser.add_argument("--source", default="cli", help="where the request came from (api, website, discord, cli)")
    parser.add_argument("--operation", help="match_operations id to report progress to")
    parser.add_argument("--dry-run", action="store_true", help="undo/edit: check and report, change nothing")
    args = parser.parse_args(argv)

    db = connect()
    _set_operation(db, args.operation, status="running")
    try:
        if args.command in ("undo", "edit") and not args.match_id:
            raise MatchOpError(f"{args.command} needs a match id")
        payload = json.load(sys.stdin) if args.command in ("submit", "edit") else None
        # the rating scripts print progress; keep stdout for the JSON result
        with locked(), contextlib.redirect_stdout(sys.stderr):
            if args.command == "submit":
                match_id = submit(db, payload, host=args.host)
                result = dict(process(db), match=str(match_id))
            elif args.command == "process":
                result = process(db)
            elif args.command == "undo":
                result = undo(db, args.match_id, args.actor, args.source, args.dry_run)
            else:
                result = edit(db, args.match_id, payload, args.actor, args.source, args.dry_run)
    except (MatchOpError, json.JSONDecodeError) as exc:
        _set_operation(db, args.operation, status="failed", kind="refused", error=str(exc))
        print(json.dumps({"error": str(exc)}))
        return 2
    except Exception as exc:  # noqa: BLE001 - report anything to the caller
        traceback.print_exc()
        _set_operation(db, args.operation, status="failed", kind="error", error=f"{type(exc).__name__}: {exc}")
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
        return 1
    _set_operation(db, args.operation, status="done", result=json.loads(json.dumps(result, default=_json_default)))
    print(json.dumps(result, default=_json_default))
    return 0


if __name__ == "__main__":
    sys.exit(main())
