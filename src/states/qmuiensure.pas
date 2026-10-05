state: qmUiEnsure
into: data/quartermaster/core.aix
helpers: qmlog
requires:
---
//! Puts the manager's two GUI states, ShowQmManager and EventQmManager, into
//! the GUI state machine. Quartermaster cannot ship menu.aix (plan S2), so the
//! states are added at run time from code lines it ships in
//! data/quartermaster/ui/*.inc, read through the engine parser - mechanism (a)
//! of the capability probes (probe 9: real clicks reach such states). Every
//! line is added before the state first runs: code added to a compiled state
//! needs StateMachineLibraryFlush (earlier probe round r4).
//!
//! The CameraControl hook runs this state on every DoCreate. It acts in the
//! main menu only, the one place the manager opens from.
//!
//! No lookup by name is silent when the name is missing: the engine offers no
//! state count, and the name lookups (StateMachineGetStateIndByName,
//! ...HndByName) go through TXStateMachine.IndexOfState, which logs one ERROR
//! line per lookup of a missing name (capability probes, probe 10; until
//! 0.1.3 this check used one and so cost one such line at the first main
//! menu after every battle). A lookup of a present name is silent, so the
//! check asks the other way round, by index:
//!   ready = 0  the states were never added in this process (a new process
//!              starts with the GUI machine read from menu.aix): add them
//!              without a lookup, and remember the index each got.
//!   ready = 1  they were added; read the name at the index remembered for
//!              ShowQmManager (StateMachineGetStateNameByInd) and compare. A
//!              map load reloads the whole GUI machine and drops both states
//!              together (probe 10: both missing at the battle DoCreate), so
//!              the index is then past the end of the list (the states were
//!              added at 142 and 143 after menu.aix's 142) or holds another
//!              state: the name differs, and both states are added again.
//!              The engine answers silently for an index past the end: no
//!              ERROR line and no crash (run g17b1, 2026-10-05, a return from
//!              a skirmish). tools/m6cases.py fails on any ERROR line before
//!              a `screens gone` line, so an engine that changed would show.
//! Nothing here is done in a battle, so the one check that can miss happens
//! at the first main-menu DoCreate after the battle.
//!
//! The code files are read from Quartermaster's own folder when the boot
//! recorded it (qm_rt `qmdir`, the same source qmIndexBegin reads vanilla.idx
//! from), else through the overlay, the way the hook loads core.aix.
//!
//! Code lines keep their `//` comments and string bodies through the parser:
//! reading progresswarai.inc that way gave the values' exact byte count
//! (capability probes, probe 6).
//!
//! qm_ui keys written: ready, show, event, showidx, adds, checks (docs/ui.md).
//! Whether the state at `qmUtInd` is `qmUtState`: by the index remembered, no
//! lookup by name; with no index remembered (-1), by name as until 0.1.3,
//! which costs one ERROR line when the state is gone.
function qmUeAt(const qmUtSm : Integer; const qmUtInd : Integer; const qmUtState : String) : Boolean;
begin
   Result := False;
   var qmUtI : Integer = qmUtInd;
   if (qmUtI<0) then
   qmUtI := StateMachineGetStateIndByName(qmUtSm, qmUtState);
   if (qmUtI>=0) then
   Result := SameText(StateMachineGetStateNameByInd(qmUtSm, qmUtI), qmUtState);
end;
//! Adds the state from its code file: the index it got (-1 when the lookup
//! after the add missed it - the state is in all the same), or -2 when there
//! is no code to add.
function qmUeAdd(const qmUaSm : Integer; const qmUaState : String; const qmUaPath : String) : Integer;
begin
   Result := -2;
   var qmUaSrc : Integer = ParserSelectByKey('qm_ui_src');
   if (qmUaSrc=0) then
   qmUaSrc := ParserCreate('qm_ui_src');
   ParserClearByHandle(qmUaSrc);
   ParserLoadFromFileByHandle(qmUaSrc, qmUaPath);
   var qmUaCode : Integer = ParserSelectByHandleByKey(qmUaSrc, 'Code');
   var qmUaN : Integer = 0;
   if (qmUaCode<>0) then
   qmUaN := ParserGetCountByHandle(qmUaCode);
   if (qmUaN=0) then
   begin
      qmLog('ui ensure: no code lines in '+qmUaPath+'; '+qmUaState+' not added');
      exit;
   end;
   StateMachineStateAdd(qmUaSm, qmUaState);
   var qmUaI : Integer;
   var qmUaLn : String;
   for qmUaI:=0 to qmUaN-1 do
   begin
      qmUaLn := ParserGetValueByIndexByHandle(qmUaCode, qmUaI);
      if (SubStr(qmUaLn, 1, 1)=';') then
      qmUaLn := SubStr(qmUaLn, 2, StrLength(qmUaLn)-1);
      StateMachineStateAddCodeLine(qmUaSm, qmUaState, qmUaLn);
   end;
   ParserClearByHandle(qmUaSrc);
   Result := StateMachineGetStateIndByName(qmUaSm, qmUaState);
   qmLog('ui ensure: added '+qmUaState+' lines='+IntToStr(qmUaN)+' index='+IntToStr(Result));
end;
// CameraControl runs this on every DoCreate, a battle's too: outside the main
// menu it does nothing at all - no lookup, no parser, no log line.
if (gInterface.gamemode<>gc_gamemode_mainmenu) then
exit;
var qmUeUi : Integer = ParserSelectByKey('qm_ui');
if (qmUeUi=0) then
qmUeUi := ParserCreate('qm_ui');
var qmUeSm : Integer = StateMachineGetGUISMHandle;
if (ParserGetIntValueByKeyByHandle(qmUeUi, 'ready')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmUeUi, 'checks', ParserGetIntValueByKeyByHandle(qmUeUi, 'checks')+1);
   if qmUeAt(qmUeSm, ParserGetIntValueByKeyByHandle(qmUeUi, 'showidx'), 'ShowQmManager') then
   begin
      qmLog('ui ensure: screens present checks='+IntToStr(ParserGetIntValueByKeyByHandle(qmUeUi, 'checks'))+' adds='+IntToStr(ParserGetIntValueByKeyByHandle(qmUeUi, 'adds')));
      exit;
   end;
   qmLog('ui ensure: screens gone (a map load reloaded the GUI machine); adding them again');
   ParserSetIntValueByKeyByHandle(qmUeUi, 'ready', 0);
   ParserSetIntValueByKeyByHandle(qmUeUi, 'show', 0);
   ParserSetIntValueByKeyByHandle(qmUeUi, 'event', 0);
end;
// `show` / `event` remember each state on its own, so a state that was
// added while its partner failed to load is never added a second time.
var qmUeRt : Integer = ParserSelectByKey('qm_rt');
var qmUeDir : String = '';
if (qmUeRt<>0) then
qmUeDir := ParserGetValueByKeyByHandle(qmUeRt, 'qmdir');
var qmUeBase : String = '.\data\quartermaster\ui\';
if (qmUeDir<>'') then
qmUeBase := qmUeDir+'\data\quartermaster\ui\';
var qmUeIdx : Integer;
if (ParserGetIntValueByKeyByHandle(qmUeUi, 'show')=0) then
begin
   qmUeIdx := qmUeAdd(qmUeSm, 'ShowQmManager', qmUeBase+'showqmmanager.inc');
   if (qmUeIdx>-2) then
   begin
      ParserSetIntValueByKeyByHandle(qmUeUi, 'show', 1);
      ParserSetIntValueByKeyByHandle(qmUeUi, 'showidx', qmUeIdx);
   end;
end;
if (ParserGetIntValueByKeyByHandle(qmUeUi, 'event')=0) then
if (qmUeAdd(qmUeSm, 'EventQmManager', qmUeBase+'eventqmmanager.inc')>-2) then
ParserSetIntValueByKeyByHandle(qmUeUi, 'event', 1);
if (ParserGetIntValueByKeyByHandle(qmUeUi, 'show')=1) and (ParserGetIntValueByKeyByHandle(qmUeUi, 'event')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmUeUi, 'ready', 1);
   ParserSetIntValueByKeyByHandle(qmUeUi, 'adds', ParserGetIntValueByKeyByHandle(qmUeUi, 'adds')+1);
end;
qmLog('ui ensure: ready='+IntToStr(ParserGetIntValueByKeyByHandle(qmUeUi, 'ready'))+' adds='+IntToStr(ParserGetIntValueByKeyByHandle(qmUeUi, 'adds'))+' from '+qmUeBase);
