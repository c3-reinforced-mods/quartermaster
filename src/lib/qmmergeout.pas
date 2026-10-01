helpers: qminc, qmdiffsrc
requires:
---
//! The write seam of the merge: the one place a merge result becomes a file.
//! qmmerge.pas hands over the final line list in order - qmMgOutBegin with the
//! path, the template whose key lines the output takes (0 vanilla's for a
//! merge, 1 the winner's for winner-takes-all; qmdiffsrc.pas qmLnKeep) and the
//! number of lines, one qmMgOutLine per line, then qmMgOutEnd - and never
//! writes anything itself.
//!
//! Written with the raw writer, streamed (qminc.pas qmIncBegin/Line/End): the
//! engine's own layout for the number of values (none: no Code line, one:
//! `Code[*] = `, more: a struct), CRLF, padded with spaces to a multiple of 4
//! bytes - ref/merge.py merge_inc(..., writer="raw"), ref/inc.py render_raw.
//! Decided 2026-09-28: the parser appends a value only once (run m2a),
//! so it cannot write a result longer than the file it loaded plus one line.
//!
//! qmMgOutEnd: 1 when exactly the announced number of lines came, else 0; the
//! bytes written go to qmOeBytes.
procedure qmMgOutBegin(const qmObPath : String; const qmObSlot : Integer; const qmObTotal : Integer);
begin
   if (qmObSlot=0) then
   qmIncBegin(qmObPath, qmLnTplV, qmLnNtV, qmObTotal)
   else
   qmIncBegin(qmObPath, qmLnTplW, qmLnNtW, qmObTotal);
end;

procedure qmMgOutLine(const qmOlV : String);
begin
   qmIncLine(qmOlV);
end;

function qmMgOutEnd(var qmOeBytes : Integer) : Integer;
begin
   Result := qmIncEnd(qmOeBytes);
end;
