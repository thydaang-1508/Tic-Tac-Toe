class Board:
    def __init__(self, size=3):
        self.size = size                      # 3 means 3x3, 9 means 9x9
        self.cells = [""] * (size * size)     # "", "X" or "O"

    def set_size(self, size):
        self.size = size
        self.reset()

    def reset(self):
        self.cells = [""] * (self.size * self.size)

    def is_empty(self, idx):
        return self.cells[idx] == ""

    def place(self, idx, player):
        if self.is_empty(idx):
            self.cells[idx] = player
            return True
        return False