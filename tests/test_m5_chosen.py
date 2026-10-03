"""The set an Apply chose in the manager window, for the start-up guard
(plan S17, 0.1.3), run offline: qmOrder, qmGlobals and qmBoot as the build
emits them, in the interpreter of tests/test_m3_pascal.py over the emulated
engine of tests/test_m5_pascal.py.

An Apply's boot (qm_rt runmode = apply) records in
<save>\\quartermaster\\chosen.cfg every mod the mods.ini it applied enables,
Quartermaster too, as the rows spell the dir and in the new load order - the
keys ref/guard.py compiled_values lists for compiled.cfg. The guard trusts
that set at the next start, so a pair the player activates in the window
starts although it never started together. The next ordinary boot saves the
file back with only n = 0; an Apply or a multiplayer sync leaves it alone, as
they leave compiled.cfg alone.
"""
import random

import pytest

import test_m5_guard as MG
import test_m5_loadorder as LO
import test_m5_pascal as M5
from ref import boot as B
from ref import guard as G
from ref import order as O

QM, W, INI, SAVE = M5.QM, M5.W, M5.INI, M5.SAVE
QSAVE = SAVE + b"quartermaster\\"
CHOSEN = QSAVE + b"chosen.cfg"
SVC = W + b"1325221799"
CANNONS = W + b"1450025705"
LIGHTS = W + b"855882129"
flat, flat_keys = M5.flat, M5.flat_keys
#: chosen.cfg after the boot that followed the Apply.
CLEARED = flat([(b"n", b"0")])


def enabled_rows(ini):
    """The dirs a mods.ini enables, in its order."""
    rows, _p = O.parse_mods_ini(ini)
    return [d for d, dis in rows if dis == O.FALSE]


# ------------------------------------------------------- the Apply's record
def test_an_apply_records_the_set_it_put_into_mods_ini():
    """Cannons switched on next to State vs Country, which ships the same
    core script, and moved before it: chosen.cfg lists the enabled rows of
    the mods.ini just written, in its order, Quartermaster last."""
    mods = [(SVC, True, b"1325221799"), (LIGHTS, False, b"855882129"),
            (CANNONS, False, b"1450025705"), (QM, True, b"0")]
    flags = [(SVC, False), (LIGHTS, True), (CANNONS, False), (QM, False)]
    eng = LO.order_run(mods, flags=flags, order=[CANNONS, LIGHTS, SVC, QM])
    assert eng.key(b"qm_ini", b"action") == b"written"
    assert enabled_rows(eng.written[INI]) == [CANNONS, SVC, QM]
    assert eng.written[CHOSEN] == flat(G.compiled_values([CANNONS, SVC, QM]))
    assert G.compiled_dirs(flat_keys(eng.written[CHOSEN])) == [CANNONS, SVC, QM]
    assert b"[qm] ui apply chosen=written n=3" in eng.log


def test_the_record_follows_the_apply_over_random_sets():
    """Whatever an Apply switches and however it orders: the record is the
    enabled rows of the mods.ini it leaves, as the engine spells the dirs."""
    rng = random.Random(3102026)
    pool = [SVC, CANNONS, LIGHTS, b"mods\\UnofficialPatch", W + b"917824662", b"mods\\Mixed Case"]
    for _ in range(60):
        dirs = rng.sample(pool, rng.randint(0, len(pool)))
        mods = [(d, rng.random() < 0.5, b"0") for d in dirs]
        mods.insert(rng.randint(0, len(mods)), (QM, True, b"0"))
        flags = [(d, rng.random() < 0.5) for d, _e, _t in mods]
        order = [d for d, _e, _t in mods]
        rng.shuffle(order)
        eng = LO.order_run(mods, flags=flags, order=order if rng.random() < 0.7 else None)
        act = eng.key(b"qm_ini", b"action")
        assert act in (b"written", b"same")
        ini = eng.written.get(INI, eng.fs[INI])
        want = enabled_rows(ini)
        assert want[-1] == QM
        assert eng.written[CHOSEN] == flat(G.compiled_values(want)), (mods, flags, order)
        assert b"[qm] ui apply chosen=written n=%d" % len(want) in eng.log


def test_an_apply_that_finds_mods_ini_so_already_records_it_too():
    """mods.ini already holds the rows (changed in modman meanwhile): nothing
    to write there, but the set is still the one the player chose."""
    mods = [(SVC, True, b"1325221799"), (CANNONS, True, b"1450025705"), (QM, True, b"0")]
    eng = LO.order_run(mods, flags=[(SVC, False), (CANNONS, False), (QM, False)])
    assert eng.key(b"qm_ini", b"action") == b"same" and INI not in eng.written
    assert eng.written[CHOSEN] == flat(G.compiled_values([SVC, CANNONS, QM]))


def test_no_record_when_mods_ini_was_not_changed_to_the_set():
    """A refused mods.ini does not hold the set the player chose: the guard
    must not trust a set the next start will not load."""
    mods = [(SVC, True, b"1325221799"), (CANNONS, False, b"1450025705"), (QM, True, b"0")]
    eng = M5.order_case(mods, LO.rows_of(mods), [(CANNONS, False)], ini_data=b"garbage\r\n")
    assert eng.key(b"qm_ini", b"action") == b"refused"
    assert CHOSEN not in eng.written
    assert b"[qm] ui apply chosen=- mods.ini=refused" in eng.log
    # The same during a multiplayer sync: mods.ini is the host's then.
    eng = LO.order_run(mods, flags=[(CANNONS, False)], sync=True)
    assert eng.key(b"qm_ini", b"action") == b"skipped" and CHOSEN not in eng.written
    assert b"[qm] ui apply chosen=- mods.ini=skipped" in eng.log


def test_a_boot_records_no_choice():
    mods = [(SVC, True, b"1325221799"), (QM, True, b"0"), (CANNONS, True, b"1450025705")]
    eng = LO.order_run(mods)
    assert eng.key(b"qm_ini", b"action") == b"written"         # Quartermaster moved last
    assert CHOSEN not in eng.written
    assert not [l for l in eng.log if b"chosen" in l]


def apply_boot(mods, flags, order):
    """qmBoot as qmTick runs it for a confirmed Apply, in the process whose
    boot loaded the marker (tests/test_m5_loadorder.py has the same)."""
    eng, _rt = M5.boot_engine(B.Marker(gen=1, hash=b"1-2-3"), changed=1, mods=mods)
    eng.__class__ = LO.Engine
    eng.deleted = set()
    eng.set("qm_state", have=1, gen=1, hash=b"1-2-3", phase=b"booted", mode=b"normal", rows=0,
            rhash=b"-", rcount=0, rk=b"-", boots=1, on=0)
    rt = dict(runmode=b"apply", uiapplyn=len(flags), uiapplyorder=1, uiapplyordn=len(order),
              uiapplyseq=1)
    for j, (d, off) in enumerate(flags):
        rt["uiapplydir%d" % j] = d
        rt["uiapplydis%d" % j] = 1 if off else 0
    for k, d in enumerate(order):
        rt["uiapplyord%d" % k] = d
    eng.set("qm_rt", **rt)
    M5.run(eng, "qmBoot")
    return eng


def test_the_apply_boot_keeps_its_record_and_the_next_boot_clears_it():
    """In the Apply's boot qmGlobals runs after qmOrder and must leave the
    record as qmOrder wrote it; the boot of the start after it - the start
    the guard trusted the set for - sets n = 0."""
    mods = [(SVC, True, b"1325221799"), (CANNONS, False, b"1450025705"), (QM, True, b"0")]
    eng = apply_boot(mods, [(SVC, False), (CANNONS, False), (QM, False)], [CANNONS, SVC, QM])
    assert eng.key(b"qm_guard", b"kind") == b"apply"
    record = eng.written[CHOSEN]
    assert record == flat(G.compiled_values([CANNONS, SVC, QM]))
    assert QSAVE + b"compiled.cfg" not in eng.written
    assert not [l for l in eng.log if l.startswith(b"[qm] globals chosen=")]
    # The start after it: mods.ini as the Apply left it.
    after = [(CANNONS, True, b"1450025705"), (SVC, True, b"1325221799"), (QM, True, b"0")]
    eng, _rt = M5.boot_engine(mods=after)
    eng.fs[CHOSEN] = record
    M5.run(eng, "qmBoot")
    assert eng.written[CHOSEN] == CLEARED
    assert eng.written[QSAVE + b"compiled.cfg"] == record
    assert b"[qm] globals chosen=cleared" in eng.log


# ------------------------------------------------------ qmGlobals clears it
class SaveFails(MG.Engine):
    """The engine with chosen.cfg that cannot be saved (a read-only file)."""

    def n_ParserSaveToFileByHandle(self, h, path):
        if path == CHOSEN:
            return False
        return MG.Engine.n_ParserSaveToFileByHandle(self, h, path)


def run_globals(chosen, apply=False, register7=b"", restore_file=False, engine=MG.Engine):
    """qmGlobals over State vs Country and Quartermaster, with chosen.cfg's
    bytes (None: no file)."""
    s = MG.Start([MG.SVC, MG.QMM], register7=register7, restore_file=restore_file)
    files, ages = MG.files_of(s)
    if chosen is not None:
        files[CHOSEN] = chosen
    eng = engine(files, ages, mods=[(m.dir, m.on, m.tag) for m in s.mods])
    eng.register7 = register7
    M5.load(eng, "qmGlobals")
    if apply:
        eng.set("qm_rt", runmode=b"apply")
    M5.run(eng, "qmGlobals")
    return eng


CHOSE = flat(G.compiled_values([CANNONS, SVC, QM]))


def test_the_boot_clears_the_set_an_apply_chose():
    eng = run_globals(CHOSE)
    assert eng.written[CHOSEN] == CLEARED
    assert b"[qm] globals chosen=cleared" in eng.log
    # The boot's own line is as it was (tests/test_m5_guard.py reads it).
    assert MG.compiled_line(eng) == [b"compiled=2", b"written", b"pending=-"]


@pytest.mark.parametrize("chosen", [None, CLEARED, flat([(b"d0", QM)]), flat([(b"n", b"x")])],
                         ids=["no-file", "n=0", "no-n", "n-not-a-count"])
def test_nothing_to_clear_writes_nothing(chosen):
    eng = run_globals(chosen)
    assert CHOSEN not in eng.written
    assert not [l for l in eng.log if b"chosen" in l]


@pytest.mark.parametrize("why", ["apply", "register7", "restore"])
def test_an_apply_or_a_multiplayer_sync_leaves_it_alone(why):
    """An Apply's boot has just written it for the next start; a sync's set
    is the host's, and the player's own start comes after it."""
    eng = run_globals(CHOSE, apply=(why == "apply"), register7=b"x" if why == "register7" else b"",
                      restore_file=(why == "restore"))
    assert CHOSEN not in eng.written
    assert not [l for l in eng.log if b"chosen" in l]


def test_a_record_that_cannot_be_saved_says_so():
    eng = run_globals(CHOSE, engine=SaveFails)
    assert CHOSEN not in eng.written
    assert b"[qm] globals chosen=not-saved" in eng.log


# ------------------------------------------------- the boot's line about it
def test_the_boot_says_how_to_run_a_pair_it_switched_off():
    """The guard switched Cannons off before the compile (a clash with a mod
    it had not started with): the report's line says that activating it in
    the window is the way to run the pair anyway."""
    note = flat([(b"restarted", b"1"), (b"shown", b"0"), (b"key", b"k"), (b"n", b"1"),
                 (b"moved", b"0"), (b"why", b"conflict"), (b"dir0", CANNONS),
                 (b"tit0", b"Cannons Attack Automatically"), (b"file0", b"lib\\unit.script"),
                 (b"odir0", SVC), (b"otit0", b"State vs Country")])
    mods = [(SVC, True, b"1325221799"), (CANNONS, False, b"1450025705"), (QM, True, b"0")]
    eng, _rt = M5.boot_engine(mods=mods)
    eng.fs[QSAVE + b"guard.cfg"] = note
    M5.run(eng, "qmBoot")
    lines = [eng.key(b"qm_boot", b"l%d" % k) for k in range(int(eng.key(b"qm_boot", b"n")))]
    assert (b"WARN Switched off at the start, before the scripts compiled: the mod Cannons Attack"
            b" Automatically. It ships scripts\\lib\\unit.script, and so does State vs Country;"
            b" they had not started together, and with both the game may stop at \"Error"
            b" compiling scripts\". If they work together, activate it again in Quartermaster's"
            b" window.") in lines
    assert eng.key(b"qm_rt", b"gdshow") == b"1"


def boot_lines(note, mods):
    eng, _rt = M5.boot_engine(mods=mods)
    eng.fs[QSAVE + b"guard.cfg"] = note
    M5.run(eng, "qmBoot")
    return [eng.key(b"qm_boot", b"l%d" % k) for k in range(int(eng.key(b"qm_boot", b"n")))]


def test_the_boot_says_a_step_after_a_start_that_did_not_reach_the_menu():
    """After a start that stopped - at "Error compiling scripts", or with a
    main menu that did not compile - a step switches mods off by name
    (failed-names: the pair did not start) or without a clash (failed-revert,
    failed-vanilla); the lines say the start before did not reach the menu."""
    mods = [(SVC, True, b"1325221799"), (CANNONS, False, b"1450025705"), (QM, True, b"0")]
    names = flat([(b"restarted", b"1"), (b"shown", b"0"), (b"key", b"k"), (b"n", b"1"),
                  (b"moved", b"0"), (b"why", b"failed-names"), (b"dir0", CANNONS),
                  (b"tit0", b"Cannons Attack Automatically"), (b"file0", b"lib\\unit.script"),
                  (b"odir0", SVC), (b"otit0", b"State vs Country")])
    assert (b"WARN Switched off at the start, before the scripts compiled: the mod Cannons Attack"
            b" Automatically. It ships scripts\\lib\\unit.script, and so does State vs Country,"
            b" and the start before, with both, did not reach the main menu.") \
        in boot_lines(names, mods)
    revert = flat([(b"restarted", b"1"), (b"shown", b"0"), (b"key", b"k"), (b"n", b"1"),
                   (b"moved", b"0"), (b"why", b"failed-revert"), (b"dir0", CANNONS),
                   (b"tit0", b"Cannons Attack Automatically"), (b"file0", b"")])
    assert (b"WARN Switched off at the start, before the scripts compiled: the mod Cannons Attack"
            b" Automatically. The start before did not reach the main menu, so Quartermaster went"
            b" back towards mods that started.") in boot_lines(revert, mods)
