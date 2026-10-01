state: qmCaseReadDump
into: data/quartermaster/selftest.aix
helpers: qmstr, qmhash, qmraw, qmnorm, qminc
requires: rawcap, inccap, inchead
---
//! SelfTest case `readdump` (twin: ref/selftest.py readdump_expected). Reads
//! vanilla files from the absolute path (never through the overlay) and dumps
//! what the game side saw; tools/qmtest.py compares every line and every
//! written file with the twin. Sizes come with the directives (from
//! vanilla.idx): the raw reader reads exactly that many bytes.
//!
//!   inc <path>                 the parser's view: inc|path|<Code values or
//!                              -1 without Code>|<hash of the values>
//!   incraw <path> <size>       the raw reader + qmIncFromLines:
//!                              incraw|path|<form>|<key lines>|<values>|<hash>
//!   raw <path> <size>          raw|path|<lines>|<hash>|<hash normalised>|
//!                              <hash compared form>|<compared lines>
//!   rawh <path>                the same with the size not given: the
//!                              handle-based reader (qmRawReadAt, size -1)
//!   incat <path> <size>        qmIncReadAt into one pool after the files before
//!                              it: incat|path|<at>|<values>|<form>|<key lines>|
//!                              <hash of the values>|<qmIncHookIndex>
//!   incatend                   every incat span hashed again, after all of
//!                              them were read: incatend|path|<hash>
//!   rt <path> <out> <size>     read, write the lines to <out>, read that back
//!                              with the size the writer reports:
//!                              rt|path|out|<lines>|<lines back>|<1 when the
//!                              compared forms are equal>|<size written>
//!   norm <path> <out> <size>   write the compared form: norm|path|out|<lines>
//!   incw <path> <out> <n> <size>
//!                              the .inc writer: vanilla's key lines and its
//!                              first n values (or all, then `;// qm appended
//!                              <k>` up to n) through qmIncRender, read back:
//!                              incw|path|out|n|<bytes>|<values back>|<1 when
//!                              they are the values written>
//!
//! Hashes are qhash of the lines, LF after each. The compared form is the
//! normalised lines without trailing empty ones (ref/textio.py compare_form):
//! a file this writer wrote reads back with a last line of padding spaces,
//! and that must not count as a change (plan S8).
var qmRdRt : Integer = ParserSelectByKey('qm_case_rt');
var qmRdOutDir : String = ParserGetValueByKeyByHandle(qmRdRt, 'outdir');
var qmRdOut : String = ParserGetValueByKeyByHandle(qmRdRt, 'out');
var qmRdCode : Integer = ParserSelectByHandleByKey(ParserSelectByKey('qm_case'), 'Code');
var qmRdNd : Integer = ParserGetCountByHandle(qmRdCode);
var qmRdApp : String = ExtractFilePath(GetApplicationFileName)+'data\';
var qmRdA : array [0..${rawcap}] of String;
var qmRdB : array [0..${rawcap}] of String;
var qmRdV : array [0..${inccap}] of String;
var qmRdW : array [0..${inccap}] of String;
var qmRdHead : array [0..${inchead}] of String;
var qmRdDump : String = '';
var qmRdD : Integer;
var qmRdK : Integer;
var qmRdDir : String;
var qmRdVerb : String;
var qmRdPath : String;
var qmRdArg : String;
var qmRdArg2 : String;
var qmRdArg3 : String;
var qmRdSize : Integer;
var qmRdEsc : String;
var qmRdLine : String;
var qmRdN : Integer;
var qmRdN2 : Integer;
var qmRdC : Integer;
var qmRdC2 : Integer;
var qmRdSame : Integer;
var qmRdP : Integer;
var qmRdCd : Integer;
var qmRdCnt : Integer;
var qmRdNh : Integer;
var qmRdNv : Integer;
var qmRdForm : Integer;
var qmRdBytes : Integer;
var qmRdH1 : Integer;
var qmRdH2 : Integer;
var qmRdHL : Integer;
var qmRdHa : String;
var qmRdHb : String;
var qmRdHc : String;
var qmRdPoolAt : Integer = 0;
var qmRdSpans : Integer = 0;
var qmRdD2 : Integer;
var qmRdSpanPath : array [0..63] of String;
var qmRdSpanAt : array [0..63] of Integer;
var qmRdSpanN : array [0..63] of Integer;
for qmRdD:=1 to qmRdNd-1 do
begin
   qmRdDir := ParserGetValueByIndexByHandle(qmRdCode, qmRdD);
   if (SubStr(qmRdDir, 1, 1)=';') then
   qmRdDir := SubStr(qmRdDir, 2, StrLength(qmRdDir)-1);
   qmField(qmRdDir, ' ', 0, qmRdVerb);
   qmField(qmRdDir, ' ', 1, qmRdPath);
   qmField(qmRdDir, ' ', 2, qmRdArg);
   qmField(qmRdDir, ' ', 3, qmRdArg2);
   qmField(qmRdDir, ' ', 4, qmRdArg3);
   qmEscape(qmRdPath, qmRdEsc);
   qmRdLine := '';
   if (qmRdVerb='inc') then
   begin
      qmRdP := qmIncLoad('qm_case_inc', qmRdApp+qmRdPath);
      qmRdCd := 0;
      if (qmRdP<>0) then
      qmRdCd := ParserSelectByHandleByKey(qmRdP, 'Code');
      qmRdCnt := -1;
      qmRdH1 := 0;
      qmRdH2 := 0;
      qmRdHL := 0;
      if (qmRdCd<>0) then
      begin
         qmRdCnt := ParserGetCountByHandle(qmRdCd);
         for qmRdK:=0 to qmRdCnt-1 do
         begin
            qmHashStr(ParserGetValueByIndexByHandle(qmRdCd, qmRdK), qmRdH1, qmRdH2, qmRdHL);
            qmHashByte(10, qmRdH1, qmRdH2, qmRdHL);
         end;
      end;
      qmHashText(qmRdH1, qmRdH2, qmRdHL, qmRdHa);
      qmRdLine := 'inc|'+qmRdEsc+'|'+IntToStr(qmRdCnt)+'|'+qmRdHa;
   end;
   if (qmRdVerb='incraw') then
   begin
      qmRawRead(qmRdApp+qmRdPath, StrToInt(qmRdArg), qmRdA, qmRdN);
      qmIncFromLines(qmRdA, qmRdN, qmRdHead, qmRdNh, qmRdV, qmRdNv, qmRdForm);
      qmRdH1 := 0;
      qmRdH2 := 0;
      qmRdHL := 0;
      for qmRdK:=0 to qmRdNv-1 do
      begin
         qmHashStr(qmRdV[qmRdK], qmRdH1, qmRdH2, qmRdHL);
         qmHashByte(10, qmRdH1, qmRdH2, qmRdHL);
      end;
      qmHashText(qmRdH1, qmRdH2, qmRdHL, qmRdHa);
      qmRdLine := 'incraw|'+qmRdEsc+'|'+IntToStr(qmRdForm)+'|'+IntToStr(qmRdNh)+'|'+IntToStr(qmRdNv)+'|'+qmRdHa;
   end;
   if (qmRdVerb='incat') then
   begin
      qmIncReadAt(qmRdApp+qmRdPath, StrToInt(qmRdArg), qmRdB, qmRdPoolAt, qmRdHead, qmRdNh, qmRdNv, qmRdForm);
      qmRdH1 := 0;
      qmRdH2 := 0;
      qmRdHL := 0;
      for qmRdK:=0 to qmRdNv-1 do
      begin
         qmHashStr(qmRdB[qmRdPoolAt+qmRdK], qmRdH1, qmRdH2, qmRdHL);
         qmHashByte(10, qmRdH1, qmRdH2, qmRdHL);
      end;
      qmHashText(qmRdH1, qmRdH2, qmRdHL, qmRdHa);
      qmRdC := -1;
      if (qmRdNv>=0) then
      qmRdC := qmIncHookIndex(qmRdB, qmRdPoolAt, qmRdNv);
      qmRdLine := 'incat|'+qmRdEsc+'|'+IntToStr(qmRdPoolAt)+'|'+IntToStr(qmRdNv)+'|'+IntToStr(qmRdForm)+'|'+IntToStr(qmRdNh)+'|'+qmRdHa+'|'+IntToStr(qmRdC);
      if (qmRdNv>=0) and (qmRdSpans<64) then
      begin
         qmRdSpanPath[qmRdSpans] := qmRdEsc;
         qmRdSpanAt[qmRdSpans] := qmRdPoolAt;
         qmRdSpanN[qmRdSpans] := qmRdNv;
         qmRdSpans := qmRdSpans+1;
         qmRdPoolAt := qmRdPoolAt+qmRdNv;
      end;
   end;
   if (qmRdVerb='incatend') then
   begin
      for qmRdD2:=0 to qmRdSpans-1 do
      begin
         qmRdH1 := 0;
         qmRdH2 := 0;
         qmRdHL := 0;
         for qmRdK:=0 to qmRdSpanN[qmRdD2]-1 do
         begin
            qmHashStr(qmRdB[qmRdSpanAt[qmRdD2]+qmRdK], qmRdH1, qmRdH2, qmRdHL);
            qmHashByte(10, qmRdH1, qmRdH2, qmRdHL);
         end;
         qmHashText(qmRdH1, qmRdH2, qmRdHL, qmRdHa);
         if (qmRdD2>0) then
         qmRdLine := qmRdLine+'~013~010';
         qmRdLine := qmRdLine+'incatend|'+qmRdSpanPath[qmRdD2]+'|'+qmRdHa;
      end;
      if (qmRdLine='') then
      qmRdLine := 'incatend|none';
   end;
   if (qmRdVerb='raw') or (qmRdVerb='rawh') then
   begin
      qmRdSize := -1;
      if (qmRdVerb='raw') then
      qmRdSize := StrToInt(qmRdArg);
      qmRawRead(qmRdApp+qmRdPath, qmRdSize, qmRdA, qmRdN);
      qmRdH1 := 0;
      qmRdH2 := 0;
      qmRdHL := 0;
      for qmRdK:=0 to qmRdN-1 do
      begin
         qmHashStr(qmRdA[qmRdK], qmRdH1, qmRdH2, qmRdHL);
         qmHashByte(10, qmRdH1, qmRdH2, qmRdHL);
         qmNormKey(qmRdA[qmRdK], qmRdK=0, qmRdLine);
         qmRdB[qmRdK] := qmRdLine;
      end;
      qmHashText(qmRdH1, qmRdH2, qmRdHL, qmRdHa);
      qmRdH1 := 0;
      qmRdH2 := 0;
      qmRdHL := 0;
      for qmRdK:=0 to qmRdN-1 do
      begin
         qmHashStr(qmRdB[qmRdK], qmRdH1, qmRdH2, qmRdHL);
         qmHashByte(10, qmRdH1, qmRdH2, qmRdHL);
      end;
      qmHashText(qmRdH1, qmRdH2, qmRdHL, qmRdHb);
      qmRdC := qmRdN;
      while (qmRdC>0) and (qmRdB[qmRdC-1]='') do
      qmRdC := qmRdC-1;
      qmRdH1 := 0;
      qmRdH2 := 0;
      qmRdHL := 0;
      for qmRdK:=0 to qmRdC-1 do
      begin
         qmHashStr(qmRdB[qmRdK], qmRdH1, qmRdH2, qmRdHL);
         qmHashByte(10, qmRdH1, qmRdH2, qmRdHL);
      end;
      qmHashText(qmRdH1, qmRdH2, qmRdHL, qmRdHc);
      qmRdLine := qmRdVerb+'|'+qmRdEsc+'|'+IntToStr(qmRdN)+'|'+qmRdHa+'|'+qmRdHb+'|'+qmRdHc+'|'+IntToStr(qmRdC);
   end;
   if (qmRdVerb='rt') then
   begin
      qmRawRead(qmRdApp+qmRdPath, StrToInt(qmRdArg2), qmRdA, qmRdN);
      qmRawWrite(qmRdOutDir+qmRdArg, qmRdA, qmRdN);
      qmRdBytes := qmRawWrittenSize(qmRdA, qmRdN);
      qmRawRead(qmRdOutDir+qmRdArg, qmRdBytes, qmRdB, qmRdN2);
      for qmRdK:=0 to qmRdN-1 do
      begin
         qmNormKey(qmRdA[qmRdK], qmRdK=0, qmRdLine);
         qmRdA[qmRdK] := qmRdLine;
      end;
      for qmRdK:=0 to qmRdN2-1 do
      begin
         qmNormKey(qmRdB[qmRdK], qmRdK=0, qmRdLine);
         qmRdB[qmRdK] := qmRdLine;
      end;
      qmRdC := qmRdN;
      while (qmRdC>0) and (qmRdA[qmRdC-1]='') do
      qmRdC := qmRdC-1;
      qmRdC2 := qmRdN2;
      while (qmRdC2>0) and (qmRdB[qmRdC2-1]='') do
      qmRdC2 := qmRdC2-1;
      qmRdSame := 0;
      if (qmRdC=qmRdC2) then
      begin
         qmRdSame := 1;
         for qmRdK:=0 to qmRdC-1 do
         if (qmRdA[qmRdK]<>qmRdB[qmRdK]) then
         qmRdSame := 0;
      end;
      qmRdLine := 'rt|'+qmRdEsc+'|'+qmRdArg+'|'+IntToStr(qmRdN)+'|'+IntToStr(qmRdN2)+'|'+IntToStr(qmRdSame)+'|'+IntToStr(qmRdBytes);
   end;
   if (qmRdVerb='norm') then
   begin
      qmRawRead(qmRdApp+qmRdPath, StrToInt(qmRdArg2), qmRdA, qmRdN);
      for qmRdK:=0 to qmRdN-1 do
      begin
         qmNormKey(qmRdA[qmRdK], qmRdK=0, qmRdLine);
         qmRdB[qmRdK] := qmRdLine;
      end;
      qmRdC := qmRdN;
      while (qmRdC>0) and (qmRdB[qmRdC-1]='') do
      qmRdC := qmRdC-1;
      qmRawWrite(qmRdOutDir+qmRdArg, qmRdB, qmRdC);
      qmRdLine := 'norm|'+qmRdEsc+'|'+qmRdArg+'|'+IntToStr(qmRdC);
   end;
   if (qmRdVerb='incw') then
   begin
      qmRdCnt := StrToInt(qmRdArg2);
      qmRawRead(qmRdApp+qmRdPath, StrToInt(qmRdArg3), qmRdA, qmRdN);
      qmIncFromLines(qmRdA, qmRdN, qmRdHead, qmRdNh, qmRdV, qmRdNv, qmRdForm);
      qmRdBytes := -1;
      qmRdN2 := -1;
      qmRdSame := 0;
      if (qmRdNv>=0) and (qmRdCnt<=${inccap}+1) then
      begin
         for qmRdK:=0 to qmRdCnt-1 do
         if (qmRdK<qmRdNv) then
         qmRdW[qmRdK] := qmRdV[qmRdK]
         else
         qmRdW[qmRdK] := ';// qm appended '+IntToStr(qmRdK-qmRdNv);
         qmIncRender(qmRdOutDir+qmRdArg, qmRdHead, qmRdNh, qmRdW, qmRdCnt, qmRdBytes);
         qmRawRead(qmRdOutDir+qmRdArg, qmRdBytes, qmRdB, qmRdN);
         qmIncFromLines(qmRdB, qmRdN, qmRdHead, qmRdNh, qmRdV, qmRdN2, qmRdForm);
         if (qmRdN2=qmRdCnt) then
         begin
            qmRdSame := 1;
            for qmRdK:=0 to qmRdCnt-1 do
            if (qmRdV[qmRdK]<>qmRdW[qmRdK]) then
            qmRdSame := 0;
         end;
      end;
      qmRdLine := 'incw|'+qmRdEsc+'|'+qmRdArg+'|'+IntToStr(qmRdCnt)+'|'+IntToStr(qmRdBytes)+'|'+IntToStr(qmRdN2)+'|'+IntToStr(qmRdSame);
   end;
   if (qmRdLine='') then
   qmRdLine := 'unknown|'+qmRdEsc;
   qmRdDump := qmRdDump+qmRdLine+'~013~010';
end;
qmRawWriteStr(qmRdOut, qmRdDump);
ParserSetValueByKeyByHandle(qmRdRt, 'status', 'ok');
