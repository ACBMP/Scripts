from pymongo import MongoClient
import eloupdate
import historyupdate
import ranks
import tweet
import botconfig as conf
from datetime import date
from util import *

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
    modes = {"mh": False, "e": False, "aa": False}
    for line in f:
        if line=="#":
            print("No new data to be added")
            return
        else:
            entry_dict={}
            csv_entry=line.split(conf.RAU_SPLIT_TOKEN)

            #new flag
            entry_dict["new"]=True

            #mode
            if csv_entry[0] in ["M", "E", "AA"]:
                entry_dict["mode"] = check_mode(csv_entry[0]).capitalize()
                # the replace is a bit stupid because we use both M and MH for manhunt
                modes[csv_entry[0].lower().replace("m", "mh")] = True
            else:
                print("Error in the \'mode\' field!")
                continue
            #outcome
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
                    temp_dict["player"] = temp_list[0]
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
    return modes

def main():
    """
    Run all scripts necessary for fully adding a new match.
    """
    modes = read_and_update()
    eloupdate.new_matches()
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
    for key in mkeys:
        if modes[key]:
            if key == "aa":
                pass
                #tweet.tweet("aar")
                #tweet.tweet("aad")
            else:
                tweet.tweet(key)

if __name__=="__main__":
    main()
