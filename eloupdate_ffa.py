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
    players: List[Player] = None
    new: bool
    mode: str

def pos_to_str(pos: int):
    if pos < 1 or pos > 8:
        raise ValueError("position must be 1-8")
    if pos == 1:
        return '1st'
    if pos == 2:
        return '2nd'
    if pos == 3:
        return '3rd'
    return f'{pos}th'

def expected_results(ratings: List[int]):
    """
    Expected win chance based on MMRs.
     :param ratings: list or tuple containing the two MMRs to compare
    :return: win chance for first MMR in ratings
    """
    expected_outcomes = []
    for player in range(len(ratings)):
        p_rating = ratings[player]
        o_ratings = np.array(ratings[:player] + ratings[player+1:])
        o_rating = (o_ratings.mean() + np.median(o_ratings))/2
        expected = (1 + 10 ** ((o_rating - p_rating) / 400)) ** -1
        expected_outcomes.append(float(expected))
    return expected_outcomes

def rating_change(current_mmr: int, result: float, expected_result: float, games_played: int,
            position: int, scores: List[int], stomp_ref: int = None, max_change: int = None):
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
        return max_change * (result - expected_result) * (1 + stomp_mmr_boost(position, scores, stomp_ref)) + result # trying to inflate by adding 1 to every win
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
    if current_mmr >= high_elo:
        return 15
    if total_games < 30:
        return 40
    return 20

def stomp_mmr_boost(position:int, scores: List[int], ref_score: int = None):
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
    avg_score = sum(scores) / len(scores)

    if ref_score is None:
        ref_score = avg_score / 2
    
    if ref_score == 0:
        return 0

    return abs(scores[position-1] - avg_score) / ref_score


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
        mmr_change = rating_change(
            current_mmr=ratings[p],
            result=result,
            expected_result=expected_outcomes[p],
            games_played=(player.db_data[f"{check_mode(match.mode, short=True)}games"]["total"] + 1),
            position=pos,
            scores=scores,
            stomp_ref=ref)
        new_mmr = ratings[p] + mmr_change
        # save the rating change
        results.append({
                    "player": player.dict(),
                    "pos": pos,
                    "mmr": new_mmr,
                    "mmrchange": mmr_change
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

        if not match.players:
            raise ValueError(f"match for mode {mode} must have players field")

        if mode == "dm":
            ref = 0
        else:
            ref = 10000

        results = player_ratings(match=m, db_conn=db, ref=ref)
        
        #Updating: mmr, total games played, finishing positions, total score, kills, deaths, check highscore
        #Updating the relevant MMR
        
        for i in range(len(results)):
            result = results[i]
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
            m["players"][i]["mmrchange"] = result["mmrchange"]
            db.matches.update_one({"_id":m["_id"]}, {"$set":{"players":False}})
            if player.get_db_data(db)[f"{mode}stats"]["highscore"] < player.score:
                db.players.update_one({
                    "name": player.player
                }, {
                    "$set": {f"{mode}stats.highscore": player.score}})

        db.matches.update_one({"_id":m["_id"]},{"$set":{"new":False, "players": m["players"]}})
        print("Match updated successfully!")

if __name__=="__main__":
    new_matches()
