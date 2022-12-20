from util import *
from datetime import datetime, date
from historyupdate import mmr_update

def introduce_num_sessions():
    db = connect()
    today = date.today().strftime("%Y-%m-%d")
    for mode in ["e", "mh", "aar", "aad", "do"]:
        db.players.update_many({}, {"$set": {f"{mode}sessionssinceplayed": 0}})
        db.players.update_many({}, {"$set": {f"{mode}lastdecay": today}})
    print("Done.")
    return


def update_sessions(players, mode):
    db = connect()
    db.players.update_many({"name": {"$nin": players}}, {"$inc": {f"{mode}sessionssinceplayed": 1}})
    return


def spread_decay(mode, amount, excluded):
    if not len(excluded):
        return
    db = connect()
    players = db.players.find({"$and": [
        {f"{mode}games.total": {"$gte": 10}},
        {"_id": {"$nin": excluded}},
        ]})
    amount /= len(players)
    players = db.players.update_many({"$and": [
        {f"{mode}games.total": {"$gte": 10}},
        {"_id": {"$nin": excluded}},
        ]},
        {"$inc": {f"{mode}mmr": amount}})
    return
    

def decay_all(mode):
    db = connect()
    # number of sessions that have to be missed
    sessions_threshold = 3
    # number of days since last session
    days_threshold = 7
    # amount to be subtracted from decay
    decay_amount = 5
    # mmr after which decay sets in and lowest value you can decay to
    decay_threshold = 1000
    # how often the decay should be applied
    decay_interval = 7 # days
    # find all players with mmr > threshold and sessions since played > threshold
    players = db.players.find({"$and": [
        {f"{mode}sessionssinceplayed": {"$gt": sessions_threshold}},
        {f"{mode}mmr": {"$gt": decay_threshold}}
        ]})
    # global spread decay pool
    decay_pool = 0
    # list of truly decayed players
    decayed_players = []
    # go through the players and make sure their last day played is also > threshold
    for p in players:
        last_day = p[f"{mode}history"]["dates"][-1]
        last_day = datetime.strptime(last_day, "%y-%m-%d")
        diff_play = datetime.now() - last_day
        #make sure it's been at least a week since last decay
        last_decay = p[f"{mode}history"]["dates"][-1]
        last_decay = datetime.strptime(last_decay, "%y-%m-%d")
        diff_decay = datetime.now() - last_decay
        if diff_play.days > days_threshold and diff_decay >= decay_interval:
            db.players.update_one({"_id": p["_id"]},
                    {"$set": [
                        {f"{mode}mmr": max(p[f"{mode}mmr"] - decay_amount, decay_threshold)},
                        {f"{mode}lastdecay": datetime.now().strftime("%Y-%m-%d")},
                        # require one session to be played in between decays
                        {f"{mode}sessionssinceplayed": sessions_threshold - 1},
                        ]})
            # update the player's mmr history
            mmr_update(date.today().strftime("%y-%m-%d"), db, p, mode)
            # add to pool and decayed players
            decay_pool += decay_amount
            decayed_players.append(p["_id"])
    spread_decay(mode, decay_pool, decayed_players)
    return


if __name__ == "__main__":
    for mode in ["e", "mh", "aar", "aad", "do"]:
        decay_all(mode)
    print("Done decaying.")
