"""The emitted merge states, run offline: qmCaseMerge and qmMerge as the build
emits them, executed by a small interpreter of the script dialect over an
emulated engine, must write exactly ref's rows and output files for the
SelfTest merge cases.

This is a desk check, not a model of the compiler: it runs what compiles and
says nothing about what the engine would refuse (the lints and the in-game run
do that). The emulated natives follow what the game was seen to do: Integer
arithmetic wraps, `shr` is logical, `and`/`or` short-circuit (capability
probes); the parser drops trailing spaces from values when it loads a file,
appends with the key [*] only once (a second append overwrites the first) and
saves the Code node in the layout its value count calls for (run m2a,
`ref.inc.render`) - the merge reads and writes through the raw reader and
writer, the parser only reads the case file and the suite; past the end of a
file ReadInteger leaves its variable alone and a partial last Integer fills
only the low bytes (run m2a2). Files are read from the installed game
(read-only) and from the generated cases in memory; nothing is written to
disk.

A construct the interpreter does not know skips the test instead of failing
it, so a helper written in more of the dialect does not break the suite; a
wrong result always fails.
"""
import gc
import re
import struct

import pytest

import hbuild as H
import m3cases as C
from ref import inc as I
from ref import merge as M

MASK = 0xFFFFFFFF


def wrap(x):
    x &= MASK
    return x - 0x100000000 if x & 0x80000000 else x


#: Natives with var parameters, by argument position: cossacks.exe declares
#: `procedure ReadInteger(const fs: Integer; var val: Integer)`.
BYREF_NATIVES = {"readinteger": (1,)}


class Unsupported(Exception):
    """The source uses something this interpreter does not implement."""


class RunError(Exception):
    """The program did something the engine would fail on (bad index, ...)."""


class _Exit(Exception):
    pass


# ------------------------------------------------------------------ lexer
_TOKEN = re.compile(r"""
  (?P<ws>\s+)|(?P<com>//[^\n]*)|(?P<bcom>\{[^}]*\})|
  (?P<str>'(?:[^']|'')*')|(?P<chr>\#\d+)|
  (?P<num>\d+\.\d+|\d+)|(?P<hex>\$[0-9A-Fa-f]+)|
  (?P<id>[A-Za-z_][A-Za-z0-9_]*)|
  (?P<op>:=|<=|>=|<>|\.\.|[-+*/=<>()\[\],;:.])
""", re.X)


def lex(text):
    out = []
    pos = 0
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise Unsupported("cannot read %r" % text[pos:pos + 30])
        pos = m.end()
        kind, value = m.lastgroup, m.group()
        if kind in ("ws", "com", "bcom"):
            continue
        if kind == "str":
            out.append(("str", value[1:-1].replace("''", "'").encode("latin-1")))
        elif kind == "chr":
            out.append(("str", bytes([int(value[1:])])))
        elif kind == "num":
            out.append(("num", float(value) if "." in value else int(value)))
        elif kind == "hex":
            out.append(("num", int(value[1:], 16)))
        elif kind == "id":
            out.append(("id", value.lower()))
        else:
            out.append(("op", value))
    out.append(("eof", None))
    return out


# ----------------------------------------------------------------- parser
class Parser(object):
    """Recursive descent over the statements the states use."""

    def __init__(self, tokens):
        self.t = tokens
        self.i = 0

    def peek(self):
        return self.t[self.i]

    def take(self):
        self.i += 1
        return self.t[self.i - 1]

    def at_op(self, v):
        return self.peek() == ("op", v)

    def at_id(self, v):
        return self.peek() == ("id", v)

    def op(self, v):
        if self.take() != ("op", v):
            raise Unsupported("expected %r near %r" % (v, self.t[self.i - 1:self.i + 6]))

    def word(self, v=None):
        tok = self.take()
        if tok[0] != "id" or (v is not None and tok[1] != v):
            raise Unsupported("expected %r near %r" % (v, self.t[self.i - 1:self.i + 6]))
        return tok[1]

    def program(self):
        items = []
        while self.peek()[0] != "eof":
            if self.at_op(";"):
                self.take()
            elif self.at_id("procedure") or self.at_id("function"):
                items.append(self.routine())
            else:
                items.append(self.statement())
        return items

    def type_(self):
        if self.at_id("array"):
            self.take()
            self.op("[")
            dims = []
            while True:
                lo = self.expr()
                self.op("..")
                dims.append((lo, self.expr()))
                if not self.at_op(","):
                    break
                self.take()
            self.op("]")
            self.word("of")
            t = self.type_()
            for lo, hi in reversed(dims):
                t = ("array", lo, hi, t)
            return t
        return ("name", self.word())

    def routine(self):
        kind, name = self.word(), self.word()
        params = []
        if self.at_op("("):
            self.take()
            while not self.at_op(")"):
                mode = "val"
                if self.at_id("const") or self.at_id("var"):
                    mode = self.word()
                names = [self.word()]
                while self.at_op(","):
                    self.take()
                    names.append(self.word())
                self.op(":")
                t = self.type_()
                params += [(n, mode, t) for n in names]
                if self.at_op(";"):
                    self.take()
            self.op(")")
        rtype = None
        if kind == "function":
            self.op(":")
            rtype = self.type_()
        self.op(";")
        block = self.block()
        self.op(";")
        return ("routine", name, kind, params, rtype, block)

    def block(self):
        self.word("begin")
        stmts = []
        while not self.at_id("end"):
            if self.at_op(";"):
                self.take()
                continue
            stmts.append(self.statement())
            if not (self.at_op(";") or self.at_id("end")):
                raise Unsupported("expected ; near %r" % (self.t[self.i:self.i + 6],))
        self.word("end")
        return ("block", stmts)

    def statement(self):
        tok = self.peek()
        if tok[0] != "id":
            raise Unsupported("statement near %r" % (self.t[self.i:self.i + 6],))
        w = tok[1]
        if w == "begin":
            return self.block()
        if w == "var":
            self.take()
            names = [self.word()]
            while self.at_op(","):
                self.take()
                names.append(self.word())
            self.op(":")
            t = self.type_()
            init = None
            if self.at_op("="):
                self.take()
                init = self.expr()
            return ("var", names, t, init)
        if w == "const":
            self.take()
            name = self.word()
            if self.at_op(":"):
                self.take()
                self.type_()
            self.op("=")
            return ("const", name, self.expr())
        if w == "if":
            self.take()
            cond = self.expr()
            self.word("then")
            yes = self.inner()
            no = None
            if self.at_id("else"):
                self.take()
                no = self.inner()
            return ("if", cond, yes, no)
        if w == "while":
            self.take()
            cond = self.expr()
            self.word("do")
            return ("while", cond, self.inner())
        if w == "for":
            self.take()
            var = self.word()
            self.op(":=")
            a = self.expr()
            direction = self.word()
            if direction not in ("to", "downto"):
                raise Unsupported("for ... %s" % direction)
            b = self.expr()
            self.word("do")
            return ("for", var, a, direction == "downto", b, self.inner())
        if w == "exit":
            self.take()
            return ("exit",)
        if w in ("repeat", "case", "with", "try", "goto", "break", "continue"):
            raise Unsupported(w)
        target = self.designator()
        if self.at_op(":="):
            self.take()
            return ("assign", target, self.expr())
        return ("call", target)

    def inner(self):
        if self.at_op(";") or self.at_id("else") or self.at_id("end"):
            return ("block", [])
        return self.statement()

    def designator(self):
        name = self.word()
        node = ("name", name)
        if self.at_op("("):
            self.take()
            args = []
            while not self.at_op(")"):
                args.append(self.expr())
                if self.at_op(","):
                    self.take()
            self.op(")")
            node = ("fcall", name, args)
        while self.at_op("["):
            self.take()
            index = self.expr()
            self.op("]")
            node = ("index", node, index)
        return node

    def expr(self):
        left = self.simple()
        tok = self.peek()
        if tok[0] == "op" and tok[1] in ("=", "<>", "<", ">", "<=", ">="):
            self.take()
            return ("rel", tok[1], left, self.simple())
        return left

    def simple(self):
        left = self.term()
        while True:
            tok = self.peek()
            if tok in (("op", "+"), ("op", "-"), ("id", "or"), ("id", "xor")):
                self.take()
                left = ("bin", tok[1], left, self.term())
            else:
                return left

    def term(self):
        left = self.factor()
        while True:
            tok = self.peek()
            if tok in (("op", "*"), ("op", "/"), ("id", "div"), ("id", "mod"),
                       ("id", "and"), ("id", "shl"), ("id", "shr")):
                self.take()
                left = ("bin", tok[1], left, self.factor())
            else:
                return left

    def factor(self):
        tok = self.peek()
        if tok == ("op", "("):
            self.take()
            e = self.expr()
            self.op(")")
            return e
        if tok == ("op", "-"):
            self.take()
            return ("neg", self.factor())
        if tok == ("op", "+"):
            self.take()
            return self.factor()
        if tok == ("id", "not"):
            self.take()
            return ("not", self.factor())
        if tok[0] == "num":
            self.take()
            return ("lit", tok[1])
        if tok[0] == "str":
            self.take()
            s = tok[1]
            while self.peek()[0] == "str":
                s += self.take()[1]
            return ("lit", s)
        if tok == ("id", "true") or tok == ("id", "false"):
            self.take()
            return ("lit", tok[1] == "true")
        if tok[0] == "id":
            return self.designator()
        raise Unsupported("expression near %r" % (self.t[self.i:self.i + 6],))


# --------------------------------------------------------------- runtime
class Arr(object):
    __slots__ = ("lo", "data")

    def __init__(self, lo, data):
        self.lo, self.data = lo, data


class Cell(object):
    __slots__ = ("v",)

    def __init__(self, v):
        self.v = v


class Elem(object):
    """A var argument that is an array element."""
    __slots__ = ("arr", "i")

    def __init__(self, arr, i):
        self.arr, self.i = arr, i

    @property
    def v(self):
        return self.arr.data[self.i]

    @v.setter
    def v(self, x):
        self.arr.data[self.i] = x


def _trunc_div(a, b):
    if b == 0:
        raise RunError("division by zero")
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


class State(object):
    """One state, parsed once; every run starts with fresh state variables."""

    def __init__(self, code_lines, engine):
        self.engine = engine
        self.items = Parser(lex("\n".join(l.decode("latin-1") for l in code_lines))).program()
        self.routines = dict((it[1], it) for it in self.items if it[0] == "routine")

    def run(self):
        frame = Frame(self, {}, None)
        try:
            for it in self.items:
                if it[0] != "routine":
                    frame.execute(it)
        except _Exit:
            pass


class Frame(object):
    def __init__(self, state, globals_, locals_):
        self.state, self.g, self.l = state, globals_, locals_
        self.natives = state.engine.natives

    def cell(self, name):
        if self.l is not None and name in self.l:
            return self.l[name]
        return self.g.get(name)

    # tcolor: the engine's colour record (gui.script), opaque here - a native
    # such as _gui_ConvertHexToTColor fills it and another only passes it on.
    ZEROS = {"integer": 0, "byte": 0, "string": b"", "boolean": False, "float": 0.0,
             "tcolor": None}

    def zero(self, t):
        if t[0] == "array":
            lo, hi = self.eval(t[1]), self.eval(t[2])
            if t[3][0] == "name":
                return Arr(lo, [self.zero(t[3])] * (hi - lo + 1))
            return Arr(lo, [self.zero(t[3]) for _ in range(hi - lo + 1)])
        if t[1] not in self.ZEROS:
            raise Unsupported("type %s" % t[1])
        return self.ZEROS[t[1]]

    def execute(self, s):
        k = s[0]
        if k == "block":
            for x in s[1]:
                self.execute(x)
        elif k == "assign":
            self.store(s[1], self.eval(s[2]))
        elif k == "call":
            t = s[1]
            if t[0] == "name":
                self.invoke(t[1], [])
            elif t[0] == "fcall":
                self.invoke(t[1], t[2])
            else:
                raise Unsupported("call of %r" % (t,))
        elif k == "if":
            if self.truth(self.eval(s[1])):
                self.execute(s[2])
            elif s[3] is not None:
                self.execute(s[3])
        elif k == "while":
            while self.truth(self.eval(s[1])):
                self.execute(s[2])
        elif k == "for":
            _k, var, a, down, b, stmt = s
            i, last = self.eval(a), self.eval(b)
            cell = self.cell(var)
            if cell is None:
                raise RunError("loop variable %s is not declared" % var)
            step = -1 if down else 1
            while (i >= last) if down else (i <= last):
                cell.v = i
                self.execute(stmt)
                i += step
        elif k == "var":
            _k, names, t, init = s
            scope = self.l if self.l is not None else self.g
            for n in names:
                v = self.zero(t) if init is None else self.eval(init)
                if t == ("name", "float") and isinstance(v, int):
                    v = float(v)
                scope[n] = Cell(v)
        elif k == "const":
            (self.l if self.l is not None else self.g)[s[1]] = Cell(self.eval(s[2]))
        elif k == "exit":
            raise _Exit()
        else:
            raise Unsupported(k)

    @staticmethod
    def truth(v):
        if not isinstance(v, bool):
            raise RunError("a condition is not Boolean: %r" % (v,))
        return v

    def element(self, node):
        arr, i = self.eval(node[1]), self.eval(node[2])
        if not isinstance(arr, Arr):
            raise RunError("index into a non-array")
        j = i - arr.lo
        if not 0 <= j < len(arr.data):
            raise RunError("index %d outside [%d..%d]" % (i, arr.lo, arr.lo + len(arr.data) - 1))
        return arr, j

    def store(self, target, v):
        if target[0] == "name":
            c = self.cell(target[1])
            if c is None:
                raise RunError("%s is not declared" % target[1])
            c.v = float(v) if isinstance(c.v, float) and isinstance(v, int) else v
        elif target[0] == "index":
            arr, j = self.element(target)
            arr.data[j] = v
        else:
            raise RunError("cannot assign to %r" % (target,))

    def reference(self, e):
        if e[0] == "name":
            c = self.cell(e[1])
            if c is None:
                raise RunError("var argument %s is not declared" % e[1])
            return c
        if e[0] == "index":
            return Elem(*self.element(e))
        raise RunError("a var argument must be a variable: %r" % (e,))

    def _alias_key(self, e):
        if e[0] == "name":
            c = self.cell(e[1])
            return ("c", id(c)) if c is not None else None
        if e[0] == "index":
            arr, j = self.element(e)
            return ("e", id(arr), j)
        return None

    def invoke(self, name, args):
        r = self.state.routines.get(name)
        if r is None:
            fn = self.natives.get(name)
            if fn is None:
                raise Unsupported("native %s" % name)
            byref = BYREF_NATIVES.get(name, ())
            return fn(*[self.reference(a) if k in byref else self.eval(a)
                        for k, a in enumerate(args)])
        _r, _n, kind, params, rtype, block = r
        if len(args) != len(params):
            raise RunError("%s takes %d arguments, got %d" % (name, len(params), len(args)))
        # One variable passed both by value and as a var parameter: the engine
        # does not keep them apart as this interpreter would - in the game
        # qmLowerAscii(qmAbRid, qmAbRid) turned `qmtestverbase` into
        # `qmtestverbas` (probe runs of 2026-09-29) - so the sources never do it.
        # A String only: that is what came back damaged; the phase A code has
        # passed a Boolean so since M3 and the game ran it right.
        outs = [self._alias_key(a) for (_p, mode, _t), a in zip(params, args) if mode == "var"]
        for (pname, mode, ptype), a in zip(params, args):
            if (mode != "var" and ptype[0] == "name" and ptype[1].lower() == "string"
                    and self._alias_key(a) is not None and self._alias_key(a) in outs):
                raise RunError("%s: %s is passed both as a value and as a var parameter"
                               % (name, a[1] if a[0] == "name" else "an element"))
        local = {}
        for (pname, mode, _t), a in zip(params, args):
            local[pname] = self.reference(a) if mode == "var" else Cell(self.eval(a))
        if kind == "function":
            local["result"] = Cell(self.zero(rtype))
        try:
            Frame(self.state, self.g, local).execute(block)
        except _Exit:
            pass
        return local["result"].v if kind == "function" else None

    def eval(self, e):
        k = e[0]
        if k == "lit":
            return e[1]
        if k == "name":
            c = self.cell(e[1])
            return c.v if c is not None else self.invoke(e[1], [])
        if k == "index":
            arr, j = self.element(e)
            return arr.data[j]
        if k == "fcall":
            return self.invoke(e[1], e[2])
        if k == "rel":
            a, b = self.eval(e[2]), self.eval(e[3])
            if isinstance(a, bytes) != isinstance(b, bytes):
                raise RunError("a String compared with a number")
            return {"=": a == b, "<>": a != b, "<": a < b, ">": a > b,
                    "<=": a <= b, ">=": a >= b}[e[1]]
        if k == "bin":
            op, a = e[1], self.eval(e[2])
            if op in ("and", "or") and isinstance(a, bool):
                if op == "and":
                    return self.truth(self.eval(e[3])) if a else False
                return True if a else self.truth(self.eval(e[3]))
            b = self.eval(e[3])
            if op == "+" and (isinstance(a, bytes) or isinstance(b, bytes)):
                if not (isinstance(a, bytes) and isinstance(b, bytes)):
                    raise RunError("a String added to a number")
                return a + b
            if isinstance(a, float) or isinstance(b, float) or op == "/":
                if op == "/":
                    return float(a) / float(b)
                return {"+": a + b, "-": a - b, "*": a * b}[op]
            if op == "+":
                return wrap(a + b)
            if op == "-":
                return wrap(a - b)
            if op == "*":
                return wrap(a * b)
            if op == "div":
                return wrap(_trunc_div(a, b))
            if op == "mod":
                return wrap(a - b * _trunc_div(a, b))
            if op == "and":
                return wrap(a & b)
            if op == "or":
                return wrap(a | b)
            if op == "xor":
                return wrap(a ^ b)
            if op == "shl":
                return wrap(a << (b & 31))
            if op == "shr":
                return wrap((a & MASK) >> (b & 31))
            raise Unsupported(op)
        if k == "neg":
            v = self.eval(e[1])
            return -v if isinstance(v, float) else wrap(-v)
        if k == "not":
            v = self.eval(e[1])
            return (not v) if isinstance(v, bool) else wrap(~v)
        raise Unsupported(k)


# ----------------------------------------------------------------- engine
class Node(object):
    def __init__(self, handle):
        self.handle = handle
        self.keys = {}
        self.inc = None
        self.code = None
        self.values = None
        self.appended = False


class Engine(object):
    """The natives the states call. `read(path)` gives a file's bytes or None;
    everything written lands in `written`, keyed by the path the script used."""

    APP = b"C:\\GAME\\"
    SAVE = b"C:\\SAVE\\"

    def __init__(self, read):
        self.read = read
        self.written = {}
        self.states = {}
        self.nodes = {}
        self.named = {}
        self.handle = 100
        self.active = None
        self.log = []
        self.clock = 0.0
        self.stream = None
        self.files = {}
        self.natives = dict((n[2:].lower(), getattr(self, n)) for n in dir(self)
                            if n.startswith("n_"))

    def _node(self):
        self.handle += 1
        n = Node(self.handle)
        self.nodes[n.handle] = n
        return n

    def _file(self, path):
        if path in self.written:
            return self.written[path]
        return self.read(path)

    # strings, time, paths
    def n_IntToStr(self, v):
        return b"%d" % v

    def n_StrToInt(self, s):
        return int(s)

    def n_StrLength(self, s):
        return len(s)

    def n_SubStr(self, s, i, n):
        if i < 1:
            n, i = n + i - 1, 1
        return s[i - 1:i - 1 + n] if n > 0 else b""

    def n_StrPos(self, sub, s):
        return s.find(sub) + 1

    def n_Ord(self, s):
        return s[0] if s else 0

    def n_FloatToStr(self, f):
        return repr(float(f)).encode("ascii")

    def n_BoolToStr(self, b):
        return b"True" if b else b"False"

    def n__misc_GetRealTime(self):
        self.clock += 0.0001
        return self.clock

    def n_Log(self, s):
        self.log.append(s)

    def n_ExtractFilePath(self, p):
        return p[:p.rfind(b"\\") + 1]

    def n_GetApplicationFileName(self):
        return self.APP + b"cossacks.exe"

    def n_GetAppSaveDirectoryPath(self):
        return self.SAVE

    def n_FileAge(self, p):
        return -1 if self._file(p) is None else 1564229335

    # parsers
    def n_ParserSelectByKey(self, name):
        h = self.named.get(name.strip().lower(), 0)
        if h:
            self.active = h
        return h

    def n_ParserCreate(self, name):
        n = self._node()
        self.named[name.strip().lower()] = self.active = n.handle
        return n.handle

    def n_ParserClearByHandle(self, h):
        n = self.nodes[h]
        if n.values is not None:
            raise RunError("ParserClearByHandle on a Code node")
        n.keys, n.inc, n.code = {}, None, None

    def n_ParserLoadFromFileByHandle(self, h, path):
        data = self._file(path)
        if data is None:
            raise RunError("load of a missing file %r" % path)
        n = self.nodes[h]
        n.inc = I.parse(data)
        c = self._node()
        # The parser drops trailing spaces from values when it loads (run m2a).
        c.values = [v.rstrip(b" ") for v in n.inc.values]
        n.code = c.handle
        return True

    def n_ParserSelectByHandleByKey(self, h, key):
        if key.strip().lower() != b"code":
            raise Unsupported("child %r" % key)
        code = self.nodes[h].code
        if code:
            self.active = code
        return code or 0

    def n_ParserGetCountByHandle(self, h):
        n = self.nodes[h]
        return len(n.values) if n.values is not None else len(n.keys)

    def n_ParserGetValueByIndexByHandle(self, h, i):
        values = self.nodes[h].values
        if values is None or not 0 <= i < len(values):
            raise RunError("value %d of node %d" % (i, h))
        return values[i]

    def n_ParserSelectByHandle(self, h):
        self.active = h
        return h

    def n_ParserSetValueByIndex(self, i, v):
        values = self.nodes[self.active].values
        if values is None or not 0 <= i < len(values):
            raise RunError("set value %d" % i)
        values[i] = v

    def n_ParserSetValueByKeyByHandle(self, h, key, v):
        n = self.nodes[h]
        if key == b"[*]":
            if n.values is None:
                raise RunError("[*] on a node without values")
            if n.appended:
                n.values[-1] = v
            else:
                n.values.append(v)
                n.appended = True
        else:
            n.keys[key.strip().lower()] = v

    def n_ParserGetValueByKeyByHandle(self, h, key):
        return self.nodes[h].keys.get(key.strip().lower(), b"")

    def n_ParserGetIntValueByKeyByHandle(self, h, key):
        v = self.nodes[h].keys.get(key.strip().lower(), b"")
        return int(v) if v.strip() else 0

    def n_ParserSaveToFileByHandle(self, h, path):
        n = self.nodes[h]
        self.written[path] = I.render(n.inc, self.nodes[n.code].values)
        return True

    # streams
    def n_OpenFileStreamForWrite(self, path):
        if self.stream is not None:
            raise RunError("two streams open")
        self.stream = ("w", path, bytearray())

    def n_FileStreamWriteInteger(self, v):
        if self.stream is None or self.stream[0] != "w":
            raise RunError("no stream open for writing")
        self.stream[2].extend(struct.pack("<i", wrap(v)))

    def n_OpenFileStreamForRead(self, path):
        if self.stream is not None:
            raise RunError("two streams open")
        data = self._file(path)
        if data is None:
            raise RunError("stream read of a missing file %r" % path)
        self.stream = ("r", data, [0])

    def n_FileStreamReadInteger(self):
        if self.stream is None or self.stream[0] != "r":
            raise RunError("no stream open for reading")
        data, pos = self.stream[1], self.stream[2]
        if pos[0] >= len(data):
            raise RunError("a stream read past the end of the file")
        chunk = data[pos[0]:pos[0] + 4]
        pos[0] += 4
        return wrap(int.from_bytes(chunk, "little"))

    def n_CloseFileStream(self):
        if self.stream is None:
            raise RunError("no stream open")
        if self.stream[0] == "w":
            self.written[self.stream[1]] = bytes(self.stream[2])
        self.stream = None

    # the handle reader
    def n_OpenFileRead(self, path):
        data = self._file(path)
        if data is None:
            raise RunError("OpenFileRead of a missing file %r" % path)
        self.handle += 1
        self.files[self.handle] = [data, 0]
        return self.handle

    def n_ReadInteger(self, fs, cell):
        data, pos = self.files[fs]
        chunk = data[pos:pos + 4]
        self.files[fs][1] = pos + len(chunk)
        if chunk:
            keep = cell.v & ~((1 << (8 * len(chunk))) - 1) & MASK
            cell.v = wrap(keep | int.from_bytes(chunk, "little"))

    def n_CloseFile(self, fs):
        del self.files[fs]

    # state machines
    def n_GetTriggerManagerStateMachineHandle(self, name):
        return 7 if name.lower() in (b"qm_core", b"qm_test") else 0

    def n_StateMachineExecuteState(self, h, name, arg):
        self.states[name.decode("ascii").lower()].run()


# ------------------------------------------------------------------ runs
@pytest.fixture(scope="module")
def cases(game_dir, reference_dir):
    all_cases = C.build_cases(game_dir, reference_dir)
    files, manifest = C.render_tree(all_cases, game_dir)
    return all_cases, files


@pytest.fixture(scope="module")
def states():
    loaded, helpers = H.load_sources()
    return dict((st.name.lower(), H.state_code(st, helpers, H.BUILD_VARIABLES))
                for st in loaded if st.name in ("qmMerge", "qmCaseMerge"))


def run_suite(game_dir, files, names, states, patch=None):
    """qmSelfTest's part for one case file: the runtime parser, the case
    loaded into qm_case, qmCaseMerge run - over the cases in `names`."""
    suite = I.parse(files[C.FIXTURE + "/m3/" + C.SUITE])
    chosen = [v for v in suite.values if v.split(b" ")[1].decode() in names]
    fixture = Engine.APP + ("mods\\%s\\" % C.FIXTURE).encode()
    data = Engine.APP + b"data\\"

    def read(path):
        if path == fixture + b"m3\\" + C.SUITE.encode():
            return I.render(suite, chosen)
        if path.startswith(fixture):
            return files.get(C.FIXTURE + "/" + path[len(fixture):].decode().replace("\\", "/"))
        if path.startswith(data):
            try:
                return C.vanilla(game_dir, "data/" + path[len(data):].decode().replace("\\", "/"))
            except OSError:
                return None
        if path == Engine.SAVE + b"qm_test\\cases\\" + C.CASE_FILE.encode():
            return files["cases/" + C.CASE_FILE]
        return None

    eng = Engine(read)
    try:
        for name, code in states.items():
            if patch:
                code = [patch(line) for line in code]
            eng.states[name] = State(code, eng)
    except Unsupported as exc:
        pytest.skip("the interpreter does not cover the emitted source: %s" % exc)
    out = Engine.SAVE + b"qm_test\\out\\"
    rt = eng.n_ParserCreate(b"qm_case_rt")
    eng.n_ParserSetValueByKeyByHandle(rt, b"outdir", out)
    eng.n_ParserSetValueByKeyByHandle(rt, b"out", out + b"qm_m3.txt")
    eng.n_ParserSetValueByKeyByHandle(rt, b"status", b"started")
    case = eng.n_ParserCreate(b"qm_case")
    eng.n_ParserLoadFromFileByHandle(case, Engine.SAVE + b"qm_test\\cases\\" + C.CASE_FILE.encode())
    # The run makes millions of short-lived tuples; the cyclic collector would
    # walk every live object of the test session for each batch of them.
    collecting = gc.isenabled()
    gc.disable()
    try:
        eng.states["qmcasemerge"].run()
    except Unsupported as exc:
        pytest.skip("the interpreter does not cover a native: %s" % exc)
    finally:
        if collecting:
            gc.enable()
    status = eng.n_ParserGetValueByKeyByHandle(rt, b"status")
    return eng, dict((k[len(out):].decode(), v) for k, v in eng.written.items()
                     if k.startswith(out)), status


def check(game_dir, all_cases, files, names, states):
    """Problems of one interpreted run over `names`: rows and output files
    must be the expected ones byte for byte, and every merge must be done."""
    eng, out, status = run_suite(game_dir, files, names, states)
    assert status == b"ok"
    summary = dict((row.split(b"|")[1].decode(), row.split(b"|"))
                   for row in out["qm_m3.txt"].split(b"\r\n") if row.startswith(b"m3case"))
    problems = []
    for case in all_cases:
        if case.name not in names:
            continue
        row = summary.get(case.name)
        if row is None or row[2] != b"1":
            problems.append("%s: not done" % case.name)
            continue
        if out.get(case.name + ".txt") != files["expected/%s.txt" % case.name]:
            problems.append("%s: rows differ" % case.name)
        want = files.get("expected/%s.inc" % case.name)
        if out.get(case.name + ".inc") != want:
            problems.append("%s: output differs" % case.name)
        if row[3] != (b"yes" if want is not None else b"none"):
            problems.append("%s: written=%s" % (case.name, row[3].decode()))
    return problems


#: The cases the default run covers - the interpreter is slow, so small files
#: only: the named cases on oncamera.inc (probe 5, the fixtures, the keys),
#: the hook step on two hook files and on a winner, and the first random cases
#: on files of at most SMALL values. The slow run covers every case.
FAST_NAMED = ("probe5", "probe5_hook", "wasd_camspeed_oncamera", "wasd_conflict_oncamera",
              "wasd_camspeed_conflict_oncamera", "key_bom", "key_whitespace",
              "vanilla_only", "repl_wta_hook", "hookfile_cameracontrol",
              "hookfile_initminimap", "hookfile_cameracontrol_wta")
SMALL = 120


def fast_names(all_cases, random_count=14):
    out = []
    for c in all_cases:
        tag = c.name.split("_", 2)[2]
        if tag in FAST_NAMED:
            out.append(c.name)
        elif "random" in c.tags and random_count and max(
                len(I.parse(d).values) for _m, d in c.parts) <= SMALL:
            out.append(c.name)
            random_count -= 1
    return set(out)


def test_the_emitted_merge_dumps_refs_rows(game_dir, cases, states):
    all_cases, files = cases
    names = fast_names(all_cases)
    assert len(names) == len(FAST_NAMED) + 14
    assert check(game_dir, all_cases, files, names, states) == []


@pytest.mark.slow
def test_the_emitted_merge_dumps_refs_rows_on_every_case(game_dir, cases, states):
    all_cases, files = cases
    assert check(game_dir, all_cases, files, set(c.name for c in all_cases), states) == []


def test_a_wrong_tie_break_is_caught(game_dir, cases, states):
    """The gate has teeth: Myers' tie-break turned around changes some rows."""
    all_cases, files = cases
    names = fast_names(all_cases, random_count=8) - set(
        c.name for c in all_cases if "random" not in c.tags)
    wrong = b"if (qmDfT[qmDrBp+qmDrJ-1]<qmDfT[qmDrBp+qmDrJ]) then"
    assert any(wrong in line for line in states["qmmerge"])
    _eng, out, _status = run_suite(game_dir, files, names, states,
                                   patch=lambda l: l.replace(wrong, wrong.replace(b"<", b"<=")))
    differ = [n for n in names if out.get(n + ".txt") != files["expected/%s.txt" % n]]
    assert differ
