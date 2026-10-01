"""The activation check in the manager window (qmUiAct with qmTick's answer,
docs/ui.md "Activation check"): a mod the check refuses goes back, one it
passes stays, Apply of new mods waits for their check and lists what it
refused, and nothing changes the pending set while a check is asked."""
import pytest

import test_m5_pascal as PAS5
import test_m6_window as W

QM, WASD, BROKEN = W.QM, W.WASD, W.BROKEN
MODS = [(WASD, True, b""), (BROKEN, False, b""), (QM, True, b"")]
REPORT = W.report((WASD, b"OK", b""), (BROKEN, b"OK", b""), (QM, b"OK", b""))


def opened(trial=(b"OK", [])):
    eng, _lo = W.window_ordered(MODS, rep=REPORT)
    eng.trial = trial
    W.cmd(eng, "open")
    return eng


def test_a_mod_the_check_refuses_goes_back_with_the_reason():
    eng = opened((b"FAIL", [(b"FAIL", b"gui\\menu.inc\\registershortcuts.inc: the merged "
                                       b"file does not compile")]))
    broken = W.row_of(eng, BROKEN)
    W.cmd(eng, "select", arg=broken)
    W.cmd(eng, "activate")
    assert W.ui(eng, "pe%d" % broken) == b"0" and W.ui(eng, "trpend") == b"0"
    assert W.ui(eng, "msg") == (b"Not activated: gui\\menu.inc\\registershortcuts.inc: the "
                                b"merged file does not compile.")
    assert eng.key(b"qm_rt", b"trrow") == b"%d" % broken


def test_a_mod_the_check_passes_stays_active():
    eng = opened()
    broken = W.row_of(eng, BROKEN)
    W.cmd(eng, "select", arg=broken)
    W.cmd(eng, "activate")
    assert W.ui(eng, "pe%d" % broken) == b"1"
    assert W.ui(eng, "msg").startswith(b"Checked: ")


def test_nothing_changes_the_pending_set_while_a_check_is_asked():
    eng = opened()
    broken = W.row_of(eng, BROKEN)
    W.cmd(eng, "select", arg=broken)
    # The command alone, without qmTick's answer on the next frame.
    eng.set("qm_ui", cmd=b"activate", arg=-1, argside=0, argto=-1, argtext=b"")
    PAS5.run(eng, "qmUiAct")
    assert W.ui(eng, "trpend") == b"1"
    eng.set("qm_ui", cmd=b"deactivate", arg=-1, argside=0, argto=-1, argtext=b"")
    PAS5.run(eng, "qmUiAct")
    assert W.ui(eng, "pe%d" % broken) == b"1"
    assert W.ui(eng, "msg") == b"Still checking the last change; a moment."
    W.answer_trial(eng)
    W.cmd(eng, "deactivate")
    assert W.ui(eng, "pe%d" % broken) == b"0"


def test_apply_of_a_new_mod_waits_for_its_check_and_lists_what_it_refused():
    eng = opened()
    broken = W.row_of(eng, BROKEN)
    W.cmd(eng, "select", arg=broken)
    W.cmd(eng, "activate")
    assert W.ui(eng, "pe%d" % broken) == b"1"
    # Apply asks the check of every mod it switches on (row -1); the answer
    # runs Apply again, and the dialog refuses with the check's FAIL line.
    eng.trial = (b"FAIL", [(b"FAIL", b"gui\\menu.aix does not load: the game would not "
                                     b"start"), (b"WARN", b"a note")])
    asks = int(eng.key(b"qm_rt", b"trq"))
    W.cmd(eng, "apply")
    assert int(eng.key(b"qm_rt", b"trq")) == asks + 1 and eng.key(b"qm_rt", b"trrow") == b"-1"
    assert W.ui(eng, "mode") == b"1" and W.ui(eng, "confblk") == b"1"
    assert W.ui(eng, "confb0") == b"gui\\menu.aix does not load: the game would not start"
    assert W.ui(eng, "confbrule") == b"1"
    notes = [W.ui(eng, "conf%d" % k) for k in range(int(W.ui(eng, "confn")))]
    assert b"Note: a note" in notes
    W.cmd(eng, "confirm")
    assert W.ui(eng, "mode") == b"0"
    assert eng.key(b"qm_rt", b"uiapply") == b"0"
    # Asked again for the same set, Apply does not check it a second time.
    W.cmd(eng, "apply")
    assert int(eng.key(b"qm_rt", b"trq")) == asks + 1 and W.ui(eng, "mode") == b"1"


def test_apply_without_new_mods_asks_no_check():
    eng = opened()
    wasd = W.row_of(eng, WASD)
    W.cmd(eng, "select", arg=wasd)
    W.cmd(eng, "deactivate")
    W.cmd(eng, "apply")
    assert (eng.key(b"qm_rt", b"trq") or b"0") == b"0" and W.ui(eng, "mode") == b"1"


# ------------------------------- the check's word in the status column
@pytest.mark.parametrize("st, want", [(b"OK", b"OK"), (b"WARN", b"WARN"), (b"SKIP", b""),
                                      (b"FAIL", b"")])
def test_a_checked_activation_keeps_the_checks_word_until_apply(st, want):
    """qmUiAct tck<i>, which ShowQmManager shows beside the row's + instead
    of PENDING (since 2026-10-01: MGraphics - Interface and -
    Multiplayer read PENDING after "Checked: ... works with the active mods")."""
    tag = b"FAIL" if st == b"FAIL" else b"WARN"
    eng = opened((st, [] if st == b"OK" else [(tag, b"a line")]))
    broken = W.row_of(eng, BROKEN)
    W.cmd(eng, "select", arg=broken)
    W.cmd(eng, "activate")
    assert W.ui(eng, "trst") == st
    assert W.ui(eng, "tck%d" % broken) == want
    assert W.ui(eng, "pe%d" % broken) == (b"0" if st == b"FAIL" else b"1")


def test_the_checks_word_goes_with_deactivate_and_a_new_window_not_with_a_new_order():
    eng = opened()
    broken = W.row_of(eng, BROKEN)
    W.cmd(eng, "select", arg=broken)
    W.cmd(eng, "activate")
    assert W.ui(eng, "tck%d" % broken) == b"OK"
    W.cmd(eng, "deactivate")
    assert W.ui(eng, "tck%d" % broken) == b""
    W.cmd(eng, "activate")
    assert W.ui(eng, "tck%d" % broken) == b"OK"
    # A new load order keeps it (the hands-on check of 2026-10-01: a word gone
    # after Move up only confused); Apply checks the set in its order again.
    W.cmd(eng, "select", arg=broken, side=1)
    W.cmd(eng, "up", arg=broken)
    assert W.ui(eng, "omoved") == b"1" and W.ui(eng, "tck%d" % broken) == b"OK"
    # A window opened again starts with no check at all.
    W.cmd(eng, "close")
    W.cmd(eng, "open")
    assert all(W.ui(eng, "tck%d" % i) == b"" for i in range(int(W.ui(eng, "n"))))
