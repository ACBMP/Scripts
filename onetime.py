from util import *

def change_usernames():
    db = connect()
    matches = db.matches.find()
    for m in matches:
        for i in [1, 2]:
            for j in range(len(m[f"team{i}"])):
                p = identify_player(db, m[f"team{i}"][j]["player"])
                m[f"team{i}"][j]["player"] = p["name"]
        db.matches.update_one({"_id": m["_id"]}, {"$set": {"team1": m["team1"], "team2": m["team2"]}})
    print("Done")
    return


def new_maps():
    import maps
    db = connect()
    db.maps.update_many({}, {"$set": {"aa.hostlosses": 0}})
    found = db.matches.find({"hostteam": {"$exists": True}, "mode": "Artifact assault"})
    for x in found:
        if x["outcome"] > 0 and x["outcome"] != x["hostteam"]:
            db.maps.update_one({"name": x["map"]}, {"$inc": {"aa.hostlosses": 1}})
    #db.matches.update_many({"map": {"$exists": True}}, {"$set": {"new": True}})
    print("Done.")
    return

def map_players():
    db = connect()
    games = list(db.matches.find({"map": {"$exists": True}}))
    for g in games:
        db.maps.update_one({"name": g["map"]}, {"$inc": {f"{check_mode(g['mode'], short=True)}.players": len(g["team1"]) * 2}})
    print("Done.")
    return

def test_query():
    from datetime import date
    from historyupdate import mmr_update
    db = connect()
    sessions_threshold = 3
    decay_threshold = 1000
    mode = "do"
    players = db.players.find()
    players = db.players.find({"$and": [
        {f"{mode}sessionssinceplayed": {"$gt": sessions_threshold}},
        {f"{mode}mmr": {"$gt": decay_threshold}}
        ]})
    for p in players:
        print(p["name"])
    return

#def cleanup():
#    db = connect()
#    ps = db.players.find()
#    for p in ps:
#        for m in ["mh", "e"]:
#            hist = p[f"{m}history"]
#            try:
#                for d in ["22-12-26", "23-01-02"]:
#                    i = hist["dates"].index(d)
#                    hist["dates"].pop(i)
#                    hist["mmrs"].pop(i)
#                db.players.update_one({"_id": p["_id"]}, {"$set": {f"{m}history": hist}})
#            except:
#                pass

if __name__ == "__main__":
    new_maps()
    #change_usernames()
