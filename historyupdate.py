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

    # list all players
    players = db.players.find()
    players = list(players)

    # iterature through players and update
    for i in range(len(players)):
        p = players[i]

        for mode in ["mh", "e", "aar", "aad", "do"]:
            # if player has no mmrhistory update it
            if p[f"{mode}history"]["mmrs"] == []:
                mmr_update(d, db, p, mode)
            # if player's current mmr differs from previous mmr update it
            elif p[f"{mode}mmr"] != p[f"{mode}history"]["mmrs"][-1]:
                mmr_update(d, db, p, mode)
        
    return


def mmr_update(d, db, p, mode):
    """
    Helper to update history.

    :param d: current date
    :param db: database
    :param p: player
    :param mode: gamemode
    """
    if mode not in ["e", "mh", "aar", "aad", "do"]:
        raise ValueError("mmr_update: Unrecognized mode!")

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
    #update()
    print(get_last_game("Dellpit", "Manhunt"))
