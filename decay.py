from util import *
from datetime import datetime, date
from historyupdate import mmr_update
import ranks

def introduce_num_sessions():
    db = connect()
    today = date.today().strftime("%Y-%m-%d")
    for mode in ALL_MODES:
        db.players.update_many({}, {"$set": {f"{mode}sessionssinceplayed": 0}})
        db.players.update_many({}, {"$set": {f"{mode}lastdecay": today}})
    print("Done.")
    return


def update_sessions(players, mode):
    db = connect()
    db.players.update_many({"name": {"$nin": players}}, {"$inc": {f"{mode}sessionssinceplayed": 1}})
    return


def spread_decay(mode, amount, excluded):
    try:
        len(excluded)
    except:
        return
    if not len(excluded):
        return
    db = connect()
    players = list(db.players.find({"$and": [
        {f"{mode}games.total": {"$gte": 10}},
        {"_id": {"$nin": excluded}},
        ]}))
    amount /= len(players)
    db.players.update_many({"$and": [
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
        {f"{mode}sessionssinceplayed": {"$gte": sessions_threshold}},
        {f"{mode}mmr": {"$gt": decay_threshold}},
#        {f"{mode}games.total": {"$gte": 9}}
        ]})
    # global spread decay pool
    decay_pool = 0
    # go through the players and make sure their last day played is also > threshold
    for p in players:
        last_day = p[f"{mode}history"]["dates"][-1]
        last_day = datetime.strptime(last_day, "%y-%m-%d")
        diff_play = datetime.now() - last_day
        if diff_play.days > days_threshold and diff_play.days >= decay_interval:
            db.players.update_one({"_id": p["_id"]},
                    {"$set": 
                        {f"{mode}mmr": max(p[f"{mode}mmr"] - decay_amount, decay_threshold),
                        f"{mode}lastdecay": datetime.now().strftime("%Y-%m-%d"),
                        # require one session to be played in between decays
                        f"{mode}sessionssinceplayed": sessions_threshold - 1}
                        })
            # to refresh the mmr
            p = db.players.find_one({"_id": p["_id"]})
            # update the player's mmr history
            mmr_update(date.today().strftime("%y-%m-%d"), db, p, mode)
            # add to pool and decayed players
            decay_pool += decay_amount
            print(f"Decayed {p['name']}.")
    if decay_pool:
        spread_decay(mode, decay_pool, players)
        ranks.main([mode])
    return


if __name__ == "__main__":
    for mode in ALL_MODES:
        decay_all(mode)
    print("Done decaying.")
