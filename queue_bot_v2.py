import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import botconfig as conf
from util import util
from motor.motor_asyncio import AsyncIOMotorClient

def connect():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    return client.public

async def setup_db(bot):
    bot.db = connect()["queuebot"]


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

        await setup_db(bot)

        await self.load_extension("cogs.queue")
        # await self.load_extension("cogs.teams")
        await self.load_extension("cogs.sync")

        await self.tree.sync()
        print("Slash commands synced.")


bot = ANBot()
bot.run(conf.discord_id)
