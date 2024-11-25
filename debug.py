import numpy as np


def w_mean(ratings, ratings_o):
    """
    Weighted arithmetic mean.
    Weights are calculated based on players' MMRs compared to the opposing
    team's.

    :param ratings: team ratings to be weighted
    :param ratings_o: opposing team's ratings
    :return: weighted mean of ratings, weights used
    """
    mean = 1000 # sum(ratings_o) / len(ratings_o)
    diffs = []
    for r in ratings:
        diffs.append(abs(r - mean))
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
    return sum([ratings[_] * weights[_] for _ in range(len(ratings))]) / w_sum, weights

t1 = [1405.5, 1354.2, 1162, 1286.1]
t2 = [1072.2, 743.9, 1059.7, 1057.5]

print(f"mean: {np.mean(t1)}")
print(f"med: {np.median(t1)}")
print(f"wmean: {w_mean(t1, t2)[0]}")

print(f"mean: {np.mean(t2)}")
print(f"med: {np.median(t2)}")
print(f"wmean: {w_mean(t2, t1)[0]}")
