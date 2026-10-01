state: qmSyAppD
into: data/quartermaster/selftest.aix
helpers:
requires:
---
//! incprobe synth, append method d: the key `*`, the name vanilla gives the
//! children it appends with ParserAddChildByIndex (eventsettings.inc:708). Does
//! it append a value or overwrite the first one?
var qmSdRt : Integer = ParserSelectByKey('qm_case_rt');
var qmSdP : Integer = ParserSelectByKey('qm_case_inc');
if (qmSdP=0) then
qmSdP := ParserCreate('qm_case_inc');
ParserClearByHandle(qmSdP);
ParserLoadFromFileByHandle(qmSdP, ParserGetValueByKeyByHandle(qmSdRt, 'sy_file'));
var qmSdC : Integer = ParserSelectByHandleByKey(qmSdP, 'Code');
ParserSetValueByKeyByHandle(qmSdC, '*', ';qd1');
ParserSaveToFileByHandle(qmSdP, ParserGetValueByKeyByHandle(qmSdRt, 'sy_out'));
ParserSetIntValueByKeyByHandle(qmSdRt, 'sy_count', ParserGetCountByHandle(qmSdC));
