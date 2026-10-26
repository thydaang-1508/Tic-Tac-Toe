import copy
import json
import os

MAX_NAME = 12
PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "profile.json")
)
DEFAULT = {
    "name": "",
    "avatar": 0,
    "stats": {"wins": 0, "losses": 0, "draws": 0},
}


class Profile:
    def __init__(self):
        self.data = copy.deepcopy(DEFAULT)
        self.load()

    # ---------- storage ----------
    def load(self):
        try:
            with open(PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved.get("name"), str):
                self.data["name"] = saved["name"][:MAX_NAME]
            if isinstance(saved.get("avatar"), int):
                self.data["avatar"] = saved["avatar"]
            if isinstance(saved.get("stats"), dict):
                self.data["stats"].update(saved["stats"])
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            os.makedirs(os.path.dirname(PATH), exist_ok=True)
            with open(PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except OSError as e:
            print("Could not save profile:", e)

    # ---------- accessors ----------
    @property
    def name(self):
        return str(self.data["name"])

    @name.setter
    def name(self, value):
        self.data["name"] = value.strip()[:MAX_NAME]

    @property
    def avatar(self):
        return int(self.data["avatar"])

    @avatar.setter
    def avatar(self, value):
        self.data["avatar"] = int(value)

    @property
    def stats(self):
        return self.data["stats"]

    def record(self, result):
        """result: 'win', 'loss' or 'draw'."""
        key = {"win": "wins", "loss": "losses", "draw": "draws"}[result]
        self.data["stats"][key] = self.data["stats"].get(key, 0) + 1
        self.save()