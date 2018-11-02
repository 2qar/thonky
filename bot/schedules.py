import datetime

class DaySchedule():
    def __init__(self, name, date, activities, notes):
        self.name = name
        self.date = date
        self.activities = activities
        self.notes = notes

    def get_activity_at_time(self, time, start_time=4):
        offset = int(time) - start_time
        if offset < 0:
            return None
        return self.activities[offset]

    def as_date(self):
        date_split = self.date.split('/')
        month = int(date_split[0])
        day = int(date_split[1])
        return datetime.date(datetime.datetime.today().year, month, day)

    def first_activity(self, remind_activities):
        for i, activity in enumerate(self.activities):
            if activity.lower() in remind_activities:
                return i
        return -1

    def get_vods(self):
        """ Return the indeces of each Player VOD with a note. """
        vods = []
        for i in range(0, len(self.activities)):
            if self.activities[i].lower() == 'player vod' and self.notes[i]:
                vods.append(i)
        return vods

    def __str__(self):
        return f"{self.name}, {self.date}"

class WeekSchedule():
    def __init__(self, days):
        self.days = days

    def __iter__(self):
        yield from self.days

    def get_day(self, name):
        for day in self:
            if name.lower() == day.name.lower():
                return day

    def __str__(self):
        week_string = ""
        for day in self:
            week_string += str(day) + "\n"
        return week_string
