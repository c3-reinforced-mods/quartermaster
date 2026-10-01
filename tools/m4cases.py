r"""SelfTest cases for the validator, writer, manifest and report (M4), and the
check of what a run wrote.

    python tools/m4cases.py cases --out DIR     the case files and the pristine hook file
    python tools/m4cases.py expect              the validation states each run fails on
                                                purpose (hrun --expect-compile-error)
    python tools/m4cases.py check RUN           compare a run's SelfTest output with ref/
    python tools/m4cases.py hookfixture [--out DIR]
                                                fixtures/QMTestM4Hook and QMTestM4Near
                                                (qm_m4b.cfg and qm_m4c.cfg need them)
    python tools/m4cases.py bootfixture RUN [--label a] [--out DIR]
                                                a mod folder made of Quartermaster and the
                                                files generation <label> wrote

The case files go to the game with tools/hrun.py (`--case`, every file of DIR,
the hook file too: it lands next to the case files, where `gen ... hooks`
looks for it). The SelfTest (src/states/qmcasem4.pas) runs every generation in
a sandbox under <save>\qm_test\out\m4\<label>\, which hrun collects into
<run>\qm_test_out\m4\ and removes; nothing is written into a mod folder.

  qm_m4a.cfg  with QMTestWASD + QMTestBroken: every file of VAL_FILES through
              the validator as vanilla ships it (all must compile), vanilla
              oncamera.inc with a line that is not Pascal (must not) and then
              again without it (the manager recovers), then generation `a`:
              the merged registershortcuts.inc does not compile, the winner's
              copy is written, the report says FAIL with the reason.
  qm_m4b.cfg  with QMTestWASD + QMTestCamSpeed + QMTestM4Hook: generation `b`
              (both files merge, and eventmainmenu.inc merges with the hook
              lines on top), `b` again with QMTestCamSpeed dropped (the two merged
              outputs are stale and deleted), `c` twice (the same inputs: the
              second writes the same bytes and keeps the generation number)
              and `d` once (a cold start from the same inputs: the same bytes).
  qm_m4c.cfg  with QMTestWASD + QMTestConflict + QMTestM4Near: generation `x`,
              one merge with a conflict and a pair of near edits (the report's
              line numbers).
  qm_m4v.cfg  optional: every merge-class vanilla `.inc` through the validator
              (the false-reject rate of the validation copy on vanilla code).
  cameracontrol.inc  the pristine CameraControl hook lines the generations use
              (PROPOSED_HOOK: today's hook lines plus the generation constant).

`check` recomputes every generation with ref/validate.py from the inputs the
dump records (mods, index, plan) and the fixtures' files, taking only the
validator's verdicts from the game, and compares candidates, tokens, results,
every file in the sandboxes (outputs, staged candidates, validation copies,
manifest, report.txt, report.cfg), the qm_report rows and the milestone's
expectations. A sandbox's report has no Boot block: that block is the boot's
own generation's.
Exit status: 0 equal, 1 a difference, 2 the output is incomplete.
"""
import argparse
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for _p in (REPO, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import hbuild  # noqa: E402
from ref import conflicts as CF  # noqa: E402
from ref import inc as I  # noqa: E402
from ref import manifest as MF  # noqa: E402
from ref import report as RP  # noqa: E402
from ref import selftest as S  # noqa: E402
from ref import validate as V  # noqa: E402
from ref.fingerprint import qhash  # noqa: E402
from ref.index import Mod, build_index, canonical_positions  # noqa: E402
from ref.planner import Decision, plan  # noqa: E402
from ref.textio import read_lines  # noqa: E402

GAME = hbuild.GAME
FIXTURES = os.path.join(REPO, "fixtures")
HOOK_FILE = "cameracontrol.inc"
BOOT_FIXTURE = "QMTestM4Gen"
#: A mod that changes one of Quartermaster's hook files, so a generation has a
#: hook file with a participant (the merged+hook candidate). EventMainMenu,
#: because whichever copy the overlay serves, the game still boots: that hook
#: only opens the manager window, and the change is a comment.
HOOK_FIXTURE = "QMTestM4Hook"
HOOK_FIXTURE_FILE = "data/gui/menu.inc/eventmainmenu.inc"
HOOK_FIXTURE_OLD = b"      [*] = ;const cTagCredits = 111;\r\n"
HOOK_FIXTURE_NEW = b"      [*] = ;const cTagCredits = 111; // QMTEST m4hook\r\n"
#: A mod whose oncamera.inc edit sits three vanilla lines above QMTestWASD's
#: first hunk there (value 10 against 14..17): with QMTestConflict as well,
#: one merge has a conflict and a pair of near edits, so the report's
#: `conflict:` and `near:` lines are exercised. A comment: it compiles alone.
NEAR_FIXTURE = "QMTestM4Near"
NEAR_FIXTURE_FILE = "data/gui/menu.inc/oncamera.inc"
NEAR_FIXTURE_OLD = b"      [*] = ;var bmouse : Boolean;\r\n"
NEAR_FIXTURE_NEW = b"      [*] = ;var bmouse : Boolean; // QMTEST near\r\n"
#: A mod with two oncamera.inc edits where the second needs the first - what
#: MGraphics - Main Menu does in showmainmenu.inc (a const one hunk declares,
#: others use; 2026-09-30): the first sits on the `var bLeft` line QMTestWASD
#: rewrites (it loses that conflict), the second eight lines below WASD's hunk.
#: `split_oracle` refuses a file with the second and not the first, the way
#: the game refused the merged showmainmenu.inc of Renaissance + MGraphics.
SPLIT_FIXTURE = "QMTestM4Split"
SPLIT_FIXTURE_FILE = "data/gui/menu.inc/oncamera.inc"
SPLIT_DECL = (b"      [*] = ;var bLeft : Boolean = IsKeyDownByName('Left');\r\n",
              b"      [*] = ;var bLeft : Boolean = IsKeyDownByName('Left'); // QMTEST split decl\r\n")
SPLIT_USE = (b"      [*] = ;SetCameraElasticMoveFactor(speed);\r\n",
             b"      [*] = ;SetCameraElasticMoveFactor(speed); // QMTEST split use\r\n")

#: The CameraControl hook lines the M4 runs use, and the change proposed for
#: src/hooks/cameracontrol.pas: the lines of today's hook with the block that
#: re-creates qm_core folded into one line, so the generation constant (plan
#: S6) and the line that publishes it fit the ten-line limit of plan S5.
PROPOSED_HOOK = [
    b"const qmHookGen = '0';",
    b"var qmHookSm : Integer = GetTriggerManagerStateMachineHandle('qm_core');",
    b"if (qmHookSm=0) then",
    b"begin TriggerManagerAdd('qm_core'); qmHookSm := GetTriggerManagerStateMachineHandle"
    b"('qm_core'); StateMachineLoadFromFile(qmHookSm, '.\\data\\quartermaster\\core.aix'); end;",
    b"if (ParserSelectByKey('qm_rt')=0) and (gInterface.gamemode=gc_gamemode_mainmenu) then",
    b"begin ParserSetValueByKeyByHandle(ParserCreate('qm_rt'), 'hookgen', qmHookGen); "
    b"StateMachineExecuteState(qmHookSm, 'qmBoot', 0); end;",
    b"StateMachineExecuteState(qmHookSm, 'qmUiEnsure', 0);",
]
#: The state name of a pristine hook file (the proposed hbuild output
#: data/quartermaster/hooks/<file>.inc has the same shape).
HOOK_STATE = b"qmHookLines"

#: Vanilla files the validation copy must accept as they are: the four hook
#: files, the three the fixtures change, one `Code[*] = ` file, one without
#: Code, the five-space indent and a value of spaces only.
VAL_FILES = (b"gui\\menu.inc\\cameracontrol.inc", b"gui\\menu.inc\\initminimap.inc",
             b"gui\\menu.inc\\doprogress.inc", b"gui\\menu.inc\\eventmainmenu.inc",
             b"gui\\menu.inc\\registershortcuts.inc", b"gui\\menu.inc\\oncamera.inc",
             b"gui\\menu.inc\\hotkeysettings.inc",
             b"scripts\\units\\global.inc\\onafterload.inc", b"gui\\menu.inc\\eventhud.inc",
             b"gui\\menu.inc\\eventcustomgame.inc", b"scripts\\env\\env.inc\\doextract.inc")
BROKEN_TARGET = b"gui\\menu.inc\\oncamera.inc"

#: The SelfTest numbers its validation states from here (qmcasem4.pas): a
#: generation the boot runs first uses the numbers below.
SEQ_BASE = 1000

RUN_A = ("QMTestWASD", "QMTestBroken")
RUN_B = ("QMTestWASD", "QMTestCamSpeed", HOOK_FIXTURE)
RUN_C = ("QMTestWASD", "QMTestConflict", NEAR_FIXTURE)
#: QMTestM4Split loses its first oncamera.inc edit to QMTestWASD; with
#: QMTestM4Near as well two participants stay, so the subset candidate exists.
RUN_D = ("QMTestWASD", SPLIT_FIXTURE, NEAR_FIXTURE)
DROP = b"mods\\QMTestCamSpeed"


def hook_values():
    return [b";" + line for line in PROPOSED_HOOK]


def hook_file():
    """The pristine CameraControl hook file: a one-state `.inc` whose Code
    values are the hook lines (hbuild's assemble_inc)."""
    return hbuild.assemble_inc(HOOK_STATE, PROPOSED_HOOK)


def hook_files():
    """`{file name: bytes}`: a pristine hook file for every hook Quartermaster
    ships, with the lines tools/hbuild.py renders today - except a
    CameraControl hook without a generation line, which gets PROPOSED_HOOK."""
    out = {}
    variables = hbuild.build_variables([h.into for h in hbuild.load_hooks()])
    for h in hbuild.load_hooks():
        name = h.into.rsplit("/", 1)[-1]
        code = hbuild.render_lines(h, hbuild._vars_for(h, variables))
        if name == HOOK_FILE and not any(V.is_gen_line(b";" + c) for c in code):
            out[name] = hook_file()
        else:
            out[name] = hbuild.assemble_inc(HOOK_STATE, code)
    return out


def merge_paths(entries):
    return [e[0] for e in entries if e[3] == b"merge"]


def cases(entries):
    """`{file name: bytes}`."""
    a = [(b"val", p) for p in VAL_FILES]
    a += [(b"valbroken", BROKEN_TARGET), (b"val", BROKEN_TARGET), (b"gen", b"a", b"hooks")]
    b = [(b"gen", b"b", b"hooks"), (b"gen", b"b", b"hooks", b"drop", DROP),
         (b"gen", b"c", b"hooks"), (b"gen", b"c", b"hooks"), (b"gen", b"d", b"hooks")]
    c = [(b"gen", b"x", b"hooks")]
    v = [(b"val", p) for p in merge_paths(entries)]
    out = {"qm_m4a.cfg": S.render_case(b"m4gen", a),
            "qm_m4b.cfg": S.render_case(b"m4gen", b),
            "qm_m4c.cfg": S.render_case(b"m4gen", c),
           "qm_m4v.cfg": S.render_case(b"m4gen", v)}
    out.update(hook_files())
    return out


# --------------------------------------------------------------- the twin
def vanilla_reader(game_dir):
    def read(path):
        full = os.path.join(game_dir, "data", *path.decode("ascii").split("\\"))
        try:
            with open(full, "rb") as fh:
                return fh.read()
        except OSError:
            return None
    return read


def _read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def mod_reader(root_of, dir_of):
    """`read_mod(pos, path)` over the folders the mods were deployed from."""
    def read(pos, path):
        root = root_of(dir_of[pos])
        if root is None:
            return None
        return _read(os.path.join(root, "data", *path.decode("ascii").split("\\")))
    return read


def roots(game_dir=GAME, fixtures_dir=FIXTURES, dist_mod=hbuild.DIST_MOD):
    def root_of(d):
        text = d.decode("latin-1").replace("/", "\\").rstrip("\\")
        if text.lower().startswith("mods\\"):
            name = text[5:]
            if name.lower() == hbuild.MOD_NAME.lower():
                return dist_mod
            if os.path.isdir(os.path.join(fixtures_dir, name)):
                return os.path.join(fixtures_dir, name)
        path = os.path.normpath(os.path.join(game_dir, text))
        return path if os.path.isdir(path) else None
    return root_of


def duplicate_var_oracle(cand):
    """An offline stand-in for the compiler, enough for the fixtures: a
    candidate fails when it holds ref/validate.py BROKEN_LINE, or QMTestBroken's
    line together with a second `var` of the same name (the language is
    case-insensitive: its SWFP_SEAT against QMTestWASD's swfp_seat). Only the
    game decides for real; `check` takes the game's verdicts."""
    names = {}
    broken = None
    for v in cand.values:
        if v == V.BROKEN_LINE:
            return False
        t = v.lstrip(b";").strip().lower()
        if t.startswith(b"var ") and b":" in t:
            name = t[4:].split(b":")[0].strip()
            names[name] = names.get(name, 0) + 1
            if b"qmtest broken" in t:
                broken = name
    return broken is None or names.get(broken, 0) < 2


class Inputs(object):
    """What one run's generations start from: the game's view (mods, index,
    positions) and the readers of every file."""

    def __init__(self, mods, pos, self_index, idx, fp, read_vanilla, read_mod,
                 hook=None):
        self.mods = mods                    # [Mod] in mods.ini order
        self.pos = pos                      # canonical position of mod i
        self.self_index = self_index
        self.idx = idx                      # path -> (class, [positions], [ages])
        self.fp = fp
        self.read_vanilla = read_vanilla
        self.read_mod = read_mod
        self.hooks = hook if hook is not None else hook_files()
        self.fo = {}
        self.ident = {}

    @property
    def self_pos(self):
        return self.pos[self.self_index] if self.self_index >= 0 else -1

    def dir_of(self):
        """Position -> dir, with the titles the report names the mods by."""
        return RP.Dirs(((self.pos[i], m.dir) for i, m in enumerate(self.mods)),
                       ((self.pos[i], m.title) for i, m in enumerate(self.mods)))

    def enabled(self, dropped=()):
        return [self.pos[i] for i, m in enumerate(self.mods)
                if m.enabled and m.dir.lower() not in dropped]

    def srcs(self, path, p):
        _cls, provs, ages = self.idx[path]
        age = ages[provs.index(p)]
        i = self.pos.index(p)
        return (self.fo.get(i, b"-"), self.ident.get(i, b""), int(age))


def offline_inputs(fixtures, game_dir=GAME, fixtures_dir=FIXTURES,
                   dist_mod=hbuild.DIST_MOD, entries=None):
    """The inputs a run with `fixtures` deployed would have, computed here:
    the fixtures and Quartermaster enabled (other registered mods are
    disabled at the player's baseline and change no plan)."""
    mods = [Mod(b"mods\\" + f.encode("ascii"), True) for f in fixtures]
    mods.append(Mod(b"mods\\" + hbuild.MOD_NAME.encode("ascii"), True))
    for f in fixtures:
        if not os.path.isdir(os.path.join(fixtures_dir, f)):
            raise SystemExit("fixture %s is not in %s: build it first (tools/fixtures.py, "
                             "tools/m4cases.py hookfixture)" % (f, fixtures_dir))
    return _inputs(mods, canonical_positions(mods, len(mods) - 1), game_dir, fixtures_dir,
                   dist_mod, entries)


def ordered_inputs(dirs, titles=(), game_dir=GAME, fixtures_dir=FIXTURES,
                   dist_mod=hbuild.DIST_MOD, entries=None):
    """The inputs with the mods at `dirs` (engine dirs: a fixture or local
    folder as `mods\\<name>`, a Workshop item as its `..\\..\\workshop\\...`
    path) enabled in this load order and Quartermaster last - the order a
    composed mods.ini gives by default - with `titles` beside them for the
    report. Real Workshop mods are read where Steam installed them; nothing of
    theirs is copied."""
    titles = list(titles) + [b""] * (len(dirs) - len(titles))
    mods = [Mod(d, True, title=t) for d, t in zip(dirs, titles)]
    mods.append(Mod(b"mods\\" + hbuild.MOD_NAME.encode("ascii"), True, title=b"Quartermaster"))
    return _inputs(mods, list(range(len(mods))), game_dir, fixtures_dir, dist_mod, entries)


def _inputs(mods, pos, game_dir, fixtures_dir, dist_mod, entries):
    """offline_inputs and ordered_inputs: Quartermaster is the last of `mods`."""
    entries = entries if entries is not None else idx_entries(dist_mod)
    root_of = roots(game_dir, fixtures_dir, dist_mod)
    self_index = len(mods) - 1
    shipped = [hbuild._vanilla_rel(h.into) for h in hbuild.load_hooks()]

    def age(d, path):
        root = root_of(d)
        full = os.path.join(root, "data", *path.decode("ascii").split("\\"))
        return 1000 if os.path.isfile(full) else -1

    def has_core(d):
        root = root_of(d)
        return root is not None and os.path.isfile(
            os.path.join(root, "data", "quartermaster", "core.aix"))

    index = build_index(mods, self_index, entries, age, shipped, has_core, pos)
    cls = dict((e[0], e[3]) for e in entries)
    idx = {}
    for path, provs in index.providers.items():
        idx[path] = (cls[path], [pos[i] for i in provs],
                     [b"-" if a is None else b"%d" % a for a in index.ages[path]])
    inp = Inputs(mods, pos, self_index, idx, b"-", vanilla_reader(game_dir), None)
    dir_of = inp.dir_of()
    inp.read_mod = mod_reader(root_of, dir_of)
    for i, m in enumerate(mods):
        inp.fo[i] = b"l"
        inp.ident[i] = m.dir[len(b"mods\\"):]
    return inp


def idx_entries(dist_mod=hbuild.DIST_MOD):
    with open(os.path.join(dist_mod, *hbuild.IDX_REL.split("/")), "rb") as fh:
        _header, rows = hbuild.parse_vanilla_idx(fh.read())
    return [(p.encode("ascii"), s, n, c.encode("ascii")) for p, s, n, c in rows]


def decisions_for(inp, entries, dropped=()):
    """ref/planner.py over the inputs, providers as canonical positions (the
    view qm_plan gives the game side), with `dropped` dirs taken out."""
    dir_of = inp.dir_of()
    by_dir = {}
    for path, (_cls, provs, _ages) in inp.idx.items():
        keep = [dir_of[p] for p in provs if dir_of[p].lower() not in dropped]
        if keep:
            by_dir[path] = keep
    self_dir = inp.mods[inp.self_index].dir
    out = []
    pos_of = dict((d, p) for p, d in dir_of.items())
    for d in plan(by_dir, [e for e in entries if e[0] in by_dir], self_dir):
        out.append(Decision(d.path, d.action, d.strategy, d.reason, pos_of[d.winner],
                            [pos_of[x] for x in d.providers]))
    return out


def run_generation(inp, decisions, compiles, mirror, deleted=None, seq0=0):
    """One generation into a sandbox whose data mirror is `mirror` ({path:
    bytes}, the files there now, the manifest under MF.MANIFEST_REL); the
    mirror is updated to what the generation leaves on disk."""
    classes = dict((p, c[0]) for p, c in inp.idx.items())
    g = V.generate(decisions, inp.self_pos, inp.read_vanilla, inp.read_mod,
                   lambda path: inp.hooks.get(path.decode("ascii").rsplit("\\", 1)[-1]),
                   compiles,
                   prev_manifest=mirror.get(MF.MANIFEST_REL),
                   deleted=deleted if deleted is not None else (lambda p: True),
                   classes=_Classes(classes), srcs=inp.srcs, fp=inp.fp, seq0=seq0,
                   existing=mirror.get)
    for s_ in g.stale:
        if s_.result == b"deleted":
            mirror.pop(s_.path, None)
    mirror.update(g.outputs)
    if g.manifest is not None:
        mirror[MF.MANIFEST_REL] = g.manifest
    return g


class _Classes(dict):
    """vanilla.idx classes; a path the index did not scan is still merge class
    when it is on the allow-list (the stale path of a dropped mod)."""

    def get(self, key, default=None):
        return dict.get(self, key, b"merge" if key.endswith(b".inc") else default)


def conflicts_of(g, inp, dropped=()):
    """ref/conflicts.py over a generation of these inputs."""
    return CF.build(g, inp.dir_of(), inp.enabled(dropped), inp.self_pos, inp.read_vanilla)


def conflicts_bytes_of(g, inp, dropped=()):
    """conflicts.txt as the game writes it for that generation."""
    return CF.conflicts_bytes(CF.report_lines(conflicts_of(g, inp, dropped), g,
                                              hbuild.QM_VERSION.encode("ascii")))


def report_of(g, inp, dropped=()):
    lines = RP.report_lines(g, inp.dir_of(), inp.enabled(dropped), inp.self_pos)
    return lines, RP.report_bytes(lines), RP.qm_report(
        g, lines, inp.dir_of(), inp.enabled(dropped), inp.self_pos,
        window=CF.window(conflicts_of(g, inp, dropped)))


def simulate(fixtures, case, entries, inp=None, compiles=duplicate_var_oracle):
    """Run a case file's directives through the twin, offline. Returns
    `[(directive, result)]` and the next seq; a result is `(seq, ok)` for a
    validation, `(Generation, report lines)` for a generation."""
    inp = inp or offline_inputs(fixtures, entries=entries)
    _kind, directives = S.parse_case(case)
    out = []
    seq = SEQ_BASE
    mirrors = {}
    for d in directives:
        if d[0] in (b"val", b"valbroken"):
            keys, values = V.inc_lines(inp.read_vanilla(d[1]))
            if d[0] == b"valbroken":
                values = values + [V.BROKEN_LINE]
            cand = V.Candidate(d[1], b"val", seq, V.token(keys, values), b"", False,
                               keys, values)
            out.append((d, (seq, compiles(cand), cand)))
            seq += 1
        elif d[0] == b"gen":
            label = d[1]
            dropped = [d[k + 1].lower() for k in range(2, len(d) - 1) if d[k] == b"drop"]
            g = run_generation(inp, decisions_for(inp, entries, dropped), compiles,
                               mirrors.setdefault(label, {}), seq0=seq)
            seq = g.seq
            out.append((d, (g, report_of(g, inp, dropped))))
    return out, seq


def expected_failures(entries=None, fixtures_dir=FIXTURES):
    """`{case file: [state names]}` the runs fail on purpose, and under
    `boot:<case file>` the ones a generation fails on when the boot runs one
    before the SelfTest (numbered from 0, with the same mods)."""
    entries = entries if entries is not None else idx_entries()
    all_cases = cases(entries)
    out = {}
    for name, fixtures in (("qm_m4a.cfg", RUN_A), ("qm_m4b.cfg", RUN_B),
                           ("qm_m4c.cfg", RUN_C)):
        inp = offline_inputs(fixtures, fixtures_dir=fixtures_dir, entries=entries)
        results, _seq = simulate(fixtures, all_cases[name], entries, inp=inp)
        names = []
        for d, r in results:
            if d[0] in (b"val", b"valbroken"):
                if not r[1]:
                    names.append(V.state_name(r[0]).decode())
            else:
                names += [V.state_name(c.seq).decode() for c in r[0].candidates if not c.ok]
        out[name] = names
        g = run_generation(inp, decisions_for(inp, entries), duplicate_var_oracle, {}, seq0=0)
        out["boot:" + name] = [V.state_name(c.seq).decode() for c in g.candidates if not c.ok]
    # qm_m4v.cfg looks for rejections of vanilla code, so any of its states may
    # fail: all of them go to hrun, a failure is a finding, not a brick.
    n = len(S.parse_case(all_cases["qm_m4v.cfg"])[1])
    out["may:qm_m4v.cfg"] = [V.state_name(SEQ_BASE + k).decode() for k in range(n)]
    return out


# ------------------------------------------------------------------ check
def _rows(dump):
    return S.parse_dump(dump)


def inputs_from_dump(rows, game_dir=GAME, fixtures_dir=FIXTURES, dist_mod=hbuild.DIST_MOD):
    """The run's own view of mods and index, from the dump's context rows."""
    mods, pos, fo, ident = [], [], {}, {}
    for r in rows:
        if r[0] == b"mod":
            i = int(r[1])
            mods.append(Mod(S.unhex(r[4]), r[3] == b"1"))
            pos.append(int(r[2]))
            fo[i] = r[5]
            ident[i] = S.unhex(r[6])
    for r in rows:
        # A title row (since 2026-09-30; older dumps have none: no title).
        if r[0] == b"title" and int(r[1]) < len(mods):
            mods[int(r[1])].title = S.unhex(r[2])
    self_index = next(int(r[1]) for r in rows if r[0] == b"self")
    fp = next((r[1] for r in rows if r[0] == b"fp"), b"-") or b"-"
    idx = {}
    for r in rows:
        if r[0] == b"idx":
            provs = [int(x) for x in r[4].split(b";")]
            idx[r[2]] = (r[3], provs, r[5].split(b";"))
    root_of = roots(game_dir, fixtures_dir, dist_mod)
    inp = Inputs(mods, pos, self_index, idx, fp, vanilla_reader(game_dir), None)
    inp.read_mod = mod_reader(root_of, inp.dir_of())
    inp.fo, inp.ident = fo, ident
    return inp


def _plan_rows(rows, label_rows):
    out = []
    for r in label_rows:
        provs = [int(x) for x in r[8].split(b";")]
        out.append(Decision(r[3], r[4], r[5], r[6], int(r[7]), provs))
    return out


def check_dump(out_dir, dump, case, game_dir=GAME, fixtures_dir=FIXTURES,
               dist_mod=hbuild.DIST_MOD, out=print):
    """Problems of one m4gen case's output, as a list of strings."""
    rows = _rows(dump)
    problems = []
    inp = inputs_from_dump(rows, game_dir, fixtures_dir, dist_mod)
    m4 = os.path.join(out_dir, "m4")
    _kind, directives = S.parse_case(case)

    # The validator on single files.
    valv = [r for r in rows if r[0] == b"valv"]
    vals = [d for d in directives if d[0] in (b"val", b"valbroken")]
    if len(valv) != len(vals):
        problems.append("valv: %d rows for %d directives" % (len(valv), len(vals)))
    for r, d in zip(valv, vals):
        keys, values = V.inc_lines(inp.read_vanilla(d[1]))
        if d[0] == b"valbroken":
            values = values + [V.BROKEN_LINE]
        tok = V.token(keys, values)
        seq, want_ok = int(r[4]), (b"0" if d[0] == b"valbroken" else b"1")
        if r[5] != tok:
            problems.append("valv %s: token game %s, ref %s" % (d[1].decode(), r[5].decode(),
                                                                 tok.decode()))
        if r[6] != want_ok:
            problems.append("valv %s%s: ok=%s, expected %s" % (
                d[1].decode(), " (broken)" if d[0] == b"valbroken" else "", r[6].decode(),
                want_ok.decode()))
        got = _read(os.path.join(m4, "val", "work", "val", "%d.aix" % seq))
        if got != V.wrapper_bytes(seq, tok, values):
            problems.append("valv %s: validation copy %d.aix differs" % (d[1].decode(), seq))

    # The generations, in dump order, each against the twin.
    gens = [d for d in directives if d[0] == b"gen"]
    gen_rows = [r for r in rows if r[0] == b"gen"]
    if len(gen_rows) != len(gens):
        problems.append("gen: %d rows for %d directives" % (len(gen_rows), len(gens)))
        return problems
    mirrors = {}
    for k, d in enumerate(gens):
        label = d[1]
        dropped = [d[j + 1].lower() for j in range(2, len(d) - 1) if d[j] == b"drop"]
        # Rows of the k-th generation: they follow each other in the dump.
        mine = _gen_block(rows, k)
        cands = [r for r in mine if r[0] == b"cand"]
        stale = [r for r in mine if r[0] == b"stale"]
        verdict = dict((int(r[4]), r[6] == b"1") for r in cands)
        verdict.update((int(r[6]), r[8] == b"1") for r in stale if r[6] != b"-")
        deleted = set(r[3] for r in stale if r[4] == b"deleted")
        seq0 = min(verdict) if verdict else 0
        decisions = _plan_rows(rows, [r for r in mine if r[0] == b"plan"])
        g = run_generation(inp, decisions, lambda c: verdict.get(c.seq, False),
                           mirrors.setdefault(label, {}), lambda p: p in deleted, seq0=seq0)
        lines, rep, qmr = report_of(g, inp, dropped)
        problems += _compare_generation(label, k, mine, g, lines, rep, qmr)
        problems += _compare_files(m4, label, g, rep, qmr, k == _last_of(gens, label),
                                   conflicts_bytes_of(g, inp, dropped))
    problems += _expectations(gens, rows)
    for p in problems[:60]:
        out("  " + p)
    return problems


def _gen_block(rows, k):
    """The rows of the k-th generation: from its first plan row to its last
    qmc/qmr/qml row."""
    starts = [i for i, r in enumerate(rows)
              if r[0] == b"plan" and (i == 0 or rows[i - 1][0] != b"plan")]
    end = starts[k + 1] if k + 1 < len(starts) else len(rows)
    return rows[starts[k]:end]


def _last_of(gens, label):
    return max(k for k, d in enumerate(gens) if d[1] == label)


def _compare_generation(label, k, mine, g, lines, rep, qmr):
    p = []
    tag = "%s#%d" % (label.decode(), k)
    gr = next(r for r in mine if r[0] == b"gen")
    want = [g.status, b"%d" % g.gen, g.outhash, g.fatal or b"",
            b"%d" % sum(1 for r in g.paths if r.written == b"yes"),
            b"%d" % sum(1 for r in g.paths if r.written == b"same"),
            b"%d" % g.changed,
            b"%d" % sum(1 for r in g.paths if r.status in (V.FAIL, V.FATAL)),
            b"%d" % sum(1 for s in g.stale if s.result in (b"deleted", b"overwritten"))]
    if list(gr[2:11]) != want:
        p.append("%s gen: game %r, ref %r" % (tag, gr[2:11], want))
    rl = next((r for r in mine if r[0] == b"rload"), None)
    if rl is None or rl[3] != b"0":
        p.append("%s report.cfg read back: %r (keys compared, keys different)" % (tag, rl))
    got_c = [(int(r[2]), r[3], int(r[4]), r[5], r[6]) for r in mine if r[0] == b"cand"]
    want_c = [(r.m, c.tier, c.seq, c.tok, b"1" if c.ok else b"0")
              for r in g.paths for c in r.tries]
    if sorted(got_c, key=lambda x: x[2]) != sorted(want_c, key=lambda x: x[2]):
        p.append("%s candidates: game %r, ref %r" % (tag, got_c, want_c))
    for r in (x for x in mine if x[0] == b"path"):
        m = int(r[2])
        if m >= len(g.paths):
            p.append("%s path row %d: no such decision" % (tag, m))
            continue
        w = g.paths[m]
        c = w.chosen
        want_r = [w.code, w.status, b"%d" % w.job, b";".join(b"%d" % x for x in w.participants),
                  b"" if w.winner is None else b"%d" % w.winner]
        if w.act in (V.MERGE_INC, V.HOOK):
            want_r += [b"%d" % w.first_line, b"%d" % w.vanilla_n]
        else:
            want_r += [b"", b""]
        want_r += [c.tier if c else b"", c.tok if c else b"", c.htok if c else b"", w.written]
        got_r = [r[3], r[4], r[5], r[7], r[8], r[9], r[10], r[11], r[12], r[13], r[14]]
        if w.act not in (V.MERGE_INC, V.HOOK):
            # Participants and winner are recorded for every decision in game;
            # the twin keeps them for merges only.
            got_r[3], got_r[4] = want_r[3], want_r[4]
        if got_r != want_r:
            p.append("%s path %s: game %r, ref %r" % (tag, w.path.decode(), got_r, want_r))
    got_s = [(r[3], r[4], r[5]) for r in mine if r[0] == b"stale"]
    want_s = [(s.path, s.result, s.source) for s in g.stale]
    if got_s != want_s:
        p.append("%s stale: game %r, ref %r" % (tag, got_s, want_s))
    files = dict((r[2], (r[3], r[4])) for r in mine if r[0] == b"file")
    for path, data in g.outputs.items():
        _check_hash(p, tag, b"out:" + path, files, data)
    if g.manifest is not None:
        _check_hash(p, tag, b"manifest", files, g.manifest)
    _check_hash(p, tag, b"report", files, rep)
    qml = next((r for r in mine if r[0] == b"qml"), None)
    if qml is None or qml[2] != qmr[b"lines"]:
        p.append("%s qm_report lines: game %r, ref %s" % (tag, qml, qmr[b"lines"].decode()))
    got_q = [(r[2], S.unhex(r[3]), r[4], r[5]) for r in mine if r[0] == b"qmr"]
    want_q = [(b"%d" % j, qmr[b"dir%d" % j], qmr[b"st%d" % j], qmr[b"cn%d" % j])
              for j in range(int(qmr[b"n"]))]
    if got_q != want_q:
        p.append("%s qm_report records: game %r, ref %r" % (tag, got_q, want_q))
    got_l = [(r[2], r[3], S.unhex(r[4])) for r in mine if r[0] == b"qmc"]
    want_l = [(b"%d" % j, b"%d" % k2, qmr[b"c%d_%d" % (j, k2)])
              for j in range(int(qmr[b"n"])) for k2 in range(int(qmr[b"cn%d" % j]))]
    if got_l != want_l:
        p.append("%s qm_report lines per mod: game %r, ref %r" % (tag, got_l, want_l))
    return p


def _check_hash(p, tag, name, files, data):
    lines = read_lines(data)
    want = (S.lines_hash(lines), b"%d" % len(lines))
    if files.get(name) != want:
        p.append("%s file %s: game %r, ref %r" % (tag, name.decode(), files.get(name), want))


def _compare_files(m4, label, g, rep, qmr, last, conf=None):
    """Staged candidates and validation copies of this generation, and - for the
    last generation of a sandbox, whose files are the ones on disk - every
    output, the manifest, report.txt, report.cfg and conflicts.txt (`conf`),
    byte for byte."""
    p = []
    base = os.path.join(m4, label.decode())
    val = os.path.join(base, "work", "val")
    for seq, data in g.staged.items():
        if _read(os.path.join(val, "%d.inc" % seq)) != data:
            p.append("%s: staged candidate %d.inc differs" % (label.decode(), seq))
    for seq, data in g.wrappers.items():
        if _read(os.path.join(val, "%d.aix" % seq)) != data:
            p.append("%s: validation copy %d.aix differs" % (label.decode(), seq))
    if not last:
        return p
    data_dir = os.path.join(base, "qmdir", "data")
    for path, data in g.outputs.items():
        full = os.path.join(data_dir, *path.decode().split("\\"))
        if _read(full) != data:
            p.append("%s: output %s differs" % (label.decode(), path.decode()))
    for s in g.stale:
        full = os.path.join(data_dir, *s.path.decode().split("\\"))
        if s.result == b"deleted" and os.path.exists(full):
            p.append("%s: stale %s still there" % (label.decode(), s.path.decode()))
    if g.manifest is not None:
        full = os.path.join(data_dir, *MF.MANIFEST_REL.decode().split("\\"))
        if _read(full) != g.manifest:
            p.append("%s: manifest differs" % label.decode())
    if _read(os.path.join(base, "work", "report.txt")) != rep:
        p.append("%s: report.txt differs" % label.decode())
    if _read(os.path.join(base, "work", "report.cfg")) != RP.report_cfg(qmr):
        p.append("%s: report.cfg differs" % label.decode())
    if conf is not None and _read(os.path.join(base, "work", "conflicts.txt")) != conf:
        p.append("%s: conflicts.txt differs" % label.decode())
    return p


def _expectations(gens, rows):
    """The milestone's tests, on the game's own rows."""
    p = []
    blocks = [_gen_block(rows, k) for k in range(len(gens))]
    labels = [d[1] for d in gens]

    def path_row(block, path):
        plan_m = dict((r[3], r[2]) for r in block if r[0] == b"plan")
        m = plan_m.get(path)
        return next((r for r in block if r[0] == b"path" and r[2] == m), None)

    if b"a" in labels:
        blk = blocks[labels.index(b"a")]
        r = path_row(blk, b"gui\\menu.inc\\registershortcuts.inc")
        cands = [(c[3], c[6]) for c in blk if c[0] == b"cand" and r is not None and c[2] == r[2]]
        if r is None or r[3] != b"fallback" or r[4] != b"FAIL" or r[11] != b"winner" \
                or r[14] != b"yes" or cands != [(b"merged", b"0"), (b"winner", b"1")]:
            p.append("expectation a: registershortcuts.inc must be merged-fails, "
                     "winner written, FAIL; got %r %r" % (r, cands))
    if labels.count(b"b") == 2:
        first, second = [blocks[k] for k, x in enumerate(labels) if x == b"b"]
        written = [r[3] for r in first if r[0] == b"file" and r[2].startswith(b"out:")]
        stale = [(r[3], r[4]) for r in second if r[0] == b"stale"]
        for path in (b"gui\\menu.inc\\oncamera.inc", b"gui\\menu.inc\\registershortcuts.inc"):
            if b"out:" + path not in [r[2] for r in first if r[0] == b"file"]:
                p.append("expectation b: %s not written in the first generation" % path.decode())
            if (path, b"deleted") not in stale:
                p.append("expectation b: %s not deleted as stale (%r)" % (path.decode(), stale))
        if not written:
            p.append("expectation b: nothing written")
    if labels.count(b"c") == 2:
        one, two = [blocks[k] for k, x in enumerate(labels) if x == b"c"]
        f1 = [(r[2], r[3], r[4]) for r in one if r[0] == b"file"]
        f2 = [(r[2], r[3], r[4]) for r in two if r[0] == b"file"]
        g1 = next(r for r in one if r[0] == b"gen")
        g2 = next(r for r in two if r[0] == b"gen")
        if f1 != f2 or g1[3:5] != g2[3:5]:
            p.append("expectation c: two generations from the same inputs differ: %r / %r"
                     % (f1, f2))
        if b"d" in labels:
            fd = [(r[2], r[3], r[4]) for r in blocks[labels.index(b"d")] if r[0] == b"file"]
            if fd != f1:
                p.append("expectation c: a cold start differs: %r / %r" % (fd, f1))
    return p


def check(run_dir, game_dir=GAME, fixtures_dir=FIXTURES, dist_mod=hbuild.DIST_MOD, out=print):
    out_dir = run_dir
    if os.path.isdir(os.path.join(run_dir, "qm_test_out")):
        out_dir = os.path.join(run_dir, "qm_test_out")
    done = _read(os.path.join(out_dir, "done.txt"))
    if done is None:
        out("no done.txt in %s: the SelfTest did not finish" % out_dir)
        return 2
    ran = dict((r[1], (r[2], r[3])) for r in S.parse_dump(done) if r[0] == b"case")
    all_cases = cases(idx_entries(dist_mod))
    bad = 0
    incomplete = False
    for name in sorted(n for n in all_cases if n.endswith(".cfg")):
        key = name.encode("ascii")
        if key not in ran:
            continue
        kind, status = ran[key]
        dump = _read(os.path.join(out_dir, name[:-4] + ".txt"))
        if status != b"ok" or dump is None:
            out("%s: status %s, dump %s" % (name, status.decode(),
                                            "missing" if dump is None else "present"))
            incomplete = True
            if dump is None:
                continue
        found = check_dump(out_dir, dump, all_cases[name], game_dir, fixtures_dir, dist_mod, out)
        out("%s (%s): %d problem(s)" % (name, kind.decode(), len(found)))
        bad += len(found)
    out("problems: %d%s" % (bad, ", output incomplete" if incomplete else ""))
    if incomplete:
        return 2
    return 0 if bad == 0 else 1


# ------------------------------------------------------------ boot fixture
def _one_line_fixture(name, rel, old, new, game_dir):
    """`{relpath: bytes}`: the vanilla file with one unique line replaced
    (byte substitution), and a mod.ini."""
    import fixtures as F
    with open(os.path.join(game_dir, *rel.split("/")), "rb") as fh:
        vanilla = fh.read()
    return {rel: F.replace_once(vanilla, old, new, name), "mod.ini": F.mod_ini(name)}


def m4_fixtures(game_dir=GAME):
    """`{name: {relpath: bytes}}` of QMTestM4Hook, QMTestM4Near and QMTestM4Split."""
    import fixtures as F
    split = _one_line_fixture(SPLIT_FIXTURE, SPLIT_FIXTURE_FILE, SPLIT_DECL[0], SPLIT_DECL[1],
                              game_dir)
    split[SPLIT_FIXTURE_FILE] = F.replace_once(split[SPLIT_FIXTURE_FILE], SPLIT_USE[0],
                                               SPLIT_USE[1], SPLIT_FIXTURE)
    return {HOOK_FIXTURE: _one_line_fixture(HOOK_FIXTURE, HOOK_FIXTURE_FILE, HOOK_FIXTURE_OLD,
                                            HOOK_FIXTURE_NEW, game_dir),
            NEAR_FIXTURE: _one_line_fixture(NEAR_FIXTURE, NEAR_FIXTURE_FILE, NEAR_FIXTURE_OLD,
                                            NEAR_FIXTURE_NEW, game_dir),
            SPLIT_FIXTURE: split}


def split_oracle(cand):
    """The validator's verdict with QMTestM4Split's dependency: its second edit
    without its first does not compile; everything else as duplicate_var_oracle."""
    use = SPLIT_USE[1].split(b";", 1)[1].rstrip(b"\r\n")
    decl = SPLIT_DECL[1].split(b";", 1)[1].rstrip(b"\r\n")
    if any(use in v for v in cand.values) and not any(decl in v for v in cand.values):
        return False
    return duplicate_var_oracle(cand)


def write_hook_fixture(out_dir=FIXTURES, game_dir=GAME):
    """Write QMTestM4Hook and QMTestM4Near under `out_dir`; the folder of each."""
    game = os.path.normcase(os.path.abspath(game_dir))
    done = []
    for name, files in sorted(m4_fixtures(game_dir).items()):
        target = os.path.join(out_dir, name)
        if os.path.normcase(os.path.abspath(target)).startswith(game):
            raise SystemExit("refusing to build a fixture inside the game folder")
        if os.path.isdir(target):
            shutil.rmtree(target)
        for rel, data in sorted(files.items()):
            full = os.path.join(target, *rel.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as fh:
                fh.write(data)
        done.append(target)
    return ", ".join(done)


def bootfixture(run_dir, label="a", out_dir=FIXTURES, dist_mod=hbuild.DIST_MOD):
    """fixtures/QMTestM4Gen: dist/Quartermaster with the files generation
    `label` wrote into its sandbox mirror laid over it - Quartermaster's folder
    as it is after that generation. Deployed alone, it shows that the written
    bytes compile and run natively (the milestone's "the game still boots")."""
    src = run_dir
    if os.path.isdir(os.path.join(run_dir, "qm_test_out")):
        src = os.path.join(run_dir, "qm_test_out")
    mirror = os.path.join(src, "m4", label, "qmdir")
    if not os.path.isdir(mirror):
        raise SystemExit("no sandbox mirror at %s" % mirror)
    target = os.path.join(out_dir, BOOT_FIXTURE)
    game = os.path.normcase(os.path.abspath(GAME))
    if os.path.normcase(os.path.abspath(target)).startswith(game):
        raise SystemExit("refusing to build a fixture inside the game folder")
    if os.path.isdir(target):
        shutil.rmtree(target)
    shutil.copytree(dist_mod, target)
    for dirpath, _dirs, names in os.walk(mirror):
        for n in names:
            full = os.path.join(dirpath, n)
            rel = os.path.relpath(full, mirror)
            os.makedirs(os.path.dirname(os.path.join(target, rel)), exist_ok=True)
            shutil.copyfile(full, os.path.join(target, rel))
    return target


def main(argv=None, out=print):
    p = argparse.ArgumentParser(prog="m4cases.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cases")
    c.add_argument("--out", required=True)
    sub.add_parser("expect")
    k = sub.add_parser("check")
    k.add_argument("run")
    k.add_argument("--game-dir", default=GAME)
    k.add_argument("--fixtures-dir", default=FIXTURES)
    k.add_argument("--dist", default=hbuild.DIST_MOD)
    h = sub.add_parser("hookfixture")
    h.add_argument("--out", default=FIXTURES)
    b = sub.add_parser("bootfixture")
    b.add_argument("run")
    b.add_argument("--label", default="a")
    b.add_argument("--out", default=FIXTURES)
    a = p.parse_args(argv)
    if a.cmd == "cases":
        os.makedirs(a.out, exist_ok=True)
        for name, data in sorted(cases(idx_entries()).items()):
            with open(os.path.join(a.out, name), "wb") as fh:
                fh.write(data)
            out("wrote %s (%d bytes)" % (os.path.join(a.out, name), len(data)))
        return 0
    if a.cmd == "expect":
        for name, names in sorted(expected_failures().items()):
            out("%s: %s" % (name, " ".join("--expect-compile-error " + n for n in names)
                            or "(none)"))
        return 0
    if a.cmd == "check":
        return check(a.run, a.game_dir, a.fixtures_dir, a.dist, out)
    if a.cmd == "hookfixture":
        out("built %s" % write_hook_fixture(a.out))
        return 0
    target = bootfixture(a.run, a.label, a.out)
    out("built %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
