import gspread
from oauth2client.service_account import ServiceAccountCredentials

from .players import Player
from .players import Players
from .day import Day
from .schedules import DaySchedule
from .schedules import WeekSchedule

	

class SheetScraper():
	""" Used for interacting with the main spreadsheet """

	# FwB doc key
	#doc_key = '15oxfuWKI97HZRaSG5Jxcyw5Ycdr9mPDc_VmEoHFu4-c'
	#QX2 key
	#doc_key = '19LIrH878DY9Ltaux3KlfIenmMFfPTA16NWnnQQMHG0Y'
	def __init__(self, doc_key):
		self.doc_key = doc_key
		self.authenticate()

	def authenticate(self):
		""" Authenticates the bot for sheets access.
			Gotta call it before calling any of the other stuff. """

		print("Authenticating Google API...")
		scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
		credentials = ServiceAccountCredentials.from_json_keyfile_name('bot/Scrim Schedule Bot-f210d5f93412.json', scope)
		self.gc = gspread.authorize(credentials)
		print("Authenticated.")

	def get_sheet(self, sheet_name):
		return self.gc.open_by_key(self.doc_key).worksheet(sheet_name)

	def get_players(self):
		""" Get all of the players in a nice little bundle :) """

		availability = self.get_sheet("Team Availability")

		print("(3/4) Getting player cells...")
		player_range_end = availability.find("Tanks Available:").row
		player_range = "C4:C" + str(player_range_end)
		player_cells = availability.range(player_range)
		
		role = ""
		players = []
		sorted_players = {}

		print("(4/4) Creating player objects...")
		for cell in player_cells:
			if cell.value != '':
				cells = availability.range('A{0}:AS{0}'.format(cell.row))
				vals = [val.value for val in cells]
				if vals[1] != '':
					role = vals[1]
					sorted_players[role] = []
				name = vals[2]

				available_times = vals[3:]
				for time in range(0, len(available_times)):
						if available_times[time] == '':
							available_times[time] = 'Nothing'
					
				players.append(Player(name, role, available_times))

		for player in players:
			sorted_players[player.role].append(player)

		player_obj = Players(sorted_players, players)

		print("Done! :)")
		return player_obj

	def get_week_schedule(self):
		""" Returns a week schedule object for getting the activities for each day n stuff """

		activity_sheet = self.get_sheet("Weekly Schedule")

		day_cols = activity_sheet.range("B3:B9")
		days = []
		for day in day_cols:
			split = day.value.split()

			name = split[0]
			name = name[0:len(name)-1]

			date = split[1]

			row_range = "C{0}:H{0}".format(day.row)
			activity_cells = activity_sheet.range(row_range)
			activities = [activity.value for activity in activity_cells]

			days.append(DaySchedule(name, date, activities))

		return WeekSchedule(days)
