"""The entry points AFSD calls (through AFSD's unite_ext.py). Keep this file small; real work goes in its own modules.

  VERSION                  shown on the Unite! tab and in AFSD's log
  build_tab(parent, theme) draws the Unite! tab (theme: bg, fg, dim, card, gold, title, body fonts)
  run_job(ctx)             one turn of the "Pokemon Unite" job; ctx = {log, stop, shell, logs_dir}
                           ctx["shell"](cmd) runs `adb shell <cmd>` on LDPlayer and returns its text

LOG-ONLY for now (CLAUDE.md rule): it only looks and writes what it saw. Nothing is tapped.
"""
import os
import time

VERSION = "0.1 (11/7: empty tab + log-only job)"
UNITE_HINTS = ("pokemonunite", "unite")          # package-name pieces; confirm the real one from the log


def front_app(focus_line):
    """Pure: the package in front from `dumpsys window | grep mCurrentFocus`, or ''."""
    s = focus_line or ""
    if "/" not in s:
        return ""
    left = s.split("/", 1)[0]
    return left.split()[-1].strip("{}") if left.split() else ""


def is_unite(pkg):
    p = (pkg or "").lower()
    return any(h in p for h in UNITE_HINTS)


def _write(logs_dir, line):
    try:
        os.makedirs(logs_dir, exist_ok=True)
        with open(os.path.join(logs_dir, "unite_log.txt"), "a", encoding="utf-8", errors="replace") as f:
            f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {line}\n")
    except OSError:
        pass


def run_job(ctx):
    log = ctx.get("log") or (lambda m: None)
    try:
        focus = ctx["shell"]("dumpsys window | grep mCurrentFocus")
    except Exception as e:                       # noqa: BLE001
        focus = f"? ({e!r})"
    pkg = front_app(focus)
    line = (f"job turn: in front = {pkg or 'unknown'} -- "
            + ("Pokemon Unite is open. Nothing to do yet (log-only)." if is_unite(pkg)
               else "Pokemon Unite is not in front. Nothing to do yet (log-only)."))
    _write(ctx.get("logs_dir", "logs"), line)
    log(f"[unite] {line}")
    return "logged"


def build_tab(parent, theme):
    import tkinter as tk
    bg = theme.get("bg", "#1e1e1e")
    tk.Label(parent, text="Pokémon Unite", font=theme.get("title"), bg=bg, fg=theme.get("fg", "#eeeeee")).pack(pady=(40, 6))
    tk.Label(parent, text=f"Coming soon. Extension version {VERSION}.\n"
                          "Tick the 'Pokémon Unite' job to see what it notices in AFSD's log.",
             font=theme.get("body"), bg=bg, fg=theme.get("dim", "#999999"), justify="center").pack()
