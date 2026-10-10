r"""The boot's decisions (docs/plan.md G14, S8, S13): the twin of the game-side
states qmGuard (src/states/qmguard.pas), qmMarkerLoad / qmMarkerSave
(qmmarker*.pas), qmKnown (qmknown.pas) and qmTick (qmtick.pas).

Quartermaster must regenerate only when its inputs changed, restart at most
once per change and never loop (plan S8). Everything that decides that is a
pure function here, so every path - the I5 loop included - is tested offline
and the game side is checked against it line for line.

The start marker, <save>\quartermaster\state.cfg
------------------------------------------------
Plan S8 names four fields: `gen, hash, written|booted, autoRestarts`. The
file is the shape of a one-state `.inc` in the engine's layout
(ref/inc.py layout_lines), written by the game's raw writer (CRLF, padded to
a whole Integer) and read back with the engine's parser - the same shape as
M4's manifest and vanilla.idx, and the one the parser was seen to load after
the raw writer made it (SelfTest run m2a3, the synthetic incprobe file):

    section.begin
       Name = qmState
       Code : struct.begin
          [*] = ;format|1
          [*] = ;gen|<N>            generation of the outputs on disk (0: none)
          [*] = ;hash|<fp>          fingerprint they were generated for (- none)
          [*] = ;phase|<phase>      written, booting or booted (below)
          [*] = ;mode|<mode>        normal, or wta: the fallback after a
                                    suspected brick (no merges at all)
          [*] = ;rows|<k>           automatic restarts in a row
          [*] = ;rhash|<fp>         fingerprint of the last automatic restart
          [*] = ;rcount|<k>         automatic restarts for rhash
          [*] = ;rk|<kind>          the restart that ended the previous life:
                                    auto, apply, test, or - for none
          [*] = ;boots|<n>          boots so far (evidence; the I5 test salt)
          [*] = ;out|<path>|<age>   one per current output: FileAge after the
                                    generation, as text (paths relative to
                                    <QmDir>\data\, vanilla.idx spelling)
       struct.end
    section.end

A file without `format|1` is not a marker (a first boot). Values are plain
ASCII and carry no trailing space, so the parser's one loss (trailing spaces,
run m2a) cannot touch them.

Phases. S8 has `written` before the restart and `booted` set by the first
hook of the next start, and calls `written` without `booted` a suspected
brick. Seen from inside, the first start after a write always finds
`written`, so one more step is needed to tell a start that worked from one
that did not:
    written   the outputs of generation N are on disk, not yet loaded by a
              start of the game;
    booting   a start found `written` and booted (its first hook ran); set
              by the boot;
    booted    that start reached the main menu's first frame (qmTick, from
              the DoProgress hook); set by the tick.
A boot that finds `booting` knows the previous start began with generation
N's files but never reached the menu: a suspected brick of N (plan S8). It
does not regenerate the same hash normally but falls back to winner takes
all (`wta`: no merged file at all, the hook files as winner+hook or
vanilla+hook - M4's qmGenerate with qm_gen_in wta = 1) and reports FAIL.

Regenerate? (`boot_plan`, first rule that applies)
  mp-sync          an MP mod sync is in progress (StringRegister7 <> '' or
                   FileAge(<save>\mods.restore) <> -1, plan S8; both quiet at a
                   normal boot, M0 probe 12): nothing is regenerated, written
                   or restarted in this start
  first            no marker
  suspected-brick  the previous start stopped between its boot and the menu
                   and the inputs are the same: regenerate in wta mode
  inputs-changed   the fingerprint differs from the marker's hash
  fallback-kept    a wta fallback is in place for this hash: kept, unless the
                   outputs were damaged (then regenerated in wta mode)
  damaged          an output's FileAge differs from the one recorded after
                   the generation (I6: a Workshop update restored the shipped
                   copies): regenerate. An Apply records the age of a file
                   that fell back as 0 (`recorded_age`), so the next start,
                   with the new set's scripts loaded, builds it again
  stable           nothing to do
The UI's Apply (`apply=True`) always regenerates (normal mode), unless an MP
sync is in progress.

Restart? (`restart_plan`) Only when a file's content changed (M4's qm_gen
`changed`: outputs with a new token, stale files removed or overwritten) or
mods.ini's effective order changed (ref/order.py mods_ini_plan and
needs_restart: not when Quartermaster only moved past mods that ship none of
its files and no file the index reads). Refused, in
this order, with the reason reported as FAIL:
  mp-sync          as above
  loop             the previous life ended with Quartermaster's own restart
                   and the inputs moved across it: whatever changed them, a
                   restart would only chase them (the I5 loop). One automatic
                   restart, then FAIL - docs/plan.md section 4, I5. Not a
                   loop: inputs that moved only by mods the engine registered
                   at this start (a folder made with New mod, a subscription)
                   - the fingerprint without them (`fp_known`,
                   ref/index.py known_fingerprint) is the marker's. A folder
                   made before an Apply restart was refused here and reported
                   FAIL (logs of 2026-10-01); the rules below still
                   bound the restarts
  in-a-row         two automatic restarts in a row already (plan S8)
  per-hash         one automatic restart for this fingerprint already (S8)
  selftest         a SelfTest run (<save>\qm_autotest.cfg exists) without the
                   case file qm_test\cases\qm_m5_restart.cfg keeps one life:
                   the SelfTest runs in every life and expects its results of
                   one; the I5/I7/I8 runs ship that case
The Apply restart is the player's own decision: only mp-sync refuses it, and
it does not count towards the automatic ones. A boot that needed no restart
ends the chain: rows, rhash and rcount go back to 0, -, 0.

The restart itself waits in qm_rt until qmTick sees at least 1 s pass since
the boot's last write, on a main-menu frame - the probe-5 restart did the
same from a DoProgress hook, 10 tenths of a second after rewriting mods.ini,
and the next start honoured both the file and the rewritten mods.ini
(docs/research/context-2026-09-27.md section 3) - then runs the vanilla sequence
LanShutdown; SteamwrapFree; RestartApplicationParam('')
(data/gui/menu.inc/onworkshopautoupdate.inc:8-11).

The load order (decided 2026-09-28, plan S11)
---------------------------------------------
The player's order, kept in <save>\quartermaster\order.cfg (ref/order.py
has the file and the rules), is an input like any other: the fingerprint
lists the mods in load order (ref/fingerprint.py), so nothing here needed a
new rule. What it means for the scenarios:
  - an Apply that reorders asks for a fingerprint of the new order, always
    regenerates (winners may change) and restarts with kind `apply` when a
    file changed or mods.ini's enabled order did; the next boot computes the
    same fingerprint from the saved order and is stable;
  - an outside reorder (modman) does not touch the saved order, so the
    fingerprint stays and the boot only puts mods.ini back: a
    `mods-ini-changed` restart under the same guards as the canonical order
    had (I7 restores the SAVED order now; a first boot without a saved order
    uses the canonical order, exactly as before);
  - a new mod is placed after the saved order and changes the fingerprint
    the way a new mod always did.
`Life(apply=Apply(...))` models an Apply after a life's boot.

Newly registered mods, <save>\quartermaster\known.cfg (plan S13)
-------------------------------------------------------------------
The same shape, Name = qmKnown, `;format|1` and then one value per dir the
boot has seen: `;k|<dir>` known, `;n|<dir>` new - registered after
Quartermaster's first boot and not yet acknowledged. The dir is the engine's
spelling (ModLibraryGetData); it is compared as ref/order.py folds it.
Without a file (the first boot) every current mod is recorded as known:
nothing was new to a Quartermaster that had never run. A confirmed Apply
acknowledges them all. The file is written only when it changes. A dir is
written as an internal string, so any byte survives (a folder name outside
ASCII). The manager window shows a new mod as NEW (qm_report st<j>,
docs/ui.md) until then.
"""
from . import inc as I
from .order import norm_dir as _norm_dir
from .textio import escape, read_lines, unescape, write_file

__all__ = ["STATE_REL", "KNOWN_REL", "STATE_KEYS", "KNOWN_KEYS", "FORMAT",
           "WRITTEN", "BOOTING", "BOOTED", "NORMAL", "WTA",
           "AUTO", "APPLY", "TEST", "NONE", "MAX_IN_A_ROW", "MAX_PER_HASH",
           "DELAY_TENTHS", "WINDOW_TENTHS",
           "SYNC", "FIRST", "SUSPECT", "INPUTS", "KEPT", "DAMAGED", "STABLE", "APPLIED",
           "OUTPUTS", "MODSINI", "LOOP", "IN_A_ROW", "PER_HASH", "NOTHING", "HELD",
           "Marker", "BootPlan", "RestartPlan", "marker_values", "render_marker",
           "parse_marker", "damaged", "unstable_fp", "boot_plan", "restart_plan",
           "next_marker", "tick", "known_values", "render_known", "parse_known",
           "update_known", "fresh", "acknowledge", "restart_due", "restart_now", "Life", "Apply",
           "simulate", "auto_restarts"]

STATE_REL = b"quartermaster\\state.cfg"
KNOWN_REL = b"quartermaster\\known.cfg"
STATE_KEYS = [b"Name = qmState"]
KNOWN_KEYS = [b"Name = qmKnown"]
FORMAT = b"1"

WRITTEN, BOOTING, BOOTED = b"written", b"booting", b"booted"
NORMAL, WTA = b"normal", b"wta"
AUTO, APPLY, TEST, NONE = b"auto", b"apply", b"test", b"-"

#: Plan S8: max 1 automatic restart per hash, 2 in a row.
MAX_IN_A_ROW = 2
MAX_PER_HASH = 1

#: The restart waits until this many tenths of a second have passed since
#: the boot's last write. Floor(t*10) can be up to one tenth late, so 11
#: tenths are at least 1 s.
DELAY_TENTHS = 11
#: A restart still waiting this long after it was due (the player left the
#: main menu, a skirmish ran) is dropped: its changes load at the next start.
WINDOW_TENTHS = 600

# Why a boot regenerates or not (log and report words; the game writes the same).
SYNC, FIRST, SUSPECT = b"mp-sync", b"first", b"suspected-brick"
INPUTS, KEPT, DAMAGED = b"inputs-changed", b"fallback-kept", b"damaged"
STABLE, APPLIED = b"stable", b"apply"
# Why a restart happens or is refused.
OUTPUTS, MODSINI, NOTHING = b"outputs-changed", b"mods-ini-changed", b"nothing-changed"
LOOP, IN_A_ROW, PER_HASH = b"loop", b"in-a-row", b"per-hash"
HELD = b"selftest"


def _int(text):
    return int(text) if text.isdigit() else 0


class Marker(object):
    """state.cfg's fields (see the module docstring)."""

    __slots__ = ("gen", "hash", "phase", "mode", "rows", "rhash", "rcount", "rk",
                 "boots", "outs")

    def __init__(self, gen=0, hash=b"-", phase=BOOTED, mode=NORMAL, rows=0, rhash=b"-",
                 rcount=0, rk=NONE, boots=0, outs=()):
        self.gen, self.hash, self.phase, self.mode = gen, hash, phase, mode
        self.rows, self.rhash, self.rcount, self.rk = rows, rhash, rcount, rk
        self.boots, self.outs = boots, list(outs)

    def copy(self):
        return Marker(self.gen, self.hash, self.phase, self.mode, self.rows, self.rhash,
                      self.rcount, self.rk, self.boots, self.outs)

    def __eq__(self, other):
        return isinstance(other, Marker) and all(
            getattr(self, k) == getattr(other, k) for k in self.__slots__)

    def __repr__(self):
        return "Marker(%s)" % ", ".join("%s=%r" % (k, getattr(self, k)) for k in self.__slots__)


def marker_values(m):
    """The Code values of state.cfg, raw bytes."""
    out = [b";format|" + FORMAT, b";gen|%d" % m.gen, b";hash|" + m.hash,
           b";phase|" + m.phase, b";mode|" + m.mode, b";rows|%d" % m.rows,
           b";rhash|" + m.rhash, b";rcount|%d" % m.rcount, b";rk|" + m.rk,
           b";boots|%d" % m.boots]
    out += [b";out|" + path + b"|" + age for path, age in m.outs]
    return out


def render_marker(m):
    """state.cfg's bytes, as the game's raw writer writes them."""
    return write_file(I.layout_lines(STATE_KEYS, [escape(v) for v in marker_values(m)]))


def _engine_values(data):
    """Code values the way the engine's parser hands them to a script (raw
    bytes, trailing spaces dropped - run m2a). The raw writer's 0-3 padding
    spaces after the last line do not stop the parser from loading the file
    (the synthetic file of SelfTest run m2a3 was written that way); the line
    model here is the raw reader's, which reads the same values."""
    if data is None or not data.lstrip(b" ").startswith(b"section.begin"):
        raise I.IncFormatError("not an .inc")
    _form, _keys, values = I.values_from_lines(read_lines(data))
    return [unescape(v).rstrip(b" ") for v in values]


def parse_marker(data):
    """A Marker from state.cfg's bytes, or None: no file, or not a marker."""
    if data is None:
        return None
    try:
        values = _engine_values(data)
    except I.IncFormatError:
        return None
    if b";format|" + FORMAT not in values:
        return None
    m = Marker()
    for v in values:
        f = v.split(b"|")
        key = f[0]
        val = f[1] if len(f) > 1 else b""
        if key == b";gen":
            m.gen = _int(val)
        elif key == b";hash" and val:
            m.hash = val
        elif key == b";phase" and val in (WRITTEN, BOOTING, BOOTED):
            m.phase = val
        elif key == b";mode" and val in (NORMAL, WTA):
            m.mode = val
        elif key == b";rows":
            m.rows = _int(val)
        elif key == b";rhash" and val:
            m.rhash = val
        elif key == b";rcount":
            m.rcount = _int(val)
        elif key == b";rk" and val in (AUTO, APPLY, TEST, NONE):
            m.rk = val
        elif key == b";boots":
            m.boots = _int(val)
        elif key == b";out" and len(f) > 2 and val:
            m.outs.append((val, f[2]))
    return m


#: The age an Apply records for an output that fell back (qm_gen x =
#: fallback): no file has it. An Apply checks what it merges against the
#: scripts the running game loaded, not the ones the new set brings, so such
#: a file may only have missed the library of a mod just switched on; the
#: next start then finds it `damaged` and builds it again with the new set
#: loaded. Once: a start's own generation records the real age.
UNCHECKED = b"0"


def recorded_age(age, fell_back, apply):
    """What state.cfg keeps as an output's FileAge after a generation."""
    return UNCHECKED if apply and fell_back else age


def damaged(marker, age_of):
    """Does any recorded output's FileAge differ now? `age_of(path)` is
    FileAge(<QmDir>\\data\\<path>) as the game prints it (b'-1' missing)."""
    if marker is None:
        return False
    return any(age_of(path) != age for path, age in marker.outs)


def unstable_fp(fp, boots):
    """The fingerprint of an I5 run (the SelfTest case qm_m5_unstable.cfg
    asks for it): a salt that changes with every boot."""
    return fp + b"|unstable " + b"%d" % boots


class BootPlan(object):
    __slots__ = ("regen", "mode", "why", "phase", "followed", "suspect", "sync",
                 "apply", "boots")

    def __repr__(self):
        return "BootPlan(%s)" % ", ".join("%s=%r" % (k, getattr(self, k)) for k in self.__slots__)


def boot_plan(marker, fp, sync, is_damaged, apply=False):
    """What this start (or an Apply) does before generating: see the module
    docstring for the rules and their order."""
    m = marker
    p = BootPlan()
    p.sync, p.apply = bool(sync), bool(apply)
    p.regen, p.mode = False, NORMAL
    p.boots = (m.boots if m else 0) + (0 if apply else 1)
    if apply:
        p.phase = m.phase if m else BOOTED
        p.followed = p.suspect = False
    else:
        p.followed = m is not None and m.rk != NONE
        p.suspect = m is not None and m.phase == BOOTING
        p.phase = BOOTING if m is not None and m.phase in (WRITTEN, BOOTING) else BOOTED
    if p.sync:
        p.why = SYNC
    elif apply:
        p.regen, p.why = True, APPLIED
    elif m is None:
        p.regen, p.why = True, FIRST
    elif p.suspect and fp == m.hash:
        p.regen, p.mode, p.why = True, WTA, SUSPECT
    elif fp != m.hash:
        p.regen, p.why = True, INPUTS
    elif m.mode == WTA:
        p.mode = WTA
        if is_damaged:
            p.regen, p.why = True, DAMAGED
        else:
            p.why = KEPT
    elif is_damaged:
        p.regen, p.why = True, DAMAGED
    else:
        p.why = STABLE
    return p


class RestartPlan(object):
    __slots__ = ("wanted", "restart", "kind", "why", "refused")

    def __init__(self, wanted, restart, kind, why, refused):
        self.wanted, self.restart, self.kind, self.why, self.refused = (
            wanted, restart, kind, why, refused)

    def __repr__(self):
        return "RestartPlan(%s)" % ", ".join("%s=%r" % (k, getattr(self, k))
                                           for k in self.__slots__)


def restart_plan(marker, plan, fp, changed, mods_changed, held=False, fp_known=None):
    """Restart after this boot (or Apply)? `changed` is qm_gen `changed` (0
    without a generation), `mods_changed` whether mods.ini's effective order
    or flags changed; `held`: a SelfTest run that did not ask for restarts;
    `fp_known` the fingerprint without the mods registered at this start
    (None: there are none, it is `fp`)."""
    m = marker
    if not (changed > 0 or mods_changed):
        return RestartPlan(False, False, NONE, NOTHING, None)
    why = OUTPUTS if changed > 0 else MODSINI
    if plan.sync:
        return RestartPlan(True, False, NONE, why, SYNC)
    if held:
        return RestartPlan(True, False, NONE, why, HELD)
    if plan.apply:
        return RestartPlan(True, True, APPLY, why, None)
    known = fp if fp_known is None else fp_known
    if plan.followed and fp != m.hash and known != m.hash:
        return RestartPlan(True, False, NONE, why, LOOP)
    if m is not None and m.rows >= MAX_IN_A_ROW:
        return RestartPlan(True, False, NONE, why, IN_A_ROW)
    if m is not None and m.rhash == fp and m.rcount >= MAX_PER_HASH:
        return RestartPlan(True, False, NONE, why, PER_HASH)
    return RestartPlan(True, True, AUTO, why, None)


def next_marker(marker, plan, rplan, fp, gen, gen_ok, changed, outs):
    """state.cfg after this boot (or Apply). `gen`, `gen_ok`, `changed`,
    `outs` describe the generation (ignored when none ran): its number, whether
    it finished (qm_gen status ok), qm_gen changed, and the outputs with their
    FileAge afterwards."""
    n = marker.copy() if marker is not None else Marker()
    n.boots = plan.boots
    n.phase = plan.phase
    if not plan.apply:
        n.rk = NONE
    if plan.regen and gen_ok:
        n.gen, n.mode, n.hash, n.outs = gen, plan.mode, fp, list(outs)
        if changed > 0:
            n.phase = WRITTEN
    if rplan.restart:
        n.rk = rplan.kind
        if rplan.kind == AUTO:
            n.rows = (marker.rows if marker else 0) + 1
            same = marker is not None and marker.rhash == fp
            n.rcount = marker.rcount + 1 if same else 1
            n.rhash = fp
        else:
            n.rows, n.rhash, n.rcount = 0, b"-", 0
    elif rplan.refused is None and not plan.sync and not plan.apply:
        # A start that needed no restart ends the chain of automatic ones.
        n.rows, n.rhash, n.rcount = 0, b"-", 0
    return n


def tick(marker):
    """The main menu's first frame: a start that found `written` is booted."""
    if marker is not None and marker.phase == BOOTING:
        n = marker.copy()
        n.phase = BOOTED
        return n
    return marker


def restart_due(now_tenths):
    """qm_rt `rsdue` for a restart requested now."""
    return now_tenths + DELAY_TENTHS


def restart_now(now_tenths, due, main_menu, sync):
    """`restart`, `wait` or `drop` for a pending restart on this frame."""
    if now_tenths > due + WINDOW_TENTHS:
        return b"drop"
    if now_tenths >= due and main_menu and not sync:
        return b"restart"
    return b"wait"


# ------------------------------------------------------------ known.cfg
def known_values(entries):
    """The Code values of known.cfg: the format line first, so the file
    always has the struct form of two or more values."""
    return [b";format|" + FORMAT] + [(b";n|" if new else b";k|") + d for d, new in entries]


def render_known(entries):
    """known.cfg's bytes; `entries` = [(dir, new)] in file order."""
    return write_file(I.layout_lines(KNOWN_KEYS, [escape(v) for v in known_values(entries)]))


def parse_known(data):
    """[(dir, new)] from known.cfg's bytes, or None when there is no file (or
    it is not a known.cfg: no format line)."""
    if data is None:
        return None
    try:
        values = _engine_values(data)
    except I.IncFormatError:
        return None
    if b";format|" + FORMAT not in values:
        return None
    out = []
    for v in values:
        if v.startswith(b";k|") and len(v) > 3:
            out.append((v[3:], False))
        elif v.startswith(b";n|") and len(v) > 3:
            out.append((v[3:], True))
    return out


def update_known(known, dirs):
    """`(entries, new dirs, changed)` for the mods registered now (`dirs`, in
    the engine's order). A missing file (`known` None) records everything
    as known. New dirs are appended in the engine's order; a known dir keeps
    its entry, and one that is gone now stays listed."""
    if known is None:
        entries = []
        seen = set()
        for d in dirs:
            if _norm_dir(d) not in seen:
                seen.add(_norm_dir(d))
                entries.append((d, False))
        return entries, [], True
    entries = list(known)
    seen = set(_norm_dir(d) for d, _new in entries)
    changed = False
    for d in dirs:
        if _norm_dir(d) not in seen:
            seen.add(_norm_dir(d))
            entries.append((d, True))
            changed = True
    now = set(_norm_dir(d) for d in dirs)
    new = [d for d, flag in entries if flag and _norm_dir(d) in now]
    return entries, new, changed


def fresh(known, dirs):
    """Which of `dirs` (the mods registered now, in the engine's order) the
    engine registered at this start: not in known.cfg at all (`known` as
    parse_known gives it). A first boot (no file) has none. qm_known fr<i>."""
    if known is None:
        return [False] * len(dirs)
    seen = set(_norm_dir(d) for d, _new in known)
    return [_norm_dir(d) not in seen for d in dirs]


def acknowledge(entries):
    """After a confirmed Apply: `(entries, changed)` with nothing new."""
    changed = any(new for _d, new in entries)
    return [(d, False) for d, _new in entries], changed


# -------------------------------------------------------- whole starts
class Life(object):
    """One start of the game as the boot sees it, for `simulate`.

    fp         the fingerprint this start computes
    changed    qm_gen changed if this start generates: an int, or a function
               of the BootPlan (the mode decides what a generation writes)
    mods       mods.ini's effective order changed
    sync       an MP mod sync is in progress
    damaged    a recorded output's FileAge moved (None: the outputs are as
               the last generation left them)
    menu       the start reached the main menu's first frame (qmTick)
    restart    a restart of another kind ends this start when the boot did
               not schedule one (`test`: a SelfTest case)
    apply      an Apply of the manager window after the boot (`Apply`), run
               by qmTick on a main-menu frame when the boot left no restart
               pending
    known_fp   the fingerprint without the mods registered at this start
               (None: none were)
    """

    def __init__(self, fp, changed=0, mods=False, sync=False, damaged=False, menu=True,
                 restart=None, apply=None, known_fp=None):
        self.fp, self.changed, self.mods, self.sync = fp, changed, mods, sync
        self.damaged, self.menu, self.restart = damaged, menu, restart
        self.apply, self.known_fp = apply, known_fp


class Apply(object):
    """A confirmed Apply in a `Life`: `fp` the fingerprint of the mods, flags
    and load order it asks for; `changed` qm_gen changed of its generation;
    `mods` mods.ini's enabled order or flags changed."""

    def __init__(self, fp, changed=0, mods=False):
        self.fp, self.changed, self.mods = fp, changed, mods


def simulate(lives, marker=None):
    """Run `lives` in order, each ending with Quartermaster's restart or with
    the next start by hand. Returns `(trace, marker)`, trace = one
    `(plan, rplan, marker after the start)` per life, and one more after it
    for a life's Apply (its plan has `apply` set)."""
    trace = []
    for life in lives:
        plan = boot_plan(marker, life.fp, life.sync, life.damaged)
        changed = 0
        if plan.regen:
            changed = life.changed(plan) if callable(life.changed) else life.changed
        rplan = restart_plan(marker, plan, life.fp, changed, life.mods, fp_known=life.known_fp)
        n = next_marker(marker, plan, rplan, life.fp, (marker.gen if marker else 0) + 1,
                        True, changed, marker.outs if marker else [])
        if life.menu:
            n = tick(n)
        if not rplan.restart and life.restart:
            n = n.copy()
            n.rk = life.restart
        trace.append((plan, rplan, n))
        marker = n
        a = life.apply
        if a is not None and life.menu and not rplan.restart:
            plan = boot_plan(marker, a.fp, life.sync, False, apply=True)
            changed = a.changed if plan.regen else 0
            rplan = restart_plan(marker, plan, a.fp, changed, a.mods)
            n = next_marker(marker, plan, rplan, a.fp, marker.gen + 1, True, changed,
                            marker.outs)
            trace.append((plan, rplan, n))
            marker = n
    return trace, marker


def auto_restarts(trace):
    """How many of the traced starts ended with an automatic restart."""
    return sum(1 for _p, r, _m in trace if r.restart and r.kind == AUTO)
