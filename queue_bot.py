import util
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import telegram_bot
import discord
from discord.ext import commands
import botconfig as conf
import teams
from functools import partial
from datetime import datetime, timedelta, date, timezone
import os
import signal
import sys
import re


db = util.connect()

scheduler = AsyncIOScheduler()
scheduler.start()

intents = discord.Intents.default()
intents.members = True
#intents.message_content = True

client = commands.Bot(command_prefix="an", intents=intents)

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


@client.event
async def on_ready():
    await update_presence()
    print("Starting.")

# we save the queues here as simple arrays since we don't expect to scale
# read out the queues from the queues file that saves state for restarts
with open("queues.txt", "r") as f:
    queues = {}
    queues_users = {}
    queues_lengths = {"e": 4, "mh": 6, "do": 8}
    old_queues = f.read()
    old_queues = old_queues.split("; ")
    i = 0
    for q in old_queues:
        old_queues[i] = old_queues[i].split(", ")
        if old_queues[i] == [""]:
            old_queues[i] = []
        i += 1
    queues["e"] = old_queues[0] if old_queues[0] != " " else []
    queues_users["e"] = old_queues[1] if old_queues[1] != " " else []
    queues["mh"] = old_queues[2] if old_queues[2] != " " else []
    queues_users["mh"] = old_queues[3] if old_queues[3] != " " else []
    queues["do"] = old_queues[4] if old_queues[4] != " " else []
    queues_users["do"] = old_queues[5] if old_queues[5] != " " else []
    f.close()

# change bot presence function
# it just appends queues if there's someone in one
# otherwise it shows Wanted 6/9
async def update_presence():
    presence = ""
    for mode in util.QUEUEABLE_MODES:
        if len(queues[mode]):
            if presence:
                presence += ", "
            presence += f"{mode.upper()}: {len(queues[mode])}/{queues_lengths[mode]}"

    if not presence:
        presence = "Wanted 6/9"

    await client.change_presence(activity=discord.Game(name=presence + " | AN help"))
    return

# team comp finder
# teams.py is the really relevant stuff
def team_finder(players, mode, random, groups=[]):
    # this outputs all the players in one array so we need to split it
    ts = teams.find_teams(players, mode=mode, random=random, groups=groups)
    t1, t2 = [], []
    for i in [0, 1]:
        for player in ts[i]:
            if i == 0:
                t1.append(player["name"])
            elif i == 1:
                t2.append(player["name"])
    return f"{', '.join(t1)} vs. {', '.join(t2)}"

# team comps generator
@util.command_dec
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
        mode = util.check_mode(mode, short=True)
    else:
        mode = util.check_mode(0, message.guild.id, short=True, channel=message.channel.id)

    # if players were specified we can just run the team_finder func and send that
    if len(players) > 1:
        # check if groups specified
        delim = " & "
        groups = []
        for p in players:
            if delim in p:
                # if so delete the group element
                players.remove(p)
                # figure out the grouped players
                group_players = p.split(delim)
                # add to groups list
                groups.append(group_players)
                # and add the playres back into the overall list
                for gp in group_players:
                    players.append(gp)
        matchup = team_finder(players, mode, r_factor, groups=groups)
        await channel.send(matchup)
    # otherwise we try to grab the mode's queue and use that
    else:
        try:
            matchup = team_finder(queues[mode], mode, r_factor)
            await channel.send(matchup)
        except:
            await channel.send("That didn't work, idiot. " + util.find_insult())
    return


@util.command_dec
async def find_lobbies(message):
    lobby_sizes = {"e": 4, "mh": 6, "do": 8, "aa": 8}
    channel = message.channel
    # let's just stick to default modes so people don't get confused
    msg = message.content[len("lobbies "):]
    mode = False
    if "mode" in msg:
        temp = msg.split(" ")
        mode = temp[temp.index("mode") + 1]
        msg = msg.replace(" mode " + mode, "")
    mode = util.check_mode(mode, message.guild.id, short=True, channel=channel.id)
    lobbies = teams.find_lobbies(msg.split(", "), mode, lobby_sizes[mode])
    lobbies = [", ".join(l) for l in lobbies]
    lobbies_text = "\n".join(lobbies)
    await channel.send("Suggested lobbies:\n" + lobbies_text)
    return


# queue removal command
# super straightforward
async def queue_rm(mode, user, player, channel):
    try:
        queues[mode].remove(player)
        queues_users[mode].remove(user.mention)
        await channel.send(f"Removed {user.name} from the queue. {modes_dict[mode]}: {len(queues[mode])}/{queues_lengths[mode]}")
        await update_presence()
    except:
        pass
    return


## I started this but it's too annoying - at this point I hate the queueing system
## this should end up being an embed listing everyone in the Q along with all schedules
#async def queue_embed(channel, mode):
#    smode = check_mode(mode, channel, short=True)
#    lmode = check_mode(mode, channel, short=False)
#    queue_str = ", ".join(queue[smode])
#    queued = scheduler.get_jobs()
#    for j in queued:
#    embed = discord.Embed(title=f"{lmode} Queue", color=0xff00ff)

# add player to play queue command
# this is the most poorly written function in here honestly
#@util.command_dec
async def play_command(msg, user, channel, gid):
    # parse the message for times
    # only support hours for simplicity's sake
    if " for " in msg:
        length = re.findall(".* for (.*)", msg)[0]
        length = length.replace(" h", "").replace("h", "")
        length = length.split(" ")[0]
        msg = msg.replace(" for " + length, "")
        try:
            length = float(length)
        except:
            await channel.send("Did not recognize given playtime length.")
            return
    else:
        length = 3 # hours
    if " in " in msg:
        start = re.findall(".* in (.*)", msg)[0]
        start = start.replace(" h", "").replace("h", "")
        start = start.split(" ")[0]
        msg = msg.replace(" in " + start, "")
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
        mode = mode.split(" ")[0]
        msg = msg.replace(" mode " + mode, "")
        mode = util.check_mode(mode, short=True)
    # if mode is empty use guild ID to auto determine mode
    else:
        mode = util.check_mode(0, gid, short=True, channel=channel.id)
    
    # now that the rest of the message has been parsed only the player name should be left
    player = msg
    
    # remove leading and trailing spaces in player names
    if player:
        if player[-1] == " ":
            player = player[:-1]
        elif player[0] == " ":
            player = player[1:]
    
    # this is where we try to find the player according to their Discord ID if no player is specified
    # otherwise we try to match the given player to an AN user
    db = util.connect()

    if not player:
        player_db = db.players.find_one({"discord_id" : str(user.id)})
        if not player_db:
            await channel.send("I don't know you. " + util.find_insult())
            return
        player = player_db["name"]
    else:
        try:
            player_db = util.identify_player(db, player)
        except ValueError as e:
            await channel.send(e)
            return

    # remove from queue before re-adding
    if player in queues[mode]:
        await queue_rm(mode, user, player, channel)
    for i in scheduler.get_jobs():
        if player + f"_{mode}_start" == i.id:
            scheduler.remove_job(player + f"_{mode}_start")
        elif player + f"_{mode}_remove" == i.id:
            scheduler.remove_job(player + f"_{mode}_remove")
            # this is only necessary for the remove command because it will always be included
            await channel.send(f"{player} has been re-scheduled to queue up.")

    # the part where people are added to the queue
    async def queue():
        queues[mode].append(player)
        queues_users[mode].append(user.mention)
        await update_presence()
        if len(queues[mode]) == queues_lengths[mode]:
            matchup = team_finder(queues[mode], mode=mode, random=0)
            await channel.send(", ".join(queues_users[mode]) + f": {modes_dict[mode]} {queues_lengths[mode]}/{queues_lengths[mode]}, get on!\nMy suggested teams: " + matchup)
            for p in queues[mode]:
                try:
                    telegram_bot.notify_player(p, modes_dict[mode])
                except:
                    pass
        elif len(queues[mode]) < queues_lengths[mode]:
            await channel.send(f"Added {player} to the queue for {length} hour(s). {modes_dict[mode]}: {len(queues[mode])}/{queues_lengths[mode]}")
        else:
            await channel.send(f"We're already enough for {modes_dict[mode]}.")
        return

    # if a start time was specified we add a job to the scheduler
    # the 1s timedelta is in case the script lags for a second
    if start > 0:
        try: 
            end_time_add = datetime.isoformat(datetime.now() + timedelta(seconds = 1, hours = start))
            scheduler.add_job(queue, 'interval', hours=start, end_date=end_time_add, id=player + f"_{mode}_start")
            await channel.send(f"Will add {player} to the queue in {start} hour(s).")
        except:
            await channel.send(f"Did not recognize given start time or user already in queue.")
            return
    else:
        await queue()

    # this adds queue removal
    end_time_rm = datetime.isoformat(datetime.now() + timedelta(hours=start + length, seconds = 1))
    scheduler.add_job(partial(queue_rm, mode=mode, user=user, player=player, channel=channel), 'interval', hours=length + start, end_date=end_time_rm, id=(player if player else user.name) + f"_{mode}_remove")
    return

# queue removal command
@util.command_dec
async def queue_rm_command(msg, user, channel): 
    # remove trailing and leading spaces
    if msg:
        if msg[-1] == " ":
            msg = msg[:-1]
        elif msg[0] == " ":
            msg = msg[1:]

    db = util.connect()

    if not msg:
        player_db = db.players.find_one({"discord_id" : str(user.id)})
        if not player_db:
            await channel.send("I don't know you. " + util.find_insult())
            return
    else:
        try:
            player_db = util.identify_player(db, player)
        except ValueError as e:
            await channel.send(e)
            return

    player = player_db["name"]

    try:
        for mode in queues.keys():
            scheduler.remove_job(player + f"_{mode}_start")
            await channel.send(f"Successfully removed {player} from the {modes_dict[mode]} queue.")
    except:
        for i in queues.keys():
            try:
                await queue_rm(i, user, player, channel)
            except:
                pass
        return

    # end queue job removal
    try:
        for mode in queues.keys():
            scheduler.remove_job(player + f"_{mode}_remove")
    except:
        pass
    return


def get_job_eta(job):
    """
    Extract job ETA as days, hours, minutes.
    """
    futures = ""
    st = job.trigger.start_date
    td = st - datetime.now(timezone.utc)
    days = td.days
    if days > 0:
        futures += f"{days} days, "
    hours, remainder = divmod(td.seconds, 3600)
    if hours > 0:
        futures += f"{hours} hours, "
    minutes, seconds = divmod(remainder, 60)
    if minutes > 0:
        futures += f"{minutes} minutes"
    return futures

# command to print the whole queue for a mode
# very simple
@util.command_dec
async def print_queue(message):
    msg = message.content.lower()
    msg = msg.replace("queue ", "")
    msg = msg.replace("queue", "")
    mode = util.check_mode(msg, message.guild.id, short=True, channel=message.channel.id)
    jobs = scheduler.get_jobs()
    if len(jobs) > 0:
        current = ""
        for p in queues[mode]:
            if current:
                current += ", "
            current += f"{p} (for {get_job_eta(scheduler.get_job(f'{p}_{mode}_remove'))})"
        futures = "\n"
        for job in jobs:
            if job.id.endswith(f"{mode}_start"):
                futures += job.id[:-7 - len(mode)] + " in "
                futures += get_job_eta(job)
                futures += "\n"
    else:
        futures = ""
        current = ", ".join(queues[mode])
    response = f"{modes_dict[mode]} {len(queues[mode])}/{queues_lengths[mode]}: {current}"
    await message.channel.send(response + futures)
    return


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    elif message.content.lower().startswith("an "):
        message.content = message.content[3:]
    
        ident = "team comps"
    
        if message.content.lower().startswith(ident):
            await team_comps(message, ident)
            return

        if message.content.lower().startswith("lobbies"):
            await find_lobbies(message)
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
                await channel.send("Did not find you in a queue. " + util.find_insult())
            return
    
        # print current queue
        if message.content.lower().startswith("queue"):
            await print_queue(message)
            return
    
        if message.content.lower().startswith("remake"):
            await check_remake(message)
            return
 

client.run(conf.discord_id)

# once the client stops we need to save current queue progress
# this doesn't save the queue removal jobs currently so unfortunately users need to do this manually
def stop_func(sig, frame):
    print("Stopping.")
    # these just join all the values in the different queues
    queues_joined = []
    for q in queues:
        queues_joined.append(", ".join(queues[q]))
        queues_joined.append(", ".join(queues_users[q]))
    with open("queues.txt", "w") as f:
        f.write("; ".join(queues_joined))
        f.close()

    sys.exit(0)

signal.signal(signal.SIGINT, stop_func)
signal.pause()

