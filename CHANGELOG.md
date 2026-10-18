# Changes

## 0.1.8 (2026-10-18)

- A mod that says in its about.cfg it must load after another mod (`loadAfter`, `requires`,
  `extends`, or the other mod's `loadBefore`) now does, without you pressing Auto-sort.
  Example: you subscribe to Reinforced - LAN after Reinforced - Core; before, LAN stayed
  below Core and the lobby of Core was lost. Now Quartermaster puts Core just under LAN
  the first time the game starts and says so in its report.
- Only the mod that has to move is moved; all other mods stay where they were.
- An order you set yourself in the window is never changed. If it breaks a rule you still
  get the warning, as before.
- If the rules of two mods contradict each other, nothing is moved and the report shows
  the error.
- Mod authors get a new line for the mod's about.cfg file: `carries = <id of the other mod>`.
  It is for a mod that already contains another mod's changes (for example a combined
  build). When that mod loads after the one it carries, the two no longer show a warning for
  the files they share: the report says "carried" instead, and conflicts.txt still lists
  the conflicts. If the order is the other way round, the warning stays. An older
  Quartermaster ignores the line and shows one note about an unknown key.

Workshop change note:

> 0.1.8: a mod that has to load after another mod (its author says so in the mod's
> about.cfg file) is now put in the right place by itself, the first time the game starts;
> you no longer need to press Auto-sort. Only that one mod moves, all other mods stay where
> they were. A list you arranged by hand stays as it is. For mod authors: a new about.cfg
> line, `carries`, for a mod that already contains another mod's changes (for example a
> combined build); such a mod no longer shows warnings for the files they share, as long as
> it loads after the mod it carries.
