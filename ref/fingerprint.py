r"""The start-up fingerprint (docs/plan.md S8, guard 2) and the hash behind it.

Quartermaster regenerates only when the fingerprint changes, so the fingerprint
must be made of INPUTS only. Anything Quartermaster itself writes - its outputs,
its own folder, its position in mods.ini - would change on every generation and
restart the game forever (docs/research/startup-chain.md, "Restart-loop risks").

Inputs, one line each, the mods in load order (`ref.order` load_order: the
player's saved order, else mods.ini's own):

    qm-fingerprint 1                 format of this text
    qm <version>                     Quartermaster's version
    vanilla <stamp>                  vanilla's FileAge (the caller picks the file)
    w 873048118 on <stamp>           a Workshop mod, enabled, its timeupdated
    l SomeLocalMod off               a local mod, disabled: no stamp

A disabled mod contributes its id and flag but no stamp: enabling it changes the
fingerprint, while a Workshop update of a mod nobody runs does not. Quartermaster's
own dir is left out entirely.

The order of the lines is an input too (decided 2026-09-28): it
decides which mod wins a conflict and whose file the engine loads, so a
reorder in the manager is a new fingerprint. Until then the lines were in
canonical order whatever mods.ini said. The header stays `qm-fingerprint 1`:
with no saved order the load order was the canonical one and the text byte
for byte what it had been. Since 2026-09-30 it is mods.ini's own order,
so for a mods.ini not in canonical order the text is another one and the
first boot after that update regenerates once; nothing had been released
before it.

`qhash` is the hash the game side can compute: no string hash exists in the
engine API, and what Integer overflow does there is not verified yet (M0), so
every intermediate value stays below 2^31. Two polynomial hashes modulo primes
chosen so that `h*M + 256` cannot overflow:

    h1 = (h1*257 + byte + 1) mod 8355967      max 8355966*257 + 256 = 2147483518
    h2 = (h2*263 + byte + 1) mod 8165329      max 8165328*263 + 256 = 2147481520

plus the length. `mod` is in vanilla (doprogress.inc:282), `Ord` returns a Byte.
"""
from .order import LOCAL, OTHER, SELF, WORKSHOP, canonical_key, identity

__all__ = ["FORMAT", "H1", "H2", "INT_MAX", "qhash", "fingerprint_text",
           "fingerprint"]

FORMAT = b"qm-fingerprint 1"
H1 = (257, 8355967)
H2 = (263, 8165329)
INT_MAX = 2 ** 31 - 1

_ORIGIN = {WORKSHOP: b"w", LOCAL: b"l", OTHER: b"o"}


def _as_bytes(v):
    return b"%d" % v if isinstance(v, int) else bytes(v)


def qhash(data):
    """`b'<h1>-<h2>-<length>'` of `data`."""
    (m1, p1), (m2, p2) = H1, H2
    h1 = h2 = 0
    for b in data:
        h1 = (h1 * m1 + b + 1) % p1
        h2 = (h2 * m2 + b + 1) % p2
    return b"%d-%d-%d" % (h1, h2, len(data))


def fingerprint_text(mods, vanilla_stamp, qm_version, self_dir=None, order=None):
    """mods = [(dir, enabled, stamp)] in any order; returns the text with the
    mods in load order: `order` = the dirs in load order (ref.order
    load_order), None for the canonical order (no saved order)."""
    rank = None if order is None else dict((d, k) for k, d in enumerate(order))
    rows = []
    for d, enabled, stamp in mods:
        key = canonical_key(d, self_dir)
        if key[0] == SELF:
            continue
        origin, ident = identity(d)
        row = _ORIGIN[origin] + b" " + ident + (b" on " + _as_bytes(stamp)
                                                if enabled else b" off")
        rows.append(((rank[d],) if rank is not None else key, row))
    rows.sort()
    lines = [FORMAT, b"qm " + _as_bytes(qm_version),
             b"vanilla " + _as_bytes(vanilla_stamp)] + [r for _k, r in rows]
    return b"\n".join(lines) + b"\n"


def fingerprint(mods, vanilla_stamp, qm_version, self_dir=None, order=None):
    return qhash(fingerprint_text(mods, vanilla_stamp, qm_version, self_dir, order))
