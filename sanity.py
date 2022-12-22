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
    out = ""
    for game in games:
        # filter out empty lines (these don't matter anyway)
        if not game.split():
            continue

        players = game.split(", ")
        mode = players[0]
        if "$" in mode:
            temp = mode.split("$")
            map_name = temp[1]
            mode = temp[0]
        else:
            map_name = None

        # sanity check mode
        if mode not in ["M", "E", "AA", "DO"]:
            out += f"Unknown mode {mode} detected in:\n{game}\n"

        # sanity check map name
        if map_name:
            map_name = identify_map(map_name)

        num_players = int(players[1])
        outcome = players[2]
        # host
        if "$" in outcome:
            temp = outcome.split("$")
            host = temp[1]
            if host not in ["1", "2"]:
                out += f"Host team not in 1, 2 in:\n{game}"
            outcome = temp[1]
        outcome = int(outcome)
        gamers = players[3:] # very epic

        # check for missing players or commas
        if len(gamers) != num_players * 2:
            out += f"Formatting error or missing player found in:\n{game}\n"

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
                out += f"Incorrect $ delim count detected for {gamers[j]} in:\n{game}\n"
            player = gamers[j].split("$")

            # check if player in db
            try:
                identify_player(db, player[0])
            except ValueError as e:
                out += str(e).replace("insert_player: p", "P") + ":\n" + game + "\n"

            # sum score
            if mode != "AA":
                try:
                    score[i] += int(player[1])
                except ValueError:
                    out += f"Detected nonnumerical input for {gamers[j]} in:\n{game}\n"
            else:
                try:
                    score[i] += int(player[4])
                except ValueError:
                    out += f"Detected nonnumerical input for {gamers[j]} in:\n{game}\n"

            # check if score is reasonable
            if int(player[1]) > 20000:
                out += f"Unusually high score detected in:\n{game.replace(player[1], f'**{player[1]}**')}\n" 
            # sum k/d
            try:
                kills[i] += int(player[2])
            except ValueError:
                out += f"Detected nonnumerical input for {gamers[j]} in:\n{game}\n"
            try:
                deaths[i] += int(player[3])
            except ValueError:
                out += f"Detected nonnumerical input for {gamers[j]} in:\n{game}\n"

            # switch to next team
            if j == num_players - 1:
                i = 1
        
        # k/d check unfortunately doesn't work for console escort
        if mode != "E":
            # sanity check k/d
            for i in range(2):
                # mildly retarded
                if kills[i] != deaths[(i + 1) % 2]:
                    out += f"Incorrect kill (team {i + 1})/death (team {(i + 1) % 3}) count detected in:\n{game}\n"
        
        # sanity check score and outcome
        if mode != "DO":
            if outcome > 0:
                if max(score) != score[outcome - 1]:
                    out += f"Incorrect score/outcome detected in:\n{game}\n"
            else:
                if score[0] != score[1]:
                    out += f"Incorrect score/outcome detected in:\n{game}\n"
    if out:
        return out
    return "No errors detected"


def main():
    try:
        return sanity_check(read_file("matches.txt"))
    except:
        return "Something must be very messed up in your input, sanity failed."


if __name__ == "__main__":
    print(main())
