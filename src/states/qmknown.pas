state: qmKnown
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qminc, qmbootdir
requires: inchead
---
//! Newly registered mods (plan S13: keep them active, mark
//! them new). The engine registers and enables every new folder in mods\
//! before any script runs (M0: appended to mods.ini with dis = False), so the
//! boot can only notice them: <save>\quartermaster\known.cfg lists every dir
//! it has seen, `;k|<dir>` known or `;n|<dir>` new. ref/boot.py update_known /
//! acknowledge are the twins and have the format.
//!
//!   - no file (a first boot): every mod registered now is recorded as known;
//!   - a dir not in the file: appended as new, in the engine's order;
//!   - a confirmed Apply (qm_rt runmode apply) acknowledges them all.
//! The file is written only when it changes; dirs are compared folded
//! (qmNormDir) and written as the engine spells them, escaped, so no byte is
//! lost. Dirs that are gone stay listed: a folder that comes back is not new.
//!
//! qm_known keys: have (the file existed), n, d<k>, f<k> (1 = new), newn,
//! new<j> (new dirs registered now: the report marks them NEW), changed;
//! fr<i> (1 = qm_mods row i was registered at this start: not in the file as
//! it was read; ref/boot.py fresh) and frn, for the loop rule's exception
//! (qmFingerprint, qmGuard).
var qmKnKn : Integer = ParserSelectByKey('qm_known');
if (qmKnKn=0) then
qmKnKn := ParserCreate('qm_known');
ParserClearByHandle(qmKnKn);
var qmKnMods : Integer = ParserSelectByKey('qm_mods');
var qmKnRt : Integer = ParserSelectByKey('qm_rt');
var qmKnApply : Boolean = (ParserGetValueByKeyByHandle(qmKnRt, 'runmode')='apply');
var qmKnPath : String = GetAppSaveDirectoryPath+'quartermaster\known.cfg';
var qmKnDir : array [0..511] of String;
var qmKnNorm : array [0..511] of String;
var qmKnFlag : array [0..511] of Integer;
var qmKnN : Integer = 0;
var qmKnHave : Integer = 0;
var qmKnChanged : Integer = 0;
var qmKnK : Integer;
var qmKnI : Integer;
var qmKnJ : Integer;
var qmKnV : String;
var qmKnD : String;
var qmKnNd : String;
var qmKnSeen : Boolean;
var qmKnSrc : Integer = qmIncLoad('qm_known_src', qmKnPath);
var qmKnCode : Integer = 0;
var qmKnCount : Integer = 0;
if (qmKnSrc<>0) then
qmKnCode := ParserSelectByHandleByKey(qmKnSrc, 'Code');
if (qmKnCode<>0) then
qmKnCount := ParserGetCountByHandle(qmKnCode);
for qmKnK:=0 to qmKnCount-1 do
if (ParserGetValueByIndexByHandle(qmKnCode, qmKnK)=';format|1') then
qmKnHave := 1;
if (qmKnHave=1) then
for qmKnK:=0 to qmKnCount-1 do
begin
   qmKnV := ParserGetValueByIndexByHandle(qmKnCode, qmKnK);
   if ((SubStr(qmKnV, 1, 3)=';k|') or (SubStr(qmKnV, 1, 3)=';n|')) and (StrLength(qmKnV)>3) and (qmKnN<512) then
   begin
      qmKnDir[qmKnN] := SubStr(qmKnV, 4, StrLength(qmKnV)-3);
      qmNormDir(qmKnDir[qmKnN], qmKnNorm[qmKnN]);
      if (SubStr(qmKnV, 1, 3)=';n|') then
      qmKnFlag[qmKnN] := 1
      else
      qmKnFlag[qmKnN] := 0;
      qmKnN := qmKnN+1;
   end;
end;
if (qmKnHave=0) then
qmKnChanged := 1;
var qmKnFileN : Integer = qmKnN;
var qmKnFr : Integer;
var qmKnFrn : Integer = 0;
var qmKnModN : Integer = ParserGetIntValueByKeyByHandle(qmKnMods, 'n');
for qmKnI:=0 to qmKnModN-1 do
begin
   qmKnD := ParserGetValueByKeyByHandle(qmKnMods, 'dir'+IntToStr(qmKnI));
   qmNormDir(qmKnD, qmKnNd);
   qmKnFr := 0;
   if (qmKnHave=1) then
   begin
      qmKnFr := 1;
      for qmKnJ:=0 to qmKnFileN-1 do
      if (qmKnNorm[qmKnJ]=qmKnNd) then
      qmKnFr := 0;
   end;
   ParserSetIntValueByKeyByHandle(qmKnKn, 'fr'+IntToStr(qmKnI), qmKnFr);
   qmKnFrn := qmKnFrn+qmKnFr;
   qmKnSeen := False;
   for qmKnJ:=0 to qmKnN-1 do
   if (qmKnNorm[qmKnJ]=qmKnNd) then
   qmKnSeen := True;
   if (not qmKnSeen) and (qmKnN<512) then
   begin
      qmKnDir[qmKnN] := qmKnD;
      qmKnNorm[qmKnN] := qmKnNd;
      //! A first boot records what it finds as known; later, a dir the file
      //! does not have is new.
      if (qmKnHave=1) then
      begin
         qmKnFlag[qmKnN] := 1;
         qmKnChanged := 1;
      end
      else
      qmKnFlag[qmKnN] := 0;
      qmKnN := qmKnN+1;
   end;
end;
if (qmKnApply) then
for qmKnK:=0 to qmKnN-1 do
if (qmKnFlag[qmKnK]=1) then
begin
   qmKnFlag[qmKnK] := 0;
   qmKnChanged := 1;
end;
var qmKnNew : Integer = 0;
for qmKnK:=0 to qmKnN-1 do
begin
   ParserSetValueByKeyByHandle(qmKnKn, 'd'+IntToStr(qmKnK), qmKnDir[qmKnK]);
   ParserSetIntValueByKeyByHandle(qmKnKn, 'f'+IntToStr(qmKnK), qmKnFlag[qmKnK]);
   if (qmKnFlag[qmKnK]=1) then
   begin
      qmKnSeen := False;
      for qmKnI:=0 to qmKnModN-1 do
      begin
         qmNormDir(ParserGetValueByKeyByHandle(qmKnMods, 'dir'+IntToStr(qmKnI)), qmKnNd);
         if (qmKnNd=qmKnNorm[qmKnK]) then
         qmKnSeen := True;
      end;
      if (qmKnSeen) then
      begin
         ParserSetValueByKeyByHandle(qmKnKn, 'new'+IntToStr(qmKnNew), qmKnDir[qmKnK]);
         qmKnNew := qmKnNew+1;
         qmLog('known: new mod '+qmKnDir[qmKnK]);
      end;
   end;
end;
ParserSetIntValueByKeyByHandle(qmKnKn, 'have', qmKnHave);
ParserSetIntValueByKeyByHandle(qmKnKn, 'n', qmKnN);
ParserSetIntValueByKeyByHandle(qmKnKn, 'newn', qmKnNew);
ParserSetIntValueByKeyByHandle(qmKnKn, 'frn', qmKnFrn);
ParserSetIntValueByKeyByHandle(qmKnKn, 'changed', qmKnChanged);
if (qmKnChanged=1) then
begin
   var qmKnHead : array [0..${inchead}] of String;
   var qmKnBytes : Integer = 0;
   var qmKnE : String;
   qmKnHead[0] := 'Name = qmKnown';
   qmIncBegin(qmKnPath, qmKnHead, 1, qmKnN+1);
   qmIncLine(';format~1241');
   for qmKnK:=0 to qmKnN-1 do
   begin
      qmEscape(qmKnDir[qmKnK], qmKnE);
      if (qmKnFlag[qmKnK]=1) then
      qmIncLine(';n~124'+qmKnE)
      else
      qmIncLine(';k~124'+qmKnE);
   end;
   qmIncEnd(qmKnBytes);
end;
qmLog('known mods='+IntToStr(qmKnN)+' new='+IntToStr(qmKnNew)+' file='+IntToStr(qmKnHave)+' written='+IntToStr(qmKnChanged));
