"""
Discord side of match corrections.

* Every processed match is posted to ``botconfig.match_channel`` with
  **Undo** and **Correct** buttons (privilege <= 5 only, like other admin
  commands). Undo asks for confirmation; Correct opens a form with the
  players' stats, the outcome, map and host.
* Changes made elsewhere (AN-API, the website) are noted under the original
  post, which is updated to show the new state.

The buttons are persistent (custom ids ``anmatch:<action>:<match id>``), so
they keep working after the bot restarts.
"""

import asyncio
import re

import discord
from bson import ObjectId
from discord.ext import tasks

import botconfig as conf
import matchops
import util

BUTTON_PATTERN = r"anmatch:(?P<action>undo|edit):(?P<id>[0-9a-f]{24})"
ANNOUNCE_BATCH = 10

MODE_NAMES = {
    "e": "Escort", "mh": "Manhunt", "do": "Domination", "dm": "Deathmatch",
    "asb": "Assassinate Brotherhood", "acraa": "ACR Artifact Assault", "ac3aa": "AC3 Artifact Assault", "ac4aa": "AC4 Artifact Assault",
}


def match_channel_id():
    return getattr(conf, "match_channel", None)


def privileged(discord_user):
    """The player doc of a Discord user allowed to change matches, or None."""
    db = util.connect()
    user = db.players.find_one({"discord_id": str(discord_user.id)})
    if user is None or user.get("privilege", 99) > 5:
        return None
    return user


async def blocking(fn, *args, **kwargs):
    """Run a database operation off the event loop, holding the match lock."""
    def run():
        with matchops.locked():
            return fn(util.connect(), *args, **kwargs)

    return await asyncio.get_running_loop().run_in_executor(None, run)


def _fmt_change(value):
    if value is None:
        return ""
    return f" ({value:+.1f})"


def match_embed(match, status=None):
    mode = matchops.short_mode(match)
    title = f"{MODE_NAMES.get(mode, match.get('mode'))}"
    if match.get("map"):
        title += f" on {match['map']}"
    embed = discord.Embed(title=title, color=0x7f7f7f if status else 0x00f5ff)
    when = " ".join(x for x in (match.get("date"), (match.get("time") or "").replace("-", ":")) if x)
    embed.description = when
    if matchops.is_ffa(match):
        lines = [f"{i + 1}. {p['player']} - {p['score']} ({p['kills']}/{p['deaths']}){_fmt_change(p.get('mmrchange'))}"
                 for i, p in enumerate(match.get("players") or [])]
        embed.add_field(name="Players", value="\n".join(lines) or "-", inline=False)
    else:
        outcome = match.get("outcome")
        for team in (1, 2):
            head = f"Team {team}" + (" (won)" if outcome == team else (" (tie)" if outcome == 0 else ""))
            lines = []
            for p in match.get(f"team{team}", []):
                extra = f", {p['scored']} art." if "scored" in p else ""
                lines.append(f"{p['player']} - {p['score']} ({p['kills']}/{p['deaths']}{extra})"
                             f"{_fmt_change(p.get('mmrchange'))}")
            embed.add_field(name=head, value="\n".join(lines) or "-", inline=True)
    if match.get("host"):
        embed.add_field(name="Host", value=match["host"], inline=False)
    if status:
        embed.add_field(name="Status", value=status, inline=False)
    embed.set_footer(text=f"Match {match['_id']}")
    return embed


def match_view(match_id):
    view = discord.ui.View(timeout=None)
    view.add_item(MatchButton("edit", str(match_id)))
    view.add_item(MatchButton("undo", str(match_id)))
    return view


async def _update_post(match, status, keep_buttons):
    post = match.get("announcement")
    if not post:
        return
    channel = util_client.get_channel(post["channel"])
    if channel is None:
        return
    try:
        message = await channel.fetch_message(post["message"])
        await message.edit(embed=match_embed(match, status),
                           view=match_view(match["_id"]) if keep_buttons else None)
    except discord.HTTPException:
        pass


class MatchButton(discord.ui.DynamicItem[discord.ui.Button], template=BUTTON_PATTERN):
    def __init__(self, action, match_id):
        super().__init__(discord.ui.Button(
            label="Undo" if action == "undo" else "Correct",
            style=discord.ButtonStyle.danger if action == "undo" else discord.ButtonStyle.secondary,
            custom_id=f"anmatch:{action}:{match_id}",
        ))
        self.action = action
        self.match_id = match_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["action"], match["id"])

    async def callback(self, interaction):
        actor = privileged(interaction.user)
        if actor is None:
            await interaction.response.send_message("You need AN admin rights to change matches.", ephemeral=True)
            return
        match = util.connect().matches.find_one({"_id": ObjectId(self.match_id)})
        if match is None:
            await interaction.response.send_message("This match has already been undone.", ephemeral=True)
            return
        if self.action == "undo":
            await interaction.response.send_message(
                "Undo this match? Every rating it touched is recalculated.",
                view=ConfirmUndo(self.match_id), ephemeral=True)
        else:
            await interaction.response.send_modal(CorrectModal(match))


class ConfirmUndo(discord.ui.View):
    def __init__(self, match_id):
        super().__init__(timeout=120)
        self.match_id = match_id

    @discord.ui.button(label="Yes, undo it", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        actor = privileged(interaction.user)
        if actor is None:
            await interaction.response.send_message("You need AN admin rights to change matches.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        db = util.connect()
        before = db.matches.find_one({"_id": ObjectId(self.match_id)})
        try:
            result = await blocking(matchops.undo, self.match_id, actor=actor["name"], source="discord")
        except matchops.MatchOpError as exc:
            await interaction.followup.send(f"Couldn't undo: {exc}", ephemeral=True)
            return
        if before:
            await _update_post(before, f"Undone by {actor['name']}", keep_buttons=False)
        await interaction.followup.send(
            f"Undone. {result.get('replayed', 0)} later match(es) recalculated.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        await interaction.response.edit_message(content="Cancelled.", view=None)


def _player_lines(entries, aa):
    return "\n".join(
        f"{p['player']} {p['score']} {p['kills']} {p['deaths']}" + (f" {p.get('scored', 0)}" if aa else "")
        for p in entries
    )


def parse_player_lines(text, aa):
    """``name score kills deaths [scored]`` per line; names may contain spaces."""
    numbers = 4 if aa else 3
    out = []
    for n, line in enumerate(text.strip().splitlines(), 1):
        parts = line.split()
        if not parts:
            continue
        if len(parts) <= numbers or not all(re.fullmatch(r"-?\d+", x) for x in parts[-numbers:]):
            raise matchops.MatchOpError(
                f"line {n}: expected 'name score kills deaths{' scored' if aa else ''}', got {line!r}")
        values = [int(x) for x in parts[-numbers:]]
        entry = {"player": " ".join(parts[:-numbers]), "score": values[0], "kills": values[1], "deaths": values[2]}
        if aa:
            entry["scored"] = values[3]
        out.append(entry)
    return out


class CorrectModal(discord.ui.Modal):
    def __init__(self, match):
        super().__init__(title="Correct match", timeout=600)
        self.match = match
        self.ffa = matchops.is_ffa(match)
        self.aa = util.is_aa(matchops.short_mode(match))
        hint = "name score kills deaths" + (" scored" if self.aa else "")
        if self.ffa:
            self.players = discord.ui.TextInput(label=f"Players ({hint})", style=discord.TextStyle.paragraph,
                                                default=_player_lines(match.get("players") or [], False)[:4000])
            self.add_item(self.players)
        else:
            self.team1 = discord.ui.TextInput(label=f"Team 1 ({hint})"[:45], style=discord.TextStyle.paragraph,
                                              default=_player_lines(match["team1"], self.aa)[:4000])
            self.team2 = discord.ui.TextInput(label=f"Team 2 ({hint})"[:45], style=discord.TextStyle.paragraph,
                                              default=_player_lines(match["team2"], self.aa)[:4000])
            self.outcome = discord.ui.TextInput(label="Winner (1, 2, or 0 for a tie)", max_length=1,
                                                default=str(match.get("outcome", 0)))
            for item in (self.team1, self.team2, self.outcome):
                self.add_item(item)
        self.map = discord.ui.TextInput(label="Map", required=False, default=match.get("map") or "")
        self.host = discord.ui.TextInput(label="Host", required=False, default=match.get("host") or "")
        self.add_item(self.map)
        self.add_item(self.host)

    def changes(self):
        m = self.match
        changes = {}
        if self.ffa:
            players = parse_player_lines(self.players.value, False)
            if players != [{k: p[k] for k in ("player", "score", "kills", "deaths")} for p in m.get("players") or []]:
                changes["players"] = players
        else:
            for team, field in (("team1", self.team1), ("team2", self.team2)):
                entries = parse_player_lines(field.value, self.aa)
                keys = ("player", "score", "kills", "deaths") + (("scored",) if self.aa else ())
                if entries != [{k: p.get(k) for k in keys} for p in m[team]]:
                    changes[team] = entries
            if self.outcome.value.strip() != str(m.get("outcome")):
                try:
                    changes["outcome"] = int(self.outcome.value)
                except ValueError:
                    raise matchops.MatchOpError("the winner must be 0, 1 or 2")
        if self.map.value.strip() and self.map.value.strip() != (m.get("map") or ""):
            changes["map"] = self.map.value.strip()
        if self.host.value.strip() != (m.get("host") or ""):
            changes["host"] = self.host.value.strip()
        return changes

    async def on_submit(self, interaction):
        actor = privileged(interaction.user)
        if actor is None:
            await interaction.response.send_message("You need AN admin rights to change matches.", ephemeral=True)
            return
        try:
            changes = self.changes()
        except matchops.MatchOpError as exc:
            await interaction.response.send_message(f"Nothing changed: {exc}", ephemeral=True)
            return
        if not changes:
            await interaction.response.send_message("Nothing to change.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            result = await blocking(matchops.edit, str(self.match["_id"]), changes, actor=actor["name"],
                                    source="discord")
        except matchops.MatchOpError as exc:
            await interaction.followup.send(f"Couldn't correct the match: {exc}", ephemeral=True)
            return
        updated = util.connect().matches.find_one({"_id": self.match["_id"]})
        if updated:
            await _update_post(updated, f"Corrected by {actor['name']}", keep_buttons=True)
        await interaction.followup.send(
            f"Corrected ({', '.join(changes)}). {result.get('replayed', 0)} later match(es) recalculated.",
            ephemeral=True)


# --- the posting loop -----------------------------------------------------------------

util_client = None


@tasks.loop(seconds=30)
async def announce_loop():
    channel_id = match_channel_id()
    if not channel_id:
        return
    channel = util_client.get_channel(channel_id)
    if channel is None:
        return
    db = util.connect()
    pending = list(db.matches.find({"announced": False, "new": False}).limit(ANNOUNCE_BATCH))
    for match in pending:
        try:
            message = await channel.send(embed=match_embed(match), view=match_view(match["_id"]))
        except discord.HTTPException as exc:
            print(f"announce: couldn't post match {match['_id']}: {exc}")
            break
        db.matches.update_one({"_id": match["_id"]}, {"$set": {
            "announced": True, "announcement": {"channel": channel.id, "message": message.id}}})
    # changes made through AN-API / the website
    for change in db.match_edits.find({"notified": False}).limit(ANNOUNCE_BATCH):
        db.match_edits.update_one({"_id": change["_id"]}, {"$set": {"notified": True}})
        via = {"api": "the API", "website": "the website"}.get(change.get("source"), change.get("source") or "?")
        if change["op"] == "undo":
            await _update_post(change["before"], f"Undone by {change.get('actor') or '?'} via {via}",
                               keep_buttons=False)
        else:
            current = db.matches.find_one({"_id": change["match"]})
            if current:
                await _update_post(current, f"Corrected by {change.get('actor') or '?'} via {via}",
                                   keep_buttons=True)


@announce_loop.before_loop
async def _wait_ready():
    await util_client.wait_until_ready()


def setup(client):
    """Register the persistent buttons and start posting (call from the client's setup_hook)."""
    global util_client
    util_client = client
    client.add_dynamic_items(MatchButton)
    if not announce_loop.is_running():
        announce_loop.start()
