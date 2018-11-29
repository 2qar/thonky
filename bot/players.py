from gspread import Cell
from typing import List


class Player:
    def __init__(self, name: str, role: str, availability: List[Cell]):
        self.name = name
        self.role = role
        self._availability = availability

    @property
    def availability(self) -> List[str]:
        return [cell.value for cell in self._availability]

    @property
    def cells(self) -> List[Cell]:
        return self._availability

    def get_availability_for_day(self, day: int):
        start = day * 6
        return self.availability[start:start + 6]

    def get_availability_at_time(self, day: int, time: int, start_time: int):
        offset = int(time) - start_time
        if offset < 0:
                return None
        return self.get_availability_for_day(day)[offset]

    def __str__(self):
        return f"Name: {self.name} \nRole: {self.role} \nAvailability: {self.availability}"


class Players:
    def __init__(self, sorted_list: dict, unsorted_list: list):
        self.sorted_list = sorted_list
        self.unsorted_list = unsorted_list
