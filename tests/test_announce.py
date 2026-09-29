"""The Discord side: parsing corrections, the persistent buttons and the posting loop."""

import copy
import re
import types

import pytest

import botconfig
import match_announce
import matchops

from .test_matchops import add_players, ffa_match, play, team_match


def test_parse_player_lines_allows_spaces_in_names():
    rows = match_announce.parse_player_lines("Tha Fazz 6325 6 6\nDellpit 5515 7 7\n", aa=False)
    assert rows == [{"player": "Tha Fazz", "score": 6325, "kills": 6, "deaths": 6},
                    {"player": "Dellpit", "score": 5515, "kills": 7, "deaths": 7}]
    aa = match_announce.parse_player_lines("A B 3 1 2 1", aa=True)
    assert aa == [{"player": "A B", "score": 3, "kills": 1, "deaths": 2, "scored": 1}]
    with pytest.raises(matchops.MatchOpError, match="line 1"):
        match_announce.parse_player_lines("Dellpit 5515 7", aa=False)


def test_button_custom_ids_round_trip():
    button = match_announce.MatchButton("undo", "0123456789abcdef01234567")
    match = re.fullmatch(match_announce.BUTTON_PATTERN, button.item.custom_id)
    assert match and match["action"] == "undo" and match["id"] == "0123456789abcdef01234567"


async def test_correct_form_reports_only_real_changes(db):
    add_players(db)
    (mid,) = play(db, [team_match("Escort", 5, host="Alpha")])
    match = db.matches.find_one({"_id": mid})
    form = match_announce.CorrectModal(match)
    assert form.changes() == {}
    lines = form.team1.default.splitlines()
    name, score, kills, deaths = lines[0].rsplit(" ", 3)
    lines[0] = f"{name} {int(score) + 50} {kills} {deaths}"
    form.team1._value = "\n".join(lines)
    form.map._value = "Venice"
    changes = form.changes()
    assert set(changes) == {"team1", "map"} and changes["team1"][0]["score"] == int(score) + 50


async def test_ffa_form(db):
    add_players(db)
    (mid,) = play(db, [ffa_match(3)])
    form = match_announce.CorrectModal(db.matches.find_one({"_id": mid}))
    assert form.changes() == {}
    assert len(form.children) == 3  # players, map, host


class FakeMessage:
    def __init__(self, mid, embed, view):
        self.id, self.embed, self.view = mid, embed, view

    async def edit(self, embed=None, view=None):
        self.embed, self.view = embed, view


class FakeChannel:
    id = 42

    def __init__(self):
        self.messages = {}

    async def send(self, embed=None, view=None):
        message = FakeMessage(len(self.messages) + 1, embed, view)
        self.messages[message.id] = message
        return message

    async def fetch_message(self, mid):
        return self.messages[mid]


async def test_posting_loop_posts_matches_and_notes_outside_changes(db, monkeypatch):
    add_players(db)
    ids = play(db, [team_match("Escort", s) for s in range(2)])
    channel = FakeChannel()
    monkeypatch.setattr(botconfig, "match_channel", 42, raising=False)
    monkeypatch.setattr(match_announce, "util_client", types.SimpleNamespace(get_channel=lambda cid: channel))

    await match_announce.announce_loop.coro()
    assert len(channel.messages) == 2
    first = db.matches.find_one({"_id": ids[0]})
    assert first["announced"] is True and first["announcement"] == {"channel": 42, "message": 1}
    post = channel.messages[1]
    assert post.embed.footer.text == f"Match {ids[0]}"
    assert [c.custom_id for c in post.view.children] == [f"anmatch:edit:{ids[0]}", f"anmatch:undo:{ids[0]}"]

    # an undo through AN-API: the post is updated and loses its buttons
    matchops.undo(db, ids[0], actor="WebAdmin", source="website")
    await match_announce.announce_loop.coro()
    assert post.view is None
    status = [f.value for f in post.embed.fields if f.name == "Status"]
    assert status == ["Undone by WebAdmin via the website"]
    assert len(channel.messages) == 2  # nothing new to post
    assert db.match_edits.find_one()["notified"] is True


async def test_posting_is_off_without_a_channel(db, monkeypatch):
    add_players(db)
    play(db, [team_match("Escort", 1)])
    monkeypatch.setattr(botconfig, "match_channel", None, raising=False)
    await match_announce.announce_loop.coro()
    assert db.matches.find_one()["announced"] is False
