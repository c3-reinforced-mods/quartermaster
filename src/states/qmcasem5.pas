state: qmCaseM5
into: data/quartermaster/selftest.aix
helpers: qmlog, qmstr, qmraw, qmbootdir
requires:
---
//! SelfTest case `m5`: the boot milestone's in-game steps (plan G5, G14; the
//! run requests are in tools/m5cases.py, which also checks the dumps).
//! Directives:
//!   step compile   run qmRestart with qm_rt rsdry = 1: it compiles, runs up
//!                  to its first line and returns without restarting - the one
//!                  state a normal boot never runs
//!   step shuffle   (I7) the first life whose boot left the restart chain
//!                  clear (below): Quartermaster's own writer qmModsIni puts
//!                  the canonical rows back with Quartermaster moved to the
//!                  front, then the case asks for a restart of kind `test`;
//!                  a life before it only waits; later lives: what the boot
//!                  found and did
//!   step disable   (I8) first life: qmModsIni writes the canonical rows with
//!                  Quartermaster's dis = True, then a `test` restart; the
//!                  next life runs without Quartermaster, so no [qm] line
//!   new <dir>      (with shuffle) the dir that must be reported new
//!   reverse 1      (with shuffle) the other rows are written in reverse
//!                  order too, so the mods the saved load order places come
//!                  back reordered: the outside reorder the boot must undo
//!                  (plan S11)
//!   step uiorder   (plan S11, the manager's order through its controller) the
//!                  first life whose boot neither generated nor has a restart
//!                  pending: qm_ui commands open, select <mod>, <cmd> (up,
//!                  down, or move to <to>), apply, confirm - run through
//!                  qmUiAct as the window runs them - and the confirmed Apply
//!                  is left in qm_rt for qmTick, which rewrites mods.ini,
//!                  regenerates and restarts; an earlier life only waits, a
//!                  later one reports the load order it booted with
//!   mod <dir>, cmd <up|down|move>, to <k>
//!                  (with uiorder) the row, the command, the Active-list place
//!   step relife    (I1) first life: a test restart, nothing else; the next
//!                  life's boot shows what a start with nothing to do logs
//!   step restart   the case file qm_m5_restart.cfg: its presence lets a
//!                  SelfTest run restart (qmBoot); the case only says so
//!   step unstable  the case file qm_m5_unstable.cfg: the I5 salt is on
//!                  (qmBoot, qmGuard); the case reports the fingerprint
//! The harness never writes mods.ini (the rule for test runs): every change of it
//! in these runs is Quartermaster's own writer, under the same checks as the
//! boot's.
//!
//! The SelfTest runs in every life of a run. What must happen once is marked
//! by a file in the SelfTest's out folder, m5_<step>.done, which the harness
//! collects; each life writes its own dump, m5_<step>_<boot>.txt, so no life
//! overwrites another's. A restart is asked for the way the boot asks
//! (qm_rt rs / rsdue / rskind, qmTick runs it at least 1 s after this last
//! write), and the marker gets rk = test so the next boot knows a restart
//! ended this life.
//!
//! The shuffle must be followed by an automatic restart, and plan S8 allows
//! one per fingerprint in a chain of them; the shuffle keeps the fingerprint
//! (it holds canonical ids and flags, not the order). So the shuffle waits
//! for a life whose boot has no restart of its own pending - the shuffle
//! would undo the boot's rewrite before that restart loads it - and whose
//! marker has rows = rcount = 0, which only a boot that needed no restart
//! leaves: then the next boot's restart is refused neither in-a-row nor
//! per-hash. A freshly deployed mod is listed after Quartermaster, so the
//! first life of I7 reorders and restarts, and the shuffle comes in the
//! second (run m5i7 of 2026-09-28 shuffled in the first and the next boot
//! refused per-hash).
//!
//! Dump lines: step|<step>|<boot>, compile|qmRestart|<0/1>,
//! boot|<why>|<restart kind>|<refused>|<mods.ini action>|<effective>,
//! wait|restart=<0/1>|rows=<k>|rcount=<k>, wrote|<action>|<effective>,
//! row|<k>|<dir>|<dis>, new|<dir>, done|<0/1>; uiorder: order|<src>|
//! <canon>|<ext>|<active dirs in load order, ` | ` between>,
//! wait|regen=<0/1>|restart=<0/1>, ui|<cmd>|<sel>|<omoved>|<ordchg>|<mode>|
//! <uiapply>|<msg>, kept|<uiapply>|<uiapplyorder>|<uiapplyordn>|<uiapplyseq>,
//! apply|<k>|<dir>; and the log gets the same lines after `m5 case `.
var qmC5Rt : Integer = ParserSelectByKey('qm_case_rt');
var qmC5Code : Integer = ParserSelectByHandleByKey(ParserSelectByKey('qm_case'), 'Code');
var qmC5Nd : Integer = ParserGetCountByHandle(qmC5Code);
var qmC5Core : Integer = GetTriggerManagerStateMachineHandle('qm_core');
var qmC5Qrt : Integer = ParserSelectByKey('qm_rt');
var qmC5St : Integer = ParserSelectByKey('qm_state');
var qmC5G : Integer = ParserSelectByKey('qm_guard');
var qmC5Ini : Integer = ParserSelectByKey('qm_ini');
var qmC5In : Integer = ParserSelectByKey('qm_ini_in');
var qmC5Kn : Integer = ParserSelectByKey('qm_known');
var qmC5Mods : Integer = ParserSelectByKey('qm_mods');
var qmC5Dir : String = ParserGetValueByKeyByHandle(qmC5Rt, 'outdir');
var qmC5Boot : String = IntToStr(ParserGetIntValueByKeyByHandle(qmC5St, 'boots'));
var qmC5Step : String = '';
var qmC5Want : String = '';
var qmC5Dump : String = '';
var qmC5Out : String;
var qmC5K : Integer;
var qmC5J : Integer;
var qmC5N : Integer;
var qmC5S : String;
var qmC5T : String;
var qmC5Self : String = '';
var qmC5Ok : Boolean = False;
var qmC5Found : Boolean = False;
var qmC5Wdir : array [0..255] of String;
var qmC5Wdis : array [0..255] of String;
var qmC5Rev : Integer = 0;
var qmC5Mod : String = '';
var qmC5Ocmd : String = 'up';
var qmC5To : Integer = 0;
var qmC5Ui : Integer = 0;

procedure qmC5Put(const qmCpLine : String);
begin
   var qmCpE : String;
   qmEscape(qmCpLine, qmCpE);
   qmC5Dump := qmC5Dump+qmCpE+'~013~010';
   qmRawWriteStr(qmC5Out, qmC5Dump);
   qmLog('m5 case '+qmCpLine);
end;

//! The canonical rows of this boot (qm_ini_in), with Quartermaster's row
//! moved to the front (shuffle) or switched off (disable), into qmModsIni.
procedure qmC5Write(const qmCwHow : String);
begin
   var qmCwN : Integer = ParserGetIntValueByKeyByHandle(qmC5In, 'n');
   var qmCwK : Integer;
   var qmCwJ : Integer;
   var qmCwAt : Integer = -1;
   var qmCwNd : String;
   for qmCwK:=0 to qmCwN-1 do
   begin
      qmC5Wdir[qmCwK] := ParserGetValueByKeyByHandle(qmC5In, 'dir'+IntToStr(qmCwK));
      qmC5Wdis[qmCwK] := ParserGetValueByKeyByHandle(qmC5In, 'dis'+IntToStr(qmCwK));
      qmNormDir(qmC5Wdir[qmCwK], qmCwNd);
      if (qmCwNd=qmC5Self) then
      qmCwAt := qmCwK;
   end;
   if (qmCwAt<0) then
   begin
      qmC5Put('error|Quartermaster''s row is not in qm_ini_in');
      exit;
   end;
   if (qmCwHow='disable') then
   ParserSetValueByKeyByHandle(qmC5In, 'dis'+IntToStr(qmCwAt), 'True')
   else
   if (qmC5Rev=1) then
   begin
      ParserSetValueByKeyByHandle(qmC5In, 'dir0', qmC5Wdir[qmCwAt]);
      ParserSetValueByKeyByHandle(qmC5In, 'dis0', qmC5Wdis[qmCwAt]);
      qmCwJ := 1;
      for qmCwK:=qmCwN-1 downto 0 do
      if (qmCwK<>qmCwAt) then
      begin
         ParserSetValueByKeyByHandle(qmC5In, 'dir'+IntToStr(qmCwJ), qmC5Wdir[qmCwK]);
         ParserSetValueByKeyByHandle(qmC5In, 'dis'+IntToStr(qmCwJ), qmC5Wdis[qmCwK]);
         qmCwJ := qmCwJ+1;
      end;
   end
   else
   begin
      ParserSetValueByKeyByHandle(qmC5In, 'dir0', qmC5Wdir[qmCwAt]);
      ParserSetValueByKeyByHandle(qmC5In, 'dis0', qmC5Wdis[qmCwAt]);
      for qmCwK:=0 to qmCwAt-1 do
      begin
         ParserSetValueByKeyByHandle(qmC5In, 'dir'+IntToStr(qmCwK+1), qmC5Wdir[qmCwK]);
         ParserSetValueByKeyByHandle(qmC5In, 'dis'+IntToStr(qmCwK+1), qmC5Wdis[qmCwK]);
      end;
   end;
   StateMachineExecuteState(qmC5Core, 'qmModsIni', 0);
   qmC5Put('wrote|'+ParserGetValueByKeyByHandle(qmC5Ini, 'action')+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Ini, 'effective')));
   for qmCwK:=0 to qmCwN-1 do
   qmC5Put('row|'+IntToStr(qmCwK)+'|'+ParserGetValueByKeyByHandle(qmC5In, 'dir'+IntToStr(qmCwK))+'|'+ParserGetValueByKeyByHandle(qmC5In, 'dis'+IntToStr(qmCwK)));
end;

//! A restart of kind test, asked for the way qmBoot asks.
procedure qmC5Restart(const qmCrWhy : String);
begin
   ParserSetValueByKeyByHandle(qmC5St, 'rk', 'test');
   StateMachineExecuteState(qmC5Core, 'qmMarkerSave', 0);
   ParserSetIntValueByKeyByHandle(qmC5Qrt, 'rs', 1);
   ParserSetIntValueByKeyByHandle(qmC5Qrt, 'rsdue', Floor(_misc_GetRealTime*10)+11);
   ParserSetValueByKeyByHandle(qmC5Qrt, 'rskind', 'test');
   ParserSetValueByKeyByHandle(qmC5Qrt, 'rswhy', qmCrWhy);
   ParserSetIntValueByKeyByHandle(qmC5Qrt, 'tick', 1);
   qmC5Put('restart|test|'+qmCrWhy);
end;

//! One command of the manager's controller, as its event state sends it.
procedure qmC5Cmd(const qmCcCmd : String; const qmCcArg : Integer; const qmCcTo : Integer);
begin
   ParserSetValueByKeyByHandle(qmC5Ui, 'cmd', qmCcCmd);
   ParserSetIntValueByKeyByHandle(qmC5Ui, 'arg', qmCcArg);
   ParserSetIntValueByKeyByHandle(qmC5Ui, 'argside', 1);
   ParserSetIntValueByKeyByHandle(qmC5Ui, 'argto', qmCcTo);
   ParserSetValueByKeyByHandle(qmC5Ui, 'argtext', '');
   ParserSetIntValueByKeyByHandle(qmC5Ui, 'omoved', 0);
   StateMachineExecuteState(qmC5Core, 'qmUiAct', 0);
   qmC5Put('ui|'+qmCcCmd+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Ui, 'sel'))+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Ui, 'omoved'))+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Ui, 'ordchg'))+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Ui, 'mode'))+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Qrt, 'uiapply'))+'|'+ParserGetValueByKeyByHandle(qmC5Ui, 'msg'));
end;

//! The load order this boot left in qm_mods, the active mods only.
procedure qmC5Order;
begin
   var qmCoOrd : Integer = ParserSelectByKey('qm_order');
   var qmCoLine : String = '';
   var qmCoK : Integer;
   var qmCoI : Integer;
   for qmCoK:=0 to ParserGetIntValueByKeyByHandle(qmC5Mods, 'n')-1 do
   begin
      qmCoI := ParserGetIntValueByKeyByHandle(qmC5Mods, 'ord'+IntToStr(qmCoK));
      if (ParserGetIntValueByKeyByHandle(qmC5Mods, 'on'+IntToStr(qmCoI))=1) then
      begin
         if (qmCoLine<>'') then
         qmCoLine := qmCoLine+' | ';
         qmCoLine := qmCoLine+ParserGetValueByKeyByHandle(qmC5Mods, 'dir'+IntToStr(qmCoI));
      end;
   end;
   qmC5Put('order|'+ParserGetValueByKeyByHandle(qmCoOrd, 'src')+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmCoOrd, 'canon'))+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmCoOrd, 'ext'))+'|'+qmCoLine);
end;

for qmC5K:=0 to qmC5Nd-1 do
begin
   qmC5S := ParserGetValueByIndexByHandle(qmC5Code, qmC5K);
   if (SubStr(qmC5S, 1, 6)=';step ') then
   qmC5Step := SubStr(qmC5S, 7, StrLength(qmC5S)-6);
   if (SubStr(qmC5S, 1, 5)=';new ') then
   qmC5Want := SubStr(qmC5S, 6, StrLength(qmC5S)-5);
   if (qmC5S=';reverse 1') then
   qmC5Rev := 1;
   if (SubStr(qmC5S, 1, 5)=';mod ') then
   qmC5Mod := SubStr(qmC5S, 6, StrLength(qmC5S)-5);
   if (SubStr(qmC5S, 1, 5)=';cmd ') then
   qmC5Ocmd := SubStr(qmC5S, 6, StrLength(qmC5S)-5);
   if (SubStr(qmC5S, 1, 4)=';to ') then
   qmC5To := StrToInt(SubStr(qmC5S, 5, StrLength(qmC5S)-4));
end;
qmC5Out := qmC5Dir+'m5_'+qmC5Step+'_'+qmC5Boot+'.txt';
if (ParserGetIntValueByKeyByHandle(qmC5Mods, 'self')>=0) then
qmNormDir(ParserGetValueByKeyByHandle(qmC5Mods, 'dir'+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Mods, 'self'))), qmC5Self);
qmC5Put('step|'+qmC5Step+'|'+qmC5Boot);
qmC5Put('boot|'+ParserGetValueByKeyByHandle(qmC5G, 'why')+'|'+ParserGetValueByKeyByHandle(qmC5G, 'kind')+'|'+ParserGetValueByKeyByHandle(qmC5G, 'refused')+'|'+ParserGetValueByKeyByHandle(qmC5Ini, 'action')+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Ini, 'effective')));
qmC5N := ParserGetIntValueByKeyByHandle(qmC5Kn, 'newn');
for qmC5K:=0 to qmC5N-1 do
qmC5Put('new|'+ParserGetValueByKeyByHandle(qmC5Kn, 'new'+IntToStr(qmC5K)));
if (qmC5Step='compile') then
begin
   ParserSetIntValueByKeyByHandle(qmC5Qrt, 'rsdryok', 0);
   ParserSetIntValueByKeyByHandle(qmC5Qrt, 'rsdry', 1);
   StateMachineExecuteState(qmC5Core, 'qmRestart', 0);
   ParserSetIntValueByKeyByHandle(qmC5Qrt, 'rsdry', 0);
   qmC5Ok := (ParserGetIntValueByKeyByHandle(qmC5Qrt, 'rsdryok')=1);
   qmC5Put('compile|qmRestart|'+BoolToStr(qmC5Ok));
end
else
if (qmC5Step='shuffle') or (qmC5Step='disable') then
begin
   var qmC5Done : String = qmC5Dir+'m5_'+qmC5Step+'.done';
   var qmC5Clear : Boolean = (ParserGetIntValueByKeyByHandle(qmC5G, 'restart')=0) and (ParserGetIntValueByKeyByHandle(qmC5St, 'rows')=0) and (ParserGetIntValueByKeyByHandle(qmC5St, 'rcount')=0);
   if (FileAge(qmC5Done)=-1) and (qmC5Step='shuffle') and (not qmC5Clear) then
   begin
      qmC5Put('wait|restart='+IntToStr(ParserGetIntValueByKeyByHandle(qmC5G, 'restart'))+'|rows='+IntToStr(ParserGetIntValueByKeyByHandle(qmC5St, 'rows'))+'|rcount='+IntToStr(ParserGetIntValueByKeyByHandle(qmC5St, 'rcount')));
      qmC5Ok := True;
   end
   else
   if (FileAge(qmC5Done)=-1) then
   begin
      qmC5Write(qmC5Step);
      qmC5Ok := (ParserGetValueByKeyByHandle(qmC5Ini, 'action')='written') and ((qmC5Step='disable') or (ParserGetIntValueByKeyByHandle(qmC5Ini, 'effective')=1));
      if (qmC5Ok) then
      begin
         qmRawWriteStr(qmC5Done, qmC5Step+'|'+qmC5Boot+'~013~010');
         qmC5Restart('selftest-'+qmC5Step);
      end;
   end
   else
   if (qmC5Step='disable') then
   qmC5Put('error|Quartermaster ran although the disable step switched it off')
   else
   begin
      //! A later life of the shuffle: done once the running game loaded the
      //! canonical order again (mods.ini already so: same, not effective) and
      //! the wanted dir is reported new.
      qmNormDir(qmC5Want, qmC5T);
      for qmC5K:=0 to qmC5N-1 do
      begin
         qmNormDir(ParserGetValueByKeyByHandle(qmC5Kn, 'new'+IntToStr(qmC5K)), qmC5S);
         if (qmC5S=qmC5T) then
         qmC5Found := True;
      end;
      qmC5Ok := True;
      if (ParserGetValueByKeyByHandle(qmC5Ini, 'action')='same') and (ParserGetIntValueByKeyByHandle(qmC5Ini, 'effective')=0) and ((qmC5Want='') or (qmC5Found)) then
      begin
         qmC5Put('done|1');
         qmLog('m5 i7 done: canonical order loaded, new='+qmC5Want);
      end
      else
      qmC5Put('done|0');
   end;
end
else
if (qmC5Step='uiorder') then
begin
   qmC5Ok := True;
   qmC5Order;
   if (FileAge(qmC5Dir+'m5_uiorder.done')<>-1) then
   begin
      //! A later life: loaded with the order the Apply saved, not canonical,
      //! mods.ini already so (same, not effective).
      if (ParserGetValueByKeyByHandle(ParserSelectByKey('qm_order'), 'src')='saved') and (ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_order'), 'canon')=0) and (ParserGetValueByKeyByHandle(qmC5Ini, 'action')='same') and (ParserGetIntValueByKeyByHandle(qmC5Ini, 'effective')=0) then
      begin
         qmC5Put('done|1');
         qmLog('m5 uiorder done: the saved load order loaded');
      end
      else
      qmC5Put('done|0');
   end
   else
   if (ParserGetIntValueByKeyByHandle(qmC5G, 'regen')=1) or (ParserGetIntValueByKeyByHandle(qmC5G, 'restart')=1) then
   qmC5Put('wait|regen='+IntToStr(ParserGetIntValueByKeyByHandle(qmC5G, 'regen'))+'|restart='+IntToStr(ParserGetIntValueByKeyByHandle(qmC5G, 'restart')))
   else
   begin
      var qmC5Row : Integer = -1;
      qmC5Ui := ParserSelectByKey('qm_ui');
      if (qmC5Ui=0) then
      qmC5Ui := ParserCreate('qm_ui');
      qmC5Cmd('open', 0, 0);
      qmNormDir(qmC5Mod, qmC5T);
      for qmC5K:=0 to ParserGetIntValueByKeyByHandle(qmC5Ui, 'n')-1 do
      begin
         qmNormDir(ParserGetValueByKeyByHandle(qmC5Ui, 'dir'+IntToStr(qmC5K)), qmC5S);
         if (qmC5S=qmC5T) and (qmC5Row<0) then
         qmC5Row := qmC5K;
      end;
      if (qmC5Row<0) then
      begin
         qmC5Put('error|no row for '+qmC5Mod);
         qmC5Ok := False;
      end
      else
      begin
         qmC5Cmd('select', qmC5Row, 0);
         qmC5Cmd(qmC5Ocmd, qmC5Row, qmC5To);
         qmC5Cmd('apply', 0, 0);
         qmC5Cmd('confirm', 0, 0);
         qmC5N := ParserGetIntValueByKeyByHandle(qmC5Qrt, 'uiapplyordn');
         qmC5Put('kept|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Qrt, 'uiapply'))+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Qrt, 'uiapplyorder'))+'|'+IntToStr(qmC5N)+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Qrt, 'uiapplyseq')));
         for qmC5K:=0 to qmC5N-1 do
         qmC5Put('apply|'+IntToStr(qmC5K)+'|'+ParserGetValueByKeyByHandle(qmC5Qrt, 'uiapplyord'+IntToStr(qmC5K)));
         qmC5Ok := (ParserGetIntValueByKeyByHandle(qmC5Qrt, 'uiapply')=1) and (ParserGetIntValueByKeyByHandle(qmC5Qrt, 'uiapplyorder')=1);
         if (qmC5Ok) then
         qmRawWriteStr(qmC5Dir+'m5_uiorder.done', 'uiorder|'+qmC5Boot+'~013~010');
      end;
   end;
end
else
if (qmC5Step='relife') then
begin
   //! I1: one more life, so the next boot can show that it finds nothing to
   //! do. The first life asks for a test restart; later lives only report.
   qmC5Ok := True;
   if (FileAge(qmC5Dir+'m5_relife.done')=-1) then
   begin
      qmRawWriteStr(qmC5Dir+'m5_relife.done', 'relife|'+qmC5Boot+'~013~010');
      qmC5Restart('selftest-relife');
   end;
end
else
if (qmC5Step='restart') or (qmC5Step='unstable') then
begin
   qmC5Put('switch|'+qmC5Step+'|norestart='+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Qrt, 'norestart'))+'|unstable='+IntToStr(ParserGetIntValueByKeyByHandle(qmC5Qrt, 'unstable'))+'|fp='+ParserGetValueByKeyByHandle(qmC5Qrt, 'fp'));
   qmC5Ok := True;
end
else
qmC5Put('error|unknown step '+qmC5Step);
if (qmC5Ok) then
ParserSetValueByKeyByHandle(qmC5Rt, 'status', 'ok')
else
ParserSetValueByKeyByHandle(qmC5Rt, 'status', 'fail');
