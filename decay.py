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
    if not excluded:
        return

    db = connect()
    now = datetime.now()
    recipients = []
    excluded_ids = [p["_id"] for p in excluded]

    for p in db.players.find({
        f"{mode}games.total": {"$gte": 10},
        "_id": {"$nin": excluded_ids}
    }):
        last_day = p[f"{mode}history"]["dates"][-1]
        last_day = datetime.strptime(last_day, "%y-%m-%d")

        if (now - last_day).days <= 7:
            recipients.append(p)

    if not recipients:
        return

    amount_per_player = amount / len(recipients)

    db.players.update_many(
        {"_id": {"$in": [p["_id"] for p in recipients]}},
        {"$inc": {f"{mode}mmr": amount_per_player}}
    )

    return   


def decay_all(mode):
    db = connect()
    # number of sessions that have to be missed
    sessions_threshold = 3
    # number of days since last session
    days_threshold = 7
    # amount to be subtracted from decay
    decay_base = 10
    # mmr after which decay sets in and lowest value you can decay to
    decay_threshold = 1000
    # how often the decay should be applied
    decay_interval = 7 # days
    # find all players with mmr > threshold and sessions since played > threshold
    players = list(db.players.find({"$and": [
        {f"{mode}sessionssinceplayed": {"$gte": sessions_threshold}},
        {f"{mode}mmr": {"$gt": decay_threshold}},
#        {f"{mode}games.total": {"$gte": 9}}
        ]}))
    # global spread decay pool
    decay_pool = 0
    # go through the players and make sure their last day played is also > threshold
    now = datetime.now()

    for p in players:
        last_day = p[f"{mode}history"]["dates"][-1]
        last_day = datetime.strptime(last_day, "%y-%m-%d")
        days_inactive = (now - last_day).days
        last_decay = datetime.strptime(p[f"{mode}lastdecay"], "%Y-%m-%d").date()
        days_since_decay = (now - last_decay).days
        
        if days_inactive >= days_threshold and days_since_decay >= decay_interval:
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
