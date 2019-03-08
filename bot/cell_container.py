from gspread import Cell
from typing import List

from abc import ABC, abstractmethod


class CellContainer(ABC):
    def __init__(self, cells: List[Cell]):
        self._cells = cells

    @property
    def cells(self) -> List[Cell]:
        return self._cells

    def cells_dict(self):
        def cell_dict(cell: Cell):
            return {"row": cell.row, "col": cell.col, "value": cell.value}
        return [cell_dict(cell) for cell in self._cells]

    @abstractmethod
    def as_dict(self):
        pass
