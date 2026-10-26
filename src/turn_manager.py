class TurnManager:

    def __init__(self):
        self.turn = "X"

    def switch_turn(self):
        self.turn = "O" if self.turn == "X" else "X"