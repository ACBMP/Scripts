from util import *

def insert_leaderboard(name, stats):
    db = connect()
    board = {"name": name, "stats": stats}
    db.vtraining.insert_one(board)
    print("Successfully inserted leaderboard")
    return


def parse_gist(gist):
    result = []
    tables = gist.split("### ")
    for table in tables[1:]:
        temp = {}
        lines = table.split("\n")
        temp["tname"] = lines[0].replace("**", "").lower().title()
        players = []
        for line in lines[4:]:
            data = line[2:-2].split(" | ")
            if data == [""]:
                continue
            player = {
                    "rank": data[0],
                    "name": data[1],
                    "time": data[2],
                    "platform": data[3]
                    }
            players.append(player)
        temp["stats"] = players
        result.append(temp)
    return result


def _str_to_time(time):
    return int(time.replace(":", "").replace(" ", "").replace(".", ""))


def insert_run(course, name, time, platform):
    new_player = {
            "rank": 0,
            "name": name,
            "time": time,
            "platform": platform
            }
    db = connect()
    old = db.vtraining.find_one({"name": course})
    if not old:
        raise ValueError("Could not identify course!")
    # we can just convert time to integer for comparison
    inttime = _str_to_time(time)
    stats = old["stats"]
    oldnames = [stat["name"] for stat in stats]
    for i in range(0, 10):
        p = stats[i]
        ptime = _str_to_time(p["time"])
        if inttime <= ptime:
            new_player["rank"] = p["rank"]
            # check if already in leaderboard - disgusting nesting here
            if name in oldnames:
                # move all down starting at old rank and go until new rank
                for j in range(oldnames.index(name) - 1, i - 1, -1):
                    stats[j]["rank"] = str(int(stats[j]["rank"]) + 1)
                    stats[j + 1] = stats[j]
            else:
                # we can skip the last player
                for j in range(8, i - 1, -1):
                    # we only need to check if their time is lower than the new one
                    if _str_to_time(stats[j]["time"]) > _str_to_time(new_player["time"]):
                        stats[j]["rank"] = str(j + 2)
                    stats[j + 1] = stats[j]
            stats[i] = new_player
            db.vtraining.update_one({"name": course}, {"$set": {"stats": stats}})
            print("Successfully inserted new run")
            return


def fix_platform(names, platform):
    db = connect()
    for course in db.vtraining.find():
        stats = course["stats"]
        for i in range(0, len(stats)):
            if stats[i]["name"] in names:
                stats[i]["platform"] = platform
        db.vtraining.update_one({"name": course["name"]}, {"$set": {"stats": stats}})
    return


def fix_by_rank(course, name, time, platform, rank):
    db = connect()
    board = db.vtraining.find_one({"name": course})
    stats = board["stats"]
    for i in range(0, 10):
        if stats[i]["rank"] == str(rank):
            stats[i]["name"] = name
            stats[i]["time"] = time
            stats[i]["platform"] = platform
            db.vtraining.update_one({"name": course}, {"$set": {"stats": stats}})
            return
    print("Couldn't find that!")
    return


def fix_by_name(course, name, time, platform, rank):
    db = connect()
    board = db.vtraining.find_one({"name": course})
    stats = board["stats"]
    for i in range(0, 10):
        if stats[i]["name"] == name:
            stats[i]["time"] = time
            stats[i]["platform"] = platform
            if int(stats[i]["rank"]) != rank:
                stats[i]["rank"] = str(rank)
                stats = sorted(stats, key=lambda x: int(x["rank"]))
            db.vtraining.update_one({"name": course}, {"$set": {"stats": stats}})
            return
    print("Couldn't find that!")
    return


if __name__ == "__main__":
    insert_run("Short Course 1", "Ted95On", "0:27:58", "PC")
    #with open("virtualtrainingtimes.md", "r") as f:
    #    gist = f.read()
    #    
    #result = parse_gist(gist)
    #for r in result:
    #    insert_leaderboard(r["tname"], r["stats"])

