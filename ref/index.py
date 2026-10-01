r"""The mod index (docs/plan.md G3): which mod ships which vanilla path.

The game side (src/states/qmmodlist.pas, qmindexbegin.pas, qmindexstep.pas,
qmfingerprint.pas) and this twin compute the same things from the same inputs;
tools/qmtest.py compares a game-side dump with them line for line.

Mod list
--------
`ModLibraryGetData(libind; var tag, dir, last, tit, ownid, desc, tags, url,
note: string; var numf, vis: integer; var dis, acc, ban, root: boolean)` is
the engine's only per-mod call (cossacks.exe registration table; called the
same way at data/gui/menu.inc/showmainmenu.inc:186 and
data/scripts/lib/init.script:172). It lists every registered mod, disabled
ones too, in mods.ini order. What each field holds, as far as the shipped
scripts show:

  dir   `mods\<folder>` or `..\..\workshop\content\333420\<id>`, relative to
        the game folder (mods\mods.ini:4,8).
  dis   True when the mod is off (init.script:173 skips those).
  tag   the Workshop id; '0' for a local mod (showmainmenu.inc:190 names a
        `tag='0'` mod by folder; showconnectstatemessage.inc:166-170 treats a
        tag other than '0' as a Workshop item to sync).
  tit   the title; `last` is what the menu shows for a mod without one.

There is no timeupdated among them (it is in a Workshop item's mod.ini, which
would need one more parser load per mod), so Workshop and local mods get the
same kind of stamp here: the FileAge of the files they provide (below). A
Workshop update rewrites the files it changes, so their FileAge moves with it.

Origin: `w` a Workshop item, `l` a local folder, `c` a local folder whose tag
is a Workshop id - a local copy of a Workshop item, `o` anything else the
engine might list. Quartermaster's own folder is `s`.

Quartermaster finds its own folder as the last enabled mod that has
`data\quartermaster\core.aix`: the hook loads core.aix through the overlay
(`StateMachineLoadFromFile` of `.\data\quartermaster\core.aix`; loading a
mod's `.aix` that way ran its code in probe 1), and the overlay serves the
copy of the last enabled mod that has the file ("same file in two mods: last
in mods.ini wins", docs/research/context-2026-09-27.md section 3). FileAge
itself ignores the overlay (docs/research/m0-probes.md, probe 5), so asking
it about `<dir>\data\...` tests exactly that folder. A folder name is not
used, so a renamed or Workshop-installed Quartermaster finds itself the same
way.

Scan
----
The index does not look at every one of the 17001 vanilla.idx paths. It scans
the paths a decision of Phase A depends on (`scan_entries`):

  * the `merge` class of vanilla.idx - the S3 allow-list, the only paths
    Quartermaster ever writes a merge for (311 today);
  * the hook files of plan S5 (all four are in the merge class today; they are
    named anyway, so a narrower allow-list cannot drop them);
  * the Phase B data profiles and dmscript.global, so a Phase A report already
    names the winner of each (hotkeys.cfg is one of the WASD test files).

Everything else is winner-takes-all by rule (plan S2): whoever ships it, the
engine's overlay decides and Quartermaster writes nothing, so scanning it
changes no output. Its only use would be a longer report, which can scan more
later without touching this path. At the measured cost (3000 FileAge calls
in 27-51 ms, docs/research/m0-probes.md probe 5) the scan is 316 calls per
enabled mod - a few ms.

For every scanned path and every enabled mod other than Quartermaster, the
game asks `FileAge(<dir>\data\<path>)`; anything but -1 means the mod ships it.
Quartermaster's own folder is never asked: it provides exactly the hook files
it ships (`shipped_hooks`), known when it was built. Asking would count its
generated outputs as inputs and restart the game forever (plan S8, guard 2).

Any other mod that ships `data\quartermaster\core.aix` is a second copy of
Quartermaster (a Workshop copy next to a local one, say) and is not scanned
either: as an ordinary mod it would bring its own hook files and its
generated outputs in as merge inputs, the hook lines would be merged in twice
and every hook file would fall back to winner+hook. It stays in the mod list
and the fingerprint (enabled, no stamp), so switching it on or off still
counts as a change of inputs.

Stamps (fingerprint inputs, plan S8)
------------------------------------
  mod stamp      qhash of `<path> <FileAge>\n` over the scanned paths the mod
                 provides, in scan order. A Workshop update or a local edit of
                 a file Quartermaster reads changes it; nothing else does.
  vanilla stamp  qhash of `<path> <FileAge>\n` over every scanned path with a
                 provider, of the pristine vanilla copy (absolute path, not
                 through the overlay), followed by `exe <FileAge>\n` of
                 cossacks.exe - a GSC patch changes the merge bases or the exe.

FileAge is the local file time as a DOS date-time (2 s steps), which is fine
for a fingerprint that never leaves the machine (plan S12 keeps it out of the
MP data constant). `dos_age` is the Python side of it.
"""
import math
import time

from .fingerprint import fingerprint_text, qhash
from .order import LOCAL, OTHER, WORKSHOP, canonical_key, identity
from .planner import ADDITIVE_GLOBAL, HOOK_FILES, MERGE_CLASS, PHASE_B_DATA

__all__ = ["CORE_AIX", "ORIGIN_WORKSHOP", "ORIGIN_LOCAL", "ORIGIN_COPY",
           "ORIGIN_OTHER", "ORIGIN_SELF", "Mod", "origin", "find_self",
           "canonical_positions", "load_positions", "scan_entries", "index_key", "Index",
           "scanned_mods", "build_index", "vanilla_stamp", "fingerprint_mods", "fingerprint",
           "without", "known_fingerprint", "dos_age"]

#: The file whose presence marks a Quartermaster folder.
CORE_AIX = b"data\\quartermaster\\core.aix"

ORIGIN_WORKSHOP, ORIGIN_LOCAL, ORIGIN_COPY = b"w", b"l", b"c"
ORIGIN_OTHER, ORIGIN_SELF = b"o", b"s"


class Mod(object):
    """One row of ModLibraryGetData, the fields the index uses."""

    __slots__ = ("dir", "enabled", "tag", "title", "last")

    def __init__(self, dir, enabled, tag=b"0", title=b"", last=b""):
        self.dir = dir
        self.enabled = enabled
        self.tag = tag
        self.title = title
        self.last = last

    def __repr__(self):
        return "Mod(%r, %s)" % (self.dir, "on" if self.enabled else "off")


def origin(mod, is_self=False):
    """`w`, `l`, `c`, `o` or `s` for one mod (see the module docstring)."""
    if is_self:
        return ORIGIN_SELF
    kind, _ident = identity(mod.dir)
    if kind == WORKSHOP:
        return ORIGIN_WORKSHOP
    if kind == LOCAL:
        return ORIGIN_COPY if mod.tag not in (b"", b"0") else ORIGIN_LOCAL
    return ORIGIN_OTHER


def find_self(mods, has_core):
    """Index of Quartermaster's own mod, or -1.

    `has_core(dir)`: the game's `FileAge(dir+'\\data\\quartermaster\\core.aix')<>-1`.
    """
    found = -1
    for i, m in enumerate(mods):
        if m.enabled and has_core(m.dir):
            found = i
    return found


def canonical_positions(mods, self_index):
    """`pos[i]`: mod i's place in canonical order (`ref.order`), 0-based.

    Ties are broken by the input position, exactly as `canonical_order` does,
    so the result is a permutation even for two spellings of one folder.
    """
    self_dir = mods[self_index].dir if self_index >= 0 else None
    keyed = sorted((canonical_key(m.dir, self_dir), i) for i, m in enumerate(mods))
    pos = [0] * len(mods)
    for rank, (_key, i) in enumerate(keyed):
        pos[i] = rank
    return pos


def load_positions(mods, self_index, rows=None):
    """`pos[i]`: mod i's place in load order - `rows` as ref.order load_order
    gives them (LoadOrder.rows), None for the canonical order (no saved
    order, plan S11). The game side's qmOrder rewrites qm_mods
    pos<i> / ord<k> to it before the index runs, so every position after it
    (providers, the plan's winner, the stamps) is a load position."""
    if rows is None:
        return canonical_positions(mods, self_index)
    pos = [0] * len(mods)
    for rank, i in enumerate(rows):
        pos[i] = rank
    return pos


def scan_entries(entries, hook_files=HOOK_FILES):
    """The vanilla.idx rows the index scans, in vanilla.idx order."""
    named = set(hook_files) | set(PHASE_B_DATA) | {ADDITIVE_GLOBAL}
    return [e for e in entries if e[3] == MERGE_CLASS or e[0] in named]


def index_key(path):
    r"""The named-parser key a path is looked up by (qm_index_keys on the game side).

    The engine's parser folds the case of keys and trims them (capability
    probes, 2026-09-28), so a key must be identifier-like: `k`, then a..z and
    0..9 as they are, `\` as `_s`, `.` as `_d`, `_` as `__`, any other byte as
    `_x` and two hex digits. Every `_` starts one of those codes, so the
    encoding is injective and two paths never share a key. The game side's
    qmIdxKey (src/lib/qmidxkey.pas) is the same function.
    """
    out = bytearray(b"k")
    for c in path:
        if 97 <= c <= 122 or 48 <= c <= 57:
            out.append(c)
        elif c == 92:
            out += b"_s"
        elif c == 46:
            out += b"_d"
        elif c == 95:
            out += b"__"
        else:
            out += b"_x%02x" % c
    return bytes(out)


class Index(object):
    """What the scan found.

    providers  path -> mod indices that ship it, in load order
    ages       path -> the FileAge of each provider's copy (None for Quartermaster)
    stamps     mod index -> stamp, for every enabled mod but Quartermaster
    """

    def __init__(self, scanned, providers, ages, stamps, calls):
        self.scanned = scanned
        self.providers = providers
        self.ages = ages
        self.stamps = stamps
        self.calls = calls

    def by_dir(self, mods):
        """path -> provider dirs, the shape `ref.planner.plan` takes."""
        return {p: [mods[i].dir for i in v] for p, v in self.providers.items()}


def scanned_mods(mods, self_index, has_core=None, pos=None):
    """Indices of the mods the index scans, in load order (`pos`, default
    canonical): every enabled mod but Quartermaster and any other copy of it
    (`has_core(dir)`, the game's
    `FileAge(dir+'\\data\\quartermaster\\core.aix')<>-1`)."""
    if pos is None:
        pos = canonical_positions(mods, self_index)
    order = sorted(range(len(mods)), key=lambda i: pos[i])
    return [i for i in order if mods[i].enabled and i != self_index
            and not (has_core is not None and has_core(mods[i].dir))]


def build_index(mods, self_index, entries, age, shipped_hooks=(), has_core=None, pos=None):
    """Scan `scan_entries(entries)` over every enabled mod.

    `age(dir, path)` is the game's `FileAge(dir+'\\data\\'+path)`: -1 when the
    file is missing. `shipped_hooks` are the hook paths Quartermaster ships.
    `has_core(dir)`: the mod ships data\\quartermaster\\core.aix; such a mod
    other than Quartermaster itself is not scanned (`scanned_mods`). `pos`:
    the load positions (`load_positions`), default canonical.
    """
    active = scanned_mods(mods, self_index, has_core, pos)
    scanned = scan_entries(entries)
    providers, ages = {}, {}
    text = dict((i, bytearray()) for i in active)
    calls = 0
    for path, _size, _lines, _cls in scanned:
        got, got_age = [], []
        for i in active:
            a = age(mods[i].dir, path)
            calls += 1
            if a != -1:
                got.append(i)
                got_age.append(a)
                text[i] += path + b" %d\n" % a
        if self_index >= 0 and path in shipped_hooks:
            got.append(self_index)
            got_age.append(None)
        if got:
            providers[path] = got
            ages[path] = got_age
    stamps = dict((i, qhash(bytes(t))) for i, t in text.items())
    return Index([e[0] for e in scanned], providers, ages, stamps, calls)


def vanilla_stamp(index, vanilla_age, exe_age):
    """qhash over the pristine copies of every provided path, then the exe."""
    text = bytearray()
    for path in index.scanned:
        if path in index.providers:
            text += path + b" %d\n" % vanilla_age(path)
    text += b"exe %d\n" % exe_age
    return qhash(bytes(text))


def fingerprint_mods(mods, self_index, index):
    """`[(dir, enabled, stamp)]` for `ref.fingerprint`: a stamp only when enabled."""
    return [(m.dir, m.enabled, index.stamps.get(i, b"") if m.enabled else b"")
            for i, m in enumerate(mods) if i != self_index]


def fingerprint(mods, self_index, index, vstamp, qm_version, pos=None):
    """`(text, hash)` of the start-up fingerprint (plan S8); `pos` the load
    positions, default canonical."""
    self_dir = mods[self_index].dir if self_index >= 0 else None
    order = None
    if pos is not None:
        order = [mods[i].dir for i in sorted(range(len(mods)), key=lambda i: pos[i])]
    text = fingerprint_text(fingerprint_mods(mods, self_index, index), vstamp,
                            qm_version, self_dir, order)
    return text, qhash(text)


def without(index, fresh):
    """The index without the mods in `fresh` (mod indices): their hits
    dropped, a path only they provide not provided, their stamps gone - what
    the scan found before the engine registered them."""
    providers, ages = {}, {}
    for path, provs in index.providers.items():
        keep = [k for k, i in enumerate(provs) if i not in fresh]
        if keep:
            providers[path] = [provs[k] for k in keep]
            ages[path] = [index.ages[path][k] for k in keep]
    stamps = dict((i, s) for i, s in index.stamps.items() if i not in fresh)
    return Index(index.scanned, providers, ages, stamps, index.calls)


def known_fingerprint(mods, self_index, index, vanilla_age, exe_age, qm_version, fresh,
                      pos=None):
    """`(text, hash)` of the fingerprint without the mods the engine
    registered at this start (`fresh`, mod indices; ref/boot.py fresh): the
    one the previous boot computed when nothing else moved. The loop rule
    (ref/boot.py restart_plan) compares it with the marker. A path stays in
    the vanilla stamp while a provider that is not such a mod ships it."""
    gone = set(fresh)
    kept = without(index, gone)
    vstamp = vanilla_stamp(kept, vanilla_age, exe_age)
    self_dir = mods[self_index].dir if self_index >= 0 else None
    order = None
    if pos is not None:
        order = [mods[i].dir for i in sorted(range(len(mods)), key=lambda i: pos[i])]
    rows = [(m.dir, m.enabled, kept.stamps.get(i, b"") if m.enabled else b"")
            for i, m in enumerate(mods) if i != self_index and i not in gone]
    text = fingerprint_text(rows, vstamp, qm_version, self_dir, order)
    return text, qhash(text)


def dos_age(mtime, localtime=time.localtime):
    """What the game's FileAge answers for a file modified at `mtime`.

    A DOS date-time of the local time, and Windows rounds a time between two
    even seconds up, not down: the vanilla oncamera.inc, modified at
    15:15:56.316 on 2026-08-24, read as 1561885181 in-game on 2026-09-27
    (seconds field 29, i.e. :58). Rounding the epoch time up to an even second
    first also carries into the minute. Informational only: the game uses the
    DST offset of today for every file, Python the one of the file's date.
    """
    t = localtime(math.ceil(mtime / 2.0) * 2)
    return (((t.tm_year - 1980) << 25) | (t.tm_mon << 21) | (t.tm_mday << 16)
            | (t.tm_hour << 11) | (t.tm_min << 5) | (t.tm_sec // 2))
