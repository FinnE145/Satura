import pytest
from app.game.board import Board, Cell
from app.game.agent import Agent, get_friction, MoveOutOfBounds, MoveCollision


# ------------------------------------------------------------------ get_friction

class TestGetFriction:
    def test_blank_cell(self):
        assert get_friction(Cell(), 1) == 1
        assert get_friction(Cell(), 2) == 1

    def test_black_cell(self):
        assert get_friction(Cell(p1=5, p2=5), 1) == 20
        assert get_friction(Cell(p1=5, p2=5), 2) == 20

    def test_opponent_paint_p1_perspective(self):
        # player 1 → opponent is p2
        assert get_friction(Cell(p1=1, p2=3), 1) == 6

    def test_opponent_paint_p2_perspective(self):
        # player 2 → opponent is p1
        assert get_friction(Cell(p1=4, p2=1), 2) == 8

    def test_only_own_paint_no_friction(self):
        # opponent paint is 0 → 2*0 = 0
        assert get_friction(Cell(p1=3, p2=0), 1) == 0
        assert get_friction(Cell(p1=0, p2=3), 2) == 0


# ------------------------------------------------------------------ Agent init

class TestAgentInit:
    def test_fields(self):
        a = Agent(1, 2, 3)
        assert a.player == 1
        assert a.row == 2
        assert a.col == 3


# ------------------------------------------------------------------ adjacent()

class TestAdjacent:
    def setup_method(self):
        self.a = Agent(1, 3, 3)

    def test_up(self):
        assert self.a.adjacent("UP") == (2, 3)

    def test_down(self):
        assert self.a.adjacent("DOWN") == (4, 3)

    def test_left(self):
        assert self.a.adjacent("LEFT") == (3, 2)

    def test_right(self):
        assert self.a.adjacent("RIGHT") == (3, 4)


# ------------------------------------------------------------------ friction_for()

class TestFrictionFor:
    def test_blank_target(self):
        b = Board(5)
        a = Agent(1, 2, 2)
        assert a.friction_for("RIGHT", b) == 1

    def test_painted_target(self):
        b = Board(5)
        b.grid[2][3].p2 = 3          # opponent paint for player 1
        a = Agent(1, 2, 2)
        assert a.friction_for("RIGHT", b) == 6

    def test_black_target(self):
        b = Board(5)
        b.grid[2][3].p1 = 5
        b.grid[2][3].p2 = 5
        a = Agent(1, 2, 2)
        assert a.friction_for("RIGHT", b) == 20


# ------------------------------------------------------------------ move()

class TestMove:
    def _setup(self, size=5, a1_pos=(2, 2), a2_pos=(4, 4)):
        b = Board(size)
        a1 = Agent(1, *a1_pos)
        a2 = Agent(2, *a2_pos)
        return b, a1, a2

    def test_move_updates_position(self):
        b, a1, a2 = self._setup()
        a1.move("RIGHT", b, a2)
        assert (a1.row, a1.col) == (2, 3)

    def test_move_returns_cost(self):
        b, a1, a2 = self._setup()
        cost = a1.move("RIGHT", b, a2)
        assert cost == 1  # blank cell

    def test_move_cost_painted(self):
        b, a1, a2 = self._setup()
        b.grid[2][3].p2 = 2          # opponent paint for player 1
        cost = a1.move("RIGHT", b, a2)
        assert cost == 4

    def test_move_all_directions(self):
        for direction, expected in [("UP", (1, 2)), ("DOWN", (3, 2)),
                                     ("LEFT", (2, 1)), ("RIGHT", (2, 3))]:
            b, a1, a2 = self._setup()
            a1.move(direction, b, a2)
            assert (a1.row, a1.col) == expected

    def test_move_out_of_bounds_raises(self):
        b, a1, a2 = self._setup(a1_pos=(0, 0))
        with pytest.raises(MoveOutOfBounds) as exc:
            a1.move("UP", b, a2)
        assert exc.value.direction == "UP"

    def test_move_out_of_bounds_no_position_change(self):
        b, a1, a2 = self._setup(a1_pos=(0, 0))
        with pytest.raises(MoveOutOfBounds):
            a1.move("UP", b, a2)
        assert (a1.row, a1.col) == (0, 0)

    def test_move_collision_raises(self):
        b = Board(5)
        a1 = Agent(1, 2, 2)
        a2 = Agent(2, 2, 3)         # directly to the right
        with pytest.raises(MoveCollision) as exc:
            a1.move("RIGHT", b, a2)
        assert exc.value.direction == "RIGHT"

    def test_move_collision_no_position_change(self):
        b = Board(5)
        a1 = Agent(1, 2, 2)
        a2 = Agent(2, 2, 3)
        with pytest.raises(MoveCollision):
            a1.move("RIGHT", b, a2)
        assert (a1.row, a1.col) == (2, 2)

    def test_move_out_of_bounds_bottom_right_corner(self):
        b = Board(5)
        a1 = Agent(1, 4, 4)
        a2 = Agent(2, 0, 0)
        with pytest.raises(MoveOutOfBounds):
            a1.move("DOWN", b, a2)
        with pytest.raises(MoveOutOfBounds):
            a1.move("RIGHT", b, a2)


# ------------------------------------------------------------------ snapshot / restore

class TestAgentSnapshotRestore:
    def test_snapshot(self):
        a = Agent(1, 3, 4)
        assert a.snapshot() == (3, 4)

    def test_restore(self):
        a = Agent(1, 3, 4)
        snap = a.snapshot()
        a.row = 0
        a.col = 0
        a.restore(snap)
        assert (a.row, a.col) == (3, 4)

    def test_snapshot_not_affected_by_later_move(self):
        b = Board(5)
        a1 = Agent(1, 2, 2)
        a2 = Agent(2, 4, 4)
        snap = a1.snapshot()
        a1.move("RIGHT", b, a2)
        assert snap == (2, 2)           # snapshot is a plain tuple — unchanged
        a1.restore(snap)
        assert (a1.row, a1.col) == (2, 2)
