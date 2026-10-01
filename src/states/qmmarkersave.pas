state: qmMarkerSave
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qminc
requires: inchead
---
//! qm_state into <save>\quartermaster\state.cfg (plan S8; ref/boot.py
//! render_marker is the twin, byte for byte). The raw writer in the engine's
//! layout: `Name = qmState`, then the Code values of the format in
//! ref/boot.py, each an internal string - `|` is outside the character table
//! and goes out as ~124 (qmEscape), so the bytes are exactly the text. The
//! FileStream writer creates the missing folder (capability probe 2).
procedure qmMvPut(const qmMpV : String);
begin
   var qmMpE : String;
   qmEscape(qmMpV, qmMpE);
   qmIncLine(qmMpE);
end;

var qmMvSt : Integer = ParserSelectByKey('qm_state');
var qmMvHead : array [0..${inchead}] of String;
var qmMvOn : Integer = ParserGetIntValueByKeyByHandle(qmMvSt, 'on');
var qmMvK : Integer;
var qmMvBytes : Integer = 0;
qmMvHead[0] := 'Name = qmState';
qmIncBegin(GetAppSaveDirectoryPath+'quartermaster\state.cfg', qmMvHead, 1, 10+qmMvOn);
qmMvPut(';format|1');
qmMvPut(';gen|'+IntToStr(ParserGetIntValueByKeyByHandle(qmMvSt, 'gen')));
qmMvPut(';hash|'+ParserGetValueByKeyByHandle(qmMvSt, 'hash'));
qmMvPut(';phase|'+ParserGetValueByKeyByHandle(qmMvSt, 'phase'));
qmMvPut(';mode|'+ParserGetValueByKeyByHandle(qmMvSt, 'mode'));
qmMvPut(';rows|'+IntToStr(ParserGetIntValueByKeyByHandle(qmMvSt, 'rows')));
qmMvPut(';rhash|'+ParserGetValueByKeyByHandle(qmMvSt, 'rhash'));
qmMvPut(';rcount|'+IntToStr(ParserGetIntValueByKeyByHandle(qmMvSt, 'rcount')));
qmMvPut(';rk|'+ParserGetValueByKeyByHandle(qmMvSt, 'rk'));
qmMvPut(';boots|'+IntToStr(ParserGetIntValueByKeyByHandle(qmMvSt, 'boots')));
for qmMvK:=0 to qmMvOn-1 do
qmMvPut(';out|'+ParserGetValueByKeyByHandle(qmMvSt, 'op'+IntToStr(qmMvK))+'|'+ParserGetValueByKeyByHandle(qmMvSt, 'oa'+IntToStr(qmMvK)));
if (qmIncEnd(qmMvBytes)=1) then
qmLog('marker saved phase='+ParserGetValueByKeyByHandle(qmMvSt, 'phase')+' gen='+IntToStr(ParserGetIntValueByKeyByHandle(qmMvSt, 'gen'))+' hash='+ParserGetValueByKeyByHandle(qmMvSt, 'hash')+' rows='+IntToStr(ParserGetIntValueByKeyByHandle(qmMvSt, 'rows'))+' rk='+ParserGetValueByKeyByHandle(qmMvSt, 'rk')+' bytes='+IntToStr(qmMvBytes))
else
qmLog('marker save wrote a different number of values than it announced');
