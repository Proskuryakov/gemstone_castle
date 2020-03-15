import copy
import random as rnd
from enum import Enum
from typing import Tuple


class CellContents(Enum):
    SQUARE = 0  # квадрат в клетке
    CIRCLE = 1  # круг в клетке
    TRIANGLE = 2  # треугольник в клетке
    KNIGHT = 3  # рыцарь в клетке
    PRINCESS = 4  # принцесса в клетке
    EMPTY = 5


class GameState(Enum):
    PLAYING = 0  # игра не закончена
    WIN = 1      # игра закончена


class Cell:
    def __init__(self, is_active: bool = False, contents: CellContents = CellContents.EMPTY) -> None:
        self._is_active = is_active  # выделена ли эта клетка
        self._contents = contents  # тип содержимого клетки

    def get_contents(self) -> CellContents:
        return self._contents

    def set_contents(self, value):
        self._contents = value

    def get_active(self) -> bool:
        return self._is_active

    def set_active(self, value):
        self._is_active = value

    contents = property(get_contents, set_contents)
    is_active = property(get_active, set_active)

    def __str__(self) -> str:
        return 'Contents = {}'.format(self.contents)


class Game:

    START_ROW_COUNT = 8
    START_COL_COUNT = 5
    START_MINIMUM_CHAIN_LENGTH = 3

    def __init__(self, row_count: int = START_ROW_COUNT,
                 col_count: int = START_COL_COUNT,
                 min_chain_len: int = START_MINIMUM_CHAIN_LENGTH) -> None:
        self._row_count = row_count
        self._col_count = col_count
        self._min_chain_len = min_chain_len
        self._start_cell = None
        self._state = None
        self._active_cells = list()
        self.new_game()

    def new_game(self) -> None:
        self._init_field()
        self._random_fill()
        self[0, self.col_count//2].contents = CellContents.KNIGHT
        self[self.row_count-1, self.col_count//2].contents = CellContents.PRINCESS
        self._state = GameState.PLAYING

    def _init_field(self):
        self._field = [
            copy.deepcopy([Cell() for _ in range(self.col_count)])
            for _ in range(self.row_count)
        ]

    def _random_fill(self):
        p = [i for i in self.my_random(self._col_count * self._row_count)]
        for r in range(self._row_count):
            for c in range(self._col_count):
                self[r, c].contents = CellContents(p[r * self._col_count + c])

    def get_row_count(self):
        return self._row_count

    def set_row_count(self, row):
        self._row_count = row

    def get_col_count(self) -> int:
        return self._col_count

    def set_col_count(self, col):
        self._col_count = col

    def get_min_chain_len(self) -> int:
        return self._min_chain_len

    def set_min_chain_len(self, min_chain_len):
        self._min_chain_len = min_chain_len

    row_count = property(get_row_count, set_row_count)
    col_count = property(get_col_count, set_col_count)
    min_chain_len = property(get_min_chain_len, set_min_chain_len)

    @property
    def state(self) -> GameState:
        return self._state

    @property
    def active_cells(self) -> list:
        return self._active_cells

    def __getitem__(self, indices: Tuple[int, int]) -> Cell:
        return self._field[indices[0]][indices[1]]

    def _get_coordinates_princess_and_knight(self):
        knight = None
        princess = None

        for r in range(self.row_count):
            for c in range(self.col_count):
                if knight is not None and princess is not None:
                    break
                if self[r, c].contents == CellContents.PRINCESS:
                    princess = (r, c)
                if self[r, c].contents == CellContents.KNIGHT:
                    knight = (r, c)
        return princess, knight

    def _is_knight_above_princess(self) -> bool:
        princess, knight = self._get_coordinates_princess_and_knight()
        return princess[1] == knight[1] and princess[0] - knight[0] == 1

    def _update_playing_state(self) -> None:
        if self._is_knight_above_princess():
            self._state = GameState.WIN
        else:
            self._state = GameState.PLAYING

    def _clear_active_cell(self) -> None:
        for rc in self._active_cells:
            self[rc].contents = CellContents.EMPTY

    def _step_down(self):
        last_index = len(self._active_cells) - 1
        new_elements = tuple(Cell(contents=CellContents(i)) for i in self.my_random(len(self._active_cells)))

        tran = list(zip(*self._field))
        for c, cc in enumerate(tran):
            empty_cell, r = None, -1
            for r, rr in enumerate(tran[c]):
                if rr.contents == CellContents.EMPTY:
                    empty_cell, index = rr, r
                    break
            if empty_cell is not None:
                self._active_cells.remove((r, c))
                tran[c] = new_elements[last_index:last_index+1] + tran[c][:r] + tran[c][r + 1:]
                last_index -= 1

        self._field = list(zip(*tran))


    def _add(self, rc):
        self._active_cells.append(rc)
        self[rc].is_active = True

    def _remove(self, rc):
        self._active_cells.remove(rc)
        self[rc].is_active = False

    def on_mouse_press(self, rc):
        self._active_cells = list()
        self._add(rc)

    def update_past_mouse_release(self):
        self._active_cells = None
        self._update_playing_state()

    def step_down_generator(self):
        if len(self._active_cells) >= self.min_chain_len:
            self._clear_active_cell()
            while len(self._active_cells) > 0:
                self._step_down()
                yield True
        else:
            for current_rc in self._active_cells:
                self[current_rc].is_active = False
            yield False

    def on_mouse_move(self, rc) -> bool:
        if rc in self._active_cells:
            return False
        current_cell = self[rc]
        last_cell = self[self._active_cells[-1]]
        if len(self._active_cells) >= 2:
            if self._active_cells[-2] == rc:
                self._remove(self._active_cells[-1])
                return
        if current_cell.contents == last_cell.contents and \
                self.is_near(rc, self._active_cells[-1]) and \
                not current_cell.is_active:
            self._add(rc)
        return True

    @staticmethod
    def is_near(cell1, cell2) -> bool:
        return (abs(cell1[0] - cell2[0]) == 0 and abs(cell1[1] - cell2[1]) == 1) or \
               (abs(cell1[0] - cell2[0]) == 1 and abs(cell1[1] - cell2[1]) == 0)

    @staticmethod
    def my_random(count):
        for _ in range(count):
            yield rnd.randint(0, 2)