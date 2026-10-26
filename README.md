# Gesture Tic-Tac-Toe

A computer-vision-based Tic-Tac-Toe game that allows players to interact using hand gestures instead of a mouse or keyboard.

The game uses:

- OpenCV for camera processing
- MediaPipe for hand tracking
- NumPy for image operations
- Gesture-based controls
- Real-time game rendering

---

## Features

### Hand Gesture Control
- Tracks player hands using MediaPipe.
- Detects finger positions in real time.
- Uses hover and dwell gestures to select cells.
- No mouse or keyboard required during gameplay.

### Adjustable Tic-Tac-Toe Board
- Choose a 3×3, 9×9, or 12×12 board.
- Five consecutive symbols required to win on larger boards.
- Supports horizontal, vertical, and diagonal victories.

### Player Management
- Player X and Player O.
- Turn-based gameplay.
- Automatic turn switching.

### Interactive UI
- Animated game board.
- Visual selection indicators.
- Progress feedback during gesture selection.
- Home screen interface.

### Avatar System
- Select player avatars.
- Display avatars during gameplay.
- Visual player identification.

### Dynamic Background
- Anime-style background.
- Decorative animated effects.
- Improved visual experience.

### Score Tracking
- Track player victories.
- Restart game at any time.
- Reset board functionality.

---

## Project Structure

```text
gesture-tic-tac-toe/
│
├── main.py
├── requirements.txt
├── README.md
│
├── src/
│   ├── camera.py
│   ├── hand_tracker.py
│   ├── gesture_detector.py
│   ├── board.py
│   ├── game_rules.py
│   ├── turn_manager.py
│   ├── score_manager.py
│   ├── game_state.py
│   ├── renderer.py
│   ├── audio_manager.py
│   └── config.py
│
├── assets/
│   ├── images/
│   ├── icons/
│   ├── sounds/
│   └── fonts/
│
├── tests/
│   ├── test_board.py
│   ├── test_rules.py
│   ├── test_gesture.py
│   └── test_score.py
│
└── docs/
    └── project-requirements.docx
```

---

## Requirements

- Python 3.10+
- Webcam
- Windows 10/11

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Dependencies

```text
opencv-python
mediapipe
numpy
```

---

## How to Run

Navigate to the project folder:

```bash
cd gesture-tic-tac-toe
```

Run the game:

```bash
python main.py
```

---

## How to Play

### Player X
- Uses the right hand.
- Move index finger over a cell.
- Hold position until the dwell timer completes.
- The symbol is placed automatically.

### Player O
- Uses the left hand.
- Follow the same selection process.

### Winning Condition

A player wins by placing:

```text
5 consecutive symbols
```

in:

- Horizontal direction
- Vertical direction
- Diagonal direction

on the 9×9 board.

---

## Technologies Used

| Technology | Purpose |
|------------|----------|
| OpenCV | Camera input and rendering |
| MediaPipe | Hand tracking |
| NumPy | Image processing |
| Python | Game logic |

---

## Future Improvements

- Sound effects
- Multiplayer networking
- AI opponent
- Difficulty levels
- Additional gesture controls
- Custom themes
- Database score saving

---

## Author

Developed as a Computer Vision and Gesture Recognition Game Project using Python, OpenCV, and MediaPipe.

---

## License

This project is intended for educational and research purposes.