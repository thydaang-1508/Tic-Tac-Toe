"""Anime-style profile avatars.

16 characters are drawn with OpenCV (no image files needed).
Extra avatars: drop any PNG/JPG into  assets/avatars/  and they appear
automatically in the character picker (max 8 extra, cropped to a circle).
"""
import math
import os

import cv2
import numpy as np

AA = cv2.LINE_AA
S = 256  # internal sprite size
AVATAR_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "avatars")
)
MAX_CUSTOM = 8


def _c(r, g, b):
    """RGB -> BGR."""
    return (b, g, r)


CHARACTERS = [
    dict(name="Sakura", bg=_c(255, 214, 230), hair=_c(255, 150, 190), light=_c(255, 205, 228),
         dark=_c(190, 85, 135), eyes=_c(60, 175, 120), style="long", bangs="straight",
         acc="ribbon", outfit=_c(235, 110, 150)),
    dict(name="Hinata", bg=_c(200, 225, 255), hair=_c(70, 110, 230), light=_c(135, 175, 255),
         dark=_c(35, 60, 160), eyes=_c(255, 190, 60), style="short", bangs="spiky",
         acc="headband", outfit=_c(60, 80, 140)),
    dict(name="Yuki", bg=_c(185, 210, 245), hair=_c(235, 240, 250), light=_c(255, 255, 255),
         dark=_c(140, 155, 190), eyes=_c(110, 185, 255), style="long", bangs="side",
         acc="none", outfit=_c(90, 110, 170)),
    dict(name="Rin", bg=_c(255, 205, 210), hair=_c(45, 45, 70), light=_c(105, 105, 150),
         dark=_c(15, 15, 30), eyes=_c(230, 60, 70), style="twintail", bangs="straight",
         acc="ribbon", outfit=_c(200, 50, 70)),
    dict(name="Kaito", bg=_c(255, 232, 175), hair=_c(255, 150, 50), light=_c(255, 205, 115),
         dark=_c(190, 85, 20), eyes=_c(120, 70, 40), style="short", bangs="spiky",
         acc="none", outfit=_c(40, 125, 65)),
    dict(name="Mei", bg=_c(200, 245, 220), hair=_c(60, 170, 120), light=_c(125, 225, 175),
         dark=_c(30, 100, 70), eyes=_c(60, 120, 205), style="bob", bangs="straight",
         acc="glasses", outfit=_c(235, 235, 240)),
    dict(name="Luna", bg=_c(225, 205, 255), hair=_c(150, 90, 220), light=_c(205, 155, 255),
         dark=_c(90, 50, 150), eyes=_c(255, 210, 60), style="bun", bangs="side",
         acc="flower", outfit=_c(110, 70, 180)),
    dict(name="Mika", bg=_c(255, 240, 200), hair=_c(255, 215, 90), light=_c(255, 242, 165),
         dark=_c(200, 150, 30), eyes=_c(60, 170, 255), style="bob", bangs="straight",
         acc="catears", outfit=_c(255, 130, 90)),
    # ---------- new characters ----------
    dict(name="Aoi", bg=_c(205, 238, 255), hair=_c(45, 70, 135), light=_c(105, 135, 210),
         dark=_c(15, 28, 80), eyes=_c(70, 205, 225), style="ponytail", bangs="parted",
         acc="crown", outfit=_c(55, 80, 145)),
    dict(name="Hana", bg=_c(255, 236, 214), hair=_c(135, 82, 55), light=_c(195, 140, 100),
         dark=_c(75, 42, 30), eyes=_c(110, 200, 90), style="twintail", bangs="side",
         acc="star", outfit=_c(250, 165, 55)),
    dict(name="Ren", bg=_c(212, 218, 232), hair=_c(36, 36, 48), light=_c(95, 95, 122),
         dark=_c(12, 12, 24), eyes=_c(255, 170, 40), style="short", bangs="parted",
         acc="headphones", outfit=_c(70, 70, 105)),
    dict(name="Nina", bg=_c(255, 240, 205), hair=_c(225, 55, 75), light=_c(255, 125, 135),
         dark=_c(140, 20, 40), eyes=_c(120, 85, 210), style="ponytail", bangs="straight",
         acc="star", outfit=_c(175, 40, 65)),
    dict(name="Sora", bg=_c(210, 240, 255), hair=_c(70, 205, 250), light=_c(160, 235, 255),
         dark=_c(25, 125, 175), eyes=_c(255, 120, 150), style="bob", bangs="parted",
         acc="flower", outfit=_c(245, 245, 250)),
    dict(name="Kenji", bg=_c(205, 242, 235), hair=_c(35, 165, 165), light=_c(110, 220, 215),
         dark=_c(15, 95, 100), eyes=_c(255, 120, 60), style="short", bangs="spiky",
         acc="headphones", outfit=_c(30, 105, 115)),
    dict(name="Ayame", bg=_c(242, 218, 250), hair=_c(78, 45, 105), light=_c(140, 100, 175),
         dark=_c(32, 15, 50), eyes=_c(255, 110, 175), style="long", bangs="parted",
         acc="flower", outfit=_c(145, 65, 155)),
    dict(name="Momo", bg=_c(255, 238, 205), hair=_c(255, 172, 148), light=_c(255, 215, 195),
         dark=_c(205, 105, 85), eyes=_c(150, 100, 225), style="bun", bangs="side",
         acc="crown", outfit=_c(255, 195, 95)),
]

BANGS = {
    "straight": [(62, 110), (60, 80), (76, 52), (128, 40), (180, 52), (196, 80), (194, 110),
                 (176, 92), (160, 116), (144, 88), (128, 118), (112, 88), (96, 116), (80, 92)],
    "spiky": [(60, 112), (52, 70), (74, 64), (70, 28), (100, 52), (116, 18), (140, 50),
              (164, 22), (172, 56), (200, 36), (196, 76), (204, 112), (180, 94), (164, 122),
              (146, 92), (128, 126), (110, 92), (92, 122), (78, 94)],
    "parted": [(60, 116), (58, 80), (76, 52), (128, 38), (180, 52), (198, 80), (196, 116),
               (188, 102), (166, 86), (142, 72), (128, 64), (114, 72), (90, 86), (68, 102)],
    "side": [(60, 118), (58, 78), (78, 50), (128, 38), (180, 52), (198, 84), (196, 116),
             (180, 96), (150, 100), (110, 112), (84, 134), (74, 112)],
}


def _poly(img, pts, fill, outline=None):
    arr = np.array(pts, np.int32)
    cv2.fillPoly(img, [arr], fill, AA)
    if outline is not None:
        cv2.polylines(img, [arr], True, outline, 2, AA)


def _blend_ellipse(img, center, axes, color, alpha):
    ov = img.copy()
    cv2.ellipse(ov, center, axes, 0, 0, 360, color, -1, AA)
    cv2.addWeighted(ov, alpha, img, 1 - alpha, 0, img)


def _render_anime(spec):
    img = np.full((S, S, 3), spec["bg"], np.uint8)
    for x, y, r in ((40, 50, 5), (215, 60, 4), (28, 150, 3), (228, 140, 5), (70, 22, 3)):
        cv2.circle(img, (x, y), r, (255, 255, 255), -1, AA)

    hair, light, dark = spec["hair"], spec["light"], spec["dark"]
    skin, shade = _c(255, 226, 205), _c(238, 192, 168)
    ink = (45, 30, 40)
    style, acc = spec["style"], spec["acc"]

    # ---------- back hair ----------
    if style == "long":
        cv2.ellipse(img, (128, 160), (88, 112), 0, 0, 360, hair, -1, AA)
    elif style == "bob":
        cv2.ellipse(img, (128, 142), (86, 92), 0, 0, 360, hair, -1, AA)
    elif style == "twintail":
        cv2.ellipse(img, (44, 175), (26, 72), 8, 0, 360, hair, -1, AA)
        cv2.ellipse(img, (212, 175), (26, 72), -8, 0, 360, hair, -1, AA)
        cv2.ellipse(img, (128, 120), (72, 76), 0, 0, 360, hair, -1, AA)
        for x in (48, 208):
            cv2.circle(img, (x, 114), 8, _c(255, 110, 150), -1, AA)
    elif style == "ponytail":
        cv2.ellipse(img, (208, 168), (24, 72), -12, 0, 360, hair, -1, AA)
        cv2.ellipse(img, (128, 120), (72, 76), 0, 0, 360, hair, -1, AA)
        cv2.circle(img, (194, 108), 8, _c(255, 110, 150), -1, AA)
    elif style == "bun":
        cv2.circle(img, (128, 36), 28, hair, -1, AA)
        cv2.circle(img, (128, 36), 28, dark, 2, AA)
        cv2.ellipse(img, (128, 120), (72, 76), 0, 0, 360, hair, -1, AA)
    else:
        cv2.ellipse(img, (128, 118), (72, 78), 0, 0, 360, hair, -1, AA)

    if acc == "catears":
        for sx in (-1, 1):
            _poly(img, [(128 + sx * 58, 78), (128 + sx * 68, 10), (128 + sx * 16, 50)], hair, dark)
            _poly(img, [(128 + sx * 54, 70), (128 + sx * 62, 28), (128 + sx * 32, 52)],
                  _c(255, 170, 190))

    # ---------- body ----------
    cv2.ellipse(img, (128, 292), (118, 70), 0, 0, 360, spec["outfit"], -1, AA)
    cv2.rectangle(img, (112, 185), (144, 235), shade, -1)
    _poly(img, [(98, 232), (128, 264), (158, 232), (128, 224)], (255, 255, 255))

    # ---------- face ----------
    cv2.ellipse(img, (128, 138), (60, 68), 0, 0, 360, skin, -1, AA)
    if style in ("long", "bob"):
        bottom = 238 if style == "long" else 198
        for sx in (-1, 1):
            _poly(img, [(128 + sx * 60, 92), (128 + sx * 74, 150), (128 + sx * 70, bottom),
                        (128 + sx * 52, 150), (128 + sx * 50, 100)], hair, dark)
    _blend_ellipse(img, (80, 172), (15, 8), _c(255, 125, 150), 0.45)
    _blend_ellipse(img, (176, 172), (15, 8), _c(255, 125, 150), 0.45)
    cv2.line(img, (128, 171), (126, 176), shade, 2, AA)
    cv2.ellipse(img, (128, 186), (10, 6), 0, 15, 165, (90, 70, 170), 3, AA)
    if spec["bangs"] == "parted":                      # flat, friendly eyebrows
        cv2.line(img, (82, 111), (112, 109), dark, 4, AA)
        cv2.line(img, (144, 109), (174, 111), dark, 4, AA)
    else:
        cv2.line(img, (82, 114), (112, 108), dark, 4, AA)
        cv2.line(img, (144, 108), (174, 114), dark, 4, AA)

    # ---------- front hair ----------
    cv2.ellipse(img, (128, 100), (66, 50), 0, 180, 360, hair, -1, AA)
    _poly(img, BANGS[spec["bangs"]], hair, dark)
    cv2.ellipse(img, (128, 90), (48, 32), 0, 208, 332, light, 7, AA)

    # ---------- eyes (drawn last so bangs never cover them) ----------
    for ex in (98, 158):
        ey = 148
        cv2.ellipse(img, (ex, ey), (21, 27), 0, 0, 360, (255, 255, 255), -1, AA)
        cv2.ellipse(img, (ex, ey + 2), (16, 23), 0, 0, 360, spec["eyes"], -1, AA)
        cv2.ellipse(img, (ex, ey + 4), (8, 13), 0, 0, 360, ink, -1, AA)
        cv2.circle(img, (ex - 6, ey - 8), 7, (255, 255, 255), -1, AA)
        cv2.circle(img, (ex + 6, ey + 10), 3, (255, 255, 255), -1, AA)
        cv2.ellipse(img, (ex, ey), (23, 29), 0, 195, 345, ink, 5, AA)

    # ---------- accessories ----------
    if acc == "ribbon":
        cx, cy = 66, 64
        _poly(img, [(cx, cy), (cx - 24, cy - 14), (cx - 24, cy + 14)], _c(255, 90, 120), dark)
        _poly(img, [(cx, cy), (cx + 24, cy - 14), (cx + 24, cy + 14)], _c(255, 90, 120), dark)
        cv2.circle(img, (cx, cy), 7, _c(255, 150, 170), -1, AA)
    elif acc == "headband":
        cv2.ellipse(img, (128, 104), (68, 52), 0, 205, 335, _c(235, 60, 70), 9, AA)
    elif acc == "glasses":
        for ex in (98, 158):
            cv2.circle(img, (ex, 148), 30, (70, 55, 75), 4, AA)
        cv2.line(img, (128 - 2, 148), (128 + 2, 148), (70, 55, 75), 4, AA)
        cv2.line(img, (68, 146), (58, 138), (70, 55, 75), 4, AA)
        cv2.line(img, (188, 146), (198, 138), (70, 55, 75), 4, AA)
    elif acc == "flower":
        fx, fy = 190, 70
        for k in range(5):
            ang = k * 2 * np.pi / 5
            cv2.circle(img, (int(fx + 11 * np.cos(ang)), int(fy + 11 * np.sin(ang))), 9,
                       (255, 255, 255), -1, AA)
        cv2.circle(img, (fx, fy), 6, _c(255, 205, 60), -1, AA)
    elif acc == "star":
        sx, sy = 70, 66
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            rad = 20 if k % 2 == 0 else 9
            pts.append((int(sx + rad * math.cos(ang)), int(sy + rad * math.sin(ang))))
        _poly(img, pts, _c(255, 215, 60), _c(200, 140, 20))
    elif acc == "crown":
        gold, edge = _c(255, 208, 60), _c(195, 135, 20)
        _poly(img, [(98, 56), (98, 28), (113, 40), (128, 16), (143, 40), (158, 28), (158, 56)],
              gold, edge)
        for jx, col in ((113, _c(255, 90, 120)), (128, _c(90, 170, 255)), (143, _c(255, 90, 120))):
            cv2.circle(img, (jx, 49), 4, col, -1, AA)
    elif acc == "headphones":
        cv2.ellipse(img, (128, 112), (78, 70), 0, 192, 348, (62, 58, 70), 9, AA)
        for ex in (50, 206):
            cv2.circle(img, (ex, 128), 20, (62, 58, 70), -1, AA)
            cv2.circle(img, (ex, 128), 12, _c(255, 120, 150), -1, AA)
            cv2.circle(img, (ex, 128), 20, (35, 32, 40), 2, AA)
    return img


# ======================= registry =======================
_custom = []     # list of (name, 256x256 BGR image)
_sprites = {}    # idx -> 256x256 BGR
_scaled = {}     # (idx, size) -> (sprite, alpha)


def init():
    """Load custom images from assets/avatars/ (safe to call more than once)."""
    _custom.clear()
    _scaled.clear()
    if not os.path.isdir(AVATAR_DIR):
        return
    for fn in sorted(os.listdir(AVATAR_DIR)):
        if len(_custom) >= MAX_CUSTOM:
            break
        if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
            continue
        try:
            data = np.fromfile(os.path.join(AVATAR_DIR, fn), np.uint8)
            im = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
            if im is None:
                continue
            if im.ndim == 2:
                im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
            elif im.shape[2] == 4:
                a = im[:, :, 3:4].astype(np.float32) / 255.0
                im = (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
            h, w = im.shape[:2]
            s = min(h, w)
            y0, x0 = (h - s) // 2, (w - s) // 2
            im = cv2.resize(im[y0:y0 + s, x0:x0 + s], (S, S), interpolation=cv2.INTER_AREA)
            _custom.append((os.path.splitext(fn)[0][:12], im))
        except Exception as e:  # a bad image must never crash the game
            print("Skipping avatar", fn, e)


def count():
    return len(CHARACTERS) + len(_custom)


def name(idx):
    idx %= count()
    if idx < len(CHARACTERS):
        return CHARACTERS[idx]["name"]
    return _custom[idx - len(CHARACTERS)][0]


def _sprite(idx):
    if idx < len(CHARACTERS):
        if idx not in _sprites:
            _sprites[idx] = _render_anime(CHARACTERS[idx])
        return _sprites[idx]
    return _custom[idx - len(CHARACTERS)][1]


def draw(img, cx, cy, r, idx):
    """Draw avatar `idx` as a circle of radius r centred at (cx, cy)."""
    idx %= count()
    size = 2 * r
    key = (idx, size)
    if key not in _scaled:
        sp = cv2.resize(_sprite(idx), (size, size), interpolation=cv2.INTER_AREA)
        m = np.zeros((size, size), np.uint8)
        cv2.circle(m, (r, r), r, 255, -1, AA)
        _scaled[key] = (sp, (m.astype(np.float32) / 255.0)[:, :, None])
    sp, alpha = _scaled[key]

    fh, fw = img.shape[:2]
    x1, y1 = cx - r, cy - r
    x2, y2 = x1 + size, y1 + size
    ax1, ay1, ax2, ay2 = max(x1, 0), max(y1, 0), min(x2, fw), min(y2, fh)
    if ax2 <= ax1 or ay2 <= ay1:
        return
    roi = img[ay1:ay2, ax1:ax2]
    s = sp[ay1 - y1:ay2 - y1, ax1 - x1:ax2 - x1]
    a = alpha[ay1 - y1:ay2 - y1, ax1 - x1:ax2 - x1]
    roi[:] = (s * a + roi * (1 - a)).astype(np.uint8)