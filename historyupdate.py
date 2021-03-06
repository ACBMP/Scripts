from flask_pymongo import PyMongo
from pymongo import MongoClient
from datetime import date


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

        for mode in ["mh", "e", "aar", "aad"]:
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
    if mode not in ["e", "mh", "aar", "aad"]:
        raise ValueError("mmr_update: Unrecognized mode!")

    dates = p[f"{mode}history"]["dates"]
    dates.append(d)
    mmrs = p[f"{mode}history"]["mmrs"]
    mmrs.append(p[f"{mode}mmr"])
    db.players.update_one({"name":p["name"]},{"$set":{f"{mode}history.dates":dates,f"{mode}history.mmrs":mmrs}})

    return


if __name__=="__main__":
    update()
