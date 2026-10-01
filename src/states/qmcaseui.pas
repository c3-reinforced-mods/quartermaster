state: qmCaseUi
into: data/quartermaster/selftest.aix
helpers: qmlog, qmstr, qmraw
requires:
---
//! SelfTest case `ui`: the manager window (docs/ui.md) driven the way the
//! game drives it, by GUI tags, with no click. Directives:
//!   cycles <n>     open with the main menu's "Mod manager" tag 108, which goes
//!                  through Quartermaster's EventMainMenu hook, then close -
//!                  with the close tag in odd cycles, with Esc in even ones
//!   toggle <dir>   then, on the mod <dir>: open, select it in the Active list,
//!                  move it one place and back (Move up then Move down, or the
//!                  other way round when it loads first), type its folder's
//!                  name into the filter box and clear it again (key releases,
//!                  the way a keystroke arrives), open the Report view and
//!                  leave it with Esc, Deactivate, Apply, Esc (cancels the
//!                  dialog), Apply, Enter (confirms: the restart notice), Esc
//!                  (closes the window)
//!   keep 1         I9 through the window (tools/m6cases.py, case --i9): the
//!                  confirmed Apply is left in qm_rt for qmTick, which
//!                  regenerates and restarts - so the flow runs once per run,
//!                  in the first life whose boot neither generated nor has a
//!                  restart pending (the files on disk are the ones the engine
//!                  loaded: the merge is in effect). An earlier life only
//!                  waits, a later one reports the mod's flag; each life
//!                  writes <case>_<boot>.txt, and <case>.done marks the flow
//! Dump (ref/selftest.py ui_expected and ui_keep_* are the twin):
//!   ensure|<ready>|<show>|<event>|<adds>
//!   cycle|<i>|<close or esc>|<opened>|<windows>|<closed>|<opens>|<closes>
//!   row|<dir hex>|<row>|<enabled>
//!   step|<name>|<sel>|<pending on>|<mode>|<visible>|<uiapply>|<uiapplyseq>|
//!        <uiapplychg>|<uiapplydis of the row>|<uiregen>|<canapply>|<ordchg>|
//!        <panel>|<Apply button enabled: 1, 0, -1 when there is none>
//!   order|<the first move: up or down>|<the row's place in Active>|<active rows>
//!   filtered|<rows the Installed list shows>|<rows whose name or dir hold the text>
//!   unfiltered|<rows the Installed list shows>|<rows>
//!   end|<windows>|<opens>|<closes>
//!   keep only: life|<boot>|go first, kept|<uiapply>|<uiapplyseq> last;
//!   life|<boot>|wait|regen=<0/1>|restart=<0/1> or
//!   life|<boot>|later|on=<the mod's on in qm_mods>|why=<the boot's why> alone
//! `windows` counts the top elements named QmManager: 1 while the window
//! exists, however often it was opened.
//!
//! The SelfTest runs inside the boot, in the first main-menu DoCreate, before
//! the hook's own qmUiEnsure line; so the case runs qmUiEnsure first. Tags go
//! through _gui_SendTagToState (data/scripts/lib/gui.script:21-27), which
//! sets the GUI machine's values by name (SetGUIValue / SetGUIIntValue) and
//! runs the state there with GUIExecuteState, so the GUI states read them as
//! they read a real click. The list selection is sent the same way, with the
//! element handle the GUI state reads (Status `select`, eventcampaign.inc:
//! 16-18); if it does not arrive, a `selectvia|cmd` line says so and the
//! controller gets the command directly, so the rest still runs.
//!
//! Every line is written as soon as it is known (the dump file is rewritten),
//! so a case that stops half way still says how far it got. At the end the
//! window is removed, so the GUI is as the case found it, and the Apply
//! request is withdrawn (qm_rt `uiapply` = 0): a controller that acts on it
//! must not act on a test's request - unless the case says `keep 1` - and
//! the restart notice goes with it (qm_ui mode 0).
// The button tags of ShowQmManager (tests/test_m6_selftest.py keeps them equal).
const qmCuTagDeact = 102;
const qmCuTagApply = 103;
const qmCuTagReport = 104;
const qmCuTagUp = 110;
const qmCuTagDown = 111;
var qmCuRt : Integer = ParserSelectByKey('qm_case_rt');
var qmCuOut : String = ParserGetValueByKeyByHandle(qmCuRt, 'out');
var qmCuCode : Integer = ParserSelectByHandleByKey(ParserSelectByKey('qm_case'), 'Code');
var qmCuNd : Integer = ParserGetCountByHandle(qmCuCode);
var qmCuCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
var qmCuRtp : Integer = ParserSelectByKey('qm_rt');
var qmCuUi : Integer = 0;
var qmCuDump : String = '';
var qmCuCycles : Integer = 0;
var qmCuToggle : String = '';
var qmCuRow : Integer = -1;
var qmCuD : Integer;
var qmCuI : Integer;
var qmCuS : String;
var qmCuVerb : String;
var qmCuArg : String;
var qmCuHow : String;
var qmCuOpened : Integer;
var qmCuWin : Integer;
var qmCuOpens : Integer;
var qmCuHex : String;
var qmCuList : Integer;
var qmCuItem : Integer;
var qmCuKeep : Integer = 0;
var qmCuSt : Integer = ParserSelectByKey('qm_state');
var qmCuG : Integer = ParserSelectByKey('qm_guard');
var qmCuMods : Integer = ParserSelectByKey('qm_mods');
var qmCuBoot : String = '';
var qmCuDone : String = '';
var qmCuOn : String = '-';
var qmCuPlace : Integer = -1;
var qmCuNa : Integer = 0;
var qmCuFirst : String;
var qmCuText : String;
var qmCuWant : Integer;
var qmCuK : Integer;

procedure qmCuPut(const qmCpLine : String);
begin
   qmCuDump := qmCuDump+qmCpLine+'~013~010';
   qmRawWriteStr(qmCuOut, qmCuDump);
   qmLog('ui case '+qmCpLine);
end;
function qmCuVisible() : Integer;
begin
   var qmCvH : Integer = GetGUIElementIndexByNameParent('QmManager', _gui_GetTop);
   Result := 0;
   if (qmCvH<>0) then
   if GetGUIElementVisible(qmCvH) then
   Result := 1;
end;
function qmCuWindows() : Integer;
begin
   var qmCwTop : Integer = _gui_GetTop;
   var qmCwI : Integer;
   Result := 0;
   for qmCwI:=0 to GetGUIElementChildrenCount(qmCwTop)-1 do
   if (GetGUIElementNameByIndex(GetGUIElementChildrenByIndex(qmCwTop, qmCwI))='QmManager') then
   Result := Result+1;
end;
function qmCuUiInt(const qmCiKey : String) : Integer;
begin
   Result := ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_ui'), qmCiKey);
end;
function qmCuRtInt(const qmCrKey : String) : Integer;
begin
   Result := 0;
   if (qmCuRtp<>0) then
   Result := ParserGetIntValueByKeyByHandle(qmCuRtp, qmCrKey);
end;
function qmCuApplyOn() : Integer;
begin
   var qmCaH : Integer = GetGUIElementIndexByNameParent('QmManager.main.wnd.bapply', _gui_GetTop);
   Result := -1;
   if (qmCaH<>0) then
   begin
      Result := 0;
      if GetGUIElementEnabled(qmCaH) then
      Result := 1;
   end;
end;
function qmCuShown() : Integer;
begin
   var qmCnH : Integer = GetGUIElementIndexByNameParent('QmManager.main.wnd.inst.installed', _gui_GetTop);
   Result := -1;
   if (qmCnH<>0) then
   Result := GetGUIListBoxItemsCount(qmCnH);
end;
procedure qmCuStep(const qmCsName : String);
begin
   var qmCsPe : Integer = -1;
   if (qmCuRow>=0) then
   qmCsPe := qmCuUiInt('pe'+IntToStr(qmCuRow));
   qmCuPut('step|'+qmCsName+'|'+IntToStr(qmCuUiInt('sel'))+'|'+IntToStr(qmCsPe)+'|'+IntToStr(qmCuUiInt('mode'))+'|'+IntToStr(qmCuVisible)+'|'+IntToStr(qmCuRtInt('uiapply'))+'|'+IntToStr(qmCuRtInt('uiapplyseq'))+'|'+IntToStr(qmCuRtInt('uiapplychg'))+'|'+IntToStr(qmCuRtInt('uiapplydis'+IntToStr(qmCuRow)))+'|'+IntToStr(qmCuRtInt('uiregen'))+'|'+IntToStr(qmCuUiInt('canapply'))+'|'+IntToStr(qmCuUiInt('ordchg'))+'|'+IntToStr(qmCuUiInt('panel'))+'|'+IntToStr(qmCuApplyOn));
end;
//! A keystroke in the filter box: the text the box holds after it, then the
//! key's release sent to the window's event state as the engine sends it
//! (Status `key`, Press `u`, eventloadgame.inc:77-99).
procedure qmCuType(const qmCtText : String);
begin
   var qmCtH : Integer = GetGUIElementIndexByNameParent('QmManager.fbox.filter.text', _gui_GetTop);
   if (qmCtH<>0) then
   SetGUIElementText(qmCtH, qmCtText);
   SetGUIValue('Status', 'key');
   SetGUIValue('Press', 'u');
   SetGUIIntValue('Tag', 65);
   SetGUIIntValue('ElementHandle', qmCtH);
   GUIExecuteState('EventQmManager');
end;

for qmCuD:=1 to qmCuNd-1 do
begin
   qmCuS := ParserGetValueByIndexByHandle(qmCuCode, qmCuD);
   if (SubStr(qmCuS, 1, 1)=';') then
   qmCuS := SubStr(qmCuS, 2, StrLength(qmCuS)-1);
   qmField(qmCuS, ' ', 0, qmCuVerb);
   qmField(qmCuS, ' ', 1, qmCuArg);
   if (qmCuVerb='cycles') then
   qmCuCycles := StrToInt(qmCuArg);
   if (qmCuVerb='toggle') then
   qmCuToggle := qmCuArg;
   if (qmCuVerb='keep') then
   qmCuKeep := StrToInt(qmCuArg);
end;
if (qmCuCycles>50) then
qmCuCycles := 50;

if (qmCuKeep=1) then
begin
   // One dump per life, <case>_<boot>.txt, next to the once-marker <case>.done.
   qmCuBoot := IntToStr(ParserGetIntValueByKeyByHandle(qmCuSt, 'boots'));
   qmCuDone := SubStr(qmCuOut, 1, StrLength(qmCuOut)-4)+'.done';
   qmCuOut := SubStr(qmCuOut, 1, StrLength(qmCuOut)-4)+'_'+qmCuBoot+'.txt';
   if (FileAge(qmCuDone)<>-1) then
   begin
      for qmCuI:=0 to ParserGetIntValueByKeyByHandle(qmCuMods, 'n')-1 do
      if SameText(ParserGetValueByKeyByHandle(qmCuMods, 'dir'+IntToStr(qmCuI)), qmCuToggle) then
      qmCuOn := IntToStr(ParserGetIntValueByKeyByHandle(qmCuMods, 'on'+IntToStr(qmCuI)));
      qmCuPut('life|'+qmCuBoot+'|later|on='+qmCuOn+'|why='+ParserGetValueByKeyByHandle(qmCuG, 'why'));
      ParserSetValueByKeyByHandle(qmCuRt, 'status', 'ok');
      exit;
   end;
   if (ParserGetIntValueByKeyByHandle(qmCuG, 'regen')=1) or (ParserGetIntValueByKeyByHandle(qmCuG, 'restart')=1) then
   begin
      qmCuPut('life|'+qmCuBoot+'|wait|regen='+IntToStr(ParserGetIntValueByKeyByHandle(qmCuG, 'regen'))+'|restart='+IntToStr(ParserGetIntValueByKeyByHandle(qmCuG, 'restart')));
      ParserSetValueByKeyByHandle(qmCuRt, 'status', 'ok');
      exit;
   end;
   qmCuPut('life|'+qmCuBoot+'|go');
end;

StateMachineExecuteState(qmCuCore, 'qmUiEnsure', 0);
qmCuUi := ParserSelectByKey('qm_ui');
qmCuPut('ensure|'+IntToStr(qmCuUiInt('ready'))+'|'+IntToStr(qmCuUiInt('show'))+'|'+IntToStr(qmCuUiInt('event'))+'|'+IntToStr(qmCuUiInt('adds')));

for qmCuI:=1 to qmCuCycles do
begin
   _gui_SendTagToState('EventMainMenu', 108);
   qmCuOpened := qmCuVisible;
   qmCuWin := qmCuWindows;
   qmCuOpens := qmCuUiInt('opens');
   if (qmCuI=1) and (qmCuOpened=0) then
   begin
      // Diagnostic only: does the window open when the hook is bypassed?
      GUIExecuteState('ShowQmManager');
      qmCuPut('direct|'+IntToStr(qmCuVisible));
   end;
   if (qmCuI mod 2=1) then
   begin
      qmCuHow := 'close';
      _gui_SendTagToState('EventQmManager', gc_gui_event_tagClose);
   end
   else
   begin
      qmCuHow := 'esc';
      _gui_SendTagToState('EventQmManager', gc_gui_hotkey_btnEscape);
   end;
   qmCuPut('cycle|'+IntToStr(qmCuI)+'|'+qmCuHow+'|'+IntToStr(qmCuOpened)+'|'+IntToStr(qmCuWin)+'|'+IntToStr(1-qmCuVisible)+'|'+IntToStr(qmCuOpens)+'|'+IntToStr(qmCuUiInt('closes')));
end;

if (qmCuToggle<>'') then
begin
   _gui_SendTagToState('EventMainMenu', 108);
   for qmCuI:=0 to qmCuUiInt('n')-1 do
   if SameText(ParserGetValueByKeyByHandle(qmCuUi, 'dir'+IntToStr(qmCuI)), qmCuToggle) then
   qmCuRow := qmCuI;
   qmHex(qmCuToggle, qmCuHex);
   if (qmCuRow>=0) then
   qmCuPut('row|'+qmCuHex+'|'+IntToStr(qmCuRow)+'|'+IntToStr(qmCuUiInt('en'+IntToStr(qmCuRow))))
   else
   qmCuPut('row|'+qmCuHex+'|-1|0');
   qmCuStep('open');
   if (qmCuRow>=0) then
   begin
      // The Active list's row of the mod, selected as a click selects it.
      qmCuList := GetGUIElementIndexByNameParent('QmManager.main.wnd.act.active', _gui_GetTop);
      qmCuItem := -1;
      if (qmCuList<>0) then
      qmCuItem := GetGUIListBoxItemIndexOfTag(qmCuList, qmCuRow);
      if (qmCuItem>=0) then
      begin
         SetGUIListBoxItemIndexSilent(qmCuList, qmCuItem);
         SetGUIValue('Status', 'select');
         SetGUIValue('Press', 'c');
         SetGUIIntValue('Tag', 0);
         SetGUIIntValue('ElementHandle', qmCuList);
         GUIExecuteState('EventQmManager');
      end;
      if (qmCuUiInt('sel')<>qmCuRow) then
      begin
         qmCuPut('selectvia|cmd|list='+IntToStr(qmCuList)+'|item='+IntToStr(qmCuItem));
         ParserSetValueByKeyByHandle(qmCuUi, 'cmd', 'select');
         ParserSetIntValueByKeyByHandle(qmCuUi, 'arg', qmCuRow);
         ParserSetIntValueByKeyByHandle(qmCuUi, 'argside', 1);
         ParserSetValueByKeyByHandle(qmCuUi, 'argtext', '');
         StateMachineExecuteState(qmCuCore, 'qmUiAct', 0);
         GUIExecuteState('ShowQmManager');
      end;
      qmCuStep('select');
      // Its place in the Active list: one place up and back, or down and back
      // when it loads first (Quartermaster, last, never moves).
      for qmCuK:=0 to qmCuUiInt('n')-1 do
      begin
         qmCuI := qmCuUiInt('ord'+IntToStr(qmCuK));
         if (qmCuUiInt('pe'+IntToStr(qmCuI))=1) then
         begin
            if (qmCuI=qmCuRow) then
            qmCuPlace := qmCuNa;
            qmCuNa := qmCuNa+1;
         end;
      end;
      if (qmCuPlace>0) then
      qmCuFirst := 'up'
      else
      qmCuFirst := 'down';
      qmCuPut('order|'+qmCuFirst+'|'+IntToStr(qmCuPlace)+'|'+IntToStr(qmCuNa));
      if (qmCuFirst='up') then
      _gui_SendTagToState('EventQmManager', qmCuTagUp)
      else
      _gui_SendTagToState('EventQmManager', qmCuTagDown);
      qmCuStep('move1');
      if (qmCuFirst='up') then
      _gui_SendTagToState('EventQmManager', qmCuTagDown)
      else
      _gui_SendTagToState('EventQmManager', qmCuTagUp);
      qmCuStep('move2');
      // The filter: the folder's name, typed; then cleared.
      qmCuText := qmCuToggle;
      while (StrPos('\', qmCuText)>0) do
      qmCuText := SubStr(qmCuText, StrPos('\', qmCuText)+1, StrLength(qmCuText)-StrPos('\', qmCuText));
      qmCuWant := 0;
      for qmCuI:=0 to qmCuUiInt('n')-1 do
      if (StrPos(StrToLowerCase(qmCuText), StrToLowerCase(ParserGetValueByKeyByHandle(qmCuUi, 'name'+IntToStr(qmCuI))+' '+ParserGetValueByKeyByHandle(qmCuUi, 'dir'+IntToStr(qmCuI))))>0) then
      qmCuWant := qmCuWant+1;
      qmCuType(qmCuText);
      qmCuStep('filter');
      qmCuPut('filtered|'+IntToStr(qmCuShown)+'|'+IntToStr(qmCuWant));
      qmCuType('');
      qmCuStep('filterclear');
      qmCuPut('unfiltered|'+IntToStr(qmCuShown)+'|'+IntToStr(qmCuUiInt('n')));
      // The Report view, and Esc back out of it.
      _gui_SendTagToState('EventQmManager', qmCuTagReport);
      qmCuStep('report');
      _gui_SendTagToState('EventQmManager', gc_gui_hotkey_btnEscape);
      qmCuStep('back');
      // Deactivate, Apply, Esc, Apply, Enter, Esc.
      _gui_SendTagToState('EventQmManager', qmCuTagDeact);
      qmCuStep('deactivate');
      _gui_SendTagToState('EventQmManager', qmCuTagApply);
      qmCuStep('apply');
      _gui_SendTagToState('EventQmManager', gc_gui_hotkey_btnEscape);
      qmCuStep('esc1');
      _gui_SendTagToState('EventQmManager', qmCuTagApply);
      qmCuStep('apply2');
      _gui_SendTagToState('EventQmManager', gc_gui_hotkey_btnEnter);
      qmCuStep('enter');
      _gui_SendTagToState('EventQmManager', gc_gui_hotkey_btnEscape);
      qmCuStep('esc2');
   end;
end;

var qmCuH : Integer = GetGUIElementIndexByNameParent('QmManager', _gui_GetTop);
if (qmCuH<>0) then
RemoveGUIElement(qmCuH);
qmCuPut('end|'+IntToStr(qmCuWindows)+'|'+IntToStr(qmCuUiInt('opens'))+'|'+IntToStr(qmCuUiInt('closes')));
if (qmCuKeep=1) then
begin
   // The request stays for qmTick: the next main-menu frame applies it.
   qmCuPut('kept|'+IntToStr(qmCuRtInt('uiapply'))+'|'+IntToStr(qmCuRtInt('uiapplyseq')));
   qmRawWriteStr(qmCuDone, 'ui|'+qmCuBoot+'~013~010');
end
else
begin
   if (qmCuRtp<>0) then
   ParserSetIntValueByKeyByHandle(qmCuRtp, 'uiapply', 0);
   if (qmCuUi<>0) then
   ParserSetIntValueByKeyByHandle(qmCuUi, 'mode', 0);
end;
ParserSetValueByKeyByHandle(qmCuRt, 'status', 'ok');
