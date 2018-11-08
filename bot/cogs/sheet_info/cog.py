from discord.ext import commands
import asyncio
import typing
import datetime
import calendar

from ...formatter import Formatter
from ...timezonehelper import TimezoneHelper


# TODO: move formatter into this folder and make it instantiable
# Instantiate Formatter with a given timezone and start time (maybe get start time from tz)
class SheetInfo:
    def __init__(self, bot):
        self.bot = bot

    def get_player_by_name(self, server_id: int, player_name: str):
        for player in self.bot.server_info[server_id].players.unsorted_list:
            if player.name == player_name:
                return player

    def day_name(day: int):
        if day in range(7):
            return calendar.day_name[day]

    @commands.command(pass_context=True)
    async def avg(self, ctx, player_name: str):
        avgs = Formatter.get_player_averages(ctx.guild.id, player_name)
        if avgs:
            await ctx.send(embed=avgs)
        else:
            await ctx.send(f"No data for {player_name}. :(")

    @commands.command(pass_context=True)
    async def check(self, ctx, player_name: str, day: typing.Optional[str] = '',
                    time: typing.Optional[int] = 0,
                    tz: typing.Optional[str] ='PST'):
        if not day:
            day = datetime.datetime.today().weekday()
        day = SheetInfo.day_name(day)

        if not tz:
            start_time = 4
        else:
            try:
                start_time = TimezoneHelper.get_start_time(tz)
            except:
                await ctx.send(f"Invalid timezone: \"{tz}\"")
                return

        server_id = ctx.guild.id
        player = self.get_player_by_name(server_id, player_name)
        if player:
            embed = Formatter.get_player_on_day(server_id, player, day, start_time)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Player \"{player_name}\"")


def setup(bot):
    bot.add_cog(SheetInfo(bot))
