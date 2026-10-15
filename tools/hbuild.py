r"""Build the Quartermaster mod folder from `src/**/*.pas`.

    python tools/hbuild.py                 build dist/Quartermaster, lint every state
    python tools/hbuild.py --vanilla-idx   ... and regenerate data/quartermaster/vanilla.idx
    python tools/hbuild.py --check         build in memory; exit 1 if dist/Quartermaster differs
    python tools/hbuild.py --offline       skip the lints that need the installed game
    python tools/hbuild.py --deploy   [--dry-run] [--game-dir G] [--save-dir S]
    python tools/hbuild.py --undeploy [--dry-run] [--game-dir G] [--save-dir S]

Exit status: 0 on success, 1 on lint findings or a --check difference, 2 on a
refused or malformed request.

----------------------------------------------------------------- the sources

    src/states/*.pas   one engine state per file
    src/lib/*.pas      helpers, inlined into every state that names them
    src/hooks/*.pas    hook lines, inserted into a copy of a vanilla file
    src/screens/*.pas  GUI states Quartermaster adds to the GUI machine at run
                       time (docs/ui.md): a state template with `screen:`
                       in place of `state:`, named Show<Qm...> or Event<Qm...>
                       and emitted as a one-state `.inc` into
                       data/quartermaster/ui/<name in lower case>.inc

A template is front matter, a line reading exactly `---`, and a body:

    state: qmHello                      states only: the state's name
    into: data/quartermaster/core.aix   states only: the file it is emitted into
    helpers: qmlog                      src/lib names to inline, comma separated
    requires: version                   build variables the body uses
    ---
    //! a note for whoever reads the template; never emitted
    // an engine comment; emitted
    qmLog('hello, version '+${version});

Every key a kind takes is mandatory and none has a default; an unknown,
missing or duplicate key, a missing `---`, trailing whitespace on a body line,
a byte outside printable ASCII (tab allowed), a `${`, `$(` or `$[` that is not
a well-formed `${name}`, a variable used but not declared, declared but not
used, or declared but unknown to the build: all of them stop the build with
`<template>:<line>`. A placeholder alone on its line is a block (each value
line takes that line's indent); inside a line its value must be one line. A
bare `$` is left alone because Pascal spells hex literals `$FF`. The rules
are those of the template renderer in the reference mod's tooling, so a
template reads the same in both projects.

Build variables are Pascal expressions, not text: `qstr()` turns a Python
string into a quoted literal with every `'` doubled, which is the only way a
value containing a quote can be spliced into a string literal.

Each state compiles alone and procedures in an `.inc` are file-local (the
engine loads no library of ours), so a helper is copied into every state that
names it, dependencies first, each once, followed by one empty code line.

-------------------------------------------------------------- the containers

Both shapes are the installed game's own, and the tests rebuild a vanilla
file of each shape from its code lines and compare the bytes:

  one-state `.inc`   `section.begin` / `   Name = X` / `   Code : struct.begin`
                     / one `      [*] = ;<code>` line per code line /
                     `   struct.end` / `section.end` / an empty line, all CRLF
                     (data/gui/menu.inc/cameracontrol.inc:1-38; 272 of the 313
                     vanilla .inc open this way, 278 end this way).
  multi-state `.aix` per state `section.begin` / `   Name = X` /
                     `   UsedFileName = ` / `   Code : struct.begin` / code
                     lines / `   struct.end` / `section.end` / an empty line;
                     then `section.begin` / `   CurrentState = ` /
                     `   SaveVariables = False` / `section.end` / an empty line
                     (data/maps/missions/rusmis1.aix:1-26). The runtime-loaded
                     `.aix` files of the capability probes had this shape and
                     loaded through StateMachineLoadFromFile.

States of one `.aix` are sorted by name, so the output does not depend on the
order the files are listed in.

---------------------------------------------------------------------- hooks

A hook template takes two keys and no helpers:

    hook: data/gui/menu.inc/cameracontrol.inc   the vanilla file it goes into
    requires:
    ---
    <the hook lines>

The emitted file is the installed game's own bytes of that file with the hook
lines inserted, each as a `      [*] = ;<line>` code line, in front of the Code
value `ref.inc.hook_index` names: the first top-level line after the routines
the state starts with, or the first line when it starts with none (plan S5;
cameracontrol.inc: `const cTagLeft = 20;`, value 8). The same rule places the
hook lines in merged output, so their position never changes between
generations. Nothing else is touched: the bytes before and after the insertion
point are vanilla's, so BOM, CRLF, tabs and every other byte survive. A target
must be one of the hook files of plan S5 (`HOOK_FILES`, which comes from
ref/planner.py - the one list) and a one-state `.inc` with a Code struct.

Each hook's lines are also emitted alone, as the one-state `.inc`
data/quartermaster/hooks/<file name> named like the vanilla state: the
generator merges them into every generated copy of the hook file (the hooked
copy under gui/menu.inc/ is itself an output a generation overwrites, so the
lines need a home of their own).

`${hookgen}` is the generation constant of plan S6 in the CameraControl hook:
the value the generator writes when Quartermaster is the only mod
(ref/validate.py alone_outputs_hash over every shipped hook file, vanilla plus
its hook lines, in vanilla.idx order). With it the shipped copies are exactly
what a first generation of Quartermaster alone produces, so that generation
changes no file and needs no restart. The constant's own line never enters
the hash, so the hooks are rendered once with a placeholder to compute it.

Hook lines run inside a vanilla state on every call of it, so plan S5 limits
them, and the build checks it (lints below): at most HOOK_MAX_LINES lines, no
`global` declarations, every name they use an engine native, an engine
constant or variable or a dmscript.global name (never a library routine
another mod could replace), and every name they declare prefixed `qm`. The
rest of the state is vanilla's and is linted only for what the hook could
break: block balance, and a hook name colliding with a vanilla one.

------------------------------------------------------------------- the lints

Compile errors in this engine name only the state ("Compile script error:
<State>"), so the lints are the only debugger. Every state is linted alone, the
way the engine compiles it; every finding is data (`Finding`) and the build
fails on any of them.

  gscript-*     the vendored parser (tools/vendor/gscript.py): block, bracket
                and container balance; a const used above its declaration;
                identifiers that resolve nowhere (natives read out of
                cossacks.exe, dmscript.global, the vanilla libraries); literals
                or const parameters handed to a `var` parameter. The last two
                need the installed game and are skipped with --offline.
  duplicate     a name declared twice in one state, compared case-insensitively
                (the language is case-insensitive: an array `M` and a var `m`
                in one state failed to compile in a probe).
  prefix        a declared name that does not start with `qm` (vanilla has no
                identifier with that prefix, so ours can never shadow one).
  chr           any use of `Chr`: it is registered as a native but does not
                compile in any form; use a character table instead.
  array-budget  the elements of every array a state declares, summed per state:
                String arrays at most 200 000 (1M took 15 s to allocate),
                every other element type at most 1 000 000 (1M Integer is fine,
                4M crashed the whole game). A bound that cannot be evaluated
                from literals and constants is a finding too. A `var`
                parameter of array type allocates nothing - it is the
                caller's array, passed by reference (verified in-game) - so it
                is not counted.
  string-function  a nested `function ... : String` in state code: it does
                not compile at state level (capability probes 2026-09-28,
                docs/research/m0-probes.md probe 4); return a String through
                a `var` parameter instead. The one such function in vanilla
                state code, gui/menu.inc/shownews.inc:305, sits inside a
                `{ }` comment.
  open-array    `array of`: open and dynamic arrays do not compile (same
                probe); every array has fixed bounds.
  char-join     a char literal next to another literal without `+` (`#13#10`,
                `'a'#9`): no vanilla line writes one, and the only state that
                did (qmCaseIncProbe, run m2a2) failed to compile; every
                vanilla char literal is joined with `+` (`#34+gamename+#34`,
                data/gui/menu.inc/eventcreatejoinroom.inc:118).
  no-routine    a call of `High`, `Length` or `SetLength`: none compiles
                (same probe). cossacks.exe registers no routine of those
                names - the String length is `function StrLength(const str:
                String): Integer` - and no vanilla `.inc` or `.script` calls
                one.
  container     an emitted file that is not all CRLF or not printable ASCII.

--------------------------------------------------------------- vanilla.idx

`data/quartermaster/vanilla.idx` lists every file under `<G>\data` for the
in-game mod index, which checks `FileAge(<mod dir>\data\<path>)` over it.

Format. The file has exactly the shape of a one-state `.inc`, because that is
the file shape whose engine-parser round trip the probes verified byte for
byte, and Quartermaster's own `.inc` reader therefore reads it unchanged:

    section.begin
       Name = qmVanillaIndex
       Format = 1
       Count = <number of entries>
       Code : struct.begin
          [*] = ;<path>|<size>|<lines>|<class>
       struct.end
    section.end
    <empty line>

The two extra keys between `Name` and `Code` follow the vanilla `.aix`
sections, which carry keys there too (rusmis1.aix:2-4). One entry per file,
sorted by path, CRLF, no timestamp, so the same game gives the same bytes.

  path    relative to `data\`, lower case, backslashes: game scripts address
          files with backslashes (`UsedFileName = .\data\scripts\user\user.inc\
          resetdefaults.inc`, data/scripts/user/user.aix:4; `dir = mods\...`,
          mods/mods.ini:4) and file lookups are case-insensitive while string
          comparison in a script is not, so one spelling is fixed here.
  size    bytes.
  lines   line terminators (LF) plus one for a final unterminated line;
          -1 for a binary file. A file is binary when it contains a NUL byte:
          on the installed game that splits every one of the 48 extensions
          under data\ cleanly (every .dds, .osm, .lng ... has one, no .inc,
          .cfg, .script ... has any).
  class   `never`  on the never-generate list (plan S2), or binary;
          `merge`  on the Phase A merge allow-list (plan S3): `.inc` under
                   `gui\menu.inc\`, `gui\common.inc\` or `scripts\`;
          `wta`    everything else - winner takes all is the default, and
                   `merge` is an allow-list, not the complement of a deny-list.

`|` separates the fields because Windows forbids it in file names, so a path
can never contain one; the build also refuses a path with any byte outside
printable ASCII. Measured on 2026-09-28: 17 001 entries (never 14 030,
merge 311, wta 2 660), 1 173 695 bytes, 17 009 lines.

------------------------------------------------------------------ deploying

`--deploy` copies dist/Quartermaster to `<G>\mods\Quartermaster` and
`--undeploy` removes that one folder and refuses any other. The game registers
and enables every folder in `mods\` when it starts, so both refuse while
cossacks.exe or modman.exe runs or while the shared test lock
`<save>\swfp_game.lock` exists. `--dry-run` says what would happen and touches
nothing. The game directory is never written by anything else here: the build
only reads it.
"""
import argparse
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SRC = os.path.join(REPO, "src")
DIST = os.path.join(REPO, "dist")
MOD_NAME = "Quartermaster"
DIST_MOD = os.path.join(DIST, MOD_NAME)
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"
LOCK_NAME = "swfp_game.lock"
GAME_IMAGES = ("cossacks.exe", "modman.exe")

QM_VERSION = "0.1.7"

IDX_REL = "data/quartermaster/vanilla.idx"
IDX_FORMAT = 1

INTEGER_BUDGET = 1000000
STRING_BUDGET = 200000

# The planner's constants are the game side's too: the build hands them to the
# templates as build variables, so the twin and the game read one definition.
if REPO not in sys.path:
    sys.path.insert(0, REPO)
from ref import about as _about  # noqa: E402
from ref import diff as _diff  # noqa: E402
from ref import fingerprint as _fingerprint  # noqa: E402
from ref import inc as _inc  # noqa: E402
from ref import planner as _planner  # noqa: E402
from ref import textio as _textio  # noqa: E402
from ref import validate as _validate  # noqa: E402

#: The hook files of plan S5 as mod-relative paths (ref.planner.HOOK_FILES).
HOOK_FILES = tuple("data/" + h.decode("ascii").replace("\\", "/")
                   for h in _planner.HOOK_FILES)
#: Plan S5: "hook lines ... <= ~10 lines".
HOOK_MAX_LINES = 10
#: Where the pristine hook lines are shipped for the generator to merge in
#: (src/lib/qmwrite.pas qmWrHookDir): the hooked copies under gui/menu.inc/
#: are outputs a generation overwrites, so the lines need a home of their own.
HOOK_LINES_DIR = "data/quartermaster/hooks/"
#: Quartermaster's own list (ref/about.py KNOWN_DIR, docs/authoring.md):
#: src/known/<Workshop number>.cfg, an about.cfg for a Workshop mod that ships
#: none, shipped as it is. A file with any problem stops the build.
KNOWN_DIR = "data/quartermaster/known/"
KNOWN_SRC = "known"
#: The pre-compile guard of plan S17 (src/guard/resource.pas): the installed
#: game's on-load script (resource.lib:88) with the guard's lines after it. The
#: one file of the never-generate list Quartermaster ships - built here from
#: the installed game, never written at runtime.
GUARD_FILE = "data/scripts/resource.script"
#: The value of `${hookgen}` before the build has computed it: the generation
#: line's value does not enter any token, so a placeholder is enough to render
#: the hooks for that computation.
HOOKGEN_PLACEHOLDER = "-"

#: Lines a raw-text buffer holds (index 0..RAW_CAP). Files over the size cap of
#: plan S14 are never merged, so 65536 covers every file the game side reads
#: as text; a String array of that size allocates in about 0.3 s (measured).
RAW_CAP = 65535
#: Code values an `.inc` buffer holds; the largest vanilla `.inc`
#: (progresswarai.inc) has 4261.
INC_CAP = 8191
#: Key lines an `.inc` header holds (index 0..INC_HEAD); vanilla has at most 3
#: (docreate.inc: Name, Description[*], UsedFileName).
INC_HEAD = 15
#: Vanilla paths the index scans per call of its step state. The whole scan is
#: a few hundred FileAge calls per mod, 17 us each (measured), so one call does
#: it all; lower this to spread a larger scan over several frames.
INDEX_BATCH = 100000

CRLF = b"\r\n"
# The code-line prefix of every wrapped state (cameracontrol.inc:4).
PREFIX = b"      [*] = ;"


class BuildError(RuntimeError):
    """The request or the sources are wrong; the message says where."""


class TemplateError(BuildError):
    """A template is malformed. Always names `<template>:<line>`."""


class DeployError(BuildError):
    """A deploy or undeploy was refused."""


# ---------------------------------------------------------------- the lint
_VENDORED = os.path.join(HERE, "vendor", "gscript.py")


def _load_gscript():
    """The vendored parser, and only that copy.

    Loaded by path so no other `gscript` on sys.path can stand in for it: the
    public repository has to build on a machine where only this file exists.
    """
    if not os.path.isfile(_VENDORED):
        raise SystemExit("hbuild: %s is missing - restore it from version "
                         "control; the build never falls back to another copy"
                         % _VENDORED)
    spec = importlib.util.spec_from_file_location("qm_vendor_gscript", _VENDORED)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gscript = _load_gscript()
# One spelling of the prefix: the lint reads code lines by it, the assembler
# writes them with it.
assert gscript.PREFIX == PREFIX


# ----------------------------------------------------------- the templates
_PLACEHOLDER = re.compile(rb"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_OPENER = re.compile(rb"\$[{(\[]")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NOTE = b"//!"
_FRONT_END = b"---"
_KEYS = {"state": ("state", "into", "helpers", "requires"),
         "screen": ("screen", "into", "helpers", "requires"),
         "helper": ("helpers", "requires"),
         "hook": ("hook", "requires"),
         "guard": ("guard", "into", "requires")}
_INTO = re.compile(r"^data/quartermaster/[a-z0-9_]+(?:/[a-z0-9_]+)*\.(?:inc|aix)$")
# A screen is a GUI state, and vanilla names those Show<Root> / Event<Root>:
# _misc_GetGUIShowEventStateNames derives the root element's name from them
# (data/scripts/lib/misc.script:1929-1940). `Qm` keeps the root clear of
# every vanilla one.
_SCREEN = re.compile(r"^(Show|Event)Qm[A-Za-z0-9]+$")
SCREEN_DIR = "data/quartermaster/ui/"


@dataclass
class Template:
    path: str               # repository-relative, forward slashes
    kind: str               # "state" | "screen" | "helper" | "hook"
    name: str               # state name, or helper name (file stem)
    into: str               # target file of a state, "" for a helper
    helpers: list
    requires: list
    body: list              # body lines, no terminators, notes included
    first_line: int         # file line number of body[0]


def _names(path, key, value, line):
    out = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if not _IDENT.match(part):
            raise TemplateError("%s:%d: %r in '%s:' is not an identifier"
                                % (path, line, part, key))
        if part.lower() in (p.lower() for p in out):
            raise TemplateError("%s:%d: %r named twice in '%s:'"
                                % (path, line, part, key))
        out.append(part)
    return out


def parse_template(path, raw, kind):
    """A `Template` from the bytes of one `.pas` file.

    Line endings are normalised on the way in, so a checkout that turned the
    template into CRLF renders the same bytes; the assembler puts CRLF back.
    """
    if kind not in _KEYS:
        raise BuildError("unknown template kind %r" % kind)
    text = raw.replace(b"\r\n", b"\n")
    lines = text.split(b"\n")
    if lines and lines[-1] == b"":
        lines.pop()
    if _FRONT_END not in lines:
        raise TemplateError("%s: no front matter - the header must be closed "
                            "by a line reading exactly '---'" % path)
    cut = lines.index(_FRONT_END)
    header, body = lines[:cut], lines[cut + 1:]
    first_line = cut + 2

    seen, where, last = {}, {}, None
    for i, raw_line in enumerate(header, 1):
        if not raw_line.strip():
            continue
        try:
            line = raw_line.decode("ascii")
        except UnicodeDecodeError:
            raise TemplateError("%s:%d: front matter is not ASCII" % (path, i))
        if line[:1] in (" ", "\t"):
            if last is None:
                raise TemplateError("%s:%d: indented front-matter line with no "
                                    "key above it" % (path, i))
            seen[last] += " " + line.strip()
            continue
        if ":" not in line:
            raise TemplateError("%s:%d: front-matter line is not '<key>: "
                                "<value>': %r" % (path, i, line))
        key, _, value = line.partition(":")
        key = key.strip()
        if key in seen:
            raise TemplateError("%s:%d: duplicate front-matter key %r"
                                % (path, i, key))
        seen[key], where[key], last = value.strip(), i, key

    allowed = _KEYS[kind]
    unknown = sorted(k for k in seen if k not in allowed)
    if unknown:
        raise TemplateError("%s: unknown front-matter key(s) %s - a %s takes %s"
                            % (path, ", ".join(unknown), kind,
                               ", ".join(allowed)))
    for key in allowed:
        if key not in seen:
            raise TemplateError("%s: front matter has no %r - every key is "
                                "mandatory and none has a default" % (path, key))

    for i, raw_line in enumerate(body, first_line):
        if raw_line != raw_line.rstrip():
            raise TemplateError("%s:%d: trailing whitespace - an emitted space "
                                "nobody can see is still a byte the engine "
                                "reads" % (path, i))
        bad = [c for c in raw_line if not (32 <= c <= 126 or c == 9)]
        if bad:
            raise TemplateError("%s:%d: byte 0x%02x is not printable ASCII - "
                                "the engine's code page is not ours to guess"
                                % (path, i, bad[0]))

    helpers = (_names(path, "helpers", seen["helpers"], where["helpers"])
               if "helpers" in seen else [])
    requires = _names(path, "requires", seen["requires"], where["requires"])
    stem = os.path.splitext(os.path.basename(path))[0]
    if kind == "hook":
        target = seen["hook"]
        if target not in HOOK_FILES:
            raise TemplateError("%s:%d: 'hook: %s' - a hook goes into one of the "
                                "hook files of plan S5: %s"
                                % (path, where["hook"], target, ", ".join(HOOK_FILES)))
        check_output_path(target)
        return Template(path, kind, stem, target, [], requires, body, first_line)
    if kind == "guard":
        if seen["into"] != GUARD_FILE:
            raise TemplateError("%s:%d: 'into: %s' - the guard goes into %s (plan S17)"
                                % (path, where["into"], seen["into"], GUARD_FILE))
        name = seen["guard"]
        if not _IDENT.match(name) or not name.lower().startswith("qm"):
            raise TemplateError("%s:%d: guard name %r must be an identifier "
                                "starting with 'qm'" % (path, where["guard"], name))
        return Template(path, kind, name, GUARD_FILE, [], requires, body, first_line)
    if kind == "screen":
        name = seen["screen"]
        if not _SCREEN.match(name):
            raise TemplateError("%s:%d: screen name %r must be Show<Qm...> or "
                                "Event<Qm...>" % (path, where["screen"], name))
        into = seen["into"]
        if into != SCREEN_DIR + name.lower() + ".inc":
            raise TemplateError("%s:%d: 'into: %s' - a screen is emitted into %s%s.inc"
                                % (path, where["into"], into, SCREEN_DIR, name.lower()))
        check_output_path(into)
        return Template(path, kind, name, into, helpers, requires, body, first_line)
    if kind == "state":
        name = seen["state"]
        if not _IDENT.match(name) or not name.lower().startswith("qm"):
            raise TemplateError("%s:%d: state name %r must be an identifier "
                                "starting with 'qm'" % (path, where["state"], name))
        into = seen["into"]
        if not _INTO.match(into):
            raise TemplateError("%s:%d: 'into: %s' - a state is emitted into a "
                                "lower-case .inc or .aix under "
                                "data/quartermaster/ (plan S6)"
                                % (path, where["into"], into))
        check_output_path(into)
    else:
        name, into = stem, ""
        if not _IDENT.match(name) or name != name.lower():
            raise TemplateError("%s: helper file names are lower-case "
                                "identifiers" % path)
    return Template(path, kind, name, into, helpers, requires, body, first_line)


def _placeholders(t):
    used = []
    for i, raw_line in enumerate(t.body, t.first_line):
        if raw_line.lstrip().startswith(_NOTE):
            continue
        pos = 0
        while True:
            opener = _OPENER.search(raw_line, pos)
            if not opener:
                break
            hit = _PLACEHOLDER.match(raw_line, opener.start())
            if not hit:
                raise TemplateError("%s:%d: %r is not a placeholder - the "
                                    "syntax is ${name}"
                                    % (t.path, i,
                                       raw_line[opener.start():opener.start() + 24]))
            name = hit.group(1).decode()
            if name not in used:
                used.append(name)
            pos = hit.end()
    return used


def _value_lines(t, var, value):
    if isinstance(value, bool):
        raise TemplateError("%s: %s is a bool; pass the bytes you mean"
                            % (t.path, var))
    if isinstance(value, int):
        return [b"%d" % value]
    if isinstance(value, bytes):
        return value.split(b"\n")
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            if not isinstance(item, bytes):
                raise TemplateError("%s: %s holds %s; a block is a sequence of "
                                    "bytes lines" % (t.path, var,
                                                     type(item).__name__))
            out += item.split(b"\n")
        return out
    raise TemplateError("%s: %s is %s; pass bytes, an int or a list of bytes "
                        "lines" % (t.path, var, type(value).__name__))


def render_lines(t, variables):
    """The template's code lines: notes dropped, placeholders filled.

    Declared, used and supplied variables must agree exactly; each of the four
    ways they can disagree is an error naming the template.
    """
    used = _placeholders(t)
    stale = [v for v in t.requires if v not in used]
    if stale:
        raise TemplateError("%s: 'requires:' declares %s, which the body does "
                            "not use" % (t.path, ", ".join(stale)))
    undeclared = [v for v in used if v not in t.requires]
    if undeclared:
        raise TemplateError("%s: the body uses ${%s} without declaring it in "
                            "'requires:'" % (t.path, "}, ${".join(undeclared)))
    missing = [v for v in t.requires if v not in variables]
    if missing:
        raise TemplateError("%s: no value for %s (the build knows: %s)"
                            % (t.path, ", ".join(missing),
                               ", ".join(sorted(variables)) or "nothing"))
    unused = sorted(v for v in variables if v not in t.requires)
    if unused:
        raise TemplateError("%s: %s was passed but the template does not "
                            "declare it" % (t.path, ", ".join(unused)))
    values = {v: _value_lines(t, v, variables[v]) for v in t.requires}

    out = []
    for i, raw_line in enumerate(t.body, t.first_line):
        stripped = raw_line.lstrip()
        if stripped.startswith(_NOTE):
            continue
        hit = _PLACEHOLDER.fullmatch(stripped)
        if hit:
            indent = raw_line[:len(raw_line) - len(stripped)]
            out += [indent + item if item else item
                    for item in values[hit.group(1).decode()]]
            continue
        pieces, pos = [], 0
        for hit in _PLACEHOLDER.finditer(raw_line):
            value = values[hit.group(1).decode()]
            if len(value) != 1:
                raise TemplateError("%s:%d: ${%s} is inside a line but its value "
                                    "is %d lines; put it on a line of its own"
                                    % (t.path, i, hit.group(1).decode(),
                                       len(value)))
            pieces += [raw_line[pos:hit.start()], value[0]]
            pos = hit.end()
        pieces.append(raw_line[pos:])
        out.append(b"".join(pieces))
    return out


def qstr(text):
    """A Pascal string literal holding `text`: quoted, every `'` doubled.

    ASCII only, and no line break, because a literal cannot span code lines.
    """
    data = text.encode("ascii")
    if any(c < 32 or c > 126 for c in data):
        raise BuildError("qstr: %r holds a byte a one-line ASCII literal "
                         "cannot carry" % text)
    return b"'" + data.replace(b"'", b"''") + b"'"


def _pipe_list(paths):
    """A Pascal literal `'|a|b|'`: membership is `StrPos('|'+x+'|', list)>0`."""
    return qstr("|" + "|".join(p.decode("ascii") for p in paths) + "|")


def _vanilla_rel(rel):
    r"""`data/gui/x.inc` -> `gui\x.inc`, the spelling of vanilla.idx."""
    return rel[len("data/"):].replace("/", "\\").encode("ascii")


def build_variables(shipped_hooks=()):
    """Every value a template can splice in with `${name}`.

    `shipped_hooks` are the targets of src/hooks, as mod-relative paths: the
    game side counts Quartermaster as a provider of exactly those.
    """
    return {
        "version": qstr(QM_VERSION),
        "dcap": _diff.d_cap(),
        "maxlines": _diff.MAX_LINES,
        "h1mul": _fingerprint.H1[0],
        "h1mod": _fingerprint.H1[1],
        "h2mul": _fingerprint.H2[0],
        "h2mod": _fingerprint.H2[1],
        "rawcap": RAW_CAP,
        "inccap": INC_CAP,
        "inchead": INC_HEAD,
        "indexbatch": INDEX_BATCH,
        "sizecap": _planner.SIZE_CAP_LINES,
        "maxsettings": _about.MAX_SETTINGS,
        "rawsettings": _about.RAW_SETTINGS,
        "scannamed": _pipe_list(list(_planner.HOOK_FILES) + list(_planner.PHASE_B_DATA)
                                + [_planner.ADDITIVE_GLOBAL]),
        "phasebdata": _pipe_list(_planner.PHASE_B_DATA),
        "additiveglobal": qstr(_planner.ADDITIVE_GLOBAL.decode("ascii")),
        "shippedhooks": _pipe_list(sorted(_vanilla_rel(h) for h in shipped_hooks)),
        # What Quartermaster ships that the index does not read and another
        # mod could ship too: the guard's resource.script, and core.aix (a
        # second copy of Quartermaster). A mod with one of them decides the
        # order with Quartermaster (qmGuard's restart, ref/order.py needs_restart).
        "ownfiles": _pipe_list([_vanilla_rel(GUARD_FILE), b"quartermaster\\core.aix"]),
        "hookgen": qstr(HOOKGEN_PLACEHOLDER),
    }


BUILD_VARIABLES = build_variables()


# ---------------------------------------------------------------- sources
def _read_dir(src_dir, sub, kind):
    folder = os.path.join(src_dir, sub)
    out = []
    if not os.path.isdir(folder):
        return out
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith(".pas"):
            continue
        full = os.path.join(folder, fn)
        rel = os.path.relpath(full, os.path.dirname(src_dir)).replace(os.sep, "/")
        with open(full, "rb") as fh:
            out.append(parse_template(rel, fh.read(), kind))
    return out


def load_hooks(src_dir=SRC):
    """The hook templates, at most one per target file."""
    hooks = _read_dir(src_dir, "hooks", "hook")
    seen = {}
    for h in hooks:
        if h.into in seen:
            raise BuildError("%s: %s already has a hook, from %s; one hook per "
                             "file keeps its lines in one place"
                             % (h.path, h.into, seen[h.into]))
        seen[h.into] = h.path
    return hooks


def load_guard(src_dir=SRC):
    """The guard template (plan S17), or None; at most one."""
    guards = _read_dir(src_dir, "guard", "guard")
    if len(guards) > 1:
        raise BuildError("%s: one guard only (also %s)"
                         % (guards[1].path, guards[0].path))
    return guards[0] if guards else None


def guard_variables(vanilla):
    """The guard's values: the stamp of the installed resource.script it was
    built against (ref/guard.py game_stamp) and the hash constants the guard
    computes it with. Until 0.1.2 the guard compared the file's FileAge, which
    is the day Steam wrote the file on that machine: the guard was off on
    every installation but the author's (first start on a second computer,
    2026-10-02)."""
    from ref.guard import game_stamp
    return {"guardstamp": qstr(game_stamp(vanilla).decode("ascii")),
            "h1mul": _fingerprint.H1[0], "h1mod": _fingerprint.H1[1],
            "h2mul": _fingerprint.H2[0], "h2mod": _fingerprint.H2[1]}


def build_guard(guard, game_dir, env):
    """`(bytes, findings)`: the installed game's resource.script, CRLF, then
    the guard's lines. The lints see the guard alone, as one state whose
    names must all be the engine's natives - the libraries are not compiled
    when it runs."""
    source = os.path.join(game_dir, *GUARD_FILE.split("/"))
    if not os.path.isfile(source):
        raise BuildError("%s: the guard needs the installed game's %s (not found "
                         "under %s)" % (guard.path, GUARD_FILE, game_dir))
    with open(source, "rb") as fh:
        vanilla = fh.read()
    code = render_lines(guard, guard_variables(vanilla))
    if not any(line.strip() for line in code):
        raise BuildError("%s: the guard has no code" % guard.path)
    head = vanilla if vanilla.endswith(CRLF) else vanilla + CRLF
    data = head + b"".join(line + CRLF for line in code)
    section = assemble_inc(guard.name.encode("ascii"), code)
    first = section.find(PREFIX)
    lines = (section[:first].count(b"\n") + 1, section[:first].count(b"\n") + len(code))
    # Line numbers of the findings are lines of that one-state wrapping: the
    # guard's code line k is line k+3 there (section.begin, Name, Code).
    findings = lint_state(guard.path, guard.name, section, 0, env, hook_lines=lines,
                          natives_only=True)
    return data, findings


def load_sources(src_dir=SRC):
    """`(states and screens, {helper name: Template})`.

    A screen is built like a state that has a one-state `.inc` of its own, so
    both go through the same assembly and lints, and one uniqueness check
    covers both: the GUI machine and a trigger manager are different
    machines, but a name used twice is a name one of them resolves wrongly.
    """
    states = _read_dir(src_dir, "states", "state") + _read_dir(src_dir, "screens", "screen")
    helpers = {t.name: t for t in _read_dir(src_dir, "lib", "helper")}
    names = {}
    for st in states:
        low = st.name.lower()
        if low in names:
            raise BuildError("%s: state %s is also declared by %s (state names "
                             "are unique case-insensitively)"
                             % (st.path, st.name, names[low]))
        names[low] = st.path
    return states, helpers


def resolve_helpers(t, helpers, _chain=()):
    """The helpers `t` needs, dependencies first, each once."""
    out = []
    for name in t.helpers:
        if name in _chain:
            raise BuildError("%s: helper cycle %s" % (t.path,
                                                       " -> ".join(_chain + (name,))))
        if name not in helpers:
            raise BuildError("%s: helper %r is not in src/lib (known: %s)"
                             % (t.path, name, ", ".join(sorted(helpers)) or "none"))
        for dep in resolve_helpers(helpers[name], helpers, _chain + (name,)):
            if dep not in out:
                out.append(dep)
        if name not in out:
            out.append(name)
    return out


def _vars_for(t, variables):
    return {k: variables[k] for k in t.requires if k in variables}


def state_code(st, helpers, variables=None):
    """The state's code lines: its helpers, then its own body."""
    variables = BUILD_VARIABLES if variables is None else variables
    code = []
    for name in resolve_helpers(st, helpers):
        h = helpers[name]
        code += render_lines(h, _vars_for(h, variables))
        code.append(b"")
    body = render_lines(st, _vars_for(st, variables))
    if not any(line.strip() for line in body):
        raise BuildError("%s: the state has no code" % st.path)
    return code + body


# -------------------------------------------------------------- containers
def _join(lines):
    return b"".join(line + CRLF for line in lines)


def assemble_inc(name, code):
    """A one-state `.inc` (cameracontrol.inc:1-38)."""
    return _join([b"section.begin", b"   Name = " + name, b"   Code : struct.begin"]
                 + [PREFIX + c for c in code]
                 + [b"   struct.end", b"section.end", b""])


def aix_section(name, code):
    """One state of a multi-state `.aix` (rusmis1.aix:1-13)."""
    return _join([b"section.begin", b"   Name = " + name, b"   UsedFileName = ",
                  b"   Code : struct.begin"]
                 + [PREFIX + c for c in code]
                 + [b"   struct.end", b"section.end", b""])


AIX_TRAILER = _join([b"section.begin", b"   CurrentState = ",
                     b"   SaveVariables = False", b"section.end", b""])


def assemble_aix(states):
    """A multi-state `.aix` from `[(name, code lines)]` (rusmis1.aix:1-26)."""
    return b"".join(aix_section(n, c) for n, c in states) + AIX_TRAILER


# ---------------------------------------------------------------- findings
@dataclass(frozen=True)
class Finding:
    lint: str
    where: str          # "<emitted path>:<line>"
    state: str
    message: str

    def __str__(self):
        return "%s: [%s] %s%s" % (self.where, self.lint, self.message,
                                  " (state %s)" % self.state if self.state else "")


class LintEnv(object):
    """What a state can see before it declares anything, read from the game."""

    def __init__(self, env, global_ints):
        self.env = env
        self.global_ints = global_ints

    @classmethod
    def from_game(cls, game_dir):
        exe = os.path.join(game_dir, "cossacks.exe")
        glob_path = os.path.join(game_dir, "data", "scripts", "dmscript.global")
        if not (os.path.isfile(exe) and os.path.isfile(glob_path)):
            raise BuildError("the identifier lints need the installed game: no "
                             "cossacks.exe / data\\scripts\\dmscript.global under "
                             "%s (pass --game-dir, or --offline to skip them)"
                             % game_dir)
        with open(glob_path, "rb") as fh:
            return cls(gscript.Environment(game_dir), global_int_constants(fh.read()))

    def stats(self):
        return self.env.stats()


_GLOBAL_INT = re.compile(rb"^\s*([A-Za-z_]\w*)\s*=\s*(-?\d+)\s*;", re.M)


def global_int_constants(data):
    """`{lower name: int}` from the first section of dmscript.global.

    That section is the constant block (`gc_ResCount = 7;` at
    dmscript.global:3, `gc_MaxPlayerCount = 12;` at :97, closed at :1670);
    array bounds in vanilla are written in terms of these names.
    """
    end = data.find(b"section.end")
    head = data if end < 0 else data[:end]
    return {m.group(1).lower(): int(m.group(2)) for m in _GLOBAL_INT.finditer(head)}


def _declarations(unit):
    """One declaration per byte offset, without the implicit `Result`.

    The parser reports a `var x` inside a parameter list twice (once as a
    parameter, once as a var) at the same offset; the offset is the identity.
    """
    functions = set(d.offset for d in unit.decls if d.kind == "function")
    by_offset = {}
    for d in unit.decls:
        if d.name.lower() == b"result" and d.offset in functions and d.kind == "var":
            continue
        by_offset.setdefault(d.offset, d)
    return [by_offset[k] for k in sorted(by_offset)]


class _NotEvaluable(Exception):
    pass


_TOKEN = re.compile(rb"\s*(?:(\d+)|([A-Za-z_]\w*)|(\S))")


def eval_int(text, consts, _depth=0):
    """An integer constant expression: literals, names, + - * div ( ).

    `consts` maps lower-case names to an int or to the bytes of their own
    expression. Anything else is not evaluable, which the budget lint reports
    rather than guesses around.
    """
    if _depth > 20:
        raise _NotEvaluable("constants nest too deep")
    tokens = []
    pos = 0
    text = text.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            break
        tokens.append(m.group(1) or m.group(2) or m.group(3))
        pos = m.end()
    tokens.append(None)
    at = [0]

    def peek():
        return tokens[at[0]]

    def take():
        at[0] += 1
        return tokens[at[0] - 1]

    def factor():
        tok = take()
        if tok is None:
            raise _NotEvaluable("expression ends early")
        if tok == b"-":
            return -factor()
        if tok == b"+":
            return factor()
        if tok == b"(":
            value = expr()
            if take() != b")":
                raise _NotEvaluable("unbalanced parenthesis")
            return value
        if tok.isdigit():
            return int(tok)
        name = tok.lower()
        if name in consts:
            value = consts[name]
            if isinstance(value, bytes):
                value = eval_int(value, consts, _depth + 1)
            return value
        raise _NotEvaluable("%s is not a known integer constant" % tok.decode())

    def term():
        value = factor()
        while peek() is not None and (peek() == b"*" or peek().lower() == b"div"):
            op = take()
            rhs = factor()
            if op == b"*":
                value *= rhs
            else:
                if rhs == 0:
                    raise _NotEvaluable("division by zero")
                value //= rhs
        return value

    def expr():
        value = term()
        while peek() in (b"+", b"-"):
            op = take()
            rhs = term()
            value = value + rhs if op == b"+" else value - rhs
        return value

    value = expr()
    if peek() is not None:
        raise _NotEvaluable("unexpected %r" % peek().decode("ascii", "replace"))
    return value


_LOCAL_CONST = re.compile(rb"\bconst\s+([A-Za-z_]\w*)\s*(?::\s*[A-Za-z_]\w*\s*)?=\s*([^;]*);",
                          re.I)
_ARRAY_OPEN = re.compile(rb"\barray\s*\[", re.I)
_OF_WORD = re.compile(rb"\s*of\s+([A-Za-z_]\w*)", re.I)
_BRACKET = re.compile(rb"\s*\[")


def declared_arrays(code):
    """`[(offset, [dimension texts], element type or None)]` over masked code.

    `array [a..b] of array [c..d] of T` is one declaration of (b-a+1)*(d-c+1)
    elements of T, and `array [a..b, c..d] of T` is the same thing spelled in
    one bracket. A parameter's open `array of T` has no bounds and allocates
    nothing, so it is not matched.
    """
    out = []
    pos = 0
    while True:
        m = _ARRAY_OPEN.search(code, pos)
        if not m:
            return out
        start, cur, dims, element = m.start(), m.end(), [], None
        while True:
            close = code.find(b"]", cur)
            if close < 0:
                pos = len(code)
                break
            dims += code[cur:close].split(b",")
            of = _OF_WORD.match(code, close + 1)
            if not of:
                pos = close + 1
                break
            if of.group(1).lower() == b"array":
                nxt = _BRACKET.match(code, of.end())
                if not nxt:
                    pos = of.end()
                    break
                cur = nxt.end()
                continue
            element, pos = of.group(1), of.end()
            break
        out.append((start, dims, element))


_ROUTINE_HEAD = re.compile(rb"\b(?:function|procedure)\s+[A-Za-z_]\w*\s*\(")
# `function qmX(...) : String;` or `function qmX : String;` - masked code, so no
# comment or string literal can match.
_STRING_FUNCTION = re.compile(
    rb"\bfunction\s+([A-Za-z_]\w*)\s*(?:\([^()]*\))?\s*:\s*string\b", re.I)
_OPEN_ARRAY = re.compile(rb"\barray\s+of\b", re.I)
# A char literal (#13) right next to another literal, without `+`: #13#10,
# 'a'#9. Masked code keeps the quotes of a string literal, so both sides show.
_CHAR_JOIN = re.compile(rb"#\d+\s*(?=[#'])|'\s*(?=#\d)")
NO_SUCH_ROUTINES = (b"high", b"length", b"setlength")


def parameter_groups(code):
    """`[(start, end, group bytes)]` of every routine parameter group in masked code.

    A group is the text between `(`, `;` and `)` of a routine header:
    `var qmA : array [0..9] of String` or `const qmB : Integer`.
    """
    out = []
    for m in _ROUTINE_HEAD.finditer(code):
        start = m.end()
        depth, i = 1, start
        while i < len(code) and depth:
            if code[i] == 40:
                depth += 1
            elif code[i] == 41:
                depth -= 1
            i += 1
        body_end = i - 1
        pos = start
        for part in code[start:body_end].split(b";"):
            out.append((pos, pos + len(part), part))
            pos += len(part) + 1
    return out


def _by_reference_arrays(code):
    """Offsets of `array` declarations that are `var` parameters."""
    out = set()
    for start, end, group in parameter_groups(code):
        if group.strip().lower().startswith(b"var"):
            for m in _ARRAY_OPEN.finditer(code, start, end):
                out.add(m.start())
    return out


def lint_array_budget(unit, consts, finding):
    """Findings for the per-state array budget (plan S14)."""
    out = []
    totals = {"integer": 0, "string": 0}
    reported = set()
    by_reference = _by_reference_arrays(unit.code)
    for offset, dims, element in declared_arrays(unit.code):
        if offset in by_reference:
            continue
        if element is None:
            out.append(finding("array-budget", offset,
                               "array declaration could not be read"))
            continue
        count = 1
        try:
            for dim in dims:
                if b".." not in dim:
                    raise _NotEvaluable("bound %r is not lo..hi"
                                        % dim.strip().decode("ascii", "replace"))
                lo, hi = dim.split(b"..", 1)
                size = eval_int(hi, consts) - eval_int(lo, consts) + 1
                if size <= 0:
                    raise _NotEvaluable("bound %s gives %d elements"
                                        % (dim.strip().decode("ascii", "replace"), size))
                count *= size
        except _NotEvaluable as exc:
            out.append(finding("array-budget", offset,
                               "array bound cannot be evaluated from literals "
                               "and constants: %s" % exc))
            continue
        kind = "string" if element.lower() == b"string" else "integer"
        totals[kind] += count
        budget = STRING_BUDGET if kind == "string" else INTEGER_BUDGET
        if totals[kind] > budget and kind not in reported:
            reported.add(kind)
            out.append(finding("array-budget", offset,
                               "%s arrays declare %d elements in this state by "
                               "here; the budget is %d (%s)"
                               % ("String" if kind == "string" else "Integer-class",
                                  totals[kind], budget,
                                  "1M Strings took 15 s to allocate"
                                  if kind == "string"
                                  else "4M Integers crashed the game")))
    return out


def _engine_names(env):
    """What hook lines may name: the engine's own API, never a library routine."""
    e = env.env
    return (gscript.lower_all(e.routines) | gscript.lower_all(e.constants)
            | gscript.lower_all(e.variables) | gscript.lower_all(e.globals)
            | e.types | gscript.KEYWORDS | gscript.BUILTIN_TYPES | gscript.INTRINSICS)


def _native_names(env):
    """What the guard may name (plan S17): the engine's routines and
    variables only - no dmscript.global name, no library routine: neither
    exists yet when resource.script runs."""
    e = env.env
    return (gscript.lower_all(e.routines) | gscript.lower_all(e.variables)
            | e.types | gscript.KEYWORDS | gscript.BUILTIN_TYPES | gscript.INTRINSICS)


# A routine header with its name, any case: the alias lint's own pattern, kept
# apart from _ROUTINE_HEAD above so parameter_groups stays as it was.
_NAMED_HEAD = re.compile(rb"\b(?:procedure|function)\s+(\w+)\s*\(", re.I)
_PLAIN_VAR = re.compile(rb"^[a-z_]\w*(?:\[.*\])?$", re.I | re.S)


def alias_misuse(unit):
    """Calls of the state's own routines that hand one variable to a const
    String parameter and to a var parameter at once: `[(offset, routine,
    argument)]`. The game gives such a variable back damaged -
    qmLowerAscii(qmAbRid, qmAbRid) turned `qmtestverbase` into `qmtestverbas`
    (probe runs of 2026-09-29, docs/research/context-2026-09-27.md section 3)
    while the script interpreter of the tests kept them apart."""
    code = unit.code
    sigs, heads = {}, set()
    for m in _NAMED_HEAD.finditer(code):
        close = code.find(b")", m.end())
        if close < 0:
            continue
        params = []
        for group in code[m.end():close].split(b";"):
            words = group.strip().split(None, 1)
            mode = b""
            if words and words[0].lower() in (b"var", b"const"):
                mode, group = words[0].lower(), words[1] if len(words) > 1 else b""
            names, _colon, ptype = group.partition(b":")
            for nm in names.split(b","):
                if nm.strip():
                    params.append((mode, ptype.strip().lower()))
        sigs[m.group(1).lower()] = params
        heads.add(m.start(1))
    out = []
    for use in unit.uses:
        name = use.name.lower()
        if not use.called or name not in sigs or use.offset in heads:
            continue
        paren = code.find(b"(", use.offset + len(use.name))
        args = [a.strip().lower() for a in gscript._call_args(code, paren)]
        sig = sigs[name]
        outs = set(args[k] for k, (mode, _t) in enumerate(sig) if k < len(args) and mode == b"var")
        for k, (mode, ptype) in enumerate(sig):
            if (k < len(args) and mode != b"var" and ptype == b"string"
                    and _PLAIN_VAR.match(args[k]) and args[k] in outs):
                out.append((use.offset, use.name, args[k]))
    return out


def lint_state(where, name, section, line_base=0, env=None, hook_lines=None,
               natives_only=False):
    """Every finding for one state.

    `section` is the state as it sits in the emitted file and `line_base` the
    number of lines above it there. The parser is handed that many empty lines
    first, so every offset it reports is already a line of the emitted file,
    and the state is still parsed alone - the way the engine compiles it.

    `hook_lines` = `(first, last)`, emitted-file lines: the state is a vanilla
    state with hook lines in it. Vanilla's own code compiles as it is and is
    not ours to rename, so the name lints look only at the hook: its uses must
    resolve to the engine's API (hook-api), its declarations must carry the
    prefix and must not collide with a vanilla name (duplicate), and it may
    declare no `global`. Block balance still covers the whole state.
    """
    data = CRLF * line_base + section
    unit = gscript.parse(where, data)
    head = "%s:%d" % (where, line_base + 1)

    def finding(lint, offset, message):
        return Finding(lint, unit.where(offset) if offset is not None else head,
                       name, message)

    def ours(offset):
        if hook_lines is None:
            return True
        return hook_lines[0] <= unit.line(offset) <= hook_lines[1]

    out = []
    for message in gscript.balance(unit):
        out.append(Finding("gscript-balance", head, name, message))
    for offset, routine, arg in alias_misuse(unit):
        if ours(offset):
            out.append(finding("gscript-alias", offset,
                               "%s gets %s both by value and as a var parameter; the game "
                               "gives it back damaged - use a second variable"
                               % (routine.decode(), arg.decode("ascii", "replace"))))
    for use, decl in gscript.use_before_decl(unit):
        out.append(finding("gscript-const-order", use.offset,
                           "%s is used above its const declaration at line %d"
                           % (use.name.decode(), unit.line(decl.offset))))
    if env is not None:
        for use in env.env.unresolved(unit):
            if ours(use.offset):
                out.append(finding("gscript-unresolved", use.offset,
                                   "%s resolves nowhere (not a native, a "
                                   "dmscript.global name, a library routine or a "
                                   "name this state declares)" % use.name.decode()))
        for offset, routine, arg, why in gscript.byref_misuse(unit, env.env.byref):
            if ours(offset):
                out.append(finding("gscript-byref", offset,
                                   "%s hands %s to a var parameter: %s"
                                   % (routine.decode(), arg.decode("ascii", "replace"),
                                      why)))

    decls = _declarations(unit)
    groups = {}
    for d in decls:
        groups.setdefault(d.name.lower(), []).append(d)
    for low, group in sorted(groups.items(), key=lambda kv: kv[1][0].offset):
        if len(group) > 1 and any(ours(d.offset) for d in group):
            out.append(finding("duplicate", group[1].offset,
                               "%s is declared %d times in this state "
                               "(case-insensitive): %s"
                               % (group[1].name.decode(), len(group),
                                  ", ".join("%s at line %d" % (d.name.decode(),
                                                               unit.line(d.offset))
                                            for d in group))))
    for d in decls:
        if ours(d.offset) and not d.name.lower().startswith(b"qm"):
            out.append(finding("prefix", d.offset,
                               "%s %s does not start with 'qm'"
                               % (d.kind, d.name.decode())))
    for use in unit.uses:
        if use.name.lower() == b"chr":
            out.append(finding("chr", use.offset,
                               "Chr does not compile in any form; use a "
                               "character table (SubStr) instead"))
    for m in _STRING_FUNCTION.finditer(unit.code):
        if ours(m.start()):
            out.append(finding("string-function", m.start(),
                               "function %s returns a String, which does not "
                               "compile in state code; return it through a var "
                               "parameter" % m.group(1).decode()))
    for m in _OPEN_ARRAY.finditer(unit.code):
        if ours(m.start()):
            out.append(finding("open-array", m.start(),
                               "'array of' (an open or dynamic array) does not "
                               "compile; give the array fixed bounds"))
    for m in _CHAR_JOIN.finditer(unit.code):
        if ours(m.start()):
            out.append(finding("char-join", m.start(),
                               "a char literal written next to another literal; "
                               "join them with + (#13+#10), as every vanilla "
                               "line does"))
    for use in unit.uses:
        if use.called and use.name.lower() in NO_SUCH_ROUTINES and ours(use.offset):
            out.append(finding("no-routine", use.offset,
                               "%s does not compile in this dialect%s"
                               % (use.name.decode(),
                                  "; the length of a String is StrLength"
                                  if use.name.lower() == b"length" else "")))

    if hook_lines is not None:
        declared = set(d.name.lower() for d in decls if ours(d.offset))
        for d in decls:
            if ours(d.offset) and d.kind == "global":
                out.append(finding("hook-global", d.offset,
                                   "hook lines declare no globals (plan S5)"))
        if env is not None:
            allowed = (_native_names(env) if natives_only else _engine_names(env)) | declared
            seen = set()
            for use in unit.uses:
                low = use.name.lower()
                if ours(use.offset) and low not in allowed and low not in seen:
                    seen.add(low)
                    if natives_only:
                        out.append(finding("guard-api", use.offset,
                                           "%s is not an engine native; the guard "
                                           "runs before the libraries compile and "
                                           "names natives only (plan S17)"
                                           % use.name.decode()))
                    else:
                        out.append(finding("hook-api", use.offset,
                                           "%s is not part of the engine's API; hook "
                                           "lines use the engine API only (plan S5)"
                                           % use.name.decode()))

    consts = dict(env.global_ints) if env is not None else {}
    for m in _LOCAL_CONST.finditer(unit.code):
        consts[m.group(1).lower()] = m.group(2)
    out += lint_array_budget(unit, consts, finding)
    return out


def lint_file(rel, data):
    """Container findings for one emitted file."""
    out = []
    if data.count(b"\n") != data.count(CRLF) or data.count(b"\r") != data.count(CRLF):
        out.append(Finding("container", rel + ":1", "",
                           "not CRLF throughout (a bare CR or LF)"))
    if not data.endswith(CRLF):
        out.append(Finding("container", rel + ":1", "", "no final CRLF"))
    for i, line in enumerate(data.split(CRLF), 1):
        # A stray CR or LF is the first check's finding; report it once.
        if any(not (32 <= c <= 126 or c in (9, 10, 13)) for c in line):
            out.append(Finding("container", "%s:%d" % (rel, i), "",
                               "byte outside printable ASCII"))
            break
    return out


# ------------------------------------------------------- the S2 / S3 rules
S2_FILES = {
    "gui/menu.aix": "the GUI state machine; a broken copy bricks the game (verified)",
    "gui/menu.cfg": "declares the GUI machine (menu.cfg:2-3)",
    "gui/menu.inc/docreate.inc": "a broken copy bricks the game (verified)",
    "scripts/dmscript.source": "the library list; not read from a mod",
    "projects/project.main.prj": "an engine start-up file",
    "resources/resource.lib": "an engine start-up file",
    "scripts/resource.script": "an engine start-up file",
    "scripts/common.aix": "the machine DoCreate runs on first start",
    "scripts/common.inc/initmap.inc": "runs from DoCreate on first start",
    "objects/objects.lib": "an engine object table",
}
MERGE_DIRS = ("gui/menu.inc/", "gui/common.inc/", "scripts/")
# Quartermaster's own machines live here (plan S6); they override nothing.
OWN_DIR = "quartermaster/"


def s2_reason(rel):
    """Why `rel` (relative to data/, lower case, `/`) is never generated, or None.

    The never-generate list of plan S2, as rules on the path. Binaries are the
    remaining S2 entry and need the file's bytes; see `classify`.
    """
    if rel in S2_FILES:
        return S2_FILES[rel]
    base = rel.rsplit("/", 1)[-1]
    if rel.startswith("scripts/lib/") and rel.endswith(".script"):
        return "a library; a broken one bricks the game (verified)"
    if rel.endswith(".aix") and not rel.startswith(OWN_DIR):
        return "a state machine file"
    if rel.endswith(".prop"):
        return "an engine object table"
    if base.startswith("font") and rel.endswith(".lib"):
        return "fonts are used by index"
    if rel.endswith(".lng"):
        return "a binary language container"
    return None


def classify(rel, binary):
    """`never`, `merge` or `wta` for a vanilla path (see vanilla.idx above)."""
    if binary or s2_reason(rel):
        return "never"
    if rel.endswith(".inc") and rel.startswith(MERGE_DIRS):
        return "merge"
    return "wta"


def check_output_path(rel):
    """Refuse to emit anything on the never-generate list, and dmscript.global.

    `rel` is relative to the mod folder. Only `mod.ini` and files under
    `data/` are emitted.
    """
    norm = rel.replace("\\", "/")
    parts = norm.split("/")
    if (not norm or norm != norm.lower() or norm.startswith("/") or ":" in norm
            or any(p in ("", ".", "..") for p in parts)):
        raise BuildError("refusing to emit %r: not a plain lower-case path inside "
                         "the mod folder" % rel)
    if norm in ("mod.ini", GUARD_FILE):
        # The guard is the one never-generate file shipped (plan S17): built
        # from the installed game by build_guard, never written at runtime.
        return
    if parts[0] != "data":
        raise BuildError("refusing to emit %r: outside data/" % rel)
    inner = norm[len("data/"):]
    if inner == "scripts/dmscript.global":
        raise BuildError("refusing to emit %r: Quartermaster ships no "
                         "dmscript.global - as the last mod it would override "
                         "every other mod's globals (plan S4)" % rel)
    reason = s2_reason(inner)
    if reason:
        raise BuildError("refusing to emit %r: it is on the never-generate list "
                         "(plan S2): %s" % (rel, reason))


# ------------------------------------------------------------- vanilla.idx
def scan_file(path):
    """`(size, lines)` of one file; lines is -1 when the file holds a NUL byte.

    Read in blocks and abandoned at the first NUL, so 7 GB of textures cost a
    block each rather than their size.
    """
    size = os.path.getsize(path)
    lines, last = 0, None
    with open(path, "rb") as fh:
        while True:
            block = fh.read(1 << 20)
            if not block:
                break
            if b"\x00" in block:
                return size, -1
            lines += block.count(b"\n")
            last = block[-1:]
    if last is not None and last != b"\n":
        lines += 1
    return size, lines


def vanilla_entries(game_dir):
    """`[(path, size, lines, class)]` for every file under `<game>\\data`."""
    data_dir = os.path.join(game_dir, "data")
    if not os.path.isdir(data_dir):
        raise BuildError("no data folder under %s" % game_dir)
    out, seen = [], set()
    for root, dirs, files in os.walk(data_dir):
        dirs.sort()
        for fn in sorted(files):
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, data_dir).replace(os.sep, "/").lower()
            if any(not (33 <= ord(c) <= 126) or c == "|" for c in rel):
                raise BuildError("vanilla path %r holds a character the index "
                                 "cannot carry" % rel)
            if rel in seen:
                raise BuildError("vanilla path %r appears twice" % rel)
            seen.add(rel)
            size, lines = scan_file(full)
            if size >= 1 << 31:
                raise BuildError("%s: %d bytes does not fit a script Integer"
                                 % (rel, size))
            out.append((rel.replace("/", "\\"), size, lines, classify(rel, lines < 0)))
    out.sort(key=lambda e: e[0].encode("ascii"))
    return out


def render_vanilla_idx(entries):
    head = [b"section.begin", b"   Name = qmVanillaIndex",
            b"   Format = %d" % IDX_FORMAT, b"   Count = %d" % len(entries),
            b"   Code : struct.begin"]
    body = [PREFIX + b"%s|%d|%d|%s" % (p.encode("ascii"), s, n, c.encode("ascii"))
            for p, s, n, c in entries]
    return _join(head + body + [b"   struct.end", b"section.end", b""])


def parse_vanilla_idx(data):
    """`(header {key: value}, [(path, size, lines, class)])` - the inverse, for tests."""
    header, entries = {}, []
    for line in data.split(CRLF):
        if line.startswith(PREFIX):
            p, s, n, c = line[len(PREFIX):].decode("ascii").split("|")
            entries.append((p, int(s), int(n), c))
        else:
            m = re.match(rb"^   (\w+) = (.*)$", line)
            if m:
                header[m.group(1).decode()] = m.group(2).decode()
    return header, entries


def idx_stats(entries, data):
    counts = {"never": 0, "merge": 0, "wta": 0}
    for e in entries:
        counts[e[3]] += 1
    return {"entries": len(entries), "bytes": len(data),
            "lines": data.count(b"\n"), "classes": counts}


# ----------------------------------------------------------------- mod.ini
def mod_ini():
    r"""The mod.ini modman shows. Keys, order and spelling follow the two on disk.

    <G>\mods\SW_Frontline_Protocol\mod.ini:1-22 (a local mod: every Workshop
    field zero, `description[*] = ;` on one line) and the Workshop-written
    ...\workshop\content\333420\873048118\mod.ini:1-43 have the same keys in the
    same order; an empty value is `key = ` with its trailing space, and the file
    ends with an empty line. The title is the placeholder of plan S1; the texts
    a player reads are final since 2026-09-30.
    """
    return _join([
        b"section.begin",
        b"   publishedfileid = 0",
        b"   creatorappid = 0",
        b"   consumerappid = 0",
        b"   contentfolder = mods\\" + MOD_NAME.encode(),
        b"   previewfile = ",
        b"   ownersteamid = 0",
        b"   timecreated = 0",
        b"   timeupdated = 0",
        b"   visibility = 0",
        b"   banned = False",
        b"   title = " + MOD_NAME.encode(),
        b"   description[*] = ;Makes your mods work together: merges the game files two mods both change, keeps a new subscription from breaking your start, and gives mods their own settings. In the game, under Mod Manager in the main menu.",
        b"   tags = ",
        b"   filename = " + MOD_NAME.encode(),
        b"   filesize = 0",
        b"   previewfilesize = 0",
        b"   url = ",
        b"   filetype = 0",
        b"   acceptedforuse = False",
        b"   changenote[*] = ;v0.1 beta: first public version.",
        b"section.end",
        b"",
    ])


# ------------------------------------------------------------------ build
@dataclass
class BuildResult:
    outputs: dict                               # mod-relative path -> bytes
    findings: list
    states: list = field(default_factory=list)  # (name, into, source)
    lint_env: dict = field(default_factory=dict)
    idx: dict = field(default_factory=dict)


_STATE_NAME = re.compile(rb"^   Name = ([A-Za-z_]\w*)\r$", re.M)


def assemble_hook(hook, vanilla, code):
    """`(bytes, (first, last))`: vanilla with the hook's code lines at its hook index.

    `(first, last)` are the emitted-file line numbers of the hook lines. The
    place is `ref.inc.hook_index` of the file's Code values; the file must be
    a one-state `.inc` of the struct form (ref.inc parses it).
    """
    try:
        inc = _inc.parse(vanilla)
    except _inc.IncFormatError as exc:
        raise BuildError("%s: %s is not a one-state .inc: %s" % (hook.path, hook.into, exc))
    if inc.form != "struct":
        raise BuildError("%s: %s has no Code struct to insert into" % (hook.path, hook.into))
    k = _inc.hook_index(inc.values)
    at = len(inc.head) + sum(len(p) + len(v) + len(e) for p, v, e in
                             zip(inc.prefixes[:k], inc.values[:k], inc.eols[:k]))
    first = vanilla[:at].count(b"\n") + 1
    data = vanilla[:at] + b"".join(PREFIX + c + CRLF for c in code) + vanilla[at:]
    return data, (first, first + len(code) - 1)


def build_hook(hook, game_dir, variables, env):
    """`(rel, bytes, findings)` for one hook template."""
    source = os.path.join(game_dir, "data", *hook.into[len("data/"):].split("/"))
    if not os.path.isfile(source):
        raise BuildError("%s: the hook needs the installed game's %s (not found "
                         "under %s)" % (hook.path, hook.into, game_dir))
    with open(source, "rb") as fh:
        vanilla = fh.read()
    code = render_lines(hook, _vars_for(hook, variables))
    if not any(line.strip() for line in code):
        raise BuildError("%s: the hook has no code" % hook.path)
    data, span = assemble_hook(hook, vanilla, code)
    m = _STATE_NAME.search(vanilla)
    name = m.group(1).decode("ascii") if m else hook.name
    findings = lint_state(hook.into, name, data, 0, env, hook_lines=span)
    if len(code) > HOOK_MAX_LINES:
        findings.append(Finding("hook-size", "%s:%d" % (hook.into, span[0]), name,
                                "%d hook lines; plan S5 allows at most %d"
                                % (len(code), HOOK_MAX_LINES)))
    return hook.into, data, findings


def hook_code(hook, variables):
    """The hook's code lines, rendered."""
    return render_lines(hook, _vars_for(hook, variables))


def hook_lines_rel(hook):
    """data/quartermaster/hooks/<file name of the hooked vanilla file>."""
    return HOOK_LINES_DIR + hook.into.rsplit("/", 1)[1]


def hook_lines_file(hook, hooked, variables):
    """The pristine hook lines as a one-state `.inc` named like the vanilla
    state: what the generator merges into every generated copy of the file
    (the Code values are all it reads)."""
    m = _STATE_NAME.search(hooked)
    name = m.group(1) if m else hook.name.encode("ascii")
    return assemble_inc(name, hook_code(hook, variables))


def alone_hookgen(hooks, game_dir, variables):
    """The generation constant of Quartermaster alone (ref/validate.py
    alone_outputs_hash): every shipped hook file as vanilla plus its hook
    lines, in vanilla.idx order. Baked into the shipped CameraControl copy,
    the first generation of a fresh install finds its outputs current."""
    by_path = dict((_vanilla_rel(h.into), h) for h in hooks)
    paths = sorted(by_path)

    def read_vanilla(path):
        full = os.path.join(game_dir, "data", *path.decode("ascii").split("\\"))
        if not os.path.isfile(full):
            raise BuildError("%s: the hook needs the installed game's %s (not found "
                             "under %s)" % (by_path[path].path, by_path[path].into, game_dir))
        with open(full, "rb") as fh:
            return fh.read()

    def hook_values(path):
        return [_textio.escape(b";" + line) for line in hook_code(by_path[path], variables)]

    return _validate.alone_outputs_hash(paths, read_vanilla, hook_values).decode("ascii")


def load_known(src_dir=SRC):
    """`[(rel, bytes)]` of Quartermaster's own list, file name order."""
    from ref import about as _about
    folder = os.path.join(src_dir, KNOWN_SRC)
    out = []
    for fn in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if not re.fullmatch(r"[0-9]+\.cfg", fn):
            raise BuildError("src/known/%s: a list entry is named <Workshop number>.cfg" % fn)
        with open(os.path.join(folder, fn), "rb") as fh:
            data = fh.read()
        found = _about.parse(data).problems
        if found:
            raise BuildError("src/known/%s: %s" % (fn, "; ".join(
                p.text.decode("ascii", "replace") for p in found)))
        out.append((KNOWN_DIR + fn, data))
    return out


def build(src_dir=SRC, game_dir=GAME, offline=False, with_vanilla_idx=False,
          variables=None):
    """Everything dist/Quartermaster should hold, in memory, plus the findings.

    Hooks read the installed game's copy of the file they go into even with
    `offline`, which only skips the lints that need the game.
    """
    states, helpers = load_sources(src_dir)
    hooks = load_hooks(src_dir)
    if variables is None:
        variables = build_variables([h.into for h in hooks])
        if any("hookgen" in h.requires for h in hooks):
            variables["hookgen"] = qstr(alone_hookgen(hooks, game_dir, variables))
    env = None if offline else LintEnv.from_game(game_dir)
    outputs = {"mod.ini": mod_ini()}
    findings = []
    result = BuildResult(outputs, findings,
                         lint_env=env.stats() if env else {})

    for hook in hooks:
        rel, data, found = build_hook(hook, game_dir, variables, env)
        outputs[rel] = data
        findings += found
        result.states.append(("(hook)", rel, hook.path))
        outputs[hook_lines_rel(hook)] = hook_lines_file(hook, data, variables)

    for rel, data in load_known(src_dir):
        outputs[rel] = data

    guard = load_guard(src_dir)
    if guard is not None:
        data, found = build_guard(guard, game_dir, env)
        outputs[GUARD_FILE] = data
        findings += found
        result.states.append(("(guard)", GUARD_FILE, guard.path))

    targets = {}
    for st in states:
        targets.setdefault(st.into, []).append(st)
    for into in sorted(targets):
        group = sorted(targets[into], key=lambda s: s.name.lower())
        rendered = [(st, state_code(st, helpers, variables)) for st in group]
        for st, _code in rendered:
            result.states.append((st.name, into, st.path))
        if into.endswith(".inc"):
            if len(group) != 1:
                raise BuildError("%s: %d states target one .inc (%s); an .inc "
                                 "holds exactly one" % (into, len(group),
                                                        ", ".join(s.name for s in group)))
            st, code = rendered[0]
            data = assemble_inc(st.name.encode(), code)
            findings += lint_state(into, st.name, data, 0, env)
        else:
            sections = [aix_section(st.name.encode(), code) for st, code in rendered]
            data = b"".join(sections) + AIX_TRAILER
            base = 0
            for (st, _code), section in zip(rendered, sections):
                findings += lint_state(into, st.name, section, base, env)
                base += section.count(b"\n")
        outputs[into] = data

    if with_vanilla_idx:
        entries = vanilla_entries(game_dir)
        outputs[IDX_REL] = render_vanilla_idx(entries)
        result.idx = idx_stats(entries, outputs[IDX_REL])

    for rel in sorted(outputs):
        check_output_path(rel)
        findings += lint_file(rel, outputs[rel])
    return result


def _files_under(root):
    out = []
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            out.append(os.path.relpath(os.path.join(dirpath, n), root).replace(os.sep, "/"))
    return sorted(out)


def diff_dist(outputs, dist_mod=DIST_MOD, keep=(IDX_REL,)):
    """`[line]` naming every way dist_mod differs from `outputs`."""
    out = []
    for rel in sorted(outputs):
        path = os.path.join(dist_mod, *rel.split("/"))
        if not os.path.isfile(path):
            out.append("missing  %s" % rel)
            continue
        with open(path, "rb") as fh:
            if fh.read() != outputs[rel]:
                out.append("differs  %s" % rel)
    if os.path.isdir(dist_mod):
        for rel in _files_under(dist_mod):
            if rel not in outputs and rel not in keep:
                out.append("extra    %s" % rel)
    return out


def write_dist(outputs, dist_mod=DIST_MOD, keep=(IDX_REL,)):
    """Write `outputs` into dist_mod; remove files the build no longer makes.

    Every path passes `check_output_path` first, so nothing on the
    never-generate list is ever written. A file whose bytes are already right
    is left alone.
    """
    for rel in outputs:
        check_output_path(rel)
    changes = []
    for rel in sorted(outputs):
        path = os.path.join(dist_mod, *rel.split("/"))
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                if fh.read() == outputs[rel]:
                    continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(outputs[rel])
        changes.append(("wrote", rel))
    if os.path.isdir(dist_mod):
        for rel in _files_under(dist_mod):
            if rel not in outputs and rel not in keep:
                os.remove(os.path.join(dist_mod, *rel.split("/")))
                changes.append(("removed", rel))
        for dirpath, dirs, names in sorted(os.walk(dist_mod), reverse=True):
            if dirpath != dist_mod and not dirs and not names:
                os.rmdir(dirpath)
    return changes


# --------------------------------------------------------------- the host
def documents_dir():
    """The user's Documents folder from the known-folder API, not assembled.

    Documents moves when OneDrive backs it up or the user redirects it; the
    profile join is the fallback off Windows.
    """
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                            ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

            # FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
            fid = GUID(0xFDD39AD0, 0x238F, 0x46AF,
                       (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
            out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(
                    ctypes.byref(fid), 0, None, ctypes.byref(out)) == 0:
                path = out.value
                ctypes.windll.ole32.CoTaskMemFree(out)
                return path
        except Exception:                     # noqa: BLE001 - fall through
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")


def default_save_dir():
    """`<Documents>\\cossacks`, what GetAppSaveDirectoryPath returns in scripts."""
    return os.path.join(documents_dir(), "cossacks")


def _toolhelp_images():
    """Lower-case image names from a Toolhelp32 process snapshot (kernel32), in
    milliseconds where `tasklist` takes 0.42 s a call (measured 2026-10-05);
    raises OSError when the snapshot cannot be taken or read."""
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_wchar * 260)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)          # TH32CS_SNAPPROCESS
    if snap is None or snap == ctypes.c_void_p(-1).value:
        raise OSError("CreateToolhelp32Snapshot failed: %d" % ctypes.get_last_error())
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not k32.Process32FirstW(snap, ctypes.byref(entry)):
            raise OSError("Process32FirstW failed: %d" % ctypes.get_last_error())
        names = set()
        while True:
            names.add(entry.szExeFile.lower())
            if not k32.Process32NextW(snap, ctypes.byref(entry)):
                break
        return names
    finally:
        k32.CloseHandle(snap)


def _tasklist_images():
    out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
                         text=True, errors="replace", check=True).stdout
    names = set()
    for row in out.splitlines():
        if row.startswith('"'):
            names.add(row.split('","', 1)[0].strip('"').lower())
    return names


def running_images():
    """Lower-case image names of every running process: a Toolhelp32 snapshot,
    else `tasklist` (the only way until 2026-10-05).

    A failure to list processes is an error, never an empty set: an empty set
    would read as "the game is not running".
    """
    try:
        names = _toolhelp_images()
        if names:
            return names
    except (OSError, AttributeError, ValueError):
        pass
    try:
        return _tasklist_images()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BuildError("cannot list processes with tasklist: %s" % exc)


def game_processes():
    """The game's own images that are running now."""
    return sorted(set(GAME_IMAGES) & running_images())


def mod_folder(game_dir, name):
    """`<game>\\mods\\<name>`, refusing anything but one plain folder name there."""
    if (not name or name in (".", "..") or name != name.strip()
            or any(c in name for c in '\\/:*?"<>|')):
        raise DeployError("%r is not a plain folder name" % name)
    mods = os.path.abspath(os.path.join(game_dir, "mods"))
    path = os.path.abspath(os.path.join(mods, name))
    if os.path.dirname(path) != mods:
        raise DeployError("%r does not name a folder directly inside %s" % (name, mods))
    return path


def is_link(path):
    return os.path.islink(path) or (hasattr(os.path, "isjunction")
                                    and os.path.isjunction(path))


def _require_game_dir(game_dir):
    ini = os.path.join(game_dir, "mods", "mods.ini")
    if not os.path.isfile(ini):
        raise DeployError("%s has no mods\\mods.ini - not a game folder" % game_dir)


def _guard_host(save_dir):
    """Refusals shared by deploy and undeploy: game running, test lock held."""
    problems = []
    running = game_processes()
    if running:
        problems.append("running: %s" % ", ".join(running))
    lock = os.path.join(save_dir, LOCK_NAME)
    if os.path.exists(lock):
        problems.append("the test lock %s exists" % lock)
    return problems


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def deploy(dist_mod=DIST_MOD, game_dir=GAME, save_dir=None, dry_run=False, out=print,
           check_host=True):
    """Copy dist_mod to `<game>\\mods\\Quartermaster`, byte for byte."""
    _require_game_dir(game_dir)
    target = mod_folder(game_dir, MOD_NAME)
    if not os.path.isfile(os.path.join(dist_mod, "mod.ini")):
        raise DeployError("%s has no mod.ini - build first" % dist_mod)
    if os.path.lexists(target):
        raise DeployError("%s already exists - --undeploy first" % target)
    if check_host:
        problems = _guard_host(save_dir or default_save_dir())
        if problems:
            raise DeployError("refusing to deploy: " + "; ".join(problems))
    files = _files_under(dist_mod)
    out("%s %d file(s): %s -> %s" % ("would copy" if dry_run else "copying",
                                     len(files), dist_mod, target))
    for rel in files:
        out("  %s" % rel)
    if dry_run:
        return files
    shutil.copytree(dist_mod, target)
    for rel in files:
        a = os.path.join(dist_mod, *rel.split("/"))
        b = os.path.join(target, *rel.split("/"))
        if _sha256_file(a) != _sha256_file(b):
            raise DeployError("%s differs after the copy" % b)
    out("deployed; every file byte-identical to dist")
    return files


_PUBLISHED = re.compile(rb"(?m)^[ \t]*publishedfileid = ([0-9]+)[ \t]*\r?$")


def update(dist_mod=DIST_MOD, game_dir=GAME, save_dir=None, dry_run=False, out=print,
           check_host=True):
    r"""Put a new build into an existing `<game>\mods\Quartermaster` and keep
    its mod.ini byte for byte - unless it names no Workshop item
    (publishedfileid 0), when dist's takes its place.

    Once the folder has been published through the game's Mod Manager, its
    mod.ini is the one that names the Workshop item: a subscribed item's
    mod.ini carries its publishedfileid, owner and times
    (workshop\content\333420\873048118\mod.ini:2-9), where dist's has 0
    (mod_ini). --undeploy then --deploy would replace it, and the next upload
    would make a second Workshop item instead of a new version of the first.
    Which keys the Mod Manager writes into the local file on an upload is not
    known yet, so none is edited: the whole file stays as it is. While a
    folder in mods\ names the item, the game never registers the subscribed
    copy (docs/research/context-2026-09-27.md, runs wsclaim1/wsplain1): the
    note below says so, since a test of the Workshop copy needs this folder
    out of mods\ and an update needs it back.

    Every other file is dist's, and a file dist does not have is removed: the
    outputs Quartermaster writes into its own folder while the game runs are
    the player's merges and must not go up with an upload. The new folder is
    made next to dist first, so the kept mod.ini is on disk at every step."""
    _require_game_dir(game_dir)
    target = mod_folder(game_dir, MOD_NAME)
    if not os.path.isfile(os.path.join(dist_mod, "mod.ini")):
        raise DeployError("%s has no mod.ini - build first" % dist_mod)
    if not os.path.lexists(target):
        raise DeployError("%s does not exist - --deploy first" % target)
    if is_link(target) or not os.path.isdir(target):
        raise DeployError("%s is not a plain folder; refusing to update it" % target)
    if not os.path.isfile(os.path.join(target, "data", "quartermaster", "core.aix")):
        raise DeployError("%s has no data\\quartermaster\\core.aix: not Quartermaster" % target)
    kept_path = os.path.join(target, "mod.ini")
    if not os.path.isfile(kept_path):
        raise DeployError("%s has no mod.ini to keep" % target)
    if check_host:
        problems = _guard_host(save_dir or default_save_dir())
        if problems:
            raise DeployError("refusing to update: " + "; ".join(problems))
    with open(kept_path, "rb") as fh:
        kept = fh.read()
    m = _PUBLISHED.search(kept)
    published = m.group(1).decode("ascii") if m else None
    files = _files_under(dist_mod)
    # A mod.ini with publishedfileid 0 names no Workshop item: there is nothing
    # in it to keep, and dist's carries the current title, description and
    # change note (2026-10-01: the installed one still had the build's old
    # placeholders). Any other mod.ini, one without the key too, stays.
    fresh = published == "0"
    if fresh:
        with open(os.path.join(dist_mod, "mod.ini"), "rb") as fh:
            kept = fh.read()
    out("%s %d file(s): %s -> %s, mod.ini %s (publishedfileid %s)"
        % ("would update" if dry_run else "updating", len(files), dist_mod, target,
           "from dist" if fresh else "kept", published if published is not None else "missing"))
    if published in (None, "0"):
        out("note: this mod.ini names no Workshop item yet: an upload makes a new one")
    else:
        out("note: while mods\\%s names Workshop item %s, the game does not load the "
            "subscribed copy" % (MOD_NAME, published))
    if dry_run:
        return files
    stage = os.path.join(os.path.dirname(os.path.abspath(dist_mod)), MOD_NAME + ".update")
    if os.path.lexists(stage):
        raise DeployError("%s is left from an earlier update - look at it, then remove it"
                          % stage)
    shutil.copytree(dist_mod, stage)
    with open(os.path.join(stage, "mod.ini"), "wb") as fh:
        fh.write(kept)
    shutil.rmtree(target)
    shutil.move(stage, target)
    for rel in files:
        b = os.path.join(target, *rel.split("/"))
        want = (hashlib.sha256(kept).hexdigest() if rel == "mod.ini"
                else _sha256_file(os.path.join(dist_mod, *rel.split("/"))))
        if _sha256_file(b) != want:
            raise DeployError("%s differs after the update" % b)
    if sorted(_files_under(target)) != sorted(files):
        raise DeployError("%s holds other files than dist after the update" % target)
    out("updated; every file byte-identical to dist, mod.ini %s"
        % ("dist's too" if fresh else "as it was"))
    return files


def undeploy(game_dir=GAME, save_dir=None, dry_run=False, out=print, folder=MOD_NAME,
             check_host=True):
    """Remove `<game>\\mods\\Quartermaster` and nothing else."""
    if folder != MOD_NAME:
        raise DeployError("--undeploy removes mods\\%s and nothing else, not %r"
                          % (MOD_NAME, folder))
    _require_game_dir(game_dir)
    target = mod_folder(game_dir, folder)
    if not os.path.lexists(target):
        out("nothing to remove: %s does not exist" % target)
        return False
    if is_link(target) or not os.path.isdir(target):
        raise DeployError("%s is not a plain folder; refusing to remove it" % target)
    if check_host:
        problems = _guard_host(save_dir or default_save_dir())
        if problems:
            raise DeployError("refusing to undeploy: " + "; ".join(problems))
    out("%s %s" % ("would remove" if dry_run else "removing", target))
    if dry_run:
        return False
    shutil.rmtree(target)
    return True


# -------------------------------------------------------------------- CLI
def _report_build(result, out):
    out("states: %d, lint environment: %s"
        % (len(result.states),
           ", ".join("%s %d" % kv for kv in sorted(result.lint_env.items()))
           or "offline (identifier resolution skipped)"))
    for name, into, source in result.states:
        out("  %-12s -> %s  (from %s)" % (name, into, source))
    for rel in sorted(result.outputs):
        data = result.outputs[rel]
        out("  emitted %-36s %9d bytes %6d lines" % (rel, len(data), data.count(b"\n")))
    if result.idx:
        c = result.idx["classes"]
        out("  vanilla.idx: %d entries (never %d, merge %d, wta %d)"
            % (result.idx["entries"], c["never"], c["merge"], c["wta"]))
    out("lint findings: %d" % len(result.findings))
    for f in result.findings:
        out("  " + str(f))


def main(argv=None, out=print):
    p = argparse.ArgumentParser(prog="hbuild.py",
                                description=__doc__.split("\n\n")[0])
    p.add_argument("--vanilla-idx", action="store_true",
                   help="regenerate data/quartermaster/vanilla.idx from <game>\\data")
    p.add_argument("--check", action="store_true",
                   help="build in memory and compare with dist; write nothing")
    p.add_argument("--offline", action="store_true",
                   help="skip the lints that need the installed game")
    p.add_argument("--deploy", action="store_true")
    p.add_argument("--undeploy", action="store_true")
    p.add_argument("--update", action="store_true",
                   help="put a new build into mods\\Quartermaster, keeping its mod.ini "
                        "(the Workshop item's id after an upload)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--game-dir", default=GAME)
    p.add_argument("--save-dir", default=None)
    p.add_argument("--src", default=SRC, help=argparse.SUPPRESS)
    p.add_argument("--dist", default=DIST_MOD, help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    try:
        if (a.deploy + a.undeploy + a.update) > 1:
            raise BuildError("--deploy, --undeploy and --update are one at a time")
        if a.update:
            update(a.dist, a.game_dir, a.save_dir, a.dry_run, out)
            return 0
        if a.deploy:
            deploy(a.dist, a.game_dir, a.save_dir, a.dry_run, out)
            return 0
        if a.undeploy:
            undeploy(a.game_dir, a.save_dir, a.dry_run, out)
            return 0
        if a.vanilla_idx and a.offline:
            raise BuildError("--vanilla-idx reads the installed game; drop --offline")
        result = build(a.src, a.game_dir, a.offline, a.vanilla_idx)
        _report_build(result, out)
        if result.findings:
            out("BUILD FAILED: %d lint finding(s); nothing written" % len(result.findings))
            return 1
        if a.check:
            diff = diff_dist(result.outputs, a.dist)
            for line in diff:
                out("  " + line)
            out("dist is up to date" if not diff else "dist differs: %d file(s)" % len(diff))
            return 0 if not diff else 1
        if a.dry_run:
            for line in diff_dist(result.outputs, a.dist):
                out("  would change: " + line)
            return 0
        changes = write_dist(result.outputs, a.dist)
        for action, rel in changes:
            out("  %s %s" % (action, rel))
        if not os.path.isfile(os.path.join(a.dist, *IDX_REL.split("/"))):
            out("note: %s is missing - run with --vanilla-idx" % IDX_REL)
        out("dist/%s: %d change(s)" % (MOD_NAME, len(changes)))
        return 0
    except BuildError as exc:
        out("hbuild: %s" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
