helpers: qmstr
requires:
---
//! qmNormDir: a mod dir as Quartermaster compares it - ref/order.py norm_dir:
//! slashes as backslashes, no trailing backslash, ASCII case folded (Windows
//! folder names are case-insensitive; the engine's StrToLowerCase is not
//! trusted beyond ASCII). The same steps qmModList takes for its sort key.
procedure qmNormDir(const qmNdS : String; var qmNdOut : String);
begin
   var qmNdT : String = qmNdS;
   while (StrPos('/', qmNdT)>0) do
   qmNdT := StrReplace(qmNdT, '/', '\');
   while (StrLength(qmNdT)>0) and (SubStr(qmNdT, StrLength(qmNdT), 1)='\') do
   qmNdT := SubStr(qmNdT, 1, StrLength(qmNdT)-1);
   qmLowerAscii(qmNdT, qmNdOut);
end;
