r"""Statement coverage of the game-side Pascal by the offline tests.

    set QM_PASCOV=<folder> & python -m pytest --runslow -n auto
    python tools/pascov.py <folder> [--lines]

The tests run the emitted states through the interpreter of
tests/test_m3_pascal.py. With QM_PASCOV set it records, per source text it
parsed, the lines a statement starts on and the lines whose statement ran,
and every test process writes them to <folder>\<worker>.json (conftest). This
tool maps each recorded text back to the template it was built from (a state
or screen with its helpers, a hook, the guard) and each line back to its
src\*.pas file and line, then prints, per file, how many statement lines the
tests ran.

A statement is an assignment, a call, an if, a while, a for or an exit; a
declaration or a begin/end is not counted. A helper's line counts as run when
any state that inlines it ran it. A unit no test parsed is counted from its
own parse, all of it not run; one the interpreter cannot parse is listed apart.
What runs only in the game (the guard before the compile, the screens' event
code the interpreter does not model) shows here as not run: the in-game cases
cover that, and this number does not see them.
"""
import argparse
import difflib
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for path in (REPO, HERE, os.path.join(REPO, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)
sys.dont_write_bytecode = True

import hbuild as H  # noqa: E402


def origins(t, variables):
    """`(path, line)` of every line `render_lines(t, variables)` gives; None for
    the lines a placeholder on a line of its own expands to (generated data)."""
    values = {v: H._value_lines(t, v, variables[v]) for v in t.requires}
    out = []
    for i, raw in enumerate(t.body, t.first_line):
        stripped = raw.lstrip()
        if stripped.startswith(H._NOTE):
            continue
        hit = H._PLACEHOLDER.fullmatch(stripped)
        if hit:
            out += [None] * len(values[hit.group(1).decode()])
            continue
        out.append((t.path, i))
    return out


def units():
    """`[(name, code lines, origins)]`: every piece of emitted code a test can run."""
    v = H.BUILD_VARIABLES
    out = []
    states, helpers = H.load_sources()
    for st in states:
        code = H.state_code(st, helpers, v)
        where = []
        for name in H.resolve_helpers(st, helpers):
            where += origins(helpers[name], H._vars_for(helpers[name], v)) + [None]
        where += origins(st, H._vars_for(st, v))
        out.append((st.name, code, where))
    for hook in H.load_hooks():
        out.append((hook.name, H.hook_code(hook, v), origins(hook, H._vars_for(hook, v))))
    guard = H.load_guard()
    if guard is not None:
        gv = {"guardages": H.qstr("|0|")}
        out.append((guard.name, H.render_lines(guard, gv), origins(guard, gv)))
    for name, code, where in out:
        if len(code) != len(where):
            raise SystemExit("%s: %d code lines but %d origins" % (name, len(code), len(where)))
    return out


def text_of(code):
    return "\n".join(line.decode("latin-1") for line in code)


#: A record field (`gGame.gamemode`), which the interpreter does not read:
#: made one name, in place, only to count a unit's statements.
_FIELD = re.compile(r"(?<=[A-Za-z0-9_\]])\.(?=[A-Za-z_])")


def statement_lines(text):
    """The lines a counted statement starts on, and whether the text had to
    lose its record fields to parse; None if it does not parse even then."""
    import test_m3_pascal as PAS
    for flat, src in ((False, text), (True, _FIELD.sub("_", text))):
        lines, marks = [], {}
        try:
            PAS.Parser(PAS.lex(src, lines), lines, marks).program()
        except PAS.Unsupported:
            continue
        return set(marks.values()), flat
    return None


def match(text, by_text, by_count, units):
    """`(unit, {recorded line: unit line})` for a recorded text: the same text;
    the unit with as many lines and most of them equal (a test that replaced
    names in some lines: test_m5_pascal DOTTED, a mutation); or the unit whose
    lines it shares, aligned (a test that built the state from fewer helpers).
    None for a snippet that is no unit."""
    if text in by_text:
        u = by_text[text]
        return u, None
    rec = text.split("\n")
    best, score = None, 0
    for u in by_count.get(len(rec), []):
        same = sum(a == b for a, b in zip(rec, u[3]))
        if same > score:
            best, score = u, same
    if best is not None and score >= 0.8 * len(rec):
        return best, None
    if len(rec) < 20:
        return None
    have = set(rec)
    u = max(units, key=lambda x: len(have & set(x[3])))
    m = difflib.SequenceMatcher(None, rec, u[3], autojunk=False)
    mapping = {}
    for a, b, size in m.get_matching_blocks():
        for k in range(size):
            mapping[a + k + 1] = b + k + 1
    if len(mapping) < 0.8 * len(rec):
        return None
    return u, mapping


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("folder")
    p.add_argument("--lines", action="store_true", help="list the lines not run, per file")
    args = p.parse_args(argv)
    rows = []
    for fn in sorted(glob.glob(os.path.join(args.folder, "*.json"))):
        with open(fn, encoding="utf-8") as fh:
            rows += json.load(fh)
    if not rows:
        raise SystemExit("no coverage files in %s" % args.folder)

    all_units = []
    for name, code, where in units():
        text = text_of(code)
        all_units.append((name, text, where, text.split("\n")))
    by_text = {u[1]: u for u in all_units}
    by_count = {}
    for u in all_units:
        by_count.setdefault(len(u[3]), []).append(u)

    total, ran = set(), set()
    seen, snippets = set(), 0
    for row in rows:
        hit = match(row["text"], by_text, by_count, all_units)
        if hit is None:
            snippets += 1
            continue
        u, mapping = hit
        seen.add(u[0])
        where = u[2]
        for key, lines in (("lines", total), ("ran", ran)):
            for line in row[key]:
                if mapping is not None:
                    line = mapping.get(line)
                    if line is None:
                        continue
                if 0 < line <= len(where) and where[line - 1] is not None:
                    lines.add(where[line - 1])
    unparsed, flattened = [], []
    for name, text, where, _ in all_units:
        if name in seen:
            continue
        found = statement_lines(text)
        if found is None:
            unparsed.append(name)
            continue
        lines, flat = found
        if flat:
            flattened.append(name)
        total.update(where[n - 1] for n in lines if where[n - 1] is not None)

    per = {}
    for path, line in total:
        per.setdefault(path, [0, 0, []])
        per[path][0] += 1
        if (path, line) in ran:
            per[path][1] += 1
        else:
            per[path][2].append(line)
    width = max(len(p) for p in per)
    for path in sorted(per):
        n, r, missing = per[path]
        print("%-*s %5d %5d %6.1f%%" % (width, path, n, r, 100.0 * r / n))
        if args.lines and missing:
            print("    not run: %s" % ", ".join(str(m) for m in sorted(missing)))
    n, r = len(total), len(total & ran)
    print("%-*s %5d %5d %6.1f%%" % (width, "TOTAL", n, r, 100.0 * r / n if n else 0.0))
    print("units run by a test: %d of %d; snippets that are no unit: %d; counted with "
          "their record fields made names (the interpreter does not run them): %s; "
          "not counted at all: %s"
          % (len(seen), len(all_units), snippets, ", ".join(flattened) or "none",
             ", ".join(unparsed) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
