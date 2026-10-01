helpers:
requires:
---
//! Every line Quartermaster writes to the game log starts with the marker
//! `[qm]`, so a harness or a player can grep one run's lines out of
//! cos_*.log. Log is the engine's own native (`procedure Log(const msg:
//! String)` in cossacks.exe's registration table); the line appears in the log
//! as `LOG| <n> |[qm] <text>`.
//!
//! A helper, not a library routine: every state compiles alone and the engine
//! loads no library of ours, so the build inlines this at the top of each
//! state that names it (the vanilla precedent for a procedure at the top of a
//! state is data/gui/menu.inc/cameracontrol.inc:4-10).
procedure qmLog(qmMsg : String);
begin
   Log('[qm] '+qmMsg);
end;
