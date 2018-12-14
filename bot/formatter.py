import calendar
import datetime
from discord import Embed
from discord import Colour

from .player_saver import DataAnalyzer
from .dbhandler import DBHandler
from .timezonehelper import get_start_time

letter_emotes = [':zero:', ':one:', ':two:', ':three:', ':four:', ':five:', ':six:', ':seven:', ':eight:', ':nine:',
                 ':keycap_ten:', ':one::one:', ':one::two:']

role_emotes = {
        "Tanks": ":shield:",
        "DPS": ":crossed_swords:",
        "Supports": ":ambulance:",
        "Flex": ":muscle:",
        "Coaches": ":books:"
}

availability_responses = {
        "Yes": "is available",
        "Maybe": "might be available",
        "No": "is not available",
        "Nothing": "has not left a response yet"
}

status_emotes = {
        "Yes": ":white_check_mark:",
        "Maybe": ":grey_question:",
        "No": ":x:",
        "Nothing": ":ghost:"
}

spreadsheet_logo = 'https://www.clicktime.com/images/web-based/timesheet/integration/googlesheets.png'

thonk_link = "https://cdn.discordapp.com/attachments/437847669839495170/476837854966710282/thonk.png"

sheet_url = "https://docs.google.com/spreadsheets/d/"


def get_formatter(tz: str):
    start_time = get_start_time(tz)
    if start_time:
        return Formatter(tz, start_time)


class Formatter:
    def __init__(self, tz, start_time):
        self.tz = tz.upper()
        self.start_time = start_time

    @staticmethod
    def day_name(day: int):
        if day in range(7):
            return calendar.day_name[day]

    def get_template_embed(self, server_id, title):
        embed = Embed()
        embed.colour = Colour.green()
        with DBHandler() as handler:
            sheet_link = sheet_url + handler.get_server_config(server_id)['doc_key']
        embed.set_author(name=title, url=sheet_link, icon_url=spreadsheet_logo)
        embed.set_footer(text=f"Times shown in {self.tz}")
        embed.set_thumbnail(url=thonk_link)
        return embed

    def get_day_availability(self, player, day):
        data = {}
        availability_on_day = player.get_availability_for_day(day)

        for i in range(0, len(availability_on_day)):
            available = availability_on_day[i]
            available_emote = status_emotes[available]
            time = i + self.start_time
            data[time] = available_emote
        return data

    def get_player_at_time(self, player, day: int, time: int):
        availability = player.get_availability_at_time(day, time, self.start_time)

        available_emote = status_emotes[availability]
        available_response = availability_responses[availability]

        message = f"{available_emote} {player.name} {available_response} at {time}"

        day_not_today = datetime.date.today().weekday() != day
        message += f" on {Formatter.day_name(day)}." if day_not_today else "."
        return message

    def get_player_on_day(self, server_id: int, player, day: int):
        day_name = Formatter.day_name(day)
        embed = self.get_template_embed(server_id, f"{player.name} on {day_name}")
        self.add_time_field(embed, "Times")
        embed.set_thumbnail(url=thonk_link)

        availability = player.get_availability_for_day(day)
        emotes = [status_emotes[response] for response in availability]
        available_str = ', '.join(emotes)
        embed.add_field(name="Availability", value=available_str, inline=False)

        return embed

    def get_player_averages(self, guild_id, player_name):
        embed = self.get_template_embed(guild_id, f"Average Responses for {player_name}")
        responses = DataAnalyzer.get_response_percents(guild_id, player_name)
        if not responses:
            return

        def format_response(response: str): return f"{status_emotes[response]} {response} {responses[response]}"
        embed_str = '\n'.join([format_response(response) for response in responses])

        embed.add_field(name="Responses", value=embed_str, inline=False)
        embed.set_footer(text="")
        return embed

    def get_hour_schedule(self, server_id, server_info, day, hour):
        players = server_info.players
        week_schedule = server_info.week_schedule

        day_obj = week_schedule[day]
        activity = day_obj.get_activity_at_time(hour, self.start_time)
        title = f"{activity} on {day_obj} at {hour} PM"
        embed = self.get_template_embed(server_id, title)

        for role in players.sorted_list:
            players_string = ""
            available_count = 0
            for player in players.sorted_list[role]:
                available = player.get_availability_at_time(day, hour, self.start_time)
                if available == "Yes":
                    available_count += 1
                emote = status_emotes[available]
                player_str = player.name + "\t" + emote
                players_string += player_str + "\n"

            role_status = ":warning:" if available_count < 2 else ":ballot_box_with_check:"
            role_name = f"{role_emotes[role]} {role} {role_status}"
            embed.add_field(name=role_name, value=players_string)

        return embed

    def get_day_schedule(self, server_id, players, day):
        day_name = Formatter.day_name(day)
        embed = self.get_template_embed(server_id, f"Schedule for {day_name}")

        self.add_time_field(embed, "Player Name")

        # add all of the players to the embed
        for player in players.unsorted_list:
            availability = self.get_day_availability(player, day)
            emotes = [availability[key] for key in availability]
            formatted_status = ', '.join([emote for emote in emotes])
            player_name = f"{role_emotes[player.role]} {player.name}"

            embed.add_field(name=player_name, value=formatted_status, inline=False)

        embed = Formatter.add_role_availability(embed, players, day)

        return embed

    def get_week_activity_schedule(self, bot, server_id, week_schedule):
        week = week_schedule[0].date
        embed = self.get_template_embed(server_id, f"Week of {week}")
        self.add_time_field(embed, "Times")

        def get_formatted_activity_name(activity):
            if activity == '' or activity == 'TBD':
                return ":grey_question:"
            else:
                activity_emoji_name = activity.lower().replace(" ", "_")
                for emote in bot.get_guild(437847669839495168).emojis:
                    if emote.name == activity_emoji_name:
                        return str(emote)

                return f':regional_indicator_{activity[0].lower()}:'

        today = datetime.datetime.today().weekday()
        for i, day in enumerate(week_schedule.days):
            # format all of the activities into one nice and pretty string
            formatted_activities = ', '.join([get_formatted_activity_name(activity) for activity in day.activities])

            day_name = str(day) if today != i else f'**{day}**'
            embed.add_field(name=day_name, value=formatted_activities, inline=False)

        return embed

    @staticmethod
    def add_role_availability(embed, players, day):
        for role in players.sorted_list:
            count = [0] * 6
            for player in players.sorted_list[role]:
                schedule = player.get_availability_for_day(day)
                for i in range(0, 6):
                    if i > len(schedule) - 1:
                        break
                    if schedule[i] == "Yes":
                        count[i] += 1

            emote_count = [letter_emotes[value] for value in count]

            schedule_string = ", ".join([emote for emote in emote_count])

            title = role_emotes[role] + " " + role
            embed.add_field(name=title, value=schedule_string, inline=False)

        return embed

    def add_time_field(self, embed, title):
        time_string = ""
        for time in range(0, 5):
            time_string += letter_emotes[time + self.start_time] + ", "
        time_string += letter_emotes[5 + self.start_time]
        embed.add_field(name=title, value=time_string, inline=False)
