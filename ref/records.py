r"""Record profiles of the Phase B data files (docs/plan.md S3, S10; G7 the
record splitter, G10 the record merger): the twin of the game side's data
merge (src/lib/qmrec.pas, src/states/qmdatamerge.pas).

The four files (vanilla `data\game\var\`) share one layout, read off the
installed game (every one of them: one root `section.begin` - formations.cfg
names it `formations : section.begin` - holding records at indent 3, each
`   [*] : struct.begin` ... `   struct.end`, nested structs deeper) and a key
that names each record, unique in vanilla (checked 2026-09-28: hotkeys.cfg
55 records by `Action`, objcustom.cfg 241 by `sid`, wallcustom.cfg 17 by
`WallVariation`, formations.cfg 149 by `id`):

    section.begin
       // buildings                <- belongs to the next record (its prefix)
       [*] : struct.begin
          Key = C
          Action = build|%nat%cen  <- the key line: at the record's own depth
       struct.end
    section.end

A record starts with `[*] : struct.begin` - spaces do not count, since
objcustom.cfg:26641 has `[*]: struct.begin` and the engine's parser takes
it. Lines are the raw reader's internal strings (ref/textio.py read_lines),
as on the game side (a report line shows a key as its bytes: `|` is ~124
there); `split` fails - None - on anything it does not understand
(no root, an unbalanced struct, a line at the root that is neither a record,
a comment nor empty, a record without its key, a key twice), and the merge
then keeps the winner's whole file (plan S10: fail-closed).

The merge, per key, against vanilla: every mod that ships the file changes a
record, removes it or leaves it alone; the last one in load order that
touched it decides (a mod that removes a record another one changed, or two
different changes, is a conflict: WARN, later wins). Records vanilla does not
have are added after vanilla's, in load order. Then the checks: structs
balanced, keys unique, and the bounds the game's loaders rely on - read from
the installed game, dmscript.global:136-165 and the loaders that fill fixed
arrays without a bound (country.script:4084-4200, init.script:9-11). Any
failure writes nothing: the winner's file stays in effect (FAIL).
"""
from ref import textio as T

__all__ = ["Profile", "PROFILES", "Record", "Split", "split", "join", "norm", "Merged",
           "merge", "check", "key_pairs", "limits_from_global", "BOUND_NAMES", "OK", "WARN",
           "FAIL"]

OK, WARN, FAIL = b"OK", b"WARN", b"FAIL"

TAB = b"~009"


class Profile(object):
    """What a file's records are keyed by and what the game allows.

    Each bound names the dmscript.global constant the game sizes it with and
    vanilla's value of it (dmscript.global:136-165): `arrays` - child structs
    of a record whose direct `[*]` children fill a fixed array; `max_records`
    - the most records the loader accepts; `key_range` - an integer key used
    as an array index, 0 up to the constant minus one. A total conversion
    that ships its own dmscript.global may raise a constant (State vs Country:
    gc_formation_maxcount = 203), and one that ships its own loader may go
    past one (its objcustom.cfg has 50 shot points in a record, the constant
    says 40) - so `check` allows the larger of the constant in effect and
    what an input file already has."""

    def __init__(self, key, arrays=(), max_records=None, key_range=None, hotkeys=False):
        self.key, self.arrays = key, list(arrays)
        self.max_records, self.key_range, self.hotkeys = max_records, key_range, hotkeys


PROFILES = {
    # registershortcuts.inc:194-198 reads Key, AlternativeKey, Action.
    b"game\\var\\hotkeys.cfg": Profile(b"action", hotkeys=True),
    # classes.script:4265-4271, country.script:4130-4200: builderPoints,
    # exitPoints, shotPoints are filled to the parser's count; smokePoints is
    # cut to its length (Min, :4192) and needs no check.
    b"game\\var\\objcustom.cfg": Profile(b"sid", arrays=(
        (b"builderpoints", b"gc_maxbuildercount", 30),
        (b"exitpoints", b"gc_maxexitpointscount", 4),
        (b"shotpoints", b"gc_maxshotpointscount", 40))),
    # classes.script:4250, :7664, country.script:4091-4097: builderPoints to
    # the parser's count, WallVariation an index into the variation array.
    b"game\\var\\wallcustom.cfg": Profile(b"wallvariation", arrays=(
        (b"builderpoints", b"gc_maxwallbuilderpointscount", 16),),
        key_range=(b"gc_maxwallvariationcount", 24)),
    # init.script:9-11: more formations than gc_formation_maxcount and none is
    # loaded at all.
    b"game\\var\\formations.cfg": Profile(b"id", max_records=(b"gc_formation_maxcount", 160)),
}

#: The constants the bounds use.
BOUND_NAMES = (b"gc_maxbuildercount", b"gc_maxexitpointscount", b"gc_maxshotpointscount",
               b"gc_maxwallbuilderpointscount", b"gc_maxwallvariationcount",
               b"gc_formation_maxcount")


def limits_from_global(lines):
    """`{constant: value}` of the bound constants a dmscript.global declares:
    a line `<name> = <digits>...` (case folded; what follows the digits -
    `;`, a `{...}` note - does not count). The first declaration counts."""
    out = {}
    for line in lines:
        s = _lower(_strip(line))
        eq = s.find(b"=")
        if eq <= 0:
            continue
        name = _strip(s[:eq])
        if name in BOUND_NAMES and name not in out:
            v = _strip(s[eq + 1:])
            digits = b""
            for c in v:
                if 48 <= c <= 57:
                    digits += bytes([c])
                else:
                    break
            if digits:
                out[name] = int(digits)
    return out


def _strip(text):
    while True:
        if text.startswith(b" "):
            text = text[1:]
        elif text.startswith(TAB):
            text = text[4:]
        elif text.endswith(b" "):
            text = text[:-1]
        elif text.endswith(TAB):
            text = text[:-4]
        else:
            return text


def _lower(text):
    return bytes(c + 32 if 65 <= c <= 90 else c for c in text)


def norm(line):
    """A line as records are compared by: tabs as spaces, no trailing space
    (ref/textio.py norm_key_escaped); the file's leading BOM is not in a record."""
    return T.norm_key_escaped(line)


class Record(object):
    def __init__(self, key, prefix, lines):
        self.key, self.prefix, self.lines = key, prefix, lines

    @property
    def body(self):
        return [norm(ln) for ln in self.lines]

    def __repr__(self):
        return "Record(%r, %d+%d lines)" % (self.key, len(self.prefix), len(self.lines))


class Split(object):
    def __init__(self, header, records, trailer):
        self.header, self.records, self.trailer = header, records, trailer
        self.by_key = dict((r.key, r) for r in records)


def _kind(line):
    s = _lower(_strip(line))
    if s.endswith(b"struct.begin"):
        return b"begin"
    if s == b"struct.end":
        return b"end"
    if s.endswith(b"section.begin"):
        return b"root"
    if s == b"section.end":
        return b"rootend"
    if s == b"" or s.startswith(b"//"):
        return b"note"
    return b"value"


def split(lines, profile):
    """Split of `lines` (internal strings), or None when it is not the layout."""
    header, records, pending, trailer = [], [], [], []
    state = 0          # 0 before the root, 1 in it, 2 in a record, 3 after it
    depth = 0
    cur = None
    key = None
    for line in lines:
        k = _kind(line)
        if state == 0:
            header.append(line)
            if k == b"root":
                state = 1
            elif k != b"note":
                return None
        elif state == 1:
            if k == b"begin" and _lower(_strip(line)).replace(b" ", b"") == b"[*]:struct.begin":
                cur, key, depth, state = [line], None, 1, 2
            elif k == b"rootend":
                trailer = pending + [line]
                pending, state = [], 3
            elif k == b"note":
                pending.append(line)
            else:
                return None
        elif state == 2:
            cur.append(line)
            if k == b"begin":
                depth += 1
            elif k == b"end":
                depth -= 1
                if depth == 0:
                    if key is None:
                        return None
                    records.append(Record(key, pending, cur))
                    pending, cur, state = [], None, 1
            elif k == b"rootend" or k == b"root":
                return None
            elif depth == 1 and key is None and k == b"value":
                s = _strip(line)
                eq = s.find(b"=")
                if eq > 0 and _lower(_strip(s[:eq])) == profile.key:
                    key = _strip(s[eq + 1:])
        else:
            trailer.append(line)
    if state != 3 or len(set(_lower(r.key) for r in records)) != len(records):
        return None
    return Split(header, records, trailer)


def join(sp):
    out = list(sp.header)
    for r in sp.records:
        out += r.prefix + r.lines
    return out + sp.trailer


class Merged(object):
    def __init__(self):
        self.lines = None
        self.status = OK
        self.lines_out = []     # report lines: (tag, text)
        self.source = {}        # key -> the mod index its record came from (-1 vanilla)
        self.problem = b""

    def note(self, tag, text):
        self.lines_out.append((tag, text))
        if tag == FAIL or (tag == WARN and self.status == OK):
            self.status = tag


def _show(key):
    """A key as a report line shows it: the bytes it stands for."""
    return T.unescape(key)


def merge(base, mods, profile, names=None, limits=None):
    """Merge of `mods` (a list of line lists, load order) over `base`
    (vanilla's lines). `names` are the mods' names for the report lines,
    `limits` the bound constants of the dmscript.global in effect
    (limits_from_global; vanilla's values when None)."""
    names = names or [b"mod %d" % i for i in range(len(mods))]
    m = Merged()
    b = split(base, profile)
    if b is None:
        m.note(FAIL, b"vanilla's file is not the record layout")
        return m
    splits = []
    for i, lines in enumerate(mods):
        s = split(lines, profile)
        if s is None:
            m.note(FAIL, b"%s: the file is not the record layout" % names[i])
            return m
        splits.append(s)
    out = []
    lowkey = lambda k: _lower(k)
    base_keys = [lowkey(r.key) for r in b.records]
    for r in b.records:
        k = lowkey(r.key)
        touched = []        # (mod index, record or None for removed)
        for i, s in enumerate(splits):
            mr = next((x for x in s.records if lowkey(x.key) == k), None)
            if mr is None:
                touched.append((i, None))
            elif mr.body != r.body:
                touched.append((i, mr))
        if not touched:
            out.append(r)
            m.source[k] = -1
            continue
        last_i, last_r = touched[-1]
        versions = set(tuple(t.body) if t is not None else None for _i, t in touched)
        if len(versions) > 1:
            who = b", ".join(names[i] for i, _t in touched)
            m.note(WARN, b"record %s: changed by %s differently; %s's version is used"
                   % (_show(r.key), who, names[last_i]))
        if last_r is None:
            m.note(OK, b"record %s: removed by %s" % (_show(r.key), names[last_i]))
            m.source[k] = last_i
            continue
        out.append(last_r)
        m.source[k] = last_i
        m.note(OK, b"record %s: from %s" % (_show(r.key), names[last_i]))
    added = []
    for i, s in enumerate(splits):
        for r in s.records:
            k = lowkey(r.key)
            if k in base_keys:
                continue
            prev = next((j for j, (_i, a) in enumerate(added) if lowkey(a.key) == k), None)
            if prev is None:
                added.append((i, r))
            else:
                if added[prev][1].body != r.body:
                    m.note(WARN, b"record %s: added by %s and %s differently; %s's version is used"
                           % (_show(r.key), names[added[prev][0]], names[i], names[i]))
                added[prev] = (i, r)
    for i, r in added:
        out.append(r)
        m.source[lowkey(r.key)] = i
        m.note(OK, b"record %s: added by %s" % (_show(r.key), names[i]))
    merged = Split(b.header, out, b.trailer)
    problem = check(merged, profile, limits, [b] + splits)
    if problem:
        m.note(FAIL, problem)
        m.problem = problem
        return m
    if profile.hotkeys:
        _hotkey_collisions(merged, m, names, [b] + splits)
    m.lines = join(merged)
    return m


def _children(record, name):
    """The direct `[*]` children of the record's struct `name`, or -1."""
    depth, inside, count = 0, False, -1
    for line in record.lines[1:-1]:
        k = _kind(line)
        s = _lower(_strip(line))
        if k == b"begin":
            depth += 1
            if depth == 1 and s.split(b":")[0].strip() == name:
                inside, count = True, 0
            elif inside and depth == 2:
                count += 1
        elif k == b"end":
            if depth == 1 and inside:
                inside = False
            depth -= 1
        elif inside and depth == 1 and k == b"value" and s.startswith(b"[*]"):
            count += 1
    return count


def _key_int(key):
    return int(key) if key.lstrip(b"-").isdigit() and key.count(b"-") <= 1 and not key.endswith(b"-") else None


def check(sp, profile, limits=None, inputs=()):
    """The first problem of a merged split, b"" when it is fine. A bound is
    the larger of its constant in effect (`limits`, else vanilla's value) and
    what an input split already has: a merge may not go past a bound further
    than one of the files it merges already does."""
    limits = limits or {}
    lines = join(sp)
    begins = sum(1 for ln in lines if _kind(ln) in (b"begin", b"root"))
    ends = sum(1 for ln in lines if _kind(ln) in (b"end", b"rootend"))
    if begins != ends:
        return b"the merged file has unbalanced structs"
    keys = [_lower(r.key) for r in sp.records]
    if len(set(keys)) != len(keys):
        return b"the merged file has a key twice"
    if profile.max_records:
        const, vanilla = profile.max_records
        allowed = max([limits.get(const, vanilla)] + [len(i.records) for i in inputs])
        if len(sp.records) > allowed:
            return b"%d records, the game loads none above %d" % (len(sp.records), allowed)
    if profile.key_range:
        const, vanilla = profile.key_range
        top = max([limits.get(const, vanilla) - 1] + [
            _key_int(r.key) for i in inputs for r in i.records if _key_int(r.key) is not None])
        for r in sp.records:
            v = _key_int(r.key)
            if v is None or v < 0 or v > top:
                return b"record %s: the key must be 0..%d" % (_show(r.key), top)
    for name, const, vanilla in profile.arrays:
        allowed = max([limits.get(const, vanilla)] + [
            _children(r, name) for i in inputs for r in i.records])
        for r in sp.records:
            n = _children(r, name)
            if n > allowed:
                return b"record %s: %s has %d entries, the game holds %d" % (_show(r.key), name, n, allowed)
    return b""


def key_pairs(sp):
    """`{(key value, action a, action b)}` (a < b, all folded): two records
    of one file bound to the same key or alternative key."""
    users = {}
    for r in sp.records:
        for line in r.lines:
            s = _strip(line)
            eq = s.find(b"=")
            if eq > 0 and _lower(_strip(s[:eq])) in (b"key", b"alternativekey"):
                v = _lower(_strip(s[eq + 1:]))
                if v:
                    users.setdefault(v, set()).add(_lower(r.key))
    out = set()
    for v, acts in users.items():
        acts = sorted(acts)
        for i in range(len(acts)):
            for j in range(i + 1, len(acts)):
                out.add((v, acts[i], acts[j]))
    return out


def _hotkey_collisions(merged, m, names, inputs):
    """Two actions the merge put on one key, where no single input - vanilla
    or a mod's own file - has them on it together: WARN, the player may want
    to rebind one (plan S10: hotkeys merged by Action with a key-collision
    check). Pairs a file already has are that file's own choice."""
    known = set()
    for sp in inputs:
        known |= key_pairs(sp)
    for v, a, b in sorted(key_pairs(merged) - known):
        m.note(WARN, b"key %s: %s and %s are on it now" % (_show(v), _show(a), _show(b)))
