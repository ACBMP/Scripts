from util import *

def worst_game(mode):
    db = connect()
    def algo(p):
        try:
            return p["score"] / p["deaths"] #* p["kills"]
        except ZeroDivisionError:
            return 10000000
    matches = db.matches.find({"mode": mode})
    winner = None
    loser = None
    for m in matches:
        for p in m["team1"]:
            if winner is None:
                winner = (p, algo(p))
            else:
                if algo(p) < winner[1]:
                    winner = (p, algo(p))
        for p in m["team2"]:
            if loser is None:
                loser = (p, algo(p))
            else:
                if algo(p) < loser[1]:
                    loser = (p, algo(p))
    print(f"The most carried scoreline was by {winner[0]['player']}: {winner[0]['score']} points with {winner[0]['kills']} kills and {winner[0]['deaths']} deaths.")
    print(f"The worst scoreline was by {loser[0]['player']}: {loser[0]['score']} points with {loser[0]['kills']} kills and {loser[0]['deaths']} deaths.")

    return None


def best_avg(mode, stat):
    db = connect()
    matches = db.matches.find({"mode": mode})
    stats = {}
    games = {}
    for m in matches:
        for i in [1, 2]:
            for p in m[f"team{i}"]:
                player = identify_player(db, p["player"])["name"]
                try:
                    stats[player] += p[stat]
                    games[player] += 1
                except:
                    stats[player] = p[stat]
                    games[player] = 1

    other = {}
    for k in stats.keys():
        other[stats[k] / games[k]] = k
    sort = sorted(other)
    for k in sort:
        print(f"{other[k]}: {k} average {stat}s ({stats[other[k]]} {stat}, {games[other[k]]} games)")
    return


def most_games(mode=None):
    db = connect()
    if mode:
        matches = db.matches.find({"mode": mode})
    else:
        matches = db.matches.find()
    stats = {}
    for m in matches:
        for i in [1, 2]:
            for p in m[f"team{i}"]:
                player = identify_player(db, p["player"])["name"]
                try:
                    stats[player] += 1
                except:
                    stats[player] = 1
    other = {}
    for k in stats.keys():
        try:
            other[stats[k]] += ", " + k
        except:
            other[stats[k]] = k
    sort = sorted(other)[::-1]
    i = 1
    for k in sort:
        print(f"{i}. {k} game(s): {other[k]}")
        i += 1
    return


def stomp(mode="Manhunt"):
    db = connect()
    matches = db.matches.find({"mode": mode})
    diff = [0, None]
    for m in matches:
        scores = [0, 0]
        for i in [1, 2]:
            for p in m[f"team{i}"]:
                scores[i - 1] += p["score"]
        temp = abs(scores[0] - scores[1])
        if temp > 30000:
            continue
        if temp > diff[0]:
            diff = [temp, m]
    print(diff)
    return


def countries():
    db = connect()
    players = db.players.find()
    cd = {}
    for p in players:
        try:
            cd[p["nation"]] += 1
        except:
            cd[p["nation"]] = 1
    for k in cd.keys():
        print(f":flag_{k.lower()}:: {cd[k]}")
    return


def average_elos():
    import numpy as np
    db = connect()
    for mode in ["e", "mh", "aar", "aad", "do"]:
        players = db.players.find({f"{mode}games.total": {"$gte": 1}})
        elos = [p[f"{mode}mmr"] for p in players]
        print(check_mode(mode).title(), "average elo:", np.mean(elos), "| number of players:", len(elos))
    return

if __name__ == "__main__":
    average_elos()
    #most_games("Manhunt")
    #countries()
    #stomp("Escort")
#    most_games("Artifact assault")
    #best_avg("Manhunt", "deaths")
    #worst_game("Escort")
