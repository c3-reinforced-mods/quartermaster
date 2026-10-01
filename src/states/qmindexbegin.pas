state: qmIndexBegin
into: data/quartermaster/core.aix
helpers: qmlog, qmidxkey
requires: scannamed
---
//! First half of the index (plan G3; twin: ref/index.py scan_entries): the
//! list of vanilla paths to scan, from vanilla.idx, into the named parser
//! qm_index. qmIndexStep then checks them, a batch per call.
//!
//! The scan covers the merge class of vanilla.idx (the S3 allow-list), the
//! S5 hook files and the Phase B data profiles plus dmscript.global - the paths
//! a Phase A decision depends on. Everything else is winner-takes-all by rule
//! (plan S2) and its providers change no output.
//!
//! vanilla.idx is a one-state .inc (tools/hbuild.py); each Code value is
//! `;<path>|<size>|<lines>|<class>`. It is read from Quartermaster's own
//! folder when qmModList found it, else through the overlay.
//!
//! Keys written: n (paths), total (vanilla.idx entries), p<k> c<k> l<k>
//! (path, class, vanilla lines), v<k> a<k> (providers and their FileAge, `-`
//! until scanned), cur, done, calls, h1_<pos> h2_<pos> hl_<pos> (the stamp
//! hash of each scanned mod, by load position: qmOrder's pos<i>). qm_index_keys maps the
//! encoded path (qmIdxKey) to k.
var qmIbIdx : Integer = ParserSelectByKey('qm_index');
if (qmIbIdx=0) then
qmIbIdx := ParserCreate('qm_index');
ParserClearByHandle(qmIbIdx);
var qmIbKeys : Integer = ParserSelectByKey('qm_index_keys');
if (qmIbKeys=0) then
qmIbKeys := ParserCreate('qm_index_keys');
ParserClearByHandle(qmIbKeys);
var qmIbMods : Integer = ParserSelectByKey('qm_mods');
var qmIbQm : String = ParserGetValueByKeyByHandle(ParserSelectByKey('qm_rt'), 'qmdir');
var qmIbFile : String = '.\data\quartermaster\vanilla.idx';
if (qmIbQm<>'') then
qmIbFile := qmIbQm+'\data\quartermaster\vanilla.idx';
var qmIbV : Integer = ParserSelectByKey('qm_vidx');
if (qmIbV=0) then
qmIbV := ParserCreate('qm_vidx');
ParserClearByHandle(qmIbV);
ParserLoadFromFileByHandle(qmIbV, qmIbFile);
var qmIbCode : Integer = ParserSelectByHandleByKey(qmIbV, 'Code');
var qmIbTotal : Integer = 0;
if (qmIbCode<>0) then
qmIbTotal := ParserGetCountByHandle(qmIbCode);
var qmIbN : Integer = 0;
var qmIbK : Integer;
var qmIbS : String;
var qmIbL : Integer;
var qmIbP : Integer;
var qmIbPath : String;
var qmIbRest : String;
var qmIbKey : String;
for qmIbK:=0 to qmIbTotal-1 do
begin
   qmIbS := ParserGetValueByIndexByHandle(qmIbCode, qmIbK);
   if (SubStr(qmIbS, 1, 1)=';') then
   qmIbS := SubStr(qmIbS, 2, StrLength(qmIbS)-1);
   qmIbL := StrLength(qmIbS);
   qmIbP := StrPos('|', qmIbS);
   if (qmIbP>1) then
   begin
      qmIbPath := SubStr(qmIbS, 1, qmIbP-1);
      if (SubStr(qmIbS, qmIbL-5, 6)='|merge') or (StrPos('|'+qmIbPath+'|', ${scannamed})>0) then
      begin
         //! size|lines|class -> lines|class
         qmIbRest := SubStr(qmIbS, qmIbP+1, qmIbL-qmIbP);
         qmIbRest := SubStr(qmIbRest, StrPos('|', qmIbRest)+1, StrLength(qmIbRest));
         qmIbP := StrPos('|', qmIbRest);
         ParserSetValueByKeyByHandle(qmIbIdx, 'p'+IntToStr(qmIbN), qmIbPath);
         ParserSetValueByKeyByHandle(qmIbIdx, 'l'+IntToStr(qmIbN), SubStr(qmIbRest, 1, qmIbP-1));
         ParserSetValueByKeyByHandle(qmIbIdx, 'c'+IntToStr(qmIbN), SubStr(qmIbRest, qmIbP+1, StrLength(qmIbRest)-qmIbP));
         ParserSetValueByKeyByHandle(qmIbIdx, 'v'+IntToStr(qmIbN), '-');
         ParserSetValueByKeyByHandle(qmIbIdx, 'a'+IntToStr(qmIbN), '-');
         qmIdxKey(qmIbPath, qmIbKey);
         ParserSetIntValueByKeyByHandle(qmIbKeys, qmIbKey, qmIbN);
         qmIbN := qmIbN+1;
      end;
   end;
end;
ParserSetIntValueByKeyByHandle(qmIbIdx, 'n', qmIbN);
ParserSetIntValueByKeyByHandle(qmIbIdx, 'total', qmIbTotal);
ParserSetIntValueByKeyByHandle(qmIbIdx, 'cur', 0);
ParserSetIntValueByKeyByHandle(qmIbIdx, 'done', 0);
ParserSetIntValueByKeyByHandle(qmIbIdx, 'calls', 0);
var qmIbEn : Integer = ParserGetIntValueByKeyByHandle(qmIbMods, 'en');
var qmIbPos : Integer;
for qmIbK:=0 to qmIbEn-1 do
begin
   qmIbPos := ParserGetIntValueByKeyByHandle(qmIbMods, 'pos'+IntToStr(ParserGetIntValueByKeyByHandle(qmIbMods, 'e'+IntToStr(qmIbK))));
   ParserSetIntValueByKeyByHandle(qmIbIdx, 'h1_'+IntToStr(qmIbPos), 0);
   ParserSetIntValueByKeyByHandle(qmIbIdx, 'h2_'+IntToStr(qmIbPos), 0);
   ParserSetIntValueByKeyByHandle(qmIbIdx, 'hl_'+IntToStr(qmIbPos), 0);
end;
qmLog('index scan list '+IntToStr(qmIbN)+' of '+IntToStr(qmIbTotal)+' vanilla.idx entries from '+qmIbFile);
