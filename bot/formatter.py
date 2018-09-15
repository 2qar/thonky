import calendar
import datetime
from discord import Embed
from discord import Colour

from .players import Player
from .player_saver import DataAnalyzer

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

overbuff_role_emotes = {
	"Offense": role_emotes['DPS'],
	"Defense": role_emotes['DPS'],
	"Tank": role_emotes['Tanks'],
	"Support": role_emotes['Supports'],
	"???": ":ghost:"
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

battlefy_logo = 'http://s3.amazonaws.com/battlefy-assets/helix/images/logos/logo.png'

thonk_link = "https://cdn.discordapp.com/attachments/437847669839495170/476837854966710282/thonk.png"

sheet_url = "https://docs.google.com/spreadsheets/d/15oxfuWKI97HZRaSG5Jxcyw5Ycdr9mPDc_VmEoHFu4-c/edit#gid=1697055162"


class Formatter():
	zone = "PDT"

	def get_template_embed(title):
		embed = Embed()
		embed.colour = Colour.green()
		embed.set_author(name=title, url=sheet_url)
		embed.set_footer(text=f"Times shown in {Formatter.zone}")
		embed.set_thumbnail(url=thonk_link)
		return embed

	# spits back the player's availability in emotes
	def get_day_availability(player, day, start_time):
		data = {}
		availability_on_day = player.get_availability_for_day(day)

		for i in range(0, len(availability_on_day)):
			available = availability_on_day[i]
			available_emote = status_emotes[available]
			time = i + start_time
			data[time] = available_emote
		return data

	def get_player_at_time(player, day, time, start):
		availability = player.get_availability_at_time(day, time, start)

		available_emote = status_emotes[availability]
		availabile_response = availability_responses[availability]

		message = f"{availabile_emote} {player.name} {available_response} at {time}" 

		day_not_today = datetime.date.today().weekday() != list(calendar.day_name).index(day)
		message += f" on {day}." if day_not_today else "."
		return message

	def get_player_on_day(player, day, start_time):
		embed = Formatter.get_template_embed(f"{player.name} on {day}")
		embed.set_thumbnail(url=thonk_link)
		formatted_data = Formatter.get_day_availability(player, day, start_time)

		for key in formatted_data:
			embed.add_field(name=key, value=formatted_data[key], inline=False)

		return embed

	def get_player_averages(server_id, player_name):
		embed = Formatter.get_template_embed(f"Average Responses for {player_name}")
		responses = DataAnalyzer.get_response_percents(server_id, player_name)
		if not responses: return None

		format_response = (lambda response: f"{status_emotes[response]} {response} {responses[response]}")
		embed_str = '\n'.join([format_response(response) for response in responses])

		embed.add_field(name="Responses", value=embed_str, inline=False)
		embed.set_footer(text="")
		return embed

	def get_hour_schedule(server_info, day, hour, start_time):
		players = server_info.players
		week_schedule = server_info.week_schedule

		day_obj = week_schedule.get_day(day)
		activity = day_obj.get_activity_at_time(hour, start_time)
		format_name = day_obj.get_formatted_name()
		title = f"{activity} on {format_name} at {hour} PM"
		embed = Formatter.get_template_embed(title)

		for role in players.sorted_list:
			players_string = ""
			available_count = 0
			for player in players.sorted_list[role]:
				try:
					available = player.get_availability_at_time(day, hour, start_time)
					if available == "Yes":
						available_count += 1
					emote = status_emotes[available]
					player_str = player.name + "\t" + emote
					players_string += player_str + "\n"
				except:
					players_string += player.name + "\t:ghost:\n"
					print(f"Unable to add player {player.name} to {role} string")

			role_status = ":warning:" if available_count < 2 else ":ballot_box_with_check:"
			role_name = f"{role_emotes[role]} {role} {role_status}"
			embed.add_field(name=role_name, value=players_string)

		return embed

	def get_day_schedule(players, day, start_time):
		embed = Formatter.get_template_embed(f"Schedule for {day}")

		Formatter.add_time_field(embed, "Player Name", start_time)
			
		# add all of the players to the embed
		for player in players.unsorted_list:
			try:
				availability = Formatter.get_day_availability(player, day, start_time)
				emotes = [availability[key] for key in availability]
				formatted_status = ', '.join([emote for emote in emotes])
				player_name = f"{role_emotes[player.role]} {player.name}"

				embed.add_field(name=player_name, value=formatted_status, inline=False)
			except Exception as reason:
				print(f"Unable to add player {player.name} to embed: {reason}")

		embed = Formatter.add_role_availability(embed, players, day)

		return embed

	def get_enemy_team_info(od_round, team_info):
		title = f"Match against {team_info['name']} in Round {od_round}"
		embed = Embed()
		embed.colour = Colour.red()
		embed.set_author(name=title, url=team_info['match_link'], icon_url=battlefy_logo)

		embed.set_thumbnail(url=team_info['logo'])
		
		players_with_info = [player for player in team_info['players'] if not isinstance(player['info'], str)]
		players =  sorted(players_with_info, key=lambda k: k['info']['sr'], reverse=True)

		def format_player_info(player):
			if isinstance(player['info'], str):
				return ":ghost: " + player['name']
			else:
				role_emote = overbuff_role_emotes[player['info']['role']]
				sr = player['info']['sr']
				if sr == 0: sr = '???'
				return f"{role_emote} {player['name']}: {sr}"

		player_string = '\n'.join([format_player_info(player) for player in team_info['players']])

		def get_top_average():
			top_players = players[:6]

			avg = 0
			for player in top_players:
				avg += player['info']['sr']

			return int(avg / len(top_players))

		if len(players) >= 6:
			average_sr = f"**Average SR: {team_info['sr_avg']}**\n"
			player_string = average_sr + player_string
			
			top_average = f"Top 6 Average: {get_top_average()}"
			embed.add_field(name=top_average, value=player_string)
		else:
			embed.add_field(name=f"Average SR: {team_info['sr_avg']}")

		return embed

	def get_week_activity_schedule(week_schedule, start_time):
		week = week_schedule.days[0].date
		embed = Formatter.get_template_embed(f"Week of {week}")
		Formatter.add_time_field(embed, "Times", start_time)

		def get_formatted_activity_name(activity):
			if activity == '':
				return ":grey_question:"
			try:
				return activity_emotes[activity]
			except:
				return f':regional_indicator_{activity[0].lower()}:'

		for day in week_schedule.days:
			title = day.get_formatted_name()

			# format all of the activities into one nice and pretty string
			formatted_activities = ', '.join([get_formatted_activity_name(activity) for activity in day.activities])

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

			emote_count = [letter_emotes[value] for value in count]

			schedule_string = ", ".join([emote for emote in emote_count])

			title = role_emotes[role] + " " + role
			embed.add_field(name=title, value=schedule_string, inline=False)

		return embed

	def add_time_field(embed, title, start_time):
		time_string = ""
		for time in range(0, 5):
			time_string += letter_emotes[time + start_time] + ", "
		time_string += letter_emotes[5 + start_time]
		embed.add_field(name=title, value = time_string, inline=False)

	def get_week_schedule(players):
		days = list(calendar.day_name)
		return [Formatter.get_day_schedule(players, day) for day in days]
