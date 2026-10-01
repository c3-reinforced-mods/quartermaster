state: qmFingerprint
into: data/quartermaster/core.aix
helpers: qmlog, qmhash
requires: version
---
//! The start-up fingerprint (plan S8, guard 2; twin: ref/fingerprint.py and
//! ref/index.py). Inputs only, one line each, LF after every line:
//!
//!   qm-fingerprint 1
//!   qm <version>
//!   vanilla <stamp>        FileAge of the pristine copy of every provided
//!                          scanned path (absolute path: FileAge ignores the
//!                          overlay anyway), then of cossacks.exe
//!   <w|l|o> <id> on <stamp> / <w|l|o> <id> off
//!                          every mod but Quartermaster, in load order
//!                          (qm_mods ord<k> as qmOrder left it: the saved
//!                          order, else canonical); the stamp is the one
//!                          qmIndexStep made
//!
//! The order of those lines is an input (decided 2026-09-28): it decides which
//! mod wins, so a reorder in the manager is a new fingerprint. With no saved
//! order the text is the canonical one it always was.
//!
//! Quartermaster's own folder is not in it: its outputs change with every
//! generation and would restart the game forever.
//!
//! The same text without the mods the engine registered at this start
//! (qm_known fr<i>; twin: ref/index.py known_fingerprint) is hashed beside it:
//! what the previous boot computed when nothing else moved, for the loop
//! rule's exception (qmGuard). A path stays in its vanilla stamp while a
//! provider that is not such a mod ships it.
//!
//! qm_fp keys: n, l<m> (the lines), hash, old. qm_index gets va<k> and exe
//! (the FileAge values that went in, so a dump can be checked), and vstamp.
//! qm_rt gets fp and fpold.
var qmFpIdx : Integer = ParserSelectByKey('qm_index');
var qmFpMods : Integer = ParserSelectByKey('qm_mods');
var qmFpRt : Integer = ParserSelectByKey('qm_rt');
var qmFpKn : Integer = ParserSelectByKey('qm_known');
var qmFpFp : Integer = ParserSelectByKey('qm_fp');
if (qmFpFp=0) then
qmFpFp := ParserCreate('qm_fp');
ParserClearByHandle(qmFpFp);
var qmFpFresh : Integer = 0;
if (qmFpKn<>0) then
qmFpFresh := ParserGetIntValueByKeyByHandle(qmFpKn, 'frn');
var qmFpApp : String = ExtractFilePath(GetApplicationFileName)+'data\';
var qmFpN : Integer = ParserGetIntValueByKeyByHandle(qmFpIdx, 'n');
var qmFpH1 : Integer = 0;
var qmFpH2 : Integer = 0;
var qmFpHL : Integer = 0;
var qmFpO1 : Integer = 0;
var qmFpO2 : Integer = 0;
var qmFpOL : Integer = 0;
var qmFpK : Integer;
var qmFpC : Integer;
var qmFpPath : String;
var qmFpAge : Integer;
var qmFpV : String;
var qmFpOv : String;
var qmFpS : String;
var qmFpP : String;
var qmFpKeep : Boolean;
for qmFpK:=0 to qmFpN-1 do
if (ParserGetValueByKeyByHandle(qmFpIdx, 'v'+IntToStr(qmFpK))<>'-') then
begin
   qmFpPath := ParserGetValueByKeyByHandle(qmFpIdx, 'p'+IntToStr(qmFpK));
   qmFpAge := FileAge(qmFpApp+qmFpPath);
   ParserSetIntValueByKeyByHandle(qmFpIdx, 'va'+IntToStr(qmFpK), qmFpAge);
   qmHashStr(qmFpPath+' '+IntToStr(qmFpAge), qmFpH1, qmFpH2, qmFpHL);
   qmHashByte(10, qmFpH1, qmFpH2, qmFpHL);
   //! v<k>: the providers' load positions, `;` between; ord<pos> is the row.
   qmFpKeep := True;
   if (qmFpFresh>0) then
   begin
      qmFpKeep := False;
      qmFpS := ParserGetValueByKeyByHandle(qmFpIdx, 'v'+IntToStr(qmFpK))+';';
      qmFpP := '';
      for qmFpC:=1 to StrLength(qmFpS) do
      begin
         if (SubStr(qmFpS, qmFpC, 1)=';') then
         begin
            if (ParserGetIntValueByKeyByHandle(qmFpKn, 'fr'+IntToStr(ParserGetIntValueByKeyByHandle(qmFpMods, 'ord'+qmFpP)))=0) then
            qmFpKeep := True;
            qmFpP := '';
         end
         else
         qmFpP := qmFpP+SubStr(qmFpS, qmFpC, 1);
      end;
   end;
   if (qmFpKeep) then
   begin
      qmHashStr(qmFpPath+' '+IntToStr(qmFpAge), qmFpO1, qmFpO2, qmFpOL);
      qmHashByte(10, qmFpO1, qmFpO2, qmFpOL);
   end;
end;
qmFpAge := FileAge(GetApplicationFileName);
ParserSetIntValueByKeyByHandle(qmFpIdx, 'exe', qmFpAge);
qmHashStr('exe '+IntToStr(qmFpAge), qmFpH1, qmFpH2, qmFpHL);
qmHashByte(10, qmFpH1, qmFpH2, qmFpHL);
qmHashText(qmFpH1, qmFpH2, qmFpHL, qmFpV);
qmHashStr('exe '+IntToStr(qmFpAge), qmFpO1, qmFpO2, qmFpOL);
qmHashByte(10, qmFpO1, qmFpO2, qmFpOL);
qmHashText(qmFpO1, qmFpO2, qmFpOL, qmFpOv);
ParserSetValueByKeyByHandle(qmFpIdx, 'vstamp', qmFpV);
//! The text's lines, then the same lines without the fresh mods' rows: both
//! hashed by one procedure.
var qmFpLine : array [0..519] of String;
var qmFpFr : array [0..259] of Integer;
var qmFpM : Integer = 3;
var qmFpO : Integer;
procedure qmFpHashLines(const qmFhFrom : Integer; const qmFhTo : Integer; var qmFhOut : String);
begin
   var qmFh1 : Integer = 0;
   var qmFh2 : Integer = 0;
   var qmFhL : Integer = 0;
   var qmFhK : Integer;
   for qmFhK:=qmFhFrom to qmFhTo-1 do
   begin
      qmHashStr(qmFpLine[qmFhK], qmFh1, qmFh2, qmFhL);
      qmHashByte(10, qmFh1, qmFh2, qmFhL);
   end;
   qmHashText(qmFh1, qmFh2, qmFhL, qmFhOut);
end;
qmFpLine[0] := 'qm-fingerprint 1';
qmFpLine[1] := 'qm '+${version};
qmFpLine[2] := 'vanilla '+qmFpV;
var qmFpCount : Integer = ParserGetIntValueByKeyByHandle(qmFpMods, 'n');
var qmFpI : Integer;
var qmFpRow : String;
for qmFpK:=0 to qmFpCount-1 do
begin
   qmFpI := ParserGetIntValueByKeyByHandle(qmFpMods, 'ord'+IntToStr(qmFpK));
   if (ParserGetValueByKeyByHandle(qmFpMods, 'org'+IntToStr(qmFpI))<>'s') then
   begin
      qmFpRow := ParserGetValueByKeyByHandle(qmFpMods, 'fo'+IntToStr(qmFpI))+' '+ParserGetValueByKeyByHandle(qmFpMods, 'id'+IntToStr(qmFpI));
      if (ParserGetIntValueByKeyByHandle(qmFpMods, 'on'+IntToStr(qmFpI))=1) then
      qmFpRow := qmFpRow+' on '+ParserGetValueByKeyByHandle(qmFpIdx, 'st'+IntToStr(qmFpK))
      else
      qmFpRow := qmFpRow+' off';
      qmFpLine[qmFpM] := qmFpRow;
      qmFpFr[qmFpM] := 0;
      if (qmFpFresh>0) then
      qmFpFr[qmFpM] := ParserGetIntValueByKeyByHandle(qmFpKn, 'fr'+IntToStr(qmFpI));
      qmFpM := qmFpM+1;
   end;
end;
qmFpO := qmFpM;
qmFpLine[qmFpO] := qmFpLine[0];
qmFpLine[qmFpO+1] := qmFpLine[1];
qmFpLine[qmFpO+2] := 'vanilla '+qmFpOv;
var qmFpE : Integer = qmFpO+3;
for qmFpK:=3 to qmFpM-1 do
if (qmFpFr[qmFpK]<>1) then
begin
   qmFpLine[qmFpE] := qmFpLine[qmFpK];
   qmFpE := qmFpE+1;
end;
for qmFpK:=0 to qmFpM-1 do
ParserSetValueByKeyByHandle(qmFpFp, 'l'+IntToStr(qmFpK), qmFpLine[qmFpK]);
qmFpHashLines(0, qmFpM, qmFpV);
qmFpHashLines(qmFpO, qmFpE, qmFpOv);
ParserSetIntValueByKeyByHandle(qmFpFp, 'n', qmFpM);
ParserSetValueByKeyByHandle(qmFpFp, 'hash', qmFpV);
ParserSetValueByKeyByHandle(qmFpFp, 'old', qmFpOv);
ParserSetValueByKeyByHandle(qmFpRt, 'fp', qmFpV);
ParserSetValueByKeyByHandle(qmFpRt, 'fpold', qmFpOv);
qmLog('fingerprint '+qmFpV+' lines='+IntToStr(qmFpM));
if (qmFpFresh>0) then
qmLog('fingerprint without the '+IntToStr(qmFpFresh)+' mod(s) registered at this start '+qmFpOv);
