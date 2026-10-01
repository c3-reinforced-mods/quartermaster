state: qmCaseEofProbe
into: data/quartermaster/selftest.aix
helpers: qmstr, qmraw
requires:
---
//! SelfTest case `eofprobe`: what the two integer readers return at and past
//! the end of a file. FileStreamReadInteger hands back a stale value there
//! (SelfTest run m2a), so a file can only be read exactly when its size is
//! known; this finds out whether the handle-based ReadInteger(fs, var val)
//! leaves the caller's variable alone at the end, which would make files of
//! unknown size readable (a variable preset to 0 would stay 0).
//!
//!   file <path> <size>   vanilla file of that size, absolute path:
//!                        eofs|path|size|<size div 4 + 3 values of
//!                        FileStreamReadInteger>
//!                        eofh|path|size|<handle>|<the same number of values of
//!                        ReadInteger, the variable preset to 305419896 before
//!                        each call>
//!
//! The stream reads of every file come first and the dump is rewritten after
//! every line, so if ReadInteger raises past the end the stream evidence
//! survives and the last line says how far the handle reads got.
var qmEpRt : Integer = ParserSelectByKey('qm_case_rt');
var qmEpOut : String = ParserGetValueByKeyByHandle(qmEpRt, 'out');
var qmEpCode : Integer = ParserSelectByHandleByKey(ParserSelectByKey('qm_case'), 'Code');
var qmEpNd : Integer = ParserGetCountByHandle(qmEpCode);
var qmEpApp : String = ExtractFilePath(GetApplicationFileName)+'data\';
var qmEpDump : String = '';
var qmEpPath : array [0..31] of String;
var qmEpSize : array [0..31] of Integer;
var qmEpNf : Integer = 0;
var qmEpD : Integer;
var qmEpF : Integer;
var qmEpK : Integer;
var qmEpDir : String;
var qmEpS : String;
var qmEpEsc : String;
var qmEpRow : String;
var qmEpFs : Integer;
var qmEpV : Integer;
for qmEpD:=1 to qmEpNd-1 do
if (qmEpNf<32) then
begin
   qmEpDir := ParserGetValueByIndexByHandle(qmEpCode, qmEpD);
   if (SubStr(qmEpDir, 1, 1)=';') then
   qmEpDir := SubStr(qmEpDir, 2, StrLength(qmEpDir)-1);
   qmField(qmEpDir, ' ', 1, qmEpS);
   qmEpPath[qmEpNf] := qmEpS;
   qmField(qmEpDir, ' ', 2, qmEpS);
   qmEpSize[qmEpNf] := StrToInt(qmEpS);
   qmEpNf := qmEpNf+1;
end;
for qmEpF:=0 to qmEpNf-1 do
begin
   qmEscape(qmEpPath[qmEpF], qmEpEsc);
   qmEpRow := 'eofs|'+qmEpEsc+'|'+IntToStr(qmEpSize[qmEpF])+'|';
   OpenFileStreamForRead(qmEpApp+qmEpPath[qmEpF]);
   for qmEpK:=0 to qmEpSize[qmEpF] div 4+2 do
   begin
      qmEpV := FileStreamReadInteger;
      if (qmEpK>0) then
      qmEpRow := qmEpRow+';';
      qmEpRow := qmEpRow+IntToStr(qmEpV);
   end;
   CloseFileStream;
   qmEpDump := qmEpDump+qmEpRow+'~013~010';
   qmRawWriteStr(qmEpOut, qmEpDump);
end;
for qmEpF:=0 to qmEpNf-1 do
begin
   qmEscape(qmEpPath[qmEpF], qmEpEsc);
   qmEpFs := OpenFileRead(qmEpApp+qmEpPath[qmEpF]);
   qmEpRow := 'eofh|'+qmEpEsc+'|'+IntToStr(qmEpSize[qmEpF])+'|'+IntToStr(qmEpFs)+'|';
   for qmEpK:=0 to qmEpSize[qmEpF] div 4+2 do
   begin
      qmEpV := 305419896;
      ReadInteger(qmEpFs, qmEpV);
      if (qmEpK>0) then
      qmEpRow := qmEpRow+';';
      qmEpRow := qmEpRow+IntToStr(qmEpV);
      qmRawWriteStr(qmEpOut, qmEpDump+qmEpRow+'~013~010');
   end;
   CloseFile(qmEpFs);
   qmEpDump := qmEpDump+qmEpRow+'~013~010';
   qmRawWriteStr(qmEpOut, qmEpDump);
end;
ParserSetValueByKeyByHandle(qmEpRt, 'status', 'ok');
