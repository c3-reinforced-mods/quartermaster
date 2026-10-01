state: qmCaseKeys
into: data/quartermaster/selftest.aix
helpers: qmraw, qmidxkey
requires:
---
//! SelfTest case `keys`: are the encoded path keys (qmIdxKey) distinct and
//! lossless in a named parser? The parser folds and trims keys (capability
//! probes), which is why paths are encoded before they become keys; this
//! checks the encoding on every path the index scans.
//!
//!   keys|<paths>|<read back wrong>|<parser count>|<key names differing from
//!   the encoded path>|<qm_index_keys lookups wrong>
//!
//! Expected (ref/selftest.py keys_expected): keys|n|0|n|0|0. The last field
//! looks the paths up in qm_index_keys, the map qmIndexBegin built.
var qmCkRt : Integer = ParserSelectByKey('qm_case_rt');
var qmCkOut : String = ParserGetValueByKeyByHandle(qmCkRt, 'out');
var qmCkCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
StateMachineExecuteState(qmCkCore, 'qmModList', 0);
StateMachineExecuteState(qmCkCore, 'qmIndex', 0);
var qmCkIdx : Integer = ParserSelectByKey('qm_index');
var qmCkMap : Integer = ParserSelectByKey('qm_index_keys');
var qmCkN : Integer = ParserGetIntValueByKeyByHandle(qmCkIdx, 'n');
var qmCkP : Integer = ParserSelectByKey('qm_keytest');
if (qmCkP=0) then
qmCkP := ParserCreate('qm_keytest');
ParserClearByHandle(qmCkP);
var qmCkKey : array [0..4095] of String;
var qmCkK : Integer;
var qmCkS : String;
var qmCkWrong : Integer = 0;
var qmCkNames : Integer = 0;
var qmCkLookup : Integer = 0;
if (qmCkN>4096) then
qmCkN := 4096;
for qmCkK:=0 to qmCkN-1 do
begin
   qmIdxKey(ParserGetValueByKeyByHandle(qmCkIdx, 'p'+IntToStr(qmCkK)), qmCkS);
   qmCkKey[qmCkK] := qmCkS;
   ParserSetIntValueByKeyByHandle(qmCkP, qmCkS, qmCkK);
end;
for qmCkK:=0 to qmCkN-1 do
begin
   if (ParserGetIntValueByKeyByHandle(qmCkP, qmCkKey[qmCkK])<>qmCkK) then
   qmCkWrong := qmCkWrong+1;
   if (ParserGetIntValueByKeyByHandle(qmCkMap, qmCkKey[qmCkK])<>qmCkK) then
   qmCkLookup := qmCkLookup+1;
end;
var qmCkCount : Integer = ParserGetCountByHandle(qmCkP);
for qmCkK:=0 to qmCkCount-1 do
if (qmCkK<qmCkN) then
if (ParserGetKeyName(ParserSelectByHandleByIndex(qmCkP, qmCkK))<>qmCkKey[qmCkK]) then
qmCkNames := qmCkNames+1;
qmRawWriteStr(qmCkOut, 'keys|'+IntToStr(qmCkN)+'|'+IntToStr(qmCkWrong)+'|'+IntToStr(qmCkCount)+'|'+IntToStr(qmCkNames)+'|'+IntToStr(qmCkLookup)+'~013~010');
ParserSetValueByKeyByHandle(qmCkRt, 'status', 'ok');
