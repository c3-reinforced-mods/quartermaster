r"""SelfTest (docs/plan.md G18): case files in, dump files out, compared here.

The game side (src/states/qmselftest.pas and the qmCase* states) is inert
unless `<save>\qm_autotest.cfg` exists; then it runs every case file in
`<save>\qm_test\cases\` and writes what it saw into `<save>\qm_test\out\`.
Nothing in the game decides pass or fail: it dumps, and this module computes
what the dump must be from the same inputs, so the comparison is done by the
twin that the rest of `ref/` is proven against.

Case files
----------
A case file has exactly the shape of a one-state `.inc` (the shape of
data/gui/menu.inc/cameracontrol.inc:1-38, whose round trip through the
engine's parser is verified byte for byte), so the game reads it with the
same parser calls as any `.inc`:

    section.begin
       Name = qmTestCase
       Code : struct.begin
          [*] = ;kind readdump
          [*] = ;raw game\var\hotkeys.cfg
          [*] = ;inc gui\menu.inc\oncamera.inc
       struct.end
    section.end
    <empty line>

Each Code value is one directive, `<verb> <arg> ...`, single spaces, after the
`;` the parser hands back with every value. The first is `kind <kind>`. Only
Code values are read: reading a key such as `Name` from the root of a loaded
file is not verified, reading Code values is (probes 4 and 5). The parser
drops trailing spaces from values (run m2a); a directive never ends in one.

Kinds and their directives (paths are vanilla.idx paths, relative to data\;
sizes are vanilla.idx sizes, for the raw reader, which reads exactly that many
bytes):

  readdump  inc <path>                   the parser's view: Code count, hash
            incraw <path> <size>         raw reader + the line model of the
                                         game's qmIncFromLines
            raw <path> <size>            the raw reader: line count, hashes
            rawh <path>                  the same, size not given (the
                                         handle-based reader)
            incat <path> <size>          qmIncReadAt into one pool after the
                                         files before it, and qmIncHookIndex
            incatend                     every incat span hashed again
            rt <path> <out> <size>       read raw, write the lines back to
                                         <out>, read that back with the size
                                         the writer reports; equal compared?
            norm <path> <out> <size>     write the compared form
            incw <path> <out> <n> <size> the `.inc` writer (qmIncRender): the
                                         file's first n values, or all and
                                         then `;// qm appended <k>`
  incprobe  probe <path>                 what the parser makes of a vanilla
                                         file, saved unchanged and after one
                                         edit
            synth <name> <text>          a synthetic `.inc` written raw, read
                                         by the parser: what it does with tabs,
                                         leading and trailing spaces, other
                                         bytes, and four ways to append
  eofprobe  file <path> <size>           the two integer readers at and past
                                         the end of a file
  bisect    aix <name> <text>            candidate states, written and loaded
            state <name>                 at run time: which ones compile
  merge     (tools/m3cases.py)           the three-way merge suite
  m4gen     (tools/m4cases.py)           validation copies, generations into a
                                         sandbox, stale cleanup, manifest, report
  plan      (none)                       mod list, index, plan, fingerprint
  keys      (none)                       every scanned path as a parser key
  ui        cycles <n>                   the manager window (docs/ui.md), driven
            toggle <dir>                 by GUI tags: n open/close cycles, then
            keep 1                       deactivate, Apply, Enter, Apply, Esc,
                                         Esc on the mod <dir> (`ui_expected`);
                                         with keep, once per run and the Apply
                                         left for qmTick (`ui_keep_*`)

Dumps
-----
`<out>\<case file stem>.txt`, written by the game's raw writer: one line per
fact, fields separated by `|`, CRLF, padded with spaces to a multiple of 4
(`ref.textio.write_file`). Strings that come from the engine or a mod (dirs,
titles, tags) are written in hex, so no byte in them can be mistaken for a
separator. `<out>\done.txt` lists every case and whether its state returned.
"""
from . import inc as I
from .fingerprint import qhash
from .index import (Mod, build_index, canonical_positions, dos_age, fingerprint,
                    find_self, known_fingerprint, vanilla_stamp)
from .planner import plan, plan_lines
from .textio import (compare_form, escape, norm_key_escaped, read_lines,
                     read_raw_lines, write_file)

__all__ = ["CASE_STATE", "KINDS", "APPENDED", "render_case", "parse_case",
           "lines_hash", "dump_bytes", "dump_lines", "parse_dump", "hexs", "unhex",
           "readdump_expected", "incprobe_expected", "eofprobe_expected", "SYNTH",
           "synth_directive", "FORM_CODE", "plan_check", "keys_expected",
           "done_expected", "ui_directives", "ui_expected", "ui_check", "ui_keep_go",
           "ui_keep_wait", "ui_keep_later"]

CASE_STATE = b"qmTestCase"
KINDS = (b"readdump", b"incprobe", b"plan", b"keys", b"eofprobe", b"merge", b"bisect", b"ui",
         b"m4gen", b"m5", b"opt", b"data", b"mod", b"host")
CRLF = b"\r\n"
#: What `incw` appends when asked for more values than the file has.
APPENDED = b";// qm appended %d"
#: What `incprobe` writes: value 0 replaced, one value appended.
PROBE_EDIT = b";// qm edited"
PROBE_APPEND = b";// qm appended"


# ------------------------------------------------------------ case files
def render_case(kind, directives):
    """Case-file bytes: `kind` first, then one Code value per directive."""
    if kind not in KINDS:
        raise ValueError("unknown case kind %r" % kind)
    values = [b";kind " + kind] + [b";" + b" ".join(d) for d in directives]
    for v in values:
        if any(c < 32 or c > 126 for c in v) or b"  " in v or v.endswith(b" "):
            raise ValueError("directive %r is not one line of single-spaced "
                             "printable ASCII" % v)
    lines = ([b"section.begin", b"   Name = " + CASE_STATE, b"   Code : struct.begin"]
             + [I.CODE_PREFIX + v for v in values]
             + [b"   struct.end", b"section.end", b""])
    return b"".join(line + CRLF for line in lines)


def parse_case(data):
    """`(kind, [directive tuples])` - what the game side reads out of a case file."""
    values = [v[1:] if v.startswith(b";") else v for v in I.parse(data).values]
    if not values or not values[0].startswith(b"kind "):
        raise ValueError("a case file starts with 'kind <kind>'")
    kind = values[0][5:]
    if kind not in KINDS:
        raise ValueError("unknown case kind %r" % kind)
    return kind, [tuple(v.split(b" ")) for v in values[1:] if v]


# ----------------------------------------------------------------- dumps
def lines_hash(lines):
    """qhash of the lines joined by LF, LF after the last: the dumps' hash."""
    return qhash(b"".join(line + b"\n" for line in lines))


def dump_bytes(lines):
    """The file the game's raw writer makes of raw dump lines."""
    return write_file([escape(line) for line in lines])


def dump_lines(data):
    """The raw lines of a dump file the game wrote.

    Read back, a file of the raw writer ends in a line of 2-4 spaces (its
    padding plus the EOF filler, `ref.textio.readback_extra_line`). No dump
    line ends in a space, so that line is dropped here.
    """
    lines = read_raw_lines(data)
    if lines and lines[-1] and not lines[-1].strip(b" "):
        lines.pop()
    return lines


def parse_dump(data):
    """Raw dump lines as field tuples."""
    return [tuple(line.split(b"|")) for line in dump_lines(data)]


def hexs(data):
    """How a dump spells an engine string: two lower-case hex digits a byte."""
    return data.hex().encode("ascii")


def unhex(text):
    return bytes.fromhex(text.decode("ascii"))


# -------------------------------------------------------------- readdump
def readdump_expected(directives, vanilla):
    """`(dump lines, {out name: bytes})` a readdump case must produce.

    `vanilla(path)` returns the bytes of `<game>\\data\\<path>`.
    """
    lines, files = [], {}
    pool_at, spans = 0, []
    for d in directives:
        verb = d[0]
        if verb == b"incatend":
            lines.extend([b"|".join([b"incatend", p, h]) for p, h in spans]
                         or [b"incatend|none"])
            continue
        path = d[1]
        data = vanilla(path)
        size = {b"incraw": 2, b"raw": 2, b"rt": 3, b"norm": 3, b"incw": 4, b"incat": 2}.get(verb)
        if size is not None and int(d[size]) != len(data):
            raise ValueError("%s: the directive says %s bytes, the file has %d"
                             % (path.decode(), d[size].decode(), len(data)))
        if verb == b"inc":
            f = I.parse(data)
            if f.form == "none":
                lines.append(b"|".join([b"inc", path, b"-1", lines_hash([])]))
            else:
                values = I.engine_values(f)
                lines.append(b"|".join([b"inc", path, b"%d" % len(values),
                                        lines_hash(values)]))
        elif verb == b"incraw":
            form, keys, values = I.values_from_lines(read_lines(data))
            lines.append(b"|".join([b"incraw", path, b"%d" % FORM_CODE[form],
                                    b"%d" % len(keys), b"%d" % len(values),
                                    lines_hash(values)]))
        elif verb == b"incat":
            form, keys, values = I.values_from_lines(read_lines(data))
            h = lines_hash(values)
            lines.append(b"|".join([b"incat", path, b"%d" % pool_at, b"%d" % len(values),
                                    b"%d" % FORM_CODE[form], b"%d" % len(keys), h,
                                    b"%d" % I.hook_index(I.parse(data).values)]))
            spans.append((path, h))
            pool_at += len(values)
        elif verb in (b"raw", b"rawh"):
            got = read_lines(data)
            cmp = compare_form(got)
            lines.append(b"|".join([verb, path, b"%d" % len(got), lines_hash(got),
                                    lines_hash([norm_key_escaped(t, i == 0)
                                                for i, t in enumerate(got)]),
                                    lines_hash(cmp), b"%d" % len(cmp)]))
        elif verb == b"rt":
            got = read_lines(data)
            written = write_file(got)
            back = read_lines(written)
            files[d[2]] = written
            same = compare_form(back) == compare_form(got)
            lines.append(b"|".join([b"rt", path, d[2], b"%d" % len(got),
                                    b"%d" % len(back), b"1" if same else b"0",
                                    b"%d" % len(written)]))
        elif verb == b"norm":
            cmp = compare_form(read_lines(data))
            files[d[2]] = write_file(cmp)
            lines.append(b"|".join([b"norm", path, d[2], b"%d" % len(cmp)]))
        elif verb == b"incw":
            _form, keys, have = I.values_from_lines(read_lines(data))
            n = int(d[3])
            if n <= len(have):
                values = have[:n]
            else:
                values = have + [APPENDED % k for k in range(n - len(have))]
            written = write_file(I.layout_lines(keys, values))
            back = I.values_from_lines(read_lines(written))[2]
            files[d[2]] = written
            lines.append(b"|".join([b"incw", path, d[2], b"%d" % n,
                                    b"%d" % len(written), b"%d" % len(back),
                                    b"1" if back == values else b"0"]))
        else:
            raise ValueError("readdump has no verb %r" % verb)
    return lines, files


# -------------------------------------------------------------- incprobe
#: How a `Code` form is spelt in a dump: qmIncFromLines's form number.
FORM_CODE = {"none": 0, "single": 1, "struct": 2}

#: The synthetic `.inc` of incprobe's `synth`: values ending in a tab, in
#: space-tab-space, starting after extra spaces, holding `{|}~` and a byte
#: above 127, only spaces, and a plain one.
SYNTH = (b"section.begin\r\n   Name = qmSynth\r\n   Code : struct.begin\r\n"
         b"      [*] = ;a\t\r\n"
         b"      [*] = ;b \t \r\n"
         b"      [*] =   ;c\r\n"
         b"      [*] = ;d{|}~\xe9\r\n"
         b"      [*] =    \r\n"
         b"      [*] = ;e\r\n"
         b"   struct.end\r\nsection.end\r\n\r\n")


def synth_directive(name, data=SYNTH):
    """`(b"synth", name, text)`: `data` as an internal string of letters, digits
    and `~NNN` only.

    The directive is itself a Code value of the case file. No vanilla code
    line holds `struct.begin`, `section.end`, `[*]` or ` = ` inside a value, so
    what the parser would make of them there is unknown; spelling every other
    byte as `~NNN` keeps the directive an ordinary value.
    """
    return (b"synth", name, b"".join(bytes([c]) if chr(c).isalnum() and c < 128
                                     else b"~%03d" % c for c in data))


def incprobe_expected(directives, vanilla):
    """What the parser makes of each probed vanilla file, as run m2a saw it.

    `[(path, form, row, rt bytes, ed bytes)]`, where `row` is the dump row
    without its index: the round trip is `render` of the parser's values
    (`engine_values`), the edit that with value 0 replaced and one value
    appended; a file without Code gets a child named `Code`, which the parser
    writes as `   Code.[*] = ` - not a Code node. `synth` directives are not
    predicted (that is what they are for) and come back as None.
    """
    out = []
    for k, d in enumerate(directives):
        if d[0] != b"probe":
            out.append(None)
            continue
        path = d[1]
        f = I.parse(vanilla(path))
        ev = I.engine_values(f)
        rt = I.render(f, ev)
        if f.form == "none":
            ed = rt.replace(b"section.end\r\n\r\n",
                            b"   Code.[*] = " + PROBE_APPEND + b"\r\nsection.end\r\n\r\n")
            row = [b"0", b"-1", b"%d" % len(f.keys), b"1", b""]
        else:
            ed = I.render(f, [PROBE_EDIT] + ev[1:] + [PROBE_APPEND])
            row = [b"1", b"%d" % len(ev), b"%d" % (len(f.keys) + 1), b"%d" % (len(ev) + 1),
                   hexs(ev[0])]
        out.append((path, f.form, [b"probe", b"%d" % k, path] + row, rt, ed))
    return out


def eofprobe_expected(directives, vanilla):
    """`[(path, size, whole Integers)]`: the values both readers must return for
    the whole integers of each file; what comes after is what the probe finds."""
    out = []
    for d in directives:
        data = vanilla(d[1])
        ints = [int.from_bytes(data[i:i + 4], "little", signed=True)
                for i in range(0, len(data) - len(data) % 4, 4)]
        out.append((d[1], int(d[2]), ints))
    return out


def probe_names(k):
    """The two files incprobe writes for its k-th directive."""
    return (b"probe%d_rt.inc" % k, b"probe%d_ed.inc" % k)


# ------------------------------------------------------------------ plan
def _mods_from_dump(rows):
    mods, pos, origins, ages = [], [], [], []
    for r in rows:
        if r[0] != b"mod":
            continue
        i = int(r[1])
        if i != len(mods):
            raise ValueError("mod rows out of order at %d" % i)
        pos.append(int(r[2]))
        mods.append(Mod(unhex(r[5]), r[3] == b"1", unhex(r[6]), unhex(r[8]),
                        unhex(r[7])))
        origins.append(r[4])
        ages.append(int(r[9]))
    return mods, pos, origins, ages


def plan_check(rows, entries, root_of, shipped_hooks, qm_version, mtime_of=None):
    """Compare a plan dump with the twin. Returns `(problems, notes)`.

    rows           parsed dump lines (`parse_dump`)
    entries        vanilla.idx rows `(path, size, lines, class)`, bytes/int
    root_of(dir)   the folder that held a mod's files during the run (the
                   fixture or dist folder, since hrun has removed the copies)
    shipped_hooks  hook paths Quartermaster ships
    mtime_of(path) optional: the mtime of an on-disk file, for the
                   informational FileAge check
    Problems are real mismatches; notes are informational (FileAge values
    Python cannot predict exactly, see `ref.index.dos_age`).
    """
    import os
    problems, notes = [], []
    mods, dumped_pos, origins, _ini = _mods_from_dump(rows)
    by = {}
    for r in rows:
        by.setdefault(r[0], []).append(r)
    self_rows = by.get(b"self", [])
    self_index = int(self_rows[0][1]) if self_rows else -1

    def has_core(d):
        root = root_of(d)
        return root is not None and os.path.isfile(os.path.join(root, "data", "quartermaster",
                                                                "core.aix"))

    want_self = find_self(mods, has_core)
    if want_self != self_index:
        problems.append("self: game %d, twin %d" % (self_index, want_self))
    pos = canonical_positions(mods, self_index)
    if pos != dumped_pos:
        problems.append("canonical positions: game %r, twin %r" % (dumped_pos, pos))

    # FileAge values come from the dump; which mod ships what is recomputed.
    dumped_idx = dict((r[1], r) for r in by.get(b"idx", []))
    dumped_ages = {}
    for path, r in dumped_idx.items():
        ps = [int(x) for x in r[2].split(b";")] if r[2] else []
        ags = r[3].split(b";") if r[3] else []
        for p, a in zip(ps, ags):
            if a != b"-":
                dumped_ages[(p, path)] = int(a)

    def age(d, path):
        i = next(k for k, m in enumerate(mods) if m.dir == d)
        root = root_of(d)
        full = None if root is None else os.path.join(root, "data",
                                                      *path.decode("ascii").split("\\"))
        if full is None or not os.path.isfile(full):
            return -1
        got = dumped_ages.get((pos[i], path))
        if mtime_of is not None:
            want = dos_age(mtime_of(full))
            if got is not None and got != want:
                notes.append("FileAge %s in %s: game %d, from mtime %d"
                             % (path.decode(), d.decode("latin-1"), got, want))
        return got if got is not None else 0

    index = build_index(mods, self_index, entries, age, shipped_hooks, has_core)
    scan_rows = by.get(b"scan", [])
    if not scan_rows or int(scan_rows[0][1]) != len(index.scanned):
        problems.append("scan: game %s paths, twin %d"
                        % (scan_rows[0][1].decode() if scan_rows else "no", len(index.scanned)))
    want_idx = {}
    for path, provs in index.providers.items():
        ags = [b"-" if a is None else b"%d" % a for a in index.ages[path]]
        want_idx[path] = (b";".join(b"%d" % pos[i] for i in provs), b";".join(ags))
    got_idx = dict((p, (r[2], r[3])) for p, r in dumped_idx.items())
    for path in sorted(set(want_idx) | set(got_idx)):
        if want_idx.get(path) != got_idx.get(path):
            problems.append("idx %s: game %r, twin %r"
                            % (path.decode(), got_idx.get(path), want_idx.get(path)))

    got_stamps = dict((int(r[1]), r[2]) for r in by.get(b"stamp", []))
    want_stamps = dict((pos[i], s) for i, s in index.stamps.items())
    if got_stamps != want_stamps:
        problems.append("stamps: game %r, twin %r" % (got_stamps, want_stamps))

    vage = dict((r[1], int(r[2])) for r in by.get(b"vage", []))
    exe = by.get(b"exe", [])
    exe_age = int(exe[0][1]) if exe else 0
    want_v = [p for p in index.scanned if p in index.providers]
    if sorted(vage) != sorted(want_v):
        problems.append("vage paths: game %d, twin %d" % (len(vage), len(want_v)))
    vstamp = vanilla_stamp(index, lambda p: vage.get(p, 0), exe_age)
    got_v = by.get(b"vstamp", [(b"", b"")])[0][1]
    if got_v != vstamp:
        problems.append("vanilla stamp: game %r, twin %r" % (got_v, vstamp))

    self_dir = mods[self_index].dir if self_index >= 0 else None
    decisions = plan(index.by_dir(mods), [e for e in entries if e[0] in index.providers],
                     self_dir)
    dir_pos = dict((m.dir, pos[i]) for i, m in enumerate(mods))
    want_plan = plan_lines(decisions, lambda d: dir_pos[d])
    got_plan = [b"|".join(r) for r in rows if r[0] == b"plan"]
    if got_plan != want_plan:
        for a, b in zip(got_plan + [b""] * len(want_plan), want_plan + [b""] * len(got_plan)):
            if a != b:
                problems.append("plan: game %r, twin %r" % (a, b))
                break
        if len(got_plan) != len(want_plan):
            problems.append("plan: game %d lines, twin %d" % (len(got_plan), len(want_plan)))

    text, fp = fingerprint(mods, self_index, index, vstamp, qm_version)
    got_text = b"".join(unhex(r[1]) + b"\n" for r in by.get(b"fpl", []))
    if got_text != text:
        problems.append("fingerprint text: game %r, twin %r" % (got_text, text))
    got_fp = by.get(b"fp", [(b"", b"")])[0][1]
    if got_fp != fp:
        problems.append("fingerprint: game %r, twin %r" % (got_fp, fp))
    # The fingerprint without the mods registered at this start (the loop
    # rule's exception), for the rows the game marked fresh; dumps made before
    # 2026-10-01 have neither line.
    if b"fpold" in by or b"fresh" in by:
        f = by.get(b"fresh", [(b"", b"-")])[0][1]
        fresh = [] if f in (b"", b"-") else [int(x) for x in f.split(b";")]
        _t, want_old = known_fingerprint(mods, self_index, index, lambda p: vage.get(p, 0),
                                         exe_age, qm_version, fresh)
        got_old = by.get(b"fpold", [(b"", b"")])[0][1]
        if got_old != want_old:
            problems.append("fingerprint without %r: game %r, twin %r" % (fresh, got_old,
                                                                         want_old))
    return problems, notes


# ------------------------------------------------------------------ keys
def keys_expected(scanned):
    """The keys dump: every scanned path a distinct, lossless parser key."""
    n = len(scanned)
    return [b"|".join([b"keys", b"%d" % n, b"0", b"%d" % n, b"0", b"0"])]


# ------------------------------------------------------------------ done
def done_expected(cases):
    """done.txt for `[(file name, kind)]` in the order the runner sorts them."""
    rows = [b"|".join([b"case", name, kind, b"ok"]) for name, kind in sorted(cases)]
    return rows + [b"done|%d|0" % len(rows)]


# -------------------------------------------------------------------- ui
#: The steps the `ui` case takes after its cycles, each followed by one dump
#: line `step|<name>|<sel>|<pending on>|<mode>|<visible>|<uiapply>|
#: <uiapplyseq>|<uiapplychg>|<uiapplydis of the row>|<uiregen>|<canapply>|
#: <ordchg>|<panel>|<Apply button enabled>` (src/states/qmcaseui.pas). `sel`
#: is -1 right after the open and the toggled row from the selection on.
#: Mode 2 is the restart notice after the confirmed Apply; Apply is enabled
#: only while something is pending in browse mode (decided 2026-09-28). The
#: notice is drawn alone - no window under it, no button on it
#: (ShowQmManager's mode 2) - so there is no Apply button then (-1).
#: `move1` / `move2` move the row one place and back; whether they move is
#: the dump's `order` line's business (ui_expected), the values here are
#: those of a move that happened.
UI_STEPS = (
    # name         selected  pe mode vis  qm_rt: apply seq chg dis regen  can ord panel btn
    (b"open",        False,   1, 0, 1,   0, 0, 0, 0, 0,   0, 0, 0, 0),
    (b"select",      True,    1, 0, 1,   0, 0, 0, 0, 0,   0, 0, 0, 0),
    (b"move1",       True,    1, 0, 1,   0, 0, 0, 0, 0,   1, 1, 0, 1),
    (b"move2",       True,    1, 0, 1,   0, 0, 0, 0, 0,   0, 0, 0, 0),
    (b"filter",      True,    1, 0, 1,   0, 0, 0, 0, 0,   0, 0, 0, 0),
    (b"filterclear", True,    1, 0, 1,   0, 0, 0, 0, 0,   0, 0, 0, 0),
    (b"report",      True,    1, 0, 1,   0, 0, 0, 0, 0,   0, 0, 1, 0),
    (b"back",        True,    1, 0, 1,   0, 0, 0, 0, 0,   0, 0, 0, 0),
    (b"deactivate",  True,    0, 0, 1,   0, 0, 0, 0, 0,   1, 0, 0, 1),
    (b"apply",       True,    0, 1, 1,   0, 0, 0, 0, 0,   0, 0, 0, 0),
    (b"esc1",        True,    0, 0, 1,   0, 0, 0, 0, 0,   1, 0, 0, 1),
    (b"apply2",      True,    0, 1, 1,   0, 0, 0, 0, 0,   0, 0, 0, 0),
    (b"enter",       True,    0, 2, 1,   1, 1, 1, 1, 1,   0, 0, 0, -1),
    (b"esc2",        True,    0, 2, 0,   1, 1, 1, 1, 1,   0, 0, 0, -1),
)

#: What the dump says about the toggled row's place when the run does not
#: (ui_keep_go's default): second of three active rows.
UI_ORDER = (1, 3)
#: The filter's counts when the run does not say (ui_keep_go's default).
UI_FILTER = (1, 3)


def ui_directives(cycles, toggle, keep=False):
    """The `ui` case's directives: `cycles <n>`, `toggle <dir>`, and `keep 1`
    when the confirmed Apply is to be left for qmTick (I9 through the window)."""
    out = [(b"cycles", b"%d" % cycles), (b"toggle", toggle)]
    if keep:
        out.append((b"keep", b"1"))
    return out


def ui_keep_go(toggle, row, boot, order=UI_ORDER, filt=UI_FILTER):
    """The dump of the life in which a `keep` case drives the window: the
    `ui_expected` flow without cycles between `life|<boot>|go` and
    `kept|1|1` - the request is still there (uiapply 1, seq 1) when it ends."""
    return ([b"life|%d|go" % boot] + ui_expected(0, toggle, row, order, filt)
            + [b"kept|1|1"])


def ui_keep_wait(boot, regen, restart):
    """A life before it: the boot generated or has its own restart pending."""
    return [b"life|%d|wait|regen=%d|restart=%d" % (boot, regen, restart)]


def ui_keep_later(boot, on, why):
    """A life after it: the mod's flag in qm_mods (0 once the Apply took
    effect) and the boot's `why`."""
    return [b"life|%d|later|on=%s|why=%s" % (boot, on, why)]


def ui_expected(cycles, toggle, row, order=UI_ORDER, filt=UI_FILTER):
    """The `ui` dump for `cycles` open/close cycles and the toggled mod at `row`.

    `row` is the mod's place in ModLibraryGetData order, `order` its place in
    the Active list and the number of active rows, `filt` the rows a filter
    by its folder name must show and the number of rows: only the run knows
    them, and `ui_check` takes them from the dump. Cycle i closes with the
    close tag when i is odd and with Esc when it is even. A fresh process
    adds both screen states once (`ensure|ready|show|event|adds`); every cycle
    opens and hides exactly one window, the counters of qm_ui count along, and
    the case removes the window at the end (`end|windows|opens|closes`).

    The first move is up, or down when the row loads first; it moves unless
    the row is not active, or loads first with only Quartermaster after it
    (Quartermaster always loads last). A move that does not happen changes
    nothing, so move1 then reads as move2 does.
    """
    place, active = order
    shown, rows = filt
    first = b"up" if place > 0 else b"down"
    moves = place > 0 or (place == 0 and active > 2)
    lines = [b"ensure|1|1|1|1"]
    for i in range(1, cycles + 1):
        how = b"close" if i % 2 else b"esc"
        lines.append(b"cycle|%d|%s|1|1|1|%d|%d" % (i, how, i, i))
    lines.append(b"row|%s|%d|1" % (hexs(toggle), row))
    for step in UI_STEPS:
        sel = row if step[1] else -1
        values = list(step[2:])
        if step[0] == b"move1" and not moves:
            values = list(UI_STEPS[3][2:])
        lines.append(b"|".join([b"step", step[0], b"%d" % sel] + [b"%d" % v for v in values]))
        if step[0] == b"select":
            lines.append(b"order|%s|%d|%d" % (first, place, active))
        if step[0] == b"filter":
            lines.append(b"filtered|%d|%d" % (shown, shown))
        if step[0] == b"filterclear":
            lines.append(b"unfiltered|%d|%d" % (rows, rows))
    lines.append(b"end|0|%d|%d" % (cycles + 1, cycles + 1))
    return lines


def ui_check(rows, cycles, toggle):
    """Problems of a `ui` dump against `ui_expected`, as text; empty = equal."""
    got = [b"|".join(r) for r in rows]
    row = -1
    order, filt = UI_ORDER, UI_FILTER
    shown = rows_n = None

    def num(v):
        return int(v) if v.lstrip(b"-").isdigit() else -1
    for r in rows:
        if r[0] == b"row" and len(r) > 2 and r[2].lstrip(b"-").isdigit():
            row = int(r[2])
        if r[0] == b"order" and len(r) > 3:
            order = (num(r[2]), num(r[3]))
        if r[0] == b"filtered" and len(r) > 2:
            shown = num(r[2])
        if r[0] == b"unfiltered" and len(r) > 2:
            rows_n = num(r[2])
    # The run's own counts: the filter must show the rows it counted itself.
    for r in rows:
        if r[0] == b"filtered" and len(r) > 2 and r[2] != r[-1]:
            shown = -1
        if r[0] == b"unfiltered" and len(r) > 2 and r[2] != r[-1]:
            rows_n = -1
    filt = (shown if shown is not None else filt[0], rows_n if rows_n is not None else filt[1])
    want = ui_expected(cycles, toggle, row, order, filt)
    problems = []
    if row < 0:
        problems.append("the toggled mod was not found (row line: %r)"
                        % [g for g in got if g.startswith(b"row|")])
    if filt[0] < 1:
        problems.append("the filter by the mod's folder name showed %r rows, and at least the "
                        "mod itself holds the text" % [g for g in got if g.startswith(b"filtered|")])
    for k in range(max(len(got), len(want))):
        g = got[k] if k < len(got) else b"<missing>"
        w = want[k] if k < len(want) else b"<none>"
        if g != w:
            problems.append("line %d: game %r, expected %r" % (k + 1, g, w))
    return problems
