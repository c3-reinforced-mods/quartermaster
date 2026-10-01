helpers:
requires:
---
//! The key a line is compared by (ref/textio.py `norm_key_escaped`), on the
//! internal form: the BOM ~239~187~191 dropped from a file's first line, every
//! tab (~009) read as a space, trailing spaces removed. Only comparison uses
//! it; what is written is always the bytes of the line that was chosen.
//!
//! A plain replace of ~009 cannot cut into another escape: every `~` in an
//! internal string starts one. The loop repeats the replace in case
//! StrReplace replaces only the first match; a space cannot recreate ~009.
procedure qmNormKey(const qmNkS : String; const qmNkFirst : Boolean; var qmNkOut : String);
begin
   var qmNkT : String = qmNkS;
   var qmNkL : Integer;
   var qmNkGuard : Integer = 0;
   if (qmNkFirst) and (SubStr(qmNkT, 1, 12)='~239~187~191') then
   qmNkT := SubStr(qmNkT, 13, StrLength(qmNkT)-12);
   while (StrPos('~009', qmNkT)>0) and (qmNkGuard<100000) do
   begin
      qmNkT := StrReplace(qmNkT, '~009', ' ');
      qmNkGuard := qmNkGuard+1;
   end;
   qmNkL := StrLength(qmNkT);
   while (qmNkL>0) and (SubStr(qmNkT, qmNkL, 1)=' ') do
   qmNkL := qmNkL-1;
   if (qmNkL=0) then
   qmNkOut := ''
   else
   qmNkOut := SubStr(qmNkT, 1, qmNkL);
end;
