import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import botconfig as conf

class ANBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
        )
        self.scheduler = None

    async def setup_hook(self):
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()

        await self.load_extension("cogs.queue")
        # await self.load_extension("cogs.teams")
        await self.load_extension("cogs.sync")

        await self.tree.sync()
        print("Slash commands synced.")


bot = ANBot()
bot.run(conf.discord_id)
