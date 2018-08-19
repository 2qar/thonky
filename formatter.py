from discord import Embed
from players import Player
from sheetbot import StatusEmotes
from player_saver import DataAnalyzer
import calendar
import datetime

#TODO: Make this instanceable
class Formatter():
	zone = "PDT"

	letter_emotes = [':zero:', ':one:', ':two:', ':three:', ':four:', ':five:', ':six:', ':seven:', ':eight:', ':nine:', ':keycap_ten:', ':one::one:', ':one::two:']

	activity_emotes = {
		"Free": ":free:",
		"TBD": ":grey_question:"
	}

	role_emotes = {
		"Tanks": ":shield:",
		"DPS": ":crossed_swords:",
		"Supports": ":ambulance:",
		"Flex": ":muscle:",
		"Coaches": ":books:"
	}

	role_status_emotes = [":warning:", ":warning:", ":ballot_box_with_check:", ":ballot_box_with_check:"] 

	thonk_link = "https://cdn.discordapp.com/attachments/437847669839495170/476837854966710282/thonk.png"

	sheet_url = "https://docs.google.com/spreadsheets/d/15oxfuWKI97HZRaSG5Jxcyw5Ycdr9mPDc_VmEoHFu4-c/edit#gid=1697055162"

	def get_template_embed():
		embed = Embed()
		embed.title = "Link to Spreadsheet"
		embed.url = Formatter.sheet_url
		embed.set_footer(text="Times shown in {0}".format(Formatter.zone))
		embed.set_thumbnail(url=Formatter.thonk_link)
		return embed

	# spits back the player's availability in emotes
	def get_day_availability(player, day, start_time):
		data = {}
		availability_on_day = player.get_availability_for_day(day)

		for i in range(0, len(availability_on_day)):
			available = availability_on_day[i]
			available_emote = StatusEmotes[available].value
			time = i + start_time
			data[time] = available_emote
		return data

	def get_player_at_time(player, day, time, start):
		availability = player.get_availability_at_time(day, time, start)
		availability_responses = {
			"Yes": " is available",
			"Maybe": " might be available",
			"No": " is not available",
			"Nothing": " has not left a response yet"
		}
		message = StatusEmotes[availability].value + " " + player.name + availability_responses[availability] + " at " + time
		if datetime.date.today().weekday() != list(calendar.day_name).index(day):
			message += " on " + day + "."
		else:
			message += "."
		return message

	def get_player_on_day(player, day, start_time):
		embed = Formatter.get_template_embed()
		embed.set_author(name="{0} on {1}".format(player.name, day))
		embed.set_thumbnail(url=Formatter.thonk_link)
		formatted_data = Formatter.get_day_availability(player, day, start_time)

		for key in formatted_data:
			embed.add_field(name=key, value=formatted_data[key], inline=False)

		return embed

	def get_player_averages(player_name):
		embed = Formatter.get_template_embed()
		embed.set_author(name="Average Responses for " + player_name)
		responses = DataAnalyzer.get_response_percents(player_name)

		embed_str = ""
		for response in responses:
			emote = StatusEmotes[response].value
			embed_str += "{0} {1}: {2}\n".format(emote, response, responses[response])

		embed.add_field(name="Responses", value=embed_str, inline=False)
		embed.set_footer(text="")
		return embed

	def get_hour_schedule(players, week_schedule, day, hour, start_time):
		embed = Formatter.get_template_embed()

		day_obj = week_schedule.get_day(day)
		activity = day_obj.get_activity_at_time(hour, start_time)
		format_name = day_obj.get_formatted_name()
		title = "{0} on {1} at {2} PM".format(activity, format_name, hour)
		embed.set_author(name=title)

		for role in players.sorted_list:
			players_string = ""
			available_count = 0
			for player in players.sorted_list[role]:
				try:
					available = player.get_availability_at_time(day, hour, start_time)
					if available == "Yes":
						available_count += 1
					emote = StatusEmotes[available].value
					player_str = player.name + "\t" + emote
					players_string += player_str + "\n"
				except:
					players_string += player.name + "\t:ghost:\n"
					print("Unable to add player {0} to {1} string".format(player.name, role))
			role_name = Formatter.role_emotes[role] + " " + role + " " + Formatter.role_status_emotes[available_count]
			embed.add_field(name=role_name, value=players_string)

		return embed

	def get_day_schedule(players, day, start_time):
		embed = Formatter.get_template_embed()
		embed.set_author(name="Schedule for " + day) 

		Formatter.add_time_field(embed, "Player Name", start_time)
			
		# add all of the players to the embed
		for player in players.unsorted_list:
			try:
				availability = Formatter.get_day_availability(player, day, start_time)

				status_emotes = [availability[key] for key in availability]

				formatted_status = ""
				for emote in range(len(status_emotes) - 1):
					formatted_status += status_emotes[emote] + ", "
				formatted_status += status_emotes[len(status_emotes) - 1]
					
				player_name = Formatter.format_player_name(player)
				embed.add_field(name=player_name, value=formatted_status, inline=False)
			except:
				print("Unable to add player {0} to embed".format(player.name))

		embed = Formatter.add_role_availability(embed, players, day)

		return embed

	def get_week_activity_schedule(week_schedule, start_time):
		embed = Formatter.get_template_embed()
		Formatter.add_time_field(embed, "Times", start_time)

		week = week_schedule.days[0].date
		embed.set_author(name="Week of " + week)

		for day in week_schedule.days:
			title = day.get_formatted_name()

			# format all of the activities into one nice and pretty string
			formatted_activities = ""
			for activity in range(0, len(day.activities) - 1):
				act = day.activities[activity]
				formatted_activity_name = Formatter.get_formatted_activity_name(act)
				formatted_activities += formatted_activity_name + ", "
			last_activity = day.activities[len(day.activities) - 1]
			formatted_activities += Formatter.get_formatted_activity_name(last_activity)

			embed.add_field(name=title, value=formatted_activities, inline=False)

		return embed

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

			emote_count = [Formatter.letter_emotes[value] for value in count]

			schedule_string = ""
			for value in range(0, len(emote_count) - 1):
				schedule_string += emote_count[value] + ", "
			schedule_string += emote_count[len(emote_count) - 1]

			title = Formatter.role_emotes[role] + " " + role
			embed.add_field(name=title, value=schedule_string, inline=False)


		return embed

	def add_time_field(embed, title, start_time):
		time_string = ""
		for time in range(0, 5):
			time_string += Formatter.letter_emotes[time + start_time] + ", "
		time_string += Formatter.letter_emotes[5 + start_time]
		embed.add_field(name=title, value = time_string, inline=False)

	def get_week_schedule(players):
		days = list(calendar.day_name)
		return [Formatter.get_day_schedule(players, day) for day in days]

	def get_formatted_activity_name(activity):
		try:
			return Formatter.activity_emotes[activity]
		except:
			return ':regional_indicator_{0}:'.format(activity[:1].lower())


	def format_player_name(player):
		return Formatter.role_emotes[player.role] + " " + player.name 
