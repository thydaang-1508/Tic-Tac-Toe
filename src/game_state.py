import random
import time
import cv2

from src import avatars
from src.board import Board
from src.camera import Camera
from src.game_rules import check_winner, computer_move, default_win_len, is_draw
from src.gesture_detector import GestureDetector
from src.hand_tracker import HandTracker
from src.player_profile import MAX_NAME, Profile
from src.renderer import (GREEN, H, HAND_FOR, O_COLOR, RED, W, WHITE, X_COLOR, YELLOW,
                          Renderer)

WINDOW = "Gesture Tic Tac Toe"


class Game:
    def __init__(self):
        self.board = Board()
        self.gesture = GestureDetector(dwell_time=0.8)
        self.renderer = Renderer()
        self.profile = Profile()
        self.level = "easy"          # computer level: easy, medium, advanced
        self.picking = False         # character pop-up open?

        self.mode = "ai"             # "ai" or "two"
        self.grid = 3                # board size: 3 means 3x3 ... 9 means 9x9
        self.win_len = 3             # marks in a row needed to win
        self.state = "home"          # welcome, home, friend_setup, playing, over
        self.scores = {"X": 0, "O": 0, "D": 0}
        self.starter = "X"
        self.opp_avatar = 1
        self.friend_name = ""
        self.edit_friend_name = ""
        self.friend_avatar = (self.profile.avatar + 1) % avatars.count()
        self.smooth = None           # smoothed fingertip position
        self.active_hand = None

        self.edit_name = self.profile.name
        self.message = ""
        self.message_until = 0

        self.reset()
        self.go_home()
        self.state = "welcome"

    # ================= navigation =================
    def go_home(self):
        self.picking = False
        self.state = "home"
        self.edit_name = self.profile.name
        self.gesture.reset()
        self.gesture.dwell_time = 0.8

    def start_game(self, mode):
        self.profile.name = self.edit_name
        self.profile.save()
        self.mode = mode
        self.scores = {"X": 0, "O": 0, "D": 0}
        self.starter = "X"
        base = self.profile.avatar % avatars.count()
        if mode == "two":
            self.friend_name = self.edit_friend_name.strip()
            self.opp_avatar = self.friend_avatar % avatars.count()
        else:
            self.friend_name = ""
            self.opp_avatar = (base + 3) % len(avatars.CHARACTERS)
        self.board.set_size(self.grid)
        self.win_len = default_win_len(self.grid)
        self.renderer.set_grid(self.grid)
        self.reset()
        self.state = "playing"
        self.gesture.dwell_time = 1.2

    def _start_friend_game(self):
        if not self.edit_friend_name.strip():
            self._notify("Please type your friend's name first")
            return
        self.start_game("two")

    def reset(self):
        """New round (scores are kept)."""
        self.board.reset()
        self.gesture.reset()
        self.turn = self.starter
        self.winner = None
        self.win_line = None
        self.draw = False
        self.ai_time = time.time() + 0.7

    # ================= keyboard (name field) =================
    def _notify(self, msg):
        self.message = msg
        self.message_until = time.time() + 2.5

    def _handle_typing(self, key):
        """Returns True when the user wants to quit (Esc)."""
        if self.picking:             # while the pop-up is open, Esc just closes it
            if key == 27:
                self.picking = False
                self.gesture.reset()
            return False

        if key == 255:               # no key
            return False
        if key == 27:                # esc
            return True
        if key in (8, 127):          # backspace
            self.edit_name = self.edit_name[:-1]
        elif key == 13:              # enter
            if self.edit_name.strip():
                self.profile.name = self.edit_name
                self.profile.save()
                self._notify("Saved!")
            else:
                self._notify("Please type your name first")
        elif 32 <= key <= 126 and len(self.edit_name) < MAX_NAME:
            if key == 32 and not self.edit_name:
                return False
            self.edit_name += chr(key)
        return False

    def _handle_friend_typing(self, key):
        if key == 27:
            self.state = "home"
            self.gesture.reset()
        elif key in (8, 127):
            self.edit_friend_name = self.edit_friend_name[:-1]
        elif key in (10, 13):
            return
        elif 32 <= key <= 126 and len(self.edit_friend_name) < MAX_NAME:
            if key != 32 or self.edit_friend_name:
                self.edit_friend_name += chr(key)

    # ================= computer player (by level) =================
    def _empty_cells(self):
        return [i for i, c in enumerate(self.board.cells) if c not in ("X", "O")]

    def _winning_move(self, mark):
        """A cell where `mark` would win right now, or None."""
        for i in self._empty_cells():
            trial = list(self.board.cells)
            trial[i] = mark
            winner, _ = check_winner(trial, self.win_len)
            if winner == mark:
                return i
        return None

    def _pick_ai_move(self):
        level = self.level
        empty = self._empty_cells()
        if not empty:
            return computer_move(self.board.cells, win_len=self.win_len)

        if level == "easy":                       # random move
            return random.choice(empty)

        if level == "medium":                     # win > block > random
            move = self._winning_move("O")
            if move is None:
                move = self._winning_move("X")
            return move if move is not None else random.choice(empty)

        # advanced: your original smart computer_move
        return computer_move(self.board.cells, win_len=self.win_len)

    # ================= game logic =================
    def _check_end(self):
        self.winner, self.win_line = check_winner(self.board.cells, self.win_len)
        self.draw = is_draw(self.board.cells, self.win_len)
        if not (self.winner or self.draw):
            return
        self.state = "over"
        self.gesture.reset()
        self.gesture.dwell_time = 0.8
        if self.winner:
            self.scores[self.winner] += 1
        else:
            self.scores["D"] += 1
        if self.mode == "ai":
            if self.draw:
                self.profile.record("draw")
            elif self.winner == "X":
                self.profile.record("win")
            else:
                self.profile.record("loss")

    def _names(self):
        me = self.profile.name or "You"
        return {"X": me, "O": "Computer" if self.mode == "ai"
                else self.friend_name or "Player 2"}

    def _header(self):
        names = self._names()
        if self.state == "over":
            if self.draw:
                return "It's a draw!", YELLOW
            if self.mode == "ai":
                return ("You win!", GREEN) if self.winner == "X" else ("Computer wins!", RED)
            return f"{names[self.winner]} wins!", GREEN
        if self.mode == "ai":
            return (("Your turn", WHITE) if self.turn == "X"
                    else ("Computer is thinking...", WHITE))
        return f"{names[self.turn]}'s turn", WHITE

    def _players(self):
        names = self._names()
        left = {"name": names["X"], "mark": "X", "mark_color": X_COLOR,
                "score": self.scores["X"], "avatar": self.profile.avatar}
        right = {"name": names["O"], "mark": "O", "mark_color": O_COLOR,
                 "score": self.scores["O"], "avatar": self.opp_avatar}
        return left, right

    # ================= per-frame update =================
    def update(self, px, py, hand=None):
        """px, py: pointer in pixels or None. Returns the hover target."""
        r = self.renderer
        has = px is not None

        if self.state == "welcome":
            target = r.target_at(r.welcome_targets, px, py) if has else None
            picked = self.gesture.update(target)
            if picked == "continue":
                self.state = "home"
                self.gesture.reset()
            elif picked == "how_to_play":
                self.state = "how_to_play"
                self.gesture.reset()
            elif picked == "exit":
                self.state = "exit"
            return target

        if self.state == "how_to_play":
            target = r.target_at(r.instructions_targets, px, py) if has else None
            picked = self.gesture.update(target)
            if picked == "home":
                self.state = "home"
                self.gesture.reset()
            return target

        if self.state == "friend_setup":
            target = r.target_at(r.friend_setup_targets, px, py) if has else None
            picked = self.gesture.update(target)
            if picked and picked.startswith("friend_avatar:"):
                self.friend_avatar = int(picked.split(":")[1])
            elif picked == "back":
                self.state = "home"
                self.gesture.reset()
            elif picked == "friend_start":
                self._start_friend_game()
            return target

        if self.state == "home":
            targets = r.pick_targets if self.picking else r.home_targets
            target = r.target_at(targets, px, py) if has else None
            picked = self.gesture.update(target)
            if picked:
                if picked.startswith("av:"):
                    self.profile.avatar = int(picked.split(":")[1])
                    self.picking = False
                    self.gesture.reset()
                    self.profile.save()
                elif picked == "profile":
                    self.picking = True
                    self.gesture.reset()
                elif picked == "welcome":
                    self.state = "welcome"
                    self.gesture.reset()
                elif picked == "how_to_play":
                    self.state = "how_to_play"
                    self.gesture.reset()
                elif picked == "close":
                    self.picking = False
                    self.gesture.reset()
                elif picked.startswith("size:"):
                    self.grid = int(picked.split(":")[1])
                elif picked.startswith("level:"):
                    self.level = picked.split(":")[1]
                    self._notify(f"Level: {self.level.title()}")
                elif picked in ("ai", "two"):
                    if self.edit_name.strip():
                        if picked == "two":
                            self.state = "friend_setup"
                            self.gesture.reset()
                        else:
                            self.start_game(picked)
                    else:
                        self._notify("Please type your name first")
            return target

        if self.state == "over":
            target = r.target_at(r.over_targets, px, py) if has else None
            picked = self.gesture.update(target)
            if picked == "again":
                self.starter = "O" if self.starter == "X" else "X"
                self.reset()
                self.state = "playing"
                self.gesture.dwell_time = 1.2
            elif picked == "menu":
                self.go_home()
            return target

        # playing
        btn = r.target_at(r.play_targets, px, py) if has else None
        if btn:                      # finger is on RESTART or HOME
            picked = self.gesture.update(btn)
            if picked == "restart":
                self.reset()
                self.state = "playing"
                self.gesture.dwell_time = 1.2
            elif picked == "menu":
                self.go_home()
            return btn
        target = r.cell_at(px, py) if has else None
        human_turn = self.mode == "two" or self.turn == "X"
        if human_turn:
            if hand != HAND_FOR[self.turn]:
                target = None
            picked = self.gesture.update(target)
            if picked is not None and self.board.place(picked, self.turn):
                self._check_end()
                if self.state == "playing":
                    self.turn = "O" if self.turn == "X" else "X"
                    self.ai_time = time.time() + 0.7
        else:
            self.gesture.update(None)
            if time.time() >= self.ai_time:
                self.board.place(self._pick_ai_move(), "O")
                self._check_end()
                if self.state == "playing":
                    self.turn = "X"
                    self.gesture.reset()
        return target

    def _smooth(self, pointer, a=0.45):
        if pointer is None:
            self.smooth = None
        elif self.smooth is None:
            self.smooth = pointer
        else:
            self.smooth = (a * pointer[0] + (1 - a) * self.smooth[0],
                           a * pointer[1] + (1 - a) * self.smooth[1])
        return self.smooth

    def _winner_info(self):
        """Who to congratulate on the game-over screen (None if no winner)."""
        if self.state != "over" or not self.winner:
            return None
        left, right = self._players()
        side = left if self.winner == "X" else right
        human = self.mode == "two" or self.winner == "X"
        return {"name": side["name"], "avatar": side["avatar"], "human": human}

    def render(self, frame, pointer, hover, progress, hand=None):
        r = self.renderer
        r._hand = hand
        if self.state == "welcome":
            r.draw_welcome(frame, pointer, hover, progress)
        elif self.state == "how_to_play":
            r.draw_instructions(frame, pointer, hover, progress)
        elif self.state == "friend_setup":
            msg = self.message if time.time() < self.message_until else ""
            r.draw_friend_setup(frame, self.edit_friend_name,
                                self.friend_avatar % avatars.count(),
                                pointer, hover, progress, msg)
        elif self.state == "home":
            msg = self.message if time.time() < self.message_until else ""
            r.draw_home(frame, self.edit_name, self.profile.avatar % avatars.count(),
                        self.profile.stats, pointer, hover, progress, msg, self.grid,
                        level=self.level, picking=self.picking, hand=hand)
        else:
            header, hcolor = self._header()
            left, right = self._players()
            r.draw_game(frame, self.board, pointer, hover, progress, header, hcolor,
                        left, right, self.scores["D"], self.turn, self.win_line,
                        over=(self.state == "over"),
                        winner=self._winner_info(), hand=hand)

    # ================= main loop =================
    def run(self):
        camera = Camera()
        if not camera.is_opened():
            print("Cannot open camera")
            return
        tracker = HandTracker()

        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW, W, H)

        while True:
            frame = camera.read()
            if frame is None:
                break
            frame = cv2.resize(frame, (W, H))

            hands = tracker.get_hands(frame)
            human_turn = self.state == "playing" and (
                self.mode == "two" or self.turn == "X")
            required_hand = HAND_FOR[self.turn] if human_turn else None
            selected = next((detection for detection in hands
                             if detection[1] == required_hand), None)
            if selected is None and hands:
                selected = hands[0]
            hand = selected[1] if selected else None
            fingertip = selected[0] if selected else None
            if hand != self.active_hand:
                self.smooth = None
                self.active_hand = hand
            pointer = self._smooth(fingertip)
            px = py = None
            if pointer is not None:
                px, py = int(pointer[0] * W), int(pointer[1] * H)

            hover = self.update(px, py, hand)
            if self.state == "exit":
                break
            self.render(frame, pointer, hover, self.gesture.progress, hand)

            cv2.imshow(WINDOW, frame)
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break

            key = cv2.waitKey(1) & 0xFF
            if self.state == "welcome":
                if key in (10, 13, 32):
                    self.state = "home"
                    self.gesture.reset()
                elif key == 27:
                    break
            elif self.state == "how_to_play":
                if key == 27:
                    self.state = "home"
                    self.gesture.reset()
            elif self.state == "friend_setup":
                self._handle_friend_typing(key)
            elif self.state == "home":
                if self._handle_typing(key):     # letters go to the name field
                    break
            elif key == ord("q"):
                break
            elif key == ord("m"):
                self.go_home()
            elif key == ord("r"):
                self.reset()
                self.state = "playing"
                self.gesture.dwell_time = 1.2

        tracker.close()
        camera.release()
        cv2.destroyAllWindows()