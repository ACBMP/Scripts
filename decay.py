from util import *
from datetime import datetime, date
import historyupdate
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
    decay_base = 20
    # mmr after which decay sets in and lowest value you can decay to
    decay_threshold = 900
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

    last_match = db.players.find_one({f'{mode}sessionssinceplayed': 0})[f'{mode}history']["dates"][-1]
    last_match = datetime.strptime(last_day, "%y-%m-%d")
    now = datetime.now()
    diff_to_last_match = now - last_match

    for p in players:
        last_day = p[f"{mode}history"]["dates"][-1]
        last_day = datetime.strptime(last_day, "%y-%m-%d")
        diff_play = now - last_day
        
        if diff_play.days >= days_threshold and diff_play.days >= decay_interval and \
                diff_play.days > diff_to_last_match.days:
            decay = decay_base * p[f'{mode}sessionssinceplayed'] / sessions_threshold
            decay = min(decay, p[f"{mode}mmr"] - decay_threshold)
            db.players.update_one({"_id": p["_id"]},
                    {"$set": 
                        {f"{mode}mmr": p[f"{mode}mmr"] - decay,
                        f"{mode}lastdecay": datetime.now().strftime("%Y-%m-%d")}
                        })
            # to refresh the mmr
            p = db.players.find_one({"_id": p["_id"]})
            # update the player's mmr history
            historyupdate.mmr_update(date.today().strftime("%y-%m-%d"), db, p, mode)
            # add to pool and decayed players
            decay_pool += decay
            print(f"Decayed {p['name']}.")
    if decay_pool:
        spread_decay(mode, decay_pool, players)
        ranks.main([mode])
        # historyupdate.force_update(mode)
    return


if __name__ == "__main__":
    for mode in ALL_MODES:
        decay_all(mode)
    print("Done decaying.")
