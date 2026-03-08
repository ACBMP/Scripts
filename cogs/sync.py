import discord
from discord.ext import commands
import botconfig as conf


class SyncCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        for group in conf.synched_channels:
            if message.channel.id in group:
                for channel_id in group:
                    if channel_id != message.channel.id:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            await channel.send(
                                f"**{message.author.display_name}:** {message.content}"
                            )


async def setup(bot):
    await bot.add_cog(SyncCog(bot))
