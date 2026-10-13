r"""Build the Quartermaster test mods (docs/plan.md section 4) into fixtures/<Name>/.

    python tools/fixtures.py            build all of them into <repo>/fixtures
    python tools/fixtures.py --check    exit 1 if fixtures/ differs from a fresh build

Never into the game's `mods\` folder: the game registers AND enables every folder
it finds there on its next start (docs/plan.md S13, S15), so a fixture is copied
in only for a test run, by tools/hrun.py, and removed afterwards. This script
refuses any output directory inside the game folder.

Every file is built from the pristine vanilla bytes of the installed game
(`<game>\data\...`) by byte substitution - read the bytes, replace one unique
byte sequence, keep the bytes - so BOM, encoding, CRLF and tabs are vanilla's own.

QMTestWASD is not written here. It is the WASD camera of SW: Frontline Protocol,
produced by that mod's own pure patch functions (`tools/swfp/patches/camera.py`:
`patch_registershortcuts`, `patch_oncamera`, `patch_hotkeysettings`,
`patch_hotkeys_cfg`, each `bytes -> PatchResult(data, steps)`), imported from the
reference mod's folder rather than copied, so the fixture is exactly what that
mod ships for this game version. Importing a module normally writes a
`__pycache__` next to it; the reference mod's folder is read-only here, so
bytecode writing is switched off before the import. Only the shortcut prefix
`swfpcamera` is renamed to `qmwasd`, so the fixture cannot collide with the
reference mod's own shortcuts.

The four mods and the edge each one exercises:

  QMTestWASD      4 files: registershortcuts.inc, oncamera.inc,
                  hotkeysettings.inc, game/var/hotkeys.cfg; marker `QMTEST wasd`
                  logged by RegisterShortcuts
  QMTestCamSpeed  oncamera.inc: keySpeed x6, `QMTEST camspeed` logged when
                  OnCamera runs in the main menu; registershortcuts.inc: one
                  extra harmless line. Touches two WASD files, no line near a
                  WASD edit: merges clean.
  QMTestConflict  oncamera.inc: the same `var bLeft` line WASD rewrites: exactly
                  one conflict.
  QMTestBroken    registershortcuts.inc: compiles alone, but its union with WASD
                  declares one identifier twice: the validator must reject it.
  QMTestCam2      only an about.cfg taking the camera slot (Phase B, M8)
  QMTestData*     formations.cfg and objcustom.cfg records for the data merge
                  (Phase B, M9); A6 / B6 go past the formation bound together
  QMTestWASD2     QMTestWASD with an about.cfg and its four keys read from the
                  Quartermaster settings (Phase B, M10); marker `QMTEST wasd2
                  keys` with the keys it registered. An alternative to
                  QMTestWASD, never loaded with it.
  QMTestMany      only an about.cfg: 40 settings under `group` lines, more
                  than the 32 a mod could declare until 0.1.5
"""
import argparse
import hashlib
import os
import shutil
import sys

# Before anything can import from the reference mod: its folder is game input
# and must not gain a __pycache__.
sys.dont_write_bytecode = True

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"
DEFAULT_OUT = os.path.join(REPO, "fixtures")
REFERENCE_MOD = "SW_Frontline_Protocol"

WASD = "QMTestWASD"
CAMSPEED = "QMTestCamSpeed"
CONFLICT = "QMTestConflict"
BROKEN = "QMTestBroken"
FIXTURES = (WASD, CAMSPEED, CONFLICT, BROKEN, "QMTestWASD2", "QMTestCam2", "QMTestDataA",
            "QMTestDataB", "QMTestDataA6", "QMTestDataB6",  # Phase B: build_wasd2, CAM2, build_data
            "QMTestMany")                                   # 0.1.6: many_about

REGISTERSHORTCUTS = "data/gui/menu.inc/registershortcuts.inc"
ONCAMERA = "data/gui/menu.inc/oncamera.inc"
HOTKEYSETTINGS = "data/gui/menu.inc/hotkeysettings.inc"
HOTKEYS_CFG = "data/game/var/hotkeys.cfg"

CRLF = b"\r\n"
CODE = b"      [*] = ;"

REFERENCE_PREFIX = b"swfpcamera"
FIXTURE_PREFIX = b"qmwasd"

# The key sequence and layout of <game>\mods\SW_Frontline_Protocol\mod.ini:1-23,
# a local mod the game registers and runs; the probe mods of 2026-09-27 used the
# same keys and were listed by ModLibraryGetData (log r5c.0.log:13-15). Empty
# values keep the space after '=' as that file does. Player-facing texts are
# placeholders (docs/plan.md, header).
MOD_INI = CRLF.join([
    b"section.begin",
    b"   publishedfileid = 0",
    b"   creatorappid = 0",
    b"   consumerappid = 0",
    b"   contentfolder = mods\\{name}",
    b"   previewfile = ",
    b"   ownersteamid = 0",
    b"   timecreated = 0",
    b"   timeupdated = 0",
    b"   visibility = 0",
    b"   banned = False",
    b"   title = {name}",
    b"   description[*] = ;TODO(owner)",
    b"   tags = ",
    b"   filename = {name}",
    b"   filesize = 0",
    b"   previewfilesize = 0",
    b"   url = ",
    b"   filetype = 0",
    b"   acceptedforuse = False",
    b"   changenote[*] = ;TODO(owner)",
    b"section.end",
    b"",
]) + CRLF


class FixtureError(RuntimeError):
    pass


def code_line(stmt):
    """One wrapped `.inc` code line, as vanilla spells them."""
    return CODE + stmt + CRLF


def replace_once(data, old, new, what):
    found = data.count(old)
    if found != 1:
        raise FixtureError("%s: expected 1 site, found %d" % (what, found))
    return data.replace(old, new)


def default_game():
    return os.environ.get("QM_GAME_DIR", DEFAULT_GAME)


def default_reference(game):
    return os.environ.get("QM_REFERENCE_MOD",
                          os.path.join(game, "mods", REFERENCE_MOD))


def vanilla(game, rel):
    with open(os.path.join(game, *rel.split("/")), "rb") as f:
        return f.read()


def mod_ini(name):
    return MOD_INI.replace(b"{name}", name.encode("ascii"))


def load_camera(reference):
    """`swfp.patches.camera` from the reference mod, without writing into it."""
    tools = os.path.join(reference, "tools")
    if not os.path.isfile(os.path.join(tools, "swfp", "patches", "camera.py")):
        raise FixtureError("reference mod not found: %s" % tools)
    for name in ("swfp", "c3kit"):
        mod = sys.modules.get(name)
        if mod is not None and not os.path.abspath(mod.__file__).startswith(
                os.path.abspath(tools)):
            raise FixtureError("a different '%s' is already imported: %s"
                               % (name, mod.__file__))
    sys.dont_write_bytecode = True
    sys.path.insert(0, tools)
    try:
        from swfp.patches import camera
    finally:
        sys.path.remove(tools)
    return camera


# ------------------------------------------------------------------ QMTestWASD
#: The first registration of the reference mod's block, after the rename.
#: The marker goes in front of it, inside WASD's own inserted block, so it adds
#: no hunk of its own.
WASD_FIRST_REGISTRATION = code_line(
    b"   RegisterGUIShortcutIgnoreShift(False, 'qmwasdleftr', 'A', filter, "
    b"'spiRepeat', 'OnCamera', 20);")
WASD_MARKER = code_line(b"   Log('QMTEST wasd');")


def build_wasd(game, reference):
    camera = load_camera(reference)
    patches = ((REGISTERSHORTCUTS, camera.patch_registershortcuts),
               (ONCAMERA, camera.patch_oncamera),
               (HOTKEYSETTINGS, camera.patch_hotkeysettings),
               (HOTKEYS_CFG, camera.patch_hotkeys_cfg))
    files = {}
    for rel, patch in patches:
        data = patch(vanilla(game, rel)).data
        files[rel] = data.replace(REFERENCE_PREFIX, FIXTURE_PREFIX)
    if files[REGISTERSHORTCUTS].count(FIXTURE_PREFIX) != 8:
        raise FixtureError("registershortcuts: expected 8 renamed shortcut names")
    files[REGISTERSHORTCUTS] = replace_once(
        files[REGISTERSHORTCUTS], WASD_FIRST_REGISTRATION,
        WASD_MARKER + WASD_FIRST_REGISTRATION, "wasd/marker")
    return files


# ------------------------------------------------------------- QMTestWASD2
#: QMTestWASD with its four keys as Quartermaster settings (plan G16, M10;
#: docs/authoring.md): an about.cfg declares them, and both files that name
#: a key read it from the named parser qm_settings (child `qmtestwasd2`),
#: falling back to A / D / W / S when Quartermaster is absent. Built from
#: QMTestWASD's bytes by byte substitution, so QMTestWASD itself - which the
#: Phase A merge tests rely on - stays as it is. It replaces the same files
#: as QMTestWASD: the two are alternatives, never loaded together.
WASD2 = "QMTestWASD2"
WASD2_KEYS = ((b"l", b"A", b"camera_left", b"Camera left"),
              (b"r", b"D", b"camera_right", b"Camera right"),
              (b"t", b"W", b"camera_up", b"Camera up"),
              (b"b", b"S", b"camera_down", b"Camera down"))
WASD2_ABOUT = CRLF.join(
    [b"# about.cfg of the Quartermaster test mod QMTestWASD2 (docs/authoring.md)",
     b"id = qmtestwasd2",
     b"name = QMTestWASD2",
     b"version = 2.0",
     b"type = mod",
     b"exclusive = camera"]
    + [b"setting = %s;key;%s;%s" % (sid, key, label) for _v, key, sid, label in WASD2_KEYS]) + CRLF


def _wasd2_read(prefix, load):
    """Code lines that set qmwasd<prefix><l|r|t|b> from qm_settings. With
    `load`, a missing parser is created from the settings file (the mod may
    run before Quartermaster's boot: RegisterShortcuts runs at start-up)."""
    p = b"qmwasd%sp" % prefix
    m = b"qmwasd%sm" % prefix
    lines = [b"   var qmwasd%s%s : String = '%s';" % (prefix, v, key) for v, key, _s, _l in WASD2_KEYS]
    lines.append(b"   var %s : Integer = ParserSelectByKey('qm_settings');" % p)
    if load:
        lines += [b"   if (%s=0) and (FileAge(GetAppSaveDirectoryPath+'quartermaster\\settings.cfg')<>-1) then" % p,
                  b"   begin",
                  b"      %s := ParserCreate('qm_settings');" % p,
                  b"      ParserLoadFromFileByHandle(%s, GetAppSaveDirectoryPath+'quartermaster\\settings.cfg');" % p,
                  b"   end;"]
    lines += [b"   var %s : Integer = 0;" % m,
              b"   if (%s<>0) then" % p,
              b"   %s := ParserSelectByHandleByKey(%s, 'qmtestwasd2');" % (m, p),
              b"   if (%s<>0) then" % m,
              b"   begin"]
    for v, _key, sid, _l in WASD2_KEYS:
        lines += [b"      if (ParserGetValueByKeyByHandle(%s, '%s')<>'') then" % (m, sid),
                  b"      qmwasd%s%s := ParserGetValueByKeyByHandle(%s, '%s');" % (prefix, v, m, sid)]
    lines.append(b"   end;")
    return b"".join(code_line(ln) for ln in lines)


def build_wasd2(wasd):
    rs, oc = wasd[REGISTERSHORTCUTS], wasd[ONCAMERA]
    rs = replace_once(rs, WASD_MARKER, WASD_MARKER + _wasd2_read(b"k", True)
                      + code_line(b"   Log('QMTEST wasd2 keys '+qmwasdkl+' '+qmwasdkr+' '+qmwasdkt+' '+qmwasdkb);"),
                      "wasd2/read")
    for v, key, _s, _l in WASD2_KEYS:
        n = rs.count(b"'%s', filter," % key)
        rs = rs.replace(b"'%s', filter," % key, b"qmwasdk%s, filter," % v)
        if n != 2:
            raise FixtureError("wasd2: key %s registered %d times, expected 2" % (key.decode(), n))
    first = code_line(b"var bLeft : Boolean = IsKeyDownByName('Left') or IsKeyDownByName('A');")
    # The evidence of a run: a move shortcut's call (tags 20-23; only in a
    # battle, the file's first lines leave the main menu) logs the key it
    # reads and where the camera looks (its target; GetCameraPosition read a
    # constant in run m10b), so the log shows the camera moving
    # under the key the settings named.
    camera_log = b"".join(code_line(ln) for ln in (
        b"   if (tag>=20) and (tag<=23) then",
        b"   begin",
        b"      var qmwasdcx : Float;",
        b"      var qmwasdcy : Float;",
        b"      var qmwasdcz : Float;",
        b"      GetCameraTargetPosition(qmwasdcx, qmwasdcy, qmwasdcz);",
        b"      Log('QMTEST wasd2 camera tag='+IntToStr(tag)+' '+qmwasdol+'='+BoolToStr(IsKeyDownByName(qmwasdol))+' x='+FloatToStr(qmwasdcx)+' z='+FloatToStr(qmwasdcz));",
        b"   end;"))
    oc = replace_once(oc, first, _wasd2_read(b"o", False) + camera_log + first, "wasd2/oncamera")
    for v, key, _s, _l in WASD2_KEYS:
        oc = replace_once(oc, b"IsKeyDownByName('%s')" % key, b"IsKeyDownByName(qmwasdo%s)" % v,
                          "wasd2/oncamera %s" % key.decode())
    files = dict(wasd)
    files[REGISTERSHORTCUTS] = rs
    files[ONCAMERA] = oc
    files["about.cfg"] = WASD2_ABOUT
    return files


# --------------------------------------------------------------- QMTestCam2
#: A second camera mod for the about.cfg rules (plan G15b, M8): no game file
#: at all, only an about.cfg that takes the `camera` slot, so with QMTestWASD2
#: active the manager refuses to activate it, and with both enabled the boot
#: reports the clash.
CAM2 = "QMTestCam2"
CAM2_ABOUT = CRLF.join([b"# about.cfg of the Quartermaster test mod QMTestCam2 (docs/authoring.md)",
                        b"id = qmtestcam2",
                        b"exclusive = camera"]) + CRLF


# --------------------------------------------------------------- QMTestMany
#: More settings than the 32 a mod could declare until 0.1.5, under `group`
#: lines (docs/authoring.md): no game file, only an about.cfg. 40 settings
#: s0 ... s39 - two before any group, then groups of 6, 12 (longer than a
#: page), 9 and 11, the last one holding every setting past the old limit:
#: five entries in the Options view's list of groups, and seven pages for all
#: of them together. Switch, `-` / `+` and `<` / `>` only: no key setting, so
#: no key of the player's game can meet one.
MANY = "QMTestMany"
MANY_GROUPS = ((b"", 2), (b"Match interface", 6), (b"Economy and trade", 12), (b"Camera", 9),
               (b"Past the old limit of 32", 11))


def many_about():
    lines = [b"# about.cfg of the Quartermaster test mod QMTestMany (docs/authoring.md)",
             b"id = qmtestmany",
             b"name = QMTestMany"]
    k = 0
    for title, count in MANY_GROUPS:
        if title:
            lines.append(b"group = " + title)
        for _ in range(count):
            if k % 10 == 1:
                lines.append(b"setting = s%d;int;3;Setting %d, a number;1..5" % (k, k))
            elif k % 10 == 7:
                lines.append(b"setting = s%d;choice;mid;Setting %d, a choice;low|mid|high" % (k, k))
            else:
                lines.append(b"setting = s%d;bool;1;Setting %d, a switch" % (k, k))
            k += 1
    return CRLF.join(lines) + CRLF


# ------------------------------------------------------------ QMTestData*
#: The data merge (plan S3, S10; M9). Each mod adds one formation - a copy of
#: vanilla's LINE3 record under a new id, so it is a formation the loader can
#: read - and changes one objcustom.cfg record (a building's decal scale):
#: A the first record (ausbar), B the second (swetem). Merged, the game reads
#: 151 formations and both changes; A6 / B6 add six formations each, 161
#: together, past gc_formation_maxcount = 160 (init.script:9-11): the merge
#: fails and B6's file, the winner's, stays in effect.
DATA_A, DATA_B, DATA_A6, DATA_B6 = "QMTestDataA", "QMTestDataB", "QMTestDataA6", "QMTestDataB6"
FORMATIONS_CFG = "data/game/var/formations.cfg"
OBJCUSTOM_CFG = "data/game/var/objcustom.cfg"


def _formation(game, ident):
    """Vanilla's LINE3 record with the id `ident`, CRLF lines."""
    data = vanilla(game, FORMATIONS_CFG)
    start = data.index(b"      id = LINE3\r\n")
    start = data.rindex(b"\r\n   [*] : struct.begin\r\n", 0, start) + 2
    # The record's own end: at the start of a line, indent 3 - the nested
    # `mask` ends with `      struct.end`, which holds the same text further in.
    end = data.index(b"\r\n   struct.end\r\n", start) + len(b"\r\n   struct.end\r\n")
    return data[start:end].replace(b"      id = LINE3\r\n", b"      id = " + ident + b"\r\n")


def _with_formations(game, idents):
    data = vanilla(game, FORMATIONS_CFG)
    tail = b"section.end"
    if data.count(tail) != 1:
        raise FixtureError("formations.cfg: expected one section.end")
    return data.replace(tail, b"".join(_formation(game, i) for i in idents) + tail)


def _decal(game, sid, old, new):
    """objcustom.cfg with the first `scale = <old>` after `sid = <sid>` changed."""
    data = vanilla(game, OBJCUSTOM_CFG)
    at = data.index(b"      sid = " + sid + b"\r\n")
    hit = data.index(b"         scale = " + old + b"\r\n", at)
    return data[:hit] + b"         scale = " + new + b"\r\n" + data[hit + len(b"         scale = " + old + b"\r\n"):]


def build_data(game):
    return {
        DATA_A: {FORMATIONS_CFG: _with_formations(game, [b"QMDATAA"]),
                 OBJCUSTOM_CFG: _decal(game, b"ausbar", b"16.0", b"17.0")},
        DATA_B: {FORMATIONS_CFG: _with_formations(game, [b"QMDATAB"]),
                 OBJCUSTOM_CFG: _decal(game, b"swetem", b"20", b"21")},
        DATA_A6: {FORMATIONS_CFG: _with_formations(game, [b"QMDATAA%d" % i for i in range(6)])},
        DATA_B6: {FORMATIONS_CFG: _with_formations(game, [b"QMDATAB%d" % i for i in range(6)])},
    }


# -------------------------------------------------------------- QMTestCamSpeed
#: oncamera.inc:4-5 exit in the main menu. The marker replaces the `exit;` with a
#: block that logs first - the shape probe 5 verified in-game (mod B, log
#: r5c.1.log:25) - so it prints only when OnCamera runs in the main menu (an
#: arrow key there, or the harness calling it) and never floods a battle log.
CAMSPEED_EXIT = (code_line(b"exit;"),
                 code_line(b"begin Log('QMTEST camspeed'); exit; end;"))
#: oncamera.inc:10.
CAMSPEED_SPEED = (code_line(b"var keySpeed : Float = gProfile.keyscrollspeed*4;"),
                  code_line(b"var keySpeed : Float = gProfile.keyscrollspeed*6;"))
#: registershortcuts.inc:4, the first code line. A statement in front of the first
#: `var` compiles (vanilla oncamera.inc:4-7 does the same), and `Log` only adds a
#: line to the game log (vanilla docreate.inc:6 logs the same way), so the line
#: changes no behaviour. It sits 14 code lines above WASD's first insertion (after
#: :17) and far from its second (after :199), so the two never overlap and are
#: not even within the 3-line proximity window.
CAMSPEED_TOP = code_line(b"var filter : String;")
CAMSPEED_LINE = code_line(b"Log('QMTEST camspeed registershortcuts');")


def build_camspeed(game):
    oc = vanilla(game, ONCAMERA)
    oc = replace_once(oc, CAMSPEED_EXIT[0], CAMSPEED_EXIT[1], "camspeed/exit")
    oc = replace_once(oc, CAMSPEED_SPEED[0], CAMSPEED_SPEED[1], "camspeed/speed")
    rs = replace_once(vanilla(game, REGISTERSHORTCUTS), CAMSPEED_TOP,
                      CAMSPEED_LINE + CAMSPEED_TOP, "camspeed/registershortcuts")
    return {ONCAMERA: oc, REGISTERSHORTCUTS: rs}


# -------------------------------------------------------------- QMTestConflict
#: oncamera.inc:18, the first of the four lines WASD rewrites. A trailing comment
#: changes the line's text but not its meaning, so whichever side wins still
#: compiles and runs.
CONFLICT_LINE = (code_line(b"var bLeft : Boolean = IsKeyDownByName('Left');"),
                 code_line(b"var bLeft : Boolean = IsKeyDownByName('Left'); "
                           b"// QMTEST conflict"))


def build_conflict(game):
    oc = replace_once(vanilla(game, ONCAMERA), CONFLICT_LINE[0], CONFLICT_LINE[1],
                      "conflict/bLeft")
    return {ONCAMERA: oc}


# ---------------------------------------------------------------- QMTestBroken
#: WHY THE UNION CANNOT COMPILE. WASD's re-seat block declares
#: `var swfp_seat : String;` inside the hotkey loop of registershortcuts.inc,
#: right after `var action` (vanilla :199). This mod declares `SWFP_SEAT` in the
#: same `begin ... end` block, in front of `var pHotkey` (vanilla :196). Script
#: identifiers are case-insensitive, and two declarations of one name in a state
#: are a compile error ("array M + var m" -> Compile script error,
#: docs/research/context-2026-09-27.md section 3). Each file alone compiles: the
#: line is an unused local here, and WASD alone has one declaration. The two
#: edits are four vanilla lines apart - no overlap, no proximity - so the merge
#: classifier calls the union clean and only the validator can catch it.
BROKEN_ANCHOR = code_line(
    b"   var pHotkey : Integer = ParserSelectByHandleByIndex(pHotkeys, i);")
BROKEN_LINE = code_line(b"   var SWFP_SEAT : Integer = 0; "
                        b"// QMTEST broken: same identifier as swfp_seat in QMTestWASD")


def build_broken(game):
    rs = replace_once(vanilla(game, REGISTERSHORTCUTS), BROKEN_ANCHOR,
                      BROKEN_LINE + BROKEN_ANCHOR, "broken/registershortcuts")
    return {REGISTERSHORTCUTS: rs}


# ---------------------------------------------------------------------- build
def build_all(game=None, reference=None):
    """`{name: {relpath: bytes}}` for all four fixtures, mod.ini included."""
    game = game or default_game()
    reference = reference or default_reference(game)
    wasd = build_wasd(game, reference)
    mods = {
        WASD: wasd,
        CAMSPEED: build_camspeed(game),
        CONFLICT: build_conflict(game),
        BROKEN: build_broken(game),
        WASD2: build_wasd2(wasd),
        CAM2: {"about.cfg": CAM2_ABOUT},
        MANY: {"about.cfg": many_about()},
    }
    mods.update(build_data(game))
    for name, files in mods.items():
        files["mod.ini"] = mod_ini(name)
    return mods


def _inside(path, root):
    path, root = os.path.normcase(os.path.realpath(path)), os.path.normcase(
        os.path.realpath(root))
    return os.path.commonpath([path, root]) == root


def write(mods, out, game=None):
    """Write `mods` under `out`, replacing each fixture folder as a whole."""
    game = game or default_game()
    if _inside(out, game):
        raise FixtureError("refusing to write inside the game folder: %s" % out)
    os.makedirs(out, exist_ok=True)
    for name, files in mods.items():
        if name not in FIXTURES:
            raise FixtureError("not a fixture name: %s" % name)
        target = os.path.join(out, name)
        if os.path.isdir(target):
            shutil.rmtree(target)
        for rel, data in sorted(files.items()):
            path = os.path.join(target, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)


def read_tree(root):
    """`{relpath: bytes}` of every file under `root` (for --check and tests)."""
    out = {}
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            path = os.path.join(dirpath, n)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, "rb") as f:
                out[rel] = f.read()
    return out


def check(mods, out):
    """Differences between a fresh build and what is on disk under `out`."""
    problems = []
    for name, files in mods.items():
        disk = read_tree(os.path.join(out, name))
        for rel in sorted(set(files) | set(disk)):
            if files.get(rel) != disk.get(rel):
                problems.append("%s/%s" % (name, rel))
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--game", default=None)
    ap.add_argument("--reference", default=None)
    ap.add_argument("--check", action="store_true",
                    help="compare with a fresh build instead of writing")
    args = ap.parse_args(argv)
    game = args.game or default_game()
    mods = build_all(game, args.reference)
    if args.check:
        problems = check(mods, args.out)
        for p in problems:
            print("differs: %s" % p)
        print("fixtures %s" % ("out of date" if problems else "up to date"))
        return 1 if problems else 0
    write(mods, args.out, game)
    for name, files in mods.items():
        for rel, data in sorted(files.items()):
            print("%-15s %-42s %7d %s" % (name, rel, len(data),
                                          hashlib.sha256(data).hexdigest()[:16]))
    print("wrote %d fixtures into %s" % (len(mods), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
