state: qmCaseOpt
into: data/quartermaster/selftest.aix
helpers: qmlog, qmstr, qmraw
requires:
---
//! SelfTest case `opt` (Phase B: M8 rules in the window, M10 the Options
//! view), driven the way the game drives the window - by GUI tags and
//! events, with no click (the mechanism of qmcaseui.pas: _gui_SendTagToState
//! and SetGUIValue / SetGUIIntValue + GUIExecuteState, so the GUI states
//! read them as a real click or key). Directives:
//!   mod <dir>     the mod with settings (QMTestWASD2)
//!   clash <dir>   a second mod in the same exclusive slot (QMTestCam2)
//!   key <code>    a key's down event for the first setting, in order; each
//!                 after a click on its Change button (tag 200); 27 = Escape
//!   accept 1      Accept at the end (tag 115)
//! and, in the order given (the in-game checks of what the
//! offline tests cover):
//!   btn <n>       in the Options view, the button with tag 200+n (setting
//!                 n div 2; 0 main, 1 the other): Switch, +, -, >, <, Edit
//!   type <text>   the text typed into the Options view's text box
//!   autosort 1    Auto-sort (tag 119) in the lists
//!   trial <dir>   that row activated (tag 101), then what qmTick does on the
//!                 next frame: qmTrial and qmUiAct `trialdone`
//!   applytrial 1  Apply (tag 103), qmTick's frame if a check was asked,
//!                 the dialog's state, then No (tag 108)
//! btn and type run in the Options view before Accept; autosort, trial and
//! applytrial in the lists, after it.
//! Dump lines (tools/m10cases.py checks them):
//!   ensure|<ready>|<adds>
//!   rows|<mod row>|<clash row>|<abok>|<abs of the mod>
//!   status|mod|<st>|<stsrc>|<why>       and the same for clash
//!   rule|deactivate|<pe of clash>
//!   rule|activate|<pe of clash>|<msg>
//!   opt|<panel>|<optn>|<ov0>|<ov1>|<ov2>|<ov3>
//!   cap|<code>|<optcap after Change>|<optcap after the key>|<ov0>|<msg>
//!   acc|<panel>|<msg>|<reregs>|<setsave>|<camera_left in qm_settings>
//!   btn|<n>|<ov of that setting>|<optsel>|<msg>
//!   type|<optsel>|<ov of that setting>
//!   store|<mod id>|<id>=<value>|... (its qm_settings child, after Accept)
//!   sort|<ordchg>|<the pending order's dirs, ;>
//!   trial|<dir>|<row>|<pe at once>|<trpend>|<pe after>|<trst>|<trn>|<tr0>|<msg>
//!   apply|<mode>|<confblk>|<confb0>|<trq>|<trrow>|<msg>
//!   end|<windows>
//! At the end the window is removed; qm_rt setsave stays, so qmTick writes
//! settings.cfg on the next main-menu frame (the evidence of the save).
const qmCoTagDeact = 102;
const qmCoTagAct = 101;
const qmCoTagOptions = 118;
const qmCoTagAccept = 115;
const qmCoTagRow = 200;
const qmCoTagApply = 103;
const qmCoTagNo = 108;
const qmCoTagAutoSort = 119;
var qmCoRt : Integer = ParserSelectByKey('qm_case_rt');
var qmCoOut : String = ParserGetValueByKeyByHandle(qmCoRt, 'out');
var qmCoCode : Integer = ParserSelectByHandleByKey(ParserSelectByKey('qm_case'), 'Code');
var qmCoNd : Integer = ParserGetCountByHandle(qmCoCode);
var qmCoCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
var qmCoDump : String = '';
var qmCoMod : String = '';
var qmCoClash : String = '';
var qmCoKeys : array [0..15] of Integer;
var qmCoKn : Integer = 0;
var qmCoAccept : Integer = 0;
var qmCoD : Integer;
var qmCoI : Integer;
var qmCoS : String;
var qmCoVerb : String;
var qmCoArg : String;
var qmCoUi : Integer;
var qmCoRowM : Integer = -1;
var qmCoRowC : Integer = -1;
var qmCoCap : Integer;
var qmCoActV : array [0..31] of String;
var qmCoActA : array [0..31] of String;
var qmCoAn : Integer = 0;
var qmCoA : Integer;
var qmCoR : Integer;
var qmCoPe : Integer;
var qmCoTp : Integer;

procedure qmCoPut(const qmOpLine : String);
begin
   qmCoDump := qmCoDump+qmOpLine+'~013~010';
   qmRawWriteStr(qmCoOut, qmCoDump);
   qmLog('opt case '+qmOpLine);
end;
function qmCoInt(const qmOiKey : String) : Integer;
begin
   Result := ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_ui'), qmOiKey);
end;
procedure qmCoStr(const qmOsKey : String; var qmOsOut : String);
begin
   qmOsOut := ParserGetValueByKeyByHandle(ParserSelectByKey('qm_ui'), qmOsKey);
end;
//! The row selected in the Active list the way a click selects it.
procedure qmCoSelect(const qmOlRow : Integer);
begin
   var qmOlList : Integer = GetGUIElementIndexByNameParent('QmManager.main.wnd.act.active', _gui_GetTop);
   var qmOlItem : Integer = -1;
   if (qmOlList<>0) then
   qmOlItem := GetGUIListBoxItemIndexOfTag(qmOlList, qmOlRow);
   if (qmOlItem>=0) then
   begin
      SetGUIListBoxItemIndexSilent(qmOlList, qmOlItem);
      SetGUIValue('Status', 'select');
      SetGUIValue('Press', 'c');
      SetGUIIntValue('Tag', 0);
      SetGUIIntValue('ElementHandle', qmOlList);
      GUIExecuteState('EventQmManager');
   end;
   if (qmCoInt('sel')<>qmOlRow) then
   begin
      qmCoPut('selectvia|cmd|row='+IntToStr(qmOlRow)+'|item='+IntToStr(qmOlItem));
      ParserSetValueByKeyByHandle(ParserSelectByKey('qm_ui'), 'cmd', 'select');
      ParserSetIntValueByKeyByHandle(ParserSelectByKey('qm_ui'), 'arg', qmOlRow);
      ParserSetIntValueByKeyByHandle(ParserSelectByKey('qm_ui'), 'argside', 1);
      ParserSetValueByKeyByHandle(ParserSelectByKey('qm_ui'), 'argtext', '');
      StateMachineExecuteState(qmCoCore, 'qmUiAct', 0);
      GUIExecuteState('ShowQmManager');
   end;
end;
//! A row selected in the Installed list the way a click selects it.
procedure qmCoSelectIn(const qmOnRow : Integer);
begin
   var qmOnList : Integer = GetGUIElementIndexByNameParent('QmManager.main.wnd.inst.installed', _gui_GetTop);
   var qmOnItem : Integer = -1;
   if (qmOnList<>0) then
   qmOnItem := GetGUIListBoxItemIndexOfTag(qmOnList, qmOnRow);
   if (qmOnItem>=0) then
   begin
      SetGUIListBoxItemIndexSilent(qmOnList, qmOnItem);
      SetGUIValue('Status', 'select');
      SetGUIValue('Press', 'c');
      SetGUIIntValue('Tag', 0);
      SetGUIIntValue('ElementHandle', qmOnList);
      GUIExecuteState('EventQmManager');
   end;
   qmCoPut('selectin|'+IntToStr(qmOnRow)+'|'+IntToStr(qmOnItem)+'|'+IntToStr(qmCoInt('sel')));
end;
//! What qmTick does on the next main-menu frame when the window asked for
//! the activation check (qmrestarttick.pas): qmTrial, then `trialdone`.
procedure qmCoTick;
begin
   var qmOtRt : Integer = ParserSelectByKey('qm_rt');
   if (ParserGetIntValueByKeyByHandle(qmOtRt, 'trq')>ParserGetIntValueByKeyByHandle(qmOtRt, 'trdone')) then
   begin
      ParserSetIntValueByKeyByHandle(qmOtRt, 'trdone', ParserGetIntValueByKeyByHandle(qmOtRt, 'trq'));
      StateMachineExecuteState(qmCoCore, 'qmTrial', 0);
      ParserSetValueByKeyByHandle(ParserSelectByKey('qm_ui'), 'cmd', 'trialdone');
      StateMachineExecuteState(qmCoCore, 'qmUiAct', 0);
      GUIExecuteState('ShowQmManager');
   end;
end;
//! A keystroke in the Options view's text box: the text, then the key's
//! release sent to the window's event state (qmcaseui.pas qmCuType).
procedure qmCoType(const qmOyText : String);
begin
   var qmOyH : Integer = GetGUIElementIndexByNameParent('QmManager.obox.otext.text', _gui_GetTop);
   if (qmOyH<>0) then
   SetGUIElementText(qmOyH, qmOyText);
   SetGUIValue('Status', 'key');
   SetGUIValue('Press', 'u');
   SetGUIIntValue('Tag', 65);
   SetGUIIntValue('ElementHandle', qmOyH);
   GUIExecuteState('EventQmManager');
   qmCoPut('typebox|'+IntToStr(qmOyH));
end;
//! A key's down event, as the engine delivers one to the window's key state.
procedure qmCoKeyDown(const qmOkCode : Integer);
begin
   SetGUIValue('Status', 'key');
   SetGUIValue('Press', 'd');
   SetGUIIntValue('Tag', qmOkCode);
   SetGUIIntValue('ElementHandle', 0);
   GUIExecuteState('EventQmManager');
end;

for qmCoD:=1 to qmCoNd-1 do
begin
   qmCoS := ParserGetValueByIndexByHandle(qmCoCode, qmCoD);
   if (SubStr(qmCoS, 1, 1)=';') then
   qmCoS := SubStr(qmCoS, 2, StrLength(qmCoS)-1);
   qmField(qmCoS, ' ', 0, qmCoVerb);
   qmField(qmCoS, ' ', 1, qmCoArg);
   if (qmCoVerb='mod') then
   qmCoMod := qmCoArg;
   if (qmCoVerb='clash') then
   qmCoClash := qmCoArg;
   if (qmCoVerb='key') and (qmCoKn<16) then
   begin
      qmCoKeys[qmCoKn] := StrToInt(qmCoArg);
      qmCoKn := qmCoKn+1;
   end;
   if (qmCoVerb='accept') then
   qmCoAccept := StrToInt(qmCoArg);
   if ((qmCoVerb='btn') or (qmCoVerb='type') or (qmCoVerb='autosort') or (qmCoVerb='trial') or (qmCoVerb='applytrial')) and (qmCoAn<32) then
   begin
      qmCoActV[qmCoAn] := qmCoVerb;
      qmCoActA[qmCoAn] := SubStr(qmCoS, StrLength(qmCoVerb)+2, StrLength(qmCoS)-StrLength(qmCoVerb)-1);
      qmCoAn := qmCoAn+1;
   end;
end;

StateMachineExecuteState(qmCoCore, 'qmUiEnsure', 0);
qmCoPut('ensure|'+IntToStr(qmCoInt('ready'))+'|'+IntToStr(qmCoInt('adds')));
_gui_SendTagToState('EventMainMenu', 108);
qmCoUi := ParserSelectByKey('qm_ui');
for qmCoI:=0 to qmCoInt('n')-1 do
begin
   if SameText(ParserGetValueByKeyByHandle(qmCoUi, 'dir'+IntToStr(qmCoI)), qmCoMod) then
   qmCoRowM := qmCoI;
   if SameText(ParserGetValueByKeyByHandle(qmCoUi, 'dir'+IntToStr(qmCoI)), qmCoClash) then
   qmCoRowC := qmCoI;
end;
qmCoPut('rows|'+IntToStr(qmCoRowM)+'|'+IntToStr(qmCoRowC)+'|'+IntToStr(qmCoInt('abok'))+'|'+IntToStr(qmCoInt('abs'+IntToStr(qmCoRowM))));
qmCoPut('status|mod|'+ParserGetValueByKeyByHandle(qmCoUi, 'st'+IntToStr(qmCoRowM))+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'stsrc'+IntToStr(qmCoRowM))+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'why'+IntToStr(qmCoRowM)));
qmCoPut('status|clash|'+ParserGetValueByKeyByHandle(qmCoUi, 'st'+IntToStr(qmCoRowC))+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'stsrc'+IntToStr(qmCoRowC))+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'why'+IntToStr(qmCoRowC)));
if (qmCoRowM>=0) and (qmCoRowC>=0) then
begin
   //! The rules: the clash mod off, then on again - refused while the mod
   //! takes the slot.
   qmCoSelect(qmCoRowC);
   _gui_SendTagToState('EventQmManager', qmCoTagDeact);
   qmCoPut('rule|deactivate|'+IntToStr(qmCoInt('pe'+IntToStr(qmCoRowC))));
   _gui_SendTagToState('EventQmManager', qmCoTagAct);
   qmCoStr('msg', qmCoS);
   qmCoPut('rule|activate|'+IntToStr(qmCoInt('pe'+IntToStr(qmCoRowC)))+'|'+qmCoS);
end;
if (qmCoRowM>=0) and ((qmCoRowC>=0) or (qmCoKn>0) or (qmCoAccept=1)) then
begin
   //! The Options view of the mod, the keys, Accept.
   qmCoSelect(qmCoRowM);
   _gui_SendTagToState('EventQmManager', qmCoTagOptions);
   qmCoPut('opt|'+IntToStr(qmCoInt('panel'))+'|'+IntToStr(qmCoInt('optn'))+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'ov0')+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'ov1')+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'ov2')+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'ov3'));
   for qmCoI:=0 to qmCoKn-1 do
   begin
      _gui_SendTagToState('EventQmManager', qmCoTagRow);
      qmCoCap := qmCoInt('optcap');
      qmCoKeyDown(qmCoKeys[qmCoI]);
      qmCoStr('msg', qmCoS);
      qmCoPut('cap|'+IntToStr(qmCoKeys[qmCoI])+'|'+IntToStr(qmCoCap)+'|'+IntToStr(qmCoInt('optcap'))+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'ov0')+'|'+qmCoS);
   end;
   for qmCoA:=0 to qmCoAn-1 do
   begin
      if (qmCoActV[qmCoA]='btn') then
      begin
         qmCoR := StrToInt(qmCoActA[qmCoA]);
         _gui_SendTagToState('EventQmManager', qmCoTagRow+qmCoR);
         qmCoStr('msg', qmCoS);
         qmCoPut('btn|'+IntToStr(qmCoR)+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'ov'+IntToStr(qmCoR div 2))+'|'+IntToStr(qmCoInt('optsel'))+'|'+qmCoS);
      end;
      if (qmCoActV[qmCoA]='type') then
      begin
         qmCoType(qmCoActA[qmCoA]);
         qmCoPut('type|'+IntToStr(qmCoInt('optsel'))+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'ov'+IntToStr(qmCoInt('optsel'))));
      end;
   end;
   if (qmCoAccept=1) then
   begin
      _gui_SendTagToState('EventQmManager', qmCoTagAccept);
      var qmCoSet : Integer = ParserSelectByKey('qm_settings');
      var qmCoCh : Integer = 0;
      var qmCoLeft : String = '-';
      if (qmCoSet<>0) then
      qmCoCh := ParserSelectByHandleByKey(qmCoSet, 'qmtestwasd2');
      if (qmCoCh<>0) then
      qmCoLeft := ParserGetValueByKeyByHandle(qmCoCh, 'camera_left');
      qmCoStr('msg', qmCoS);
      qmCoPut('acc|'+IntToStr(qmCoInt('panel'))+'|'+qmCoS+'|'+IntToStr(qmCoInt('reregs'))+'|'+IntToStr(ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_rt'), 'setsave'))+'|'+qmCoLeft);
      //! Every value of the mod's child in qm_settings, as a mod reads it.
      qmCoS := ParserGetValueByKeyByHandle(qmCoUi, 'abid'+IntToStr(qmCoRowM));
      qmCoCh := 0;
      if (qmCoSet<>0) then
      qmCoCh := ParserSelectByHandleByKey(qmCoSet, qmCoS);
      qmCoS := 'store|'+qmCoS;
      for qmCoI:=0 to qmCoInt('optn')-1 do
      begin
         qmCoLeft := '-';
         if (qmCoCh<>0) then
         qmCoLeft := ParserGetValueByKeyByHandle(qmCoCh, ParserGetValueByKeyByHandle(qmCoUi, 'oid'+IntToStr(qmCoI)));
         qmCoS := qmCoS+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'oid'+IntToStr(qmCoI))+'='+qmCoLeft;
      end;
      qmCoPut(qmCoS);
   end;
end;
//! The actions in the lists.
if (qmCoInt('panel')=2) then
_gui_SendTagToState('EventQmManager', qmCoTagOptions);
for qmCoA:=0 to qmCoAn-1 do
begin
   if (qmCoActV[qmCoA]='autosort') then
   begin
      _gui_SendTagToState('EventQmManager', qmCoTagAutoSort);
      qmCoS := 'sort|'+IntToStr(qmCoInt('ordchg'))+'|';
      for qmCoI:=0 to qmCoInt('n')-1 do
      qmCoS := qmCoS+ParserGetValueByKeyByHandle(qmCoUi, 'dir'+IntToStr(qmCoInt('ord'+IntToStr(qmCoI))))+';';
      qmCoPut(qmCoS);
   end;
   if (qmCoActV[qmCoA]='trial') then
   begin
      qmCoR := -1;
      for qmCoI:=0 to qmCoInt('n')-1 do
      if SameText(ParserGetValueByKeyByHandle(qmCoUi, 'dir'+IntToStr(qmCoI)), qmCoActA[qmCoA]) then
      qmCoR := qmCoI;
      qmCoSelectIn(qmCoR);
      _gui_SendTagToState('EventQmManager', qmCoTagAct);
      qmCoPe := qmCoInt('pe'+IntToStr(qmCoR));
      qmCoTp := qmCoInt('trpend');
      qmCoTick;
      qmCoStr('msg', qmCoS);
      qmCoPut('trial|'+qmCoActA[qmCoA]+'|'+IntToStr(qmCoR)+'|'+IntToStr(qmCoPe)+'|'+IntToStr(qmCoTp)+'|'+IntToStr(qmCoInt('pe'+IntToStr(qmCoR)))+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'trst')+'|'+IntToStr(qmCoInt('trn'))+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'tr0')+'|'+qmCoS);
   end;
   if (qmCoActV[qmCoA]='applytrial') then
   begin
      _gui_SendTagToState('EventQmManager', qmCoTagApply);
      qmCoTick;
      qmCoStr('msg', qmCoS);
      qmCoPut('apply|'+IntToStr(qmCoInt('mode'))+'|'+IntToStr(qmCoInt('confblk'))+'|'+ParserGetValueByKeyByHandle(qmCoUi, 'confb0')+'|'+IntToStr(ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_rt'), 'trq'))+'|'+IntToStr(ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_rt'), 'trrow'))+'|'+qmCoS);
      if (qmCoInt('mode')=1) then
      _gui_SendTagToState('EventQmManager', qmCoTagNo);
   end;
end;
var qmCoH : Integer = GetGUIElementIndexByNameParent('QmManager', _gui_GetTop);
if (qmCoH<>0) then
RemoveGUIElement(qmCoH);
qmCoPut('end|'+IntToStr(GetGUIElementIndexByNameParent('QmManager', _gui_GetTop)));
ParserSetValueByKeyByHandle(qmCoRt, 'status', 'ok');
