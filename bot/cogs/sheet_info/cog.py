from discord.ext.commands import command, check, Context, Converter
from gspread.exceptions import APIError
import typing
import calendar
import datetime
import random
import re

from ...formatter import get_formatter, Formatter
from ...dbhandler import DBHandler
from ...timezonehelper import get_start_time

from ..odscraper.cog import ODScraper


class Day(Converter):
    async def convert(self, ctx, argument):
        if SheetInfo.get_day_int(argument):
            return argument


def if_doc_key():
    def predicate(ctx):
        with DBHandler() as handler:
            # TODO: maybe find a way to get access to SheetInfo instance so this can be cleaner
            conf = handler.get_server_config(ctx.guild.id)
            found_team = False
            for team in handler.get_teams(ctx.guild.id):
                for channel in team['channels']:
                    if channel == ctx.channel.id:
                        conf = team
                        found_team = True
                        break
                if found_team:
                    break
            return bool(conf['doc_key'])
    return check(predicate)


class SheetInfo:
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_listener(self._on_command_error, 'on_command_error')

    def get_player_by_name(self, ctx: Context, player_name: str):
        for player in self.bot.get_info(ctx).players.unsorted_list:
            if player.name.lower() == player_name.lower():
                return player

    async def _on_command_error(self, ctx: Context, exception):
        if type(ctx.cog) == type(self):
            if not self.bot.get_info(ctx).sheet_handler:
                await ctx.send("No doc key provided.")
            else:
                await ctx.send(f"{exception} :(")

    @staticmethod
    def get_day_int(day: str):
        try:
            return list(calendar.day_name).index(day.title())
        except ValueError:
            try:
                return list(calendar.day_abbr).index(day.title())
            except ValueError:
                pass

    @command(pass_context=True)
    @if_doc_key()
    async def avg(self, ctx, player_name: str):
        """ Check the average responses for a player.

            Equivalent to !get <player name> avg
        """

        async def error(): await ctx.send(f"No data for {player_name} :(")

        player = self.get_player_by_name(ctx, player_name)
        if player:
            avgs = get_formatter("PST").get_player_averages(ctx.guild.id, player.name)
            if avgs:
                await ctx.send(embed=avgs)
            else:
                await error()
        else:
            await error()

    # TODO: Fix day and tz getting mixed up when trying to do something like "!check ads pst"
    @command(pass_context=True)
    @if_doc_key()
    async def check(self, ctx, player_name: str,
                    day: typing.Optional[Day] = '',
                    time: typing.Optional[int] = 0,
                    *,
                    tz: typing.Optional[str]='PST'):
        """ Check somebody's availability at a certain time.

            Equivalent to all of the !get player at time commands.
        """

        if not day:
            day = Formatter.day_name(datetime.datetime.today().weekday())
        elif day.lower() == 'tomorrow':
            day = Formatter.day_name(datetime.datetime.today().weekday() + 1)

        day_int = SheetInfo.get_day_int(day)
        if not day_int:
            ctx.send(f"Invalid day \"{day}\"")
            return

        guild_id = ctx.guild.id
        player = self.get_player_by_name(ctx, player_name)
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

    @command(pass_context=True)
    @if_doc_key()
    async def get(self, ctx, *, args: str):
        """ Get information from the configured spreadsheet.

            Schedule commands:
            !get <day name OR today OR tomorrow>
                Show who's available at what time on a certain day.
            !get <day name OR today OR tomorrow> at <time>
                Show who's available on a certain day at a certain time.
            !get <time>
                Show who's available today at a certain time.
            !get week
                Show the schedule for this week.

            Player commands:
            !get <player name>
                Show this player's availability this week.
            !get <player name> avg
                Show the average responses for somebody.
            !get <player name> on <day name>
                Show this player's availability on a certain day.
            !get <player name> at <time>
                Show this player's availability today at a certain time.
            !get <player name> on <day name> at <time>
                Show this player's availability on a certain day at a certain time.
        """

        split = args.split()

        if args.lower() == 'superior hog':
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
        info = self.bot.get_info(ctx)

        if 'tomorrow' in split:
            if not Formatter.day_name(day) == 'Sunday':
                day += 1
            else:
                await ctx.send("It's Sunday silly")
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
            player = self.get_player_by_name(ctx, arg)

            embed = None
            if player:
                embed = formatter.get_player_this_week(guild_id, player, info.week_schedule)
            elif is_hour(arg):
                embed = formatter.get_hour_schedule(guild_id, info, day, arg)
            elif arg in ['today', 'tomorrow']:
                embed = formatter.get_day_schedule(guild_id, info.players, day)
            elif arg == 'week':
                embed = formatter.get_week_activity_schedule(self.bot, guild_id, info.week_schedule)
            else:
                day_int = SheetInfo.get_day_int(arg)
                if day_int is not None:
                    embed = formatter.get_day_schedule(guild_id, info.players, day_int)
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

            player = self.get_player_by_name(ctx, player_name)
            if player:
                if target in ['today', 'tomorrow']:
                    await send_embed(formatter.get_player_on_day(guild_id, player, day))
                elif target in ['avg', 'average']:
                    await self.avg(ctx, player_name)
            elif player_name == 'od':
                await ODScraper.send_od(ctx, target)
            else:
                await ctx.send("Invalid player given.")
        elif arg_count == 3:
            target = split[0].lower()
            decider = split[1].lower()
            given_day = split[2].title()

            player = self.get_player_by_name(ctx, target)
            if decider == 'at':
                try:
                    given_time = int(given_day)
                except ValueError:
                    await ctx.send("Invalid time.")
                    return
                if player:
                    await ctx.send(formatter.get_player_at_time(player, day, given_time))
                else:
                    target_day = day if target in ['today', 'tomorrow'] else self.get_day_int(target)
                    if target_day is None:
                        await ctx.send("Invalid day.")
                    else:
                        await send_embed(formatter.get_hour_schedule(guild_id, info, target_day, given_day))
            elif decider == 'on':
                day = self.get_day_int(given_day)
                if day is None:
                    await ctx.send("Invalid day.")
                else:
                    await send_embed(formatter.get_player_on_day(guild_id, player, day))
            else:
                await ctx.send("Invalid identifier.")
        elif arg_count == 5:
            player_name = split[0].lower()
            player = self.get_player_by_name(ctx, player_name)
            if not player:
                await ctx.send("Invalid player.")
            else:
                time = split[2]
                given_day = split[4].title()

                day_int = self.get_day_int(given_day)
                if day_int is not None:
                    await ctx.send("Invalid day.")
                else:
                    try:
                        given_time = int(time)
                    except ValueError:
                        await ctx.send("Invalid time.")
                        return
                    msg = formatter.get_player_at_time(player, day_int, given_time)
                    await ctx.send(msg)

    @command(pass_context=True, hidden=True)
    @if_doc_key()
    async def set(self, ctx, *, args):
        """ Update information on the configured spreadsheet.

            !set < player name > < day name > < time range > < availability >
                Update player availability.
            !set < day name > < time range > < activity / activities >
                Update schedule.

            To give multiple responses / activities, use commas:
                !set tydra monday 4-6 no, yes

            Giving one response for multiple cells will set the value of each cell to that response:
                !set monday 4-10 free
        """

        split = args.split()

        start_time = get_start_time(split[-1])
        if start_time:
            del split[-1]
        else:
            start_time = 4

        info = self.bot.get_info(ctx)

        def get_range(given_range: str, offset: int) -> typing.Tuple[int, int] or None:
            time_re_raw = '\d{1,2}'
            time_re = re.compile(f'{time_re_raw}-{time_re_raw}')

            range_start = start_time

            range_end = None

            try:
                # get range_end from a single num
                range_end = int(given_range) - start_time
                range_start = range_end
            except ValueError:
                match = time_re.match(given_range)
                # get range_end from a time range ex. 4-5
                if match:
                    match_str = match.group()
                    try:
                        times = [int(num) for num in match_str.split('-')]
                    except ValueError:
                        return None

                    if times[1] > times[0]:
                        range_start = times[0] - start_time
                        range_end = range_start + (times[1] - times[0])

            if range_end is not None:
                if offset != -1:
                    offset *= 6
                    range_start += offset
                    range_end += offset
                return range_start, range_end

        def get_csv(given_values: typing.List[str]) -> typing.List[str]:
            joined_values = ' '.join(given_values)
            return joined_values.split(', ')

        async def parse_activities(given_values: typing.List[str]):
            valid_activities = info.valid_activities
            lower_activities = [activity.lower() for activity in valid_activities]

            is_split = False
            for value in given_values:
                if ',' in value:
                    is_split = True

            if len(given_values) > 1 and is_split:
                activity_list = get_csv(given_values)
                for i, activity in enumerate(activity_list):
                    try:
                        lower_index = lower_activities.index(activity.lower())
                        activity_list[i] = valid_activities[lower_index]
                    except ValueError:
                        await ctx.send(f"Invalid activity \"{activity}\"")
                        return
                return activity_list
            elif len(given_values) == 2:
                long_valid_activities = [activity for activity in valid_activities if len(activity.split()) == 2]
                lower_long_activities = [activity.lower() for activity in long_valid_activities]

                activity = ' '.join(given_values)
                try:
                    i = lower_long_activities.index(activity.lower())
                    return [long_valid_activities[i]]
                except ValueError:
                    await ctx.send(f"Invalid activity \"{activity}\"")
            else:
                try:
                    i = lower_activities.index(given_values[0].lower())
                    return [valid_activities[i]]
                except ValueError:
                    await ctx.send(f"Invalid activity \"{given_values[0]}\"")

        async def parse_availability(given_values: typing.List[str]):
            valid_availability = ['Yes', 'Maybe', 'No']
            valid_lower = [response.lower() for response in valid_availability]

            if len(given_values) > 1:
                response_list = get_csv(given_values)
                for i, value in enumerate(response_list):
                    try:
                        lower_index = valid_lower.index(value.lower())
                        response_list[i] = valid_availability[lower_index]
                    except ValueError:
                        await ctx.send(f"Invalid response \"{value}\"")
                        return
                return response_list
            else:
                try:
                    i = valid_lower.index(given_values[0].lower())
                    return [valid_availability[i]]
                except ValueError:
                    await ctx.send(f"Invalid response \"{given_values[0]}\"")

        async def update_cells(sheet_name: str, cell_container, value_parser, value_start_index: int, offset=-1):
            cell_range = get_range(split[value_start_index + 1], offset)
            if cell_range is not None:
                range_start = cell_range[0]
                range_end = cell_range[1]
                if range_start == range_end:
                    cells = [cell_container.cells[range_start]]
                else:
                    cells = cell_container.cells[range_start:range_end]
                parsed_values = await value_parser(split[value_start_index + 2::])
                if parsed_values:
                    handler = info.sheet_handler
                    try:
                        log = handler.update_cells(sheet_name, cells, parsed_values)
                        await ctx.send(f"Changed {log[0]} to {log[1]}")
                    except IndexError:
                        await ctx.send("Weird amount of values given for the range given.")
                    except APIError as e:
                        error = e.response.json()['error']
                        if error['code'] == 400:
                            if error['message'].startswith('You are trying to edit a protected cell or object.'):
                                await ctx.send(f"The sheet \"{sheet_name}\" is protected. "
                                               "I need edit permission :(")
            else:
                await ctx.send(f"Invalid time range \"{split[value_start_index + 1]}\"")

        arg_count = len(args)
        if arg_count >= 3:
            day = self.get_day_int(split[0])
            player = self.get_player_by_name(ctx, split[0])
            if day is not None:
                day_obj = info.week_schedule[day]
                await update_cells('Weekly Schedule', day_obj, parse_activities, 0)
            elif player is not None:
                day = self.get_day_int(split[1])
                if day is not None:
                    await update_cells(player.name, player, parse_availability, 1, offset=day)
                else:
                    await ctx.send(f"Invalid day \"{split[1]}\"")
            else:
                await ctx.send(f"Invalid day / player \"{split[0]}\"")

    @command(pass_context=True)
    @if_doc_key()
    async def update(self, ctx):
        """ Pull any new changes from the sheet. """

        info = self.bot.get_info(ctx)
        if not info:
            ctx.send("No server info for this server.")
            return

        try:
            doc_key = info.get_config()['doc_key']
        except KeyError:
            ctx.send("No doc key provided for this server.")
            return

        await info.update(channel=ctx.message.channel)


def setup(bot):
    bot.add_cog(SheetInfo(bot))
