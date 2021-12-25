from flask_pymongo import PyMongo
from pymongo import MongoClient
from util import *

def E(R):
    return (1 + 10 ** ((R[1] - R[0]) / 400)) ** -1

def R_1v1(R, S, K=None, N=1):
    if K is None:
        K = Kc(N, R[0])
    return R[0] + K * (S - E(R))

def new_R(R, S, E, K=None, N=None, t1=None, t2=None):
    if N > 10:
        if K is None:
            K = Kc(N, R)
        return R + K * (S - E) * (1 + score(t1, t2)) + S # trying to inflate by adding 1 to every win
    else:
        if S == 1:
            return R + 50
        elif S == 0:
            return R - 10
        elif S == .5:
            return R
        else:
            raise ValueError("Broken outcome.")

def Kc(N, R):
    hi = 1200
    if N < 30 and R < hi:
        return 40
    elif R <= hi:
        return 20
    else: # R > hi
        return 15

def score(t1, t2):
    try:
        return abs(t1 - t2) / ((t1 + t2) / 2)
    except ZeroDivisionError:
        return 0
    
def w_mean(rankings, rankings_o):
    mean = sum(rankings_o) / len(rankings_o)
    diffs = []
    for r in rankings:
        diffs.append(abs(r - mean))
    weights = []
    for d in diffs:
        try:
            weights.append(d / sum(diffs))
        except ZeroDivisionError:
            weights.append(0)
    w_sum = sum(weights)
    if w_sum == 0:
        w_sum = len(rankings)
        weights = [1] * len(rankings)
    return sum([rankings[_] * weights[_] for _ in range(len(rankings))]) / sum(weights), weights


def team_ratings(match, team_1, team_2, outcome, score_1, score_2, aa=False):

    # team sizes
    l = len(team_1)
    
    # make sure team_1 and team_2 have same length
    if l != len(team_2):
        raise ValueError("team_1 and team_2 must have the same length!")
    
    # set S value according to outcome
    if outcome == 1:
        S = [1, 0]
    elif outcome == 2:
        S = [0, 1]
    elif outcome == 0:
        S = [.5, .5]
    else:
        raise ValueError("outcome must be 1 for team_1, 2 for team_2, or 0 for a tie!")

    # calculate total rating for each team 
    R_old_1 = []
    R_old_2 = []
    # disgusting
    if aa:
        role = match["team1"]["role"]
        R_old_1.append(team_1[i][f"aa{role}mmr"])
        role = match["team2"]["role"]
        R_old_2.append(team_2[i][f"aa{role}mmr"])
    else:
        mode = check_mode(match["mode"], short=True)
        for i in range(l):
            R_old_1.append(team_1[i][f"{mode}mmr"])
            R_old_2.append(team_2[i][f"{mode}mmr"])

    
    # calculate expected outcome for each team
    E_1 = E([w_mean(R_old_1, R_old_2)[0], w_mean(R_old_2, R_old_1)[0]])
    E_2 = 1 - E_1
    
    result = []
    # update values in database
    teams = [team_1, team_2]
    Es = [E_1, E_2]

    # iterate through number of players per team
    for i in range(l):
        # iterate through both teams
        for j in range(2):
            result.append({
                    "name": teams[j][i]["name"],
                    "mmr": int(round(new_R(
                        R=teams[j][i][f"{mode}mmr"] if not aa else teams[j][i][f"aa{match[f'team{j}][role]}mmr"],
                        S=S[j],
                        E=Es[j],
                        N=(teams[j][i][f"{mode}games"]["total"] + 1),
                        t1=score_1, t2=score_2
                        )))
                    })

    return result


def new_matches():
    #Establishing a connectiong to the db
    client = MongoClient('mongodb://localhost:27017/')
    db = client.public

    #Querying the db about new matches
    matches = db.matches.find({"new":True})
    matches = list(matches)
    #Checking whether there are new matches
    if not matches:
        print("No new matches")
        return

    for i in range(len(matches)):
        m = matches[i]
        t = [[], []]
        s = [0, 0]
        i = 0
        R_team = [0, 0] # team ratings which should be calculated in the loop
        score_key = "score"
        if m["mode"] == "AA":
            score_key += "d"

            kds = {}
            for team in [1, 2]:
                # find kd for every player in team
                for p in m[f"team{team}"]:
                    try:
                        kds[p["player"]] = p["kills"] / p["deaths"]
                    except ZeroDivisionError:
                        kds[p["player"]] = 1000 # easier than inf I think
                # sort the kds, this creates a list of tuples
                kds = sorted(kds[team - 1].items(), key=lambda x: x[1])
                # highest kds are defenders
                role = "d"
                # go through every player
                for i in range(len(m[f"team{team}"])):
                    # set role value on match 
                    m[f"team{team}"][kds[i][0]]["role"] = role
                    if i > 1:
                        role = "r"

        for team in [1, 2]:
            for player in m[f"team{team}"]:
                temp_ = identify_player(db, player["player"])
                t[team - 1].append(temp_)
                s[team - 1] += m[f"team{team}"][i][score_key]
                if m["mode"] in ["Escort", "Manhunt"]:
                    R_team[team - 1] += temp_[f"{check_mode(m['mode'], short=True)}mmr"]
                elif m["mode"] == "AA":
                    R_team[team - 1] += temp_[f"{check_mode(m['mode'], short=True)}{role}mmr"]
                i += 1
            i = 0

        result = team_ratings(match=m, team_1=t[0], team_2=t[1], outcome=m["outcome"], score_1=s[0], score_2=s[1], aa=m["mode"] == "AA")
        
        #Updating: mmr, total games played, wins/losses, total score, kills, deaths, check highscore
        
        team_stat = [[0, 0], [0, 0]]
        if m["outcome"] == 1:
            team_stat = [[1, 0], [0, 1]]
        elif m["outcome"] == 2:
            team_stat = [[0, 1], [1, 0]]

        #Updating the relevant MMR
        if m["mode"] in ["Escort", "Manhunt"]:
            mode = check_mode(m["mode"], short=True)
            for resultentry in result:
                db.players.update_one(
                        {"name": resultentry["name"]},
                        {"$set": {
                            f"{mode}mmr":
                            resultentry["mmr"]
                            }}
                        )

            for team in [1, 2]:
                team_x_stat = team_stat[team - 1]
                for player_ in m[f"team{team}"]:
                    db.players.update_one(
                            {"ign": player_["player"]},
                            {"$inc": {
                                f"{mode}games.total": 1,
                                f"{mode}games.won": team_x_stat[0],
                                f"{mode}games.lost": team_x_stat[1],
                                f"{mode}stats.totalscore": player_["score"],
                                f"{mode}stats.kills": player_["kills"],
                                f"{mode}stats.deaths": player_["deaths"]
                                }}
                            )
    
                    temp_player = db.players.find_one({"ign": player_["player"]})
    
                    if temp_player[f"{mode}stats"]["highscore"] < player_["score"]:
                        db.players.update_one(
                                {"ign": player_["player"]},
                                {"$set": {f"{mode}stats.highscore": player_["score"]}}
                                )

        elif m["mode"] == "Artifact assault":
            # we still have to figure out runners and defenders!
            # otherwise the mode doesn't make sense because we separate stats by role
            mode = check_mode(m["mode"], short=True)

            for team in [1, 2]:
                team_x_stat = team_stat[team - 1]
                for player_ in m[f"team{team}"]:
                    db.players.update_one(
                            {"ign": player_["player"]},
                            {"$inc": {
                                f"{mode}{role}games.total": 1,
                                f"{mode}{role}games.won": team_x_stat[0],
                                f"{mode}{role}games.lost": team_x_stat[1],
                                f"{mode}{role}stats.totalscore": player_["score"],
                                f"{mode}{role}stats.kills": player_["kills"],
                                f"{mode}{role}stats.deaths": player_["deaths"],
                                f"{mode}{role}stats.conceded": player_["conceded"],
                                f"{mode}{role}stats.scored": player_["scored"]
                                }}
                            )

            for resultentry in result:
                db.players.update_one(
                        {"name": resultentry["name"]},
                        {"$set": {
                            f"{mode}mmr":
                            resultentry["mmr"]
                            }}
                        )
       
        db.matches.update_one({"_id":m["_id"]},{"$set":{"new":False}})
        print("Match updated successfully!")

    
    return

if __name__=="__main__":
    new_matches()
