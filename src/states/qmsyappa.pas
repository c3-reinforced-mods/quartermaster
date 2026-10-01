state: qmSyAppA
into: data/quartermaster/selftest.aix
helpers:
requires:
---
//! incprobe synth, append method a: the key [*] twice on a fresh load of the
//! synthetic file (run m2a: only the last of three survived). The file and the
//! output come in qm_case_rt (sy_file, sy_out); the Code count after the
//! appends goes back as sy_count.
var qmSaRt : Integer = ParserSelectByKey('qm_case_rt');
var qmSaP : Integer = ParserSelectByKey('qm_case_inc');
if (qmSaP=0) then
qmSaP := ParserCreate('qm_case_inc');
ParserClearByHandle(qmSaP);
ParserLoadFromFileByHandle(qmSaP, ParserGetValueByKeyByHandle(qmSaRt, 'sy_file'));
var qmSaC : Integer = ParserSelectByHandleByKey(qmSaP, 'Code');
ParserSetValueByKeyByHandle(qmSaC, '[*]', ';qa1');
ParserSetValueByKeyByHandle(qmSaC, '[*]', ';qa2');
ParserSaveToFileByHandle(qmSaP, ParserGetValueByKeyByHandle(qmSaRt, 'sy_out'));
ParserSetIntValueByKeyByHandle(qmSaRt, 'sy_count', ParserGetCountByHandle(qmSaC));
