from util import *

def _get_stat(match, stat, teams=None, ffa=False):
    out = 0
    if ffa:
        for p in match["players"]:
            out += p[stat]
    else:
        teams = [1,2] if not teams else teams
        if isinstance(teams, int):
            teams = [teams]

        for i in teams:
            for p in match[f"team{i}"]:
                out += p[stat]

    return out


def update_maps():
    db = connect()
    matches = db.matches.find({"new": True})

    for match in matches:
        try:
            map_name = match["map"]
        except:
            continue
        # short mode
        smode = check_mode(match["mode"], short=True)
        ffa = smode in FFA_MODES
        # stats that are tracked no matter what
        base_stats = ["kills", "deaths", "score"]
        bs = [_get_stat(match, s, ffa=ffa) for s in base_stats]
        # dict with the base starts for mode
        stats = {f'{smode}.{k}': v for (k, v) in zip(base_stats, bs)}
        # in aa also track scored artifacts
        if smode == "aa":
            stats["aa.scored"] = _get_stat(match, "scored")
            stats["aa.hostscored"] = _get_stat(match, "scored", [match["hostteam"]])
        # if host data was given save w/l
        if ffa:
            if match["host"] == match["players"][0]["player"]:
                stats[f'{smode}.hostwins'] = 1
            else:
                stats[f'{smode}.hostlosses'] = 1
            if match["host"] in [match["players"][0]["player"], match["players"][1]["player"], 
                    match["players"][2]["player"]]:
                stats[f'{smode}.hostpodiums'] = 1
        else:
            try:
                # determine which team host was on
                if match["hostteam"] == match["outcome"]:
                    stats[f'{smode}.hostwins'] = 1
                elif match["outcome"] != 0:
                    stats[f'{smode}.hostlosses'] = 1
            except KeyError:
                pass
        # wins + 1
        stats[f'{smode}.games'] = 1
        # save number of players
        if ffa:
            stats[f'{smode}.players'] = len(match["players"])
        else:
            stats[f'{smode}.players'] = len(match["team1"]) * 2
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

def add_new_maps():
    new_maps = {
            "st mathieu1": "Saint-Mathieu DM",
            "st mathieu2": "Saint-Mathieu DM2",
            "st mathieu3": "Saint-Mathieu DM3",

            "santa lucia1": "Santa Lucia DM",
            "santa lucia2": "Santa Lucia DM2",
            "santa lucia3": "Santa Lucia DM3",

            "tampa1": "Tampa Bay DM",
            "tampa2": "Tampa Bay DM2",
            "tampa3": "Tampa Bay DM3",

            "havana1": "Havana DM",
            "havana2": "Havana DM2",
            "havana3": "Havana DM3",

            "kingston1": "Kingston DM",
            "kingston2": "Kingston DM2",
            "kingston3": "Kingston DM3",

            "palenque1": "Palenque DM",
            "palenque2": "Palenque DM2",
            "palenque3": "Palenque DM3",

            "portobelo1": "Portobelo DM",
            "portobelo2": "Portobelo DM2",
            "portobelo3": "Portobelo DM3",

            "prison1": "Prison DM",
            "prison2": "Prison DM2",
            "prison3": "Prison DM3",

            "plantation1": "Virginian Plantation DM",
            "plantation2": "Virginian Plantation DM2",
            "plantation3": "Virginian Plantation DM3",

            "saba1": "Saba Island DM",
            "saba2": "Saba Island DM2",
            "saba3": "Saba Island DM3",

            "st pierre1": "Saint Pierre DM",
            "st pierre2": "Saint Pierre DM2",
            "st pierre3": "Saint Pierre DM3",

            "charlestown1": "Charlestown DM",
            "charlestown2": "Charlestown DM2",
            "charlestown3": "Charlestown DM3"
    }
    db = connect()
    maps_db = db["maps"]
    stats = {}
    base_stats = {"kills": 0, "deaths": 0, "score": 0, "hostwins": 0, "hostlosses": 0, "games": 0, "hostrating": 1000, "players": 0}
    for m in GAME_MODES:
        stats[m] = base_stats
    stats["aa"]["scored"] = 0
    stats["aa"]["hostscored"] = 0

    for m in FFA_MODES:
        stats[m]["hostpodiums"] = 0

    for k in new_maps.keys():
        maps_db.insert_one(dict({"name": identify_map(k)}, **stats))

def add_mode_to_maps(mode):
    if mode not in GAME_MODES:
        raise ValueError("mode not recognized")
    db = connect()
    maps_db = db["maps"]
    stats = {}
    base_stats = {"kills": 0, "deaths": 0, "score": 0, "hostwins": 0, "hostlosses": 0, "games": 0, "hostrating": 1000, "players": 0}    
    stats[mode] = base_stats

    if mode == "aa":
        stats[mode]["scored"] = 0
        stats[mode]["hostscored"] = 0

    if mode in FFA_MODES:
        stats[mode]["hostpodiums"] = 0

    for k in identify_map(get_map_keys=True):
        maps_db.update_one({"name": identify_map(k)}, {"$set": {**stats}})

def remove_maps():
    maps = {
            "st mathieu1": "Saint-Mathieu DM",
            "st mathieu2": "Saint-Mathieu DM2",
            "st mathieu3": "Saint-Mathieu DM3",

            "santa lucia1": "Santa Lucia DM",
            "santa lucia2": "Santa Lucia DM2",
            "santa lucia3": "Santa Lucia DM3",

            "tampa1": "Tampa Bay DM",
            "tampa2": "Tampa Bay DM2",
            "tampa3": "Tampa Bay DM3",

            "havana1": "Havana DM",
            "havana2": "Havana DM2",
            "havana3": "Havana DM3",

            "kingston1": "Kingston DM",
            "kingston2": "Kingston DM2",
            "kingston3": "Kingston DM3",

            "palenque1": "Palenque DM",
            "palenque2": "Palenque DM2",
            "palenque3": "Palenque DM3",

            "portobelo1": "Portobelo DM",
            "portobelo2": "Portobelo DM2",
            "portobelo3": "Portobelo DM3",

            "prison1": "Prison DM",
            "prison2": "Prison DM2",
            "prison3": "Prison DM3",

            "plantation1": "Virginian Plantation DM",
            "plantation2": "Virginian Plantation DM2",
            "plantation3": "Virginian Plantation DM3",

            "saba1": "Saba Island DM",
            "saba2": "Saba Island DM2",
            "saba3": "Saba Island DM3",

            "st pierre1": "Saint Pierre DM",
            "st pierre2": "Saint Pierre DM2",
            "st pierre3": "Saint Pierre DM3",

            "charlestown1": "Charlestown DM",
            "charlestown2": "Charlestown DM2",
            "charlestown3": "Charlestown DM3"
    }
    db = connect()
    maps_db = db["maps"]

    for k in maps.keys():
        maps_db.delete_one(dict({"name": identify_map(k)}))
