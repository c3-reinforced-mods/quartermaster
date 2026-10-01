r"""Canonical mod order (docs/plan.md S11) and the load order built on it.

The order a merge sees its participants in decides every conflict ("later wins").
Phase A made it canonical - never how the player happened to arrange modman - so
that the same set of mods gives the same order on every machine, in SP and MP.
That was revised after the Phase A check (2026-09-28): the player
sets the order by hand in the manager and Quartermaster keeps it (the load
order, at the end of this module). The canonical order stayed the default until
2026-09-30: as a default it changed which mod wins every whole file two
mods ship, and a set that starts without Quartermaster stopped at "Error
compiling scripts" with it (Cannons + State vs Country). The default is now the
order mods.ini has; the canonical order below is what Auto-sort gives. The same
order on every machine in MP is the players' responsibility, as it is without
Quartermaster, and the report says so when it is not the canonical one.

A mod is identified by its `dir` as the engine lists it (`ModLibraryGetData`,
and `mods\mods.ini` in the game folder, lines 4 and 8 today):

    ..\..\workshop\content\333420\873048118   a Workshop item: its id
    mods\SW_Frontline_Protocol                 a local folder: its name

Sort key, smallest first:

  1. Workshop items, by id as a number. The id is compared as a zero-padded
     string, so that no id ever has to fit the game side's 32-bit Integer.
  2. Local folders, by name, ASCII case folded (Windows folder names are case
     insensitive; the engine's `StrToLowerCase` is not trusted beyond ASCII).
  3. Anything else the engine may list, by its whole dir, case folded.
  4. Quartermaster itself, always last - it carries the hook lines and must be
     the final override.

Local after Workshop is a default, not a derived fact: a local folder is the
player's own work or a local copy, which should win over a subscription. Ties
(the same name in two spellings) fall back to the raw bytes, then to the input
position, so the result is always a total order.
"""

__all__ = ["WORKSHOP_DIR", "LOCAL_DIR", "WORKSHOP", "LOCAL", "OTHER", "SELF",
           "ascii_lower", "norm_dir", "identity", "canonical_key", "canonical_order",
           "canonical_indices", "TRUE", "FALSE", "is_off", "render_mods_ini",
           "parse_mods_ini", "canonical_rows", "IniPlan", "moved_past", "mods_ini_plan",
           "enabled_order",
           "needs_restart", "ini_changes", "ORDER_REL", "ORDER_KEYS", "ORDER_FORMAT",
           "order_values", "render_order", "parse_order", "LoadOrder", "load_order",
           "apply_order", "load_rows", "order_file_after", "UI_UNKNOWN", "UI_SELECT",
           "UI_SELF", "UI_INACTIVE", "UI_FIRST", "UI_LAST", "ui_move"]

WORKSHOP_DIR = b"..\\..\\workshop\\content\\333420\\"
LOCAL_DIR = b"mods\\"

WORKSHOP, LOCAL, OTHER, SELF = 0, 1, 2, 3

_ID_WIDTH = 20


def ascii_lower(data):
    return bytes(c + 32 if 65 <= c <= 90 else c for c in data)


def _norm_dir(d):
    return ascii_lower(d.replace(b"/", b"\\")).rstrip(b"\\")


def norm_dir(d):
    """A dir as Quartermaster compares it: slashes as backslashes, no trailing
    backslash, ASCII case folded (Windows folder names are case-insensitive)."""
    return _norm_dir(d)


def identity(d):
    """`(origin, id)` of a mod dir: `(WORKSHOP, b'873048118')`, `(LOCAL, name)`."""
    low = _norm_dir(d)
    if low.startswith(WORKSHOP_DIR):
        rest = d.replace(b"/", b"\\").rstrip(b"\\")[len(WORKSHOP_DIR):]
        if rest.isdigit():
            return WORKSHOP, rest
    if low.startswith(LOCAL_DIR):
        rest = d.replace(b"/", b"\\").rstrip(b"\\")[len(LOCAL_DIR):]
        if rest and b"\\" not in rest:
            return LOCAL, rest
    return OTHER, d


def canonical_key(d, self_dir=None):
    if self_dir is not None and _norm_dir(d) == _norm_dir(self_dir):
        return (SELF, b"", d)
    origin, ident = identity(d)
    if origin == WORKSHOP:
        return (WORKSHOP, ident.lstrip(b"0").rjust(_ID_WIDTH, b"0"), d)
    return (origin, ascii_lower(ident), d)


def canonical_order(dirs, self_dir=None):
    """`dirs` sorted canonically; `self_dir` (Quartermaster's own dir) last."""
    return [dirs[i] for i in canonical_indices(dirs, self_dir)]


def canonical_indices(dirs, self_dir=None):
    """The indices of `dirs` in canonical order (ties by input position)."""
    keyed = [(canonical_key(d, self_dir), i) for i, d in enumerate(dirs)]
    keyed.sort()
    return [i for _key, i in keyed]



# ------------------------------------------------------------------ mods.ini
r"""mods.ini (plan S11, G5): the twin of src/states/qmorder.pas and
src/states/qmmodsini.pas.

The engine writes `<G>\mods\mods.ini` at every start in this layout (the file
it wrote during the capability-probe run, docs/research/m0-probes.md, last
section - an appended folder, dis = False - and an installed
mods\mods.ini; tests/test_m5_order.py rebuilds both byte for byte):

    section.begin
       mods : struct.begin
          [*] : struct.begin
             dir = mods\SW_Frontline_Protocol
             dis = True
          struct.end
          ...
       struct.end
    section.end
    <empty line>

Quartermaster rewrites it the way probe 5 did and the game honoured after the
restart (docs/research/context-2026-09-27.md section 3: "Rewriting mods.ini
from script (parser, path ModLibraryGetIniFile) + restart: honored, not
overwritten"): load it with the engine's
parser from ModLibraryGetIniFile, set `dir` and `dis` in the entries that are
there, save it with ParserSaveToFileByHandle. No entry is added or dropped -
only the values of the existing nodes move - so whatever else the engine
keeps in the file stays where it is. The parser drops trailing spaces from
values, which no dir the engine lists can have (Windows strips them from
folder names).

The rewrite is refused, and mods.ini left alone, unless every entry is
exactly `dir` + `dis`, `dis` reads True or False, and the dirs are the
engine's own list (ModLibraryGetData) as a set - so a file Quartermaster
does not understand, or one another program changed since the start, is
never reordered. It is skipped when the rows are already the wanted ones
(plan S8: "mods.ini rewritten only if its content differs").

The wanted rows: every registered mod in load order (`load_rows`; with no
saved order that is mods.ini's own order, Quartermaster last), each with its own
`dis` text as the file has it; the UI's Apply (docs/ui.md, qm_rt uiapply*)
changes the flags it names, never Quartermaster's own, and may bring a new
order (qm_rt uiapplyord<k>, `apply_order`). A restart is needed when the effective order changes:
the enabled mods, in order, as the engine loaded them versus as the new file
lists them (disabled ones decide nothing: the overlay skips them).
"""

TRUE, FALSE = b"True", b"False"


def is_off(dis):
    """`dis` text -> the mod is off. The engine writes True / False."""
    return dis.lower() == b"true"


def render_mods_ini(rows):
    """The engine's mods.ini for `rows` = [(dir, dis text)]."""
    out = [b"section.begin", b"   mods : struct.begin"]
    for d, dis in rows:
        out += [b"      [*] : struct.begin", b"         dir = " + d,
                b"         dis = " + dis, b"      struct.end"]
    out += [b"   struct.end", b"section.end", b""]
    return b"".join(line + b"\r\n" for line in out)


def _ini_entries(data):
    """`(entries, problem)`: each entry as {key: value} the way the parser
    hands them over (keys folded, trailing spaces of values dropped), or
    `(None, 'missing' | 'layout')` - no file, or not the layout above."""
    if data is None:
        return None, b"missing"
    lines = [ln.strip(b" \t") for ln in data.replace(b"\r\n", b"\n").split(b"\n")]
    while lines and lines[-1] == b"":
        lines.pop()
    if lines[:2] != [b"section.begin", b"mods : struct.begin"] or lines[-2:] != [
            b"struct.end", b"section.end"]:
        return None, b"layout"
    body = lines[2:-2]
    entries = []
    i = 0
    while i < len(body):
        if body[i] != b"[*] : struct.begin" or b"struct.end" not in body[i:]:
            return None, b"layout"
        j = body.index(b"struct.end", i)
        keys = []
        for kv in body[i + 1:j]:
            k, sep, v = kv.partition(b" =")
            if not sep:
                return None, b"layout"
            keys.append((k.strip().lower(), v.strip(b" ")))
        entries.append(keys)
        i = j + 1
    return entries, None


def parse_mods_ini(data):
    """`(rows, problem)`: [(dir, dis text)], or `(None, why)` when the file
    is not in the layout above or an entry is not exactly dir + dis."""
    entries, problem = _ini_entries(data)
    if problem is not None:
        return None, problem
    rows = []
    for keys in entries:
        d = dict(keys)
        if len(keys) != 2 or set(d) != {b"dir", b"dis"}:
            return None, b"entry"
        rows.append((d[b"dir"], d[b"dis"]))
    return rows, None


def canonical_rows(ini_rows, self_dir, intent=None):
    """The wanted rows: `ini_rows` in canonical order, each dir with its own
    dis text; `intent` = {norm_dir: off} from a confirmed Apply changes the
    flags it names (never Quartermaster's own)."""
    dis_of = dict((norm_dir(d), dis) for d, dis in ini_rows)
    out = []
    for d in canonical_order([d for d, _dis in ini_rows], self_dir):
        dis = dis_of[norm_dir(d)]
        key = norm_dir(d)
        if intent is not None and key in intent and key != norm_dir(self_dir or b""):
            if intent[key] != is_off(dis):
                dis = TRUE if intent[key] else FALSE
        out.append((d, dis))
    return out


def enabled_order(rows):
    """The enabled dirs of `rows` = [(dir, dis text)], in order, folded."""
    return [norm_dir(d) for d, dis in rows if not is_off(dis)]


class IniPlan(object):
    __slots__ = ("action", "why", "rows", "effective", "over")

    def __init__(self, action, why, rows, effective, over=None):
        self.action, self.why, self.rows, self.effective = action, why, rows, effective
        self.over = over

    def __repr__(self):
        return "IniPlan(%r, %r, effective=%r, over=%r, %d rows)" % (
            self.action, self.why, self.effective, self.over, len(self.rows or []))


def moved_past(before, after, self_key):
    """The enabled dirs Quartermaster moved past (folded, in order) when only
    its own place in the enabled order changed from `before` to `after`: the
    ones between its old and its new place. None when anything else moved
    too, nothing moved, or it is not enabled in both (qm_ini selfonly / over<j>)."""
    if before == after or self_key not in before or self_key not in after:
        return None
    rest = [d for d in before if d != self_key]
    if rest != [d for d in after if d != self_key]:
        return None
    b, a = before.index(self_key), after.index(self_key)
    return rest[min(a, b):max(a, b)]


def mods_ini_plan(engine_rows, ini_data, wanted, limit=256, self_dir=None):
    """What qmModsIni does with `wanted` = [(dir, dis text)]: `same`,
    `write` or `refused` (why, in the order the game checks: count, missing,
    layout, entry, dis, dirs; readback is the game's own check after a save).

    `engine_rows` = [(dir, loaded)] as ModLibraryGetData lists them, with the
    flag the running game loaded: the set of dirs the file must hold, and the
    enabled order `effective` compares the new rows with. The rows written
    keep the file's own spelling of a flag that does not change. `over`: the
    mods Quartermaster (`self_dir`) moved past when only its place changed
    (`moved_past`)."""
    n = len(engine_rows)
    if n > limit or len(wanted) != n:
        return IniPlan(b"refused", b"count", None, False)
    entries, problem = _ini_entries(ini_data)
    if problem is not None:
        return IniPlan(b"refused", problem, None, False)
    if len(entries) != n:
        return IniPlan(b"refused", b"count", None, False)
    file_rows = []
    for k in range(n):
        d = dict(entries[k])
        fdir, fdis = d.get(b"dir", b""), d.get(b"dis", b"")
        if len(entries[k]) != 2 or fdir == b"":
            return IniPlan(b"refused", b"entry", None, False)
        if fdis.lower() not in (b"true", b"false"):
            return IniPlan(b"refused", b"dis", None, False)
        if wanted[k][1].lower() not in (b"true", b"false"):
            return IniPlan(b"refused", b"dis", None, False)
        file_rows.append((fdir, fdis))
    engine = [norm_dir(d) for d, _on in engine_rows]
    for e in engine:
        if (sum(1 for d, _x in file_rows if norm_dir(d) == e) != 1
                or sum(1 for d, _x in wanted if norm_dir(d) == e) != 1):
            return IniPlan(b"refused", b"dirs", None, False)
    spelled = dict((norm_dir(d), dis) for d, dis in file_rows)
    rows = []
    for d, dis in wanted:
        have = spelled[norm_dir(d)]
        rows.append((d, have if have.lower() == dis.lower() else dis))
    before = [norm_dir(d) for d, on in engine_rows if on]
    after = enabled_order(rows)
    effective = before != after
    over = None if self_dir is None else moved_past(before, after, norm_dir(self_dir))
    if file_rows == rows:
        return IniPlan(b"same", b"-", rows, effective, over)
    return IniPlan(b"write", b"-", rows, effective, over)


def needs_restart(plan, ships=None):
    """Does mods.ini ask for a restart (qmGuard's `modsini`)? The file holds
    the wanted rows - written now or already there - and their enabled order
    is not the one the running game loaded.

    Not when only Quartermaster's own place changed and none of the mods it
    moved past `ships(dir)` - a path the index read, or a file Quartermaster
    ships that the index does not read (the guard's resource.script, its
    core.aix): with no file in common the order between them decides nothing
    a restart would change. A folder made with New mod, registered after
    Quartermaster at the next start, cost a restart for that (logs of
    2026-10-01)."""
    if not (plan.action in (b"same", b"write") and plan.effective):
        return False
    if plan.over is not None and ships is not None and not any(ships(d) for d in plan.over):
        return False
    return True


def ini_changes(file_rows, rows):
    """`(moves, flags)`: what writing `rows` over `file_rows` changes, as
    qmModsIni words it for the log and the report - every entry that moves
    (`<dir> <from>-><to>`, 1-based positions) and every flag that changes
    (`<dir> dis <old>-><new>`), `; ` between them, in the new order."""
    at = dict((norm_dir(d), (j, dis)) for j, (d, dis) in enumerate(file_rows))
    moves, flags = [], []
    for k, (d, dis) in enumerate(rows):
        j, old = at[norm_dir(d)]
        if j != k:
            moves.append(d + b" %d->%d" % (j + 1, k + 1))
        if old != dis:
            flags.append(d + b" dis " + old + b"->" + dis)
    return b"; ".join(moves), b"; ".join(flags)


# --------------------------------------------------------------- load order
r"""The load order (plan S11 as revised on 2026-09-28 and
2026-09-30): the twin of src/states/qmorder.pas and of the window's
src/states/qmuiorder.pas.

The player sets the order by hand in the manager window; Quartermaster keeps
it, writes it to mods.ini and puts it in the fingerprint (it decides which mod
wins). Until then it is the order mods.ini has - the one the game loads
without Quartermaster - so installing Quartermaster changes no winner. The
canonical order above is only what Auto-sort gives.

The saved order, <save>\quartermaster\order.cfg
------------------------------------------------
The shape of known.cfg (ref/boot.py): a one-state `.inc` in the engine's
layout, Name = qmOrder, written by the game's raw writer and read back with
the engine's parser. Values: `;format|1`, then `;o|<dir>` for every mod in load
order, Quartermaster's own row left out (it is always last, and its dir may
change: local or Workshop). The dir is the engine's spelling
(ModLibraryGetData), written as an internal string, so any byte survives; the
leading `;` keeps the parser from dropping a leading space (it drops leading
and trailing spaces of a value on load, runs m4a/m4c), and no dir the engine
lists ends in a space (Windows strips them from folder names). The same order
always gives the same bytes.

Rules (`load_order`, `apply_order`)
-----------------------------------
1. No saved order (no order.cfg, or a file without `;format|1`): every mod in
   the order mods.ini lists it (ModLibraryGetData's order), Quartermaster
   moved last, and a boot writes nothing. That is the order the game loads
   without Quartermaster, so every whole file two mods ship has the same
   winner with it. Until 2026-09-30 this rule gave the canonical order, so
   that every machine with the same mods had the same order however they were
   installed; as a default it changed those winners, and Cannons + State vs
   Country, which start without Quartermaster, stopped at "Error compiling
   scripts" with it (docs/plan.md S11).
2. A confirmed Apply of the window that changed the order saves it - unless
   the order it asks for is exactly rule 1's (mods.ini's order, Quartermaster
   last): then order.cfg is deleted and rule 1 applies again. The Apply's
   order is used only when it lists every registered mod exactly once (dirs
   compared folded); otherwise the saved order stays and the refusal is
   logged.
3. With a saved order: its dirs that are still registered keep their order;
   a dir that is gone drops out; mods Quartermaster has not placed yet
   (installed since) follow them, in mods.ini's order among themselves - the
   engine appends a new folder at the end, so in the order they arrived;
   Quartermaster is last. A boot writes the file back when that changed it,
   and deletes it when none of its dirs is registered any more (rule 1
   again) - not during an MP mod sync, when the engine's restore branch owns
   the mod list for a while, and not when Quartermaster's own folder is
   unknown.
   Unseen mods go last because "after everything the player placed" is the
   one position that never reorders what the player chose, and it is where
   the engine itself appends a new folder in mods.ini (M0).
The saved order is authoritative: mods.ini reordered outside Quartermaster (in
modman) is put back at the next boot, and the report says so (`ext`).
"""
from . import inc as _I  # noqa: E402
from .textio import escape as _escape, read_lines as _read_lines  # noqa: E402
from .textio import unescape as _unescape, write_file as _write_file  # noqa: E402

ORDER_REL = b"quartermaster\\order.cfg"
ORDER_KEYS = [b"Name = qmOrder"]
ORDER_FORMAT = b"1"


def order_values(dirs):
    """The Code values of order.cfg for `dirs` in load order (no Quartermaster)."""
    return [b";format|" + ORDER_FORMAT] + [b";o|" + d for d in dirs]


def render_order(dirs):
    """order.cfg's bytes, as the game's raw writer writes them."""
    return _write_file(_I.layout_lines(ORDER_KEYS, [_escape(v) for v in order_values(dirs)]))


def parse_order(data):
    """The saved dirs from order.cfg's bytes, as the engine's parser hands the
    values over (trailing spaces dropped), or None: no file, or not an
    order.cfg (no format line)."""
    if data is None or not data.lstrip(b" ").startswith(b"section.begin"):
        return None
    _form, _keys, values = _I.values_from_lines(_read_lines(data))
    values = [_unescape(v).rstrip(b" ") for v in values]
    if b";format|" + ORDER_FORMAT not in values:
        return None
    dirs = [v[3:] for v in values if v.startswith(b";o|") and len(v) > 3]
    # No dir: the same as no file (rule 3 over nothing is rule 1). Nothing
    # writes such a file: its one value would take the engine's other Code
    # form (`Code[*] = `), which the reader is not built for.
    return dirs or None


class LoadOrder(object):
    """What `load_order` / `apply_order` found.

    rows     indices into the registered dirs, in load order (a permutation)
    src      b"ini" (rule 1), b"saved" (rule 3), b"apply" (rule 2)
    unseen   indices placed after the saved ones, in mods.ini's order
    dropped  saved dirs no registered mod has any more
    ext      mods.ini (the registered order) had the placed mods in another
             order than the saved one: an outside reorder, put back
    canon    the enabled mods' load order is their canonical order
    save     what order.cfg must hold now: a list of dirs, None for "no
             file" (rule 1), or False for "leave the file as it is"
    why      an Apply's order that was not used: b"count" or b"dirs"
    """

    __slots__ = ("rows", "src", "unseen", "dropped", "ext", "canon", "save", "why")

    def __init__(self):
        self.rows, self.src, self.unseen, self.dropped = [], b"ini", [], []
        self.ext, self.canon, self.save, self.why = False, True, False, b""

    def __repr__(self):
        return "LoadOrder(%s)" % ", ".join("%s=%r" % (k, getattr(self, k))
                                           for k in self.__slots__)


def _self_rows(dirs, self_dir):
    return set(i for i, d in enumerate(dirs)
               if self_dir is not None and norm_dir(d) == norm_dir(self_dir))


def _ini_rows(dirs, selfs):
    """Rule 1's order: mods.ini's own, Quartermaster's rows moved last."""
    return ([i for i in range(len(dirs)) if i not in selfs]
            + [i for i in range(len(dirs)) if i in selfs])


def _place(dirs, wanted, skip):
    """`(taken, missing)`: each wanted dir matched to the first registered row
    with the same folded dir that is neither taken yet nor in `skip`."""
    taken, missing = [], []
    for w in wanted:
        k = norm_dir(w)
        hit = next((i for i, d in enumerate(dirs)
                    if i not in taken and i not in skip and norm_dir(d) == k), None)
        if hit is None:
            missing.append(w)
        else:
            taken.append(hit)
    return taken, missing


def _finish(lo, dirs, self_dir, enabled):
    canon = canonical_indices(dirs, self_dir)
    on = enabled if enabled is not None else [True] * len(dirs)
    lo.canon = [i for i in lo.rows if on[i]] == [i for i in canon if on[i]]
    return lo


def load_order(dirs, self_dir=None, saved=None, enabled=None):
    """The load order of a boot (rules 1 and 3). `dirs`: the registered mods
    as ModLibraryGetData lists them (mods.ini order); `saved`: parse_order of
    order.cfg; `enabled`: their flags for the next start (for `canon`),
    default all on."""
    lo = LoadOrder()
    selfs = _self_rows(dirs, self_dir)
    ini = _ini_rows(dirs, selfs)
    if saved is None:
        lo.rows = ini
        return _finish(lo, dirs, self_dir, enabled)
    taken, lo.dropped = _place(dirs, saved, selfs)
    if not taken:
        # Every mod the player placed is gone: nothing of the manual order
        # is left, so rule 1 again, and the file goes.
        lo.rows, lo.save = ini, None
        return _finish(lo, dirs, self_dir, enabled)
    lo.src = b"saved"
    lo.unseen = [i for i in ini if i not in taken and i not in selfs]
    lo.rows = taken + lo.unseen + [i for i in ini if i in selfs]
    lo.ext = sorted(taken) != taken
    now = [dirs[i] for i in lo.rows if i not in selfs]
    lo.save = now if now != list(saved) else False
    return _finish(lo, dirs, self_dir, enabled)


def apply_order(dirs, self_dir=None, saved=None, wanted=None, enabled=None):
    """The load order of an Apply (rule 2): `wanted` = the window's order as
    dirs (qm_rt uiapplyord<k>), None when the Apply did not change the order
    (then the boot's `load_order`; `ext` is not asked in an Apply)."""
    base = load_order(dirs, self_dir, saved, enabled)
    base.ext = False
    if wanted is None:
        return base
    if len(wanted) != len(dirs):
        base.why = b"count"
        return base
    taken, missing = _place(dirs, wanted, set())
    if missing:
        base.why = b"dirs"
        return base
    selfs = _self_rows(dirs, self_dir)
    ini = _ini_rows(dirs, selfs)
    lo = LoadOrder()
    lo.src = b"apply"
    lo.rows = [i for i in taken if i not in selfs] + [i for i in ini if i in selfs]
    now = [dirs[i] for i in lo.rows if i not in selfs]
    if lo.rows == ini:
        lo.save = None if saved is not None else False
    else:
        lo.save = now if saved is None or now != list(saved) else False
    return _finish(lo, dirs, self_dir, enabled)


def load_rows(ini_rows, self_dir, order, intent=None):
    """`canonical_rows` for a load order: the rows of mods.ini (`ini_rows`,
    the registered mods in the engine's order) arranged as `order.rows`, each
    with its own dis text and an Apply's flags (`intent`) laid over them."""
    out = []
    for i in order.rows:
        d, dis = ini_rows[i]
        key = norm_dir(d)
        if intent is not None and key in intent and key != norm_dir(self_dir or b""):
            if intent[key] != is_off(dis):
                dis = TRUE if intent[key] else FALSE
        out.append((d, dis))
    return out


def order_file_after(order, have, sync=False, self_known=True):
    """order.cfg after this run, for `have` = its bytes now (None: no file):
    `(action, bytes)` with action b"same" (left alone), b"written" or
    b"deleted"."""
    if sync or not self_known or order.save is False:
        return b"same", have
    if order.save is None:
        return (b"deleted", None) if have is not None else (b"same", None)
    data = render_order(order.save)
    return (b"same", have) if data == have else (b"written", data)


# ------------------------------------------------------ the window's moves
#: Why a move of the window was refused (qmUiOrder writes a text for each).
UI_UNKNOWN, UI_SELECT, UI_SELF, UI_INACTIVE, UI_FIRST, UI_LAST = (
    b"unknown", b"select", b"self", b"inactive", b"first", b"last")


def ui_move(order, pending, self_row, row, cmd, to=0):
    """One command of the window's load-order controls (the twin of
    src/states/qmuiorder.pas): `order` = qm_ui ord<k> (rows, every one,
    Quartermaster last), `pending` = pe<i> (True: active after Apply),
    `self_row` = Quartermaster's row or -1, `cmd` = b"up", b"down" or b"move"
    (`to`: the place the row must have in the Active list afterwards).

    Only the pending-active rows move, among the slots they hold; an inactive
    row keeps its slot; Quartermaster never moves and nothing goes below it; a
    move beyond the ends is clamped. Returns `(new order, moved, refused)`,
    refused one of the UI_* reasons or None."""
    order = list(order)
    slots = [k for k, i in enumerate(order) if 0 <= i < len(pending) and pending[i]]
    act = [order[k] for k in slots]
    lim = len(act) - 1
    if act and self_row >= 0 and act[-1] == self_row:
        lim -= 1
    if cmd not in (b"up", b"down", b"move"):
        return order, False, UI_UNKNOWN
    if not 0 <= row < len(pending):
        return order, False, UI_SELECT
    if row == self_row:
        return order, False, UI_SELF
    if row not in act:
        return order, False, UI_INACTIVE
    at = act.index(row)
    if cmd == b"up":
        go = at - 1
        if go < 0:
            return order, False, UI_FIRST
    elif cmd == b"down":
        go = at + 1
        if go > lim:
            return order, False, UI_LAST
    else:
        go = min(max(to, 0), lim)
    if go == at:
        return order, False, None
    act.pop(at)
    act.insert(go, row)
    for k, i in zip(slots, act):
        order[k] = i
    return order, True, None
