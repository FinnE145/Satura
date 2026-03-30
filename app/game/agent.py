from .board import Board, Cell

_DELTAS: dict[str, tuple[int, int]] = {
    "UP":    (-1,  0),
    "DOWN":  ( 1,  0),
    "LEFT":  ( 0, -1),
    "RIGHT": ( 0,  1),
}


def get_friction(cell: Cell, player: int) -> int:
    """
    Friction cost to move into `cell` from `player`'s perspective.

      blank cell          → 1
      black cell          → 20
      otherwise           → 2 * opponent_paint
    """
    if cell.is_blank:
        return 1
    if cell.is_black:
        return 20
    opp = cell.p2 if player == 1 else cell.p1
    return 2 * opp


class Agent:
    def __init__(self, player: int, row: int, col: int):
        self.player = player  # 1 or 2
        self.row = row
        self.col = col

    # ---------------------------------------------------------------- movement

    def adjacent(self, direction: str) -> tuple[int, int]:
        dr, dc = _DELTAS[direction]
        return self.row + dr, self.col + dc

    def friction_for(self, direction: str, board: Board) -> int:
        """Friction cost to move in `direction` from current position."""
        r, c = self.adjacent(direction)
        return get_friction(board.cell(r, c), self.player)

    def move(self, direction: str, board: Board, opponent: "Agent") -> int:
        """
        Attempt to move one cell in `direction`.

        Returns the op cost of the move on success.
        Raises MoveOutOfBounds if the target is off the board.
        Raises MoveCollision if the target is occupied by the opponent.
        """
        r, c = self.adjacent(direction)

        if not board.in_bounds(r, c):
            raise MoveOutOfBounds(direction)

        if opponent.row == r and opponent.col == c:
            raise MoveCollision(direction)

        cost = get_friction(board.cell(r, c), self.player)
        self.row = r
        self.col = c
        return cost

    def snapshot(self) -> tuple[int, int]:
        return (self.row, self.col)

    def restore(self, snap: tuple[int, int]) -> None:
        self.row, self.col = snap


# -------------------------------------------------------------------- signals

class MoveOutOfBounds(Exception):
    def __init__(self, direction: str):
        super().__init__(f"move({direction}) is outside the board boundary")
        self.direction = direction


class MoveCollision(Exception):
    def __init__(self, direction: str):
        super().__init__(f"move({direction}) collides with opponent agent")
        self.direction = direction
