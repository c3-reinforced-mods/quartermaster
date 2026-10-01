hook: data/gui/menu.inc/eventmainmenu.inc
requires:
---
//! The vanilla "Mod manager" button opens Quartermaster's manager instead of
//! the Workshop page (plan S5, G15; docs/ui.md).
//!
//! The button is ShowButton('bmodman', ..., cTagModManager, ...)
//! (data/gui/menu.inc/showmainmenu.inc:141) and its arm only calls OpenURL
//! (eventmainmenu.inc:154-156). cTagModManager = 108 (eventmainmenu.inc:20);
//! the literal is spelled out because hook lines name the engine's API only,
//! and the vanilla locals `tag` / `press` / `cTagModManager` are not part of
//! it - so the event values are read again with the engine's own getters.
//!
//! The build puts the lines at the hook index of plan S5 (ref/inc.py
//! hook_index), which is 0 here: the state starts with no routine. What they
//! then run ahead of (eventmainmenu.inc:4-27) has no effect an early exit
//! could lose - three reads of the event values, constants, the pure name
//! helper _misc_GetGUIShowEventStateNames (misc.script:1929-1940) and the
//! Ctrl remap of tag 100 - so for tag 108 the result is the same as in
//! front of `if (press='c') then`.
//!
//! `and` short-circuits (capability probes, probe 4), so the parser is read
//! only when it exists. qm_ui `ready` is 1 only while both manager states are
//! in the GUI machine (qmUiEnsure); until then, and in any installation where
//! Quartermaster's controller never loaded, the button keeps its vanilla
//! meaning.
var qmMmUi : Integer = ParserSelectByKey('qm_ui');
if (qmMmUi<>0) and (GetIntValueByName('Tag')=108) and (GetValueByName('Press')='c') and (ParserGetIntValueByKeyByHandle(qmMmUi, 'ready')=1) then
begin
   ExecuteState('ShowQmManager');
   exit;
end;
