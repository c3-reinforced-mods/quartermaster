"""The activation check's key settings and its clean-up (qmTrial), offline on
the settings tests' engine (named children of qm_settings, hotkeys.cfg as
records): a key another key setting of the same mod or of another active mod
holds is a WARN; so is a key the game holds against it by the Options view's
rules (src/lib/qmkeys.pas) - but not the setting's own default, and not an
`event` hotkey; and the validation copies a check made are gone afterwards.
The pipeline the check drives is stood in by Python."""
import test_m10_settings as M10
import test_m5_pascal as PAS5

KEYS = b"mods\\QMTestKeys"
KEYS_ABOUT = (b"id = qmtestkeys\r\nsetting = fire;key;A;Fire\r\nsetting = alt;key;C;Alt\r\n"
              b"setting = ev;key;V;Ev\r\nsetting = pan;key;X;Pan\r\n")
WORK = PAS5.SAVE + b"quartermaster\\trial\\work\\val\\"


class Engine(M10.Engine):
    def n_GetTriggerManagerStateMachineHandle(self, name):
        return 7 if name.lower() == b"qm_core" else 0

    def n_DeleteFileStream(self, path):
        self.__dict__.setdefault("removed", []).append(path)


def checked(wasd_on=True, stored=None):
    mod_list = [(M10.WASD, wasd_on, b""), (KEYS, False, b""), (M10.QM, True, b"0")]
    fs = dict(M10.FILES)
    fs[KEYS + b"\\about.cfg"] = KEYS_ABOUT
    eng = Engine(fs, mod_list)
    if stored:
        # The player's settings.cfg: keys set in the Options view.
        eng.saved[M10.SETTINGS] = ({}, [(b"qmtestkeys", (dict(stored), []))])
        eng.fs[M10.SETTINGS] = b"saved"
    PAS5.load(eng, "qmAbout", "qmSettings", "qmModList", "qmUiAct", "qmUiModel", "qmUiDetails",
              "qmUiApply", "qmUiOrder", "qmAbRules", "qmTrial")
    for st in ("qmAbout", "qmSettings", "qmModList"):
        PAS5.run(eng, st)
    eng.set("qm_rt", uiapply=0, uiapplyseq=0)
    M10.W6.cmd(eng, "open")
    row = next(i for i in range(int(M10.ui(eng, "n"))) if M10.ui(eng, "dir%d" % i) == KEYS)
    eng.set("qm_ui", **{"pe%d" % row: 1})
    eng.set("qm_val", seq=5)

    def generate():
        eng.set("qm_gen", status=b"ok")
        eng.set("qm_val", seq=8)
    for name, fn in (("qmIndex", lambda: None), ("qmPlan", lambda: eng.set("qm_plan", n=0)),
                     ("qmGenerate", generate), ("qmValFiles", lambda: None)):
        eng.states[name.lower()] = PAS5.Fake(fn)
    eng.set("qm_rt", trrow=row, trsig=b"s")
    PAS5.run(eng, "qmTrial")
    lines = [(eng.key(b"qm_ui", b"trt%d" % k), eng.key(b"qm_ui", b"tr%d" % k))
             for k in range(int(eng.key(b"qm_ui", b"trn")))]
    return eng, lines


def test_a_key_another_active_mod_holds_is_a_warn_even_as_a_default():
    eng, lines = checked()
    assert eng.key(b"qm_ui", b"trst") == b"WARN"
    # C is the default of Alt and vanilla's hotkey of build|%nat%cen: the
    # author chose it, as the Options view lets them - no line.
    assert lines == [(b"WARN", b"key A: Fire of QMTestKeys and Camera left of QMTestWASD")]


def test_a_mod_that_is_not_active_shares_no_key():
    eng, lines = checked(wasd_on=False)
    assert lines == [] and eng.key(b"qm_ui", b"trst") == b"OK"


def test_two_settings_of_the_mod_itself_on_one_key_are_a_warn():
    _eng, lines = checked(wasd_on=False, stored={b"alt": b"A"})
    assert lines == [(b"WARN", b"key A: Fire and Alt of QMTestKeys")]


def test_a_key_the_game_holds_against_a_stored_key_is_a_warn():
    # The rules of the Options view (qmkeys), for a key set away from the
    # default: a player's hotkey (but an event one), a key the game does not
    # let a hotkey use, a shortcut registered by its literal name.
    cases = [(b"J", b"key J: Pan of QMTestKeys - the game's hotkey build|%nat%tem uses it"),
             (b"Q", b"key Q: Pan of QMTestKeys - the game's hotkey build|%nat%cen uses it"),
             (b"P", b"key P: Pan of QMTestKeys - the game does not let a hotkey use it"),
             (b"K", b"key K: Pan of QMTestKeys - the game's shortcut myname uses it"),
             # V: only Ev of the mod itself - vanilla's V is an event hotkey.
             (b"V", b"key V: Ev and Pan of QMTestKeys"), (b"Y", None)]
    for key, want in cases:
        _eng, lines = checked(wasd_on=False, stored={b"pan": key})
        assert lines == ([(b"WARN", want)] if want else []), key


def test_the_validation_copies_of_the_check_are_removed():
    eng, _lines = checked()
    assert eng.removed == [WORK + b"%d.%s" % (k, e) for k in (5, 6, 7) for e in (b"inc", b"aix")]
    assert eng.key(b"qm_ui", b"trvals") == b"3"
