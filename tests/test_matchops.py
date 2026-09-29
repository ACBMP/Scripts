"""Undo and correction must leave the database as if it had only ever seen the final matches."""

import copy
import random

import pytest

import eloupdate
import matchops

NAMES = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel"]
from util import ALL_MODES


def add_players(db, games=20):
    for i, name in enumerate(NAMES):
        doc = {"name": name, "ign": name, "hidden": False, "privilege": 10, "discord_id": str(1000 + i)}
        for m in ALL_MODES:
            doc[f"{m}mmr"] = 1000 + 13 * i
            doc[f"{m}games"] = {"total": games, "won": games // 2, "lost": games - games // 2,
                                "podium": 0, "finishes": 0}
            doc[f"{m}stats"] = {"totalscore": 0, "kills": 0, "deaths": 0, "highscore": 0, "conceded": 0, "scored": 0}
            doc[f"{m}history"] = {"dates": [], "mmrs": []}
            doc[f"{m}rank"] = 0
            doc[f"{m}rankchange"] = 0
        db.players.insert_one(doc)
    stats = {"kills": 0, "deaths": 0, "score": 0, "hostwins": 0, "hostlosses": 0, "games": 0, "hostrating": 1000,
             "players": 0, "scored": 0, "hostscored": 0, "hostpodiums": 0}
    db.maps.insert_one({"name": "Rome", **{m: dict(stats) for m in ("e", "mh", "do", "acraa", "dm", "asb")}})


def team_match(mode, seed, roster=None, host=None):
    rng = random.Random(seed)
    roster = roster or rng.sample(NAMES, 8)
    players = []
    for i, name in enumerate(roster):
        p = {"player": name, "team": 1 if i < 4 else 2, "score": rng.randrange(100, 3000, 5),
             "kills": rng.randrange(0, 15), "deaths": rng.randrange(0, 15)}
        if "Artifact assault" in mode:
            p["scored"] = rng.randrange(0, 3)
            p["score"] = rng.randrange(0, 4)
        players.append(p)
    raw = {"mode": mode, "map": "Rome", "players": players}
    if host:
        raw["host"] = host
    return raw


def ffa_match(seed, roster=None):
    rng = random.Random(seed)
    roster = roster or rng.sample(NAMES, 6)
    players = [{"player": n, "score": rng.randrange(1000, 9000, 5), "kills": rng.randrange(0, 20),
                "deaths": rng.randrange(0, 20)} for n in roster]
    players.sort(key=lambda p: p["score"], reverse=True)
    return {"mode": "Deathmatch", "map": "Rome", "players": players, "host": roster[0]}


def play(db, raws):
    ids = []
    for raw in raws:
        ids.append(matchops.submit(db, copy.deepcopy(raw), host=raw.get("host")))
        matchops.process(db)
    return ids


def state(db):
    out = {}
    for p in db.players.find():
        for m in ALL_MODES:
            out[(p["name"], f"{m}mmr")] = p[f"{m}mmr"]
            for k, v in p[f"{m}games"].items():
                out[(p["name"], f"{m}games.{k}")] = v
            for k, v in p[f"{m}stats"].items():
                out[(p["name"], f"{m}stats.{k}")] = v
            out[(p["name"], f"{m}rank")] = p[f"{m}rank"]
    rome = db.maps.find_one({"name": "Rome"})
    for mode, stats in rome.items():
        if isinstance(stats, dict):
            for k, v in stats.items():
                if k != "hostrating":
                    out[("map", f"{mode}.{k}")] = v
    return out


def assert_same(actual, expected):
    assert actual.keys() == expected.keys()
    diffs = {k: (actual[k], expected[k]) for k in actual if actual[k] != pytest.approx(expected[k], abs=1e-6)}
    assert not diffs, diffs


@pytest.mark.parametrize("mode", ["Escort", "Manhunt", "ACR Artifact assault", "AC3 Artifact assault",
                                  "AC4 Artifact assault"])
def test_undo_equals_never_having_played(db, mode):
    raws = [team_match(mode, seed, host="Alpha") for seed in range(5)]
    add_players(db)
    ids = play(db, raws)
    matchops.undo(db, ids[2], actor="Admin")
    after_undo = state(db)
    assert db.matches.count_documents({}) == 4 and db.matches_undone.count_documents({}) == 1

    for name in db.list_collection_names():
        db.drop_collection(name)
    add_players(db)
    play(db, raws[:2] + raws[3:])
    assert_same(after_undo, state(db))


@pytest.mark.parametrize("mode", ["Escort", "ACR Artifact assault", "AC3 Artifact assault"])
def test_edit_equals_having_played_the_corrected_match(db, mode):
    raws = [team_match(mode, seed) for seed in range(10, 15)]
    add_players(db)
    ids = play(db, raws)
    target = db.matches.find_one({"_id": ids[1]})
    corrected = copy.deepcopy(raws[1])
    # swap two players' stats and raise one score
    corrected["players"][0]["score"], corrected["players"][5]["score"] = \
        corrected["players"][5]["score"] + 3, corrected["players"][0]["score"]
    team1 = [p for p in corrected["players"] if p["team"] == 1]
    team2 = [p for p in corrected["players"] if p["team"] == 2]
    strip = lambda ps: [{k: v for k, v in p.items() if k != "team"} for p in ps]
    matchops.edit(db, ids[1], {"team1": strip(team1), "team2": strip(team2)}, actor="Admin")
    after_edit = state(db)
    assert db.matches.find_one({"_id": ids[1]})["corrected"] is True
    assert db.match_edits.find_one()["before"]["_id"] == target["_id"]

    for name in db.list_collection_names():
        db.drop_collection(name)
    add_players(db)
    play(db, raws[:1] + [corrected] + raws[2:])
    assert_same(after_edit, state(db))


def test_ffa_undo_and_edit(db):
    raws = [ffa_match(seed) for seed in range(20, 25)]
    add_players(db)
    ids = play(db, raws)
    matchops.undo(db, ids[1])
    changed = copy.deepcopy(raws[3])
    changed["players"][-1]["score"] = changed["players"][0]["score"] + 100  # last place wins
    matchops.edit(db, ids[3], {"players": changed["players"]})
    result = state(db)

    for name in db.list_collection_names():
        db.drop_collection(name)
    add_players(db)
    changed["players"].sort(key=lambda p: p["score"], reverse=True)
    play(db, [raws[0], raws[2], changed, raws[4]])
    assert_same(result, state(db))


def test_undoing_the_last_match_restores_everything_even_after_decay(db):
    add_players(db)
    play(db, [team_match("Escort", 1), team_match("Escort", 2)])
    # decay / manual correction between matches must survive
    db.players.update_one({"name": "Charlie"}, {"$inc": {"emmr": -37.5}})
    before = state(db)
    last = play(db, [team_match("Escort", 3)])[0]
    matchops.undo(db, last)
    after = state(db)
    ranks_only = {k for k in before if k[1].endswith("rank")}
    assert_same({k: v for k, v in after.items() if k not in ranks_only},
                {k: v for k, v in before.items() if k not in ranks_only})


def test_failure_restores_everything(db, monkeypatch):
    add_players(db)
    ids = play(db, [team_match("Escort", s) for s in range(3)])
    before = state(db)
    matches_before = list(db.matches.find())

    def broken(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(eloupdate, "new_matches", broken)
    with pytest.raises(RuntimeError):
        matchops.undo(db, ids[0])
    assert_same(state(db), before)
    assert sorted(db.matches.find(), key=lambda m: m["_id"]) == sorted(matches_before, key=lambda m: m["_id"])
    assert db.matches_undone.count_documents({}) == 0


def test_legacy_matches_without_rating_changes_are_refused(db):
    add_players(db)
    ids = play(db, [team_match("Escort", s) for s in range(3)])
    legacy = db.matches.find_one({"_id": ids[2]})
    for p in legacy["team1"]:
        p.pop("mmrchange")
    db.matches.replace_one({"_id": ids[2]}, legacy)
    before = state(db)
    with pytest.raises(matchops.MatchOpError, match="no recorded rating change"):
        matchops.undo(db, ids[0])
    assert_same(state(db), before)


def test_unprocessed_match_and_heatmaps(db):
    add_players(db)
    raw = team_match("Escort", 7)
    raw["players"][0]["heatmap"] = [[1, 2, 30.0], [3, 4, 10.0]]
    first = matchops.submit(db, copy.deepcopy(raw))
    second_raw = copy.deepcopy(raw)
    second_raw["players"][0]["heatmap"] = [[1, 2, 10.0]]
    second = matchops.submit(db, second_raw)
    name = db.matches.find_one({"_id": first})["team1"][0]["player"]
    merged = db.players.find_one({"name": name})["eheatmap"]["rome"]
    assert merged["count"] == 2 and merged["heatmap"]["1,2"] == pytest.approx(20.0)
    matchops.undo(db, second)  # not processed yet: removed, heatmap averaged back
    restored = db.players.find_one({"name": name})["eheatmap"]["rome"]
    assert restored["count"] == 1 and restored["heatmap"] == {"1,2": pytest.approx(30.0), "3,4": pytest.approx(10.0)}
    matchops.undo(db, first)
    assert "rome" not in db.players.find_one({"name": name}).get("eheatmap", {})
    assert db.matches.count_documents({}) == 0


def test_map_and_host_only_edit_skips_the_replay(db):
    add_players(db)
    raws = [team_match("Escort", s, host="Alpha") for s in range(3)]
    ids = play(db, raws)
    db.maps.insert_one({"name": "Venice", "e": {"kills": 0, "deaths": 0, "score": 0, "hostwins": 0, "hostlosses": 0,
                                                "games": 0, "hostrating": 1000, "players": 0}})
    ratings = {p["name"]: p["emmr"] for p in db.players.find()}
    result = matchops.edit(db, ids[0], {"map": "Venice"})
    assert result["replayed"] == 0
    assert {p["name"]: p["emmr"] for p in db.players.find()} == ratings
    assert db.maps.find_one({"name": "Venice"})["e"]["games"] == 1
    assert db.maps.find_one({"name": "Rome"})["e"]["games"] == 2


def test_edit_validation(db):
    add_players(db)
    ids = play(db, [team_match("Escort", 1), ffa_match(2)])
    team = db.matches.find_one({"_id": ids[0]})
    with pytest.raises(matchops.MatchOpError, match="contradicts"):
        matchops.edit(db, ids[0], {"outcome": 3 - team["outcome"] if team["outcome"] else 1})
    with pytest.raises(matchops.MatchOpError, match="not found"):
        bad = [dict(p) for p in team["team1"]]
        bad[0]["player"] = "Nobody"
        matchops.edit(db, ids[0], {"team1": bad})
    with pytest.raises(matchops.MatchOpError, match="both teams"):
        matchops.edit(db, ids[0], {"team1": team["team1"] + [team["team2"][0]]})
    with pytest.raises(matchops.MatchOpError, match="can't change"):
        matchops.edit(db, ids[0], {"mode": "Manhunt"})
    with pytest.raises(matchops.MatchOpError, match="not teams"):
        matchops.edit(db, ids[1], {"team1": []})
    assert db.match_edits.count_documents({}) == 0


def test_dry_run_changes_nothing(db):
    add_players(db)
    ids = play(db, [team_match("Escort", s) for s in range(4)])
    before = state(db)
    result = matchops.undo(db, ids[1], dry_run=True)
    assert result["replayed"] == 2 and result["dry_run"]
    assert_same(state(db), before)


def test_history_points_are_shifted_by_day(db):
    add_players(db)
    db.players.update_one({"name": "Alpha"}, {"$set": {"ehistory": {"dates": ["25-01-01", "25-01-02", "25-01-03"],
                                                                     "mmrs": [1000, 1010, 1020]}}})
    before = [{"_id": 1, "mode": "Escort", "date": "2025-01-02", "team1": [{"player": "Alpha", "mmrchange": 10}],
               "team2": []},
              {"_id": 2, "mode": "Escort", "date": "2025-01-03", "team1": [{"player": "Alpha", "mmrchange": 10}],
               "team2": []}]
    after = [{"_id": 2, "mode": "Escort", "date": "2025-01-03", "team1": [{"player": "Alpha", "mmrchange": 12}],
              "team2": []}]
    matchops._fix_history(db, before, after)
    assert db.players.find_one({"name": "Alpha"})["ehistory"]["mmrs"] == [1000, 1000, 1012]


def test_domination_margin_does_not_change_ratings(db):
    # there's no bar percentage data, so Domination has no stomp bonus
    add_players(db)
    close = team_match("Domination", 3)
    winners = 1 if sum(p["score"] for p in close["players"][:4]) > sum(p["score"] for p in close["players"][4:]) else 2
    (mid,) = play(db, [close])
    changes = lambda m: [p["mmrchange"] for p in m["team1"] + m["team2"]]
    before = changes(db.matches.find_one({"_id": mid}))
    matchops.undo(db, mid)
    stomp = copy.deepcopy(close)
    for p in stomp["players"][:4] if winners == 1 else stomp["players"][4:]:
        p["score"] += 5000
    (mid,) = play(db, [stomp])
    assert changes(db.matches.find_one({"_id": mid})) == before


def test_command_line_submit_undo_and_operations(db, monkeypatch, capsys):
    import io
    import json

    from bson import ObjectId

    add_players(db)
    op = ObjectId()
    db.match_operations.insert_one({"_id": op, "status": "queued"})
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(team_match("Escort", 9))))
    assert matchops.main(["submit", "--host", "Alpha", "--operation", str(op), "--actor", "Api"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["processed"][0]["id"] == out["match"]
    assert all(p["mmrchange"] is not None for p in out["processed"][0]["players"])
    assert db.match_operations.find_one({"_id": op})["status"] == "done"
    assert db.matches.find_one({"_id": ObjectId(out["match"])})["hostteam"] in (1, 2)

    assert matchops.main(["undo", out["match"], "--actor", "Api", "--source", "api"]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "e"
    assert db.match_edits.find_one()["notified"] is False  # the bot will post a note

    op2 = ObjectId()
    assert matchops.main(["undo", out["match"], "--operation", str(op2)]) == 2
    assert "no match" in json.loads(capsys.readouterr().out)["error"]
    assert db.match_operations.find_one({"_id": op2})["status"] == "failed"


@pytest.mark.parametrize("key,name", [("ac3aa", "AC3 Artifact assault"), ("ac4aa", "AC4 Artifact assault")])
def test_other_games_artifact_assault_is_rated_separately(db, key, name):
    add_players(db)
    before = {p["name"]: (p["acraarmmr"], p["acraadmmr"]) for p in db.players.find()}
    raw = team_match(name, 31)
    raw["mode"] = key.upper()  # any spelling check_mode knows is stored canonically
    (mid,) = play(db, [raw])
    match = db.matches.find_one({"_id": mid})
    assert match["mode"] == name
    roles = {p["role"] for p in match["team1"] + match["team2"]}
    assert roles == {"r", "d"}
    for p in db.players.find():
        assert (p["acraarmmr"], p["acraadmmr"]) == before[p["name"]]  # ACR's AA untouched
        played = [e for e in match["team1"] + match["team2"] if e["player"] == p["name"]]
        if played:
            role = played[0]["role"]
            assert p[f"{key}{role}games"]["total"] == 21
            assert p[f"{key}{role}mmr"] == pytest.approx(1000 + 13 * NAMES.index(p["name"]) + played[0]["mmrchange"])
            assert p[f"{key}{role}history"]["mmrs"][-1] == round(p[f"{key}{role}mmr"])


def test_check_mode_knows_the_new_games():
    from util import check_mode, mode_name

    assert check_mode("ac3 artifact assault", short=True) == "ac3aa"
    assert check_mode("AC4AA") == "ac4 artifact assault"
    assert check_mode("ac4 aa defending", short=True) == "ac4aad"
    assert check_mode("ACR AA", short=True) == "acraa"
    assert check_mode("acr aa running", short=True) == "acraar"
    assert mode_name("acr aa") == "ACR Artifact assault"
    # the names ACR's Artifact assault had before
    assert check_mode("artifact assault", short=True) == "acraa"
    assert check_mode("AA") == "acr artifact assault"
    assert check_mode("aad", short=True) == "acraad"
    assert mode_name("Artifact assault") == "ACR Artifact assault"


def test_ensure_modes_adds_only_what_is_missing(db):
    import add_mode

    add_players(db)
    db.players.update_many({}, {"$unset": {"ac4aarmmr": "", "ac4aargames": ""}})
    db.players.update_one({"name": "Alpha"}, {"$set": {"emmr": 1234}})
    added = add_mode.ensure_modes(db)
    assert added["ac4aar"] == len(NAMES) and added["e"] == 0
    alpha = db.players.find_one({"name": "Alpha"})
    assert alpha["emmr"] == 1234  # existing modes untouched
    assert alpha["ac4aarmmr"] == 800 and alpha["ac4aarstats"]["scored"] == 0
    assert add_mode.ensure_modes(db)["ac4aar"] == 0  # rerunning changes nothing


def test_fill_counters_adds_missing_podium_and_finishes(db):
    import add_mode

    add_players(db)
    db.players.update_many({}, {"$unset": {"asbgames.finishes": "", "asbgames.podium": ""}})
    db.players.update_one({"name": "Alpha"}, {"$set": {"asbgames.total": 12}})
    added = add_mode.fill_counters(db)
    assert added == {"asbgames.podium": len(NAMES), "asbgames.finishes": len(NAMES)}
    alpha = db.players.find_one({"name": "Alpha"})
    assert alpha["asbgames"] == {"total": 12, "won": 10, "lost": 10, "podium": 0, "finishes": 0}
    assert add_mode.fill_counters(db) == {}
