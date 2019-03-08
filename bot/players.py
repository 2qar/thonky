from gspread import Cell
from typing import List

from .cell_container import CellContainer


class Player(CellContainer):
    def __init__(self, name: str, role: str, availability: List[Cell]):
        super().__init__(availability)
        self.name = name
        self.role = role

    @property
    def availability(self) -> List[str]:
        return [cell.value for cell in self.cells]

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

    def as_dict(self):
        return {"name": self.name, "role": self.role, "availability": self.cells_dict()}


class Players:
    def __init__(self, sorted_list: dict, unsorted_list: list):
        self.sorted_list = sorted_list
        self.unsorted_list = unsorted_list

    def as_dict(self):
        sorted_list = {}
        for key in self.sorted_list:
            sorted_list[key] = [player.as_dict() for player in self.sorted_list[key]]
        return {'sorted_list': sorted_list}
