import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from functools import partial
from util import util
# import telegram_bot



queues = {"e": [], "mh": [], "do": [], "asb": []}
queue_lengths = {"e": 4, "mh": 6, "do": 8, "asb": 6}
modes_dict = {
    "e": "Escort",
    "mh": "Manhunt",
    "do": "Domination",
    "asb": "Assassinate Brotherhood",
}

def get_job_eta(job):
    """
    Extract job ETA as days, hours, minutes.
    """
    futures = ""
    st = job.trigger.run_date
    td = st - datetime.now(timezone.utc)
    days = td.days
    if days > 0:
        futures += f"{days} days, "
    hours, remainder = divmod(td.seconds, 3600)
    if hours > 0:
        futures += f"{hours} hours, "
    minutes, _ = divmod(remainder, 60)
    if minutes > 0:
        futures += f"{minutes} minutes"
    return futures



class QueueCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_players(self, mode):
        doc = await self.bot.db.queues.find_one({"mode": mode})
        return doc["players"]

    async def add_player(self, mode, player):
        await self.bot.db.queues.update_one(
            {"mode": mode},
            {"$addToSet": {"players": player}}
        )

    async def remove_player(self, mode, player):
        await self.bot.db.queues.update_one(
            {"mode": mode},
            {"$pull": {"players": player}}
        )


    async def update_presence(self):
        text = []

        for mode, players in queues.items():
            if players:
                text.append(f"{mode.upper()}: {len(players)}/{queue_lengths[mode]}")

        presence = ", ".join(text) if text else "Wanted 6/9"

        await self.bot.change_presence(
            activity=discord.Game(name=f"{presence} | /queue")
        )

    @app_commands.command(name="play", description="Join a queue")
    @app_commands.describe(
        play_for="How long to queue in hours (default 3)",
        start_in="Start queueing in X hours",
        mode="Game mode",
    )
    async def play(
        self,
        interaction: discord.Interaction,
        play_for: float = 3.0,
        start_in: float = 0.0,
        mode: str = "",
    ):
        await interaction.response.defer()

        mode = util.check_mode(mode, server=interaction.guild_id, short=True)
        player = interaction.user.display_name

        scheduler = self.bot.scheduler

        async def add_to_queue():
            await self.add_player(mode, player)
            await self.update_presence()

            if len(queues[mode]) == queue_lengths[mode]:
                teams = ", ".join(queues[mode])
                await interaction.followup.send(
                    f"{modes_dict[mode]} full! {teams}"
                )

                # for p in queues[mode]:
                #     try:
                #         telegram_bot.notify_player(p, modes_dict[mode])
                #     except:
                #         pass
            else:
                await interaction.followup.send(
                    f"{player} added to {modes_dict[mode]} for {play_for} hours: "
                    f"{len(queues[mode])}/{queue_lengths[mode]}"
                )

        async def remove_from_queue():
            await self.remove_player(mode, player)
            await self.update_presence()

        # schedule start
        if start_in > 0:
            scheduler.add_job(
                add_to_queue,
                "date",
                run_date=datetime.now(timezone.utc) + timedelta(hours=start_in),
                id=f"{player}_{mode}_start",
                replace_existing=True,
            )
            await interaction.followup.send(
                f"Will queue in {start_in} hours for {play_for} hours."
            )
        else:
            await add_to_queue()

        # schedule removal
        scheduler.add_job(
            remove_from_queue,
            "date",
            run_date=datetime.now(timezone.utc) + timedelta(hours=play_for + start_in),
            id=f"{player}_{mode}_remove",
            replace_existing=True,
        )

    @app_commands.command(name="queue", description="View queue")
    async def queue(self, interaction: discord.Interaction, mode: str = "all"):
        if mode != "all":
            modes = [util.check_mode(mode, server=interaction.guild_id, short=True)]
        else:
            modes = queues.keys()
        jobs = self.bot.scheduler.get_jobs()
        current = {k: "" for k in modes}
        if len(jobs) > 0:
            for m in modes:
                players = await self.get_players(m)
                for p in players:
                    if current[m]:
                        current[m] += ", "
                    current[m] += f"{p} (for {get_job_eta(self.bot.scheduler.get_job(f'{p}_{m}_remove'))})"
            futures = "\n"
            for m in modes:
                for job in jobs:
                    if job.id.endswith(f"{m}_start"):
                        futures += job.id[:-7 - len(m)] + " in "
                        futures += get_job_eta(job)
                        futures += "\n"
        else:
            futures = ""
            for m in modes:
                if queues[m]:
                    current[m] = ", ".join(queues[m])
        response = "\n".join([f"{modes_dict[m]} {len(await self.get_players(m))}/{queue_lengths[m]}: {current[m]}" for m in modes])

        await interaction.response.send_message(
            response
        )

    @app_commands.command(name="remove", description="Leave all queues")
    async def remove(self, interaction: discord.Interaction):
        player = interaction.user.display_name

        for mode in queues:
            await self.remove_player(mode, player)

            try:
                self.bot.scheduler.remove_job(f"{player}_{mode}_remove")
            except:
                pass

        await self.update_presence()

        await interaction.response.send_message("Removed from all queues.")


async def ensure_queue_docs(db):
    for mode in ["e", "mh", "do", "asb"]:
        await db.queues.update_one(
            {"mode": mode},
            {"$setOnInsert": {"players": []}},
            upsert=True
        )

async def setup(bot):
    await ensure_queue_docs(util.connect())
    await bot.add_cog(QueueCog(bot))
