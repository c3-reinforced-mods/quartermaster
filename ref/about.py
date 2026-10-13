r"""about.cfg (docs/plan.md G4, G5 v2; docs/authoring.md): the twin of
src/states/qmabout.pas.

A mod may ship `about.cfg` next to its `mod.ini`. It is Quartermaster's own
file, not the engine's, so its grammar is defined here (v1, docs/research/
context-2026-09-27.md section 4) and read with the raw reader
(ref/textio.py read_lines): every line is an internal string, bytes outside
32..122 as `~NNN` - `|` is `~124`, a tab `~009`, a UTF-8 BOM
`~239~187~191`. The twin works on that form, as the game does, so both give
the same values byte for byte.

    # a comment line
    id = qmtestwasd
    name = WASD camera
    version = 1.2
    type = mod
    exclusive = camera
    requires = 1325221799; mybase>=2.0
    group = Camera keys
    setting = camera_left;key;A;Camera left

Line rules: spaces and tabs around a line, a key and a value are dropped;
an empty line or one whose first character is `#` is skipped; any other line
must hold `=` - the key is the text before the first one, ASCII case folded,
the value the text after it. Lists are `;`-separated, empty items dropped.
List keys may repeat (their items add up), `setting` repeats by design, a
scalar key given twice keeps its last value (WARN). `group` is a heading: the
settings after it, up to the next `group`, are shown under its title
(option_rows).

Problems: FAIL for a value Quartermaster must be able to trust to keep the
game starting - `id`, `type`, `exclusive`, `requires`, `extends`; WARN for
everything else - an unknown key, a line without `=`, a bad version, a
setting it cannot use (dropped).
"""
import re

from ref import textio as T

__all__ = ["FILE_NAME", "TYPES", "SLOTS", "SETTING_TYPES", "MAX_SETTINGS", "Setting",
           "About", "parse", "parse_lines", "version_tuple", "cmp_version", "names",
           "Problem", "Row", "rules", "edges", "topo_order", "draft", "unescape_text",
           "canonical_v2", "Plan", "fixed_text", "parse_setting", "RuleProblem",
           "KNOWN_DIR", "WORKSHOP_PREFIX", "known_name", "ROWS_A_PAGE", "option_rows",
           "STRIP_ROWS", "GENERAL", "ALL_SETTINGS", "option_groups", "option_strip",
           "option_page", "option_shown", "option_view"]

FILE_NAME = b"about.cfg"
#: Quartermaster's own list (docs/authoring.md): an about.cfg per Workshop mod
#: that ships none, `<Quartermaster's folder>\data\quartermaster\known\<number>.cfg`.
#: qmAbout reads it, with the same grammar, when the mod has no about.cfg of
#: its own (qm_about kn<i> = 1, has<i> stays 0: the mod itself ships none).
KNOWN_DIR = b"data\\quartermaster\\known\\"
WORKSHOP_PREFIX = b"..\\..\\workshop\\content\\333420\\"


def known_name(d):
    """The list's file name for mod dir `d` (`<Workshop number>.cfg`), or None
    for a dir that is not a Workshop item."""
    if d.startswith(WORKSHOP_PREFIX) and len(d) > len(WORKSHOP_PREFIX):
        return d[len(WORKSHOP_PREFIX):] + b".cfg"
    return None

TYPES = (b"mod", b"totalconversion", b"library")
SLOTS = (b"camera", b"ai", b"ui", b"balance", b"economy", b"sound", b"graphics", b"hotkeys")
SETTING_TYPES = (b"bool", b"int", b"float", b"choice", b"key", b"text")
#: Until 0.1.5 a mod had 32 settings at most, and a mod with a switch for
#: every function reached it. 1000 is not a number a mod is meant to come
#: near: it only bounds what a file can ask of the reader, which keeps the
#: `setting` lines in an array until the rest of the file is read. Nothing
#: else is sized by it: a setting's elements in the window are named by its
#: number, and its two button tags, 200 + 2 * number, end at 2199, far below
#: the engine's own (8003 and up).
MAX_SETTINGS = 1000
RAW_SETTINGS = 1024     # setting lines the game side keeps while it reads a file
ROWS_A_PAGE = 10        # rows of the Options view

SCALAR = (b"id", b"name", b"version", b"quartermaster", b"gamebuild", b"type", b"extends")
LISTS = (b"exclusive", b"requires", b"loadafter", b"loadbefore", b"incompatiblewith",
         b"compatiblewith", b"extradirs")
REPEATED = (b"setting",)
GROUP = b"group"

TAB = b"~009"
BOM = b"~239~187~191"
PIPE = b"~124"

_ID = re.compile(rb"[a-z0-9_.\-]+\Z")
_SETTING_ID = re.compile(rb"[a-z0-9_]+\Z")
_VERSION = re.compile(rb"[0-9]+(\.[0-9]+)*\Z")
_INT = re.compile(rb"-?[0-9]+\Z")
_DEC = re.compile(rb"-?[0-9]+(\.[0-9]+)?\Z")

BOOL_TRUE = (b"1", b"true", b"yes", b"on")
BOOL_FALSE = (b"0", b"false", b"no", b"off")


def _strip(text):
    """Spaces and tabs (`~009`) dropped at both ends."""
    while True:
        if text.startswith(b" "):
            text = text[1:]
        elif text.startswith(TAB):
            text = text[4:]
        elif text.endswith(b" "):
            text = text[:-1]
        elif text.endswith(TAB):
            text = text[:-4]
        else:
            return text


def _lower(text):
    return bytes(c + 32 if 65 <= c <= 90 else c for c in text)


def _items(value, sep=b";"):
    return [s for s in (_strip(p) for p in value.split(sep)) if s]


def unescape_text(text):
    """An internal string as the bytes a GUI text shows (textio.unescape)."""
    return T.unescape(text)


def version_tuple(text):
    """`1.2.10` -> (1, 2, 10); None when it is not digits and dots."""
    if not _VERSION.match(text):
        return None
    return tuple(int(p) for p in text.split(b"."))


def cmp_version(a, b):
    """-1, 0, 1 for version texts; missing parts count as 0 (1.2 = 1.2.0)."""
    ta, tb = version_tuple(a), version_tuple(b)
    n = max(len(ta), len(tb))
    ta += (0,) * (n - len(ta))
    tb += (0,) * (n - len(tb))
    return (ta > tb) - (ta < tb)


class Setting(object):
    """One `setting = id;type;default;label[;extra][;scope]` line, checked.

    `value` is the default as Quartermaster stores it: bool `1`/`0`; int an
    integer text; float a fixed-point text with `decimals` places; choice one
    of `options`; key and text as written. Numbers carry `lo`, `hi`, `step`
    as integers scaled by 10^decimals (float) - integer arithmetic on both
    sides, so the game and the twin show the same text. `group` is the title
    of the `group` line the setting stands under, empty without one.
    """

    def __init__(self, sid, kind, default, label, extra=b"", scope=b"local"):
        self.id, self.kind, self.default, self.label = sid, kind, default, label
        self.extra, self.scope = extra, scope
        self.options = []
        self.lo = self.hi = self.step = None
        self.decimals = 0
        self.maxlen = 0
        self.group = b""

    def __repr__(self):
        return "Setting(%r, %r, %r)" % (self.id, self.kind, self.default)


def _dec_places(text):
    return len(text.split(b".", 1)[1]) if b"." in text else 0


def _scaled(text, decimals):
    """`-1.25` at 3 places -> -1250 (text already matches _DEC)."""
    neg = text.startswith(b"-")
    if neg:
        text = text[1:]
    whole, _, frac = text.partition(b".")
    frac = (frac + b"0" * decimals)[:decimals]
    v = int(whole) * 10 ** decimals + (int(frac) if frac else 0)
    return -v if neg else v


def fixed_text(v, decimals):
    """The text of a scaled number: 1250 at 3 places -> `1.250`. Always
    `decimals` places, so a value reads back as it was stored."""
    if decimals == 0:
        return b"%d" % v
    neg = v < 0
    v = -v if neg else v
    s = b"%d.%0*d" % (v // 10 ** decimals, decimals, v % 10 ** decimals)
    return b"-" + s if neg else s


def parse_setting(value, problems):
    """A Setting, or None (WARN in `problems`) when it cannot be used."""
    f = [_strip(p) for p in value.split(b";")]
    if len(f) < 4:
        problems.append(Problem(b"WARN", b"setting-fields",
                                b"setting '%s' needs id;type;default;label" % value))
        return None
    sid, kind, default, label = _lower(f[0]), _lower(f[1]), f[2], f[3]
    extra = f[4] if len(f) > 4 else b""
    scope = _lower(f[5]) if len(f) > 5 else b"local"
    if not _SETTING_ID.match(sid):
        problems.append(Problem(b"WARN", b"setting-id",
                                b"setting id '%s' is not a-z, 0-9, _" % f[0]))
        return None
    if kind not in SETTING_TYPES:
        problems.append(Problem(b"WARN", b"setting-type",
                                b"setting %s: type '%s' is not one of %s"
                                % (sid, f[1], b", ".join(SETTING_TYPES))))
        return None
    if scope == b"":
        scope = b"local"
    if scope not in (b"local", b"host"):
        problems.append(Problem(b"WARN", b"setting-scope",
                                b"setting %s: scope '%s' is not local or host" % (sid, f[5])))
        scope = b"local"
    if label == b"":
        label = sid
    s = Setting(sid, kind, default, label, extra, scope)
    if kind == b"bool":
        low = _lower(default)
        if low in BOOL_TRUE:
            s.default = b"1"
        elif low in BOOL_FALSE:
            s.default = b"0"
        else:
            problems.append(Problem(b"WARN", b"setting-default",
                                    b"setting %s: '%s' is not a bool; 0 used" % (sid, default)))
            s.default = b"0"
    elif kind in (b"int", b"float"):
        pat = _INT if kind == b"int" else _DEC
        parts = [_strip(p) for p in extra.split(b"..")] if extra else []
        if len(parts) not in (2, 3) or not all(pat.match(p) for p in parts):
            problems.append(Problem(b"WARN", b"setting-range",
                                    b"setting %s: range '%s' is not min..max or min..max..step" % (sid, extra)))
            return None
        if not pat.match(default):
            problems.append(Problem(b"WARN", b"setting-default",
                                    b"setting %s: default '%s' is not a number" % (sid, default)))
            return None
        dec = max(_dec_places(p) for p in parts + [default]) if kind == b"float" else 0
        s.decimals = dec
        s.lo, s.hi = _scaled(parts[0], dec), _scaled(parts[1], dec)
        s.step = _scaled(parts[2], dec) if len(parts) == 3 else 10 ** dec
        if s.lo > s.hi or s.step <= 0:
            problems.append(Problem(b"WARN", b"setting-range",
                                    b"setting %s: range '%s' is empty" % (sid, extra)))
            return None
        v = _scaled(default, dec)
        if v < s.lo or v > s.hi:
            problems.append(Problem(b"WARN", b"setting-default",
                                    b"setting %s: default %s is outside %s; clamped" % (sid, default, extra)))
            v = min(max(v, s.lo), s.hi)
        s.default = fixed_text(v, dec)
    elif kind == b"choice":
        s.options = _items(extra, PIPE)
        if not s.options:
            problems.append(Problem(b"WARN", b"setting-options",
                                    b"setting %s: no options (a|b|c)" % sid))
            return None
        if default not in s.options:
            problems.append(Problem(b"WARN", b"setting-default",
                                    b"setting %s: default '%s' is not an option; the first one used" % (sid, default)))
            s.default = s.options[0]
    elif kind == b"key":
        if default == b"":
            problems.append(Problem(b"WARN", b"setting-default",
                                    b"setting %s: a key setting needs a default key" % sid))
            return None
    elif kind == b"text":
        if extra:
            if not _INT.match(extra) or int(extra) < 1:
                problems.append(Problem(b"WARN", b"setting-range",
                                        b"setting %s: max length '%s' is not a number" % (sid, extra)))
            else:
                s.maxlen = int(extra)
                if len(T.unescape(default)) > s.maxlen:
                    s.default = b""
                    problems.append(Problem(b"WARN", b"setting-default",
                                            b"setting %s: default is longer than %d; empty used" % (sid, s.maxlen)))
    return s


class Problem(object):
    def __init__(self, tag, code, text):
        self.tag, self.code, self.text = tag, code, text

    def __eq__(self, other):
        return (self.tag, self.code, self.text) == (other.tag, other.code, other.text)

    def __repr__(self):
        return "Problem(%r, %r, %r)" % (self.tag, self.code, self.text)


class About(object):
    def __init__(self):
        self.present = False
        self.values = {}
        self.id = b""
        self.name = b""
        self.version = b""
        self.quartermaster = b""
        self.gamebuild = b""
        self.type = b"mod"
        self.extends = b""
        self.exclusive = []
        self.requires = []          # [(id, version or b"")]
        self.loadafter = []
        self.loadbefore = []
        self.incompatiblewith = []
        self.compatiblewith = []
        self.extradirs = []
        self.settings = []
        self.problems = []

    @property
    def fail(self):
        return any(p.tag == b"FAIL" for p in self.problems)


def parse(data):
    """About of the raw bytes of an about.cfg (None: no file)."""
    if data is None:
        return About()
    return parse_lines(T.read_lines(data))


def parse_lines(lines):
    a = About()
    a.present = True
    seen = set()
    raw = {k: [] for k in LISTS + REPEATED}
    group = b""
    for n, line in enumerate(lines, 1):
        if n == 1 and line.startswith(BOM):
            line = line[len(BOM):]
        line = _strip(line)
        if line == b"" or line.startswith(b"#"):
            continue
        eq = line.find(b"=")
        if eq < 0:
            a.problems.append(Problem(b"WARN", b"line", b"line %d is not key = value" % n))
            continue
        key, value = _lower(_strip(line[:eq])), _strip(line[eq + 1:])
        if key in SCALAR:
            if key in seen:
                a.problems.append(Problem(b"WARN", b"repeated",
                                          b"line %d: %s is given twice; the last one counts" % (n, key)))
            seen.add(key)
            a.values[key] = value
        elif key == GROUP:
            if value == b"":
                a.problems.append(Problem(b"WARN", b"group",
                                          b"line %d: group needs a title; ignored" % n))
            else:
                group = value
        elif key in REPEATED and len(raw[key]) >= RAW_SETTINGS:
            a.problems.append(Problem(b"WARN", b"setting-lines",
                                      b"line %d: more than %d setting lines; ignored" % (n, RAW_SETTINGS)))
        elif key in REPEATED:
            raw[key].append((group, value))
        elif key in LISTS:
            raw[key].append(value)
        else:
            a.problems.append(Problem(b"WARN", b"unknown",
                                      b"line %d: unknown key '%s'" % (n, key)))
    v = a.values
    if b"id" in v:
        a.id = _lower(v[b"id"])
        if not _ID.match(a.id):
            a.problems.append(Problem(b"FAIL", b"id",
                                      b"id '%s' is not a-z, 0-9, _ . -" % v[b"id"]))
            a.id = b""
    a.name = v.get(b"name", b"")
    a.gamebuild = v.get(b"gamebuild", b"")
    if b"version" in v:
        if version_tuple(v[b"version"]) is None:
            a.problems.append(Problem(b"WARN", b"version",
                                      b"version '%s' is not digits and dots" % v[b"version"]))
        else:
            a.version = v[b"version"]
    if b"quartermaster" in v:
        if version_tuple(v[b"quartermaster"]) is None:
            a.problems.append(Problem(b"WARN", b"version",
                                      b"quartermaster '%s' is not digits and dots" % v[b"quartermaster"]))
        else:
            a.quartermaster = v[b"quartermaster"]
    if b"type" in v:
        t = _lower(v[b"type"])
        if t not in TYPES:
            a.problems.append(Problem(b"FAIL", b"type",
                                      b"type '%s' is not mod, totalConversion or library" % v[b"type"]))
        else:
            a.type = t
    if b"extends" in v:
        e = _lower(v[b"extends"])
        if not _ID.match(e):
            a.problems.append(Problem(b"FAIL", b"extends",
                                      b"extends '%s' is not a mod id" % v[b"extends"]))
        else:
            a.extends = e
    for value in raw[b"exclusive"]:
        for item in _items(value):
            s = _lower(item)
            if s not in SLOTS:
                a.problems.append(Problem(b"FAIL", b"exclusive",
                                          b"exclusive '%s' is not one of %s" % (item, b", ".join(SLOTS))))
            elif s not in a.exclusive:
                a.exclusive.append(s)
    for value in raw[b"requires"]:
        for item in _items(value):
            rid, ver = item, b""
            if b">=" in item:
                rid, _, ver = item.partition(b">=")
                rid, ver = _strip(rid), _strip(ver)
            rid = _lower(rid)
            if not _ID.match(rid) or (b">=" in item and version_tuple(ver) is None):
                a.problems.append(Problem(b"FAIL", b"requires",
                                          b"requires '%s' is not id or id>=version" % item))
            else:
                a.requires.append((rid, ver))
    for key in (b"loadafter", b"loadbefore", b"incompatiblewith", b"compatiblewith"):
        out = getattr(a, key.decode())
        for value in raw[key]:
            for item in _items(value):
                i = _lower(item)
                if not _ID.match(i):
                    a.problems.append(Problem(b"WARN", b"list",
                                              b"%s '%s' is not a mod id; ignored" % (key, item)))
                elif i not in out:
                    out.append(i)
    for value in raw[b"extradirs"]:
        a.extradirs += _items(value)
    ids = set()
    for group, value in raw[b"setting"]:
        s = parse_setting(value, a.problems)
        if s is None:
            continue
        if s.id in ids:
            a.problems.append(Problem(b"WARN", b"setting-twice",
                                      b"setting %s is declared twice; the first one counts" % s.id))
            continue
        if len(a.settings) >= MAX_SETTINGS:
            a.problems.append(Problem(b"WARN", b"setting-many",
                                      b"more than %d settings; setting %s dropped" % (MAX_SETTINGS, s.id)))
            continue
        ids.add(s.id)
        s.group = group
        a.settings.append(s)
    return a


def option_rows(settings, page=ROWS_A_PAGE, shown=None, titles=True):
    """The rows of the Options view for the settings `shown` (indices in
    their order; all of them when None), `page` rows a page: `(kind, k)` with
    kind `set` (setting k), `head` (the title of setting k's group), `more`
    (that title again, on a page a group runs on to) or `none` (an empty row,
    k = -1). Without `titles` a row a setting and nothing else.

    Settings without a group follow each other as they are declared, which is
    all an about.cfg without `group` lines has. A group starts with its title;
    when the title and the whole group do not fit the rest of the page, they
    start the next one - so a title never stands alone at the foot of a page,
    and a group that fits a page under its title is never split."""
    shown = list(range(len(settings))) if shown is None else list(shown)
    if not titles:
        return [(b"set", k) for k in shown]
    rows = []
    names = [T.unescape(settings[k].group) for k in shown]
    for i, k in enumerate(shown):
        title = names[i]
        if title != b"" and (i == 0 or names[i - 1] != title):
            size = 1
            while i + size < len(names) and names[i + size] == title:
                size += 1
            used = len(rows) % page
            if used and 1 + size > page - used:
                rows += [(b"none", -1)] * (page - used)
            rows.append((b"head", k))
        elif title != b"" and len(rows) % page == 0:
            rows.append((b"more", k))
        rows.append((b"set", k))
    return rows


#: The Options view of a mod with groups, or with more settings than a page
#: holds, has a strip over its rows - the list of groups and the search box -
#: and a row less for it.
STRIP_ROWS = 9
#: What the list of groups calls the settings that stand under no group.
GENERAL = b"General"
ALL_SETTINGS = b"All settings"


def option_groups(settings):
    """The entries of the Options view's list of groups: `(title, count)` in
    the order the titles first appear, the settings under no group as an entry
    with the title b"" (shown as GENERAL). Empty when no setting has a group:
    the view has no list then."""
    titles = [T.unescape(s.group) for s in settings]
    if not any(titles):
        return []
    out = []
    for t in titles:
        for i, (title, count) in enumerate(out):
            if title == t:
                out[i] = (title, count + 1)
                break
        else:
            out.append((t, 1))
    return out


def option_strip(settings):
    return bool(option_groups(settings)) or len(settings) > ROWS_A_PAGE


def option_page(settings):
    return STRIP_ROWS if option_strip(settings) else ROWS_A_PAGE


def option_shown(settings, group, query=b""):
    """`(indices, titles)`: the settings the view shows, and whether with
    their groups' titles. A search text shows the settings whose label or
    whose group's title holds it (ASCII case folded here; the game folds with
    the engine's StrToLowerCase, which knows the player's code page too), of
    every group and under the titles; else `group` - an entry of
    option_groups - shows that group's settings alone, and any other number
    (the list's last entry, ALL_SETTINGS) all of them under their titles."""
    groups = option_groups(settings)
    if query != b"":
        q = query.lower()
        return [k for k, s in enumerate(settings)
                if q in (T.unescape(s.label) + b"|" + T.unescape(s.group)).lower()], True
    if 0 <= group < len(groups):
        return [k for k, s in enumerate(settings) if T.unescape(s.group) == groups[group][0]], False
    return list(range(len(settings))), True


def option_view(settings, group, query=b""):
    """The rows of the Options view (the twin of qmUiAct qmUaOptView)."""
    shown, titles = option_shown(settings, group, query)
    return option_rows(settings, option_page(settings), shown, titles)


def names(d, about):
    """Every name a mod answers to in requires / incompatibleWith / ...: its
    declared id and its folder identity (Workshop number, local folder name),
    ASCII case folded."""
    from ref import order as O
    out = []
    if about is not None and about.id:
        out.append(about.id)
    origin, ident = O.identity(d)
    if origin in (O.WORKSHOP, O.LOCAL):
        low = _lower(ident)
        if low not in out:
            out.append(low)
    return out


class Row(object):
    """One registered mod for the rules: its dir, title, about, active flag,
    Quartermaster or not."""

    def __init__(self, d, title, about=None, on=True, is_self=False):
        self.dir, self.title, self.on, self.is_self = d, title, on, is_self
        self.about = about if about is not None else About()
        self.names = [b"quartermaster"] if is_self else names(d, self.about)


class RuleProblem(object):
    def __init__(self, row, tag, code, text, other=-1):
        self.row, self.tag, self.code, self.text, self.other = row, tag, code, text, other

    def __eq__(self, o):
        return (self.row, self.tag, self.code, self.text, self.other) == \
            (o.row, o.tag, o.code, o.text, o.other)

    def __repr__(self):
        return "RuleProblem(%d, %r, %r, %r, %d)" % (self.row, self.tag, self.code, self.text, self.other)


def _find(rows, name, active_only):
    for j, r in enumerate(rows):
        if (r.on or not active_only) and name in r.names:
            return j
    return -1


def _related(rows, a, b):
    """`a` extends `b` or `b` extends `a` (an add-on and its base)."""
    ea, eb = rows[a].about.extends, rows[b].about.extends
    return (ea != b"" and ea in rows[b].names) or (eb != b"" and eb in rows[a].names)


def _compatible(rows, a, b):
    ca, cb = rows[a].about.compatiblewith, rows[b].about.compatiblewith
    return any(n in ca for n in rows[b].names) or any(n in cb for n in rows[a].names)


def rules(rows, order=None, qm_version=b"0.0.0"):
    """The rule problems of the active rows, in `order` (row indices, load
    order; mods.ini order when None). One problem per broken rule, on the row
    that breaks it - the later of two in load order."""
    order = list(range(len(rows))) if order is None else order
    pos = {i: k for k, i in enumerate(order)}
    out = []
    for i in order:
        r = rows[i]
        if not r.on or r.is_self:
            continue
        a = r.about
        need = list(a.requires)
        if a.extends and all(rid != a.extends for rid, _v in need):
            need.append((a.extends, b""))
        for rid, ver in need:
            j = _find(rows, rid, True)
            if j < 0:
                k = _find(rows, rid, False)
                if k >= 0:
                    out.append(RuleProblem(i, b"FAIL", b"requires",
                                           b"%s needs %s, which is not active" % (r.title, rows[k].title), k))
                else:
                    out.append(RuleProblem(i, b"FAIL", b"requires",
                                           b"%s needs %s, which is not installed" % (r.title, rid)))
                continue
            if ver:
                have = rows[j].about.version
                if have == b"":
                    out.append(RuleProblem(i, b"WARN", b"version",
                                           b"%s needs %s %s or later; its version is not known" % (r.title, rows[j].title, ver), j))
                elif cmp_version(have, ver) < 0:
                    out.append(RuleProblem(i, b"FAIL", b"version",
                                           b"%s needs %s %s or later, not %s" % (r.title, rows[j].title, ver, have), j))
        if a.quartermaster and cmp_version(qm_version, a.quartermaster) < 0:
            out.append(RuleProblem(i, b"WARN", b"quartermaster",
                                   b"%s is made for Quartermaster %s or later, this is %s" % (r.title, a.quartermaster, qm_version)))
        for inc in a.incompatiblewith:
            j = _find(rows, inc, True)
            if j >= 0 and j != i:
                out.append(RuleProblem(i, b"FAIL", b"incompatible",
                                       b"%s does not work with %s" % (r.title, rows[j].title), j))
    for i in order:
        r = rows[i]
        if not r.on or r.is_self:
            continue
        for j in order:
            if pos[j] >= pos[i]:
                break
            o = rows[j]
            if not o.on or o.is_self or _related(rows, i, j):
                continue
            if r.about.type == b"totalconversion" and o.about.type == b"totalconversion":
                out.append(RuleProblem(i, b"FAIL", b"total",
                                       b"%s and %s are both total conversions; only one can be active" % (o.title, r.title), j))
            if _compatible(rows, i, j):
                continue
            for slot in r.about.exclusive:
                if slot in o.about.exclusive:
                    out.append(RuleProblem(i, b"FAIL", b"exclusive",
                                           b"%s and %s both take the %s slot; only one can be active" % (o.title, r.title, slot), j))
                    break
    # A load order set by hand (plan S11) may break a constraint: say so, the
    # player's Auto-sort puts it right.
    e = edges(rows)
    for i in order:
        r = rows[i]
        if not r.on or r.is_self:
            continue
        for b in sorted({b for b, a in e if a == i}):
            if rows[b].on and b in pos and pos[b] > pos[i]:
                out.append(RuleProblem(i, b"WARN", b"order",
                                       b"%s should load after %s" % (r.title, rows[b].title), b))
    return out


def edges(rows):
    """Load-order constraints `(before, after)` between registered rows."""
    out = []
    for i, r in enumerate(rows):
        if r.is_self:
            continue
        a = r.about
        before = [rid for rid, _v in a.requires] + ([a.extends] if a.extends else []) + a.loadafter
        for name in before:
            j = _find(rows, name, False)
            if j >= 0 and j != i and not rows[j].is_self and (j, i) not in out:
                out.append((j, i))
        for name in a.loadbefore:
            j = _find(rows, name, False)
            if j >= 0 and j != i and not rows[j].is_self and (i, j) not in out:
                out.append((i, j))
    return out


def topo_order(canon, rows):
    """Kahn's sort of `canon` (row indices, Phase A canonical order) under
    `edges(rows)`: of the rows whose predecessors are all placed, the one
    earliest in `canon` goes next. Quartermaster keeps its place (last).

    Returns `(order, cycle)`: `cycle` lists the rows placed while no row was
    ready (each then the earliest left in `canon` that another row left still
    waits for), in placement order."""
    e = edges(rows)
    left = [i for i in canon if not rows[i].is_self]
    tail = [i for i in canon if rows[i].is_self]
    preds = {i: set() for i in left}
    for b, a in e:
        if a in preds and b in preds:
            preds[a].add(b)
    placed, order, cycle = set(), [], []
    while left:
        pick = -1
        for i in left:
            if preds[i] <= placed:
                pick = i
                break
        if pick < 0:
            # No row is ready: a cycle. Break it at the earliest row another
            # row still waits for (a row of the cycle, not one merely behind it).
            waited = [i for i in left if any(i in preds[j] for j in left)]
            pick = waited[0] if waited else left[0]
            cycle.append(pick)
        order.append(pick)
        placed.add(pick)
        left.remove(pick)
    return order + tail, cycle


class Plan(object):
    def __init__(self, order, cycle):
        self.order, self.cycle = order, cycle


def canonical_v2(dirs, abouts, self_index=-1):
    """Canonical order v2 of the registered `dirs` (plan S11 Phase B): the
    Phase A canonical order, then the about.cfg constraints."""
    from ref import order as O
    self_dir = dirs[self_index] if self_index >= 0 else None
    canon = O.canonical_indices(dirs, self_dir)
    rows = [Row(d, d, abouts[i], True, i == self_index) for i, d in enumerate(dirs)]
    order, cycle = topo_order(canon, rows)
    return Plan(order, cycle)


def draft(ident, title, overhaul=False, camera=False, settings=()):
    """A draft about.cfg for an existing mod (M8 task 6, M11): CRLF lines,
    ASCII; `title` is written as it is (the engine's title bytes)."""
    # The comment a draft starts with.
    lines = [b"# about.cfg - read by Quartermaster; the Quartermaster Workshop page lists the keys.",
             b"id = " + ident,
             b"name = " + title,
             b"version = 1.0",
             b"type = " + (b"totalConversion" if overhaul else b"mod")]
    if camera:
        lines.append(b"exclusive = camera")
    for s in settings:
        lines.append(b"setting = " + s)
    return b"\r\n".join(lines) + b"\r\n"
