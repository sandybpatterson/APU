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
import minimap   # noqa: E402

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
        self.busy_until = 0.0

    def send(self, cmd):
        # Never build a backlog: the device runs commands one by one (tap ~0.15 s, swipe = its ms).
        # If the queue is already >0.5 s behind, drop this command instead of queueing it.
        now = time.time()
        if self.busy_until - now > 0.5:
            return
        cost = int(cmd.split()[-1]) / 1000 + 0.1 if cmd.startswith("input swipe") else 0.15
        self.busy_until = max(now, self.busy_until) + cost
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
            self.p.kill()
        except Exception:   # noqa: BLE001
            pass
        # the device-side shell can outlive the local process: kill any input still queued there
        subprocess.run([ADB, "-s", DEV, "shell", "pkill -9 -f 'input (tap|swipe)'; "
                        "for p in $(pgrep -x sh); do [ $p != $$ ] && kill -9 $p; done"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)


def hp_frac(img, box):
    """Own HP bar over the player's head: its height moves with the name label, so search a band
    (box = x1, y1, x2, y2 of that band) for the greenest row and measure its filled share."""
    x1, y1, x2, y2 = box
    hsv = cv2.cvtColor(img[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    g = (hsv[..., 0] > 35) & (hsv[..., 0] < 85) & (hsv[..., 1] > 120) & (hsv[..., 2] > 120)
    row = g.sum(axis=1).argmax()
    cols = g[max(0, row - 2):row + 3].any(axis=0)
    return cols.sum() / 122.0


def orange_frac(img, box):
    """Enemy goal zones are orange; share of strong orange around the player."""
    x1, y1, x2, y2 = box
    hsv = cv2.cvtColor(img[y1:y2, x1:x2], cv2.COLOR_BGR2HSV)
    return ((hsv[..., 0] > 8) & (hsv[..., 0] < 22) & (hsv[..., 1] > 170) & (hsv[..., 2] > 170)).mean()


def play(seconds=90, direction="up"):
    lay = json.load(open(LAYOUT, encoding="utf-8"))
    flash.ON = True
    out = os.path.join(ROOT, "recordings", time.strftime("play_%Y%m%d_%H%M%S"))
    os.makedirs(out, exist_ok=True)
    hands = Hands()
    d = DIRS[direction]
    t0 = time.time()
    last = {"save": 0, "m1": 0, "m2": 0, "unite": 0, "move": 0, "potion": 0, "base": 0, "log": 0}
    hold_until = side_until = 0
    last_score = time.time()
    hp_hist = [1.0] * 8
    prev_me = (40, 180)
    stuck = {"pos": (0, 0), "t": time.time()}
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
            hp, org = 1.0, 0.0
            if img is not None:
                hp, org = hp_frac(img, lay["hp_box"]), orange_frac(img, lay["goal_box"])
                if now - last["log"] >= 3:
                    log(f"hp {hp:.2f} orange {org:.3f}")
                    last["log"] = now
            # HEAL: potion at half HP, recall to base when really low
            if hp < lay["hp_potion"] and now - last["potion"] > 10:
                hands.tap(lay["potion"]); last["potion"] = now; log(f"HEAL potion (hp {hp:.2f})")
            if hp < lay["hp_base"] and now - last["base"] > 20:
                tb = lay["to_base"]
                hands.stick(lay["joystick"], (-1, 0), lay["stick_radius"], 1500)
                hands.send(f"input swipe {tb[0]} {tb[1]} {tb[0]} {tb[1]} 4500")
                last["base"] = now; hold_until = now + 7
                log(f"HEAL: low hp {hp:.2f} -- stepping back, holding To Base 4.5 s")
            # STEER by the minimap: farm NPC dots, every FARM_SEC go score at the nearest front goal
            if img is not None:
                me, goals, npcs, foes = minimap.read(img, prev_me)
                prev_me = me or prev_me
                foe_near = any(math.dist(f, me) < lay['foe_near'] for f in foes) if me else False
                hurt = hp < hp_hist[0] - 0.08
                hp_hist = hp_hist[1:] + [hp]
                if me:
                    mode = "score" if now - last_score >= lay["farm_sec"] and goals else "farm"
                    pool = goals if mode == "score" else [p for p in npcs if math.dist(p, me) > 6]
                    if pool:
                        tgt = min(pool, key=lambda p: math.dist(p, me))
                        d = (tgt[0] - me[0], tgt[1] - me[1])
                        if mode == "score" and math.dist(tgt, me) < lay["goal_near"] and now >= hold_until and (foe_near or hurt):
                            if now - last["log"] >= 3:
                                log(f"NOT scoring: {'enemy near' if foe_near else 'being hit'}")
                        elif mode == "score" and math.dist(tgt, me) < lay["goal_near"] and now >= hold_until:
                            hold_until = now + lay["score_sec"]; last_score = now
                            a = lay["attack"]
                            hands.send(f"input swipe {a[0]} {a[1]} {a[0]} {a[1]} {int(lay['score_sec'] * 1000) - 300}")
                            log(f"SCORE: at the goal {tuple(int(a) for a in tgt)}, holding the score button")
                    # STUCK: marker hasn't moved for 3 s -> sidestep
                    if math.dist(me, stuck["pos"]) > 3:
                        stuck.update(pos=me, t=now)
                    elif now - stuck["t"] > 3 and now > side_until:
                        side_until = now + 1.5; stuck["t"] = now
                        log(f"STUCK at {tuple(int(a) for a in me)} -- sidestepping")
                    if now < side_until:
                        d = (-d[1], d[0])
            if now < hold_until:
                time.sleep(lay["tick"]); continue
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
