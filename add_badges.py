from util import *
from datetime import datetime


def introduce_badges():
    db = connect()
    db.players.update_many({}, {"$set": {"badges": []}})
    print("Successfully introduced badges!")
    return


def add_badge(player: str, date: str, rank: str = "", mode: str = "", season: int = None, name=None):
    db = connect()
    badges = db.players.find_one({"name": player})["badges"]
    new_badge = {"date": date}
    # there's probably a more elegant way to create these dicts
    if rank:
        new_badge["rank"] = rank
    if mode:
        new_badge["mode"] = mode
    if season:
        new_badge["season"] = season
    if name:
        new_badge["name"] = name
    badges.append(new_badge)
    badges = sorted(badges, key=lambda d: datetime.strptime(d["date"], "%Y-%m-%d"))
    db.players.update_one({"name": player}, {"$set": {"badges": badges}})
    print(f"Successfully added badge!")
    return


if __name__ == "__main__":
    introduce_badges()

    # all the badges so far wowie

    # 1
    season = 1

    add_badge("untroversion", "2020-07-01", "Rookie", "", season, f"Season {season} Rookie of the Season")

    add_badge("DevelSpirit", "2020-07-01", "1st", "Manhunt", season)
    add_badge("Tha Fazz", "2020-07-01", "2nd", "Manhunt", season)
    add_badge("Dellpit", "2020-07-01", "3rd", "Manhunt", season)

    # 2
    season = 2

    add_badge("Sugarfree", "2022-02-01", "Rookie", "", season, f"Season {season} Rookie of the Season")

    add_badge("Edi", "2022-02-01", "1st", "AA Defending", season)
    add_badge("piesio1", "2022-02-01", "2nd", "AA Defending", season)
    add_badge("robin331", "2022-02-01", "3rd", "AA Defending", season)
    add_badge("dreamkiller2000", "2022-02-01", "1st", "AA Running", season)
    add_badge("DurandalSword", "2022-02-01", "2nd", "AA Running", season)
    add_badge("Onyxies", "2022-02-01", "3rd", "AA Running", season)

    add_badge("DevelSpirit", "2021-11-01", "1st", "Manhunt", season)
    add_badge("Auditore92", "2021-11-01", "2nd", "Manhunt", season)
    add_badge("Jelko", "2021-11-01", "3rd", "Manhunt", season)
    add_badge("DevelSpirit", "2021-11-11", "Trophy", "", "", f"Manhunt Season {season} Playoffs Champion")
    add_badge("EternityEzioWolf", "2021-11-11", "Trophy", "", "", f"Manhunt Season {season} Playoffs Champion")
    add_badge("Jelko", "2021-11-11", "Trophy", "", "", f"Manhunt Season {season} Playoffs Champion")

    add_badge("DevelSpirit", "2022-02-01", "1st", "Escort", season)
    add_badge("Dellpit", "2022-02-01", "2nd", "Escort", season)
    add_badge("Sugarfree", "2022-02-18", "2nd", "Escort", season)
    add_badge("DevelSpirit", "2022-02-18", "Trophy", "", "", f"Escort Season {season} Playoffs Champion")
    add_badge("Tha Fazz", "2022-02-18", "Trophy", "", "", f"Escort Season {season} Playoffs Champion")

    # 3
    season = 3
    
    add_badge("MilliaRage89", "2022-11-01", "Rookie", "", season, f"Season {season} Rookie of the Season")

    add_badge("DevelSpirit", "2022-06-01", "1st", "Manhunt", season)
    add_badge("Tha Fazz", "2022-06-01", "2nd", "Manhunt", season)
    add_badge("Dellpit", "2022-06-01", "3rd", "Manhunt", season)

    add_badge("DevelSpirit", "2022-11-01", "1st", "Escort", season)
    add_badge("Dellpit", "2022-11-01", "2nd", "Escort", season)
    add_badge("Jelko", "2022-11-01", "3rd", "Escort", season)

