state: qmCaseData
into: data/quartermaster/selftest.aix
helpers: qmlog, qmstr, qmraw
requires:
---
//! SelfTest case `data` (Phase B, M9): what the game itself reads of the two
//! data files the fixtures QMTestData* change, through the engine's parser
//! and the mod overlay (.\data\...), the way the loaders read them
//! (init.script:9-11 formations, country.script:4113-4120 objcustom). Run in
//! every life; each writes <case>_<boot>.txt, so the life after the merge's
//! restart shows the merged files in effect.
//! Dump lines (tools/m9cases.py checks them):
//!   life|<boot>|regen=<0/1>|restart=<0/1>
//!   formations|<count>|<QMDATAA present>|<QMDATAB present>|<QMDATAA0..5 present>|<QMDATAB0..5 present>
//!   objcustom|<count>|<ausbar Decal scale>|<swetem Decal scale>
var qmCdRt : Integer = ParserSelectByKey('qm_case_rt');
var qmCdOut : String = ParserGetValueByKeyByHandle(qmCdRt, 'out');
var qmCdSt : Integer = ParserSelectByKey('qm_state');
var qmCdG : Integer = ParserSelectByKey('qm_guard');
var qmCdBoot : String = IntToStr(ParserGetIntValueByKeyByHandle(qmCdSt, 'boots'));
var qmCdDump : String = '';
var qmCdP : Integer;
var qmCdN : Integer;
var qmCdI : Integer;
var qmCdK : Integer;
var qmCdC : Integer;
var qmCdId : String;
var qmCdA : Integer = 0;
var qmCdB : Integer = 0;
var qmCdA6 : Integer = 0;
var qmCdB6 : Integer = 0;
var qmCdSa : String = '-';
var qmCdSb : String = '-';
var qmCdD : Integer;

procedure qmCdPut(const qmCpLine : String);
begin
   qmCdDump := qmCdDump+qmCpLine+'~013~010';
   qmRawWriteStr(qmCdOut, qmCdDump);
   qmLog('data case '+qmCpLine);
end;

qmCdOut := SubStr(qmCdOut, 1, StrLength(qmCdOut)-4)+'_'+qmCdBoot+'.txt';
qmCdPut('life|'+qmCdBoot+'|regen='+IntToStr(ParserGetIntValueByKeyByHandle(qmCdG, 'regen'))+'|restart='+IntToStr(ParserGetIntValueByKeyByHandle(qmCdG, 'restart')));
qmCdP := ParserSelectByKey('qm_case_data');
if (qmCdP=0) then
qmCdP := ParserCreate('qm_case_data');
ParserClearByHandle(qmCdP);
ParserLoadFromFileByHandle(qmCdP, '.\data\game\var\formations.cfg');
qmCdN := ParserGetCountByHandle(qmCdP);
for qmCdI:=0 to qmCdN-1 do
begin
   qmCdC := ParserSelectByHandleByIndex(qmCdP, qmCdI);
   qmCdId := ParserGetValueByKeyByHandle(qmCdC, 'id');
   if (qmCdId='QMDATAA') then
   qmCdA := 1;
   if (qmCdId='QMDATAB') then
   qmCdB := 1;
   for qmCdK:=0 to 5 do
   begin
      if (qmCdId='QMDATAA'+IntToStr(qmCdK)) then
      qmCdA6 := qmCdA6+1;
      if (qmCdId='QMDATAB'+IntToStr(qmCdK)) then
      qmCdB6 := qmCdB6+1;
   end;
end;
qmCdPut('formations|'+IntToStr(qmCdN)+'|'+IntToStr(qmCdA)+'|'+IntToStr(qmCdB)+'|'+IntToStr(qmCdA6)+'|'+IntToStr(qmCdB6));
ParserClearByHandle(qmCdP);
ParserLoadFromFileByHandle(qmCdP, '.\data\game\var\objcustom.cfg');
qmCdN := ParserGetCountByHandle(qmCdP);
for qmCdI:=0 to qmCdN-1 do
begin
   qmCdC := ParserSelectByHandleByIndex(qmCdP, qmCdI);
   qmCdId := ParserGetValueByKeyByHandle(qmCdC, 'sid');
   if (qmCdId='ausbar') or (qmCdId='swetem') then
   begin
      qmCdD := ParserSelectByHandleByKey(qmCdC, 'Decal');
      if (qmCdD<>0) then
      begin
         if (qmCdId='ausbar') then
         qmCdSa := ParserGetValueByKeyByHandle(qmCdD, 'scale');
         if (qmCdId='swetem') then
         qmCdSb := ParserGetValueByKeyByHandle(qmCdD, 'scale');
      end;
   end;
end;
qmCdPut('objcustom|'+IntToStr(qmCdN)+'|'+qmCdSa+'|'+qmCdSb);
ParserClearByHandle(qmCdP);
ParserSetValueByKeyByHandle(qmCdRt, 'status', 'ok');
