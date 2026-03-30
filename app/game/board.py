from dataclasses import dataclass


@dataclass
class Cell:
    p1: int = 0
    p2: int = 0

    @property
    def is_blank(self) -> bool:
        return self.p1 == 0 and self.p2 == 0

    @property
    def is_black(self) -> bool:
        return self.p1 == 5 and self.p2 == 5

    def owner(self) -> int | None:
        """Returns 1, 2, or None (contested/blank/black)."""
        if self.p1 > self.p2:
            return 1
        if self.p2 > self.p1:
            return 2
        return None


class Board:
    def __init__(self, size: int):
        self.size = size
        self.grid: list[list[Cell]] = [
            [Cell() for _ in range(size)] for _ in range(size)
        ]

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.size and 0 <= col < self.size

    def cell(self, row: int, col: int) -> Cell:
        return self.grid[row][col]

    def paint(self, row: int, col: int, player: int, amount: int) -> None:
        """
        Apply `amount` paint for `player` (1 or 2) to cell (row, col).
        Raises PaintBlackCell or PaintOverflow — callers convert to
        the appropriate runtime signal.
        """
        c = self.grid[row][col]
        if c.is_black:
            raise PaintBlackCell(row, col)
        current = c.p1 if player == 1 else c.p2
        if current + amount > 5 or c.p1 + c.p2 + amount > 10:
            raise PaintOverflow(row, col, amount)
        if player == 1:
            c.p1 += amount
        else:
            c.p2 += amount

    # ---------------------------------------------------------------- territory

    def territory(self) -> tuple[int, int, int, int]:
        """
        Returns (p1_dominated, p2_dominated, black_cells, total_cells).
        """
        p1 = p2 = 0
        black = 0
        for row in self.grid:
            for c in row:
                owner = c.owner()
                if owner == 1:
                    p1 += 1
                elif owner == 2:
                    p2 += 1
                if c.is_black:
                    black += 1
        return p1, p2, black, self.size * self.size

    # ---------------------------------------------------------------- snapshot

    def snapshot(self) -> list[list[tuple[int, int]]]:
        return [[( c.p1, c.p2) for c in row] for row in self.grid]

    def restore(self, snap: list[list[tuple[int, int]]]) -> None:
        for r, row in enumerate(snap):
            for c_idx, pair in enumerate(row):
                self.grid[r][c_idx].p1 = pair[0]
                self.grid[r][c_idx].p2 = pair[1]


# ------------------------------------------------------------------------ errors

class PaintBlackCell(Exception):
    def __init__(self, row: int, col: int):
        super().__init__(f"paint() on black cell at ({row}, {col})")
        self.row = row
        self.col = col


class PaintOverflow(Exception):
    def __init__(self, row: int, col: int, amount: int):
        super().__init__(f"paint({amount}) would overflow cell at ({row}, {col})")
        self.row = row
        self.col = col
        self.amount = amount
