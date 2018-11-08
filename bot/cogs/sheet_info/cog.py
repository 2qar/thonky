from discord.ext import commands
import asyncio
import typing
import datetime

from .formatter import Formatter

class SheetInfo:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def avg(self, ctx, player_name: str):
        avgs = Formatter.get_player_averages(ctx.guild.id, player_name)
        if avgs:
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"No data for {player_name}. :(")

    @commands.command(pass_context=True)
    async def check(self, ctx, player_name: str, day: typing.Optional[int] = 0):
        if not day:
            day = datetime.datetime.today().weekday()
        #Formatter.get_player_on_day(server_id, 


def setup(bot):
    bot.add_cog(SheetInfo(bot))
