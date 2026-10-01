r"""The manifest of written outputs (docs/plan.md S9, G12): the twin of the
manifest part of src/states/qmwritegen.pas and of src/lib/qmmanifest.pas.

`<QmDir>\data\quartermaster\state\manifest.cfg` lists what one generation
wrote into Quartermaster's folder, so the next generation knows which files
are its own and can remove the ones no longer needed (plan S9). It lives in
Quartermaster's folder, next to the outputs, so a Workshop update that wipes
the folder takes both together.

Format
------
The shape of a one-state `.inc` in the engine's layout (ref/inc.py
layout_lines), written by the game's raw writer: CRLF, padded with spaces to
a multiple of 4 bytes. That is the shape of vanilla.idx too.

    section.begin
       Name = qmManifest
       Format = 1
       Code : struct.begin
          [*] = ;gen|<N>
          [*] = ;outhash|<outputs hash>
          [*] = ;fp|<fingerprint of the inputs>
          [*] = ;out|<path>|<token>|<tier>|<mode>|<status>|<reason>|<hunks>|<conflicts>|<proximity>
          [*] = ;src|<path>|<position>|<origin>|<identity, hex>|<FileAge>
          ...
          [*] = ;left|<path>|<token>
       struct.end
    section.end
    <empty line>

- `out`: one per output written, in plan order (vanilla.idx order), followed
  by one `src` per participant in canonical order. `path` is relative to
  data\ (vanilla.idx spelling); `token` is ref/validate.py token of the file's
  key lines and values - it determines the bytes, as the file is the engine
  layout of exactly those; `tier` is the candidate that was written; mode,
  status, reason, hunks, conflicts, proximity summarise the merge (`-`, `-`,
  `-`, 0, 0, 0 without one; `error`, `fail` on a merge error).
- `src`: a participant: canonical position, origin letter (`w` Workshop, `l`
  local, `o` other - qm_mods `fo`), its identity (qm_mods `id`: the Workshop
  id or the folder name) as lower-case hex, and the FileAge of its copy of the
  file (qm_index `a`). ModLibraryGetData has no timeupdated (M2), so there is
  no field for it.
- `left`: an output of an earlier generation that DeleteFileStream did not
  remove, overwritten with the file the game should use now (plan S9). The
  next generation tries to delete it again.
- No timestamps. The generation N stays the same when the outputs hash does
  (`next_generation`), so two generations from the same inputs write the
  same bytes.

Reading it back in game: the raw reader without a size (qmraw.pas, the handle
reader - exact for a text file, SelfTest run m2a3: 25 `rawh` rows equal to the
sized reader) and qminc.pas's line model, the same path as every `.inc`
Quartermaster reads. A value comes back as an internal string, so `|` (124,
outside the character table) reads `~124`; qmmanifest.pas splits on that.
"""
from . import inc as I
from .fingerprint import qhash
from .textio import escape, read_lines, unescape, write_file

__all__ = ["MANIFEST_REL", "KEYS", "Output", "Manifest", "outputs_hash",
           "next_generation", "render", "parse", "lines"]

MANIFEST_REL = b"quartermaster\\state\\manifest.cfg"
KEYS = [b"Name = qmManifest", b"Format = 1"]


class Output(object):
    __slots__ = ("path", "tok", "tier", "summary", "srcs")

    def __init__(self, path, tok, tier, summary, srcs):
        self.path, self.tok, self.tier = path, tok, tier
        self.summary = summary      # (mode, status, reason, hunks, conflicts, proximity)
        self.srcs = srcs            # [(position, origin, identity, FileAge)]


class Manifest(object):
    def __init__(self):
        self.gen = 0
        self.outhash = b"-"
        self.fp = b"-"
        self.outs = []      # (path, token)
        self.lefts = []     # (path, token)

    def paths(self):
        """Every file this manifest says Quartermaster wrote, in its order."""
        return [p for p, _t in self.outs] + [p for p, _t in self.lefts]


def outputs_hash(entries):
    """qhash of `<path>|<token without gen lines>` LF per output, plan order."""
    return qhash(b"".join(p + b"|" + t + b"\n" for p, t in entries))


def next_generation(prev, outhash):
    """The previous N when nothing changed, else N + 1 (1 for a first one)."""
    if prev is None:
        return 1
    return prev.gen if prev.outhash == outhash else prev.gen + 1


def lines(gen, outhash, fp, outs, lefts):
    """The Code values, raw bytes."""
    out = [b";gen|%d" % gen, b";outhash|" + outhash, b";fp|" + fp]
    for o in outs:
        mode, status, reason, hunks, conflicts, prox = o.summary
        out.append(b"|".join([b";out", o.path, o.tok, o.tier, mode, status, reason,
                              b"%d" % hunks, b"%d" % conflicts, b"%d" % prox]))
        for pos, origin, ident, age in o.srcs:
            out.append(b"|".join([b";src", o.path, b"%d" % pos, origin,
                                  ident.hex().encode("ascii"), b"%d" % age]))
    for path, tok in lefts:
        out.append(b";left|" + path + b"|" + tok)
    return out


def render(gen, outhash, fp, outs, lefts):
    """The manifest file's bytes."""
    return write_file(I.layout_lines(KEYS, [escape(v) for v in
                                             lines(gen, outhash, fp, outs, lefts)]))


def parse(data):
    """A `Manifest` from the file's bytes, read the way the game reads it."""
    _form, _keys, values = I.values_from_lines(read_lines(data))
    m = Manifest()
    for v in values:
        f = unescape(v).split(b"|")
        if f[0] == b";gen":
            m.gen = int(f[1]) if len(f) > 1 and f[1].isdigit() else 0
        elif f[0] == b";outhash" and len(f) > 1:
            m.outhash = f[1]
        elif f[0] == b";fp" and len(f) > 1:
            m.fp = f[1]
        elif f[0] == b";out" and len(f) > 2:
            m.outs.append((f[1], f[2]))
        elif f[0] == b";left" and len(f) > 2:
            m.lefts.append((f[1], f[2]))
    return m
