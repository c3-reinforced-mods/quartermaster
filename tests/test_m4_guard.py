r"""The write guard (plan S7, G12): nothing reaches Quartermaster's data mirror
unless it passed validation. Checked on the Pascal sources:

- the mirror's root (qmWrBase) is named in src/lib/qmwrite.pas only, and every
  write there goes to qmWrBase + a relative path: qmWrOutput after its
  validation check, qmWrManifest to the one manifest path, qmWrDelete after
  the path check and never on a hook file;
- in every other source, no file-writing call gets a path built from what
  points into a mod folder or the game folder: a `data\` literal, the qm_rt
  key `qmdir`, GetApplicationFileName, or qmWrHookDir (a taint check over
  assignments, flow-insensitive, so it errs on the side of a finding);
- Copy, Move and Rename are used nowhere (plan S9, capability probe 1).
The checks are shown to catch planted violations.
"""
import os
import re

import pytest

import hbuild as H
from ref.planner import HOOK_FILES

SRC = os.path.join(H.REPO, "src")
WRITER = "src/lib/qmwrite.pas"

#: File-writing natives and routines, and the argument that names the file.
SINKS = {"openfilestreamforwrite": (0,), "openfilewrite": (0,),
         "parsersavetofilebyhandle": (1,), "copyfilestream": (0, 1),
         "movefilestream": (0, 1), "renamefilestream": (0, 1), "deletefilestream": (0,),
         "qmrawwrite": (0,), "qmrawwritestr": (0,), "qmincbegin": (0,), "qmincrender": (0,),
         "qmvalstage": (0,), "qmvalwrap": (0,), "qmmgoutbegin": (0,)}
#: The merge writes where qm_mg_in's `out` / `dump` say (qmmerge.pas).
KEY_SINK = re.compile(r"(?:out|dump)'\s*$", re.I)
SOURCES = re.compile(r"GetApplicationFileName|'qmdir'|qmWrBase|qmWrDst|qmWrHookDir|'[^']*data\\[^']*'",
                     re.I)


def sources():
    out = {}
    for sub in ("lib", "states", "screens", "hooks"):
        folder = os.path.join(SRC, sub)
        for fn in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            if fn.endswith(".pas"):
                with open(os.path.join(folder, fn), "rb") as fh:
                    out["src/%s/%s" % (sub, fn)] = fh.read().decode("ascii")
    return out


def code_of(text):
    """The Pascal of a template: the body, without `//` and `{ }` comments
    (strings kept)."""
    body = text.split("\n---\n", 1)[1] if "\n---\n" in text else text
    out, i, n = [], 0, len(body)
    while i < n:
        c = body[i]
        if c == "'":
            j = i + 1
            while j < n and body[j] != "'":
                j += 1
            out.append(body[i:j + 1])
            i = j + 1
        elif body.startswith("//", i):
            while i < n and body[i] != "\n":
                i += 1
        elif c == "{":
            while i < n and body[i] != "}":
                i += 1
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def calls(code, name):
    """`(offset, [argument texts])` of every call of `name` (case-insensitive)."""
    found = []
    for m in re.finditer(r"\b%s\s*\(" % re.escape(name), code, re.I):
        depth, j, start, args, quote = 1, m.end(), m.end(), [], False
        while j < len(code) and depth:
            c = code[j]
            if c == "'":
                quote = not quote
            elif not quote:
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                    if depth == 0:
                        args.append(code[start:j].strip())
                elif c == "," and depth == 1:
                    args.append(code[start:j].strip())
                    start = j + 1
            j += 1
        found.append((m.start(), args))
    return found


_ASSIGN = re.compile(r"\b(qm\w+)\s*(?:\[[^\]]*\])?\s*:=\s*([^;]*);|"
                     r"\bvar\s+(qm\w+)\s*:\s*\w+\s*=\s*([^;]*);", re.I)


def tainted(code):
    """Variables that may hold a path into a mod folder or the game folder:
    assigned from a source or from another such variable, and the var
    argument of qmWrHookDir."""
    bad = set(m[0].lower() for m in (a for _o, a in calls(code, "qmWrHookDir")) if m)
    pairs = [((m.group(1) or m.group(3)).lower(), m.group(2) or m.group(4))
             for m in _ASSIGN.finditer(code)]
    while True:
        more = set(v for v, rhs in pairs if v not in bad and (
            SOURCES.search(rhs) or any(re.search(r"\b%s\b" % b, rhs, re.I) for b in bad)))
        if not more:
            return bad
        bad |= more


def findings(files):
    """`[(file, sink, argument)]`: writes whose file name may point into a mod
    folder or the game folder, outside the writer."""
    out = []
    for path, text in sorted(files.items()):
        if path == WRITER:
            continue
        code = code_of(text)
        bad = tainted(code)

        def dirty(arg):
            return SOURCES.search(arg) or any(re.search(r"\b%s\b" % b, arg, re.I) for b in bad)

        for sink, positions in SINKS.items():
            for _off, args in calls(code, sink):
                for k in positions:
                    if k < len(args) and dirty(args[k]):
                        out.append((path, sink, args[k]))
        for _off, args in calls(code, "ParserSetValueByKeyByHandle"):
            if len(args) == 3 and KEY_SINK.search(args[1]) and dirty(args[2]):
                out.append((path, "qm_mg_in " + args[1], args[2]))
    return out


def test_no_source_but_the_writer_writes_into_a_mod_or_the_game_folder():
    files = sources()
    assert WRITER in files and "src/states/qmwritegen.pas" in files
    assert findings(files) == []


def test_the_check_catches_planted_writes():
    files = sources()
    base = files["src/states/qmreport.pas"]
    planted = [
        "OpenFileStreamForWrite(ExtractFilePath(GetApplicationFileName)+'data\\gui\\x.inc');",
        "var qmZz : String = ParserGetValueByKeyByHandle(ParserSelectByKey('qm_rt'), 'qmdir');\n"
        "var qmZy : String = qmZz+'\\data\\';\nqmRawWriteStr(qmZy+'gui\\x.inc', 'x');",
        "qmWrHookDir(qmZx);\nqmIncBegin(qmZx+'a.inc', qmReHd, 0, 0);",
        "DeleteFileStream('.\\data\\gui\\menu.inc\\oncamera.inc');",
        "ParserSetValueByKeyByHandle(qmZw, 'j0out', qmReApp+'mods\\Quartermaster\\data\\x.inc');\n"
        "var qmReApp : String = ExtractFilePath(GetApplicationFileName);",
        "ParserSaveToFileByHandle(qmReRep, qmWrBase+'x.cfg');",
    ]
    for line in planted:
        got = findings({"src/states/qmreport.pas": base + "\n" + line + "\n"})
        assert got, line


def test_the_writer_writes_only_under_its_root_and_only_after_validation():
    code = code_of(sources()[WRITER])
    for name, files in sources().items():
        if name != WRITER:
            assert "qmwrbase" not in code_of(files).lower(), name
            assert "qmwrdst" not in code_of(files).lower(), name
    routines = dict((m.group(1).lower(), m.start()) for m in
                    re.finditer(r"^(?:function|procedure)\s+(\w+)", code, re.M))
    order = sorted(routines.items(), key=lambda kv: kv[1])

    def body(name):
        start = routines[name.lower()]
        later = [o for _n, o in order if o > start]
        return code[start:later[0] if later else len(code)]

    for sink in SINKS:
        for off, args in calls(code, sink):
            owner = max((n for n, o in order if o <= off), key=lambda n: routines[n])
            path = args[SINKS[sink][0]] if args else ""
            # qmWrDataOut (Phase B, M9) writes the data files of the record
            # merge; qmWrNewMod, qmWrCopyVanilla and qmWrAboutDraft (M11) the
            # player's own local mod folders, each after its own checks (below).
            assert owner in ("qmwroutput", "qmwrdelete", "qmwrmanifest", "qmwrdataout",
                             "qmwrnewmod", "qmwrcopyvanilla", "qmwraboutdraft"), (sink, owner)
            if owner == "qmwrnewmod":
                assert path.startswith("qmWnDir+"), (sink, path)
            elif owner == "qmwrcopyvanilla":
                assert path in ("qmWvDst", "qmWvSrc"), (sink, path)
            elif owner == "qmwraboutdraft":
                assert path.startswith("qmWbDir+"), (sink, path)
            else:
                assert path.startswith("qmWrDst") or path == "qmWtTarget", (sink, path)
    out = body("qmWrOutput")
    assert "qmWtTarget := qmWrDst+qmWtRel;" in out
    assert out.index("qmValCheck(") < out.index("qmIncBegin(")
    assert out.index("qmWrCheckPath(") < out.index("qmIncBegin(")
    # The data gate: the path is one of the four data files, and qm_val
    # d<seq> holds the token of exactly the lines written (set by qmDataMerge
    # after its checks and the engine parser's trial load).
    data = body("qmWrDataOut")
    assert data.index("qmWrCheckData(") < data.index("qmRawWrite(")
    assert data.index("'d'+IntToStr(qmWdSeq)") < data.index("qmRawWrite(")
    assert data.index("qmWdFlag := 1") < data.index("qmRawWrite(")
    manifest = body("qmWrManifest")
    assert manifest.count("qmWrDst+'quartermaster\\state\\manifest.cfg'") == 2
    new = body("qmWrNewMod")
    assert new.index("qmWrFolderOk(") < new.index("qmRawWriteStr(")
    assert new.index("SameText(qmWnD, qmWnDir)") < new.index("qmRawWriteStr(")
    assert new.index("if (not qmWnOk) then") < new.index("qmRawWriteStr(")
    copy = body("qmWrCopyVanilla")
    assert copy.index("qmWrLocalDir(") < copy.index("OpenFileStreamForWrite(")
    assert copy.index("FileAge(qmWvDst)<>-1") < copy.index("OpenFileStreamForWrite(")
    # the target's folders exist before the copy (a copy into a missing
    # folder raises, capability probe 1)
    assert copy.index("OpenFileStreamForWrite(qmWvDst)") < copy.index("CopyFileStream(")
    draft = body("qmWrAboutDraft")
    assert draft.index("qmWrLocalDir(") < draft.index("qmRawWriteStr(")
    delete = body("qmWrDelete")
    assert delete.index("qmWrCheckPath(") < delete.index("DeleteFileStream(")
    assert delete.index("qmWrCheckData(") < delete.index("DeleteFileStream(")
    assert delete.index("not qmWrIsHook(") < delete.index("DeleteFileStream(")


def test_the_writers_hook_list_is_the_planners():
    code = code_of(sources()[WRITER])
    m = re.search(r"StrPos\('\|'\+qmWhRel\+'\|', '\|([^']*)\|'\)", code)
    assert m and m.group(1).encode().split(b"|") == list(HOOK_FILES)


def test_no_copy_move_or_rename():
    """Copy and Move raise when the target folder is missing (capability
    probe 1), Rename does not replace. The one copy is Edit game file's
    (qmWrCopyVanilla, M11): a byte-for-byte copy of a game file, binary ones
    too, into a folder a stream write has just made."""
    for name, text in sources().items():
        code = code_of(text).lower()
        for native in ("movefilestream", "renamefilestream"):
            assert native not in code, (name, native)
        if name == WRITER:
            assert code.count("copyfilestream") == 1
        else:
            assert "copyfilestream" not in code, (name, "copyfilestream")


def test_the_s2_inc_files_the_writer_names_are_the_builds():
    code = code_of(sources()[WRITER])
    named = set(re.findall(r"qmWcRel<>'([^']*)'", code))
    s2 = set(p.replace("/", "\\") for p in H.S2_FILES if p.endswith(".inc"))
    assert named == s2
