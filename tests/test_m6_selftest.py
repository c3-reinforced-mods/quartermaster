"""Offline gates for the manager window's SelfTest case (`ui`) and its checks.

The case state is src/states/qmcaseui.pas, the twin ref.selftest.ui_expected,
the tool tools/m6cases.py (case file, dump check, log rules). Nothing here
runs the game; the logs below are made up in the shape of cos_*.log.
"""
import os
import re

import pytest

import hbuild
import m6cases
from ref import selftest as S

REPO = hbuild.REPO
CASE_STATE = os.path.join(REPO, "src", "states", "qmcaseui.pas")
RUNNER = os.path.join(REPO, "src", "states", "qmselftest.pas")
SHOW = os.path.join(REPO, "src", "screens", "showqmmanager.pas")
MENU_HOOK = os.path.join(REPO, "src", "hooks", "eventmainmenu.pas")


def _text(path):
    with open(path, "rb") as fh:
        return fh.read().decode("ascii")


def _body(path):
    text = _text(path)
    return text[text.index("\n---\n") + 5:]


# ------------------------------------------------------------ the wiring
def test_ui_is_a_case_kind_the_runner_dispatches():
    assert b"ui" in S.KINDS
    runner = _body(RUNNER)
    assert "if (qmStKind='ui') then\n   StateMachineExecuteState(qmStT, 'qmCaseUi', 0)" in runner
    states, _helpers = hbuild.load_sources()
    case = [t for t in states if t.name == "qmCaseUi"]
    assert len(case) == 1 and case[0].into == "data/quartermaster/selftest.aix"


def test_the_case_file_round_trips():
    data = m6cases.case_bytes()
    assert S.parse_case(data) == (b"ui", [(b"cycles", b"10"), (b"toggle", b"mods\\QMTestCamSpeed")])
    assert hbuild.lint_file("qm_case_ui.cfg", data) == []


def test_the_case_sends_the_tags_the_window_uses():
    case = _body(CASE_STATE)
    show = dict(re.findall(r"^const (qmTag\w+) = (\d+);$", _body(SHOW), re.M))
    mine = dict(re.findall(r"^const (qmCuTag\w+) = (\d+);$", case, re.M))
    assert mine == {"qmCuTagDeact": show["qmTagDeact"], "qmCuTagApply": show["qmTagApply"],
                    "qmCuTagReport": show["qmTagReport"], "qmCuTagUp": show["qmTagUp"],
                    "qmCuTagDown": show["qmTagDown"]}
    # The "Mod manager" tag is the literal the EventMainMenu hook checks.
    assert "(GetIntValueByName('Tag')=108)" in _body(MENU_HOOK)
    assert case.count("_gui_SendTagToState('EventMainMenu', 108);") == 2
    for tag in ("gc_gui_event_tagClose", "gc_gui_hotkey_btnEscape", "gc_gui_hotkey_btnEnter"):
        assert "_gui_SendTagToState('EventQmManager', %s);" % tag in case


def test_the_case_writes_only_its_dump_and_withdraws_the_request():
    case = _body(CASE_STATE)
    writers = re.findall(r"\b(ParserSaveToFileByHandle|FileStreamWrite\w*|OpenFileWrite|"
                         r"CopyFileStream|MoveFileStream|RenameFileStream|DeleteFileStream|"
                         r"RestartApplicationParam|qmRawWrite)\b", case)
    assert writers == []
    assert case.count("qmRawWriteStr(qmCuOut, qmCuDump);") == 1
    tail = case[case.rindex("RemoveGUIElement(qmCuH);"):]
    assert "ParserSetIntValueByKeyByHandle(qmCuRtp, 'uiapply', 0);" in tail
    assert tail.rstrip().endswith("ParserSetValueByKeyByHandle(qmCuRt, 'status', 'ok');")


def test_the_case_and_the_twin_agree_on_the_step_line():
    case = _body(CASE_STATE)
    step = [ln for ln in case.splitlines() if ln.strip().startswith("qmCuPut('step|'")][0]
    # name and thirteen values after `step|`.
    assert step.count("'|'") + 1 == 14
    assert len(S.ui_expected(1, m6cases.TOGGLE, 0)[-2].split(b"|")) == 15
    names = re.findall(r"qmCuStep\('(\w+)'\);", case)
    assert tuple(n.encode() for n in names) == tuple(s[0] for s in S.UI_STEPS)


def test_a_kept_request_is_left_for_the_tick_and_the_flow_runs_once():
    case = _body(CASE_STATE)
    tail = case[case.rindex("RemoveGUIElement(qmCuH);"):]
    keep = tail[tail.index("if (qmCuKeep=1) then"):tail.index("else\nbegin\n   if (qmCuRtp<>0) then")]
    assert "'uiapply', 0" not in keep and "'mode', 0" not in keep
    # Without keep the request goes, and the restart notice with it.
    rest = tail[tail.index("else\nbegin\n   if (qmCuRtp<>0) then"):]
    assert "'uiapply', 0" in rest and "ParserSetIntValueByKeyByHandle(qmCuUi, 'mode', 0);" in rest
    assert "qmRawWriteStr(qmCuDone, " in keep
    # The early lives return before the window is touched.
    head = case[:case.index("StateMachineExecuteState(qmCuCore, 'qmUiEnsure', 0);")]
    assert head.count("exit;") == 2 and "FileAge(qmCuDone)<>-1" in head


# ------------------------------------------------------ keep, desk check
def keep_engine(boots, regen=0, restart=0, done=False, on=1):
    """qmCaseUi with `keep 1` after a boot, over test_m5_pascal's emulated
    engine: the lives that only wait or report (no GUI call runs there)."""
    import test_m5_pascal as PAS5

    class Engine(PAS5.Engine):
        def n_SameText(self, a, b):
            # The engine's SameText: equal but for ASCII case.
            return a.lower() == b.lower()

    eng = Engine(mods=[(m6cases.TOGGLE, True, b"0")])
    PAS5.load(eng, "qmCaseUi")
    out = PAS5.SAVE + b"qm_test\\out\\"
    eng.set("qm_case_rt", outdir=out, out=out + b"qm_case_ui9.txt", status=b"started")
    eng.fs[PAS5.SAVE + b"case.cfg"] = m6cases.i9_case_files()[m6cases.CASE_I9]
    eng.n_ParserLoadFromFileByHandle(eng.n_ParserCreate(b"qm_case"), PAS5.SAVE + b"case.cfg")
    eng.set("qm_state", boots=boots)
    eng.set("qm_guard", regen=regen, restart=restart, why=b"stable")
    eng.set("qm_mods", n=1, dir0=m6cases.TOGGLE, on0=on)
    eng.set("qm_rt", uiapply=0)
    if done:
        eng.fs[out + b"qm_case_ui9.done"] = b"ui|2\r\n"
    PAS5.run(eng, "qmCaseUi")
    return eng, out


@pytest.mark.parametrize("regen, restart", [(1, 1), (1, 0), (0, 1)])
def test_a_keep_case_waits_while_the_merge_is_not_loaded(regen, restart):
    eng, out = keep_engine(1, regen, restart)
    assert S.dump_lines(eng.written[out + b"qm_case_ui9_1.txt"]) == S.ui_keep_wait(1, regen,
                                                                                 restart)
    assert out + b"qm_case_ui9.done" not in eng.written
    assert eng.key(b"qm_case_rt", b"status") == b"ok"


def test_a_keep_case_reports_the_flag_after_its_flow():
    eng, out = keep_engine(3, done=True, on=0)
    assert S.dump_lines(eng.written[out + b"qm_case_ui9_3.txt"]) == S.ui_keep_later(3, b"0",
                                                                                  b"stable")
    assert eng.key(b"qm_case_rt", b"status") == b"ok"


def test_the_i9_case_files_round_trip():
    files = m6cases.i9_case_files()
    assert sorted(files) == ["qm_case_ui9.cfg", "qm_m5_restart.cfg"]
    assert S.parse_case(files["qm_case_ui9.cfg"]) == (
        b"ui", [(b"cycles", b"0"), (b"toggle", m6cases.TOGGLE), (b"keep", b"1")])
    assert S.parse_case(files["qm_m5_restart.cfg"]) == (b"m5", [(b"step", b"restart")])
    for name, data in files.items():
        assert hbuild.lint_file(name, data) == []


# ------------------------------------------ the status column (docs/ui.md)
def test_the_status_column_comes_from_report_cfg_on_a_stable_boot():
    """A boot that does not generate runs qmReportLoad, which reads M4's
    report.cfg into qm_report; the window's model takes each row's status
    from there by dir, and `-` for a mod without a record (disabled ones)."""
    import test_m5_pascal as PAS5
    from ref import report as RP

    class Engine(PAS5.Engine):
        def n_SameText(self, a, b):
            return a.lower() == b.lower()

        def n_ParserLoadFromFileByHandle(self, h, path):
            data = self._file(path)
            if path.endswith(b"report.cfg") and data is not None:
                # A flat file, read as the engine's parser reads it (outer
                # spaces dropped: ref/report.py parser_read_flat).
                n = self.nodes[h]
                n.keys, n.inc, n.code = RP.parser_read_flat(data), None, None
                return True
            return PAS5.Engine.n_ParserLoadFromFileByHandle(self, h, path)

    mods = [(b"mods\\SW_Frontline_Protocol", False, b"0"), (b"mods\\QMTestWASD", True, b"0"),
            (b"mods\\QMTestNew", True, b"0"), (PAS5.QM, True, b"0")]
    qmr = {b"lines": b"2", b"l0": b"Quartermaster report", b"l1": b"  indented",
           b"n": b"3", b"dir0": b"mods\\qmtestwasd", b"st0": b"WARN", b"cn0": b"1",
           b"c0_0": b"WARN gui\\menu.inc\\oncamera.inc: merged with conflicts or near edits",
           b"dir1": b"mods\\QMTestNew", b"st1": b"NEW", b"cn1": b"0",
           b"dir2": PAS5.QM, b"st2": b"OK", b"cn2": b"0"}
    eng = Engine({PAS5.SAVE + b"quartermaster\\report.cfg": RP.report_cfg(qmr),
                  PAS5.QM + b"\\data\\quartermaster\\core.aix": b"x"}, mods=mods)
    PAS5.load(eng, "qmReportLoad", "qmUiModel")
    PAS5.run(eng, "qmReportLoad")
    PAS5.run(eng, "qmUiModel")
    assert [eng.key(b"qm_ui", b"st%d" % i) for i in range(4)] == [b"-", b"WARN", b"NEW", b"OK"]
    assert eng.key(b"qm_ui", b"hasreport") == b"1"
    # The report panel's lines keep their indentation through report.cfg.
    assert eng.key(b"qm_report", b"l1") == b"  indented"
    # No report.cfg (a first boot that could not generate) and no index: a
    # disabled row is `-`, a loaded one `?` - never `-` (hands-on check, point 1).
    bare = Engine({PAS5.QM + b"\\data\\quartermaster\\core.aix": b"x"}, mods=mods)
    PAS5.load(bare, "qmReportLoad", "qmUiModel")
    PAS5.run(bare, "qmReportLoad")
    PAS5.run(bare, "qmUiModel")
    assert [bare.key(b"qm_ui", b"st%d" % i) for i in range(4)] == [b"-", b"?", b"?", b"?"]


# ------------------------------------------------------------- the twin
def test_expected_dump_shape():
    lines = S.ui_expected(10, m6cases.TOGGLE, 3, (2, 4), (1, 6))
    # ensure, cycles, row, the steps with order / filtered / unfiltered, end
    assert len(lines) == 1 + 10 + 1 + len(S.UI_STEPS) + 3 + 1
    assert lines[0] == b"ensure|1|1|1|1"
    assert lines[1] == b"cycle|1|close|1|1|1|1|1" and lines[10] == b"cycle|10|esc|1|1|1|10|10"
    assert lines[11] == b"row|" + S.hexs(m6cases.TOGGLE) + b"|3|1"
    assert lines[12] == b"step|open|-1|1|0|1|0|0|0|0|0|0|0|0|0"
    assert lines[14] == b"order|up|2|4"
    # A move is pending until the second move takes it back: Apply on, then off.
    assert lines[15] == b"step|move1|3|1|0|1|0|0|0|0|0|1|1|0|1"
    assert lines[16] == b"step|move2|3|1|0|1|0|0|0|0|0|0|0|0|0"
    assert lines[18] == b"filtered|1|1" and lines[20] == b"unfiltered|6|6"
    assert lines[21] == b"step|report|3|1|0|1|0|0|0|0|0|0|0|1|0"
    # The confirmed Apply: the request in qm_rt and the restart notice (mode 2),
    # drawn alone - no Apply button under it.
    enter = [l for l in lines if l.startswith(b"step|enter|")][0]
    assert enter == b"step|enter|3|0|2|1|1|1|1|1|1|0|0|0|-1"
    assert lines[-1] == b"end|0|11|11"


@pytest.mark.parametrize("place, active, first, moves", [
    (0, 3, b"down", True), (2, 3, b"up", True), (0, 2, b"down", False), (-1, 2, b"down", False)])
def test_the_twin_knows_when_the_move_cannot_happen(place, active, first, moves):
    lines = S.ui_expected(0, m6cases.TOGGLE, 1, (place, active), (1, 3))
    assert b"order|%s|%d|%d" % (first, place, active) in lines
    move1 = [l for l in lines if l.startswith(b"step|move1|")][0].split(b"|")
    assert move1[-4:-2] == ([b"1", b"1"] if moves else [b"0", b"0"])


def test_check_accepts_the_twin_and_names_a_difference():
    good = S.parse_dump(S.dump_bytes(S.ui_expected(10, m6cases.TOGGLE, 4, (0, 3), (2, 7))))
    assert S.ui_check(good, 10, m6cases.TOGGLE) == []
    # The filter must show the rows the case counted itself.
    wrong = [r if r[0] != b"filtered" else (b"filtered", b"1", b"2") for r in good]
    assert any("line" in p for p in S.ui_check(wrong, 10, m6cases.TOGGLE))
    empty = [r if r[0] != b"filtered" else (b"filtered", b"0", b"0") for r in good]
    assert any("at least" in p for p in S.ui_check(empty, 10, m6cases.TOGGLE))
    bad = list(good)
    bad[3] = (b"cycle", b"3", b"close", b"1", b"2", b"1", b"3", b"3")
    problems = S.ui_check(bad, 10, m6cases.TOGGLE)
    assert len(problems) == 1 and "line 4" in problems[0]
    missing = [r for r in good if r[0] != b"row"]
    assert any("not found" in p for p in S.ui_check(missing, 10, m6cases.TOGGLE))


# ------------------------------------------------------------ log rules
def _log(*qm, errors=()):
    lines = ["LOG|  7 |...DoCreate started..."]
    lines += ["ERROR| 9 |error (.\\data\\gui\\menu.aix): TXStateMachine.IndexOfState(%s)" % e
              for e in errors]
    lines += ["LOG| %d |[qm] %s" % (10 + i, t) for i, t in enumerate(qm)]
    return lines


BOOT = ("ui ensure: added ShowQmManager lines=338 index=142",
        "ui ensure: added EventQmManager lines=132 index=143",
        "ui ensure: ready=1 adds=1 from .\\data\\quartermaster\\ui\\",
        "ui ensure: screens present checks=1 adds=1")
CYCLE = ("ui show fresh=True rows=5 active=3 pending=0 sel=-1 mode=0 panel=0 top=12 windows=1",
         "ui close closes=1")


def test_log_rules_hold_for_a_clean_boot():
    problems, facts = m6cases.log_problems(_log(*(BOOT + CYCLE)), battles=0, closes=1)
    assert problems == [] and facts["present_checks"] == 1


def test_log_rules_allow_one_missed_lookup_per_battle():
    after = ("ui ensure: screens gone (a map load reloaded the GUI machine); adding them again",
             "ui ensure: added ShowQmManager lines=338 index=142",
             "ui ensure: added EventQmManager lines=132 index=143",
             "ui ensure: ready=1 adds=2 from .\\data\\quartermaster\\ui\\")
    lines = _log(*(BOOT + CYCLE)) + _log(*after, errors=("ShowQmManager",))
    assert m6cases.log_problems(lines, battles=1)[0] == []
    # Without the battle, the same log is wrong twice over.
    assert len(m6cases.log_problems(lines, battles=0)[0]) >= 2


@pytest.mark.parametrize("change, needle", [
    (lambda ls: ls + ["ERROR| 99 |Compile script error: EventQmManager"], "compile errors"),
    (lambda ls: [l.replace("windows=1", "windows=2") for l in ls], "windows other than 1"),
    (lambda ls: [l for l in ls if "screens present" not in l], "no 'screens present'"),
    (lambda ls: ls + ["ERROR| 98 |error (): TXStateMachine.IndexOfState(ShowQmManager)"],
     "IndexOfState"),
])
def test_log_rules_catch(change, needle):
    lines = change(_log(*(BOOT + CYCLE)))
    assert any(needle in p for p in m6cases.log_problems(lines, battles=0)[0])


# --------------------------------------------------------------- the tool
def test_tool_writes_the_case_and_checks_a_run(tmp_path):
    assert m6cases.main(["case", "--out", str(tmp_path / "cases")], out=lambda s: None) == 0
    with open(tmp_path / "cases" / "qm_case_ui.cfg", "rb") as fh:
        assert fh.read() == m6cases.case_bytes()
    run = tmp_path / "run"
    (run / "qm_test_out").mkdir(parents=True)
    (run / "qm_test_out" / "qm_case_ui.txt").write_bytes(
        S.dump_bytes(S.ui_expected(10, m6cases.TOGGLE, 2)))
    (run / "qm_test_out" / "done.txt").write_bytes(
        S.dump_bytes(S.done_expected([(b"qm_case_ui.cfg", b"ui")])))
    log = _log(*BOOT) + _log(*[CYCLE[0]] * 11, "ui show restart notice", "ui close closes=11",
                             "ui rename: main menu button caption set, renames=1 "
                             "reads back=[Mod Manager] off=0")
    (run / "0.cos_260928_120000.log").write_bytes("\r\n".join(log).encode("latin-1"))
    said = []
    assert m6cases.main(["check", str(run)], out=said.append) == 0, said
    assert said[-1] == "ui run A: OK"
    assert m6cases.main(["check", str(tmp_path / "nothing")], out=lambda s: None) == 2


def test_run_a_needs_the_caption_and_the_restart_notice():
    lines = _log(*(BOOT + CYCLE))
    problems = m6cases.log_problems(lines, closes=1, run_a=True)[0]
    assert any("caption" in p for p in problems) and any("restart notice" in p for p in problems)
    lines += _log("ui show restart notice", "ui rename: main menu button caption set, "
                  "renames=2 reads back=[Mod Manager] off=0", "ui drag none: the button was up")
    problems, facts = m6cases.log_problems(lines, closes=1, run_a=True)
    assert problems == [] and facts["renames"] == [("Mod Manager", "0")]
    assert facts["drag_none"] == 1 and facts["notice_window"] == 1
