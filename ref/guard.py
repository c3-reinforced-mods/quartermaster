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
(docs/research/guard-probes.md verdicts 1-3). It predicts a clash by file
names for every mod that has not started with the others, and reacts to a
start that stopped all the same:

  - an ordinary start: the enabled mods of the last start that booted
    (compiled.cfg, written by the boot, qmGlobals) and those the player
    applied in Quartermaster's window since (chosen.cfg, written by that
    Apply, cleared by the next boot) are trusted; every other enabled mod
    - a new subscription, or one switched on in modman - is taken out when
    it ships a global script an enabled mod already ships. Pass 1: the
    trusted mods claim their global scripts, in load order; pass 2: each
    other mod, in load order, is switched off when one of its global
    scripts is claimed already (the first such file, in its own list order,
    names the conflict), else it claims its own. Without compiled.cfg (a
    first start of 0.1.3) known.cfg is trusted instead (ref/boot.py
    known.cfg, either flag): only new subscriptions are judged; without
    either, a first boot, nothing is judged. Names cannot tell a pair that
    runs from one that stops; the window's Apply is the way to run such a
    pair, and a start it stops is undone as below;
  - a start after one that stopped (`failed`: compile.cfg, written before
    that start compiled, is still pending - pending = 1, its boot never
    confirmed it, or no such key, a record of 0.1.2 - its mods are the ones
    enabled now, and that start's log, the second newest cos_*.log, holds a
    CompileFramework line or "Compile script error: DoCreate"). The good set is
    the enabled mods of the last start that booted (compiled.cfg, written
    by the boot, qmGlobals) - none without that record, the game alone. In
    steps, each followed by a restart:
      names   the enabled mods outside the good set are judged as pass 2
              judges a new one, against the claims of the good set's;
      revert  if none of them clashes by name, all of them go;
      vanilla if every enabled mod is in the good set - that set itself no
              longer compiles (a Workshop update) - every mod goes but
              Quartermaster: the game alone compiles.
    A start the guard restarted and that compiled logs neither mark, so the
    start after it is ordinary; when that one stops too, the next step
    follows. chosen.cfg is not trusted here, and the guard clears it;
  - an add-on and its base are not a clash (0.1.4): a mod whose about.cfg
    says `extends = <id>` and the mod that id names - its declared `id` or its
    folder (the Workshop number, the local folder name), the names
    ref/about.py `names` gives - may ship the same global script. Either way
    round (`related`): a base earlier in mods.ini than its add-on is not
    switched off for the add-on's claim. Only these two keys of about.cfg are
    read (`about_of`; the rules are ref/about.py parse: the last line of a
    key counts, an id that is not a valid id counts as none), by raw bytes as
    the manager reads the file. Which copy of the file loads is still the
    load order's business: one of the two replaces the other whole. The boot,
    the window and the Apply do not call the pair a clash either
    (`conflicts`, `conflict_pairs`; src/lib/qmglob.pas qmGlobRelated, which
    reads qm_about). A start that stops all the same is undone by the steps
    below, which judge by the same rule;
  - a dir the guard cannot compare safely (a byte outside printable ASCII,
    or `~`, which the files escape) counts as known and as good: the guard
    never switches off what it cannot identify;
  - Quartermaster itself and any other copy of it (a mod with
    data\quartermaster\core.aix) are neither judged nor claim anything.

Until 0.1.2 only new subscriptions were caught: on 2026-10-02 the owner
switched 32 known Workshop mods on in modman at once (State vs Country, its
++, Rise of America and its +, 19th Century and more, all with the same
libraries), the guard logged `clean`, and two starts in a row stopped at
"Error compiling scripts". A first 0.1.3 judged every mod switched on since
the last start that booted, in advance - which also blocked pairs that share
a file and run together, with no way out but switching Quartermaster off; the
owner chose to react instead (2026-10-03). That left the engine's dialog
("Warning. Error compiling scripts. Try to disable some mods via Mod
Manager...", a string constant in cossacks.exe that no mod can change) on
the screen before every repair: the owner switched mods on in modman with
Quartermaster in the middle of mods.ini and met it twice (2026-10-03 08:45,
08:46). So 0.1.3 judges in advance again, with the window's Apply as the
way to run a pair names would refuse (chosen.cfg), and keeps the steps for
what names cannot see.

It does nothing in the multiplayer sync (StringRegister7 set, or
<save>\mods.restore present: plan S8), on a game whose resource.script is
not the one it was built from (the guard carries a copy of that file), or
when the previous start was a guard restart for the same mods (a loop: the
note says so and the key matches). Which resource.script the game has is
told by its content (`game_stamp`). Until 0.1.2 it was its FileAge, the day
Steam wrote the file on that machine: every installation has its own, and
the guard was off on all but the author's (first start on a second
computer, 2026-10-02).

Every start that reads the mod list (all but the multiplayer sync and a
changed game) it also records the mods that start compiles with, in load
order - `<save>\quartermaster\compile.cfg`, keys n, d<k> (dir), t<k>
(title) and pending = 1, the record before moved to compile.prev.cfg first
(`record_values`) - for ref/laststart.py, which names the library of a
start that stopped at "Error compiling scripts", and for its own `failed`
test: the boot sets pending = 0. A start it restarts is recorded too: that
life still compiles the libraries before the engine restarts. Until
2026-10-03 it was not; with Quartermaster put in the middle of mods.ini, the
guard restarted to move it last, that life stopped at the error, and the next
start - its record not pending - ran the same set into the error again (the
owner's starts of 2026-10-03 08:45 and 08:46).

What it does is verified in run g8: hand SteamSyncWorkshopItems the engine's
own mod list with those mods off (it takes them out of this start - and
switches every local mod off and moves the enabled Workshop items first,
verdict 6), write mods.ini back as it was loaded with only those mods off,
write the note <save>\quartermaster\guard.cfg, and restart.

The record of the last start that booted (compiled.cfg) is a flat file as
well: d<k> the dir of each enabled mod in the engine's order (Quartermaster
too), n how many. The boot writes it when it differs, never on an Apply (that
set has not compiled yet) or in a multiplayer sync (that set is the host's).

The note (guard.cfg) is the engine parser's flat file, keys:
  restarted  1; the boot sets 0 once the restarted start booted (the loop
             test is disarmed then)
  shown      0; 1 once the manager showed the notice (qmTick) - a first
             generation's own restart may come before the main menu
  key        the folded dirs switched off, in load order, each followed by
             `|` (the loop test)
  n          how many
  moved      1 when Quartermaster's entry moved last
  why        the rule: conflict (judged by names), failed-names,
             failed-revert, failed-vanilla, order
  dir<k>, tit<k>, file<k>, odir<k>, otit<k>
             the mod switched off, its title, the global script and the mod
             that ships it already (dir and title); file and the other mod
             are empty when a step switched it off without a clash (revert,
             vanilla)
"""

__all__ = ["LIB", "GLOBAL", "SOURCE", "COMPILED_REL", "fold", "comparable", "global_names",
           "ABOUT_INTS", "about_of", "mod_names", "related",
           "GMod", "known_set", "is_known", "quarantine", "conflicts", "COMPILE_ERROR",
           "LOG_INTS", "log_failed", "failed", "fallback",
           "first_shared", "conflict_pairs", "Plan", "decide",
           "note_values", "note_key", "game_stamp", "compiled_values", "compiled_dirs"]

LIB = b"lib\\"
GLOBAL = b"dmscript.global"
SOURCE = b"dmscript.source"
COMPILED_REL = b"quartermaster\\compiled.cfg"


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


#: The guard reads at most this many Integers (4 bytes each) of an about.cfg,
#: as the manager does (src/states/qmabout.pas).
ABOUT_INTS = 262144


def about_of(data):
    """`(id, extends)` of a mod's about.cfg as the guard reads it: `data` the
    file's bytes (None: the mod ships none), cut at the first zero byte or
    ABOUT_INTS Integers like the game's reader, and read by ref/about.py
    parse - the last line of a key counts, an id or extends that is not a
    valid id is empty. Both lower case."""
    if data is None:
        return b"", b""
    from ref import about as A
    a = A.parse(data[:ABOUT_INTS * 4].split(b"\x00", 1)[0])
    return a.id, a.extends


def mod_names(d, declared):
    """Every name a mod answers to as an `extends` target: its declared id
    (`declared`, may be empty) and its folder identity - the Workshop number
    or the local folder name, ASCII lower case (ref/about.py names)."""
    from ref import order as O
    out = [declared] if declared else []
    origin, ident = O.identity(d)
    if origin in (O.WORKSHOP, O.LOCAL):
        low = O.ascii_lower(ident)
        if low not in out:
            out.append(low)
    return out


class GMod(object):
    """One registered mod as the guard sees it, in load order. `about` is the
    bytes the guard reads for it: its about.cfg, or for a Workshop mod without
    one Quartermaster's known\\<number>.cfg, as the manager does
    (src/states/qmabout.pas); None: neither. It is read only for a mod that
    ships a global script, the only kind that can claim or be judged. `ext` is
    the id its `extends` names (empty: none) and `ids` the names it answers
    to."""

    __slots__ = ("dir", "title", "on", "is_self", "files", "hooks", "ids", "ext")

    def __init__(self, dir, title=b"", on=True, is_self=False, files=(), hooks=b"", about=None):
        self.dir = dir
        self.title = title
        self.on = on
        self.is_self = is_self
        self.files = list(files)
        # The first of Quartermaster's hook files (plan S5) the mod ships, in
        # the guard's order (HOOK_ORDER), or b"".
        self.hooks = hooks
        declared, self.ext = about_of(about)
        self.ids = mod_names(dir, declared)

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


def related(a, b):
    """An add-on and its base (ref/about.py `_related`): `a` extends `b` or `b`
    extends `a`, by the names each answers to."""
    return (a.ext != b"" and a.ext in b.ids) or (b.ext != b"" and b.ext in a.ids)


def quarantine(mods, trusted):
    """`[(i, file, j)]`: mod i is switched off, because mod j claims `file`.
    `trusted`: the folded dirs that claim first (pass 1); every other enabled
    mod is judged in load order (pass 2). A claim by the mod's base, or by an
    add-on of it, is no clash (`related`); j is the first claimant that is
    not one."""
    claimed = {}
    for i, m in enumerate(mods):
        if m.on and not m.is_self and is_known(m.dir, trusted):
            for f in m.files:
                claimed.setdefault(f, []).append(i)
    off = []
    for i, m in enumerate(mods):
        if not m.on or m.is_self or is_known(m.dir, trusted):
            continue
        hit = None
        for f in m.files:
            by = next((j for j in claimed.get(f, ()) if not related(m, mods[j])), None)
            if by is not None:
                hit = (f, by)
                break
        if hit is not None:
            off.append((i, hit[0], hit[1]))
        else:
            for f in m.files:
                claimed.setdefault(f, []).append(i)
    return off


#: What marks a start that stopped at "Error compiling scripts" in its log:
#: "CompileFramework() - compile global script error: ..." (the owner's starts
#: of 2026-10-02 23:42 and 23:43; docs/research/context-2026-09-27.md).
COMPILE_ERROR = b"CompileFramework"
#: What marks a start whose main menu did not compile: nothing runs after it.
#: Of the 1268 logs on the author's machine (2026-10-03) 19 hold this line,
#: none of them reached the main menu (no "...DoCreate started..." line), 8
#: with a CompileFramework line too. "Parser load error" is no such mark: 18
#: logs that reached the menu have one.
MENU_ERROR = b"Compile script error: DoCreate"
#: The guard reads at most this many Integers (4 bytes each) of that log.
LOG_INTS = 262144


def log_failed(data):
    """True when a log's bytes, as the guard reads them - up to the first zero
    byte, at most LOG_INTS Integers - hold COMPILE_ERROR or MENU_ERROR."""
    text = data[:LOG_INTS * 4].split(b"\x00", 1)[0]
    return COMPILE_ERROR in text or MENU_ERROR in text


def same_set(dirs, mods):
    """Whether `dirs` (a record's, or None) are the mods enabled now, as a set:
    as many, and every enabled mod the guard can compare is among them. The
    order does not count (Quartermaster's own move last is no change)."""
    if dirs is None:
        return False
    on = [m for m in mods if m.on]
    have = set(fold(d) for d in dirs)
    return len(dirs) == len(on) and all(fold(m.dir) in have for m in on if comparable(m.dir))


def failed(compile_keys, previous_log, mods):
    """The `failed` test: compile.cfg (`{key: value}` or None) is still
    pending - pending = 1, or no pending key at all, a record of 0.1.2, whose
    boot never cleared one - its mods are the ones enabled now (`same_set`),
    and the previous start's log (bytes or None) has a mark of a start that
    stopped (`log_failed`). With other mods enabled than the start that
    stopped had, the player (or a guard restart Steam did not carry out) has
    changed the set since: the start is an ordinary one, so the steps never
    switch off what the player has put right in modman already - the engine's
    dialog itself says "Try to disable some mods via Mod Manager"."""
    return (compile_keys is not None and compile_keys.get(b"pending", b"") in (b"1", b"")
            and previous_log is not None and log_failed(previous_log)
            and same_set(compiled_dirs(compile_keys), mods))


def fallback(mods, good):
    """`(why, off)` for a start after one that stopped (see the module doc):
    `good` the folded dirs of the last start that booted (empty: none)."""
    outside = [i for i, m in enumerate(mods)
               if m.on and not m.is_self and not is_known(m.dir, good)]
    if outside:
        off = quarantine(mods, good)
        if off:
            return b"failed-names", off
        return b"failed-revert", [(i, b"", -1) for i in outside]
    rest = [i for i, m in enumerate(mods) if m.on and not m.is_self and comparable(m.dir)]
    if rest:
        return b"failed-vanilla", [(i, b"", -1) for i in rest]
    return b"failed-alone", []


def conflicts(mods):
    """`{i: [(file, j)]}` over the enabled mods (known or not): for every
    global script two of them ship, each gets the other one. The window and
    the report warn of these, and the Apply asks before it writes a set that
    has any. An add-on and the mod it extends are no clash (`related`, 0.1.4):
    neither gets the other for a file they share."""
    seen = {}
    out = {}
    for i, m in enumerate(mods):
        if not m.on or m.is_self:
            continue
        for f in m.files:
            # Every earlier mod that ships it, as the window pairs them
            # (src/states/qmuimodel.pas); until 0.1.4 only the first one.
            for j in seen.get(f, ()):
                if not related(m, mods[j]):
                    out.setdefault(i, []).append((f, j))
                    out.setdefault(j, []).append((f, i))
            seen.setdefault(f, []).append(i)
    return out


def first_shared(a, b):
    """The first name of list `a`, in its order, that list `b` holds too, or None."""
    return next((f for f in a if f in b), None)


def conflict_pairs(mods):
    """`[(a, b, file)]`, a < b both enabled, `file` the first global script of
    a's list that b ships too: the boot's clash lines and the Apply's refusal
    (src/states/qmglobals.pas, qmuiact.pas), at most 64. An add-on and the mod
    it extends are no pair (`related`; qmGlobRelated, 0.1.4)."""
    out = []
    on = [i for i, m in enumerate(mods) if m.on and not m.is_self and m.files]
    for x, a in enumerate(on):
        for b in on[x + 1:]:
            f = first_shared(mods[a].files, mods[b].files)
            if f is not None and not related(mods[a], mods[b]) and len(out) < 64:
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
    rule decided; `moved` whether Quartermaster's entry moves; `basis` what
    the decision stood on: b"compiled", b"known" or b"none" (compiled.cfg
    with chosen.cfg, else known.cfg, else none) on an ordinary start,
    b"compiled" or b"none" (compiled.cfg, or none) after a failed one, b"-"
    when the guard read no record (a multiplayer sync, another game
    version)."""

    __slots__ = ("action", "why", "off", "key", "late", "moved", "basis")

    def __init__(self, action, why, off=(), key=b"", late=(), moved=False, basis=b"-"):
        self.action, self.why, self.off, self.key = action, why, list(off), key
        self.late, self.moved, self.basis = list(late), moved, basis

    def __repr__(self):
        return "Plan(%s, %s, %r, late=%r, basis=%s)" % (self.action, self.why, self.off,
                                                        self.late, self.basis)


def decide(mods, known_entries, mp_sync=False, restore_file=False, same_game=True,
           previous=None, compiled=None, failed=False, chosen=None):
    """The guard's decision for one start. `previous` is the note of the
    previous start (`{key: value}`) or None; `compiled` the dirs of
    compiled.cfg (`compiled_dirs`) or None; `failed` the `failed` test;
    `chosen` the dirs of chosen.cfg (`compiled_dirs` of it) or None."""
    if mp_sync or restore_file:
        return Plan(b"none", b"mp-sync")
    if not same_game:
        return Plan(b"none", b"game-version")
    if failed:
        basis = b"compiled" if compiled is not None else b"none"
        why, off = fallback(mods, set(fold(d) for d in compiled or []))
    elif compiled is not None:
        # The mods of the last start that booted, and those the player applied
        # in the window since, claim first; every other enabled mod - new, or
        # switched on in modman - is judged like a new subscription.
        basis = b"compiled"
        off = quarantine(mods, set(fold(d) for d in list(compiled) + list(chosen or [])))
        why = b"conflict"
    else:
        known = known_set(known_entries)
        basis = b"known" if known is not None else b"none"
        # Without known.cfg nothing is new, so nothing is switched off; the
        # load order is still put right.
        off = quarantine(mods, known) if known is not None else []
        why = b"conflict"
    late = late_hooks(mods, off)
    if not off and not late:
        if failed:
            return Plan(b"none", why, basis=basis)
        return Plan(b"none", b"first-boot" if basis == b"none" else b"clean", basis=basis)
    if not off:
        why = b"order"
    key = note_key(mods, off)
    me = find_self(mods)
    if late:
        key += b"order:" + fold(mods[me].dir) + b"|"
    moved = bool(late) and me != len(mods) - 1
    if previous is not None and previous.get(b"restarted") == b"1" and previous.get(b"key") == key:
        return Plan(b"none", b"loop", off, key, late, moved, basis)
    return Plan(b"off", why, off, key, late, moved, basis)


def record_values(mods, plan, took):
    """compile.cfg's keys for the mods this start compiles with: the enabled
    ones in load order, then n and pending = 1. `took`: SteamSyncWorkshopItems
    took the mods `plan` switches off out of this start (Steam running and
    something to switch off), so they are not compiled; otherwise they are."""
    off = set(i for i, _f, _j in plan.off) if took else set()
    on = [m for i, m in enumerate(mods) if m.on and i not in off]
    out = []
    for k, m in enumerate(on):
        out += [(b"d%d" % k, m.dir), (b"t%d" % k, m.title)]
    return out + [(b"n", b"%d" % len(on)), (b"pending", b"1")]


def compiled_values(dirs):
    """compiled.cfg's keys for the enabled mods of a start that booted, in
    the engine's order (qmGlobals writes them in this order)."""
    return [(b"d%d" % k, d) for k, d in enumerate(dirs)] + [(b"n", b"%d" % len(dirs))]


def compiled_dirs(keys):
    """The dirs of compiled.cfg's keys (`{key: value}`, keys lower case as the
    engine's parser folds them), or None when `n` is missing or not a count
    of at least 1: a boot always has Quartermaster enabled, so such a file
    is not a record of one - after a failed start the good set is then the
    game alone. It reads at most 512 dirs."""
    try:
        n = int(keys.get(b"n", b""))
    except ValueError:
        return None
    if n < 1:
        return None
    return [keys.get(b"d%d" % k, b"") for k in range(min(n, 512))]


def note_values(mods, plan):
    """guard.cfg's keys for an `off` plan, in the order the guard writes them."""
    out = [(b"restarted", b"1"), (b"shown", b"0"), (b"key", plan.key),
           (b"n", b"%d" % len(plan.off)), (b"moved", b"1" if plan.moved else b"0"),
           (b"why", plan.why)]
    if plan.late:
        i, f = plan.late[0]
        out += [(b"latedir", mods[i].dir), (b"latefile", f)]
    for k, (i, f, j) in enumerate(plan.off):
        out += [(b"dir%d" % k, mods[i].dir), (b"tit%d" % k, mods[i].title), (b"file%d" % k, f)]
        if j >= 0:
            out += [(b"odir%d" % k, mods[j].dir), (b"otit%d" % k, mods[j].title)]
    return out
