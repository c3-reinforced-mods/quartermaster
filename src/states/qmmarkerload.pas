state: qmMarkerLoad
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qminc
requires:
---
//! The start marker <save>\quartermaster\state.cfg into the named parser
//! qm_state (plan S8; ref/boot.py has the format and parse_marker is the
//! twin). The file is read with the engine's parser, the reader for files
//! whose values have no trailing space (docs/plan.md section 1): Quartermaster
//! writes it with the raw writer in the engine's layout, a file the parser was
//! seen to load (SelfTest run m2a3, the synthetic incprobe file).
//!
//! qm_state keys: have (1 = the file is a marker), gen, hash, phase, mode,
//! rows, rhash, rcount, rk, boots, on, op<k> oa<k> (an output's path relative
//! to <QmDir>\data\ and its FileAge text). Without a marker every key keeps its
//! default and have is 0: a first boot.
var qmMkSt : Integer = ParserSelectByKey('qm_state');
if (qmMkSt=0) then
qmMkSt := ParserCreate('qm_state');
ParserClearByHandle(qmMkSt);
ParserSetIntValueByKeyByHandle(qmMkSt, 'have', 0);
ParserSetIntValueByKeyByHandle(qmMkSt, 'gen', 0);
ParserSetValueByKeyByHandle(qmMkSt, 'hash', '-');
ParserSetValueByKeyByHandle(qmMkSt, 'phase', 'booted');
ParserSetValueByKeyByHandle(qmMkSt, 'mode', 'normal');
ParserSetIntValueByKeyByHandle(qmMkSt, 'rows', 0);
ParserSetValueByKeyByHandle(qmMkSt, 'rhash', '-');
ParserSetIntValueByKeyByHandle(qmMkSt, 'rcount', 0);
ParserSetValueByKeyByHandle(qmMkSt, 'rk', '-');
ParserSetIntValueByKeyByHandle(qmMkSt, 'boots', 0);
ParserSetIntValueByKeyByHandle(qmMkSt, 'on', 0);
var qmMkPath : String = GetAppSaveDirectoryPath+'quartermaster\state.cfg';
var qmMkSrc : Integer = qmIncLoad('qm_state_src', qmMkPath);
var qmMkCode : Integer = 0;
var qmMkN : Integer = 0;
if (qmMkSrc<>0) then
qmMkCode := ParserSelectByHandleByKey(qmMkSrc, 'Code');
if (qmMkCode<>0) then
qmMkN := ParserGetCountByHandle(qmMkCode);
var qmMkK : Integer;
var qmMkV : String;
var qmMkKey : String;
var qmMkVal : String;
var qmMkVal2 : String;
var qmMkHave : Integer = 0;
for qmMkK:=0 to qmMkN-1 do
if (ParserGetValueByIndexByHandle(qmMkCode, qmMkK)=';format|1') then
qmMkHave := 1;
var qmMkOn : Integer = 0;
if (qmMkHave=1) then
for qmMkK:=0 to qmMkN-1 do
begin
   qmMkV := ParserGetValueByIndexByHandle(qmMkCode, qmMkK);
   qmField(qmMkV, '|', 0, qmMkKey);
   qmField(qmMkV, '|', 1, qmMkVal);
   qmField(qmMkV, '|', 2, qmMkVal2);
   if (qmMkKey=';gen') and (qmIsDigits(qmMkVal)) then
   ParserSetIntValueByKeyByHandle(qmMkSt, 'gen', StrToInt(qmMkVal));
   if (qmMkKey=';hash') and (qmMkVal<>'') then
   ParserSetValueByKeyByHandle(qmMkSt, 'hash', qmMkVal);
   if (qmMkKey=';phase') and ((qmMkVal='written') or (qmMkVal='booting') or (qmMkVal='booted')) then
   ParserSetValueByKeyByHandle(qmMkSt, 'phase', qmMkVal);
   if (qmMkKey=';mode') and ((qmMkVal='normal') or (qmMkVal='wta')) then
   ParserSetValueByKeyByHandle(qmMkSt, 'mode', qmMkVal);
   if (qmMkKey=';rows') and (qmIsDigits(qmMkVal)) then
   ParserSetIntValueByKeyByHandle(qmMkSt, 'rows', StrToInt(qmMkVal));
   if (qmMkKey=';rhash') and (qmMkVal<>'') then
   ParserSetValueByKeyByHandle(qmMkSt, 'rhash', qmMkVal);
   if (qmMkKey=';rcount') and (qmIsDigits(qmMkVal)) then
   ParserSetIntValueByKeyByHandle(qmMkSt, 'rcount', StrToInt(qmMkVal));
   if (qmMkKey=';rk') and ((qmMkVal='auto') or (qmMkVal='apply') or (qmMkVal='test') or (qmMkVal='-')) then
   ParserSetValueByKeyByHandle(qmMkSt, 'rk', qmMkVal);
   if (qmMkKey=';boots') and (qmIsDigits(qmMkVal)) then
   ParserSetIntValueByKeyByHandle(qmMkSt, 'boots', StrToInt(qmMkVal));
   if (qmMkKey=';out') and (qmMkVal<>'') and (StrPos('|', SubStr(qmMkV, 6, StrLength(qmMkV)-5))>0) then
   begin
      ParserSetValueByKeyByHandle(qmMkSt, 'op'+IntToStr(qmMkOn), qmMkVal);
      ParserSetValueByKeyByHandle(qmMkSt, 'oa'+IntToStr(qmMkOn), qmMkVal2);
      qmMkOn := qmMkOn+1;
   end;
end;
ParserSetIntValueByKeyByHandle(qmMkSt, 'on', qmMkOn);
ParserSetIntValueByKeyByHandle(qmMkSt, 'have', qmMkHave);
qmLog('marker '+IntToStr(qmMkHave)+' gen='+IntToStr(ParserGetIntValueByKeyByHandle(qmMkSt, 'gen'))+' hash='+ParserGetValueByKeyByHandle(qmMkSt, 'hash')+' phase='+ParserGetValueByKeyByHandle(qmMkSt, 'phase')+' mode='+ParserGetValueByKeyByHandle(qmMkSt, 'mode')+' rows='+IntToStr(ParserGetIntValueByKeyByHandle(qmMkSt, 'rows'))+' rhash='+ParserGetValueByKeyByHandle(qmMkSt, 'rhash')+' rcount='+IntToStr(ParserGetIntValueByKeyByHandle(qmMkSt, 'rcount'))+' rk='+ParserGetValueByKeyByHandle(qmMkSt, 'rk')+' boots='+IntToStr(ParserGetIntValueByKeyByHandle(qmMkSt, 'boots'))+' outputs='+IntToStr(qmMkOn));
