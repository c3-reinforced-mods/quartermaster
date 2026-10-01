helpers:
requires:
---
//! The named-parser key a vanilla path is looked up by (ref/index.py
//! `index_key` is the twin; change both or neither). The engine's parser folds
//! the case of keys and trims them (capability probes), so only
//! identifier-like keys are safe: `k`, then a..z and 0..9 as they are, `\` as
//! `_s`, `.` as `_d`, `_` as `__` and any other byte as `_x` plus two hex
//! digits. Every `_` starts one of those four codes, so two paths never share
//! a key: gui\menu.inc\oncamera.inc -> kgui_smenu_dinc_soncamera_dinc.
procedure qmIdxKey(const qmIkPath : String; var qmIkOut : String);
begin
   var qmIkI : Integer;
   var qmIkC : String;
   var qmIkB : Integer;
   qmIkOut := 'k';
   for qmIkI:=1 to StrLength(qmIkPath) do
   begin
      qmIkC := SubStr(qmIkPath, qmIkI, 1);
      qmIkB := Ord(qmIkC);
      if ((qmIkB>=97) and (qmIkB<=122)) or ((qmIkB>=48) and (qmIkB<=57)) then
      qmIkOut := qmIkOut+qmIkC
      else
      if (qmIkB=92) then
      qmIkOut := qmIkOut+'_s'
      else
      if (qmIkB=46) then
      qmIkOut := qmIkOut+'_d'
      else
      if (qmIkB=95) then
      qmIkOut := qmIkOut+'__'
      else
      qmIkOut := qmIkOut+'_x'+SubStr('0123456789abcdef', (qmIkB div 16)+1, 1)+SubStr('0123456789abcdef', (qmIkB mod 16)+1, 1);
   end;
end;
