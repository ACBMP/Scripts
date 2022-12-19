from flask_pymongo import PyMongo
from pymongo import MongoClient
from datetime import date
from util import *


def aa_roles(m):
    """
    Determine roles for players in an AA match and append to their dict.
    """
    kds = [{}, {}]
    for team in [1, 2]:
        # find kd for every player in team
        for p in m[f"team{team}"]:
            try:
                kds[team - 1][p["player"]] = p["kills"] / p["deaths"]
            except ZeroDivisionError:
                kds[team - 1][p["player"]] = 1000 # easier than inf I think
        # sort the kds, this creates a list of tuples
        kds[team - 1] = sorted(kds[team - 1].items(), key=lambda x: x[1])
        # highest kds are defenders
        role = "r"
        # go through every player
        for i in range(len(m[f"team{team}"])):
            if i > 1:
                role = "d"
            # set role value on match 
            found = False
            j = 0
            # go thru players until we find the right player
            while not found:
                if m[f"team{team}"][j]["player"] == kds[team-1][i][0]:
                    m[f"team{team}"][j]["role"] = role
                    found = True
                j += 1
    return m


def update():
    """
    Update all players' MMRs if they played a game on the current day.
    """
    # establishing a connection to the db
    client = MongoClient('mongodb://localhost:27017/')
    db = client.public

    # get current date
    d = date.today().strftime("%y-%m-%d")
    
    # find matches not in history
    players = {}
    matches = db.matches.find({"inhist": False})

    # save all the players who played
    for m in matches:
        mode = m["mode"]
        # for aa we have to figure out roles
        if mode == "Artifact assault":
            m = aa_roles(m)
        for i in [1, 2]:
            for p in m[f"team{i}"]:
                # we can just use shortened roles
                if mode == "Artifact assault":
                    mode = "aa" + p["role"]
                try:
                    if p["player"] in players[mode]:
                        continue
                    players[mode].append(p["player"])
                except KeyError:
                    players[mode] = [p["player"]]
                # reset mode - only important for aa but whatever
                mode = m["mode"]

    # run history mmr update on all players who played
    for mode in players.keys():
        # update sessionssinceplayed
        db.players.update_many({"name": {"$nin": players[mode]}}, {"$inc": {f"{check_mode(mode, short=True)}sessionssinceplayed": 1}})
        # run history update
        for p in players[mode]:
            mmr_update(d, db, identify_player(db, p), check_mode(mode, short=True))
        
    db.matches.update_many({"inhist": False}, {"$set": {"inhist": True}})
    return


def mmr_update(d, db, p, mode):
    """
    Helper to update history.

    :param d: current date
    :param db: database
    :param p: player
    :param mode: gamemode
    """
    # skip check_mode for AA 
    if mode not in ["aar, aad"]:
        mode = check_mode(mode, short=True)

    dates = p[f"{mode}history"]["dates"]
    dates.append(d)
    mmrs = p[f"{mode}history"]["mmrs"]
    mmrs.append(p[f"{mode}mmr"])
    db.players.update_one({"name":p["name"]},{"$set":{f"{mode}history.dates":dates,f"{mode}history.mmrs":mmrs}})

    return


def get_last_game(player, mode):
    """
    Get the date of the last game a player played in a given mode.

    :param player: player name or document
    :param mode: mode name as used in db
    :return: last game played's date
    """
    db = connect()
    if isinstance(player, str):
        player = db.players.find_one({"name": player})
    found = False
    igns = player["ign"]
    if type(igns) == str:
        igns = [igns]
    if player["name"] not in igns:
        igns += [name]
    search = [{"team1":{"$elemMatch":{"player":ign}}} for ign in igns]
    search += [{"team2":{"$elemMatch":{"player":ign}}} for ign in igns]
    last_match = db.matches.find({"$or": search}).sort("_id", -1).limit(1)[0]
    return last_match["date"]


if __name__=="__main__":
    update()
    #print(get_last_game("Dellpit", "Manhunt"))
