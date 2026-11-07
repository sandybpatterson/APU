"""APU v0 -- a first, simple practice-match player for Pokemon Unite.

Eyes: LDPlayer window copy (foodstreet-bot/flash.py, ~0.13 s per look).
Hands: one persistent `adb shell` (taps ~0.1-0.3 s), joystick by short held swipes.
Brain v0: walk in a chosen direction, spam basic attack (the game auto-aims), fire moves
and the Unite move on a timer. Saves a frame every SAVE_EVERY s so we can review.

Owner's rule: practice / own play only. Never taps menus, shops or prices -- this loop
only touches the in-match control positions in layout.json.

Usage:  python apu/play.py [seconds] [direction]      direction: up/down/left/right/upright/...
Stop early: create the file APU/STOP (or Ctrl+C).
"""
import json
import math
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, r"C:\Users\trent\foodstreet-bot")
import cv2       # noqa: E402
import flash     # noqa: E402

ADB = r"C:\LDPlayer\LDPlayer9\adb.exe"
DEV = "127.0.0.1:5555"
LAYOUT = os.path.join(HERE, "layout.json")
STOP = os.path.join(ROOT, "STOP")
SAVE_EVERY = 2.0
LOG = os.path.join(ROOT, "play_log.txt")

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0),
        "upright": (1, -1), "upleft": (-1, -1), "downright": (1, 1), "downleft": (-1, 1)}


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8", errors="replace") as f:
        f.write(line + "\n")


class Hands:
    """One open adb shell; commands are fire-and-forget lines."""

    def __init__(self):
        self.p = subprocess.Popen([ADB, "-s", DEV, "shell"], stdin=subprocess.PIPE,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  text=True)
        self.lock = threading.Lock()

    def send(self, cmd):
        with self.lock:
            self.p.stdin.write(cmd + "\n")
            self.p.stdin.flush()

    def tap(self, xy):
        self.send(f"input tap {xy[0]} {xy[1]}")

    def stick(self, centre, d, radius, ms):
        dx, dy = d
        n = math.hypot(dx, dy) or 1
        x2 = int(centre[0] + dx / n * radius)
        y2 = int(centre[1] + dy / n * radius)
        self.send(f"input swipe {centre[0]} {centre[1]} {x2} {y2} {ms}")

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(3)
        except Exception:   # noqa: BLE001
            self.p.kill()


def play(seconds=90, direction="up"):
    lay = json.load(open(LAYOUT, encoding="utf-8"))
    flash.ON = True
    out = os.path.join(ROOT, "recordings", time.strftime("play_%Y%m%d_%H%M%S"))
    os.makedirs(out, exist_ok=True)
    hands = Hands()
    d = DIRS[direction]
    t0 = time.time()
    last = {"save": 0, "m1": 0, "m2": 0, "unite": 0, "move": 0}
    n = 0
    log(f"PLAY start: {seconds}s, direction {direction}, frames -> {out}")
    try:
        while time.time() - t0 < seconds and not os.path.exists(STOP):
            now = time.time()
            img = flash.grab((1600, 900))
            if img is not None and now - last["save"] >= SAVE_EVERY:
                cv2.imwrite(os.path.join(out, f"f{n:03d}_t{int(now - t0):03d}.jpg"), img,
                            [cv2.IMWRITE_JPEG_QUALITY, 70])
                n += 1
                last["save"] = now
            if now - last["move"] >= lay["move_every"]:
                hands.stick(lay["joystick"], d, lay["stick_radius"], lay["move_ms"])
                last["move"] = now
            hands.tap(lay["attack"])
            for k in ("m1", "m2", "unite"):
                if k in lay and now - last[k] >= lay[k + "_every"]:
                    hands.tap(lay[k])
                    last[k] = now
                    log(f"used {k}")
            time.sleep(lay["tick"])
    finally:
        hands.close()
        log(f"PLAY end after {time.time() - t0:.0f}s, {n} frames saved")


if __name__ == "__main__":
    secs = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    play(secs, sys.argv[2] if len(sys.argv) > 2 else "up")
