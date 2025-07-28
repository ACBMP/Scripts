from util import *

def change_usernames():
    db = connect()
    matches = db.matches.find()
    for m in matches:
        if "team1" in m:
            for i in [1, 2]:
                for j in range(len(m[f"team{i}"])):
                    p = identify_player(db, m[f"team{i}"][j]["player"])
                    m[f"team{i}"][j]["player"] = p["name"]
            db.matches.update_one({"_id": m["_id"]}, {"$set": {"team1": m["team1"], "team2": m["team2"]}})
        else:
            for i in range(len(m["players"])):
                p = identify_player(db, m["players"][i]["player"])
                m["players"][i]["player"] = p["name"]
            db.matches.update_one({"_id": m["_id"]}, {"$set": {"players": m["players"]}})
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

def change_name():
    db = connect()
    names = {"Alexutza123": "Alewoo",
             "Auditore92": "Audi",
             "BB-MurderCases": "BB",
             "BigDriply": "Drip",
             "Bounty Hunta 08": "Bounty",
             "Crispi Kreme": "Crispi",
             "DANIEL_BAILOTE": "Daniel",
             "Dellpit": "Dell",
             "DevelSpirit": "Try",
             "DurandalSword": "Durandal",
             "EternityEzioWolf": "Ezio",
             "Fabianfosf": "Fabian",
             "FatalWolf": "Fatal",
             "FynnC": "Fynn",
             "GamerPrince98": "Prince",
             "H4v0k": "Havok",
             "I Jaamie AC I": "Jamie",
             "I-14-Inch-LEGEND": "Inch",
             "IntooDeep202": "Deep",
             "LaDamaRossa77": "Dama",
             "Lime232": "Lime",
             "Lunaire.-": "Lunaire",
             "mariyaban": "Mariya",
             "MagicalNightKat": "Kat",
             "Maxi911": "Maxi",
             "Merrick 73": "Merrick",
             "MilliaRage89": "Millia",
             "piesio1": "piesio",
             "robin331": "Robin",
             "Reaper19111": "Reaper",
             "Sugarfree": "Sugar",
             "TDA-TheBeast": "Beast",
             "TL_ANGE": "Ange",
             "Ted95On": "Ted",
             "Tha Fazz": "Fazz",
             "TheAngryRiver": "Omse",
             "Vinny_Ferrara": "Vinny",
             "werty125": "Werty",
             "XxSkixxo": "Skixxo",
             "dreamkiller2000": "Dream",
             "jurrevolkers3000": "Jurre",
             "oliguembol": "Zysl",
             "x-JigZaw": "Jig",
             "xAlmighty IV": "Almighty",
             "xCanibal96": "Canibal",
             "xPsychoticLlama": "Llama"}
    for k, v in names.items():
        db.players.update_one({"name": k}, {"$set": {"name": v}})
    return

def inactive_users():
    db = connect()
    queries = [{f"{i}games.total": 0} for i in ALL_MODES]
    players = db.players.find({"$and": queries})
    for p in players:
        print(p["name"])

def remove_inactive():
    db = connect()
    to_delete = ["Ejesza", "Exological", "Bounty", "Alewoo", "POPO91Z", "Shen", "speedydrg", "wabashop", "fouadix", "zado", "Skill", "Gwin", "captainvallois", "darkcepters", "Swan_Maiden", "Tobiname", "Alkumer", "XxSilentdeathx", "Treyway", "Darius", "Vex", "Maxi", "Kyle", "PikuEon", "Nikita_Schur", "Rychu", "Trazz", "delfix", "Rabbi", "EazyAdry", "execution_time"]
    for n in to_delete:
        db.players.delete_one({"name": n})

def merge_user_average_pug(username):
    db = connect()
    player = db.players.find_one({"name": username})
    if not player:
        print(f"Name {username} not found")
        return
    igns = player["ign"] 
    if type(igns) == str:
        igns = [igns]
    if username not in igns:
        igns += [username]
    # I just haven't had to do this for team modes yet
#    search = [{"team1":{"$elemMatch":{"player":ign}}} for ign in igns]
#    t1_matches = db.matches.find({"$or": search}).sort("_id", -1)
#    search = [{"team2":{"$elemMatch":{"player":ign}}} for ign in igns]
#    t2_matches = db.matches.find({"$or": search}).sort("_id", -1)
    search = [{"players":{"$elemMatch":{"player":ign}}} for ign in igns]
    ffa_matches = db.matches.find({"$or": search}).sort("_id", -1)
    for m in ffa_matches:
        print(m)
        for ign in igns:
            db.matches.update_one(
                    {"_id": m["_id"], "players": {"$elemMatch":{"player":ign}}},
                    {"$set": {"players.$.player": "Average Pug"}}
                    )
    pug = db.players.find_one({"name": "Average Pug"})
    db.players.update_one({"_id": pug["_id"]}, {"$push": {"ign": username}})
    db.players.delete_one({"name": username})
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
    #merge_user_average_pug("sKIDcROW2018")
    #remove_inactive()
    inactive_users()
    #change_name()
    #new_maps()
    #change_usernames()
