r"""The pre-compile guard and the global-script check (docs/plan.md S17): the
twin of the guard code in src/guard/resource.pas and of the boot's check
(src/states/qmglobals.pas).

Global scripts
--------------
A mod's *global scripts* are the files the game compiles as one framework
before any state runs: every `data\scripts\lib\*.script` it ships, and
`data\scripts\dmscript.global` / `dmscript.source` (the vanilla check of
init.script:176-185 looks at the same folder). Two enabled mods that ship
the same one cannot both be loaded: the later one's copy replaces the whole
file (the overlay, docs/research/context-2026-09-27.md section 3), and the
libraries of the other mod then usually miss names they need - "Error
compiling scripts" before Quartermaster or anything else runs (a test
start of 2026-09-28, run g2a in docs/research/guard-probes.md). That the
game would *not* compile cannot be known from names; that one of the two
mods loses its whole copy can.

Names are compared folded: the file name in lower case, `lib\` in front of
a library (`lib\unit.script`), `dmscript.global`, `dmscript.source`.

The guard
---------
Quartermaster's `data\scripts\resource.script` is the vanilla file with the
guard after it, so it runs before the libraries compile, after
SteamPrepareWorkshop has registered and switched on every new subscription
(docs/research/guard-probes.md verdicts 1-3). It takes *new* mods out of the
start when they ship a global script that an enabled mod already ships:

  - known mods are the dirs of <save>\quartermaster\known.cfg (ref/boot.py
    known.cfg, either flag); no file: a first boot, nothing is new. A dir
    the guard cannot compare safely (a byte outside printable ASCII, or `~`,
    which known.cfg escapes) counts as known: the guard never switches off
    what it cannot identify;
  - pass 1: every enabled known mod claims its global scripts, in load
    order; pass 2: each enabled new mod, in load order, is switched off when
    one of its global scripts is claimed already (the first such file, in
    its own list order, names the conflict), else it claims its own;
  - Quartermaster itself and any other copy of it (a mod with
    data\quartermaster\core.aix) are neither judged nor claim anything.

It does nothing in the multiplayer sync (StringRegister7 set, or
<save>\mods.restore present: plan S8), on a game whose resource.script is
not the one it was built from (the guard carries a copy of that file), or
when the previous start was a guard restart for the same mods (a loop: the
note says so and the key matches). Which resource.script the game has is
told by its content (`game_stamp`). Until 0.1.2 it was its FileAge, the day
Steam wrote the file on that machine: every installation has its own, and
the guard was off on all but the author's (first start on a second
computer, 2026-10-02).

Every start it does not restart (clean, first boot, loop, no mods.ini) it
also records the enabled mods in load order - `<save>\quartermaster\
compile.cfg`, keys n, d<k> (dir), t<k> (title), the record before moved to
compile.prev.cfg first - for ref/laststart.py, which names the library of a
start that stopped at "Error compiling scripts".

What it does is verified in run g8: hand SteamSyncWorkshopItems the engine's
own mod list with those mods off (it takes them out of this start - and
switches every local mod off and moves the enabled Workshop items first,
verdict 6), write mods.ini back as it was loaded with only those mods off,
write the note <save>\quartermaster\guard.cfg, and restart.

The note (guard.cfg) is the engine parser's flat file, keys:
  restarted  1; the boot sets 0 once the restarted start booted (the loop
             test is disarmed then)
  shown      0; 1 once the manager showed the notice (qmTick) - a first
             generation's own restart may come before the main menu
  key        the folded dirs switched off, in load order, each followed by
             `|` (the loop test)
  n          how many
  dir<k>, tit<k>, file<k>, odir<k>, otit<k>
             the mod switched off, its title, the global script and the mod
             that ships it already (dir and title)
"""

__all__ = ["LIB", "GLOBAL", "SOURCE", "fold", "comparable", "global_names", "GMod",
           "known_set", "is_known", "quarantine", "conflicts", "first_shared",
           "conflict_pairs", "Plan", "decide",
           "note_values", "note_key", "game_stamp"]

LIB = b"lib\\"
GLOBAL = b"dmscript.global"
SOURCE = b"dmscript.source"


def game_stamp(data):
    """The stamp of a resource.script as the guard reads the installed one:
    its bytes up to the first zero byte (a text file has none - the guard
    reads it as qmRawRead reads text), hashed as ref/fingerprint.py qhash."""
    from ref.fingerprint import qhash
    return qhash(data.split(b"\x00", 1)[0])


def fold(d):
    """A dir or file name as the guard compares it: ASCII lower case, `/` as `\\`."""
    return bytes(c + 32 if 65 <= c <= 90 else c for c in d).replace(b"/", b"\\")


def comparable(d):
    """Only printable ASCII without `~` is compared (see the module doc)."""
    return all(32 <= c <= 126 for c in d) and b"~" not in d


def global_names(lib_files, has_global, has_source):
    """The folded global scripts of one mod, in the guard's list order: the
    `scripts\\lib\\*.script` names as ParserGetFilesInRoot lists them (sorted
    here), then dmscript.global, then dmscript.source."""
    out = [LIB + fold(n) for n in sorted(lib_files, key=fold)]
    if has_global:
        out.append(GLOBAL)
    if has_source:
        out.append(SOURCE)
    return out


class GMod(object):
    """One registered mod as the guard sees it, in load order."""

    __slots__ = ("dir", "title", "on", "is_self", "files", "hooks")

    def __init__(self, dir, title=b"", on=True, is_self=False, files=(), hooks=b""):
        self.dir = dir
        self.title = title
        self.on = on
        self.is_self = is_self
        self.files = list(files)
        # The first of Quartermaster's hook files (plan S5) the mod ships, in
        # the guard's order (HOOK_ORDER), or b"".
        self.hooks = hooks

    def __repr__(self):
        return "GMod(%r, %s%s, %r)" % (self.dir, "on" if self.on else "off",
                                        ", self" if self.is_self else "", self.files)


def known_set(entries):
    """The folded dirs of known.cfg (ref/boot.py parse_known), or None."""
    if entries is None:
        return None
    return set(fold(d) for d, _new in entries)


def is_known(d, known):
    return not comparable(d) or fold(d) in known


def quarantine(mods, known):
    """`[(i, file, j)]`: mod i is switched off, because mod j claims `file`."""
    claimed = {}
    for i, m in enumerate(mods):
        if m.on and not m.is_self and is_known(m.dir, known):
            for f in m.files:
                claimed.setdefault(f, i)
    off = []
    for i, m in enumerate(mods):
        if not m.on or m.is_self or is_known(m.dir, known):
            continue
        hit = next(((f, claimed[f]) for f in m.files if f in claimed), None)
        if hit is not None:
            off.append((i, hit[0], hit[1]))
        else:
            for f in m.files:
                claimed.setdefault(f, i)
    return off


def conflicts(mods):
    """`{i: [(file, j)]}` over the enabled mods (known or not): for every
    global script two of them ship, each gets the other one. The window and
    the report show these; the Apply refuses a set that has any."""
    first = {}
    out = {}
    for i, m in enumerate(mods):
        if not m.on or m.is_self:
            continue
        for f in m.files:
            if f in first:
                j = first[f]
                out.setdefault(i, []).append((f, j))
                out.setdefault(j, []).append((f, i))
            else:
                first[f] = i
    return out


def first_shared(a, b):
    """The first name of list `a`, in its order, that list `b` holds too, or None."""
    return next((f for f in a if f in b), None)


def conflict_pairs(mods):
    """`[(a, b, file)]`, a < b both enabled, `file` the first global script of
    a's list that b ships too: the boot's clash lines and the Apply's refusal
    (src/states/qmglobals.pas, qmuiact.pas), at most 64."""
    out = []
    on = [i for i, m in enumerate(mods) if m.on and not m.is_self and m.files]
    for x, a in enumerate(on):
        for b in on[x + 1:]:
            f = first_shared(mods[a].files, mods[b].files)
            if f is not None and len(out) < 64:
                out.append((a, b, f))
    return out


def note_key(mods, off):
    """The folded dirs switched off, in load order, each followed by `|`."""
    return b"".join(fold(mods[i].dir) + b"|" for i, _f, _j in sorted(off))


#: The guard asks for Quartermaster's hook files in this order.
HOOK_ORDER = (b"gui\\menu.inc\\cameracontrol.inc", b"gui\\menu.inc\\initminimap.inc",
              b"gui\\menu.inc\\doprogress.inc", b"gui\\menu.inc\\eventmainmenu.inc",
              b"gui\\menu.inc\\onlanevent.inc")


def find_self(mods):
    """Quartermaster: the last enabled mod with core.aix (ref/index.py find_self)."""
    found = -1
    for i, m in enumerate(mods):
        if m.on and m.is_self:
            found = i
    return found


def late_hooks(mods, off):
    """`[(i, hook file)]`: enabled mods after Quartermaster, not switched off,
    that ship one of its hook files - with them it would not load last, so
    its hooks lose (proof run p4 of 2026-09-28). The guard moves it last."""
    me = find_self(mods)
    if me < 0:
        return []
    gone = set(i for i, _f, _j in off)
    return [(i, m.hooks) for i, m in enumerate(mods)
            if i > me and m.on and i not in gone and m.hooks]


class Plan(object):
    """`action` b"off" (switch `off` off and/or move Quartermaster last -
    `late` non-empty - write the note, restart) or b"none"; `why` says which
    rule decided; `moved` whether Quartermaster's entry moves."""

    __slots__ = ("action", "why", "off", "key", "late", "moved")

    def __init__(self, action, why, off=(), key=b"", late=(), moved=False):
        self.action, self.why, self.off, self.key = action, why, list(off), key
        self.late, self.moved = list(late), moved

    def __repr__(self):
        return "Plan(%s, %s, %r, late=%r)" % (self.action, self.why, self.off, self.late)


def decide(mods, known_entries, mp_sync=False, restore_file=False, same_game=True,
           previous=None):
    """The guard's decision for one start. `previous` is the note of the
    previous start (`{key: value}`) or None."""
    known = known_set(known_entries)
    if mp_sync or restore_file:
        return Plan(b"none", b"mp-sync")
    if not same_game:
        return Plan(b"none", b"game-version")
    # Without known.cfg nothing is new, so nothing is switched off; the load
    # order is still put right.
    off = quarantine(mods, known) if known is not None else []
    late = late_hooks(mods, off)
    if not off and not late:
        return Plan(b"none", b"first-boot" if known is None else b"clean")
    key = note_key(mods, off)
    me = find_self(mods)
    if late:
        key += b"order:" + fold(mods[me].dir) + b"|"
    moved = bool(late) and me != len(mods) - 1
    if previous is not None and previous.get(b"restarted") == b"1" and previous.get(b"key") == key:
        return Plan(b"none", b"loop", off, key, late, moved)
    return Plan(b"off", b"conflict" if off else b"order", off, key, late, moved)


def note_values(mods, plan):
    """guard.cfg's keys for an `off` plan, in the order the guard writes them."""
    out = [(b"restarted", b"1"), (b"shown", b"0"), (b"key", plan.key),
           (b"n", b"%d" % len(plan.off)), (b"moved", b"1" if plan.moved else b"0")]
    if plan.late:
        i, f = plan.late[0]
        out += [(b"latedir", mods[i].dir), (b"latefile", f)]
    for k, (i, f, j) in enumerate(plan.off):
        out += [(b"dir%d" % k, mods[i].dir), (b"tit%d" % k, mods[i].title),
                (b"file%d" % k, f), (b"odir%d" % k, mods[j].dir),
                (b"otit%d" % k, mods[j].title)]
    return out
