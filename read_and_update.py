from pymongo import MongoClient
import eloupdate
import eloupdate_ffa
import historyupdate
import ranks
import tweet
import botconfig as conf
from datetime import date
from util import *
import maps

def read_and_update():
    """
    Read and update the new matches file defined in botconfig.

    Matches must be formatted as follows:
    MODE, PLAYERS PER TEAM, WINNING TEAM, PLAYER NAME$SCORE$KILLS$DEATHS, ...

    With one line per match.
    """
    client = MongoClient('mongodb://localhost:27017/')
    db = client.public
    today = date.today().strftime("%Y-%m-%d")
    f = open(conf.RAU_FILE_PATH + conf.RAU_FILE_NAME,'r')
    # keep track of whether a mode was played
    mode_tracker = {k:False for k in GAME_MODES}

    for line in f:
        if line=="#":
            print("No new data to be added")
            return mode_tracker
        else:
            entry_dict={}
            csv_entry=line.split(conf.RAU_SPLIT_TOKEN)

            #new flag
            entry_dict["new"]=True
            # inhist flag
            entry_dict["inhist"] = False
            host_player = None

            # save map/host
            if "$" in csv_entry[0]:
                temp = csv_entry[0].split("$")
                csv_entry[0] = temp[0]
                if len(temp) == 3:
                    entry_dict["map"] = identify_map(temp[1])
                    entry_dict["host"] = identify_player(db, temp[2])["name"]
                    host_player = entry_dict["host"]
                else:
                    # check if either a map or player can be identified
                    try:
                        entry_dict["map"] = identify_map(temp[1])
                    except:
                        try:
                            entry_dict["host"] = identify_player(db, temp[2])["name"]
                            host_player = entry_dict["host"]
                        except:
                            raise ValueError("Could not identify host or map!")

            #mode
            try:
                mode = check_mode(csv_entry[0])
                smode = check_mode(csv_entry[0], short=True)
                entry_dict["mode"] = mode.capitalize()
                mode_tracker[smode] = True
            except ValueError:
                print("Error in the \'mode\' field!")
                continue
            #outcome
            if check_mode(entry_dict["mode"], short=True) in FFA_MODES:
                csv_entry.pop(0)
                entry_dict["players"] = []
                for entry in csv_entry:
                    temp_dict = {}
                    temp_list = entry.split(conf.RAU_SECONDARY_TOKEN)
                    temp_dict["player"] = identify_player(db, temp_list[0])["name"]
                    if host_player and temp_dict["player"] == host_player:
                        temp_dict["host"] = True
                    temp_dict["score"] = int(temp_list[1])
                    temp_dict["kills"] = int(temp_list[2])
                    temp_dict["deaths"] = int(temp_list[3])
                    entry_dict["players"].append(temp_dict)
                entry_dict["players"].sort(key=lambda p: p["score"], reverse=True)
            
            else:
                entry_dict["outcome"]=int(csv_entry[2])
        
                #players
                number_of_players = int(csv_entry[1])
                teams = [[], []]
                for index in range(0, number_of_players):
                    teams[0].append(csv_entry[3 + index])
                for index in range(0, number_of_players):
                    teams[1].append(csv_entry[3 + number_of_players + index])

                for i in range(2):
                    team_n = f"team{i + 1}"
                    entry_dict[team_n] = []
                    for entry in teams[i]:
                        temp_dict = {}
                        temp_list = entry.split(conf.RAU_SECONDARY_TOKEN)
                        temp_dict["player"] = identify_player(db, temp_list[0])["name"]
                        if host_player and temp_dict["player"] == host_player:
                            entry_dict["hostteam"] = i + 1
                        temp_dict["score"] = int(temp_list[1])
                        temp_dict["kills"] = int(temp_list[2])
                        temp_dict["deaths"] = int(temp_list[3])
                        if csv_entry[0] == "AA":
                            temp_dict["scored"] = int(temp_list[4])
                        entry_dict[team_n].append(temp_dict)
            
            # add current date
            entry_dict["date"] = today

            #inserting the record into the db
            db.matches.insert_one(entry_dict)
            print("Match entry added!")
    f.close()
    #emptying the file
    f = open(conf.RAU_FILE_PATH + conf.RAU_FILE_NAME,'w')
    f.write("#")
    f.close()
    return mode_tracker

def read_and_edit():
    """
    Read and update the new matches file defined in botconfig.

    Matches must be formatted as follows:
    MODE, PLAYERS PER TEAM, WINNING TEAM, PLAYER NAME$SCORE$KILLS$DEATHS, ...

    With one line per match.
    """
    client = MongoClient('mongodb://localhost:27017/')
    db = client.public
    today = date.today().strftime("%Y-%m-%d")
    f = open(conf.RAU_FILE_PATH + conf.RAE_FILE_NAME,'r')

    for line in f:
        if line=="#":
            print("No new data to be added")
        else:
            entry_dict = {}
            csv_entry=line.split(conf.RAU_SPLIT_TOKEN)

            #new flag
            entry_dict["new"] = False
            host_player = None

            new_dict = {}
            new_data = csv_entry[-1]
            new_data = new_data.replace("\n", "")
            swap = False
            for d in new_data.split("#"):
                if d == "swap":
                    swap = True
                    continue
                try:
                    k, v = d.split(": ")
                except:
                    print(d)
                if k == "map":
                    v = identify_map(v)
                new_dict[k] = v
            csv_entry.pop(-1)

            # save map/host
            if "$" in csv_entry[0]:
                temp = csv_entry[0].split("$")
                csv_entry[0] = temp[0]
                if len(temp) == 3:
                    entry_dict["map"] = identify_map(temp[1])
                    entry_dict["host"] = identify_player(db, temp[2])["name"]
                    host_player = entry_dict["host"]
                else:
                    # check if either a map or player can be identified
                    try:
                        entry_dict["map"] = identify_map(temp[1])
                    except:
                        try:
                            entry_dict["host"] = identify_player(db, temp[2])["name"]
                            host_player = entry_dict["host"]
                        except:
                            raise ValueError("Could not identify host or map!")

            #mode
            mode = check_mode(csv_entry[0])
            smode = check_mode(csv_entry[0], short=True)
            entry_dict["mode"] = mode.capitalize()
            #outcome
            if check_mode(entry_dict["mode"], short=True) in FFA_MODES:
                csv_entry.pop(0)
                entry_dict["players"] = []
                for entry in csv_entry:
                    temp_dict = {}
                    temp_list = entry.split(conf.RAU_SECONDARY_TOKEN)
                    temp_dict["player"] = identify_player(db, temp_list[0])["name"]
                    if host_player and temp_dict["player"] == host_player:
                        temp_dict["host"] = True
                    temp_dict["score"] = int(temp_list[1])
                    temp_dict["kills"] = int(temp_list[2])
                    temp_dict["deaths"] = int(temp_list[3])
                    entry_dict["players"].append(temp_dict)
                entry_dict["players"].sort(key=lambda p: p["score"], reverse=True)
            
            else:
                entry_dict["outcome"]=int(csv_entry[2])
        
                #players
                number_of_players = int(csv_entry[1])
                teams = [[], []]
                for index in range(0, number_of_players):
                    teams[0].append(csv_entry[3 + index])
                for index in range(0, number_of_players):
                    teams[1].append(csv_entry[3 + number_of_players + index])

                for i in range(2):
                    team_n = f"team{i + 1}"
                    entry_dict[team_n] = []
                    for entry in teams[i]:
                        temp_dict = {}
                        temp_list = entry.split(conf.RAU_SECONDARY_TOKEN)
                        temp_dict["player"] = identify_player(db, temp_list[0])["name"]
                        if host_player and temp_dict["player"] == host_player:
                            entry_dict["hostteam"] = i + 1
                        temp_dict["score"] = int(temp_list[1])
                        temp_dict["kills"] = int(temp_list[2])
                        temp_dict["deaths"] = int(temp_list[3])
                        if csv_entry[0] == "AA":
                            temp_dict["scored"] = int(temp_list[4])
                        entry_dict[team_n].append(temp_dict)

            # find match so we can swap teams too
            old = db.matches.find_one(entry_dict)
            print(entry_dict)
            if old is None:
                raise ValueError(f"Match {csv_entry} not found!")
            if swap:
                if old["outcome"] == 1:
                    new_dict["outcome"] = 2
                elif old["outcome"] == 2:
                    new_dict["outcome"] = 1
                new_dict["team1"] = old["team2"]
                new_dict["team2"] = old["team1"]
            # update the record in the db
            db.matches.update_one({"_id": old["_id"]}, {"$set": new_dict})
            db.matches.update_one({"_id": old["_id"]}, {"$set": {"corrected": True}})
            if "map" in new_dict:
                db.matches.update_one({"_id": old["_id"]}, {"$set": {"new": True}})
                maps.update_maps()
                db.matches.update_one({"_id": old["_id"]}, {"$set": {"new": False}})
            if "host" in new_dict:
                if new_dict["host"] in new_dict["team1"].values():
                    new_dict["hostteam"] = 1
                else:
                    new_dict["hostteam"] = 2
            print("Match entry updated!")
    f.close()
    #emptying the file
    f = open(conf.RAU_FILE_PATH + conf.RAE_FILE_NAME,'w')
    f.write("#")
    f.close()
    return 


def main():
    """
    Run all scripts necessary for fully adding a new match.
    """
    modes = read_and_update()
    maps.update_maps()
    eloupdate.new_matches()
    eloupdate_ffa.new_matches()
    historyupdate.update()
    rmodes = []
    mkeys = list(modes.keys())
    for m in mkeys:
        if modes[m]:
            if m == "aa":
                rmodes.append("aar")
                rmodes.append("aad")
            else:
                rmodes.append(m)
    ranks.main(rmodes)
#    for key in mkeys:
#        if modes[key]:
#            if key in ["e", "mh"]:
#                tweet.tweet(key)

if __name__=="__main__":
    main()
