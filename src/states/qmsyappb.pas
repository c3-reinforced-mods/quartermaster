state: qmSyAppB
into: data/quartermaster/selftest.aix
helpers:
requires:
---
//! incprobe synth, append method b: ParserSetValueByIndex one past the last
//! value. Last of the four, because it may raise (then sy_count stays -9).
var qmSbRt : Integer = ParserSelectByKey('qm_case_rt');
var qmSbP : Integer = ParserSelectByKey('qm_case_inc');
if (qmSbP=0) then
qmSbP := ParserCreate('qm_case_inc');
ParserClearByHandle(qmSbP);
ParserLoadFromFileByHandle(qmSbP, ParserGetValueByKeyByHandle(qmSbRt, 'sy_file'));
var qmSbC : Integer = ParserSelectByHandleByKey(qmSbP, 'Code');
var qmSbN : Integer = ParserGetCountByHandle(qmSbC);
ParserSelectByHandle(qmSbC);
ParserSetValueByIndex(qmSbN, ';qb1');
ParserSaveToFileByHandle(qmSbP, ParserGetValueByKeyByHandle(qmSbRt, 'sy_out'));
ParserSetIntValueByKeyByHandle(qmSbRt, 'sy_count', ParserGetCountByHandle(qmSbC));
