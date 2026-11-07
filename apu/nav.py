"""Lane waypoints on the minimap (1600x900 frame coords). Walk node to node, never straight through walls.
Top lane: H M T1..T5 E ; bottom lane: H M B1..B5 E. T4/B4 = front enemy score zones, T5/B5 = back ones."""
import math

N = {"H": (37, 177), "M": (85, 181),
     "T1": (127, 123), "T2": (185, 101), "T3": (227, 87), "T4": (267, 100), "T5": (322, 123),
     "B1": (127, 239), "B2": (189, 260), "B3": (225, 277), "B4": (260, 262), "B5": (322, 239),
     "E": (365, 180)}
LANE = {"top": ["H", "M", "T1", "T2", "T3", "T4", "T5", "E"],
        "bot": ["H", "M", "B1", "B2", "B3", "B4", "B5", "E"]}


def lane_of(me):
    return "top" if me[1] < 181 else "bot"


def step_toward(me, lane, target):
    """Next waypoint (x, y) on `lane` going from `me` toward node `target`."""
    seq = LANE[lane]
    i = min(range(len(seq)), key=lambda k: math.dist(N[seq[k]], me))
    j = seq.index(target)
    if i == j:
        return N[target]
    nxt = i + (1 if j > i else -1)
    # already at node i? head to the next one; otherwise first reach node i
    return N[seq[nxt]] if math.dist(N[seq[i]], me) < 12 else N[seq[i]]


def active_zone(lane, goals):
    """Closest still-active (bright orange) enemy score zone on this lane, front first."""
    for k in (["T4", "T5"] if lane == "top" else ["B4", "B5"]):
        if any(math.dist(N[k], g) < 18 for g in goals):
            return k
    return "T5" if lane == "top" else "B5"
