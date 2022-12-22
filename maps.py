from util import *

def _get_stat(match, stat):
    return sum([p[stat] for p in match[f"team{i}"] for i in [1, 2]]),


def update_maps():
    db = connect()
    matches = db.matches.find({"new": True})
    for match in matches:
        smode = check_mode(match["mode"], short=True)
        base_stats = ["kills", "deaths", "score"]
        bs = [_get_stat(match, s) for s in base_stats]
        stats = {k: v for (k, v) in zip(base_stats, bs)}
        if match["mode"] == "Artifact assault":
            stats["scored"] = _get_stat(match, "scored")
        try:
            stats["host"] = int(match["host"] == match["outcome"])
        stats["games"] = 1
        stats[match["mode"]] = 1
        db.maps.update_one({"name": match["map"]}, {"$inc": stats})

    return
