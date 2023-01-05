from util import *

def _get_stat(match, stat, teams=[1, 2]):
    if isinstance(teams, int):
        teams = [teams]
    out = 0
    for i in teams:
        for p in match[f"team{i}"]:
            out += p[stat]
   # if stat == "score":
   #     out /= len(match["team1"])
    return out


def update_maps():
    db = connect()
    matches = db.matches.find({"new": True})

    for match in matches:
        try:
            map_name = match["map"]
        except:
            continue
        # short mode + .
        smode = check_mode(match["mode"], short=True) + "."
        # stats that are tracked no matter what
        base_stats = ["kills", "deaths", "score"]
        bs = [_get_stat(match, s) for s in base_stats]
        # dict with the base starts for mode
        stats = {smode + k: v for (k, v) in zip(base_stats, bs)}
        # in aa also track scored artifacts
        if match["mode"] == "Artifact assault":
            stats["aa.scored"] = _get_stat(match, "scored")
            stats["aa.hostscored"] = _get_stat(match, "scored", [match["hostteam"]])
        # if host data was given save w/l
        try:
            # determine which team host was on
            if match["hostteam"] == match["outcome"]:
                stats[smode + "hostwins"] = 1
            else:
                stats[smode + "hostlosses"] = 1
        except KeyError:
            pass
        # wins + 1
        stats[smode + "games"] = 1
        # save number of players
        stats[smode + "players"] = len(match["team1"]) * 2
        db.maps.update_one({"name": map_name}, {"$inc": stats})

    return


def introduce_maps():
    db = connect()
    maps_db = db["maps"]
    stats = {}
    base_stats = {"kills": 0, "deaths": 0, "score": 0, "hostwins": 0, "hostlosses": 0, "games": 0, "hostrating": 1000, "players": 0}
    for m in ["aa", "do", "e", "mh"]:
        stats[m] = base_stats
    stats["aa"]["scored"] = 0
    stats["aa"]["hostscored"] = 0

    for k in identify_map(get_map_keys=True):
        maps_db.insert_one(dict({"name": identify_map(k)}, **stats))
