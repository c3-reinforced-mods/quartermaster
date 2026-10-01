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
//! No silent existence check exists: the engine offers no state count, and
//! the only name lookups (StateMachineGetStateIndByName, ...HndByName) go
//! through TXStateMachine.IndexOfState, which logs one ERROR line per lookup
//! of a missing name (capability probes, probe 10). A lookup of a present
//! name is silent, so the check is arranged to look up only names that are
//! expected to be there:
//!   ready = 0  the states were never added in this process (a new process
//!              starts with the GUI machine read from menu.aix): add them
//!              without a lookup.
//!   ready = 1  they were added; confirm with one lookup of ShowQmManager.
//!              The lookup misses only after a map load, which reloads the
//!              whole GUI machine and drops both states together (probe 10:
//!              both missing at the battle DoCreate), so a miss costs exactly
//!              one ERROR line and both states are added again.
//! Nothing here is done in a battle, so the one lookup that can miss happens
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
//! qm_ui keys written: ready, show, event, adds, checks (docs/ui.md).
function qmUeHas(const qmUhSm : Integer; const qmUhState : String) : Boolean;
begin
   var qmUhInd : Integer = StateMachineGetStateIndByName(qmUhSm, qmUhState);
   Result := False;
   if (qmUhInd>=0) then
   Result := SameText(StateMachineGetStateNameByInd(qmUhSm, qmUhInd), qmUhState);
end;
function qmUeAdd(const qmUaSm : Integer; const qmUaState : String; const qmUaPath : String) : Boolean;
begin
   Result := False;
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
   qmLog('ui ensure: added '+qmUaState+' lines='+IntToStr(qmUaN)+' index='+IntToStr(StateMachineGetStateIndByName(qmUaSm, qmUaState)));
   Result := True;
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
   if qmUeHas(qmUeSm, 'ShowQmManager') then
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
if (ParserGetIntValueByKeyByHandle(qmUeUi, 'show')=0) then
if qmUeAdd(qmUeSm, 'ShowQmManager', qmUeBase+'showqmmanager.inc') then
ParserSetIntValueByKeyByHandle(qmUeUi, 'show', 1);
if (ParserGetIntValueByKeyByHandle(qmUeUi, 'event')=0) then
if qmUeAdd(qmUeSm, 'EventQmManager', qmUeBase+'eventqmmanager.inc') then
ParserSetIntValueByKeyByHandle(qmUeUi, 'event', 1);
if (ParserGetIntValueByKeyByHandle(qmUeUi, 'show')=1) and (ParserGetIntValueByKeyByHandle(qmUeUi, 'event')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmUeUi, 'ready', 1);
   ParserSetIntValueByKeyByHandle(qmUeUi, 'adds', ParserGetIntValueByKeyByHandle(qmUeUi, 'adds')+1);
end;
qmLog('ui ensure: ready='+IntToStr(ParserGetIntValueByKeyByHandle(qmUeUi, 'ready'))+' adds='+IntToStr(ParserGetIntValueByKeyByHandle(qmUeUi, 'adds'))+' from '+qmUeBase);
