import discord
from discord import app_commands
from discord.ext import commands
import util.teams
import util.util


class TeamsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="team_comps", description="Generate team comps")
    async def team_comps(
        self,
        interaction: discord.Interaction,
        players: str,
        mode: str,
        randomness: int = 25
    ):
        await interaction.response.defer()

        player_list = [p.strip() for p in players.split(",")]

        mode = util.check_mode(mode, short=True)

        result = teams.find_teams(
            player_list,
            mode=mode,
            random=randomness
        )

        t1 = ", ".join([p["name"] for p in result[0]])
        t2 = ", ".join([p["name"] for p in result[1]])

        await interaction.followup.send(f"{t1} vs {t2}")


async def setup(bot):
    await bot.add_cog(TeamsCog(bot))
