import botconfig as conf
import datetime
import discord
import random
import traceback

# Artifact assault is played in several games; each is its own mode, rated
# separately for running and defending: players carry <key>rmmr / <key>dmmr
# ("acraa" gives "acraarmmr" / "acraadmmr"). ACR's used to be the plain
# "aa" / "aar" / "aad"; migrate_acr_aa.py renames existing data, and
# check_mode still understands the old spellings.
AA_GAMES = {"acraa": "ACR", "ac3aa": "AC3", "ac4aa": "AC4"}
AA_MODES = list(AA_GAMES)
AA_ROLE_MODES = [key + role for key in AA_MODES for role in ("r", "d")]

GAME_MODES = ["e", "mh", "do", "dm", "asb"] + AA_MODES
ALL_MODES = ["e", "mh", "do", "dm", "asb"] + AA_ROLE_MODES
TEAM_MODES = ["e", "mh", "do"] + AA_ROLE_MODES
FFA_MODES = ["dm", "asb"]

# how each mode is spelled in match documents
MODE_NAMES = {
    "e": "Escort",
    "mh": "Manhunt",
    "do": "Domination",
    "dm": "Deathmatch",
    "asb": "Assassinate brotherhood",
    "acraa": "ACR Artifact assault",
    "ac3aa": "AC3 Artifact assault",
    "ac4aa": "AC4 Artifact assault",
}


def is_aa(mode):
    """True for any Artifact assault mode key ("acraa", "ac3aa", ...)."""
    return mode in AA_GAMES


def aa_mode_of(role_mode):
    """The Artifact assault mode of a role key: "ac3aar" -> "ac3aa"."""
    return role_mode[:-1] if role_mode[:-1] in AA_GAMES else None


def mode_name(mode):
    """The spelling of a mode key in match documents."""
    return MODE_NAMES[check_mode(mode, short=True)]


def _aa_variant(mode, short):
    """check_mode for Artifact assault spelled with its game ("ac3 aa", "acr aa running", ...)."""
    for key, game in AA_GAMES.items():
        g = game.lower()
        full = f"{g} artifact assault"
        base = {key, f"{g} aa", f"{g}aa", f"{g} artifact assault", f"artifact assault {g}", f"aa {g}"}
        if mode in base:
            return key if short else full
        for role, word in (("r", "running"), ("d", "defending")):
            names = {key + role, f"{g} aa{role}", f"{g} aa {word}", f"{g} artifact assault {word}",
                     f"artifact assault {word} {g}"}
            if mode in names:
                return key + role if short else f"{full} {word}"
    return None
QUEUEABLE_MODES = ["e", "mh", "do", "asb"]

def connect():
    """
    very basic connect to port 27017 mongodb client
    """
    from flask_pymongo import PyMongo
    from pymongo import MongoClient
#    client = MongoClient('mongodb://mongoservice:27017')
    client = MongoClient('mongodb://localhost:27017')
    db = client.public
    return db


def identify_player(db, name):
    """
    identify a player by trying the name first then igns
    case insensitive

    :param db: database
    :param name: name to search for
    :return: player mongodb object
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
def check_mode(mode, server=None, short=False, channel=None):
    """
    Identify the mode referred to by parsing the mode string and falling back
    to discord server IDs.

    :param mode: mode string to parse
    :param server: discord server ID
    :param short: switch between abbreviations and full names
    :param channel: discord channel ID
    :return: identified mode
    """
    # default modes for servers
    if (channel or server) and not mode:
        if channel in conf.e_channels:
            return "e" if short else "escort"
        elif channel in conf.mh_channels:
            return "mh" if short else "manhunt"
        elif channel in conf.aa_channels:
            return "acraa" if short else "acr artifact assault"
        elif channel in conf.do_channels:
            return "do" if short else "domination"
        elif channel in conf.dm_channels:
            return "dm" if short else "deathmatch"
        elif channel in conf.asb_channels:
            return "asb" if short else "assassinate brotherhood"
        elif server in conf.e_servers:
            return "e" if short else "escort"
        elif server in conf.mh_servers:
            return "mh" if short else "manhunt"
        elif server in conf.aa_servers:
            return "acraa" if short else "acr artifact assault"
        elif server in conf.do_servers:
            return "do" if short else "domination"
        elif server in conf.dm_servers:
            return "dm" if short else "deathmatch"
        elif server in conf.asb_servers:
            return "asb" if short else "assassinate brotherhood"
        else:
            return "escort"
    mode = mode.lower()
    # if server wasn't specified use abbreviations
    if mode in ["m", "mh", "manhunt"]:
        return "mh" if short else "manhunt"
    elif mode in ["e", "escort"]:
        return "e" if short else "escort"
    # ACR's Artifact assault under its old names
    elif mode in ["aa", "artifact assault"]:
        return "acraa" if short else "acr artifact assault"
    elif mode in ["aar", "artifact assault running"]:
        return "acraar" if short else "acr artifact assault running"
    elif mode in ["aad", "artifact assault defending"]:
        return "acraad" if short else "acr artifact assault defending"
    elif mode in ["do", "domination"]:
        return "do" if short else "domination"
    elif mode in ["dm", "deathmatch"]:
        return "dm" if short else "deathmatch"
    elif mode in ["asb", "assassinate brotherhood"]:
        return "asb" if short else "assassinate brotherhood"
    elif _aa_variant(mode, short) is not None:
        return _aa_variant(mode, short)
    else:
        raise ValueError("check_mode: Unsupported mode found.")

def att_to_file(message, n=0):
    """
    Convert discord attachment to file.

    :param message: message object including attachment
    :param n: attachment number
    :return: attachment as file
    """
    # I was having issues getting this working without saving separately
    import requests
    _att = requests.get(message.attachments[n].url)
    fname = f"sync/{message.attachments[n].filename}"
    with open(fname, "wb") as f:
        f.write(_att.content)
    with open(fname, "rb") as f:
        att = discord.File(f, filename="image.png")
    return att


# some fun ACB insults to use as error messages
insults = ["You suck.", "Even fouadix speaks English better than you.",
        "I bet you'd choose sex over escort.", "Go back to wanted.", "You played on Xbox, didn't you?",
        "I'd choose Fazz over you.", "Even Fazz kills less civis than you.", "Dell runs less than you.",
        "Are you from AC4?", "Speed gets fewer deaths than you.", "What the fuck is that?",
        "Let's not do that again.", "I just want to punch myself in the fucking face.", "Really fucking hilarious.",
        "Dude, I'ma slaughter your entire family if you ever do that again.", "Oh man, I hate you.", "u r getting scummy",
        "If only you could fuck up the escort never.", "Welcome to TCG.", "You turbotrolled more than Omse.",
        "Do your fucking job I can't do mine.", "You go in, I'm not even there, and then you wonder waroi waroi.",
        "Even Edi is more sylish than you."]

def find_insult():
    """
    Find a fun ACMP theme insult from list of insults.

    :return: random insult
    """
    return random.choice(insults)


def command_dec(func):
    """
    command decorator with proper error handling
    prints the error and informs the user of the error while insulting them
    """
    async def exceptionhandler(*arg):
        try:
            await func(*arg)
        except Exception as e:
            print(traceback.format_exc())
            await arg[0].channel.send(str(e) + " " + find_insult())
    return exceptionhandler


def permission_locked(func):
    """
    Locks a command behind the Assassins' Network role or admin accounts.
    """
    async def permission_checker(*args):
        message = args[0]
        db = connect()
        user = db.players.find_one({"discord_id": str(message.author.id)})
        if not user or user["privilege"] > 5:
            await message.channel.send("You do not have the required permissions! Please contact an admin.")
        else:
            await func(*args)
    return permission_checker


def identify_map(name=None, get_map_keys=False):
    maps = {
            "antioch": "Antioch",
            "castel": "Castel Gandolfo",
            "galata": "Galata",
            "ippo": "Ippokratous",
            "kh": "Knight's Hospital",
            "msm": "Mont-Saint-Michel",
            "rome": "Rome",
            "souk": "Souk",
            "venice": "Venice",
            "dyers": "Dyers",
            "imperial": "Imperial",
            "jerusalem": "Jerusalem",
            "siena": "Siena",
            "sd": "San Donato",
            "florence": "Florence",
            "monte": "Monteriggioni",
            "alhambra": "Alhambra",
            "pienza": "Pienza",
            "forli": "Forli",
            "st mathieu": "Saint-Mathieu",
            "st mathieu1": "Saint-Mathieu DM",
            "st mathieu2": "Saint-Mathieu DM2",
            "st mathieu3": "Saint-Mathieu DM3",
            "santa lucia": "Santa Lucia",
            "santa lucia1": "Santa Lucia DM",
            "santa lucia2": "Santa Lucia DM2",
            "santa lucia3": "Santa Lucia DM3",
            "tampa": "Tampa Bay",
            "tampa1": "Tampa Bay DM",
            "tampa2": "Tampa Bay DM2",
            "tampa3": "Tampa Bay DM3",
            "havana": "Havana",
            "havana1": "Havana DM",
            "havana2": "Havana DM2",
            "havana3": "Havana DM3",
            "kingston": "Kingston",
            "kingston1": "Kingston DM",
            "kingston2": "Kingston DM2",
            "kingston3": "Kingston DM3",
            "palenque": "Palenque",
            "palenque1": "Palenque DM",
            "palenque2": "Palenque DM2",
            "palenque3": "Palenque DM3",
            "portobelo": "Portobelo",
            "portobelo1": "Portobelo DM",
            "portobelo2": "Portobelo DM2",
            "portobelo3": "Portobelo DM3",
            "prison": "Prison",
            "prison1": "Prison DM",
            "prison2": "Prison DM2",
            "prison3": "Prison DM3",
            "plantation": "Virginian Plantation",
            "plantation1": "Virginian Plantation DM",
            "plantation2": "Virginian Plantation DM2",
            "plantation3": "Virginian Plantation DM3",
            "saba": "Saba Island",
            "saba1": "Saba Island DM",
            "saba2": "Saba Island DM2",
            "saba3": "Saba Island DM3",
            "st pierre": "Saint Pierre",
            "st pierre1": "Saint Pierre DM",
            "st pierre2": "Saint Pierre DM2",
            "st pierre3": "Saint Pierre DM3",
            "charlestown": "Charlestown",
            "charlestown1": "Charlestown DM",
            "charlestown2": "Charlestown DM2",
            "charlestown3": "Charlestown DM3"
            }
    # return the map keys if needed
    if get_map_keys:
        return maps.keys()
    elif name is None:
        raise ValueError("name cannot be None if get_map_keys is not set!")

    return maps[name.lower()]

def rank_title(elo):
    if elo < 801:
        return "Disciple"
    if elo < 1000:
        return "Cleric"
    if elo < 1200:
        return "Cleric Supreme"
    if elo < 1400:
        return "Grand Cleric"
    return "Supreme Overlord Cleric"
