import json
import os

from .day import Day

player_dir = "players"
class PlayerSaver():
	def save_players(players, week_schedule):
		week = week_schedule.days[0].date.replace('/', '-')
		PlayerSaver.make_folder_if_necessary(player_dir)
		for player in players.unsorted_list:
				player_folder = f"{player_dir}/{player.name}"
				PlayerSaver.make_folder_if_necessary(player_folder)
				filename = player_folder + f"/{week}.json"
				availability = {}
				for key in Day:
					day = key.name
					availability[day] = player.get_availability_for_day(day)
				print(filename)
				if os.path.exists(filename):
					print("\talready saved")
					continue
				with open(filename, 'w') as outfile:
					json.dump(availability, outfile)

	def make_folder_if_necessary(folder):
		if not os.path.exists(folder):
			os.makedirs(folder)

class DataAnalyzer():
	def get_player_responses(player_name):
		try:
			os.listdir(player_dir)
		except:
			print("No player data folder")
			return

		player_folder = None
		for player in os.listdir(player_dir):
			if player_name.lower() == player.lower():
				player_folder = player

		if player_folder == None: return None

		data = {}
		directory = player_dir + "/" + player_folder
		for data_file in os.listdir(directory):
			path = f"{player_dir}/{player_folder}/{data_file}"

			# get the date to use as a key
			dot = data_file.find(".")
			key = data_file[:dot]

			with open(path) as file:
				data[key] = json.load(file)

		return data

	def get_response_percents(player_name):
		data = DataAnalyzer.get_player_responses(player_name)
		if data == None: return None

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
