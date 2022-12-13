from util import connect, check_mode
import history

def reset_stats(mode):
    db = connect()
    mmr = 800
#    history = {"dates": [], "mmrs": [800]}
    games = {"total": 0, "won": 0, "lost": 0}
    stats = {"highscore": 0, "kills": 0, "deaths": 0, "totalscore": 0}
    rank = 0
    rankchange = 0
    db.players.update_many({}, {"$set": {f"{mode}mmr": mmr, f"{mode}games": games,
        f"{mode}stats": stats, f"{mode}rank": rank, f"{mode}rankchange": rankchange}})
    print(f"Successfully reset all players' {check_mode(mode)} stats")
    return


def reset_new(first, last, insert=None):
    import pymongo
    if len(insert.keys()) > 1:
        raise ValueError("Only one insert allowed!")
    from bson.objectid import ObjectId
    db = connect()
    first_value = int(first, 16)
    last_value = int(last, 16)
    if insert:
        ins_key = int([*insert][0], 16)
        # reset up until insert id
        for v in range(first_value, last_value + 1):
            db.matches.update_one({"_id": ObjectId(hex(v)[2:])}, {"$set": {"new": True}})
        # reset all after insert id
        for v in range(last_value, ins_key - 1, -1):
            db.matches.update_one({"_id": ObjectId(hex(v)[2:])}, {"$set": {"new": True, "_id": ObjectId(hex(v + 1)[2:])}})
        ins_data = insert[[*insert][0]]
        ins_players = [*ins_data]
        ins_data_separated = [{"player": ins_players[i], "score": ins_data[ins_players[i]][0],
            "kills": ins_data[ins_players[i]][1], "deaths": ins_data[ins_players[i]][2]} for i in range(len(ins_players))]
        ins_dict1 = [ins_data_separated[i] for i in range(int(len(ins_players) / 2))]
        ins_dict2 = [ins_data_separated[i] for i in range(int(len(ins_players) / 2), len(ins_players))]
        db.matches.update_one({"_id": ObjectId(hex(ins_key)[2:])}, {"$set": {"team1": ins_dict1, "team2": ins_dict2}})
    else:
        for v in range(first_value, last_value + 1):
            db.matches.update_one({"_id": ObjectId(hex(v)[2:])}, {"$set": {"new": True}})



if __name__ == "__main__":
    reset_stats("e")
    reset_stats("mh")
    reset_stats("aar")
    reset_stats("aad")
    history.update()
#    reset_new("61954c54703aef997af74a47", "61954c54703aef997af74a50",
#            {"61954c54703aef997af74a4c": {"Dellpit": [4200, 5, 6], "Tha Fazz": [3800, 6, 6],
#                "DevelSpirit": [4200, 6, 5], "Ted95On": [3300, 5, 5]}})
