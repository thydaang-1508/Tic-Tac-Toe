import time

import cv2
import numpy as np

LEVELS = ["easy", "medium", "advanced"]
LABELS = {"easy": "EASY", "medium": "MEDIUM", "advanced": "ADVANCED"}
COLORS = {                       # BGR
    "easy": (110, 200, 90),
    "medium": (0, 190, 255),
    "advanced": (70, 70, 235),
}


class LevelSelector:
    """Three buttons (Easy / Medium / Advanced) shown on the home page.
    Point at a button and hold for ~1 second to pick it."""

    def __init__(self, width, height, y_frac=0.75, hold_seconds=1.0):
        self.selected = "easy"
        self.hold_seconds = hold_seconds
        self.progress = 0.0
        self._hover = None
        self._start = 0.0

        bw = int(width * 0.16)
        bh = int(height * 0.075)
        gap = int(width * 0.02)
        x0 = (width - (3 * bw + 2 * gap)) // 2
        y0 = min(int(height * y_frac), height - bh - 6)
        self.rects = {lvl: (x0 + i * (bw + gap), y0, bw, bh)
                      for i, lvl in enumerate(LEVELS)}

    def level_at(self, px, py):
        if px is None:
            return None
        for lvl, (x, y, w, h) in self.rects.items():
            if x <= px <= x + w and y <= py <= y + h:
                return lvl
        return None

    def update(self, px, py):
        """Call every frame. Returns the level when it was just picked."""
        lvl = self.level_at(px, py)
        if lvl != self._hover:
            self._hover = lvl
            self._start = time.time()
            self.progress = 0.0
            return None
        if lvl is None:
            return None
        self.progress = min((time.time() - self._start) / self.hold_seconds, 1.0)
        if self.progress >= 1.0:
            self.progress = 0.0
            self._start = time.time()
            if lvl != self.selected:
                self.selected = lvl
                return lvl
        return None

    def draw(self, frame, px=None, py=None):
        x0, y0 = self.rects["easy"][0], self.rects["easy"][1]
        cv2.putText(frame, "LEVEL", (x0, y0 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (255, 255, 255), 2, cv2.LINE_AA)
        for lvl, (x, y, w, h) in self.rects.items():
            color = COLORS[lvl]
            is_sel = lvl == self.selected
            roi = frame[y:y + h, x:x + w]
            fill = np.full_like(roi, color)
            alpha = 0.85 if is_sel else 0.30
            cv2.addWeighted(fill, alpha, roi, 1 - alpha, 0, roi)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 3 if is_sel else 2)

            text = LABELS[lvl]
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.putText(frame, text, (x + (w - tw) // 2, y + (h + th) // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

            if lvl == self._hover and self.progress > 0:
                cv2.rectangle(frame, (x, y + h - 6),
                              (x + int(w * self.progress), y + h),
                              (255, 255, 255), -1)
        if px is not None:
            cv2.circle(frame, (int(px), int(py)), 10, (255, 255, 255), 2, cv2.LINE_AA)
        return frame