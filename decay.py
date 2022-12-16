from util import *
from datetime import datetime

def introduce_num_sessions():
    db = connect()
    for mode in ["e", "mh", "aar", "aad", "do"]:
        db.players.update({}, {"$set": {f"{mode}sessionssinceplayed": 0}})
    print("Done.")
    return


def update_sessions(players, mode):
    db = connect()
    db.players.update({"name": {"$nin": players}}, {"$inc": {f"{mode}sessionssinceplayed}", 1}})
    return


def decay_all(mode):
    db = connect()
    # number of sessions that have to be missed
    sessions_threshold = 5
    # number of days since last session
    days_threshold = 7
    # amount to be subtracted from decay
    decay_amount = 5
    # mmr after which decay sets in and lowest value you can decay to
    decay_threshold = 1200
    # find all players with mmr > threshold and sessions since played > threshold
    players = db.players.find({"$and": [
        {f"{mode}sessionssinceplayed": {"$gt": sessions_threshold}},
        {f"{mode}mmr": {"$gt": decay_threshold}}
        ]})
    # go through the players and make sure their last day played is also > threshold
    for p in players:
        last_day = p[f"{mode}history"]["dates"][-1]
        last_day = datetime.strptime(last_day, "%y-%m-%d")
        diff = datetime.now() - last_day
        if diff.days > days_threshold:
            db.players.update_one({"_id": p["_id"]},
                    {"$set":
                        {f"{mode}mmr": max(f"{mode}mmr" - decay_amount, decay_threshold)}})
    return
