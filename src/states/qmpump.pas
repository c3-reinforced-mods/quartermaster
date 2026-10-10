state: qmPump
into: data/quartermaster/core.aix
helpers: qmlog
requires:
---
//! The tick's stand-in when no frame runs it (plan S5, G14). qmTick hangs on
//! a line in DoProgress, a merged state: the copy this process loaded is the
//! one the last generation wrote, and when a mod it was merged from has been
//! switched off outside Quartermaster since - in mods.ini by the game's own
//! manager, by hand, by unsubscribing - that copy calls a library that is not
//! loaded and does not compile. Hands-on, 2026-10-10 (Reinforced - Core off,
//! the outputs of generation 241 made with it): "Compile script error:
//! DoProgress", the boot regenerated and asked for its restart, the restart
//! never came, and the manager window answered every Apply with "Still
//! checking the last change; a moment." for minutes. The boot hooks and the
//! window ran: they are other states.
//!
//! So the window runs this state - ShowQmManager before a fresh open,
//! EventQmManager before and after every command - and it runs qmTick when
//! the frame hook does not: qmTick leaves the time of every run by a frame in
//! qm_rt `tkat`, and a second without one, in the main menu with no boot
//! running, means no frame runs it (DoProgress runs every 10 ms, menu.cfg:20,
//! :28). A run too many costs nothing: qmTick does what is pending and no
//! more. qm_rt `pump` = 1 tells qmTick who runs it (qmrestarttick.pas: the
//! work, nothing a frame draws, not the restart), `pumps` counts the runs.
//!
//! A restart that is pending then runs here and at once. Nothing would tick
//! again to show the notice for a frame or to wait out the second after the
//! last write, and the minute after which qmTick drops a late restart does
//! not count either: this process runs files older than the ones on the
//! disk, and the restart is what loads them. Main menu, outside a map and
//! with no MP sync, as qmTick asks. The notice is put up (qm_ui mode 2) for
//! the redraw of whoever runs this state.
var qmPuRt : Integer = ParserSelectByKey('qm_rt');
if (qmPuRt=0) then
exit;
if (gInterface.gamemode<>gc_gamemode_mainmenu) then
exit;
if (ParserGetIntValueByKeyByHandle(qmPuRt, 'busy')=1) or (ParserGetIntValueByKeyByHandle(qmPuRt, 'pump')=1) then
exit;
var qmPuNow : Integer = Floor(_misc_GetRealTime*10);
var qmPuAt : Integer = ParserGetIntValueByKeyByHandle(qmPuRt, 'tkat');
if (qmPuAt>0) and (qmPuNow-qmPuAt<10) then
exit;
var qmPuCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
if (qmPuCore=0) then
exit;
var qmPuN : Integer = ParserGetIntValueByKeyByHandle(qmPuRt, 'pumps');
if (qmPuN=0) then
begin
   if (qmPuAt=0) then
   qmLog('pump: no main-menu frame has run Quartermaster''s tick in this start (a merged DoProgress that does not compile takes the hook with it); the manager window does its work from now on')
   else
   qmLog('pump: no main-menu frame has run Quartermaster''s tick for '+IntToStr(qmPuNow-qmPuAt)+' tenths; the manager window does its work from now on');
end;
ParserSetIntValueByKeyByHandle(qmPuRt, 'pumps', qmPuN+1);
ParserSetIntValueByKeyByHandle(qmPuRt, 'pump', 1);
StateMachineExecuteState(qmPuCore, 'qmTick', 0);
ParserSetIntValueByKeyByHandle(qmPuRt, 'pump', 0);
if (ParserGetIntValueByKeyByHandle(qmPuRt, 'rs')=1) and (gMap.gamestage=gc_map_gamestage_none) and (ParserGetIntValueByKeyByHandle(qmPuRt, 'sync')=0) then
begin
   ParserSetIntValueByKeyByHandle(qmPuRt, 'rs', 2);
   var qmPuUi : Integer = ParserSelectByKey('qm_ui');
   if (qmPuUi<>0) then
   if (ParserGetIntValueByKeyByHandle(qmPuUi, 'ready')=1) then
   ParserSetIntValueByKeyByHandle(qmPuUi, 'mode', 2);
   qmLog('restart now kind='+ParserGetValueByKeyByHandle(qmPuRt, 'rskind')+' why='+ParserGetValueByKeyByHandle(qmPuRt, 'rswhy')+' from the manager window: no frame runs the tick');
   StateMachineExecuteState(qmPuCore, 'qmRestart', 0);
end;
