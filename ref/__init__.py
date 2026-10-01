"""Python reference of every algorithm Quartermaster runs inside the game.

Each module here is the twin of a piece of game-side code (docs/plan.md section 3,
G2/G6/G8/G9). The game-side code is written in the engine's Pascal dialect, where
a local array holds at most 1M Integers and a String pool about 200k entries, so
these twins are written the way the game has to run them - flat Integer arrays,
explicit loops, no clever library calls - and not the most Pythonic way. In-game
results are compared against this package, so a behaviour that differs between
the two is a bug in one of them, never a matter of taste.

Everything works on `bytes`. A game file is read with `read_bytes()` and handed
over unchanged; nothing here decodes text.

    textio       the raw 4-byte reader and writer, the character table, `~NNN`
                 escapes, and the normalisation used when comparing lines
    inc          `.inc` state files: the `Code` values, byte-identical round trip,
                 and the layout the engine's parser writes
    diff         common prefix/suffix trim, then greedy Myers with a capped D
    merge        three-way merge of several mods against vanilla, and the
                 classifier (conflict, identical, proximity, replacement)
    order        canonical mod order (Workshop id / local folder, Quartermaster last)
    fingerprint  the start-up fingerprint of the inputs, and a hash the game can
                 compute without Integer overflow
"""
