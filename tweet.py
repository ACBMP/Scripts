import botconfig as conf
from teams import connect
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import six
import tweepy
import random

def generate_table(table, df, rowLabels=None):
    """
    generic function to generate table images
    requires the following to be set:
    table: table file save location
    df: table dataframe
    rowLabels: optional row labels
    """
    # https://stackoverflow.com/questions/26678467/export-a-pandas-dataframe-as-a-table-image
    def render_mpl_table(data, col_width=3.0, row_height=0.625, font_size=14,
                         header_color='#000000', row_colors=['#1e1e1e', '#373737'], edge_color='#444444',
                         bbox=[0, 0, 1, 1], header_columns=0,
                         ax=None, **kwargs):
        if ax is None:
            size = (np.array(data.shape[::-1]) + np.array([0, 1])) * np.array([col_width, row_height])
            fig, ax = plt.subplots(figsize=size)
            ax.axis('off')
    
        mpl_table = ax.table(cellText=data.values, bbox=bbox, colLabels=data.columns, **kwargs)

        mpl_table.auto_set_font_size(False)
        mpl_table.set_fontsize(font_size)

        mpl_table.auto_set_column_width(col=list(range(len(data.columns))))
    
        for k, cell in six.iteritems(mpl_table._cells):
            cell.set_edgecolor(edge_color)
            if k[0] == 0 or k[1] < header_columns:
                cell.set_text_props(weight='bold', color='#ececec')
                cell.set_facecolor(header_color)
            else:
                cell.set_text_props(color='#c6c6c6')
                cell.set_facecolor(row_colors[k[0]%len(row_colors) ])
        return ax
    
    render_mpl_table(df, header_columns=0, col_width=1.8, loc="center", cellLoc="center", rowLabels=rowLabels)
    plt.savefig(table, bbox_inches='tight', pad_inches=0, facecolor="#000000")
    print("Created table image")
    return

"""
all of these are to generate frames and with that tables
"""

def rank_frame(mode, table):
    db = connect()

    players = db.players.find({f"{mode}games.total": {"$gte":10}})
    p_sorted = sorted(players, key=lambda player: player[f"{mode}rank"], reverse=False)
    
    
    df = pd.DataFrame()
    ranks = []
    changes = []
    players = []
    points = []

    for p in p_sorted:
        ranks.append(p[f"{mode}rank"])
        changes.append(p[f"{mode}rankchange"])
        players.append(p[f"name"])
        points.append(p[f"{mode}mmr"])

    df['Rank'] = ranks
    #df['Change'] = changes
    df['Player'] = players
    df['Points'] = points
    generate_table(table, df)
    return


def stat_frame(stat, mode, table):
    """
    Winrate
    Highscore
    Avg Score
    K/D
    Avg Kills
    Avg Deaths
    """
    db = connect()

    players = db.players.find({f"{mode}games.total": {"$gte":10}})
    if stat == "Highscore":
        fstat = lambda p: p[f"{mode}stats"]["highscore"]
    elif stat == "Winrate":
        fstat = lambda p: p[f"{mode}games"]["won"] / (p[f"{mode}games"]["won"] + p[f"{mode}games"]["lost"])
    elif stat == "Avg Score":
        fstat = lambda p: p[f"{mode}stats"]["totalscore"] / p[f"{mode}games"]["total"]
    elif stat == "K/D":
        fstat = lambda p: p[f"{mode}stats"]["kills"] / p[f"{mode}stats"]["deaths"]
    elif stat == "Avg Deaths":
        fstat = lambda p: p[f"{mode}stats"]["deaths"] / p[f"{mode}games"]["total"]
    elif stat == "Avg Kills":
        fstat = lambda p: p[f"{mode}stats"]["kills"] / p[f"{mode}games"]["total"]

    p_sorted = sorted(players, key=fstat, reverse=True if stat != "Avg Deaths" else False)
    
    
    df = pd.DataFrame()
    stats = []
    ranks = []
    players = []
    points = []

    for p in p_sorted:
        stats.append("%.2f" % round(fstat(p), 2) if stat != "Highscore" else fstat(p))
        ranks.append(p[f"{mode}rank"])
        players.append(p[f"name"])
        points.append(p[f"{mode}mmr"])

    df[stat] = stats
    df['Rank'] = ranks
    df['Player'] = players
    df['Points'] = points
    generate_table(table, df)
    return


def first_place_frame(mode, table):
    db = connect()

    player = db.players.find_one({f"{mode}rank" : 1})
    
    df = pd.DataFrame()
    df[player['name']] = [str(player[f"{mode}mmr"]),
            str(max(player[f"{mode}history"]["mmrs"])),
            f'{round(player[f"{mode}games"]["won"] * 100 / (player[f"{mode}games"]["lost"] + player[f"{mode}games"]["won"]), 2)}%',
            str(player[f"{mode}games"]["total"]),
            round(player[f"{mode}stats"]["totalscore"] / player[f"{mode}games"]["total"], 2),
            str(player[f"{mode}stats"]["highscore"]),
            round(player[f"{mode}stats"]["kills"] / player[f"{mode}stats"]["deaths"], 2),
            round(player[f"{mode}stats"]["kills"] / player[f"{mode}games"]["total"], 2),
            round(player[f"{mode}stats"]["deaths"] / player[f"{mode}games"]["total"], 2)]
    labels = ["MMR", "Peak MMR", "Winrate", "Games", "Avg Score", "Highscore", "K/D", "Avg Kills", "Avg Deaths"]

    generate_table(table, df, labels)
    return


def tweet(mode):
    # connect to db and twitter api
    db = connect()
    auth = tweepy.OAuthHandler(conf.twitter_authhandler[0], conf.twitter_authhandler[1])
    auth.set_access_token(conf.twitter_access_token[0], conf.twitter_access_token[1])

    api = tweepy.API(auth)

    # find players at rank 1 and high rank change to determine tweet
    hichange = db.players.find({f"{mode}rankchange" : {"$gte" : 2}})

    first = db.players.find({f"{mode}rank" : 1})

    # helper to join player names
    def join_players(players):
        players  = [p for p in players]
        players_joined = ", ".join([p['name'] for p in players])
        return players, players_joined

    # for people reaching first place
    if any([player[f'{mode}rankchange'] > 0 for player in first]):
        if first.count() == 1:
            first = db.players.find({f"{mode}rank" : 1})
            first = first[0]
            text = f"Congratulations to {first['name']} for climbing the mountain and attaining the coveted first place with {first[f'{mode}mmr']} points!"
        else:
            first = db.players.find({f"{mode}rank" : 1})
            players, players_joined = join_players(first)
            text = f"Things are getting spicy as we have a tie at first place between {players_joined} and {players[-1]['name']}."
        table = rank_frame(mode, "table.png")

    # high rankchange
    elif hichange.count() > 0:
        if hichange.count() == 1:
            hichange = hichange[0]
            text = f"Congratulations to {hichange['name']} for climbing from rank {hichange[f'{mode}rank'] + hichange[f'{mode}rankchange']} all the way to rank {hichange[f'{mode}rank']}!"
        else:
            players, players_joined = join_players(hichange)
            text = f"{players_joined} and {players[-1]['name']} did some impressive climbing today!"
        table = rank_frame(mode, "table.png")

    # random
    else:
        r = random.randint(0, 3)

        # so apparently looking for people having reached first place breaks first soooo let's redo the search here
        first = db.players.find({f"{mode}rank" : 1})
        if r == 0:
            if first.count() == 1:
                first = first[0]
                text = f"{first['name']} currently sits atop our leaderboards with {first[f'{mode}mmr']} points."
                first_place_frame(mode, "table.png")
            else:
                players, players_joined = join_players(first)
                text = f"As the rest of our players are fighting to get that sweet, sweet first place, {players_joined}, and {players[-1]['name']} are enjoying their stay there."
                rank_frame(mode, "table.png")

        elif r == 1:
            text = f"The leaderboards have been updated. What are your spicy predictions? Will the Xbox players finally do well on PS3?"
            rank_frame(mode, "table.png")

        elif r == 2:
            text = f"Another day, another AN leaderboard update. Did your favorite player pop off today?"
            rank_frame(mode, "table.png")

        elif r == 3:
            text = f"Anyone feel like playing some ACB today? Our players sure did. Check out the results!"
            rank_frame(mode, "table.png")

        # stat frames
        elif r == 4:
            text = f"How much does your average score even matter? Let's see what our leaderboard says:"
            stat_frame("Avg Score", mode, "table.png")

        elif r == 5:
            text = f"Is lowering your average deaths really the key to winning matches? A peek at our leaderboard might help answer that:"
            stat_frame("Avg Deaths", mode, "table.png")

        elif r == 6:
            text = f"Should you really be boasting your average kills? Let's check in with the leaderboard:"
            stat_frame("Avg Kills", mode, "table.png")

        elif r == 7:
            text = f"High K/D is always better, right? Here's what our leaderboard says:"
            stat_frame("K/D", mode, "table.png")

        elif r == 8:
            text = f"Is your winrate truly the most important stat in an Assassins' Network season? Let's see:"
            stat_frame("Winrate", mode, "table.png")

        elif r == 9:
            text = f"Yeah that 30k looks juicy and all, but how much do highscores say about how good you are? Let's look at our leaderboard:"
            stat_frame("Highscore", mode, "table.png")
   
    status = api.update_with_media("table.png", text)

    print("Tweeted successfully")
    return

if __name__ == "__main__":
    tweet("e")
