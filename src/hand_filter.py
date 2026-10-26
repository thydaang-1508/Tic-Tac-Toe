"""Keep only the hand that is allowed to play the current mark.

Rule: RIGHT hand plays "X", LEFT hand plays "O".

Works with the classic MediaPipe Hands API (mp.solutions.hands), where
`results.multi_hand_landmarks` and `results.multi_handedness` are parallel lists.

MediaPipe's Left/Right label is correct from the USER's point of view only when
the image given to MediaPipe is mirrored (selfie view, cv2.flip(frame, 1)).
If you feed the un-flipped camera image, set image_is_mirrored=False and the
labels are swapped for you.
"""

HAND_FOR_MARK = {"X": "Right", "O": "Left"}


def hand_for_mark(mark):
    """'X' -> 'Right', 'O' -> 'Left'."""
    return HAND_FOR_MARK[mark]


def _label(handedness, image_is_mirrored):
    label = handedness.classification[0].label        # "Left" or "Right"
    if image_is_mirrored:
        return label
    return "Left" if label == "Right" else "Right"


def choose_hand(results, mark, image_is_mirrored=True, min_score=0.6):
    """Pick the hand allowed to play `mark`.

    Returns (landmarks, seen_label):
      landmarks   - landmark list of the allowed hand, or None when that hand
                    is not visible (a wrong hand is ignored completely)
      seen_label  - 'Left' / 'Right' of the hand being shown (the allowed hand
                    if visible, otherwise the wrong one), or None if no hand.
                    Pass it to Renderer.draw_game(..., hand=seen_label) so the
                    screen can say "Use your RIGHT hand to play X".
    """
    need = HAND_FOR_MARK[mark]
    hands = getattr(results, "multi_hand_landmarks", None)
    sides = getattr(results, "multi_handedness", None)
    if not hands or not sides:
        return None, None

    wrong = None
    for lm, side in zip(hands, sides):
        if side.classification[0].score < min_score:
            continue
        label = _label(side, image_is_mirrored)
        if label == need:
            return lm, label
        wrong = wrong or label
    return None, wrong