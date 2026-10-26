class ScoreManager:

    def __init__(self):
        self.x_score = 0
        self.o_score = 0

    def add_x(self):
        self.x_score += 1

    def add_o(self):
        self.o_score += 1