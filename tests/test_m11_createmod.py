"""Create mod, Create about.cfg, Edit game file (plan G17; M11), run
offline on the script interpreter: the window's commands (qmUiAct) leave a
request in qm_rt, qmTick runs qmModFiles, and the writer's functions make
the files - compared byte for byte with the twin ref/createmod.py (plus the
raw writer's padding) - or refuse.
"""
import test_m5_pascal as PAS5
import test_m6_window as W6
from ref import createmod as CM
from ref import textio as T

QM = PAS5.QM
APP = PAS5.APP
LOCAL = b"mods\\MyLocal"
WS = b"..\\..\\workshop\\content\\333420\\873048118"
VIDX = QM + b"\\data\\quartermaster\\vanilla.idx"
ONCAM = b"gui\\menu.inc\\oncamera.inc"


class Engine(W6.Engine):
    def n_CopyFileStream(self, src, dst):
        data = self._file(src)
        if data is None:
            raise PAS5.PAS.RunError("copy of a missing file")
        if dst not in self.written:
            raise PAS5.PAS.RunError("a copy into a folder that may not exist raises (probe 1)")
        self.written[dst] = data

    def n_GetGUIElementIndexByNameParent(self, name, parent):
        return 0

    def n__gui_GetTop(self):
        return 0


def vidx(paths):
    lines = [b"section.begin", b"   Name = qmVanillaIndex", b"   Format = 1",
             b"   Count = %d" % len(paths), b"   Code : struct.begin"]
    lines += [b"      [*] = ;" + p for p in paths]
    lines += [b"   struct.end", b"section.end", b""]
    return b"\r\n".join(lines)


def world(extra=None):
    files = {QM + b"\\data\\quartermaster\\core.aix": b"x",
             VIDX: vidx([b"gui\\menu.inc\\oncamera.inc|4423|70|merge",
                         b"game\\var\\hotkeys.cfg|5316|243|wta",
                         b"gui\\menu.aix|99|9|never"]),
             APP + b"data\\" + ONCAM: b"vanilla oncamera\r\nbytes \x00\x01 kept\r\n"}
    files.update(extra or {})
    mods = [(LOCAL, True, b""), (WS, True, b"873048118"), (QM, True, b"0")]
    eng = Engine(files, mods=mods)
    PAS5.load(eng, "qmUiAct", "qmUiModel", "qmUiDetails", "qmUiApply", "qmUiOrder",
              "qmAbRules", "qmModFiles", "qmTick", "qmRestart", "qmMarkerSave")
    eng.set("qm_rt", uiapply=0, uiapplyseq=0, qmdir=QM)
    W6.cmd(eng, "open")
    return eng


def ui(eng, key):
    return eng.key(b"qm_ui", key.encode())


def tick(eng):
    PAS5.run(eng, "qmTick")


def test_new_mod_writes_the_three_files_the_twin_makes():
    eng = world()
    W6.cmd(eng, "newmod")
    assert ui(eng, "mode") == b"4"
    W6.cmd(eng, "filter", text=b"My new mod!")
    assert ui(eng, "nmfolder") == b"My_new_mod"
    W6.cmd(eng, "nmtype")
    W6.cmd(eng, "nmexcl")                       # camera
    W6.cmd(eng, "activate")                     # ignored in the dialog
    assert ui(eng, "mode") == b"4"
    W6.cmd(eng, "enter")                        # Create
    assert ui(eng, "mode") == b"0" and eng.key(b"qm_rt", b"mfreq") == b"new"
    assert not any(p.startswith(b"mods\\My_new_mod") for p in eng.written)
    tick(eng)
    want = CM.files(b"My_new_mod", b"My new mod!", b"totalConversion", b"camera")
    for rel, data in want.items():
        got = eng.written[b"mods\\My_new_mod\\" + rel]
        assert got.rstrip(b" ") == data and len(got) % 4 == 0, rel
    assert eng.key(b"qm_rt", b"mfres") == b"1" and eng.key(b"qm_rt", b"mfreq") == b""
    assert ui(eng, "msg") == (b"Created mods\\My_new_mod. It is in the list after you restart "
                              b"the game: the game looks for new mod folders only when it starts.")


def test_closing_the_new_mod_dialog_gives_the_filter_box_its_text_back():
    """Every command carries its box's text, stored as `typed` (what the
    filter box shows after a redraw); in the dialog that is the name box's.
    Run look-msg2 (2026-10-01): after Create the filter box held the name,
    and its next key filtered the Installed list by it to nothing."""
    for close in ("enter", "esc"):
        eng = world()
        W6.cmd(eng, "filter", text=b"my")
        assert ui(eng, "filter") == b"my"
        W6.cmd(eng, "newmod", text=b"my")
        W6.cmd(eng, "filter", text=b"Better Cavalry")
        assert ui(eng, "typed") == b"Better Cavalry" and ui(eng, "nmname") == b"Better Cavalry"
        W6.cmd(eng, close, text=b"Better Cavalry")
        assert ui(eng, "mode") == b"0", close
        assert (ui(eng, "typed"), ui(eng, "filter")) == (b"my", b"my"), close


def test_new_mod_refuses_a_taken_folder_and_a_name_without_letters():
    eng = world()
    W6.cmd(eng, "newmod")
    W6.cmd(eng, "filter", text=b"MyLocal")
    W6.cmd(eng, "nmcreate")
    assert ui(eng, "msg") == b"mods\\MyLocal is a mod already; choose another name."
    assert ui(eng, "mode") == b"4"
    W6.cmd(eng, "filter", text=b"123")
    W6.cmd(eng, "nmcreate")
    assert ui(eng, "msg") == b"Type a name with at least one letter."
    W6.cmd(eng, "esc")
    assert ui(eng, "mode") == b"0" and eng.key(b"qm_rt", b"mfreq") == b""
    # the writer refuses on its own too: files there already
    eng2 = world({b"mods\\Taken\\about.cfg": b"x"})
    eng2.set("qm_rt", mfreq=b"new", mffolder=b"Taken", mftitle=b"Taken", mftype=b"mod", mfexcl=b"")
    tick(eng2)
    assert eng2.key(b"qm_rt", b"mfres") == b"0" and b"mods\\Taken\\mod.ini" not in eng2.written


def rows(eng):
    return int(ui(eng, "n"))


def test_mod_files_about_cfg_for_a_local_mod_only():
    eng = world({LOCAL + b"\\data\\" + ONCAM: b"its camera"})
    W6.cmd(eng, "select", arg=1)                 # the Workshop mod
    W6.cmd(eng, "modfiles")
    assert ui(eng, "panel") == b"0" and ui(eng, "msg").startswith(b"Only a local mod")
    W6.cmd(eng, "select", arg=0)
    W6.cmd(eng, "modfiles")
    assert ui(eng, "panel") == b"3" and ui(eng, "mfhas") == b"0"
    W6.cmd(eng, "mfabout")
    assert eng.key(b"qm_rt", b"mfreq") == b"about" and eng.key(b"qm_rt", b"mfcam") == b"1"
    tick(eng)
    got = eng.written[LOCAL + b"\\about.cfg"]
    assert got.rstrip(b" ") == CM.draft_for(b"MyLocal", b"MyLocal", b"", camera=True)
    # never over an existing about.cfg
    W6.cmd(eng, "mfabout")
    assert ui(eng, "msg") == b"This mod has an about.cfg already."


def test_edit_game_file_copies_the_pristine_bytes_and_never_over_a_file():
    eng = world()
    W6.cmd(eng, "select", arg=0)
    W6.cmd(eng, "modfiles")
    W6.cmd(eng, "filter", text=b"on")                     # two characters: no search
    assert ui(eng, "vn") == b"0"
    W6.cmd(eng, "filter", text=b"ONCAM")
    assert ui(eng, "vn") == b"1" and ui(eng, "v0") == ONCAM and ui(eng, "vc0") == b"merge"
    W6.cmd(eng, "mfcopy")
    assert ui(eng, "msg") == b"Pick a game file in the list first."
    W6.cmd(eng, "vselect", arg=0)
    W6.cmd(eng, "mfcopy")
    tick(eng)
    assert eng.written[LOCAL + b"\\data\\" + ONCAM] == b"vanilla oncamera\r\nbytes \x00\x01 kept\r\n"
    assert eng.key(b"qm_rt", b"mfres") == b"1"
    W6.cmd(eng, "mfcopy")
    tick(eng)
    assert eng.key(b"qm_rt", b"mfres") == b"0"
    W6.cmd(eng, "esc")
    assert ui(eng, "panel") == b"0"


def test_the_writer_never_writes_outside_a_local_mod():
    eng = world()
    for d in (QM, WS, b"mods\\a\\b", b"mods\\..", b"data"):
        eng.set("qm_rt", mfreq=b"copy", mfdir=d, mfrel=ONCAM)
        tick(eng)
        assert eng.key(b"qm_rt", b"mfres") == b"0", d
    eng.set("qm_rt", mfreq=b"copy", mfdir=LOCAL, mfrel=b"..\\x")
    tick(eng)
    assert eng.key(b"qm_rt", b"mfres") == b"0"
