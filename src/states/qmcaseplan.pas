state: qmCasePlan
into: data/quartermaster/selftest.aix
helpers: qmstr, qmraw
requires:
---
//! SelfTest case `plan`: runs the boot pipeline again (mod list, index,
//! plan, fingerprint - the states of core.aix, in its manager qm_core) and
//! dumps the named parsers they filled. ref/selftest.py plan_check recomputes
//! every line from the mod rows and the files on disk. Strings that come from
//! the engine or a mod are in hex.
//!
//!   mod|i|pos|on|origin|dir|tag|last|title|FileAge of mod.ini
//!   self|i
//!   scan|paths|FileAge calls
//!   idx|path|provider positions|their FileAge   (paths with a provider)
//!   stamp|pos|stamp                              (scanned mods)
//!   vage|path|FileAge of the vanilla copy        (paths with a provider)
//!   exe|FileAge of cossacks.exe
//!   vstamp|stamp
//!   plan|path|action|strategy|reason|winner|providers
//!   fpl|line in hex
//!   fp|hash
//!   fresh|rows registered at this start (qm_known fr<i>, `;` between; - none)
//!   fpold|the hash without them (qm_fp old: the loop rule's exception)
var qmCpRt : Integer = ParserSelectByKey('qm_case_rt');
var qmCpOut : String = ParserGetValueByKeyByHandle(qmCpRt, 'out');
var qmCpCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
StateMachineExecuteState(qmCpCore, 'qmModList', 0);
StateMachineExecuteState(qmCpCore, 'qmIndex', 0);
StateMachineExecuteState(qmCpCore, 'qmPlan', 0);
StateMachineExecuteState(qmCpCore, 'qmFingerprint', 0);
var qmCpMods : Integer = ParserSelectByKey('qm_mods');
var qmCpIdx : Integer = ParserSelectByKey('qm_index');
var qmCpPlan : Integer = ParserSelectByKey('qm_plan');
var qmCpFp : Integer = ParserSelectByKey('qm_fp');
var qmCpDump : String = '';
var qmCpN : Integer;
var qmCpK : Integer;
var qmCpI : Integer;
var qmCpA : String;
var qmCpB : String;
var qmCpC : String;
var qmCpD : String;
var qmCpE : String;
var qmCpV : String;
qmCpN := ParserGetIntValueByKeyByHandle(qmCpMods, 'n');
for qmCpI:=0 to qmCpN-1 do
begin
   qmHex(ParserGetValueByKeyByHandle(qmCpMods, 'dir'+IntToStr(qmCpI)), qmCpA);
   qmHex(ParserGetValueByKeyByHandle(qmCpMods, 'tag'+IntToStr(qmCpI)), qmCpB);
   qmHex(ParserGetValueByKeyByHandle(qmCpMods, 'last'+IntToStr(qmCpI)), qmCpC);
   qmHex(ParserGetValueByKeyByHandle(qmCpMods, 'tit'+IntToStr(qmCpI)), qmCpD);
   qmCpDump := qmCpDump+'mod|'+IntToStr(qmCpI)+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmCpMods, 'pos'+IntToStr(qmCpI)))+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmCpMods, 'on'+IntToStr(qmCpI)))+'|'+ParserGetValueByKeyByHandle(qmCpMods, 'org'+IntToStr(qmCpI))+'|'+qmCpA+'|'+qmCpB+'|'+qmCpC+'|'+qmCpD+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmCpMods, 'ini'+IntToStr(qmCpI)))+'~013~010';
end;
qmCpDump := qmCpDump+'self|'+IntToStr(ParserGetIntValueByKeyByHandle(qmCpMods, 'self'))+'~013~010';
qmCpN := ParserGetIntValueByKeyByHandle(qmCpIdx, 'n');
qmCpDump := qmCpDump+'scan|'+IntToStr(qmCpN)+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmCpIdx, 'calls'))+'~013~010';
for qmCpK:=0 to qmCpN-1 do
begin
   qmCpV := ParserGetValueByKeyByHandle(qmCpIdx, 'v'+IntToStr(qmCpK));
   if (qmCpV<>'-') then
   begin
      qmEscape(ParserGetValueByKeyByHandle(qmCpIdx, 'p'+IntToStr(qmCpK)), qmCpE);
      qmCpDump := qmCpDump+'idx|'+qmCpE+'|'+qmCpV+'|'+ParserGetValueByKeyByHandle(qmCpIdx, 'a'+IntToStr(qmCpK))+'~013~010';
   end;
end;
qmCpN := ParserGetIntValueByKeyByHandle(qmCpMods, 'en');
for qmCpK:=0 to qmCpN-1 do
begin
   qmCpI := ParserGetIntValueByKeyByHandle(qmCpMods, 'pos'+IntToStr(ParserGetIntValueByKeyByHandle(qmCpMods, 'e'+IntToStr(qmCpK))));
   qmCpDump := qmCpDump+'stamp|'+IntToStr(qmCpI)+'|'+ParserGetValueByKeyByHandle(qmCpIdx, 'st'+IntToStr(qmCpI))+'~013~010';
end;
qmCpN := ParserGetIntValueByKeyByHandle(qmCpIdx, 'n');
for qmCpK:=0 to qmCpN-1 do
if (ParserGetValueByKeyByHandle(qmCpIdx, 'v'+IntToStr(qmCpK))<>'-') then
begin
   qmEscape(ParserGetValueByKeyByHandle(qmCpIdx, 'p'+IntToStr(qmCpK)), qmCpE);
   qmCpDump := qmCpDump+'vage|'+qmCpE+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmCpIdx, 'va'+IntToStr(qmCpK)))+'~013~010';
end;
qmCpDump := qmCpDump+'exe|'+IntToStr(ParserGetIntValueByKeyByHandle(qmCpIdx, 'exe'))+'~013~010';
qmCpDump := qmCpDump+'vstamp|'+ParserGetValueByKeyByHandle(qmCpIdx, 'vstamp')+'~013~010';
qmCpN := ParserGetIntValueByKeyByHandle(qmCpPlan, 'n');
for qmCpK:=0 to qmCpN-1 do
begin
   qmEscape(ParserGetValueByKeyByHandle(qmCpPlan, 'path'+IntToStr(qmCpK)), qmCpE);
   qmCpDump := qmCpDump+'plan|'+qmCpE+'|'+ParserGetValueByKeyByHandle(qmCpPlan, 'act'+IntToStr(qmCpK))+'|'+ParserGetValueByKeyByHandle(qmCpPlan, 'str'+IntToStr(qmCpK))+'|'+ParserGetValueByKeyByHandle(qmCpPlan, 'why'+IntToStr(qmCpK))+'|'+ParserGetValueByKeyByHandle(qmCpPlan, 'win'+IntToStr(qmCpK))+'|'+ParserGetValueByKeyByHandle(qmCpPlan, 'prov'+IntToStr(qmCpK))+'~013~010';
end;
qmCpN := ParserGetIntValueByKeyByHandle(qmCpFp, 'n');
for qmCpK:=0 to qmCpN-1 do
begin
   qmHex(ParserGetValueByKeyByHandle(qmCpFp, 'l'+IntToStr(qmCpK)), qmCpA);
   qmCpDump := qmCpDump+'fpl|'+qmCpA+'~013~010';
end;
qmCpDump := qmCpDump+'fp|'+ParserGetValueByKeyByHandle(qmCpFp, 'hash')+'~013~010';
var qmCpKn : Integer = ParserSelectByKey('qm_known');
qmCpA := '';
if (qmCpKn<>0) then
for qmCpI:=0 to ParserGetIntValueByKeyByHandle(qmCpMods, 'n')-1 do
if (ParserGetIntValueByKeyByHandle(qmCpKn, 'fr'+IntToStr(qmCpI))=1) then
begin
   if (qmCpA<>'') then
   qmCpA := qmCpA+';';
   qmCpA := qmCpA+IntToStr(qmCpI);
end;
if (qmCpA='') then
qmCpA := '-';
qmCpDump := qmCpDump+'fresh|'+qmCpA+'~013~010';
qmCpDump := qmCpDump+'fpold|'+ParserGetValueByKeyByHandle(qmCpFp, 'old')+'~013~010';
qmRawWriteStr(qmCpOut, qmCpDump);
ParserSetValueByKeyByHandle(qmCpRt, 'status', 'ok');
