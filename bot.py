import botconfig as conf
import random
import discord
from discord.utils import get
from discord.ext import commands
import teams
import util
import re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, date, timezone
import AC_Score_OCR
import requests
import sys
import tweet
import glob
import os
import sanity
import synergy
import elostats
import numpy as np
from scipy.special import binom
from add_badges import readable_badges

# Members intent
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print("Starting.")

modes_list = ['e', 'mh', 'aar', 'aad', 'do', 'dm', 'asb']
modes_dict = {
        'e' : "Escort",
        'mh' : 'Manhunt',
        'aar' : 'AA Running',
        'aad' : 'AA Defending',
        'aa' : 'Artifact Assault',
        'do' : 'Domination',
        'dm' : 'Deathmatch',
        'asb': 'Assassinate Brotherhood'
        }


async def send_long_message(content, channel):
    """
    discord has a 2k char limit which we often hit with eg matches
    embed has a limit of 4096 so that's not a great way to bypass this is a lot easier
    """
    if content[-1] == "\n":
        content = content[:-1]
    elif len(content) < 2000:
        await sync_channels(content, channel_id=channel.id, server_id=channel.guild.id, nick="Assassins' Network")
        return
    line_split = content.split("\n")
    line = ""
    for i in range(len(line_split)):
        newline = line + "\n" + line_split[i]
        if len(newline) > 2000:
            await sync_channels(line, channel_id=channel.id, server_id=channel.guild.id, nick="Assassins' Network")
            line = ""
        line += "\n" + line_split[i]
    await sync_channels(line, channel_id=channel.id, server_id=channel.guild.id, nick="Assassins' Network")
    return


def help_message(message):
    # simple message parsing
    msg = message.content.lower()
    msg = msg.replace("help ", "")
    msg = msg.replace("help", "")

    # long descriptions for each function
    # they need to be ugly like this for ```css to work and not using that makes it look ugly
    intro = "Welcome to the Assassins' Network bot. The following commands are currently available:\n"
    team_help = "To generate random teams, send:\n" +"""```css
AN team comps [PLAYER_0, PLAYER_2, PLAYER_3...] [mode MODE] [random FACTOR]```""" + "\nNot specifying players uses the queue from the specified mode.\nPlayer names must be Assassins' Network names.\nTo force players onto the same team, separate names by \" & \" instead of \", \"."
    lfg_help = """\nTo queue up for a game, type\n```css
AN play [PLAYER] [mode MODE] [in START_TIME] [for LENGTH_TIME]```\nIf PLAYER is unspecified, the bot attempts to match your Discord account to a player. Otherwise, these must be AN usernames.\nTimes must be given in hours. Default `LENGTH_TIME` is 3 hours, default mode is defined by the server the command is sent in."""
    lookup_help = """To look up a user's stats on AN, type\n```css
AN lookup [PLAYER]```"""
    synergy_help = """To look up a user's synergies, type\n```css
AN synergy [PLAYER] [MODE] [MIN_GAMES] [TRACK_TEAMS]```"""
    queue_rm_help = """To remove yourself from all queues you are currently in, use\n```css
AN queue remove```"""
    queue_help = """To print the players currently queued up for a mode, use\n```css
AN queue [MODE]```"""
    remake_help = """To calculate whether a game should be remade after a disutil.connect, use\n```css
AN remake TEAM_1_SCORE TEAM_2_SCORE TIME_LEFT PLAYERS_PER_TEAM [MODE]```Whereby time is in-game time formatted as X:YZ."""
    ocr_help = """To use optical character recognition to scan screenshots into the AN matches format, use the following with the screenshot attached\n```css
AN OCR [GAME] [TOTAL_PLAYERS] [+CORRECTION TEAM]```This currently only supports ACB and ACR AA.\nScreenshots must be uncropped pictures taken from your PC or similar, i.e. phone pictures won't work.\nTo correct for e.g. one dodge on team 1, append +750 1."""
    add_help = f"""To queue matches for being added to AN, use\n```css
AN add FORMATTED_MATCH```with the match data formatted in the AN format pinned in #an-help on the #secualhealing server, e.g.:\n```css
M, 3, 1, DevelSpirit$7760$8$6, x-JigZaw$6960$6$7, EsquimoJo$4400$5$6, Tha Fazz$6325$6$6, dripdriply$5935$6$6, Dellpit$5515$7$7```If you want to save map and/or host:\n```css
E$Forli$HOST_PLAYER, 2, 1, ...```Where the maps are identified by the following keys: {", ".join(util.identify_map(get_map_keys=True))}."""
    edit_help = """To edit ALL the matches to be added to the database, use\n```css
AN edit UPDATED_MATCHES```Please note that you should first print all matches with ```css
AN print``` and edit those results, then feed ALL the matches to this in one single command. Otherwise, all unmentioned matches will be removed."""
    replace_help = """To replace certain content in the matches to be queued to the database, use\n```css
AN replace ORIGINAL with REPLACEMENT```"""
    print_help = """To print the matches currently queued to be added to the database, use\n```css
AN print```"""
    update_help = """If you have the Assassins' Network role, you can update the matches in the database using\n```css
AN update```Note that improperly formatted matches won't be added. If this occurs, please contact Dell."""
    missing_help = """To add missing data to an old match, use\n```css
AN missing OLD_MATCH_DATA, NEW_KEY: NEW_VALUE```"""
    user_add_help = """If you have the Assassins' Network role, you can add users to the database using\n```css
AN user add NAME; IGN[1, IGN2, ...]; LINK; COUNTRY; PLATFORM[1, PLATFORM2, ...]; @USER```"""
    user_edit_help = """If you have the Assassins' Network role, you can edit users in the database using\n```css
AN user edit NAME: KEY: VALUE```Please note that new values need to be formatted like Python code, e.g. instead of nation: US, run nation: \"US\"."""
    sanity_help = """To run the sanity checker over the currently added matches, run\n```css
AN sanity```"""
    compare_help = """To find the likelihood of one team beating another, run\n```css
AN compare PLAYER_A[, ADDITIONAL_PLAYER_A] vs PLAYER_B[, ADDITIONAL_PLAYER_B]```"""
    estimate_help = """To estimate players' rating changes in a match, run\n```css
AN estimate PLAYER_A[, ADDITIONAL_PLAYER_A] vs PLAYER_B[, ADDITIONAL_PLAYER_B] [mode MODE]```"""
    ladder_help = """To view the leaderboard for a mode, run\n```css
AN ladder [MODE]```"""
    reload_help = """To reload all the bot's imported modules, run\n```css
AN reload```"""
    lobbies_help = """To generate MMR-based lobbies, run\n```css
AN lobbies PLAYER_A, PLAYER_B, PLAYER_C, PLACER_D, ...```Grouped lobby generation is currently not supported, but is being worked on."""
    swap_help = """To swap teams in an OCR result, run\n```css
AN swap MATCHDATA```with `MATCHDATA` formatted for AN add."""

    # if the user asked for help on a specific function the msg isn't empty after parsing
    # so we find out what it is and return an embed with the long description from above
    if msg != "":
        if msg == "team comps":
            return discord.Embed(title=":elevator: Team Generator", description=team_help, color=0xff00fe)
        elif msg == "lobbies":
            return discord.Embed(title=":put_litter_in_its_place: Lobbies Generator", description=lobbies_help, color=0xff00fe)
        elif msg == "play":
            return discord.Embed(title=":vibration_mode: Add to Queue", description=lfg_help, color=0xff00fe)
        elif msg == "queue remove":
            return discord.Embed(title=":no_mobile_phones: Remove from Queue", description=queue_rm_help, color=0xff00fe)
        elif msg == "queue":
            return discord.Embed(title=":flag_gb: Print Queue", description=queue_help, color=0xff00fe)
        elif msg == "lookup":
            return discord.Embed(title=":mag: User Lookup", description=lookup_help, color=0xff00fe)
        elif msg == "synergy":
            return discord.Embed(title=":handshake: Lookup Synergies", description=synergy_help, color=0xff00fe)
        elif msg == "remake":
            return discord.Embed(title=":judge: Remake Calculator", description=remake_help, color=0xff00fe)
        elif msg == "compare":
            return discord.Embed(title=":wrestlers: Compare Users", description=compare_help, color=0xff00fe)
        elif msg == "estimate":
            return discord.Embed(title=":chart: Estimate Changes", description=estimate_help, color=0xff00fe)
        elif msg == "ocr":
            return discord.Embed(title=":camera: Scan Screenshot", description=ocr_help, color=0xff00fe)
        elif msg == "swap":
            return discord.Embed(title=":left_right_arrow: Swap Teams", description=swap_help, color=0xff00fe)
        elif msg == "sanity":
            return discord.Embed(title=":confused: Sanity Check", description=sanity_help, color=0xff00fe)
        elif msg == "add":
            return discord.Embed(title=":memo: Add Matches", description=add_help, color=0xff00fe)
        elif msg == "replace":
            return discord.Embed(title=":crayon: Replace Match Content", description=replace_help, color=0xff00fe)
        elif msg == "missing":
            return discord.Embed(title=":question: Add Missing Data", description=missing_help, color=0xff00fe)
        elif msg == "print":
            return discord.Embed(title=":printer: Print Matches", description=print_help, color=0xff00fe)
        elif msg == "ladder":
            return discord.Embed(title=":ladder: View Leaderboard", description=ladder_help, color=0xff00fe)
    # otherwise we do one giant embed and keep adding fields with functions
    else:
         embedVar = discord.Embed(title="Assassins' Network Help", url = "https://assassins.network/", color = 0xffa8e8)
         embedVar.set_thumbnail(url="https://assassins.network/static/an_logo_white.png")
         embedVar.add_field(name=":vibration_mode: Add to Queue", value="AN play", inline=True)
         embedVar.add_field(name=":no_mobile_phones: Remove from Queue", value="AN queue remove", inline=True)
         embedVar.add_field(name=":flag_gb: Print Queue", value="AN queue", inline=True)
         embedVar.add_field(name=":elevator: Team Generator", value="AN team comps", inline=True)
         embedVar.add_field(name=":put_litter_in_its_place: Lobbies Generator", value="AN lobbies", inline=True)
         embedVar.add_field(name=":mag: User Lookup", value="AN lookup", inline=True)
         embedVar.add_field(name=":handshake: Lookup Synergies", value="AN synergy", inline=True)
         embedVar.add_field(name=":judge: Remake Calculator", value="AN remake", inline=True)
         embedVar.add_field(name=":wrestlers: Compare Users", value="AN compare", inline=True)
         embedVar.add_field(name=":chart: Estimate Changes", value="AN estimate", inline=True)
         embedVar.add_field(name=":camera: Scan Screenshot", value="AN OCR", inline=True)
         embedVar.add_field(name=":left_right_arrow: Swap Teams", value="AN swap", inline=True)
         embedVar.add_field(name=":memo: Add Matches", value="AN add", inline=True)
         embedVar.add_field(name=":printer: Print Matches", value="AN print", inline=True)
         embedVar.add_field(name=":confused: Sanity Check", value="AN sanity", inline=True)
         embedVar.add_field(name=":crayon: Replace Match Content", value="AN replace", inline=True)
         embedVar.add_field(name=":question: Add Missing Data", value="AN missing", inline=True)
         embedVar.add_field(name=":ladder: View Leaderboard", value="AN ladder", inline=True)
         embedVar.set_footer(text="For more information, use AN help COMMAND.")

    # if the channel name fits we add the AN db/parsing functions
    if message.channel.name in ["an-help", "assassinsnetwork"] or message.author.id in conf.admin:
        if msg != "":
            if msg == "edit":
                return discord.Embed(title=":pencil2: Edit Matches", description=edit_help, color=0xff00fe)
            elif msg == "update":
                return discord.Embed(title=":pager: Update Matches", description=update_help, color=0xff00fe)
            elif msg == "user add":
                return discord.Embed(title=":chess_pawn: Add Users", description=user_add_help, color=0xff00fe)
            elif msg == "user edit":
                return discord.Embed(title=":performing_arts: Edit Users", description=user_edit_help, color=0xff00fe)
            elif msg == "reload":
                return discord.Embed(title=":arrows_clockwise: Reload Modules", description=reload_help, color=0xff00fe)
        else:
            embedVar.add_field(name=":pencil2: Edit Matches", value="AN edit", inline=True)
            embedVar.add_field(name=":pager: Update Matches", value="AN update", inline=True)
            embedVar.add_field(name=":chess_pawn: Add Users", value="AN user add", inline=True)
            embedVar.add_field(name=":performing_arts: Edit Users", value="AN user edit", inline=True)
            embedVar.add_field(name=":arrows_clockwise: Reload Modules", value="AN reload", inline=True)

    return embedVar


def rank_pic_big(elo):
    """
    grabs rank pics, copied from an_flask
    """
    if elo < 801:
        return "badge_1_big.png"
    if elo < 1000:
        return "badge_2_big.png"
    if elo < 1100:
        return "badge_3_big.png"
    if elo < 1200:
        return "badge_4_big.png"
    if elo < 1400:
        return "badge_6_big.png"
    return "badge_5_big.png"


# command to look up a user on the AN db
# util.connect to DB -> look up user -> print user
@util.command_dec
async def lookup_user(message):
    player = message.content.replace("lookup ", "")
    player = player.replace("  ", " ")
    db = util.connect()
    if player == "lookup":
        player_db = db.players.find_one({"discord_id" : str(message.author.id)})
        player = player_db["name"]
    elif "@" in player:
        discord_id = player.replace("@!", "").replace("@", "").replace(">", "").replace("<", "")
        player_db = db.players.find_one({"discord_id" : discord_id})
        player = player_db["name"]
    else:
        player_db = util.identify_player(db, player)
    if player_db is None:
        embedVar = discord.Embed(title="Congratulations, you're an Xbox player!", url="https://assassins.network/players", color=0xff00ff)
        embedVar.add_field(name=util.find_insult(), value="Did not recognize username.\nPlease check that it's the same as on https://assassins.network/players.")
    elif player_db["hidden"] == True and str(message.author.id) != player_db["discord_id"]:
        embedVar = discord.Embed(title="Congratulations, you're an Xbox player!", url="https://assassins.network/players", color=0xff00ff)
        embedVar.add_field(name=util.find_insult(), value="The user you have tried to look up has opted to rename hidden.")
    else:
        # embed title is player name and their country flag as an emoji
        import flag
        if player_db["nation"] != "_unknown":
            embedVar = discord.Embed(title=f"{player} {flag.flag(player_db['nation'])}", url=f"https://assassins.network/profile/{player.replace(' ', '%20')}", color=0xff00ff)
        else:
            embedVar = discord.Embed(title=f"{player} :clown:", url=f"https://assassins.network/profile/{player.replace(' ', '%20')}", color=0xff00ff)
        # only add information that is present
        embedVar.add_field(name="In-Game Names", value=", ".join(player_db["ign"]), inline=False)
        badges = readable_badges(player_db["name"])
        if len(badges) > 0:
            embedVar.add_field(name="Achievements", value=badges, inline=False)
        top_elo = 0
        for mode in util.ALL_MODES:
            if player_db[f"{mode}games"]["total"] > 0:
                top_elo = round(max(top_elo, player_db[f'{mode}mmr']))
                user_stats = f"MMR (Rank): {round(player_db[f'{mode}mmr'])} ({player_db[f'{mode}rank']})\n \
                               Peak MMR: {max(player_db[f'{mode}history']['mmrs'])}\n \
                               Winrate: {round((player_db[f'{mode}games']['won'] / (player_db[f'{mode}games']['total'])) * 100)}% \n"
                user_stats += f"Games Played: {player_db[f'{mode}games']['total']}\n"
                if mode in util.FFA_MODES:
                    user_stats += f"Podium Rate: {round((player_db[f'{mode}games']['podium'] / (player_db[f'{mode}games']['total'])) * 100)}% \n"
                    user_stats += f"Average Finish: {round(player_db[f'{mode}games']['finishes'] / (player_db[f'{mode}games']['total']))} \n"
                if 'aa' not in mode:
                    embedVar.add_field(name=modes_dict[mode], value=user_stats +
                    f"K/D Ratio: {round(player_db[f'{mode}stats']['kills'] / player_db[f'{mode}stats']['deaths'], 2)} \n \
                     Avg Kills / Deaths: {round(player_db[f'{mode}stats']['kills'] / player_db[f'{mode}games']['total'], 2)} / {round(player_db[f'{mode}stats']['deaths'] / player_db[f'{mode}games']['total'], 2)}\n \
                     Highscore: {player_db[f'{mode}stats']['highscore']}", inline=False)
                else:
                    if mode == 'aar':
                        try:
                            deaths_per_score = round(player_db[f'{mode}stats']['deaths'] / player_db[f'{mode}stats']['scored'], 2)
                        except ZeroDivisionError:
                            deaths_per_score = ":infinity:"
                        embedVar.add_field(name=modes_dict[mode], value=user_stats +
                                f"Avg Scores: {round(player_db[f'{mode}stats']['scored'] / player_db[f'{mode}games']['total'], 2)} \n \
                                 Avg Deaths / Score: {deaths_per_score} \n \
                                 Rat Index: {round(player_db[f'{mode}stats']['kills'] / player_db[f'{mode}games']['total'], 3)}",
                                 inline=False)
                    else:
                        embedVar.add_field(name=modes_dict[mode], value=user_stats +
                                f"Avg Kills: {round(player_db[f'{mode}stats']['kills'] / player_db[f'{mode}games']['total'], 2)} \n \
                                 Avg Concedes: {round(player_db[f'{mode}stats']['conceded'] / player_db[f'{mode}games']['total'], 2)}",
                                 inline=False)
        embedVar.set_image(url="https://assassins.network/static/badges/" + rank_pic_big(top_elo))
    await sync_channels(message=message, embed=embedVar)
    return

# WIP
async def lookup_ladder(message):
    """
    Look up and print the leaderboard ladder for a mode.
    """
    mode = message.content.replace("ladder", "").split(" ")[-1]
    mode = util.check_mode(mode, server=message.guild.id, short=True, channel=message.channel.id)
    # try to deal with proper url linking
    mode_link = util.check_mode(mode, short=False)
    mode_link = mode_link.split(" ")[-1]
    # deal with empty leaderboard error
    fname = "table.png"
    try:
        tweet.rank_frame(mode, fname)
    except IndexError:
        fname = "TimDaddy.png"
    table = discord.File(fname, filename=fname)
    embedVar = discord.Embed(title=util.check_mode(mode).title() + " Leaderboard",
            url=f"https://assassins.network/{mode_link}", color=0xff00ff)
    embedVar.set_image(url=f"attachment://{fname}")
    await sync_channels(message=message, embed=embedVar, attachments=[table])


@util.command_dec
async def lookup_synergy(message):
    db = util.connect()
    content = message.content
    content = content[8:]
    content = content.split(" ")
    player = content[0]
    if player == "":
        player = db.players.find_one({"discord_id" : str(message.author.id)})
        player = player["name"]
    else:
        player = util.identify_player(db, player)["name"]
    # this is so primitive I'm sorry
    min_games = 5
    track_teams = False
    date_range = None
    if len(content) > 1:
        mode = content[1]
        if len(content) > 2:
            min_games = int(content[2])
            if len(content) > 3:
                track_teams = (content[3] in ("true", "True"))
                if len(content) > 4:
                    date_range = (content[4], content[5])
    else:
        mode = None
    mode = util.check_mode(mode, message.guild.id, short=False, channel=message.channel.id).capitalize()
    # since there are two modes that are grouped together to AA
    if "Artifact" in mode:
        mode = "Artifact assault"
    embedVar = discord.Embed(title=f"{player}'s {mode.title()} Synergies", color=0xff00ff)
    if util.check_mode(mode, short=True) in util.FFA_MODES:
        synergies = synergy.find_synergy_ffa(player, mode, min_games)
        embedVar.add_field(name="Average Finish (with them in lobby)", value=synergies[0])
        embedVar.add_field(name="Chance to beat", value=synergies[1])
    else:
        synergies = synergy.find_synergy(player, mode, min_games, track_teams, None, date_range)
        embedVar.add_field(name="Top Teammates", value=synergies[0])
        embedVar.add_field(name="Top Opponents (Opponent's Winrate)", value=synergies[1])

    await sync_channels(message=message, embed=embedVar)


@util.command_dec
async def map_synergy(message):
    db = util.connect()
    content = message.content
    content = content[8:]
    content = content.split(" ")
    player = content[0]
    if player == "":
        player = db.players.find_one({"discord_id" : str(message.author.id)})
        player = player["name"]
    else:
        player = util.identify_player(db, player)["name"]
    # this is so primitive I'm sorry
    min_games = 5
    date_range = None
    if len(content) > 1:
        mode = content[1]
        if len(content) > 2:
            min_games = int(content[2])
            if len(content) > 3:
                date_range = (content[4], content[5])
    else:
        mode = None
    mode = util.check_mode(mode, message.guild.id, short=False, channel=message.channel.id).capitalize()
    # since there are two modes that are grouped together to AA
    if "Artifact" in mode:
        mode = "Artifact assault"
    embedVar = discord.Embed(title=f"{player}'s {mode.title()} Map stats", color=0xff00ff)
    if util.check_mode(mode, short=True) in util.FFA_MODES:
        synergies = synergy.map_ffa_synergy(player, mode, min_games, date_range)
        embedVar.add_field(name="Average Finish (wins|pod|games)", value=synergies[0])
        embedVar.add_field(name="Average Statline (score, k/d)", value=synergies[1])
    else:
        synergies = synergy.map_synergy(player, mode, min_games, date_range)
        embedVar.add_field(name="Winrate", value=synergies[0])
        embedVar.add_field(name="Average Statline (score, k/d)", value=synergies[1])

    await sync_channels(message=message, embed=embedVar)

# add a match to the matches.txt file
def add_match(message):
    msg = message.content.replace("add ", "")
    msg = msg.replace("add ", "")
    msg = msg.replace("  ", " ")
    # if the file content is # we overwrite
    # otherwise we append
    with open("matches.txt", "r") as f:
        if "#" in f.readline():
            mode = "w"
        else:
            mode = "a"
        f.close()
    with open("matches.txt", mode) as f:
        f.write(msg + "\n")
        f.close()
    return


# print the matches.txt file
@util.command_dec
async def print_matches(message):
    fname = conf.RAU_FILE_NAME
    if "missing" in message.content:
        fname = conf.RAE_FILE_NAME
    with open(fname, "r") as f:
        content = f.read()
        if content == "#\n":
            content = "No matches currently queued."
        await send_long_message(content, message.channel)
#        try:
#            await message.channel.send(content)
#        except:
#            embedVar = discord.Embed(title="Matches", color=0xff00ff, description=content)
#            await message.channel.send(embed=embedVar)
        f.close()
    return


@util.command_dec
async def sanity_check_matches(message):
    """
    sanity check matches for errors
    """
    try:
        max_err = int(message.content.split("sanity ")[1])
    except Exception:
        max_err = 0
    await send_long_message(sanity.main(max_err), message.channel)


# edit matches.txt file
# this overwrites the whole thing
@util.command_dec
async def edit_matches(message):
    msg = message.content.replace("edit ", "").replace("edit ", "")
    with open("matches.txt", "w") as f:
        f.write(msg)
        f.close()
    await sync_channels("Game(s) edited!", message)
    return


@util.command_dec
async def add_missing(message):
    # database backup
    os.system(f"mongodump -d public -o dump/dump_{str(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))}")
    msg = message.content.replace("missing ", "")
    # if the file content is # we overwrite
    # otherwise we append
    with open(conf.RAE_FILE_NAME, "r") as f:
        if "#" in f.readline():
            mode = "w"
        else:
            mode = "a"
        f.close()
    with open(conf.RAE_FILE_NAME, mode) as f:
        f.write(msg + "\n")
        f.close()
    import read_and_update as rau
    rau.read_and_edit()
    await sync_channels("Missing data added!", message)
    return


# edit matches.txt file by replacing content from the file
@util.command_dec
async def replace_matches(message):
    msg = message.content.replace("replace ", "").replace("replace ", "")
    msg = msg.split(" with ")
    # we specifically want to truncate
    with open("matches.txt", "r") as f:
        c = f.read()
        c = c.replace(msg[0], msg[1])
        f.close()
    # which means we need to open the file again yay
    with open("matches.txt", "w") as f:
        f.write(c)
        f.close()
    await sync_channels(f"Replaced every instance of {msg[0]} with {msg[1]}!", message)
    return


class OutcomeError(Exception):
    pass

# update the AN db by running the read_and_update script
@util.permission_locked
@util.command_dec
async def updater(message):
    # database backup
    os.system(f"mongodump -d public -o dump/dump_{str(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))}")
    try:
        import read_and_update as rau
        rau.main()
        #rau.read_and_update()
        #rau.eloupdate.new_matches()
        #rau.historyupdate.update()
        await sync_channels("Successfully updated the leaderboards!", message)
    except OutcomeError as e:
        await sync_channels("Error! " + e, message)
    except:
        await sync_channels("An error has occurred, please message an administrator.", message)



# command to calculate whether a remake is necessary according to https://rulebook.assassins.network
@util.command_dec
async def check_remake(message):
    """
    Check whether a remake is necessary according to rulebook.
    Assassinate not implemented currently.
    """
    # function called by "AN remake" so skip first two entries
    msg = message.content.split(" ")[1:]
    # check that the message includes only the scores time left and players
    if len(msg) > 6:
        await sync_channels("I did not understand that. " + util.find_insult(), message)
        return
    elif len(msg) < 4:
        await sync_channels("Did not understand input, expect AN remake score_1 score_2 time_left players_per_team [mode]. " + util.find_insult(), message)
        return
    # auto set mode if not given
    elif len(msg) == 4:
        mode = util.check_mode(0, message.guild.id, channel=message.channel.id)
    else:
        mode = msg[-1]
    score_1, score_2 = int(msg[0]), int(msg[1])
    time = msg[2].split(":")
    time = int(time[0]) * 60 + int(time[1])
    players = int(msg[3][0])

    # functions from rulebook
    def manhunt(t, p):
        """score difference in points"""
        return t ** 1.3 * p * 2.2 + 960

    def escort(t, p):
        """score difference in percentage"""
        return t ** 1.42 * 29e-5 + .067

    # check mode and use correct function
    try:
        if util.check_mode(mode) == "escort":
            s_diff = escort(time, players)
            if abs(score_1 - score_2) / max(score_1, score_2) > s_diff:
                s_diff = round(s_diff)
                await sync_channels(f"No remake is necessary; score difference is above the threshold ({s_diff}).", message)
            else:
                await sync_channels(f"A remake is necessary; score difference is below the threshold ({s_diff}).", message)
        else:
            s_diff = manhunt(time, players)
            if abs(score_1 - score_2) > s_diff:
                s_diff = round(s_diff)
                await sync_channels(f"No remake is necessary; score difference is above the threshold ({s_diff}).", message)
            else:
                await sync_channels(f"A remake is necessary; score difference is below the threshold ({s_diff}).", message)
    except:
        await sync_channels("Did not understand input, expect AN remake score_1 score_2 time_left players_per_team [mode]. " + util.find_insult(), message)
        return

    return


# the OCR function
@util.command_dec
async def ocr_screenshot(message):
    # function to grab params from guild IDs
    def guild_params():
        if message.guild.id in conf.e_servers:
            game = "acb"
            players = 4
        elif message.guild.id in conf.mh_servers:
            game = "acb"
            players = 6
        elif message.guild.id in conf.aa_servers:
            game = "acr"
            players = 8
        elif message.guild.id in conf.do_servers:
            game = "ac4"
            players = 8
        else:
            game = "acb"
            players = 6
        return game, players

    msg = message.content.lower()
    msg = msg.replace("ocr ", "").replace("ocr", "")
    msg = msg.split(" ")

    # check if post game (for AC4)
    if "post" in msg:
        post = True
        msg.remove("post")
        if msg == []:
            msg = [""]
    else:
        post = False

    if "ffa" in message.content:
        ffa = True
        msg.remove("ffa")
        if msg == []:
            msg = ['']
    else:
        ffa = False

    correction = False
    if "+" in message.content:
        correction = msg[-2:]
        msg = msg[:-2]



    # if one of game, players isn't specified use guild_params
    if len(msg) == 2:
        players = msg[1]
        game = msg[0]
    elif msg != [""]:
        try:
            players = int(msg[0])
            game = guild_params()[0]
        except:
            game = msg[0]
            players = guild_params()[1]
    else:
        game, players = guild_params()
    # download the image and save to folder then send the results of the OCR script
    if not ffa:
        mode = 'DO' if game.lower()=='ac4' else 'E'
    else:
        mode = 'DM' if game.lower()=='ac4' else 'ASB'

    if message.attachments:
        results = []
        for attachment in message.attachments:
            img = requests.get(attachment.url)
            fname = f"screenshots/{str(datetime.now())}.png"
            with open(fname, "wb") as f:
                f.write(img.content)
            try:
                result = AC_Score_OCR.OCR(fname, game, players, post, ffa)
            except Exception as e:
                print(e)
                result = "Sorry, something went wrong with your screenshot. We recommend using mpv to take screenshots."
            # delete the image again - discord's cdn should be good enough for us
            os.remove(fname)
            if correction:
                result = AC_Score_OCR.correct_score(result, correction[0], correction[1])
            result = f'{mode}, {int(players/2)}, 1, {result}' if not ffa else f'{mode}, {result}'
            results.append(result)
            await sync_channels(result, message)
        return
    else:
        await sync_channels("Could not find attachment.", message)
        return



@util.command_dec
async def swap_teams(message):
    msg = message.content[5:]
    items = msg.split(", ")
    outcome = int(items[2])
    if outcome == 1:
        outcome = 2
    elif outcome == 2:
        outcome = 1
    t1 = items[3:3 + int(items[1])]
    t2 = items[3 + int(items[1]):]
    out = ", ".join(items[0:2] + [str(outcome)] + t2 + t1)
    await sync_channels(out, message)
    return

# add users to the db
@util.permission_locked
@util.command_dec
async def user_add(message):
    msg = message.content[9:]
    info = msg.split("; ")
    name = info[0]
    ign = info[1].split(", ")
    link = info[2]
    nation = info[3]
    platforms = info[4].split(", ")
    try:
        discord_id = info[5].replace("@!", "").replace(">", "").replace("<", "").replace("@", "")
    except IndexError:
        discord_id = ""
    db = util.connect()
    starting_mmr = 800
    d = date.today().strftime("%y-%m-%d")
    try:
        db.players.insert_one({
            "name":name,
            "ign":ign,
            "link":link,
            "nation":nation,
            "platforms":platforms,
            "badges": [],
            "emmr":starting_mmr,
            "mhmmr":starting_mmr,
            "aarmmr":starting_mmr,
            "aadmmr":starting_mmr,
            "dommr":starting_mmr,
            "dmmmr":starting_mmr,
            "asbmmr":starting_mmr,
            "ehistory":{"dates":[d], "mmrs":[starting_mmr]},
            "mhhistory":{"dates":[d], "mmrs":[starting_mmr]},
            "aarhistory":{"dates":[d], "mmrs":[starting_mmr]},
            "aadhistory":{"dates":[d], "mmrs":[starting_mmr]},
            "dohistory":{"dates":[d], "mmrs":[starting_mmr]},
            "dmhistory":{"dates":[d], "mmrs":[starting_mmr]},
            "asbhistory":{"dates":[d], "mmrs":[starting_mmr]},
            "egames":{"total":int(0), "won":int(0), "lost":int(0)},
            "mhgames":{"total":int(0), "won":int(0), "lost":int(0)},
            "aargames":{"total":int(0), "won":int(0), "lost":int(0)},
            "aadgames":{"total":int(0), "won":int(0), "lost":int(0)},
            "dogames":{"total":int(0), "won":int(0), "lost":int(0)},
            "dmgames":{"total":int(0), "won":int(0), "lost":int(0), "podium":int(0), "finishes":int(0)},
            "asbgames":{"total":int(0), "won":int(0), "lost":int(0), "podium":int(0), "finishes":int(0)},
            "estats":{"totalscore":int(0), "highscore":int(0), "kills":int(0), "deaths":int(0)},
            "mhstats":{"totalscore":int(0), "highscore":int(0), "kills":int(0), "deaths":int(0)},
            "aarstats":{"totalscore":int(0), "kills":int(0), "deaths":int(0), "scored":int(0), "conceded":int(0)},
            "aadstats":{"totalscore":int(0), "kills":int(0), "deaths":int(0), "scored":int(0), "conceded":int(0)},
            "dostats":{"totalscore":int(0), "kills":int(0), "deaths":int(0), "scored":int(0), "conceded":int(0)},
            "dmstats":{"totalscore":int(0), "highscore":int(0), "kills":int(0), "deaths":int(0)},
            "asbstats":{"totalscore":int(0), "highscore":int(0), "kills":int(0), "deaths":int(0)},
            "erank": 0,
            "erankchange": 0,
            "mhrank": 0,
            "mhrankchange": 0,
            "aarrank": 0,
            "aarrankchange": 0,
            "aadrank": 0,
            "aadrankchange": 0,
            "dorankchange": 0,
            "dorank": 0,
            "dmrank": 0,
            "dmrankchange": 0,
            "asbrank": 0,
            "asbrankchange": 0,
            "discord_id": discord_id,
            "hidden": False}
            )
        await sync_channels("Successfully added user.", message)
    except:
        await sync_channels("An error has occured.", message)


@util.permission_locked
@util.command_dec
async def user_edit(message):
    """
    User editing function.
    """
    msg = message.content[10:]
    info = msg.split(": ")
    name = info[0]
    db = util.connect()
    player = util.identify_player(db, name)
    all_keys = player.keys()
    key = info[1]
    if key not in all_keys:
        await sync_channels(f"Improper key specified! Possible keys are: {', '.join(all_keys)}.", message)
        return
    # kinda iffy to do this but there's a reason why it's permission locked
    value = eval(info[2])
    # update names in case that's what's updated
    # I'm pretty sure this should be optimized
    if key == "name":
        search = [{"team1": {"$elemMatch": {"player": name}}}]
        search += [{"team2": {"$elemMatch": {"player": name}}}]
        matches = db.matches.find({"$or": search})
        for m in matches:
            for i in [1, 2]:
                for j in range(len(m[f"team{i}"])):
                    if m[f"team{i}"][j]["player"] == player["name"]:
                        m[f"team{i}"][j]["player"] = value
            db.matches.update_one({"_id": m["_id"]}, {"$set": {"team1": m["team1"], "team2": m["team2"]}})
        # update host in match history as well
        db.matches.update_many({"host": name}, {"$set": {"host": value}})
    db.players.update_one({"_id": player["_id"]}, {"$set": {key: value}})
    await sync_channels(f"Successfully edited {player['name']}.", message)
    return


async def sync_channels(content=None, message=None, channel_id=None, server_id=None, nick=None, attachments=None, embed=None, bot_response=True):

    if message:
        channel_id = message.channel.id
        server_id = message.channel.guild.id
        nick = message.author.name
    if bot_response:
        nick = "Assassins' Network"

    # since we want to replace the role pings with equivalents
    def replace_roles(content, origin_guild_id, dest_guild_id):
        for r in roles.values():
            # don't care to add a safety check
            content = content.replace(str(r.get(origin_guild_id)), str(r.get(dest_guild_id)))
        return content

    sent = False
    roles = conf.sync_roles
    for sync_group in conf.synched_channels:
        if channel_id in sync_group:
            sent = True
            for x in sync_group:
                if x != channel_id or bot_response:
                    channel = client.get_channel(x)
                    if embed:
                        await channel.send(embed=embed)
                    else:
                        # filter the roles
                        content = replace_roles(content, server_id, channel.guild.id)
                        # make sure our user gets a good nick
                        if not bot_response:
                            content = f"**{nick}:** {content}"
                        # grab attachments and attach them, then send
                        if attachments:
                            if len(attachments) > 1:
                                att = []
                                for n in range(len(attachments)):
                                    att += [util.att_to_file(message, n)]
                                await channel.send(content, files=att)
                            else:
                                att = util.att_to_file(message)
                                await channel.send(content, file=att)
                            # delete files after they're sent
                            files = glob.glob("sync/*")
                            for f in files:
                                os.remove(f)
                        else:
                            await channel.send(content)
    if bot_response and not sent:
        channel = client.get_channel(channel_id)
        if embed:
            await channel.send(embed=embed)
            return
        await channel.send(content)
    return


@util.command_dec
async def compare_users(message):
    db = util.connect()
    content = message.content[8:]
    if " mode " in content:
        content, mode = content.split(" mode ")
    else:
        mode = None
    mode = util.check_mode(mode, message.guild.id, short=True, channel=message.channel.id)
    teams_str = content.split(" vs ")
    if len(teams_str) < 2:
        await sync_channels("Missing a second team. " + util.find_insult(), message)
        return
    teams = [[], []]
    for i in range(2):
        players = teams_str[i].split(", ")
        for j in range(len(players)):
            try:
                players[j] = util.identify_player(db, players[j])
            except ValueError:
                try:
                    players[j] = {
                        "name": f'a {util.rank_title(int(players[j]))}',
                        f"{mode}mmr": int(players[j])
                    }
                except ValueError:
                    await sync_channels(f"I've never heard of {players[j]}. {util.find_insult()}", message)
                    return
        teams[i] = players
    chance = elostats.compare_players(teams[0], teams[1], mode, verbose=True)
    chance_p = round(chance[0] * 100, 2)
    teams = [[p["name"] for p in team] for team in teams]
    await sync_channels(f"The chance of {', '.join(teams[0])} ({round(chance[1][0])} MMR) beating {', '.join(teams[1])} ({round(chance[1][1])} MMR) in {modes_dict[mode]} is {chance_p}%.", message)
    return


#@util.command_dec
async def estimate_change(message):
    content = message.content[9:]
    # identify mode
    mode = None
    if " mode " in content:
        temp = content.split(" mode ")
        mode = temp[1]
        content = temp[0]
    mode = util.check_mode(mode, message.guild.id, short=True, channel=message.channel.id)
    # extract players and team comps
    if " vs. " in content:
        ts = content.split(" vs. ")
    elif " vs " in content:
        ts = content.split(" vs ")
    else:
        await sync_channels("team splitting token ' vs ' missing. " + util.find_insult(), message)
        return

    embedVar = discord.Embed(title="Rating Change Estimates", url = "https://assassins.network/elo", color = 0xff00ff)
    ts = [ts[i].split(", ") for i in [0, 1]]
    try:
        ts = [teams.extract_players(t, mode) for t in ts]
    except Exception as e:
        await sync_channels(f"There's an error with your input ({e}). {util.find_insult()}", message)
        return
    team_ratings = [[p[f"{mode}mmr"] for p in ts[i]] for i in [0, 1]]
    if mode in util.FFA_MODES:
        import eloupdate_ffa as ffaelo
        if len(ts[0]) > 1:
            await sync_channels("Only 1 player should be to the left of 'vs'" + util.find_insult(), message)
            return
        player = ts[0][0]
        # calculate shit we need
        total_players = len(ts[1]) + 1
        lobby_ratings = team_ratings[0] + team_ratings[1]
        fake_scores = [1 for _ in lobby_ratings]
        expected = ffaelo.expected_results(lobby_ratings)[0]
        changes = []
        pos_chances = []

        for pos in range(1, total_players+1):
            result = ffaelo.get_result(pos, total_players)
            changes.append(ffaelo.rating_change(
                player[f'{mode}mmr'],
                result, expected, player[f'{mode}games']["total"],
                pos, fake_scores
            ))

            beating = total_players-pos
            beat_by = total_players-1-beating
            placing_chance = (expected**beating)*binom(total_players-1, beating)
            placing_chance *= ((1-expected)**beat_by)*binom((total_players-1)-beating, beat_by)
            pos_chances.append(placing_chance)


        expected_pos = total_players - expected*(total_players-1)
        opp_ratings = np.array(team_ratings[1])
        opposition_rating = (opp_ratings.mean() + np.median(opp_ratings)) / 2

        # display
        player_display =\
            f"""{player['name']} ({round(player[f'{mode}mmr'], 1)})
            Average Expected Finish: **{ffaelo.pos_to_str(round(expected_pos))}** ({round(expected_pos, 2)})"""
        opp_display = "\n".join([f"{o['name']} ({round(o[f'{mode}mmr'], 1)})" for o in ts[1]]) + \
                    f"\n**Estimated opposition strength: {round(opposition_rating, 1)}**"

        embedVar.add_field(name="Player", value=player_display, inline=False)
        embedVar.add_field(name="Opposition", value=opp_display, inline=False)

        results = []
        for pos in range(1, total_players+1):
            change = round(changes[pos-1], 1)
            change = f"+{change}" if change > 0 else change
            chance = round(pos_chances[pos-1] * 100, 1)
            result = f'{ffaelo.pos_to_str(pos)} ({chance}%): {change}'
            if pos <= 3:
                result = f'**{result}**'
            results.append(result)
        embedVar.add_field(name="Possible results", value='\n'.join(results), inline=False)

    # get team elos
    else:
        import eloupdate as elo
        team_ratings = [elo.w_mean(team_ratings[0], team_ratings[1])[0], elo.w_mean(team_ratings[1], team_ratings[0])[0]]
        # get expected outcome
        expect = elo.E(team_ratings)
        expect = [expect, 1 - expect]
        if expect[0] == 0.5:
            expect_outcome = "Tie"
        elif expect[0] > 0.5:
            expect_outcome = f"Team 1 - {round(expect[0] * 100)}%"
        else:
            expect_outcome = f"Team 2 - {round(expect[1] * 100)}%"
        # get rating changes
        changes = {ts[i][j]["name"]: [round(elo.R_change(ts[i][j][f"{mode}mmr"], S, expect[i], ts[i][j][f"{mode}games"]["total"] + 1, 0, 0, 0), 2) for S in [0, 0.5, 1]] for i in [0, 1] for j in range(len(ts[0]))}
        outputs = [[f"{k}: {'+' if changes[k][i] > 0 else ''}{changes[k][i]}" for i in [0, 1, 2]] for k in changes.keys()]
        # strings with names of all players in teams and their ratings
        names = ["\n".join([f'{ts[i][j]["name"]} ({round(ts[i][j][f"{mode}mmr"], 2)} MMR)' for j in range(len(ts[0]))]) for i in [0, 1]]
        # team string with names and team rating
        team_str = [f"{names[i]}\nTeam Rating: **{round(team_ratings[i], 2)}**" for i in [0, 1]]
        embedVar.add_field(name="Team 1", value=team_str[0], inline=False)
        embedVar.add_field(name="Team 2", value=team_str[1], inline=False)
        embedVar.add_field(name="Expected Winner", value=expect_outcome, inline=False)
        team_size = len(ts[0])
        # team 1 perspective
        w = t = l = ""
        for i in range(len(outputs)):
            # a line break between teams
            if i == team_size:
                w += "\n"
                t += "\n"
                l += "\n"
            t += outputs[i][1] + "\n"
            # check whether we're at t1 or t2 w
            if i < team_size:
                w += outputs[i][2] + "\n"
                l += outputs[i][0] + "\n"
            else:
                w += outputs[i][0] + "\n"
                l += outputs[i][2] + "\n"
        embedVar.add_field(name="Team 1 Win", value=w, inline=True)
        embedVar.add_field(name="Tie", value=t, inline=True)
        embedVar.add_field(name="Team 2 Win", value=l, inline=True)
    await sync_channels(embed=embedVar, message=message)
    return



@util.permission_locked
@util.command_dec
async def restore_backup(message):
    path = "/home/dell/Match_Update/dump/"
    dumps = os.listdir(path)
    paths = [os.path.join(path, basename) for basename in dumps]
    newest = max(paths, key=os.path.getctime)
    os.system(f"mongorestore --drop --nsInclude=public.* {newest}/")
    await sync_channels("Restored backup.", message)


@util.permission_locked
@util.command_dec
async def reload_modules(message):
    import importlib
    for module in sys.modules.values():
        try:
            if module.__file__.startswith("/home/dell/Match_Update/"):
                importlib.reload(module)
                print(f"Reloaded module: {module.__name__}")
        except:
            pass
    await sync_channels("Successfully reloaded modules.", message)
    return

@client.event
async def on_member_join(member):
    if member.guild.id == conf.main_server:
        db = util.connect()
        user_id = member.mention.replace("@!", "").replace(">", "").replace("<", "").replace("@", "")
        in_db = db.players.find_one({"discord_id": user_id})
        if in_db:
            new_nick = in_db["name"]
            # ideally I'd like to append badges to names
            # I prefer that over adding igns
            await member.edit(nick=new_nick)
            await member.add_roles(conf.verified_role)
        else:
            print(f"Couldn't identify user {member.id}")
            channel = client.get_channel(conf.main_channel)
            await channel.send(f"Hello {member.mention}, I couldn't find you in the AN database. If you're new here, please reply to this with your prefered name, in-game usernames, platforms, and the nation you'd like to represent, and an admin will verify if you're a member of the competitive AC community and add you to the database if so.")
    return

@util.permission_locked
async def rename_all(message):
    db = util.connect()
    for member in message.guild.members:
        if member.id == message.guild.owner.id:
            continue
        in_db = db.players.find_one({"discord_id": member.mention.replace("@!", "").replace(">", "").replace("<", "").replace("@", "")})
        if in_db:
            print(f"Renaming {in_db['name']}")
            await member.edit(nick=in_db["name"])
        else:
            print(f"Couldn't identify {member.name}")
    return

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.lower().startswith("an "):
#        await sync_channels(message.content, message, bot_response=False)

        message.content = message.content[3:]
        # help message
        if message.content.lower().startswith("help"):
            try:
                await sync_channels(message=message, embed=help_message(message))
            except UnboundLocalError:
                await sync_channels("Could not find the function you're looking for.", message)
        # lookup
        elif message.content.lower().startswith("lookup"):
            await lookup_user(message)

        # ladder
        elif message.content.lower().startswith("ladder"):
            await lookup_ladder(message)

        # synergy
        elif message.content.lower().startswith("synergy"):
            try:
                await lookup_synergy(message)
            except discord.errors.HTTPException as e:
                print(e)
                await sync_channels("An error has occurred, you might not have enough games. " + util.find_insult(), message)

        elif message.content.lower().startswith("mapstat"):
            try:
                await map_synergy(message)
            except discord.errors.HTTPException as e:
                print(e)
                await sync_channels("An error has occurred, you might not have enough games. " + util.find_insult(), message)

        # add games
        elif message.content.lower().startswith("add "):
            add_match(message)
            await sync_channels("Game(s) added!", message)

        # print matches.txt
        elif message.content.lower() == "print":
            await print_matches(message)

        elif message.content.lower().startswith("sanity"):
            await sanity_check_matches(message)

        # edit matches.txt
        elif message.content.lower().startswith("edit "):
            await edit_matches(message)

        # replace matches.txt content
        elif message.content.lower().startswith("replace"):
            await replace_matches(message)

        # update db
        elif message.content.lower().startswith("update"):
            await updater(message)

        elif message.content.lower().startswith("ocr"):
            await ocr_screenshot(message)

        # add missing content
        elif message.content.lower().startswith("missing"):
            await add_missing(message)

        elif message.content.lower().startswith("swap"):
            await swap_teams(message)

        elif message.content.lower().startswith("user add"):
            await user_add(message)

        elif message.content.lower().startswith("user edit"):
            await user_edit(message)

        elif message.content.lower().startswith("compare"):
            await compare_users(message)

        elif message.content.lower().startswith("estimate"):
            await estimate_change(message)

        elif message.content.lower().startswith("restore"):
            await restore_backup(message)

        elif message.content.lower().startswith("reload"):
            await reload_modules(message)

        elif message.content.lower() == "rename all":
            await rename_all(message)

    elif message.content == "Y":
        await sync_channels(f"{message.author.name} has tacoed out.", message)

    else:
        await sync_channels(message.content, message, bot_response=False)
        pass


client.run(conf.discord_id)
