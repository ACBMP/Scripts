from util import *
from datetime import date

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
    mode = ["aad", "aar"]
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
    add_ffa_mode("asb")
