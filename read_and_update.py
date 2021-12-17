from pymongo import MongoClient
import eloupdate
import historyupdate
import ranks
import tweet
import botconfig as conf
from util import *

def read_and_update():
    client = MongoClient('mongodb://localhost:27017/')
    db = client.public
    f = open(conf.RAU_FILE_PATH + conf.RAU_FILE_NAME,'r')
    # keep track of whether a mode was played
    modes = {"mh": False, "e": False}
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
#                modes[check_mode(csv_entry[0], short=True)] = True
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
                entry_dict[team_n] = {}
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
    modes = read_and_update()
    eloupdate.new_matches()
    historyupdate.update()
    ranks.main()
    tweet.tweet("e")
#    for key in modes.keys():
#        if modes[key]:
#            tweet.tweet(key)

if __name__=="__main__":
    main()
