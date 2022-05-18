import itertools
from util import *

# I have yet to run this so nobody has a rank yet

def main(modes=["mh", "e", "aar", "aad"]):
    """
    Update ranks for all players with >= 10 games in given modes.

    :param modes: modes to run over
    """
    for mode in modes:
        db = connect()
        players = db.players.find({f"{mode}games.total": {"$gte":10}})
        p_sorted = sorted(players, key=lambda player: player[f"{mode}mmr"], reverse=True)
        r = 1
        n = -1
    
        elos = []
    
        for k, v in itertools.groupby(p_sorted, lambda x: x[f"{mode}mmr"]):
            elos.append(k)
    
        for i in elos:
            p = db.players.find({f"{mode}mmr":i, f"{mode}games.total": {"$gte":10}})
            for player in p:
                if player[f"{mode}rank"] == 0:
                    c = 0
                else:
                    c = player[f"{mode}rank"] - r
                db.players.update_one({"_id":player["_id"]}, {"$set":{f"{mode}rankchange":c}})
                n += 1
            db.players.update_many({f"{mode}mmr":i, f"{mode}games.total": {"$gte":10}}, {"$set":{f"{mode}rank":r}})
            r += 1 + n
            n = -1
    
        p_inactive = db.players.find({f"{mode}games.total":{"$lt":10}})
        for x in p_inactive:
            db.players.update_one({"_id":x["_id"]}, {"$set":{f"{mode}rankchange":0}})
            db.players.update_one({"_id":x["_id"]}, {"$set":{f"{mode}rank":0}})

if __name__ == "__main__":
    main()
    print("Ranks updated.")
