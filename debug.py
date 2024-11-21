import numpy as np
from scipy.special import perm
import eloupdate_ffa as ffa

total_players = 3
opp_ratings = [1000, 1000]
player_rating = np.mean(opp_ratings)
chance_to_beat = ffa.expected_results([player_rating]+opp_ratings)[0]
pos_chances = []

for pos in range(1, total_players+1):    
    beating = total_players-pos
    beat_by = total_players-1-beating
    placing_chance = (chance_to_beat**beating)
    placing_chance *= ((1-chance_to_beat)**beat_by)
    placing_chance *= perm(total_players-1, total_players-1)/int((total_players-1)/2)
    pos_chances.append(placing_chance)
print(pos_chances)
print(sum(pos_chances))
