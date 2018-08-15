from day import Day

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

class Players():
	def __init__(self, sorted_list, unsorted_list):
		self.sorted_list = sorted_list
		self.unsorted_list = unsorted_list

	def get_players_with_role(role):
		return player_list[role.title()]
