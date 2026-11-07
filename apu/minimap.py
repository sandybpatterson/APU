"""Read the top-left minimap: own marker (blue ring), enemy goals (bright orange), NPC dots (yellow)."""
import cv2
import numpy as np

MM = (0, 40, 460, 320)          # x1, y1, x2, y2 on the 1600x900 frame


def _blobs(mask, amin, amax):
    n, _l, st, cen = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    return [(cen[i][0], cen[i][1], st[i][4]) for i in range(1, n) if amin <= st[i][4] <= amax]


def read(img, prev=None):
    x1, y1, x2, y2 = MM
    hsv = cv2.cvtColor(img[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    blue = (h >= 95) & (h <= 118) & (s > 120) & (v > 150)
    cands = _blobs(blue, 100, 800)
    if prev is not None and cands:
        px, py = prev[0] - x1, prev[1] - y1
        near = [b for b in cands if (b[0] - px) ** 2 + (b[1] - py) ** 2 < 90 ** 2]
        cands = near or cands
    me = max(cands, key=lambda b: b[2], default=None)
    goals = _blobs((h >= 6) & (h <= 20) & (s > 150) & (v > 200), 120, 900)
    npcs = _blobs((h >= 21) & (h <= 34) & (s > 80) & (s < 210) & (v > 160), 15, 140)
    red = ((h <= 5) | (h >= 172)) & (s > 150) & (v > 150)
    enemies = _blobs(red, 60, 900)
    off = lambda b: (b[0] + x1, b[1] + y1)
    return (off(me) if me else None), [off(b) for b in goals], [off(b) for b in npcs], [off(b) for b in enemies]
