r"""The English master of Quartermaster's texts, taken from the code.

    python tools/qmtext.py            print what src/text/en.cfg should hold
    python tools/qmtext.py --write    write src/text/en.cfg
    python tools/qmtext.py --check    exit 1 when src/text/en.cfg differs from the code
    python tools/qmtext.py --status   how far each language is translated
    python tools/qmtext.py --missing CODE        the texts CODE still lacks, as key = English
    python tools/qmtext.py --fill CODE FILE      FILE (UTF-8, one translation per line, in the order
                                                 --missing prints them) added to src/text/CODE.cfg

A text the player sees is written qmT('English') in the code (src/lib/qmtext.pas);
the English stays there, and en.cfg is only the list the translators work from.
The other fifteen languages are translated from it (docs/localisation.md).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for p in (HERE, REPO):
    if p not in sys.path:
        sys.path.insert(0, p)

import hbuild  # noqa: E402
from ref import lang  # noqa: E402

TEXT = os.path.join(REPO, "src", "text")
EN = os.path.join(TEXT, "en.cfg")


def main(argv):
    english = hbuild.collect_english()
    data = hbuild.english_source(english)
    if "--write" in argv:
        os.makedirs(TEXT, exist_ok=True)
        with open(EN, "wb") as fh:
            fh.write(data)
        print("%d texts written to src/text/en.cfg" % len(english))
        return 0
    if "--check" in argv:
        have = open(EN, "rb").read() if os.path.exists(EN) else b""
        if have != data:
            print("src/text/en.cfg is not what the code holds; run tools/qmtext.py --write")
            return 1
        return 0
    if "--missing" in argv or "--fill" in argv:
        flag = "--missing" if "--missing" in argv else "--fill"
        code = argv[argv.index(flag) + 1]
        path = os.path.join(TEXT, code + ".cfg")
        have = dict(lang.parse(open(path, "rb").read())[0]) if os.path.exists(path) else {}
        todo = [(k, v) for k, v in sorted(english.items()) if k not in have]
        if flag == "--missing":
            for k, v in todo:
                print("%s = %s" % (k, v))
            return 0
        with open(argv[argv.index(flag) + 2], "rb") as fh:
            values = [ln for ln in fh.read().decode("utf-8").splitlines() if ln.strip()]
        if len(values) != len(todo):
            print("%d translations given for %d missing texts" % (len(values), len(todo)))
            return 1
        have.update((k, v.strip()) for (k, _e), v in zip(todo, values))
        with open(path, "wb") as fh:
            fh.write("".join("%s = %s\n" % (k, have[k]) for k in sorted(english) if k in have).encode("utf-8"))
        print("%s: %d texts added, %d of %d" % (code, len(todo), len(have), len(english)))
        return 0
    if "--status" in argv:
        for code in lang.CODES[1:]:
            path = os.path.join(TEXT, code + ".cfg")
            have = dict(lang.parse(open(path, "rb").read())[0]) if os.path.exists(path) else {}
            print("%s %-22s %4d of %d" % (code, lang.NAMES[code], sum(k in have for k in english), len(english)))
        return 0
    sys.stdout.write(data.decode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
