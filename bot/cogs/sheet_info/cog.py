from discord.ext import commands
import typing
import datetime
import calendar
import datetime
import random

from ...formatter import get_formatter, Formatter
from ...dbhandler import DBHandler
from ...timezonehelper import TimezoneHelper

from ..odscraper.cog import ODScraper


class Day(commands.Converter):
    async def convert(self, ctx, argument):
        if SheetInfo.get_day_int(argument):
            return argument


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
        except ValueError:
            try:
                return list(calendar.day_abbr).index(day.title())
            except ValueError:
                pass

    @commands.command(pass_context=True)
    async def avg(self, ctx, player_name: str):
        async def error():
            await ctx.send(f"No data for {player_name} :(")

        player = self.get_player_by_name(ctx.guild.id, player_name)
        if player:
            proper_name = self.get_player_by_name(ctx.guild.id, player_name).name
            avgs = get_formatter("PST").get_player_averages(ctx.guild.id, proper_name)
            if avgs:
                await ctx.send(embed=avgs)
            else:
                await error()
        else:
            await error()

    # TODO: Fix day and tz getting mixed up when trying to do something like "!check ads pst"
    @commands.command(pass_context=True)
    async def check(self, ctx, player_name: str,
                    day: typing.Optional[Day] = '',
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
    async def get(self, ctx, *, args: str):
        split = args.split()

        if args.lower() == '!get superior hog':
            superior_hog = ['ADS', 'Tydra'][random.randrange(2)]
            await ctx.send(superior_hog)
            return

        day = datetime.datetime.today().weekday()
        formatter = get_formatter(split[-1])
        if not formatter:
            formatter = get_formatter('PST')
        guild_id = ctx.guild.id
        server_info = self.bot.server_info[guild_id]

        if 'tomorrow' in split:
            if not Formatter.day_name(day) == 'Sunday':
                day += 1
            else:
                ctx.send("It's Sunday silly")
                return

        def is_hour(hour: str):
            try:
                int(hour)
                return True
            except ValueError:
                return False

        async def send_embed(discord_embed):
            await ctx.send(embed=discord_embed)

        arg_count = len(split)
        if arg_count == 1:
            arg = split[0].lower()
            player = self.get_player_by_name(guild_id, arg)

            embed = None
            if player:
                embed = formatter.get_player_on_day(guild_id, player, day)
            elif is_hour(arg):
                embed = formatter.get_hour_schedule(guild_id, server_info, day, arg)
            elif arg in ['today', 'tomorrow']:
                embed = formatter.get_day_schedule(guild_id, server_info.players, day)
            elif arg == 'week':
                embed = formatter.get_week_activity_schedule(guild_id, server_info.week_schedule)
            else:
                if SheetInfo.get_day_int(arg):
                    embed = formatter.get_day_schedule(guild_id, server_info.players, day)
                else:
                    await ctx.send("Invalid day.")

            if embed:
                await send_embed(embed)
            else:
                await ctx.send("Invalid argument.")
        elif arg_count == 2:
            player_name = split[0]
            target = split[1].lower()

            player = self.get_player_by_name(guild_id, player_name)
            if player:
                if target in ['today', 'tomorrow']:
                    await send_embed(formatter.get_player_on_day(guild_id, player, day))
                elif target in ['avg', 'average']:
                    await self.avg(ctx, player_name)
                    return
            elif player_name == 'od':
                # this probably won't work but let's try it anyways :)
                await ODScraper(self.bot).od(ctx, target)
            else:
                await ctx.send("Invalid player given.")
        elif arg_count == 3:
            target = split[0].lower()
            decider = split[1].lower()
            given_day = split[2].title()

            player = self.get_player_by_name(guild_id, target)
            # TODO: Clean up the blanket try-excepts here cus it looks bad
            if decider == 'at':
                if player:
                    try:
                        await send_embed(formatter.get_player_at_time(player, day, given_day))
                    except:
                        await ctx.send("Invalid time.")
                else:
                    try:
                        target_day = day if target in ['today', 'tomorrow'] else target
                        await send_embed(formatter.get_hour_schedule(guild_id, server_info, target_day, given_day))
                    except:
                        await ctx.send("Invalid time or day.")
            elif decider == 'on':
                try:
                    await send_embed(formatter.get_player_on_day(guild_id, player, given_day))
                except:
                    await ctx.send("Invalid day.")
            else:
                await ctx.send("Invalid identifier.")
        elif arg_count == 5:
            player_name = split[0].lower()
            pass

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
            with DBHandler() as handler:
                doc_key = handler.get_server_config(guild_id)['doc_key']
        except KeyError:
            ctx.send("No doc key provided for this server.")
            return

        await server_info.update(channel=ctx.message.channel)


def setup(bot):
    bot.add_cog(SheetInfo(bot))
