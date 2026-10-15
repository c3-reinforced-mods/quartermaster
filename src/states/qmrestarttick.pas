state: qmTick
into: data/quartermaster/core.aix
helpers: qmlog
requires:
---
//! Quartermaster's main-menu tick: the DoProgress hook runs it on every
//! main-menu frame (plan S5, G14). It must cost next to nothing when idle, so
//! it reads a few qm_rt keys and returns; qmBoot sets `tick` = 1 when there
//! is work.
//!
//!   confirm  the first main-menu frame of a start that found `written`: the
//!            marker goes from booting to booted (ref/boot.py tick), so the
//!            next start knows this one reached the menu (plan S8);
//!   apply    a confirmed Apply of the manager window (qm_rt uiapply = 1,
//!            docs/ui.md): qmBoot runs again with runmode = apply - mods.ini,
//!            regeneration and the restart for the mods the player chose;
//!   restart  qm_rt rs = 1: when rsdue (tenths of a second, ref/boot.py
//!            restart_due: at least 1 s after the last write) has come, on a
//!            main-menu frame outside a map (gMap.gamestage none, as probe 5
//!            checked) and with no MP sync, qmRestart. A restart still waiting
//!            a minute after it was due (the player went into a battle) is
//!            dropped: its changes load at the next start (restart_now).
//!            The restart of a start that rewrote its outputs is not here:
//!            the boot runs it at its end (qmboot.pas; rs = 2 then).
//!   hooks    whenever the hook counters of qm_hk moved, one log line: the
//!            evidence of how often the hook points ran (capability probe 11).
//!   notice   before a restart it runs, the manager's restart notice
//!            (ShowQmManager, qm_ui mode 2) on the screen: the process exit
//!            and Steam's relaunch take about half a minute, which nothing
//!            here can shorten, and the vanilla restart shows nothing
//!            (onworkshopautoupdate.inc:4-11). The notice is drawn on the
//!            first frame the restart is due or waiting for its time, and the
//!            restart runs at least a tenth of a second later, so at least
//!            one frame shows it. GUIExecuteState from this trigger manager
//!            is how the SelfTest's ui case runs the window (qmcaseui.pas).
//!   rename   the main menu's "Mod manager" button reads "Mod Manager"
//!            (hands-on check, point 9): on every main-menu frame the caption
//!            of MainMenu.col1.row1.wnewgame.bmodman.txtbtn
//!            (showmainmenu.inc:85-93, :141, ShowButton at :16-24) is
//!            compared, and when ShowMainMenu has drawn it again, the GUI
//!            state EventQmManager sets it (qm_ui rename; eventprofile.inc:
//!            43-67 is the vanilla caption change). Only while the manager's
//!            screens are ready: without them the button keeps its vanilla
//!            meaning and its vanilla caption.
//!   version  Quartermaster's version in the main menu's bottom-right corner,
//!            where the game shows its own (2026-09-30: as
//!            SW_Frontline_Protocol shows its version): on every main-menu
//!            frame the text MainMenu.col1.row1.wnewgame.ver (the game's
//!            version line, showmainmenu.inc:173; Renaissance, New Terrain Mod
//!            and the Unofficial Patch keep it at that path) is looked up, and
//!            when its frame has no text `qmver` yet - ShowMainMenu has made
//!            the frame again - EventQmManager adds it (qm_ui verline). Only
//!            while the manager's screens are ready, and never again in the
//!            process after a text that could not be found (veroff).
//!   lobby    the multiplayer lobby's line (v1.2 hands-on check, point 4): on
//!            every main-menu frame - the internet shell is drawn in the
//!            main-menu mode (doprogress.inc:1193, :1263) - the shell's main
//!            window InternetShell.backgroundparent.background
//!            (showinternetshell.inc:682, :687, :1813; the same path form as
//!            eventinternetshell.inc:69) is looked up, and when it has no
//!            child `qmlobby` yet, EventQmManager draws one (qm_ui lobby).
//!            It says whether the running game's load order is custom: the
//!            boot's qm_order `canon` = 0, the condition of the report's
//!            multiplayer line (qmboot.pas). Without qm_order nothing is
//!            drawn: the order is not known. A missed name lookup is silent
//!            (_gui_CreateParent looks up every new name, gui.script:447).
//!
//! A write here (the confirm) moves rsdue so the restart still comes at least
//! 1 s after it.
//!
//! The frame hook is a line in a merged state: when that DoProgress does not
//! compile - a mod it was merged from was switched off outside Quartermaster,
//! and the start loaded the outputs made with it - nothing runs this state
//! (hands-on, 2026-10-10: the boot's restart never came and the window's
//! activation check waited for ever). So every run by the frame hook leaves
//! the time in qm_rt `tkat`, and qmPump, which the manager window runs, runs
//! this state itself (qm_rt `pump` = 1) once that time stands still. Such a
//! run does the work - settings, mod files, the activation check, the
//! confirm, an Apply - and leaves out what belongs to a frame: the captions
//! and lines it draws through EventQmManager (the window's event state may be
//! the one running the pump), the notices and the run switches, and the
//! restart, which qmPump runs itself, as no later frame would. The boot's
//! restart after such a start no longer waits for either: since 2026-10-15
//! the boot runs it itself (qmboot.pas; hands-on, 2026-10-14: the player went
//! for the lobby, not the window, and no restart came).
var qmTkRt : Integer = ParserSelectByKey('qm_rt');
if (qmTkRt=0) then
exit;
var qmTkPump : Boolean = (ParserGetIntValueByKeyByHandle(qmTkRt, 'pump')=1);
if (not qmTkPump) then
ParserSetIntValueByKeyByHandle(qmTkRt, 'tkat', Floor(_misc_GetRealTime*10));
// Set by the work below that can take seconds; the time is left again then.
var qmTkLong : Boolean = False;
var qmTkUi : Integer = ParserSelectByKey('qm_ui');
// What a frame draws: none of it in a run by qmPump.
var qmTkGui : Integer = qmTkUi;
if (qmTkPump) then
qmTkGui := 0;
if (qmTkGui<>0) then
if (ParserGetIntValueByKeyByHandle(qmTkUi, 'ready')=1) and (ParserGetIntValueByKeyByHandle(qmTkUi, 'renameoff')=0) then
begin
   var qmTkBtn : Integer = GetGUIElementIndexByNameParent('MainMenu.col1.row1.wnewgame.bmodman.txtbtn', _gui_GetTop);
   // The main menu button's caption (EventQmManager sets it).
   if (qmTkBtn<>0) then
   if (GetGUIElementText(qmTkBtn)<>'Mod Manager') then
   begin
      ParserSetIntValueByKeyByHandle(qmTkUi, 'rename', 1);
      GUIExecuteState('EventQmManager');
   end;
end;
if (qmTkGui<>0) then
if (ParserGetIntValueByKeyByHandle(qmTkUi, 'ready')=1) and (ParserGetIntValueByKeyByHandle(qmTkUi, 'veroff')=0) then
begin
   var qmTkVer : Integer = GetGUIElementIndexByNameParent('MainMenu.col1.row1.wnewgame.ver', _gui_GetTop);
   if (qmTkVer<>0) then
   if (GetGUIElementIndexByNameParent('qmver', GetGUIElementParentByIndex(qmTkVer))=0) then
   begin
      ParserSetIntValueByKeyByHandle(qmTkUi, 'verline', 1);
      GUIExecuteState('EventQmManager');
   end;
end;
if (qmTkGui<>0) then
if (ParserGetIntValueByKeyByHandle(qmTkUi, 'ready')=1) and (ParserGetIntValueByKeyByHandle(qmTkUi, 'lobbyoff')=0) then
begin
   var qmTkLob : Integer = GetGUIElementIndexByNameParent('InternetShell.backgroundparent.background', _gui_GetTop);
   if (qmTkLob<>0) then
   if (GetGUIElementIndexByNameParent('qmlobby', qmTkLob)=0) then
   begin
      var qmTkOrd : Integer = ParserSelectByKey('qm_order');
      if (qmTkOrd<>0) then
      if (ParserGetValueByKeyByHandle(qmTkOrd, 'src')<>'') then
      begin
         if (ParserGetIntValueByKeyByHandle(qmTkOrd, 'canon')=0) then
         ParserSetIntValueByKeyByHandle(qmTkUi, 'lobbycustom', 1)
         else
         ParserSetIntValueByKeyByHandle(qmTkUi, 'lobbycustom', 0);
         ParserSetIntValueByKeyByHandle(qmTkUi, 'lobby', 1);
         GUIExecuteState('EventQmManager');
      end;
   end;
end;
//! The start-up guard's notice (plan S17): qmBoot sets qm_rt gdshow after a
//! start the guard restarted. On the first main-menu frame outside a map with
//! the manager's screens ready, no boot running and no restart pending, the
//! manager opens with the notice on top (qm_ui gdopen; qmUiAct mode 3) - once.
if (qmTkGui<>0) then
if (ParserGetIntValueByKeyByHandle(qmTkRt, 'gdshow')=1) and (ParserGetIntValueByKeyByHandle(qmTkUi, 'ready')=1) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'busy')=0) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'rs')=0) and (gMap.gamestage=gc_map_gamestage_none) then
begin
   ParserSetIntValueByKeyByHandle(qmTkRt, 'gdshow', 0);
   ParserSetIntValueByKeyByHandle(qmTkUi, 'gdopen', 1);
   GUIExecuteState('ShowQmManager');
   // The note is marked shown only now (qmGlobals shows a note until then).
   var qmTkGn : Integer = ParserSelectByKey('qm_glob_note');
   if (qmTkGn<>0) then
   if (ParserGetValueByKeyByHandle(qmTkGn, 'n')<>'') then
   begin
      ParserSetValueByKeyByHandle(qmTkGn, 'shown', '1');
      ParserSaveToFileByHandle(qmTkGn, GetAppSaveDirectoryPath+'quartermaster\guard.cfg');
   end;
   qmLog('tick: the guard notice opened, mode='+IntToStr(ParserGetIntValueByKeyByHandle(qmTkUi, 'mode'))+' lines='+IntToStr(ParserGetIntValueByKeyByHandle(qmTkUi, 'gdln')));
end
else
//! A harness run's switch (qmBoot, qm_show_ui.flag): the window opens once -
//! not before qm_rt uishowat (tenths of a second; 0 for the switch file),
//! which a SelfTest case that leaves a view sets a few seconds ahead: the
//! case runs in the boot's own frame, and a window opened there goes with the
//! GUI the start-up's second DoCreate builds anew (run g21v1, 2026-10-13:
//! opened at log line 175, DoCreate at 186).
if (ParserGetIntValueByKeyByHandle(qmTkRt, 'uishow')=1) and (Floor(_misc_GetRealTime*10)>=ParserGetIntValueByKeyByHandle(qmTkRt, 'uishowat')) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'gdshow')=0) and (ParserGetIntValueByKeyByHandle(qmTkUi, 'ready')=1) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'busy')=0) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'rs')=0) and (gMap.gamestage=gc_map_gamestage_none) then
begin
   ParserSetIntValueByKeyByHandle(qmTkRt, 'uishow', 0);
   GUIExecuteState('ShowQmManager');
   qmLog('tick: the window opened for the run (qm_show_ui.flag)');
   ParserSetIntValueByKeyByHandle(qmTkRt, 'uishowat', 0);
   //! A SelfTest case's view (qmCaseOpt `keep`): a window a case leaves open
   //! does not outlive the start-up, whose second DoCreate builds the GUI
   //! anew, so the case leaves the steps to its view instead - qm_rt uiplayn,
   //! and per step uiplayc<k> the command, uiplaya<k> its number, uiplayt<k>
   //! its text. The controller gets them here, the window open, and the
   //! window is drawn again.
   var qmTkPn : Integer = ParserGetIntValueByKeyByHandle(qmTkRt, 'uiplayn');
   var qmTkPk : Integer;
   if (qmTkPn>0) then
   begin
      ParserSetIntValueByKeyByHandle(qmTkRt, 'uiplayn', 0);
      for qmTkPk:=0 to qmTkPn-1 do
      begin
         ParserSetValueByKeyByHandle(qmTkUi, 'cmd', ParserGetValueByKeyByHandle(qmTkRt, 'uiplayc'+IntToStr(qmTkPk)));
         ParserSetIntValueByKeyByHandle(qmTkUi, 'arg', ParserGetIntValueByKeyByHandle(qmTkRt, 'uiplaya'+IntToStr(qmTkPk)));
         ParserSetIntValueByKeyByHandle(qmTkUi, 'argside', 1);
         ParserSetIntValueByKeyByHandle(qmTkUi, 'argto', 0);
         ParserSetValueByKeyByHandle(qmTkUi, 'argtext', ParserGetValueByKeyByHandle(qmTkRt, 'uiplayt'+IntToStr(qmTkPk)));
         StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmUiAct', 0);
      end;
      GUIExecuteState('ShowQmManager');
      qmLog('tick: the window shows the view a case left, steps='+IntToStr(qmTkPn));
   end;
end;
//! The notice outlives a rebuilt menu. The game's second start-up DoCreate
//! builds the GUI anew, and the window went with it while qm_ui mode stayed
//! 3: the player never saw the notice, and the manager then ignored `open`
//! (run look-wsH, 2026-09-30: opened at log line 231, the second DoCreate at
//! 236). So on a main-menu frame outside a map with no boot or restart under
//! way, a notice still up whose window (QmManager, misc.script:1931-1932) is
//! gone or hidden is drawn again; OK or close end mode 3.
if (qmTkGui<>0) then
if (ParserGetIntValueByKeyByHandle(qmTkUi, 'mode')=3) and (ParserGetIntValueByKeyByHandle(qmTkUi, 'ready')=1) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'busy')=0) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'rs')=0) and (gMap.gamestage=gc_map_gamestage_none) then
if (GetGUIElementIndexByNameParent('MainMenu', _gui_GetTop)<>0) then
begin
   var qmTkWin : Integer = GetGUIElementIndexByNameParent('QmManager', _gui_GetTop);
   var qmTkUp : Boolean = False;
   if (qmTkWin<>0) then
   qmTkUp := GetGUIElementVisible(qmTkWin);
   if (not qmTkUp) then
   begin
      GUIExecuteState('ShowQmManager');
      ParserSetIntValueByKeyByHandle(qmTkUi, 'gdagain', ParserGetIntValueByKeyByHandle(qmTkUi, 'gdagain')+1);
      qmLog('tick: the guard notice shown again, its window was gone (times='+IntToStr(ParserGetIntValueByKeyByHandle(qmTkUi, 'gdagain'))+')');
   end;
end;
//! A harness run's switch (qmBoot, qm_skirmish.flag): into a skirmish the way
//! SW_Frontline_Protocol's autotest walks in
//! (mods\SW_Frontline_Protocol\tools\swfp\templates\autotest.pas:357-399,
//! read only): ShowCustomGame, and two seconds later DoNewGame with
//! gbool_gui_donewgamerestart. It waits for a start with no boot running, no
//! restart pending and no Apply, then 15 s on the main menu (the window is
//! captured meanwhile) and closes the manager first.
var qmTkSk : Integer = ParserGetIntValueByKeyByHandle(qmTkRt, 'skphase');
if (qmTkSk>0) and (qmTkSk<9) and (not qmTkPump) then
begin
   var qmTkSkNow : Integer = Floor(_misc_GetRealTime*10);
   var qmTkSkT : Integer = ParserGetIntValueByKeyByHandle(qmTkRt, 'skt');
   if (qmTkSk=1) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'busy')=0) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'rs')=0) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'uiapply')=0) and (gMap.gamestage=gc_map_gamestage_none) and (GetGUIElementIndexByNameParent('MainMenu', _gui_GetTop)<>0) then
   begin
      ParserSetIntValueByKeyByHandle(qmTkRt, 'skphase', 2);
      ParserSetIntValueByKeyByHandle(qmTkRt, 'skt', qmTkSkNow);
      qmLog('run: a skirmish starts in 15 s');
   end
   else
   if (qmTkSk=2) and (qmTkSkNow-qmTkSkT>=150) then
   begin
      _gui_SetGUIElementVisibleByName('QmManager', False);
      ParserSetIntValueByKeyByHandle(qmTkRt, 'skphase', 3);
      ParserSetIntValueByKeyByHandle(qmTkRt, 'skt', qmTkSkNow);
      qmLog('run: skirmish lobby opened');
      GUIExecuteState('ShowCustomGame');
   end
   else
   if (qmTkSk=3) and (qmTkSkNow-qmTkSkT>=20) and (GetGUIElementIndexByNameParent('CustomGame', _gui_GetTop)<>0) then
   begin
      ParserSetIntValueByKeyByHandle(qmTkRt, 'skphase', 9);
      gbool_gui_donewgamerestart := True;
      _gui_SetGUIElementVisibleByName('CustomGame', False);
      qmLog('run: skirmish started');
      GUIExecuteState('DoNewGame');
   end;
end;
var qmTkHk : Integer = ParserSelectByKey('qm_hk');
if (qmTkHk<>0) then
if (ParserGetIntValueByKeyByHandle(qmTkHk, 'cc')<>ParserGetIntValueByKeyByHandle(qmTkHk, 'lcc')) or (ParserGetIntValueByKeyByHandle(qmTkHk, 'im')<>ParserGetIntValueByKeyByHandle(qmTkHk, 'lim')) then
begin
   ParserSetIntValueByKeyByHandle(qmTkHk, 'lcc', ParserGetIntValueByKeyByHandle(qmTkHk, 'cc'));
   ParserSetIntValueByKeyByHandle(qmTkHk, 'lim', ParserGetIntValueByKeyByHandle(qmTkHk, 'im'));
   qmLog('hooks cc='+IntToStr(ParserGetIntValueByKeyByHandle(qmTkHk, 'cc'))+' im='+IntToStr(ParserGetIntValueByKeyByHandle(qmTkHk, 'im'))+' booted by '+ParserGetValueByKeyByHandle(qmTkRt, 'hook'));
end;
if (ParserGetIntValueByKeyByHandle(qmTkRt, 'busy')=1) then
exit;
//! Options accepted in the manager window (qmUiAct optacc sets qm_rt
//! setsave): qmSetSave writes settings.cfg - with this machine's own values
//! of the settings a LAN host decides for the session.
if (ParserGetIntValueByKeyByHandle(qmTkRt, 'setsave')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmTkRt, 'setsave', 0);
   qmTkLong := True;
   StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmSetSave', 0);
end;
//! Create mod / Create about.cfg / Edit game file asked in the manager
//! window (qm_rt mfreq, qmUiAct): qmModFiles writes, and the window, if it
//! is open, is drawn again so its message line says what happened.
if (ParserGetValueByKeyByHandle(qmTkRt, 'mfreq')<>'') then
begin
   qmTkLong := True;
   StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmModFiles', 0);
   var qmTkMw : Integer = GetGUIElementIndexByNameParent('QmManager', _gui_GetTop);
   if (qmTkMw<>0) then
   if GetGUIElementVisible(qmTkMw) then
   GUIExecuteState('ShowQmManager');
end;
//! The activation check asked in the manager window (qm_rt trq, qmUiAct):
//! qmTrial runs it, qmUiAct `trialdone` acts on the answer, and the window
//! is drawn again. The window showed "Checking..." on the frame before, so
//! the seconds a trial generation takes are not a silent freeze.
if (ParserGetIntValueByKeyByHandle(qmTkRt, 'trq')>ParserGetIntValueByKeyByHandle(qmTkRt, 'trdone')) then
begin
   ParserSetIntValueByKeyByHandle(qmTkRt, 'trdone', ParserGetIntValueByKeyByHandle(qmTkRt, 'trq'));
   qmTkLong := True;
   var qmTkTc : Integer = GetTriggerManagerStateMachineHandle('qm_core');
   StateMachineExecuteState(qmTkTc, 'qmTrial', 0);
   ParserSetValueByKeyByHandle(ParserSelectByKey('qm_ui'), 'cmd', 'trialdone');
   StateMachineExecuteState(qmTkTc, 'qmUiAct', 0);
   var qmTkTw : Integer = GetGUIElementIndexByNameParent('QmManager', _gui_GetTop);
   if (qmTkTw<>0) then
   if GetGUIElementVisible(qmTkTw) then
   GUIExecuteState('ShowQmManager');
end;
//! Settings of `host` scope in a LAN room (docs/authoring.md): the host
//! sends its values about once a second while the room is open
//! (qmHostSend); a client takes them as each message comes - the OnLanEvent
//! hook runs qmHostRecv - and gets its own back here once it has left the
//! session (qmSettings reads settings.cfg again, which never holds the
//! host's values: qmSetSave).
var qmTkLm : Integer = GetLanMode;
if (qmTkLm>=gc_lanmode_server) and (LanGetClientsCount>1) then
begin
   if (Floor(_misc_GetRealTime*10)>=ParserGetIntValueByKeyByHandle(qmTkRt, 'hsnext')) then
   begin
      ParserSetIntValueByKeyByHandle(qmTkRt, 'hsnext', Floor(_misc_GetRealTime*10)+10);
      StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmHostSend', 0);
   end;
end
else
if (qmTkLm=0) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'hostin')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmTkRt, 'hostin', 0);
   ParserSetValueByKeyByHandle(qmTkRt, 'hssig', '');
   var qmTkHo : Integer = ParserSelectByKey('qm_hostown');
   if (qmTkHo<>0) then
   ParserClearByHandle(qmTkHo);
   StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmSettings', 0);
   qmLog('tick: the LAN session is over; the settings of this machine are back');
end;
//! A trial generation takes seconds, and a click can come before the next
//! frame: the heartbeat says when this run ended, so qmPump does not take
//! the time the work took for a tick that stopped.
if (qmTkLong) and (not qmTkPump) then
ParserSetIntValueByKeyByHandle(qmTkRt, 'tkat', Floor(_misc_GetRealTime*10));
if (ParserGetIntValueByKeyByHandle(qmTkRt, 'tick')=0) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'uiapply')=0) then
exit;
var qmTkCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
var qmTkNow : Integer = Floor(_misc_GetRealTime*10);
if (ParserGetIntValueByKeyByHandle(qmTkRt, 'confirm')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmTkRt, 'confirm', 0);
   var qmTkSt : Integer = ParserSelectByKey('qm_state');
   if (qmTkSt<>0) then
   if (ParserGetValueByKeyByHandle(qmTkSt, 'phase')='booting') then
   begin
      ParserSetValueByKeyByHandle(qmTkSt, 'phase', 'booted');
      StateMachineExecuteState(qmTkCore, 'qmMarkerSave', 0);
      qmLog('tick: the start reached the main menu; marker booted');
      if (ParserGetIntValueByKeyByHandle(qmTkRt, 'rsdue')<qmTkNow+11) then
      ParserSetIntValueByKeyByHandle(qmTkRt, 'rsdue', qmTkNow+11);
   end;
end;
if (ParserGetIntValueByKeyByHandle(qmTkRt, 'uiapply')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmTkRt, 'uiapply', 0);
   qmLog('tick: running the Apply of the manager window, seq='+IntToStr(ParserGetIntValueByKeyByHandle(qmTkRt, 'uiapplyseq')));
   ParserSetValueByKeyByHandle(qmTkRt, 'runmode', 'apply');
   StateMachineExecuteState(qmTkCore, 'qmBoot', 0);
   ParserSetValueByKeyByHandle(qmTkRt, 'runmode', '');
   qmTkNow := Floor(_misc_GetRealTime*10);
   if (not qmTkPump) then
   ParserSetIntValueByKeyByHandle(qmTkRt, 'tkat', qmTkNow);
end;
if (ParserGetIntValueByKeyByHandle(qmTkRt, 'rs')=1) and (not qmTkPump) then
begin
   var qmTkDue : Integer = ParserGetIntValueByKeyByHandle(qmTkRt, 'rsdue');
   if (qmTkNow>qmTkDue+600) then
   begin
      ParserSetIntValueByKeyByHandle(qmTkRt, 'rs', 0);
      ParserSetIntValueByKeyByHandle(qmTkRt, 'rsnote', 0);
      qmLog('tick: restart dropped, it waited '+IntToStr(qmTkNow-qmTkDue)+' tenths past its time; the changes load at the next start');
   end
   else
   if (gMap.gamestage=gc_map_gamestage_none) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'sync')=0) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'rsnote')=0) then
   begin
      //! The notice first; the restart comes on a later frame.
      ParserSetIntValueByKeyByHandle(qmTkRt, 'rsnote', qmTkNow);
      if (qmTkUi<>0) then
      if (ParserGetIntValueByKeyByHandle(qmTkUi, 'ready')=1) then
      begin
         ParserSetIntValueByKeyByHandle(qmTkUi, 'mode', 2);
         GUIExecuteState('ShowQmManager');
      end;
      qmLog('tick: restart notice shown, the restart is due in '+IntToStr(qmTkDue-qmTkNow)+' tenths');
   end
   else
   if (qmTkNow>=qmTkDue) and (qmTkNow>ParserGetIntValueByKeyByHandle(qmTkRt, 'rsnote')) and (gMap.gamestage=gc_map_gamestage_none) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'sync')=0) then
   begin
      ParserSetIntValueByKeyByHandle(qmTkRt, 'rs', 2);
      qmLog('restart now kind='+ParserGetValueByKeyByHandle(qmTkRt, 'rskind')+' why='+ParserGetValueByKeyByHandle(qmTkRt, 'rswhy')+' '+IntToStr(qmTkNow-qmTkDue+11)+' tenths after the last write');
      StateMachineExecuteState(qmTkCore, 'qmRestart', 0);
   end;
end;
if (ParserGetIntValueByKeyByHandle(qmTkRt, 'confirm')=0) and (ParserGetIntValueByKeyByHandle(qmTkRt, 'rs')<>1) then
ParserSetIntValueByKeyByHandle(qmTkRt, 'tick', 0);
