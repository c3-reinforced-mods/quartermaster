helpers:
requires:
---
//! String helpers. The engine has no Chr, so a byte becomes text only through a
//! table (`SubStr(table, i, 1)`) and text becomes a byte through
//! `Ord(SubStr(s, i, 1))` - both verified in the raw-IO probe. A nested
//! function returning String does not compile at state level (capability
//! probes, 2026-09-28), so every routine here that makes a String hands it
//! back through its last, `var` parameter. Each routine keeps its own
//! parameter and local names (qmXx...), so no two routines of one state ever
//! declare the same name.
//!
//! qmEscape     an engine string (any bytes) as an internal string: bytes
//!              32..122 as they are, every other byte as ~NNN - the form the
//!              raw reader produces and the raw writer consumes (ref/textio.py)
//! qmHex        two lower-case hex digits per byte: how dumps carry strings
//!              that come from the engine or a mod, so no byte in them can be
//!              mistaken for a field separator
//! qmLowerAscii A..Z to a..z and nothing else, the case folding ref/order.py
//!              uses; the engine's StrToLowerCase is not trusted beyond ASCII
//! qmCmpStr     -1, 0 or 1: byte-wise comparison, shorter first on a tie, like
//!              Python's comparison of bytes
//! qmField      the k-th (0-based) field of a string split at a one-character
//!              separator; '' when there are fewer fields
//! qmIsDigits   non-empty and only 0..9
procedure qmEscape(const qmEsS : String; var qmEsOut : String);
begin
   var qmEsI : Integer;
   var qmEsC : String;
   var qmEsB : Integer;
   var qmEsD : String;
   qmEsOut := '';
   for qmEsI:=1 to StrLength(qmEsS) do
   begin
      qmEsC := SubStr(qmEsS, qmEsI, 1);
      qmEsB := Ord(qmEsC);
      if (qmEsB>=32) and (qmEsB<=122) then
      qmEsOut := qmEsOut+qmEsC
      else
      begin
         qmEsD := IntToStr(qmEsB);
         while (StrLength(qmEsD)<3) do
         qmEsD := '0'+qmEsD;
         qmEsOut := qmEsOut+'~'+qmEsD;
      end;
   end;
end;

procedure qmHex(const qmHxS : String; var qmHxOut : String);
begin
   var qmHxI : Integer;
   var qmHxB : Integer;
   qmHxOut := '';
   for qmHxI:=1 to StrLength(qmHxS) do
   begin
      qmHxB := Ord(SubStr(qmHxS, qmHxI, 1));
      qmHxOut := qmHxOut+SubStr('0123456789abcdef', (qmHxB div 16)+1, 1)+SubStr('0123456789abcdef', (qmHxB mod 16)+1, 1);
   end;
end;

procedure qmLowerAscii(const qmLaS : String; var qmLaOut : String);
begin
   var qmLaI : Integer;
   var qmLaC : String;
   var qmLaP : Integer;
   qmLaOut := '';
   for qmLaI:=1 to StrLength(qmLaS) do
   begin
      qmLaC := SubStr(qmLaS, qmLaI, 1);
      qmLaP := StrPos(qmLaC, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ');
      if (qmLaP>0) then
      qmLaC := SubStr('abcdefghijklmnopqrstuvwxyz', qmLaP, 1);
      qmLaOut := qmLaOut+qmLaC;
   end;
end;

function qmCmpStr(const qmCsA : String; const qmCsB : String) : Integer;
begin
   var qmCsLa : Integer = StrLength(qmCsA);
   var qmCsLb : Integer = StrLength(qmCsB);
   var qmCsI : Integer = 1;
   var qmCsR : Integer = 0;
   var qmCsX : Integer;
   var qmCsY : Integer;
   while (qmCsR=0) and (qmCsI<=qmCsLa) and (qmCsI<=qmCsLb) do
   begin
      qmCsX := Ord(SubStr(qmCsA, qmCsI, 1));
      qmCsY := Ord(SubStr(qmCsB, qmCsI, 1));
      if (qmCsX<qmCsY) then
      qmCsR := -1
      else
      if (qmCsX>qmCsY) then
      qmCsR := 1;
      qmCsI := qmCsI+1;
   end;
   if (qmCsR=0) then
   begin
      if (qmCsLa<qmCsLb) then
      qmCsR := -1
      else
      if (qmCsLa>qmCsLb) then
      qmCsR := 1;
   end;
   Result := qmCsR;
end;

procedure qmField(const qmFdS : String; const qmFdSep : String; const qmFdK : Integer; var qmFdOut : String);
begin
   var qmFdRest : String = qmFdS;
   var qmFdI : Integer = 0;
   var qmFdP : Integer = StrPos(qmFdSep, qmFdRest);
   while (qmFdI<qmFdK) and (qmFdP>0) do
   begin
      qmFdRest := SubStr(qmFdRest, qmFdP+1, StrLength(qmFdRest)-qmFdP);
      qmFdI := qmFdI+1;
      qmFdP := StrPos(qmFdSep, qmFdRest);
   end;
   if (qmFdI<qmFdK) then
   qmFdOut := ''
   else
   if (qmFdP>0) then
   qmFdOut := SubStr(qmFdRest, 1, qmFdP-1)
   else
   qmFdOut := qmFdRest;
end;

function qmIsDigits(const qmIdS : String) : Boolean;
begin
   var qmIdOk : Boolean = (StrLength(qmIdS)>0);
   var qmIdI : Integer;
   for qmIdI:=1 to StrLength(qmIdS) do
   if (StrPos(SubStr(qmIdS, qmIdI, 1), '0123456789')=0) then
   qmIdOk := False;
   Result := qmIdOk;
end;
