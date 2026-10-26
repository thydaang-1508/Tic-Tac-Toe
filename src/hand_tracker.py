import os
import time
import urllib.request

import cv2
import mediapipe as mp

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "assets", "hand_landmarker.task"
)


def _ensure_model():
    path = os.path.abspath(MODEL_PATH)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        print("Downloading hand model (one time only)...")
        urllib.request.urlretrieve(MODEL_URL, path)
        print("Done.")
    return path


class HandTracker:
    INDEX_TIP = 8

    def __init__(self):
        BaseOptions = mp.tasks.BaseOptions
        HandLandmarker = mp.tasks.vision.HandLandmarker
        HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
        RunningMode = mp.tasks.vision.RunningMode

        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=_ensure_model()),
            running_mode=RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self.landmarker = HandLandmarker.create_from_options(options)
        self._last_ts = 0

    def get_hands(self, frame_bgr):
        """Return detected index fingertips and handedness labels."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        ts = int(time.time() * 1000)
        if ts <= self._last_ts:  # timestamps must increase
            ts = self._last_ts + 1
        self._last_ts = ts

        result = self.landmarker.detect_for_video(image, ts)
        detections = []
        for landmarks, handedness in zip(result.hand_landmarks, result.handedness):
            category = handedness[0]
            label = category.category_name
            if label not in ("Left", "Right") or category.score < 0.6:
                continue
            tip = landmarks[self.INDEX_TIP]
            detections.append(((tip.x, tip.y), label))
        return detections

    def get_fingertip(self, frame_bgr):
        """Return the first detected index fingertip, normalized 0..1, or None."""
        hands = self.get_hands(frame_bgr)
        return hands[0][0] if hands else None

    def close(self):
        self.landmarker.close()