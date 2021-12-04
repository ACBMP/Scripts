from random import randrange, shuffle
from eloupdate import w_mean
import numpy as np
import itertools
from util import *


def find_teams(players, mode, random=25, debug=False):
    """
    Main function to run.
    players: list of strings of player names
    mode: string of mode: "Escort" or "Manhunt"
    random: int, sane values in [1, 100], 0 to disable
    debug: useless
    returns array of two teams with the best team matchups
    """
    if len(players) % 2 == 1 or len(players) < 2 or len(players) > 8:
        raise ValueError("find_teams: even number of players in [2, 8] required!")
    shuffle(players)
    players = extract_players(players)
    all_combs = combinations(players)
    all_diffs = []
    for comb in all_combs:
        all_diffs.append(team_diff(comb[0], comb[1], mode, players, random))
    best_matchup = all_combs[np.argmin(all_diffs)]
    if debug:
        print(all_diffs)
        return best_matchup, np.min(all_diffs)
    else:
        return best_matchup[::randrange(-1, 2, 2)]


def combinations(players):
    teams = itertools.combinations(players, int(len(players) / 2))
    teams = list(teams)
    return [[teams[int(i - 1)], teams[-int(i)]] for i in range(1, int(len(teams) / 2) + 1, 1)]


def team_elo(team, o_team, random):
    elo = w_mean(team, o_team)[0]
    std = (1 / (len(team) - 1) * sum([(x - elo) ** 2 for x in team])) ** .5
    if random:
        return elo + std * randrange(-random, random) / 100
    else:
        return elo


def team_diff(team1, team2, mode, players, random):
    R1, R2 = [], []

    if mode.lower() == "escort" or mode.lower() == "e":
        for i in range(len(team1)):
            R1.append(team1[i]["emmr"])
            R2.append(team2[i]["emmr"])
    elif mode.lower() == "manhunt" or mode.lower() == "mh":
        for i in range(len(team1)):
            R1.append(team1[i]["mhmmr"])
            R2.append(team2[i]["mhmmr"])

    elo1 = team_elo(R1, R2, random)
    elo2 = team_elo(R2, R1, random)
    return abs(elo1 - elo2)


def extract_players(players):
    """players needs to be a list of strings with names"""
    db = connect()
    p = []
    for player in players:
        p.append(identify_player(db, player))
    return p


def test(n):
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

