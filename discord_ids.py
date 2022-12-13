from teams import connect

db = connect()

ids = "/home/dell/discord_ids.txt"

with open(ids) as data:
    data = data.read().replace("\t", ",").replace("\n", ",").split(",")

names = data[::2]
ids = data[1::2]

for i in range(len(names) - 1):
    print(f"Adding {names[i]}'s ID: {ids[i]}")
    db.players.update_one({"name":names[i]}, {"$set":{"discord_id":ids[i]}})

print("Done.")
