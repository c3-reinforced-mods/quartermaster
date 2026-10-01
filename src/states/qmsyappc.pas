state: qmSyAppC
into: data/quartermaster/selftest.aix
helpers:
requires:
---
//! incprobe synth, append method c: one value that carries CR LF and a second
//! code line, as `+`-joined char literals (vanilla writes #9 and #34 that way,
//! doprogressquickplay1x1.inc:1335). Does the parser write it as two lines?
var qmScRt : Integer = ParserSelectByKey('qm_case_rt');
var qmScP : Integer = ParserSelectByKey('qm_case_inc');
if (qmScP=0) then
qmScP := ParserCreate('qm_case_inc');
ParserClearByHandle(qmScP);
ParserLoadFromFileByHandle(qmScP, ParserGetValueByKeyByHandle(qmScRt, 'sy_file'));
var qmScC : Integer = ParserSelectByHandleByKey(qmScP, 'Code');
ParserSetValueByKeyByHandle(qmScC, '[*]', ';qc1'+#13+#10+'      [*] = ;qc2');
ParserSaveToFileByHandle(qmScP, ParserGetValueByKeyByHandle(qmScRt, 'sy_out'));
ParserSetIntValueByKeyByHandle(qmScRt, 'sy_count', ParserGetCountByHandle(qmScC));
