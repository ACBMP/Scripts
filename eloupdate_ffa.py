from flask_pymongo import PyMongo
from pymongo import MongoClient
from util import *
from pydantic import BaseModel
import numpy as np
from typing import List

class Player(BaseModel):
    player: str
    score: int
    kills: int
    deaths: int
    db_data: dict = None

    def get_db_data(self, db_conn = None) -> dict:
        if not db_conn:
            return self.db_data
        if not self.db_data:
            self.db_data = identify_player(db_conn, self.player)
        return self.db_data

    def get_mmr(self, mode, db_conn=None):
        return self.get_db_data(db_conn)[f"{check_mode(mode, short=True)}mmr"]

class Match(BaseModel):
    players: List[Player]
    new: bool
    mode: str
    players: List[Player]

# def expected_results(ratings: List[int]):
#     """
#     Expected win chance based on MMRs.

#     :param ratings: list or tuple containing the two MMRs to compare
#     :return: win chance for first MMR in ratings
#     """
#     expected_outcomes = []
#     for player in range(len(ratings)):
#         expected = 0
#         p_rating = ratings[player]
#         for opponent in range(len(ratings)):
#             if opponent != player:
#                 o_rating = ratings[opponent]
#                 expected += ((1 + 10 ** ((p_rating - o_rating) / 400)) ** -1) * 1/(len(ratings)-1)
#         expected_outcomes.append(expected)
#     return expected_outcomes

def expected_results(ratings: List[int]):
    expected_outcomes = []

    for p in range(len(ratings)):
        mean_opponents = mean_opponent_rating(p, ratings)
        p_rating = ratings[p]
        expected = ((1 + 10 ** ((mean_opponents - p_rating) / 400)) ** -1)
        #print(f"player ({ratings[p]}) vs. mean ({mean_opponents} expected winrate: {'{0:.2f}%'.format(expected)})")
        expected_outcomes.append(expected)
    return expected_outcomes


def new_mmr(current_mmr: int, result: float, expected_result: float, max_change: int = None, games_played=None, 
            scores: List[int] = None, stomp_ref: int = None):
    """
    Function to calculate new MMR.

    :param R: current MMR
    :param S: outcome; 0 for loss, 1 for win, 0.5 for tie
    :param E: expected win chance
    :param K: max MMR change
              this won't be the actual max change if t1 and t2 are used
    :param N: total number of games played
    :param scores: players scores
    :param stomp_ref: reference "stomp" score
    :return: adjusted MMR
    """
    if games_played > 10:
        if max_change is None:
            max_change = max_mmr_change(games_played, current_mmr)
        return current_mmr + max_change * (result - expected_result) * (1 + stomp_mmr_boost(scores, stomp_ref)) + result # trying to inflate by adding 1 to every win
    else:
        return current_mmr + (result * 60) - 10

def max_mmr_change(total_games, current_mmr):
    """
    Calculate max MMR change.

    :param N: total number of games played
    :param R: current MMR
    :return: max MMR change
    """
    high_elo = 1200
    if current_mmr >= high_elo:
        return 15
    if total_games < 30:
        return 40
    return 20

def stomp_mmr_boost(scores: List[int], ref_score: int = None):
    """
    Score difference MMR boost.
    This is used to make sure closer games count less than stomps.

    If no reference score is passed, this will be calculated according to the
    total score of the two players

    With a reference score, this is based on the how close to a standard "stomp"
    the score is.

    :param scores: tuple/list of scores
    :param ref_score: reference score, 0 to return 0
    :return: boost amount
    """
    if ref_score is None:
        try:
            return abs(scores[0] - scores[1]) / ((scores[0] + scores[1]) / 2)
        except ZeroDivisionError:
            return 0
    else:
        if ref_score > 0:
            return max(abs(scores[1] - scores[1]) - 1, 0) / ref_score
        return 0
    
def mean_opponent_rating(player, ratings):
    """
    Weighted arithmetic mean.
    Weights are calculated based on players' MMRs compared to the opposing
    team's.

    :param ratings: team ratings to be weighted
    :param ratings_o: opposing team's ratings
    :return: weighted mean of ratings, weights used
    """
    diffs = []
    opponents = []

    for opponent in range(len(ratings)):
        if opponent != player:
            opponents.append(ratings[opponent])
    return sum(opponents)/len(opponents)
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
    return sum([opponents[_] * weights[_] for _ in range(len(opponents))])/w_sum

def get_result(position: int, players: int):
    f_x = lambda x: 2.144033**x -1
    x_val = list(np.linspace(1, 0, players))[position-1]
    return f_x(x_val)
    #return ((1.1 ** (players - position)) - 1) \
    #    / (1.1**(players-1) - 1)

def player_ratings(match: Match, db_conn, ref=None):
    """
    Calculate new ratings for all players in a match.

    :param match: Match object
    :param ref: set reference stomp value
    :return: list of players containing names and new MMRs
    """

    # calculate expected outcome for each player
    if isinstance(match, dict):
        match = Match(**match)

    ratings = list(map(lambda player: player.get_mmr(match.mode, db_conn), match.players))
    scores = list(map(lambda player: player.score, match.players))
    expected_outcomes = expected_results(ratings)
    results = []

    for p in range(len(match.players)):
        player = match.players[p]
        pos = p if p > 0 and match.players[p].score == match.players[p-1].score else p+1
        result = get_result(pos, len(match.players))
        results.append({
                    "player": player.dict(),
                    "pos": pos,
                    "mmr": int(round(new_mmr(
                            current_mmr=ratings[p],
                            result=result,
                            expected_result=expected_outcomes[p],
                            games_played=(player.db_data[f"{check_mode(match.mode, short=True)}games"]["total"] + 1),
                            scores=scores,
                            stomp_ref=ref
                        )))
                    })
    return results


def new_matches():
    """
        Parse new matches in the database and update MMRs accordingly.
    """
    client = MongoClient('mongodb://localhost:27017/')
    db = client.public
    #Querying the db about new matches
    matches = db.matches.find({"new":True})
    matches = list(matches)

    if not matches:
        print("No new matches")

    for m in matches:
        match = Match(**m)

        mode = check_mode(match.mode, short=True)
        if mode not in FFA_MODES:
            continue

        results = player_ratings(match=m, db_conn=db, ref=None)
        
        #Updating: mmr, total games played, finishing positions, total score, kills, deaths, check highscore
        #Updating the relevant MMR
        
        for result in results:
            db.players.update_one({
                    "name": result["player"]["player"]
                }, {
                    "$set": {
                        f"{mode}mmr":
                        result["mmr"]
                    }})
            player = Player(**result["player"])
            db.players.update_one({
                "name": player.get_db_data(db)["name"]
                }, {
                "$inc": {
                    f"{mode}games.total": 1,
                    f"{mode}games.won": 1 if result["pos"] == 1 else 0,
                    f"{mode}games.lost": 1 if result["pos"] != 1 else 0,
                    f"{mode}games.podium": 1 if result["pos"] <= 3 else 0,
                    f"{mode}games.finishes": result["pos"],
                    f"{mode}stats.totalscore": player.score,
                    f"{mode}stats.kills": player.kills,
                    f"{mode}stats.deaths": player.deaths
                }})
    
            if player.get_db_data(db)[f"{mode}stats"]["highscore"] < player.score:
                db.players.update_one({
                    "ign": player.player
                }, {
                    "$set": {f"{mode}stats.highscore": player.score}})
       
        db.matches.update_one({"_id":m["_id"]},{"$set":{"new":False}})
        print("Match updated successfully!")

if __name__=="__main__":
    new_matches()
