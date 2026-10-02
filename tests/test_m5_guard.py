"""The pre-compile guard (plan S17) run offline: the lines src/guard/resource.pas
adds to the game's resource.script, as the build renders them, in the
interpreter of tests/test_m3_pascal.py over the emulated engine of
tests/test_m5_pascal.py.

It must decide what ref/guard.py decide() decides from the same start - the
mods switched off and why, Quartermaster moved last - and do it the way run
g8 showed works: the engine's own list handed to SteamSyncWorkshopItems with
those mods off, mods.ini written back as loaded with only those changes, the
note guard.cfg as note_values() lists it, a restart; and on every start it
does not restart, the record compile.cfg of the mods this start compiles with
(the one before it kept as compile.prev.cfg).
"""
import functools
import random

import pytest

import hbuild as H
import test_m3_pascal as PAS
import test_m5_pascal as M5
from ref import boot as B
from ref import guard as G
from ref import order as O

QM, W, INI, SAVE = M5.QM, M5.W, M5.INI, M5.SAVE
QSAVE = SAVE + b"quartermaster\\"
RESOURCE = b".\\data\\scripts\\resource.script"
#: The installed resource.script as the guard reads it: by the absolute path
#: (GetApplicationFileName's folder), not through the overlay.
VANILLA_PATH = M5.APP + b"data\\scripts\\resource.script"
#: The resource.script the guard was built against (any text; its length is
#: not a multiple of 4, so the last ReadInteger is a partial one).
VANILLA = b"// vanilla resource.script\r\nvar res: boolean=SteamPrepareWorkshop(true, false);\r\n"
AGE = 1564229335                      # its FileAge: logged, never compared


@functools.lru_cache(maxsize=None)
def guard_code():
    return tuple(H.render_lines(H.load_guard(), H.guard_variables(VANILLA)))


flat, flat_keys = M5.flat, M5.flat_keys


class Engine(M5.Engine):
    """test_m5_pascal's engine (which loads and saves the flat parser files:
    guard.cfg, compile.cfg, compiled.cfg) and what only the guard asks of it:
    Steam, the engine's mod list as a parser and the sync that takes mods out
    of the running start."""

    def __init__(self, *args, **kw):
        self.steam = True
        self.synced = []
        M5.Engine.__init__(self, *args, **kw)

    def n_SteamwrapIsSteamRunning(self):
        return self.steam

    def n_ModLibraryGetParser(self, h, _whole):
        mods = M5.IniNode(self._next())
        self.nodes[mods.handle] = mods
        for d, enabled, tag in self.mods:
            e = M5.IniNode(self._next(), [(b"tag", tag), (b"dis", O.FALSE if enabled else O.TRUE),
                                          (b"dir", d), (b"tit", self.titles.get(d, b""))])
            self.nodes[e.handle] = e
            mods.children.append(e.handle)
        self.nodes[h].ini = mods.handle

    def n_SteamSyncWorkshopItems(self, h):
        rows = [dict(self.nodes[c].keys) for c in self.nodes[self.nodes[h].ini].children]
        self.synced.append([(r[b"dir"], r[b"dis"]) for r in rows])
        return 0


class Mod(object):
    def __init__(self, dir, on=True, title=b"", core=False, libs=(), glob=False, src=False,
                 hooks=(), tag=b"0"):
        self.dir, self.on, self.title, self.core = dir, on, title, core
        self.libs, self.glob, self.src, self.hooks, self.tag = list(libs), glob, src, list(hooks), tag


class Start(object):
    """One start: the mods in mods.ini order and what the save folder holds."""

    def __init__(self, mods, known=None, register7=b"", restore_file=False, age=AGE,
                 previous=None, compile_prev=None, ini=True, steam=True, game=VANILLA,
                 compiled=None):
        self.mods, self.known, self.register7 = mods, known, register7
        self.restore_file, self.age, self.previous = restore_file, age, previous
        self.compile_prev, self.ini, self.steam = compile_prev, ini, steam
        # The installed resource.script (None: not there at all).
        self.game = game
        # compiled.cfg: the dirs of the last start that booted (a list), the
        # file's bytes as they are (bytes), or no file (None).
        self.compiled = compiled


def compiled_bytes(s):
    if s.compiled is None or isinstance(s.compiled, bytes):
        return s.compiled
    return flat(G.compiled_values(s.compiled))


def files_of(s):
    files, ages = {}, {RESOURCE: s.age}
    files[RESOURCE] = b"vanilla"
    if s.game is not None:
        files[VANILLA_PATH] = s.game
    if s.ini:
        files[INI] = O.render_mods_ini([(m.dir, O.FALSE if m.on else O.TRUE) for m in s.mods])
    for m in s.mods:
        data = m.dir + b"\\data\\"
        if m.core:
            files[data + b"quartermaster\\core.aix"] = b"x"
        for n in m.libs:
            files[data + b"scripts\\lib\\" + n] = b"x"
        if m.glob:
            files[data + b"scripts\\dmscript.global"] = b"x"
        if m.src:
            files[data + b"scripts\\dmscript.source"] = b"x"
        for h in m.hooks:
            files[data + h] = b"x"
    if s.known is not None:
        files[QSAVE + b"known.cfg"] = B.render_known(s.known)
    if s.previous is not None:
        files[QSAVE + b"guard.cfg"] = flat(s.previous)
    if s.compile_prev is not None:
        files[QSAVE + b"compile.cfg"] = s.compile_prev
    if compiled_bytes(s) is not None:
        files[QSAVE + b"compiled.cfg"] = compiled_bytes(s)
    if s.restore_file:
        files[SAVE + b"mods.restore"] = b"x"
    return files, ages


def run_guard(s):
    files, ages = files_of(s)
    eng = Engine(files, ages, mods=[(m.dir, m.on, m.tag) for m in s.mods])
    eng.titles = dict((m.dir, m.title) for m in s.mods)
    eng.register7, eng.steam = s.register7, s.steam
    PAS.State(list(guard_code()), eng).run()
    return eng


def twin(s):
    gm = [G.GMod(m.dir, m.title, m.on, m.core,
                 G.global_names(m.libs, m.glob, m.src),
                 next((h for h in G.HOOK_ORDER if h in m.hooks), b""))
          for m in s.mods]
    previous = dict(s.previous) if s.previous is not None else None
    same = s.game is not None and G.game_stamp(s.game) == G.game_stamp(VANILLA)
    raw = compiled_bytes(s)
    compiled = G.compiled_dirs(flat_keys(raw)) if raw is not None else None
    plan = G.decide(gm, s.known, mp_sync=s.register7 != b"", restore_file=s.restore_file,
                    same_game=same, previous=previous, compiled=compiled)
    return gm, plan


def check(s):
    eng = run_guard(s)
    gm, plan = twin(s)
    text = b"\n".join(eng.log)
    why = plan.why if plan.action == b"none" else b"restart"
    if why == b"restart" and not s.ini:
        # No mods.ini to write back (the twin does not read the file): the
        # start goes on as it is.
        why = b"no-mods-ini"
    assert b"[qm-guard] %s mods=%d age=%d game=" % (why, len(s.mods), s.age) in text, (why, text)
    last = [l for l in eng.log if l.startswith(b"[qm-guard] %s mods=" % why)][-1]
    assert last.endswith(b" basis=" + plan.basis), (last, plan.basis)
    note = eng.written.get(QSAVE + b"guard.cfg")
    if why == b"restart":
        assert eng.restarted == ["lan", "steam", "restart"]
        assert note == flat(G.note_values(gm, plan)), (note, G.note_values(gm, plan))
        off = set(G.fold(gm[i].dir) for i, _f, _j in plan.off)
        rows = [(m.dir, O.TRUE if (not m.on or G.fold(m.dir) in off) else O.FALSE)
                for m in s.mods]
        if plan.late:
            me = G.find_self(gm)
            rows = rows[:me] + rows[me + 1:] + [rows[me]]
        assert O.parse_mods_ini(eng.written[INI])[0] == rows
        if plan.off and s.steam:
            assert eng.synced == [[(m.dir, O.TRUE if (not m.on or G.fold(m.dir) in off)
                                    else O.FALSE) for m in s.mods]]
        else:
            assert eng.synced == []
        assert b"sync=%d mods.ini=saved; restarting" % (0 if plan.off and s.steam else -1) in text
        assert QSAVE + b"compile.cfg" not in eng.written
    else:
        assert eng.restarted == [] and eng.synced == [] and INI not in eng.written
        assert note is None
        record = eng.written.get(QSAVE + b"compile.cfg")
        if why in (b"mp-sync", b"game-version"):
            assert record is None
        else:
            on = [m for m in s.mods if m.on]
            assert record == flat([kv for k, m in enumerate(on)
                                   for kv in ((b"d%d" % k, m.dir), (b"t%d" % k, m.title))]
                                  + [(b"n", b"%d" % len(on))])
            assert eng.written.get(QSAVE + b"compile.prev.cfg") == s.compile_prev
    return eng, plan


SVC = Mod(W + b"1325221799", title=b"State vs Country", libs=[b"unit.script", b"Classes.script"],
          tag=b"1325221799")
CANNONS = Mod(W + b"1450025705", title=b"Cannons Attack Automatically", libs=[b"unit.script"],
              tag=b"1450025705")
LIGHTS = Mod(W + b"855882129", title=b"MGraphics - Lights", libs=[b"miscext2.script"],
             tag=b"855882129")
PATROL = Mod(W + b"917824662", title=b"Patrol", glob=True, tag=b"917824662")
QMM = Mod(QM, title=b"Quartermaster", core=True, libs=[b"x.script"],
          hooks=[b"gui\\menu.inc\\doprogress.inc"])
LATE = Mod(W + b"2476747618", title=b"State vs Country++", hooks=[b"gui\\menu.inc\\doprogress.inc",
                                                                   b"gui\\menu.inc\\onlanevent.inc"],
           tag=b"2476747618")


def known(*mods):
    return [(m.dir, False) for m in mods]


def test_a_new_cannons_next_to_state_vs_country_is_switched_off():
    eng, plan = check(Start([SVC, QMM, CANNONS], known=known(SVC, QMM)))
    assert plan.why == b"conflict" and [i for i, _f, _j in plan.off] == [2]
    assert (b"[qm-guard] off " + CANNONS.dir + b" (lib\\unit.script, shipped by " + SVC.dir
            + b")") in eng.log


def test_quartermaster_is_moved_last_past_a_mod_that_ships_a_hook_file():
    eng, plan = check(Start([SVC, QMM, LATE], known=known(SVC, QMM, LATE)))
    assert plan.why == b"order" and plan.moved
    assert any(l.startswith(b"[qm-guard] Quartermaster moved last=1: 1 mod(s) after it ship a "
                            b"hook file, first " + LATE.dir + b" (gui\\menu.inc\\doprogress.inc)")
               for l in eng.log)


def test_both_at_once_and_a_new_mod_of_its_own_kept():
    new_ok = Mod(b"mods\\NewAlone", title=b"New alone", libs=[b"mine.script"])
    check(Start([SVC, LIGHTS, QMM, CANNONS, new_ok, LATE, PATROL],
                known=known(SVC, QMM, LIGHTS)))


@pytest.mark.parametrize("start, why", [
    (Start([SVC, QMM, CANNONS]), b"first-boot"),
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM, CANNONS)), b"clean"),
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM), register7=b"x"), b"mp-sync"),
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM), restore_file=True), b"mp-sync"),
    # Another game version: its resource.script differs by one byte, or is gone.
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM), game=VANILLA.replace(b"true", b"True")),
     b"game-version"),
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM), game=None), b"game-version"),
    # The same file written on another day (another installation): the guard works
    # there too - the case that was off on every machine but the author's.
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM), age=AGE - 3600 * 24 * 40), b"restart"),
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM), steam=False), b"restart"),
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM),
           previous=[(b"restarted", b"1"), (b"key", G.fold(CANNONS.dir) + b"|")]), b"loop"),
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM),
           previous=[(b"restarted", b"0"), (b"key", G.fold(CANNONS.dir) + b"|")]), b"restart"),
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM), ini=False), b"no-mods-ini"),
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM, CANNONS),
           compile_prev=flat([(b"n", b"1"), (b"d0", b"mods\\Before"), (b"t0", b"Before")])),
     b"clean"),
    # compiled.cfg (0.1.3): Cannons is known, but it was off in the last start
    # that booted - switched on in modman since - so it is judged...
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM, CANNONS), compiled=[SVC.dir, QM]),
     b"restart"),
    # ...and a set that booted is trusted as it is, clash or not.
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM), compiled=[SVC.dir, QM, CANNONS.dir]),
     b"clean"),
    (Start([SVC, QMM, CANNONS], compiled=[SVC.dir, QM]), b"restart"),
    # A record that is not one (no count, a count of 0): known.cfg decides.
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM, CANNONS),
           compiled=flat([(b"n", b"0"), (b"d0", SVC.dir)])), b"clean"),
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM, CANNONS), compiled=flat([(b"d0", SVC.dir)])),
     b"clean"),
    (Start([SVC, QMM, CANNONS], known=known(SVC, QMM), compiled=[SVC.dir, QM], register7=b"x"),
     b"mp-sync"),
])
def test_each_rule_decides_as_the_twin(start, why):
    eng, _plan = check(start)
    assert eng.log[-1].startswith(b"[qm-guard] " + why + b" ")


@pytest.mark.parametrize("game", [b"", b"a", b"ab", b"abc", b"abcd", b"abcde",
                                  b"line\r\nline 2\r\n", VANILLA * 40, b"text\x00after a zero",
                                  bytes(range(1, 256)) * 3])
def test_the_guard_reads_the_stamp_the_twin_computes(game):
    """Built against `game`, the guard finds the same stamp in it (the twin's
    game_stamp: bytes up to a zero byte, qhash): a start it judges, not
    game-version - whatever the file's length modulo 4."""
    code = tuple(H.render_lines(H.load_guard(), H.guard_variables(game)))
    files, ages = files_of(Start([SVC, QMM], known=known(SVC, QMM), game=game))
    eng = Engine(files, ages, mods=[(SVC.dir, True, SVC.tag), (QM, True, b"0")])
    PAS.State(list(code), eng).run()
    assert eng.log[-1] == b"[qm-guard] clean mods=2 age=%d game=%s basis=known" % (
        AGE, G.game_stamp(game))


def test_moved_follows_mods_ini_not_the_engines_list():
    """The guard moves Quartermaster's entry of mods.ini as loaded: a file that
    lists it last already keeps every entry in place (moved=0), whatever
    order the engine's list has. The twin only sees the engine's list."""
    s = Start([SVC, QMM, LATE], known=known(SVC, QMM, LATE))
    files, ages = files_of(s)
    files[INI] = O.render_mods_ini([(SVC.dir, O.FALSE), (LATE.dir, O.FALSE), (QM, O.FALSE)])
    eng = Engine(files, ages, mods=[(m.dir, m.on, m.tag) for m in s.mods])
    PAS.State(list(guard_code()), eng).run()
    note = eng.written[QSAVE + b"guard.cfg"]
    assert b"   moved = 0\r\n" in note and b"   latedir = " + LATE.dir + b"\r\n" in note
    assert O.parse_mods_ini(eng.written[INI])[0] == [(SVC.dir, O.FALSE), (LATE.dir, O.FALSE),
                                                     (QM, O.FALSE)]
    assert eng.restarted == ["lan", "steam", "restart"]


def test_a_dir_it_cannot_compare_is_never_switched_off():
    odd = Mod(b"mods\\Caf\xe9", title=b"odd", libs=[b"unit.script"])
    tilde = Mod(b"mods\\A~1", title=b"tilde", libs=[b"unit.script"])
    _eng, plan = check(Start([SVC, QMM, odd, tilde], known=known(SVC, QMM)))
    assert plan.why == b"clean"


def test_a_mod_that_is_off_and_a_copy_of_quartermaster_are_left_alone():
    off = Mod(b"mods\\Off", on=False, libs=[b"unit.script"])
    copy = Mod(b"mods\\QmCopy", core=True, libs=[b"unit.script"])
    _eng, plan = check(Start([copy, SVC, off, QMM], known=known(SVC, QMM)))
    assert plan.why == b"clean"


def test_random_starts_agree_with_the_twin():
    rng = random.Random(28092026)
    # Names whose order is the same byte by byte and folded: in which order
    # the engine's ParserGetFilesInRoot lists names that differ in case is not
    # known (the emulator sorts bytes, ref/guard.py global_names folded), and
    # the first claimed name of a mod's list is the one its note gives.
    libs = [b"unit.script", b"miscext2.script", b"Ai.script", b"classes.script"]
    hooks = list(G.HOOK_ORDER)
    for n in range(60):
        mods = []
        for k in range(rng.randint(0, 7)):
            d = (W + b"%d" % (1000 + k)) if rng.random() < 0.5 else b"mods\\M%dx" % k
            mods.append(Mod(d, on=rng.random() < 0.85, title=b"T%d" % k,
                            libs=rng.sample(libs, rng.randint(0, 2)), glob=rng.random() < 0.2,
                            src=rng.random() < 0.1,
                            hooks=rng.sample(hooks, rng.randint(0, 2)) if rng.random() < 0.3 else ()))
        mods.insert(rng.randint(0, len(mods)), Mod(QM, title=b"Quartermaster", core=True,
                                                   hooks=[hooks[2]]))
        known_mods = [m for m in mods if rng.random() < 0.5] + [mods[0]]
        # compiled.cfg: none, or the dirs of some of them (a set that booted),
        # spelled in another case now and then - the guard folds them
        compiled = None
        if rng.random() < 0.5:
            compiled = [m.dir.upper() if rng.random() < 0.2 else m.dir
                        for m in mods if rng.random() < 0.6] + [QM]
        start = Start(mods, known=known(*known_mods) if rng.random() < 0.85 else None,
                      compiled=compiled)
        _eng, plan = check(start)
        if plan.action == b"off" and rng.random() < 0.5:
            # The same start again after its restart: a loop.
            again = Start(mods, known=start.known, compiled=compiled,
                          previous=[(b"restarted", b"1"), (b"key", plan.key)])
            _eng, plan2 = check(again)
            assert plan2.why == b"loop"


# ---------------------------------------------------------- the boot's side
def run_globals(s, apply=False):
    """qmGlobals (the boot's global-script check and the reader of the
    guard's note) over the same start."""
    files, ages = files_of(s)
    eng = Engine(files, ages, mods=[(m.dir, m.on, m.tag) for m in s.mods])
    eng.titles = dict((m.dir, m.title) for m in s.mods)
    M5.load(eng, "qmGlobals")
    if apply:
        eng.set("qm_rt", runmode=b"apply")
    M5.run(eng, "qmGlobals")
    return eng


def test_the_boots_clashes_are_the_twins_pairs():
    rng = random.Random(29092026)
    libs = [b"unit.script", b"miscext2.script", b"Ai.script", b"classes.script"]
    for _ in range(30):
        mods = [Mod(b"mods\\M%dx" % k, on=rng.random() < 0.8, title=b"T%d" % k if k % 3 else b"",
                    libs=rng.sample(libs, rng.randint(0, 3)), glob=rng.random() < 0.3,
                    src=rng.random() < 0.2) for k in range(rng.randint(0, 9))]
        mods.insert(rng.randint(0, len(mods)), QMM)
        eng = run_globals(Start(mods))
        gm, _plan = twin(Start(mods))
        key = functools.partial(eng.key, b"qm_glob")
        assert key(b"n") == b"%d" % len(mods)
        for i, m in enumerate(mods):
            assert key(b"dir%d" % i) == m.dir
            # no title: the folder name, as the engine's `last` gives it
            assert key(b"tit%d" % i) == (m.title or m.dir.rsplit(b"\\", 1)[1])
            assert key(b"on%d" % i) == (b"1" if m.on and not m.core else b"0")
            names = [] if m.core else G.global_names(m.libs, m.glob, m.src)
            assert key(b"gl%d" % i) == b"|" + b"".join(n + b"|" for n in names)
        pairs = G.conflict_pairs(gm)
        assert key(b"cn") == b"%d" % len(pairs)
        assert [(int(key(b"ca%d" % k)), int(key(b"cb%d" % k)), key(b"cf%d" % k))
                for k in range(len(pairs))] == pairs
        assert b"[qm] globals mods=%d with global scripts=%d clashes=%d guard note=0 fresh=0 " \
            b"compiled=%d written" % (
                len(mods), sum(1 for m in mods if not m.core and (m.libs or m.glob or m.src)),
                len(pairs), sum(1 for m in mods if m.on)) in eng.log


def compiled_line(eng):
    return [l for l in eng.log if l.startswith(b"[qm] globals mods=")][-1].rsplit(b" ", 2)[1:]


def test_the_boot_records_the_mods_it_compiled_with():
    """compiled.cfg: every enabled mod in the engine's order, Quartermaster
    too, as ref/guard.py compiled_values lists them; written when it differs."""
    off = Mod(W + b"999", on=False, title=b"Off", libs=[b"unit.script"])
    s = Start([SVC, off, QMM, CANNONS])
    eng = run_globals(s)
    want = flat(G.compiled_values([SVC.dir, QM, CANNONS.dir]))
    assert eng.written[QSAVE + b"compiled.cfg"] == want
    assert compiled_line(eng) == [b"compiled=3", b"written"]
    # The same set again: nothing is written.
    eng = run_globals(Start([SVC, off, QMM, CANNONS], compiled=want))
    assert QSAVE + b"compiled.cfg" not in eng.written
    assert compiled_line(eng) == [b"compiled=3", b"same"]
    # Another set, or the same mods in another order: written anew.
    for other in ([SVC.dir, QM], [CANNONS.dir, SVC.dir, QM]):
        eng = run_globals(Start([SVC, off, QMM, CANNONS], compiled=other))
        assert eng.written[QSAVE + b"compiled.cfg"] == want
        assert compiled_line(eng) == [b"compiled=3", b"written"]


@pytest.mark.parametrize("why", ["apply", "register7", "restore"])
def test_no_record_from_an_apply_or_a_multiplayer_sync(why):
    s = Start([SVC, QMM, CANNONS], register7=b"x" if why == "register7" else b"",
              restore_file=(why == "restore"))
    files, ages = files_of(s)
    eng = Engine(files, ages, mods=[(m.dir, m.on, m.tag) for m in s.mods])
    eng.register7 = s.register7
    M5.load(eng, "qmGlobals")
    if why == "apply":
        eng.set("qm_rt", runmode=b"apply")
    M5.run(eng, "qmGlobals")
    assert QSAVE + b"compiled.cfg" not in eng.written
    assert compiled_line(eng) == [b"compiled=3", b"-"]


def test_the_owners_32_mods_in_modman_are_caught_at_the_next_start():
    """2026-10-02: a start with the Unofficial Patch and Quartermaster booted;
    then State vs Country and four more known mods with its libraries were
    switched on in modman. The boot's record makes the guard judge them: one
    of each script stays, the rest are switched off and the game restarts.
    Patrol stays: the one other mod with a dmscript.global, Rise of America,
    is switched off before it claims anything."""
    up = Mod(b"mods\\UnofficialPatch", title=b"Cossacks 3 Unofficial Patch")
    svcpp = Mod(W + b"2476747618", title=b"State vs Country++", libs=[b"unit.script", b"ai.script"],
                tag=b"2476747618")
    roa = Mod(W + b"1812752526", title=b"Rise of America", libs=[b"classes.script"], glob=True,
              tag=b"1812752526")
    before = [up, Mod(SVC.dir, on=False, title=SVC.title, libs=SVC.libs, tag=SVC.tag),
              Mod(svcpp.dir, on=False, title=svcpp.title, libs=svcpp.libs, tag=svcpp.tag),
              Mod(roa.dir, on=False, title=roa.title, libs=roa.libs, glob=True, tag=roa.tag),
              Mod(CANNONS.dir, on=False, title=CANNONS.title, libs=CANNONS.libs, tag=CANNONS.tag),
              Mod(PATROL.dir, on=False, title=PATROL.title, glob=True, tag=PATROL.tag), QMM]
    every = known(*before)
    record = run_globals(Start(before, known=every)).written[QSAVE + b"compiled.cfg"]
    assert G.compiled_dirs(flat_keys(record)) == [up.dir, QM]
    after = [up, SVC, svcpp, roa, CANNONS, PATROL, QMM]
    # 0.1.2 (no record): clean, and the game would stop at "Error compiling scripts".
    assert check(Start(after, known=every))[1].why == b"clean"
    eng, plan = check(Start(after, known=every, compiled=record))
    assert plan.why == b"conflict" and plan.basis == b"compiled"
    assert [(after[i].title, f) for i, f, _j in plan.off] == [
        (b"State vs Country++", b"lib\\unit.script"), (b"Rise of America", b"lib\\classes.script"),
        (b"Cannons Attack Automatically", b"lib\\unit.script")]
    assert b"[qm-guard] off " + svcpp.dir + b" (lib\\unit.script, shipped by " + SVC.dir + b")" \
        in eng.log


def test_the_boot_reads_the_guards_note_once_and_disarms_its_loop_test():
    s = Start([SVC, QMM, CANNONS], known=known(SVC, QMM))
    eng = run_guard(s)
    note = eng.written[QSAVE + b"guard.cfg"]
    # The next start: the boot finds the fresh note.
    after = Start([SVC, QMM, Mod(CANNONS.dir, on=False, title=CANNONS.title, libs=CANNONS.libs,
                                 tag=CANNONS.tag)], known=known(SVC, QMM))
    files, ages = files_of(after)
    files[QSAVE + b"guard.cfg"] = note
    eng = Engine(files, ages, mods=[(m.dir, m.on, m.tag) for m in after.mods])
    eng.titles = dict((m.dir, m.title) for m in after.mods)
    M5.load(eng, "qmGlobals")
    M5.run(eng, "qmGlobals")
    key = functools.partial(eng.key, b"qm_glob")
    assert (key(b"gdn"), key(b"gdnew")) == (b"1", b"1")
    assert (key(b"gdd0"), key(b"gdt0"), key(b"gdf0"), key(b"gdo0")) == (
        CANNONS.dir, CANNONS.title, b"lib\\unit.script", SVC.title)
    saved = eng.written[QSAVE + b"guard.cfg"]
    assert b"   restarted = 0\r\n" in saved and saved.replace(b"restarted = 0", b"restarted = 1") == note
    assert b"[qm] globals: guard note read, 1 mod(s) switched off; the guard restart booted" in eng.log
    # Shown already (qmTick set it): nothing fresh; no title: the dir stands in.
    shown = note.replace(b"   shown = 0\r\n", b"   shown = 1\r\n").replace(
        b"   tit0 = " + CANNONS.title + b"\r\n", b"   tit0 = \r\n").replace(
        b"   otit0 = " + SVC.title + b"\r\n", b"   otit0 = \r\n")
    files[QSAVE + b"guard.cfg"] = shown
    eng = Engine(files, ages, mods=[(m.dir, m.on, m.tag) for m in after.mods])
    M5.load(eng, "qmGlobals")
    M5.run(eng, "qmGlobals")
    assert eng.key(b"qm_glob", b"gdnew") == b"0"
    assert (eng.key(b"qm_glob", b"gdt0"), eng.key(b"qm_glob", b"gdo0")) == (CANNONS.dir, SVC.dir)
    # An Apply reads nothing of it.
    eng = Engine(files, ages, mods=[(m.dir, m.on, m.tag) for m in after.mods])
    M5.load(eng, "qmGlobals")
    eng.set("qm_rt", runmode=b"apply")
    M5.run(eng, "qmGlobals")
    assert eng.key(b"qm_glob", b"gdn") == b"0" and QSAVE + b"guard.cfg" not in eng.written


def test_the_boot_reports_the_guard_moving_quartermaster_last():
    eng = run_guard(Start([SVC, QMM, LATE], known=known(SVC, QMM, LATE)))
    files, ages = files_of(Start([SVC, LATE, QMM], known=known(SVC, QMM, LATE)))
    files[QSAVE + b"guard.cfg"] = eng.written[QSAVE + b"guard.cfg"]
    eng = Engine(files, ages, mods=[(SVC.dir, True, SVC.tag), (LATE.dir, True, LATE.tag),
                                    (QM, True, b"0")])
    M5.load(eng, "qmGlobals")
    M5.run(eng, "qmGlobals")
    key = functools.partial(eng.key, b"qm_glob")
    assert (key(b"gdmoved"), key(b"gdlate"), key(b"gdlatef")) == (
        b"1", LATE.dir, b"gui\\menu.inc\\doprogress.inc")
    assert (key(b"gdn"), key(b"gdnew")) == (b"0", b"0")
