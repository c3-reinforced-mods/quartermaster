screen: ShowQmManager
into: data/quartermaster/ui/showqmmanager.inc
helpers: qmlog, qmstr
requires:
---
//! The manager window (plan G15): Installed on the left, Active in load order
//! on the right, Activate / Deactivate between them, Up / Down under the
//! Active list, a one-line Details panel below and Apply, Report, Open
//! Workshop and Close at the bottom, under them a footer line while the load
//! order is not the canonical one; the Report view replaces the lists with
//! the report grouped by mod. A GUI state added to the GUI machine at run
//! time by qmUiEnsure; it draws qm_ui and decides nothing - qmUiAct owns the
//! behaviour, docs/ui.md the keys.
//!
//! Vanilla templates, all under data/gui/menu.inc/:
//!   modal parent, black mask, DPI scale, key state   showcreatejoinroom.inc:219-226
//!   main window, close button                        showcampaign.inc:313-315
//!   title in the main window's head frame            showcampaign.inc:318-320
//!                                                    (showloadgame.inc:389-390)
//!   list in a skin window with a head                showloadgame.inc:87-101
//!   tabs deleted before they are added again         showloadgame.inc:95-96
//!   selection, row count, scroller, top index        showcampaign.inc:246-253
//!   scrollable text panel                            showcampaign.inc:262-278
//!   input box and its character filter               showcreatejoinroom.inc:170, 189
//!   button with a caption; disabled when useless     showmainmenu.inc:16-24,
//!                                                    showloadgame.inc:326-327
//!   secondary text in grey 999999                    showmainmenu.inc:170, :173
//! Running this state again rebuilds the window in place: _gui_CreateParent
//! finds a parent by name and, unless asked to update, removes its children
//! first (data/scripts/lib/gui.script:446-452), so no element is ever
//! doubled. The top parent and the filter box are updated in place instead
//! (bupdate True): the box's edit control then survives every redraw, so a
//! keystroke's redraw keeps its caret and its focus - _gui_CreateInputBox
//! reuses the control and sets its text only when it changed
//! (gui.script:1602-1636), which is how the vanilla load window redraws on
//! every key (showloadgame.inc:20, :266; eventloadgame.inc:91-98).
//!
//! A fresh open (no window, or a hidden one) first asks the controller for
//! the command `open`, which rebuilds the model. When Quartermaster's
//! controller is not loaded the button keeps its vanilla meaning and opens the
//! Workshop page (eventmainmenu.inc:155).
//!
//! The confirm dialog is drawn over the window when qm_ui `mode` is 1, and
//! lists the pending changes (conf<k>). It is Quartermaster's own:
//! _gui_ShowModalMessage sends its buttons to EventModalMessage
//! (eventmodalmessage.inc:21-146), not to this window. Mode 2 is the restart
//! notice: drawn alone, no button, from a confirmed Apply until the process
//! ends - qmTick draws it too before a restart it runs itself, so the long
//! shutdown does not look like a freeze. The vanilla restart shows nothing
//! (onworkshopautoupdate.inc:4-11). Mode 3 is the start-up guard's notice
//! (plan S17): drawn over the window, the mods it switched off before
//! the scripts compiled (gdl<k>), one OK button.
//!
//! A pending set with a global-script clash (qmUiAct pcn, pc<k>) says so on
//! the message line, and the confirm dialog then lists the clashes
//! (confblk, confb<k>) with its Apply button disabled.
//!
//! The captions and messages are final since 2026-09-30.
const qmSmBupdate = False;
var qmSmElmname : String;
var qmSmShowstate : String;
var qmSmEventstate : String;
_misc_GetGUIShowEventStateNames('ShowQmManager', qmSmElmname, qmSmShowstate, qmSmEventstate);

// Tags shared with EventQmManager (tests/test_m6_screens.py keeps them equal).
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

const qmSmW = 1100;
const qmSmH = 740;
const qmSmPad = 7;
const qmSmScrollOff = 26;
// Layout in window units before the DPI scale: the lists end at 456 and
// start at 670, leaving the middle for the move buttons; Up / Down sit under
// the Active list, the one-line Details panel above the message line and
// the bottom buttons.
const qmSmLeftX = 40;
const qmSmRightX = 670;
const qmSmListY = 110;
const qmSmListW = 390;
const qmSmListH = 280;
const qmSmDescrY = 485;
const qmSmDescrH = 56;

var qmSmNul : String = '';
var qmSmText : String;
var qmSmColor : TColor;
_gui_SetupTColorInteger(255, 220, 170, 255, 0.9, qmSmColor);
var qmSmGrey : TColor;
_gui_SetupTColorInteger(150, 140, 125, 255, 0.9, qmSmGrey);
var qmSmHeadColor : TColor;
_gui_ConvertHexToTColor('FFDFAF', qmSmHeadColor);

//! A button with its caption; a disabled one gets a grey caption, so it
//! looks as unusable as it is.
function qmSmButton(const qmSbName : String; const qmSbParent : Integer; const qmSbHal : Integer; const qmSbVal : Integer; const qmSbX : Integer; const qmSbY : Integer; const qmSbCaption : String; const qmSbTag : Integer; const qmSbEnabled : Boolean) : Integer;
begin
   var qmSbText : String = qmSbCaption;
   Result := _gui_CreateButton(qmSbName, qmSbParent, 'btn.small', qmSbHal, qmSbVal, qmSbX, qmSbY, 0, 0, qmSmEventstate, qmSmNul, qmSbTag, qmSmBupdate);
   SetGUIElementEnabled(Result, qmSbEnabled);
   if (qmSbEnabled) then
   _gui_CreateText('txtbtn', Result, qmSbText, gc_halParentMiddle, gc_valParentMiddle, 0, 0, 0, 0, gc_halLeft, gc_valMiddle, gc_font_serif_15, qmSmColor, qmSmBupdate)
   else
   _gui_CreateText('txtbtn', Result, qmSbText, gc_halParentMiddle, gc_valParentMiddle, 0, 0, 0, 0, gc_halLeft, gc_valMiddle, gc_font_serif_15, qmSmGrey, qmSmBupdate);
end;

//! A name cut to what a column shows: measured in the font it is drawn in
//! (qmSfFont, an index of gUIConst.font; GetGUIElementFontTextRect, as
//! qmSmTextPanel measures its text) and cut with `...` until it fits, so it
//! never runs into the next column (hands-on check: "Cannons Attack
//! Automatically" ran into "Workshop").
procedure qmSmFit(const qmSfText : String; const qmSfW : Integer; const qmSfFont : Integer; var qmSfOut : String);
begin
   var qmSfTw : Integer;
   var qmSfTh : Integer;
   var qmSfN : Integer = StrLength(qmSfText);
   qmSfOut := qmSfText;
   GetGUIElementFontTextRect(gUIConst.font[qmSfFont], qmSfOut, qmSfTw, qmSfTh);
   while (qmSfTw>qmSfW) and (qmSfN>1) do
   begin
      qmSfN := qmSfN-1;
      qmSfOut := SubStr(qmSfText, 1, qmSfN)+'...';
      GetGUIElementFontTextRect(gUIConst.font[qmSfFont], qmSfOut, qmSfTw, qmSfTh);
   end;
end;

//! A setting's label for the Options view: as it is when it fits its column,
//! else broken at the last space that still fits, with the rest on a second
//! line, cut with `...` when that does not fit either. qmSlLines says how
//! many lines it took. Until 0.1.4 a label had one line, measured in serif 12
//! and drawn in serif 13: a long one lost its end and the `...` with it
//! (hands-on, 2026-10-10: "Fall of the capital in a new skirmish (the first
//! town centre fall", then the value). The break is made here from measured
//! widths, so the number of lines is known and not read out of a wrapped text.
//! qmSlCut says whether anything was left out: the caller then hangs the
//! whole label on it as a hint.
procedure qmSmLabel(const qmSlText : String; const qmSlW : Integer; const qmSlFont : Integer; var qmSlLines : Integer; var qmSlCut : Boolean; var qmSlOut : String);
begin
   var qmSlTw : Integer;
   var qmSlTh : Integer;
   var qmSlN : Integer = StrLength(qmSlText);
   var qmSlI : Integer = 2;
   var qmSlBreak : Integer = 0;
   var qmSlGo : Boolean = True;
   var qmSlHead : String;
   var qmSlTail : String;
   qmSlLines := 1;
   qmSlCut := False;
   qmSlOut := qmSlText;
   GetGUIElementFontTextRect(gUIConst.font[qmSlFont], qmSlOut, qmSlTw, qmSlTh);
   if (qmSlTw>qmSlW) then
   begin
      // The last space with a start that fits; the first start that does not
      // fit ends the search, every later one is longer.
      while (qmSlGo) and (qmSlI<=qmSlN) do
      begin
         if (SubStr(qmSlText, qmSlI, 1)=' ') then
         begin
            qmSlHead := SubStr(qmSlText, 1, qmSlI-1);
            GetGUIElementFontTextRect(gUIConst.font[qmSlFont], qmSlHead, qmSlTw, qmSlTh);
            if (qmSlTw<=qmSlW) then
            qmSlBreak := qmSlI
            else
            qmSlGo := False;
         end;
         qmSlI := qmSlI+1;
      end;
      if (qmSlBreak=0) then
      begin
         // No space to break at: one line, cut.
         qmSmFit(qmSlText, qmSlW, qmSlFont, qmSlOut);
         qmSlCut := True;
      end
      else
      begin
         qmSlHead := SubStr(qmSlText, 1, qmSlBreak-1);
         qmSlTail := SubStr(qmSlText, qmSlBreak+1, qmSlN-qmSlBreak);
         qmSmFit(qmSlTail, qmSlW, qmSlFont, qmSlOut);
         qmSlCut := (qmSlOut<>qmSlTail);
         qmSlOut := qmSlHead+gc_gui_breakline+qmSlOut;
         qmSlLines := 2;
      end;
   end;
end;

//! A scrollable text panel in skin window qmStBox (showcampaign.inc:262-278).
procedure qmSmTextPanel(const qmStBox : Integer; const qmStBody : String; const qmStH : Integer);
begin
   var qmStWrapped : String = GetGUIWrappedTextByFont(gUIConst.font[gc_font_serif_12], qmStBody, GetGUIElementWidth(qmStBox)-40);
   var qmStTw : Integer;
   var qmStTh : Integer;
   GetGUIElementFontTextRect(gUIConst.font[gc_font_serif_12], qmStWrapped, qmStTw, qmStTh);
   var qmStLayer : Integer = _gui_CreateScrollLayer('scrolllayer', qmStBox, gc_halParentLeft, gc_valParentTop, 0, 3, 0, qmStH-6, 0, 0, 0, 0, False, qmSmBupdate);
   SetGUIElementCursorByIndex(qmStLayer, 1);
   _gui_CreateText('txt', qmStLayer, qmStWrapped, gc_halParentLeft, gc_valParentTop, qmSmPad+4, qmSmPad-2, qmStTw, qmStTh, gc_halLeft, gc_valTop, gc_font_serif_12, qmSmColor, qmSmBupdate);
   var qmStScroll : Boolean = (qmStTh>(GetGUIElementHeight(qmStBox)-qmSmPad+4));
   _gui_AddScroller(qmStLayer, gc_halParentRightWidth, gc_valParentTop, 27, 20, 0, GetGUIElementHeight(qmStLayer), qmStScroll);
   SetGUIElementHeight(qmStLayer, Max(GetGUIElementHeight(qmStLayer)+1, qmStTh+7));
   SetGUIAllowEvents(qmStLayer, qmStScroll, False, False);
end;

var qmSmUi : Integer = ParserSelectByKey('qm_ui');
var qmSmCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
if (qmSmUi=0) or (qmSmCore=0) then
begin
   qmLog('ui show: the controller is not loaded (qm_ui='+IntToStr(qmSmUi)+' qm_core='+IntToStr(qmSmCore)+'); opening the Workshop page instead');
   OpenURL('http://steamcommunity.com/app/333420/workshop/');
   exit;
end;
var qmSmMode : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'mode');
//! A restart notice whose restart is gone (a SelfTest withdrew its Apply, or
//! qmTick dropped a restart that waited too long) is stale: browse again.
if (qmSmMode=2) then
begin
   var qmSmRtp : Integer = ParserSelectByKey('qm_rt');
   var qmSmLive : Boolean = False;
   if (qmSmRtp<>0) then
   qmSmLive := (ParserGetIntValueByKeyByHandle(qmSmRtp, 'uiapply')=1) or (ParserGetIntValueByKeyByHandle(qmSmRtp, 'rs')=1) or (ParserGetIntValueByKeyByHandle(qmSmRtp, 'rs')=2);
   if (not qmSmLive) then
   begin
      qmSmMode := 0;
      ParserSetIntValueByKeyByHandle(qmSmUi, 'mode', 0);
      qmLog('ui show: the restart notice is stale; back to browsing');
   end;
end;
var qmSmOld : Integer = GetGUIElementIndexByNameParent(qmSmElmname, _gui_GetTop);
var qmSmFresh : Boolean = True;
if (qmSmOld<>0) then
qmSmFresh := not GetGUIElementVisible(qmSmOld);
if (qmSmFresh) and (qmSmMode<>2) then
begin
   // Nothing is drawn unless the event state answers (it alone can close the
   // modal) and the controller took `open` (it clears `cmd` first thing).
   ParserSetIntValueByKeyByHandle(qmSmUi, 'pong', 0);
   ParserSetIntValueByKeyByHandle(qmSmUi, 'ping', 1);
   ExecuteState(qmSmEventstate);
   if (ParserGetIntValueByKeyByHandle(qmSmUi, 'pong')<>1) then
   begin
      ParserSetIntValueByKeyByHandle(qmSmUi, 'ping', 0);
      qmLog('ui show: '+qmSmEventstate+' did not answer; opening the Workshop page instead');
      OpenURL('http://steamcommunity.com/app/333420/workshop/');
      exit;
   end;
   //! qmPump first: when no frame runs qmTick, a restart the boot asked for
   //! is still owed, and it runs now (qmpump.pas).
   StateMachineExecuteState(qmSmCore, 'qmPump', 0);
   ParserSetValueByKeyByHandle(qmSmUi, 'cmd', 'open');
   StateMachineExecuteState(qmSmCore, 'qmUiAct', 0);
   if (ParserGetValueByKeyByHandle(qmSmUi, 'cmd')='open') then
   begin
      ParserSetValueByKeyByHandle(qmSmUi, 'cmd', '');
      qmLog('ui show: the controller qmUiAct did not run; opening the Workshop page instead');
      OpenURL('http://steamcommunity.com/app/333420/workshop/');
      exit;
   end;
   qmSmMode := ParserGetIntValueByKeyByHandle(qmSmUi, 'mode');
end;

// parent, mask and the DPI-scaled layers the window sits in; the parent is
// updated in place (see the top), everything under `main` is rebuilt
var qmSmParent : Integer = _gui_CreateParent(qmSmElmname, 0, gc_halLeft, gc_valTop, 0, 0, GetViewerWidth, GetViewerHeight, True);
var qmSmDpi : Float = _gui_AbsScaleByDPI(qmSmParent);
var qmSmVw : Integer = Round(GetViewerWidth/qmSmDpi);
var qmSmVh : Integer = Round(GetViewerHeight/qmSmDpi);
// The mask carries this window's event state so a click beside the window
// reaches EventQmManager (which ignores qmTagMask) instead of the main menu.
var qmSmMask : Integer = _gui_CreateImageActive('blackmask', qmSmParent, gc_gui_material_black, gc_halParentLeft, gc_valParentTop, 0, 0, GetViewerWidth, GetViewerHeight, qmTagMask, qmSmEventstate, '', True);
SetGUIElementUserBlend(qmSmMask, 0.65);
SetGUIElementPressState(qmSmParent, qmSmEventstate);
var qmSmMain : Integer = _gui_CreateParent('main', qmSmParent, gc_halLeft, gc_valTop, 0, 0, qmSmVw, qmSmVh, qmSmBupdate);
var qmSmBox : Integer = _gui_CreateParent('fbox', qmSmParent, gc_halLeft, gc_valTop, 0, 0, qmSmVw, qmSmVh, True);
// The Options view's text box lives in its own layer, updated in place like
// the filter box, so its edit control keeps caret and focus over redraws.
var qmSmOBox : Integer = _gui_CreateParent('obox', qmSmParent, gc_halLeft, gc_valTop, 0, 0, qmSmVw, qmSmVh, True);
// The Options view's search box, in a layer of its own for the same reason.
var qmSmSBox : Integer = _gui_CreateParent('sbox', qmSmParent, gc_halLeft, gc_valTop, 0, 0, qmSmVw, qmSmVh, True);
//! Each of the two layers is shown or hidden once a redraw, below, when the
//! view has said whether it uses it - not hidden here and shown again there:
//! in the hands-on run of 2026-10-13 (g21c) the search box took the letters
//! typed before the first redraw and none after it, three times "ca" of
//! "camera". The lists' filter box, whose layer is never hidden on the way,
//! keeps the keyboard over every redraw.
var qmSmOBoxOn : Boolean = False;
var qmSmSBoxOn : Boolean = False;
// The new-mod dialog (mode 4) and its name box, in a layer of its own that is
// updated in place, like the filter box.
var qmSmNm : Integer = _gui_CreateParent('newmod', qmSmParent, gc_halLeft, gc_valTop, 0, 0, qmSmVw, qmSmVh, qmSmBupdate);
var qmSmNBox : Integer = _gui_CreateParent('nbox', qmSmParent, gc_halLeft, gc_valTop, 0, 0, qmSmVw, qmSmVh, True);
SetGUIElementVisible(qmSmNm, qmSmMode=4);
SetGUIElementVisible(qmSmNBox, qmSmMode=4);
var qmSmConf : Integer = _gui_CreateParent('confirm', qmSmParent, gc_halLeft, gc_valTop, 0, 0, qmSmVw, qmSmVh, qmSmBupdate);
var qmSmNote : Integer = _gui_CreateParent('notice', qmSmParent, gc_halLeft, gc_valTop, 0, 0, qmSmVw, qmSmVh, qmSmBupdate);
var qmSmGNote : Integer = _gui_CreateParent('gnotice', qmSmParent, gc_halLeft, gc_valTop, 0, 0, qmSmVw, qmSmVh, qmSmBupdate);
SetGUIElementVisible(qmSmConf, qmSmMode=1);
SetGUIElementVisible(qmSmNote, qmSmMode=2);
SetGUIElementVisible(qmSmGNote, qmSmMode=3);
// One line of the dialogs' serif-13 lists: the font's own height and a gap,
// not a guess (20 was too small in the hands-on check: the list was cut).
var qmSmLh : Integer = GetGUIElementFontHeight(gUIConst.font[gc_font_serif_13])+3;
var qmSmT : Integer;

if (qmSmMode=2) then
begin
   // The restart notice alone: no window under it, no button on it.
   SetGUIElementVisible(qmSmMain, False);
   SetGUIElementVisible(qmSmBox, False);
   SetGUIElementVisible(qmSmOBox, False);
   SetGUIElementVisible(qmSmSBox, False);
   var qmSmNWnd : Integer = _gui_CreateSkinWindow('nwnd', qmSmNote, gc_halParentMiddle, gc_valParentMiddle, 0, 0, 660, 210, 1, qmSmBupdate);
   // The restart notice.
   qmSmText := 'Restarting the game';
   _gui_CreateText('ntext', qmSmNWnd, qmSmText, gc_halParentMiddle, gc_valParentTop, 0, 36, 0, 0, gc_halMiddle, gc_valMiddle, gc_font_serif_16, qmSmHeadColor, qmSmBupdate);
   qmSmText := ParserGetValueByKeyByHandle(qmSmUi, 'msg');
   if (qmSmText='') then
   qmSmText := 'Quartermaster has written the new files.';
   qmSmText := qmSmText+gc_gui_breakline+'The game closes and starts again by itself. This can take up to half a minute; the window may look frozen meanwhile.';
   qmSmText := GetGUIWrappedTextByFont(gUIConst.font[gc_font_serif_13], qmSmText, 600);
   _gui_CreateText('nnote', qmSmNWnd, qmSmText, gc_halParentMiddle, gc_valParentTop, 0, 70, 600, 110, gc_halMiddle, gc_valTop, gc_font_serif_13, qmSmColor, qmSmBupdate);
   SetGUIEventStateOnKeyDown(qmSmEventstate);
   qmLog('ui show restart notice');
   exit;
end;
SetGUIElementVisible(qmSmMain, True);

var qmSmWnd : Integer = _gui_CreateMainWindow('wnd', qmSmMain, gc_halParentMiddle, gc_valParentMiddle, 0, 0, qmSmW, qmSmH, 1, qmSmBupdate);
_gui_CreateButton('bclose', qmSmWnd, 'btn.close', gc_halParentRightWidth, gc_valParentTop, 4, -4, 0, 0, qmSmEventstate, qmSmNul, gc_gui_event_tagClose, qmSmBupdate);
var qmSmPanel : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'panel');
// The title goes into the main window's head frame, as vanilla puts it
// (showcampaign.inc:318-320): the child `head` of the window's `head` image.
// Window titles.
// The title is just the product name, in both views.
qmSmText := 'Quartermaster';
var qmSmHeadHnd : Integer = GetGUIElementIndexByNameParent('head.head', qmSmWnd);
if (qmSmHeadHnd<>0) then
_gui_CreateText('thead', qmSmHeadHnd, qmSmText, gc_halParentMiddle, gc_valParentMiddle, 9, 3, 0, 28, gc_halMiddle, gc_valMiddle, gc_font_serif_16, qmSmHeadColor, qmSmBupdate);

var qmSmN : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'n');
var qmSmSel : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'sel');
var qmSmSide : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'side');
var qmSmSelf : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'self');
var qmSmHeadOff : Integer = GetGUITextureHeight('skin.header.l')+5;
var qmSmHead : Integer;
var qmSmK : Integer;
var qmSmLines : Integer = 0;
var qmSmBody : String = '';
var qmSmRows : Integer = 0;
var qmSmActive : Integer = 0;

if (qmSmPanel=1) then
begin
   // The Report view: the report grouped by mod over the whole window.
   SetGUIElementVisible(qmSmBox, False);
   var qmSmRepBox : Integer = _gui_CreateSkinWindow('rep', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmLeftX, 60+qmSmHeadOff, qmSmW-qmSmLeftX*2-qmSmScrollOff, qmSmH-230, 1, qmSmBupdate);
   qmSmHead := _gui_CreateSkinHeadWindow('sh', qmSmRepBox, gc_halParentLeft, gc_valParentTop, 0, -qmSmHeadOff, GetGUIElementWidth(qmSmRepBox)+qmSmScrollOff, qmSmBupdate);
   // Head of the report view and the empty-report text.
   qmSmText := 'By mod, in load order';
   _gui_CreateText('thead', qmSmHead, qmSmText, gc_halParentLeft, gc_valParentMiddle, qmSmPad, 2, GetGUIElementWidth(qmSmHead), 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
   var qmSmRep : Integer = ParserSelectByKey('qm_report');
   if (qmSmRep<>0) then
   qmSmLines := ParserGetIntValueByKeyByHandle(qmSmRep, 'mlines');
   if (qmSmLines=0) then
   qmSmBody := 'No report yet: Quartermaster has not generated anything in this installation.'
   else
   for qmSmK:=0 to qmSmLines-1 do
   begin
      if (qmSmK>0) then
      qmSmBody := qmSmBody+gc_gui_breakline;
      qmSmBody := qmSmBody+ParserGetValueByKeyByHandle(qmSmRep, 'm'+IntToStr(qmSmK));
   end;
   qmSmTextPanel(qmSmRepBox, qmSmBody, qmSmH-230);
end
else
if (qmSmPanel=3) then
begin
   //! Mod files of a local mod (qmUiAct panel 3; plan G17): Create about.cfg
   //! when it has none, and the game files found by what the filter box
   //! holds, each marked with how Quartermaster treats it; the one picked is
   //! copied into the mod by Copy.
   SetGUIElementVisible(qmSmBox, True);
   var qmSmMr : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'mfrow');
   var qmSmVn : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'vn');
   var qmSmVs : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'vsel');
   // The texts of the Mod files view.
   qmSmText := 'Find:';
   _gui_CreateText('tfind', qmSmWnd, qmSmText, gc_halParentLeft, gc_valParentTop, qmSmLeftX, 70, 0, 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
   qmSmText := ParserGetValueByKeyByHandle(qmSmUi, 'typed');
   var qmSmVf : Integer = _gui_CreateInputBox('filter', qmSmBox, qmSmText, gc_halParentLeft, gc_valParentTop, (qmSmVw-qmSmW) div 2+qmSmLeftX+80, (qmSmVh-qmSmH) div 2+52, 260, 40, qmSmEventstate, qmSmNul, True, 10, 1, gc_halLeft, gc_valMiddle, gc_font_serif_13, 1, 1, 1, 1, True);
   _gui_InputBoxSetupStrCharFilter(qmSmVf, True, gc_gui_charfilter_default);
   var qmSmVBg : Integer = _gui_CreateSkinWindow('vbox', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmLeftX, qmSmListY+qmSmHeadOff, qmSmW-qmSmLeftX*2-qmSmScrollOff, qmSmListH, 1, qmSmBupdate);
   qmSmHead := _gui_CreateSkinHeadWindow('sh', qmSmVBg, gc_halParentLeft, gc_valParentTop, 0, -qmSmHeadOff, GetGUIElementWidth(qmSmVBg)+qmSmScrollOff, qmSmBupdate);
   qmSmText := 'Game files of '+ParserGetValueByKeyByHandle(qmSmUi, 'dir'+IntToStr(qmSmMr))+' (type 3 letters of a file path, pick a file, then Copy into mod)';
   _gui_CreateText('thead', qmSmHead, qmSmText, gc_halParentLeft, gc_valParentMiddle, qmSmPad, 2, GetGUIElementWidth(qmSmHead), 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
   var qmSmVl : Integer = _gui_CreateListBox('vfiles', qmSmVBg, gc_halParentLeft, gc_valParentTop, 2, qmSmPad, GetGUIElementWidth(qmSmVBg)-qmSmPad-2+qmSmScrollOff, GetGUIElementHeight(qmSmVBg)-qmSmPad*2+1, gc_halLeft, gc_valMiddle, 0, 0, gc_font_serif_12, qmSmEventstate, False, qmSmBupdate);
   for qmSmT:=GetGUIListBoxTabsCount(qmSmVl)-1 downto 0 do
   DeleteGUIListBoxTab(qmSmVl, qmSmT);
   AddGUIListBoxTabProperty(qmSmVl, 1, 1, 1, 1, qmSmPad+2, 'tsText');
   AddGUIListBoxTabProperty(qmSmVl, 1, 1, 1, 1, 620, 'tsText');
   AddGUIListBoxTabProperty(qmSmVl, 1, 1, 1, 1, 300, 'tsText');
   GUIListBoxClearSilent(qmSmVl);
   var qmSmVk : Integer;
   var qmSmVc : String;
   for qmSmVk:=0 to qmSmVn-1 do
   begin
      qmSmVc := ParserGetValueByKeyByHandle(qmSmUi, 'vc'+IntToStr(qmSmVk));
      // How a game file is treated, in the list.
      if (qmSmVc='merge') then
      qmSmVc := 'merged with other mods'
      else
      qmSmVc := 'not merged - the last mod''s copy is used';
      GUIListBoxAddItem(qmSmVl, #9+ParserGetValueByKeyByHandle(qmSmUi, 'v'+IntToStr(qmSmVk))+#9+qmSmVc, qmSmVk);
      if (qmSmVk=qmSmVs) then
      SetGUIListBoxItemIndexSilent(qmSmVl, qmSmVk);
   end;
   var qmSmVneed : Boolean = _gui_SetListBoxHeight(qmSmVl, (qmSmListH-qmSmPad*2) div (GetGUIElementFontHeight(gUIConst.font[gc_font_serif_12])+4));
   _gui_AddScroller(qmSmVl, gc_halParentRightWidth, gc_valParentTop, 28-4+5, 14+3-2, 0, GetGUIElementHeight(qmSmVBg), qmSmVneed);
   // The captions of the Mod files view.
   qmSmButton('bmfabout', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmLeftX, qmSmListY+qmSmHeadOff+qmSmListH+10, 'Create about.cfg', qmTagMfAbout, ParserGetIntValueByKeyByHandle(qmSmUi, 'mfhas')=0);
   qmSmButton('bmfcopy', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmLeftX+200, qmSmListY+qmSmHeadOff+qmSmListH+10, 'Copy into mod', qmTagMfCopy, qmSmVs>=0);
   qmSmButton('bmfback', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmLeftX+400, qmSmListY+qmSmHeadOff+qmSmListH+10, 'Back', qmTagMfBack, True);
end
else
if (qmSmPanel=2) then
begin
   //! The Options view (qmUiAct panel 2; plan G16): ten rows a page (orw<j>,
   //! orh<j>: qmUiAct lays them out), a row a setting with its label, its
   //! edited value (green while it differs from the stored one) and the
   //! buttons of its type - bool Switch; int and float - and +; choice < and
   //! >; key Change (then "press a key"); text Edit (then a text box in the
   //! value column) - or the title of the group of settings under it. A mod
   //! with groups, or with more settings than a page holds, has a strip over
   //! the rows (optstrip): the list of its groups and a search box, where the
   //! lists' filter stands in the main view. The rows then start where the
   //! lists do and a page has nine of them (optper).
   SetGUIElementVisible(qmSmBox, False);
   var qmSmOpt : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'opt');
   var qmSmOn : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'optn');
   var qmSmOrows : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'optrows');
   var qmSmOpg : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'optpg');
   var qmSmOcap : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'optcap');
   var qmSmOsel : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'optsel');
   var qmSmOper : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'optper');
   if (qmSmOper<1) then
   qmSmOper := 10;
   var qmSmOstrip : Boolean = (ParserGetIntValueByKeyByHandle(qmSmUi, 'optstrip')=1);
   var qmSmOgn : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'ogn');
   var qmSmOq : String = ParserGetValueByKeyByHandle(qmSmUi, 'optq');
   var qmSmOtop : Integer = 60;
   var qmSmOht : Integer = qmSmH-230;
   if (qmSmOstrip) then
   begin
      qmSmOtop := qmSmListY;
      qmSmOht := qmSmH-230-(qmSmListY-60);
   end;
   var qmSmOpages : Integer = (qmSmOrows+qmSmOper-1) div qmSmOper;
   var qmSmOBg : Integer = _gui_CreateSkinWindow('opts', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmLeftX, qmSmOtop+qmSmHeadOff, qmSmW-qmSmLeftX*2-qmSmScrollOff, qmSmOht, 1, qmSmBupdate);
   qmSmHead := _gui_CreateSkinHeadWindow('sh', qmSmOBg, gc_halParentLeft, gc_valParentTop, 0, -qmSmHeadOff, GetGUIElementWidth(qmSmOBg)+qmSmScrollOff, qmSmBupdate);
   // The head, captions and value words of the Options view.
   qmSmText := 'Options: '+ParserGetValueByKeyByHandle(qmSmUi, 'name'+IntToStr(qmSmOpt));
   // What a search found, in the head.
   if (qmSmOq<>'') then
   qmSmText := qmSmText+' - '+IntToStr(ParserGetIntValueByKeyByHandle(qmSmUi, 'optshown'))+' found';
   if (qmSmOpages>1) then
   qmSmText := qmSmText+' (page '+IntToStr(qmSmOpg+1)+' of '+IntToStr(qmSmOpages)+')';
   _gui_CreateText('thead', qmSmHead, qmSmText, gc_halParentLeft, gc_valParentMiddle, qmSmPad, 2, GetGUIElementWidth(qmSmHead), 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
   var qmSmOk : Integer;
   var qmSmOr : Integer;
   var qmSmOs : String;
   var qmSmOty : String;
   var qmSmOval : String;
   var qmSmOy : Integer;
   var qmSmOlb : String;
   var qmSmOll : Integer;
   var qmSmOcut : Boolean;
   var qmSmOhd : Integer;
   var qmSmOgt : String;
   // What the rows say when a search finds nothing (no other view is empty).
   if (qmSmOrows=0) then
   begin
      qmSmText := 'No setting has this in its name. Esc empties the search.';
      _gui_CreateText('onone', qmSmOBg, qmSmText, gc_halParentLeft, gc_valParentTop, 16, 14, 0, 36, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmGrey, qmSmBupdate);
   end;
   for qmSmOr:=0 to qmSmOper-1 do
   begin
      qmSmOk := -1;
      qmSmOhd := 0;
      if (qmSmOpg*qmSmOper+qmSmOr<qmSmOrows) then
      begin
         qmSmOk := ParserGetIntValueByKeyByHandle(qmSmUi, 'orw'+IntToStr(qmSmOpg*qmSmOper+qmSmOr));
         qmSmOhd := ParserGetIntValueByKeyByHandle(qmSmUi, 'orh'+IntToStr(qmSmOpg*qmSmOper+qmSmOr));
      end;
      qmSmOy := 14+qmSmOr*48;
      //! A group's title, in the font of the dialogs' titles and at the foot
      //! of its row, next to the settings it stands over; cut with `...`
      //! where the row ends. On a page the group runs on to it says so.
      if (qmSmOk>=0) and (qmSmOk<qmSmOn) and (qmSmOhd>0) then
      begin
         qmSmOgt := ParserGetValueByKeyByHandle(qmSmUi, 'ogr'+IntToStr(qmSmOk));
         // The mark of a group's title on a later page of the group.
         if (qmSmOhd=2) then
         qmSmOgt := qmSmOgt+' (continued)';
         qmSmFit(qmSmOgt, 940, gc_font_serif_16, qmSmOlb);
         _gui_CreateText('ogh'+IntToStr(qmSmOr), qmSmOBg, qmSmOlb, gc_halParentLeft, gc_valParentTop, 16, qmSmOy+8, 950, 36, gc_halLeft, gc_valMiddle, gc_font_serif_16, qmSmHeadColor, qmSmBupdate);
      end;
      if (qmSmOk>=0) and (qmSmOk<qmSmOn) and (qmSmOhd=0) then
      begin
         qmSmOs := IntToStr(qmSmOk);
         qmSmOty := ParserGetValueByKeyByHandle(qmSmUi, 'oty'+qmSmOs);
         qmSmOval := ParserGetValueByKeyByHandle(qmSmUi, 'ov'+qmSmOs);
         var qmSmOlt : String = ParserGetValueByKeyByHandle(qmSmUi, 'olb'+qmSmOs);
         // The mark of a setting the host decides in multiplayer.
         if (ParserGetValueByKeyByHandle(qmSmUi, 'osc'+qmSmOs)='host') then
         qmSmOlt := qmSmOlt+' (the host decides in multiplayer)';
         qmSmLabel(qmSmOlt, 410, gc_font_serif_13, qmSmOll, qmSmOcut, qmSmOlb);
         if (qmSmOll=1) then
         _gui_CreateText('olb'+qmSmOs, qmSmOBg, qmSmOlb, gc_halParentLeft, gc_valParentTop, 16, qmSmOy, 420, 36, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate)
         else
         // Two lines around the row's middle, each qmSmLh high from the top,
         // as the guard's notice lays out its list.
         _gui_CreateText('olb'+qmSmOs, qmSmOBg, qmSmOlb, gc_halParentLeft, gc_valParentTop, 16, qmSmOy+18-qmSmLh, 420, qmSmLh*2+4, gc_halLeft, gc_valTop, gc_font_serif_13, qmSmColor, qmSmBupdate);
         //! What a cut label leaves out is in its hint: a blank image over the
         //! label with a hint and no event state, as vanilla hangs a hint on an
         //! icon (showaiassistantadvices.inc:309; gui.script:236-275), in the
         //! style of vanilla's longer hints (showaiassistantsettings.inc:98) and
         //! wrapped at the label's own width.
         if (qmSmOcut) then
         begin
            qmSmText := gUIConst.fontstyle[gc_font_serif_13]+gc_font_color_white+GetGUIWrappedTextByFont(gUIConst.font[gc_font_serif_13], qmSmOlt, 420);
            _gui_CreateImageActive('olh'+qmSmOs, qmSmOBg, qmSmNul, gc_halParentLeft, gc_valParentTop, 16, qmSmOy-4, 420, 44, 0, qmSmNul, qmSmText, qmSmBupdate);
         end;
         if (qmSmOty='bool') then
         begin
            if (qmSmOval='1') then
            qmSmOval := 'On'
            else
            qmSmOval := 'Off';
         end;
         if (qmSmOty='key') and (qmSmOcap=qmSmOk) then
         qmSmOval := 'press a key...';
         if (qmSmOty='text') and (qmSmOval='') then
         qmSmOval := '(empty)';
         if (ParserGetValueByKeyByHandle(qmSmUi, 'ov'+qmSmOs)<>ParserGetValueByKeyByHandle(qmSmUi, 'ovs'+qmSmOs)) then
         qmSmOval := gc_font_color_green+qmSmOval+gc_font_color_default;
         if not ((qmSmOty='text') and (qmSmOsel=qmSmOk)) then
         _gui_CreateText('oval'+qmSmOs, qmSmOBg, qmSmOval, gc_halParentLeft, gc_valParentTop, 440, qmSmOy, 160, 36, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
         // The captions of a setting's buttons.
         if (qmSmOty='bool') then
         qmSmButton('ob1'+qmSmOs, qmSmOBg, gc_halParentLeft, gc_valParentTop, 800, qmSmOy-2, 'Switch', qmTagOptRow+qmSmOk*2, True);
         if (qmSmOty='int') or (qmSmOty='float') then
         begin
            qmSmButton('ob2'+qmSmOs, qmSmOBg, gc_halParentLeft, gc_valParentTop, 610, qmSmOy-2, '-', qmTagOptRow+qmSmOk*2+1, True);
            qmSmButton('ob1'+qmSmOs, qmSmOBg, gc_halParentLeft, gc_valParentTop, 800, qmSmOy-2, '+', qmTagOptRow+qmSmOk*2, True);
         end;
         if (qmSmOty='choice') then
         begin
            qmSmButton('ob2'+qmSmOs, qmSmOBg, gc_halParentLeft, gc_valParentTop, 610, qmSmOy-2, '<', qmTagOptRow+qmSmOk*2+1, True);
            qmSmButton('ob1'+qmSmOs, qmSmOBg, gc_halParentLeft, gc_valParentTop, 800, qmSmOy-2, '>', qmTagOptRow+qmSmOk*2, True);
         end;
         if (qmSmOty='key') then
         qmSmButton('ob1'+qmSmOs, qmSmOBg, gc_halParentLeft, gc_valParentTop, 800, qmSmOy-2, 'Change', qmTagOptRow+qmSmOk*2, qmSmOcap<>qmSmOk);
         if (qmSmOty='text') then
         begin
            qmSmButton('ob1'+qmSmOs, qmSmOBg, gc_halParentLeft, gc_valParentTop, 800, qmSmOy-2, 'Edit', qmTagOptRow+qmSmOk*2, qmSmOsel<>qmSmOk);
            if (qmSmOsel=qmSmOk) then
            begin
               //! The text box, in the value column of its row: window position
               //! plus box position plus row (the window is centred in the view).
               qmSmOBoxOn := True;
               qmSmText := ParserGetValueByKeyByHandle(qmSmUi, 'typed');
               var qmSmOIn : Integer = _gui_CreateInputBox('otext', qmSmOBox, qmSmText, gc_halParentLeft, gc_valParentTop, (qmSmVw-qmSmW) div 2+qmSmLeftX+436, (qmSmVh-qmSmH) div 2+qmSmOtop+qmSmHeadOff+qmSmOy-2, 168, 40, qmSmEventstate, qmSmNul, True, 10, 1, gc_halLeft, gc_valMiddle, gc_font_serif_13, 1, 1, 1, 1, True);
               _gui_InputBoxSetupStrCharFilter(qmSmOIn, True, gc_gui_charfilter_default);
            end;
         end;
      end;
   end;
   // The page buttons of the Options view.
   if (qmSmOpages>1) then
   begin
      qmSmButton('bprev', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmLeftX, qmSmOtop+qmSmHeadOff+qmSmOht+6, 'Previous', qmTagOptPrev, qmSmOpg>0);
      qmSmButton('bnext', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmW-qmSmLeftX-qmSmScrollOff-177, qmSmOtop+qmSmHeadOff+qmSmOht+6, 'Next', qmTagOptNext, qmSmOpg<qmSmOpages-1);
   end;
   //! The strip. The list of groups is vanilla's combo box, made and filled
   //! as the campaign window makes its difficulty list (showcampaign.inc:
   //! 101-110); a pick arrives as a `select` of the element, like a list's
   //! (eventcampaign.inc:16-33). It is made after the rows, so its open list
   //! lies over them. Its last entry is every setting; an entry's tag is its
   //! place. The search box is laid out as the lists' filter is.
   if (qmSmOstrip) then
   begin
      var qmSmOsx : Integer = qmSmLeftX;
      if (qmSmOgn>0) then
      begin
         // The captions of the strip.
         qmSmText := 'Group:';
         _gui_CreateText('tgroup', qmSmWnd, qmSmText, gc_halParentLeft, gc_valParentTop, qmSmOsx, 70, 0, 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
         // The open list shows twelve entries at most and scrolls the rest. The
         // box is some 22 high: at 60 its middle is the search box's (seen in
         // the game, run g21v1 of 2026-10-13: at 55 it stood 5 too high).
         var qmSmOlist : Integer = 0;
         if (qmSmOgn+1>12) then
         qmSmOlist := 12;
         var qmSmOcb : Integer = _gui_CreateComboBox('ogroup', qmSmWnd, qmSmOgn+1, qmSmOlist, gc_halParentLeft, gc_valParentTop, qmSmOsx+80, 60, 330, gc_halLeft, gc_valMiddle, 5, 0, gc_font_serif_12, True, qmSmEventstate, False, qmSmBupdate);
         for qmSmOk:=0 to qmSmOgn-1 do
         begin
            qmSmOgt := ParserGetValueByKeyByHandle(qmSmUi, 'ogt'+IntToStr(qmSmOk));
            // The name of the settings that stand under no group.
            if (qmSmOgt='') then
            qmSmOgt := 'General';
            qmSmFit(qmSmOgt+' ('+IntToStr(ParserGetIntValueByKeyByHandle(qmSmUi, 'ogc'+IntToStr(qmSmOk)))+')', 290, gc_font_serif_12, qmSmOlb);
            GUIListBoxAddItem(qmSmOcb, qmSmOlb, qmSmOk);
         end;
         qmSmText := 'All settings ('+IntToStr(qmSmOn)+')';
         GUIListBoxAddItem(qmSmOcb, qmSmText, qmSmOgn);
         //! A search goes over every group, so while one is on the list
         //! says All settings; the group comes back with the emptied box
         //! (seen in the game, run g21v3 of 2026-10-13: "General (2)" over
         //! nine settings found in another group read as a search in General).
         if (qmSmOq<>'') then
         SetGUIListBoxItemIndexSilent(qmSmOcb, qmSmOgn)
         else
         SetGUIListBoxItemIndexSilent(qmSmOcb, ParserGetIntValueByKeyByHandle(qmSmUi, 'optgrp'));
         qmSmOsx := qmSmOsx+450;
      end;
      qmSmText := 'Search:';
      _gui_CreateText('tsearch', qmSmWnd, qmSmText, gc_halParentLeft, gc_valParentTop, qmSmOsx, 70, 0, 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
      qmSmSBoxOn := True;
      var qmSmOfind : Integer = _gui_CreateInputBox('ofind', qmSmSBox, qmSmOq, gc_halParentLeft, gc_valParentTop, (qmSmVw-qmSmW) div 2+qmSmOsx+80, (qmSmVh-qmSmH) div 2+52, 260, 40, qmSmEventstate, qmSmNul, True, 10, 1, gc_halLeft, gc_valMiddle, gc_font_serif_13, 1, 1, 1, 1, True);
      _gui_InputBoxSetupStrCharFilter(qmSmOfind, True, gc_gui_charfilter_default);
   end;
end
else
begin
   // filter: every keystroke filters the Installed list (EventQmManager)
   // Filter label.
   qmSmText := 'Filter:';
   _gui_CreateText('tfilter', qmSmWnd, qmSmText, gc_halParentLeft, gc_valParentTop, qmSmLeftX, 70, 0, 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
   SetGUIElementVisible(qmSmBox, True);
   qmSmText := ParserGetValueByKeyByHandle(qmSmUi, 'typed');
   var qmSmFilter : Integer = _gui_CreateInputBox('filter', qmSmBox, qmSmText, gc_halParentLeft, gc_valParentTop, (qmSmVw-qmSmW) div 2+qmSmLeftX+80, (qmSmVh-qmSmH) div 2+52, 260, 40, qmSmEventstate, qmSmNul, True, 10, 1, gc_halLeft, gc_valMiddle, gc_font_serif_13, 1, 1, 1, 1, True);
   _gui_InputBoxSetupStrCharFilter(qmSmFilter, True, gc_gui_charfilter_default);

   var qmSmFilt : String = StrToLowerCase(ParserGetValueByKeyByHandle(qmSmUi, 'filter'));
   var qmSmRowH : Integer = GetGUIElementFontHeight(gUIConst.font[gc_font_serif_12])+4;
   qmSmRows := (qmSmListH-qmSmPad*2) div qmSmRowH;
   var qmSmI : Integer;
   var qmSmS : String;
   var qmSmName : String;
   var qmSmShort : String;
   var qmSmMark : String;
   var qmSmSt : String;
   var qmSmRow : Integer;
   var qmSmTop : Integer;
   var qmSmNeed : Boolean;

   // Installed: every registered mod, disabled ones too, in mods.ini order.
   // Column 1 marks a pending change (+ activated, - deactivated by Apply,
   // the Apply button's rule); the status column is `-` for an inactive mod.
   var qmSmInstBg : Integer = _gui_CreateSkinWindow('inst', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmLeftX, qmSmListY+qmSmHeadOff, qmSmListW, qmSmListH, 1, qmSmBupdate);
   qmSmHead := _gui_CreateSkinHeadWindow('sh', qmSmInstBg, gc_halParentLeft, gc_valParentTop, 0, -qmSmHeadOff, GetGUIElementWidth(qmSmInstBg)+qmSmScrollOff, qmSmBupdate);
   // Head of the Installed list.
   qmSmText := 'Installed';
   _gui_CreateText('thead', qmSmHead, qmSmText, gc_halParentLeft, gc_valParentMiddle, qmSmPad, 2, GetGUIElementWidth(qmSmHead), 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
   var qmSmInst : Integer = _gui_CreateListBox('installed', qmSmInstBg, gc_halParentLeft, gc_valParentTop, 2, qmSmPad, GetGUIElementWidth(qmSmInstBg)-qmSmPad-2+qmSmScrollOff, GetGUIElementHeight(qmSmInstBg)-qmSmPad*2+1, gc_halLeft, gc_valMiddle, 0, 0, gc_font_serif_12, qmSmEventstate, False, qmSmBupdate);
   for qmSmT:=GetGUIListBoxTabsCount(qmSmInst)-1 downto 0 do
   DeleteGUIListBoxTab(qmSmInst, qmSmT);
   AddGUIListBoxTabProperty(qmSmInst, 1, 1, 1, 1, qmSmPad+2, 'tsText');
   AddGUIListBoxTabProperty(qmSmInst, 1, 1, 1, 1, 20, 'tsText');
   AddGUIListBoxTabProperty(qmSmInst, 1, 1, 1, 1, 180, 'tsText');
   AddGUIListBoxTabProperty(qmSmInst, 1, 1, 1, 1, 100, 'tsText');
   AddGUIListBoxTabProperty(qmSmInst, 1, 1, 1, 1, 60, 'tsText');
   GUIListBoxClearSilent(qmSmInst);
   qmSmRow := 0;
   for qmSmI:=0 to qmSmN-1 do
   begin
      qmSmS := IntToStr(qmSmI);
      qmSmName := ParserGetValueByKeyByHandle(qmSmUi, 'name'+qmSmS);
      if (qmSmFilt='') or (StrPos(qmSmFilt, StrToLowerCase(qmSmName+' '+ParserGetValueByKeyByHandle(qmSmUi, 'dir'+qmSmS)))>0) then
      begin
         qmSmMark := '';
         if (ParserGetIntValueByKeyByHandle(qmSmUi, 'pe'+qmSmS)>ParserGetIntValueByKeyByHandle(qmSmUi, 'en'+qmSmS)) then
         qmSmMark := gc_font_color_green+'+';
         if (ParserGetIntValueByKeyByHandle(qmSmUi, 'pe'+qmSmS)<ParserGetIntValueByKeyByHandle(qmSmUi, 'en'+qmSmS)) then
         qmSmMark := gc_font_color_red+'-';
         // Status as plain text in the vanilla colour tags (dmscript.global:1212-1217);
         // the fonts are not known to hold check-mark glyphs.
         qmSmSt := ParserGetValueByKeyByHandle(qmSmUi, 'st'+qmSmS);
         if (qmSmSt='OK') then
         qmSmSt := gc_font_color_green+qmSmSt
         else
         if (qmSmSt='WARN') or (qmSmSt='?') then
         qmSmSt := gc_font_color_orange+qmSmSt
         else
         if (qmSmSt='FAIL') then
         qmSmSt := gc_font_color_red+qmSmSt
         else
         if (qmSmSt='NEW') then
         qmSmSt := gc_font_color_white+qmSmSt
         else
         qmSmSt := gc_font_color_lightgrey+qmSmSt;
         // A pending change has no status until the next generation (hands-on check).
         // The pending status word.
         if (qmSmMark<>'') then
         qmSmSt := gc_font_color_lightgrey+'PENDING';
         // An activation the check passed shows the check's word instead
         // (qmUiAct tck<i>, since 2026-10-01); the + stays.
         if (ParserGetIntValueByKeyByHandle(qmSmUi, 'pe'+qmSmS)>ParserGetIntValueByKeyByHandle(qmSmUi, 'en'+qmSmS)) then
         begin
            if (ParserGetValueByKeyByHandle(qmSmUi, 'tck'+qmSmS)='OK') then
            qmSmSt := gc_font_color_green+'OK';
            if (ParserGetValueByKeyByHandle(qmSmUi, 'tck'+qmSmS)='WARN') then
            qmSmSt := gc_font_color_orange+'WARN';
         end;
         // A colour tag lasts into the next cell: each coloured cell ends with the
         // default colour again (showinternetshell.inc:821).
         // The name column is 180 wide (the third tab above).
         qmSmFit(qmSmName, 172, gc_font_serif_12, qmSmShort);
         GUIListBoxAddItem(qmSmInst, #9+qmSmMark+gc_font_color_default+#9+qmSmShort+#9+ParserGetValueByKeyByHandle(qmSmUi, 'org'+qmSmS)+#9+qmSmSt+gc_font_color_default, qmSmI);
         if (qmSmI=qmSmSel) and (qmSmSide=0) then
         SetGUIListBoxItemIndexSilent(qmSmInst, qmSmRow);
         qmSmRow := qmSmRow+1;
      end;
   end;
   var qmSmShown : Integer = qmSmRow;
   qmSmNeed := _gui_SetListBoxHeight(qmSmInst, qmSmRows);
   _gui_AddScroller(qmSmInst, gc_halParentRightWidth, gc_valParentTop, 28-4+5, 14+3-2, 0, GetGUIElementHeight(qmSmInstBg), qmSmNeed);
   if (qmSmNeed) then
   begin
      qmSmTop := Max(0, Min(ParserGetIntValueByKeyByHandle(qmSmUi, 'topi'), qmSmRow-qmSmRows));
      SetGUIListBoxTopIndex(qmSmInst, qmSmTop);
      _gui_UpdateListBoxScrollerPos(qmSmInst);
   end;

   // Active: the mods Apply leaves enabled, in the pending load order
   var qmSmActBg : Integer = _gui_CreateSkinWindow('act', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmRightX, qmSmListY+qmSmHeadOff, qmSmListW, qmSmListH, 1, qmSmBupdate);
   qmSmHead := _gui_CreateSkinHeadWindow('sh', qmSmActBg, gc_halParentLeft, gc_valParentTop, 0, -qmSmHeadOff, GetGUIElementWidth(qmSmActBg)+qmSmScrollOff, qmSmBupdate);
   // Head of the Active list.
   qmSmText := 'Active (load order)';
   _gui_CreateText('thead', qmSmHead, qmSmText, gc_halParentLeft, gc_valParentMiddle, qmSmPad, 2, GetGUIElementWidth(qmSmHead), 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
   var qmSmAct : Integer = _gui_CreateListBox('active', qmSmActBg, gc_halParentLeft, gc_valParentTop, 2, qmSmPad, GetGUIElementWidth(qmSmActBg)-qmSmPad-2+qmSmScrollOff, GetGUIElementHeight(qmSmActBg)-qmSmPad*2+1, gc_halLeft, gc_valMiddle, 0, 0, gc_font_serif_12, qmSmEventstate, False, qmSmBupdate);
   for qmSmT:=GetGUIListBoxTabsCount(qmSmAct)-1 downto 0 do
   DeleteGUIListBoxTab(qmSmAct, qmSmT);
   AddGUIListBoxTabProperty(qmSmAct, 1, 1, 1, 1, qmSmPad+2, 'tsText');
   AddGUIListBoxTabProperty(qmSmAct, 1, 1, 1, 1, 34, 'tsText');
   AddGUIListBoxTabProperty(qmSmAct, 1, 1, 1, 1, 20, 'tsText');
   AddGUIListBoxTabProperty(qmSmAct, 1, 1, 1, 1, 230, 'tsText');
   AddGUIListBoxTabProperty(qmSmAct, 1, 1, 1, 1, 60, 'tsText');
   GUIListBoxClearSilent(qmSmAct);
   qmSmRow := 0;
   var qmSmPlace : Integer = -1;
   for qmSmK:=0 to qmSmN-1 do
   begin
      qmSmI := ParserGetIntValueByKeyByHandle(qmSmUi, 'ord'+IntToStr(qmSmK));
      qmSmS := IntToStr(qmSmI);
      if (ParserGetIntValueByKeyByHandle(qmSmUi, 'pe'+qmSmS)=1) then
      begin
         qmSmName := ParserGetValueByKeyByHandle(qmSmUi, 'name'+qmSmS);
         qmSmMark := '';
         qmSmSt := ParserGetValueByKeyByHandle(qmSmUi, 'st'+qmSmS);
         // A row Apply will activate has no status until the next generation: the
         // mark column says + and the status column says so in words (hands-on check).
         // The pending status word.
         if (ParserGetIntValueByKeyByHandle(qmSmUi, 'en'+qmSmS)=0) then
         begin
            qmSmMark := gc_font_color_green+'+';
            qmSmSt := gc_font_color_lightgrey+'PENDING';
            // The activation check's word once it passed (qmUiAct tck<i>).
            if (ParserGetValueByKeyByHandle(qmSmUi, 'tck'+qmSmS)='OK') then
            qmSmSt := gc_font_color_green+'OK';
            if (ParserGetValueByKeyByHandle(qmSmUi, 'tck'+qmSmS)='WARN') then
            qmSmSt := gc_font_color_orange+'WARN';
         end
         else
         if (qmSmSt='OK') then
         qmSmSt := gc_font_color_green+qmSmSt
         else
         if (qmSmSt='WARN') or (qmSmSt='?') then
         qmSmSt := gc_font_color_orange+qmSmSt
         else
         if (qmSmSt='FAIL') then
         qmSmSt := gc_font_color_red+qmSmSt
         else
         if (qmSmSt='NEW') then
         qmSmSt := gc_font_color_white+qmSmSt
         else
         qmSmSt := gc_font_color_lightgrey+qmSmSt;
         // The name column is 230 wide (the fourth tab above).
         qmSmFit(qmSmName, 222, gc_font_serif_12, qmSmShort);
         GUIListBoxAddItem(qmSmAct, #9+IntToStr(qmSmRow+1)+#9+qmSmMark+gc_font_color_default+#9+qmSmShort+#9+qmSmSt+gc_font_color_default, qmSmI);
         if (qmSmI=qmSmSel) and (qmSmSide=1) then
         begin
            SetGUIListBoxItemIndexSilent(qmSmAct, qmSmRow);
            qmSmPlace := qmSmRow;
         end;
         qmSmRow := qmSmRow+1;
      end;
   end;
   qmSmNeed := _gui_SetListBoxHeight(qmSmAct, qmSmRows);
   _gui_AddScroller(qmSmAct, gc_halParentRightWidth, gc_valParentTop, 28-4+5, 14+3-2, 0, GetGUIElementHeight(qmSmActBg), qmSmNeed);
   if (qmSmNeed) then
   begin
      qmSmTop := Max(0, Min(ParserGetIntValueByKeyByHandle(qmSmUi, 'topa'), qmSmRow-qmSmRows));
      SetGUIListBoxTopIndex(qmSmAct, qmSmTop);
      _gui_UpdateListBoxScrollerPos(qmSmAct);
   end;
   qmSmActive := qmSmRow;

   // the move buttons, enabled only when they would do something; Up / Down
   // move the selected Active row one place (qmUiOrder), never past
   // Quartermaster, which loads last
   var qmSmCanAct : Boolean = False;
   var qmSmCanDeact : Boolean = False;
   var qmSmCanUp : Boolean = False;
   var qmSmCanDown : Boolean = False;
   if (qmSmSel>=0) and (qmSmSel<qmSmN) then
   begin
      qmSmCanAct := (ParserGetIntValueByKeyByHandle(qmSmUi, 'pe'+IntToStr(qmSmSel))=0);
      qmSmCanDeact := (ParserGetIntValueByKeyByHandle(qmSmUi, 'pe'+IntToStr(qmSmSel))=1) and (qmSmSel<>qmSmSelf);
      qmSmCanUp := (qmSmPlace>0) and (qmSmSel<>qmSmSelf);
      qmSmCanDown := (qmSmPlace>=0) and (qmSmSel<>qmSmSelf) and (qmSmPlace<qmSmActive-2);
      if (qmSmSelf<0) then
      qmSmCanDown := (qmSmPlace>=0) and (qmSmPlace<qmSmActive-1);
   end;
   // Captions of the move buttons.
   qmSmButton('bact', qmSmWnd, gc_halParentMiddle, gc_valParentTop, 0, qmSmListY+qmSmHeadOff+100, 'Activate >', qmTagAct, qmSmCanAct);
   qmSmButton('bdeact', qmSmWnd, gc_halParentMiddle, gc_valParentTop, 0, qmSmListY+qmSmHeadOff+160, '< Deactivate', qmTagDeact, qmSmCanDeact);
   // Options: the selected mod declares settings in its about.cfg (qmUiModel
   // abs<i>); Auto-sort: the canonical order is known (hascanon).
   var qmSmCanOpt : Boolean = False;
   if (qmSmSel>=0) and (qmSmSel<qmSmN) then
   qmSmCanOpt := (ParserGetIntValueByKeyByHandle(qmSmUi, 'abs'+IntToStr(qmSmSel))>0) and (ParserGetIntValueByKeyByHandle(qmSmUi, 'abok')=1);
   qmSmButton('bopt', qmSmWnd, gc_halParentMiddle, gc_valParentTop, 0, qmSmListY+qmSmHeadOff+40, 'Options', qmTagOptions, qmSmCanOpt);
   qmSmButton('bsort', qmSmWnd, gc_halParentMiddle, gc_valParentTop, 0, qmSmListY+qmSmHeadOff+220, 'Auto-sort', qmTagAutoSort, ParserGetIntValueByKeyByHandle(qmSmUi, 'hascanon')=1);
   // New mod, and Mod files of a selected local mod (plan G17, M11).
   var qmSmCanFiles : Boolean = False;
   if (qmSmSel>=0) and (qmSmSel<qmSmN) then
   qmSmCanFiles := (ParserGetValueByKeyByHandle(qmSmUi, 'org'+IntToStr(qmSmSel))='Local') or (ParserGetValueByKeyByHandle(qmSmUi, 'org'+IntToStr(qmSmSel))='Local copy');
   // The captions of New mod and Mod files.
   qmSmButton('bnewmod', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmLeftX, qmSmListY+qmSmHeadOff+qmSmListH+10, 'New mod', qmTagNewMod, True);
   qmSmButton('bmodfiles', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmLeftX+200, qmSmListY+qmSmHeadOff+qmSmListH+10, 'Mod files', qmTagModFiles, qmSmCanFiles);
   qmSmButton('bup', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmRightX, qmSmListY+qmSmHeadOff+qmSmListH+10, 'Move up', qmTagUp, qmSmCanUp);
   qmSmButton('bdown', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmRightX+200, qmSmListY+qmSmHeadOff+qmSmListH+10, 'Move down', qmTagDown, qmSmCanDown);

   // the Details line of the selected mod (qmUiDetails)
   var qmSmDescr : Integer = _gui_CreateSkinWindow('descr', qmSmWnd, gc_halParentLeft, gc_valParentTop, qmSmLeftX, qmSmDescrY+qmSmHeadOff, qmSmW-qmSmLeftX*2-qmSmScrollOff, qmSmDescrH, 1, qmSmBupdate);
   qmSmHead := _gui_CreateSkinHeadWindow('sh', qmSmDescr, gc_halParentLeft, gc_valParentTop, 0, -qmSmHeadOff, GetGUIElementWidth(qmSmDescr)+qmSmScrollOff, qmSmBupdate);
   // Head of the details panel.
   qmSmText := 'Details';
   _gui_CreateText('thead', qmSmHead, qmSmText, gc_halParentLeft, gc_valParentMiddle, qmSmPad, 2, GetGUIElementWidth(qmSmHead), 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
   qmSmLines := ParserGetIntValueByKeyByHandle(qmSmUi, 'dn');
   for qmSmK:=0 to qmSmLines-1 do
   begin
      if (qmSmK>0) then
      qmSmBody := qmSmBody+gc_gui_breakline;
      qmSmBody := qmSmBody+ParserGetValueByKeyByHandle(qmSmUi, 'd'+IntToStr(qmSmK));
   end;
   qmSmTextPanel(qmSmDescr, qmSmBody, qmSmDescrH);
   qmSmRows := qmSmShown;
end;

// The Options view's two text-box layers: there for the view that made its
// box, gone for every other.
SetGUIElementVisible(qmSmOBox, qmSmOBoxOn);
SetGUIElementVisible(qmSmSBox, qmSmSBoxOn);

// the message line and the bottom buttons; Apply only with pending changes
// (qmUiAct `canapply`)
var qmSmCan : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'canapply');
qmSmText := ParserGetValueByKeyByHandle(qmSmUi, 'msg');
var qmSmPc : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'pcn');
// The line's colour goes to _gui_CreateText, not into the text as a
// %color()% code, so the line can wrap without a guess at whether a code
// carries over a line break.
var qmSmMsgHex : String = '';
// The about.cfg rules of the pending set (qmUiAct pan, pa<k>, pat<k>): the
// first FAIL in red, else the first WARN in orange. They come before a clash:
// a FAIL stops the Apply, a clash only asks (0.1.3).
var qmSmPa : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'pan');
var qmSmPk : Integer;
if (qmSmText='') and (qmSmPa>0) and (qmSmPanel<>2) then
begin
   var qmSmPfirst : String = '';
   qmSmMsgHex := gc_font_hex_color_orange;
   for qmSmPk:=qmSmPa-1 downto 0 do
   if (ParserGetValueByKeyByHandle(qmSmUi, 'pat'+IntToStr(qmSmPk))='FAIL') then
   begin
      qmSmPfirst := ParserGetValueByKeyByHandle(qmSmUi, 'pa'+IntToStr(qmSmPk))+'.';
      qmSmMsgHex := gc_font_hex_color_red;
   end;
   if (qmSmPfirst='') then
   qmSmPfirst := ParserGetValueByKeyByHandle(qmSmUi, 'pa0')+'.';
   qmSmText := qmSmPfirst;
   if (qmSmPa>1) then
   qmSmText := qmSmText+' ('+IntToStr(qmSmPa-1)+' more)';
end;
// The clash line, orange: two mods that ship the same file may still run
// together, and the start-up guard undoes a start that stops (red, and a
// refused Apply, until 0.1.3).
if (qmSmText='') and (qmSmPc>0) then
begin
   qmSmMsgHex := gc_font_hex_color_orange;
   qmSmText := 'May clash: '+ParserGetValueByKeyByHandle(qmSmUi, 'pc0')+'. If the game does not start with both, Quartermaster switches back.';
   if (qmSmPc>1) then
   qmSmText := qmSmText+' ('+IntToStr(qmSmPc-1)+' more)';
end;
// The pending-changes line.
if (qmSmText='') and (qmSmCan=1) and (qmSmPanel<>2) then
qmSmText := 'Pending changes: '+IntToStr(ParserGetIntValueByKeyByHandle(qmSmUi, 'chg'))+' mod(s), load order '+IntToStr(ParserGetIntValueByKeyByHandle(qmSmUi, 'ordchg'))+'. Apply writes them and restarts the game.';
// The line wraps to the window's width, and _gui_CreateText takes its height
// from the wrapped text (gui.script:288-296): a clash names two mods, and as
// one line it ran past both edges of the window (run look-wsX). The element
// hangs from its bottom edge, so a second line grew up into the Report
// view's panel (run look-wsY); half the extra height down keeps the lines
// centred where one line sits.
var qmSmMsgColor : TColor;
_gui_SetupTColorInteger(255, 220, 170, 255, 0.9, qmSmMsgColor);
if (qmSmMsgHex<>'') then
_gui_ConvertHexToTColor(qmSmMsgHex, qmSmMsgColor);
qmSmText := GetGUIWrappedTextByFont(gUIConst.font[gc_font_serif_13], qmSmText, qmSmW-80);
var qmSmMsgW : Integer;
var qmSmMsgH : Integer;
GetGUIElementFontTextFormatRect(gUIConst.font[gc_font_serif_13], qmSmText, qmSmMsgW, qmSmMsgH);
var qmSmMsgY : Integer = -92+Max(0, qmSmMsgH-GetGUIElementFontHeight(gUIConst.font[gc_font_serif_13])) div 2;
_gui_CreateText('tmsg', qmSmWnd, qmSmText, gc_halParentMiddle, gc_valParentBottomHeight, 0, qmSmMsgY, qmSmW-80, 0, gc_halMiddle, gc_valMiddle, gc_font_serif_13, qmSmMsgColor, qmSmBupdate);
// Captions of the bottom buttons.
if (qmSmPanel=2) then
begin
   // The Options view keeps its edits until Accept (qmUiAct optacc).
   qmSmButton('boacc', qmSmWnd, gc_halParentMiddle, gc_valParentBottomHeight, -300, -40, 'Accept', qmTagOptAccept, True);
   qmSmButton('bocan', qmSmWnd, gc_halParentMiddle, gc_valParentBottomHeight, -100, -40, 'Cancel', qmTagOptCancel, True);
   qmSmButton('bodef', qmSmWnd, gc_halParentMiddle, gc_valParentBottomHeight, 100, -40, 'Defaults', qmTagOptDefaults, True);
end
else
begin
   qmSmButton('bapply', qmSmWnd, gc_halParentMiddle, gc_valParentBottomHeight, -300, -40, 'Apply', qmTagApply, qmSmCan=1);
   if (qmSmPanel=1) then
   qmSmButton('breport', qmSmWnd, gc_halParentMiddle, gc_valParentBottomHeight, -100, -40, 'Back', qmTagReport, True)
   else
   qmSmButton('breport', qmSmWnd, gc_halParentMiddle, gc_valParentBottomHeight, -100, -40, 'Report', qmTagReport, True);
   qmSmButton('bworkshop', qmSmWnd, gc_halParentMiddle, gc_valParentBottomHeight, 100, -40, 'Open Workshop', qmTagWorkshop, True);
end;
qmSmButton('bclose2', qmSmWnd, gc_halParentMiddle, gc_valParentBottomHeight, 300, -40, 'Close', gc_gui_event_tagClose, True);

// the confirm dialog, in its own layer over the window: the changes it applies
if (qmSmMode=1) then
begin
   var qmSmCn : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'confn');
   var qmSmCo : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'confon');
   var qmSmCl : Integer = Max(qmSmCn, qmSmCo);
   var qmSmBlk : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'confblk');
   var qmSmBh : Integer = 0;
   if (qmSmBlk>0) then
   qmSmBh := (qmSmBlk+1)*qmSmLh+10;
   var qmSmCMask : Integer = _gui_CreateImageActive('cmask', qmSmConf, gc_gui_material_black, gc_halParentLeft, gc_valParentTop, 0, 0, qmSmVw, qmSmVh, qmTagMask, qmSmEventstate, '', qmSmBupdate);
   SetGUIElementUserBlend(qmSmCMask, 0.5);
   // Two columns side by side (hands-on check): what Apply switches on or off, and
   // the load order it leaves; each column is capped at 14 lines by qmUiAct.
   // A clash (confblk) adds its lines above the columns, in red.
   var qmSmCWnd : Integer = _gui_CreateSkinWindow('cwnd', qmSmConf, gc_halParentMiddle, gc_valParentMiddle, 0, 0, 820, 216+qmSmCl*qmSmLh+qmSmBh, 1, qmSmBupdate);
   // The confirm dialog's question, note and button captions.
   if (qmSmBlk>0) and (ParserGetIntValueByKeyByHandle(qmSmUi, 'confbrule')=1) then
   qmSmText := 'This set of mods cannot be applied'
   else
   if (qmSmBlk>0) then
   qmSmText := 'These mods cannot be active together'
   else
   qmSmText := 'Apply these changes and restart the game?';
   _gui_CreateText('ctext', qmSmCWnd, qmSmText, gc_halParentMiddle, gc_valParentTop, 0, 34, 0, 0, gc_halMiddle, gc_valMiddle, gc_font_serif_16, qmSmHeadColor, qmSmBupdate);
   if (qmSmBlk>0) then
   begin
      // The clash note of the confirm dialog.
      if (ParserGetIntValueByKeyByHandle(qmSmUi, 'confbrule')=1) then
      qmSmBody := gc_font_color_red+'Their about.cfg rules, or core scripts both of them replace, rule it out:'
      else
      qmSmBody := gc_font_color_red+'Both mods of each pair replace the same core script. Only one copy can load, and the game would stop at "Error compiling scripts":';
      for qmSmK:=0 to qmSmBlk-1 do
      qmSmBody := qmSmBody+gc_gui_breakline+gc_font_color_red+ParserGetValueByKeyByHandle(qmSmUi, 'confb'+IntToStr(qmSmK));
      _gui_CreateText('cblk', qmSmCWnd, qmSmBody, gc_halParentLeft, gc_valParentTop, 50, 58, 720, qmSmBh, gc_halLeft, gc_valTop, gc_font_serif_13, qmSmColor, qmSmBupdate);
   end;
   // The heads of the two columns and the no-switch line.
   qmSmText := 'Changes:';
   _gui_CreateText('chead', qmSmCWnd, qmSmText, gc_halParentLeft, gc_valParentTop, 50, 66+qmSmBh, 0, 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmHeadColor, qmSmBupdate);
   if (ParserGetIntValueByKeyByHandle(qmSmUi, 'confordchg')=1) then
   qmSmText := 'Load order (changed):'
   else
   qmSmText := 'Load order:';
   _gui_CreateText('cohead', qmSmCWnd, qmSmText, gc_halParentLeft, gc_valParentTop, 430, 66+qmSmBh, 0, 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmHeadColor, qmSmBupdate);
   qmSmBody := '';
   if (qmSmCn=0) then
   qmSmBody := 'no mod switched on or off'
   else
   for qmSmK:=0 to qmSmCn-1 do
   begin
      if (qmSmK>0) then
      qmSmBody := qmSmBody+gc_gui_breakline;
      qmSmBody := qmSmBody+ParserGetValueByKeyByHandle(qmSmUi, 'conf'+IntToStr(qmSmK));
   end;
   _gui_CreateText('clist', qmSmCWnd, qmSmBody, gc_halParentLeft, gc_valParentTop, 50, 84+qmSmBh, 350, qmSmCl*qmSmLh+4, gc_halLeft, gc_valTop, gc_font_serif_13, qmSmColor, qmSmBupdate);
   qmSmBody := '';
   for qmSmK:=0 to qmSmCo-1 do
   begin
      if (qmSmK>0) then
      qmSmBody := qmSmBody+gc_gui_breakline;
      qmSmBody := qmSmBody+ParserGetValueByKeyByHandle(qmSmUi, 'confo'+IntToStr(qmSmK));
   end;
   _gui_CreateText('colist', qmSmCWnd, qmSmBody, gc_halParentLeft, gc_valParentTop, 430, 84+qmSmBh, 350, qmSmCl*qmSmLh+4, gc_halLeft, gc_valTop, gc_font_serif_13, qmSmColor, qmSmBupdate);
   // The dialog's key note, with and without clashes.
   if (qmSmBlk>0) then
   qmSmText := 'Esc goes back; deactivate one mod of each pair first.'
   else
   qmSmText := 'Enter confirms, Esc cancels.';
   _gui_CreateText('cnote', qmSmCWnd, qmSmText, gc_halParentMiddle, gc_valParentBottomHeight, 0, -76, 0, 0, gc_halMiddle, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
   qmSmButton('byes', qmSmCWnd, gc_halParentMiddle, gc_valParentBottomHeight, -110, -28, 'Apply', qmTagYes, qmSmBlk=0);
   qmSmButton('bno', qmSmCWnd, gc_halParentMiddle, gc_valParentBottomHeight, 110, -28, 'Cancel', qmTagNo, True);
end;

// the new-mod dialog, over the window (mode 4; qmUiAct nm*)
if (qmSmMode=4) then
begin
   SetGUIElementVisible(qmSmBox, False);
   var qmSmNMask : Integer = _gui_CreateImageActive('nmask', qmSmNm, gc_gui_material_black, gc_halParentLeft, gc_valParentTop, 0, 0, qmSmVw, qmSmVh, qmTagMask, qmSmEventstate, '', qmSmBupdate);
   SetGUIElementUserBlend(qmSmNMask, 0.5);
   var qmSmNWnd2 : Integer = _gui_CreateSkinWindow('nwnd', qmSmNm, gc_halParentMiddle, gc_valParentMiddle, 0, 0, 820, 330, 1, qmSmBupdate);
   // The texts and captions of the new-mod dialog.
   qmSmText := 'New mod';
   _gui_CreateText('ntitle', qmSmNWnd2, qmSmText, gc_halParentMiddle, gc_valParentTop, 0, 34, 0, 0, gc_halMiddle, gc_valMiddle, gc_font_serif_16, qmSmHeadColor, qmSmBupdate);
   qmSmText := 'Name:';
   _gui_CreateText('nlabel', qmSmNWnd2, qmSmText, gc_halParentLeft, gc_valParentTop, 50, 90, 0, 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
   qmSmText := ParserGetValueByKeyByHandle(qmSmUi, 'nmname');
   var qmSmNIn : Integer = _gui_CreateInputBox('nname', qmSmNBox, qmSmText, gc_halParentLeft, gc_valParentTop, (qmSmVw-820) div 2+140, (qmSmVh-330) div 2+70, 400, 40, qmSmEventstate, qmSmNul, True, 40, 1, gc_halLeft, gc_valMiddle, gc_font_serif_13, 1, 1, 1, 1, True);
   _gui_InputBoxSetupStrCharFilter(qmSmNIn, True, gc_gui_charfilter_default);
   qmSmText := 'Folder: mods\'+ParserGetValueByKeyByHandle(qmSmUi, 'nmfolder');
   _gui_CreateText('nfolder', qmSmNWnd2, qmSmText, gc_halParentLeft, gc_valParentTop, 50, 140, 0, 0, gc_halLeft, gc_valMiddle, gc_font_serif_13, qmSmColor, qmSmBupdate);
   if (ParserGetIntValueByKeyByHandle(qmSmUi, 'nmtype')=1) then
   qmSmText := 'Type: total conversion'
   else
   qmSmText := 'Type: mod';
   qmSmButton('bnmtype', qmSmNWnd2, gc_halParentLeft, gc_valParentTop, 50, 175, qmSmText, qmTagNmType, True);
   qmField('|none|camera|ai|ui|balance|economy|sound|graphics|hotkeys|', '|', ParserGetIntValueByKeyByHandle(qmSmUi, 'nmexcl')+1, qmSmText);
   qmSmText := 'Slot: '+qmSmText;
   qmSmButton('bnmslot', qmSmNWnd2, gc_halParentLeft, gc_valParentTop, 260, 175, qmSmText, qmTagNmSlot, True);
   qmSmButton('bnmcreate', qmSmNWnd2, gc_halParentMiddle, gc_valParentBottomHeight, -110, -28, 'Create', qmTagNmCreate, ParserGetValueByKeyByHandle(qmSmUi, 'nmfolder')<>'');
   qmSmButton('bnmcancel', qmSmNWnd2, gc_halParentMiddle, gc_valParentBottomHeight, 110, -28, 'Cancel', qmTagNmCancel, True);
end;

// the start-up guard's notice, over the window (mode 3; qmUiAct gdl<k>)
if (qmSmMode=3) then
begin
   var qmSmGn : Integer = ParserGetIntValueByKeyByHandle(qmSmUi, 'gdln');
   var qmSmGMask : Integer = _gui_CreateImageActive('gmask', qmSmGNote, gc_gui_material_black, gc_halParentLeft, gc_valParentTop, 0, 0, qmSmVw, qmSmVh, qmTagMask, qmSmEventstate, '', qmSmBupdate);
   SetGUIElementUserBlend(qmSmGMask, 0.5);
   // The guard's notice: mods it switched off before the compile because each
   // ships a core script another active mod ships and the two had not started
   // together (conflict), or a step after a start that stopped (qm_ui gdwhy
   // failed-*, 0.1.3). A mod switched off after a failed start need not be
   // new, so neither text calls it so.
   var qmSmGFail : Boolean = (SubStr(ParserGetValueByKeyByHandle(qmSmUi, 'gdwhy'), 1, 7)='failed-');
   qmSmText := 'Each of them replaces a core script that another active mod replaces too, and they have not started together before. With both, the game may stop at "Error compiling scripts", so Quartermaster switched these mods off and restarted the game:';
   if (qmSmGFail) then
   qmSmText := 'The last start did not reach the main menu: it stopped at "Error compiling scripts", or the menu did not compile. To get the game running again, Quartermaster switched these mods off and restarted it:';
   var qmSmGWhy : String = GetGUIWrappedTextByFont(gUIConst.font[gc_font_serif_13], qmSmText, 720);
   // The line under the list: a clashing pair still runs when the player
   // activates it in this window (the Apply's chosen.cfg, qmOrder: the guard
   // trusts that set for one start and switches back if it stops).
   qmSmText := 'If they do work together, activate them here: Quartermaster lets them start once and switches back if the game does not start.';
   if (qmSmGFail) then
   qmSmText := 'Activate them again here one at a time to find the one that stops the start.';
   var qmSmGEnd : String = GetGUIWrappedTextByFont(gUIConst.font[gc_font_serif_13], qmSmText, 720);
   // Both texts wrap at the body's width and are measured as the message line
   // is; the list goes under the first, the second under the list, and the
   // window takes their height, so the OK button stays clear of a line under
   // the list that wraps (until 0.1.3 the body had three lines' room and that
   // line was one line hung above the button).
   var qmSmGTw : Integer;
   var qmSmGWh : Integer;
   var qmSmGEh : Integer;
   GetGUIElementFontTextFormatRect(gUIConst.font[gc_font_serif_13], qmSmGWhy, qmSmGTw, qmSmGWh);
   GetGUIElementFontTextFormatRect(gUIConst.font[gc_font_serif_13], qmSmGEnd, qmSmGTw, qmSmGEh);
   var qmSmGListY : Integer = 62+qmSmGWh+12;
   var qmSmGEndY : Integer = qmSmGListY+qmSmGn*qmSmLh+4+16;
   var qmSmGWnd : Integer = _gui_CreateSkinWindow('gwnd', qmSmGNote, gc_halParentMiddle, gc_valParentMiddle, 0, 0, 820, qmSmGEndY+qmSmGEh+4+70, 1, qmSmBupdate);
   qmSmText := 'Quartermaster switched off clashing mods';
   if (qmSmGFail) then
   qmSmText := 'Quartermaster switched mods off';
   _gui_CreateText('gtext', qmSmGWnd, qmSmText, gc_halParentMiddle, gc_valParentTop, 0, 34, 0, 0, gc_halMiddle, gc_valMiddle, gc_font_serif_16, qmSmHeadColor, qmSmBupdate);
   _gui_CreateText('gwhy', qmSmGWnd, qmSmGWhy, gc_halParentLeft, gc_valParentTop, 50, 62, 720, qmSmGWh+4, gc_halLeft, gc_valTop, gc_font_serif_13, qmSmColor, qmSmBupdate);
   qmSmBody := '';
   for qmSmK:=0 to qmSmGn-1 do
   begin
      if (qmSmK>0) then
      qmSmBody := qmSmBody+gc_gui_breakline;
      qmSmBody := qmSmBody+ParserGetValueByKeyByHandle(qmSmUi, 'gdl'+IntToStr(qmSmK));
   end;
   _gui_CreateText('glist', qmSmGWnd, qmSmBody, gc_halParentLeft, gc_valParentTop, 70, qmSmGListY, 700, qmSmGn*qmSmLh+4, gc_halLeft, gc_valTop, gc_font_serif_13, qmSmColor, qmSmBupdate);
   // Centred under the list, as the restart notice centres its wrapped note.
   _gui_CreateText('gnote', qmSmGWnd, qmSmGEnd, gc_halParentMiddle, gc_valParentTop, 0, qmSmGEndY, 720, qmSmGEh+4, gc_halMiddle, gc_valTop, gc_font_serif_13, qmSmColor, qmSmBupdate);
   qmSmButton('bok', qmSmGWnd, gc_halParentMiddle, gc_valParentBottomHeight, 0, -28, 'OK', qmTagOk, True);
end;
SetGUIEventStateOnKeyDown(qmSmEventstate);

// Evidence for the open/close runs: exactly one QmManager among the top
// elements, however often the window was opened.
var qmSmTopN : Integer = GetGUIElementChildrenCount(_gui_GetTop);
var qmSmMine : Integer = 0;
for qmSmT:=0 to qmSmTopN-1 do
if (GetGUIElementNameByIndex(GetGUIElementChildrenByIndex(_gui_GetTop, qmSmT))=qmSmElmname) then
qmSmMine := qmSmMine+1;
qmLog('ui show fresh='+BoolToStr(qmSmFresh)+' rows='+IntToStr(qmSmN)+' active='+IntToStr(qmSmActive)+' shown='+IntToStr(qmSmRows)+' pending='+IntToStr(ParserGetIntValueByKeyByHandle(qmSmUi, 'chg'))+' order='+IntToStr(ParserGetIntValueByKeyByHandle(qmSmUi, 'ordchg'))+' apply='+IntToStr(qmSmCan)+' sel='+IntToStr(qmSmSel)+' mode='+IntToStr(qmSmMode)+' panel='+IntToStr(qmSmPanel)+' top='+IntToStr(qmSmTopN)+' windows='+IntToStr(qmSmMine));
