from util import *
from datetime import datetime


def introduce_badges():
    db = connect()
    db.players.update_many({}, {"$set": {"badges": []}})
    print("Successfully introduced badges!")
    return


def add_badge(player: str, date: str, rank: str = "", mode: str = "", season: int = None, name=None, medal=None):
    db = connect()
    badges = db.players.find_one({"name": player})["badges"]
    new_badge = {"date": date}
    # there's probably a more elegant way to create these dicts
    if rank:
        new_badge["rank"] = rank
    if mode:
        new_badge["mode"] = mode
    else:
        new_badge["mode"] = "all"
    if season:
        new_badge["season"] = season
    if name:
        new_badge["name"] = name
    if medal:
        new_badge["medal"] = medal
    badges.append(new_badge)
    badges = sorted(badges, key=lambda d: datetime.strptime(d["date"], "%Y-%m-%d"))
    db.players.update_one({"name": player}, {"$set": {"badges": badges}})
    print(f"Successfully added badge!")
    return


def readable_badges(player, discord=True):
    db = connect()
    badges_list = identify_player(db, player)["badges"]

    if len(badges_list) == 0:
        return ""

    badges = ""
    for badge in badges_list:
        try:
            rank = badge["rank"]
        except:
            pass
        try:
            mode = badge["mode"]
        except:
            pass
        try:
            season = badge["season"]
        except:
            pass
        try:
            name = badge["name"]
        except:
            pass
        if rank == "1st":
            if discord:
                medal = ":first_place:"
            else:
                medal = "&#129351"
        elif rank == "2nd":
            if discord:
                medal = ":second_place:"
            else:
                medal = "&#129352"
        elif rank == "3rd":
            if discord:
                medal = ":third_place:"
            else:
                medal = "&#129353"
        elif rank == "Trophy":
            if discord:
                medal = ":trophy:"
            else:
                medal = "&#127942"
        elif rank == "Rookie":
            if discord:
                medal = ":beginner:"
            else:
                medal = "&#128304"
        elif rank == "Special":
            if discord:
                medal = ":star:"
            else:
                medal = "&#127941"
        elif rank == "All-Star":
            if discord:
                medal = ":star:"
            else:
                medal = "&#11088"
        elif rank == "Custom":
            if discord:
                medal = badge["medal"]["Discord"]
            else:
                medal = badge["medal"]["HTML"]
        else:
            raise ValueError("Unknown rank! Options are: 1st, 2nd, 3rd, Trophy, Rookie, Special, All-Star, and Custom.")
        if rank in ["Trophy", "All-Star", "Custom", "Special"]:
            badges = f"{medal} {name}\n" + badges
        elif rank == "Rookie":
            badges = f"{medal} Season {season} Rookie of the Season\n" + badges
        else:
            badges = f"{medal} Season {season} {mode} {rank} Place\n" + badges
    return badges[:-1]




if __name__ == "__main__":
    introduce_badges()

    # all the badges so far wowie

    # 1
    season = 1

    add_badge("untroversion", "2020-07-01", "Rookie", "all", season, f"Season {season} Rookie of the Season")

    add_badge("DevelSpirit", "2020-07-01", "1st", "Manhunt", season)
    add_badge("Tha Fazz", "2020-07-01", "2nd", "Manhunt", season)
    add_badge("Dellpit", "2020-07-01", "3rd", "Manhunt", season)

#    add_badge("DevelSpirit", "2020-07-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
#    add_badge("Tha Fazz", "2020-07-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
#    add_badge("Dellpit", "2020-07-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
    add_badge("BigDriply", "2020-07-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
    add_badge("Jelko", "2020-07-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
    add_badge("EternityEzioWolf", "2020-07-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")

    # 2
    season = 2

    add_badge("Sugarfree", "2022-02-01", "Rookie", "all", season, f"Season {season} Rookie of the Season")

    add_badge("Edi", "2022-02-01", "1st", "AA Defending", season)
    add_badge("piesio1", "2022-02-01", "2nd", "AA Defending", season)
    add_badge("robin331", "2022-02-01", "3rd", "AA Defending", season)
    add_badge("dreamkiller2000", "2022-02-01", "1st", "AA Running", season)
    add_badge("DurandalSword", "2022-02-01", "2nd", "AA Running", season)
    add_badge("Onyxies", "2022-02-01", "3rd", "AA Running", season)

    add_badge("Jelko", "2021-07-25", "Trophy", "Assassinate", season, f"El's Cancer Fundraiser Assassinate Tournament Champion")
    add_badge("Dellpit", "2021-07-25", "Trophy", "Assassinate", season, f"El's Cancer Fundraiser Assassinate Tournament Champion")

    add_badge("DevelSpirit", "2021-11-01", "1st", "Manhunt", season)
    add_badge("Auditore92", "2021-11-01", "2nd", "Manhunt", season)
    add_badge("Jelko", "2021-11-01", "3rd", "Manhunt", season)

#    add_badge("Edi", "2022-02-01", "All-Star", "AA Defending", season, f"Season {season} Artifact Assault All-Star Defender")
#    add_badge("piesio1", "2022-02-01", "All-Star", "AA Defending", season, f"Season {season} Artifact Assault All-Star Defender")
#    add_badge("robin331", "2022-02-01", "All-Star", "AA Defending", season, f"Season {season} Artifact Assault All-Star Defender")
    add_badge("Onyxies", "2022-02-01", "All-Star", "AA Defending", season, f"Season {season} Artifact Assault All-Star Defender")

#    add_badge("dreamkiller2000", "2022-02-01", "All-Star", "AA Running", season, f"Season {season} Artifact Assault All-Star Runner")
#    add_badge("DurandalSword", "2022-02-01", "All-Star", "AA Running", season, f"Season {season} Artifact Assault All-Star Runner")
#    # Onyxies only has 44 games as a runner and 185 as a defender so let's give priority there
#    #add_badge("Onyxies", "2022-02-01", "All-Star", "AA Running", season, f"Season {season} Artifact Assault All-Star Runner")
    add_badge("Reaper19111", "2022-02-01", "All-Star", "AA Running", season, f"Season {season} Artifact Assault All-Star Runner")
    # replacement for Onyxies
    add_badge("Sugarfree", "2022-02-01", "All-Star", "AA Running", season, f"Season {season} Artifact Assault All-Star Runner")

#    add_badge("DevelSpirit", "2021-11-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
#    add_badge("Auditore92", "2021-11-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
#    add_badge("Jelko", "2021-11-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
    add_badge("Tha Fazz", "2021-11-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
    add_badge("Dellpit", "2021-11-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
    add_badge("FatalWolf", "2021-11-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")

    add_badge("DevelSpirit", "2021-11-11", "Custom", "Manhunt", season, f"Season {season} Manhunt All-Star Match Champion", {"Discord": ":star2:", "HTML": "&#127775"})
    add_badge("EternityEzioWolf", "2021-11-11", "Custom", "Manhunt", season, f"Season {season} Manhunt All-Star Match Champion", {"Discord": ":star2:", "HTML": "&#127775"})
    add_badge("Jelko", "2021-11-11", "Custom", "Manhunt", season, f"Season {season} Manhunt All-Star Match Champion", {"Discord": ":star2:", "HTML": "&#127775"})

    add_badge("DevelSpirit", "2022-02-01", "1st", "Escort", season)
    add_badge("Dellpit", "2022-02-01", "2nd", "Escort", season)
    add_badge("Sugarfree", "2022-02-01", "2nd", "Escort", season)

#    add_badge("DevelSpirit", "2022-02-01", "All-Star", "Escort", season, f"Season {season} Escort All-Star")
#    add_badge("Dellpit", "2022-02-01", "All-Star", "Escort", season, f"Season {season} Escort All-Star")
#    add_badge("Sugarfree", "2022-02-01", "All-Star", "Escort", season, f"Season {season} Escort All-Star")
#    add_badge("Tha Fazz", "2022-02-01", "All-Star", "Escort", season, f"Season {season} Escort All-Star")

    add_badge("DevelSpirit", "2022-02-18", "Custom", "Escort", season, f"Season {season} Escort All-Star Match Champion", {"Discord": ":star2:", "HTML": "&#127775"})
    add_badge("Tha Fazz", "2022-02-18", "Custom", "Escort", season, f"Season {season} Escort All-Star Match Champion", {"Discord": ":star2:", "HTML": "&#127775"})

    # 3
    season = 3
    
    add_badge("MilliaRage89", "2022-11-01", "Rookie", "all", season, f"Season {season} Rookie of the Season")

    add_badge("DevelSpirit", "2022-06-01", "1st", "Manhunt", season)
    add_badge("Tha Fazz", "2022-06-01", "2nd", "Manhunt", season)
    add_badge("Dellpit", "2022-06-01", "3rd", "Manhunt", season)

#    add_badge("DevelSpirit", "2022-06-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
#    add_badge("Tha Fazz", "2022-06-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
#    add_badge("Dellpit", "2022-06-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
    add_badge("Jelko", "2022-06-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
    add_badge("EternityEzioWolf", "2022-06-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
    add_badge("Auditore92", "2022-06-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")

    add_badge("DevelSpirit", "2022-11-01", "1st", "Escort", season)
    add_badge("Dellpit", "2022-11-01", "2nd", "Escort", season)
    add_badge("Jelko", "2022-11-01", "3rd", "Escort", season)

#    add_badge("DevelSpirit", "2022-11-01", "All-Star", "Escort", season, f"Season {season} Escort All-Star")
#    add_badge("Dellpit", "2022-11-01", "All-Star", "Escort", season, f"Season {season} Escort All-Star")
#    add_badge("Jelko", "2022-11-01", "All-Star", "Escort", season, f"Season {season} Escort All-Star")
    add_badge("Sugarfree", "2022-11-01", "All-Star", "Escort", season, f"Season {season} Escort All-Star")

    season = 4

    add_badge("piesio1", "2023-05-01", "1st", "AA Defending", season)
    add_badge("Edi", "2023-05-01", "2nd", "AA Defending", season)
    add_badge("dreamkiller2000", "2023-05-01", "3rd", "AA Defending", season)
    add_badge("Sugarfree", "2023-05-01", "All-Star", "AA Defending", season, f"Season {season} Artifact Assault All-Star Defender")

    add_badge("Sugarfree", "2023-05-01", "1st", "AA Running", season)
    add_badge("Onyxies", "2023-05-01", "2nd", "AA Running", season)
    add_badge("Dusk", "2023-05-01", "3rd", "AA Running", season)
    add_badge("dreamkiller2000", "2023-05-01", "All-Star", "AA Running", season, f"Season {season} Artifact Assault All-Star Runner")

    add_badge("Edi", "2023-05-01", "1st", "Domination", season)
    add_badge("Rorce", "2023-05-01", "2nd", "Domination", season)
    add_badge("Lunaire.-", "2023-05-01", "3rd", "Domination", season)
    add_badge("Jelko", "2023-05-01", "All-Star", "Domination", season, f"Season {season} Domination All-Star")
    add_badge("Sugarfree", "2023-05-01", "All-Star", "Domination", season, f"Season {season} Domination All-Star")
    add_badge("Onyxies", "2023-05-01", "All-Star", "Domination", season, f"Season {season} Domination All-Star")
    add_badge("Lars", "2023-05-01", "All-Star", "Domination", season, f"Season {season} Domination All-Star")
    add_badge("Xanthex", "2023-05-01", "All-Star", "Domination", season, f"Season {season} Domination All-Star")

    add_badge("Dellpit", "2023-05-01", "1st", "Manhunt", season)
    add_badge("Auditore92", "2023-05-01", "2nd", "Manhunt", season)
    add_badge("DevelSpirit", "2023-05-01", "3rd", "Manhunt", season)
    add_badge("EternityEzioWolf", "2023-05-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
    add_badge("xCanibal96", "2023-05-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")
    add_badge("Ted95On", "2023-05-01", "All-Star", "Manhunt", season, f"Season {season} Manhunt All-Star")

    add_badge("Tha Fazz", "2023-05-01", "1st", "Escort", season)
    add_badge("Dellpit", "2023-05-01", "2nd", "Escort", season)
    add_badge("Ted95On", "2023-05-01", "3rd", "Escort", season)
    add_badge("Crispi Kreme", "2023-05-01", "All-Star", "Escort", season, f"Season {season} Escort All-Star")
    add_badge("Levi", "2023-05-01", "Rookie", "all", season, f"Season {season} Rookie of the Season")

    season = 5

    add_badge("DurandalSword", "2023-10-28", "Trophy", "Escort", season, "VERY EPIC GAMER")
    add_badge("Reaper19111", "2023-10-28", "Trophy", "Escort", season, "VERY EPIC GAMER")
    add_badge("Edi", "2023-10-28", "Custom", "Escort", season, "EPIC GAMER", {"Discord": ":medal:", "HTML": "&#127941"})
    add_badge("Rorce", "2023-10-28", "Custom", "Escort", season, "EPIC GAMER", {"Discord": ":medal:", "HTML": "&#127941"})
    add_badge("MilliaRage89", "2023-10-28", "Custom", "Escort", season, "EPIC GAMER", {"Discord": ":medal:", "HTML": "&#127941"})
    add_badge("Kapi", "2023-10-28", "Custom", "Escort", season, "EPIC GAMER", {"Discord": ":medal:", "HTML": "&#127941"})
    add_badge("Cota", "2023-10-28", "Custom", "Escort", season, "EPIC GAMER", {"Discord": ":medal:", "HTML": "&#127941"})
    add_badge("Ariiro", "2023-10-28", "Custom", "Escort", season, "EPIC GAMER", {"Discord": ":medal:", "HTML": "&#127941"})
    
    add_badge("Edi", "2024-03-26", "1st", "AA Defending", season)
    add_badge("Onyxies", "2024-03-26", "2nd", "AA Defending", season)
    add_badge("piesio1", "2024-03-26", "3rd", "AA Defending", season)
    add_badge("robin331", "2024-03-26", "All-Star", "AA Defending", season, f"Season {season} Artifact Assault All-Star Defender")

    add_badge("Sugarfree", "2024-03-26", "1st", "AA Running", season)
    add_badge("Reaper19111", "2024-03-26", "2nd", "AA Running", season)
    add_badge("D4", "2024-03-26", "3rd", "AA Running", season)
    add_badge("GamerPrince98", "2024-03-26", "All-Star", "AA Running", season, f"Season {season} Artifact Assault All-Star Runner")

    add_badge("Jelko", "2024-03-26", "1st", "Assassinate", season)
    add_badge("Lime232", "2024-03-26", "2nd", "Assassinate", season)
    add_badge("Ruslan", "2024-03-26", "3rd", "Assassinate", season)

    add_badge("Dellpit", "2024-03-26", "1st", "Escort", season)
    add_badge("Sugarfree", "2024-03-26", "2nd", "Escort", season)
    add_badge("DevelSpirit", "2024-03-26", "3rd", "Escort", season)
    add_badge("Tha Fazz", "2024-03-26", "All-Star", "Escort", season, f"Season {season} Escort All-Star")
    add_badge("Lunaire.-", "2024-03-26", "Rookie", "all", season, f"Season {season} Rookie of the Season")

    season = 6
    add_badge("Edi", "2024-12-28", "1st", "Domination", season)
    add_badge("Xanthex", "2024-12-28", "2nd", "Domination", season)
    add_badge("Lars", "2024-12-28", "3rd", "Domination", season)
    #add_badge("Lunaire.-", "2024-12-28", "All-Star", "Domination", season, f"Season {season} Domination All-Star")
    #add_badge("Cota", "2024-12-28", "All-Star", "Domination", season, f"Season {season} Domination All-Star")
    add_badge("Gummy", "2024-12-28", "All-Star", "Domination", season, f"Season {season} Domination All-Star")
    #add_badge("Arun", "2024-12-28", "All-Star", "Domination", season, f"Season {season} Domination All-Star")
    add_badge("Christian", "2024-12-28", "All-Star", "Domination", season, f"Season {season} Domination All-Star")
    add_badge("Gummy", "2024-12-28", "Rookie", "all", season, f"Season {season} Rookie of the Season")


    add_badge("Edi", "2024-12-28", "Custom", "Domination", season, f"Season {season} Domination All-Star Match Champion", {"Discord": ":star2:", "HTML": "&#127775"})
    add_badge("Lars", "2024-12-28", "Custom", "Domination", season, f"Season {season} Domination All-Star Match Champion", {"Discord": ":star2:", "HTML": "&#127775"})
    add_badge("Xanthex", "2024-12-28", "Custom", "Domination", season, f"Season {season} Domination All-Star Match Champion", {"Discord": ":star2:", "HTML": "&#127775"})
    add_badge("Lunaire.-", "2024-12-28", "Custom", "Domination", season, f"Season {season} Domination All-Star Match Champion", {"Discord": ":star2:", "HTML": "&#127775"})
    add_badge("Cota", "2024-12-28", "Custom", "Domination", season, f"Season {season} Domination All-Star Match Champion", {"Discord": ":star2:", "HTML": "&#127775"})
    add_badge("Arun", "2024-12-28", "Custom", "Domination", season, f"Season {season} Domination All-Star Match Champion", {"Discord": ":star2:", "HTML": "&#127775"})

    add_badge("Lunaire.-", "2024-03-26", "1st", "Deathmatch", season)
    add_badge("Arun", "2024-03-26", "2nd", "Deathmatch", season)
    add_badge("Xanthex", "2024-03-26", "3rd", "Deathmatch", season)
    add_badge("Shmush", "2024-12-28", "All-Star", "Deathmatch", season, f"Season {season} Deathmatch All-Star")
    add_badge("Lars", "2024-12-28", "All-Star", "Deathmatch", season, f"Season {season} Deathmatch All-Star")
    add_badge("Kapi", "2024-12-28", "All-Star", "Deathmatch", season, f"Season {season} Deathmatch All-Star")
    add_badge("Christian", "2024-12-28", "All-Star", "Deathmatch", season, f"Season {season} Deathmatch All-Star")
    add_badge("CHUCKIE", "2024-12-28", "All-Star", "Deathmatch", season, f"Season {season} Deathmatch All-Star")

