"""Adds the LEVEL row (Easy / Medium / Advanced) to the home page.

Run it ONCE from the project folder (the folder that has main.py):
    python patch_level_ui.py
It edits src/renderer.py and src/game_state.py and keeps backups (*.bak).
Nothing is changed unless every edit can be applied.
"""
import os
import shutil
import sys

RENDERER = os.path.join("src", "renderer.py")
GAME = os.path.join("src", "game_state.py")

LEVEL_BLOCK = '''can_play = bool(name.strip())
        text(frame, "LEVEL", 470, 546, 0.6, MUTED, 1, "left")
        desc = {"easy": "Easy: computer plays random moves",
                "medium": "Medium: computer wins and blocks",
                "advanced": "Advanced: smart computer"}
        if can_play:
            text(frame, desc.get(level, ""), 1190, 546, 0.55, YELLOW, 1, "right")
        else:
            text(frame, "Type your name to unlock play", 1190, 546, 0.55, YELLOW, 1, "right")
        dots = {"easy": GREEN, "medium": YELLOW, "advanced": RED}
        for lvl, rect in self.level_rects.items():
            tgt = f"level:{lvl}"
            self._button(frame, lvl.upper(), "", rect, hover == tgt,
                         progress if hover == tgt else 0, primary=(lvl == level))
            dot = (rect[0] + 24, rect[1] + rect[3] // 2)
            cv2.circle(frame, dot, 7, dots[lvl], -1, AA)
            cv2.circle(frame, dot, 7, WHITE, 1, AA)'''

RENDERER_EDITS = [
    # more room on the right panel: tighter name / avatar area
    ('cols, pitch, row_pitch, x_start, self.av_r = 8, 90, 82, 515, 34',
     'cols, pitch, row_pitch, x_start, self.av_r = 8, 90, 74, 515, 34'),
    ('row_y = 358 if n > cols else 395', 'row_y = 316 if n > cols else 340'),
    ('self.size_rects = {k: (470 + i * 183, 540, 170, 52) for i, k in enumerate(BOARD_SIZES)}',
     'self.size_rects = {k: (470 + i * 183, 476, 170, 46) for i, k in enumerate(BOARD_SIZES)}\n'
     '        # computer level buttons\n'
     '        self.level_rects = {lvl: (470 + i * 246, 558, 228, 44)\n'
     '                            for i, lvl in enumerate(("easy", "medium", "advanced"))}'),
    ('"Challenge the computer", (470, 610, 350, 70), True)',
     '"Challenge the computer", (470, 616, 350, 64), True)'),
    ('"Take turns, 2 players", (840, 610, 350, 70), False)',
     '"Take turns, 2 players", (840, 616, 350, 64), False)'),
    ('+ [(f"size:{k}", ("rect", r)) for k, r in self.size_rects.items()]',
     '+ [(f"size:{k}", ("rect", r)) for k, r in self.size_rects.items()]\n'
     '            + [(f"level:{k}", ("rect", r)) for k, r in self.level_rects.items()]'),
    ('def draw_home(self, frame, name, sel, stats, pointer, hover, progress, message, grid=3, hand=None):',
     'def draw_home(self, frame, name, sel, stats, pointer, hover, progress, message, grid=3, hand=None,\n'
     '                  level="easy"):'),
    # name field + hint + character label (moved up)
    ('text(frame, "YOUR NAME", 470, 160, 0.6, MUTED, 1, "left")',
     'text(frame, "YOUR NAME", 470, 154, 0.6, MUTED, 1, "left")'),
    ('panel(frame, 470, 175, 720, 64, CARD, 0.92, 16, (255, 170, 90), 2)',
     'panel(frame, 470, 166, 720, 56, CARD, 0.92, 16, (255, 170, 90), 2)'),
    ('text(frame, name, 495, 207, 1.3, WHITE, 2, "left")',
     'text(frame, name, 495, 194, 1.3, WHITE, 2, "left")'),
    ('"Type your name...", 495, 207, 1.1, MUTED, 1, "left")',
     '"Type your name...", 495, 194, 1.1, MUTED, 1, "left")'),
    ('cv2.line(frame, (cx, 190), (cx, 224), YELLOW, 3, AA)',
     'cv2.line(frame, (cx, 178), (cx, 210), YELLOW, 3, AA)'),
    ('text(frame, message, 470, 262, 0.62, RED, 2, "left")',
     'text(frame, message, 470, 242, 0.62, RED, 2, "left")'),
    ('470, 262, 0.55, MUTED, 1, "left")', '470, 242, 0.55, MUTED, 1, "left")'),
    ('text(frame, "CHOOSE YOUR CHARACTER", 470, 300, 0.6, MUTED, 1, "left")',
     'text(frame, "CHOOSE YOUR CHARACTER", 470, 264, 0.6, MUTED, 1, "left")'),
    # board size row
    ('text(frame, "BOARD SIZE", 470, 521, 0.6, MUTED, 1, "left")',
     'text(frame, "BOARD SIZE", 470, 462, 0.6, MUTED, 1, "left")'),
    ('1190, 521, 0.6, YELLOW, 1, "right")', '1190, 462, 0.6, YELLOW, 1, "right")'),
    # old unlock message position -> removed (it now lives on the LEVEL row)
    ('text(frame, "Type your name to unlock play", 830, 592, 0.5, YELLOW, 1)', 'pass'),
    # the new LEVEL row
    ('can_play = bool(name.strip())', LEVEL_BLOCK),
]

GAME_EDITS = [
    ('from src.difficulty import LevelSelector\n', ''),
    ('self.levels = LevelSelector(W, H)   # Easy / Medium / Advanced buttons',
     'self.level = "easy"          # computer level: easy, medium, advanced'),
    ('level = self.levels.selected', 'level = self.level'),
    ('            chosen = self.levels.update(px, py)\n'
     '            if chosen:\n'
     '                self._notify(f"Level: {chosen.title()}")\n', ''),
    ('self.grid = int(picked.split(":")[1])',
     'self.grid = int(picked.split(":")[1])\n'
     '                elif picked.startswith("level:"):\n'
     '                    self.level = picked.split(":")[1]\n'
     '                    self._notify(f"Level: {self.level.title()}")'),
    ('progress, msg, self.grid)', 'progress, msg, self.grid,\n'
     '                        level=self.level)'),
    ('            if pointer is not None:\n'
     '                self.levels.draw(frame, pointer[0] * W, pointer[1] * H)\n'
     '            else:\n'
     '                self.levels.draw(frame)\n', ''),
]


def transform(path, edits, done_marker):
    with open(path, encoding="utf-8") as f:
        s = f.read()
    if done_marker in s:
        print(f"{path}: already patched, skipping")
        return s, False
    for old, new in edits:
        n = s.count(old)
        if n != 1:
            print(f"ERROR in {path}: expected 1 match but found {n} for:\n    {old.strip()[:80]}")
            return None, False
        s = s.replace(old, new)
    return s, True


def main():
    for p in (RENDERER, GAME):
        if not os.path.exists(p):
            print(f"Cannot find {p}. Run this from the folder that contains main.py")
            sys.exit(1)
    r_new, r_changed = transform(RENDERER, RENDERER_EDITS, "level_rects")
    g_new, g_changed = transform(GAME, GAME_EDITS, "self.level =")
    if r_new is None or g_new is None:
        print("\nNothing was changed. Please send me this message.")
        sys.exit(1)
    for path, new, changed in ((RENDERER, r_new, r_changed), (GAME, g_new, g_changed)):
        if changed:
            shutil.copy(path, path + ".bak")
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            print(f"Patched {path} (backup: {path}.bak)")
    print("\nDone! Now run:  python main.py")


if __name__ == "__main__":
    main()