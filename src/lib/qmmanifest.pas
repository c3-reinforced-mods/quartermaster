helpers:
requires:
---
//! Reading the manifest back (ref/manifest.py has the format). It is read
//! with the raw reader like every .inc Quartermaster reads (qmWrReadManifest),
//! so its values are internal strings, in which the field separator `|`
//! (124, outside the character table) stands as ~124. No path, token or hex
//! field can hold a `~`: the writer refuses such a path (qmWrCheckPath), and
//! the rest are digits, `-` and hex.
//!
//! qmMqField  the k-th (0-based) ~124-separated field; '' when there are fewer
procedure qmMqField(const qmMqS : String; const qmMqK : Integer; var qmMqOut : String);
begin
   var qmMqRest : String = qmMqS;
   var qmMqI : Integer = 0;
   var qmMqP : Integer = StrPos('~124', qmMqRest);
   while (qmMqI<qmMqK) and (qmMqP>0) do
   begin
      qmMqRest := SubStr(qmMqRest, qmMqP+4, StrLength(qmMqRest)-qmMqP-3);
      qmMqI := qmMqI+1;
      qmMqP := StrPos('~124', qmMqRest);
   end;
   if (qmMqI<qmMqK) then
   qmMqOut := ''
   else
   if (qmMqP>0) then
   qmMqOut := SubStr(qmMqRest, 1, qmMqP-1)
   else
   qmMqOut := qmMqRest;
end;
