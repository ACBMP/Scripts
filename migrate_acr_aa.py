"""
Rename ACR's Artifact assault from the old "aa" / "aar" / "aad" to "acraa" /
"acraar" / "acraad", matching AC3 and AC4's "ac3aa" / "ac4aa".

- players: aarmmr, aadgames, ... -> acraarmmr, acraadgames, ...;
  badges for "AA Running" / "AA Defending" -> "ACR AA Running" / "ACR AA Defending"
- maps: the "aa" stats -> "acraa"
- matches, matches_undone and the match_edits log: mode "Artifact assault" -> "ACR Artifact assault"

Run it once, with the bots and the match update stopped, before starting the
new code:

    python3 migrate_acr_aa.py            # show what would change
    python3 migrate_acr_aa.py --apply    # change it

Rerunning is safe: data already renamed is left alone. If a player or map
already has *played* games under the new name as well as data under the old
one, it is reported and skipped rather than overwritten.
"""

import argparse
import re
import sys

OLD_PREFIXES = {"aar": "acraar", "aad": "acraad"}
OLD_MAP_KEY, NEW_MAP_KEY = "aa", "acraa"
OLD_MODE, NEW_MODE = re.compile(r"^artifact assault$", re.I), "ACR Artifact assault"
BADGE_MODES = {"AA Running": "ACR AA Running", "AA Defending": "ACR AA Defending"}
MATCH_COLLECTIONS = ("matches", "matches_undone")


def _played(value):
    """Whether a games/stats sub-document under the new name holds real games."""
    return isinstance(value, dict) and value.get("games", value.get("total", 0))


def _player_changes(player):
    renames = {}
    for key in player:
        new_prefix = OLD_PREFIXES.get(key[:3])
        if new_prefix:
            renames[key] = new_prefix + key[3:]
    conflict = any(_played(player.get(prefix + "games")) for prefix in OLD_PREFIXES.values()
                   if any(new.startswith(prefix) for new in renames.values()))
    badges = player.get("badges") or []
    new_badges = [dict(b, mode=BADGE_MODES[b["mode"]]) if b.get("mode") in BADGE_MODES else b
                  for b in badges]
    return renames, (new_badges if new_badges != badges else None), conflict


def migrate(db, apply=False, out=sys.stdout):
    """Rename everything; returns {what: count} (what would change without apply)."""
    counts = {"players": 0, "badges": 0, "maps": 0, "matches": 0, "matches_undone": 0, "match_edits": 0}
    skipped = []

    for player in db.players.find():
        renames, badges, conflict = _player_changes(player)
        if conflict:
            skipped.append(f"player {player.get('name')}: has games under both the old and new name")
            continue
        update = {}
        if renames:
            update["$rename"] = renames
            counts["players"] += 1
        if badges is not None:
            update["$set"] = {"badges": badges}
            counts["badges"] += 1
        if update and apply:
            db.players.update_one({"_id": player["_id"]}, update)

    for m in db.maps.find({OLD_MAP_KEY: {"$exists": True}}):
        if _played(m.get(NEW_MAP_KEY)):
            skipped.append(f"map {m.get('name')}: has games under both '{OLD_MAP_KEY}' and '{NEW_MAP_KEY}'")
            continue
        counts["maps"] += 1
        if apply:
            db.maps.update_one({"_id": m["_id"]}, {"$rename": {OLD_MAP_KEY: NEW_MAP_KEY}})

    for name in MATCH_COLLECTIONS:
        query = {"mode": OLD_MODE}
        counts[name] = db[name].count_documents(query)
        if apply and counts[name]:
            db[name].update_many(query, {"$set": {"mode": NEW_MODE}})

    for side in ("before", "after"):
        query = {f"{side}.mode": OLD_MODE}
        counts["match_edits"] += db.match_edits.count_documents(query)
        if apply:
            db.match_edits.update_many(query, {"$set": {f"{side}.mode": NEW_MODE}})

    verb = "Changed" if apply else "Would change"
    for what, n in counts.items():
        print(f"{verb} {n} {what}", file=out)
    for line in skipped:
        print(f"Skipped {line}", file=out)
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="make the changes (default: only report them)")
    args = parser.parse_args(argv)

    from util import connect
    import matchops

    db = connect()
    # keep matchops (AN-API / bot corrections) from running at the same time
    with matchops.locked():
        migrate(db, apply=args.apply)
    if not args.apply:
        print("Nothing was changed; rerun with --apply.")


if __name__ == "__main__":
    main()
