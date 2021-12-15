from flask_pymongo import PyMongo
from pymongo import MongoClient
from datetime import date


def update():
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

        # if player has no mmrhistory update it
        if p["mhhistory"]["mmrs"] == []:
            mmr_update(d, db, p, "mh")
        # if player's current mmr differs from previous mmr update it
        elif p["mhmmr"] != p["mhhistory"]["mmrs"][-1]:
            mmr_update(d, db, p, "mh")

        # same for escort
        if p["ehistory"]["mmrs"] == []:
            mmr_update(d, db, p, "e")
        elif p["emmr"] != p["ehistory"]["mmrs"][-1]:
            mmr_update(d, db, p, "e")
        
    return


def mmr_update(d, db, p, mode):
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
