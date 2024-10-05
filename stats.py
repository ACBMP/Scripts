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
    j = 0
    for m in matches:
        j += 1
        for i in [1, 2]:
            for p in m[f"team{i}"]:
                player = identify_player(db, p["player"])["name"]
                try:
                    stats[player] += 1
                except:
                    stats[player] = 1
    print(f"Total {mode} games: {j}")
    other = {}
    for k in stats.keys():
        try:
            other[stats[k]] += ", " + k
        except:
            other[stats[k]] = k
    sort = sorted(other)[::-1]
    i = 1
    for k in sort:
        print(f"{i}. {k} game(s): {other[k]} ({round(k / j * 100, 2)}%)")
        i += 1
    return


def team_avg(stat, mode=None):
    db = connect()
    if mode:
        matches = db.matches.find({"mode": mode})
    else:
        matches = db.matches.find()
    games = {}
    stats = {}
    j = 0
    for m in matches:
        j += 1
        for i in [1, 2]:
            for p in m[f"team{i}"]:
                player = identify_player(db, p["player"])["name"]
                s = 0
                for p_except in m[f"team{i}"]:
                    if p_except != p:
                        s += p_except[stat]
                s /= len(m[f"team{i}"]) - 1
                if player in games:
                    games[player] += 1
                    stats[player] += s
                else:
                    games[player] = 1
                    stats[player] = s
    for k, v in stats.items():
        stats[k] = v / games[k]
    print(f"Total {mode} games: {j}")
    other = {}
    for k in stats.keys():
        try:
            other[stats[k]] += ", " + k + f" ({games[k]} games)"
        except:
            other[stats[k]] = k + f" ({games[k]} games)"
    sort = sorted(other)[::-1]
    i = 1
    for k in sort:
        print(f"{i}. {round(k, 3)} teammate average {stat}: {other[k]}")
        i += 1
    return


def team_streaks_avg(mode=None, opponents=False):
    db = connect()
    if mode:
        matches = db.matches.find({"mode": mode})
    else:
        matches = db.matches.find()
    games = {}
    stats = {}
    j = 0
    for m in matches:
        j += 1
        for i in [1, 2]:
            for p in m[f"team{i}"]:
                player = identify_player(db, p["player"])["name"]
                s = 0
                for p_ in m[f"team{i if not opponents else i % 2 + 1}"]:
                    s += p_["kills"] // 5
                try:
                    games[player] += 1
                    stats[player] += s
                except:
                    games[player] = 1
                    stats[player] = s
    for k, v in stats.items():
        stats[k] = v / games[k]
    print(f"Total {mode} games: {j}")
    other = {}
    for k in stats.keys():
        try:
            other[stats[k]] += ", " + k + f" ({games[k]} games)"
        except:
            other[stats[k]] = k + f" ({games[k]} games)"
    sort = sorted(other)
    if not opponents:
        sort = sort[::-1]
    i = 1
    st = "opponents" if opponents else "team"
    for k in sort:
        print(f"{i}. {round(k, 3)} {st} average streaks: {other[k]}")
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
    for mode in ALL_MODES:
        players = db.players.find({f"{mode}games.total": {"$gte": 1}})
        elos = [p[f"{mode}mmr"] for p in players]
        print(check_mode(mode).title(), "average elo:", np.mean(elos), "| number of players:", len(elos))
    return


def team_winrate(mode="Escort"):
    db = connect()
    n = db.matches.find({"mode": mode, "corrected": True}).count()
    for t in [1, 2]:
        w = db.matches.find({"mode": mode, "corrected": True, "outcome": t}).count()
        print(f"Team {t} win rate: {round(w / n * 100)}% ({w}/{n})")
    return


def team_winrate_map(m, mode="Escort"):
    db = connect()
    n = db.matches.find({"mode": mode, "corrected": True, "map": m}).count()
    for t in [1, 2]:
        w = db.matches.find({"mode": mode, "corrected": True, "outcome": t, "map": m}).count()
        print(f"Team {t} win rate: {round(w / n * 100)}% ({w}/{n})")
    return

if __name__ == "__main__":
    team_streaks_avg("Escort")
    # team_streaks_avg("Escort", True)
    # team_avg("kills", "Escort")
    #team_winrate()
    # most_games("Escort")
    # most_games("Manhunt")
    # most_games("Domination")
    # most_games("Artifact assault")
    #countries()
    #stomp("Escort")
#    most_games("Artifact assault")
    #best_avg("Manhunt", "deaths")
    #worst_game("Escort")
