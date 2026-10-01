state: qmCaseMod
into: data/quartermaster/selftest.aix
helpers: qmlog, qmstr, qmraw
requires: rawcap
---
//! SelfTest case `mod` (Phase B, M11): Create mod, Create about.cfg and
//! Edit game file driven through the window by GUI tags and events (the
//! mechanism of qmcaseui.pas), then the next start's registration. Each
//! request is carried out by running qmModFiles at once - what qmTick does on
//! the next frame - so one life does all three. Directives:
//!   name <text>    the new mod's name (a folder name already)
//!   local <dir>    a local mod for Create about.cfg and Edit game file
//!                  (none: life 1 only creates the new mod)
//!   find <text>    the search for the game file to copy (its first match)
//!   own 1          the restart counts as Quartermaster's own, as an Apply's
//!                  does (the marker's rk = test), so the next boot's loop
//!                  rule sees a folder made before it (a bug found
//!                  2026-10-01)
//! Dump lines (tools/m11cases.py), one file per life:
//!   life|<boot>|<registered: 1 when the new folder is a registered mod>
//!   new|<mfres>|<mod.ini>|<about.cfg>|<readme> (1 = the file exists)|<folder>
//!   about|<mfres>|<the local mod's about.cfg exists>
//!   copy|<mfres>|<path>|<lines equal to vanilla's: 1>
//!   registered|<row>|<enabled>|<about.cfg id read by the boot>
//! Life 1 ends by scheduling a restart (qm_rt rs), as a player's Apply does.
const qmCmTagNewMod = 120;
const qmCmTagModFiles = 121;
const qmCmTagNmCreate = 124;
const qmCmTagMfAbout = 126;
const qmCmTagMfCopy = 127;
const qmCmTagMfBack = 128;
var qmCmRt : Integer = ParserSelectByKey('qm_case_rt');
var qmCmOut : String = ParserGetValueByKeyByHandle(qmCmRt, 'out');
var qmCmCode : Integer = ParserSelectByHandleByKey(ParserSelectByKey('qm_case'), 'Code');
var qmCmNd : Integer = ParserGetCountByHandle(qmCmCode);
var qmCmCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
var qmCmSt : Integer = ParserSelectByKey('qm_state');
var qmCmQrt : Integer = ParserSelectByKey('qm_rt');
var qmCmBoot : String = IntToStr(ParserGetIntValueByKeyByHandle(qmCmSt, 'boots'));
var qmCmDump : String = '';
var qmCmName : String = '';
var qmCmLocal : String = '';
var qmCmFind : String = '';
var qmCmOwnRs : String = '';
var qmCmD : Integer;
var qmCmI : Integer;
var qmCmS : String;
var qmCmVerb : String;
var qmCmArg : String;
var qmCmRow : Integer = -1;
var qmCmOn : Integer = 0;
var qmCmH : Integer;
var qmCmUi : Integer;
var qmCmTag, qmCmDir, qmCmLast, qmCmTit, qmCmOwn, qmCmDesc, qmCmTags, qmCmUrl, qmCmNote : String;
var qmCmNumf, qmCmVis : Integer;
var qmCmDis, qmCmAcc, qmCmBan, qmCmRoot : Boolean;
var qmCmA : array [0..${rawcap}] of String;
var qmCmNa : Integer;
var qmCmNb : Integer;
var qmCmSame : Integer;
var qmCmK : Integer;
var qmCmVan : array [0..511] of String;

procedure qmCmPut(const qmCpLine : String);
begin
   qmCmDump := qmCmDump+qmCpLine+'~013~010';
   qmRawWriteStr(qmCmOut, qmCmDump);
   qmLog('mod case '+qmCpLine);
end;
function qmCmExists(const qmCeP : String) : Integer;
begin
   Result := 0;
   if (FileAge(qmCeP)<>-1) then
   Result := 1;
end;
//! A keystroke in a text box: the text, then the key's release sent to the
//! window's event state (qmcaseui.pas qmCuType).
procedure qmCmType(const qmCtBox : String; const qmCtText : String);
begin
   var qmCtH : Integer = GetGUIElementIndexByNameParent(qmCtBox, _gui_GetTop);
   if (qmCtH<>0) then
   SetGUIElementText(qmCtH, qmCtText);
   SetGUIValue('Status', 'key');
   SetGUIValue('Press', 'u');
   SetGUIIntValue('Tag', 65);
   SetGUIIntValue('ElementHandle', qmCtH);
   GUIExecuteState('EventQmManager');
end;
//! A list's row selected the way a click selects it (qmcaseui.pas).
procedure qmCmPick(const qmCkList : String; const qmCkTag : Integer);
begin
   var qmCkL : Integer = GetGUIElementIndexByNameParent(qmCkList, _gui_GetTop);
   var qmCkItem : Integer = -1;
   if (qmCkL<>0) then
   qmCkItem := GetGUIListBoxItemIndexOfTag(qmCkL, qmCkTag);
   if (qmCkItem>=0) then
   begin
      SetGUIListBoxItemIndexSilent(qmCkL, qmCkItem);
      SetGUIValue('Status', 'select');
      SetGUIValue('Press', 'c');
      SetGUIIntValue('Tag', 0);
      SetGUIIntValue('ElementHandle', qmCkL);
      GUIExecuteState('EventQmManager');
   end;
   qmLog('mod case pick '+qmCkList+' tag='+IntToStr(qmCkTag)+' item='+IntToStr(qmCkItem));
end;

for qmCmD:=1 to qmCmNd-1 do
begin
   qmCmS := ParserGetValueByIndexByHandle(qmCmCode, qmCmD);
   if (SubStr(qmCmS, 1, 1)=';') then
   qmCmS := SubStr(qmCmS, 2, StrLength(qmCmS)-1);
   qmField(qmCmS, ' ', 0, qmCmVerb);
   qmField(qmCmS, ' ', 1, qmCmArg);
   if (qmCmVerb='name') then
   qmCmName := qmCmArg;
   if (qmCmVerb='local') then
   qmCmLocal := qmCmArg;
   if (qmCmVerb='find') then
   qmCmFind := qmCmArg;
   if (qmCmVerb='own') then
   qmCmOwnRs := qmCmArg;
end;
qmCmOut := SubStr(qmCmOut, 1, StrLength(qmCmOut)-4)+'_'+qmCmBoot+'.txt';
for qmCmI:=0 to ModLibraryGetCount-1 do
begin
   ModLibraryGetData(qmCmI, qmCmTag, qmCmDir, qmCmLast, qmCmTit, qmCmOwn, qmCmDesc, qmCmTags, qmCmUrl, qmCmNote, qmCmNumf, qmCmVis, qmCmDis, qmCmAcc, qmCmBan, qmCmRoot);
   if SameText(qmCmDir, 'mods\'+qmCmName) then
   begin
      qmCmRow := qmCmI;
      if (not qmCmDis) then
      qmCmOn := 1;
   end;
end;
if (qmCmRow>=0) then
begin
   qmCmPut('life|'+qmCmBoot+'|1');
   qmCmPut('registered|'+IntToStr(qmCmRow)+'|'+IntToStr(qmCmOn)+'|'+ParserGetValueByKeyByHandle(ParserSelectByKey('qm_about'), 'id'+IntToStr(qmCmRow)));
   ParserSetValueByKeyByHandle(qmCmRt, 'status', 'ok');
   exit;
end;
qmCmPut('life|'+qmCmBoot+'|0');
StateMachineExecuteState(qmCmCore, 'qmUiEnsure', 0);
_gui_SendTagToState('EventMainMenu', 108);
qmCmUi := ParserSelectByKey('qm_ui');
//! Create mod: the dialog, the name typed into its box, Create.
_gui_SendTagToState('EventQmManager', qmCmTagNewMod);
qmCmType('QmManager.nbox.nname.text', qmCmName);
_gui_SendTagToState('EventQmManager', qmCmTagNmCreate);
StateMachineExecuteState(qmCmCore, 'qmModFiles', 0);
qmCmS := 'mods\'+ParserGetValueByKeyByHandle(qmCmUi, 'nmfolder');
qmCmPut('new|'+IntToStr(ParserGetIntValueByKeyByHandle(qmCmQrt, 'mfres'))+'|'+IntToStr(qmCmExists(qmCmS+'\mod.ini'))+'|'+IntToStr(qmCmExists(qmCmS+'\about.cfg'))+'|'+IntToStr(qmCmExists(qmCmS+'\data\readme.txt'))+'|'+ParserGetValueByKeyByHandle(qmCmUi, 'nmfolder'));
//! Mod files of the local mod: Create about.cfg, then the game file.
if (qmCmLocal<>'') then
begin
   for qmCmI:=0 to ParserGetIntValueByKeyByHandle(qmCmUi, 'n')-1 do
   if SameText(ParserGetValueByKeyByHandle(qmCmUi, 'dir'+IntToStr(qmCmI)), qmCmLocal) then
   qmCmPick('QmManager.main.wnd.inst.installed', qmCmI);
   _gui_SendTagToState('EventQmManager', qmCmTagModFiles);
   _gui_SendTagToState('EventQmManager', qmCmTagMfAbout);
   StateMachineExecuteState(qmCmCore, 'qmModFiles', 0);
   qmCmPut('about|'+IntToStr(ParserGetIntValueByKeyByHandle(qmCmQrt, 'mfres'))+'|'+IntToStr(qmCmExists(qmCmLocal+'\about.cfg')));
   qmCmType('QmManager.fbox.filter.text', qmCmFind);
   qmCmPick('QmManager.main.wnd.vbox.vfiles', 0);
   _gui_SendTagToState('EventQmManager', qmCmTagMfCopy);
   StateMachineExecuteState(qmCmCore, 'qmModFiles', 0);
   qmCmS := ParserGetValueByKeyByHandle(qmCmUi, 'v0');
   qmCmSame := 0;
   qmRawRead(ExtractFilePath(GetApplicationFileName)+'data\'+qmCmS, -1, qmCmA, qmCmNa);
   qmCmNb := qmCmNa;
   if (qmCmNa>0) then
   begin
      qmCmSame := 1;
      //! The copy's lines against vanilla's, one at a time: the pool holds one file.
      for qmCmK:=0 to qmCmNa-1 do
      if (qmCmK<512) then
      qmCmVan[qmCmK] := qmCmA[qmCmK];
      qmRawRead(qmCmLocal+'\data\'+qmCmS, -1, qmCmA, qmCmNb);
      if (qmCmNb<>qmCmNa) then
      qmCmSame := 0
      else
      for qmCmK:=0 to qmCmNa-1 do
      if (qmCmK<512) then
      if (qmCmVan[qmCmK]<>qmCmA[qmCmK]) then
      qmCmSame := 0;
   end;
   qmCmPut('copy|'+IntToStr(ParserGetIntValueByKeyByHandle(qmCmQrt, 'mfres'))+'|'+qmCmS+'|'+IntToStr(qmCmSame)+'|'+IntToStr(qmCmNa)+'|'+IntToStr(qmCmNb));
   _gui_SendTagToState('EventQmManager', qmCmTagMfBack);
end;
qmCmH := GetGUIElementIndexByNameParent('QmManager', _gui_GetTop);
if (qmCmH<>0) then
RemoveGUIElement(qmCmH);
if (qmCmOwnRs='1') then
begin
   ParserSetValueByKeyByHandle(qmCmSt, 'rk', 'test');
   StateMachineExecuteState(qmCmCore, 'qmMarkerSave', 0);
end;
//! The restart that makes the game register the new folder, the way a
//! confirmed Apply's is scheduled (qmTick runs it on a later frame).
ParserSetIntValueByKeyByHandle(qmCmQrt, 'rs', 1);
ParserSetIntValueByKeyByHandle(qmCmQrt, 'rsdue', Floor(_misc_GetRealTime*10)+11);
ParserSetValueByKeyByHandle(qmCmQrt, 'rskind', 'test');
ParserSetValueByKeyByHandle(qmCmQrt, 'rswhy', 'mod case');
ParserSetIntValueByKeyByHandle(qmCmQrt, 'tick', 1);
qmCmPut('restart|scheduled');
ParserSetValueByKeyByHandle(qmCmRt, 'status', 'ok');
