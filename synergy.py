from util import *
import re
from datetime import datetime

def date_convert(date):
    return datetime.strptime(date, "%Y-%m-%d")

def find_games(db, name, mode, game_map=None, date_range=None):
    """
    Find all games by a player in a given mode.

    :param db: database
    :param name: player name
    :param mode: mode to search for games in
    :param game_map: maps to search for
    :param date_range: tuple of start and end date
    :return: matches and teammates' IGNs
    """
    data = identify_player(db, name)
    # load and search for all igns plus name so we don't get empty match histories
    igns = data["ign"]
    if type(igns) == str:
        igns = [igns]
    igns += [name]
    if game_map:
        # we only need to find matches where the player was on the winning team
        search = [{"team1":{"$elemMatch":{"player":ign}}} for ign in igns]
        search += [{"team2":{"$elemMatch":{"player":ign}}} for ign in igns]
        search += [{"players":{"$elemMatch":{"player":ign}}} for ign in igns]
        matches = db.matches.find({"$and": [{"$or": search}, {"mode": mode, "map": game_map}]})
    else:
        # we only need to find matches where the player was on the winning team
        search = [{"team1":{"$elemMatch":{"player":ign}}} for ign in igns]
        search += [{"team2":{"$elemMatch":{"player":ign}}} for ign in igns]
        search += [{"players":{"$elemMatch":{"player":ign}}} for ign in igns]
        matches = db.matches.find({"$and": [{"$or": search}, {"mode": mode}]})
    filtered_matches = []
    if date_range:
        for match in matches:
            if "date" in match:
                if date_convert(date_range[0]) <= date_convert(match["date"]) <= date_convert(date_range[1]):
                    filtered_matches.append(match)
        return filtered_matches, igns
    return matches, igns


def parse_matches(db, matches, name, min_games, track_teams=False):
    """
    Parse given matches for a player to find synergies.

    :param db: database
    :param matches: all won matches by a player
    :param name: player name
    :param min_games: minimum number of games played together
    :param track_teams: track teams or individual teammates
    :return: dict of players/teams and their games won, lost
    """
    # dict with [games played, wins] for [opponents, teammates]
    dicts = [{}, {}]
    for m in matches:
        for i in [1, 2]:
            team = m[f"team{i}"]
            players = []
            changes = []
            for player in team:
                changes.append(player["mmrchange"])
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
                            dicts[d][players[j]] = [dicts[d][players[j]][0] + 1, dicts[d][players[j]][1], dicts[d][players[j]][2] + 1, dicts[d][players[j]][3] + changes[j]]
                        except:
                            dicts[d][players[j]] = [1, 0, 1, changes[j]]
                    elif i == m["outcome"]:
                        try:
                            dicts[d][players[j]] = [dicts[d][players[j]][0] + 1, dicts[d][players[j]][1] + 1, dicts[d][players[j]][2], dicts[d][players[j]][3] + changes[j]]
                        except:
                            dicts[d][players[j]] = [1, 1, 0, changes[j]]
                    else:
                        try:
                            dicts[d][players[j]] = [dicts[d][players[j]][0] + 1, dicts[d][players[j]][1], dicts[d][players[j]][2], dicts[d][players[j]][3] + changes[j]]
                        except:
                            dicts[d][players[j]] = [1, 0, 0, changes[j]]
    sorted_dicts = [{}, {}]
    for d in range(len(dicts)):
        for player in dicts[d]:
            # make sure min games played
            if dicts[d][player][0] >= min_games:
                sorted_dicts[d][player] = [dicts[d][player][1] / dicts[d][player][0], dicts[d][player][0], dicts[d][player][1], dicts[d][player][2], dicts[d][player][3], dicts[d][player][3] / dicts[d][player][0]]
        sorted_dicts[d] = dict(sorted(sorted_dicts[d].items(), key=lambda item: item[1][0], reverse=True))
    return sorted_dicts


def parse_matches_elo(db, matches, name, min_games, mode, track_teams=False):
    """
    Parse given matches for a player to find synergies using MMR and outcome.

    :param db: database
    :param matches: all won matches by a player
    :param name: player name
    :param min_games: minimum number of games played together
    :param mode: game mode
    :param track_teams: track teams or individual teammates
    :return: dict of players/teams and their games won, lost
    """
    import eloupdate as elo
    # dict with [games played, wins] for [opponents, teammates]
    dicts = [{}, {}]
    mode = check_mode(mode, short=True)
    if mode == "do":
        ref = 0
    else:
        ref = None
    for m in matches:
        ratings = [[identify_player(db, m[f"team{i}"][j]["player"])[f"{mode}mmr"] for j in range(len(m[f"team{i}"]))] for i in [1, 2]]
        scores = [sum(m[f"team{i}"][j]["score"] for j in range(len(m[f"team{i}"]))) for i in [1, 2]]
        expected = []
        expected.append(elo.E([elo.w_mean(ratings[0], ratings[1])[0], elo.w_mean(ratings[1], ratings[0])[0]]))
        expected.append(1 - expected[0])
        if m["outcome"] == 1:
            S = [1, 0]
        elif m["outcome"] == 2:
            S = [0, 1]
        elif m["outcome"] == 0:
            S = [.5, .5]
        # calculate for first team and later check player's team
        rating_change = elo.R_change(R=0, S=S[0], E=expected[0], N=50, t1=scores[0], t2=scores[1], ref=ref)
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
                if ign in players:
                    d = 1
            if i == 2:
                rating_change *= -1
            if track_teams:
                players = ", ".join(sorted(players))
                try:
                    dicts[d][players] = [dicts[d][players][0] + 1, dicts[d][players][1] + rating_change]
                except:
                    dicts[d][players] = [1, rating_change]
            else:
                for j in range(len(players)):
                    try:
                        dicts[d][players[j]] = [dicts[d][players[j]][0] + 1, dicts[d][players[j]][1] + rating_change]
                    except:
                        dicts[d][players[j]] = [1, rating_change]
    sorted_dicts = [{}, {}]
    for d in range(len(dicts)):
        for player in dicts[d]:
            # make sure min games played
            if dicts[d][player][0] >= min_games:
                sorted_dicts[d][player] = [dicts[d][player][0], dicts[d][player][1] / dicts[d][player][0]]
        sorted_dicts[d] = dict(sorted(sorted_dicts[d].items(), key=lambda item: item[1][1], reverse=True))
    return sorted_dicts

def parse_ffa(db, matches, name, min_games):
    """
    Parse given matches for a player to find synergies.

    :param db: database
    :param matches: all won matches by a player
    :param name: player name
    :param min_games: minimum number of games played together
    :param track_teams: track teams or individual teammates
    :return: dict of players and their games won, lost
    """
    # dict with [games played, wins] for opponents

    opponents = {}
    for m in matches:
        players = []
        position = 0
        for i in range(len(m['players'])):
                player = m['players'][i]["player"]
                player = identify_player(db, player)["name"]
                players.append(player)
                if not opponents.get(player):
                    opponents[player] = {"wins": 0, "draws": 0, "games": 0, "finishes": 0}

        for ign in name:
            try:
                position = [p.lower() for p in players].index(ign.lower()) + 1
                break
            except ValueError:
                 continue

        for i in range(len(players)):
            opponents[players[i]]["finishes"] += position
            opponents[players[i]]["games"] += 1
            if m["players"][i]["score"] == m["players"][position-1]["score"]:
                opponents[players[i]]["draws"] += 1
                if i+1 < position:
                    opponents[players[i]]["finishes"] -= 1
            elif position < i+1:
                opponents[players[i]]["wins"] += 1

    opponents = dict(filter(lambda item: item[1]["games"] >= min_games, opponents.items()))
    return opponents

def dict_string_elo(d):
    """
    Convert a dictionary to a properly formatted string for printing.

    :param d: dictionary to convert
    :return: d as formatted string
    """
    val = ""
    for item in d:
        val += f"{item}: {round(d[item][1], 2)} MMR ({d[item][0]} games)\n"
    return val


def dict_string(d):
    """
    Convert a dictionary to a properly formatted string for printing.

    :param d: dictionary to convert
    :return: d as formatted string
    """
    val = ""
    for item in d:
        val += f"{item}: {round(d[item][0] * 100)}% ({d[item][2]} / {d[item][1]} | {d[item][3]} ties)\n"
    return val

def dict_string_ffa(opponents: dict):
    """
    Convert a dictionary to a properly formatted string for printing.

    :param d: dictionary to convert
    :return: d as formatted string
    """
    winrate_sort = dict(sorted(opponents.items(), key=lambda item: (item[1]["wins"]+item[1]["draws"]/2)/item[1]["games"], reverse=True))
    finish_sort = dict(sorted(opponents.items(), key=lambda item: item[1]["finishes"]/item[1]["games"]))
    winrate_str = ""
    finish_str = ""

    for player in winrate_sort:
        winrate_str += f"{player}: " + str(round( \
            ((opponents[player]['wins'] + opponents[player]['draws'] / 2)/ opponents[player]['games']) * 100))+ "% " \
            f"({opponents[player]['wins']} / {opponents[player]['games']} | {opponents[player]['draws']} ties)\n"

    for player in finish_sort:
        finish_str += f"{player}: {round(opponents[player]['finishes'] / opponents[player]['games'], 2)} " \
            f"(over {opponents[player]['games']} games)\n"

    return finish_str, winrate_str


def own_winrate(name, mode="Manhunt", game_maps=None):
    """
    Wrapper around find_games, parse_matches, dict_string to find one player's
    winrate on a map
    :param name: player name
    :param mode: mode to search for games of
    :return: string of synergies
    """
    db = connect()
    games, igns = find_games(db, name, mode, game_maps)
    results = parse_matches(db, games, igns, 1, False)
    d = results[1][name]
    return d[0], f"{name}: {round(d[0] * 100)}% ({d[2]} / {d[1]} | {d[3]} ties) (MMR: {round(d[4], 2)} total, {round(d[5], 4)} avg)"


def find_synergy(name, mode="Manhunt", min_games=25, track_teams=False, game_maps=None, date_range=None, elo=False):
    """
    Wrapper around find_games, parse_matches, dict_string to find synergies for
    a given player in a given mode.

    :param name: player name
    :param mode: mode to search for games of
    :param min_games: minimum number of games played with a team(mate)
    :param track_teams: switch between individual teammates or full teams
    :param game_maps: maps to search for
    :param date_range: tuple of start and end date
    :return: string of synergies
    """
    db = connect()
    games, igns = find_games(db, name, mode, game_maps, date_range)
    if elo:
        results = parse_matches_elo(db, games, igns, min_games, mode, track_teams)
        return dict_string_elo(results[1]), dict_string_elo(results[0])
    results = parse_matches(db, games, igns, min_games, track_teams)
    return dict_string(results[1]), dict_string(results[0])


def find_synergy_ffa(name, mode="Deathmatch", min_games=25):
    """
    Wrapper around find_games, parse_matches, dict_string to find synergies for
    a given player in a given mode.

    :param name: player name
    :param mode: mode to search for games of
    :param min_games: minimum number of games played with a team(mate)
    :param track_teams: switch between individual teammates or full teams
    :return: string of synergies
    """
    db = connect()
    games, igns = find_games(db, name, mode)
    results = parse_ffa(db, games, igns, min_games)
    return dict_string_ffa(results)

# region map synergy

def find_games_w_map(db, name, mode, date_range=None):
    """
    Find all games by a player in a given mode.

    :param db: database
    :param name: player name
    :param mode: mode to search for games in
    :param game_map: maps to search for
    :param date_range: tuple of start and end date
    :return: matches and teammates' IGNs
    """
    data = identify_player(db, name)
    # load and search for all igns plus name so we don't get empty match histories
    igns = data["ign"]
    if type(igns) == str:
        igns = [igns]
    igns += [name]

    # we only need to find matches where the player was on the winning team
    search = [{"team1":{"$elemMatch":{"player":ign}}} for ign in igns]
    search += [{"team2":{"$elemMatch":{"player":ign}}} for ign in igns]
    search += [{"players":{"$elemMatch":{"player":ign}}} for ign in igns]
    matches = db.matches.find({"$and": [{"$or": search}, {"mode": mode, "map": {"$ne": None}}]})

    filtered_matches = []
    if date_range:
        for match in matches:
            if "date" in match:
                if date_convert(date_range[0]) <= date_convert(match["date"]) <= date_convert(date_range[1]):
                    filtered_matches.append(match)
        return filtered_matches, igns
    return matches, igns

def map_synergy(name, mode="Manhunt", min_games=25, date_range=None):
    """
    Wrapper around find_games, parse_matches, dict_string to find synergies for
    a given player in a given mode.

    :param name: player name
    :param mode: mode to search for games of
    :param min_games: minimum number of games played with a team(mate)
    :param track_teams: switch between individual teammates or full teams
    :param game_maps: maps to search for
    :param date_range: tuple of start and end date
    :return: string of synergies
    """
    db = connect()
    games, _ = find_games_w_map(db, name, mode, date_range=date_range)
    results = map_parse(games, name, min_games)

    winrate_sort = dict(sorted(results.items(), key=lambda item: (item[1]["wins"]+item[1]["draws"]/2)/item[1]["games"], reverse=True))
    statline_sort = dict(sorted(results.items(), key=lambda item: 
        (item[1]["score"]/item[1]["games"]) if mode in ['Manhunt', 'Escort'] else (item[1]['kills']/item[1]['deaths'])))
    winrate_str = ""
    stats_str = ""

    for gmap in winrate_sort:
        winrate_str += f"{gmap}: " + str(round( \
            ((results[gmap]['wins'] + results[gmap]['draws'] / 2)/ results[gmap]['games']) * 100))+ "% " \
            f"({results[gmap]['wins']} / {results[gmap]['games']} | {results[gmap]['draws']} ties)\n"

    for gmap in statline_sort:
        stats_str += f"{gmap}: {round(results[gmap]['score'] / results[gmap]['games'])}, "\
            f"{round(results[gmap]['kills']/results[gmap]['deaths'], 2)} " \
            f"({results[gmap]['games']} games)\n"

    return winrate_str, stats_str

def map_parse_ffa(db, matches, name, min_games):
    maps = {}
    for m in matches:
        position = 0
        if not m['map'] in maps:
            maps[m['map']] = {
                "wins": 0,
                "draws": 0,
                "games": 0,
                "finishes": 0,
                "kills": 0,
                "deaths": 0,
                "score": 0
            }
        for i in range(len(m['players'])):
                player = m['players'][i]["player"]
                player = identify_player(db, player)["name"]
                players.append(player)
                if not opponents.get(player):
                    opponents[player] = {"wins": 0, "draws": 0, "games": 0, "finishes": 0}

        for ign in name:
            try:
                position = [p.lower() for p in players].index(ign.lower()) + 1
                break
            except ValueError:
                 continue

        for i in range(len(players)):
            opponents[players[i]]["finishes"] += position
            opponents[players[i]]["games"] += 1
            if m["players"][i]["score"] == m["players"][position-1]["score"]:
                opponents[players[i]]["draws"] += 1
                if i+1 < position:
                    opponents[players[i]]["finishes"] -= 1
            elif position < i+1:
                opponents[players[i]]["wins"] += 1

    opponents = dict(filter(lambda item: item[1]["games"] >= min_games, opponents.items()))
    return opponents

def map_parse(matches, name, min_games):
    maps = {}
    for m in matches:
        if not m['map'] in maps:
            maps[m['map']] = {
                "wins": 0,
                "draws": 0,
                "games": 0,
                "kills": 0,
                "deaths": 0,
                "score": 0
            }
        team = None
        for i in [1,2]:
            for p in m[f'team{i}']:
                if p['player'] == name:
                    team = i
                    break
            if team:
                break
        res = {
            "wins": 0,
            "draws": 0,
            "games": 1,
            "kills": p['kills'],
            "deaths": p['deaths'],
            "score": p['score']
        }

        if m['outcome'] == 0:
            res['draws'] = 1
        elif m['outcome'] == team:
            res['wins'] = 1

        for k in res.keys():
            maps[m['map']][k] += res[k]

    maps = dict(filter(lambda item: item[1]["games"] >= min_games, maps.items()))
    return maps
# endregion


if __name__ == "__main__":
    #mode = "Domination"
    mode = "Escort"
    #mode = "Manhunt"
    #for m in ["Palenque", "Havana", "Tampa Bay", "Kingston", "Virginian Plantation"]:
    for m in ["Castel Gandolfo", "Siena", "Venice", "Forli", "San Donato", "Rome"]:
#    for m in ["Castel Gandolfo"]:
        print(m)
        s = []
        # print("Player: Winrate (Games Won / Tied / Played)")
        #for x in ["Shmush", "Lunaire.-", "Edi", "Xanthex", "Lars", "Christian", "Cota", "Gummy", "Katsvya", "Arun", "Skorpius"]:
        for x in ["DevelSpirit", "Sugarfree", "Tha Fazz", "Ted95On", "Dellpit", "Jelko"]:
        # for x in ["Dellpit", "Tha Fazz"]:
            s.append(own_winrate(x, mode, game_maps=m))
            # print("Finding synergy for:", x)
            # synergies = find_synergy(x, mode, min_games=5, game_maps=None, date_range=("2020-01-01", "2024-01-01"), elo=True)
            # synergies = find_synergy(x, mode, min_games=15, game_maps=None, date_range=None, elo=True)
            # print("Top teammates:")
            # print(synergies[0])
            # print("Top opponents:")
            # print(synergies[1])
        for i in sorted(s, reverse=True):
            print(i[1])
