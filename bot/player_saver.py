from .day import Day
from .dbhandler import DBHandler

base_player_dir = "servers/{}/players"
class PlayerSaver():
	def save_players(server_id, players, week_schedule):
		week = week_schedule.days[0].date.replace('/', '-')

		with DBHandler() as handler:
			for player in players.unsorted_list:
				availability = {}
				for key in Day:
					day = key.name
					availability[day] = player.get_availability_for_day(day)

				if not handler.get_player_data(server_id, player.name, date=week):
					handler.add_player_data(server_id, player.name, week, availability)
					print(f"added {player.name} on {week} to db")
				else:
					print(f"{player.name} on {week} already added, skipping")

class DataAnalyzer():
	def get_player_responses(server_id, player_name):
		with DBHandler() as handler:
			player_data = handler.get_player_data(server_id, player_name)

			response_data = {}
			if isinstance(player_data, list):
				for entry in player_data:
					response_data[entry['date']] = entry['availability']
			else:
				response_data[player_data['date']] = player_data['availability']

			return response_data

	def get_response_percents(server_id, player_name):
		data = DataAnalyzer.get_player_responses(server_id, player_name)
		if not data: return

		response_counts = {
			"Yes": 0,
			"Maybe": 0,
			"No": 0,
			"Nothing": 0
		}

		# get all of the response totals
		week_total = 0
		for week in data:
			week_total += 1
			for day in data[week]:
				for response in data[week][day]:
					response_counts[response] += 1

		# format the counts into percents
		div_total = 42.0 * week_total
		for response in response_counts:
			percent = round(response_counts[response] / div_total, 2)
			formatted_percent = int(percent * 100)
			response_counts[response] = f"{formatted_percent}%"

		return response_counts
