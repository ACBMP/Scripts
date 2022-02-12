from util import *
import re

def find_games(db, name, mode):
    data = identify_player(db, name)
    # load and search for all igns plus name so we don't get empty match histories
    igns = data["ign"]
    if type(igns) == str:
        igns = [igns]
    igns += [name]
    # we only need to find matches where the player was on the winning team
    search = [{"team1":{"$elemMatch":{"player":ign}}} for ign in igns]
    search += [{"team2":{"$elemMatch":{"player":ign}}} for ign in igns]
    matches = db.matches.find({"$and": [{"$or": search}, {"mode": mode}]})
    return matches, igns


def parse_matches(db, matches, name, min_games, track_teams=False):
    # dict with [games played, wins] for [opponents, teammates]
    dicts = [{}, {}]
    for m in matches:
        for i in [1, 2]:
            team = m[f"team{i}"]
            players = []
            for player in team:
                player = player["player"]
                player = identify_player(db, player)["name"]
                players.append(player)
            # check whether player is on team
            d = 0
            for ign in name:
                if ign.lower() in [p.lower() for p in players]:
                    d = 1
            if track_teams:
                players = ", ".join(sorted(players))
                if m["outcome"] == 0:
                    try:
                        dicts[d][players] = [dicts[d][players][0] + 1, dicts[d][players][1], dicts[d][players][2] + 1]
                    except:
                        dicts[d][players] = [1, 0, 1]
                elif i == m["outcome"]:
                    try:
                        dicts[d][players] = [dicts[d][players][0] + 1, dicts[d][players][1] + 1, dicts[d][players][2]]
                    except:
                        dicts[d][players] = [1, 1, 0]
                else:
                    try:
                        dicts[d][players] = [dicts[d][players][0] + 1, dicts[d][players][1], dicts[d][players][2]]
                    except:
                        dicts[d][players] = [1, 0, 0]
            else:
                for j in range(len(players)):
                    if m["outcome"] == 0:
                        try:
                            dicts[d][players[j]] = [dicts[d][players[j]][0] + 1, dicts[d][players[j]][1], dicts[d][players[j]][2] + 1]
                        except:
                            dicts[d][players[j]] = [1, 0, 1]
                    elif i == m["outcome"]:
                        try:
                            dicts[d][players[j]] = [dicts[d][players[j]][0] + 1, dicts[d][players[j]][1] + 1, dicts[d][players[j]][2]]
                        except:
                            dicts[d][players[j]] = [1, 1, 0]
                    else:
                        try:
                            dicts[d][players[j]] = [dicts[d][players[j]][0] + 1, dicts[d][players[j]][1], dicts[d][players[j]][2]]
                        except:
                            dicts[d][players[j]] = [1, 0, 0]
    sorted_dicts = [{}, {}]
    for d in range(len(dicts)):
        for player in dicts[d]:
            # make sure min games played
            if dicts[d][player][0] >= min_games:
                sorted_dicts[d][player] = [dicts[d][player][1] / dicts[d][player][0], dicts[d][player][0], dicts[d][player][1], dicts[d][player][2]]
        sorted_dicts[d] = dict(sorted(sorted_dicts[d].items(), key=lambda item: item[1][0], reverse=True))
    return sorted_dicts


def dict_string(d):
    val = ""
    for item in d:
        val += f"{item}: {round(d[item][0] * 100)}% ({d[item][2]} / {d[item][1]} | {d[item][3]} ties)\n"
    return val


def find_synergy(name, mode="Manhunt", min_games=25, track_teams=False):
    db = connect()
    games, igns = find_games(db, name, mode)
    results = parse_matches(db, games, igns, min_games, track_teams)
    return dict_string(results[1]), dict_string(results[0])

if __name__ == "__main__":
#    find_synergy("Tha Fazz", min_games=5, track_teams=False)
    print("Player: Winrate (Games Won / Tied / Played)")
    for x in ["DevelSpirit", "Sugarfree", "Tha Fazz", "Ted95On", "Dellpit"]:
        print("Finding synergy for:", x)
        synergies = find_synergy(x, "Escort", min_games=5)
        print("Top teammates:")
        print(synergies[0])
        print("Top opponents:")
        print(synergies[1])
