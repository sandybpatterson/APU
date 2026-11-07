# APU -- Auto Pokemon Unite
### For Claude (or a local model): read this first, before writing any code.

Owner: Trenton. Plays Pokemon Unite in **LDPlayer 9** on a Windows PC (machine "WOW3"), the same PC + emulator
that runs the Food Street bot (repo `sandybpatterson/afsd`, folder `foodstreet-bot`). Pokemon Unite is closing
down; this project is for learning / fun. Push straight to `main` (one-person project).

Everything below was LEARNED THE HARD WAY on the Food Street bot (Oct-Nov 2026). Reuse it -- do not rediscover it.
The afsd file named in brackets is working, live-proven code to copy from.

---

## How APU runs: an AFSD extension (11/7, owner's idea)
APU is NOT a separate program. It is loaded by AFSD (the Food Street bot window) as an EXTENSION:
- AFSD Settings > Experimental > "Pokemon Unite" switch -> adds the **Unite!** tab and the **Pokemon Unite** job.
- AFSD's Update clones / pulls this repo into `<afsd>/extensions/APU`; AFSD's Send logs pushes `logs/` here.
- AFSD's bridge is `unite_ext.py` in the afsd repo. It calls this repo's **`apu/ext.py`**:
  `VERSION`, `build_tab(parent, theme)` (Tkinter, theme = bg/fg/dim/card/gold/title/body),
  `run_job(ctx)` with ctx = {log, stop, shell, logs_dir}; `ctx["shell"](cmd)` = `adb shell cmd` on LDPlayer.
  Keep those names/signatures stable -- AFSD on the PC calls them. Put real work in other modules under `apu/`.
- AFSD already has adb, FLASH, fast taps, restarts: when inside AFSD, import them (`adb_helper`, `flash`,
  `fast_input`) instead of copying -- they are on sys.path. Copy only for a stand-alone tool.
- One LDPlayer, two games: while the Unite job really plays, Food Street's own checks must be paused (not built yet).
- Tests: `python -m pytest tests -q` here; AFSD's tests/test_unite.py loads this checkout too.

## 0. Hard rules (never break)
- Never spend Aeos gems, money, or any paid currency; never confirm a purchase; never tap a price.
- New behaviour starts LOG-ONLY: look, decide, log "WOULD press X because Y". It only acts after the logs prove it
  AND the owner says yes.
- Ranked / other players: keep it to the owner's own practice / casual play; human-like pacing.
- Tests: `python -m pytest tests -q` must pass before every push. A fixed bug gets a new test.
- Small files, one job each, pure logic separate from adb/screen code (afsd grew 4,000-line files -- don't).

---

## 1. Connecting to LDPlayer (adb)
- LDPlayer folder: `C:\LDPlayer\LDPlayer9\` -- `adb.exe`, `dnconsole.exe`, `ldconsole.exe` live there.
- Device address: **`127.0.0.1:5555`** (fallback `127.0.0.1:5554`). `adb connect 127.0.0.1:5555`, then
  `adb -s 127.0.0.1:5555 shell ...`. Always pass `-s` (LDPlayer + another adb can both be listed).
- Screenshot: `adb -s DEV exec-out screencap` (RAW, not `-p` PNG: raw ~1.0 s vs PNG ~1.8 s). Raw = 12-byte header
  (w, h, format) then RGBA bytes -> numpy reshape -> drop alpha -> RGB->BGR for OpenCV.
- Tap: `adb shell input tap X Y`; drag: `input swipe X1 Y1 X2 Y2 MS`; Back key: `input keyevent 4`.
- Which app is in front: `adb shell dumpsys window | grep mCurrentFocus` (game vs ad vs Play Store).
- Unite's package: find it with `adb shell pm list packages | grep -i unite` (expected `jp.pokemon.pokemonunite`).
  Start: `adb shell monkey -p <pkg> -c android.intent.category.LAUNCHER 1`; stop: `am force-stop <pkg>`.
- **Resolution matters.** Pick ONE (e.g. 1600x900 landscape, LDPlayer Settings > Advanced) and never change it --
  every coordinate and picture template is tied to it. The Food Street bot lost a morning when LDPlayer came back at
  1920x1080. Check `img.shape` at Start and alarm if it changed. [afsd: afsd_core.screen_size_check]

### adb traps (each cost hours)
- **Never `subprocess.run(..., capture_output=True, timeout=...)` for adb on Windows.** When adb's background server
  holds the pipes, the call hangs FOREVER past its timeout (one tap hung 12 min). Write output to temp files,
  `Popen.wait(timeout)`, kill on timeout. [afsd: adb_resilience.safe_run]
- adb drops out for 20 s - 6 min now and then; most recover by themselves. Hard freeze ("no devices" while LDPlayer
  shows) -> `adb kill-server`, taskkill EVERY adb.exe (LDPlayer runs its own older adb), `adb start-server`,
  `adb connect`. Still dead -> cold restart: `dnconsole quitall`, taskkill dnplayer.exe / Ld9BoxHeadless.exe /
  Ld9BoxSVC.exe, `dnconsole launch --index 0`, wait up to 5 min for `getprop sys.boot_completed` = 1.
  [afsd: afsd_core.adb_hard_reset, hard_restart_emulator, watchdog_restart]
- After the PC sleeps, LDPlayer's network can be broken (game shows an error). Cold restart fixes it.
- Log files: open with `encoding="utf-8", errors="replace"` (Windows cp1252 crashed on one odd OCR character).

---

## 2. Going FAST -- project FLASH (Fast Live Access to Screen History)
adb screenshots are 1-2 s (slower the longer LDPlayer runs). For a real-time game that is far too slow.
**FLASH: copy LDPlayer's own window instead -- ~0.03-0.17 s, 7-30x faster.** [afsd: flash.py, adb_helper.screenshot]
- Find LDPlayer's top window (class `LDPlayerMainFrame`), then its render child (class `RenderWindow`, title
  `TheRender`) -- the child whose shape is closest to the game's 16:9. ctypes only, no extra packages.
- Capture with **`PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT=2)`** into a bitmap. It works even when AFSD's (or any)
  window covers LDPlayer. Screen-copy (BitBlt from the desktop) only sees what is on top -- useless.
- **LDPlayer must not be MINIMISED** (minimised -> no picture). Covered is fine.
- **Windows display scaling (125% etc.) lies about the window size.** Run the capture thread with
  `SetThreadDpiAwarenessContext(PER_MONITOR_AWARE_V2 = -4)`, draw into a bitmap 2x the client size and trim the black
  edge (`trim_black`), then resize to your fixed working size (1600x900). Readers then work unchanged.
- Check every copy: not black, right aspect (+-4%). Bad -> fall back to adb for that look.
- **FROZEN FRAME GUARD**: LDPlayer sometimes stops repainting -> the window copy returns the same old picture forever
  (the Food Street bot was blind 6 h). If the copy hasn't changed at all for 20 s, take one adb shot; if adb differs a
  lot, use adb only for 10 min. [afsd: flash.stale_step / stale_verdict / note_adb]
- Wait ~0.4 s after a tap before trusting a window copy (adb's own slowness used to hide the animation delay).

### Fast taps [afsd: fast_input.py]
- A new `adb shell input tap` process costs ~0.6 s. Keep ONE `adb -s DEV shell` open (Popen, reader thread) and write
  `input tap X Y; echo __OK_n__` lines into it -> ~0.3 s per tap, and you still know when it finished.
- Once a line is sent, never "retry the old way" -- a double tap can hit the wrong button.
- For real-time play even that is slow. Faster options to TEST (log timings first):
  1. `adb shell sendevent` / write raw touch events to `/dev/input/eventN` (no `input` startup cost).
  2. **LDPlayer key mapping (best for Unite):** LDPlayer turns PC keys/mouse into touches itself, with ~no delay.
     Send key presses to the LDPlayer window (Win32 `PostMessage WM_KEYDOWN/WM_KEYUP` to the render window, or
     `SendInput` while it has focus) and LDPlayer presses Q/W/E/1/2/3 etc. for us. **adb input does NOT go through
     the key mapping** -- adb taps must hit the screen spot directly.
- "Look until it happened" instead of fixed sleeps: poll fast window copies until the screen changes / settles
  (max N s). Fixed sleeps were 44% of the Food Street bot's time before this. [afsd: event_orders.wait_for, _settle]

---

## 3. Pokemon Unite controls in LDPlayer (owner, 11/7)
- The owner uses LDPlayer's **key mapping for Unite**: keys **Q W E** (moves / unite move), **1 2 3** (items /
  battle item / etc.), **right-click to move** (MOBA style), probably more (recall, score, ping). The exact layout is
  in LDPlayer's Keyboard Mapping panel -- ask the owner for a screenshot of it and write the table here.
- **The bot can SEE the mapping**: LDPlayer draws the key letters (Q, W, E, 1, 2, 3 ...) over the buttons in its window.
  These hint letters show up in the **window copy (FLASH)** but NOT in adb screenshots (seen on the Food Street bot
  11/1: letters O, P, L, M on the icons). So from one window copy the bot can locate every mapped button: find the
  letter glyphs (template-match each letter, or OCR) -> button centre = tap spot. Save that table to a json file.
- Movement without key mapping: adb drag on the on-screen joystick (bottom-left), short swipes held ~200-400 ms.
- Real-time loop goal: window copy (0.03-0.17 s) -> decide -> key press via LDPlayer mapping (~instant). adb only as
  backup and for menus.

---

## 4. Recording the owner (how the bot learns)
[afsd: ad_skip.TapWatcher / record_session, "Let Me Play" button; apmtcg repo has a cleaned-up copy: apmtcg/record.py,
apmtcg/touch.py with a pure, tested TouchParser]
- `adb shell -tt getevent -lt <touch device>` streams the owner's touches line-buffered (without `-tt` the lines sit
  in a pipe buffer and arrive minutes late). Find the touch device + its range with `getevent -lp` (do not hard-code).
- **getevent gives RAW panel coordinates.** Scale them to the screenshot size. If the screen is rotated (portrait app
  on a landscape panel), rotate: portrait (x, y) = (H - raw_y, raw_x). Check against a picture before trusting.
- Key-mapped key presses reach Android as touches injected by LDPlayer, so getevent SHOULD see them (at the mapped
  button's spot) -- verify on the first recording; if not, also log PC key presses on the Windows side.
- Per touch save: before-picture, marked before-picture (red circle / arrow), after-picture, and a line in
  `lessons.jsonl` {n, t, kind tap|drag, x, y, x2, y2, screen = 8x8 hash, pre, post}. Plus half-size frames whenever
  the screen changes. Send = commit + push the recording folder to GitHub (max ~8 MB per push; only NEW files).

---

## 5. Seeing the screen (picture tricks that worked)
- Template matching (`cv2.matchTemplate`, TM_CCOEFF_NORMED) on a SMALL region, at half size for speed; always test a
  template on 100+ saved screens: it must find its screen and NOT the others, and write the scores in the notes.
- Numbers: cut the game's own digit shapes from screenshots and match glyphs; Windows OCR (`ocr_image.ps1`, 1-3 s)
  only as a backup for words. [afsd: stock_digits.py, coin_digits.py]
- A red-X / close button found by template = the safe way out of any popup. Unknown popup -> picture + Back key.
- "Stuck" detector: same covered screen for 5 min -> ladder: Back key -> known close button -> restart game ->
  restart LDPlayer. [afsd: unstuck.py, no_progress.py]

---

## 6. Plan to build APU (in order; each step log-only first)
1. `apu/adb.py` (safe_run, screenshot raw, device connect), `apu/flash.py` (window copy + frozen guard),
   `apu/fast_input.py`, `apu/log.py`, `apu/config.py`. Speed log line: looks/s and ms per look, taps.
2. Key-map reader: one window copy of a match -> find the LDPlayer hint letters -> `keymap.json` (letter -> x, y).
3. Recorder + Send (copy apmtcg's), owner plays 2-3 matches.
4. Name the screens from the recordings: lobby, character select, loading, in-match, result, popups. Templates +
   tests that each finds only its own screen.
5. In-match reading (log-only): own HP bar, skill cooldowns (greyed buttons), minimap position, score.
6. Lobby automation first (start a practice / quick match, accept, pick the character, collect rewards) -- menus are
   slow and safe. In-match play last.

## Log
- 11/7 repo created (owner). These notes written from the Food Street bot's experience.
- 11/7 v0.1: apu/ext.py -- empty "coming soon" tab + LOG-ONLY job (logs which app is in front to AFSD's log and
  logs/unite_log.txt). tests/test_ext.py. Unite's real package name: read it from the first job log line.
- 11/6 night (Claude, live with owner): first practice-match player built and run 4x (Venusaur vs Alolan Raichu bot).
  `apu/play.py` (window copy eyes via foodstreet-bot/flash.py with flash.ON=True; persistent adb shell, drops a
  command when >0.5 s behind -- an earlier version queued minutes of taps that kept firing after the match),
  `apu/minimap.py` (own marker = Hough circle with BLUE rim, enemy = red/orange rim, filled goal circles skipped;
  bright orange = active enemy score zone, yellow dots = NPCs; 230/239 replay frames tracked), `apu/nav.py` (lane
  waypoints H-M-T1..T5-E / B1..B5; T4/B4 front zones), `apu/layout.json` (1600x900 taps: attack 1450,770; moves
  1280,600 / 1180,780; potion 1050,670; To Base 820,770 held 4.5 s; unite 1450,540). Score = HOLD attack on the zone.
  Results: levels up to 6-10 and farms, 0 scores yet (marker tracking was the bug; fixed but untested live). HP bar
  reader is unreliable at low level. Owner's game rules: cat-face markers = bosses (team bonus); NPCs show a gold
  pokeball number + red bar; score only at the closest zone, not with enemies near; being hit interrupts scoring;
  more points = longer hold; heal in tall grass via To Base (hold 4 s), blue jump pads, or own score circles.
