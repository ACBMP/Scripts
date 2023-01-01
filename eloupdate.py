from flask_pymongo import PyMongo
from pymongo import MongoClient
from util import *

class OutcomeError(Exception):
    pass

def E(R):
    """
    Expected win chance based on MMRs.

    :param R: list or tuple containing the two MMRs to compare
    :return: win chance for first MMR in R
    """
    return (1 + 10 ** ((R[1] - R[0]) / 400)) ** -1

def new_R(R, S, E, K=None, N=None, t1=None, t2=None, ref=None):
    """
    Function to calculate new MMR.

    :param R: current MMR
    :param S: outcome; 0 for loss, 1 for win, 0.5 for tie
    :param E: expected win chance
    :param K: max MMR change
              this won't be the actual max change if t1 and t2 are used
    :param N: total number of games played
    :param t1: player's score
    :param t2: opponent's score
    :param ref: reference "stomp" score
    :return: adjusted MMR
    """
    if N > 10:
        if K is None:
            K = Kc(N, R)
        return R + K * (S - E) * (1 + score(t1, t2, ref)) + S # trying to inflate by adding 1 to every win
    else:
        if S == 1:
            return R + 50
        elif S == 0:
            return R - 10
        elif S == .5:
            return R + 20
        else:
            raise ValueError("Broken outcome.")

def Kc(N, R):
    """
    Calculate max MMR change.

    :param N: total number of games played
    :param R: current MMR
    :return: max MMR change
    """
    hi = 1200
    if N < 30 and R < hi:
        return 40
    elif R <= hi:
        return 20
    else: # R > hi
        return 15

def score(t1, t2, ref=None):
    """
    Score difference MMR boost.
    This is used to make sure closer games count less than stomps.

    If no reference score is passed, this will be calculated according to the
    total score of the two teams.

    With a reference score, this is based on the how close to a standard "stomp"
    the score is.

    :param t1: team 1 score
    :param t2: team 2 score
    :param ref: reference score, 0 to return 0
    :return: boost amount
    """
    if ref is None:
        try:
            return abs(t1 - t2) / ((t1 + t2) / 2)
        except ZeroDivisionError:
            return 0
    else:
        # reference stomp value
        try:
            return max(abs(t1 - t2) - 1, 0) / ref
        # bad way to implement no score ref
        except ZeroDivisionError:
            return 0
    
def w_mean(ratings, ratings_o):
    """
    Weighted arithmetic mean.
    Weights are calculated based on players' MMRs compared to the opposing
    team's.

    :param ratings: team ratings to be weighted
    :param ratings_o: opposing team's ratings
    :return: weighted mean of ratings, weights used
    """
    mean = sum(ratings_o) / len(ratings_o)
    diffs = []
    for r in ratings:
        diffs.append(abs(r - mean))
    weights = []
    for d in diffs:
        try:
            weights.append(d / sum(diffs))
        except ZeroDivisionError:
            weights.append(0)
    w_sum = sum(weights)
    if w_sum == 0:
        w_sum = len(ratings)
        weights = [1] * len(ratings)
    return sum([ratings[_] * weights[_] for _ in range(len(ratings))]) / sum(weights), weights


def team_ratings(match, team_1, team_2, outcome, score_1, score_2, aa=False, ref=None):
    """
    Calculate new ratings for all players in a match.

    :param match: match as a dict as given by readandupdate
    :param team_1: list of player dicts for team 1
    :param team_2: list of player dicts for team 2
    :param outcome: match outcome, 0 for team 1 winning, 1 for team 2, 0.5 tie
    :param score_1: team 1's score
    :param score_2: team 2's score
    :param aa: artifact assault switch
    :param ref: set reference stomp value
    :return: list of dicts containing names and new MMRs
    """

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
        for i in range(l):
            role = match["team1"][i]["role"]
            R_old_1.append(team_1[i][f"aa{role}mmr"])
            role = match["team2"][i]["role"]
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
                    "mmr": new_R(
                        R=teams[j][i][f"{mode}mmr"] if not aa else teams[j][i][f"aa{match[f'team{j + 1}'][i]['role']}mmr"],
                        S=S[j],
                        E=Es[j],
                        N=(teams[j][i][f"{mode}games" if not aa else f"aa{match[f'team{j + 1}'][i]['role']}games"]["total"] + 1),
                        t1=score_1, t2=score_2,
                        ref=4 if aa else ref
                        )
                    })
            if aa:
                result[-1]["role"] = match[f'team{j + 1}'][i]['role']
    # if host data is given update those
    try:
        db = connect()
        map_db = db.maps.find_one({"name": match["map"]})
        db.maps.update_one({"name": match["map"]}, {"$set": {f"{mode}.hostrating":
            new_R(
                R=map_db[mode]["hostrating"],
                S=S[match["hostteam"] - 1],
                E=Es[match["hostteam"] - 1],
                N=map_db[mode]["games"] + 10,
                t1=score_1, t2=score_2,
                ref=4 if aa else ref
                )
            }})
    except KeyError:
        pass

    return result


def new_matches():
    """
    Parse new matches in the database and update MMRs accordingly.
    """
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
        if m["mode"] == "Artifact assault":
            score_key += "d"

            kds = [{}, {}]
            for team in [1, 2]:
                # find kd for every player in team
                for p in m[f"team{team}"]:
                    try:
                        kds[team - 1][p["player"]] = p["kills"] / p["deaths"]
                    except ZeroDivisionError:
                        kds[team - 1][p["player"]] = 1000 # easier than inf I think
                # sort the kds, this creates a list of tuples
                kds[team - 1] = sorted(kds[team - 1].items(), key=lambda x: x[1])
                # highest kds are defenders
                role = "r"
                # go through every player
                for i in range(len(m[f"team{team}"])):
                    if i > 1:
                        role = "d"
                    # set role value on match 
                    found = False
                    j = 0
                    # go thru players until we find the right player
                    while not found:
                        if m[f"team{team}"][j]["player"] == kds[team-1][i][0]:
                            m[f"team{team}"][j]["role"] = role
                            found = True
                        j += 1

        i = 0
        for team in [1, 2]:
            for player in m[f"team{team}"]:
                temp_ = identify_player(db, player["player"])
                t[team - 1].append(temp_)
                s[team - 1] += m[f"team{team}"][i][score_key]
                if m["mode"] in ["Escort", "Manhunt"]:
                    R_team[team - 1] += temp_[f"{check_mode(m['mode'], short=True)}mmr"]
                elif m["mode"] == "Artifact assault":
                    R_team[team - 1] += temp_[f"{check_mode(m['mode'], short=True)}{role}mmr"]
                i += 1
            i = 0

        # sanity check
        if m["mode"] != "Domination":
            if m["outcome"] > 0:
                if s[m["outcome"] - 1] < s[m["outcome"] % 2]:
                    raise OutcomeError(f"outcome {m['outcome']} contradicts scoreline: Winner: {s[m['outcome'] - 1]}, Loser: {s[m['outcome'] % 2]}")
            elif s[0] != s[1]:
                raise OutcomeError("outcome 0 contradicts scoreline: {s[0]} - {s[1]}")

        # disable reference stomp for domination since points don't matter there and we don't currently check the bar
        if m["mode"] == "Domination":
            ref = 0
        else:
            ref = None

        result = team_ratings(match=m, team_1=t[0], team_2=t[1], outcome=m["outcome"], score_1=s[0], score_2=s[1], aa=m["mode"] == "Artifact assault", ref=ref)
        
        #Updating: mmr, total games played, wins/losses, total score, kills, deaths, check highscore
        
        team_stat = [[0, 0], [0, 0]]
        if m["outcome"] == 1:
            team_stat = [[1, 0], [0, 1]]
        elif m["outcome"] == 2:
            team_stat = [[0, 1], [1, 0]]

        #Updating the relevant MMR
        if m["mode"] in ["Escort", "Manhunt", "Domination"]:
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
                    player_db = identify_player(db, player_["player"])
                    db.players.update_one(
                            {"_id": player_db["_id"]},
                            {"$inc": {
                                f"{mode}games.total": 1,
                                f"{mode}games.won": team_x_stat[0],
                                f"{mode}games.lost": team_x_stat[1],
                                f"{mode}stats.totalscore": player_["score"],
                                f"{mode}stats.kills": player_["kills"],
                                f"{mode}stats.deaths": player_["deaths"]
                                }}
                            )
    
    
                    # hack please remove
                    try:
                        if player_db[f"{mode}stats"]["highscore"] < player_["score"]:
                            db.players.update_one(
                                    {"_id": player_db["_id"]},
                                    {"$set": {f"{mode}stats.highscore": player_["score"]}}
                                    )
                    except:
                        db.players.update_one(
                                {"_id": player_db["_id"]},
                                {"$set": {f"{mode}stats.highscore": player_["score"]}}
                                )


        elif m["mode"] == "Artifact assault":
            mode = check_mode(m["mode"], short=True)

            concededs = [sum([p["scored"] for p in m[f"team{team}"]]) for team in [2, 1]]
            for team in [1, 2]:
                team_x_stat = team_stat[team - 1]
                for player_ in m[f"team{team}"]:
                    role = player_["role"]
                    name = identify_player(db, player_["player"])["name"]
                    db.players.update_one(
                            {"name": name},
                            {"$inc": {
                                f"{mode}{role}games.total": 1,
                                f"{mode}{role}games.won": team_x_stat[0],
                                f"{mode}{role}games.lost": team_x_stat[1],
                                f"{mode}{role}stats.totalscore": player_["score"],
                                f"{mode}{role}stats.kills": player_["kills"],
                                f"{mode}{role}stats.deaths": player_["deaths"],
                                f"{mode}{role}stats.conceded": concededs[team - 1],
                                f"{mode}{role}stats.scored": player_["scored"]
                                }}
                            )

            for resultentry in result:
                db.players.update_one(
                        {"name": resultentry["name"]},
                        {"$set": {
                            f"{mode}{resultentry['role']}mmr":
                            resultentry["mmr"]
                            }}
                        )
       
        db.matches.update_one({"_id":m["_id"]},{"$set":{"new":False}})
        print("Match updated successfully!")

    
    return

if __name__=="__main__":
    new_matches()
