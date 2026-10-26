"""Makes the RESTART and HOME buttons work during a game.
Run once from the project folder (the one with main.py):
    python patch_buttons.py
"""
import os
import shutil
import sys

PATH = os.path.join("src", "game_state.py")
OLD = 'target = r.cell_at(px, py) if has else None'
NEW = '''btn = r.target_at(r.play_targets, px, py) if has else None
        if btn:                      # finger is on RESTART or HOME
            picked = self.gesture.update(btn)
            if picked == "restart":
                self.reset()
                self.state = "playing"
                self.gesture.dwell_time = 1.2
            elif picked == "menu":
                self.go_home()
            return btn
        target = r.cell_at(px, py) if has else None'''

if not os.path.exists(PATH):
    print(f"Cannot find {PATH}. Run this from the folder that contains main.py")
    sys.exit(1)
with open(PATH, encoding="utf-8") as f:
    s = f.read()
if "play_targets" in s:
    print("Already patched.")
    sys.exit(0)
if s.count(OLD) != 1:
    print(f"ERROR: expected 1 match but found {s.count(OLD)}. Nothing changed.")
    sys.exit(1)
shutil.copy(PATH, PATH + ".bak3")
with open(PATH, "w", encoding="utf-8") as f:
    f.write(s.replace(OLD, NEW))
print("Patched src/game_state.py (backup: src/game_state.py.bak3)")
print("Done! Now run:  python main.py")