from discord.ext import commands
import typing
import calendar
import datetime
import random
import re

from ...formatter import get_formatter, Formatter
from ...dbhandler import DBHandler
from ...timezonehelper import get_start_time

from ..odscraper.cog import ODScraper


class Day(commands.Converter):
    async def convert(self, ctx, argument):
        if SheetInfo.get_day_int(argument):
            return argument


class SheetInfo:
    def __init__(self, bot):
        self.bot = bot

    def get_player_by_name(self, guild_id: int, player_name: str):
        for player in self.server_info(guild_id).players.unsorted_list:
            if player.name.lower() == player_name.lower():
                return player

    def server_info(self, guild_id: typing.Union[str, int]):
        return self.bot.server_info[str(guild_id)]

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
        else:
            del split[-1]
        guild_id = ctx.guild.id
        server_info = self.server_info(guild_id)

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
                    return

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
            player = self.get_player_by_name(guild_id, player_name)
            if not player:
                await ctx.send("Invalid player.")
            else:
                time = split[2]
                given_day = split[4].title()

                day_int = SheetInfo.get_day_int(given_day)
                if not day_int:
                    await ctx.send("Invalid day.")
                else:
                    try:
                        msg = formatter.get_player_at_time(player, day_int, time)
                        await ctx.send(msg)
                    except:
                        await ctx.send("Invalid time.")

    # TODO: Make a note that says you have to put underscores in stuff with spaces OR make a command with proper arg
    #       parsing
    @commands.command(pass_context=True, hidden=True)
    async def set(self, ctx, *, args):
        split = args.split()

        start_time = get_start_time(split[-1])
        if start_time:
            del split[-1]
        else:
            start_time = 4

        arg_count = len(args)
        if arg_count == 3:
            day = self.get_day_int(split[0])
            if day:
                row = 3 + day
                time_re_raw = '\d{1,2}'
                time_re = re.compile(f'{time_re_raw}-{time_re_raw}')

                range_start = start_time

                def get_range_end(columns: int): return chr(ord('C') + columns)
                range_end = None

                try:
                    # get range_end from a single num
                    range_end = get_range_end(int(split[1]) - start_time)
                except ValueError:
                    match = time_re.match(split[1])
                    # get range_end from a time range ex. 4-5
                    if match:
                        match_str = match.group()
                        try:
                            times = [int(num) for num in match_str.split('-')]
                        except ValueError:
                            ctx.send("Invalid time range \"{split[1]}\"")
                            return

                        time_diff = times[1] - times[0]
                        if time_diff == 1:
                            range_start = get_range_end(times[1] - start_time)
                            range_end = range_start
                        elif times[1] > times[0]:
                            start = times[0] - start_time
                            range_start = get_range_end(start)
                            range_end = get_range_end(start + time_diff - 1)

                if range_end:
                    cell_range = f'{range_start}{row}:{range_end}{row}'
                    handler = self.server_info(ctx.guild.id).sheet_handler
                    try:
                        handler.update_cells('Weekly Schedule', cell_range, split[2])
                    except ValueError:
                        ctx.send("Invalid time range.")
                    except IndexError:
                        ctx.send("Weird amount of values given for the range given.")
                else:
                    ctx.send(f"Invalid time range \"{split[1]}\"")
            else:
                ctx.send(f"Invalid day \"{split[0]}\"")

    # TODO: Make a config cog and move this command there
    @commands.command(pass_context=True)
    async def update(self, ctx):
        guild_id = ctx.guild.id
        try:
            server_info = self.server_info(guild_id)
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
