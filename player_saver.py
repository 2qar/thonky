import json
from day import Day
import os

class PlayerSaver():
	def save_players(players, week_schedule):
		week = week_schedule.days[0].date.replace('/', '-')
		PlayerSaver.make_folder_if_necessary("players")
		for player in players.unsorted_list:
				player_folder = "players/{0}".format(player.name)
				PlayerSaver.make_folder_if_necessary(player_folder)
				filename = player_folder + "/{0}.json".format(week)
				availability = {}
				for key in Day:
					day = key.name
					availability[day] = player.get_availability_for_day(day)
				with open(filename, 'w') as outfile:
					json.dump(availability, outfile)

	def make_folder_if_necessary(folder):
		if not os.path.exists(folder):
			os.makedirs(folder)

class DataAnalyzer():
	def get_player_responses(player_name):
		player_folder = None
		for player in os.listdir("players/"):
			if player_name.lower() == player.lower():
				player_folder = player

		if player_folder == None: return None

		data = {}
		directory = "players/" + player_folder
		for data_file in os.listdir(directory):
			path = "players/{0}/{1}".format(player_folder, data_file)

			# get the date to use as a key
			dot = data_file.find(".")
			key = data_file[:dot]

			with open(path) as file:
				data[key] = json.load(file)

		return data

	def get_response_counts(player_name):
		data = DataAnalyzer.get_player_responses(player_name)
		if data == None: return None

		response_counts = {
			"Yes": 0,
			"Maybe": 0,
			"No": 0,
			"Nothing": 0
		}

		# get all of the response totals
		for week in data:
			for day in data[week]:
				for response in data[week][day]:
					response_counts[response] += 1

		for response in response_counts:
			percent = round(response_counts[response] / 42.0, 2)
			formatted_percent = int(percent * 100)
			print("{0}: {1}%".format(response, formatted_percent))

for player in os.listdir("players/"):
	DataAnalyzer.get_response_counts(player)
