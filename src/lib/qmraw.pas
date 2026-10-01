helpers:
requires: rawcap
---
//! Raw text IO through the engine's integer file calls; ref/textio.py is the
//! twin and has the evidence.
//!
//! Reading. FileStreamReadInteger does not report the end of a file: past it
//! it returns a stale value (4, 32, a loop bound, a pointer - SelfTest runs
//! m2a, m2a2). The handle-based ReadInteger(fs, var val) does: past the end it
//! leaves the caller's variable alone, and on a partial last integer it
//! overwrites only the low bytes it read (run m2a2 eofprobe: a preset
//! 0x12345678 stayed 0x12345678 past the end and became 0x1234560A on the
//! last byte of style.txt). So:
//!   size >= 0  FileStreamReadInteger, exactly `size` bytes: size div 4 whole
//!              integers, then the low size mod 4 bytes of one more - never
//!              past the end (run m2a2: 983 lines of 333 files equal to ref/);
//!   size <  0  OpenFileRead + ReadInteger with the variable preset to 0 before
//!              every call: past the end it stays 0, a partial last integer
//!              has zero high bytes, and a zero byte ends the text anyway. For
//!              a text file (no zero byte) that is an exact read of a file
//!              whose size is not known - a mod's file, say.
//! Both give ref/textio.py read_lines: CR dropped, LF splits, a zero byte ends
//! the text, at most 2,000,000 integers, a last line without LF kept when it
//! is not empty.
//!
//! Lines are internal strings: bytes 32..122 as characters (the table below,
//! space to z), every other byte as ~NNN. Bytes come out of an Integer with
//! `shr` and `and 255`; `shr` is logical and arithmetic wraps (capability
//! probes), so a negative Integer comes apart like any other.
//!
//! qmRawReadAt       a file's lines into pool[at..at+n-1] of a caller-owned
//!                   [0..rawcap] array, so several files share one array (a
//!                   String array costs about 4.6 us per element on every call
//!                   of the state that declares it). n is the count; -1 when
//!                   they do not fit (the ones that fit are stored), -2 when
//!                   the file does not exist
//! qmRawRead         qmRawReadAt at 0
//! qmRawLen          the bytes an internal string stands for
//! qmRawWrittenSize  the size of the file qmRawWrite makes of lines [0..n-1]
//! qmRawWrite        lines [0..n-1], each followed by CR LF, padded with spaces
//!                   to a multiple of 4 (only whole integers can be written)
//! qmRawWriteStr     one internal string as it is: a caller that writes a few
//!                   lines builds them with ~013~010 between them and needs no
//!                   array
procedure qmRawReadAt(const qmRaPath : String; const qmRaSize : Integer; var qmRaPool : array [0..${rawcap}] of String; const qmRaAt : Integer; var qmRaN : Integer);
begin
   var qmRaTbl : String = ' !"#$%&''()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz';
   var qmRaCur : String = '';
   var qmRaDone : Boolean = False;
   var qmRaInts : Integer = 0;
   var qmRaTotal : Integer = 2000000;
   var qmRaRem : Integer = 0;
   var qmRaCount : Integer;
   var qmRaV : Integer;
   var qmRaSh : Integer;
   var qmRaB : Integer;
   var qmRaE : String;
   var qmRaFs : Integer = 0;
   qmRaN := 0;
   if (FileAge(qmRaPath)=-1) then
   begin
      qmRaN := -2;
      exit;
   end;
   if (qmRaSize>=0) then
   begin
      qmRaRem := qmRaSize mod 4;
      qmRaTotal := qmRaSize div 4;
      if (qmRaRem>0) then
      qmRaTotal := qmRaTotal+1;
      if (qmRaTotal>2000000) then
      qmRaTotal := 2000000;
      OpenFileStreamForRead(qmRaPath);
   end
   else
   qmRaFs := OpenFileRead(qmRaPath);
   while (not qmRaDone) and (qmRaInts<qmRaTotal) do
   begin
      if (qmRaSize>=0) then
      qmRaV := FileStreamReadInteger
      else
      begin
         qmRaV := 0;
         ReadInteger(qmRaFs, qmRaV);
      end;
      qmRaInts := qmRaInts+1;
      qmRaCount := 4;
      if (qmRaSize>=0) and (qmRaInts=qmRaTotal) and (qmRaRem>0) and (qmRaTotal*4>qmRaSize) then
      qmRaCount := qmRaRem;
      for qmRaSh:=0 to qmRaCount-1 do
      if (not qmRaDone) then
      begin
         qmRaB := (qmRaV shr (qmRaSh*8)) and 255;
         if (qmRaB=0) then
         qmRaDone := True
         else
         if (qmRaB=10) then
         begin
            if (qmRaAt+qmRaN<=${rawcap}) then
            qmRaPool[qmRaAt+qmRaN] := qmRaCur;
            qmRaN := qmRaN+1;
            qmRaCur := '';
         end
         else
         if (qmRaB<>13) then
         begin
            if (qmRaB>=32) and (qmRaB<=122) then
            qmRaCur := qmRaCur+SubStr(qmRaTbl, qmRaB-31, 1)
            else
            begin
               qmRaE := IntToStr(qmRaB);
               while (StrLength(qmRaE)<3) do
               qmRaE := '0'+qmRaE;
               qmRaCur := qmRaCur+'~'+qmRaE;
            end;
         end;
      end;
   end;
   if (qmRaSize>=0) then
   CloseFileStream
   else
   CloseFile(qmRaFs);
   if (qmRaCur<>'') then
   begin
      if (qmRaAt+qmRaN<=${rawcap}) then
      qmRaPool[qmRaAt+qmRaN] := qmRaCur;
      qmRaN := qmRaN+1;
   end;
   if (qmRaAt+qmRaN>${rawcap}+1) then
   qmRaN := -1;
end;

procedure qmRawRead(const qmRrPath : String; const qmRrSize : Integer; var qmRrOut : array [0..${rawcap}] of String; var qmRrN : Integer);
begin
   qmRawReadAt(qmRrPath, qmRrSize, qmRrOut, 0, qmRrN);
end;

function qmRawLen(const qmRlS : String) : Integer;
begin
   var qmRlN : Integer = StrLength(qmRlS);
   var qmRlI : Integer;
   for qmRlI:=1 to StrLength(qmRlS) do
   if (SubStr(qmRlS, qmRlI, 1)='~') then
   qmRlN := qmRlN-3;
   Result := qmRlN;
end;

function qmRawWrittenSize(var qmRzL : array [0..${rawcap}] of String; const qmRzN : Integer) : Integer;
begin
   var qmRzT : Integer = 0;
   var qmRzK : Integer;
   for qmRzK:=0 to qmRzN-1 do
   qmRzT := qmRzT+qmRawLen(qmRzL[qmRzK])+2;
   while (qmRzT mod 4<>0) do
   qmRzT := qmRzT+1;
   Result := qmRzT;
end;

procedure qmRawPut(const qmRpB : Integer; var qmRpAcc : Integer; var qmRpCnt : Integer);
begin
   qmRpAcc := qmRpAcc or (qmRpB shl (qmRpCnt*8));
   qmRpCnt := qmRpCnt+1;
   if (qmRpCnt=4) then
   begin
      FileStreamWriteInteger(qmRpAcc);
      qmRpAcc := 0;
      qmRpCnt := 0;
   end;
end;

procedure qmRawPutStr(const qmRsS : String; var qmRsAcc : Integer; var qmRsCnt : Integer);
begin
   var qmRsLen : Integer = StrLength(qmRsS);
   var qmRsC : Integer = 1;
   var qmRsCh : String;
   var qmRsB : Integer;
   while (qmRsC<=qmRsLen) do
   begin
      qmRsCh := SubStr(qmRsS, qmRsC, 1);
      if (qmRsCh='~') then
      begin
         qmRsB := StrToInt(SubStr(qmRsS, qmRsC+1, 3));
         qmRsC := qmRsC+3;
      end
      else
      qmRsB := Ord(qmRsCh);
      qmRawPut(qmRsB, qmRsAcc, qmRsCnt);
      qmRsC := qmRsC+1;
   end;
end;

procedure qmRawPutLine(const qmRtS : String; var qmRtAcc : Integer; var qmRtCnt : Integer);
begin
   qmRawPutStr(qmRtS, qmRtAcc, qmRtCnt);
   qmRawPut(13, qmRtAcc, qmRtCnt);
   qmRawPut(10, qmRtAcc, qmRtCnt);
end;

procedure qmRawClose(var qmRcAcc : Integer; var qmRcCnt : Integer);
begin
   while (qmRcCnt>0) do
   qmRawPut(32, qmRcAcc, qmRcCnt);
   CloseFileStream;
end;

procedure qmRawWrite(const qmRwPath : String; var qmRwL : array [0..${rawcap}] of String; const qmRwN : Integer);
begin
   var qmRwAcc : Integer = 0;
   var qmRwCnt : Integer = 0;
   var qmRwK : Integer;
   OpenFileStreamForWrite(qmRwPath);
   for qmRwK:=0 to qmRwN-1 do
   qmRawPutLine(qmRwL[qmRwK], qmRwAcc, qmRwCnt);
   qmRawClose(qmRwAcc, qmRwCnt);
end;

procedure qmRawWriteStr(const qmWsPath : String; const qmWsText : String);
begin
   var qmWsAcc : Integer = 0;
   var qmWsCnt : Integer = 0;
   OpenFileStreamForWrite(qmWsPath);
   qmRawPutStr(qmWsText, qmWsAcc, qmWsCnt);
   qmRawClose(qmWsAcc, qmWsCnt);
end;
