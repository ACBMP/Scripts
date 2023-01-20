from random import randrange, shuffle
from eloupdate import w_mean
import numpy as np
import itertools
from util import *


def find_teams(players, mode, random=25, debug=False, groups=None):
    """
    Main function to run to find optimal teams.

    :param players: list of strings of player names
    :param mode: string of mode: "Escort" or "Manhunt"
    :param random: int, sane values in [1, 100], 0 to disable
                   randomness factor so you don't always get the optimal team
                   since the same team every time gets boring
    :param debug: useless
    :return: array of two teams with the best team matchups
    """
    if len(players) % 2 == 1 or len(players) < 2 or len(players) > 8:
        raise ValueError("find_teams: even number of players in [2, 8] required!")
    shuffle(players)
    players = extract_players(players, mode)
    all_combs = combinations(players)
    # group check not optimal
    if groups:
        for g in groups:
            gset = set([identify_player(connect(), p)["name"] for p in g])
            for i in reversed(range(len(all_combs))):
                temp = [[p["name"] for p in all_combs[i][j]] for j in [0, 1]]
                if not (gset.issubset(temp[0]) or gset.issubset(temp[1])):
                    del all_combs[i]
        if all_combs == []:
            raise ValueError("Impossible to find team compositions with given groups.")
    all_diffs = []
    for comb in all_combs:
        all_diffs.append(team_diff(comb[0], comb[1], mode, random))
    best_matchup = all_combs[np.argmin(all_diffs)]
    if debug:
        print(all_diffs)
        return best_matchup, np.min(all_diffs)
    else:
        return best_matchup[::randrange(-1, 2, 2)]


def combinations(players):
    """
    Find combinations of players.

    :param players: players to combine
    :return: list of possible teams
    """
    teams = itertools.combinations(players, int(len(players) / 2))
    teams = list(teams)
    return [[teams[int(i - 1)], teams[-int(i)]] for i in range(1, int(len(teams) / 2) + 1, 1)]


def team_elo(team, o_team, random):
    """
    Calculate team MMR.

    :param team: team whose MMR will be calculated
    :param o_team: opposing team
    :param random: int, sane values in [1, 100], 0 to disable
                   randomness factor so you don't always get the optimal team
                   since the same team every time gets boring
    :return: team MMR
    """
    elo = w_mean(team, o_team)[0]
    if random:
        std = (1 / (len(team) - 1) * sum([(x - elo) ** 2 for x in team])) ** .5
        return elo + std * randrange(-random, random) / 100
    else:
        return elo


def team_diff(team1, team2, mode, random):
    """
    Calculate the difference between two teams' MMRs.

    :param team1: team 1
    :param team2: team 2
    :param mode: game mode
    :param random: int, sane values in [1, 100], 0 to disable
                   randomness factor so you don't always get the optimal team
                   since the same team every time gets boring
    :return difference between teams' MMRs
    """
    R1, R2 = [], []

    mode = check_mode(mode, short=True)
    for i in range(len(team1)):
        R1.append(team1[i][f"{mode}mmr"])
        R2.append(team2[i][f"{mode}mmr"])

    elo1 = team_elo(R1, R2, random)
    elo2 = team_elo(R2, R1, random)
    return abs(elo1 - elo2)


def extract_players(players, mode):
    """
    Find players in database.

    :param players: player names to find teams for
    :return: list of players as mongodb objects
    """
    db = connect()
    p = []
    for player in players:
        try:
            p.append(identify_player(db, player))
        except ValueError:
            try:
                p.append({
                    "name": f'{rank_title(int(player))}',
                    f"{mode}mmr": int(player),
                    f"{mode}games": {"total": 50}
                })
            except ValueError:
                raise ValueError(f"I've never heard of {player}.")
    return p


def find_lobbies(players, mode="Domination", lobby_size=8):
    """
    Split a group of players into lobbies of a given size. Doesn't support multiple sizes.

    Splits according to MMR with consideration for placements.
    
    :param players: List of players.
    :param mode: Game mode.
    :param lobby_size: Size of lobbies.
    :return: List of lobbies with players.
    """
    # supporting varying lobby sizes seems annoying
    if len(players) % lobby_size != 0:
        raise ValueError("Could not evenly divide players into lobbies.")
    num_lobbies = len(players) / lobby_size
    import numpy as np
    db = connect()
    mode = check_mode(mode, short=True)
    players = [identify_player(db, p) for p in players]
    players_split = [[], []]
    # run through players and check for whether they've finished placements
    for p in players:
        if p[f"{mode}games"]["total"] < 10:
            players_split[1].append(p)
        else:
            players_split[0].append(p)
    # sort players by mmr
    for i in range(2):
        players_split[i].sort(key=lambda p: p[f"{mode}mmr"])
    # split into lobbies
    lobbies = np.array_split(players_split[0], num_lobbies)
    # fill up lobbies with any remaining placement players
    if len(players_split[1]) > 0:
        for p in players_split[1]:
            free = True
            i = 0
            while free:
                if len(lobbies[i]) < lobby_size:
                    lobbies[i] = np.append(lobbies[i], p)
                    free = False
                i += 1
    # only need the names
    for i in range(len(lobbies)):
        lobbies[i] = [p["name"] for p in lobbies[i]]
    return lobbies


def find_lobbies_groups(players, mode="Domination", lobby_size=8):
    """
    Split a group of players into lobbies of a given size. Doesn't support multiple sizes.

    Splits according to MMR with consideration for placements.
    
    :param players: List of players.
    :param mode: Game mode.
    :param lobby_size: Size of lobbies.
    :return: List of lobbies with players.
    """
    groups = []
    if isinstance(players, str):
        players = players.split(", ")
        for p in players:
            if "+" in p:
                groups.append(p.split("+"))
        
    # supporting varying lobby sizes seems annoying
    if len(players) % lobby_size != 0:
        raise ValueError("Could not evenly divide players into lobbies.")
    num_lobbies = len(players) / lobby_size
    import numpy as np
    db = connect()
    mode = check_mode(mode, short=True)

    players = [identify_player(db, p) for p in players]
    players_split = [[], []]
    # run through players and check for whether they've finished placements
    for p in players:
        if p[f"{mode}games"]["total"] < 10:
            players_split[1].append(p)
        else:
            players_split[0].append(p)
    # sort players by mmr
    for i in range(2):
        players_split[i].sort(key=lambda p: p[f"{mode}mmr"])
    # split into lobbies
    lobbies = np.array_split(players_split[0], num_lobbies)
    # fill up lobbies with any remaining placement players
    if len(players_split[1]) > 0:
        for p in players_split[1]:
            free = True
            i = 0
            while free:
                if len(lobbies[i]) < lobby_size:
                    lobbies[i] = np.append(lobbies[i], p)
                    free = False
                i += 1
    # only need the names
    for i in range(len(lobbies)):
        lobbies[i] = [p["name"] for p in lobbies[i]]
    return lobbies


def test(n):
    """
    Test function.

    :param n: number of tests to run
    """
    players = ["Sugarfree", "Edi", "Arun", "TDCANDHP", "Cota", "Xanthex"]#["Dellpit", "Tha Fazz", "Auditore92", "EsquimoJo", "Crispi Kreme", "EternityEzioWolf"]
    for x in range(n):
        res = find_teams(players, "Domination", 25, groups=[players[1:3]])
        for i in [1, 2]:
            print(f"Team {i}")
            for player in res[i - 1]:
                print(player["name"])
#                print(player)
    return


def test_lobbies(n, **kwargs):
    for i in range(n):
        print(find_lobbies(**kwargs))
    return

if __name__ == "__main__":
    test(10)
#    test_lobbies(1, players=["Sugarfree", "Edi", "Arun", "TDCANDHP", "Cota", "Xanthex"], lobby_size=2)
#    test_lobbies(1, players="Sugarfree., iqueazo, piesio1, luc_link5, durza, rorce, scorpius, camiikase, Shmush, Vlad, Lunaire.-, ShadowX, Xanthex, FynnC, Arun, Lars".split(", "), lobby_size=8)

