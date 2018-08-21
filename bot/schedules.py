class DaySchedule():
	def __init__(self, name, date, activities):
		self.name = name
		self.date = date
		self.activities = activities

	def get_activity_at_time(self, time, start_time=4):
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

