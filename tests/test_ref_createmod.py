"""Gates for ref.createmod (plan G17; M11): the folder a typed name makes,
the new mod's files byte for byte, and that its mod.ini has the layout of
the local mods here."""
import os

from ref import about as A
from ref import createmod as C

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"


def test_the_folder_a_name_makes():
    assert C.folder_of(b"My new mod!") == b"My_new_mod"
    assert C.folder_of(b"  2nd try") == b"nd_try"            # a letter first
    assert C.folder_of(b"???") == b""
    assert C.folder_of(b"Pr\xc3\xb3ba") == b"Prba"           # non-ASCII dropped
    assert C.folder_of(b"x" * 60) == b"x" * 40


def test_mod_ini_has_the_layout_of_a_local_mod():
    mine = C.mod_ini(b"My_new_mod", b"My new mod!")
    assert mine.endswith(b"section.end\r\n\r\n")
    keys = [ln.split(b" = ")[0] for ln in mine.split(b"\r\n")[1:-3]]
    for local in ("SW_Frontline_Protocol", "UnofficialPatch"):
        path = os.path.join(GAME, "mods", local, "mod.ini")
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as fh:
            theirs = fh.read()
        lines = theirs.replace(b"\r\n", b"\n").split(b"\n")
        # A mod uploaded with a text of several lines has it as a struct
        # (`key : struct.begin`, a `[*]` line each, `struct.end`): the same
        # key as the one-line `key[*]` a new mod starts with.
        theirs_keys, inside = [], False
        for ln in lines[1:lines.index(b"section.end")]:
            if ln.endswith(b" : struct.begin"):
                theirs_keys.append(ln[:-len(b" : struct.begin")] + b"[*]")
                inside = True
            elif inside:
                inside = ln.strip() != b"struct.end"
            else:
                theirs_keys.append(ln.split(b" = ")[0])
        assert theirs_keys == keys
    assert b"   contentfolder = mods\\My_new_mod\r\n" in mine
    assert b"   title = My new mod!\r\n" in mine and b"   filename = My_new_mod\r\n" in mine


def test_the_about_cfg_reads_back_as_declared():
    a = A.parse(C.about_cfg(b"My_new_mod", b"My new mod!", b"totalConversion", b"camera"))
    assert a.problems == [] and (a.id, a.type, a.exclusive) == (b"my_new_mod", b"totalconversion",
                                                                 [b"camera"])
    b = A.parse(C.about_cfg(b"Plain", b"Plain"))
    assert b.problems == [] and (b.type, b.exclusive) == (b"mod", [])


def test_the_three_files():
    f = C.files(b"My_new_mod", b"My new mod!")
    assert sorted(f) == [b"about.cfg", b"data\\readme.txt", b"mod.ini"]
    assert all(v.endswith(b"\r\n") and v.count(b"\n") == v.count(b"\r\n") for v in f.values())
