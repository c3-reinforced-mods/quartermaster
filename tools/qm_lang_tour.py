"""Run: Quartermaster's window in the languages of the game, one picture per view.

    cd <the Core worktree> && python tools/pathrun.py <this file> --yes
    QM_TOUR=pl,de,fr   the languages to show (default: every language of the game)

A run of the kit of Reinforced - Core (tools/pathrun.py, tools/scenario.py): it starts the game, switches the
language the way a player does (Settings, the list of languages, Accept), opens the window from the button of the
main menu, and takes a picture of the lists, the report, the New mod dialog and the Options view of a mod, then
puts the language back. The pictures land in dist/perf/<stamp>/ of that worktree as <language>-<n>-<view>-full.png.

The candidate stands in mods\\Quartermaster (tools/hbuild.py --deploy); the run plays with it in the place of the
Workshop copy, so the list of the mods it composes names that folder.
"""
import os
import subprocess
import time

import build
import pathrun
import scenario

CORE_RUNS = os.environ.get("QM_CORE_RUNS", r"C:\Projects\Cossacks 3\core-wt\main\runs")


def sibling(name):
    """The module of a run file of the Core worktree: its helpers were proved in the game by its own runs."""
    return pathrun.load(os.path.join(CORE_RUNS, name))[1]


LT = sibling("lang-tour.py")             # the language list's first row, the language put back
QS = sibling("qm-settings.py")           # the window of Quartermaster: open, pick a row, Options, close
P179 = LT.P179
p006 = LT.p006
# the languages Core adds (Hungarian, Dutch, Chinese, Japanese, Korean) are no folder of the game's own eleven
for extra in ("hu", "nl", "zh", "ja", "ko"):
    if extra not in P179.KNOWN:
        P179.KNOWN = tuple(P179.KNOWN) + (extra,)
LABEL = "qm-lang-tour"
STATES = []

# Quartermaster's candidate and LAN from the Workshop, and the patch (last: UPATCH_FAMILY=core takes the last)
NO_QM = bool(os.environ.get("QM_TOUR_NOQM"))        # without Quartermaster: the menu as the game and Core draw it
scenario.FAMILY = (scenario.WORKSHOP + "3812736237",) + (() if NO_QM else ("mods\\Quartermaster",)) + ("mods\\" + build.MOD_NAME,)


WIDE = ("zh", "ja", "ko")                 # drawn from wide fonts: read from resource.lib at the start of the game only


def game_pids():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq cossacks.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    return {line.split(",")[1].strip('"') for line in out.splitlines() if line.lower().startswith('"cossacks.exe"')}


def restart_game(r, code):
    """The game restarted the way Quartermaster restarts it (LanShutdown, SteamwrapFree, RestartApplicationParam), through the
    link's `compile` op, so that the wide fonts a language of Core needs are read from resource.lib; the link then starts again."""
    path = os.path.join(scenario.SAVE, "upatch_scenario", "qmlang_restart.aix")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [b"section.begin", b"   Name = QmLangRestart", b"   UsedFileName = ", b"   Code : struct.begin",
             b"      [*] = ;Log('[qm] restart: language tour, LanShutdown, SteamwrapFree, RestartApplicationParam');",
             b"      [*] = ;LanShutdown;", b"      [*] = ;SteamwrapFree;", b"      [*] = ;RestartApplicationParam('');",
             b"   struct.end", b"section.end", b"",
             b"section.begin", b"   CurrentState = ", b"   SaveVariables = False", b"section.end", b""]
    with open(path, "wb") as fh:
        fh.write(b"\r\n".join(lines))
    old = game_pids()
    try:
        r.link.send("compile", path, "QmLangRestart", timeout=8)
    except Exception as exc:                                  # noqa: BLE001 - the game goes away before it answers
        r.event("restart_sent", lang=code, note=repr(exc))
    deadline = time.time() + 240
    while time.time() < deadline:
        now = game_pids()
        if now and not (now & old):
            break
        time.sleep(2)
    else:
        raise scenario.Failed("the game did not restart within 240 s")
    with open(path, "rb"):
        pass
    r.link.open()
    got = None
    deadline = time.time() + 240
    while time.time() < deadline and got is None:
        try:
            got = r.link.send("hello", timeout=6)
        except Exception:                                     # noqa: BLE001 - not up yet
            time.sleep(3)
    if got is None:
        raise scenario.Failed("the restarted game did not answer hello")
    if not pathrun.wait_seen(r, "MainMenu", "bsettings", 180):
        raise scenario.Failed("the restarted game shows no main menu")
    r.event("restarted", lang=code, old=sorted(old), new=sorted(game_pids()))


def codes():
    text = os.environ.get("QM_TOUR", "")
    wanted = [c for c in text.replace(";", ",").split(",") if c.strip()] or list(P179.KNOWN)
    return [c.strip().lower() for c in wanted if c.strip().lower() in P179.KNOWN]


def to_panel(r, ev, name, want, tries=4):
    """The window pressed on `name` until its panel (qm_ui `panel`) reads `want`: a click that lands while the window redraws is lost."""
    for _ in range(tries):
        if QS.ui_int(r, "panel") == want:
            return True
        QS.press(r, ev, QS.ROOT, name)
        r.sleep(1.2)
    return QS.ui_int(r, "panel") == want


def views(r, code):
    """The window in the language the game has now: the lists, the report, New mod, the Options of Core."""
    ev = {}
    QS.to_main_menu(r)
    pathrun.full(r, "%s-0-menu" % code)
    if NO_QM:
        return
    QS.open_window(r, ev)
    r.sleep(1.0)
    to_panel(r, ev, "breport", 0)
    pathrun.full(r, "%s-1-lists" % code)
    if not to_panel(r, ev, "breport", 1):
        raise scenario.Failed("the Report view did not open (panel %r)" % QS.ui(r, "panel"))
    pathrun.full(r, "%s-2-report" % code)
    if not to_panel(r, ev, "breport", 0):
        raise scenario.Failed("the lists did not come back from the Report view (panel %r)" % QS.ui(r, "panel"))
    QS.press(r, ev, QS.ROOT, "bnewmod")
    r.sleep(1.2)
    if QS.ui_int(r, "mode") not in (4, 5) and not QS.pathrun.seen(r, QS.ROOT, "bnmcancel"):
        QS.press(r, ev, QS.ROOT, "bnewmod")
        r.sleep(1.2)
    pathrun.full(r, "%s-3-newmod" % code)
    QS.press(r, ev, QS.ROOT, "bnmcancel")
    r.sleep(1.0)
    QS.reach_options(r, ev, "clock")
    r.sleep(0.6)
    pathrun.full(r, "%s-4-options" % code)
    QS.press(r, ev, QS.ROOT, "bocan")
    r.sleep(0.6)
    QS.close_window(r, ev)
    r.event("qm_views", lang=code, **ev)


def run(r):
    shown = codes()
    state = {"original": None, "touched": False, "code": shown[0] if shown else "pl"}
    r.event("plan", langs=shown)
    try:
        LT.P155.tolerate_unread(r)
        ok, state["original"] = p006.step(r, LABEL, "remember the language", P179.remember_language, r)
        if not ok:
            state["original"] = None
        p006.step(r, LABEL, "the main menu", p006.recover, r)
        r.do_pick_item = lambda root, name, value: LT.pick_item(r, root, name, value)
        for code in shown:
            now, _profile = P179.reported(r)
            if now != code:
                if state["original"] is None:
                    r.event("failed", lang=code, step="the language at the start is not known: none is switched")
                    break
                state["touched"] = True
                state["code"] = code
                done, _ = p006.step(r, LABEL, "switch to " + code, P179.switch, r, P179.value_of(code), code + "-switch")
                if not done:
                    continue
                if code in WIDE:
                    ok_restart, _ = p006.step(r, LABEL, "restart for " + code, restart_game, r, code)
                    if not ok_restart:
                        continue
            p006.step(r, LABEL, "the window in " + code, views, r, code)
    finally:
        if hasattr(r, "do_pick_item"):
            del r.do_pick_item
        LT.restore(r, state)
        pathrun.errors(r, LABEL)
