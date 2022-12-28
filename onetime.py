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


if __name__ == "__main__":
    change_usernames()
