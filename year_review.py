import discord
from synergy import date_convert, find_games, find_synergy, parse_matches, parse_matches_elo, map_synergy, map_ffa_synergy, parse_ffa
from util import *
from datetime import datetime, date
from collections import defaultdict


def parse_stats(block1: str, block2: str):
    import re
    stats = defaultdict(dict)

    # Parse block1
    for line in block1.splitlines():
        m = re.match(r"(.+?): (\d+)% \((\d+) / (\d+) \| (\d+) ties\)", line.strip())
        if m:
            name, pct, wins, total, ties = m.groups()
            stats[name].update({
                "win_rate": int(pct),
                "wins": int(wins),
                "total": int(total),
                "ties": int(ties)
            })

    # Parse block2
    for line in block2.splitlines():
        m = re.match(r"(.+?): (\d+), ([\d.]+) \((\d+) games\)", line.strip())
        if m:
            name, score, ratio, games = m.groups()
            stats[name].update({
                "score": int(score),
                "k/d": float(ratio),
                "games": int(games)
            })

    return dict(stats)



def combine_stats(list_of_blocks):
    """
    list_of_blocks: list of (block1, block2) pairs
    Returns a dict with combined stats per name.
    """
    combined = defaultdict(lambda: {
        "win_rate": 0, "wins": 0, "total": 0, "ties": 0,
        "score": 0, "k/d_sum": 0.0, "games": 0
    })

    for block1, block2 in list_of_blocks:
        stats = parse_stats(block1, block2)
        for name, s in stats.items():
            combined[name]["win_rate"] += s.get("win_rate", 0)   # careful: % not additive
            combined[name]["wins"]    += s.get("wins", 0)
            combined[name]["total"]   += s.get("total", 0)
            combined[name]["ties"]    += s.get("ties", 0)
            combined[name]["score"]   += s.get("score", 0)
            combined[name]["k/d_sum"] += s.get("k/d", 0.0)
            combined[name]["games"]   += s.get("games", 0)

    # Optionally recompute average ratio
    for name, s in combined.items():
        if s["games"] > 0:
            s["k/d"] = s["k/d_sum"] / combined[name]["games"]
        else:
            s["k/d"] = 0.0
        del s["k/d_sum"]

    return dict(combined)


def create_review(player, year=datetime.now().year):
    embedVar = discord.Embed(title=f"{player}'s {year} Assassins' Network Recap", url = "https://assassins.network/", color = 0xffa8e8)
    embedVar.set_thumbnail(url="https://assassins.network/static/an_logo_white.png")
    formatted_modes = [check_mode(mode).title() for mode in ALL_MODES]
    db = connect()
    player = identify_player(db, player)
    name = player["name"]
    year_start = date(year, 1, 1).strftime("%Y-%m-%d")
    year_end = date(year, 12, 31).strftime("%Y-%m-%d")
    year_range = (year_start, year_end)
    games_dict = {k: find_games(db, player["name"], k, date_range=year_range) for k in formatted_modes}

    # most played mode
    max_games = 0
    total_games = 0
    top_mode = None
    map_stats = []
    modes_played = 0
    best_score = 0
    total_score = 0
    worst_score = 100000
    for mode_formatted in formatted_modes:
        mode_count = len(list(games_dict[mode_formatted][0]))
        total_games += mode_count
        if mode_count:
            modes_played += 1
            if mode_count > max_games:
                max_games = mode_count
                top_mode = mode_formatted
            if check_mode(mode_formatted, short=True) in TEAM_MODES:
                map_stats.append(map_synergy(name, mode_formatted, 1, year_range))

                for m in games_dict[mode_formatted][0]:
                    for i in [1, 2]:
                        for p in m[f"team{i}"]:
                            if p["player"] == name:
                                best_score = max(p["score"], best_score)
                                worst_score = min(p["score"], worst_score)
                                total_score += p["score"]

            else:
                map_stats.append(map_ffa_synergy(name, mode_formatted, 1, year_range))

                for m in games_dict[mode_formatted][0]:
                    for p in m["players"]:
                        if p["player"] == name:
                            best_score = max(p["score"], best_score)
                            worst_score = min(p["score"], worst_score)
                            total_score += p["score"]

    if not total_games:
        embedVar.add_field(name=f":thumbsdown: You suck", value="You didn't play AC at all!")
        return embedVar
    embedVar.add_field(name=f":one_thirty: Total games played", value=f"{total_games}", inline=True)
    #print(f"Total games played: {total_games}")
    embedVar.add_field(name=f":shark: Most played mode", value=f"{top_mode} ({max_games})", inline=True)
    #print(f"Most played mode: {top_mode} ({max_games})")
    embedVar.add_field(name=f":rainbow_flag: Modes played", value=f"{modes_played}", inline=True)
    combined_map_stats = combine_stats(map_stats)
    map_keys = {"games": ":video_game: Most played map", "win_rate": ":medal: Best map win rate", "score": ":100: Best map average score"}
    best_maps = {k: max(combined_map_stats.items(), key=lambda kv: kv[1][k]) for k in map_keys}
    for k in map_keys.keys():
        if k != "win_rate":
            val = round(best_maps[k][1][k], 2)
        else:
            val = f"{round(best_maps[k][1][k], 2)}%"
        embedVar.add_field(name=f"{map_keys[k]}", value=f"{best_maps[k][0]} ({val})", inline=True)
        #print(f"{k}: {best_maps[k][0]} ({best_maps[k][1][k]})")

    embedVar.add_field(name=f":mountain: Best session score", value=f"{best_score}", inline=True)
    embedVar.add_field(name=f":wheelchair: Worst session score", value=f"{worst_score}", inline=True)
    embedVar.add_field(name=f":cricket: Average score", value=f"{round(total_score / total_games, 2)}", inline=True)

    dicts = [{"Nothing": [0] * 5}]
    # best teammate
    for mode_formatted in formatted_modes:
        games, igns = games_dict[mode_formatted]
        mode_dict = {}
        if check_mode(mode_formatted, short=True) in TEAM_MODES:
            synergies = parse_matches(db, games, igns, min_games=1)
            for k in synergies[1].keys():
                w = synergies[1][k][2]
                g = synergies[1][k][1]
                games = sum([synergies[i][k][1] if k in synergies[i] else 0 for i in range(2)])
                elo_change = synergies[1][k][4]
                if k not in synergies[0]:
                    elo_lost = 0
                else:
                    elo_lost = synergies[0][k][4]
                mode_dict[k] = [w, g, games, elo_change, elo_lost]
        else:
            synergies = parse_ffa(db, games, igns, min_games=1)
            for k in synergies.keys():
                g = synergies[k]["games"]
                mode_dict[k] = [0, 0, g, 0, 0]
        dicts.append(mode_dict)
    combined = defaultdict(lambda: [0] * len(next(iter(dicts[0].values()))))
    
    for d in dicts:
        for name, stats in d.items():
            combined[name] = [a + b for a, b in zip(combined[name], stats)]
    
    adjusted = dict(combined)
    for name, stats in adjusted.items():
        adjusted[name] = [stats[0] / max(stats[1], 1), stats[1], stats[2], stats[3], stats[4]]

    del adjusted[player["name"]]
    num_stats = len(next(iter(adjusted.values())))
    winners = {}
    
    def add_stat_embed(stat, i, func=max):
        key, value = func(adjusted.items(), key=lambda kv: kv[1][i])
        if not value[i]:
            key = "Nobody"
        winners[stat] = (key, value[i])
        if i > 0:
            str_val = round(value[i], 2)
        else:
            str_val = f"{100 * round(value[i], 2)}%"
        return f":{stats[stat]}: {stat}", f"{key} ({str_val})"

    stats = {"Best win rate with": "military_medal", "Most games on team with": "people_hugging", "Most games in lobby with": "people_holding_hands", "Most elo gained with": "chart_with_upwards_trend", "Biggest elo stealer": "ninja", "Most elo lost with": "chart_with_downwards_trend"}
    for i in range(num_stats):
        stat = list(stats.keys())[i]
        name, value = add_stat_embed(stat, i, max)
        embedVar.add_field(name=name, value=value, inline=True)
        if "Most elo gained with" in stat:
            stat = list(stats.keys())[-1]
            name, value = add_stat_embed(stat, i, min)
            embedVar.add_field(name=name, value=value, inline=True)
        #print(f"{stat}: {key} ({value[i]})")

    return embedVar
    # most elo won with teammate
    # most games played with
    # most games on team with
    # most games played against
    # year stats: games played, average score, best score, k/d, peak MMR
    # most played map
    # best map

if __name__ == "__main__":
    create_review("Gummy")
