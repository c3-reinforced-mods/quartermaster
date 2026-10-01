r"""SelfTest merge cases for the game-side diff and merge (plan G8, G9).

    python tools/m3cases.py                 write fixtures/m3cases/
    python tools/m3cases.py --check         exit 1 if fixtures/m3cases/ is not what
                                            this generator makes now
    python tools/m3cases.py --compare DIR   compare a SelfTest out folder (hrun's
                                            <run folder>\qm_test_out) with the
                                            expected files; exit 1 on a mismatch
                            [--rows-only]   ... the rows only, not the output files

Every case is one three-way merge: a vanilla `.inc` of the installed game, one
or more participants in canonical order, and optionally Quartermaster's hook
lines. What the game must produce is computed here by `ref.merge` - the rows of
`result_rows` and the bytes of `merge_inc` - so an in-game run is compared with
the twin, never with a second implementation. The output bytes are those of
the raw writer (`merge_inc(..., writer="raw")`, decided 2026-09-28);
`--compare --rows-only` checks the classification alone, which does not
depend on how files are read or written.

The cases are made of GSC's own files, so fixtures/ (gitignored) holds them and
nothing of them is tracked:

    fixtures/m3cases/QMTestM3/          deployed as mods\QMTestM3 for the run
        mod.ini
        m3/suite.inc                    one `;case ...` Code value per merge
        m3/<case>_p<i>.inc              the participants
        m3/<case>_h.inc                 the hook lines, when the case has some
    fixtures/m3cases/cases/qm_m3.cfg    the SelfTest case file (hrun --case)
    fixtures/m3cases/expected/<case>.txt   the rows, as the game's raw writer
                                           writes them
    fixtures/m3cases/expected/<case>.inc   the output file, when one is written
    fixtures/m3cases/manifest.json      per case: base, participants, tags and
                                        the expected summary

Nothing in QMTestM3 is under `data\`, so deploying it overrides no game file;
the game only registers the folder. Participant files keep vanilla's bytes
around the Code block and carry the edited Code values in vanilla's own
spelling (`      [*] = <value>`, CRLF).

The cases are deterministic: fixed seeds, sorted inputs, no timestamps. They
change only when the installed game's vanilla files change (a GSC patch) - then
regenerate and rerun.
"""
import argparse
import hashlib
import json
import os
import random
import shutil
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for _p in (REPO, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fixtures as F  # noqa: E402
import hbuild  # noqa: E402
from ref import diff as D  # noqa: E402
from ref import inc as I  # noqa: E402
from ref import merge as M  # noqa: E402
from ref import planner as PL  # noqa: E402
from ref.order import canonical_order  # noqa: E402
from ref.textio import BOM, escape, write_file  # noqa: E402

OUT = os.path.join(REPO, "fixtures", "m3cases")
FIXTURE = "QMTestM3"
#: Where the game finds the fixture: relative to the game folder, which the
#: case state prefixes with ExtractFilePath(GetApplicationFileName).
GAME_REL = "mods\\" + FIXTURE + "\\m3\\"
SUITE = "suite.inc"
CASE_FILE = "qm_m3.cfg"
CRLF = b"\r\n"
PREFIX = I.CODE_PREFIX

ONCAMERA = "data/gui/menu.inc/oncamera.inc"
PROGRESSWARAI = "data/scripts/units/global.inc/progresswarai.inc"

#: The M0 diff fixtures (capability probe 6): progresswarai.inc with n scattered
#: edits, seed n. The game logged D and hunks for the first three (cap.0.log
#: :186, :194, :198); the fourth went over that run's cap of 706 and is inside
#: the cap of 998.
M0_CASES = (50, 300, 500, 600)

HOOK_LINES = [b";// qm hook line: once-per-process guard",
              b";if (gInterface.gamemode=gc_gamemode_mainmenu) then",
              b";begin",
              b";end;"]


class CaseError(RuntimeError):
    pass


class Case(object):
    """One merge: `base` is a vanilla path (`/`, starting with data/)."""

    def __init__(self, name, base, parts, hook=None, tags=()):
        self.name = name
        self.base = base
        self.parts = parts
        self.hook = hook
        self.tags = list(tags)


# ------------------------------------------------------------ the inputs
def vanilla(game, rel):
    return F.vanilla(game, rel)


def with_values(inc, values):
    """A participant file: vanilla's bytes around Code, `values` as its lines."""
    if inc.form != "struct":
        raise CaseError("%s: only struct-form files take edited Code values"
                        % inc.name.decode("latin-1"))
    return inc.head + b"".join(PREFIX + v + CRLF for v in values) + inc.tail


def hook_file(values):
    """The hook lines as a one-state `.inc` the parser reads like any other."""
    lines = ([b"section.begin", b"   Name = qmM3Hook", b"   Code : struct.begin"]
             + [PREFIX + v for v in values]
             + [b"   struct.end", b"section.end", b""])
    return CRLF.join(lines) + CRLF


def merge_bases(game):
    """Struct-form vanilla `.inc` on the plan S3 merge allow-list, by path."""
    data = os.path.join(game, "data")
    out = []
    for root, dirs, names in os.walk(data):
        dirs.sort()
        for n in sorted(names):
            if not n.lower().endswith(".inc"):
                continue
            rel = os.path.relpath(os.path.join(root, n), data).replace(os.sep, "/").lower()
            if hbuild.classify(rel, False) != "merge":
                continue
            raw = vanilla(game, "data/" + rel)
            try:
                inc = I.parse(raw)
            except I.IncFormatError:
                continue
            if inc.form == "struct" and inc.values:
                out.append(("data/" + rel, inc))
    return out


# ------------------------------------------------------- the named cases
def probe5_mods(vanilla_bytes):
    """Mods A and B exactly as the probe-5 merge built them (make_probe5 A/B).

    Its game-side merge wrote 5 hunks, 1 conflict and a 74-line file.
    """
    lines = vanilla_bytes.split(CRLF)
    p = b"      [*] = ;"
    first = next(i for i, ln in enumerate(lines) if ln.startswith(p))
    ks = lines.index(p + b"var keySpeed : Float = gProfile.keyscrollspeed*4;")
    last = max(i for i, ln in enumerate(lines) if ln.startswith(p))
    a = list(lines)
    a[ks] = p + b"var keySpeed : Float = gProfile.keyscrollspeed*5;"
    a.insert(first, p + b"Log('HPROBE merge: change from A (line inserted at top)');")
    b = list(lines)
    b[first + 1] = p + b"begin Log('HPROBE merge: change from B (exit line replaced)'); exit; end;"
    b[ks] = p + b"var keySpeed : Float = gProfile.keyscrollspeed*6;"
    b[last] = p + b"SetCameraElasticMoveTurnOff(); // B changed the last line"
    return CRLF.join(a), CRLF.join(b)


def m0_fixture(data, n_edits, seed):
    """progresswarai.inc with `n_edits` scattered edits, as the M0 probe made it.

    Only code lines are touched; the kinds rotate change / insert / delete and
    the positions are spread evenly with jitter. Byte for byte the files the
    in-game Myers run read.
    """
    lines = data.split(CRLF)
    p = b"      [*] = ;"
    code_idx = [i for i, ln in enumerate(lines) if ln.startswith(p)]
    rnd = random.Random(seed)
    step = len(code_idx) / float(n_edits)
    picks = []
    for e in range(n_edits):
        lo = int(e * step)
        hi = max(lo, int((e + 1) * step) - 1)
        picks.append(code_idx[rnd.randint(lo, hi)])
    kinds = ("change", "insert", "delete")
    todo = dict((li, kinds[e % 3]) for e, li in enumerate(sorted(set(picks))))
    out = []
    for i, ln in enumerate(lines):
        kind = todo.get(i)
        if kind == "change":
            out.append(ln + b" // qm edit " + str(i).encode("ascii"))
        elif kind == "insert":
            out.append(ln)
            out.append(p + b"// qm inserted after line " + str(i + 1).encode("ascii"))
        elif kind == "delete":
            continue
        else:
            out.append(ln)
    return CRLF.join(out)


def changed_lines(inc, count, extra_insert=False, stride=None):
    """`count` Code values replaced by unique lines: D = 2*count exactly.

    Every new line is unique, so the longest common subsequence is the
    n - count untouched lines and the edit distance is 2*count (plus one for
    the extra unique insertion). That puts a case on either side of the cap.
    """
    values = list(inc.values)
    n = len(values)
    stride = stride or max(1, n // (count + 1))
    spots = [stride * (k + 1) - 1 for k in range(count)]
    if spots[-1] >= n:
        raise CaseError("%d changes do not fit %d lines" % (count, n))
    for k, pos in enumerate(spots):
        values[pos] = b";// qm cap change %d" % k
    if extra_insert:
        values.insert(0, b";// qm cap insertion")
    return values


def replacement(inc, share_num, share_den, tag):
    """The first share of the values replaced by new lines (a rewrite)."""
    values = list(inc.values)
    cut = (len(values) * share_num) // share_den
    return [b";// qm %s rewrite %d" % (tag, k) for k in range(cut)] + values[cut:]


def named_cases(game, reference):
    cases = []

    def add(tag, base, parts, hook=None, tags=()):
        cases.append(Case(tag, base, parts, hook, [tag] + list(tags)))

    oc = vanilla(game, ONCAMERA)
    a, b = probe5_mods(oc)
    pair = [(b"mods\\HProbeMergeA", a), (b"mods\\HProbeMergeB", b)]
    add("probe5", ONCAMERA, pair, tags=["timing-oncamera"])
    add("probe5_hook", ONCAMERA, pair, HOOK_LINES[:2], tags=["hook"])

    mods = F.build_all(game, reference)
    combos = (("wasd_camspeed", [F.WASD, F.CAMSPEED]),
              ("wasd_conflict", [F.WASD, F.CONFLICT]),
              ("wasd_broken", [F.WASD, F.BROKEN]),
              ("wasd_camspeed_conflict", [F.WASD, F.CAMSPEED, F.CONFLICT]))
    for tag, names in combos:
        dirs = canonical_order([b"mods\\" + n.encode("ascii") for n in names])
        order = [d[len(b"mods\\"):].decode("ascii") for d in dirs]
        paths = sorted({rel for n in names for rel in mods[n]
                        if rel.endswith(".inc")})
        for rel in paths:
            parts = [(("mods\\" + n).encode("ascii"), mods[n][rel])
                     for n in order if rel in mods[n]]
            stem = rel.rsplit("/", 1)[-1][:-len(".inc")]
            add("%s_%s" % (tag, stem), "data/" + rel[len("data/"):], parts,
                tags=["fixtures"] + (["timing-oncamera"] if rel == ONCAMERA else []))

    pw_bytes = vanilla(game, PROGRESSWARAI)
    pw = I.parse(pw_bytes)
    for n in M0_CASES:
        add("m0_b%d" % n, PROGRESSWARAI, [(b"p0", m0_fixture(pw_bytes, n, n))],
            tags=["m0"] + (["timing-progresswarai"] if n == 50 else []))
    # Two participants with 50 scattered edits each, on different lines.
    add("pw_50x2", PROGRESSWARAI,
        [(b"p0", m0_fixture(pw_bytes, 50, 50)), (b"p1", m0_fixture(pw_bytes, 50, 5051))],
        tags=["timing-progresswarai"])
    # Either side of the D cap: 499 changes (D = 998) fit, one line more does not.
    cap = D.d_cap(D.DEFAULT_BUDGET)
    small = list(pw.values)
    small[100] = b";// qm small edit"
    add("dcap_998", PROGRESSWARAI, [(b"p0", with_values(pw, changed_lines(pw, cap // 2)))],
        tags=["dcap"])
    add("dcap_999", PROGRESSWARAI,
        [(b"p0", with_values(pw, changed_lines(pw, cap // 2, extra_insert=True))),
         (b"p1", with_values(pw, small))], tags=["dcap"])
    add("dcap_b750", PROGRESSWARAI, [(b"p0", m0_fixture(pw_bytes, 750, 750))],
        tags=["dcap"])
    # Over the line cap: the diff refuses before it reads a line.
    big = list(I.parse(oc).values) + [b";// qm line %d" % k for k in range(D.MAX_LINES)]
    add("too_many_lines", ONCAMERA,
        [(b"p0", with_values(I.parse(oc), big)), (b"p1", a)], tags=["limits"])

    # Replacement (plan G9: > 50% of vanilla lines deleted or replaced).
    rs_rel = F.REGISTERSHORTCUTS
    rs = I.parse(vanilla(game, rs_rel))
    rewrite = with_values(rs, replacement(rs, 3, 4, b"repl"))
    edit = list(rs.values)
    edit[-3] = edit[-3] + b" // qm small edit"
    other = with_values(rs, edit)
    add("repl_wta", rs_rel, [(b"p0", rewrite), (b"p1", other)], tags=["replacement"])
    add("repl_wta_hook", rs_rel, [(b"p0", rewrite), (b"p1", other)], HOOK_LINES,
        tags=["replacement", "hook"])
    add("repl_alone", rs_rel, [(b"p0", rewrite), (b"p1", vanilla(game, rs_rel))],
        tags=["replacement"])
    add("repl_same", rs_rel, [(b"p0", rewrite), (b"p1", rewrite)], tags=["replacement"])
    add("repl_later", rs_rel, [(b"p0", other), (b"p1", rewrite)], tags=["replacement"])
    half = len(rs.values)
    exact = with_values(rs, [b";// qm half %d" % k for k in range(half // 2)]
                        + rs.values[half // 2:])
    over = with_values(rs, [b";// qm half %d" % k for k in range(half // 2 + 1)]
                       + rs.values[half // 2 + 1:])
    add("repl_half", rs_rel, [(b"p0", exact), (b"p1", other)], tags=["replacement"])
    add("repl_half_plus", rs_rel, [(b"p0", over), (b"p1", other)], tags=["replacement"])

    # Comparison keys: BOM on a file's first value, tabs and trailing blanks.
    ocv = I.parse(oc)
    v = list(ocv.values)
    bom0 = [BOM + v[0]] + v[1:]
    bom3 = v[:3] + [BOM + v[3]] + v[4:]
    add("key_bom", ONCAMERA, [(b"p0", with_values(ocv, bom0)), (b"p1", with_values(ocv, bom3))],
        tags=["keys"])
    ws = list(v)
    ws[5] = ws[5] + b"  "
    ws[9] = ws[9] + b"\t"
    ws[12] = ws[12].replace(b" ", b"\t", 1)
    x1 = list(v)
    x1[20] = b";var qmX : Integer = 1;"
    x2 = list(v)
    x2[20] = b";var qmX : Integer = 1; \t"
    add("key_whitespace", ONCAMERA,
        [(b"p0", with_values(ocv, ws)), (b"p1", with_values(ocv, x1)),
         (b"p2", with_values(ocv, x2))], tags=["keys"])
    add("vanilla_only", ONCAMERA, [(b"p0", with_values(ocv, ws)), (b"p1", oc)],
        HOOK_LINES[:1], tags=["keys", "hook"])

    # The hook files of plan S5: Quartermaster's lines go in at the hook index
    # of the result (after the routines a state starts with: cameracontrol.inc
    # 8, doprogress.inc 10, the other two 0), wherever the merge moved it.
    for h in PL.HOOK_FILES:
        rel = "data/" + h.decode("ascii").replace("\\", "/")
        inc = I.parse(vanilla(game, rel))
        v = list(inc.values)
        stem = rel.rsplit("/", 1)[-1][:-len(".inc")]
        below = list(v)
        below[len(v) // 2] = below[len(v) // 2] + b" // qm edit below the hook"
        parts = [(b"p0", with_values(inc, below))]
        if I.hook_index(v):
            inside = list(v)
            inside.insert(2, b";   // qm line inside the leading routine")
            parts.append((b"p1", with_values(inc, inside)))
        at = list(v)
        at.insert(I.hook_index(v), b";// qm line where the hook goes")
        parts.append((b"p%d" % len(parts), with_values(inc, at)))
        add("hookfile_" + stem, rel, parts, HOOK_LINES, tags=["hook", "hook-file"])
    cc_rel = "data/gui/menu.inc/cameracontrol.inc"
    cc = I.parse(vanilla(game, cc_rel))
    add("hookfile_cameracontrol_wta", cc_rel,
        [(b"p0", with_values(cc, replacement(cc, 3, 4, b"cc"))),
         (b"p1", with_values(cc, cc.values[:-1] + [cc.values[-1] + b" // qm last"]))],
        HOOK_LINES, tags=["hook", "hook-file", "replacement"])
    return cases


# ------------------------------------------------------ the random cases
class Op(object):
    """Replace vanilla values [pos, pos+span) with `lines`."""

    def __init__(self, pos, span, lines):
        self.pos = pos
        self.span = span
        self.lines = lines

    def end(self):
        return self.pos + self.span


def apply_ops(values, ops):
    out = list(values)
    for op in sorted(ops, key=lambda o: (o.pos, o.span), reverse=True):
        out[op.pos:op.end()] = op.lines
    return out


def _free(ops, pos, span):
    """No op of this participant touches [pos, pos+span] (a gap of one line
    keeps two ops from reading as one)."""
    for o in ops:
        if pos <= o.end() and o.pos <= pos + span:
            return False
    return True


def whitespace_variant(line):
    """The same comparison key, other bytes (a tab for one space, blanks at the end)."""
    if b" " in line[1:]:
        return line[:1] + line[1:].replace(b" ", b"\t", 1)
    return line + b" \t"


def random_ops(rng, values, tag, others, want):
    """`want` ops on `values` for one participant, some sharing positions or
    exact edits with `others` (earlier participants' ops) on purpose."""
    n = len(values)
    ops = []
    tries = 0
    while len(ops) < want and tries < want * 20:
        tries += 1
        roll = rng.random()
        src = [o for os_ in others for o in os_]
        if src and roll < 0.18:
            o = rng.choice(src)                      # the very same edit
            cand = Op(o.pos, o.span, list(o.lines))
        elif src and roll < 0.36:
            o = rng.choice(src)                      # same place, other text
            span = o.span if rng.random() < 0.6 else rng.randint(0, 2)
            cand = Op(o.pos, min(span, n - o.pos),
                      [b";// qm %s conflict %d" % (tag, len(ops))])
        elif src and roll < 0.52:
            o = rng.choice(src)                      # a few lines away
            pos = o.end() + rng.randint(0, 5) if rng.random() < 0.5 else o.pos - rng.randint(1, 5)
            pos = max(0, min(n, pos))
            span = rng.randint(0, 1) if pos < n else 0
            cand = Op(pos, span, [b";// qm %s near %d" % (tag, len(ops))])
        else:
            pos = rng.randint(0, n)
            kind = rng.random()
            if pos == n or kind < 0.3:               # insertion
                if rng.random() < 0.3 and n:
                    new = [values[rng.randrange(n)]]  # a copy of a vanilla line: ties
                else:
                    new = [b";// qm %s ins %d.%d" % (tag, len(ops), k)
                           for k in range(rng.randint(1, 3))]
                cand = Op(pos, 0, new)
            elif kind < 0.55:                        # deletion
                cand = Op(pos, min(rng.randint(1, 3), n - pos), [])
            elif kind < 0.65:                        # the same key in other bytes
                cand = Op(pos, 1, [whitespace_variant(values[pos])])
            else:                                    # change
                span = min(rng.randint(1, 3), n - pos)
                cand = Op(pos, span, [values[pos] + b" // qm %s chg %d" % (tag, len(ops))]
                          + [b";// qm %s new %d.%d" % (tag, len(ops), k)
                             for k in range(rng.randint(0, 2))])
        if cand.pos + cand.span <= n and _free(ops, cand.pos, cand.span):
            ops.append(cand)
    return ops


def random_case(rng, name, bases):
    rel, inc = rng.choice(bases)
    values = inc.values
    count = rng.choice((1, 2, 2, 2, 3, 3, 4))
    all_ops, parts, tags = [], [], ["random"]
    for i in range(count):
        roll = rng.random()
        if i and roll < 0.08:
            data = parts[rng.randrange(i)][1]          # the same file as an earlier one
            tags.append("same-file")
            all_ops.append([])
        elif roll < 0.14:
            data = with_values(inc, list(values))      # changes nothing
            all_ops.append([])
        elif roll < 0.18 and len(values) >= 8:
            cut = len(values) // 2 + rng.randint(1, max(1, len(values) // 4))
            new = [b";// qm %s p%d rewrite %d" % (name.encode(), i, k) for k in range(cut)]
            data = with_values(inc, new + list(values[cut:]))
            tags.append("rewrite")
            all_ops.append([])
        else:
            ops = random_ops(rng, values, b"%s p%d" % (name.encode(), i), all_ops,
                             rng.randint(1, 8))
            data = with_values(inc, apply_ops(values, ops))
            all_ops.append(ops)
        parts.append((b"p%d" % i, data))
    hook = None
    if rng.random() < 0.12:
        hook = HOOK_LINES[:rng.randint(1, len(HOOK_LINES))]
        tags.append("hook")
    return Case(name, rel, parts, hook, tags)


def build_cases(game=None, reference=None, count=290, seed=20260928):
    """Every case, named ones first, then `count` seeded random ones."""
    game = game or F.default_game()
    reference = reference or F.default_reference(game)
    cases = named_cases(game, reference)
    rng = random.Random(seed)
    bases = [b for b in merge_bases(game) if len(b[1].values) <= 2000]
    for k in range(count):
        cases.append(random_case(rng, "r%03d" % k, bases))
    for k, c in enumerate(cases):
        c.name = "m3c_%03d_%s" % (k, c.name)
    return cases


# ------------------------------------------------------------ expected
def rel_game(rel):
    r"""`data/gui/x.inc` -> `gui\x.inc`, the spelling of vanilla.idx."""
    return rel[len("data/"):].replace("/", "\\")


def expected(case, game):
    """`(MergeResult, rows, output bytes or None)` - what the game must write."""
    result, out = M.merge_inc(vanilla(game, case.base), case.parts, hook=case.hook,
                              writer="raw")
    rows = M.result_rows(result)
    if M.final_lines(result, case.hook) is None:
        out = None
    return result, rows, out


def dump_bytes(rows):
    """The rows as the game's raw writer writes them (CRLF, space padding)."""
    return write_file([escape(r) for r in rows])


def _one_state(name, values):
    lines = ([b"section.begin", b"   Name = " + name, b"   Code : struct.begin"]
             + [PREFIX + v for v in values] + [b"   struct.end", b"section.end", b""])
    for v in values:
        if any(c < 32 or c > 126 for c in v) or b"  " in v or v.endswith(b" "):
            raise CaseError("%r is not one line of single-spaced printable ASCII" % v)
    return CRLF.join(lines) + CRLF


def render_tree(cases, game):
    """`({path under fixtures/m3cases: bytes}, manifest)`."""
    files = {}
    suite = []
    manifest = []
    root = FIXTURE + "/m3/"
    for c in cases:
        result, rows, out = expected(c, game)
        names = []
        for i, (_mod, data) in enumerate(c.parts):
            fn = "%s_p%d.inc" % (c.name, i)
            files[root + fn] = data
            names.append(GAME_REL + fn)
        hook = "-"
        if c.hook is not None:
            fn = "%s_h.inc" % c.name
            files[root + fn] = hook_file(c.hook)
            hook = GAME_REL + fn
        suite.append(("case %s %s %s %s" % (c.name, rel_game(c.base), hook,
                                            " ".join(names))).encode("ascii"))
        files["expected/%s.txt" % c.name] = dump_bytes(rows)
        if out is not None:
            files["expected/%s.inc" % c.name] = out
        manifest.append({
            "name": c.name, "tags": c.tags, "base": rel_game(c.base),
            "participants": [m.decode("latin-1") for m, _d in c.parts],
            "hook_lines": 0 if c.hook is None else len(c.hook),
            "mode": result.mode, "status": result.status, "reason": result.reason,
            "winner": result.winner, "hunks": len(result.hunks),
            "conflicts": result.conflicts, "proximity": len(result.pairs),
            "lines": len(result.lines), "output": out is not None,
            "outlines": 0 if out is None else len(M.final_lines(result, c.hook)),
            "d": [p.d for p in result.participants],
            "part_hunks": [sum(1 for h in result.hunks if h.participant == i)
                           for i in range(len(result.participants))],
        })
    files[root + SUITE] = _one_state(b"qmM3Suite", [b";" + s for s in suite])
    files[FIXTURE + "/mod.ini"] = F.mod_ini(FIXTURE)
    files["cases/" + CASE_FILE] = _one_state(
        b"qmTestCase", [b";kind merge", b";suite " + (GAME_REL + SUITE).encode("ascii")])
    files["manifest.json"] = (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode("ascii")
    return files, manifest


# ----------------------------------------------------------- the files
def _inside(path, root):
    path, root = os.path.normcase(os.path.realpath(path)), os.path.normcase(
        os.path.realpath(root))
    return os.path.commonpath([path, root]) == root


def read_tree(root):
    out = {}
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            path = os.path.join(dirpath, n)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, "rb") as fh:
                out[rel] = fh.read()
    return out


def write_tree(files, out=OUT, game=None):
    game = game or F.default_game()
    if _inside(out, game):
        raise CaseError("refusing to write inside the game folder: %s" % out)
    if os.path.isdir(out):
        shutil.rmtree(out)
    for rel, data in sorted(files.items()):
        path = os.path.join(out, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)


def tree_digest(files):
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode("ascii") + b"\0" + hashlib.sha256(files[rel]).digest())
    return h.hexdigest()


# ------------------------------------------------------------ compare
def compare(game_out, expected_root=OUT, rows_only=False):
    """`(problems, notes)`: a SelfTest out folder against the expected files.

    Problems are mismatches: a rows dump or an output file that differs from
    ref's bytes, an output that should not exist, a merge the game did not
    finish or whose write was refused. Notes carry the timings the case state
    logged. `rows_only` skips the output files and the write status.
    """
    with open(os.path.join(expected_root, "manifest.json"), "rb") as fh:
        manifest = json.loads(fh.read().decode("ascii"))
    exp = os.path.join(expected_root, "expected")
    problems, notes = [], []
    for m in manifest:
        name = m["name"]
        want = _read(os.path.join(exp, name + ".txt"))
        got = _read(os.path.join(game_out, name + ".txt"))
        if got is None:
            problems.append("%s: no rows dump" % name)
        elif got != want:
            problems.append("%s: rows differ: %s" % (name, _first_difference(want, got)))
        if rows_only:
            continue
        want = _read(os.path.join(exp, name + ".inc"))
        got = _read(os.path.join(game_out, name + ".inc"))
        if want is None and got is not None:
            problems.append("%s: an output file was written; ref writes none" % name)
        elif want is not None and got is None:
            problems.append("%s: no output file" % name)
        elif want is not None and got != want:
            problems.append("%s: output differs (%d bytes, ref %d; sha256 %s, ref %s)"
                            % (name, len(got), len(want), hashlib.sha256(got).hexdigest()[:12],
                               hashlib.sha256(want).hexdigest()[:12]))
    summary = _read(os.path.join(game_out, os.path.splitext(CASE_FILE)[0] + ".txt"))
    if summary is None:
        problems.append("no %s summary from the case state" % CASE_FILE)
    else:
        rows = [r.split(b"|") for r in summary.split(CRLF) if r.strip()]
        done = dict((r[1].decode("latin-1"), r) for r in rows if r[0] == b"m3case")
        for r in rows:
            if r[0] == b"m3call":
                notes.append("call %s: %s merges in %s ms (the read pool's allocation "
                             "included)" % tuple(x.decode("latin-1") for x in r[1:4]))
        for m in manifest:
            r = done.get(m["name"])
            if r is None:
                problems.append("%s: not run" % m["name"])
            elif r[2] != b"1":
                problems.append("%s: qmMerge did not finish" % m["name"])
            else:
                written = r[3].decode("latin-1")
                if not rows_only and written != ("yes" if m["output"] else "none"):
                    problems.append("%s: written=%s, ref %s" % (m["name"], written,
                                                                "yes" if m["output"] else "none"))
                if set(m["tags"]) & {"timing-oncamera", "timing-progresswarai"}:
                    notes.append("%s ms total=%s load=%s diff=%s merge=%s write=%s"
                                 % ((m["name"],) + tuple(x.decode("latin-1") for x in r[4:9])))
    return problems, notes


def _read(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return fh.read()


def _first_difference(want, got):
    a, b = want.split(CRLF), got.split(CRLF)
    for k, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return "row %d: game %r, ref %r" % (k, y[:80], x[:80])
    return "game %d rows, ref %d" % (len(b), len(a))


# ---------------------------------------------------------------- CLI
def main(argv=None, out=print):
    p = argparse.ArgumentParser(prog="m3cases.py", description=__doc__.split("\n\n")[0])
    p.add_argument("--check", action="store_true")
    p.add_argument("--compare", metavar="DIR")
    p.add_argument("--rows-only", action="store_true")
    p.add_argument("--out", default=OUT)
    p.add_argument("--game-dir", default=None)
    p.add_argument("--reference-dir", default=None)
    a = p.parse_args(argv)
    if a.compare:
        problems, notes = compare(a.compare, a.out, a.rows_only)
        for line in notes:
            out("  " + line)
        for line in problems:
            out("MISMATCH " + line)
        out("%d mismatch(es)" % len(problems))
        return 1 if problems else 0
    game = a.game_dir or F.default_game()
    cases = build_cases(game, a.reference_dir)
    files, manifest = render_tree(cases, game)
    if a.check:
        have = read_tree(a.out) if os.path.isdir(a.out) else {}
        if have != files:
            out("fixtures/m3cases differs from the generator (%d files there, %d made); "
                "run python tools/m3cases.py" % (len(have), len(files)))
            return 1
        out("fixtures/m3cases up to date: %d cases, %d files, %s"
            % (len(cases), len(files), tree_digest(files)[:16]))
        return 0
    write_tree(files, a.out, game)
    out("wrote %d cases, %d files, %d bytes into %s (digest %s)"
        % (len(cases), len(files), sum(len(d) for d in files.values()), a.out,
           tree_digest(files)[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
