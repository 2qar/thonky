from discord.ext import commands
import typing
import datetime
import calendar

from ...formatter import get_formatter, Formatter
from ...dbhandler import DBHandler


class SheetInfo:
    def __init__(self, bot):
        self.bot = bot

    def get_player_by_name(self, guild_id: int, player_name: str):
        for player in self.bot.server_info[guild_id].players.unsorted_list:
            if player.name.lower() == player_name.lower():
                return player

    @staticmethod
    def get_day_int(day: str):
        try:
            return list(calendar.day_name).index(day.title())
        except KeyError:
            try:
                return list(calendar.day_abbr).index(day.title())
            except KeyError:
                pass

    @commands.command(pass_context=True)
    async def avg(self, ctx, player_name: str):
        avgs = get_formatter("PST").get_player_averages(ctx.guild.id, player_name)
        if avgs:
            await ctx.send(embed=avgs)
        else:
            await ctx.send(f"No data for {player_name}. :(")

    # TODO: Fix day and tz getting mixed up when trying to do something like "!check ads pst"
    @commands.command(pass_context=True)
    async def check(self, ctx, player_name: str,
                    day: typing.Optional[str] = '',
                    time: typing.Optional[int] = 0,
                    *,
                    tz: typing.Optional[str]='PST'):
        if not day:
            day = Formatter.day_name(datetime.datetime.today().weekday())
        elif day.lower() == 'tomorrow':
            day = Formatter.day_name(datetime.datetime.today().weekday() + 1)

        day_int = SheetInfo.get_day_int(day)
        if not day_int:
            ctx.send(f"Invalid day \"{day}\"")
            return

        guild_id = ctx.guild.id
        player = self.get_player_by_name(guild_id, player_name)
        if player:
            formatter = get_formatter(tz)
            if formatter:
                if time:
                    msg = formatter.get_player_at_time(player, day_int, time)
                    await ctx.send(msg)
                else:
                    embed = formatter.get_player_on_day(guild_id, player, day_int)
                    await ctx.send(embed=embed)
            else:
                await ctx.send(f"Invalid timezone: \"{tz}\"")
        else:
            await ctx.send(f"No player named \"{player_name}\"")

    @commands.command(pass_context=True)
    async def test(self, ctx, *, arg):
        await ctx.send(arg)

    # TODO: Make a config cog and move this command there
    @commands.command(pass_context=True)
    async def update(self, ctx):
        guild_id = ctx.guild.id
        try:
            server_info = self.bot.server_info[guild_id]
        except KeyError:
            ctx.send("No server info for this server.")
            return

        try:
            with DBHandler as handler:
                doc_key = handler.get_server_config(guild_id)['doc_key']
        except KeyError:
            ctx.send("No doc key provided for this server.")
            return

        await server_info.update(channel=ctx.message.channel)


def setup(bot):
    bot.add_cog(SheetInfo(bot))
