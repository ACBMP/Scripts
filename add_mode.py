from util import *
from datetime import date


def mode_fields(mode, day=None, mmr=800):
    """The fields a player starts a mode with."""
    day = day or date.today().strftime("%y-%m-%d")
    games = {"total": 0, "won": 0, "lost": 0}
    stats = {"highscore": 0, "kills": 0, "deaths": 0, "totalscore": 0}
    if mode in FFA_MODES:
        games.update(podium=0, finishes=0)
    if mode in AA_ROLE_MODES:
        stats = {"kills": 0, "deaths": 0, "totalscore": 0, "scored": 0, "conceded": 0}
    return {f"{mode}mmr": mmr, f"{mode}games": games, f"{mode}stats": stats, f"{mode}rank": 0,
            f"{mode}rankchange": 0, f"{mode}history": {"dates": [day], "mmrs": [mmr]},
            # decay.py reads these once a mode has been played
            f"{mode}sessionssinceplayed": 0, f"{mode}lastdecay": date.today().strftime("%Y-%m-%d")}


def ensure_modes(db=None, query=None, modes=None):
    """
    Give players every mode they don't have yet (e.g. after new modes were
    added). Existing mode data is never touched, so this is safe to rerun.

    :return: {mode: number of players that got it}
    """
    db = db if db is not None else connect()
    added = {}
    for mode in modes or ALL_MODES:
        missing = dict(query or {}, **{f"{mode}mmr": {"$exists": False}})
        added[mode] = db.players.update_many(missing, {"$set": mode_fields(mode)}).modified_count
    return added


def add_mode(mode):
    db = connect()
    d = date.today().strftime("%y-%m-%d")
    mmr = 800
    history = {"dates": [d], "mmrs": [mmr]}
    games = {"total": 0, "won": 0, "lost": 0}
    stats = {"highscore": 0, "kills": 0, "deaths": 0, "totalscore": 0}
    rank = 0
    rankchange = 0
    db.players.update_many({}, {"$set": {f"{mode}mmr": mmr, f"{mode}games": games,
        f"{mode}stats": stats, f"{mode}rank": rank, f"{mode}rankchange": rankchange,
        f"{mode}history": history}})
    print(f"Successfully added {check_mode(mode)} stats for all players")
    return

def add_ffa_mode(mode):
    db = connect()
    d = date.today().strftime("%y-%m-%d")
    mmr = 800
    history = {"dates": [d], "mmrs": [mmr]}
    games = {"total": 0, "won": 0, "podium": 0, "lost": 0, "finishes": 0}
    stats = {"highscore": 0, "kills": 0, "deaths": 0, "totalscore": 0}
    rank = 0
    rankchange = 0
    db.players.update_many({}, {"$set": {f"{mode}mmr": mmr, f"{mode}games": games,
        f"{mode}stats": stats, f"{mode}rank": rank, f"{mode}rankchange": rankchange,
        f"{mode}history": history}})
    print(f"Successfully added {check_mode(mode)} stats for all players")

def remove_ffa_mode(mode):
    db = connect()
    db.players.update_many({}, {"$unset": {f"{mode}mmr": "", f"{mode}games": "",
        f"{mode}stats": "", f"{mode}rank": "", f"{mode}rankchange": "",
        f"{mode}history": ""}})
    print(f"Successfully removed {check_mode(mode)} stats for all players")

def add_aa():
    db = connect()
    d = date.today().strftime("%y-%m-%d")
    mmr = 800
    mode = ["acraad", "acraar"]
    for i in range(2):
        history = {"dates": [d], "mmrs": [mmr]}
        games = {"total": 0, "won": 0, "lost": 0}
        stats = {"kills": 0, "deaths": 0, "totalscore": 0, "scored":0, "conceded": 0}
        rank = 0
        rankchange = 0
        db.players.update_many({}, {"$set": {f"{mode[i]}mmr": mmr, f"{mode[i]}games": games,
            f"{mode[i]}stats": stats, f"{mode[i]}rank": rank, f"{mode[i]}rankchange": rankchange,
            f"{mode[i]}history": history}})
        print(f"Successfully added {check_mode(mode[i])} stats for all players")
    return

if __name__ == "__main__":
    for mode, count in ensure_modes().items():
        if count:
            print(f"Added {check_mode(mode)} to {count} players")
