helpers: qmraw
requires: rawcap, inccap, inchead
---
//! `.inc` state files (ref/inc.py is the twin and has the evidence).
//!
//! Reading: the engine's parser drops trailing spaces from Code values
//! (SelfTest run m2a), so an `.inc` is read with the raw reader and the key
//! lines and Code values are taken out of its lines here. The parser stays
//! for files where nothing is lost (qmIncLoad: the SelfTest's own case files).
//!
//! Writing: the parser appends with the key [*] only once (m2a), so an `.inc`
//! is written with the raw writer, in the layout the parser itself writes:
//! section.begin, the key lines with three spaces, the Code form by the number
//! of values (none: no Code line; one: `   Code[*] = <v>`; more: a struct of
//! `      [*] = <v>` lines), section.end and an empty line; CRLF, then 0-3
//! spaces of padding to a whole Integer. Key lines and values are internal
//! strings (~NNN for bytes outside 32..122); a value taken from the parser
//! goes through qmEscape first.
//!
//! Reading:
//!   qmIncLoad       load a file into the named parser qmIlName, cleared
//!                   first; the handle, or 0 when the file does not exist
//!   qmIncScan       where the key lines and the Code values are among raw
//!                   lines L[at..at+n-1]: form 0 no Code, 1 `Code[*] = `,
//!                   2 struct; the values are the lines L[first..first+nv-1]
//!   qmIncValueOf    a value out of its line, for the form
//!   qmIncFromLines  raw lines [0..n-1] -> key lines [0..inchead] and values
//!                   [0..inccap]; nv is -1 when they do not fit
//!   qmIncReadAt     a file's key lines into head and its Code values into a
//!                   caller-owned pool at an offset, in place (no second array):
//!                   n values, -1 the pool is full, -2 no such file; size as for
//!                   qmRawReadAt (below 0: not known)
//!   qmIncHookIndex  where Quartermaster's hook lines go among values
//!                   pool[at..at+n-1] (ref/inc.py hook_index: after the
//!                   routines a state starts with, else 0)
//! Writing (one file at a time):
//!   qmIncBegin      open a file: key lines, the number of values that follow
//!   qmIncLine       the next value
//!   qmIncEnd        close it; 1 when exactly `total` values came, else 0 (the
//!                   layout was chosen for `total`); the bytes written go to
//!                   qmIeBytes, for reading the file back exactly
//!   qmIncRender     all of it for values [0..n-1] of an array
var qmWxAcc : Integer = 0;
var qmWxCnt : Integer = 0;
var qmWxTotal : Integer = 0;
var qmWxDone : Integer = 0;
var qmWxBytes : Integer = 0;

function qmIncLoad(const qmIlName : String; const qmIlPath : String) : Integer;
begin
   var qmIlP : Integer = ParserSelectByKey(qmIlName);
   if (qmIlP=0) then
   qmIlP := ParserCreate(qmIlName);
   ParserClearByHandle(qmIlP);
   if (FileAge(qmIlPath)=-1) then
   Result := 0
   else
   begin
      ParserLoadFromFileByHandle(qmIlP, qmIlPath);
      Result := qmIlP;
   end;
end;

procedure qmIncLstrip(const qmIsS : String; var qmIsOut : String);
begin
   qmIsOut := qmIsS;
   while (SubStr(qmIsOut, 1, 1)=' ') do
   qmIsOut := SubStr(qmIsOut, 2, StrLength(qmIsOut)-1);
end;

procedure qmIncScan(var qmIcL : array [0..${rawcap}] of String; const qmIcAt : Integer; const qmIcN : Integer; var qmIcHead : array [0..${inchead}] of String; var qmIcNh : Integer; var qmIcFirst : Integer; var qmIcNv : Integer; var qmIcForm : Integer);
begin
   var qmIcI : Integer = 1;
   var qmIcT : String;
   var qmIcGo : Boolean = True;
   qmIcNh := 0;
   qmIcNv := 0;
   qmIcForm := 0;
   qmIcFirst := qmIcAt+qmIcN;
   while (qmIcGo) and (qmIcI<qmIcN) do
   begin
      qmIncLstrip(qmIcL[qmIcAt+qmIcI], qmIcT);
      if (SubStr(qmIcT, 1, 19)='Code : struct.begin') then
      begin
         qmIcForm := 2;
         qmIcI := qmIcI+1;
         qmIcFirst := qmIcAt+qmIcI;
         qmIcT := '';
         if (qmIcI<qmIcN) then
         qmIncLstrip(qmIcL[qmIcAt+qmIcI], qmIcT);
         while (qmIcI<qmIcN) and (qmIcT<>'struct.end') do
         begin
            qmIcNv := qmIcNv+1;
            qmIcI := qmIcI+1;
            qmIcT := '';
            if (qmIcI<qmIcN) then
            qmIncLstrip(qmIcL[qmIcAt+qmIcI], qmIcT);
         end;
         qmIcGo := False;
      end
      else
      if (SubStr(qmIcT, 1, 10)='Code[*] = ') then
      begin
         qmIcForm := 1;
         qmIcFirst := qmIcAt+qmIcI;
         qmIcNv := 1;
         qmIcGo := False;
      end
      else
      if (qmIcT='section.end') then
      qmIcGo := False
      else
      begin
         if (qmIcNh<=${inchead}) then
         qmIcHead[qmIcNh] := qmIcL[qmIcAt+qmIcI];
         qmIcNh := qmIcNh+1;
         qmIcI := qmIcI+1;
      end;
   end;
end;

procedure qmIncValueOf(const qmIvS : String; const qmIvForm : Integer; var qmIvOut : String);
begin
   var qmIvAt : Integer;
   var qmIvT : String;
   qmIvOut := '';
   if (qmIvForm=1) then
   begin
      qmIncLstrip(qmIvS, qmIvT);
      qmIvOut := SubStr(qmIvT, 11, StrLength(qmIvT)-10);
   end
   else
   begin
      qmIvAt := StrPos('[*] = ', qmIvS);
      if (qmIvAt>0) then
      qmIvOut := SubStr(qmIvS, qmIvAt+6, StrLength(qmIvS)-qmIvAt-5);
   end;
end;

procedure qmIncFromLines(var qmIfL : array [0..${rawcap}] of String; const qmIfN : Integer; var qmIfHead : array [0..${inchead}] of String; var qmIfNh : Integer; var qmIfV : array [0..${inccap}] of String; var qmIfNv : Integer; var qmIfForm : Integer);
begin
   var qmIfFirst : Integer;
   var qmIfK : Integer;
   var qmIfT : String;
   qmIncScan(qmIfL, 0, qmIfN, qmIfHead, qmIfNh, qmIfFirst, qmIfNv, qmIfForm);
   if (qmIfNv>${inccap}+1) or (qmIfNh>${inchead}+1) then
   qmIfNv := -1
   else
   for qmIfK:=0 to qmIfNv-1 do
   begin
      qmIncValueOf(qmIfL[qmIfFirst+qmIfK], qmIfForm, qmIfT);
      qmIfV[qmIfK] := qmIfT;
   end;
end;

procedure qmIncReadAt(const qmIrPath : String; const qmIrSize : Integer; var qmIrPool : array [0..${rawcap}] of String; const qmIrAt : Integer; var qmIrHead : array [0..${inchead}] of String; var qmIrNh : Integer; var qmIrN : Integer; var qmIrForm : Integer);
begin
   var qmIrCnt : Integer;
   var qmIrFirst : Integer;
   var qmIrK : Integer;
   var qmIrT : String;
   qmIrNh := 0;
   qmIrForm := 0;
   qmRawReadAt(qmIrPath, qmIrSize, qmIrPool, qmIrAt, qmIrCnt);
   if (qmIrCnt<0) then
   qmIrN := qmIrCnt
   else
   begin
      qmIncScan(qmIrPool, qmIrAt, qmIrCnt, qmIrHead, qmIrNh, qmIrFirst, qmIrN, qmIrForm);
      if (qmIrNh>${inchead}+1) then
      qmIrN := -1
      else
      for qmIrK:=0 to qmIrN-1 do
      begin
         qmIncValueOf(qmIrPool[qmIrFirst+qmIrK], qmIrForm, qmIrT);
         qmIrPool[qmIrAt+qmIrK] := qmIrT;
      end;
   end;
end;

procedure qmIncWords(const qmWdS : String; const qmWdIn : Boolean; var qmWdFirst : String; var qmWdOpen : Integer; var qmWdEnd : Integer; var qmWdOut : Boolean);
begin
   var qmWdI : Integer = 1;
   var qmWdJ : Integer;
   var qmWdL : Integer = StrLength(qmWdS);
   var qmWdB : Integer;
   var qmWdC : Integer;
   var qmWdW : String;
   var qmWdE : String;
   var qmWdK : Integer;
   qmWdOut := qmWdIn;
   qmWdFirst := '';
   qmWdOpen := 0;
   qmWdEnd := 0;
   while (qmWdI<=qmWdL) do
   begin
      qmWdB := Ord(SubStr(qmWdS, qmWdI, 1));
      if (qmWdB=126) then
      begin
         qmWdE := SubStr(qmWdS, qmWdI, 4);
         if (qmWdOut) then
         begin
            if (qmWdE='~125') then
            qmWdOut := False;
         end
         else
         if (qmWdE='~123') then
         qmWdOut := True;
         qmWdI := qmWdI+4;
      end
      else
      if (qmWdOut) then
      qmWdI := qmWdI+1
      else
      if (qmWdB=47) and (SubStr(qmWdS, qmWdI+1, 1)='/') then
      qmWdI := qmWdL+1
      else
      if (qmWdB=39) then
      begin
         qmWdI := qmWdI+1;
         while (qmWdI<=qmWdL) and (Ord(SubStr(qmWdS, qmWdI, 1))<>39) do
         qmWdI := qmWdI+1;
         qmWdI := qmWdI+1;
      end
      else
      if (qmWdB=95) or ((qmWdB>=65) and (qmWdB<=90)) or ((qmWdB>=97) and (qmWdB<=122)) or ((qmWdB>=48) and (qmWdB<=57)) then
      begin
         qmWdJ := qmWdI;
         qmWdC := qmWdB;
         while (qmWdJ<=qmWdL) and ((qmWdC=95) or ((qmWdC>=65) and (qmWdC<=90)) or ((qmWdC>=97) and (qmWdC<=122)) or ((qmWdC>=48) and (qmWdC<=57))) do
         begin
            qmWdJ := qmWdJ+1;
            qmWdC := 0;
            if (qmWdJ<=qmWdL) then
            qmWdC := Ord(SubStr(qmWdS, qmWdJ, 1));
         end;
         if (qmWdB<48) or (qmWdB>57) then
         begin
            qmWdW := '';
            for qmWdK:=qmWdI to qmWdJ-1 do
            begin
               qmWdC := Ord(SubStr(qmWdS, qmWdK, 1));
               if (qmWdC>=65) and (qmWdC<=90) then
               qmWdW := qmWdW+SubStr('abcdefghijklmnopqrstuvwxyz', qmWdC-64, 1)
               else
               qmWdW := qmWdW+SubStr(qmWdS, qmWdK, 1);
            end;
            if (qmWdFirst='') then
            qmWdFirst := qmWdW;
            if (qmWdW='begin') or (qmWdW='case') or (qmWdW='try') or (qmWdW='asm') or (qmWdW='record') or (qmWdW='class') then
            qmWdOpen := qmWdOpen+1;
            if (qmWdW='end') then
            qmWdEnd := qmWdEnd+1;
         end;
         qmWdI := qmWdJ;
      end
      else
      qmWdI := qmWdI+1;
   end;
end;

function qmIncBlank(const qmBkS : String) : Boolean;
begin
   var qmBkT : String = qmBkS;
   var qmBkGo : Boolean = True;
   while (qmBkGo) do
   begin
      qmBkGo := False;
      if (SubStr(qmBkT, 1, 1)=' ') then
      begin
         qmBkT := SubStr(qmBkT, 2, StrLength(qmBkT)-1);
         qmBkGo := True;
      end
      else
      if (SubStr(qmBkT, 1, 4)='~009') then
      begin
         qmBkT := SubStr(qmBkT, 5, StrLength(qmBkT)-4);
         qmBkGo := True;
      end
      else
      if (StrLength(qmBkT)>0) and (SubStr(qmBkT, StrLength(qmBkT), 1)=' ') then
      begin
         qmBkT := SubStr(qmBkT, 1, StrLength(qmBkT)-1);
         qmBkGo := True;
      end
      else
      if (StrLength(qmBkT)>=4) and (SubStr(qmBkT, StrLength(qmBkT)-3, 4)='~009') then
      begin
         qmBkT := SubStr(qmBkT, 1, StrLength(qmBkT)-4);
         qmBkGo := True;
      end;
   end;
   var qmBkR : Boolean = (qmBkT='') or (SubStr(qmBkT, 1, 2)='//');
   if (not qmBkR) and (SubStr(qmBkT, 1, 4)='~123') and (StrLength(qmBkT)>=8) then
   if (SubStr(qmBkT, StrLength(qmBkT)-3, 4)='~125') then
   qmBkR := (StrPos('~125', SubStr(qmBkT, 1, StrLength(qmBkT)-4))=0);
   Result := qmBkR;
end;

function qmIncHookIndex(var qmHkL : array [0..${rawcap}] of String; const qmHkAt : Integer; const qmHkN : Integer) : Integer;
begin
   var qmHkI : Integer = 0;
   var qmHkSeen : Boolean = False;
   var qmHkGo : Boolean = True;
   var qmHkInner : Boolean;
   var qmHkDepth : Integer;
   var qmHkOpened : Boolean;
   var qmHkBrace : Boolean;
   var qmHkFirst : String;
   var qmHkOpen : Integer;
   var qmHkEnd : Integer;
   var qmHkT : String;
   while (qmHkGo) and (qmHkI<qmHkN) do
   begin
      qmHkT := qmHkL[qmHkAt+qmHkI];
      if (SubStr(qmHkT, 1, 1)=';') then
      qmHkT := SubStr(qmHkT, 2, StrLength(qmHkT)-1);
      qmIncWords(qmHkT, False, qmHkFirst, qmHkOpen, qmHkEnd, qmHkBrace);
      if (qmHkFirst='procedure') or (qmHkFirst='function') then
      begin
         qmHkSeen := True;
         qmHkDepth := 0;
         qmHkOpened := False;
         qmHkBrace := False;
         qmHkInner := True;
         while (qmHkInner) and (qmHkI<qmHkN) do
         begin
            qmHkT := qmHkL[qmHkAt+qmHkI];
            if (SubStr(qmHkT, 1, 1)=';') then
            qmHkT := SubStr(qmHkT, 2, StrLength(qmHkT)-1);
            qmIncWords(qmHkT, qmHkBrace, qmHkFirst, qmHkOpen, qmHkEnd, qmHkBrace);
            qmHkDepth := qmHkDepth+qmHkOpen-qmHkEnd;
            if (qmHkOpen>0) then
            qmHkOpened := True;
            qmHkI := qmHkI+1;
            if (qmHkOpened) and (qmHkDepth<=0) then
            qmHkInner := False;
         end;
      end
      else
      if (qmHkSeen) and (qmIncBlank(qmHkT)) then
      qmHkI := qmHkI+1
      else
      qmHkGo := False;
   end;
   if (qmHkSeen) then
   Result := qmHkI
   else
   Result := 0;
end;

procedure qmIncBegin(const qmBgPath : String; var qmBgHead : array [0..${inchead}] of String; const qmBgNh : Integer; const qmBgTotal : Integer);
begin
   var qmBgK : Integer;
   var qmBgT : String;
   qmWxAcc := 0;
   qmWxCnt := 0;
   qmWxTotal := qmBgTotal;
   qmWxDone := 0;
   OpenFileStreamForWrite(qmBgPath);
   qmRawPutLine('section.begin', qmWxAcc, qmWxCnt);
   qmWxBytes := 15;
   for qmBgK:=0 to qmBgNh-1 do
   begin
      qmIncLstrip(qmBgHead[qmBgK], qmBgT);
      qmRawPutLine('   '+qmBgT, qmWxAcc, qmWxCnt);
      qmWxBytes := qmWxBytes+qmRawLen(qmBgT)+5;
   end;
   if (qmWxTotal>1) then
   begin
      qmRawPutLine('   Code : struct.begin', qmWxAcc, qmWxCnt);
      qmWxBytes := qmWxBytes+24;
   end;
end;

procedure qmIncLine(const qmIlV : String);
begin
   if (qmWxTotal=1) then
   begin
      qmRawPutLine('   Code[*] = '+qmIlV, qmWxAcc, qmWxCnt);
      qmWxBytes := qmWxBytes+qmRawLen(qmIlV)+15;
   end
   else
   begin
      qmRawPutLine('      [*] = '+qmIlV, qmWxAcc, qmWxCnt);
      qmWxBytes := qmWxBytes+qmRawLen(qmIlV)+14;
   end;
   qmWxDone := qmWxDone+1;
end;

function qmIncEnd(var qmIeBytes : Integer) : Integer;
begin
   if (qmWxTotal>1) then
   begin
      qmRawPutLine('   struct.end', qmWxAcc, qmWxCnt);
      qmWxBytes := qmWxBytes+15;
   end;
   qmRawPutLine('section.end', qmWxAcc, qmWxCnt);
   qmRawPutLine('', qmWxAcc, qmWxCnt);
   qmWxBytes := qmWxBytes+15;
   while (qmWxBytes mod 4<>0) do
   qmWxBytes := qmWxBytes+1;
   qmRawClose(qmWxAcc, qmWxCnt);
   qmIeBytes := qmWxBytes;
   if (qmWxDone=qmWxTotal) then
   Result := 1
   else
   Result := 0;
end;

procedure qmIncRender(const qmIdPath : String; var qmIdHead : array [0..${inchead}] of String; const qmIdNh : Integer; var qmIdV : array [0..${inccap}] of String; const qmIdN : Integer; var qmIdBytes : Integer);
begin
   var qmIdK : Integer;
   qmIncBegin(qmIdPath, qmIdHead, qmIdNh, qmIdN);
   for qmIdK:=0 to qmIdN-1 do
   qmIncLine(qmIdV[qmIdK]);
   qmIncEnd(qmIdBytes);
end;
