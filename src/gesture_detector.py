import time


class GestureDetector:
    """Dwell selection: keep the fingertip on one cell for `dwell_time` seconds."""

    def __init__(self, dwell_time=1.2):
        self.dwell_time = dwell_time
        self.reset()

    def reset(self):
        self.current_cell = None
        self.start = None
        self.progress = 0.0
        self.locked = False  # after a pick, must leave the cell before picking again

    def update(self, cell):
        """Pass the cell under the finger (or None). Returns a cell index when selected."""
        if cell != self.current_cell:
            self.current_cell = cell
            self.start = time.time() if cell is not None else None
            self.progress = 0.0
            self.locked = False
            return None

        if cell is None or self.locked:
            return None

        self.progress = min((time.time() - self.start) / self.dwell_time, 1.0)
        if self.progress >= 1.0:
            self.locked = True
            self.progress = 0.0
            return cell
        return None