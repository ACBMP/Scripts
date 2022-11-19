from util import *


def add_badge(player: str, rank: str, mode: str, season: int, name=None):
    db = connect()
    badges = db.players.find_one({"name": player})["badges"]
    if rank == "1st":
        medal = "&#129351"
    elif rank == "2nd":
        medal = "&#129352"
    elif rank == "3rd":
        medal = "&#129353"
    elif rank == "Trophy":
        medal = "&#127942"
    elif rank == "Rookie":
        medal = "&#128304"
    elif rank == "Special":
        medal = "&#127941"
    else:
        raise ValueError("Unknown rank! Options are: 1st, 2nd, 3rd, Trophy, and Special.")
    if rank in ["Trophy", "Special"]:
        badges = f"<span title=\"{name}\">{medal}</span>" + badges
    elif rank == "Rookie":
        badges = f"<span title=\"Season {season} Rookie of the Season\">{medal}</span>" + badges
    else:
        badges = f"<span title=\"Season {season} {mode} {rank} Place\">{medal}</span>" + badges
    db.players.update_one({"name": player}, {"$set": {"badges": badges}})
    print(f"Successfully added badge!")
    return


def introduce_badges():
    db = connect()
    db.players.update_many({}, {"$set": {"badges": ""}})
    print("Successfully introduced badges!")
    return


if __name__ == "__main__":
    introduce_badges()

    # all the badges so far wowie

    # 1
    season = 1

    add_badge("untroversion", "Rookie", "", season, f"Season {season} Rookie of the Season")

    add_badge("DevelSpirit", "1st", "Manhunt", season)
    add_badge("Tha Fazz", "2nd", "Manhunt", season)
    add_badge("Dellpit", "3rd", "Manhunt", season)

    # 2
    season = 2

    add_badge("Sugarfree", "Rookie", "", season, f"Season {season} Rookie of the Season")

    add_badge("Edi", "1st", "AA Defending", season)
    add_badge("piesio1", "2nd", "AA Defending", season)
    add_badge("robin331", "3rd", "AA Defending", season)
    add_badge("dreamkiller2000", "1st", "AA Running", season)
    add_badge("DurandalSword", "2nd", "AA Running", season)
    add_badge("Onyxies", "3rd", "AA Running", season)

    add_badge("DevelSpirit", "1st", "Manhunt", season)
    add_badge("Auditore92", "2nd", "Manhunt", season)
    add_badge("Jelko", "3rd", "Manhunt", season)
    add_badge("DevelSpirit", "Special", "", "", f"Manhunt Season {season} Playoffs Champion")
    add_badge("EternityEzioWolf", "Special", "", "", f"Manhunt Season {season} Playoffs Champion")
    add_badge("Jelko", "Special", "", "", f"Manhunt Season {season} Playoffs Champion")

    add_badge("DevelSpirit", "1st", "Escort", season)
    add_badge("Dellpit", "2nd", "Escort", season)
    add_badge("Sugarfree", "2nd", "Escort", season)
    add_badge("DevelSpirit", "Special", "", "", f"Escort Season {season} Playoffs Champion")
    add_badge("Tha Fazz", "Special", "", "", f"Escort Season {season} Playoffs Champion")

    # 3
    season = 3
    
    add_badge("MilliaRage89", "Rookie", "", season, f"Season {season} Rookie of the Season")

    add_badge("DevelSpirit", "1st", "Manhunt", season)
    add_badge("Tha Fazz", "2nd", "Manhunt", season)
    add_badge("Dellpit", "3rd", "Manhunt", season)

    add_badge("DevelSpirit", "1st", "Escort", season)
    add_badge("Dellpit", "2nd", "Escort", season)
    add_badge("Jelko", "3rd", "Escort", season)

