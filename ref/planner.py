r"""The planner (docs/plan.md G6): what Quartermaster does with each vanilla path.

Input is the mod index (`ref.index`): for every scanned vanilla path, the mods
that ship a copy of it, in canonical order (`ref.order`), Quartermaster last.
Output is one `Decision` per path that has at least one provider.

Two answers per path, because they are asked for different reasons:

  strategy  what Quartermaster would do if two or more mods shipped the path.
            It depends only on the path and its class in vanilla.idx, so it is
            the same on every machine and can be shown before a conflict exists.
  action    what it does now, with the providers it found: `skip` when one mod
            alone ships the path (the engine's overlay already uses that copy
            and nothing needs to be written), otherwise the strategy.

Strategies, first match wins:

  hook             Quartermaster itself ships the path: one of its hook files
                   (plan S5). Its lines are always merged in, never
                   winner-takes-all, so this holds even with one provider.
  winner           the vanilla file has more than SIZE_CAP_LINES lines (plan
                   S14): the merge would not fit the game side's arrays.
  merge-inc        on the Phase A merge allow-list (plan S3): the `merge` class
                   of vanilla.idx, which tools/hbuild.py assigns to `.inc`
                   files under gui\menu.inc\, gui\common.inc\ and scripts\
                   minus the never-generate list (plan S2).
  merge-data       a data file with a record profile (plan S3, Phase B).
  additive-global  dmscript.global, new names only (plan S3, Phase B).
  winner           everything else: the never-generate list, binaries, every
                   other class, and a class this code does not know. The
                   allow-list decides what is merged; anything not on it is
                   winner-takes-all (plan S2).

`merge-data` and `additive-global` are Phase B. In Phase A they are reported as
`winner` with the reason saying what they will become, so a Phase A report
already names the files Phase B will merge.

`winner` is the last provider in canonical order: the copy the engine's overlay
uses once Quartermaster has put mods.ini into canonical order (plan S11; "same
file in two mods: last in mods.ini wins", docs/research/context-2026-09-27.md
section 3).

The game side (src/states/qmplan.pas) applies the same rules in the same order;
tools/qmtest.py compares its dump line for line with `plan_lines`.
"""

__all__ = ["HOOK_FILES", "PHASE_B_DATA", "ADDITIVE_GLOBAL", "SIZE_CAP_LINES",
           "MERGE_CLASS", "KNOWN_CLASSES", "PHASE_A", "PHASE_B", "SKIP", "HOOK",
           "MERGE_INC", "MERGE_DATA", "ADDITIVE", "WINNER", "Decision",
           "strategy", "decide", "plan", "plan_line", "plan_lines"]

#: The hook files of plan S5, relative to data\, in the spelling of vanilla.idx:
#: CameraControl (primary), InitMinimap (second), DoProgress (last resort),
#: EventMainMenu (the manager button) and OnLanEvent (a client reads the host's
#: settings of `host` scope as the engine hands them over; added 2026-09-29).
#: This is the one list: tools/hbuild.py refuses a hook source for any other
#: file and tools/hrun.py hashes these files before and after every run.
HOOK_FILES = (b"gui\\menu.inc\\cameracontrol.inc",
              b"gui\\menu.inc\\initminimap.inc",
              b"gui\\menu.inc\\doprogress.inc",
              b"gui\\menu.inc\\eventmainmenu.inc",
              b"gui\\menu.inc\\onlanevent.inc")

#: Data files with a record profile (plan S3, Phase B). Their vanilla paths:
#: vanilla.idx lists them under game\var\.
PHASE_B_DATA = (b"game\\var\\objcustom.cfg", b"game\\var\\hotkeys.cfg",
                b"game\\var\\formations.cfg", b"game\\var\\wallcustom.cfg")

#: Merged additive-only in Phase B (plan S3); Quartermaster never ships its own
#: (plan S4).
ADDITIVE_GLOBAL = b"scripts\\dmscript.global"

#: Files over this many lines are winner-takes-all (plan S14).
SIZE_CAP_LINES = 60000

#: The classes tools/hbuild.py writes into vanilla.idx.
MERGE_CLASS = b"merge"
KNOWN_CLASSES = (b"never", b"merge", b"wta")

PHASE_A, PHASE_B = "A", "B"

SKIP, HOOK, MERGE_INC = b"skip", b"hook", b"merge-inc"
MERGE_DATA, ADDITIVE, WINNER = b"merge-data", b"additive-global", b"winner"

#: Reasons, short and fixed: the game side writes the same words.
WHY_HOOK = b"quartermaster-hook"
WHY_SIZE = b"over-size-cap"
WHY_ALLOW = b"merge-allow-list"
WHY_DATA = b"record-profile"
WHY_DATA_A = b"record-profile-phase-b"
WHY_GLOBAL = b"additive-global"
WHY_GLOBAL_A = b"additive-global-phase-b"
#: Phase B: dmscript.global is a global script (plan S17) - two copies never
#: load together (the pre-compile guard and the clash report see to that),
#: so there is no second copy to add into it: the winner's file.
WHY_GLOBAL_B = b"global-script"
WHY_NEVER = b"never-generate"
WHY_BINARY = b"binary"
WHY_WTA = b"not-on-allow-list"
WHY_UNKNOWN = b"unknown-class"


class Decision(object):
    """What the planner decided for one path."""

    __slots__ = ("path", "action", "strategy", "reason", "winner", "providers")

    def __init__(self, path, action, strategy, reason, winner, providers):
        self.path = path
        self.action = action
        self.strategy = strategy
        self.reason = reason
        self.winner = winner
        self.providers = providers

    def __eq__(self, other):
        return isinstance(other, Decision) and all(
            getattr(self, k) == getattr(other, k) for k in self.__slots__)

    def __repr__(self):
        return "Decision(%r, %s/%s, %s, winner=%r)" % (
            self.path, self.action.decode(), self.strategy.decode(),
            self.reason.decode(), self.winner)


def strategy(path, cls, lines, self_provides=False, phase=PHASE_B):
    """`(strategy, reason)` for a vanilla path, whatever its providers.

    `cls` and `lines` are the path's vanilla.idx columns (`lines` is -1 for a
    binary file). `self_provides`: Quartermaster ships this path.
    """
    if self_provides:
        return HOOK, WHY_HOOK
    if lines > SIZE_CAP_LINES:
        return WINNER, WHY_SIZE
    if cls == MERGE_CLASS:
        return MERGE_INC, WHY_ALLOW
    if path in PHASE_B_DATA:
        return (MERGE_DATA, WHY_DATA) if phase == PHASE_B else (WINNER, WHY_DATA_A)
    if path == ADDITIVE_GLOBAL:
        return (WINNER, WHY_GLOBAL_B) if phase == PHASE_B else (WINNER, WHY_GLOBAL_A)
    if lines < 0:
        return WINNER, WHY_BINARY
    if cls == b"never":
        return WINNER, WHY_NEVER
    if cls == b"wta":
        return WINNER, WHY_WTA
    return WINNER, WHY_UNKNOWN


def decide(path, cls, lines, providers, self_dir=None, phase=PHASE_B):
    """The `Decision` for one path, or None when no mod ships it.

    `providers` are mod dirs in canonical order; `self_dir` is Quartermaster's.
    """
    if not providers:
        return None
    self_provides = self_dir is not None and self_dir in providers
    strat, why = strategy(path, cls, lines, self_provides, phase)
    action = strat if (strat == HOOK or len(providers) > 1) else SKIP
    return Decision(path, action, strat, why, providers[-1], list(providers))


def plan(index, entries, self_dir=None, phase=PHASE_B):
    """Decisions for every indexed path with a provider, in vanilla.idx order.

    `index` maps path -> providers (canonical order); `entries` are the
    vanilla.idx rows `(path, size, lines, class)` that were scanned.
    """
    out = []
    for path, _size, lines, cls in entries:
        d = decide(path, cls, lines, index.get(path, []), self_dir, phase)
        if d is not None:
            out.append(d)
    return out


def plan_line(d, position):
    """The dump line of one decision: `plan|path|action|strategy|reason|winner|providers`.

    `position(dir)` gives a provider's canonical position; positions rather
    than dirs keep the line free of anything a mod folder name could contain.
    """
    return b"|".join([b"plan", d.path, d.action, d.strategy, d.reason,
                      b"%d" % position(d.winner),
                      b";".join(b"%d" % position(p) for p in d.providers)])


def plan_lines(decisions, position):
    return [plan_line(d, position) for d in decisions]
