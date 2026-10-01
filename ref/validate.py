r"""Validation and writing (docs/plan.md G11, G12, S7, S9): the twin of
src/lib/qmval.pas, src/lib/qmwrite.pas and the driver state qmGenerate
(src/states/qmwritegen.pas).

Nothing reaches `<QmDir>\data\` unless it compiled in a validation copy.

The validation copy (plan S7)
-----------------------------
A candidate is a key-line header and a list of Code values - what an `.inc`
holds. Its validation copy is a one-state machine file,
`<save>\quartermaster\val\<seq>.aix`, outside every folder the engine loads
from:

    section.begin
       Name = qmVal<seq>
       UsedFileName =                              (one trailing space)
       Code : struct.begin
          [*] = ;ParserSetValueByKeyByHandle(ParserSelectByKey('qm_val'), 'f<seq>', '<token>');
          [*] = ;exit;
          [*] = <value 0>
          ...
       struct.end
    section.end
    <empty line>
    section.begin
       CurrentState =                              (one trailing space)
       SaveVariables = False
    section.end
    <empty line>

Why this shape, each part with its evidence:
- the machine-file shape is what tools/hbuild.py writes for core.aix
  (assemble_aix, from data/maps/missions/rusmis1.aix:1-26), and what the
  capability probes loaded with StateMachineLoadFromFile: probe 3's
  candidate `<save>\quartermaster\val\cand.aix` of the cap run (Name,
  UsedFileName, a Code struct, the CurrentState trailer; written by the
  4-byte writer, so it ends in padding spaces) loaded and ran
  (cap.0.log:94-105, docs/research/m0-probes.md probe 3);
- a candidate's Code values go in unchanged, leading `;` and all: a Code
  value of an `.inc` is exactly what follows `[*] = ` on its line, the same in
  a machine file (ref/inc.py);
- the flag line comes first and `exit;` after it, so the candidate's own code
  is compiled but never run: probe 3's candidates were `flag; exit; <code>`;
  a broken one gave "Compile script error: QmCandX" and flag 0
  (cap.0.log:103-104), and the next good one in the same manager worked
  (:105);
- the flag line may stand in front of a state's leading routines: run r7
  validated vanilla cameracontrol.inc with its flag line before the nested
  procedure CreateCameraControlLayer (r7.0.log:23, "flag before nested
  procedure: ok=1") and rejected a broken copy (r7.0.log:26);
- the flag is a named-parser value, not a global (plan S4); probe 3 used
  `ParserSetIntValueByKeyByHandle(ParserSelectByKey('qmp_val'), 'ok', n)`.
  Here the value is the candidate's token (below) as a String, so a flag
  carries which content compiled, not only that something did.

The token
---------
`token(keys, values)` is ref/fingerprint.py `qhash` of

    <number of key lines> LF  <each key line, leading spaces cut> LF ...  <each value> LF ...

over internal strings (ref/textio.py: bytes outside 32..122 spelt `~NNN`).
The game computes it the same way (qmValToken). The validator writes it into
the flag line; the writer (qmWrOutput) reads the staged candidate back,
computes it again and writes only when `qm_val` holds exactly that value for
the candidate's `f<seq>`. Only the compiled flag line of that very wrapper
sets it, so a file whose bytes were never validated cannot be written.

Candidates of one path, in the order they are tried (plan S7)
-------------------------------------------------------------
merge-inc  merged (the merge's output) -> subset -> winner (the last
           participant's own file). Nothing compiles: nothing is written.
           subset is the merge without the participants that lost a conflict
           (`losers`), there only when at least two participants stay: half
           of one mod's changes may not compile, the rest of the mods whole
           may. Chosen, it is `partial`, WARN; the report names who is left out.
hook       merged+hook -> subset+hook -> winner+hook -> vanilla+hook. Quartermaster's hook
           lines go in at `ref.inc.hook_index` of the file they join (plan
           S5). vanilla+hook failing is a build bug: FATAL, and nothing at all
           is written that generation.
A candidate whose token equals one already tried for the path is skipped (it
would compile the same way). The merged candidate exists only when the merge
wrote a file: not for winner-takes-all (mode winner) and not on a merge error.

The generation constant
-----------------------
The CameraControl hook lines may hold one line `;const qmHookGen = '<g>';`
(plan S6: the generation constant sits in the CameraControl hook, inside the
MP checksum). The value written there is the generation's outputs hash
(ref/manifest.py outputs_hash), not a counter: two players with the same mods
then have the same bytes and the same checksum, whatever their history (plan
S12). The hash covers every output's token with gen lines left out, so the
constant does not depend on itself; CameraControl is processed last so the
other outputs are known.

The data mirror and what may be written there
---------------------------------------------
`writable(rel, cls)`: an `.inc` on the Phase A merge allow-list (plan S3:
vanilla.idx class `merge` - under gui\menu.inc\, gui\common.inc\ or
scripts\, minus the never-generate list of plan S2), spelt in plain lower
case. Everything on the S2 list is refused, by class and again by name.
"""
from . import inc as I
from . import merge as M
from .fingerprint import qhash
from .planner import HOOK_FILES
from .textio import escape, read_lines, unescape, write_file

__all__ = ["VAL_PARSER", "VAL_MANAGER", "STATE_PREFIX", "BROKEN_LINE", "GEN_PREFIX",
           "CAMERA", "MERGE_DIRS", "NEVER_INC", "PATH_CHARS", "MAX_PATH",
           "TIER_MERGED", "TIER_WINNER", "TIER_MERGED_HOOK", "TIER_WINNER_HOOK",
           "TIER_VANILLA_HOOK", "TIER_STALE", "TIER_SUBSET", "TIER_SUBSET_HOOK",
           "losers", "token", "state_name", "flag_key",
           "flag_line", "wrapper_lines", "wrapper_bytes", "candidate_bytes",
           "gen_line", "is_gen_line", "with_generation", "writable", "deletable",
           "inc_lines", "code_values", "Candidate", "PathResult", "StaleResult", "Generation",
           "generate", "alone_outputs_hash", "OK", "WARN", "FAIL", "FATAL",
           "PARTICIPANT_LIMIT"]

VAL_PARSER = b"qm_val"
#: The one validation trigger manager of a boot (plan S7). It is looked up by
#: name and added only when missing: adding a live name creates a second,
#: empty manager (probe 3, cap.0.log:90-91).
VAL_MANAGER = b"qm_valtm"
STATE_PREFIX = b"qmVal"
#: A line that is not Pascal: the SelfTest's deliberately broken candidate
#: (run r7's val_bad used the same kind of line, r7.0.log:26).
BROKEN_LINE = b";qm this line is not pascal ("
GEN_PREFIX = b";const qmHookGen = "
CAMERA = b"gui\\menu.inc\\cameracontrol.inc"
MERGE_DIRS = (b"gui\\menu.inc\\", b"gui\\common.inc\\", b"scripts\\")
#: The `.inc` files of the never-generate list (plan S2; tools/hbuild.py
#: S2_FILES). Refused by name as well as by class.
NEVER_INC = (b"gui\\menu.inc\\docreate.inc", b"scripts\\common.inc\\initmap.inc")
#: The bytes a merge-class path uses (vanilla.idx, 2026-09-28: a-z, 0-9, `.`,
#: `\`); `_` and `-` are allowed too. Anything else is refused.
PATH_CHARS = frozenset(b"abcdefghijklmnopqrstuvwxyz0123456789_.-\\")
MAX_PATH = 200
#: qmMerge takes at most this many participants (qmmerge.pas qmMgPmax).
PARTICIPANT_LIMIT = 16

TIER_MERGED = b"merged"
TIER_WINNER = b"winner"
TIER_MERGED_HOOK = b"merged+hook"
TIER_WINNER_HOOK = b"winner+hook"
TIER_VANILLA_HOOK = b"vanilla+hook"
#: The merge without the participants that lost a conflict (`losers`): tried
#: when the merged file does not compile, before the winner's copy.
TIER_SUBSET = b"subset"
TIER_SUBSET_HOOK = b"subset+hook"
#: An output of an earlier generation that could not be deleted, overwritten
#: with the file the game should use now (plan S9).
TIER_STALE = b"stale"

OK, WARN, FAIL, FATAL = b"OK", b"WARN", b"FAIL", b"FATAL"
_MERGE_TAG = {"ok": OK, "warn": WARN, "fail": FAIL}

MERGE_INC, HOOK = b"merge-inc", b"hook"


# --------------------------------------------------------------- the copy
def token(keys, values, skip_gen=False):
    """The content token of a candidate (see the module docstring).

    `keys` and `values` are internal strings. `skip_gen`: leave the
    generation line out (the form the outputs hash takes).
    """
    vals = [v for v in values if not (skip_gen and is_gen_line(v))]
    data = (b"%d\n" % len(keys) + b"".join(k.lstrip(b" ") + b"\n" for k in keys)
            + b"".join(v + b"\n" for v in vals))
    return qhash(data)


def state_name(seq):
    return STATE_PREFIX + b"%d" % seq


def flag_key(seq):
    return b"f%d" % seq


def flag_line(seq, tok):
    return (b";ParserSetValueByKeyByHandle(ParserSelectByKey('" + VAL_PARSER + b"'), '"
            + flag_key(seq) + b"', '" + tok + b"');")


def wrapper_lines(seq, tok, values):
    """The validation copy's lines, internal strings (written CRLF, padded)."""
    return ([b"section.begin", b"   Name = " + state_name(seq), b"   UsedFileName = ",
             b"   Code : struct.begin", I.CODE_PREFIX + flag_line(seq, tok),
             I.CODE_PREFIX + b";exit;"]
            + [I.CODE_PREFIX + v for v in values]
            + [b"   struct.end", b"section.end", b"", b"section.begin",
               b"   CurrentState = ", b"   SaveVariables = False", b"section.end", b""])


def wrapper_bytes(seq, tok, values):
    return write_file(wrapper_lines(seq, tok, values))


def candidate_bytes(keys, values):
    """The staged candidate, and the output file written from it: the engine
    layout by value count (ref/inc.py layout_lines), the raw writer's bytes."""
    return write_file(I.layout_lines(keys, values))


def inc_lines(data):
    """`(keys, values)` as the game's qmIncReadAt returns them: internal
    strings, key lines as they stand in the file."""
    _form, keys, values = I.values_from_lines(read_lines(data))
    return keys, values


# ------------------------------------------------------ generation constant
def gen_line(g):
    return GEN_PREFIX + b"'" + g + b"';"


def is_gen_line(v):
    return v.startswith(GEN_PREFIX)


def with_generation(values, g):
    return [gen_line(g) if is_gen_line(v) else v for v in values]


# --------------------------------------------------------------- the paths
def writable(rel, cls):
    """May the writer put `rel` (vanilla.idx spelling, relative to data\\)
    into the data mirror? `cls` is its vanilla.idx class (None: not listed)."""
    if not rel or len(rel) > MAX_PATH or any(c not in PATH_CHARS for c in rel):
        return False
    if not rel.endswith(b".inc") or b".." in rel or rel.startswith(b"\\") or b"\\\\" in rel:
        return False
    if not rel.startswith(MERGE_DIRS) or rel in NEVER_INC:
        return False
    return cls == b"merge"


def deletable(rel, cls):
    """Stale cleanup may delete `rel`: writable and not a hook file (the
    shipped hooked copies must never go, plan S5)."""
    return writable(rel, cls) and rel not in HOOK_FILES


# --------------------------------------------------------------- the model
class Candidate(object):
    __slots__ = ("path", "tier", "seq", "tok", "htok", "ok", "keys", "values")

    def __init__(self, path, tier, seq, tok, htok, ok, keys, values):
        self.path, self.tier, self.seq, self.tok, self.htok = path, tier, seq, tok, htok
        self.ok, self.keys, self.values = ok, keys, values

    def __repr__(self):
        return "Candidate(%r, %s, seq=%d, ok=%s)" % (self.path, self.tier.decode(),
                                                     self.seq, self.ok)


class PathResult(object):
    """What the generation did for one plan decision (qm_gen keys per m)."""

    def __init__(self, m, decision):
        self.m = m
        self.decision = decision
        self.job = -1
        self.merge = None          # ref.merge.MergeResult
        self.merge_err = b""
        self.sub_job = -1          # the merge without the losers (qmMerge's second batch)
        self.sub_merge = None
        self.sub_err = b""
        self.left_out = []         # canonical positions of the losers
        self.participants = []     # canonical positions, Quartermaster left out
        self.winner = None         # the last participant's position
        self.tries = []
        self.chosen = None
        self.code = b""
        self.status = OK
        self.written = b"-"
        self.first_line = 0        # vanilla's first Code value, 1-based file line
        self.vanilla_n = 0

    @property
    def path(self):
        return self.decision.path

    @property
    def act(self):
        return self.decision.action


class StaleResult(object):
    __slots__ = ("path", "result", "source", "cand")

    def __init__(self, path, result, source=b"-", cand=None):
        self.path, self.result, self.source, self.cand = path, result, source, cand


class Generation(object):
    def __init__(self):
        self.status = b"ok"
        self.gen = 0
        self.outhash = b"-"
        self.fp = b"-"
        self.paths = []
        self.stale = []
        self.outputs = {}      # path -> bytes, what was written into the data mirror
        self.staged = {}       # seq -> staged candidate bytes
        self.wrappers = {}     # seq -> validation copy bytes
        self.manifest = None
        self.fatal = None      # the path whose last hook candidate failed
        self.seq = 0
        self.changed = 0       # files of the mirror whose content changed

    @property
    def candidates(self):
        out = [c for p in self.paths for c in p.tries]
        out += [s.cand for s in self.stale if s.cand is not None]
        return sorted(out, key=lambda c: c.seq)


def code_values(data):
    """The Code values of `.inc` bytes as the game side reads them
    (qmIncFromLines: the text after the first `[*] = ` of each line), as bytes.

    Not `ref.inc.parse`, which refuses every shape vanilla does not have:
    mods have some. State vs Country (Workshop 1325221799) starts code lines
    with a tab in 33 files; the game reads them like any other line, and this
    twin raised on them until the Workshop dry run of 2026-09-28. On every
    vanilla file both give the same values (tests/test_ref_inc.py)."""
    return [unescape(v) for v in I.values_from_lines(read_lines(data))[2]]


def losers(mg):
    """Indices of the participants with a hunk lost to a later participant's
    change (ref.merge CONFLICT_LOST). A mod's own hunks can depend on each
    other - one declares a const another uses - so a merge that keeps some of
    them and drops the rest may not compile (Renaissance with MGraphics - Main
    Menu, showmainmenu.inc, 2026-09-30); the merge without those mods keeps
    every change it takes whole."""
    return sorted(set(h.participant for h in mg.hunks if h.status == M.CONFLICT_LOST))


def _merge_job(vanilla, parts):
    """ref.merge.merge over `.inc` bytes, and the error qmMerge would report."""
    if len(parts) > PARTICIPANT_LIMIT:
        return None, b"participants %d" % len(parts)
    base = code_values(vanilla)
    mods = [(pos, code_values(data)) for pos, data in parts]
    return M.merge(base, mods), b""


def generate(decisions, self_pos, read_vanilla, read_mod, hook_file, compiles,
             prev_manifest=None, deleted=lambda path: True, classes=None,
             srcs=None, fp=b"-", seq0=0, existing=lambda path: None, wta=False,
             gensalt=b""):
    """One generation, as qmGenerate runs it. Returns a `Generation`.

    decisions      ref.planner.Decision list, plan order, providers as canonical
                   positions (qm_plan's view)
    self_pos       Quartermaster's canonical position
    read_vanilla(path), read_mod(pos, path)  file bytes (None: missing)
    hook_file(path)  the pristine hook `.inc` for a hook path, or None
    compiles(cand)   the validator's verdict for a Candidate (keys/values set)
    prev_manifest  the previous manifest's bytes, or None
    deleted(path)  did DeleteFileStream remove a stale output (FileAge = -1)?
    classes        {path: vanilla.idx class}; default: `merge` for every
                   decision's path
    srcs(path, pos)  `(fo, ident, age)` of a participant, for the manifest
    existing(path) the file now in the data mirror, or None: a candidate
                   whose token equals it is not written again (`same`), so
                   an unchanged output keeps its bytes and its FileAge
    wta            the boot suspects the last generation kept the game from
                   starting (plan S8): nothing is merged - merge-inc paths
                   get no output, hook paths try winner+hook, vanilla+hook
    gensalt        appended to the generation constant (the boot's unstable-
                   fingerprint test, I5)
    """
    from . import manifest as MF
    g = Generation()
    g.fp = fp
    g.seq = seq0
    cls = (lambda p: classes.get(p)) if classes is not None else (lambda p: b"merge")
    prev = MF.parse(prev_manifest) if prev_manifest is not None else None

    for m, d in enumerate(decisions):
        r = PathResult(m, d)
        g.paths.append(r)
        if d.action not in (MERGE_INC, HOOK):
            r.code = b"skip" if d.action == b"skip" else b"winner"
            r.status = OK if d.action == b"skip" else WARN
            continue
        r.participants = [p for p in d.providers if p != self_pos]
        r.winner = r.participants[-1] if r.participants else None
        van = read_vanilla(d.path)
        vinc = I.parse(van)
        r.vanilla_n = len(vinc.values)
        r.first_line = len(vinc.keys) + (3 if vinc.form == "struct" else 2)
        if r.participants and not wta:
            r.job = sum(1 for x in g.paths[:-1] if x.job >= 0)
            r.merge, r.merge_err = _merge_job(van, [(p, read_mod(p, d.path))
                                                    for p in r.participants])
            mg = r.merge
            if mg is not None and not r.merge_err and mg.mode == "merged" and mg.conflicts:
                lost = losers(mg)
                keep = [p for i, p in enumerate(r.participants) if i not in lost]
                # One participant left is the winner's own copy, the next tier.
                if len(keep) >= 2:
                    r.left_out = [r.participants[i] for i in lost]
                    r.sub_job = sum(1 for x in g.paths[:-1] if x.sub_job >= 0)
                    r.sub_merge, r.sub_err = _merge_job(van, [(p, read_mod(p, d.path))
                                                              for p in keep])

    order = [r for r in g.paths if r.act in (MERGE_INC, HOOK) and r.path != CAMERA]
    order += [r for r in g.paths if r.act in (MERGE_INC, HOOK) and r.path == CAMERA]
    for r in order:
        _decide(g, r, read_vanilla, read_mod, hook_file, compiles, wta, gensalt)
        if r.code == b"fatal":
            g.fatal = r.path
    g.outhash = MF.outputs_hash([(r.path, r.chosen.htok) for r in g.paths if r.chosen])

    if g.fatal is not None:
        # Nothing is written, so the generation stays the previous one.
        g.status = b"fatal"
        g.gen = prev.gen if prev is not None else 0
        return g

    for r in g.paths:
        if r.chosen is None:
            continue
        if not writable(r.path, cls(r.path)):
            r.written = b"refused"
            r.code, r.status = b"writefail", FAIL
            continue
        now = existing(r.path)
        if now is not None and token(*inc_lines(now)) == r.chosen.tok:
            g.outputs[r.path] = now
            r.written = b"same"
        else:
            g.outputs[r.path] = candidate_bytes(r.chosen.keys, r.chosen.values)
            r.written = b"yes"
            g.changed += 1

    current = set(r.path for r in g.paths if r.chosen is not None)
    lefts = []
    for path in (prev.paths() if prev else []):
        if path in current:
            continue
        if not deletable(path, cls(path)):
            g.stale.append(StaleResult(path, b"refused"))
            continue
        if deleted(path):
            g.stale.append(StaleResult(path, b"deleted"))
            g.changed += 1
            continue
        src, keys, values = _stale_source(g, path, read_vanilla, read_mod, self_pos)
        cand = _candidate(g, path, TIER_STALE, keys, values, compiles)
        if cand.ok:
            g.outputs[path] = candidate_bytes(keys, values)
            g.stale.append(StaleResult(path, b"overwritten", src, cand))
            lefts.append((path, cand.tok))
            g.changed += 1
        else:
            g.stale.append(StaleResult(path, b"failed", src, cand))

    g.gen = MF.next_generation(prev, g.outhash)
    outs = []
    for r in g.paths:
        if r.written not in (b"yes", b"same"):
            continue
        mg = r.merge
        summary = ((b"-", b"-", b"-", 0, 0, 0) if mg is None or r.merge_err else
                   (mg.mode.encode(), mg.status.encode(),
                    b"-" if mg.reason is None else mg.reason.encode(),
                    len(mg.hunks) if mg.mode == "merged" else 0,
                    mg.conflicts if mg.mode == "merged" else 0,
                    len(mg.pairs) if mg.mode == "merged" else 0))
        if r.merge_err:
            summary = (b"error", b"fail", b"-", 0, 0, 0)
        rows = [(p,) + tuple(srcs(r.path, p) if srcs else (b"-", b"", -1))
                for p in r.participants]
        outs.append(MF.Output(r.path, r.chosen.tok, r.chosen.tier, summary, rows))
    g.manifest = MF.render(g.gen, g.outhash, g.fp, outs, lefts)
    return g


def alone_outputs_hash(paths, read_vanilla, hook_values):
    """The generation constant Quartermaster writes when it is the only mod:
    every shipped hook file as vanilla with its hook lines (the first
    candidate of a hook path without participants), gen lines left out of the
    tokens, `ref.manifest.outputs_hash` in vanilla.idx order (`paths`).

    tools/hbuild.py can bake this value into the shipped static CameraControl
    copy: the first generation of a fresh install then finds every output
    equal (`same`), changes nothing and needs no restart.
    `hook_values(path)` gives the hook lines as internal strings.
    """
    from . import manifest as MF
    entries = []
    for path in paths:
        keys, values = inc_lines(read_vanilla(path))
        entries.append((path, token(keys, _hooked(values, hook_values(path)), skip_gen=True)))
    return MF.outputs_hash(entries)


def _candidate(g, path, tier, keys, values, compiles):
    seq = g.seq
    g.seq += 1
    tok = token(keys, values)
    cand = Candidate(path, tier, seq, tok, token(keys, values, skip_gen=True), False,
                     keys, values)
    g.staged[seq] = candidate_bytes(keys, values)
    g.wrappers[seq] = wrapper_bytes(seq, tok, values)
    cand.ok = bool(compiles(cand))
    return cand


def _stale_source(g, path, read_vanilla, read_mod, self_pos):
    """What an undeletable stale output is overwritten with: the file the game
    would use without it - the current winner's copy, or vanilla."""
    for r in g.paths:
        if r.path == path:
            parts = [p for p in r.decision.providers if p != self_pos]
            if parts:
                data = read_mod(parts[-1], path)
                if data is not None:
                    keys, values = inc_lines(data)
                    return b"winner", keys, values
    keys, values = inc_lines(read_vanilla(path))
    return b"vanilla", keys, values


def _hooked(values, hook):
    """`values` with the hook lines at the hook index (ref/inc.py
    insert_at_hook); the index is taken on the bytes the values stand for."""
    k = I.hook_index([unescape(v) for v in values])
    return list(values[:k]) + list(hook) + list(values[k:])


def _merge_status(code, mg, alone=False):
    """A file's tag from its merge (the Workshop check of 2026-09-28): a
    merge that gave up leaves the last mod's copy - what the game alone would
    load - so it is WARN, not FAIL; a merge whose only findings are near edits
    kept every change, so it is OK (the report still lists the near edits).
    WARN stays for changes lost to a later mod and for a full replacement
    that had to win outright.

    A hook file whose merge gave up gets the last mod's copy with the hook
    lines: WARN like `gaveup`, and OK when that mod is the only participant
    (`alone`), as nothing of anyone's is lost. Until 2026-10-01 it read FAIL:
    SW_Frontline_Protocol's doprogress.inc, all 3336 of its lines kept."""
    if code == b"gaveup":
        return WARN
    if code == b"hooked" and mg.mode == "winner":
        return OK if alone else WARN
    if mg.mode == "merged" and mg.status == "warn" and mg.conflicts == 0:
        return OK
    return _MERGE_TAG[mg.status]


def _decide(g, r, read_vanilla, read_mod, hook_file, compiles, wta=False, gensalt=b""):
    """The tiers of one path, tried in order until one compiles."""
    from . import manifest as MF
    d = r.decision
    mg = r.merge
    merged = None
    if mg is not None and not r.merge_err and mg.mode != "winner":
        vkeys, _v = inc_lines(read_vanilla(d.path))
        merged = (vkeys, [escape(v) for v in mg.lines])
    subset = None
    sm = r.sub_merge
    if sm is not None and not r.sub_err and sm.mode != "winner":
        vkeys, _v = inc_lines(read_vanilla(d.path))
        subset = (vkeys, [escape(v) for v in sm.lines])
    winner = None
    if r.winner is not None:
        data = read_mod(r.winner, d.path)
        if data is not None:
            winner = inc_lines(data)
    tiers = []
    if d.action == MERGE_INC:
        if wta:
            r.code, r.status = b"wta", FAIL
            return
        if merged is not None:
            tiers.append((TIER_MERGED,) + merged)
        if subset is not None:
            tiers.append((TIER_SUBSET,) + subset)
        if winner is not None:
            tiers.append((TIER_WINNER,) + winner)
    else:
        hdata = hook_file(d.path)
        if hdata is None:
            r.code, r.status = b"nohook", FAIL
            return
        _hk, hook = inc_lines(hdata)
        if merged is not None:
            tiers.append((TIER_MERGED_HOOK, merged[0], _hooked(merged[1], hook)))
        if subset is not None:
            tiers.append((TIER_SUBSET_HOOK, subset[0], _hooked(subset[1], hook)))
        if winner is not None:
            tiers.append((TIER_WINNER_HOOK, winner[0], _hooked(winner[1], hook)))
        vkeys, vvalues = inc_lines(read_vanilla(d.path))
        tiers.append((TIER_VANILLA_HOOK, vkeys, _hooked(vvalues, hook)))

    seen = set()
    for k, (tier, keys, values) in enumerate(tiers):
        if d.path == CAMERA:
            htok = token(keys, values, skip_gen=True)
            entries = [(x.path, htok if x is r else x.chosen.htok) for x in g.paths
                       if x is r or x.chosen is not None]
            value = MF.outputs_hash(entries)
            if gensalt:
                value += b"-" + gensalt
            values = with_generation(values, value)
        tok = token(keys, values)
        if tok in seen:
            continue
        seen.add(tok)
        cand = _candidate(g, d.path, tier, keys, values, compiles)
        r.tries.append(cand)
        if cand.ok:
            r.chosen = cand
            if tier in (TIER_SUBSET, TIER_SUBSET_HOOK):
                # Every change but the losers' is in: a warning, not a failure.
                r.code, r.status = b"partial", WARN
            elif k > 0:
                r.code, r.status = b"fallback", FAIL
            elif wta:
                r.code, r.status = b"wtahook", FAIL
            else:
                if d.action == MERGE_INC:
                    r.code = b"merged" if tier == TIER_MERGED else (
                        b"mergeerr" if r.merge_err else b"gaveup")
                else:
                    r.code = b"hooked"
                if r.merge_err:
                    r.status = FAIL
                elif mg is not None:
                    r.status = _merge_status(r.code, mg, len(r.participants) == 1)
                else:
                    r.status = OK
            return
    if d.action == HOOK:
        r.code, r.status = b"fatal", FATAL
    else:
        r.code, r.status = b"none", FAIL
