import botconfig as conf
import random
import discord
from discord.utils import get
from discord.ext import commands
from teams import find_teams
from util import *
import re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta, date
from functools import partial
import AC_Score_OCR
import requests
import signal
import sys
from tweet import rank_frame
import glob
import os
import sanity

client = discord.Client()

@client.event
async def on_ready():
    await update_presence()
    print("Starting.")

scheduler = AsyncIOScheduler()
scheduler.start()

modes_list = ['e', 'mh', 'aar', 'aad']
modes_dict = {
        'e' : "Escort",
        'mh' : 'Manhunt',
        'aar' : 'AA Running',
        'aad' : 'AA Defending'
        }

# we save the queues here as simple arrays since we don't expect to scale
# read out the queues from the queues file that saves state for restarts
with open("queues.txt", "r") as f:
    queues = f.read()
    queues = queues.split("; ")
    i = 0
    for q in queues:
        queues[i] = queues[i].split(", ")
        if queues[i] == [""]:
            queues[i] = []
        i += 1
    aa_queue = queues[0]
    dm_queue = queues[1]
    e_queue = queues[2]
    mh_queue = queues[3]
    aa_queue_users = queues[4]
    dm_queue_users = queues[5]
    e_queue_users = queues[6]
    mh_queue_users = queues[7]
    au_queue = queues[8]
    f.close()

abilities = ["Normal Disguise","Long Lasting Disguise", "Strong Disguise",
"Rapid Reload Disguise", "Normal Sprint Boost", "Long Lasting Sprint Boost", "Strong Sprint Boost",
"Rapid Reload Sprint Boost", "Normal Smoke Bomb", "Long Lasting Smoke Bomb", "Strong Smoke Bomb",
"Rapid Reload Smoke Bomb", "Normal Templar Vision", "Long Lasting Templar Vision", "Strong Templar Vision",
"Rapid Reload Templar Vision", "Normal Fire Crackers", "Long Lasting Fire Crackers", "Strong Fire Crackers",
"Rapid Reload Fire Crackers", "Normal Charge", "Long Lasting Charge", "Strong Charge", "Rapid Reload Charge",
"Normal Mute", "Long Lasting Mute", "Strong Mute", "Rapid Reload Mute", "Normal Hidden Gun",
"Deadly Hidden Gun","Quick Fire Hidden Gun", "Rapid Reload Hidden Gun", "Normal Throwing Knives",
"Long Lasting Throwing Knives", "Sharp Throwing Knives",
"Rapid Reload Throwing Knives","Normal Poison", "Fast Acting Poison", "Slow Acting Poison", "Rapid Reload Poison", "Normal Morph",
"Power Morph", "Strong Morph", "Rapid Reload Morph", "Normal Decoy", "Long Lasting Decoy", "Disguised Decoy", "Rapid Reload Decoy"]

Perks = ["Enhanced Autobash", "Wall Runner", "Resistance", "Blender", "Fast Getaway", "Chase Expert", "Overall Cooldowns"]

Kill_Streak = ["+100", "+300", "+250", "+750"]
Loss_Streak = ["Extra Precision", "Reset Cooldowns", "Score X2", "Boost Cooldowns"]

#Command which generates random ability sets for a set number of players
async def ability_randomizer(message):
    aset = ", ".join(random.sample(abilities, k=2))
    aset += "\n" + ", ".join(random.sample(Perks, k=2))
    aset += "\n" + random.choice(Kill_Streak)
    await message.channel.send(aset + "\n" + random.choice(Loss_Streak))
    return


# some fun ACB insults to use as error messages
insults = ["You suck.", "ur mam gay", "Even fouadix speaks English better than you.",
        "I bet you'd choose sex over escort.", "Go back to wanted.", "You played on Xbox, didn't you?",
        "I'd choose Fazz over you.", "Even Fazz kills less civis than you.", "Dell runs less than you.",
        "Are you from AC4?", "Speed gets fewer deaths than you.", "tdas gay", "ultro is trans", "What the fuck is that?",
        "Let's not do that again.", "I just want to punch myself in the fucking face.", "Really fucking hilarious.",
        "Dude, I'ma slaughter your entire family if you ever do that again.", "Oh man, I hate you.", "u r getting scummy"]

def find_insult():
    return random.choice(insults)


async def send_long_message(content, channel):
    """
    discord has a 2k char limit which we often hit with eg matches
    embed has a limit of 4096 so that's not a great way to bypass this is a lot easier
    """
    line_split = content.split("\n")
    line = ""
    for i in line_split:
        newline = line + line_split[i]
        if len(newline) > 2000:
            await channel.send(line)
        line = line_split[i]
    return


# change bot presence function
# it just appends queues if there's someone in one
# otherwise it shows Wanted 6/9
async def update_presence():
    presence = 0
    if len(e_queue):
        presence = f"E: {len(e_queue)}/4"
    if len(mh_queue):
        tmp = f"MH: {len(mh_queue)}/6"
        if presence:
            presence += f", {tmp}"
        else:
            presence = tmp
    if len(aa_queue_users):
        tmp = f"AA: {len(aa_queue_users)}/8"
        if presence:
            presence += f", {tmp}"
        else:
            presence = tmp
    if len(dm_queue):
        tmp = f"DM: {len(dm_queue)}/6"
        if presence:
            presence += f", {tmp}"
        else:
            presence = tmp

    if not presence:
        presence = "Wanted 6/9"
    await client.change_presence(activity=discord.Game(name=presence + " | AN help"))
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
AN team comps [PLAYER_0, PLAYER_2, PLAYER_3...] [mode MODE] [random FACTOR]```""" + "\nNot specifying players uses the queue from the specified mode.\nPlayer names must be Assassins' Network names."
    lfg_help = """\nTo queue up for a game, type\n```css
AN play [PLAYER] [mode MODE] [in START_TIME] [for LENGTH_TIME]```\nIf PLAYER is unspecified, the bot attempts to match your Discord account to a player. Otherwise, these must be AN usernames.\nTimes must be given in hours. Default `LENGTH_TIME` is 3 hours, default mode is defined by the server the command is sent in.\nNote that you can only queue up for one mode at a time."""
    lookup_help = """To look up a user's stats on an, type\n```css
AN lookup [PLAYER]```"""
    queue_rm_help = """To remove yourself from the queue you are currently in, use\n```css
AN queue remove```"""
    queue_help = """To print the players currently queued up for a mode, use\n```css
AN queue [MODE]```"""
    remake_help = """To calculate whether a game should be remade after a disconnect, use\n```css
AN remake TEAM_1_SCORE TEAM_2_SCORE TIME_LEFT PLAYERS_PER_TEAM [MODE]```Whereby time is in-game time formatted as X:YZ."""
    ocr_help = """To use optical character recognition to scan screenshots into the AN matches format, use the following with the screenshot attached\n```css
AN OCR [GAME] [TOTAL_PLAYERS]```This currently only supports ACB and ACR AA.\nScreenshots must be uncropped pictures taken from your PC or similar, i.e. phone pictures won't work."""
    add_help = """To queue matches for being added to AN, use\n```css
AN add [FORMATTED_MATCH]```with the match data formatted in the AN format pinned in #an-help on the #secualhealing server, e.g.:\n```css
M, 3, 1, DevelSpirit$7760$8$6, x-JigZaw$6960$6$7, EsquimoJo$4400$5$6, Tha Fazz$6325$6$6, dripdriply$5935$6$6, Dellpit$5515$7$7```"""
    edit_help = """To edit ALL the matches to be added to the database, use\n```css
AN edit [UPDATED_MATCHES]```Please note that you should first print all matches with ```css
AN print``` and edit those results, then feed ALL the matches to this in one single command. Otherwise, all unmentioned matches will be removed."""
    replace_help = """To replace certain content in the matches to be queued to the database, use\n```css
AN replace [ORIGINAL] with [REPLACEMENT]```"""
    print_help = """To print the matches currently queued to be added to the database, use\n```css
AN print```"""
    update_help = """If you have the Assassins' Network role, you can update the matches in the database using\n```css
AN update```Note that improperly formatted matches won't be added. If this occurs, please contact Dell."""
    user_add_help = """If you have the Assassins' Network role, you can add users to the database using\n```css
AN user add NAME; IGN[1, IGN2, ...]; LINK; COUNTRY; PLATFORM[1, PLATFORM2, ...]; @USER```"""
    sanity_help = """To run the sanity checker over the currently added matches, run\n```css
AN sanity```"""

    # if the user asked for help on a specific function the msg isn't empty after parsing
    # so we find out what it is and return an embed with the long description from above
    if msg != "":
        if msg == "team comps":
            return discord.Embed(title=":elevator: Team Generator", description=team_help, color=0xff00fe)
        elif msg == "play":
            return discord.Embed(title=":vibration_mode: Add to Queue", description=lfg_help, color=0xff00fe)
        elif msg == "queue remove":
            return discord.Embed(title=":no_mobile_phones: Remove from Queue", description=queue_rm_help, color=0xff00fe)
        elif msg == "queue":
            return discord.Embed(title=":printer: Print Queue", description=queue_help, color=0xff00fe)
        elif msg == "lookup":
            return discord.Embed(title=":mag: User Lookup", description=lookup_help, color=0xff00fe)
        elif msg == "remake":
            return discord.Embed(title=":judge: Remake Calculator", description=remake_help, color=0xff00fe)
    # otherwise we do one giant embed and keep adding fields with functions
    else:
         embedVar = discord.Embed(title="Assassins' Network Help", url = "https://assassins.network/", color = 0xffa8e8)
         embedVar.set_thumbnail(url="https://assassins.network/static/an_logo_white.png")
         embedVar.add_field(name=":vibration_mode: Add to Queue", value="AN play", inline=True)
         embedVar.add_field(name=":no_mobile_phones: Remove from Queue", value="AN queue remove", inline=True)
         embedVar.add_field(name=":printer: Print Queue", value="AN queue", inline=True)
         embedVar.add_field(name=":elevator: Team Generator", value="AN team comps", inline=True)
         embedVar.add_field(name=":mag: User Lookup", value="AN lookup", inline=True)
         embedVar.add_field(name=":judge: Remake Calculator", value="AN remake", inline=True)
         embedVar.set_footer(text="For more information, use AN help [COMMAND].")

    # if the channel name fits we add the AN db/parsing functions
    if message.channel.name in ["an-help", "assassinsnetwork"] and message.guild.id == conf.main_server or message.author.id in conf.admin:
        if msg != "":
            if msg == "ocr":
                return discord.Embed(title=":camera: Scan Screenshot", description=ocr_help, color=0xff00fe)
            elif msg == "add":
                return discord.Embed(title=":memo: Add Matches", description=add_help, color=0xff00fe)
            elif msg == "edit":
                return discord.Embed(title=":pencil2: Edit Matches", description=edit_help, color=0xff00fe)
            elif msg == "replace":
                return discord.Embed(title=":crayon: Replace Match Content", description=replace_help, color=0xff00fe)
            elif msg == "print":
                return discord.Embed(title=":printer: Print Matches", description=print_help, color=0xff00fe)
            elif msg == "sanity":
                return discord.Embed(title=":confused: Sanity Check", description=sanity_help, color=0xff00fe)
            elif msg == "update":
                return discord.Embed(title=":pager: Update Matches", description=update_help, color=0xff00fe)
            elif msg == "user add":
                return discord.Embed(title=":chess_pawn: Add Users", description=user_add_help, color=0xff00fe)
        else:
            embedVar.add_field(name=":camera: Scan Screenshot", value="AN OCR", inline=True)
            embedVar.add_field(name=":memo: Add Matches", value="AN add", inline=True)
            embedVar.add_field(name=":printer: Print Matches", value="AN print", inline=True)
            embedVar.add_field(name=":confused: Sanity Check", value="AN sanity", inline=True)
            embedVar.add_field(name=":pencil2: Edit Matches", value="AN edit", inline=True)
            embedVar.add_field(name=":crayon: Replace Match Content", value="AN replace", inline=True)
            embedVar.add_field(name=":pager: Update Matches", value="AN update", inline=True)
            embedVar.add_field(name=":chess_pawn: Add Users", value="AN user add", inline=True)
        # note sure what these were for honestly
#        match_help="""To add a match, use\n```css
#an add```\n followed by a match in the an format, for example:```M, 2, 1, DevelSpirit$7760$8$6, x-JigZaw$6960$6$7, EsquimoJo$4400$5$6, Tha Fazz$6325$6$6, dripdriply$5935$6$6, Dellpit$5515$7$7```"""
#        if get(message.author.roles, name="Assassins' Network"):
#            match_help += """\nTo update the leaderboards, use```css
#AN update```"""
       # embedVar.add_field(name="Match Management", value=match_help, inline = False)
    
    return embedVar


def rank_pic_big(elo):
    """
    grabs rank pics, copied from an_flask
    """
    if elo < 801:
        return "badge_1_big.png"
    if elo < 1000:
        return "badge_2_big.png"
    if elo < 1200:
        return "badge_3_big.png"
    if elo < 1400:
        return "badge_4_big.png"
    return "badge_5_big.png"


# command to look up a user on the AN db
# connect to DB -> look up user -> print user
def lookup_user(message):
    player = message.content.replace("lookup ", "")
    player = player.replace("  ", " ")
    db = connect()
    if player == "lookup":
        player_db = db.players.find_one({"discord_id" : str(message.author.id)})
        player = player_db["name"]
    elif "@" in player:
        discord_id = player.replace("@!", "").replace(">", "").replace("<", "")
        player_db = db.players.find_one({"discord_id" : discord_id})
        player = player_db["name"]
    else:
        player_db = identify_player(db, player)
    if player_db is None:
        embedVar = discord.Embed(title="Congratulations, you're an Xbox player!", url="https://assassins.network/players", color=0xff00ff)
        embedVar.add_field(name=find_insult(), value="Did not recognize username.\nPlease check that it's the same as on https://assassins.network/players.")
    else:
        # embed title is player name and their country flag as an emoji
        import flag
        embedVar = discord.Embed(title=f"{player} {flag.flag(player_db['nation'])}", url=f"https://assassins.network/profile/{player.replace(' ', '%20')}", color=0xff00ff)
        # only add information that is present
        embedVar.add_field(name="In-Game Names", value=", ".join(player_db["ign"]), inline=False)
        top_elo = 0
        for mode in modes_list:
            if player_db[f"{mode}games"]["total"] > 0:
                top_elo = max(top_elo, player_db[f'{mode}mmr'])
                user_stats = f"MMR (Rank): {player_db[f'{mode}mmr']} ({player_db[f'{mode}rank']})\n \
                               Peak MMR: {max(player_db[f'{mode}history']['mmrs'])}\n \
                               Winrate: {round(player_db[f'{mode}games']['won'] / (player_db[f'{mode}games']['lost'] + player_db[f'{mode}games']['won']) * 100)}% \n \
                               Games Played: {player_db[f'{mode}games']['total']}\n"

                if 'aa' not in mode:
                    embedVar.add_field(name=modes_dict[mode], value=user_stats +
                    f"K/D Ratio: {round(player_db[f'{mode}stats']['kills'] / player_db[f'{mode}stats']['deaths'], 2)} \n \
                     Avg Kills / Deaths: {round(player_db[f'{mode}stats']['kills'] / player_db[f'{mode}games']['total'], 2)} / {round(player_db[f'{mode}stats']['deaths'] / player_db[f'{mode}games']['total'], 2)}\n \
                     Highscore: {player_db[f'{mode}stats']['highscore']}", inline=False)
                else:
                    if mode == 'aar':
                        embedVar.add_field(name=modes_dict[mode], value=user_stats +
                                f"Avg Scores: {round(player_db[f'{mode}stats']['scored'] / player_db[f'{mode}games']['total'], 2)} \n \
                                 Avg Deaths / Score: {round(player_db[f'{mode}stats']['deaths'] / player_db[f'{mode}stats']['scored'], 2)} \n \
                                 Rat Index: {round(player_db[f'{mode}stats']['kills'] / player_db[f'{mode}games']['total'], 3)}",
                                 inline=False)
                    else:
                        embedVar.add_field(name=modes_dict[mode], value=user_stats +
                                f"Avg Kills: {round(player_db[f'{mode}stats']['kills'] / player_db[f'{mode}games']['total'], 2)} \n \
                                 Avg Concedes: {round(player_db[f'{mode}stats']['conceded'] / player_db[f'{mode}games']['total'], 2)}",
                                 inline=False)
        embedVar.set_image(url="https://assassins.network/static/badges/" + rank_pic_big(top_elo))
    return embedVar

# WIP
def lookup_ladder(message):
    mode = message.content.replace("ladder", "").split(" ")[-1]
    mode = check_mode(mode, server=message.guild.id, short=True)
    rank_frame(mode, "table.png")
    table = discord.File("table.png", filename="table.png")
    embedVar = discord.Embed(title=check_mode(mode).title() + " Leaderboard",
            url=f"https://assassins.network/{mode}", color=0xff00ff)
    embedVar.set_image(url="attachment://table.png")
    return embedVar, table


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
async def print_matches(message):
    with open("matches.txt", "r") as f:
        content = f.read()
        send_long_message(content, message.channel)
#        try:
#            await message.channel.send(content)
#        except:
#            embedVar = discord.Embed(title="Matches", color=0xff00ff, description=content)
#            await message.channel.send(embed=embedVar)
        f.close()
    return


async def sanity_check_matches(message):
    """
    sanity check matches for errors
    """
    await message.channel.send(sanity.main())


# edit matches.txt file
# this overwrites the whole thing
async def edit_matches(message):
    if get(message.author.roles, name="Assassins' Network") or message.author.id in conf.admin:
        msg = message.content.replace("edit ", "").replace("edit ", "")
        with open("matches.txt", "w") as f:
            f.write(msg)
            f.close()
        await message.channel.send("Game(s) edited!")
        return
    else:
        await message.channel.send("You do not have access to this command, please contact a System Administrator. " + find_insult())
        return


# edit matches.txt file by replacing content from the file
async def replace_matches(message):
    if get(message.author.roles, name="Assassins' Network") or message.author.id in conf.admin:
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
        await message.channel.send(f"Replaced every instance of {msg[0]} with {msg[1]}!")
        return
    else:
        await message.channel.send("You do not have access to this command, please contact a System Administrator. " + find_insult())
        return


# team comp finder
# teams.py is the really relevant stuff
def team_finder(players, mode, random):
    # this outputs all the players in one array so we need to split it
    teams = find_teams(players, mode=mode, random=random)
    t1, t2 = [], []
    for i in [0, 1]:
        for player in teams[i]:
            if i == 0:
                t1.append(player["name"])
            elif i == 1:
                t2.append(player["name"])
    return f"{', '.join(t1)} vs. {', '.join(t2)}"


class OutcomeError(Exception):
    pass

# update the AN db by running the read_and_update script
async def updater(message):
    if get(message.author.roles, name="Assassins' Network") or message.author.id in conf.admin:
        try:
            import read_and_update as rau
            rau.main()
            #rau.read_and_update()
            #rau.eloupdate.new_matches()
            #rau.historyupdate.update()
            await message.channel.send("Successfully updated the leaderboards!")
        except OutcomeError as e:
            await message.channel.send("Error! " + e)
        except:
            await message.channel.send("An error has occurred, please message an administrator.")
    else:
        await message.channel.send("You do not have access to this command, please contact a System Administrator. " + find_insult())
    return


# team comps generator
async def team_comps(message, ident):
    # message parsing
    channel = message.channel
    msg = message.content.replace(ident, "")
    msg = message.content.replace(ident + " ", "")
    msg = message.content.replace("team comps ", "")
    msg = msg.replace("  ", " ")
    players = msg.split(', ')
    # grab randomness factor and mode
    if " random " in players[-1]:
        r_factor = re.findall(".* random (.*)", players[-1])
        players[-1] = players[-1].replace(" random " + str(r_factor[0]), "")
        r_factor = int(r_factor[0])
    else:
        r_factor = 25
    if " mode " in players[-1]:
        mode = re.findall(".* mode (.*)", players[-1])
        players[-1] = players[-1].replace(" mode " + mode[0], "")
        mode = str(mode[0])
        mode = check_mode(mode)
    else:
        mode = check_mode(0, message.guild.id)

    # if players were specified we can just run the team_finder func and send that
    if len(players) > 1:
        try:
            matchup = team_finder(players, mode, r_factor)
            await channel.send(matchup)
        except:
            await channel.send("I couldn't identify all players named. " + find_insult())
    # otherwise we try to grab the mode's queue and use that
    else:
        try:
            if mode == "escort":
                queue = e_queue
            elif mode == "artifact assault":
                # AA currently works differently so we just randomly shuffle the queue and return that with role assignments
                queue = aa_queue
                random.shuffle(queue)
                queue = f"Team 1:\nDefenders: {', '.join(queue[0:2])}\nRunners: {', '.join(queue[2:4])}\nTeam 2:\nDefenders: {', '.join(queue[4:6])}\nRunners: {', '.join(queue[6:8])}"
                await channel.send(queue)
                return
            elif mode == "deathmatch":
                queue = dm_queue
            else:
                mode = "manhunt"
            matchup = team_finder(queue, mode, r_factor)
            await channel.send(matchup)
        except:
            await channel.send("That didn't work, idiot. " + find_insult())
    return


# queue removal command
# super straightforward
async def queue_rm(mode, user, player, channel):
    if mode == "escort" or mode == "e":
        e_queue.remove(player)
        e_queue_users.remove(user.mention)
        await channel.send(f"Removed {user.name} from the queue. Escort: {len(e_queue)}/4")
        await update_presence()
    elif mode == "among us":
        au_queue.remove(user.mention)
        await channel.send(f"Removed {user.name} from the queue. Among Us: {len(au_queue)}/4")
    elif mode == "deathmatch":
        dm_queue.remove(player)
        dm_queue_users.remove(user.mention)
        await channel.send(f"Removed {user.name} from the queue. Deathmatch: {len(dm_queue)}/6")
        await update_presence()
    elif mode == "artifact assault":
        aa_queue.remove(player)
        aa_queue_users.remove(user.mention)
        await channel.send(f"Removed {user.name} from the queue. Artifact Assault: {len(aa_queue_users)}/8")
        await update_presence()
    else:
        mh_queue.remove(player)
        mh_queue_users.remove(user.mention)
        await channel.send(f"Removed {user.name} from the queue. Manhunt: {len(mh_queue)}/6")
        await update_presence()
    return


# add player to play queue command
# this is the most poorly written function in here honestly
async def play_command(msg, user, channel, gid):
    # parse the message for times
    # only support hours for simplicity's sake
    if " for " in msg:
        length = re.findall(".* for (.*)", msg)[0]
        msg = msg.replace(" for " + length, "")
        if " h" in length:
            length = length.replace(" h", "")
        elif "h" in length:
            length = length.replace("h", "")
        try:
            length = float(length)
        except:
            await channel.send("Did not recognize given playtime length.")
            return
    else:
        length = 3 # hours
    if " in " in msg:
        start = re.findall(".* in (.*)", msg)[0]
        msg = msg.replace(" in " + start, "")
        if " h" in start:
            start = start.replace(" h", "")
        elif "h" in start:
            start = start.replace("h", "")
        try:
            start = float(start)
        except:
            await channel.send("Did not recognize given starting playtime.")
            return
    else:
        start = 0 # now
    # determine mode
    if " mode " in msg:
        mode = re.findall(".* mode (.*)", msg)[0]
        msg = msg.replace(" mode " + mode, "")
        mode = check_mode(mode)
    # if mode is empty use guild ID to auto determine mode
    else:
        mode = check_mode(0, gid)
    
    # now that the rest of the message has been parsed only the player name should be left
    player = msg
    
    # remove leading and trailing spaces in player names
    if player:
        if player[-1] == " ":
            player = player[:-1]
        elif player[0] == " ":
            player = player[1:]
    
    # since among us and aa don't have players in the AN db we can't use standard queues
    # instead for AA we use player = nickname and for AU we only use one queue
    if mode not in ["among us", "artifact assault"]:
        # this is where we try to find the player according to their Discord ID if no player is specified
        # otherwise we try to match the given player to an AN user
        db = connect()

        if not player:
            player_db = db.players.find_one({"discord_id" : str(user.id)})
            if not player_db:
                await channel.send("I don't know you. " + find_insult())
                return
            player = player_db["name"]
        else:
            player_db = identify_player(db, player)
            if player_db is None:
                await channel.send("Did not recognize username. Please check that it's the same as on https://assassins.network/players. " + find_insult())
                return

    if mode == "artifact assault":
        player = user.name

    # make it impossible to add the same user twice
    # could maybe allow being in two modes
    if player in [*e_queue, *mh_queue, *dm_queue]:
        await channel.send(f"{player} is already in a queue.")
        return
    else:
        if user in au_queue:
            await channel.send(f"{user.name} is already in the Among Us queue.")
            return

    # the part where people are added to the queue
    # most of this is copy-pasted with minor adjustments like queue names and team sizes
    async def queue():
        if mode == "escort":
            e_queue.append(player)
            e_queue_users.append(user.mention)
            await update_presence()
            if len(e_queue) == 4:
                matchup = team_finder(e_queue, mode="escort", random=0)
                await channel.send(", ".join(e_queue_users) + ": Escort 4/4, get on!\nMy suggested teams: " + matchup)
            elif len(e_queue) < 4:
                await channel.send(f"Added {player} to the queue for {length} hour(s). Escort: {len(e_queue)}/4")
            else:
                await channel.send("We're already enough for escort.")
        # AA is an exception in that we don't have users in the DB currently so we have to do the aforementioned BS to get around it
        # additionally in AA we want to assign users random roles
        elif mode == "artifact assault":
            aa_queue.append(player)
            aa_queue_users.append(user.mention)
            await update_presence()
            if len(aa_queue) == 8:
                # temp until AA is added to team_finder
#                matchup = team_finder(aa_queue, mode="artifact assault", random=0)
                matchup = aa_queue
                random.shuffle(matchup)
                matchup = f"\nTeam 1:\nDefenders: {', '.join(matchup[0:2])}\nRunners: {', '.join(matchup[2:4])}\nTeam 2:\nDefenders: {', '.join(matchup[4:6])}\nRunners: {', '.join(matchup[6:8])}"
                await channel.send(", ".join(aa_queue_users) + ": Artifact Assault 8/8, get on!\nMy suggested teams: " + matchup)
#                await channel.send(", ".join(aa_queue_users) + ": Artifact Assault 8/8, get on!")
            elif len(aa_queue) < 8:
                # this is user.nick not play because of the AA queue
                await channel.send(f"Added {player} to the queue for {length} hour(s). Artifact Assault: {len(aa_queue)}/8")
            else:
                await channel.send("We're already enough for artifact assault.")
        elif mode == "deathmatch":
            dm_queue.append(player)
            dm_queue_users.append(user.mention)
            await update_presence()
            if len(dm_queue) == 6:
                await channel.send(", ".join(dm_queue_users) + ": Deathmatch 6/6, get on!")
            elif len(dm_queue) < 6:
                await channel.send(f"Added {player} to the queue for {length} hour(s). Deathmatch: {len(dm_queue)}/6")
            else:
                await channel.send("We're already enough for deathmatch.")
        elif mode == "among us":
            au_queue.append(user.mention)
            if len(au_queue) == 4:
                await channel.send(", ".join(au_queue) + ": Among Us 4/4, get on!")
            elif len(au_queue) < 4:
                await channel.send(f"Added {user.name} to the queue for {length} hour(s). Among Us: {len(au_queue)}/4")
            else:
                await channel.send(f"Among Us already started, currently {len(au_queue)}/10.")
        else:
            mh_queue.append(player)
            mh_queue_users.append(user.mention)
            await update_presence()
            if len(mh_queue) == 6:
                matchup = team_finder(mh_queue, mode="manhunt", random=0)
                await channel.send(", ".join(mh_queue_users) + ": Manhunt 6/6, get on!\nMy suggested teams: " + matchup)
            elif len(mh_queue) < 6:
                await channel.send(f"Added {player} to the queue for {length} hour(s). Manhunt: {len(mh_queue)}/6")
            else:
                await channel.send("We're already enough for manhunt. :cry:")
        return

    # if a start time was specified we add a job to the scheduler
    # the 1s timedelta is in case the script lags for a second
    if start > 0:
        try:
            end_time_add = datetime.isoformat(datetime.now() + timedelta(seconds = 1, hours = start))
            # the if is there for among us bc no player is grabbed from AN
            scheduler.add_job(queue, 'interval', hours=start, end_date=end_time_add, id=(player if player else user.name) + "_start")
            await channel.send(f"Will add {player} to the queue in {start} hour(s).")
        except:
            await channel.send(f"Did not recognize given start time or user already in queue.")
            return
    else:
        await queue()

    # this adds queue removal
    end_time_rm = datetime.isoformat(datetime.now() + timedelta(hours=start + length, seconds = 1))
    scheduler.add_job(partial(queue_rm, mode=mode, user=user, player=player, channel=channel), 'interval', hours=length + start, end_date=end_time_rm, id=(player if player else user.name) + "_remove")
    return

# queue removal command
async def queue_rm_command(msg, user, channel): 
    # remove trailing and leading spaces
    if msg:
        if msg[-1] == " ":
            msg = msg[:-1]
        elif msg[0] == " ":
            msg = msg[1:]

    # AU queue is very simple
    if user.mention in au_queue:
        au_queue.remove(user.mention)
        await channel.send(f"Removed {user.name} from the Among Us queue.")
        return
    # in other cases we have to grab players from the DB again
    else:
        db = connect()

        if not msg:
            player_db = db.players.find_one({"discord_id" : str(user.id)})
            if not player_db:
                await channel.send("I don't know you. " + find_insult())
                return
        else:
            player_db = identify_player(db, msg)
            if player_db is None:
                await channel.send("Did not recognize username. Please check that it's the same as on https://assassins.network/players. " + find_insult())
                return

        player = player_db["name"]

        try:
            scheduler.remove_job(player + "_start")
            await channel.send(f"Successfully removed {player} from the queue.")
        except:
            # no else ifs because we want to remove from every queue at once
            if user.mention in e_queue_users:
                await queue_rm("escort", user, player, channel)
            if user.mention in mh_queue_users:
                await queue_rm("manhunt", user, player, channel)
            if user.mention in dm_queue_users:
                await queue_rm("deathmatch", user, player, channel)
            if user.mention in aa_queue_users:
                # for AA we have to feed it user.nick instead of player currently
                await queue_rm("artifact assault", user, user.name, channel)
            return

        # end queue job removal
        try:
            scheduler.remove_job(player + "_remove")
        except:
            pass
    return


# command to print the whole queue for a mode
# very simple
async def print_queue(message):
    msg = message.content.lower()
    msg = msg.replace("queue ", "")
    msg = msg.replace("queue", "")
    mode = check_mode(msg, message.guild.id)
    if mode == "escort":
        await message.channel.send(f"Escort {len(e_queue)}/4: {', '.join([p for p in e_queue])}")
    elif mode == "manhunt":
        await message.channel.send(f"Manhunt {len(mh_queue)}/6: {', '.join([p for p in mh_queue])}")
    elif mode == "artifact assault":
        await message.channel.send(f"Artifact Assault {len(aa_queue)}/8: {', '.join([p for p in aa_queue])}")
    elif mode == "deathmatch":
        await message.channel.send(f"Deathmatch {len(dm_queue)}/8: {', '.join([p for p in dm_queue])}")
    elif mode == "among us":
        await message.channel.send(f"Among Us {len(au_queue)}/8: {', '.join([p for p in au_queue])}")
    else:
        await message.channel.send("Could not identify mode. " + find_insult())
    return


# command to calculate whether a remake is necessary according to https://rulebook.assassins.network
async def check_remake(message):
    """
    Check whether a remake is necessary according to rulebook.
    Assassinate not implemented currently.
    """
    # function called by "AN remake" so skip first two entries
    msg = message.content.split(" ")[1:]
    # check that the message includes only the scores time left and players
    if len(msg) > 6:
        await message.channel.send("I did not understand that. " + find_insult())
        return
    elif len(msg) < 4:
        await message.channel.send("Did not understand input, expect AN remake score_1 score_2 time_left players_per_team [mode]. " + find_insult())
        return
    # auto set mode if not given
    elif len(msg) == 4:
        mode = check_mode(0, message.guild.id)
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
        if check_mode(mode) == "escort":
            s_diff = escort(time, players)
            if abs(score_1 - score_2) / max(score_1, score_2) > s_diff:
                s_diff = round(s_diff)
                await message.channel.send(f"No remake is necessary; score difference is above the threshold ({s_diff}).")
            else:
                await message.channel.send(f"A remake is necessary; score difference is below the threshold ({s_diff}).")
        else:
            s_diff = manhunt(time, players)
            if abs(score_1 - score_2) > s_diff:
                s_diff = round(s_diff)
                await message.channel.send(f"No remake is necessary; score difference is above the threshold ({s_diff}).")
            else:
                await message.channel.send(f"A remake is necessary; score difference is below the threshold ({s_diff}).")
    except:
        await message.channel.send("Did not understand input, expect AN remake score_1 score_2 time_left players_per_team [mode]. " + find_insult())
        return

    return


# the OCR function
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
        elif message.guild.id in conf.dm_servers:
            game = "ac4"
            players = 8
        else:
            game = "acb"
            players = 6
        return game, players

    msg = message.content.lower()
    msg = msg.replace("ocr ", "").replace("ocr", "")
    msg = msg.split(" ")
    
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
    print(game, players)
    # download the image and save to folder then send the results of the OCR script
    if message.attachments:
        img = requests.get(message.attachments[0].url)
        fname = f"screenshots/{str(datetime.now())}.png"
        with open(fname, "wb") as f:
            f.write(img.content)
        try:
            result = AC_Score_OCR.OCR(fname, game, players)
        except:
            result = "Sorry, something went wrong with your screenshot. We recommend using mpv to take screenshots."
        await message.channel.send(result)
        return
    else:
        await message.channel.send("Could not find attachment.")
        return

# add users to the db
async def user_add(message):
    if (get(message.author.roles, name="Assassins' Network") and message.channel.guild.id == conf.main_server) or message.author.id in conf.admin:
        msg = message.content[9:]
        info = msg.split("; ")
        name = info[0]
        ign = info[1].split(", ")
        link = info[2]
        nation = info[3]
        platforms = info[4].split(", ")
        try:
            discord_id = info[5].replace("@!", "").replace(">", "").replace("<", "")
        except IndexError:
            discord_id = ""
        db = connect()
        starting_mmr = 800
        d = date.today().strftime("%y-%m-%d")
        try:
            db.players.insert_one({
                "name":name,
                "ign":ign,
                "link":link,
                "nation":nation,
                "platforms":platforms,
                "emmr":starting_mmr,
                "mhmmr":starting_mmr,
                "aarmmr":starting_mmr,
                "aadmmr":starting_mmr,
                "ehistory":{"dates":[d], "mmrs":[starting_mmr]},
                "mhhistory":{"dates":[d], "mmrs":[starting_mmr]},
                "aarhistory":{"dates":[d], "mmrs":[starting_mmr]},
                "aadhistory":{"dates":[d], "mmrs":[starting_mmr]},
                "egames":{"total":int(0), "won":int(0), "lost":int(0)},
                "mhgames":{"total":int(0), "won":int(0), "lost":int(0)},
                "aargames":{"total":int(0), "won":int(0), "lost":int(0)},
                "aadgames":{"total":int(0), "won":int(0), "lost":int(0)},
                "estats":{"totalscore":int(0), "highscore":int(0), "kills":int(0), "deaths":int(0)},
                "mhstats":{"totalscore":int(0), "highscore":int(0), "kills":int(0), "deaths":int(0)},
                "aarstats":{"totalscore":int(0), "kills":int(0), "deaths":int(0), "scored":int(0), "conceded":int(0)},
                "aadstats":{"totalscore":int(0), "kills":int(0), "deaths":int(0), "scored":int(0), "conceded":int(0)},
                "erank": 0,
                "erankchange": 0,
                "mhrank": 0,
                "mhrankchange": 0,
                "aarrank": 0,
                "aarrankchange": 0,
                "aadrank": 0,
                "aadrankchange": 0,
                "discord_id":discord_id}
                )
            await message.channel.send("Successfully added user.")
        except:
            await message.channel.send("An error has occured.")
    else:
        await message.channel.send("You do not have the required permissions")


async def sync_channels(message):

    # since we want to replace the role pings with equivalents
    def replace_roles(content, roles, replacement_role):
        for r in roles:
            # don't care to add a safety check
            content = content.replace(str(r), str(replacement_role))
        return content

    roles = conf.sync_roles

    for x in conf.synched_channels:
        if x != message.channel.id:
            content = message.content
            channel = client.get_channel(x)
            # filter the roles
            content = replace_roles(content, roles[message.channel.guild.id], roles[channel.guild.id][0])
            # make sure our user gets a good nick
            nick = message.author.nick
            if nick is None:
                nick = message.author.name
            content = f"**{nick}:** {content}"
            attachments = message.attachments
            # grab attachments and attach them, then send
            if attachments:
                if len(attachments) > 1:
                    att = []
                    for n in range(len(attachments)):
                        att += [att_to_file(message, n)]
                    await channel.send(content, files=att)
                else:
                    att = att_to_file(message)
                    await channel.send(content, file=att)
                # delete files after they're sent
                files = glob.glob("sync/*")
                for f in files:
                    os.remove(f)
            else:
                await channel.send(content)
    return 
 
                                   
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    elif message.content.lower().startswith("an "):
        message.content = message.content[3:]
        # help message
        if message.content.lower().startswith("help"):
            try:
                await message.channel.send(embed=help_message(message))
            except UnboundLocalError:
                await message.channel.send("Could not find the function you're looking for.")
            return
     
        # lookup
        if message.content.lower().startswith("lookup"):
            await message.channel.send(embed=lookup_user(message))
            return
    
        # ladder
        if message.content.lower().startswith("ladder"):
            ladder = lookup_ladder(message)
            await message.channel.send(embed=ladder[0], file=ladder[1])
            return
        
        # add games
        if message.content.lower().startswith("add "):# and message.channel.guild.id == conf.main_server:
            add_match(message)
            await message.channel.send("Game(s) added!")
            return
        
        #ability randomizer 
        if message.content.lower().startswith("randomizer"):
            await ability_randomizer(message)
            return            
                                   
        # print matches.txt
        if message.content.lower() == "print":
            await print_matches(message)
            return

        if message.content.lower() in ["sanity", "check", "sanity check"]:
            await sanity_check_matches(message)
    
        # edit matches.txt
        if message.content.lower().startswith("edit "):
            await edit_matches(message)
            return
    
        # replace matches.txt content
        if message.content.lower().startswith("replace"):
            await replace_matches(message)
            return
    
        ident = "update"
    
        # update db
        if message.content.lower().startswith(ident) and message.channel.guild.id == conf.main_server or message.author.id in conf.admin:
            await updater(message)
            return
    
        ident = "team comps"
    
        if message.content.lower().startswith(ident):
            await team_comps(message, ident)
            return
    
        play = "play"
    
        # the queue
        if message.content.lower().startswith(play):
            channel = message.channel
            user = message.author
            msg = message.content
            msg = msg.replace("  ", " ")
            msg = msg.replace(play, "")
            msg = msg.replace(play.capitalize(), "")
            msg = msg.replace("Play", "")
            await play_command(msg, user, channel, message.guild.id)
            return
    
        ident = "queue remove"
    
        if ident in message.content.lower():
            channel = message.channel
            user = message.author
            msg = message.content
            msg = msg.replace("  ", " ")
            msg = msg.replace(ident, "")
            msg = msg.replace("queue remove", "")
            try:
                await queue_rm_command(msg, user, channel)
            except:
                await channel.send("Did not find you in a queue. " + find_insult())
            return
    
        # print current queue
        if message.content.lower().startswith("queue"):
            await print_queue(message)
            return
    
        if message.content.lower().startswith("remake"):
            await check_remake(message)
            return
    
        if message.content.lower().startswith("ocr"):
            await ocr_screenshot(message)

        if message.content.lower().startswith("user add"):
            await user_add(message)
            return
     
    elif message.content == "Y":
        await message.channel.send(f"{message.author.name} has tacoed out.")
        return
    
        return
    
    elif message.channel.id in conf.synched_channels:
        await sync_channels(message)
                                  

client.run(conf.discord_id)

# once the client stops we need to save current queue progress
# this doesn't save the queue removal jobs currently so unfortunately users need to do this manually
def stop_func(sig, frame):
    print("Stopping.")
    # these just join all the values in the different queues
    queues = []
    for q in [aa_queue, dm_queue, e_queue, mh_queue, aa_queue_users, dm_queue_users, e_queue_users, mh_queue_users, au_queue]:
        queues.append(", ".join(q))
    with open("queues.txt", "w") as f:
        f.write("; ".join(queues))
        f.close()

    sys.exit(0)

signal.signal(signal.SIGINT, stop_func)
signal.pause()
