r"""Three-way merge of several mods against vanilla, and the classifier.

This is the algorithm of the probe-5 merge (2026-09-27), the one that ran inside
the game and whose output ran natively after a restart (log r5c.0.log:24-34,
r5c.1.log:23-25), with the diff replaced by `ref.diff` and the classifier rules
of docs/plan.md section 3 (G9) added:

1. Every participant is diffed against vanilla on normalised keys
   (`ref.textio.norm_key`). Participants come in canonical order
   (`ref.order`), so "later" always means later in that order.
2. A diff that is given up (D over the cap, or a file over the line cap) makes
   the whole file winner-takes-all, status fail: the last participant's file is
   used as it is.
3. A participant whose diff deletes or replaces more than half of the vanilla
   lines (`2*deleted > n` in Integers) is a full replacement. Merging it with
   anything else would splice two different files, so if another participant
   makes a different change to the file it is winner-takes-all, status warn;
   alone, or with participants that made the very same change, it merges like
   any other. Inserted lines do not count: a mod that only adds code keeps
   every vanilla line, and others' edits to those lines still apply. "Half of
   the vanilla lines" is counted on the diff, not on the trimmed region: the
   probe-5 mod B trimmed to 72x72 of 73 lines and changed three of them
   (docs/research/reviews.md A.2).
4. Hunks of different participants that overlap - the same start, or
   intersecting ranges, exactly the probe's test - are resolved pairwise in hunk
   order: identical hunks keep the first and drop the second (deduplicated,
   fine); different ones drop the earlier and keep the later (conflict, later
   wins, warn).
5. Kept hunks of different participants with at most `proximity` vanilla lines
   between them are flagged (warn): each applies cleanly, but code that close
   together often depends on each other.
6. The output is vanilla with the kept hunks applied. Unchanged lines are
   vanilla's own bytes; changed lines are the participant's bytes.
7. Quartermaster's hook lines are not a participant. They go into the Code
   values after the merge (`insert_hook`), at the hook index of plan S5
   (`ref.inc.hook_index`: before the first top-level Code line after the
   routines a state starts with), so they never take part in a diff and no
   other mod's edit can conflict with them; the same step puts them into the
   winner's file when the file went winner-takes-all (plan S5: Quartermaster
   always merges its own hook lines).

A hunk's status, strongest first: conflict-won, proximity, identical, clean -
and, for a dropped hunk, conflict-lost or duplicate.

`result_rows` is the result as flat `|`-separated rows: what the game side
dumps and keeps for the report, so the two sides are compared row by row.
"""
from .diff import DEFAULT_BUDGET, diff
from .inc import EMPTY_VALUE, insert_at_hook, parse, render, render_raw
from .textio import escape, norm_key, read_raw_lines, write_file

__all__ = ["PROXIMITY_LINES", "REPLACEMENT_SHARE", "OK", "WARN", "FAIL",
           "MergeHunk", "ParticipantInfo", "MergeResult", "keys_of", "merge",
           "insert_hook", "final_lines", "padded", "merge_inc", "merge_text",
           "describe", "result_rows"]

#: "distinct edits within <= 3 lines of each other -> proximity" (docs/plan.md G9).
PROXIMITY_LINES = 3
#: "edits more than 50% of the vanilla lines -> full replacement".
REPLACEMENT_SHARE = 0.5

#: The three report tags (docs/plan.md uses check mark, warning sign and cross).
OK, WARN, FAIL = "ok", "warn", "fail"

CLEAN = "clean"
IDENTICAL = "identical"
DUPLICATE = "duplicate"
CONFLICT_WON = "conflict-won"
CONFLICT_LOST = "conflict-lost"
PROXIMITY = "proximity"


class MergeHunk(object):
    """One participant's hunk, and what the merge did with it."""

    def __init__(self, index, participant, mod_id, start, end, lines, keys):
        self.index = index
        self.participant = participant
        self.mod_id = mod_id
        self.start = start
        self.end = end
        self.lines = lines
        self.keys = keys
        self.kept = True
        self.conflict_with = []
        self.duplicate_of = None
        self.duplicates = []
        self.proximity_with = []

    @property
    def status(self):
        if not self.kept:
            return DUPLICATE if self.duplicate_of is not None else CONFLICT_LOST
        if self.conflict_with:
            return CONFLICT_WON
        if self.proximity_with:
            return PROXIMITY
        if self.duplicates:
            return IDENTICAL
        return CLEAN

    def __repr__(self):
        return "MergeHunk(%d, %r, [%d,%d) +%d, %s)" % (
            self.index, self.mod_id, self.start, self.end, len(self.lines),
            self.status)


class ParticipantInfo(object):
    """Per participant: its diff figures and whether it is a replacement."""

    def __init__(self, mod_id, result, replacement):
        self.mod_id = mod_id
        self.ok = result.ok
        self.reason = result.reason
        self.d = result.d
        self.deleted = result.deleted
        self.inserted = result.inserted
        self.cells = result.cells
        self.replacement = replacement

    def __repr__(self):
        return "ParticipantInfo(%r, d=%s, deleted=%s, replacement=%s)" % (
            self.mod_id, self.d, self.deleted, self.replacement)


class MergeResult(object):
    """mode     'vanilla' (nobody changes anything), 'merged' or 'winner'
    status   OK / WARN / FAIL
    reason   None, or why the file went winner-takes-all
             ('too-different', 'too-many-lines', 'replacement')
    winner   participant index whose file is used as it is (mode 'winner')
    lines    the output lines: vanilla's, the merged ones, or the winner's own
    pairs    the proximity pairs `(a, b)` as hunk indices, in the order they
             were found (kept hunks sorted by start, `a` before `b`)
    """

    def __init__(self, mode, status, reason, winner, lines, hunks, participants,
                 pairs=()):
        self.mode = mode
        self.status = status
        self.reason = reason
        self.winner = winner
        self.lines = lines
        self.hunks = hunks
        self.participants = participants
        self.pairs = list(pairs)

    @property
    def conflicts(self):
        return sum(1 for h in self.hunks if h.status == CONFLICT_LOST)

    @property
    def proximity_pairs(self):
        return sum(len(h.proximity_with) for h in self.hunks) // 2

    def __repr__(self):
        return "MergeResult(%s, %s, %d hunks, %d conflicts)" % (
            self.mode, self.status, len(self.hunks), self.conflicts)


def keys_of(lines):
    return [norm_key(line, first=(i == 0)) for i, line in enumerate(lines)]


def _overlap(a, b):
    """The probe-5 test: same start, or intersecting ranges."""
    return a.start == b.start or (a.start < b.end and b.start < a.end)


def merge(base, mods, budget=DEFAULT_BUDGET, proximity=PROXIMITY_LINES,
          replacement_share=REPLACEMENT_SHARE):
    """Merge `mods` = [(mod_id, lines)] (canonical order) into `base` lines."""
    base_keys = keys_of(base)
    n = len(base)
    last = len(mods) - 1
    participants = []
    diffs = []
    keys = []
    for mod_id, lines in mods:
        keys.append(keys_of(lines))
        result = diff(base_keys, keys[-1], budget=budget)
        replacement = bool(result.ok and result.deleted > replacement_share * n)
        participants.append(ParticipantInfo(mod_id, result, replacement))
        diffs.append(result)
        if not result.ok:
            return MergeResult("winner", FAIL, result.reason, last,
                               list(mods[last][1]), [], participants)

    changers = [i for i, r in enumerate(diffs) if r.hunks]
    if not changers:
        return MergeResult("vanilla", OK, None, None, list(base), [], participants)
    # Two participants that made the very same change do not make a replacement
    # a conflict: their hunks deduplicate below like any identical edit.
    differing = len(set(tuple(keys[i]) for i in changers)) > 1
    if differing and any(participants[i].replacement for i in changers):
        return MergeResult("winner", WARN, "replacement", last,
                           list(mods[last][1]), [], participants)

    hunks = []
    for i in changers:
        mod_id, lines = mods[i]
        mod_keys = keys[i]
        for h in diffs[i].hunks:
            hunks.append(MergeHunk(len(hunks), i, mod_id, h.start, h.end,
                                   lines[h.mod_start:h.mod_end],
                                   mod_keys[h.mod_start:h.mod_end]))

    for a in hunks:
        for b in hunks[a.index + 1:]:
            if not (a.kept and b.kept) or a.participant == b.participant:
                continue
            if not _overlap(a, b):
                continue
            if (a.start, a.end, a.keys) == (b.start, b.end, b.keys):
                b.kept = False
                b.duplicate_of = a.index
                a.duplicates.append(b.index)
            else:
                a.kept = False
                a.conflict_with.append(b.index)
                b.conflict_with.append(a.index)

    kept = sorted((h for h in hunks if h.kept), key=lambda h: (h.start, h.end))
    pairs = []
    for x, a in enumerate(kept):
        for b in kept[x + 1:]:
            if b.start - a.end > proximity:
                break
            if a.participant != b.participant:
                a.proximity_with.append(b.index)
                b.proximity_with.append(a.index)
                pairs.append((a.index, b.index))

    out = []
    pos = 0
    for h in kept:
        out.extend(base[pos:h.start])
        out.extend(h.lines)
        pos = h.end
    out.extend(base[pos:])

    status = WARN if any(h.status in (CONFLICT_WON, PROXIMITY) for h in hunks) else OK
    return MergeResult("merged", status, None, None, out, hunks, participants, pairs)


def insert_hook(values, hook):
    """Code values with Quartermaster's hook lines at the hook index (plan S5).

    The index is taken on the values the hook lines go into - the merge's
    result, or the winner's file - by the one rule `ref.inc.hook_index`, which
    the static hooked copy and the game side (qmIncHookIndex) use too, so the
    hook block sits in the same place in every generation.
    """
    return insert_at_hook(values, hook)


def final_lines(result, hook=None):
    """The final line list a writer gets, or None when nothing is written.

    The result's lines - the merged ones, vanilla's, or the winner's own - with
    the hook lines at the hook index (`insert_hook`). A winner-takes-all result
    without hook lines writes nothing: the winner's own file is what the engine
    loads.
    """
    if result.mode == "winner" and hook is None:
        return None
    return insert_hook(result.lines, hook or [])


def padded(values, count):
    """`values` padded with `;` up to `count`: what a parser write needs, as a
    Code line cannot be removed through the parser."""
    return list(values) + [EMPTY_VALUE] * max(0, count - len(values))


def merge_inc(vanilla, mods, hook=None, writer="parser", **kw):
    """`.inc` bytes in, `(MergeResult, output bytes)` out.

    The output is vanilla's file (the winner's, for winner-takes-all with hook
    lines) with the final line list (`final_lines`) as its Code values, or the
    winner's file unchanged when there is nothing to write. `writer` says how
    the game side writes it:

      "raw"     through the raw writer, the way the game side writes (decided
                2026-09-28): the final line list as it is, in the
                engine's layout for its count, plus the writer's padding to a
                multiple of 4 (`ref.inc.render_raw`).
      "parser"  through the engine's parser, as the probe-5 merge did: the
                values padded with `;` to the loaded file's count
                (`ref.inc.render`). Its bytes are what probe 5 wrote; the
                game side no longer writes this way (the parser appends one
                value only, run m2a), the writer stays for that record.

    Raises `ref.inc.IncFormatError` when a participant's file is not a
    well-formed `.inc`.
    """
    if writer not in ("parser", "raw"):
        raise ValueError("writer is 'parser' or 'raw', not %r" % (writer,))
    v = parse(vanilla)
    parsed = [(mod_id, parse(data).values) for mod_id, data in mods]
    result = merge(v.values, parsed, **kw)
    final = final_lines(result, hook)
    if final is None:
        return result, mods[result.winner][1]
    target = parse(mods[result.winner][1]) if result.mode == "winner" else v
    if writer == "raw":
        return result, render_raw(target, final)
    return result, render(target, padded(final, len(target.values)))


def merge_text(vanilla, mods, **kw):
    """Raw text bytes in (read as the game's raw reader reads them), bytes out."""
    base = read_raw_lines(vanilla)
    parsed = [(mod_id, read_raw_lines(data)) for mod_id, data in mods]
    result = merge(base, parsed, **kw)
    if result.mode == "winner":
        return result, mods[result.winner][1]
    return result, write_file([escape(line) for line in result.lines])


def describe(result):
    """Plain-text lines for a report or a test failure message."""
    out = ["%s %s%s: %d hunks, %d conflicts, %d proximity pairs" % (
        result.status, result.mode,
        "" if result.reason is None else " (%s)" % result.reason,
        len(result.hunks), result.conflicts, result.proximity_pairs)]
    for p in result.participants:
        out.append("  participant %s: d=%s deleted=%s inserted=%s%s%s" % (
            p.mod_id, p.d, p.deleted, p.inserted,
            " replacement" if p.replacement else "",
            "" if p.ok else " " + p.reason))
    if result.mode == "winner":
        out.append("  winner-takes-all: %s" % result.participants[result.winner].mod_id)
    for h in result.hunks:
        extra = ""
        if h.conflict_with:
            extra = " vs hunk %s" % ",".join(str(i) for i in h.conflict_with)
        elif h.duplicate_of is not None:
            extra = " of hunk %d" % h.duplicate_of
        elif h.proximity_with:
            extra = " near hunk %s" % ",".join(str(i) for i in h.proximity_with)
        out.append("  hunk %d %s base [%d,%d) new lines=%d %s%s" % (
            h.index, h.mod_id, h.start, h.end, len(h.lines), h.status, extra))
    return out



def result_rows(result):
    """The result as rows of `|`-separated ASCII fields, in a fixed order.

    This is the structured result the game side keeps for the report and
    dumps in a SelfTest, so the two sides are compared row for row. Numbers
    are decimal, a missing one is -1, a missing reason is `-`:

        merge|<mode>|<status>|<reason>|<winner>|<hunks>|<conflicts>|<proximity pairs>|<lines>
        part|<i>|<ok 1/0>|<reason>|<d>|<deleted>|<inserted>|<trace cells>|<replacement 1/0>
        hunk|<i>|<participant>|<start>|<end>|<new lines>|<status>|<by>
        prox|<a>|<b>

    One `part` row per participant that was diffed (a diff that is given up
    ends the loop), one `hunk` row per hunk in index order, one `prox` row per
    proximity pair in the order the pairs were found. `<lines>` counts the
    output lines before padding and hook lines. `<by>` names the hunk that
    dropped this one - the one it duplicates, or the later one that won the
    conflict - and is -1 for a kept hunk; every relation of `describe` follows
    from it and the statuses.
    """
    def num(x):
        return b"-1" if x is None else b"%d" % x

    def txt(x):
        return b"-" if x is None else x.encode("ascii")

    rows = [b"|".join([b"merge", txt(result.mode), txt(result.status),
                       txt(result.reason), num(result.winner),
                       b"%d" % len(result.hunks), b"%d" % result.conflicts,
                       b"%d" % len(result.pairs), b"%d" % len(result.lines)])]
    for i, p in enumerate(result.participants):
        rows.append(b"|".join([b"part", b"%d" % i, b"1" if p.ok else b"0",
                               txt(p.reason), num(p.d), num(p.deleted),
                               num(p.inserted), num(p.cells),
                               b"1" if p.replacement else b"0"]))
    for h in result.hunks:
        if h.kept:
            by = None
        elif h.duplicate_of is not None:
            by = h.duplicate_of
        else:
            by = h.conflict_with[-1]
        rows.append(b"|".join([b"hunk", b"%d" % h.index, b"%d" % h.participant,
                               b"%d" % h.start, b"%d" % h.end,
                               b"%d" % len(h.lines), txt(h.status), num(by)]))
    for a, b in result.pairs:
        rows.append(b"prox|%d|%d" % (a, b))
    return rows
