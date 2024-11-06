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
        map_name = None
        host_player = None
        if "$" in mode:
            temp = mode.split("$")
            mode = temp[0]
            if len(temp) == 3:
                map_name = temp[1]
                host_player = temp[2]
            else:
                try:
                    map_name = identify_map(temp[1])
                except:
                    try:
                        host_player = identify_player(db, temp[1])
                    except:
                        out += f"Unknown map or host detected in:\n{game}\n"
        mode = str(mode).lower()
        # sanity check mode
        if mode not in GAME_MODES:
            out += f"Unknown mode {mode} detected in:\n{game}\n"
        
        # sanity check map name
        if map_name:
            try:
                identify_map(map_name)
            except:
                out += f"Unknown map detected in:\n{game}\n"

        num_delim = 3
        all_gamers = []

        if mode not in FFA_MODES:
            num_players = int(players[1])
            outcome = players[2]
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
            if mode == "aa":
                num_delim += 1

        else:
            kills = 0
            deaths = 0
            score = 0
            gamers = players[1:]

        for j in range(len(gamers)):
            # check for $ delim count
            if gamers[j].count("$") != num_delim:
                out += f"Incorrect $ delim count detected for {gamers[j]} in:\n{game}\n"
                continue
            player = gamers[j].split("$")

            # check if player in db
            try:
                player[0] = identify_player(db, player[0])["name"]
            except ValueError as e:
                out += str(e).replace("insert_player: p", "P") + ":\n" + game + "\n"

            # check for duplicate players
            if player[0] in all_gamers:
                out += f"Duplicate player {player[0]} detected in:\n{game}\n"
            else:
                all_gamers.append(player[0])

            # sum score
            if mode != "aa":
                try:
                    if mode not in FFA_MODES:
                        score[i] += int(player[1])
                    else:
                        score += int(player[1])
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
                if mode not in FFA_MODES:
                    kills[i] += int(player[2])
                else:
                    kills += int(player[2])
            except ValueError:
                out += f"Detected nonnumerical input for {gamers[j]} in:\n{game}\n"
            try:
                if mode not in FFA_MODES:
                    deaths[i] += int(player[3])
                else:
                    deaths += int(player[3])
            except ValueError:
                out += f"Detected nonnumerical input for {gamers[j]} in:\n{game}\n"

            if mode not in FFA_MODES:
                # switch to next team
                if j == num_players - 1:
                    i = 1
        
        # sanity check host player
        if host_player:
            try:
                identify_player(db, host_player)
                if host_player not in all_gamers:
                    out += f"{host_player} is host yet not found in player list for {game}"
            except:
                out += f"Unknown host detected in:\n{game}\n"

        # k/d check unfortunately doesn't work for console escort
        if mode != "e":
            if mode not in FFA_MODES:
                # sanity check k/d
                for i in range(2):
                    # mildly retarded
                    if kills[i] != deaths[(i + 1) % 2]:
                        out += f"Incorrect kill (team {i + 1})/death (team {(i + 1) % 3}) count detected in:\n{game}\n"
            elif kills != deaths:
                out += f"Incorrect kill/death count detected in:\n{game}\n"

        # sanity check score and outcome
        if mode not in FFA_MODES and mode != "do":
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
    except Exception as e:
        print(e)
        return f"Something must be very messed up in your input, sanity failed.\n{e}"


if __name__ == "__main__":
    print(main())
