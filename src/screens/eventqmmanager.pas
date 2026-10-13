screen: EventQmManager
into: data/quartermaster/ui/eventqmmanager.inc
helpers: qmlog
requires: version, maxsettings
---
//! Events of the manager window. A GUI state, so it can read the event values
//! (capability probes, probe 9a); it only translates each event into one
//! command for qmUiAct and then hides the window or draws it again. The
//! skeleton is vanilla (data/gui/menu.inc/eventcampaign.inc:4-59): read
//! ElementHandle / Press / Status / Tag, handle a list `select`, then the
//! button tags of press `c`.
//!
//! Esc and Enter arrive as the tags gc_gui_hotkey_btnEscape / btnEnter:
//! OnShortcut sends them to the last visible top element that has an event
//! state (onshortcut.inc:157-179), which is this window's parent while it is
//! open. While the filter box has the keyboard they may come as key events
//! instead, the way eventloadgame.inc:77-90 takes Esc and Enter on a key's
//! release; so a key-up of Esc or Enter counts when an edit control has the
//! focus. One key could then arrive both ways: the same key by the other way
//! within 0.4 s is the same keystroke and is taken once. Two presses by the
//! same way are two keystrokes, however quick.
//!
//! The filter follows every keystroke: on a key's release the box's text is
//! read (eventloadgame.inc:35-38) and, when it differs from the filter in
//! effect, sent as `filter` - vanilla redraws its window on every key the
//! same way (eventloadgame.inc:91-98).
//!
//! The load order moves with Move up / Move down only. A drag in the Active
//! list was built in v1.1 and dropped in v1.2: in the hands-on check of v1.1
//! every list select arrived with the left button already up (17 `ui drag
//! none` lines, not one `ui drag start`), so a select cannot start a drag,
//! and vanilla routes a drag only through its mouse hook (onmousehook.inc:
//! 9-12, for sliders) - a file Quartermaster does not hook (docs/ui.md).
//!
//! Open Workshop calls OpenURL exactly as the vanilla button does
//! (eventmainmenu.inc:155).
//!
//! Only this state can close the modal window, and a state that does not
//! compile does not run (capability probes, probe 8). So ShowQmManager runs it
//! once with qm_ui `ping` = 1 before it draws anything, and draws the window
//! only when the answer `pong` came back. For the same reason a command the
//! controller did not take (qmUiAct clears `cmd` first thing) closes the
//! window here rather than leaving it stuck over the main menu.
//!
//! qm_ui `rename` = 1 (set by qmTick) asks for the main menu's "Mod manager"
//! button caption instead: the vanilla way to change a caption at run time,
//! width first (eventprofile.inc:43-67), on the button's text child `txtbtn`
//! (showmainmenu.inc:16-24, :141).
//!
//! qm_ui `verline` = 1 (set by qmTick) asks for Quartermaster's version in the
//! main menu's bottom-right corner instead, where the game shows its own
//! (the text `ver` of the left frame, showmainmenu.inc:173) and where
//! SW_Frontline_Protocol adds its line (its showmainmenu.inc:173).
//! Quartermaster ships no showmainmenu.inc (its files are the hook files,
//! plan S5), so it adds a text of its own, `qmver`, to that frame, and leaves
//! every text the menu made as it is. It goes one line above the stack of
//! texts the menu keeps there: `ver`, and each visible text of the frame
//! whose y lies less than two heights above the stack's top - New Terrain
//! Mod puts its own version a line above the game's
//! (its showmainmenu.inc:174-175). The first try of 2026-09-30 grew `ver` by a
//! line instead, and the game's line then ran into New Terrain's (in game,
//! run look-wsD). The text is made the way the menu makes `ver` (anchored to
//! the frame's right and bottom, gc_font_serif_10), in the manager window's
//! head colour (FFDFAF).
//!
//! qm_ui `lobby` = 1 (set by qmTick) asks for Quartermaster's line in the
//! multiplayer lobby instead: one text `qmlobby` in the main window of the
//! internet shell, InternetShell.backgroundparent.background (the parent is
//! named after the state, misc.script:1929-1936; showinternetshell.inc:682,
//! :687, :1813). It says whether the load order is custom (qm_ui
//! `lobbycustom`, from the boot's qm_order `canon`). It is made once per
//! window: the shell redraws itself in place (bupdate True, :526, so
//! _gui_CreateParent keeps every child, gui.script:446-452) and is hidden,
//! not removed, when the player leaves it (eventinternetshell.inc:219-220,
//! :232). It sits at the window's bottom edge, centred and at most 460 wide,
//! clear of the chat input above it (showmultiplayerchat.inc:103) and of the
//! "Rating game" check box and the "Change profile" button beside it
//! (showinternetshell.inc:1787, :871); docs/ui.md has the arithmetic.
var qmEmUi : Integer = ParserSelectByKey('qm_ui');
if (qmEmUi<>0) and (ParserGetIntValueByKeyByHandle(qmEmUi, 'ping')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmEmUi, 'ping', 0);
   ParserSetIntValueByKeyByHandle(qmEmUi, 'pong', 1);
   exit;
end;
if (qmEmUi<>0) and (ParserGetIntValueByKeyByHandle(qmEmUi, 'rename')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmEmUi, 'rename', 0);
   var qmEmBtn : Integer = GetGUIElementIndexByNameParent('MainMenu.col1.row1.wnewgame.bmodman.txtbtn', _gui_GetTop);
   // The main menu button's caption.
   var qmEmCap : String = 'Mod Manager';
   if (qmEmBtn<>0) then
   begin
      var qmEmCapW : Integer = _gui_GetFontTextWidth(qmEmCap, gc_font_serif_15);
      SetGUIElementWidth(qmEmBtn, qmEmCapW);
      SetGUIElementLogicWidth(qmEmBtn, qmEmCapW);
      SetGUIElementText(qmEmBtn, qmEmCap);
      ParserSetIntValueByKeyByHandle(qmEmUi, 'renames', ParserGetIntValueByKeyByHandle(qmEmUi, 'renames')+1);
      // A caption that does not read back as set would be set again every frame.
      if (GetGUIElementText(qmEmBtn)<>qmEmCap) then
      ParserSetIntValueByKeyByHandle(qmEmUi, 'renameoff', 1);
      qmLog('ui rename: main menu button caption set, renames='+IntToStr(ParserGetIntValueByKeyByHandle(qmEmUi, 'renames'))+' reads back=['+GetGUIElementText(qmEmBtn)+'] off='+IntToStr(ParserGetIntValueByKeyByHandle(qmEmUi, 'renameoff')));
   end;
   exit;
end;
if (qmEmUi<>0) and (ParserGetIntValueByKeyByHandle(qmEmUi, 'verline')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmEmUi, 'verline', 0);
   var qmEmVer : Integer = GetGUIElementIndexByNameParent('MainMenu.col1.row1.wnewgame.ver', _gui_GetTop);
   if (qmEmVer<>0) then
   begin
      var qmEmVerPar : Integer = GetGUIElementParentByIndex(qmEmVer);
      if (GetGUIElementIndexByNameParent('qmver', qmEmVerPar)=0) then
      begin
         var qmEmTopY : Integer = GetGUIElementPositionY(qmEmVer);
         var qmEmTopH : Integer = GetGUIElementHeight(qmEmVer);
         var qmEmStack : Integer = 1;
         var qmEmMore : Boolean = True;
         var qmEmC : Integer;
         var qmEmCy : Integer;
         var qmEmK : Integer;
         while (qmEmMore) and (qmEmStack<8) do
         begin
            qmEmMore := False;
            for qmEmK:=0 to GetGUIElementChildrenCount(qmEmVerPar)-1 do
            if (not qmEmMore) then
            begin
               qmEmC := GetGUIElementChildrenByIndex(qmEmVerPar, qmEmK);
               qmEmCy := GetGUIElementPositionY(qmEmC);
               if (qmEmC<>qmEmVer) and (GetGUIElementVisible(qmEmC)) and (GetGUIElementText(qmEmC)<>'') and (qmEmCy<qmEmTopY) and (qmEmCy>qmEmTopY-2*qmEmTopH) then
               begin
                  qmEmTopY := qmEmCy;
                  qmEmTopH := GetGUIElementHeight(qmEmC);
                  qmEmStack := qmEmStack+1;
                  qmEmMore := True;
               end;
            end;
         end;
         // Quartermaster's version line.
         var qmEmVerText : String = 'Quartermaster '+${version};
         var qmEmVerColor : TColor;
         _gui_ConvertHexToTColor('FFDFAF', qmEmVerColor);
         _gui_CreateText('qmver', qmEmVerPar, qmEmVerText, gc_halParentRightWidth, gc_valParentBottomHeight, GetGUIElementPositionX(qmEmVer), qmEmTopY-qmEmTopH, GetGUIElementWidth(qmEmVer), 0, gc_halRight, gc_valMiddle, gc_font_serif_10, qmEmVerColor, True);
         ParserSetIntValueByKeyByHandle(qmEmUi, 'vers', ParserGetIntValueByKeyByHandle(qmEmUi, 'vers')+1);
         // A text that cannot be found again would be made again every frame.
         if (GetGUIElementIndexByNameParent('qmver', qmEmVerPar)=0) then
         ParserSetIntValueByKeyByHandle(qmEmUi, 'veroff', 1);
         qmLog('ui version line: made, vers='+IntToStr(ParserGetIntValueByKeyByHandle(qmEmUi, 'vers'))+' stack='+IntToStr(qmEmStack)+' y='+IntToStr(qmEmTopY-qmEmTopH)+' off='+IntToStr(ParserGetIntValueByKeyByHandle(qmEmUi, 'veroff')));
      end;
   end;
   exit;
end;
if (qmEmUi<>0) and (ParserGetIntValueByKeyByHandle(qmEmUi, 'lobby')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmEmUi, 'lobby', 0);
   var qmEmLob : Integer = GetGUIElementIndexByNameParent('InternetShell.backgroundparent.background', _gui_GetTop);
   if (qmEmLob<>0) then
   if (GetGUIElementIndexByNameParent('qmlobby', qmEmLob)=0) then
   begin
      var qmEmLobCus : Integer = ParserGetIntValueByKeyByHandle(qmEmUi, 'lobbycustom');
      var qmEmLobText : String;
      // The lobby line, for a custom and for the standard load order.
      if (qmEmLobCus=1) then
      qmEmLobText := 'Quartermaster: custom load order - every player needs the same mods in the same order.'
      else
      qmEmLobText := 'Quartermaster: standard load order.';
      // One line, in the grey of vanilla's secondary text (showmainmenu.inc:170;
      // the window's footer). The lobby window is 1018 wide (showinternetshell.inc:1813),
      // so the line needs no wrapping.
      var qmEmLobColor : TColor;
      _gui_ConvertHexToTColor('999999', qmEmLobColor);
      _gui_CreateText('qmlobby', qmEmLob, qmEmLobText, gc_halParentMiddle, gc_valParentBottomHeight, 0, -14, 900, 0, gc_halMiddle, gc_valMiddle, gc_font_serif_12, qmEmLobColor, True);
      ParserSetIntValueByKeyByHandle(qmEmUi, 'lobbies', ParserGetIntValueByKeyByHandle(qmEmUi, 'lobbies')+1);
      // A line that cannot be found again would be made again every frame.
      if (GetGUIElementIndexByNameParent('qmlobby', qmEmLob)<>0) then
      qmLog('lobby line shown custom='+IntToStr(qmEmLobCus))
      else
      begin
         ParserSetIntValueByKeyByHandle(qmEmUi, 'lobbyoff', 1);
         qmLog('lobby line: the text was not found after it was made; not tried again');
      end;
   end;
   exit;
end;
var qmEmElm : Integer = GetIntValueByName('ElementHandle');
var qmEmPress : String = GetValueByName('Press');
var qmEmTag : Integer = GetIntValueByName('Tag');
var qmEmStatus : String = GetValueByName('Status');
// A key or shortcut event carries a stale element handle (eventcreatejoinroom.inc:27-29).
if (qmEmStatus='shortcut') or (qmEmStatus='key') then
qmEmElm := 0;
var qmEmElmname : String;
var qmEmShowstate : String;
var qmEmEventstate : String;
_misc_GetGUIShowEventStateNames('EventQmManager', qmEmElmname, qmEmShowstate, qmEmEventstate);

// Tags shared with ShowQmManager (tests/test_m6_screens.py keeps them equal).
const qmTagAct = 101;
const qmTagDeact = 102;
const qmTagApply = 103;
const qmTagReport = 104;
const qmTagWorkshop = 105;
const qmTagYes = 107;
const qmTagNo = 108;
const qmTagMask = 109;
const qmTagUp = 110;
const qmTagDown = 111;
const qmTagOk = 112;
const qmTagOptPrev = 113;
const qmTagOptNext = 114;
const qmTagOptAccept = 115;
const qmTagOptCancel = 116;
const qmTagOptDefaults = 117;
const qmTagOptions = 118;
const qmTagAutoSort = 119;
const qmTagNewMod = 120;
const qmTagModFiles = 121;
const qmTagNmType = 122;
const qmTagNmSlot = 123;
const qmTagNmCreate = 124;
const qmTagNmCancel = 125;
const qmTagMfAbout = 126;
const qmTagMfCopy = 127;
const qmTagMfBack = 128;
const qmTagOptRow = 200;

var qmEmCmd : String = '';
var qmEmArg : Integer = -1;
var qmEmTo : Integer = -1;
var qmEmSide : Integer = 0;
var qmEmVia : String = 'shortcut';
var qmEmText : String = '';
var qmEmHnd : Integer;
var qmEmList : String = '';
var qmEmNow : Integer = Floor(_misc_GetRealTime*10);
if (qmEmUi=0) then
begin
   // No controller parser: nothing can be drawn or decided, so the modal goes.
   _gui_SetGUIElementVisibleByName(qmEmElmname, False);
   SetGUIEventStateOnKeyDown('');
   exit;
end;
// The filter box's text goes with every command, so a redraw keeps what was
// typed; the input box's edit control is its child `text`
// (showcreatejoinroom.inc:184, eventloadgame.inc:35-38). The box lives in
// its own layer `fbox`, updated in place, so the control survives redraws.
qmEmHnd := GetGUIElementIndexByNameParent(qmEmElmname+'.fbox.filter.text', _gui_GetTop);
if (qmEmHnd<>0) then
qmEmText := GetGUIElementText(qmEmHnd);
// The new-mod dialog's name box (layer nbox) holds the text in mode 4.
if (ParserGetIntValueByKeyByHandle(qmEmUi, 'mode')=4) then
begin
   qmEmHnd := GetGUIElementIndexByNameParent(qmEmElmname+'.nbox.nname.text', _gui_GetTop);
   if (qmEmHnd<>0) then
   qmEmText := GetGUIElementText(qmEmHnd);
end;
//! The Options view has two boxes of its own: the search box of its strip
//! (layer sbox; qm_ui optstrip) and, while a text setting is edited (optsel),
//! that setting's box (layer obox). A command carries the edited text while
//! there is one, else the search text - never the lists' filter, which this
//! view does not show.
var qmEmFind : String = '';
var qmEmBox : String = '';
if (ParserGetIntValueByKeyByHandle(qmEmUi, 'panel')=2) then
begin
   qmEmText := '';
   if (ParserGetIntValueByKeyByHandle(qmEmUi, 'optstrip')=1) then
   begin
      qmEmHnd := GetGUIElementIndexByNameParent(qmEmElmname+'.sbox.ofind.text', _gui_GetTop);
      if (qmEmHnd<>0) then
      qmEmFind := GetGUIElementText(qmEmHnd);
   end;
   qmEmText := qmEmFind;
   if (ParserGetIntValueByKeyByHandle(qmEmUi, 'optsel')>=0) then
   begin
      qmEmHnd := GetGUIElementIndexByNameParent(qmEmElmname+'.obox.otext.text', _gui_GetTop);
      if (qmEmHnd<>0) then
      qmEmText := GetGUIElementText(qmEmHnd);
   end;
end;
//! A key setting waiting for its key (qm_ui optcap, the Options view): the
//! key's down event, named the way vanilla's hotkey window names it
//! (hotkeysettings.inc:227-253: GetKeyNameByCode of the tag, a name longer
//! than two characters ignored unless it is Escape, Ctrl / Shift / Alt in
//! front). Escape keeps the old key. The same keystroke's release, and an
//! Esc or Enter shortcut of it, are not taken again within 0.4 s (capend).
if (qmEmStatus='key') and (ParserGetIntValueByKeyByHandle(qmEmUi, 'optcap')>=0) and (ParserGetIntValueByKeyByHandle(qmEmUi, 'panel')=2) then
begin
   if (qmEmPress<>'d') then
   exit;
   var qmEmKn : String = GetKeyNameByCode(qmEmTag);
   var qmEmEsc : Boolean = (StrPos('scape', StrToLowerCase(qmEmKn))>0) or (qmEmTag=27);
   if (StrLength(qmEmKn)>2) and (not qmEmEsc) then
   exit;
   var qmEmKey : String = '';
   if (not qmEmEsc) then
   begin
      if IsGUIShortcutPressed('Ctrl') then
      qmEmKey := 'Ctrl';
      if IsGUIShortcutPressed('Shift') then
      begin
         if (qmEmKey<>'') then
         qmEmKey := qmEmKey+'+';
         qmEmKey := qmEmKey+'Shift';
      end;
      if IsGUIShortcutPressed('Alt') then
      begin
         if (qmEmKey<>'') then
         qmEmKey := qmEmKey+'+';
         qmEmKey := qmEmKey+'Alt';
      end;
      if (qmEmKey<>'') then
      qmEmKey := qmEmKey+'+';
      qmEmKey := qmEmKey+qmEmKn;
   end;
   qmEmCmd := 'optkey';
   qmEmText := qmEmKey;
   ParserSetIntValueByKeyByHandle(qmEmUi, 'capend', qmEmNow);
   qmLog('ui key capture code='+IntToStr(qmEmTag)+' name='+qmEmKn+' key=['+qmEmKey+']');
end
else
if (qmEmStatus='key') then
begin
   // Key releases only (eventloadgame.inc:77-78): the text holds the key by then.
   if (qmEmPress<>'u') then
   exit;
   if (qmEmTag=13) or (qmEmTag=27) then
   begin
      if (GetGUIFocusedElementHandle=0) then
      exit;
      if (qmEmTag=13) then
      qmEmCmd := 'enter'
      else
      qmEmCmd := 'esc';
      qmEmVia := 'key';
   end
   else
   begin
      //! The box holds the filter, or in the Options view the text setting
      //! Edit chose (optsel): a key's release counts when the text changed.
      var qmEmRef : String = ParserGetValueByKeyByHandle(qmEmUi, 'filter');
      if (ParserGetIntValueByKeyByHandle(qmEmUi, 'mode')=4) then
      qmEmRef := ParserGetValueByKeyByHandle(qmEmUi, 'nmname')
      else
      if (ParserGetIntValueByKeyByHandle(qmEmUi, 'panel')=3) then
      qmEmRef := ParserGetValueByKeyByHandle(qmEmUi, 'vq');
      if (ParserGetIntValueByKeyByHandle(qmEmUi, 'panel')=2) then
      begin
         //! The search box's text changed: a search, whatever else is open.
         if (ParserGetIntValueByKeyByHandle(qmEmUi, 'optstrip')=1) and (qmEmFind<>ParserGetValueByKeyByHandle(qmEmUi, 'optq')) then
         begin
            qmEmCmd := 'optfind';
            qmEmText := qmEmFind;
            qmEmBox := qmEmElmname+'.sbox.ofind.text';
         end
         else
         begin
            if (ParserGetIntValueByKeyByHandle(qmEmUi, 'optsel')<0) then
            exit;
            qmEmRef := ParserGetValueByKeyByHandle(qmEmUi, 'ov'+IntToStr(ParserGetIntValueByKeyByHandle(qmEmUi, 'optsel')));
            qmEmBox := qmEmElmname+'.obox.otext.text';
         end;
      end;
      if (qmEmCmd='') then
      begin
         if (qmEmText=qmEmRef) then
         exit;
         qmEmCmd := 'filter';
      end;
   end;
end
else
if (qmEmStatus='select') and (qmEmElm<>0) then
begin
   // The item tag is the row in qm_ui (eventcampaign.inc:17-18).
   qmEmArg := GetGUIListBoxItemTag(qmEmElm, GetGUIListBoxItemIndex(qmEmElm));
   qmEmList := GetGUIElementNameByIndex(qmEmElm);
   if (qmEmList='installed') then
   qmEmCmd := 'select';
   if (qmEmList='vfiles') then
   qmEmCmd := 'vselect';
   //! The Options view's list of groups: the entry picked. Not on the press,
   //! as vanilla takes a combo box's pick (eventsettings.inc:455), and only
   //! a pick that changes what is shown: every command draws the window
   //! again, list included, and a list made anew while it opens would shut
   //! under the player's hand.
   if (qmEmList='ogroup') and (qmEmPress<>'d') then
   begin
      if (qmEmArg<>ParserGetIntValueByKeyByHandle(qmEmUi, 'optgrp')) or (ParserGetValueByKeyByHandle(qmEmUi, 'optq')<>'') then
      qmEmCmd := 'optgroup';
   end;
   if (qmEmList='active') then
   begin
      qmEmCmd := 'select';
      qmEmSide := 1;
   end;
end
else
if (qmEmPress='c') then
begin
   if (qmEmTag=qmTagAct) then
   qmEmCmd := 'activate';
   if (qmEmTag=qmTagDeact) then
   qmEmCmd := 'deactivate';
   if (qmEmTag=qmTagUp) then
   begin
      qmEmCmd := 'up';
      qmEmArg := ParserGetIntValueByKeyByHandle(qmEmUi, 'sel');
   end;
   if (qmEmTag=qmTagDown) then
   begin
      qmEmCmd := 'down';
      qmEmArg := ParserGetIntValueByKeyByHandle(qmEmUi, 'sel');
   end;
   if (qmEmTag=qmTagApply) then
   qmEmCmd := 'apply';
   if (qmEmTag=qmTagReport) then
   qmEmCmd := 'report';
   if (qmEmTag=qmTagYes) then
   qmEmCmd := 'confirm';
   if (qmEmTag=qmTagNo) then
   qmEmCmd := 'cancel';
   if (qmEmTag=qmTagOk) then
   qmEmCmd := 'ok';
   if (qmEmTag=gc_gui_event_tagClose) then
   qmEmCmd := 'close';
   if (qmEmTag=gc_gui_hotkey_btnEscape) then
   qmEmCmd := 'esc';
   if (qmEmTag=qmTagWorkshop) then
   begin
      OpenURL('http://steamcommunity.com/app/333420/workshop/');
      qmEmCmd := 'workshop';
   end;
   if (qmEmTag=gc_gui_hotkey_btnEnter) then
   qmEmCmd := 'enter';
   if (qmEmTag=qmTagOptions) then
   qmEmCmd := 'options';
   if (qmEmTag=qmTagNewMod) then
   qmEmCmd := 'newmod';
   if (qmEmTag=qmTagModFiles) then
   qmEmCmd := 'modfiles';
   if (qmEmTag=qmTagNmType) then
   qmEmCmd := 'nmtype';
   if (qmEmTag=qmTagNmSlot) then
   qmEmCmd := 'nmexcl';
   if (qmEmTag=qmTagNmCreate) then
   qmEmCmd := 'nmcreate';
   if (qmEmTag=qmTagNmCancel) then
   qmEmCmd := 'nmcancel';
   if (qmEmTag=qmTagMfAbout) then
   qmEmCmd := 'mfabout';
   if (qmEmTag=qmTagMfCopy) then
   qmEmCmd := 'mfcopy';
   if (qmEmTag=qmTagMfBack) then
   qmEmCmd := 'mfback';
   if (qmEmTag=qmTagAutoSort) then
   qmEmCmd := 'autosort';
   if (qmEmTag=qmTagOptAccept) then
   qmEmCmd := 'optacc';
   if (qmEmTag=qmTagOptCancel) then
   qmEmCmd := 'optcancel';
   if (qmEmTag=qmTagOptDefaults) then
   qmEmCmd := 'optdef';
   if (qmEmTag=qmTagOptPrev) then
   begin
      qmEmCmd := 'optpage';
      qmEmArg := -1;
   end;
   if (qmEmTag=qmTagOptNext) then
   begin
      qmEmCmd := 'optpage';
      qmEmArg := 1;
   end;
   //! A setting's buttons: tag 200 + 2 * setting + (0 main, 1 the other), for
   //! every setting a mod may declare: 200-2199 (until 0.1.5 the first 32
   //! only: the rest would have had buttons that did nothing).
   if (qmEmTag=qmTagOptRow) or ((qmEmTag>qmTagOptRow) and (qmEmTag<qmTagOptRow+${maxsettings}*2)) then
   begin
      qmEmCmd := 'optbtn';
      qmEmArg := (qmEmTag-qmTagOptRow) div 2;
      qmEmTo := (qmEmTag-qmTagOptRow) mod 2;
   end;
end;
// A capture's own keystroke may come back as its release or as an Esc /
// Enter shortcut; within 0.4 s it is the same keystroke.
if ((qmEmCmd='esc') or (qmEmCmd='enter')) and (ParserGetIntValueByKeyByHandle(qmEmUi, 'capend')>0) and (qmEmNow-ParserGetIntValueByKeyByHandle(qmEmUi, 'capend')<=4) then
begin
   qmLog('ui key '+qmEmCmd+' taken as the key capture''s own keystroke');
   exit;
end;
// Hover, mouse downs and ups, and clicks on the masks carry no command.
if (qmEmCmd='') then
exit;
// Esc and Enter may arrive twice for one key (shortcut and key release).
if (qmEmCmd='esc') or (qmEmCmd='enter') then
begin
   if (ParserGetValueByKeyByHandle(qmEmUi, 'keycmd')=qmEmCmd) and (ParserGetValueByKeyByHandle(qmEmUi, 'keyvia')<>qmEmVia) and (qmEmNow-ParserGetIntValueByKeyByHandle(qmEmUi, 'keyt')<=4) then
   begin
      qmLog('ui key '+qmEmCmd+' taken once: it came by '+qmEmVia+' too, '+IntToStr(qmEmNow-ParserGetIntValueByKeyByHandle(qmEmUi, 'keyt'))+' tenths later');
      ParserSetValueByKeyByHandle(qmEmUi, 'keycmd', '');
      exit;
   end;
   ParserSetValueByKeyByHandle(qmEmUi, 'keycmd', qmEmCmd);
   ParserSetValueByKeyByHandle(qmEmUi, 'keyvia', qmEmVia);
   ParserSetIntValueByKeyByHandle(qmEmUi, 'keyt', qmEmNow);
end;
var qmEmCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
if (qmEmCore=0) then
begin
   qmLog('ui event '+qmEmCmd+': the controller is not loaded (qm_core='+IntToStr(qmEmCore)+'); closing the window');
   _gui_SetGUIElementVisibleByName(qmEmElmname, False);
   SetGUIEventStateOnKeyDown('');
   exit;
end;
// The scroll positions are taken before the controller runs, so a command
// that resets them (a new filter) has the last word.
qmEmHnd := GetGUIElementIndexByNameParent(qmEmElmname+'.main.wnd.inst.installed', _gui_GetTop);
if (qmEmHnd<>0) then
ParserSetIntValueByKeyByHandle(qmEmUi, 'topi', GetGUIListBoxTopIndex(qmEmHnd));
qmEmHnd := GetGUIElementIndexByNameParent(qmEmElmname+'.main.wnd.act.active', _gui_GetTop);
if (qmEmHnd<>0) then
ParserSetIntValueByKeyByHandle(qmEmUi, 'topa', GetGUIListBoxTopIndex(qmEmHnd));
//! qmPump before the command and after it: when no frame runs qmTick (a
//! merged DoProgress that did not compile), what the last command left for
//! the tick is done before this one is judged, and what this one asks for -
//! the activation check, an Apply, a save - right after it (qmpump.pas).
StateMachineExecuteState(qmEmCore, 'qmPump', 0);
ParserSetValueByKeyByHandle(qmEmUi, 'cmd', qmEmCmd);
ParserSetIntValueByKeyByHandle(qmEmUi, 'arg', qmEmArg);
ParserSetIntValueByKeyByHandle(qmEmUi, 'argside', qmEmSide);
ParserSetIntValueByKeyByHandle(qmEmUi, 'argto', qmEmTo);
ParserSetValueByKeyByHandle(qmEmUi, 'argtext', qmEmText);
StateMachineExecuteState(qmEmCore, 'qmUiAct', 0);
//! New keys saved in the Options view: the shortcuts are registered again
//! as vanilla does after its hotkeys are saved (eventsettings.inc:727-728),
//! so a mod that reads its keys from qm_settings in RegisterShortcuts has
//! them at once.
if (ParserGetIntValueByKeyByHandle(qmEmUi, 'rereg')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmEmUi, 'rereg', 0);
   UnregisterGUIAllShortcuts();
   ExecuteState('RegisterShortcuts');
   ParserSetIntValueByKeyByHandle(qmEmUi, 'reregs', ParserGetIntValueByKeyByHandle(qmEmUi, 'reregs')+1);
   qmLog('ui shortcuts registered again after new keys, reregs='+IntToStr(ParserGetIntValueByKeyByHandle(qmEmUi, 'reregs')));
end;
if (ParserGetValueByKeyByHandle(qmEmUi, 'cmd')=qmEmCmd) then
begin
   qmLog('ui event '+qmEmCmd+': the controller qmUiAct did not run; closing the window');
   ParserSetValueByKeyByHandle(qmEmUi, 'cmd', '');
   _gui_SetGUIElementVisibleByName(qmEmElmname, False);
   SetGUIEventStateOnKeyDown('');
   exit;
end;
StateMachineExecuteState(qmEmCore, 'qmPump', 0);
if (ParserGetIntValueByKeyByHandle(qmEmUi, 'close')=1) then
begin
   // Closing only hides the window: it is a modal over the main menu, which
   // stayed where it was, and a later open rebuilds it in place.
   ParserSetIntValueByKeyByHandle(qmEmUi, 'close', 0);
   _gui_SetGUIElementVisibleByName(qmEmElmname, False);
   SetGUIEventStateOnKeyDown('');
end
else
begin
   ExecuteState(qmEmShowstate);
   //! A key typed into one of the Options view's boxes: the box has the
   //! keyboard after the redraw as before it. Its layer is updated in place
   //! and never hidden on the way (showqmmanager.pas), which is what keeps
   //! it; should a redraw take it all the same, it is given back the way
   //! vanilla gives a chat box the keyboard (eventclans.inc:61), and the log
   //! says so.
   if (qmEmBox<>'') then
   begin
      qmEmHnd := GetGUIElementIndexByNameParent(qmEmBox, _gui_GetTop);
      if (qmEmHnd<>0) and (GetGUIFocusedElementHandle<>qmEmHnd) then
      begin
         SetGUIElementFocusedHandle(qmEmHnd);
         qmLog('ui focus: the redraw took the keyboard from '+qmEmBox+'; given back');
      end;
   end;
end;
