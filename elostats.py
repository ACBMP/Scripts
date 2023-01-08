from util import *
import eloupdate as elo

def compare_players(p1, p2, mode, db=None, verbose=False):
    if db is None:
        db = connect()
    if type(p1) == type(p2) == list:
        temp = [p1, p2]
        for i in range(2):
            temp[i] = [p[f"{mode}mmr"] for p in temp[i]]
        p1 = elo.w_mean(temp[0], temp[1])[0]
        p2 = elo.w_mean(temp[1], temp[0])[0]
        if verbose:
            return elo.E([p1, p2]), [p1, p2]
        return elo.E([p1, p2])

    if type(mode) == str:
        return elo.E([p1[f"{mode}mmr"], p2[f"{mode}mmr"]])
    else:
        return elo.E([p1[f"{mode[0]}mmr"], p2[f"{mode[1]}mmr"]])

if __name__ == "__main__":
    db = connect()
    p1 = ["Dellpit", "Auditore92", "Tha Fazz"]
    p1 = [identify_player(db, p) for p in p1]
    p2 = ["DevelSpirit", "Jelko", "EternityEzioWolf"]
    p2 = [identify_player(db, p) for p in p2]
    print(compare_players(p1, p2, "mh", db))
