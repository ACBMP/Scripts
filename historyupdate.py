from flask_pymongo import PyMongo
from pymongo import MongoClient
from datetime import date
from util import *


def update():
    """
    Update all players' MMRs if they differ from their previous MMR.
    """
    # establishing a connection to the db
    client = MongoClient('mongodb://localhost:27017/')
    db = client.public

    # get current date
    d = date.today().strftime("%y-%m-%d")
    
    # find matches from current date
    players = {}
    matches = db.matches.find({"date": date.today().strftime("%Y-$m-$d")})

    # save all the players who played
    for m in matches:
        if m["mode"] == "Artifact assault":
            continue
        for i in [1, 2]:
            for p in m[f"team{i}"]:
                try:
                    if p["player"] in players[m["mode"]]:
                        continue
                    players[m["mode"]].append(p["player"])
                except KeyError:
                    players[m["mode"]] = [p["player"]]

    # run history mmr update on all players who played
    for mode in players.keys():
        for p in players[mode]:
            mmr_update(d, db, identify_player(db, p), mode)
        
    return


def mmr_update(d, db, p, mode):
    """
    Helper to update history.

    :param d: current date
    :param db: database
    :param p: player
    :param mode: gamemode
    """
    mode = check_mode(mode, short=True)

    dates = p[f"{mode}history"]["dates"]
    dates.append(d)
    mmrs = p[f"{mode}history"]["mmrs"]
    mmrs.append(p[f"{mode}mmr"])
    db.players.update_one({"name":p["name"]},{"$set":{f"{mode}history.dates":dates,f"{mode}history.mmrs":mmrs}})

    return


def get_last_game(player, mode):
    """
    Get the date of the last game a player played in a given mode.

    :param player: player name or document
    :param mode: mode name as used in db
    :return: last game played's date
    """
    db = connect()
    if isinstance(player, str):
        player = db.players.find_one({"name": player})
    found = False
    igns = player["ign"]
    if type(igns) == str:
        igns = [igns]
    if player["name"] not in igns:
        igns += [name]
    search = [{"team1":{"$elemMatch":{"player":ign}}} for ign in igns]
    search += [{"team2":{"$elemMatch":{"player":ign}}} for ign in igns]
    last_match = db.matches.find({"$or": search}).sort("_id", -1).limit(1)[0]
    return last_match["date"]


if __name__=="__main__":
    update()
    #print(get_last_game("Dellpit", "Manhunt"))
