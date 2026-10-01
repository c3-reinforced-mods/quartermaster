# Start here

Quartermaster - merge framework + in-game mod manager for Cossacks 3. What it is and how
to build and test it: [README.md](README.md). The design: [docs/plan.md](docs/plan.md).

Working copy: `C:\projects\Cossacks 3\cossacks3-quartermaster`. Public repo name later: `pjugowiec/cossacks3-quartermaster`.

## Layout
- `docs/plan.md` - where the design stands, safety decisions, architecture, test mods, milestones, decisions
- `docs/ui.md` - the manager window and the report seams; `docs/authoring.md` - about.cfg
- `docs/research/` - verified facts (`context-2026-09-27.md`), startup chain and file classes, GUI patterns, SWFP reuse, architecture reviews
- `src/` game-side code, `ref/` its Python twin, `tools/` build and harness, `tests/` the suite

Raw research material - probe generators and launcher, logs of the in-game runs, the engine API list - is not part of the repository.

The texts for players (the window, the report, the Workshop page) are final for 0.1.0, since
2026-09-30. Until then this file said they were placeholders.
