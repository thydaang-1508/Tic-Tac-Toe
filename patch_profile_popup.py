"""Moves the character list into a pop-up.

On the home page you now see only YOUR profile picture. Point at it (or click it)
and a pop-up opens where you pick another character. The freed space is used to
give BOARD SIZE, LEVEL and the PLAY buttons more room.

Run it ONCE from the project folder (the folder that has main.py):
    python patch_profile_popup.py
(You must have already run patch_level_ui.py before.)
Backups are saved as *.bak2. Nothing changes unless every edit can be applied.
"""
import os
import re
import shutil
import sys

RENDERER = os.path.join("src", "renderer.py")
GAME = os.path.join("src", "game_state.py")

PICK_LAYOUT = '''# ----- character picker pop-up (opens when you click your profile) -----
        cnt = avatars.count()
        if cnt <= 16:
            pcols, ppitch, prow, self.pick_r = 8, 100, 96, 38
        else:
            pcols, ppitch, prow, self.pick_r = 12, 66, 82, 28
        prows = (cnt + pcols - 1) // pcols
        pw, ph = pcols * ppitch + 60, prows * prow + 220
        ppx, ppy = (W - pw) // 2, (H - ph) // 2
        self.pick_panel = (ppx, ppy, pw, ph)
        self.pick_pos = [(ppx + 30 + ppitch // 2 + (i % pcols) * ppitch,
                          ppy + 140 + (i // pcols) * prow) for i in range(cnt)]
        self.pick_close = (W // 2 - 130, ppy + ph - 78, 260, 52)
        self.pick_targets = (
            [(f"av:{i}", ("circle", (x, y, self.pick_r + 10))) for i, (x, y) in enumerate(self.pick_pos)]
            + [("close", ("rect", self.pick_close))]
        )

        # ----- game-over layout -----'''

PICK_METHOD = '''def _draw_picker(self, frame, sel, hover, progress):
        """Pop-up with all characters: point at one and hold to choose it."""
        dim = frame.copy()
        cv2.rectangle(dim, (0, 0), (W, H), (10, 6, 8), -1)
        cv2.addWeighted(dim, 0.62, frame, 0.38, 0, frame)
        ppx, ppy, pw, ph = self.pick_panel
        panel(frame, ppx, ppy, pw, ph, CARD, 0.96, 30, NEON, 3, shadow=True)
        text(frame, "CHOOSE YOUR CHARACTER", W // 2, ppy + 48, 0.95, WHITE, 2, shadow=True)
        text(frame, "point at a character and hold to select", W // 2, ppy + 82, 0.5, MUTED, 1)
        r0 = self.pick_r
        for i, (x, y) in enumerate(self.pick_pos):
            r = r0
            if hover == f"av:{i}":
                r = r0 + 4
                cv2.circle(frame, (x, y), r0 + 12, YELLOW, 2, AA)
            avatar(frame, x, y, r, i, WHITE, 2)
            if i == sel:
                cv2.circle(frame, (x, y), r0 + 10, WHITE, 4, AA)
        if isinstance(hover, str) and hover.startswith("av:"):
            i = int(hover.split(":")[1])
            x, y = self.pick_pos[i]
            text(frame, avatars.name(i), x, y + r0 + 22, 0.5, WHITE, 1, shadow=True)
        self._button(frame, "CLOSE", "", self.pick_close, hover == "close",
                     progress if hover == "close" else 0)

    # ======================= HOME ======================='''

# (old, new) = exact text swap, must match exactly once
RENDERER_EDITS = [
    ('[(f"av:{i}", ("circle", (x, y, self.av_r + 10))) for i, (x, y) in enumerate(self.avatar_pos)]',
     '[("profile", ("circle", (235, 305, 104)))]'),
    ('self.size_rects = {k: (470 + i * 183, 476, 170, 46) for i, k in enumerate(BOARD_SIZES)}',
     'self.size_rects = {k: (470 + i * 183, 318, 170, 56) for i, k in enumerate(BOARD_SIZES)}'),
    ('self.level_rects = {lvl: (470 + i * 246, 558, 228, 44)',
     'self.level_rects = {lvl: (470 + i * 246, 438, 228, 56)'),
    ('"Challenge the computer", (470, 616, 350, 64), True)',
     '"Challenge the computer", (470, 556, 350, 76), True)'),
    ('"Take turns, 2 players", (840, 616, 350, 64), False)',
     '"Take turns, 2 players", (840, 556, 350, 76), False)'),
    ('# ----- game-over layout -----', PICK_LAYOUT),
    ('level="easy"):', 'level="easy", picking=False):'),
    ('text(frame, "YOUR PLAYER", 235, 160, 0.6, MUTED, 1)',
     'text(frame, "YOUR PLAYER", 235, 160, 0.6, MUTED, 1)\n'
     '        text(frame, "point at the picture to change", 235, 182, 0.45, MUTED, 1)'),
    ('avatar(frame, 235, 305 + bob, 94, sel, WHITE, 5)',
     'avatar(frame, 235, 305 + bob, 94, sel, WHITE, 5)\n'
     '        if hover == "profile":\n'
     '            cv2.circle(frame, (235, 305 + bob), 114, YELLOW, 3, AA)\n'
     '        cv2.circle(frame, (312, 380 + bob), 21, ACCENT, -1, AA)\n'
     '        cv2.circle(frame, (312, 380 + bob), 21, WHITE, 2, AA)\n'
     '        self._icon(frame, "restart", 312, 380 + bob, 9, WHITE)'),
    ('text(frame, "BOARD SIZE", 470, 462, 0.6, MUTED, 1, "left")',
     'text(frame, "BOARD SIZE", 470, 300, 0.6, MUTED, 1, "left")'),
    ('1190, 462, 0.6, YELLOW, 1, "right")', '1190, 300, 0.6, YELLOW, 1, "right")'),
    ('text(frame, "LEVEL", 470, 546, 0.6, MUTED, 1, "left")',
     'text(frame, "LEVEL", 470, 420, 0.6, MUTED, 1, "left")'),
    ('text(frame, desc.get(level, ""), 1190, 546, 0.55, YELLOW, 1, "right")',
     'text(frame, desc.get(level, ""), 1190, 420, 0.55, YELLOW, 1, "right")'),
    ('text(frame, "Type your name to unlock play", 1190, 546, 0.55, YELLOW, 1, "right")',
     'text(frame, "Type your name to unlock play", 1190, 420, 0.55, YELLOW, 1, "right")'),
    ('W // 2, H - 14, 0.55, MUTED, 1)',
     'W // 2, H - 14, 0.55, MUTED, 1)\n'
     '        if picking:\n'
     '            self._draw_picker(frame, sel, hover, progress)'),
    ('# ======================= HOME =======================', PICK_METHOD),
]

# (regex, replacement) - whitespace tolerant removals, must match exactly once
RENDERER_REGEX = [
    (r'[ \t]*ar = self\.av_r\n.*?text\(frame, avatars\.name\(i\), x, y \+ ar \+ 20, 0\.5, WHITE, 1, shadow=True\)\n', ''),
    (r'[ \t]*text\(frame, "CHOOSE YOUR CHARACTER", 470, 264, 0\.6, MUTED, 1, "left"\)\n', ''),
]

GAME_EDITS = [
    ('# computer level: easy, medium, advanced',
     '# computer level: easy, medium, advanced\n'
     '        self.picking = False         # character pop-up open?'),
    ('def go_home(self):', 'def go_home(self):\n        self.picking = False'),
    ('"""Returns True when the user wants to quit (Esc)."""',
     '"""Returns True when the user wants to quit (Esc)."""\n'
     '        if self.picking:             # while the pop-up is open, Esc just closes it\n'
     '            if key == 27:\n'
     '                self.picking = False\n'
     '                self.gesture.reset()\n'
     '            return False'),
    ('target = r.target_at(r.home_targets, px, py) if has else None',
     'targets = r.pick_targets if self.picking else r.home_targets\n'
     '            target = r.target_at(targets, px, py) if has else None'),
    ('self.profile.avatar = int(picked.split(":")[1])',
     'self.profile.avatar = int(picked.split(":")[1])\n'
     '                    self.picking = False\n'
     '                    self.gesture.reset()'),
    ('elif picked.startswith("size:"):',
     'elif picked == "profile":\n'
     '                    self.picking = True\n'
     '                    self.gesture.reset()\n'
     '                elif picked == "close":\n'
     '                    self.picking = False\n'
     '                    self.gesture.reset()\n'
     '                elif picked.startswith("size:"):'),
    ('level=self.level)', 'level=self.level, picking=self.picking)'),
]


def transform(path, edits, regexes, done_marker, needs_marker):
    with open(path, encoding="utf-8") as f:
        s = f.read()
    if done_marker in s:
        print(f"{path}: already patched, skipping")
        return s, False
    if needs_marker not in s:
        print(f"ERROR: {path} does not have the level buttons yet. Run patch_level_ui.py first.")
        return None, False
    for old, new in edits:
        n = s.count(old)
        if n != 1:
            print(f"ERROR in {path}: expected 1 match but found {n} for:\n    {old.strip()[:80]}")
            return None, False
        s = s.replace(old, new)
    for pat, new in regexes:
        found = re.findall(pat, s, flags=re.S)
        if len(found) != 1:
            print(f"ERROR in {path}: expected 1 block but found {len(found)} for:\n    {pat[:70]}")
            return None, False
        s = re.sub(pat, lambda m: new, s, flags=re.S)
    return s, True


def main():
    for p in (RENDERER, GAME):
        if not os.path.exists(p):
            print(f"Cannot find {p}. Run this from the folder that contains main.py")
            sys.exit(1)
    r_new, r_changed = transform(RENDERER, RENDERER_EDITS, RENDERER_REGEX, "pick_targets", "level_rects")
    g_new, g_changed = transform(GAME, GAME_EDITS, [], "self.picking", "self.level =")
    if r_new is None or g_new is None:
        print("\nNothing was changed. Please send me this message.")
        sys.exit(1)
    for path, new, changed in ((RENDERER, r_new, r_changed), (GAME, g_new, g_changed)):
        if changed:
            shutil.copy(path, path + ".bak2")
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
            print(f"Patched {path} (backup: {path}.bak2)")
    print("\nDone! Now run:  python main.py")


if __name__ == "__main__":
    main()