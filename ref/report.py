r"""The generation report (docs/plan.md G13): the twin of src/states/qmreport.pas.

`<save>\quartermaster\report.txt` says, for every file the plan decided on,
what Quartermaster did and why: the decision, the mods that ship the file
(canonical order), the winner, the merge with its conflicts and near edits by
vanilla line number, every candidate the validator tried and whether it
compiled, and the result. Plain English, plain ASCII; the status tags are
the words OK, WARN, FAIL and FATAL, because the game's fonts have no check
mark or cross. No timestamps and no timings: the same inputs give the same
bytes (plan S12). CRLF, written by the game's raw writer.

The same lines fill the named parser qm_report for the manager window
(docs/ui.md): `lines`, `l<k>`, and per enabled mod in load order `dir<j>`,
`st<j>` (the worst tag of the files it ships; NEW for a mod the boot lists as
new whose files are all OK), `why<j>` (one short sentence on how it loads,
the Details line of the window; `mod_why`), `cn<j>` and `c<j>_<k>` (one line
per file of that mod that is not OK, at most CLASSIFICATION_LINES), and the
report grouped by mod for the window's Report view, `mlines` and `m<k>`
(`mod_lines`: per mod what it ships, where the merge touched it and how). The game saves qm_report
next to report.txt as report.cfg (the engine's own parser writes and reads it
back; state qmReportLoad), so a boot that does not generate can show it.

report.cfg is the engine parser's flat file (`report_cfg`, `read_report_cfg`;
src/lib/qmrepcfg.pas in game): `section.begin`, one `   <key> = <value>` line
per key, `section.end` and an empty line, all CRLF. That layout is the one the
game wrote in run m4a. On load the engine's parser drops the spaces a value
starts with (run m4a: exactly the 34 of 72 values that began with a space read
back different) and those it ends with (run m2a, on Code values). So every
text value is saved behind a `;` (CFG_GUARD), the first character every .inc
Code value carries through the parser with its indentation intact. The load
takes it off. The numbers `lines`, `n`, `cn<j>` and `mlines` are saved as they
are. Keys come in the order `lines`, `l<k>`, `n`, then per record `dir<j>`,
`st<j>`, `why<j>`, `cn<j>`, `c<j>_<k>`, and last `mlines`, `m<k>`.

The boot may add a block of its own (the named parser qm_boot: `n`, `l<k>`
ready-made lines, `st` their worst tag, `newn`, `new<k>` new mods' dirs). It
describes the boot's own generation: a SelfTest sandbox generation (qm_gen
`box` set) reports without it, which here is `boot=None`.

How many files changed is not in the report: a second generation from the
same inputs changes nothing, and its report must still be byte for byte the
first one's (qm_gen `changed` carries it for the boot).

The wording is final since 2026-09-30. Line by line (two
spaces indent the details):

    Quartermaster report
    generation <N>, outputs hash <hash>
    status <TAG>: <n> files in place, <n> failed, <n> removed
    and, when the boot adds a block:
    <empty>
    Boot:
      <line>
    <empty>
    Mods in load order:
      <mod>[ (Quartermaster)]                          enabled mods only
    <empty>
    Files:
    then per plan decision, in plan order:
    <empty>
    <TAG> <path>
      decision: <what the planner decided>
      mods: <mod>, ...                               every provider
      winner: <mod>                                  when one mod's copy wins
      merge: <mode>, <status>[, <reason>]: <h> changes, <c> conflicts, <p> near each other
      merge error: <text>                            instead, on a merge error
      conflict: <range> of <mod> lost to <mod>       per conflict (a dropped hunk)
      near: <range> of <mod> and <range> of <mod>    per proximity pair
      candidate <tier>: compiles | does not compile   per validation, in order
      left out: <mod>                                per loser, when the subset was written
      result: <what was written>
    and, when an earlier generation's outputs were removed:
    <empty>
    Removed from the previous generation:
      <path>: <what happened>
    and on a build bug:
    <empty>
    FATAL: <path>: ...

A mod is `<position+1>. <title> (<Workshop number or dir>)`, or
`<position+1>. <dir>` when it has no title (`_who`). ` (Quartermaster)`
marks Quartermaster's own row only when it has no title (`_row`).

A range is `vanilla lines A-B`, `vanilla line A`, `before vanilla line A` or
`after the last vanilla line`, numbered as the lines of the vanilla file.

The report by mod (qm_report `m<k>`, the window's Report view; report.txt
stays by file):

    Quartermaster report by mod
    status <TAG>: <n> files in place, <n> failed, <n> removed
    and the boot's block as above, then per enabled mod in load order:
    <empty>
    <TAG> <mod>[ (Quartermaster)]                  TAG: the worst of its files
                                                   and FAIL with a clash
      <why>                                        mod_why
      FAIL scripts\<file>: <mod> ships it too: only one copy loads, and the
        game may not start with both               per clash of the boot's
                                                   (_clash_lines)
      <TAG> <path>: <how>                          per file it ships (mod_how)
        conflict: <range>: this mod's change lost to <mod>
        conflict: <range>: this mod's change kept over <mod>
        near: <range> and <range> of <mod>          this mod's range first
    and the removed files and the FATAL line as above.
"""
from .order import ascii_lower
from .textio import escape, write_file
from .validate import FAIL, FATAL, OK, WARN

__all__ = ["CLASSIFICATION_LINES", "DECISION", "WINNER_WHY", "RESULT", "STALE", "SHORT",
           "NEW", "CFG_GUARD", "Boot", "report_lines", "report_bytes", "qm_report",
           "report_cfg", "parser_read_flat", "read_report_cfg", "worst", "rng", "Dirs", "ranked",
           "mod_why", "mod_how", "mod_lines", "mod_status", "mod_short", "SHORT_LEFT"]

#: Classification lines kept per mod for the manager window.
CLASSIFICATION_LINES = 20
NEW = b"NEW"
#: The first byte of every text value in report.cfg (see the module text).
CFG_GUARD = b";"

_RANK = {OK: 0, WARN: 1, FAIL: 2, FATAL: 3}

#: The planner's decision, by action; `winner` by its reason (ref/planner.py).
DECISION = {
    b"skip": b"one mod ships this file; the game uses that copy",
    b"merge-inc": b"merge (a script file on the merge list)",
    b"merge-data": b"merge by records (a data file with a record profile)",
    b"hook": b"Quartermaster's hook file: its hook lines are always merged in",
}
WINNER_WHY = {
    b"over-size-cap": b"the file has more lines than Quartermaster merges",
    b"never-generate": b"Quartermaster never generates this file",
    b"not-on-allow-list": b"this kind of file is not merged",
    b"record-profile-phase-b": b"data files are not merged yet",
    b"additive-global-phase-b": b"dmscript.global is not merged yet",
    b"global-script": b"a global script: only one copy loads",
    b"binary": b"a binary file",
    b"unknown-class": b"an unknown kind of file",
}

RESULT = {
    b"merged": b"the merged file was written",
    b"gaveup": b"not merged: the copies differ too much to merge; the copy of the last mod in load order was written, as the game alone would load it",
    b"mergeerr": b"the merge failed; the winner's copy was written",
    b"fallback": b"the first candidate does not compile; the next one that does was written",
    b"partial": b"the merged file does not compile; merged again without the mods whose changes "
                b"lost a conflict, and that was written",
    b"none": b"no candidate compiles; nothing was written, the game uses the winner's copy as it is",
    b"hooked": b"written with Quartermaster's hook lines",
    b"fatal": b"even vanilla with Quartermaster's hook lines does not compile; nothing was written",
    b"nohook": b"Quartermaster's own copy of its hook lines is missing; nothing was written for this file",
    b"writefail": b"the file compiles but was not written",
    b"datafail": b"the merged records failed a check; nothing was written, the game uses the winner's copy as it is",
    b"wta": b"the last generation may have kept the game from starting; nothing was merged, "
            b"the game uses the winner's copy as it is",
    b"wtahook": b"written with Quartermaster's hook lines only; nothing was merged, because "
                b"the last generation may have kept the game from starting",
}

#: Per mod, one line per file that is not OK (qm_report c<j>_<k>).
SHORT = {
    b"winner": b"winner takes all",
    b"merged": b"merged; a later mod's change replaced some of its changes",
    b"gaveup": b"not merged, the last mod's copy is used",
    b"mergeerr": b"the merge failed",
    b"fallback": b"the first candidate does not compile",
    b"partial": b"merged without the mods whose changes lost a conflict",
    b"none": b"no candidate compiles",
    b"hooked": b"merged; a later mod's change replaced some of its changes",
    b"fatal": b"vanilla with the hook lines does not compile",
    b"nohook": b"the hook lines are missing",
    b"writefail": b"not written",
    b"datafail": b"the records were not merged, the last mod's copy is used",
    b"wta": b"not merged after a suspected start-up failure",
    b"wtahook": b"not merged after a suspected start-up failure",
}

STALE = {
    b"deleted": b"deleted",
    b"overwritten": b"could not be deleted; overwritten with the %s copy",
    b"failed": b"could not be deleted or overwritten",
    b"refused": b"kept: Quartermaster may not write or delete this file",
}


class Boot(object):
    """The boot's block (qm_boot): ready-made lines, their worst tag, new dirs,
    and the clashes between enabled mods as `(dir a, dir b, file under
    scripts\\)` (qm_boot gcn, gca<k>, gcb<k>, gcf<k>; qmBoot from qm_glob)."""

    def __init__(self, lines=(), st=OK, new=(), clashes=()):
        self.lines, self.st, self.new = list(lines), st, list(new)
        self.clashes = list(clashes)


def worst(tags):
    out = OK
    for t in tags:
        if _RANK.get(t, 0) > _RANK[out]:
            out = t
    return out


def rng(start, end, first, n):
    """A hunk's vanilla range [start, end) as text."""
    if end > start + 1:
        return b"vanilla lines %d-%d" % (first + start, first + end - 1)
    if end == start + 1:
        return b"vanilla line %d" % (first + start)
    if start < n:
        return b"before vanilla line %d" % (first + start)
    return b"after the last vanilla line"


class Dirs(dict):
    """`{canonical position: dir}` with the mods' titles beside it (`titles`,
    position -> title as ModLibraryGetData gives it), which the report names
    the mods by, and their numbers (`ranks`, position -> place on the
    window's Active list) once `enabled` is given. A plain dict of dirs
    names them by dir alone and numbers every mod in it."""

    def __init__(self, dirs=(), titles=None, enabled=None):
        dict.__init__(self, dirs)
        self.titles = dict(titles or {})
        self.ranks = None if enabled is None else _ranks(enabled)


def _ranks(enabled):
    return dict((p, k + 1) for k, p in enumerate(sorted(enabled)))


def ranked(dirs, enabled):
    """`dirs` numbered by the place of each enabled mod on the window's
    Active list: the report and conflicts.txt use these numbers."""
    return Dirs(dirs, getattr(dirs, "titles", {}), enabled)


_WORKSHOP = b"..\\..\\workshop\\content\\333420\\"


def _short(d):
    """A dir as the report puts it beside a title: a Workshop item's number,
    anything else as it is."""
    if len(d) > len(_WORKSHOP) and ascii_lower(d[:len(_WORKSHOP)]) == _WORKSHOP:
        return d[len(_WORKSHOP):]
    return d


def _who(pos, dirs):
    """`<k>. <title> (<number or dir>)`, or `<k>. <dir>` for a mod without a
    title (qmReWho, src/states/qmreport.pas); `<k>` is the mod's place on the
    window's Active list (`Dirs.ranks`), and a mod not on it has no
    number. The title came in on 2026-09-30: a report that named Workshop mods
    by their folder only (`42. ..\\..\\workshop\\content\\333420\\855916926`)
    told a player nothing; until 2026-10-01 `<k>` was the place in mods.ini
    among all mods (`44. Cannons ...` beside the window's 1)."""
    ranks = getattr(dirs, "ranks", None)
    if ranks is None:
        ranks = _ranks(dirs)
    lead = b"%d. " % ranks[pos] if pos in ranks else b""
    title = getattr(dirs, "titles", {}).get(pos, b"")
    if not title:
        return lead + dirs[pos]
    return lead + title + b" (" + _short(dirs[pos]) + b")"


def _row(pos, dirs, self_pos):
    """A mod's own line in either report: `_who`, and for Quartermaster's row
    ` (Quartermaster)` when it has no title to say so (qmReport's two
    `qmReSelf` lines). With the title the mark only repeated it:
    `46. Quartermaster (mods\\QMTestQM) (Quartermaster)`, run look-wsW."""
    who = _who(pos, dirs)
    if pos == self_pos and not getattr(dirs, "titles", {}).get(pos, b""):
        who += b" (Quartermaster)"
    return who


def report_lines(g, dirs, enabled, self_pos, boot=None):
    """The report as lines (bytes, no line ends).

    g        ref.validate.Generation
    dirs     {canonical position: dir}
    enabled  canonical positions of the enabled mods
    boot     a `Boot`, or None
    """
    dirs = ranked(dirs, enabled)
    inplace = sum(1 for r in g.paths if r.written in (b"yes", b"same"))
    failed = sum(1 for r in g.paths if r.status in (FAIL, FATAL))
    removed = sum(1 for s in g.stale if s.result in (b"deleted", b"overwritten"))
    tags = [r.status for r in g.paths] + ([boot.st] if boot is not None and boot.lines else [])
    tag = FATAL if g.fatal is not None else worst(tags)
    out = [b"Quartermaster report",
           b"generation %d, outputs hash %s" % (g.gen, g.outhash),
           b"status %s: %d files in place, %d failed, %d removed" % (
               tag, inplace, failed, removed)]
    if boot is not None and boot.lines:
        out += [b"", b"Boot:"] + [b"  " + line for line in boot.lines]
    out += [b"", b"Mods in load order:"]
    for pos in sorted(enabled):
        out.append(b"  " + _row(pos, dirs, self_pos))
    out += [b"", b"Files:"]
    for r in g.paths:
        d = r.decision
        out += [b"", r.status + b" " + d.path]
        if d.action == b"winner":
            out.append(b"  decision: winner takes all: " + WINNER_WHY.get(d.reason, d.reason))
        else:
            out.append(b"  decision: " + DECISION.get(d.action, d.action))
        out.append(b"  mods: " + b", ".join(_who(p, dirs) for p in d.providers))
        win = r.winner if d.action in (b"merge-inc", b"hook") else (
            d.providers[-1] if d.action == b"winner" else None)
        if win is not None:
            out.append(b"  winner: " + _who(win, dirs))
        if r.job >= 0:
            if r.merge_err:
                out.append(b"  merge error: " + r.merge_err)
            else:
                mg = r.merge
                head = b"  merge: %s, %s" % (mg.mode.encode(), mg.status.encode())
                if mg.reason is not None:
                    head += b", " + mg.reason.encode()
                merged = mg.mode == "merged"
                out.append(head + b": %d changes, %d conflicts, %d near each other" % (
                    len(mg.hunks) if merged else 0, mg.conflicts if merged else 0,
                    len(mg.pairs) if merged else 0))
                if merged:
                    parts = r.participants
                    for h in mg.hunks:
                        if h.status == "conflict-lost":
                            by = mg.hunks[h.conflict_with[-1]]
                            out.append(b"  conflict: %s of %s lost to %s" % (
                                rng(h.start, h.end, r.first_line, r.vanilla_n),
                                _who(parts[h.participant], dirs),
                                _who(parts[by.participant], dirs)))
                    for a, b in mg.pairs:
                        ha, hb = mg.hunks[a], mg.hunks[b]
                        out.append(b"  near: %s of %s and %s of %s" % (
                            rng(ha.start, ha.end, r.first_line, r.vanilla_n),
                            _who(parts[ha.participant], dirs),
                            rng(hb.start, hb.end, r.first_line, r.vanilla_n),
                            _who(parts[hb.participant], dirs)))
        for c in r.tries:
            out.append(b"  candidate %s: %s" % (c.tier, b"compiles" if c.ok else b"does not compile"))
        if r.code == b"partial":
            for p in r.left_out:
                out.append(b"  left out: " + _who(p, dirs))
        if r.code in RESULT:
            out.append(b"  result: " + RESULT[r.code])
    if g.stale:
        out += [b"", b"Removed from the previous generation:"]
        for s in g.stale:
            text = STALE[s.result]
            if s.result == b"overwritten":
                text = text % (b"winner's" if s.source == b"winner" else b"vanilla")
            out.append(b"  " + s.path + b": " + text)
    if g.fatal is not None:
        out += [b"", b"FATAL: " + g.fatal + b": vanilla with Quartermaster's hook lines "
                b"does not compile. This is a Quartermaster bug; nothing was written."]
    return out


def report_bytes(lines):
    """report.txt as the game's raw writer writes the lines."""
    return write_file([escape(line) for line in lines])


def _files_of(g, pos):
    """The plan's files the mod at canonical position `pos` ships, in plan order."""
    return [r for r in g.paths if pos in r.decision.providers]


#: SHORT for a mod the written subset leaves out.
SHORT_LEFT = b"its changes are left out: they lost a conflict"


def mod_status(r, pos):
    """File `r`'s tag for the mod at `pos`. A mod whose own changes all went in
    lost nothing, so the file is OK for it: one the written subset keeps, and
    the winner when its own copy (with or without the hook lines) was written
    after the merge failed. Otherwise the file's own tag. Without this the
    window showed Renaissance FAIL for the file MGraphics - Main Menu lost
    (2026-09-30)."""
    if r.code == b"partial":
        return WARN if pos in r.left_out else OK
    if (r.code == b"fallback" and r.chosen is not None and pos == r.winner
            and r.chosen.tier.startswith(b"winner")):
        return OK
    return r.status


def mod_short(r, pos):
    """SHORT of file `r`, seen from the mod at `pos`."""
    if r.code == b"partial" and pos in r.left_out:
        return SHORT_LEFT
    # A hook file whose merge gave up holds the last mod's copy: nothing was
    # merged, so nothing was "replaced" (ref/validate.py _merge_status).
    if r.code == b"hooked" and r.merge is not None and r.merge.mode == "winner":
        return SHORT[b"gaveup"]
    return SHORT.get(r.code, r.code)


def mod_why(files, pos=None):
    """One short sentence on how a mod loads (qm_report why<j>), the window's
    Details line. It is about the mod's files only: the window says itself
    that a mod is new."""
    bad = [r for r in files if mod_status(r, pos) != OK]
    if not files:
        return b"loads as it is: it ships none of the files Quartermaster merges"
    if not bad:
        return b"%d files, all merged or used without problems" % len(files)
    first = bad[0]
    return b"%d of %d files need a look, first %s: %s" % (
        len(bad), len(files), first.path, mod_short(first, pos))


def mod_how(r, pos, dirs):
    """What became of file `r` for the mod at `pos`, in the report by mod."""
    d = r.decision
    if d.action == b"skip":
        return b"used as it is; no other mod ships it"
    if d.action == b"winner":
        why = WINNER_WHY.get(d.reason, d.reason)
        win = d.providers[-1]
        if win == pos:
            return b"winner takes all (" + why + b"); this mod's copy is used"
        return (b"winner takes all (" + why + b"); " + _who(win, dirs)
                + b" wins, this mod's copy is not used")
    if r.code == b"partial":
        if pos in r.left_out:
            return (b"this mod's changes are left out: some of them lost a conflict, "
                    b"and the file does not compile with the rest")
        return b"merged without " + b", ".join(_who(p, dirs) for p in r.left_out)
    if r.code == b"fallback" and r.chosen is not None:
        # The validator refused the first candidate; the one written is the
        # last one tried.
        out = b"the merged file does not compile; written instead: the " + r.chosen.tier + b" candidate"
        if r.chosen.tier.startswith(b"winner") and r.winner is not None:
            out += b" of " + _who(r.winner, dirs)
        return out
    return RESULT.get(r.code, r.code)


def _mod_merge_lines(r, pos, dirs):
    """The conflicts and near edits of merged file `r` that involve the mod at
    `pos`: the report's file lines, seen from that mod."""
    out = []
    mg = r.merge
    if r.job < 0 or r.merge_err or mg is None or mg.mode != "merged":
        return out
    parts = r.participants
    for h in mg.hunks:
        if h.status == "conflict-lost":
            by = mg.hunks[h.conflict_with[-1]]
            lost, won = parts[h.participant], parts[by.participant]
            where = rng(h.start, h.end, r.first_line, r.vanilla_n)
            if lost == pos:
                out.append(b"    conflict: " + where + b": this mod's change lost to "
                           + _who(won, dirs))
            elif won == pos:
                out.append(b"    conflict: " + where + b": this mod's change kept over "
                           + _who(lost, dirs))
    for a, b in mg.pairs:
        ha, hb = mg.hunks[a], mg.hunks[b]
        pa, pb = parts[ha.participant], parts[hb.participant]
        ra = rng(ha.start, ha.end, r.first_line, r.vanilla_n)
        rb = rng(hb.start, hb.end, r.first_line, r.vanilla_n)
        if pa == pos:
            out.append(b"    near: " + ra + b" and " + rb + b" of " + _who(pb, dirs))
        elif pb == pos:
            out.append(b"    near: " + rb + b" and " + ra + b" of " + _who(pa, dirs))
    return out


def _clash_lines(pos, dirs, boot):
    """The lines of the boot's clashes (Boot.clashes) in the block of the mod
    at `pos`, the other mod named as `_who` names it, or by its dir when it
    has no position. Until 2026-10-01 only the Boot block told of a clash,
    and both mods' own blocks read OK while the window marked them FAIL (run
    look-wsZ: Cannons Attack Automatically and State vs Country)."""
    if boot is None:
        return []
    me = ascii_lower(dirs[pos])
    out = []
    for a, b, path in boot.clashes:
        if ascii_lower(a) == me:
            other = b
        elif ascii_lower(b) == me:
            other = a
        else:
            continue
        at = next((p for p in sorted(dirs) if ascii_lower(dirs[p]) == ascii_lower(other)), None)
        out.append(b"  FAIL scripts\\" + path + b": " + (other if at is None else _who(at, dirs))
                   + b" ships it too: only one copy loads, and the game may not start with both")
    return out


#: The head of the Report view's block of pair lines (ref/conflicts.py window).
CONFLICTS_HEAD = (b"Conflicts between mods (the later mod in the load order wins; every detail "
                  b"in conflicts.txt):")


def mod_lines(g, lines, dirs, enabled, self_pos, boot=None, window=None):
    """The report grouped by mod (qm_report m<k>) of the same generation;
    `lines` is report_lines' output, whose status line it repeats. `window`
    is ref/conflicts.py window's `(pair lines, sentences)`: with a pair line,
    the block of them comes right after the status line."""
    dirs = ranked(dirs, enabled)
    out = [b"Quartermaster report by mod", lines[2]]
    if window is not None and window[0]:
        out += [b"", CONFLICTS_HEAD] + list(window[0])
    if boot is not None and boot.lines:
        out += [b"", b"Boot:"] + [b"  " + line for line in boot.lines]
    for pos in sorted(enabled):
        files = _files_of(g, pos)
        clash = _clash_lines(pos, dirs, boot)
        tag = worst([mod_status(r, pos) for r in files] + [FAIL] * bool(clash))
        out += [b"", tag + b" " + _row(pos, dirs, self_pos),
                b"  " + mod_why(files, pos)] + clash
        for r in files:
            out.append(b"  " + mod_status(r, pos) + b" " + r.path + b": " + mod_how(r, pos, dirs))
            out += _mod_merge_lines(r, pos, dirs)
    if g.stale:
        at = lines.index(b"Removed from the previous generation:")
        out += [b""] + lines[at:at + 1 + len(g.stale)]
    if g.fatal is not None:
        out += [b"", lines[-1]]
    return out


def qm_report(g, lines, dirs, enabled, self_pos, boot=None, window=None):
    """The qm_report keys (docs/ui.md), as a dict of bytes -> bytes. Until
    2026-10-01 it found `self_pos` by the ` (Quartermaster)` mark in `lines`;
    a titled row has no mark, so it is given, as qmReport has qmReSelf.
    `window` as for mod_lines; its sentences go to cpd<j>."""
    dirs = ranked(dirs, enabled)
    out = {b"lines": b"%d" % len(lines)}
    for k, line in enumerate(lines):
        out[b"l%d" % k] = line
    recs = sorted(enabled)
    new = set(ascii_lower(d) for d in (boot.new if boot is not None else ()))
    out[b"n"] = b"%d" % len(recs)
    for j, pos in enumerate(recs):
        mine = [r for r in g.paths if pos in r.decision.providers]
        out[b"dir%d" % j] = dirs[pos]
        st = worst([mod_status(r, pos) for r in mine])
        if st == OK and ascii_lower(dirs[pos]) in new:
            st = NEW
        out[b"st%d" % j] = st
        out[b"why%d" % j] = mod_why(mine, pos)
        cls = [mod_status(r, pos) + b" " + r.path + b": " + mod_short(r, pos)
               for r in mine if mod_status(r, pos) != OK][:CLASSIFICATION_LINES]
        out[b"cn%d" % j] = b"%d" % len(cls)
        for k, c in enumerate(cls):
            out[b"c%d_%d" % (j, k)] = c
        out[b"cpd%d" % j] = window[1].get(pos, b"") if window is not None else b""
    mlines = mod_lines(g, lines, dirs, enabled, self_pos, boot, window)
    out[b"mlines"] = b"%d" % len(mlines)
    for k, line in enumerate(mlines):
        out[b"m%d" % k] = line
    return out


def _cfg_keys(qmr):
    """`(key, is text)` in the order qmRepCfgSave writes and qmRepCfgLoad
    reads them; a key qm_report lacks reads '' / 0, as in game."""
    def num(key):
        v = qmr.get(key, b"")
        return int(v) if v.strip() else 0

    out = [(b"lines", False)] + [(b"l%d" % k, True) for k in range(num(b"lines"))]
    out.append((b"n", False))
    for j in range(num(b"n")):
        out += [(b"dir%d" % j, True), (b"st%d" % j, True), (b"why%d" % j, True),
                (b"cn%d" % j, False)]
        out += [(b"c%d_%d" % (j, k), True) for k in range(num(b"cn%d" % j))]
        out.append((b"cpd%d" % j, True))
    out.append((b"mlines", False))
    out += [(b"m%d" % k, True) for k in range(num(b"mlines"))]
    return out


def report_cfg(qmr):
    """report.cfg as the engine's parser saves qmRepCfgSave's scratch parser."""
    body = []
    for key, text in _cfg_keys(qmr):
        v = qmr.get(key, b"")
        body.append(b"   " + key + b" = " + (CFG_GUARD + v if text else b"%d" % int(v or 0)))
    return b"".join(line + b"\r\n" for line in [b"section.begin"] + body
                    + [b"section.end", b""])


def parser_read_flat(data):
    """What the engine's parser holds after loading a flat file: every
    `   <key> = <value>` line, the value without the spaces it starts or ends
    with."""
    out = {}
    for line in data.split(b"\r\n"):
        if line.startswith(b"   ") and b" = " in line:
            key, _eq, value = line[3:].partition(b" = ")
            out[key.lower()] = value.strip(b" ")
    return out


def read_report_cfg(data):
    """qm_report as qmRepCfgLoad fills it from report.cfg (None: no file, an
    empty qm_report). A text value without the guard (a file saved before
    the guard) is taken as it is."""
    if data is None:
        return {}
    got = parser_read_flat(data)
    out = {}
    for key, text in _cfg_keys(got):
        v = got.get(key, b"")
        if text:
            out[key] = v[1:] if v.startswith(CFG_GUARD) else v
        else:
            out[key] = b"%d" % (int(v) if v.strip() else 0)
    return out
