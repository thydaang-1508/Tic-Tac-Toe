import math
import random
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

from src import avatars
from src.game_rules import default_win_len

W, H = 1280, 720
FONT = cv2.FONT_HERSHEY_DUPLEX
AA = cv2.LINE_AA

# ---------- palette (BGR) ----------
WHITE = (255, 255, 255)
MUTED = (205, 195, 190)
CARD = (72, 52, 46)
CARD_LIGHT = (100, 76, 68)
BORDER = (135, 112, 104)
ACCENT = (255, 140, 50)
GREEN = (120, 220, 110)
RED = (100, 100, 250)
YELLOW = (60, 210, 255)
X_COLOR = (110, 110, 255)
O_COLOR = (255, 190, 80)
PETAL_COLORS = [(190, 140, 255), (160, 110, 245), (210, 170, 255), (130, 190, 255)]

TILE = 180
CONGRATS_DELAY = 2.5      # seconds to show the winning line before the congratulation card
BOARD_SIZES = (3, 9, 12)
MARK_POP_TIME = 0.65      # seconds for the mark "pop-in" animation
WIN_LINE_TIME = 1.3      # seconds for the winning line to draw itself

ANIM_SPEED = 0.40         # 1.0 = original speed; lower = slower, calmer animations
THEME = "logic"           # "logic" = blueprint X/O logic board, "tulip" = tulip field
NEON = (230, 205, 90)     # cyan-ish accent (BGR)
GRID_MINOR = (58, 40, 30)
GRID_MAJOR = (84, 60, 44)
HAND_FOR = {"X": "Right", "O": "Left"}   # right hand plays X, left hand plays O


# ======================= background =======================
HORIZON = 330
CLOUD_H = 300
TULIP_BANDS = [((70, 70, 230), (100, 90, 245)), ((185, 140, 255), (205, 170, 255)),
               ((80, 215, 250), (120, 230, 255)), ((60, 150, 250), (90, 175, 255)),
               ((210, 110, 180), (230, 140, 200)), ((240, 240, 250), (215, 225, 245))]


def _tulip(img, x, y, s, col):
    """One little anime-style tulip with its base at (x, y); s = size in pixels."""
    x, y = int(x), int(y)
    if s < 5:
        cv2.circle(img, (x, int(y - s)), max(1, int(s * 0.55)), col, -1, AA)
        return
    stem, leaf = (55, 140, 70), (45, 120, 60)
    cv2.line(img, (x, y), (x, int(y - s * 0.7)), stem, max(1, int(s * 0.12)), AA)
    for sx, ang in ((-1, -35), (1, 35)):
        cv2.ellipse(img, (int(x + sx * s * 0.28), int(y - s * 0.15)),
                    (int(s * 0.3), max(1, int(s * 0.1))), ang, 0, 360, leaf, -1, AA)
    cx, cy = x, int(y - s)
    ax, ay = int(s * 0.42), int(s * 0.55)
    cv2.ellipse(img, (cx, cy), (ax, ay), 0, 0, 360, col, -1, AA)
    crown = np.array([(cx - .42 * s, cy - .10 * s), (cx - .38 * s, cy - .85 * s),
                      (cx - .14 * s, cy - .45 * s), (cx, cy - .95 * s),
                      (cx + .14 * s, cy - .45 * s), (cx + .38 * s, cy - .85 * s),
                      (cx + .42 * s, cy - .10 * s)], np.int32)
    cv2.fillPoly(img, [crown], col, AA)
    hl = tuple(min(255, c + 45) for c in col)
    cv2.ellipse(img, (int(cx - s * 0.12), cy), (max(1, int(s * 0.1)), int(s * 0.35)),
                0, 0, 360, hl, -1, AA)
    shade = tuple(int(c * 0.7) for c in col)
    cv2.ellipse(img, (cx, cy), (ax, ay), 0, 20, 160, shade, max(1, int(s * 0.05)), AA)


def _make_scene():
    """Pre-rendered tulip-field landscape: dusk sky, sun, hills, rows of tulips."""
    rng = random.Random(7)
    ys = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    sky_top = np.array((170, 92, 112), np.float32)
    sky_hor = np.array((178, 205, 255), np.float32)
    k = np.clip(ys / (HORIZON / H), 0, 1) ** 0.8
    rows = sky_top * (1 - k) + sky_hor * k
    img = np.empty((H, W, 3), np.float32)
    img[:] = rows[:, None, :]
    yy, xx = np.ogrid[:H, :W]
    d = np.sqrt((xx - 960) ** 2 + (yy - 285) ** 2)
    img += (np.clip(1 - d / 380, 0, 1) ** 2)[:, :, None] * np.array((70, 120, 150), np.float32)
    img = np.clip(img, 0, 255).astype(np.uint8)
    cv2.circle(img, (960, 285), 46, (205, 238, 255), -1, AA)

    xs = np.arange(W)
    for base, amp, f, ph, col in ((HORIZON - 70, 34, 0.0042, 0.8, (170, 125, 160)),
                                  (HORIZON - 30, 26, 0.0065, 2.1, (150, 105, 135)),
                                  (HORIZON - 6, 14, 0.011, 4.0, (95, 120, 100))):
        ysurf = base + amp * np.sin(xs * f + ph) + amp * 0.4 * np.sin(xs * f * 2.3 + ph * 1.7)
        pts = np.stack([xs, ysurf], 1).astype(np.int32)
        poly = np.vstack([pts, [[W - 1, HORIZON + 40], [0, HORIZON + 40]]])
        cv2.fillPoly(img, [poly], col, AA)

    gt = np.linspace(0, 1, H - HORIZON, dtype=np.float32)[:, None, None]
    ground = np.array((85, 140, 110), np.float32) * (1 - gt) + np.array((45, 100, 60), np.float32) * gt
    img[HORIZON:] = np.broadcast_to(ground, (H - HORIZON, W, 3)).astype(np.uint8)

    R = 26
    for r in range(R):
        t = (r + 1) / R
        y = int(HORIZON + (H - HORIZON - 10) * t ** 1.6)
        s = 2.5 + 30 * t ** 1.5
        band = TULIP_BANDS[(r // 3) % len(TULIP_BANDS)]
        cv2.rectangle(img, (0, y), (W, y + max(2, int(s * 0.45))), (35, 80, 45), -1)
        step = max(4.0, s * 0.95)
        x = -rng.uniform(0, step)
        while x < W + step:
            if rng.random() > 0.12:
                col = band[rng.randint(0, 1)]
            else:
                col = rng.choice(TULIP_BANDS)[0]
            _tulip(img, x + rng.uniform(-1, 1) * step * 0.2, y, s * rng.uniform(0.85, 1.1), col)
            x += step
    img[HORIZON:] = cv2.GaussianBlur(img[HORIZON:], (3, 3), 0)

    out = img.astype(np.float32)
    hz = np.arange(90, dtype=np.float32)
    a = ((1 - hz / 90) * 0.5)[:, None, None]
    out[HORIZON:HORIZON + 90] = out[HORIZON:HORIZON + 90] * (1 - a) + np.array((190, 200, 245), np.float32) * a
    out *= 0.78                                     # darken so the UI stays readable
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    out *= np.clip(1.15 - 0.45 * d, 0.55, 1.0)[:, :, None]
    return np.clip(out, 0, 255).astype(np.uint8)


def _make_clouds():
    """Soft, horizontally tileable cloud strip -> (add, inv) layers."""
    rng = random.Random(3)
    m = np.zeros((CLOUD_H, W), np.uint8)
    for _ in range(9):
        cx, cy, sc = rng.randint(0, W), rng.randint(60, CLOUD_H - 60), rng.uniform(0.7, 1.4)
        puffs = [(rng.randint(-70, 70), rng.randint(-14, 14), rng.randint(34, 60)) for _ in range(5)]
        for off in (-W, 0, W):
            for dx, dy, r in puffs:
                cv2.ellipse(m, (cx + off + int(dx * sc), cy + dy),
                            (int(r * sc * 1.6), int(r * sc * 0.7)), 0, 0, 360, 255, -1, AA)
    m = cv2.GaussianBlur(m, (0, 0), 14)
    m = (m.astype(np.float32) * 0.42).astype(np.uint8)
    m = np.hstack([m, m])
    tint = np.array((235, 220, 255), np.float32)
    add = (m[:, :, None].astype(np.float32) / 255 * tint).astype(np.uint8)
    inv = np.repeat((255 - m)[:, :, None], 3, 2)
    return add, inv


def _mini_board(img, x, y, size, marks):
    """Tiny 3x3 board with X/O marks - used as decoration of the logic background."""
    c = size / 3.0
    line = (120, 95, 60)
    cv2.rectangle(img, (int(x), int(y)), (int(x + size), int(y + size)), (80, 60, 42), 1, AA)
    for k in (1, 2):
        cv2.line(img, (int(x + k * c), int(y + 3)), (int(x + k * c), int(y + size - 3)), line, 1, AA)
        cv2.line(img, (int(x + 3), int(y + k * c)), (int(x + size - 3), int(y + k * c)), line, 1, AA)
    for i, m in enumerate(marks):
        cx, cy, r = int(x + (i % 3 + 0.5) * c), int(y + (i // 3 + 0.5) * c), max(2, int(c * 0.26))
        if m == "X":
            cv2.line(img, (cx - r, cy - r), (cx + r, cy + r), (100, 100, 215), 2, AA)
            cv2.line(img, (cx - r, cy + r), (cx + r, cy - r), (100, 100, 215), 2, AA)
        elif m == "O":
            cv2.circle(img, (cx, cy), r, (215, 165, 80), 2, AA)


def _make_logic_scene():
    """Blueprint / graph-paper board with game-tree diagrams of X and O positions."""
    rng = random.Random(11)
    yy, xx = np.ogrid[:H, :W]
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    base, mid = np.array((40, 22, 14), np.float32), np.array((92, 54, 34), np.float32)
    k = np.clip(1 - d, 0, 1)[:, :, None] ** 1.2
    img = (base * (1 - k) + mid * k).astype(np.uint8)
    for x in range(0, W, 32):
        cv2.line(img, (x, 0), (x, H), GRID_MAJOR if x % 160 == 0 else GRID_MINOR, 1)
    for y in range(0, H, 32):
        cv2.line(img, (0, y), (W, y), GRID_MAJOR if y % 160 == 0 else GRID_MINOR, 1)
    for _ in range(60):                                   # nodes on the grid crossings
        cv2.circle(img, (rng.randrange(0, W, 32), rng.randrange(0, H, 32)), 2, (140, 110, 64), -1, AA)
    for _ in range(10):                                   # big outlined X / O watermarks
        cx, cy, r = rng.randint(40, W - 40), rng.randint(40, H - 40), rng.randint(26, 52)
        if rng.random() < 0.5:
            cv2.line(img, (cx - r, cy - r), (cx + r, cy + r), (100, 74, 54), 3, AA)
            cv2.line(img, (cx - r, cy + r), (cx + r, cy - r), (100, 74, 54), 3, AA)
        else:
            cv2.circle(img, (cx, cy), r, (100, 74, 54), 3, AA)
    for cx in (10, W - 24):                               # binary columns on the edges
        for r in range(14, H - 10, 20):
            cv2.putText(img, rng.choice("01"), (cx, r), FONT, 0.4, (96, 70, 50), 1, AA)

    def add(marks, mark):
        m = list(marks)
        m[rng.choice([i for i, c in enumerate(m) if c == "."])] = mark
        return m

    def tree(tx, ty):                                     # root -> 3 moves -> 6 replies
        root = ["."] * 9
        for mk in "XO":
            root = add(root, mk)
        rcx = tx + 121
        nodes = []
        for i in range(3):
            ccx = tx + 21 + i * 100
            child = add(root, "X")
            cv2.line(img, (rcx, ty + 50), (ccx, ty + 88), (130, 108, 56), 1, AA)
            cv2.circle(img, (ccx, ty + 88), 3, NEON, -1, AA)
            for j in (-1, 1):
                gcx = ccx + j * 26
                cv2.line(img, (ccx, ty + 130), (gcx, ty + 166), (130, 108, 56), 1, AA)
                cv2.circle(img, (gcx, ty + 166), 3, NEON, -1, AA)
                nodes.append((gcx - 15, ty + 166, 30, add(child, "O")))
            nodes.append((ccx - 21, ty + 88, 42, child))
        nodes.append((rcx - 25, ty, 50, root))
        for x, y, sz, mk in nodes:
            _mini_board(img, x, y, sz, mk)

    for tx, ty in ((30, 14), (905, 14), (24, 470), (505, 500), (930, 470)):
        tree(tx, ty)

    out = img.astype(np.float32) * np.clip(1.10 - 0.50 * d, 0.5, 1.0)[:, :, None]
    return np.clip(out, 0, 255).astype(np.uint8)


def _make_pattern():
    """(kept for compatibility) tileable X / O symbols layer."""
    pat = np.zeros((H + TILE, W + TILE, 3), np.uint8)
    for gy in range(0, H + TILE, TILE):
        for gx in range(0, W + TILE, TILE):
            xc, yc = gx + 45, gy + 45
            cv2.line(pat, (xc - 16, yc - 16), (xc + 16, yc + 16), X_COLOR, 5, AA)
            cv2.line(pat, (xc - 16, yc + 16), (xc + 16, yc - 16), X_COLOR, 5, AA)
            cv2.circle(pat, (gx + 135, gy + 135), 18, O_COLOR, 5, AA)
    return pat


# ======================= drawing helpers =======================
def _ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def _lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rounded_rect(img, p1, p2, color, radius, thickness=-1):
    x1, y1 = p1
    x2, y2 = p2
    r = max(1, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    if thickness < 0:
        cv2.rectangle(img, (x1 + r, y1), (x2 - r, y2), color, -1)
        cv2.rectangle(img, (x1, y1 + r), (x2, y2 - r), color, -1)
        for cx, cy in ((x1 + r, y1 + r), (x2 - r, y1 + r),
                       (x1 + r, y2 - r), (x2 - r, y2 - r)):
            cv2.circle(img, (cx, cy), r, color, -1, AA)
    else:
        cv2.line(img, (x1 + r, y1), (x2 - r, y1), color, thickness, AA)
        cv2.line(img, (x1 + r, y2), (x2 - r, y2), color, thickness, AA)
        cv2.line(img, (x1, y1 + r), (x1, y2 - r), color, thickness, AA)
        cv2.line(img, (x2, y1 + r), (x2, y2 - r), color, thickness, AA)
        cv2.ellipse(img, (x1 + r, y1 + r), (r, r), 180, 0, 90, color, thickness, AA)
        cv2.ellipse(img, (x2 - r, y1 + r), (r, r), 270, 0, 90, color, thickness, AA)
        cv2.ellipse(img, (x2 - r, y2 - r), (r, r), 0, 0, 90, color, thickness, AA)
        cv2.ellipse(img, (x1 + r, y2 - r), (r, r), 90, 0, 90, color, thickness, AA)


def panel(img, x, y, w, h, color, alpha=0.85, radius=20, border=None, border_t=2,
          shadow=False):
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + w, W), min(y + h, H)
    if x2 <= x1 or y2 <= y1:
        return
    if shadow:   # soft drop shadow: two offset dark layers
        for off, a in ((9, 0.16), (5, 0.20)):
            panel(img, x + 2, y + off, w - 4, h, (10, 6, 8), a, radius)
    roi = img[y1:y2, x1:x2]
    overlay = roi.copy()
    rounded_rect(overlay, (x - x1, y - y1), (x - x1 + w, y - y1 + h), color, radius)
    cv2.addWeighted(overlay, alpha, roi, 1 - alpha, 0, roi)
    if border is not None:
        rounded_rect(img, (x, y), (x + w, y + h), border, radius, border_t)


def text(img, s, x, y, scale=1.0, color=WHITE, thick=2, align="center", shadow=False):
    (tw, th), _ = cv2.getTextSize(s, FONT, scale, thick)
    if align == "center":
        x -= tw // 2
    elif align == "right":
        x -= tw
    pos = (int(x), int(y + th // 2))
    if shadow:
        cv2.putText(img, s, (pos[0] + 2, pos[1] + 3), FONT, scale, (20, 12, 16), thick + 1, AA)
    cv2.putText(img, s, pos, FONT, scale, color, thick, AA)


def _fit(label, max_w, scale, thick):
    while scale > 0.4 and cv2.getTextSize(label, FONT, scale, thick)[0][0] > max_w:
        scale -= 0.05
    return scale


def draw_mark(img, mark, cx, cy, r, thick):
    if mark == "X":
        cv2.line(img, (cx - r, cy - r), (cx + r, cy + r), X_COLOR, thick, AA)
        cv2.line(img, (cx - r, cy + r), (cx + r, cy - r), X_COLOR, thick, AA)
    elif mark == "O":
        cv2.circle(img, (cx, cy), r, O_COLOR, thick, AA)


def avatar(img, cx, cy, r, idx, ring=WHITE, ring_t=None):
    avatars.draw(img, cx, cy, r, idx)
    cv2.circle(img, (cx, cy), r, ring, ring_t or max(2, r // 14), AA)


# ======================= renderer =======================
class Renderer:
    def __init__(self):
        avatars.init()

        welcome_path = Path(__file__).resolve().parent.parent / "assets" / "images" / "welcome page.jpg"
        welcome_image = cv2.imread(str(welcome_path))
        if welcome_image is None:
            raise FileNotFoundError(f"Could not load welcome image: {welcome_path}")
        ih, iw = welcome_image.shape[:2]
        scale = max(W / iw, H / ih)
        resized = cv2.resize(welcome_image, (int(iw * scale), int(ih * scale)),
                             interpolation=cv2.INTER_AREA)
        x0 = (resized.shape[1] - W) // 2
        y0 = (resized.shape[0] - H) // 2
        self.welcome_background = resized[y0:y0 + H, x0:x0 + W].copy()
        self.welcome_buttons = [
            ("continue", "LET'S GO", (250, 565, 230, 78), True),
            ("how_to_play", "HOW TO PLAY", (525, 565, 230, 78), False),
            ("exit", "EXIT", (800, 565, 230, 78), False),
        ]
        self.welcome_targets = [(name, ("rect", rect))
                                for name, _, rect, _ in self.welcome_buttons]
        avatar_count = avatars.count()
        avatar_cols = 6
        avatar_pitch = 82
        avatar_x = 700
        avatar_y = 310
        self.friend_avatar_pos = [
            (avatar_x + (i % avatar_cols) * avatar_pitch,
             avatar_y + (i // avatar_cols) * 70)
            for i in range(avatar_count)
        ]
        self.friend_setup_buttons = [
            ("back", "BACK", (135, 590, 190, 58), False),
            ("friend_start", "LET'S GO", (900, 590, 245, 64), True),
        ]
        self.friend_setup_targets = (
            [(f"friend_avatar:{i}", ("circle", (x, y, 34)))
             for i, (x, y) in enumerate(self.friend_avatar_pos)]
            + [(name, ("rect", rect))
               for name, _, rect, _ in self.friend_setup_buttons]
        )

        self.y0 = 150
        self.set_grid(3)

        # animation / effect state
        self._over_since = None
        self._confetti = []
        self._last_t = time.time()
        self._dt = 0.016
        self._at = 0.0             # slow animation clock (real time * ANIM_SPEED)
        self._hand = None          # 'Left' / 'Right' hand currently tracked
        self._trail = deque(maxlen=12)
        self._placed = {}          # cell index -> time the mark appeared
        self._last_move = None
        self._win_since = None
        self._petals = [self._new_petal(True) for _ in range(22)]

        self.grad = _make_logic_scene() if THEME == "logic" else _make_scene()
        self.cloud_add, self.cloud_inv = _make_clouds()
        self._glyphs = [self._new_glyph(True) for _ in range(18)]
        self.pattern = _make_pattern()
        self._btn_cache = {}
        self._sparks = [{"x": random.uniform(0, W), "y": random.uniform(40, H - 40),
                         "ph": random.uniform(0, 6.28), "sp": random.uniform(1.0, 2.6)}
                        for _ in range(34)]

        # ----- home layout -----
        n = avatars.count()
        if n <= 16:      # up to 16 characters: 8 per row, big circles
            cols, pitch, row_pitch, x_start, self.av_r = 8, 90, 74, 515, 34
        else:            # 17 - 24 characters: 12 per row, smaller circles
            cols, pitch, row_pitch, x_start, self.av_r = 12, 60, 70, 500, 26
        row_y = 316 if n > cols else 340
        self.avatar_pos = [(x_start + (i % cols) * pitch, row_y + (i // cols) * row_pitch)
                           for i in range(n)]
        # board-size buttons: 3x3, 9x9, 12x12
        self.size_rects = {k: (470 + i * 246, 318, 220, 56) for i, k in enumerate(BOARD_SIZES)}
        # computer level buttons
        self.level_rects = {lvl: (470 + i * 246, 438, 228, 56)
                            for i, lvl in enumerate(("easy", "medium", "advanced"))}
        # (name, label, sublabel, rect, primary)
        self.home_buttons = [
            ("ai", "PLAY vs COMPUTER", "Challenge the computer", (470, 556, 350, 76), True),
            ("two", "PLAY WITH A FRIEND", "Take turns, 2 players", (840, 556, 350, 76), False),
        ]
        self.home_targets = (
            [("profile", ("circle", (235, 305, 104))),
             ("welcome", ("rect", (60, 20, 180, 44)))]
            + [(f"size:{k}", ("rect", r)) for k, r in self.size_rects.items()]
            + [(f"level:{k}", ("rect", r)) for k, r in self.level_rects.items()]
            + [(b[0], ("rect", b[3])) for b in self.home_buttons]
        )
        self.instructions_targets = [("home", ("rect", (510, 590, 260, 64)))]

        # ----- character picker pop-up (opens when you click your profile) -----
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

        # ----- game-over layout -----
        self.over_buttons = [
            ("again", "PLAY AGAIN", (950, 560, 280, 56), True),
            ("menu", "HOME", (950, 624, 280, 56), False),
        ]
        self.over_targets = [(n_, ("rect", r)) for n_, _, r, _ in self.over_buttons]

        # ----- in-game buttons (visible while playing) -----
        # hover names: "restart" and "menu"; main.py must hit-test self.play_targets
        self.play_buttons = [
            ("restart", "RESTART", (50, 560, 280, 56), True),
            ("menu", "HOME", (50, 624, 280, 56), False),
        ]
        self.play_targets = [(n_, ("rect", r)) for n_, _, r, _ in self.play_buttons]
        self._icons = {"ai": "cpu", "two": "friend", "again": "restart",
                       "restart": "restart", "menu": "home"}

    def set_grid(self, n):
        """Board is n x n. Cells shrink so the board keeps its size."""
        self.n = n
        self.cell = 520 // n
        self.size = self.cell * n
        self.x0 = (W - self.size) // 2
        self._placed = {}
        self._last_move = None
        self._win_since = None
        if THEME == "logic":
            self._gap = 3 if n <= 5 else 2
            self._cell_rad = 5
        else:
            self._gap = 8 if n <= 3 else 6 if n <= 5 else 4 if n <= 9 else 2
            self._cell_rad = max(3, self.cell // 6)
        self._build_board_layer()

    def _build_board_layer(self):
        """Pre-render the board plate and its tiles once per grid size."""
        logic = THEME == "logic"
        pad = 26 if logic else 14
        bw = bh = self.size + 2 * pad
        lay = np.zeros((bh, bw, 3), np.uint8)
        msk = np.zeros((bh, bw), np.uint8)
        g, c, rad = self._gap, self.cell, self._cell_rad
        if logic:
            rounded_rect(lay, (0, 0), (bw - 1, bh - 1), (34, 24, 18), 14)
            rounded_rect(msk, (0, 0), (bw - 1, bh - 1), 238, 14)
            rounded_rect(lay, (0, 0), (bw - 1, bh - 1), (120, 100, 55), 14, 1)
            rounded_rect(msk, (0, 0), (bw - 1, bh - 1), 255, 14, 1)
            L = 24                                           # heavy corner brackets
            for (px, py, sx, sy) in ((1, 1, 1, 1), (bw - 2, 1, -1, 1),
                                     (1, bh - 2, 1, -1), (bw - 2, bh - 2, -1, -1)):
                for img, col in ((lay, NEON), (msk, 255)):
                    cv2.line(img, (px, py), (px + sx * L, py), col, 3, AA)
                    cv2.line(img, (px, py), (px, py + sy * L), col, 3, AA)
            fs = 0.5 if self.n <= 9 else 0.38
            for i in range(self.n):                          # coordinates: A B C... / 1 2 3...
                for lab, cx, cy in ((chr(65 + i), pad + i * c + c // 2, pad // 2 + 1),
                                    (str(i + 1), pad // 2 + 1, pad + i * c + c // 2)):
                    (tw, th), _ = cv2.getTextSize(lab, FONT, fs, 1)
                    pos = (cx - tw // 2, cy + th // 2)
                    cv2.putText(lay, lab, pos, FONT, fs, (205, 185, 120), 1, AA)
                    cv2.putText(msk, lab, pos, FONT, fs, 255, 1, AA)
        else:
            rounded_rect(lay, (0, 0), (bw - 1, bh - 1), (58, 40, 40), 28)
            rounded_rect(msk, (0, 0), (bw - 1, bh - 1), 232, 28)
            rounded_rect(lay, (0, 0), (bw - 1, bh - 1), (170, 140, 155), 28, 2)
            rounded_rect(msk, (0, 0), (bw - 1, bh - 1), 255, 28, 2)
        for row in range(self.n):
            for col in range(self.n):
                x1, y1 = pad + col * c + g, pad + row * c + g
                x2, y2 = pad + (col + 1) * c - g, pad + (row + 1) * c - g
                light = (row + col) % 2 == 0
                if logic:
                    rounded_rect(lay, (x1, y1), (x2, y2), (62, 46, 36) if light else (50, 36, 28), rad)
                    rounded_rect(msk, (x1, y1), (x2, y2), 232, rad)
                    rounded_rect(lay, (x1, y1), (x2, y2), (130, 105, 62), rad, 1)
                    rounded_rect(msk, (x1, y1), (x2, y2), 255, rad, 1)
                    if c >= 28:                              # technical corner ticks
                        t = max(4, c // 7)
                        for (px, py, sx, sy) in ((x1 + 2, y1 + 2, 1, 1), (x2 - 2, y1 + 2, -1, 1),
                                                 (x1 + 2, y2 - 2, 1, -1), (x2 - 2, y2 - 2, -1, -1)):
                            for img, col_ in ((lay, NEON), (msk, 255)):
                                cv2.line(img, (px, py), (px + sx * t, py), col_, 1, AA)
                                cv2.line(img, (px, py), (px, py + sy * t), col_, 1, AA)
                else:
                    rounded_rect(lay, (x1, y1), (x2, y2), (118, 92, 100) if light else (92, 68, 74), rad)
                    rounded_rect(msk, (x1, y1), (x2, y2), 228 if light else 214, rad)
                    if c >= 50:
                        cv2.line(lay, (x1 + rad, y1 + 3), (x2 - rad, y1 + 3), (165, 140, 150), 2, AA)
                        cv2.line(lay, (x1 + rad, y2 - 3), (x2 - rad, y2 - 3), (74, 54, 60), 1, AA)
                        cv2.line(msk, (x1 + rad, y1 + 3), (x2 - rad, y1 + 3), 255, 2, AA)
                        cv2.line(msk, (x1 + rad, y2 - 3), (x2 - rad, y2 - 3), 255, 1, AA)
        a = (msk.astype(np.float32) / 255)[:, :, None]
        self._bl = (self.x0 - pad, self.y0 - pad, bw, bh,
                    (lay.astype(np.float32) * a), 1 - a)

    def _blit_board(self, frame):
        bx, by, bw, bh, lay, inv = self._bl
        roi = frame[by:by + bh, bx:bx + bw]
        roi[:] = (roi * inv + lay).astype(np.uint8)

    def _cell_fill(self, frame, idx, color, alpha, border=None):
        cx, cy = self.center(idx)
        half = self.cell // 2 - self._gap
        panel(frame, cx - half, cy - half, half * 2, half * 2, color, alpha,
              self._cell_rad, border, 2)

    def _mark(self, frame, mark, cx, cy, r, thick, alpha=1.0):
        """Mark with rounded ends, soft shadow, glow and a light core line."""
        pad = r + thick * 2 + 8
        x1, y1 = max(cx - pad, 0), max(cy - pad, 0)
        x2, y2 = min(cx + pad, W), min(cy + pad, H)
        sub = frame[y1:y2, x1:x2]
        lx, ly = cx - x1, cy - y1

        def shape(img, color, t, dx=0, dy=0):
            if mark == "X":
                pts = [(lx - r + dx, ly - r + dy), (lx + r + dx, ly + r + dy),
                       (lx - r + dx, ly + r + dy), (lx + r + dx, ly - r + dy)]
                cv2.line(img, pts[0], pts[1], color, t, AA)
                cv2.line(img, pts[2], pts[3], color, t, AA)
                for q in pts:
                    cv2.circle(img, q, max(1, t // 2), color, -1, AA)
            else:
                cv2.circle(img, (lx + dx, ly + dy), r, color, t, AA)

        col = X_COLOR if mark == "X" else O_COLOR
        if alpha < 1.0:                              # ghost preview
            ov = sub.copy()
            shape(ov, col, thick)
            cv2.addWeighted(ov, alpha, sub, 1 - alpha, 0, sub)
            return
        big = thick >= 5
        if big:
            ov = sub.copy()
            shape(ov, (15, 10, 14), thick + 2, 3, 4)
            cv2.addWeighted(ov, 0.40, sub, 0.60, 0, sub)
            ov = sub.copy()
            shape(ov, col, thick + 7)
            cv2.addWeighted(ov, 0.22, sub, 0.78, 0, sub)
        shape(sub, col, thick)
        if big:
            shape(sub, tuple(min(255, c + 70) for c in col), max(1, thick // 3))

    def _hover_cell(self, frame, idx, progress, now, turn):
        pulse = 0.5 + 0.5 * math.sin(now * 6)
        self._cell_fill(frame, idx, YELLOW, 0.26 + 0.10 * pulse, border=YELLOW)
        cx, cy = self.center(idx)
        if turn in ("X", "O"):
            self._mark(frame, turn, cx, cy, self.cell // 3, max(3, self.cell // 12), alpha=0.35)
        if progress > 0:
            rr = max(5, self.cell // 2 - self._gap - 4)
            cv2.ellipse(frame, (cx, cy), (rr, rr), -90, 0, 360 * progress, YELLOW,
                        max(2, min(4, self.cell // 16)), AA)

    # ---------- per-frame bookkeeping ----------
    def _tick(self):
        now = time.time()
        real = min(now - self._last_t, 0.1)
        self._last_t = now
        self._dt = real * ANIM_SPEED          # all decorative motion uses the slowed dt
        self._at += self._dt
        return now

    @staticmethod
    def _new_petal(anywhere=False):
        return {"x": random.uniform(0, W), "y": random.uniform(0, H) if anywhere else H + 20,
                "vy": random.uniform(-38, -16), "vx": random.uniform(-14, 14),
                "s": random.uniform(7, 15), "rot": random.uniform(0, 360),
                "vr": random.uniform(-40, 40), "ph": random.uniform(0, 6.28),
                "c": random.choice(PETAL_COLORS)}

    def _draw_petals(self, frame, now):
        """Soft pink petals floating upward (tulip-field mood)."""
        overlay = frame.copy()
        for p in self._petals:
            p["y"] += p["vy"] * self._dt
            p["x"] += (p["vx"] + 12 * math.sin(now * 1.3 + p["ph"])) * self._dt
            p["rot"] += p["vr"] * self._dt
            if p["y"] < -20:
                p.update(self._new_petal())
            s = p["s"]
            cv2.ellipse(overlay, (int(p["x"]), int(p["y"])), (int(s), max(2, int(s * 0.55))),
                        p["rot"], 0, 360, p["c"], -1, AA)
        cv2.addWeighted(overlay, 0.30, frame, 0.70, 0, frame)

    # ---------- winner celebration ----------
    def _celebrate(self, frame, over, winner):
        now = time.time()
        dt = self._dt
        if not over:
            self._over_since = None
            self._confetti = []
            return
        if self._over_since is None:
            self._over_since = now
        if not winner or not winner.get("human", True):
            return                                  # computer won: no party
        if now - self._over_since < CONGRATS_DELAY:  # first show the winning line
            return
        self._draw_congrats(frame, winner, now)
        self._draw_confetti(frame, dt)

    def _draw_congrats(self, frame, winner, now):
        mx, my, mw, mh = W // 2 - 270, 138, 540, 544
        cx = W // 2
        # card eases in
        age = min(1.0, (now - self._over_since - CONGRATS_DELAY) / 0.8)
        k = _ease_out_back(age)
        my += int((1 - k) * 40)
        panel(frame, mx, my, mw, mh, CARD, 0.95, 30, YELLOW, 3, shadow=True)
        pulse = 1 + 0.04 * math.sin(self._at * 5)
        cv2.circle(frame, (cx, my + 172), int(118 * pulse), ACCENT, 3, AA)
        cv2.circle(frame, (cx, my + 172), int(126 * pulse), (110, 70, 150), 1, AA)
        avatar(frame, cx, my + 172, 88, winner["avatar"], YELLOW, 6)
        base = my + 84                                   # little crown on top
        crown = np.array([(cx - 42, base), (cx - 42, base - 34), (cx - 21, base - 16),
                          (cx, base - 46), (cx + 21, base - 16), (cx + 42, base - 34),
                          (cx + 42, base)], np.int32)
        cv2.fillPoly(frame, [crown], YELLOW, AA)
        cv2.polylines(frame, [crown], True, (30, 150, 200), 3, AA)
        sc = _fit("CONGRATULATIONS!", mw - 60, 1.25, 3)
        text(frame, "CONGRATULATIONS!", cx, my + 307, sc, YELLOW, 3, shadow=True)
        name = (winner.get("name") or "Player")[:14]
        text(frame, name, cx, my + 367, _fit(name, mw - 80, 1.7, 3), WHITE, 3, shadow=True)
        text(frame, f"won with {default_win_len(self.n)} in a row on the {self.n}x{self.n} board",
             cx, my + 422, _fit("won with 5 in a row on the 12x12 board", mw - 40, 0.7, 1), MUTED, 1)
        text(frame, "Hold your finger on PLAY AGAIN or HOME", cx, my + 487, 0.55, MUTED, 1)

    def _draw_confetti(self, frame, dt):
        colors = [X_COLOR, O_COLOR, YELLOW, GREEN, WHITE, ACCENT]
        if not self._confetti:
            for _ in range(140):
                self._confetti.append({
                    "x": random.uniform(0, W), "y": random.uniform(-H, 0),
                    "vx": random.uniform(-40, 40), "vy": random.uniform(140, 320),
                    "rot": random.uniform(0, 360), "vr": random.uniform(-300, 300),
                    "w": random.uniform(9, 15), "h": random.uniform(5, 9),
                    "c": random.choice(colors), "ph": random.uniform(0, 6.28)})
        for p in self._confetti:
            p["y"] += p["vy"] * dt
            p["x"] += (p["vx"] + 30 * math.sin(time.time() * 3 + p["ph"])) * dt
            p["rot"] += p["vr"] * dt
            if p["y"] > H + 20:
                p["y"] = -20
                p["x"] = random.uniform(0, W)
            box = cv2.boxPoints(((p["x"], p["y"]), (p["w"], p["h"]), p["rot"]))
            cv2.fillConvexPoly(frame, box.astype(np.int32), p["c"], AA)

    # ---------- hit testing ----------
    @staticmethod
    def _inside(shape, px, py):
        kind, v = shape
        if kind == "rect":
            x, y, w, h = v
            return x <= px <= x + w and y <= py <= y + h
        cx, cy, r = v
        return (px - cx) ** 2 + (py - cy) ** 2 <= r * r

    def target_at(self, targets, px, py):
        for name, shape in targets:
            if self._inside(shape, px, py):
                return name
        return None

    def cell_at(self, px, py):
        end = self.cell * self.n
        if not (self.x0 <= px < self.x0 + end and self.y0 <= py < self.y0 + end):
            return None
        return int(((py - self.y0) // self.cell) * self.n + (px - self.x0) // self.cell)

    def center(self, idx):
        row, col = divmod(idx, self.n)
        return (self.x0 + col * self.cell + self.cell // 2,
                self.y0 + row * self.cell + self.cell // 2)

    # ---------- shared widgets ----------
    @staticmethod
    def _new_glyph(anywhere=False):
        return {"x": random.uniform(0, W), "y": random.uniform(0, H) if anywhere else H + 30,
                "vy": random.uniform(-26, -10), "s": random.uniform(10, 20),
                "rot": random.uniform(0, 90), "vr": random.uniform(-25, 25),
                "k": random.choice("XO"), "ph": random.uniform(0, 6.28)}

    def _draw_glyphs(self, frame, now):
        """Small X / O outlines drifting upward - 'thinking' particles."""
        overlay = frame.copy()
        for g in self._glyphs:
            g["y"] += g["vy"] * self._dt
            g["x"] += 6 * math.sin(now * 0.9 + g["ph"]) * self._dt
            g["rot"] += g["vr"] * self._dt
            if g["y"] < -30:
                g.update(self._new_glyph())
            x, y, r = int(g["x"]), int(g["y"]), int(g["s"])
            if g["k"] == "X":
                ca, sa = math.cos(math.radians(g["rot"])), math.sin(math.radians(g["rot"]))
                for ang in (0, 90):
                    c2, s2 = math.cos(math.radians(g["rot"] + ang)), math.sin(math.radians(g["rot"] + ang))
                    cv2.line(overlay, (int(x - r * c2), int(y - r * s2)),
                             (int(x + r * c2), int(y + r * s2)), X_COLOR, 3, AA)
            else:
                cv2.circle(overlay, (x, y), r, O_COLOR, 3, AA)
        cv2.addWeighted(overlay, 0.28, frame, 0.72, 0, frame)

    def _bg(self, frame, cam_alpha, pat_alpha):
        """Animated background (logic board or tulip field), with a hint of the camera."""
        now = self._tick()
        at = self._at
        cv2.addWeighted(frame, cam_alpha, self.grad, 1 - cam_alpha, 0, frame)
        if THEME == "logic":
            by = int((at * 70) % (H + 260)) - 130           # soft scan band sweeping down
            for off, hh, v in ((0, 130, 4), (30, 70, 5), (50, 30, 5)):
                y1, y2 = max(by + off, 0), min(by + off + hh, H)
                if y2 > y1:
                    roi = frame[y1:y2]
                    cv2.add(roi, (v, v, v // 2, 0), dst=roi)
            for sp in self._sparks:                          # pulsing logic nodes
                a = 0.5 + 0.5 * math.sin(at * sp["sp"] + sp["ph"])
                if a > 0.4:
                    x, y = int(sp["x"]), int(sp["y"])
                    cv2.circle(frame, (x, y), int(1 + 2.5 * a), (255, 230, 150), -1, AA)
                    cv2.circle(frame, (x, y), int(4 + 5 * a), NEON, 1, AA)
            self._draw_glyphs(frame, at)
            return now
        off = int(at * 9) % W
        roi = frame[0:CLOUD_H]
        inv = np.ascontiguousarray(self.cloud_inv[:, off:off + W])
        add = np.ascontiguousarray(self.cloud_add[:, off:off + W])
        cv2.multiply(roi, inv, dst=roi, scale=1 / 255)
        cv2.add(roi, add, dst=roi)
        for sp in self._sparks:
            a = 0.5 + 0.5 * math.sin(at * sp["sp"] + sp["ph"])
            if a < 0.35:
                continue
            x, y, r = int(sp["x"]), int(sp["y"]), int(1 + 2.5 * a)
            cv2.circle(frame, (x, y), r, (225, 245, 255), -1, AA)
            if a > 0.8:
                cv2.line(frame, (x - 6, y), (x + 6, y), (225, 245, 255), 1, AA)
                cv2.line(frame, (x, y - 6), (x, y + 6), (225, 245, 255), 1, AA)
        self._draw_petals(frame, at)
        return now

    def _icon(self, frame, kind, cx, cy, sz, color, dark=(50, 35, 35)):
        """Tiny vector icons drawn with OpenCV (no image files needed)."""
        cx, cy = int(cx), int(cy)
        if kind == "play":
            pts = np.array([(cx - sz * .5, cy - sz * .75), (cx - sz * .5, cy + sz * .75),
                            (cx + sz * .8, cy)], np.int32)
            cv2.fillPoly(frame, [pts], color, AA)
        elif kind == "restart":
            cv2.ellipse(frame, (cx, cy), (int(sz), int(sz)), 0, 30, 320, color, max(2, int(sz * .28)), AA)
            th = math.radians(320)
            px, py = cx + sz * math.cos(th), cy + sz * math.sin(th)
            dx, dy = -math.sin(th), math.cos(th)
            ex, ey = math.cos(th), math.sin(th)
            tip = (px + dx * sz * .75, py + dy * sz * .75)
            b1 = (px + ex * sz * .55, py + ey * sz * .55)
            b2 = (px - ex * sz * .55, py - ey * sz * .55)
            cv2.fillPoly(frame, [np.array([tip, b1, b2], np.int32)], color, AA)
        elif kind == "home":
            roof = np.array([(cx - sz, cy - sz * .1), (cx, cy - sz), (cx + sz, cy - sz * .1)], np.int32)
            cv2.fillPoly(frame, [roof], color, AA)
            cv2.rectangle(frame, (int(cx - sz * .68), int(cy - sz * .1)),
                          (int(cx + sz * .68), int(cy + sz * .85)), color, -1, AA)
            cv2.rectangle(frame, (int(cx - sz * .2), int(cy + sz * .3)),
                          (int(cx + sz * .2), int(cy + sz * .85)), dark, -1, AA)
        elif kind == "friend":
            for dx in (-.5, .5):
                cv2.circle(frame, (int(cx + dx * sz), int(cy - sz * .35)), max(2, int(sz * .34)), color, -1, AA)
                cv2.ellipse(frame, (int(cx + dx * sz), int(cy + sz * .75)),
                            (int(sz * .55), int(sz * .5)), 0, 180, 360, color, -1, AA)
        elif kind == "cpu":
            rounded_rect(frame, (int(cx - sz * .85), int(cy - sz * .55)),
                         (int(cx + sz * .85), int(cy + sz * .75)), color, max(2, int(sz * .3)))
            for dx in (-.4, .4):
                cv2.circle(frame, (int(cx + dx * sz), int(cy + sz * .08)), max(2, int(sz * .17)), dark, -1, AA)
            cv2.line(frame, (cx, int(cy - sz * .55)), (cx, int(cy - sz * .95)), color, 2, AA)
            cv2.circle(frame, (cx, int(cy - sz * .98)), max(2, int(sz * .12)), color, -1, AA)
        elif kind == "grid":
            h2 = int(sz * .85)
            for k in (-.33, .33):
                cv2.line(frame, (int(cx + k * 2 * h2), cy - h2), (int(cx + k * 2 * h2), cy + h2), color, 2, AA)
                cv2.line(frame, (cx - h2, int(cy + k * 2 * h2)), (cx + h2, int(cy + k * 2 * h2)), color, 2, AA)

    def _grad_rect(self, frame, x, y, w, h, top, bottom, radius, prog=0.0, prog_color=YELLOW):
        """Rounded rectangle with a vertical gradient (mask cached per size)."""
        if x < 0 or y < 0 or x + w > W or y + h > H:
            return
        key = (w, h, radius)
        a = self._btn_cache.get(key)
        if a is None:
            m = np.zeros((h, w), np.uint8)
            rounded_rect(m, (0, 0), (w - 1, h - 1), 255, radius)
            a = self._btn_cache[key] = (m.astype(np.float32) / 255)[:, :, None]
        t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
        grad = np.array(top, np.float32) * (1 - t) + np.array(bottom, np.float32) * t
        roi = frame[y:y + h, x:x + w]
        out = roi * (1 - a) + grad * a
        if prog > 0:                                  # progress sweep, left to right
            pw = max(2, int(w * prog))
            out[:, :pw] = out[:, :pw] * (1 - 0.5 * a[:, :pw]) + np.array(prog_color, np.float32) * 0.5 * a[:, :pw]
        roi[:] = out.astype(np.uint8)

    def _button(self, frame, label, sub, rect, hover, progress,
                primary=False, disabled=False, icon=None):
        x, y, w, h = rect
        lit = bool(hover) and not disabled
        grow = 4 if lit else 0                        # hovered buttons grow and lift
        x, y, w, h = x - grow, y - grow - (2 if lit else 0), w + 2 * grow, h + 2 * grow
        rad = min(18, h // 2)
        if disabled:
            top, bot, edge = (96, 86, 82), (68, 60, 58), (120, 108, 104)
        elif primary:
            top, bot, edge = ((255, 215, 140), (245, 150, 50), (255, 235, 190)) if lit \
                else ((255, 190, 110), (230, 120, 30), (255, 215, 160))
        else:
            top, bot, edge = ((152, 124, 108), (106, 82, 70), NEON) if lit \
                else ((122, 96, 84), (82, 60, 50), (150, 128, 112))
        if not disabled:                              # drop shadow
            for off, al in ((10, 0.14), (6, 0.20)):
                panel(frame, x + 3, y + off, w - 6, h, (8, 5, 6), al, rad)
        if lit:                                       # neon glow ring
            rounded_rect(frame, (x - 5, y - 5), (x + w + 5, y + h + 5), _lerp_color((60, 45, 30), NEON, 0.55), rad + 4, 2)
        self._grad_rect(frame, x, y, w, h, top, bot, rad, progress if lit else 0.0)
        rounded_rect(frame, (x, y), (x + w, y + h), NEON if lit else edge, rad, 3 if lit else 2)
        if not disabled:                              # gloss + bottom edge for a 3D feel
            panel(frame, x + 4, y + 4, w - 8, max(6, h // 2 - 4), WHITE, 0.12, max(3, rad - 3))
            cv2.line(frame, (x + rad, y + h - 4), (x + w - rad, y + h - 4),
                     _lerp_color(bot, (0, 0, 0), 0.4), 2, AA)
        if lit and progress > 0:
            by = y + h - 10
            cv2.line(frame, (x + 22, by), (x + w - 22, by), (50, 38, 32), 5, AA)
            cv2.line(frame, (x + 22, by), (x + 22 + int((w - 44) * progress), by), YELLOW, 5, AA)

        col = MUTED if disabled else WHITE
        tx = x + w // 2
        if icon:
            self._icon(frame, icon, x + int(h * 0.55), y + h // 2, h * 0.24,
                       MUTED if disabled else WHITE, bot)
            tx += int(h * 0.30)
        avail = w - (int(h * 1.15) if icon else 30) - 10
        if sub:
            sc = _fit(label, avail, 1.1, 2)
            text(frame, label, tx, y + int(h * 0.36), sc, col, 2, shadow=not disabled)
            text(frame, sub, tx, y + int(h * 0.70), _fit(sub, avail, 0.62, 1),
                 MUTED if not primary else WHITE, 1)
        else:
            sc = _fit(label, avail, 0.95, 2)
            text(frame, label, tx, y + h // 2, sc, col, 2, shadow=not disabled)

    def _finish(self, frame, pointer, progress):
        # tracking status pill (always visible)
        if pointer is None:
            self._trail.clear()
            panel(frame, W - 360, 18, 330, 40, CARD, 0.9, 20, BORDER, shadow=True)
            cv2.circle(frame, (W - 335, 38), 6, RED, -1, AA)
            text(frame, "No hand - show your hand", W - 185, 38, 0.55, WHITE, 1)
            return frame
        hand = self._hand if self._hand in HAND_FOR.values() else None
        mark = {"Right": "X", "Left": "O"}.get(hand)
        col = X_COLOR if mark == "X" else O_COLOR if mark == "O" else YELLOW
        panel(frame, W - 260, 18, 230, 40, CARD, 0.9, 20, BORDER, shadow=True)
        cv2.circle(frame, (W - 235, 38), 6, GREEN, -1, AA)
        label = f"{hand} hand = {mark}" if hand else "Hand tracked"
        text(frame, label, W - 130, 38, 0.55, WHITE, 1)

        px, py = int(pointer[0] * W), int(pointer[1] * H)
        self._trail.append((px, py))
        pts = list(self._trail)
        for i, (tx, ty) in enumerate(pts[:-1]):           # fading comet trail in the hand's colour
            f = (i + 1) / len(pts)
            cv2.circle(frame, (tx, ty), max(2, int(7 * f)), _lerp_color((60, 40, 30), col, f * 0.9), -1, AA)

        at = self._at
        x1, y1, x2, y2 = max(px - 60, 0), max(py - 60, 0), min(px + 60, W), min(py + 60, H)
        sub = frame[y1:y2, x1:x2]
        ov = sub.copy()                                    # soft glow halo
        cv2.circle(ov, (px - x1, py - y1), 36, col, -1, AA)
        cv2.addWeighted(ov, 0.22, sub, 0.78, 0, sub)
        rot = at * 55                                      # slowly rotating dashed ring
        for k in range(10):
            cv2.ellipse(frame, (px, py), (27, 27), 0, rot + k * 36, rot + k * 36 + 20, col, 3, AA)
        cv2.circle(frame, (px, py), 15 + int(1.5 * math.sin(at * 3)), WHITE, 2, AA)
        for ang in (0, 90, 180, 270):                      # crosshair ticks
            c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            cv2.line(frame, (int(px + c * 18), int(py + s_ * 18)),
                     (int(px + c * 25), int(py + s_ * 25)), WHITE, 2, AA)
        cv2.circle(frame, (px, py), 5, col, -1, AA)
        cv2.circle(frame, (px, py), 2, WHITE, -1, AA)
        if mark:                                           # which mark this hand will place
            bx, by = px + 34, py + 34
            cv2.circle(frame, (bx, by), 15, (40, 30, 26), -1, AA)
            cv2.circle(frame, (bx, by), 15, col, 2, AA)
            draw_mark(frame, mark, bx, by, 6, 3)
        if progress > 0:                                   # dwell ring with a glowing head
            cv2.ellipse(frame, (px, py), (36, 36), -90, 0, 360, (60, 45, 40), 7, AA)
            cv2.ellipse(frame, (px, py), (36, 36), -90, 0, 360 * progress, YELLOW, 5, AA)
            ang = math.radians(-90 + 360 * progress)
            cv2.circle(frame, (int(px + 36 * math.cos(ang)), int(py + 36 * math.sin(ang))), 5, WHITE, -1, AA)
        return frame

    def _draw_picker(self, frame, sel, hover, progress):
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

    # ======================= WELCOME =======================
    def draw_welcome(self, frame, pointer, hover, progress):
        frame[:] = self.welcome_background

        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 455), (W, H), (18, 15, 32), -1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

        text(frame, "READY TO PLAY?", W // 2, 495, 1.1, WHITE, 2, shadow=True)
        text(frame, "Play Tic-Tac-Toe using hand gestures", W // 2, 530,
             0.62, MUTED, 1, shadow=True)
        for name, label, rect, primary in self.welcome_buttons:
            self._button(frame, label, "", rect, hover == name,
                         progress if hover == name else 0, primary=primary)
        text(frame, "Hold a button  |  Enter = let's go  |  Esc = exit",
             W // 2, 670, 0.52, MUTED, 1, shadow=True)
        return self._finish(frame, pointer, progress)

    def draw_instructions(self, frame, pointer, hover, progress):
        self._bg(frame, 0.16, 0.18)
        panel(frame, 170, 90, 940, 600, CARD, 0.94, 30, BORDER, 2, shadow=True)
        text(frame, "HOW TO PLAY", W // 2, 150, 1.5, WHITE, 3, shadow=True)

        instructions = [
            ("1", "Choose your player", "Type your name and pick a character on the home screen."),
            ("2", "Choose a game", "Play vs Computer or play with a friend."),
            ("3", "Use your hands", "Show your hands to the camera. Right hand is X; left hand is O."),
            ("4", "Make a move", "Point at an empty square and hold until your mark appears."),
            ("5", "Win the game", "Get the required marks in a row before your opponent does."),
        ]
        for i, (number, title, detail) in enumerate(instructions):
            y = 225 + i * 67
            cv2.circle(frame, (245, y - 8), 21, ACCENT, -1, AA)
            text(frame, number, 245, y, 0.58, WHITE, 2)
            text(frame, title, 290, y - 8, 0.72, WHITE, 2, "left")
            text(frame, detail, 290, y + 18, 0.5, MUTED, 1, "left")

        text(frame, "Hold a button with your fingertip to select it.",
             W // 2, 565, 0.55, YELLOW, 1)
        self._button(frame, "BACK TO HOME", "", (510, 590, 260, 64),
                     hover == "home", progress if hover == "home" else 0)
        return self._finish(frame, pointer, progress)

    def draw_friend_setup(self, frame, name, sel, pointer, hover, progress, message=""):
        self._bg(frame, 0.10, 0.14)
        panel(frame, 80, 105, 1120, 570, CARD, 0.94, 30, BORDER, 2, shadow=True)
        text(frame, "PLAY WITH A FRIEND", W // 2, 150, 1.25, WHITE, 2, shadow=True)
        text(frame, "Set up your friend before starting the game", W // 2, 190,
             0.62, MUTED, 1)

        panel(frame, 125, 225, 455, 340, CARD_LIGHT, 0.76, 24, BORDER, 2)
        panel(frame, 620, 225, 535, 340, CARD_LIGHT, 0.76, 24, BORDER, 2)
        text(frame, "FRIEND'S NAME", 160, 260, 0.62, MUTED, 1, "left")
        panel(frame, 155, 278, 395, 58, CARD, 0.96, 14, NEON, 2)
        shown_name = name or "Type a name..."
        name_color = WHITE if name else MUTED
        text(frame, shown_name, 180, 307, 1.0, name_color, 2, "left")
        if name and int(time.time() * 2) % 2 == 0:
            (tw, _), _ = cv2.getTextSize(name, FONT, 1.0, 2)
            cv2.line(frame, (185 + tw, 289), (185 + tw, 325), YELLOW, 2, AA)
        text(frame, "Type a name, then hold LET'S GO to start", 160, 365,
             0.48, MUTED, 1, "left")
        text(frame, "CHOSEN PICTURE", 350, 414, 0.55, MUTED, 1)
        avatar(frame, 350, 475, 54, sel, YELLOW, 4)
        text(frame, avatars.name(sel), 350, 540, 0.58, YELLOW, 1)
        if message:
            text(frame, message, 160, 585, 0.48, RED, 1, "left")

        text(frame, "CHOOSE A PICTURE", 887, 260, 0.7, WHITE, 1)
        for i, (x, y) in enumerate(self.friend_avatar_pos):
            lit = hover == f"friend_avatar:{i}"
            if i == sel:
                cv2.circle(frame, (x, y), 37, YELLOW, 3, AA)
            elif lit:
                cv2.circle(frame, (x, y), 36, WHITE, 2, AA)
            avatar(frame, x, y, 28, i, WHITE if lit else BORDER, 2)

        for button, label, rect, primary in self.friend_setup_buttons:
            self._button(frame, label, "", rect, hover == button,
                         progress if hover == button else 0, primary=primary,
                         disabled=button == "friend_start" and not name.strip())
        text(frame, "Type the name with your keyboard  |  Hold a picture to choose it  |  Esc = back",
             W // 2, 650, 0.48, MUTED, 1)
        return self._finish(frame, pointer, progress)

    # ======================= HOME =======================
    def draw_home(self, frame, name, sel, stats, pointer, hover, progress, message, grid=3, hand=None,
                  level="easy", picking=False):
        self._over_since = None
        self._bg(frame, 0.16, 0.18)
        t = self._at
        self._hand = hand

        # logo / title
        text(frame, "GESTURE TIC TAC TOE", W // 2, 55, 1.8, WHITE, 4, shadow=True)
        draw_mark(frame, "X", W // 2 - 385, 55, 20, 7)
        draw_mark(frame, "O", W // 2 + 385, 55, 22, 7)
        text(frame, "Right hand = X     Left hand = O     |     pick a character and a name", W // 2, 98, 0.62, WHITE, 1, shadow=True)

        # ----- left: player card -----
        panel(frame, 60, 125, 350, 565, CARD, 0.90, 28, BORDER, shadow=True)
        text(frame, "YOUR PLAYER", 235, 160, 0.6, MUTED, 1)
        text(frame, "point at the picture to change", 235, 182, 0.45, MUTED, 1)
        bob = int(5 * math.sin(t * 2.2))
        glow = 2 + int(1.5 * (1 + math.sin(t * 3)))
        cv2.circle(frame, (235, 305 + bob), 108, (130, 80, 60), 1, AA)
        cv2.circle(frame, (235, 305 + bob), 104, ACCENT, glow, AA)
        avatar(frame, 235, 305 + bob, 94, sel, WHITE, 5)
        if hover == "profile":
            cv2.circle(frame, (235, 305 + bob), 114, YELLOW, 3, AA)
        cv2.circle(frame, (312, 380 + bob), 21, ACCENT, -1, AA)
        cv2.circle(frame, (312, 380 + bob), 21, WHITE, 2, AA)
        self._icon(frame, "restart", 312, 380 + bob, 9, WHITE)
        text(frame, avatars.name(sel), 235, 425, 0.7, YELLOW, 1)
        text(frame, name[:14] or "Player", 235, 465, 1.25,
             WHITE if name else MUTED, 2, shadow=bool(name))
        cv2.line(frame, (110, 500), (360, 500), BORDER, 1, AA)
        text(frame, "RECORD vs COMPUTER", 235, 535, 0.5, MUTED, 1)
        for x, key, label, col in ((120, "wins", "WINS", GREEN),
                                   (235, "losses", "LOSSES", RED),
                                   (350, "draws", "DRAWS", YELLOW)):
            text(frame, str(stats.get(key, 0)), x, 580, 1.3, col, 2)
            text(frame, label, x, 620, 0.5, MUTED, 1)

        # ----- right: name + characters -----
        panel(frame, 440, 125, 780, 565, CARD, 0.62, 28, BORDER, shadow=True)

        text(frame, "YOUR NAME", 470, 154, 0.6, MUTED, 1, "left")
        panel(frame, 470, 166, 720, 56, CARD, 0.92, 16, (255, 170, 90), 2)
        if name:
            text(frame, name, 495, 194, 1.3, WHITE, 2, "left")
            (tw, _), _ = cv2.getTextSize(name, FONT, 1.3, 2)
            cx = 495 + tw + 6
        else:
            text(frame, "Type your name...", 495, 194, 1.1, MUTED, 1, "left")
            cx = 495
        if int(time.time() * 2) % 2 == 0:
            cv2.line(frame, (cx, 178), (cx, 210), YELLOW, 3, AA)
        if message:
            text(frame, message, 470, 242, 0.62, RED, 2, "left")
        else:
            text(frame, "Use your keyboard to type, press Enter to confirm",
                 470, 242, 0.55, MUTED, 1, "left")


        text(frame, "BOARD SIZE", 470, 300, 0.6, MUTED, 1, "left")
        text(frame, f"{default_win_len(grid)} in a row to win", 1190, 300, 0.6, YELLOW, 1, "right")
        for k, rect in self.size_rects.items():
            tgt = f"size:{k}"
            self._button(frame, f"{k}x{k}", "", rect, hover == tgt,
                         progress if hover == tgt else 0, primary=(k == grid), icon="grid")

        can_play = bool(name.strip())
        text(frame, "LEVEL", 470, 420, 0.6, MUTED, 1, "left")
        desc = {"easy": "Easy: computer plays random moves",
                "medium": "Medium: computer wins and blocks",
                "advanced": "Advanced: smart computer"}
        if can_play:
            text(frame, desc.get(level, ""), 1190, 420, 0.55, YELLOW, 1, "right")
        else:
            text(frame, "Type your name to unlock play", 1190, 420, 0.55, YELLOW, 1, "right")
        dots = {"easy": GREEN, "medium": YELLOW, "advanced": RED}
        for lvl, rect in self.level_rects.items():
            tgt = f"level:{lvl}"
            self._button(frame, lvl.upper(), "", rect, hover == tgt,
                         progress if hover == tgt else 0, primary=(lvl == level))
            dot = (rect[0] + 24, rect[1] + rect[3] // 2)
            cv2.circle(frame, dot, 7, dots[lvl], -1, AA)
            cv2.circle(frame, dot, 7, WHITE, 1, AA)
        for n_, label, sub, rect, primary in self.home_buttons:
            self._button(frame, label, sub, rect, hover == n_,
                         progress if hover == n_ else 0, primary, disabled=not can_play,
                         icon=self._icons.get(n_))
        self._button(frame, "COME BACK", "", (60, 20, 180, 44),
                     hover == "welcome", progress if hover == "welcome" else 0)
        if not can_play:
            pass

        text(frame, "Keyboard:  type name    Enter = confirm    Backspace = delete    Esc = quit",
             W // 2, H - 14, 0.55, MUTED, 1)
        if picking:
            self._draw_picker(frame, sel, hover, progress)
        return self._finish(frame, pointer, progress)

    # ======================= GAME =======================
    def _hand_icon(self, frame, cx, cy, sz, color, left):
        """Small open-hand glyph; thumb side tells left from right."""
        sgn = 1 if left else -1
        cv2.ellipse(frame, (cx, int(cy + sz * .3)), (int(sz * .5), int(sz * .55)), 0, 0, 360, color, -1, AA)
        for i, (dx, ln) in enumerate(((-.36, .85), (-.12, 1.05), (.12, 1.0), (.36, .8))):
            cv2.line(frame, (int(cx + dx * sz), int(cy)), (int(cx + dx * sz), int(cy - ln * sz)),
                     color, max(2, int(sz * .2)), AA)
        cv2.line(frame, (int(cx + sgn * sz * .4), int(cy + sz * .4)),
                 (int(cx + sgn * sz * .95), int(cy - sz * .1)), color, max(2, int(sz * .22)), AA)

    def _player_card(self, frame, x, y, p, active, now, hand=None):
        pulse = 0.5 + 0.5 * math.sin(now * 4)
        if active:      # glowing halo around the player whose turn it is
            halo = _lerp_color(CARD, YELLOW, 0.25 + 0.2 * pulse)
            panel(frame, x - 6, y - 6, 292, 382, halo, 0.55, 30)
        panel(frame, x, y, 280, 370, CARD, 0.90, 26,
              YELLOW if active else BORDER, 3 if active else 2, shadow=True)
        cx = x + 140
        if active:
            cv2.circle(frame, (cx, y + 95), 58 + 6 + int(3 * pulse), YELLOW, 2, AA)
        avatar(frame, cx, y + 95, 58, p["avatar"], YELLOW if active else WHITE, 4)
        text(frame, p["name"][:14], cx, y + 185, 0.95, WHITE, 2, shadow=True)
        draw_mark(frame, p["mark"], cx, y + 235, 17, 5)
        text(frame, str(p["score"]), cx, y + 292, 1.8, p["mark_color"], 3, shadow=True)
        text(frame, "WINS", cx, y + 328, 0.55, MUTED, 1)
        if active:
            text(frame, "YOUR TURN", cx, y + 20, 0.5, YELLOW, 1)
        # hand rule badge: right hand = X, left hand = O
        need = HAND_FOR.get(p["mark"], "Right")
        ok = active and hand == need
        bcol = GREEN if ok else (RED if (active and hand and hand != need) else BORDER)
        panel(frame, x + 30, y + 338, 220, 26, (50, 36, 30), 0.9, 13, bcol, 2)
        self._hand_icon(frame, x + 52, y + 357, 9, GREEN if ok else MUTED, need == "Left")
        text(frame, f"{need.upper()} HAND = {p['mark']}", x + 160, y + 351, 0.5,
             GREEN if ok else WHITE, 1)

    def _track_marks(self, board, now):
        """Remember when each mark appeared (for the pop-in animation + last move)."""
        cells = board.cells
        if any(i in self._placed and not cells[i] for i in self._placed):
            self._placed = {}
            self._last_move = None
        for idx, mark in enumerate(cells):
            if mark and idx not in self._placed:
                self._placed[idx] = now
                self._last_move = idx

    def draw_game(self, frame, board, pointer, hover, progress, header,
                  header_color, left, right, draws, turn, win_line, over, winner=None, hand=None):
        now = self._bg(frame, 0.30, 0.09)
        self._hand = hand
        self._track_marks(board, now)

        panel(frame, W // 2 - 300, 36, 600, 66, CARD, 0.92, 33, BORDER, shadow=True)
        text(frame, header, W // 2, 69, _fit(header, 560, 1.1, 2), header_color, 2, shadow=True)
        text(frame, f"Draws: {draws}", W // 2, 113, 0.55, MUTED, 1)

        self._player_card(frame, 50, 170, left, turn == left["mark"] and not over, self._at, hand)
        self._player_card(frame, 950, 170, right, turn == right["mark"] and not over, self._at, hand)

        self._blit_board(frame)                      # plate + rounded tiles

        # hover highlight (+ ghost preview of your mark) on the pointed cell
        if not over and isinstance(hover, int) and board.is_empty(hover):
            self._hover_cell(frame, hover, progress, self._at, turn)

        # winning cells pulse green
        if win_line:
            pulse = 0.5 + 0.5 * math.sin(self._at * 6)
            for idx in win_line:
                self._cell_fill(frame, idx, GREEN, 0.30 + 0.18 * pulse, border=GREEN)

        # marks (pop-in animation)
        base_r = self.cell // 3
        base_t = max(3, self.cell // 12)
        for idx, mark in enumerate(board.cells):
            if not mark:
                continue
            cx, cy = self.center(idx)
            age = (now - self._placed.get(idx, 0)) / MARK_POP_TIME
            sc = _ease_out_back(min(1.0, age)) if age < 1 else 1.0
            self._mark(frame, mark, cx, cy, max(2, int(base_r * sc)), base_t)

        # last-move marker (small dot in the cell corner)
        if self._last_move is not None and not over and board.cells[self._last_move]:
            cx, cy = self.center(self._last_move)
            off = self.cell // 2 - max(4, self.cell // 9)
            cv2.circle(frame, (cx + off, cy - off), max(2, self.cell // 22), YELLOW, -1, AA)

        # winning line draws itself
        if win_line:
            if self._win_since is None:
                self._win_since = now
            p = min(1.0, (now - self._win_since) / WIN_LINE_TIME)
            a, b = self.center(win_line[0]), self.center(win_line[-1])
            end = (int(a[0] + (b[0] - a[0]) * p), int(a[1] + (b[1] - a[1]) * p))
            th = max(6, self.cell // 11)
            cv2.line(frame, a, end, (40, 90, 40), th + 6, AA)
            cv2.line(frame, a, end, GREEN, th, AA)
        else:
            self._win_since = None

        buttons = self.over_buttons if over else self.play_buttons
        for n_, label, rect, primary in buttons:
            self._button(frame, label, "", rect, hover == n_,
                         progress if hover == n_ else 0, primary, icon=self._icons.get(n_))

        # wrong-hand warning (right hand = X, left hand = O)
        if (not over and pointer is not None and hand in ("Left", "Right")
                and turn in HAND_FOR and hand != HAND_FOR[turn]):
            panel(frame, W // 2 - 300, 106, 600, 36, (40, 40, 150), 0.95, 18, RED, 2, shadow=True)
            text(frame, f"Use your {HAND_FOR[turn].upper()} hand to play {turn}",
                 W // 2, 124, 0.7, WHITE, 2)

        self._celebrate(frame, over, winner)

        text(frame, "Keyboard:  R = restart round    M = home    Q = quit",
             W // 2, H - 14, 0.5, MUTED, 1)
        return self._finish(frame, pointer, progress)