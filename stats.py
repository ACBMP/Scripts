from util import *
import numpy as np

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
        print(f"{other[k]}: {round(k, 2)} average {stat}s ({round(stats[other[k]], 2)} {stat}, {games[other[k]]} games)")
    return


def points_per_stat(mode, stat="kills"):
    db = connect()
    matches = db.matches.find({"mode": mode})
    stats = {}
    games = {}
    for m in matches:
        for i in [1, 2]:
            for p in m[f"team{i}"]:
                player = identify_player(db, p["player"])["name"]
                try:
                    s = p["score"] / p[stat]
                except ZeroDivisionError:
                    continue
                if player in stats:
                    stats[player] += s
                    games[player] += 1
                else:
                    stats[player] = s
                    games[player] = 1

    other = {}
    for k in stats.keys():
        other[stats[k] / games[k]] = k
    sort = sorted(other)
    for k in sort:
        if games[other[k]] >= 10:
            print(f"{other[k]}: {round(k, 2)} average points per {stat} ({games[other[k]]} games)")
    return

def score_per_round(kills, per_5, streak):
    return kills * (per_5 - streak) / 5 + streak * (kills // 5)

def approx_round_score(mode="Manhunt", avg_score=lambda k: score_per_round(k, 3000, 750), roundname="def", games_thr=100):
    db = connect()
    matches = db.matches.find({"mode": mode})
    stats = {}
    games = {}
    for m in matches:
        for i in [1, 2]:
            for p in m[f"team{i}"]:
                player = identify_player(db, p["player"])["name"]
                s = p["score"] - avg_score(p["kills"])
                if player in stats:
                    stats[player] += s
                    games[player] += 1
                else:
                    stats[player] = s
                    games[player] = 1

    other = {}
    for k in stats.keys():
        other[stats[k] / games[k]] = k
    sort = sorted(other)
    for k in sort:
        if games[other[k]] >= games_thr:
            print(f"{other[k]}: {round(k, 2)} avg approx {roundname} ({games[other[k]]} games)")
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


def most_games_stat(mode=None, stat="kills", check=lambda x: x >= 10):
    print(f"{stat}")
    db = connect()
    if mode:
        matches = db.matches.find({"mode": mode})
    else:
        matches = db.matches.find()
    stats = {}
    games = {}
    j = 0
    for m in matches:
        j += 1
        for i in [1, 2]:
            for p in m[f"team{i}"]:
                player = identify_player(db, p["player"])["name"]
                if player in games:
                    games[player] += 1
                else:
                    games[player] = 1
                if check(p[stat]):
                #    print(m)
                    if player in stats:
                        stats[player] += 1
                    else:
                        stats[player] = 1
    print(f"Total {mode} games: {j}")
    other = {}
    for k in stats.keys():
        try:
            other[stats[k]] += [k]
        except:
            other[stats[k]] = [k]
    sort = sorted(other)[::-1]
    i = 1
    for k in sort:
        print(f"{i}. {k} game(s): {', '.join(other[k])} ({', '.join([str(round(k / games[i] * 100, 2)) + '%' for i in other[k]])})")
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


def lobby_score(mode, games_thr = 100):
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
        scores = [0, 0]
        for i in [1, 2]:
            scores[i - 1] += np.sum([p["score"] for p in m[f"team{i}"]])
        s = abs(scores[0] - scores[1])
        for i in [1, 2]:
            for p in m[f"team{i}"]:
                player = identify_player(db, p["player"])["name"]
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
        if games[k] >= games_thr:
            try:
                other[stats[k]] += ", " + k + f" ({games[k]} games)"
            except:
                other[stats[k]] = k + f" ({games[k]} games)"
    sort = sorted(other)[::-1]
    i = 1
    for k in sort:
        print(f"{i}. {round(k, 3)} {mode} average score diff: {other[k]}")
        i += 1
    return


def lobby_mmr(mode, games_thr = 100):
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
                mmrs = []
                player = identify_player(db, p["player"])["name"]
                for k in [1, 2]:
                    for p_except in m[f"team{k}"]:
                        # if p_except != p:
                            # mmrs.append(identify_player(db, p_except["player"])[f"{check_mode(mode, short=True)}mmr"])
                        mmrs.append(identify_player(db, p_except["player"])[f"{check_mode(mode, short=True)}mmr"])
                s = np.std(mmrs)
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
        if games[k] >= games_thr:
            try:
                other[stats[k]] += ", " + k + f" ({games[k]} games)"
            except:
                other[stats[k]] = k + f" ({games[k]} games)"
    sort = sorted(other)[::-1]
    i = 1
    for k in sort:
        print(f"{i}. {round(k, 3)} {mode} lobby MMR standard deviation: {other[k]}")
        i += 1
    return


def lobby_number_games(mode, games_thr = 100):
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
                mmrs = []
                player = identify_player(db, p["player"])["name"]
                for k in [1, 2]:
                    for p_except in m[f"team{k}"]:
                        if p_except != p:
                            mmrs.append(identify_player(db, p_except["player"])[f"{check_mode(mode, short=True)}games"]["total"])
                        # mmrs.append(identify_player(db, p_except["player"])[f"{check_mode(mode, short=True)}games"]["total"])
                s = any([i <= games_thr for i in mmrs])# np.mean(mmrs)
                if player in games:
                    games[player] += 1
                    stats[player] += s
                else:
                    games[player] = 1
                    stats[player] = s
    # for k, v in stats.items():
    #     stats[k] = v / games[k]
    print(f"Total {mode} games: {j}")
    other = {}
    for k in stats.keys():
        if games[k] >= games_thr:
            try:
                other[stats[k]] += ", " + k + f" ({games[k]} games)"
            except:
                other[stats[k]] = k + f" ({games[k]} games)"
    sort = sorted(other)[::-1]
    i = 1
    for k in sort:
        print(f"{i}. {round(k, 3)} {mode} games with new player(s): {other[k]}")
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
    # lobby_mmr("Manhunt")
    lobby_score("Manhunt")
    # lobby_number_games("Escort", 200)
    # approx_round_score("Manhunt")
    # approx_round_score("Escort", lambda k: score_per_round(k, 2000, 250), "offense")
#    points_per_stat("Escort", "kills")
    #most_games_stat("Escort", "kills", check=lambda x: x >= 8)
    #most_games_stat("Manhunt", stat="deaths", check=lambda x: x < 5)
    # team_streaks_avg("Escort")
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
