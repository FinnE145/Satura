import pytest
from app.game.board import Board, Cell, PaintBlackCell, PaintOverflow


# ------------------------------------------------------------------ Cell

class TestCell:
    def test_defaults(self):
        c = Cell()
        assert c.p1 == 0 and c.p2 == 0

    def test_is_blank_true(self):
        assert Cell().is_blank

    def test_is_blank_false(self):
        assert not Cell(p1=1).is_blank

    def test_is_black_true(self):
        assert Cell(p1=5, p2=5).is_black

    def test_is_black_false(self):
        assert not Cell(p1=5, p2=4).is_black

    def test_owner_p1(self):
        assert Cell(p1=3, p2=1).owner() == 1

    def test_owner_p2(self):
        assert Cell(p1=1, p2=3).owner() == 2

    def test_owner_none_blank(self):
        assert Cell().owner() is None

    def test_owner_none_tied(self):
        assert Cell(p1=2, p2=2).owner() is None

    def test_owner_none_black(self):
        assert Cell(p1=5, p2=5).owner() is None


# ------------------------------------------------------------------ Board init

class TestBoardInit:
    def test_size(self):
        b = Board(5)
        assert b.size == 5

    def test_grid_dimensions(self):
        b = Board(4)
        assert len(b.grid) == 4
        assert all(len(row) == 4 for row in b.grid)

    def test_all_cells_blank(self):
        b = Board(3)
        for row in b.grid:
            for c in row:
                assert c.is_blank


# ------------------------------------------------------------------ in_bounds

class TestInBounds:
    def setup_method(self):
        self.b = Board(5)

    def test_inside(self):
        assert self.b.in_bounds(0, 0)
        assert self.b.in_bounds(4, 4)
        assert self.b.in_bounds(2, 3)

    def test_negative_row(self):
        assert not self.b.in_bounds(-1, 0)

    def test_negative_col(self):
        assert not self.b.in_bounds(0, -1)

    def test_row_too_large(self):
        assert not self.b.in_bounds(5, 0)

    def test_col_too_large(self):
        assert not self.b.in_bounds(0, 5)


# ------------------------------------------------------------------ cell()

class TestCellAccessor:
    def test_returns_same_object(self):
        b = Board(3)
        b.grid[1][2].p1 = 3
        assert b.cell(1, 2).p1 == 3


# ------------------------------------------------------------------ paint()

class TestPaint:
    def setup_method(self):
        self.b = Board(5)

    def test_paint_p1(self):
        self.b.paint(0, 0, 1, 3)
        assert self.b.cell(0, 0).p1 == 3

    def test_paint_p2(self):
        self.b.paint(0, 0, 2, 2)
        assert self.b.cell(0, 0).p2 == 2

    def test_paint_accumulates(self):
        self.b.paint(1, 1, 1, 2)
        self.b.paint(1, 1, 1, 2)
        assert self.b.cell(1, 1).p1 == 4

    def test_paint_black_cell_raises(self):
        self.b.grid[0][0].p1 = 5
        self.b.grid[0][0].p2 = 5
        with pytest.raises(PaintBlackCell) as exc:
            self.b.paint(0, 0, 1, 1)
        assert exc.value.row == 0
        assert exc.value.col == 0

    def test_paint_overflow_own_cap(self):
        # p1 already at 5 — adding 1 overflows
        self.b.grid[2][2].p1 = 5
        with pytest.raises(PaintOverflow) as exc:
            self.b.paint(2, 2, 1, 1)
        assert exc.value.row == 2
        assert exc.value.col == 2

    def test_paint_overflow_total_cap(self):
        # p1=4, p2=4 — adding 2 for p1 would push total to 10+2
        self.b.grid[0][1].p1 = 4
        self.b.grid[0][1].p2 = 4
        with pytest.raises(PaintOverflow):
            self.b.paint(0, 1, 1, 3)

    def test_paint_exactly_at_cap(self):
        # p1=5 is the max; adding 5 in one shot should work
        self.b.paint(0, 0, 1, 5)
        assert self.b.cell(0, 0).p1 == 5

    def test_paint_combined_exactly_at_total_cap(self):
        # p1=5, p2=5 would be black — but getting there individually:
        self.b.paint(0, 0, 1, 5)
        self.b.paint(0, 0, 2, 5)
        assert self.b.cell(0, 0).is_black


# ------------------------------------------------------------------ territory()

class TestTerritory:
    def test_all_blank(self):
        b = Board(3)
        p1, p2, black, total = b.territory()
        assert p1 == 0 and p2 == 0 and black == 0 and total == 9

    def test_total_cells(self):
        b = Board(4)
        assert b.territory()[3] == 16

    def test_p1_dominates(self):
        b = Board(2)
        b.grid[0][0].p1 = 3
        p1, p2, black, total = b.territory()
        assert p1 == 1 and p2 == 0

    def test_p2_dominates(self):
        b = Board(2)
        b.grid[0][0].p2 = 3
        p1, p2, black, total = b.territory()
        assert p1 == 0 and p2 == 1

    def test_black_cells_counted(self):
        b = Board(2)
        b.grid[0][0].p1 = 5
        b.grid[0][0].p2 = 5
        p1, p2, black, total = b.territory()
        assert black == 1
        assert p1 == 0  # black cells are not dominated

    def test_tied_not_counted(self):
        b = Board(2)
        b.grid[1][1].p1 = 2
        b.grid[1][1].p2 = 2
        p1, p2, _, _ = b.territory()
        assert p1 == 0 and p2 == 0


# ------------------------------------------------------------------ snapshot / restore

class TestSnapshotRestore:
    def test_snapshot_shape(self):
        b = Board(3)
        snap = b.snapshot()
        assert len(snap) == 3
        assert all(len(row) == 3 for row in snap)

    def test_snapshot_values(self):
        b = Board(2)
        b.grid[0][1].p1 = 2
        b.grid[0][1].p2 = 3
        snap = b.snapshot()
        assert snap[0][1] == (2, 3)

    def test_snapshot_is_copy(self):
        b = Board(2)
        snap = b.snapshot()
        snap[0][0] = (9, 9)
        assert b.cell(0, 0).p1 == 0  # original unchanged

    def test_restore(self):
        b = Board(2)
        b.grid[1][0].p1 = 4
        snap = b.snapshot()
        b.grid[1][0].p1 = 0
        b.restore(snap)
        assert b.cell(1, 0).p1 == 4

    def test_restore_full_board(self):
        b = Board(3)
        b.grid[0][0].p1 = 1
        b.grid[2][2].p2 = 3
        snap = b.snapshot()
        # mutate everything
        for row in b.grid:
            for c in row:
                c.p1 = 0
                c.p2 = 0
        b.restore(snap)
        assert b.cell(0, 0).p1 == 1
        assert b.cell(2, 2).p2 == 3
        assert b.cell(1, 1).p1 == 0
