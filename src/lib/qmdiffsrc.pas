helpers: qminc
requires: rawcap, inchead
---
//! The read seam of the diff and the merge. Every file they read is opened
//! with qmLnOpen and every line comes through qmLnRead, and the comparison key
//! of a line (qmLnHash, qmLnKey) is defined here because it depends on how a
//! line is represented. qmdiff.pas and qmmerge.pas never touch a file.
//!
//! Files are read with the raw reader (qminc.pas qmIncReadAt, the handle
//! reader for a size not known in advance), which is lossless: the engine's
//! parser would drop trailing spaces from values (SelfTest run m2a). All the
//! files of one merge share ONE pool, qmLnPool, and a source is the offset of
//! its first line there: vanilla, every participant, the hook lines, and the
//! merged result laid out for the hook index (qmmerge.pas). One String array
//! costs about 4.6 us per element on every call of the state that declares it
//! (probe 4) - 0.3 s for this one - so the pool is the only String array of
//! the merge, and a caller merges a batch of files per call.
//!
//! Lines are internal strings: bytes 32..122 as they are, every other byte as
//! ~NNN (ref/textio.py), and `~` always starts one. The key is ref/textio.py
//! norm_key_escaped: the BOM ~239~187~191 dropped from a file's first line, a
//! tab (~009) read as a space, trailing spaces removed (CR never reaches an
//! internal string).
//!
//! qmLnReset   empty the pool (a new merge)
//! qmLnOpen    read a file into the pool: its source and value count, or
//!             -2 (no such file) / -1 (the pool is full); its key lines are
//!             left in qmLnHead/qmLnNh until the next file
//! qmLnKeep    keep the key lines of the file just read as template 0
//!             (vanilla's) or 1 (the winner's): the output takes its layout
//! qmLnPut     append a line to the pool (the merged result); 0 when full
//! qmLnRead    line qmLrI of a source
//! qmLnHash    the hash of a line's key (24 bits, so `*31` never overflows);
//!             qmLhFirst = 1 for a file's line 0, the only one whose BOM goes
//! qmLnKey     the key itself, for the exact comparison behind an equal hash
var qmLnPool : array [0..${rawcap}] of String;
var qmLnTop : Integer = 0;
var qmLnHead : array [0..${inchead}] of String;
var qmLnNh : Integer = 0;
var qmLnForm : Integer = 0;
var qmLnTplV : array [0..${inchead}] of String;
var qmLnNtV : Integer = 0;
var qmLnTplW : array [0..${inchead}] of String;
var qmLnNtW : Integer = 0;

procedure qmLnReset;
begin
   qmLnTop := 0;
   qmLnNh := 0;
   qmLnNtV := 0;
   qmLnNtW := 0;
end;

procedure qmLnOpen(const qmLoPath : String; var qmLoSrc : Integer; var qmLoN : Integer);
begin
   qmLoSrc := qmLnTop;
   qmIncReadAt(qmLoPath, -1, qmLnPool, qmLnTop, qmLnHead, qmLnNh, qmLoN, qmLnForm);
   if (qmLoN>=0) then
   qmLnTop := qmLnTop+qmLoN;
end;

procedure qmLnKeep(const qmLpSlot : Integer);
begin
   var qmLpK : Integer;
   for qmLpK:=0 to qmLnNh-1 do
   if (qmLpSlot=0) then
   qmLnTplV[qmLpK] := qmLnHead[qmLpK]
   else
   qmLnTplW[qmLpK] := qmLnHead[qmLpK];
   if (qmLpSlot=0) then
   qmLnNtV := qmLnNh
   else
   qmLnNtW := qmLnNh;
end;

function qmLnPut(const qmLuS : String) : Integer;
begin
   Result := 0;
   if (qmLnTop<=${rawcap}) then
   begin
      qmLnPool[qmLnTop] := qmLuS;
      qmLnTop := qmLnTop+1;
      Result := 1;
   end;
end;

procedure qmLnRead(const qmLrSrc : Integer; const qmLrI : Integer; var qmLrOut : String);
begin
   qmLrOut := qmLnPool[qmLrSrc+qmLrI];
end;

//! First (1): a leading ~239~187~191 is not part of the key. The key ends
//! where only spaces and ~009 remain.
procedure qmLnSpan(const qmLzS : String; const qmLzFirst : Integer; var qmLzA : Integer; var qmLzL : Integer);
begin
   var qmLzGo : Boolean = True;
   qmLzA := 1;
   qmLzL := StrLength(qmLzS);
   if (qmLzFirst=1) and (SubStr(qmLzS, 1, 12)='~239~187~191') then
   qmLzA := 13;
   while (qmLzGo) and (qmLzL>=qmLzA) do
   begin
      if (SubStr(qmLzS, qmLzL, 1)=' ') then
      qmLzL := qmLzL-1
      else
      if (qmLzL-3>=qmLzA) and (SubStr(qmLzS, qmLzL-3, 4)='~009') then
      qmLzL := qmLzL-4
      else
      qmLzGo := False;
   end;
end;

function qmLnHash(const qmLhS : String; const qmLhFirst : Integer) : Integer;
begin
   var qmLhA : Integer;
   var qmLhL : Integer;
   var qmLhI : Integer;
   var qmLhB : Integer;
   var qmLhH : Integer = 0;
   var qmLhC : String;
   qmLnSpan(qmLhS, qmLhFirst, qmLhA, qmLhL);
   qmLhI := qmLhA;
   while (qmLhI<=qmLhL) do
   begin
      qmLhC := SubStr(qmLhS, qmLhI, 1);
      if (qmLhC='~') and (SubStr(qmLhS, qmLhI, 4)='~009') then
      begin
         qmLhB := 32;
         qmLhI := qmLhI+4;
      end
      else
      begin
         qmLhB := Ord(qmLhC);
         qmLhI := qmLhI+1;
      end;
      qmLhH := ((qmLhH*31)+qmLhB) and 16777215;
   end;
   Result := qmLhH;
end;

procedure qmLnKey(const qmLkS : String; const qmLkFirst : Integer; var qmLkOut : String);
begin
   var qmLkA : Integer;
   var qmLkL : Integer;
   var qmLkI : Integer;
   var qmLkC : String;
   qmLkOut := '';
   qmLnSpan(qmLkS, qmLkFirst, qmLkA, qmLkL);
   qmLkI := qmLkA;
   while (qmLkI<=qmLkL) do
   begin
      qmLkC := SubStr(qmLkS, qmLkI, 1);
      if (qmLkC='~') and (SubStr(qmLkS, qmLkI, 4)='~009') then
      begin
         qmLkOut := qmLkOut+' ';
         qmLkI := qmLkI+4;
      end
      else
      begin
         qmLkOut := qmLkOut+qmLkC;
         qmLkI := qmLkI+1;
      end;
   end;
end;
