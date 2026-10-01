helpers:
requires: h1mul, h1mod, h2mul, h2mod
---
//! The hash of ref/fingerprint.py (`qhash`): two polynomial hashes modulo
//! primes chosen so that `h*mul + 256` stays below 2^31, plus the byte count.
//! Integer arithmetic wraps silently in this engine (capability probes), so
//! the bound is what keeps the game side equal to the twin, not a guard
//! against a crash. The constants come from ref/fingerprint.py through the
//! build, so there is one definition of them.
//!
//! A hash is three Integers the caller keeps (h1, h2, length); qmHashByte and
//! qmHashStr feed bytes in, qmHashText renders `<h1>-<h2>-<length>`.
procedure qmHashByte(const qmHbB : Integer; var qmHbH1 : Integer; var qmHbH2 : Integer; var qmHbL : Integer);
begin
   qmHbH1 := (qmHbH1*${h1mul}+qmHbB+1) mod ${h1mod};
   qmHbH2 := (qmHbH2*${h2mul}+qmHbB+1) mod ${h2mod};
   qmHbL := qmHbL+1;
end;

procedure qmHashStr(const qmHsS : String; var qmHsH1 : Integer; var qmHsH2 : Integer; var qmHsL : Integer);
begin
   var qmHsI : Integer;
   var qmHsB : Integer;
   for qmHsI:=1 to StrLength(qmHsS) do
   begin
      qmHsB := Ord(SubStr(qmHsS, qmHsI, 1));
      qmHsH1 := (qmHsH1*${h1mul}+qmHsB+1) mod ${h1mod};
      qmHsH2 := (qmHsH2*${h2mul}+qmHsB+1) mod ${h2mod};
   end;
   qmHsL := qmHsL+StrLength(qmHsS);
end;

procedure qmHashText(const qmHtH1 : Integer; const qmHtH2 : Integer; const qmHtL : Integer; var qmHtOut : String);
begin
   qmHtOut := IntToStr(qmHtH1)+'-'+IntToStr(qmHtH2)+'-'+IntToStr(qmHtL);
end;
