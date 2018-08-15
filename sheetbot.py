import gspread
from oauth2client.service_account import ServiceAccountCredentials
from enum import Enum
from players import Player
from players import Players
from day import Day
from schedules import DaySchedule
from schedules import WeekSchedule

class StatusEmotes(Enum):
	Yes = ":white_check_mark:"
	Maybe = ":grey_question:"
	No = ":x:"
	

#TODO: Make an object that makes getting stuff from the array of players easier
class SheetScraper():
	doc_key = '15oxfuWKI97HZRaSG5Jxcyw5Ycdr9mPDc_VmEoHFu4-c'
	def __init__(self):
		print("Authenticating Google API...")
		scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
		credentials = ServiceAccountCredentials.from_json_keyfile_name('Scrim Schedule Bot-f210d5f93412.json', scope)
		self.gc = gspread.authorize(credentials)
		print("Authenticated.")


	def get_players(self):
		print("(1/4) Opening spreadsheet...")
		doc = self.gc.open_by_key(SheetScraper.doc_key)
		print("(2/4) Opening worksheet...")
		availability = doc.worksheet('Team Availability')

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
				vals = availability.row_values(row=cell.row)
				print(vals)
				if vals[1] != '':
					role = vals[1]
					sorted_players[role] = []
				name = vals[2]
				available_times = vals[3:]
				if len(vals) == 3:
					continue
				players.append(Player(name, role, available_times))

		for player in players:
			sorted_players[player.role].append(player)

		player_obj = Players(sorted_players, players)

		print(sorted_players)

		print("Done! :)")
		return player_obj

	def get_week_schedule(self):
		doc = self.gc.open_by_key(SheetScraper.doc_key)
		activity_sheet = doc.worksheet('Weekly Schedule')

		day_cols = activity_sheet.range("B3:B9")
		days = []
		for day in day_cols:
			split = day.value.split()

			name = split[0]
			name = name[0:len(name)-1]

			date = split[1]

			row = str(day.row)
			row_range = "C" + row + ":H" + row
			activity_cells = activity_sheet.range(row_range)
			activities = []
			for activity in activity_cells:
				activities.append(activity.value)

			days.append(DaySchedule(name, date, activities))

		return WeekSchedule(days)
