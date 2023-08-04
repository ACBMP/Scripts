from flask_pymongo import PyMongo
from pymongo import MongoClient
from util import *
from pydantic import BaseModel
from typing import List

class Player(BaseModel):
    player: str
    score: int
    kills: int
    deaths: int
    _db_data: dict = None

    def get_mmr(self, db_conn, mode):
        if not self._db_data:
            self._db_data = identify_player(db_conn, self.player)
        return self._db_data[f"{check_mode(mode, short=True)}mmr"]

class Match(BaseModel):
    players: List[Player]
    new: bool
    mode: str
    players: List[Player]

def expected_results(ratings: List[int]):
    """
    Expected win chance based on MMRs.

    :param ratings: list or tuple containing the two MMRs to compare
    :return: win chance for first MMR in ratings
    """
    expected_outcomes = []
    for player in range(ratings):
        expected = 0
        p_rating = ratings[player]
        for opponent in range(ratings):
            if opponent != player:
                o_rating = ratings[opponent]
                expected += ((1 + 10 ** ((p_rating - o_rating) / 400)) ** -1) * 1/len(ratings-1)
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
        return (result * 60) - 10

def max_mmr_change(total_games, current_mmr):
    """
    Calculate max MMR change.

    :param N: total number of games played
    :param R: current MMR
    :return: max MMR change
    """
    high_elo = 1200
    if total_games < 30 and current_mmr < high_elo:
        return 40
    elif current_mmr < high_elo:
        return 20
    else: # current_mmr >= high_elo
        return 15

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
    
def weighted_mean(ratings):
    """
    Weighted arithmetic mean.
    Weights are calculated based on players' MMRs compared to the opposing
    team's.

    :param ratings: team ratings to be weighted
    :param ratings_o: opposing team's ratings
    :return: weighted mean of ratings, weights used
    """
    diffs = []
    for player in range(ratings):
        p_rating = ratings[player]
        opponents = []
        for opponent in range(ratings):
            if opponent != player:
                opponents.append(ratings[player])
        mean = sum(opponents) / len(opponents)
        diffs.append(abs(p_rating - mean))
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


def get_result(position: int, players: int):
    return ((1.1 ** (players - position)) - 1) \
        / (1.1**(players-1) - 1)

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

    ratings = list(map(lambda player: player.get_mmr(db_conn, match.mode), match.players))
    scores = list(map(lambda player: player.score, match.players))
    expected_outcomes = expected_results(weighted_mean(ratings))
    results = []

    for p in range(len(match.players)):
        player = match.players[p]
        pos = p - 1 if p > 0 and match.players[p].score == match.players[p-1].score else p
        result = get_result(pos + 1, len(match.players))
        results.append({
                    "name": player.player,
                    "mmr": int(round(new_mmr(
                            current_mmr=ratings[p],
                            result=result,
                            expected_result=expected_outcomes[p],
                            games_played=(player._db_data[f"{match.mode}games"]["total"] + 1),
                            scores=scores,
                            ref=ref
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
        results = player_ratings(match=m, db_conn=db, ref=None)
        
        #Updating: mmr, total games played, finishing positions, total score, kills, deaths, check highscore
        #Updating the relevant MMR
        
        mode = check_mode(match.mode, short=True)
        if mode not in FFA_MODES:
            continue

        for resultentry in results:
            db.players.update_one({
                    "name": resultentry["name"]
                }, {
                    "$set": {
                        f"{mode}mmr":
                        resultentry["mmr"]
                    }})

            for i in range(1, len(match.players) + 1):
                player = match.players[i]
                db.players.update_one({
                        "ign": player.player
                    }, {
                        "$inc": {
                            f"{mode}games.total": 1,
                            f"{mode}games.won": 1 if i == 1 else 0,
                            f"{mode}games.lost": 1 if i != 1 else 0,
                            f"{mode}games.podium": 1 if i <= 3 else 0,
                            f"{mode}stats.totalscore": player.score,
                            f"{mode}stats.kills": player.kills,
                            f"{mode}stats.deaths": player.deaths
                            }})
                temp_player = db.players.find_one({"ign": player.player})
    
                if temp_player[f"{mode}stats"]["highscore"] < player.score:
                    db.players.update_one({
                            "ign": player.player
                        }, {
                            "$set": {f"{mode}stats.highscore": player.score}})
       
        db.matches.update_one({"_id":m["_id"]},{"$set":{"new":False}})
        print("Match updated successfully!")

if __name__=="__main__":
    new_matches()
