import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file as oauth_file, client, tools

from .players import Player
from .players import Players
from .day import Day
from .schedules import DaySchedule
from .schedules import WeekSchedule

class SheetScraper():
	""" Used for snatching some useful information from a sheet using a given doc key """

	script_scope = ['https://www.googleapis.com/auth/script.projects', 'https://www.googleapis.com/auth/spreadsheets']
	script_id = '1LPgef8gEDpefvna6p9AZVKrqvpNqWVxRD6yOhYZgFSs3QawU1ktypVEm'

	def __init__(self, doc_key):
		self.doc_key = doc_key
		self.authenticate()

	def authenticate(self):
		""" Authenticates the bot for sheets access.
			Gotta call it before calling any of the other stuff. """

		print("Authenticating Google API...")
		scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
		credentials = ServiceAccountCredentials.from_json_keyfile_name('creds/service_account.json', scope)
		self.gc = gspread.authorize(credentials)
		print("Authenticated.")

	def get_service(self):
		store = oauth_file.Storage('creds/token.json')
		creds = store.get()
		if not creds or creds.invalid:
			flow = client.flow_from_clientsecrets('creds/client_secret.json', SheetScraper.script_scope)
			creds = tools.run_flow(flow, store)
		return build('script', 'v1', http=creds.authorize(Http()))

	def get_sheet(self, sheet_name):
		return self.gc.open_by_key(self.doc_key).worksheet(sheet_name)

	def get_players(self):
		""" Get all of the players in a nice little bundle :) """

		availability = self.get_sheet("Team Availability")

		print("Getting player cells...")
		player_range_end = availability.find("Tanks Available:").row
		player_range = "C4:C" + str(player_range_end)
		player_cells = availability.range(player_range)
		
		role = ""
		players = []
		sorted_players = {}

		print("Creating player objects...")
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

		# get all of the cell notes
		request = {'function': 'getCellNotes', 'parameters': [self.doc_key, 'C3:H9']}
		service = self.get_service()
		response = service.scripts().run(body=request, scriptId=SheetScraper.script_id).execute()
		try:
			notes = response['response']['result']
		except KeyError as e:
			print(f"ERROR grabbing notes on sheet with key [{self.doc_key}].\nDoes your Google account you authenticated this app with have read access on the spreadsheet?")
			notes = [''] * 6
		
		activity_sheet = self.get_sheet("Weekly Schedule")
		day_rows = activity_sheet.range("B3:B9")

		def get_day(row, notes):
			split = row.value.split()

			name = split[0]
			name = name[0:len(name)-1]

			date = split[1]

			row_range = "C{0}:H{0}".format(row.row)
			activity_cells = activity_sheet.range(row_range)
			activities = [activity.value for activity in activity_cells]

			return DaySchedule(name, date, activities, notes)

		days = [get_day(row, note) for row, note in zip(day_rows, notes)]

		return WeekSchedule(days)
