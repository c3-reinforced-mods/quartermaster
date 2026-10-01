state: qmUiApply
into: data/quartermaster/core.aix
helpers: qmlog
requires:
---
//! Apply, after the player confirmed it: the intended activation of every
//! row and the pending load order go into the runtime parser qm_rt. qmTick
//! (src/states/qmrestarttick.pas, run by the DoProgress hook) picks it up on
//! the next main-menu frame and runs qmBoot with runmode = apply: mods.ini
//! with these flags and this order (written only when its content differs,
//! plan S8), a generation for the mods the next start loads, and the
//! restart. This state writes no file itself: mods.ini belongs to modman and
//! to that one writer. docs/ui.md owns the key list.
//!
//! A change is an activation that differs from what the game loaded, or a
//! load order that differs from the one it loaded (qm_ui ordchg,
//! decided 2026-09-28). The order vector uiapplyord<k> is written with every Apply;
//! the boot's qmOrder takes it only when uiapplyorder is 1.
//!
//! qm_rt is never created here. The CameraControl hook creates it once per
//! process and uses its absence as the "boot has not run yet" flag (plan S5),
//! so a parser made by the window would silence the boot.
var qmUpUi : Integer = ParserSelectByKey('qm_ui');
var qmUpRt : Integer = ParserSelectByKey('qm_rt');
if (qmUpUi=0) then
exit;
if (qmUpRt=0) then
begin
   // Message when the boot never ran.
   ParserSetValueByKeyByHandle(qmUpUi, 'msg', 'Not applied: Quartermaster did not start in this session.');
   qmLog('ui apply not recorded: qm_rt is missing, the boot has not run');
   exit;
end;
var qmUpN : Integer = ParserGetIntValueByKeyByHandle(qmUpUi, 'n');
var qmUpOrd : Integer = ParserGetIntValueByKeyByHandle(qmUpUi, 'ordchg');
var qmUpI : Integer;
var qmUpS : String;
var qmUpChg : Integer = 0;
for qmUpI:=0 to qmUpN-1 do
begin
   qmUpS := IntToStr(qmUpI);
   if (ParserGetIntValueByKeyByHandle(qmUpUi, 'pe'+qmUpS)<>ParserGetIntValueByKeyByHandle(qmUpUi, 'en'+qmUpS)) then
   qmUpChg := qmUpChg+1;
end;
if (qmUpChg=0) and (qmUpOrd<>1) then
begin
   // Message when there is nothing to apply.
   ParserSetValueByKeyByHandle(qmUpUi, 'msg', 'Nothing to apply.');
   qmLog('ui apply: no change');
   exit;
end;
var qmUpSeq : Integer = ParserGetIntValueByKeyByHandle(qmUpRt, 'uiapplyseq')+1;
var qmUpWas : Integer;
var qmUpNow : Integer;
ParserSetIntValueByKeyByHandle(qmUpRt, 'uiapplyn', qmUpN);
for qmUpI:=0 to qmUpN-1 do
begin
   qmUpS := IntToStr(qmUpI);
   // dis as mods.ini spells it: 1 = off. en/pe in qm_ui are 1 = on.
   qmUpWas := 1-ParserGetIntValueByKeyByHandle(qmUpUi, 'en'+qmUpS);
   qmUpNow := 1-ParserGetIntValueByKeyByHandle(qmUpUi, 'pe'+qmUpS);
   ParserSetValueByKeyByHandle(qmUpRt, 'uiapplydir'+qmUpS, ParserGetValueByKeyByHandle(qmUpUi, 'dir'+qmUpS));
   ParserSetIntValueByKeyByHandle(qmUpRt, 'uiapplydis'+qmUpS, qmUpNow);
   if (qmUpWas<>qmUpNow) then
   qmLog('ui apply change seq='+IntToStr(qmUpSeq)+' row='+qmUpS+' dis='+IntToStr(qmUpWas)+'->'+IntToStr(qmUpNow)+' dir='+ParserGetValueByKeyByHandle(qmUpUi, 'dir'+qmUpS));
end;
//! The pending load order, every row, as the dirs ModLibraryGetData returns.
var qmUpLine : String = '';
ParserSetIntValueByKeyByHandle(qmUpRt, 'uiapplyordn', qmUpN);
for qmUpI:=0 to qmUpN-1 do
begin
   qmUpS := ParserGetValueByKeyByHandle(qmUpUi, 'dir'+IntToStr(ParserGetIntValueByKeyByHandle(qmUpUi, 'ord'+IntToStr(qmUpI))));
   ParserSetValueByKeyByHandle(qmUpRt, 'uiapplyord'+IntToStr(qmUpI), qmUpS);
   if (qmUpLine<>'') then
   qmUpLine := qmUpLine+' | ';
   qmUpLine := qmUpLine+qmUpS;
end;
if (qmUpOrd=1) then
ParserSetIntValueByKeyByHandle(qmUpRt, 'uiapplyorder', 1)
else
ParserSetIntValueByKeyByHandle(qmUpRt, 'uiapplyorder', 0);
ParserSetIntValueByKeyByHandle(qmUpRt, 'uiapplychg', qmUpChg);
ParserSetIntValueByKeyByHandle(qmUpRt, 'uiregen', 1);
ParserSetIntValueByKeyByHandle(qmUpRt, 'uiapplyseq', qmUpSeq);
ParserSetIntValueByKeyByHandle(qmUpRt, 'uiapply', 1);
ParserSetIntValueByKeyByHandle(qmUpUi, 'applies', ParserGetIntValueByKeyByHandle(qmUpUi, 'applies')+1);
// Message after a confirmed Apply. The restart notice shows it
// until the game closes: qmTick regenerates on the next main-menu frame and
// restarts a second later.
ParserSetValueByKeyByHandle(qmUpUi, 'msg', 'Applying the changes: Quartermaster regenerates its files and restarts the game.');
qmLog('ui apply seq='+IntToStr(qmUpSeq)+' changes='+IntToStr(qmUpChg)+' order='+IntToStr(qmUpOrd)+' rows='+IntToStr(qmUpN)+' recorded in qm_rt; qmTick regenerates and restarts');
qmLog('ui apply order: '+qmUpLine);
