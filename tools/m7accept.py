r"""Acceptance A (milestone M7): I1-I9 of docs/plan.md section 4 through the
real pipeline, and a regression run of the game without Quartermaster.

    python tools/m7accept.py prepare --out DIR
        every case file the runs need (m5cases prepare: the m5 cases, the empty
        fixture fixtures\m5\QMTestNew and the I7 seed; m6cases: the I9 case)
    python tools/m7accept.py plan --out DIR --logs LOGS
        the run requests in order: the hrun command, lives and restarts, what
        each life's log must show, and the check command
    python tools/m7accept.py check RUN --scenario ID
        check a finished hrun run folder; exit 0 when it holds, 1 when
        something differs, 2 when the run folder is incomplete

Every run is the boot a player gets: dist\Quartermaster and the fixtures
deployed, the game started, Quartermaster's own boot doing the work. No run
uses a SelfTest sandbox (the M4 generations into <save>\qm_test\out). A
SelfTest case appears only where a scenario needs something a player does by
hand - another life (I1, I7, I8), the unstable fingerprint (I5), the manager
window (I9) - and every change of mods.ini is made by Quartermaster's own
writer, never by the harness. A SelfTest run holds every
restart unless the case file qm_m5_restart.cfg is there (qmBoot).

What a check compares, on top of m5cases' rules (the run reached its marker,
SWEEP OK, no brick, the restarts, no compile error but the expected ones, one
boot per process, the lines each life must and must not hold, mods.ini as the
game left it, the marker's stamps against the writer's own lines):

  the replay   every generation the logs show is recomputed by the twin
               (ref/validate.py generate) from what that boot logged - the mod
               list, the plan, the validator's verdicts, the stale files it
               could delete - and the game's files: vanilla, the fixtures and
               dist. Candidates (path, tier, seq), the gen done counts, the
               outputs hash, every written token, the stale results must be
               the twin's; the next life's CameraControl constant (hookgen)
               must be the outputs hash that life loaded; the files in
               Quartermaster's folder at the end of the run (hrun's qm_mod
               copy) must be the twin's, byte for byte, the manifest's
               generation, hash and tokens too; and report.txt and report.cfg
               of the last generation (qm_save) must be the twin's report of
               it, Boot block and NEW marks included
  per scenario what the milestone asks (below)

Scenarios, in the order to run them (restarts = lives - 1, as hrun counts):
  vanilla  the game alone (--no-quartermaster): no [qm] line, both start-up
           DoCreates reached, every folder of mods\ unchanged (hrun's sweep
           compares SW_Frontline_Protocol's mod.ini and data\ file by file);
           1 life, 0 restarts
  i1       Quartermaster alone (cases relife + restart): the first boot changes
           no file (the shipped copies carry the alone generation constant),
           no restart is even wanted; a test restart gives a second life whose
           boot is stable; mods.ini keeps its order, Quartermaster last; 2 lives,
           1 restart (test)
  i2       QMTestWASD + QMTestCamSpeed, no SelfTest: both files merged, one
           automatic restart; the second life runs both fixtures' markers
           (`QMTEST camspeed registershortcuts`, `QMTEST wasd`; `QMTEST
           camspeed` of oncamera.inc prints only when OnCamera runs); the
           written oncamera.inc / registershortcuts.inc equal the twin's;
           2 lives, 1 restart (auto)
  i3       QMTestWASD + QMTestConflict: one conflict, the later mod (WASD)
           wins, the game starts; 2 lives, 1 restart (auto)
  i4       QMTestWASD + QMTestBroken: the merged registershortcuts.inc does
           not compile (its validation state's compile error is expected), the
           winner's copy is written, the report says FAIL, the game starts;
           2 lives, 1 restart (auto)
  i5       forced unstable fingerprint (m5cases i5): one automatic restart,
           then FAIL (loop); 2 lives, 1 restart (auto). No replay: the salt
           the SelfTest adds to the generation constant is not in the log
  i6       the hook files restored to the shipped copies: i2's
           <save>\quartermaster seeded into a fresh deploy; the outputs are
           damaged, regenerated, one restart; 2 lives, 1 restart (auto)
  i7       shuffled mods.ini + a new folder (m5cases i7): 4 lives, 3 restarts
           (auto, test, auto)
  i8       Quartermaster switched off in mods.ini by its own writer (m5cases
           i8): no [qm] line in life 2; 2 lives, 1 restart (test)
  i9       a mod switched off after a merge, through the manager window
           (m6cases i9): the stale merged files are deleted, WASD's own files
           are in effect; 3 lives, 2 restarts (auto, apply)
  order    the load order the player sets (plan S11, m5cases
           order): QMTestWASD moved above QMTestConflict through the manager's
           controller + Apply - mods.ini and order.cfg in the new order, the
           conflict now won by QMTestConflict, the report's MP note; 3 lives,
           2 restarts (auto, apply)
  saved    a saved load order put back after an outside shuffle, a new folder
           placed after it (m5cases saved); 4 lives, 3 restarts (auto, test,
           auto)

The replay maps a plan's positions to dirs by the load positions the boot
logged (`order: mod <i> pos=<k> (canonical <c>)`, qmOrder), not by the
canonical ones of the mod list.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for _p in (REPO, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import hbuild  # noqa: E402
import m4cases  # noqa: E402
import m5cases  # noqa: E402
import m6cases  # noqa: E402
from ref import conflicts as CF  # noqa: E402
from ref import manifest as MF  # noqa: E402
from ref import report as RP  # noqa: E402
from ref import validate as V  # noqa: E402
from ref.planner import Decision  # noqa: E402

GAME = hbuild.GAME
FIXTURES = os.path.join(REPO, "fixtures")
OUT, LOGS = m5cases.OUT, m5cases.LOGS
PREFIX = "m7"
TICK_START = m5cases.TICK_START
CONFIRMED = m5cases.CONFIRMED
#: The last line of the game's start-up log without Quartermaster (see vanilla).
VANILLA_LAST = "SteamwrapGetNumAchievements"
QM_COPY = m6cases.QM_COPY
CAMERA = b"gui\\menu.inc\\cameracontrol.inc"
BROKEN_PATH = b"gui\\menu.inc\\registershortcuts.inc"


# ------------------------------------------------------------- scenarios
class Accept(object):
    """A scenario: the m5cases.Scenario that runs and checks it, and what this
    tool adds - `replay` (recompute the generations), `report` (compare the
    last generation's report files), `extra` (the scenario's own rules)."""

    def __init__(self, s, replay=True, report=True, extra=None):
        self.s, self.replay, self.report, self.extra = s, replay, report, extra

    @property
    def name(self):
        return self.s.name


def broken_states(fixtures_dir=FIXTURES):
    """The validation states the boot's generation of WASD + Broken fails on
    (m4cases' twin), for hrun --expect-compile-error."""
    return m4cases.expected_failures(fixtures_dir=fixtures_dir)["boot:qm_m4a.cfg"]


def scenarios(out=OUT, logs=LOGS, expect_broken=None):
    """Every run, in order. `expect_broken`: the I4 validation states (None:
    computed from the fixtures)."""
    if expect_broken is None:
        expect_broken = broken_states()
    by = dict((s.name, s) for s in m5cases.scenarios(out, logs))
    i1, i5, i7, i8 = by["i1"], by["i5"], by["i7"], by["i8"]
    order, saved = by["order"], by["saved"]
    i6 = by["i6b"]
    i6.name = "i6"
    i6.state = os.path.join(logs, PREFIX + "i2", "qm_save")
    for s in (i5, i6):
        s.ini_check = "kept"
    two = dict(until=TICK_START, until_log=2, timeout=420, restarts=1, ini_check="kept")
    first = ["why=first", "[qm] guard restart=True kind=auto why=outputs-changed",
             "[qm] restart now kind=auto"]
    stable = ["why=stable", "[qm] boot stable", CONFIRMED, TICK_START, "![qm] restart now"]
    # The game alone ends its start-up log with Steam's achievement callback,
    # after both InitMap lines: the 16th and last line of 11 of 11 complete
    # vanilla logs (m7vanilla, m12*vanilla). Until 2026-10-05 the run waited
    # out its 90 s timeout, ~78 s of an m12 pass, with nothing more to log.
    vanilla = m5cases.Scenario(
        "vanilla", "the game without Quartermaster: no [qm] line, SWFP untouched",
        quartermaster=False, until=VANILLA_LAST, timeout=60, restarts=0,
        lives=[["!" + "[qm]", "InitMap finished"]])
    i2 = m5cases.Scenario(
        "i2", "WASD + CamSpeed: both merged, both markers after the restart",
        fixtures=["QMTestWASD", "QMTestCamSpeed"],
        lives=[first, stable + ["QMTEST camspeed registershortcuts", "QMTEST wasd"]], **two)
    i3 = m5cases.Scenario(
        "i3", "WASD + Conflict: one conflict, the later mod wins, the game starts",
        fixtures=["QMTestWASD", "QMTestConflict"],
        lives=[first + ["[qm] report WARN"], stable + ["QMTEST wasd"]], **two)
    i4 = m5cases.Scenario(
        "i4", "WASD + Broken: the merge does not compile, the winner's copy, FAIL",
        fixtures=["QMTestWASD", "QMTestBroken"], expect=expect_broken,
        lives=[first + ["[qm] gen candidate %s merged seq=" % BROKEN_PATH.decode(),
                        "[qm] gen candidate %s winner seq=" % BROKEN_PATH.decode(),
                        "[qm] report FAIL"],
               stable + ["QMTEST wasd"]], **two)
    i9 = m6cases.i9_scenario(out, logs)
    return [Accept(vanilla, replay=False, report=False, extra=_vanilla_rules),
            Accept(i1, extra=_alone_rules),
            Accept(i2),
            Accept(i3, extra=_conflict_rules),
            Accept(i4, extra=_broken_rules),
            Accept(i5, replay=False, report=False),
            Accept(i6),
            Accept(i7),
            Accept(i8),
            Accept(i9, extra=_i9_rules),
            Accept(order, extra=_reorder_rules),
            Accept(saved)]


def by_name(name, out=OUT, logs=LOGS, expect_broken=None):
    for a in scenarios(out, logs, expect_broken):
        if a.name == name:
            return a
    raise KeyError(name)


NAMES = ("vanilla", "i1", "i2", "i3", "i4", "i5", "i6", "i7", "i8", "i9", "order", "saved")


# ------------------------------------------------------------ the logs
_QM = re.compile(rb"\[qm\] (.*)$")
_BOOT = re.compile(rb"^boot version (\S+) (?:hook=(\S+) hookgen=(\S*)|apply seq=(\d+))")
#: The title at the end came in on 2026-09-30 (the report names mods by it);
#: older logs end at ini=.
_MOD = re.compile(rb"^mod (\d+) pos=(\d+) on=([01]) origin=(\w) dir=(.*) tag=(\S*) ini=(-?\d+)"
                  rb"(?: tit=(.*))?$")
_APPLY_ON = re.compile(rb"^order: apply sets on=([01]) for (.*)$")
_LOAD_POS = re.compile(rb"^order: mod (\d+) pos=(\d+) \(canonical (\d+)\)$")
_PLAN = re.compile(rb"^plan (\S+) (\S+) \((\S+), (\S+)\) winner=(\d+) providers=([\d;]+)$")
_FP = re.compile(rb"^fingerprint (\S+) lines=\d+$")
_GUARD = re.compile(rb"^guard plan regen=(\d) mode=(\w+) why=(\S+)")
_GEN_START = re.compile(rb"^gen start sandbox=(\S*) decisions=")
_CAND = re.compile(rb"^gen candidate (\S+) (\S+) seq=(\d+) ok=([01])$")
_STALE = re.compile(rb"^gen stale (\S+) (\w+)$")
_WRITE = re.compile(rb"^write (\S+) result=(-?\d+) .* staged=-?\d+:(\S+) .* back=-?\d+:(\S+) to ")
_DONE = re.compile(rb"^gen done status=(\w+) generation=(\d+) outputs hash=(\S+) written=(\d+) "
                   rb"same=(\d+) changed=(\d+) failed=(\d+) removed=(\d+)$")
_BOOT_LINE = re.compile(rb"^boot report (\w+) (.*)$")
#: A clash between enabled mods, for both mods' blocks of the report by mod
#: (qmBoot, since 2026-10-01): the two dirs and the file under scripts\.
_CLASH = re.compile(rb"^boot clash\|([^|]*)\|([^|]*)\|([^|]*)$")
_NEW = re.compile(rb"^known: new mod (.*)$")


def _read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def qm_lines(data):
    """The `[qm]` texts of one game log (bytes), without the marker."""
    out = []
    for raw in data.split(b"\n"):
        m = _QM.search(raw.rstrip(b"\r"))
        if m:
            out.append(m.group(1))
    return out


class Block(object):
    """One run of qmBoot as its log lines tell it: a boot or an Apply."""

    def __init__(self, life, apply_seq, hookgen):
        self.life, self.apply, self.hookgen = life, apply_seq, hookgen
        self.mods = {}           # index -> [pos, on, origin, dir]
        self.plan = []
        self.fp = b"-"
        self.mode = b"normal"
        self.box = None          # None: no generation; b"": the production one
        self.cands, self.stale, self.writes = [], [], {}
        self.done = None
        self.boot_lines, self.new = [], []
        self.clashes = []


def blocks(logs):
    """Every boot and Apply of a run, in order; `logs` = [(name, bytes)]."""
    out = []
    for life, (_name, data) in enumerate(logs, 1):
        cur = None
        for t in qm_lines(data):
            m = _BOOT.match(t)
            if m:
                cur = Block(life, m.group(4), m.group(3))
                out.append(cur)
                continue
            if cur is None:
                continue
            m = _MOD.match(t)
            if m:
                cur.mods[int(m.group(1))] = [int(m.group(2)), m.group(3) == b"1", m.group(4),
                                             m.group(5), m.group(8) or b""]
                continue
            m = _APPLY_ON.match(t)
            if m:
                for row in cur.mods.values():
                    if row[3].lower() == m.group(2).lower():
                        row[1] = m.group(1) == b"1"
                continue
            m = _LOAD_POS.match(t)
            if m:
                if int(m.group(1)) in cur.mods:
                    cur.mods[int(m.group(1))][0] = int(m.group(2))
                continue
            m = _PLAN.match(t)
            if m:
                cur.plan.append(Decision(m.group(1), m.group(2), m.group(3), m.group(4),
                                         int(m.group(5)),
                                         [int(x) for x in m.group(6).split(b";")]))
                continue
            for rx, fn in ((_FP, lambda m: setattr(cur, "fp", m.group(1))),
                           (_GUARD, lambda m: setattr(cur, "mode", m.group(2))),
                           (_GEN_START, lambda m: setattr(cur, "box", m.group(1))),
                           (_CAND, lambda m: cur.cands.append(
                               (m.group(1), m.group(2), int(m.group(3)), m.group(4) == b"1"))),
                           (_STALE, lambda m: cur.stale.append((m.group(1), m.group(2)))),
                           (_WRITE, lambda m: cur.writes.__setitem__(
                               m.group(1), (m.group(2), m.group(3), m.group(4)))),
                           (_DONE, lambda m: setattr(cur, "done", m.groups())),
                           (_BOOT_LINE, lambda m: cur.boot_lines.append(
                               m.group(1) + b" " + m.group(2))),
                           (_CLASH, lambda m: cur.clashes.append(m.groups())),
                           (_NEW, lambda m: cur.new.append(m.group(1)))):
                m = rx.match(t)
                if m:
                    fn(m)
                    break
    return out


# ------------------------------------------------------------ the replay
class Files(object):
    """The game's files the twin reads: vanilla, the mods' folders, dist."""

    def __init__(self, game_dir=GAME, fixtures_dir=FIXTURES, dist_mod=hbuild.DIST_MOD):
        self.game_dir, self.fixtures_dir, self.dist_mod = game_dir, fixtures_dir, dist_mod
        self.read_vanilla = m4cases.vanilla_reader(game_dir)
        extra = os.path.join(fixtures_dir, "m5")
        self._roots = [m4cases.roots(game_dir, fixtures_dir, dist_mod),
                       m4cases.roots(game_dir, extra, dist_mod)]
        entries = m4cases.idx_entries(dist_mod)
        self.classes = m4cases._Classes((e[0], e[3]) for e in entries)

    def root_of(self, d):
        for r in self._roots:
            got = r(d)
            if got is not None:
                return got
        return None

    def read_mod(self, d, path):
        root = self.root_of(d)
        if root is None:
            return None
        return _read(os.path.join(root, "data", *path.decode("ascii").split("\\")))

    def hook_file(self, path):
        name = path.decode("ascii").rsplit("\\", 1)[-1]
        return _read(os.path.join(self.dist_mod, "data", "quartermaster", "hooks", name))

    def dist_data(self):
        """`{path: bytes}` of dist's data\\ files, vanilla.idx spelling."""
        out = {}
        top = os.path.join(self.dist_mod, "data")
        for dirpath, _dirs, names in os.walk(top):
            for n in names:
                full = os.path.join(dirpath, n)
                rel = os.path.relpath(full, top).replace(os.sep, "\\").lower()
                out[rel.encode("ascii")] = _read(full)
        return out

    def shipped_hookgen(self):
        """The generation constant baked into dist's CameraControl copy."""
        data = _read(os.path.join(self.dist_mod, "data", *CAMERA.decode().split("\\"))) or b""
        m = re.search(rb"const qmHookGen = '([^']*)';", data)
        return m.group(1) if m else None


class Replay(object):
    """What the twin made of a run: per generation block (the Generation,
    its inputs for the report), the mirror of Quartermaster's folder, and the
    differences found on the way."""

    def __init__(self):
        self.gens = []           # (block, Generation, dirs, enabled, self_pos)
        self.mirror = {}
        self.deleted = set()
        self.problems = []


def _view(b):
    """`(dirs {pos: dir} with the titles, enabled positions, self_pos)` of a block."""
    dirs = RP.Dirs(((row[0], row[3]) for row in b.mods.values()),
                   ((row[0], row[4]) for row in b.mods.values()))
    enabled = [row[0] for row in b.mods.values() if row[1]]
    self_pos = next((row[0] for row in b.mods.values() if row[2] == b"s"), -1)
    return dirs, enabled, self_pos


def replay(logs, files):
    """Recompute every production generation of a run (module docstring)."""
    rp = Replay()
    rp.mirror = files.dist_data()
    prev = None
    hookgen = files.shipped_hookgen()
    last_life = 0
    for b in blocks(logs):
        tag = "life %d %s" % (b.life, "apply %s" % b.apply.decode() if b.apply else "boot")
        if b.apply is None and b.hookgen is not None and b.life != last_life:
            last_life = b.life
            if hookgen is not None and b.hookgen != hookgen:
                rp.problems.append("%s: the loaded CameraControl constant is %s, the files on "
                                   "disk say %s" % (tag, b.hookgen.decode(), hookgen.decode()))
        if b.box != b"":
            continue
        dirs, enabled, self_pos = _view(b)
        verdict = dict((seq, ok) for _p, _t, seq, ok in b.cands)
        dropped = set(p for p, r in b.stale if r == b"deleted")
        mirror = rp.mirror
        g = V.generate(b.plan, self_pos, files.read_vanilla,
                       lambda pos, path: files.read_mod(dirs.get(pos, b""), path),
                       files.hook_file, lambda c: verdict.get(c.seq, False),
                       prev_manifest=prev, deleted=lambda p: p in dropped,
                       classes=files.classes, fp=b.fp,
                       seq0=min(verdict) if verdict else 0, existing=mirror.get,
                       wta=(b.mode == b"wta"))
        got_c = [(p, t, s) for p, t, s, _ok in b.cands]
        want_c = [(c.path, c.tier, c.seq) for c in g.candidates]
        if got_c != want_c:
            rp.problems.append("%s: candidates game %r, twin %r" % (tag, got_c, want_c))
        if b.done is None:
            rp.problems.append("%s: no `gen done` line" % tag)
        else:
            want_d = (g.status, b"%d" % g.gen, g.outhash,
                      b"%d" % sum(1 for r in g.paths if r.written == b"yes"),
                      b"%d" % sum(1 for r in g.paths if r.written == b"same"),
                      b"%d" % g.changed,
                      b"%d" % sum(1 for r in g.paths if r.status in (V.FAIL, V.FATAL)),
                      b"%d" % sum(1 for s in g.stale if s.result in (b"deleted",
                                                                       b"overwritten")))
            if tuple(b.done) != want_d:
                rp.problems.append("%s: gen done game %r, twin %r" % (tag, b.done, want_d))
        for r in g.paths:
            if r.chosen is None or r.written not in (b"yes", b"same"):
                continue
            w = b.writes.get(r.path)
            if w is None:
                rp.problems.append("%s: no write line for %s" % (tag, r.path.decode()))
                continue
            result, staged, back = w
            want_r = b"1" if r.written == b"yes" else b"2"
            if result != want_r or staged != r.chosen.tok or (
                    result == b"1" and back != r.chosen.tok):
                rp.problems.append("%s: write %s game result=%s staged=%s back=%s, twin "
                                   "result=%s token=%s" % (tag, r.path.decode(), result.decode(),
                                                           staged.decode(), back.decode(),
                                                           want_r.decode(),
                                                           r.chosen.tok.decode()))
        got_s = list(b.stale)
        want_s = [(s.path, s.result) for s in g.stale]
        if got_s != want_s:
            rp.problems.append("%s: stale game %r, twin %r" % (tag, got_s, want_s))
        for s in g.stale:
            if s.result == b"deleted":
                mirror.pop(s.path, None)
                rp.deleted.add(s.path)
        for path in g.outputs:
            rp.deleted.discard(path)
        mirror.update(g.outputs)
        if g.manifest is not None:
            mirror[MF.MANIFEST_REL] = g.manifest
            prev = g.manifest
        if g.status == b"ok" and any(r.path == CAMERA and r.chosen for r in g.paths):
            hookgen = g.outhash
        rp.gens.append((b, g, dirs, enabled, self_pos))
    return rp


def folder_problems(rp, run_dir):
    """Quartermaster's folder at the end of the run (hrun's qm_mod) against the
    twin's mirror - dist's files with every generation's outputs laid over
    them and the deleted ones taken out: the same files, each byte for byte,
    the manifest by its generation, hash, fingerprint and tokens (its source
    rows hold FileAge values the log does not carry)."""
    copy = os.path.join(run_dir, QM_COPY)
    if not os.path.isdir(copy):
        return ["%s missing: hrun did not keep Quartermaster's folder" % QM_COPY]
    top = os.path.join(copy, "data")
    have = {}
    for dirpath, _dirs, names in os.walk(top):
        for n in names:
            full = os.path.join(dirpath, n)
            have[os.path.relpath(full, top).replace(os.sep, "\\").lower().encode("ascii")] = full
    problems = []
    for path in sorted(set(have) - set(rp.mirror)):
        problems.append("%s: %s is there, the twin has no such file%s" % (
            QM_COPY, path.decode(), " (deleted as stale)" if path in rp.deleted else ""))
    for path in sorted(set(rp.mirror) - set(have)):
        problems.append("%s: %s is missing" % (QM_COPY, path.decode()))
    for path in sorted(set(rp.mirror) & set(have)):
        got, want = _read(have[path]), rp.mirror[path]
        if path == MF.MANIFEST_REL:
            a, b = MF.parse(got), MF.parse(want)
            if (a.gen, a.outhash, a.fp, a.outs, a.lefts) != (b.gen, b.outhash, b.fp, b.outs,
                                                            b.lefts):
                problems.append("%s: manifest gen/hash/fp/tokens game %r, twin %r" % (
                    QM_COPY, (a.gen, a.outhash, a.fp, a.outs, a.lefts),
                    (b.gen, b.outhash, b.fp, b.outs, b.lefts)))
        elif got != want:
            problems.append("%s: %s differs from the twin" % (QM_COPY, path.decode()))
    return problems


def report_problems(rp, run_dir, files=None):
    """report.txt, report.cfg and conflicts.txt of the run's last generation
    (qm_save) against the twin's report of it."""
    if not rp.gens:
        return []
    b, g, dirs, enabled, self_pos = rp.gens[-1]
    boot = RP.Boot(b.boot_lines, RP.worst([ln.split(b" ", 1)[0] for ln in b.boot_lines]),
                   b.new, b.clashes)
    lines = RP.report_lines(g, dirs, enabled, self_pos, boot)
    want_txt = RP.report_bytes(lines)
    cf = CF.build(g, dirs, enabled, self_pos, (files or Files()).read_vanilla, boot)
    want_cfg = RP.report_cfg(RP.qm_report(g, lines, dirs, enabled, self_pos, boot,
                                          window=CF.window(cf)))
    want_conf = CF.conflicts_bytes(CF.report_lines(cf, g, hbuild.QM_VERSION.encode("ascii")))
    problems = []
    got_txt = _read(os.path.join(run_dir, "qm_save", "report.txt"))
    if got_txt != want_txt:
        got = (got_txt or b"").split(b"\r\n")
        first = next((k for k, (x, y) in enumerate(zip(got, want_txt.split(b"\r\n"))) if x != y),
                     min(len(got), len(want_txt.split(b"\r\n"))))
        problems.append("qm_save\\report.txt differs from the twin's from line %d: game %r, "
                        "twin %r" % (first + 1, got[first:first + 1],
                                     want_txt.split(b"\r\n")[first:first + 1]))
    if _read(os.path.join(run_dir, "qm_save", "report.cfg")) != want_cfg:
        problems.append("qm_save\\report.cfg differs from the twin's")
    got_conf = _read(os.path.join(run_dir, "qm_save", "conflicts.txt"))
    if got_conf != want_conf:
        got = (got_conf or b"").split(b"\r\n")
        want = want_conf.split(b"\r\n")
        first = next((k for k, (x, y) in enumerate(zip(got, want)) if x != y),
                     min(len(got), len(want)))
        problems.append("qm_save\\conflicts.txt differs from the twin's from line %d: game %r, "
                        "twin %r" % (first + 1, got[first:first + 1], want[first:first + 1]))
    return problems


# ------------------------------------------------------------ the rules
def _log_bytes(run_dir):
    return [(n, "\r\n".join(lines).encode("latin-1")) for n, lines in m5cases.run_logs(run_dir)]


def _vanilla_rules(run_dir, files):
    problems = []
    logs = m5cases.run_logs(run_dir)
    if logs and sum("InitMap finished" in ln for ln in logs[0][1]) < 2:
        problems.append("%s: fewer than two `InitMap finished`: the main menu's second "
                        "start-up DoCreate was not reached" % logs[0][0])
    summary = json.loads((_read(os.path.join(run_dir, "summary.json")) or b"{}").decode())
    checked = summary.get("sweep", {}).get("mods_trees_checked") or {}
    if "SW_Frontline_Protocol" not in checked:
        problems.append("the sweep did not compare mods\\SW_Frontline_Protocol file by file "
                        "(an hrun without that check?): %r" % checked)
    return problems


def _alone_rules(run_dir, files):
    """I1: the shipped hook copies are what Quartermaster alone generates, so
    they end the run byte-identical to dist."""
    problems = []
    copy = os.path.join(run_dir, QM_COPY)
    if not os.path.isdir(copy):
        return problems                 # folder_problems says so already
    for h in hbuild.HOOK_FILES:
        rel = h.split("/")
        if _read(os.path.join(copy, *rel)) != _read(os.path.join(files.dist_mod, *rel)):
            problems.append("%s: %s is not dist's copy" % (QM_COPY, h))
    return problems


def _report_text(run_dir):
    return (_read(os.path.join(run_dir, "qm_save", "report.txt")) or b"").split(b"\r\n")


def _lost_to(line, loser, winner):
    """A report.txt `conflict:` line in which the mod at `loser`'s dir lost to
    the one at `winner`'s, whether the report names them by dir alone or by
    title with the dir beside it (since 2026-09-30: `1. QMTestConflict
    (mods\\QMTestConflict) lost to 2. QMTestWASD (mods\\QMTestWASD)`)."""
    before, sep, after = line.partition(b" lost to ")
    return bool(sep) and loser in before and winner in after and not after.count(b" lost to ")


def _conflict_rules(run_dir, files):
    lines = [ln for ln in _report_text(run_dir) if ln.startswith(b"  conflict: ")]
    if len(lines) != 1 or not _lost_to(lines[0], b"mods\\QMTestConflict", b"mods\\QMTestWASD"):
        return ["report.txt: expected one conflict that QMTestConflict lost to QMTestWASD, "
                "got %r" % lines]
    return []


def _reorder_rules(run_dir, files):
    """Load order (a): after QMTestWASD was moved above QMTestConflict, the one
    conflict is won by QMTestConflict, and the report says the order is not
    the canonical one."""
    text = _report_text(run_dir)
    lines = [ln for ln in text if ln.startswith(b"  conflict: ")]
    problems = []
    if len(lines) != 1 or not _lost_to(lines[0], b"mods\\QMTestWASD", b"mods\\QMTestConflict"):
        problems.append("report.txt: expected one conflict that QMTestWASD lost to "
                        "QMTestConflict, got %r" % lines)
    if not any(b"Multiplayer: every player needs the same mods" in ln for ln in text):
        problems.append("report.txt lacks the multiplayer line (the load order is not canonical)")
    return problems


def _broken_rules(run_dir, files):
    text = _report_text(run_dir)
    want = [b"FAIL " + BROKEN_PATH, b"  candidate merged: does not compile",
            b"  candidate winner: compiles"]
    missing = [w for w in want if w not in text]
    return ["report.txt lacks %r" % missing] if missing else []


def _i9_rules(run_dir, files):
    problems, facts = m6cases.i9_problems(run_dir, fixtures_dir=files.fixtures_dir)
    if problems is None:
        return ["the SelfTest output of I9 is missing: %s" % facts]
    return problems


def check_run(run_dir, a, files):
    """`(problems, facts)` of a run folder against the scenario `a`."""
    problems, facts = m5cases.check_run(run_dir, a.s)
    if problems is None:
        return None, facts
    if a.replay:
        rp = replay(_log_bytes(run_dir), files)
        facts["generations"] = ["life %d: gen %d %s changed=%d" % (b.life, g.gen, g.outhash.decode(),
                                                                   g.changed)
                                for b, g, _d, _e, _s in rp.gens]
        problems += rp.problems + folder_problems(rp, run_dir)
        if a.report:
            problems += report_problems(rp, run_dir, files)
    if a.extra is not None:
        problems += a.extra(run_dir, files)
    return problems, facts


def check(run_dir, name, files=None, echo=print):
    files = files or Files()
    a = by_name(name, expect_broken=broken_states(files.fixtures_dir) if name == "i4" else [])
    problems, facts = check_run(run_dir, a, files)
    if problems is None:
        echo("incomplete: %s" % facts)
        return 2
    echo("facts: %s" % facts)
    for p in problems:
        echo("DIFF " + p)
    echo("m7 %s: %s" % (name, "OK" if not problems else "%d difference(s)" % len(problems)))
    return 0 if not problems else 1


# ------------------------------------------------------ prepare and plan
def prepare(out=OUT, fixtures=FIXTURES, game=GAME, echo=print):
    m5cases.prepare(out, os.path.join(fixtures, "m5"), game, echo)
    for name, data in sorted(m6cases.i9_case_files().items()):
        with open(os.path.join(out, name), "wb") as fh:
            fh.write(data)
        echo("wrote %s" % os.path.join(out, name))
    return 0


def plan(out=OUT, logs=LOGS, echo=print, expect_broken=None):
    runs = scenarios(out, logs, expect_broken)
    echo("Prerequisites: python tools/hbuild.py --check (0 findings, dist up to date); "
         "python tools/fixtures.py; python tools/m7accept.py prepare --out %s; a frozen "
         "dist snapshot (sha256 of every file); mods\\ holds only SW_Frontline_Protocol and "
         "mods.ini." % out)
    echo("Every run starts from the player's baseline: hrun restores mods.ini and "
         "<save>\\quartermaster after each one. Run them one at a time, in this order.")
    for n, a in enumerate(runs, 1):
        s = a.s
        echo("")
        echo("%d. %s%s - %s" % (n, PREFIX, s.name, s.what))
        echo("   " + m5cases.command(s, out, logs, prefix=PREFIX))
        echo("   lives %d, restarts %d; then python tools/m7accept.py check %s --scenario %s"
             % (s.restarts + 1, s.restarts, os.path.join(logs, PREFIX + s.name), s.name))
        for k, want in enumerate(s.lives, 1):
            echo("   log %d: %s" % (k, "; ".join(want)))
    return 0


def main(argv=None, echo=print):
    p = argparse.ArgumentParser(prog="m7accept.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("prepare")
    pr.add_argument("--out", required=True)
    pr.add_argument("--fixtures", default=FIXTURES)
    pr.add_argument("--game-dir", default=GAME)
    pl = sub.add_parser("plan")
    pl.add_argument("--out", required=True)
    pl.add_argument("--logs", required=True)
    ch = sub.add_parser("check")
    ch.add_argument("run")
    ch.add_argument("--scenario", required=True, choices=NAMES)
    ch.add_argument("--game-dir", default=GAME)
    ch.add_argument("--fixtures-dir", default=FIXTURES)
    ch.add_argument("--dist", default=None,
                    help="the dist the run deployed (default: the one its summary.json names, "
                         "else dist\\Quartermaster)")
    a = p.parse_args(argv)
    if a.cmd == "prepare":
        return prepare(a.out, a.fixtures, a.game_dir, echo)
    if a.cmd == "plan":
        return plan(a.out, a.logs, echo)
    return check(a.run, a.scenario, Files(a.game_dir, a.fixtures_dir,
                                          a.dist or run_dist(a.run)), echo)


def run_dist(run_dir):
    """The dist folder a run deployed, as hrun's summary names it (a frozen
    snapshot, usually), when it still exists; else dist\\Quartermaster."""
    try:
        with open(os.path.join(run_dir, "summary.json"), encoding="utf-8") as fh:
            dist = json.load(fh).get("dist")
    except (OSError, ValueError):
        dist = None
    return dist if dist and os.path.isdir(dist) else hbuild.DIST_MOD


if __name__ == "__main__":
    sys.exit(main())
