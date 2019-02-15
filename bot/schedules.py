import datetime
from typing import List
from gspread import Cell


class DaySchedule:
    def __init__(self, name: str, date: str, activities: List[Cell], notes: List[str]):
        self.name = name
        self.date = date
        self._activities = activities
        self.notes = notes

    @property
    def activities(self) -> List[str]:
        return [cell.value for cell in self._activities]

    @property
    def cells(self) -> List[Cell]:
        return self._activities

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

    def first_activity(self, remind_activities: List[str]):
        """ Get the first pingable activity in the list """

        lower_remind_activities = [a.lower() for a in remind_activities]
        for i, activity in enumerate(self.activities):
            if activity.lower() in lower_remind_activities:
                return i
        return -1

    def get_vods(self):
        """ Return the indexes of each Player VOD with a note. """

        vods = []
        for i, activity in enumerate(self.activities):
            if activity.lower() == 'player vod':
                try:
                    if self.notes[i]:
                        vods.append(i)
                except IndexError:
                    pass
        return vods

    def __str__(self):
        return f"{self.name}, {self.date}"


class WeekSchedule:
    def __init__(self, days):
        self.days = days

    def __iter__(self):
        yield from self.days

    @property
    def today(self):
        today = datetime.date.today().weekday()
        return self.days[today]

    def get_day(self, name):
        for day in self:
            if name.lower() == day.name.lower():
                return day

    def __getitem__(self, day):
        return self.days[day]

    def __str__(self):
        week_string = ""
        for day in self:
            week_string += str(day) + "\n"
        return week_string
