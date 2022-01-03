import botconfig as conf
import datetime
import discord

def connect():
    """
    very basic connect to port 27017 mongodb client
    """
    from flask_pymongo import PyMongo
    from pymongo import MongoClient
    client = MongoClient('mongodb://localhost:27017')
    db = client.public
    return db


def identify_player(db, name):
    """
    identify a player by trying the name first then igns
    case insensitive
    """
    import re
    rename = re.compile(name, re.IGNORECASE)
    player = db.players.find_one({"name" : rename})
    if player is None:
        player = db.players.find_one({"ign": rename})
    if player is None:
        player = db.players.find_one({"discord_id": name.replace("@!", "").replace(">", "").replace("<", "")})
    if player is None:
        raise ValueError(f"identify_player: player {name} not found")
    return player


# mode checker
def check_mode(mode, server=None, short=False):
    # default modes for servers
    if server and not mode:
        if server in conf.e_servers:
            return "e" if short else "escort"
        elif server in conf.mh_servers:
            return "mh" if short else "manhunt"
        elif server in conf.dm_servers:
            return "dm" if short else "deathmatch"
        elif server in conf.aa_servers:
            return "aa" if short else "artifact assault"
        else:
            return "manhunt"
    mode = mode.lower()
    # if server wasn't specified use abbreviations
    if mode in ["mh", "manhunt"]:
        return "mh" if short else "manhunt"
    elif mode in ["e", "escort"]:
        return "e" if short else "escort"
    elif mode in ["au", "among", "among us"]:
        return "au" if short else "among us"
    elif mode in ["dm", "deathmatch", "dmatch"]:
        return "dm" if short else "deathmatch"
    elif mode in ["aa", "artifact assault"]:
        return "aa" if short else "artifact assault"
    elif mode in ["aar", "artifact assault running"]:
        return "aar" if short else "artifact assault running"
    elif mode in ["aad", "artifact assault defending"]:
        return "aad" if short else "artifact assault defending"
    else:
        raise ValueError("check_mode: Unsupported mode found.")


def att_to_file(message, n=0):
    # I was having issues getting this working without saving separately
    import requests
    _att = requests.get(message.attachments[n].url)
    fname = f"sync/{message.attachments[n].filename}"
    with open(fname, "wb") as f:
        f.write(_att.content)
    with open(fname, "rb") as f:
        att = discord.File(f, filename="image.png")
    return att

