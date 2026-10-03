"""The manager window's controller, run offline: qmUiModel, qmUiAct,
qmUiDetails, qmUiApply and qmUiOrder as hbuild emits them, on the script
interpreter of tests/test_m3_pascal.py over test_m5_pascal's emulated engine
(the mod list, the parsers). The hands-on check of 2026-09-28 is the list of
what they must do (docs/ui.md):

  1. every mod the game loaded has a status; `-` only for an inactive one
  2. Up / Down (and the drag's `move`) change the pending load order
  3. Apply is enabled only while a change is pending
  4. the Details line is one line
  5. the filter follows every keystroke
  7. the confirm dialog lists the changes
  8. a confirmed Apply shows the restart notice (mode 2)

and the decision of the same day, a footer with the multiplayer note
while the load order is not the canonical one, which the default order of 2026-09-30 took out
again: with mods.ini's own order as the default it would show nearly always.

A desk check of what the states decide; how the window looks is judged
in game. The GUI states only draw these keys.
"""
import random

import pytest

import test_m5_pascal as PAS5
from ref import order as O

QM = PAS5.QM
WASD = b"mods\\QMTestWASD"
CONF = b"mods\\QMTestConflict"
BROKEN = b"mods\\QMTestBroken"
SWFP = b"mods\\SW_Frontline_Protocol"
WS = b"..\\..\\workshop\\content\\333420\\873048118"


class Engine(PAS5.Engine):
    def n_SameText(self, a, b):
        # The engine's SameText: equal but for ASCII case.
        return a.lower() == b.lower()


def report(*records):
    """qm_report keys for `(dir, status, why)` records."""
    out = {"lines": 1, "l0": b"Quartermaster report", "n": len(records), "mlines": 0}
    for j, (d, st, why) in enumerate(records):
        out["dir%d" % j], out["st%d" % j], out["why%d" % j], out["cn%d" % j] = d, st, why, 0
    return out


def window(mods, rep=None, rt=True, index=None, mods_keys=None):
    """The controller over the mod list `mods` ([(dir, enabled, tag)]), with
    qm_report `rep`, the boot's qm_rt and, when `index` gives the provider
    positions of the scanned files, qm_mods (in mod-list order) and qm_index;
    `mods_keys` are qm_mods keys as a boot left them (`window_ordered`)."""
    eng = Engine({QM + b"\\data\\quartermaster\\core.aix": b"x"}, mods=mods)
    PAS5.load(eng, "qmUiAct", "qmUiModel", "qmUiDetails", "qmUiApply", "qmUiOrder", "qmAbRules")
    if rep is not None:
        eng.set("qm_report", **rep)
    if rt:
        eng.set("qm_rt", uiapply=0, uiapplyseq=0)
    if index is not None:
        keys = {"n": len(mods)}
        for i, (d, _on, _t) in enumerate(mods):
            keys["dir%d" % i], keys["ord%d" % i], keys["pos%d" % i] = d, i, i
        eng.set("qm_mods", **keys)
        idx = {"n": len(index)}
        for k, v in enumerate(index):
            idx["p%d" % k], idx["v%d" % k] = b"gui\\menu.inc\\f%d.inc" % k, v
        eng.set("qm_index", **idx)
    if mods_keys is not None:
        eng.set("qm_mods", **mods_keys)
    cmd(eng, "open")
    return eng


def cmd(eng, name, arg=-1, side=0, to=-1, text=b""):
    eng.set("qm_ui", cmd=name.encode(), arg=arg, argside=side, argto=to, argtext=text)
    PAS5.run(eng, "qmUiAct")
    assert eng.key(b"qm_ui", b"cmd") == b"", "qmUiAct did not take %s" % name
    answer_trial(eng)


def answer_trial(eng):
    """The next frame's qmTick when the command asked for the activation
    check (qm_rt trq): qmTrial's answer - `eng.trial` = (status, [(tag,
    text)]), OK by default - then qmUiAct `trialdone`, as qmrestarttick.pas
    does. The trial itself (a whole generation) is not run here."""
    if b"qm_rt" not in eng.named:
        return
    q = eng.key(b"qm_rt", b"trq") or b"0"
    if int(q) <= int(eng.key(b"qm_rt", b"trdone") or b"0"):
        return
    st, lines = getattr(eng, "trial", (b"OK", []))
    keys = {"trst": st, "trn": len(lines), "trrow": eng.key(b"qm_rt", b"trrow"),
            "trsig": eng.key(b"qm_rt", b"trsig")}
    for k, (tag, text) in enumerate(lines):
        keys["tr%d" % k], keys["trt%d" % k] = text, tag
    eng.set("qm_rt", trdone=int(q))
    eng.set("qm_ui", cmd=b"trialdone", **keys)
    PAS5.run(eng, "qmUiAct")


def ui(eng, key):
    return eng.key(b"qm_ui", key.encode())


def row_of(eng, d):
    return next(i for i in range(int(ui(eng, "n"))) if ui(eng, "dir%d" % i) == d)


def active_order(eng):
    """The Active list as the window draws it: rows with pe = 1 in ord order."""
    n = int(ui(eng, "n"))
    rows = [int(ui(eng, "ord%d" % k)) for k in range(n)]
    return [ui(eng, "dir%d" % i) for i in rows if ui(eng, "pe%d" % i) == b"1"]


MODS = [(WS, False, b"873048118"), (CONF, True, b"0"), (WASD, True, b"0"),
        (SWFP, False, b"0"), (QM, True, b"0")]
REPORT = report((CONF, b"WARN", b"1 of 1 files need a look, first gui\\menu.inc\\oncamera.inc:"
                 b" merged with conflicts or near edits"),
                (WASD, b"OK", b"4 files, all merged or used without problems"),
                (QM, b"OK", b"4 files, all merged or used without problems"))


def test_the_details_line_says_what_the_conflict_report_says_of_the_mod():
    """qm_report cpd<j> (qmConflicts' Details sentence) ends the row's line,
    as a sentence of its own; a row without one gets nothing."""
    rep = dict(REPORT, cpd0=b"Loses 1 conflict to mods\\QMTestWASD")
    eng = window(MODS, rep)
    cmd(eng, "select", arg=row_of(eng, CONF))
    assert ui(eng, "d0").endswith(b"near edits. Loses 1 conflict to mods\\QMTestWASD.")
    cmd(eng, "select", arg=row_of(eng, WASD))
    assert b"conflict" not in ui(eng, "d0")


# ------------------------------------------------------- 1. the status column
def test_every_loaded_mod_has_a_status_and_only_an_inactive_one_reads_dash():
    eng = window(MODS, REPORT)
    assert [ui(eng, "st%d" % i) for i in range(5)] == [b"-", b"WARN", b"OK", b"-", b"OK"]
    assert [ui(eng, "stsrc%d" % i) for i in range(5)] == [b"", b"report", b"report", b"",
                                                           b"report"]


def test_a_loaded_mod_the_report_does_not_know_is_ok_when_it_ships_no_merged_file():
    """A Workshop mod that ships none of the scanned files is OK by the
    index, not `-` (hands-on check, point 1)."""
    mods = [(WS, True, b"873048118")] + MODS[1:]
    # The index: two files, both from rows 1 and 2 (positions = rows here).
    eng = window(mods, REPORT, index=[b"1;2", b"2;4"])
    assert (ui(eng, "st0"), ui(eng, "stsrc0")) == (b"OK", b"index")
    assert any(b"no report record for loaded " + WS in line and b"status=OK" in line
               for line in eng.log)
    # One that ships a scanned file stays unknown until the next generation.
    eng = window(mods, REPORT, index=[b"0;2"])
    assert (ui(eng, "st0"), ui(eng, "stsrc0")) == (b"?", b"none")


def test_without_index_or_report_a_loaded_mod_is_unknown_not_dash():
    eng = window(MODS, None)
    assert [ui(eng, "st%d" % i) for i in range(5)] == [b"-", b"?", b"?", b"-", b"?"]


# ------------------------------------------- 3. Apply only with a pending change
def test_apply_is_enabled_only_while_an_activation_is_pending():
    eng = window(MODS, REPORT)
    assert (ui(eng, "chg"), ui(eng, "canapply")) == (b"0", b"0")
    cmd(eng, "apply")
    assert (ui(eng, "mode"), ui(eng, "msg")) == (b"0", b"Nothing to apply.")
    cmd(eng, "select", arg=0)
    cmd(eng, "activate")
    assert (ui(eng, "chg"), ui(eng, "canapply")) == (b"1", b"1")
    cmd(eng, "deactivate")
    assert (ui(eng, "chg"), ui(eng, "canapply")) == (b"0", b"0")


# ------------------------------------------------------- 2. the load order
def test_up_and_down_change_the_pending_order_and_enable_apply():
    eng = window(MODS, REPORT)
    assert active_order(eng) == [CONF, WASD, QM]
    wasd = row_of(eng, WASD)
    cmd(eng, "select", arg=wasd, side=1)
    cmd(eng, "up", arg=wasd)
    assert active_order(eng) == [WASD, CONF, QM]
    assert (ui(eng, "ordchg"), ui(eng, "canapply"), ui(eng, "sel")) == (b"1", b"1", b"%d" % wasd)
    cmd(eng, "down", arg=wasd)
    assert active_order(eng) == [CONF, WASD, QM]
    assert (ui(eng, "ordchg"), ui(eng, "canapply")) == (b"0", b"0")
    # Quartermaster loads last: nothing goes below it, it never moves.
    cmd(eng, "down", arg=wasd)
    assert active_order(eng) == [CONF, WASD, QM] and ui(eng, "omoved") == b"0"
    cmd(eng, "up", arg=row_of(eng, QM))
    assert active_order(eng) == [CONF, WASD, QM] and ui(eng, "msg") != b""


def test_the_drag_command_moves_a_row_to_the_place_it_was_dropped_at():
    mods = [(CONF, True, b"0"), (BROKEN, True, b"0"), (WASD, True, b"0"), (QM, True, b"0")]
    eng = window(mods, None)
    cmd(eng, "move", arg=row_of(eng, WASD), side=1, to=0)
    assert active_order(eng) == [WASD, CONF, BROKEN, QM] and ui(eng, "ordchg") == b"1"
    # A drop below Quartermaster lands just above it: here, back where it was.
    cmd(eng, "move", arg=row_of(eng, WASD), side=1, to=9)
    assert active_order(eng) == [CONF, BROKEN, WASD, QM]
    assert (ui(eng, "ordchg"), ui(eng, "canapply")) == (b"0", b"0")


# ------------------------------------------- 7. the confirm dialog's list
def conf_lines(eng):
    return [ui(eng, "conf%d" % k) for k in range(int(ui(eng, "confn")))]


def test_the_confirm_dialog_lists_activations_deactivations_and_the_new_order():
    eng = window(MODS, REPORT)
    cmd(eng, "select", arg=0)
    cmd(eng, "activate")
    cmd(eng, "select", arg=row_of(eng, CONF), side=1)
    cmd(eng, "deactivate")
    cmd(eng, "select", arg=row_of(eng, WASD), side=1)
    cmd(eng, "up", arg=row_of(eng, WASD))
    cmd(eng, "apply")
    assert ui(eng, "mode") == b"1"
    # Two columns: the switches, and the load order Apply leaves (always shown).
    assert conf_lines(eng) == [b"+ 873048118", b"- QMTestConflict"]
    assert [ui(eng, "confo%d" % k) for k in range(int(ui(eng, "confon")))] ==         [b"1. QMTestWASD", b"2. 873048118", b"3. Quartermaster"]
    assert ui(eng, "confordchg") == b"1"
    # The window's own rows are unchanged by the question.
    assert ui(eng, "canapply") == b"0"
    cmd(eng, "cancel")
    assert (ui(eng, "mode"), ui(eng, "canapply")) == (b"0", b"1")


def test_a_long_confirm_list_is_cut_with_a_count():
    mods = [(b"mods\\M%02d" % i, False, b"0") for i in range(20)] + [(QM, True, b"0")]
    eng = window(mods, None)
    for i in range(20):
        cmd(eng, "select", arg=i)
        cmd(eng, "activate")
    cmd(eng, "apply")
    lines = conf_lines(eng)
    assert len(lines) == 14 and lines[-1] == b"... and 7 more"


# ------------------------------------ 8. the confirmed Apply and the notice
def test_a_confirmed_apply_records_flags_and_order_and_shows_the_restart_notice():
    eng = window(MODS, REPORT)
    wasd = row_of(eng, WASD)
    cmd(eng, "select", arg=wasd, side=1)
    cmd(eng, "up", arg=wasd)
    cmd(eng, "apply")
    cmd(eng, "enter")                       # Enter confirms in the dialog
    rt = lambda k: eng.key(b"qm_rt", k)     # noqa: E731
    assert (rt(b"uiapply"), rt(b"uiapplyseq"), rt(b"uiapplychg"), rt(b"uiapplyorder")) == (
        b"1", b"1", b"0", b"1")
    assert [rt(b"uiapplyord%d" % k) for k in range(5)] == [WS, WASD, CONF, SWFP, QM]
    assert [rt(b"uiapplydis%d" % k) for k in range(5)] == [b"1", b"0", b"0", b"1", b"0"]
    assert ui(eng, "mode") == b"2"
    # While the notice shows, nothing but close counts; the notice stays the mode.
    cmd(eng, "activate")
    cmd(eng, "apply")
    assert (ui(eng, "mode"), rt(b"uiapplyseq")) == (b"2", b"1")
    cmd(eng, "esc")
    assert (ui(eng, "close"), ui(eng, "mode")) == (b"1", b"2")


def test_without_the_boot_the_confirm_records_nothing_and_stays_in_browse_mode():
    eng = window(MODS, REPORT, rt=False)
    cmd(eng, "select", arg=0)
    cmd(eng, "activate")
    cmd(eng, "apply")
    cmd(eng, "confirm")
    assert ui(eng, "mode") == b"0" and ui(eng, "msg").startswith(b"Not applied")


# ------------------------------------------------------------ 4. Details
def test_the_details_panel_is_one_line_with_status_and_reason():
    eng = window(MODS, REPORT)
    cmd(eng, "select", arg=row_of(eng, CONF), side=1)
    assert ui(eng, "dn") == b"1"
    assert ui(eng, "d0") == (b"QMTestConflict - WARN: 1 of 1 files need a look, first "
                             b"gui\\menu.inc\\oncamera.inc: merged with conflicts or near edits")
    cmd(eng, "select", arg=0)
    assert ui(eng, "d0") == b"873048118 - inactive"
    cmd(eng, "activate")
    assert ui(eng, "d0") == b"873048118 - inactive. Apply activates it."
    cmd(eng, "select", arg=row_of(eng, QM), side=1)
    assert ui(eng, "d0").endswith(b"(Quartermaster itself)")


# ------------------------------------------------------------ 5. the filter
def test_every_keystroke_filters_and_the_report_view_leaves_with_esc():
    eng = window(MODS, REPORT)
    eng.set("qm_ui", topi=3)
    cmd(eng, "filter", text=b"q")
    assert (ui(eng, "filter"), ui(eng, "typed"), ui(eng, "topi")) == (b"q", b"q", b"0")
    cmd(eng, "filter", text=b"qm")
    assert ui(eng, "filter") == b"qm"
    cmd(eng, "report")
    assert ui(eng, "panel") == b"1"
    cmd(eng, "esc", text=b"qm")
    assert (ui(eng, "panel"), ui(eng, "close")) == (b"0", b"0")
    cmd(eng, "esc", text=b"qm")
    assert ui(eng, "close") == b"1"


# ------------------------------------------ 9. the load order in the window
def window_ordered(mods, saved=None, rep=None):
    """`(controller, LoadOrder)` after a boot over `mods` with the saved order
    `saved` (dirs, None: no order.cfg): qm_mods as qmOrder leaves it - ord<k>
    / pos<i> the load order (ref/order.py load_order), cord<k> / cpos<i> the
    canonical order."""
    dirs = [d for d, _on, _t in mods]
    lo = O.load_order(dirs, QM, saved, [on for _d, on, _t in mods])
    canon = O.canonical_indices(dirs, QM)
    keys = {"n": len(mods)}
    for i, d in enumerate(dirs):
        keys["dir%d" % i] = d
    for k, (i, c) in enumerate(zip(lo.rows, canon)):
        keys["ord%d" % k], keys["pos%d" % i] = i, k
        keys["cord%d" % k], keys["cpos%d" % c] = c, k
    return window(mods, rep, mods_keys=keys), lo


def test_the_window_keeps_the_canonical_order_for_auto_sort():
    # MODS is mods.ini's order and the canonical one: rule 1 keeps it.
    eng, lo = window_ordered(MODS, rep=REPORT)
    assert lo.src == b"ini" and lo.canon
    assert [ui(eng, "cord%d" % k) for k in range(5)] == [b"0", b"1", b"2", b"3", b"4"]
    assert (ui(eng, "order"), ui(eng, "hascanon")) == (b"qm_mods", b"1")
    eng, lo = window_ordered(MODS, saved=[WASD, CONF], rep=REPORT)
    assert lo.src == b"saved" and not lo.canon
    assert active_order(eng) == [WASD, CONF, QM]
    assert (ui(eng, "hascanon"), ui(eng, "ordchg")) == (b"1", b"0")
    assert any(b"ui model n=5 " in line and b" canon=1 " in line for line in eng.log)
    # The custom-order footer is gone: no key says it any more.
    assert ui(eng, "ordcustom") == b""
    # Auto-sort puts the canonical order back, a change Apply can make.
    cmd(eng, "autosort")
    assert active_order(eng) == [CONF, WASD, QM]
    assert (ui(eng, "ordchg"), ui(eng, "canapply")) == (b"1", b"1")


def test_a_move_back_to_the_loaded_order_leaves_nothing_pending():
    eng, _lo = window_ordered(MODS, rep=REPORT)
    wasd = row_of(eng, WASD)
    cmd(eng, "select", arg=wasd, side=1)
    cmd(eng, "up", arg=wasd)
    assert active_order(eng) == [WASD, CONF, QM]
    assert (ui(eng, "ordchg"), ui(eng, "canapply")) == (b"1", b"1")
    cmd(eng, "down", arg=wasd)
    assert (ui(eng, "ordchg"), ui(eng, "canapply")) == (b"0", b"0")
    # A saved order moved: pending until the dialog's answer, and back again.
    eng, _lo = window_ordered(MODS, saved=[WASD, CONF], rep=REPORT)
    wasd = row_of(eng, WASD)
    cmd(eng, "select", arg=wasd, side=1)
    cmd(eng, "down", arg=wasd)
    assert active_order(eng) == [CONF, WASD, QM]
    assert (ui(eng, "ordchg"), ui(eng, "canapply")) == (b"1", b"1")
    cmd(eng, "apply")
    assert ui(eng, "mode") == b"1"
    cmd(eng, "cancel")
    assert ui(eng, "mode") == b"0"
    cmd(eng, "up", arg=wasd)
    assert (ui(eng, "ordchg"), ui(eng, "canapply")) == (b"0", b"0")


def test_without_a_canonical_order_auto_sort_is_off():
    # No qm_mods: the rows keep mods.ini order, and nothing says what is canonical.
    eng = window(MODS, REPORT)
    assert (ui(eng, "order"), ui(eng, "hascanon")) == (b"engine", b"0")
    # qm_mods without cord<k>: every missing key reads 0, not a permutation.
    eng = window(MODS, REPORT, index=[b"1;2"])
    assert (ui(eng, "order"), ui(eng, "hascanon")) == (b"qm_mods", b"0")
    assert any(b"ui model n=5 " in line and b" canon=0 " in line for line in eng.log)


# ---------------------------------------------- global scripts (plan S17)
SVC = b"..\\..\\workshop\\content\\333420\\1325221799"
CANNONS = b"..\\..\\workshop\\content\\333420\\1450025705"
UNIT = b"\\data\\scripts\\lib\\unit.script"


def globals_window(cannons_on):
    mods = [(SVC, True, b"1325221799"), (CANNONS, cannons_on, b"1450025705"), (QM, True, b"0")]
    eng = Engine({QM + b"\\data\\quartermaster\\core.aix": b"x", SVC + UNIT: b"u",
                  SVC + b"\\data\\scripts\\lib\\ai.script": b"a", CANNONS + UNIT: b"c"},
                 mods=mods)
    PAS5.load(eng, "qmUiAct", "qmUiModel", "qmUiDetails", "qmUiApply", "qmUiOrder", "qmAbRules")
    eng.set("qm_rt", uiapply=0, uiapplyseq=0)
    return eng


def test_rows_list_their_global_scripts_and_enabled_clashes_read_warn():
    # A WARN since 0.1.3 (a FAIL before): the game loaded both.
    eng = globals_window(True)
    cmd(eng, "open")
    assert ui(eng, "gl0") == b"|lib\\ai.script|lib\\unit.script|"
    assert ui(eng, "gl1") == b"|lib\\unit.script|" and ui(eng, "gl2") == b"|"
    assert (ui(eng, "st0"), ui(eng, "stsrc0")) == (b"WARN", b"globals")
    assert b"scripts\\lib\\unit.script" in ui(eng, "why1")
    # The status sentence has no full stop of its own; it gets one before the
    # clash sentence (run look-wsX read "Deactivate one of them It clashes").
    cmd(eng, "select", arg=0)
    assert b"deactivate the other. It may clash with " in ui(eng, "d0")
    assert b".." not in ui(eng, "d0")


def test_apply_asks_about_a_pending_set_with_a_clash():
    # Until 0.1.3 the dialog listed the clash instead of the question and
    # confirm refused; the start-up guard now undoes a start that stops.
    eng = globals_window(False)
    cmd(eng, "open")
    assert ui(eng, "pcn") == b"0" and ui(eng, "st1") == b"-"
    cmd(eng, "select", arg=1)
    cmd(eng, "activate")
    assert ui(eng, "pcn") == b"1"
    assert b"both replace scripts\\lib\\unit.script" in ui(eng, "pc0")
    assert b"Apply activates it. It may clash with" in ui(eng, "d0")
    cmd(eng, "apply")
    assert ui(eng, "mode") == b"1" and ui(eng, "confblk") == b"0"
    lines = [ui(eng, "conf%d" % k) for k in range(int(ui(eng, "confn")))]
    assert any(l.startswith(b"Note: ") and b"both replace scripts\\lib\\unit.script" in l
               and b"Quartermaster switches back at the next start" in l for l in lines)
    cmd(eng, "cancel")
    # Deactivating it again clears the clash, and Apply has nothing to do.
    cmd(eng, "deactivate")
    assert ui(eng, "pcn") == b"0" and ui(eng, "canapply") == b"0"


def test_the_guard_notice_opens_once_and_ok_closes_it():
    eng = globals_window(False)
    eng.set("qm_glob", gdn=1, gdd0=CANNONS, gdt0=b"Cannons Attack Automatically",
            gdf0=b"lib\\unit.script", gdo0=b"State vs Country")
    eng.set("qm_ui", gdopen=1)
    cmd(eng, "open")
    assert ui(eng, "mode") == b"3" and ui(eng, "gdln") == b"1"
    assert ui(eng, "gdl0") == (b"Cannons Attack Automatically - ships scripts\\lib\\unit.script,"
                               b" like State vs Country")
    assert ui(eng, "gdoff1") == b"1" and b"switched off at start" in ui(eng, "why1")
    # The pair had not started together; activated here, it is trusted for a
    # start (the Apply's chosen.cfg), so the row says how to run it anyway.
    assert ui(eng, "why1").endswith(b"; with both the game may not start. If they work"
                                    b" together, activate it again")
    # A step after a start that stopped: by name, or with no clash.
    for why, f, end in ((b"failed-names", b"lib\\unit.script",
                         b", and the start before, with both, did not reach the main menu"),
                        (b"failed-revert", b"", b": the start before did not reach the main menu")):
        step = globals_window(False)
        step.set("qm_glob", gdn=1, gdd0=CANNONS, gdt0=b"Cannons Attack Automatically", gdf0=f,
                 gdo0=b"State vs Country" if f else b"", gdwhy=why)
        step.set("qm_ui", gdopen=1)
        cmd(step, "open")
        assert ui(step, "why1").endswith(end), ui(step, "why1")
    cmd(eng, "activate")                      # ignored under the notice
    assert ui(eng, "mode") == b"3"
    # `open` under the notice draws it again (qmTick after a rebuilt menu, or
    # the main menu button); until 2026-10-01 it was ignored.
    cmd(eng, "open")
    assert ui(eng, "mode") == b"3" and ui(eng, "gdln") == b"1"
    assert ui(eng, "gdl0").startswith(b"Cannons Attack Automatically - ships ")
    cmd(eng, "enter")
    assert ui(eng, "mode") == b"0"
    cmd(eng, "close")
    cmd(eng, "open")                          # gdopen was taken once
    assert ui(eng, "mode") == b"0"
