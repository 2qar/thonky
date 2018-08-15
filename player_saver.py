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
