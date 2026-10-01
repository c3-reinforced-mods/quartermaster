r"""The conflict report: where two enabled mods change the same game code.

The twin of src/states/qmconflicts.pas. Reporting only (decided 2026-10-01):
it reads what a generation did (`ref.validate.Generation`) and changes
nothing in how mods are merged, ordered, validated or written. Each record
describes the file that was actually written:

  conflict        a change that lost to a later mod's (`ref.merge`
                  CONFLICT_LOST) in a file written as a merge: the full merge
                  for the tiers merged and merged+hook; for subset and
                  subset+hook the full merge's lost changes - all the left-out
                  mods' - and then the subset merge's own. A change that was a
                  duplicate of one that lost is dropped too and named with it;
  left out        the written file is the subset: all of a left-out mod's
                  changes there are dropped;
  close together  changes of two mods within `ref.merge.PROXIMITY_LINES`
                  vanilla lines, both in the written file: the pairs of the
                  merge that was written;
  whole file      one copy is used and the other mods' copies are not: the
                  planner's winner-takes-all paths, a merge that gave up or
                  failed, a written copy that is the winner's or vanilla's, no
                  copy written at all (the game then loads the last mod's);
                  only with two or more mods besides Quartermaster;
  core script     two enabled mods ship the same global script (the boot's
                  clashes, `ref.report.Boot.clashes`): only one copy loads.

Mods are named as the report names them, `<k>. <title> (<Workshop number or
folder>)`, `<k>` the place on the window's Active list. A record's place
in the code is the state's `Name` and the routines its vanilla lines sit in
(`routines`); `at:` is the vanilla line where the range starts; the kind of
file comes from its folder alone and says so.

conflicts.txt is English, written by the game's raw writer: CRLF, no
timestamps, so the same inputs give the same bytes. Its layout:

    Quartermaster conflict report
    format 1, Quartermaster <version>, generation <N>, outputs hash <hash>
    rule: where two mods change the same lines, the mod later in the load order wins.
          Move a mod up or down in Quartermaster's window to change the winner.
    <empty>
    Load order (enabled mods):
      <k>. <mod>
    <empty>
    Pairs:
      <a> <-> <b>: <n> conflicts[ - <mod> active in <n>, <mod> active in <n>];
        <n> close together (both active); <n> whole files[ (<mods>)][; <mod>
        left out of <n> files][; FAIL <n> core scripts both ship]   (one line)
    <empty>
    Core scripts (only one copy loads; the game may not start with both):
      scripts\<file>: <mod> and <mod>
    <empty>
    Conflicts (one version is active, the other is dropped):
    C<k> <path>, <range>, [state <Name>, ]<routines>
       at: <vanilla line>
       active: <mod>: <change>   dropped: <mod>: <change>[; <mod>: the same change]
       why: <k> is later in the load order
       kind: <kind> (by folder)
    <empty>
    Files written without a mod (all its changes in the file are dropped):
      <path>: without <mod> (<n> changes); the merged file does not compile,
        and it compiles without them                                (one line)
    <empty>
    Close together (both changes are active; check they do not fix the same thing twice):
    N<k> <path>, [state <Name>, ]<routines>
       at: <vanilla line>
       <a>: <range>   <b>: <range>
       kind: <kind> (by folder)
    <empty>
    Whole files (one copy is used, the other copies are not):
      <path>: <owner>'s copy; not used: <mods> (<why>; <kind>)

An empty section reads `  none`. A range is `ref.report.rng`'s. `<change>` is
`adds <m> lines`, `removes <n> lines`, `changes <n> lines` or `replaces <n>
lines with <m>` (one line: `line`). The window shows the pair lines
(`pair_lines`, at most `PAIR_LINES`) at the top of the Report view, and one
sentence per mod in its Details line (`details`).
"""
from .inc import code_words, values_from_lines
from .merge import CONFLICT_LOST, DUPLICATE
from .report import WINNER_WHY, _row, _who, ascii_lower, ranked, rng
from .textio import escape, read_lines, unescape, write_file

__all__ = ["FORMAT", "AT_CHARS", "PAIR_LINES", "kind", "routines", "where", "at_text",
           "change", "Conflicts", "build", "report_lines", "conflicts_bytes", "pair_lines",
           "details", "window"]

FORMAT = 1
#: `at:` keeps this many bytes of the vanilla line, the last three `...` when cut.
AT_CHARS = 60
#: Pair lines the window's Report view shows; conflicts.txt has them all.
PAIR_LINES = 14

#: The kind of a file by its folder, first match wins; the paths are
#: vanilla.idx's, lower case.
_KINDS = ((b"scripts\\lib\\", b"core script, whole game"),
          (b"scripts\\dmscript.", b"core script, whole game"),
          (b"scripts\\", b"script, gameplay"),
          (b"gui\\menu.inc\\", b"script, interface"),
          (b"gui\\common.inc\\", b"script, interface"),
          (b"gui\\", b"interface layout"),
          (b"hud\\", b"graphics"),
          (b"images\\", b"graphics"),
          (b"game\\var\\", b"data, gameplay"))

#: Why a whole file was used, beyond the planner's own reasons (WINNER_WHY).
_WHOLE_WHY = {
    "too-different": b"the copies differ too much to merge",
    "too-many-lines": b"the file is too long to merge",
    "replacement": b"a mod replaces most of the file",
}

_OPENERS = (b"case", b"try", b"record", b"asm")


def kind(path):
    p = ascii_lower(path)
    for prefix, text in _KINDS:
        if p.startswith(prefix):
            return text
    return b"data, content"


def _plural(n, word):
    return b"%d %s" % (n, word if n == 1 else word + b"s")


def routines(values):
    """Per Code value (bytes, leading `;` kept): the routine it sits in, as
    `(keyword, name)`, or None for the state's main code.

    A `procedure` or `function` word opens a routine named by the next word;
    its first `begin` one level deeper starts its body, and the `end` that
    comes back to its level closes it. `begin`, `case`, `try`, `record` and
    `asm` go one level deeper, `end` one back. The line that declares a
    routine or closes it belongs to it. Words as `ref.inc.code_words` reads
    them, so comments and strings do not count."""
    out = []
    stack = []          # [keyword, name, started, depth]
    depth = 0
    brace = False
    for v in values:
        text = v[1:] if v[:1] == b";" else v
        words, brace = code_words(text, brace, keep_case=True)
        here = None
        for k, w in enumerate(words):
            lw = w.lower()
            if lw in (b"procedure", b"function") and k + 1 < len(words):
                stack.append([lw, words[k + 1], False, depth])
                here = (lw, words[k + 1])
            elif lw == b"begin":
                depth += 1
                if stack and not stack[-1][2] and depth == stack[-1][3] + 1:
                    stack[-1][2] = True
            elif lw in _OPENERS:
                depth += 1
            elif lw == b"end":
                depth -= 1
                if stack and stack[-1][2] and depth == stack[-1][3]:
                    here = here or (stack[-1][0], stack[-1][1])
                    stack.pop()
        if here is None and stack:
            here = (stack[-1][0], stack[-1][1])
        out.append(here)
    return out


def where(rt, start, end):
    """The routines of the vanilla range [start, end): `procedure X`,
    `function Y` or `main code`, each once, in order. An insertion (start ==
    end) is placed by the line before it; past the last line, by the last."""
    n = len(rt)
    if n == 0:
        return b"main code"
    lines = range(start, end) if end > start else [max(start - 1, 0)]
    names = []
    for k in lines:
        r = rt[min(k, n - 1)]
        name = b"main code" if r is None else r[0] + b" " + r[1]
        if name not in names:
            names.append(name)
    return b", ".join(names)


def at_text(values, start):
    """The vanilla Code value at `start` (bytes), its leading `;` and the
    spaces and tabs around it cut, at most AT_CHARS bytes; `(end of file)`
    past the last one."""
    if start >= len(values):
        return b"(end of file)"
    t = values[start]
    if t[:1] == b";":
        t = t[1:]
    t = t.strip(b" \t")
    if len(t) > AT_CHARS:
        t = t[:AT_CHARS - 3] + b"..."
    return t


def change(h):
    """A hunk in words: `adds <m> lines`, `removes <n> lines`, `changes <n>
    lines` (as many as before) or `replaces <n> lines with <m>`."""
    old, new = h.end - h.start, len(h.lines)
    if old == 0:
        return b"adds " + _plural(new, b"line")
    if new == 0:
        return b"removes " + _plural(old, b"line")
    if old == new:
        return b"changes " + _plural(old, b"line")
    return b"replaces " + _plural(old, b"line") + b" with %d" % new


class _Pair(object):
    def __init__(self):
        self.conflicts = 0
        self.won = {}           # position -> conflicts that mod's change won
        self.near = 0
        self.whole = 0
        self.owners = []        # whose copy each whole file used (position or None)
        self.left = {}          # position -> files written without that mod
        self.core = 0

    def any(self):
        return bool(self.conflicts or self.near or self.whole or self.left or self.core)


class Conflicts(object):
    """The records of one generation, in plan order, and the pairs."""

    def __init__(self, dirs, enabled, self_pos):
        self.dirs, self.enabled, self.self_pos = ranked(dirs, enabled), sorted(enabled), self_pos
        self.core = []          # (file, a, b) positions, a before b
        self.conflicts = []     # (path, range, place, at, active, its change,
                                #  [(dropped, its change or None for a duplicate)], kind)
        self.left = []          # (path, position, changes)
        self.near = []          # (path, place, at, (pos, range), (pos, range), kind)
        self.whole = []         # (path, owner position or None, [not used], why, kind)
        self.pairs = {}
        self.lost = {}          # position -> {other: conflicts it lost to it}

    def pair(self, a, b):
        return self.pairs.setdefault((min(a, b), max(a, b)), _Pair())


def _name(c, pos):
    """A mod as the pair lines name it: its title, else its dir."""
    return c.dirs.titles.get(pos, b"") or c.dirs[pos]


def _num(c, pos):
    """A mod's number alone: its place on the Active list."""
    return b"%d" % c.dirs.ranks[pos]


def _state_name(keys):
    """The state's `Name = ` from an .inc's key lines (internal strings)."""
    for k in keys:
        t = k.lstrip(b" ")
        if t.startswith(b"Name = "):
            return unescape(t[len(b"Name = "):])
    return b""


def _code(read_vanilla, path):
    """`(state name, Code values as bytes)` of a vanilla .inc, read as the game
    side reads it (qmIncReadAt), or `(b"", [])` without one."""
    data = read_vanilla(path)
    if data is None:
        return b"", []
    _form, keys, values = values_from_lines(read_lines(data))
    return _state_name(keys), [unescape(v) for v in values]


def _place(state, rt, start, end):
    names = where(rt, start, end)
    return (b"state " + state + b", " + names) if state else names


def _merge_records(mg, only=None):
    """`(lost hunk, the hunk it lost to, its duplicates)` of merge `mg`;
    `only` keeps the hunks of those positions alone. For a subset file the
    full merge gives only the left-out mods' changes: another mod's duplicate
    of a lost change took part in the subset merge, which tells its fate."""
    out = []
    for h in mg.hunks:
        if h.status != CONFLICT_LOST or (only is not None and h.mod_id not in only):
            continue
        by = mg.hunks[h.conflict_with[-1]]
        dups = [d for d in mg.hunks if d.status == DUPLICATE and d.duplicate_of == h.index
                and (only is None or d.mod_id in only)]
        out.append((h, by, dups))
    return out


def build(g, dirs, enabled, self_pos, read_vanilla, boot=None):
    """The `Conflicts` of generation `g` (`ref.report.report_lines`' inputs,
    and `read_vanilla(path)` for the vanilla .inc the records point into)."""
    c = Conflicts(dirs, enabled, self_pos)
    # The lowest position with a dir, as the report's _clash_lines finds it.
    lower = dict((ascii_lower(d), p) for p, d in sorted(c.dirs.items(), reverse=True))
    for a, b, path in (boot.clashes if boot is not None else ()):
        pa, pb = lower.get(ascii_lower(a)), lower.get(ascii_lower(b))
        if pa is None or pb is None:
            continue
        pa, pb = min(pa, pb), max(pa, pb)
        c.core.append((path, pa, pb))
        c.pair(pa, pb).core += 1
    for r in g.paths:
        _path_records(c, r, read_vanilla)
    return c


def _path_records(c, r, read_vanilla):
    d = r.decision
    path = d.path
    k = kind(path)
    if d.action == b"winner":
        if len(d.providers) >= 2:
            _whole(c, path, d.providers[-1], d.providers[:-1],
                   WINNER_WHY.get(d.reason, d.reason), k)
        return
    if d.action not in (b"merge-inc", b"hook"):
        return
    parts = list(r.participants)
    if len(parts) < 2:
        return
    tier = r.chosen.tier if r.chosen is not None else b""
    mg = r.merge
    if tier.startswith(b"merged") or tier.startswith(b"subset"):
        state, values = _code(read_vanilla, path)
        rt = routines(values)
        subset = tier.startswith(b"subset")
        found = _merge_records(mg, set(r.left_out) if subset else None)
        if subset and r.sub_merge is not None:
            found += _merge_records(r.sub_merge)
        for h, by, dups in found:
            s, e = min(h.start, by.start), max(h.end, by.end)
            c.conflicts.append((path, rng(s, e, r.first_line, r.vanilla_n),
                                _place(state, rt, s, e), at_text(values, s), by.mod_id, change(by),
                                [(h.mod_id, change(h))] + [(x.mod_id, None) for x in dups], k))
            for lost in [h.mod_id] + [x.mod_id for x in dups]:
                p = c.pair(lost, by.mod_id)
                p.conflicts += 1
                p.won[by.mod_id] = p.won.get(by.mod_id, 0) + 1
                mine = c.lost.setdefault(lost, {})
                mine[by.mod_id] = mine.get(by.mod_id, 0) + 1
        written = r.sub_merge if subset else mg
        if subset:
            for lo in r.left_out:
                c.left.append((path, lo, sum(1 for h in mg.hunks if h.mod_id == lo)))
                for w in parts:
                    if w not in r.left_out:
                        p = c.pair(lo, w)
                        p.left[lo] = p.left.get(lo, 0) + 1
        if written is not None:
            for a, b in written.pairs:
                ha, hb = written.hunks[a], written.hunks[b]
                s, e = min(ha.start, hb.start), max(ha.end, hb.end)
                c.near.append((path, _place(state, rt, s, e), at_text(values, s),
                               (ha.mod_id, rng(ha.start, ha.end, r.first_line, r.vanilla_n)),
                               (hb.mod_id, rng(hb.start, hb.end, r.first_line, r.vanilla_n)), k))
                c.pair(ha.mod_id, hb.mod_id).near += 1
        return
    # One copy, or none: the winner's (fallback, a merge that gave up or
    # failed, nothing that compiles - the game then loads the last mod's),
    # or vanilla's with Quartermaster's hook lines.
    if tier.startswith(b"vanilla"):
        _whole(c, path, None, parts, b"neither the merge nor a mod's copy compiles", k)
        return
    if mg is not None and mg.mode == "winner" and mg.reason in _WHOLE_WHY:
        why = _WHOLE_WHY[mg.reason]
    elif r.merge_err:
        why = b"the merge failed"
    elif tier.startswith(b"winner"):
        why = b"the merged file does not compile"
    elif r.code == b"wta" or r.code == b"wtahook":
        why = b"not merged after a suspected start-up failure"
    else:
        why = b"no candidate compiles"
    owner = r.winner if r.winner is not None else parts[-1]
    _whole(c, path, owner, [p for p in parts if p != owner], why, k)


def _whole(c, path, owner, others, why, k):
    c.whole.append((path, owner, list(others), why, k))
    if owner is None:
        for x, a in enumerate(others):
            for b in others[x + 1:]:
                p = c.pair(a, b)
                p.whole += 1
                p.owners.append(None)
        return
    for o in others:
        p = c.pair(o, owner)
        p.whole += 1
        p.owners.append(owner)


def _pair_line(c, a, b, p):
    head = _plural(p.conflicts, b"conflict")
    if p.conflicts:
        head += b" - %s active in %d, %s active in %d" % (
            _name(c, b), p.won.get(b, 0), _name(c, a), p.won.get(a, 0))
    bits = [head, b"%d close together (both active)" % p.near]
    whole = _plural(p.whole, b"whole file")
    if p.whole:
        # Whose copies they were: the mods in load order, vanilla last; with
        # more than one, how many each.
        owners = sorted(set(p.owners), key=lambda o: (o is None, o))
        names = [b"vanilla" if o is None else _name(c, o) for o in owners]
        if len(owners) > 1:
            names = [n + b" %d" % p.owners.count(o) for n, o in zip(names, owners)]
        whole += b" (" + b", ".join(names) + b")"
    bits.append(whole)
    for lo in (a, b):
        if p.left.get(lo):
            bits.append(_name(c, lo) + b" left out of " + _plural(p.left[lo], b"file"))
    if p.core:
        bits.append(b"FAIL " + _plural(p.core, b"core script") + b" both ship")
    return b"  " + _num(c, a) + b" <-> " + _num(c, b) + b": " + b"; ".join(bits)


def pair_lines(c):
    """One line per pair of mods with a record, in load order."""
    return [_pair_line(c, a, b, p) for (a, b), p in sorted(c.pairs.items()) if p.any()]


def details(c, pos):
    """The window's Details sentence for the mod at `pos`, without its full
    stop: the first file it is left out of, else the mod it loses the most
    conflicts to, else the one it wins the most over (the lower number on a
    tie); `b""` without either."""
    for path, lo, _n in c.left:
        if lo == pos:
            return b"Left out of " + path
    lost = c.lost.get(pos, {})
    if lost:
        other = min(lost, key=lambda o: (-lost[o], o))
        return b"Loses " + _plural(lost[other], b"conflict") + b" to " + _name(c, other)
    won = {}
    for lp, against in c.lost.items():
        if pos in against:
            won[lp] = against[pos]
    if won:
        other = min(won, key=lambda o: (-won[o], o))
        return b"Wins " + _plural(won[other], b"conflict") + b" over " + _name(c, other)
    return b""


def window(c):
    """What the window shows of it (ref/report.py mod_lines, qm_report): the
    pair lines, at most PAIR_LINES and then a line that counts the rest, and
    `{position: Details sentence}` of the enabled mods that have one."""
    lines = pair_lines(c)
    if len(lines) > PAIR_LINES:
        lines = lines[:PAIR_LINES] + [b"  ... and %d more pairs: see conflicts.txt"
                                      % (len(lines) - PAIR_LINES)]
    phrases = dict((p, details(c, p)) for p in c.enabled)
    return lines, dict((p, s) for p, s in phrases.items() if s)


def report_lines(c, g, version):
    """conflicts.txt as lines (bytes, no line ends)."""
    out = [b"Quartermaster conflict report",
           b"format %d, Quartermaster %s, generation %d, outputs hash %s" % (
               FORMAT, version, g.gen, g.outhash),
           b"rule: where two mods change the same lines, the mod later in the load order wins.",
           b"      Move a mod up or down in Quartermaster's window to change the winner.",
           b"", b"Load order (enabled mods):"]
    out += [b"  " + _row(pos, c.dirs, c.self_pos) for pos in c.enabled]
    out += [b"", b"Pairs:"] + (pair_lines(c) or [b"  none"])
    out += [b"", b"Core scripts (only one copy loads; the game may not start with both):"]
    out += [b"  scripts\\" + f + b": " + _who(a, c.dirs) + b" and " + _who(b, c.dirs)
            for f, a, b in c.core] or [b"  none"]
    out += [b"", b"Conflicts (one version is active, the other is dropped):"]
    if not c.conflicts:
        out.append(b"  none")
    for k, (path, rg, place, at, active, achange, dropped, kd) in enumerate(c.conflicts, 1):
        drop = b"; ".join(_who(p, c.dirs) + b": " + (ch or b"the same change")
                          for p, ch in dropped)
        out += [b"C%d %s, %s, %s" % (k, path, rg, place),
                b"   at: " + at,
                b"   active: " + _who(active, c.dirs) + b": " + achange + b"   dropped: " + drop,
                b"   why: " + _num(c, active) + b" is later in the load order",
                b"   kind: " + kd + b" (by folder)"]
    out += [b"", b"Files written without a mod (all its changes in the file are dropped):"]
    out += [b"  %s: without %s (%s); the merged file does not compile, and it compiles "
            b"without them" % (path, _who(lo, c.dirs), _plural(n, b"change"))
            for path, lo, n in c.left] or [b"  none"]
    out += [b"", b"Close together (both changes are active; check they do not fix the same "
            b"thing twice):"]
    if not c.near:
        out.append(b"  none")
    for k, (path, place, at, (pa, ra), (pb, rb), kd) in enumerate(c.near, 1):
        out += [b"N%d %s, %s" % (k, path, place),
                b"   at: " + at,
                b"   " + _num(c, pa) + b": " + ra + b"   " + _num(c, pb) + b": " + rb,
                b"   kind: " + kd + b" (by folder)"]
    out += [b"", b"Whole files (one copy is used, the other copies are not):"]
    out += [b"  %s: %s's copy; not used: %s (%s; %s)" % (
        path, b"vanilla" if owner is None else _who(owner, c.dirs),
        b", ".join(_who(p, c.dirs) for p in others), why, kd)
        for path, owner, others, why, kd in c.whole] or [b"  none"]
    return out


def conflicts_bytes(lines):
    """conflicts.txt as the game's raw writer writes the lines."""
    return write_file([escape(line) for line in lines])
