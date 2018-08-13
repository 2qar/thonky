import gspread
from oauth2client.service_account import ServiceAccountCredentials
from enum import Enum

class StatusEmotes(Enum):
	Yes = ":white_check_mark:"
	Maybe = ":grey_question:"
	No = ":x:"

# day offsets
class Day(Enum):
	MONDAY = 0
	TUESDAY = 6
	WEDNESDAY = 12
	THURSDAY = 18
	FRIDAY = 24
	SATURDAY = 30
	SUNDAY = 36
	
class Player():
	def __init__(self, name, role, availability):
		self.name = name
		self.role = role
		self.availability = availability

	def get_availability_for_day(self, day):
		start = Day[day.upper()].value
		return self.availability[start:start + 6]

	def get_availability_at_time(self, day, time, start_time):
		offset = int(time) - start_time
		if offset < 0:
			return None
		return self.get_availability_for_day(day)[offset]

	def __str__(self):
		return "Name: " + self.name + "\nRole: " + self.role + "\nAvailability: " + str(self.availability)

class DaySchedule():
	def __init__(self, name, date, activities):
		self.name = name
		self.date = date
		self.activities = activities

	def get_activity_at_time(self, time, start_time):
		offset = int(time) - start_time
		if offset < 0:
			return None
		return self.activities[offset]

	def get_formatted_name(self):
		return self.name + ", " + self.date

	def __str__(self):
		return self.name + ", " + self.date + ": " + str(self.activities)

class WeekSchedule():
	def __init__(self, days):
		self.days = days

	def get_day(self, name):
		for day in self.days:
			if name.lower() == day.name.lower():
				return day

	def __str__(self):
		week_string = ""
		for day in self.days:
			week_string += str(day) + "\n"
		return week_string

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
		roles = {
			"Tanks" : 0,
			"DPS" : 0,
			"Supports" : 0,
			"Flex" : 0
		}

		print("(4/4) Creating player objects...")
		for cell in player_cells:
			if cell.value != '':
				vals = availability.row_values(row=cell.row)
				print(vals)
				if vals[1] != '':
					role = vals[1]
				roles[role] += 1
				name = vals[2]
				available_times = vals[3:]
				if len(vals) == 3:
					continue
				players.append(Player(name, role, available_times))
		print("Done! :)")
		return players

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
