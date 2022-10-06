from random import randrange, shuffle
from eloupdate import w_mean
import numpy as np
import itertools
from util import *


def find_teams(players, mode, random=25, debug=False):
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
    players = extract_players(players)
    all_combs = combinations(players)
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


def extract_players(players):
    """
    Find players in database.

    :param players: player names to find teams for
    :return: list of players as mongodb objects
    """
    db = connect()
    p = []
    for player in players:
        p.append(identify_player(db, player))
    return p


def test(n):
    """
    Test function.

    :param n: number of tests to run
    """
    players = ["Dellpit", "Tha Fazz", "Auditore92", "EsquimoJo", "Crispi Kreme", "EternityEzioWolf"]
    for x in range(n):
        res = find_teams(players, "Manhunt", 25)
        for i in [1, 2]:
            print(f"Team {i}")
            for player in res[i - 1]:
                print(player["name"])
    return

if __name__ == "__main__":
    test(1)

