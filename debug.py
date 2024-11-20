import numpy as np
import math

import eloupdate_ffa as ffa

total_players = 4
opp_ratings = [1000, 1000]
player_rating = np.mean(opp_ratings)
chance_to_beat = ffa.expected_results([player_rating]+opp_ratings)[0]
pos_chances = []

for pos in range(1, total_players+1):    
    beating = total_players-pos
    beat_by = total_players-1-beating
    placing_chance = (chance_to_beat**beating)*math.comb(total_players-1, beating)
    placing_chance *= ((1-chance_to_beat)**beat_by)*math.comb((total_players-1)-beating, beat_by)
    pos_chances.append(placing_chance)
print(pos_chances)
print(sum(pos_chances))
