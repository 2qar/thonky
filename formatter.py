from discord import Embed
from sheetbot import Player
from sheetbot import StatusEmotes
import calendar
import datetime

#TODO: Make this instanceable
class Formatter():
	zone = "PDT"
	letter_emotes = [':zero:', ':one:', ':two:', ':three:', ':four:', ':five:', ':six:', ':seven:', ':eight:', ':nine:', ':keycap_ten:', ':one::one:', ':one::two:']
	role_emotes = {
		"Tanks": ":shield:",
		"DPS": ":crossed_swords:",
		"Supports": ":ambulance:",
		"Flex": ":muscle:"
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
		print("availability: ", availability)
		availability_responses = {
			"Yes": " is available",
			"Maybe": " might be available",
			"No": " is not available"
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

	def get_hour_schedule(players, week_schedule, day, hour, start_time):
		embed = Formatter.get_template_embed()

		day_obj = week_schedule.get_day(day)
		activity = day_obj.get_activity_at_time(hour, start_time)
		format_name = day_obj.get_formatted_name()
		title = "{0} on {1} at {2} PM".format(activity, format_name, hour)
		embed.set_author(name=title)

		roles = {
			"Tanks": [],
			"DPS": [],
			"Supports": [],
			"Flex": []
		}

		for player in players:
			available = player.get_availability_at_time(day, hour, start_time)
			roles[player.role].append([player.name, available])

		for role in roles:
			players_string = ""
			available_count = 0
			for player in roles[role]:
				if player[1] == "Yes":
					available_count += 1
				emote = StatusEmotes[player[1]].value
				name = player[0]
				player_str = name + "\t" + emote
				players_string += player_str + "\n"
			role_name = Formatter.role_emotes[role] + " " + role + " " + Formatter.role_status_emotes[available_count]
			embed.add_field(name=role_name, value=players_string)

		return embed

	def get_day_schedule(players, day, start_time):
		embed = Formatter.get_template_embed()
		embed.set_author(name="Schedule for " + day) 

		time_string = ""
		for time in range(0, 5):
			time_string += Formatter.letter_emotes[time + start_time] + ", "
		time_string += Formatter.letter_emotes[5 + start_time]
		embed.add_field(name="Player Name", value = time_string, inline=False)
	
		# add all of the players to the embed
		for player in players:
			try:
				availability = Formatter.get_day_availability(player, day, start_time)

				status_emotes = []
				for key in availability:
					status_emotes.append(availability[key])

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

	def add_role_availability(embed, players, day):
		roles_with_player_availability = {
			"Tanks": [],
			"DPS": [],
			"Supports": [],
			"Flex": []
		}

		for player in players:
			roles_with_player_availability[player.role].append(player.get_availability_for_day(day))

		for key in roles_with_player_availability:
			count = [0] * 6
			for schedule in roles_with_player_availability[key]:
				for i in range(0, len(schedule)):
					if schedule[i] == "Yes":
						count[i] += 1

			emote_count = []
			for value in count:
				emote_count.append(Formatter.letter_emotes[value])

			schedule_string = ""
			for value in range(0, len(emote_count) - 1):
				schedule_string += emote_count[value] + ", "
			schedule_string += emote_count[len(emote_count) - 1]

			title = Formatter.role_emotes[key] + " " + key
			embed.add_field(name=title, value=schedule_string, inline=False)


		return embed

	def get_week_schedule(players):
		embeds = []
		for day in range(0, 7):
			embeds.append(Formatter.get_day_schedule(players, calendar.day_name[day]))
		return embeds

	def format_player_name(player):
		return Formatter.role_emotes[player.role] + " " + player.name 
