import math
import random

# row, column steps: horizontal, vertical, diagonal down-right, diagonal down-left
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


def grid_size(cells):
    """3 for 9 cells, 4 for 16 cells ... 9 for 81 cells."""
    return math.isqrt(len(cells))


def default_win_len(n):
    """3x3 -> 3; bigger boards -> 5 in a row."""
    return n if n <= 4 else 5


def check_winner(cells, win_len=None):
    """Return (winner, line) or (None, None). line = tuple of cell indexes."""
    n = grid_size(cells)
    win_len = win_len or default_win_len(n)
    for r in range(n):
        for c in range(n):
            p = cells[r * n + c]
            if not p:
                continue
            for dr, dc in DIRECTIONS:
                # only start counting at the beginning of a run
                pr, pc = r - dr, c - dc
                if 0 <= pr < n and 0 <= pc < n and cells[pr * n + pc] == p:
                    continue
                line = []
                rr, cc = r, c
                while 0 <= rr < n and 0 <= cc < n and cells[rr * n + cc] == p:
                    line.append(rr * n + cc)
                    rr += dr
                    cc += dc
                if len(line) >= win_len:
                    return p, tuple(line)
    return None, None


def is_draw(cells, win_len=None):
    return all(cells) and check_winner(cells, win_len)[0] is None


def _wins_with(cells, idx, player, win_len):
    test = cells[:]
    test[idx] = player
    return check_winner(test, win_len)[0] == player


def computer_move(cells, me="O", opponent="X", win_len=None):
    """Win if possible, else block, else center, corner, near marks, random."""
    n = grid_size(cells)
    win_len = win_len or default_win_len(n)
    empty = [i for i, v in enumerate(cells) if v == ""]

    for player in (me, opponent):          # 1) win, 2) block
        for i in empty:
            if _wins_with(cells, i, player, win_len):
                return i

    center = (n // 2) * n + n // 2
    if cells[center] == "":
        return center

    if n <= 4:
        corners = [i for i in (0, n - 1, n * (n - 1), n * n - 1) if cells[i] == ""]
        if corners:
            return random.choice(corners)

    # on bigger boards, play next to existing marks
    near = []
    for i in empty:
        r, c = divmod(i, n)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r + dr, c + dc
                if (dr or dc) and 0 <= rr < n and 0 <= cc < n and cells[rr * n + cc]:
                    near.append(i)
                    break
            else:
                continue
            break
    return random.choice(near or empty)