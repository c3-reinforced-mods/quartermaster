state: qmConflictsCode
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qmraw, qminc
requires: rawcap, inccap, inchead
---
//! The conflict report's look into the vanilla files (ref/conflicts.py
//! routines, where, at_text): qmConflicts runs it once, when a record has
//! asked (qm_conf rn; rp<q> the file, rs<q> re<q> the vanilla range), and
//! it answers each ask with rpl<q> - `state <Name>, ` and the routines -
//! and rat<q>, the vanilla line. Each file is read once, as the game side
//! reads an .inc (qmIncReadAt); the asks of one file come one after another.
//! It holds the read pool of 65536 lines, which is why it is a state of
//! its own (qmConflicts says so).
//!
//! Limits of the game side the twin does not have: 1024 words on a Code
//! line and routines in a file, 256 nested routines, Code values of a
//! file beyond inccap+1 scanned as main code.
var qmXcC : Integer = ParserSelectByKey('qm_conf');
var qmXcApp : String = ExtractFilePath(GetApplicationFileName);
var qmXcPool : array [0..${rawcap}] of String;
var qmXcHead : array [0..${inchead}] of String;
var qmXcRt : array [0..${inccap}] of Integer;
var qmXcRn : array [0..1023] of String;
var qmXcW : array [0..1023] of String;
var qmXcSk : array [0..255] of Integer;
var qmXcSs : array [0..255] of Integer;
var qmXcSd : array [0..255] of Integer;
var qmXcVals : Integer = 0;
var qmXcNv : Integer = 0;
var qmXcState : String = '';
var qmXcLoaded : String = '';
var qmXcScanned : Boolean = False;
var qmXcQ : Integer;
var qmXcPath : String;
var qmXcPl : String;
var qmXcAt : String;

//! The words of Code value qmZhS (an internal string) in order, as written,
//! into qmXcW[0..qmZhN-1] (ref/inc.py code_words with keep_case): outside
//! `//` comments, `{ }` comments - ~123 and ~125 here, as they may span
//! lines - and string literals.
procedure qmZhWords(const qmZhS : String; const qmZhIn : Boolean; var qmZhN : Integer; var qmZhOut : Boolean);
begin
   var qmZhI : Integer = 1;
   var qmZhJ : Integer;
   var qmZhL : Integer = StrLength(qmZhS);
   var qmZhB : Integer;
   var qmZhC : Integer;
   var qmZhE : String;
   qmZhOut := qmZhIn;
   qmZhN := 0;
   while (qmZhI<=qmZhL) do
   begin
      qmZhB := Ord(SubStr(qmZhS, qmZhI, 1));
      if (qmZhB=126) then
      begin
         qmZhE := SubStr(qmZhS, qmZhI, 4);
         if (qmZhOut) then
         begin
            if (qmZhE='~125') then
            qmZhOut := False;
         end
         else
         if (qmZhE='~123') then
         qmZhOut := True;
         qmZhI := qmZhI+4;
      end
      else
      if (qmZhOut) then
      qmZhI := qmZhI+1
      else
      if (qmZhB=47) and (SubStr(qmZhS, qmZhI+1, 1)='/') then
      qmZhI := qmZhL+1
      else
      if (qmZhB=39) then
      begin
         qmZhI := qmZhI+1;
         while (qmZhI<=qmZhL) and (Ord(SubStr(qmZhS, qmZhI, 1))<>39) do
         qmZhI := qmZhI+1;
         qmZhI := qmZhI+1;
      end
      else
      if (qmZhB=95) or ((qmZhB>=65) and (qmZhB<=90)) or ((qmZhB>=97) and (qmZhB<=122)) or ((qmZhB>=48) and (qmZhB<=57)) then
      begin
         qmZhJ := qmZhI;
         qmZhC := qmZhB;
         while (qmZhJ<=qmZhL) and ((qmZhC=95) or ((qmZhC>=65) and (qmZhC<=90)) or ((qmZhC>=97) and (qmZhC<=122)) or ((qmZhC>=48) and (qmZhC<=57))) do
         begin
            qmZhJ := qmZhJ+1;
            qmZhC := 0;
            if (qmZhJ<=qmZhL) then
            qmZhC := Ord(SubStr(qmZhS, qmZhJ, 1));
         end;
         if ((qmZhB<48) or (qmZhB>57)) and (qmZhN<1024) then
         begin
            qmXcW[qmZhN] := SubStr(qmZhS, qmZhI, qmZhJ-qmZhI);
            qmZhN := qmZhN+1;
         end;
         qmZhI := qmZhJ;
      end
      else
      qmZhI := qmZhI+1;
   end;
end;

//! The routine of every Code value of the file in the pool (ref/conflicts.py
//! routines): qmXcRt[k] an index into qmXcRn (`procedure X`), -1 main code.
procedure qmZiScan;
begin
   var qmZiD : Integer = 0;
   var qmZiTop : Integer = 0;
   var qmZiNr : Integer = 0;
   var qmZiBrace : Boolean = False;
   var qmZiK : Integer;
   var qmZiW : Integer;
   var qmZiN : Integer;
   var qmZiHere : Integer;
   var qmZiT : String;
   var qmZiL : String;
   for qmZiK:=0 to qmXcNv-1 do
   begin
      qmZiT := qmXcPool[qmZiK];
      if (SubStr(qmZiT, 1, 1)=';') then
      qmZiT := SubStr(qmZiT, 2, StrLength(qmZiT)-1);
      qmZhWords(qmZiT, qmZiBrace, qmZiN, qmZiBrace);
      qmZiHere := -1;
      for qmZiW:=0 to qmZiN-1 do
      begin
         qmLowerAscii(qmXcW[qmZiW], qmZiL);
         if ((qmZiL='procedure') or (qmZiL='function')) and (qmZiW+1<qmZiN) then
         begin
            if (qmZiTop<256) and (qmZiNr<1024) then
            begin
               qmXcRn[qmZiNr] := qmZiL+' '+qmXcW[qmZiW+1];
               qmXcSk[qmZiTop] := qmZiNr;
               qmXcSs[qmZiTop] := 0;
               qmXcSd[qmZiTop] := qmZiD;
               qmZiHere := qmZiNr;
               qmZiNr := qmZiNr+1;
               qmZiTop := qmZiTop+1;
            end;
         end
         else
         if (qmZiL='begin') then
         begin
            qmZiD := qmZiD+1;
            if (qmZiTop>0) then
            if (qmXcSs[qmZiTop-1]=0) and (qmZiD=qmXcSd[qmZiTop-1]+1) then
            qmXcSs[qmZiTop-1] := 1;
         end
         else
         if (qmZiL='case') or (qmZiL='try') or (qmZiL='record') or (qmZiL='asm') then
         qmZiD := qmZiD+1
         else
         if (qmZiL='end') then
         begin
            qmZiD := qmZiD-1;
            if (qmZiTop>0) then
            if (qmXcSs[qmZiTop-1]=1) and (qmZiD=qmXcSd[qmZiTop-1]) then
            begin
               if (qmZiHere<0) then
               qmZiHere := qmXcSk[qmZiTop-1];
               qmZiTop := qmZiTop-1;
            end;
         end;
      end;
      if (qmZiHere<0) and (qmZiTop>0) then
      qmZiHere := qmXcSk[qmZiTop-1];
      qmXcRt[qmZiK] := qmZiHere;
   end;
   qmXcScanned := True;
end;

//! The vanilla .inc into the pool, as the game side reads it (qmIncReadAt):
//! its Code values and the state's `Name = `.
procedure qmZjLoad(const qmZjPath : String);
begin
   var qmZjNh : Integer = 0;
   var qmZjForm : Integer = 0;
   var qmZjK : Integer;
   var qmZjT : String;
   qmXcLoaded := qmZjPath;
   qmXcScanned := False;
   qmXcState := '';
   qmIncReadAt(qmXcApp+'data\'+qmZjPath, -1, qmXcPool, 0, qmXcHead, qmZjNh, qmXcVals, qmZjForm);
   if (qmXcVals<0) then
   qmXcVals := 0;
   qmXcNv := qmXcVals;
   if (qmXcNv>${inccap}+1) then
   qmXcNv := ${inccap}+1;
   for qmZjK:=qmZjNh-1 downto 0 do
   if (qmZjK<=${inchead}) then
   begin
      qmIncLstrip(qmXcHead[qmZjK], qmZjT);
      if (SubStr(qmZjT, 1, 7)='Name = ') then
      qmXcState := SubStr(qmZjT, 8, StrLength(qmZjT)-7);
   end;
end;

//! The routines of the vanilla range [qmZkS, qmZkE), each once, in order
//! (ref/conflicts.py where), behind the state's name.
procedure qmZkPlace(const qmZkS : Integer; const qmZkE : Integer; var qmZkOut : String);
begin
   var qmZkA : Integer = qmZkS;
   var qmZkB : Integer = qmZkE;
   var qmZkK : Integer;
   var qmZkI : Integer;
   var qmZkN : String;
   var qmZkSeen : String = '|';
   if (not qmXcScanned) then
   qmZiScan;
   qmZkOut := '';
   if (qmXcNv=0) then
   qmZkOut := 'main code'
   else
   begin
      if (qmZkB<=qmZkA) then
      begin
         qmZkA := qmZkS-1;
         if (qmZkA<0) then
         qmZkA := 0;
         qmZkB := qmZkA+1;
      end;
      for qmZkK:=qmZkA to qmZkB-1 do
      begin
         qmZkI := qmZkK;
         if (qmZkI>qmXcNv-1) then
         qmZkI := qmXcNv-1;
         if (qmXcRt[qmZkI]<0) then
         qmZkN := 'main code'
         else
         qmZkN := qmXcRn[qmXcRt[qmZkI]];
         if (StrPos('|'+qmZkN+'|', qmZkSeen)=0) then
         begin
            qmZkSeen := qmZkSeen+qmZkN+'|';
            if (qmZkOut<>'') then
            qmZkOut := qmZkOut+', ';
            qmZkOut := qmZkOut+qmZkN;
         end;
      end;
   end;
   if (qmXcState<>'') then
   qmZkOut := 'state '+qmXcState+', '+qmZkOut;
end;

//! The vanilla line at qmZlS, its leading `;` and the spaces and tabs around
//! it cut, at most 60 bytes of it (ref/conflicts.py at_text, AT_CHARS); the
//! value is an internal string, so a ~NNN counts as one byte.
procedure qmZlAt(const qmZlS : Integer; var qmZlOut : String);
begin
   var qmZlT : String;
   var qmZlGo : Boolean = True;
   var qmZlI : Integer;
   var qmZlN : Integer;
   if (qmZlS>=qmXcVals) then
   qmZlOut := '(end of file)'
   else
   begin
      qmZlT := qmXcPool[qmZlS];
      if (SubStr(qmZlT, 1, 1)=';') then
      qmZlT := SubStr(qmZlT, 2, StrLength(qmZlT)-1);
      while (qmZlGo) do
      begin
         qmZlGo := False;
         if (SubStr(qmZlT, 1, 1)=' ') then
         begin
            qmZlT := SubStr(qmZlT, 2, StrLength(qmZlT)-1);
            qmZlGo := True;
         end
         else
         if (SubStr(qmZlT, 1, 4)='~009') then
         begin
            qmZlT := SubStr(qmZlT, 5, StrLength(qmZlT)-4);
            qmZlGo := True;
         end
         else
         if (StrLength(qmZlT)>0) and (SubStr(qmZlT, StrLength(qmZlT), 1)=' ') then
         begin
            qmZlT := SubStr(qmZlT, 1, StrLength(qmZlT)-1);
            qmZlGo := True;
         end
         else
         if (StrLength(qmZlT)>=4) and (SubStr(qmZlT, StrLength(qmZlT)-3, 4)='~009') then
         begin
            qmZlT := SubStr(qmZlT, 1, StrLength(qmZlT)-4);
            qmZlGo := True;
         end;
      end;
      if (qmRawLen(qmZlT)>60) then
      begin
         qmZlI := 1;
         qmZlN := 0;
         while (qmZlN<57) do
         begin
            if (SubStr(qmZlT, qmZlI, 1)='~') then
            qmZlI := qmZlI+4
            else
            qmZlI := qmZlI+1;
            qmZlN := qmZlN+1;
         end;
         qmZlT := SubStr(qmZlT, 1, qmZlI-1)+'...';
      end;
      qmZlOut := qmZlT;
   end;
end;

if (qmXcC=0) then
exit;
for qmXcQ:=0 to ParserGetIntValueByKeyByHandle(qmXcC, 'rn')-1 do
begin
   qmXcPath := ParserGetValueByKeyByHandle(qmXcC, 'rp'+IntToStr(qmXcQ));
   if (qmXcPath<>qmXcLoaded) then
   qmZjLoad(qmXcPath);
   qmZkPlace(ParserGetIntValueByKeyByHandle(qmXcC, 'rs'+IntToStr(qmXcQ)), ParserGetIntValueByKeyByHandle(qmXcC, 're'+IntToStr(qmXcQ)), qmXcPl);
   qmZlAt(ParserGetIntValueByKeyByHandle(qmXcC, 'rs'+IntToStr(qmXcQ)), qmXcAt);
   ParserSetValueByKeyByHandle(qmXcC, 'rpl'+IntToStr(qmXcQ), qmXcPl);
   ParserSetValueByKeyByHandle(qmXcC, 'rat'+IntToStr(qmXcQ), qmXcAt);
end;
