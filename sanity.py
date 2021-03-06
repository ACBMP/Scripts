from util import *

def read_file(fname="matches.txt"):
    """
    File reading wrapper.
    
    :param fname: file name
    :return: contents of fname
    """
    with open(fname, "r") as f:
        data = f.read()
        f.close()
    return data


def sanity_check(data):
    """
    Sanity check for data to e.g. prevent a losing team from being marked as
    having won a match.

    The function will output only the first error detected, hence it's
    recommended to run multiple times.

    :param data: data to parse
    :return: first error detected
    """
    games = data.split("\n")
    db = connect()
    for game in games:
        # filter out empty lines (these don't matter anyway)
        if not game.split():
            continue

        players = game.split(", ")
        mode = players[0]

        # sanity check mode
        if mode not in ["M", "E", "AA"]:
            return f"Unknown mode {mode} detected in:\n{game}"

        num_players = int(players[1])
        outcome = int(players[2])
        gamers = players[3:] # very epic

        # check for missing players or commas
        if len(gamers) != num_players * 2:
            return f"Formatting error or missing player found in:\n{game}"

        # load player data
        score = [0, 0]
        kills = [0, 0]
        deaths = [0, 0]
        # team index
        i = 0
        num_delim = 3
        if mode == "AA":
            num_delim += 1
        for j in range(len(gamers)):
            # check for $ delim count
            if gamers[j].count("$") != num_delim:
                return f"Incorrect $ delim count detected for {gamers[j]} in:\n{game}"
            player = gamers[j].split("$")

            # check if player in db
            try:
                identify_player(db, player[0])
            except ValueError as e:
                return str(e).replace("insert_player: p", "P") + ":\n" + game

            # sum score
            if mode != "AA":
                score[i] += int(player[1])
            else:
                score[i] += int(player[4])

            # check if score is reasonable
            if int(player[1]) > 20000:
                return f"Unusually high score detected in:\n{game.replace(player[1], f'**{player[1]}**')}" 

            # sum k/d
            kills[i] += int(player[2])
            deaths[i] += int(player[3])

            # switch to next team
            if j == num_players - 1:
                i = 1
        
        # sanity check k/d
        for i in range(2):
            # mildly retarded
            if kills[i] != deaths[(i + 1) % 2]:
                return f"Incorrect kill ({i + 1})/death ({i + 1 % 2 + 1}) count detected in:\n{game}"
        
        # sanity check score and outcome
        if outcome > 0:
            if max(score) != score[outcome - 1]:
                return f"Incorrect score/outcome detected in:\n{game}"
        else:
            if score[0] != score[1]:
                return f"Incorrect score/outcome detected in:\n{game}"
    return "No errors detected"


def main():
    return sanity_check(read_file("matches.txt"))


if __name__ == "__main__":
    print(main())
