import itertools
from util import *

# I have yet to run this so nobody has a rank yet

def main(modes=None):
    """
    Update ranks for all players with >= 10 games in given modes.

    :param modes: modes to run over
    """
    modes = modes if modes else ALL_MODES

    for mode in modes:
        db = connect()
        players = db.players.find({f"{mode}games.total": {"$gte":10}})
        p_sorted = sorted(players, key=lambda player: round(player[f"{mode}mmr"]), reverse=True)
        r = 1
        n = -1
    
        elos = []
    
        for k, v in itertools.groupby(p_sorted, lambda x: round(x[f"{mode}mmr"])):
            elos.append(round(k))
    
        for i in elos:
            for p in p_sorted:
                if round(p[f"{mode}mmr"]) == i:
                    if p[f"{mode}rank"] == 0:
                        c = 0
                    else:
                        c = p[f"{mode}rank"] - r
                    c = p[f"{mode}rank"] - r
                    db.players.update_one({"_id":p["_id"]}, {"$set":{f"{mode}rankchange":c, f"{mode}rank":r}})
                    n += 1
            r += 1 + n
            n = -1
    
        p_inactive = db.players.find({f"{mode}games.total":{"$lt":10}})
        for x in p_inactive:
            db.players.update_one({"_id":x["_id"]}, {"$set":{f"{mode}rankchange":0}})
            db.players.update_one({"_id":x["_id"]}, {"$set":{f"{mode}rank":0}})

if __name__ == "__main__":
    main()
    print("Ranks updated.")
