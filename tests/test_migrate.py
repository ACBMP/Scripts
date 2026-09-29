"""Renaming ACR's Artifact assault from aa/aar/aad to acraa/acraar/acraad."""

import io

import add_mode
import matchops
import migrate_acr_aa

from .test_matchops import add_players, play, team_match

OLD_FIELDS = ("mmr", "games", "stats", "history", "rank", "rankchange", "sessionssinceplayed", "lastdecay")


def old_player(name, **extra):
    doc = {"name": name, "ign": name, "hidden": False,
           "badges": [{"mode": "AA Running", "rank": "1st", "season": 3}, {"mode": "Escort", "rank": "2nd"}],
           "emmr": 900}
    for role in ("r", "d"):
        doc.update({f"aa{role}{f}": f"{role}-{f}" for f in OLD_FIELDS})
        doc[f"aa{role}games"] = {"total": 7, "won": 4, "lost": 3}
    doc.update(extra)
    return doc


def test_renames_players_maps_and_matches(db):
    db.players.insert_one(old_player("Alpha"))
    # a player the new add_mode.py already gave empty ACR fields
    db.players.insert_one(old_player("Bravo"))
    add_mode.ensure_modes(db, {"name": "Bravo"})
    db.maps.insert_one({"name": "Rome", "aa": {"games": 5, "hostrating": 1010}, "e": {"games": 2}})
    db.matches.insert_many([{"mode": "Artifact assault"}, {"mode": "artifact Assault"}, {"mode": "Escort"}])
    db.matches_undone.insert_one({"mode": "Artifact assault"})

    report = migrate_acr_aa.migrate(db, out=io.StringIO())
    assert report == {"players": 2, "badges": 2, "maps": 1, "matches": 2, "matches_undone": 1, "match_edits": 0}
    assert db.players.find_one({"name": "Alpha"})["aarmmr"] == "r-mmr"  # only a report

    migrate_acr_aa.migrate(db, apply=True, out=io.StringIO())
    for name in ("Alpha", "Bravo"):
        p = db.players.find_one({"name": name})
        assert not [k for k in p if k.startswith(("aar", "aad"))]
        assert p["acraarmmr"] == "r-mmr" and p["acraadlastdecay"] == "d-lastdecay"
        assert p["acraargames"]["total"] == 7
        assert [b["mode"] for b in p["badges"]] == ["ACR AA Running", "Escort"]
    rome = db.maps.find_one()
    assert "aa" not in rome and rome["acraa"]["hostrating"] == 1010
    assert sorted(m["mode"] for m in db.matches.find()) == ["ACR Artifact assault"] * 2 + ["Escort"]
    assert db.matches_undone.find_one()["mode"] == "ACR Artifact assault"

    # a second run finds nothing left to do
    again = migrate_acr_aa.migrate(db, apply=True, out=io.StringIO())
    assert not any(again.values())


def test_skips_data_played_under_both_names(db):
    db.players.insert_one(old_player("Alpha", acraargames={"total": 2, "won": 1, "lost": 1}))
    out = io.StringIO()
    migrate_acr_aa.migrate(db, apply=True, out=out)
    assert db.players.find_one()["aarmmr"] == "r-mmr"
    assert "Skipped player Alpha" in out.getvalue()


def test_migrated_acr_matches_can_still_be_corrected(db):
    add_players(db)
    # played under the old names, then migrated
    db.players.update_many({}, {"$rename": {f"acraa{r}{f}": f"aa{r}{f}" for r in "rd"
                                            for f in ("mmr", "games", "stats", "history", "rank", "rankchange")}})
    db.maps.update_many({}, {"$rename": {"acraa": "aa"}})
    migrate_acr_aa.migrate(db, apply=True, out=io.StringIO())
    ids = play(db, [team_match("Artifact assault", s) for s in range(3)])  # the old spelling still works
    assert {m["mode"] for m in db.matches.find()} == {"ACR Artifact assault"}
    matchops.undo(db, ids[1])
    assert db.matches.count_documents({}) == 2
