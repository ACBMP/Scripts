class player:
    
    def __init__(self, name, points, kills, deaths):
        self.name = name
        self.points = points
        self.kills = kills
        self.deaths = deaths

    def subtract_dodge(self):
        self.points -= 750


class idiot(player):
    """
    class for AA players
    """

    def __init__(self, name, points, kills, deaths, artifacts):
        player.__init__(self, name, points, kills, deaths)
        self.artifacts = artifacts

    def subtract_score(self):
        self.artifacts -= 1
        self.points -= 650


######### FUCK ALL THS
def txt_to_matches(fname="matches.txt"):
    with open(fname, "r") as f:
        matches = f.split("\n")
        f.close()
    return matches


def parse_matches(matches):
    for game in matches:
        players = game.split(", ")
        team
        for i in range(players):
            stats = players[i].split("$")
            if len(stats) == 5:
                players[i] = idiot(stats[0], stats[1], stats[2], stats[3], stats[4])
            elif len(stats) == 4:
                players[i] = player(stats[0], stats[1], stats[2], stats[3])
            else:
                raise ValueError()
