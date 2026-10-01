state: qmUiModel
into: data/quartermaster/core.aix
helpers: qmlog, qmglob, qmstr
requires:
---
//! The manager's model (plan G15): one row per registered mod, rebuilt every
//! time the window opens, into the named parser qm_ui. docs/ui.md owns the
//! key list; qmUiAct runs this state on the command `open`.
//!
//! The rows come from the engine itself: ModLibraryGetData lists every
//! registered mod, disabled ones too, in mods.ini order, and is called here
//! the way the shipped scripts call it (data/gui/menu.inc/showmainmenu.inc:186,
//! data/scripts/lib/init.script:172), one variable per var parameter.
//!
//! Origin follows ref/index.py `origin`: a Workshop dir is
//! `..\..\workshop\content\333420\<digits>`, a local one `mods\<folder>`; a
//! local folder whose tag is a Workshop id is a local copy. Quartermaster's
//! own row is the last enabled mod that has data\quartermaster\core.aix, the
//! rule of ref/index.py `find_self`. FileAge ignores the overlay, so it tests
//! that folder and nothing else, and a missing file answers -1 without an
//! ERROR line.
//!
//! The Active list shows the load order (decided 2026-09-28). The order is
//! not computed here: the boot's mod list (qmModList, named parser qm_mods)
//! owns it - the saved manual order, unseen mods in canonical order before
//! Quartermaster, Quartermaster last. qm_mods is used only when it lists
//! exactly these dirs; otherwise the rows keep mods.ini order with
//! Quartermaster moved last, and `order` says which one the window shows, so
//! a run log can tell them apart. ord<k> is the pending order the order
//! commands (qmUiOrder) change; oord<k> keeps the order the game loaded, and
//! ordchg (0 here) says whether they differ.
//!
//! Status (st<i>, docs/ui.md): `-` for a mod the engine did not load; for a
//! loaded one the status of its record in the report seam qm_report (OK,
//! WARN, FAIL, NEW), matched by dir. A loaded mod without a record - the
//! report is from a generation that did not load it - still gets a status
//! when the boot's index shows it ships none of the files Quartermaster
//! merges: nothing of it can have gone wrong, so it is OK (stsrc<i> = index;
//! the Workshop mod of the hands-on check was such a mod). Otherwise it reads
//! `?` until the next generation, and a log line names it. why<i> is the
//! record's short sentence for the Details line.
var qmUmUi : Integer = ParserSelectByKey('qm_ui');
if (qmUmUi=0) then
qmUmUi := ParserCreate('qm_ui');
var qmUmN : Integer = ModLibraryGetCount;
if (qmUmN>256) then
begin
   qmLog('ui model: '+IntToStr(qmUmN)+' registered mods, the window lists the first 256');
   qmUmN := 256;
end;
var qmUmRep : Integer = ParserSelectByKey('qm_report');
var qmUmRepN : Integer = 0;
if (qmUmRep<>0) then
qmUmRepN := ParserGetIntValueByKeyByHandle(qmUmRep, 'n');
var qmUmDirs : array [0..255] of String;
var qmUmTag : String;
var qmUmDir : String;
var qmUmLast : String;
var qmUmTit : String;
var qmUmOwn : String;
var qmUmDesc : String;
var qmUmTags : String;
var qmUmUrl : String;
var qmUmNote : String;
var qmUmNumf : Integer;
var qmUmVis : Integer;
var qmUmDis : Boolean;
var qmUmAcc : Boolean;
var qmUmBan : Boolean;
var qmUmRoot : Boolean;
var qmUmI : Integer;
var qmUmJ : Integer;
var qmUmK : Integer;
var qmUmName : String;
var qmUmOrg : String;
var qmUmRest : String;
var qmUmDigits : Boolean;
var qmUmSt : String;
var qmUmSrc : String;
var qmUmWhy : String;
var qmUmCpd : String;
var qmUmSelf : Integer = -1;
var qmUmOn : Integer = 0;
for qmUmI:=0 to qmUmN-1 do
begin
   // For a folder without mod.ini the engine leaves the title and `last`
   // untouched: they would still hold the row before's (run b4, 2026-09-29).
   qmUmTit := '';
   qmUmLast := '';
   ModLibraryGetData(qmUmI, qmUmTag, qmUmDir, qmUmLast, qmUmTit, qmUmOwn, qmUmDesc, qmUmTags, qmUmUrl, qmUmNote, qmUmNumf, qmUmVis, qmUmDis, qmUmAcc, qmUmBan, qmUmRoot);
   qmUmDirs[qmUmI] := qmUmDir;
   qmUmName := qmUmTit;
   if (qmUmName='') then
   qmUmName := qmUmLast;
   if (qmUmName='') then
   qmUmName := qmUmDir;
   // Origin labels shown to the player.
   qmUmOrg := 'Other';
   if (StrLength(qmUmDir)>30) and SameText(SubStr(qmUmDir, 1, 30), '..\..\workshop\content\333420\') then
   begin
      qmUmRest := SubStr(qmUmDir, 31, StrLength(qmUmDir)-30);
      qmUmDigits := True;
      for qmUmK:=1 to StrLength(qmUmRest) do
      if (Ord(SubStr(qmUmRest, qmUmK, 1))<48) or (Ord(SubStr(qmUmRest, qmUmK, 1))>57) then
      qmUmDigits := False;
      if (qmUmDigits) then
      qmUmOrg := 'Workshop';
   end
   else
   if (StrLength(qmUmDir)>5) and SameText(SubStr(qmUmDir, 1, 5), 'mods\') and (StrPos('\', SubStr(qmUmDir, 6, StrLength(qmUmDir)-5))=0) then
   begin
      if (qmUmTag<>'') and (qmUmTag<>'0') then
      qmUmOrg := 'Local copy'
      else
      qmUmOrg := 'Local';
   end;
   qmUmSt := '-';
   qmUmSrc := '';
   qmUmWhy := '';
   qmUmCpd := '';
   if (not qmUmDis) then
   begin
      qmUmSt := '?';
      qmUmSrc := 'none';
      for qmUmJ:=0 to qmUmRepN-1 do
      if SameText(ParserGetValueByKeyByHandle(qmUmRep, 'dir'+IntToStr(qmUmJ)), qmUmDir) then
      begin
         qmUmSt := ParserGetValueByKeyByHandle(qmUmRep, 'st'+IntToStr(qmUmJ));
         qmUmWhy := ParserGetValueByKeyByHandle(qmUmRep, 'why'+IntToStr(qmUmJ));
         qmUmCpd := ParserGetValueByKeyByHandle(qmUmRep, 'cpd'+IntToStr(qmUmJ));
         qmUmSrc := 'report';
      end;
   end;
   // The conflict report's sentence for the row (qm_report cpd<j>, qmConflicts).
   ParserSetValueByKeyByHandle(qmUmUi, 'cpd'+IntToStr(qmUmI), qmUmCpd);
   ParserSetValueByKeyByHandle(qmUmUi, 'dir'+IntToStr(qmUmI), qmUmDir);
   ParserSetValueByKeyByHandle(qmUmUi, 'name'+IntToStr(qmUmI), qmUmName);
   ParserSetValueByKeyByHandle(qmUmUi, 'org'+IntToStr(qmUmI), qmUmOrg);
   ParserSetValueByKeyByHandle(qmUmUi, 'st'+IntToStr(qmUmI), qmUmSt);
   ParserSetValueByKeyByHandle(qmUmUi, 'stsrc'+IntToStr(qmUmI), qmUmSrc);
   ParserSetValueByKeyByHandle(qmUmUi, 'why'+IntToStr(qmUmI), qmUmWhy);
   // No activation check of this window yet (qmUiAct tck<i>).
   ParserSetValueByKeyByHandle(qmUmUi, 'tck'+IntToStr(qmUmI), '');
   if (qmUmDis) then
   begin
      ParserSetIntValueByKeyByHandle(qmUmUi, 'en'+IntToStr(qmUmI), 0);
      ParserSetIntValueByKeyByHandle(qmUmUi, 'pe'+IntToStr(qmUmI), 0);
   end
   else
   begin
      ParserSetIntValueByKeyByHandle(qmUmUi, 'en'+IntToStr(qmUmI), 1);
      ParserSetIntValueByKeyByHandle(qmUmUi, 'pe'+IntToStr(qmUmI), 1);
      qmUmOn := qmUmOn+1;
      if (FileAge(qmUmDir+'\data\quartermaster\core.aix')<>-1) then
      qmUmSelf := qmUmI;
   end;
end;
if (qmUmSelf>=0) then
ParserSetValueByKeyByHandle(qmUmUi, 'org'+IntToStr(qmUmSelf), 'Quartermaster');

//! Global scripts (plan S17): each row's list (gl<i>, qmGlobFiles; `|` for
//! Quartermaster and its copies), the rows the start-up guard switched off
//! at this start (qm_glob gd*, matched by dir: gdoff<i> = 1, their why<i>
//! says so), and FAIL for every enabled row that ships a global script
//! another enabled row ships too (stsrc<i> = globals). qmUiAct checks the
//! pending set against the same lists before an Apply.
var qmUmGl : array [0..255] of String;
var qmUmGlob : Integer = ParserSelectByKey('qm_glob');
var qmUmF : String;
var qmUmPath : String;
var qmUmClash : Integer = 0;
for qmUmI:=0 to qmUmN-1 do
begin
   qmUmF := '|';
   if (FileAge(qmUmDirs[qmUmI]+'\data\quartermaster\core.aix')=-1) then
   qmGlobFiles(qmUmI, qmUmDirs[qmUmI], qmUmF);
   qmUmGl[qmUmI] := qmUmF;
   ParserSetValueByKeyByHandle(qmUmUi, 'gl'+IntToStr(qmUmI), qmUmF);
   ParserSetIntValueByKeyByHandle(qmUmUi, 'gdoff'+IntToStr(qmUmI), 0);
end;
if (qmUmGlob<>0) then
for qmUmK:=0 to ParserGetIntValueByKeyByHandle(qmUmGlob, 'gdn')-1 do
for qmUmI:=0 to qmUmN-1 do
if SameText(ParserGetValueByKeyByHandle(qmUmGlob, 'gdd'+IntToStr(qmUmK)), qmUmDirs[qmUmI]) then
begin
   ParserSetIntValueByKeyByHandle(qmUmUi, 'gdoff'+IntToStr(qmUmI), 1);
   qmGlobPath(ParserGetValueByKeyByHandle(qmUmGlob, 'gdf'+IntToStr(qmUmK)), qmUmPath);
   // Why a row is off after the start-up guard.
   ParserSetValueByKeyByHandle(qmUmUi, 'why'+IntToStr(qmUmI), 'switched off at start by Quartermaster: it replaces '+qmUmPath+', and so does '+ParserGetValueByKeyByHandle(qmUmGlob, 'gdo'+IntToStr(qmUmK))+'; with both the game would not start');
end;
for qmUmI:=0 to qmUmN-1 do
if (ParserGetIntValueByKeyByHandle(qmUmUi, 'en'+IntToStr(qmUmI))=1) and (StrLength(qmUmGl[qmUmI])>1) then
for qmUmJ:=0 to qmUmN-1 do
if (qmUmJ<>qmUmI) and (ParserGetIntValueByKeyByHandle(qmUmUi, 'en'+IntToStr(qmUmJ))=1) and (StrLength(qmUmGl[qmUmJ])>1) then
begin
   qmGlobFirst(qmUmGl[qmUmI], qmUmGl[qmUmJ], qmUmF);
   if (qmUmF<>'') and (ParserGetValueByKeyByHandle(qmUmUi, 'stsrc'+IntToStr(qmUmI))<>'globals') then
   begin
      qmGlobPath(qmUmF, qmUmPath);
      ParserSetValueByKeyByHandle(qmUmUi, 'st'+IntToStr(qmUmI), 'FAIL');
      ParserSetValueByKeyByHandle(qmUmUi, 'stsrc'+IntToStr(qmUmI), 'globals');
      // Why a row clashes.
      ParserSetValueByKeyByHandle(qmUmUi, 'why'+IntToStr(qmUmI), 'replaces '+qmUmPath+', and so does '+ParserGetValueByKeyByHandle(qmUmUi, 'name'+IntToStr(qmUmJ))+': only one copy can load, and the game may not start with both. Deactivate one of them');
      qmUmClash := qmUmClash+1;
   end;
end;
qmLog('ui model globals: rows with global scripts clashing='+IntToStr(qmUmClash));
ParserSetIntValueByKeyByHandle(qmUmUi, 'n', qmUmN);
ParserSetIntValueByKeyByHandle(qmUmUi, 'self', qmUmSelf);
if (qmUmRep<>0) then
ParserSetIntValueByKeyByHandle(qmUmUi, 'hasreport', 1)
else
ParserSetIntValueByKeyByHandle(qmUmUi, 'hasreport', 0);

var qmUmMods : Integer = ParserSelectByKey('qm_mods');
var qmUmCanon : Boolean = False;
if (qmUmMods<>0) then
qmUmCanon := (ParserGetIntValueByKeyByHandle(qmUmMods, 'n')=qmUmN);
if (qmUmCanon) then
for qmUmI:=0 to qmUmN-1 do
if not SameText(ParserGetValueByKeyByHandle(qmUmMods, 'dir'+IntToStr(qmUmI)), qmUmDirs[qmUmI]) then
qmUmCanon := False;
var qmUmSeen : array [0..255] of Integer;
for qmUmI:=0 to qmUmN-1 do
qmUmSeen[qmUmI] := 0;
if (qmUmCanon) then
for qmUmK:=0 to qmUmN-1 do
begin
   qmUmI := ParserGetIntValueByKeyByHandle(qmUmMods, 'ord'+IntToStr(qmUmK));
   if (qmUmI<0) or (qmUmI>=qmUmN) then
   qmUmCanon := False
   else
   if (qmUmSeen[qmUmI]<>0) then
   qmUmCanon := False
   else
   qmUmSeen[qmUmI] := 1;
end;
if (qmUmCanon) then
begin
   for qmUmK:=0 to qmUmN-1 do
   ParserSetIntValueByKeyByHandle(qmUmUi, 'ord'+IntToStr(qmUmK), ParserGetIntValueByKeyByHandle(qmUmMods, 'ord'+IntToStr(qmUmK)));
   ParserSetValueByKeyByHandle(qmUmUi, 'order', 'qm_mods');
end
else
begin
   qmUmK := 0;
   for qmUmI:=0 to qmUmN-1 do
   if (qmUmI<>qmUmSelf) then
   begin
      ParserSetIntValueByKeyByHandle(qmUmUi, 'ord'+IntToStr(qmUmK), qmUmI);
      qmUmK := qmUmK+1;
   end;
   if (qmUmSelf>=0) then
   ParserSetIntValueByKeyByHandle(qmUmUi, 'ord'+IntToStr(qmUmK), qmUmSelf);
   ParserSetValueByKeyByHandle(qmUmUi, 'order', 'engine');
end;
for qmUmK:=0 to qmUmN-1 do
ParserSetIntValueByKeyByHandle(qmUmUi, 'oord'+IntToStr(qmUmK), ParserGetIntValueByKeyByHandle(qmUmUi, 'ord'+IntToStr(qmUmK)));
ParserSetIntValueByKeyByHandle(qmUmUi, 'ordchg', 0);

//! The canonical order for Auto-sort (qmUiAct `autosort`): qmOrder keeps
//! qmModList's canonical order in qm_mods cord<k>. It is taken only when
//! qm_mods lists exactly these rows and cord<k> is a permutation of them - a
//! missing key reads 0, so an absent cord<k> fails the check - and `hascanon`
//! says whether it was; without it Auto-sort is disabled.
var qmUmHasCanon : Integer = 0;
if (qmUmCanon) then
begin
   qmUmHasCanon := 1;
   for qmUmI:=0 to qmUmN-1 do
   qmUmSeen[qmUmI] := 0;
   for qmUmK:=0 to qmUmN-1 do
   begin
      qmUmI := ParserGetIntValueByKeyByHandle(qmUmMods, 'cord'+IntToStr(qmUmK));
      if (qmUmI<0) or (qmUmI>=qmUmN) then
      qmUmHasCanon := 0
      else
      if (qmUmSeen[qmUmI]<>0) then
      qmUmHasCanon := 0
      else
      qmUmSeen[qmUmI] := 1;
   end;
end;
if (qmUmHasCanon=1) then
for qmUmK:=0 to qmUmN-1 do
ParserSetIntValueByKeyByHandle(qmUmUi, 'cord'+IntToStr(qmUmK), ParserGetIntValueByKeyByHandle(qmUmMods, 'cord'+IntToStr(qmUmK)));
ParserSetIntValueByKeyByHandle(qmUmUi, 'hascanon', qmUmHasCanon);

//! A loaded mod without a report record: OK when the index shows it ships
//! none of the merged files (qm_index v<k> are `;`-joined positions of
//! qm_mods, the same lookup qmUiDetails makes); the index is read only when
//! qm_mods lists exactly these dirs.
var qmUmIdx : Integer = ParserSelectByKey('qm_index');
var qmUmIdxN : Integer = 0;
var qmUmPos : String;
var qmUmFiles : Integer;
var qmUmMiss : Integer = 0;
if (qmUmIdx<>0) then
qmUmIdxN := ParserGetIntValueByKeyByHandle(qmUmIdx, 'n');
for qmUmI:=0 to qmUmN-1 do
if (ParserGetValueByKeyByHandle(qmUmUi, 'st'+IntToStr(qmUmI))='?') then
begin
   qmUmFiles := -1;
   if (qmUmCanon) and (qmUmIdx<>0) then
   begin
      qmUmFiles := 0;
      qmUmPos := ';'+IntToStr(ParserGetIntValueByKeyByHandle(qmUmMods, 'pos'+IntToStr(qmUmI)))+';';
      for qmUmK:=0 to qmUmIdxN-1 do
      if (StrPos(qmUmPos, ';'+ParserGetValueByKeyByHandle(qmUmIdx, 'v'+IntToStr(qmUmK))+';')>0) then
      qmUmFiles := qmUmFiles+1;
   end;
   if (qmUmFiles=0) then
   begin
      ParserSetValueByKeyByHandle(qmUmUi, 'st'+IntToStr(qmUmI), 'OK');
      ParserSetValueByKeyByHandle(qmUmUi, 'stsrc'+IntToStr(qmUmI), 'index');
   end
   else
   qmUmMiss := qmUmMiss+1;
   qmLog('ui model: no report record for loaded '+qmUmDirs[qmUmI]+'; files in the index='+IntToStr(qmUmFiles)+' status='+ParserGetValueByKeyByHandle(qmUmUi, 'st'+IntToStr(qmUmI)));
end;
//! about.cfg (plan G15b; qmAbout at the boot, qmAbRules; ref/about.py).
//! `abok` = 1 when qm_about lists exactly these rows; then per row `abs<i>`
//! its settings (the Options button) and `abid<i>` the id they are kept
//! under, and the status: a loaded row that breaks a rule of the loaded set
//! (qmAbRules over en<i> in the loaded order) or whose file has a FAIL value
//! is FAIL (stsrc<i> = about, why<i> the problem); an OK row with a WARN is
//! WARN. A global-script clash (stsrc globals) keeps its own FAIL.
var qmUmAb : Integer = ParserSelectByKey('qm_about');
var qmUmAbOk : Integer = 0;
var qmUmAs : String;
var qmUmAk : Integer;
var qmUmAt : String;
var qmUmAx : String;
if (qmUmAb<>0) then
if (ParserGetIntValueByKeyByHandle(qmUmAb, 'n')=qmUmN) then
begin
   qmUmAbOk := 1;
   for qmUmI:=0 to qmUmN-1 do
   if not SameText(ParserGetValueByKeyByHandle(qmUmAb, 'dir'+IntToStr(qmUmI)), qmUmDirs[qmUmI]) then
   qmUmAbOk := 0;
end;
ParserSetIntValueByKeyByHandle(qmUmUi, 'abok', qmUmAbOk);
if (qmUmAbOk=1) then
begin
   var qmUmAin : Integer = ParserSelectByKey('qm_abin');
   if (qmUmAin=0) then
   qmUmAin := ParserCreate('qm_abin');
   ParserClearByHandle(qmUmAin);
   ParserSetIntValueByKeyByHandle(qmUmAin, 'n', qmUmN);
   for qmUmK:=0 to qmUmN-1 do
   begin
      ParserSetIntValueByKeyByHandle(qmUmAin, 'on'+IntToStr(qmUmK), ParserGetIntValueByKeyByHandle(qmUmUi, 'en'+IntToStr(qmUmK)));
      ParserSetIntValueByKeyByHandle(qmUmAin, 'ord'+IntToStr(qmUmK), ParserGetIntValueByKeyByHandle(qmUmUi, 'oord'+IntToStr(qmUmK)));
   end;
   StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmAbRules', 0);
   var qmUmAr : Integer = ParserSelectByKey('qm_abr');
   for qmUmI:=0 to qmUmN-1 do
   begin
      qmUmAs := IntToStr(qmUmI);
      ParserSetIntValueByKeyByHandle(qmUmUi, 'abs'+qmUmAs, ParserGetIntValueByKeyByHandle(qmUmAb, 'sn'+qmUmAs));
      qmUmAt := ParserGetValueByKeyByHandle(qmUmAb, 'id'+qmUmAs);
      if (qmUmAt='') then
      qmField(ParserGetValueByKeyByHandle(qmUmAb, 'nm'+qmUmAs), '|', 1, qmUmAt);
      ParserSetValueByKeyByHandle(qmUmUi, 'abid'+qmUmAs, qmUmAt);
      if (ParserGetIntValueByKeyByHandle(qmUmUi, 'en'+qmUmAs)=1) and (ParserGetValueByKeyByHandle(qmUmUi, 'stsrc'+qmUmAs)<>'globals') then
      begin
         qmUmAt := '';
         qmUmAx := '';
         for qmUmK:=0 to ParserGetIntValueByKeyByHandle(qmUmAr, 'n')-1 do
         if (ParserGetIntValueByKeyByHandle(qmUmAr, 'row'+IntToStr(qmUmK))=qmUmI) then
         begin
            if (ParserGetValueByKeyByHandle(qmUmAr, 'tag'+IntToStr(qmUmK))='FAIL') and (qmUmAt='') then
            qmUmAt := ParserGetValueByKeyByHandle(qmUmAr, 'text'+IntToStr(qmUmK));
            if (ParserGetValueByKeyByHandle(qmUmAr, 'tag'+IntToStr(qmUmK))='WARN') and (qmUmAx='') then
            qmUmAx := ParserGetValueByKeyByHandle(qmUmAr, 'text'+IntToStr(qmUmK));
         end;
         for qmUmAk:=0 to ParserGetIntValueByKeyByHandle(qmUmAb, 'pn'+qmUmAs)-1 do
         begin
            if (ParserGetValueByKeyByHandle(qmUmAb, 'pt'+qmUmAs+'_'+IntToStr(qmUmAk))='FAIL') and (qmUmAt='') then
            qmUmAt := 'about.cfg: '+ParserGetValueByKeyByHandle(qmUmAb, 'px'+qmUmAs+'_'+IntToStr(qmUmAk));
            if (ParserGetValueByKeyByHandle(qmUmAb, 'pt'+qmUmAs+'_'+IntToStr(qmUmAk))='WARN') and (qmUmAx='') then
            qmUmAx := 'about.cfg: '+ParserGetValueByKeyByHandle(qmUmAb, 'px'+qmUmAs+'_'+IntToStr(qmUmAk));
         end;
         if (qmUmAt<>'') then
         begin
            ParserSetValueByKeyByHandle(qmUmUi, 'st'+qmUmAs, 'FAIL');
            ParserSetValueByKeyByHandle(qmUmUi, 'stsrc'+qmUmAs, 'about');
            ParserSetValueByKeyByHandle(qmUmUi, 'why'+qmUmAs, qmUmAt);
         end
         else
         if (qmUmAx<>'') and ((ParserGetValueByKeyByHandle(qmUmUi, 'st'+qmUmAs)='OK') or (ParserGetValueByKeyByHandle(qmUmUi, 'st'+qmUmAs)='NEW')) then
         begin
            ParserSetValueByKeyByHandle(qmUmUi, 'st'+qmUmAs, 'WARN');
            ParserSetValueByKeyByHandle(qmUmUi, 'stsrc'+qmUmAs, 'about');
            ParserSetValueByKeyByHandle(qmUmUi, 'why'+qmUmAs, qmUmAx);
         end;
      end;
   end;
end
else
for qmUmI:=0 to qmUmN-1 do
begin
   ParserSetIntValueByKeyByHandle(qmUmUi, 'abs'+IntToStr(qmUmI), 0);
   ParserSetValueByKeyByHandle(qmUmUi, 'abid'+IntToStr(qmUmI), '');
end;
qmLog('ui model n='+IntToStr(qmUmN)+' enabled='+IntToStr(qmUmOn)+' self='+IntToStr(qmUmSelf)+' order='+ParserGetValueByKeyByHandle(qmUmUi, 'order')+' canon='+IntToStr(qmUmHasCanon)+' report='+IntToStr(ParserGetIntValueByKeyByHandle(qmUmUi, 'hasreport'))+' unknown='+IntToStr(qmUmMiss)+' about='+IntToStr(qmUmAbOk));
var qmUmLine : String = '';
for qmUmK:=0 to qmUmN-1 do
begin
   qmUmI := ParserGetIntValueByKeyByHandle(qmUmUi, 'ord'+IntToStr(qmUmK));
   if (ParserGetIntValueByKeyByHandle(qmUmUi, 'en'+IntToStr(qmUmI))=1) then
   begin
      if (qmUmLine<>'') then
      qmUmLine := qmUmLine+' | ';
      qmUmLine := qmUmLine+qmUmDirs[qmUmI];
   end;
end;
qmLog('ui model active order: '+qmUmLine);
var qmUmStLine : String = '';
for qmUmI:=0 to qmUmN-1 do
begin
   if (qmUmStLine<>'') then
   qmUmStLine := qmUmStLine+' ';
   qmUmStLine := qmUmStLine+ParserGetValueByKeyByHandle(qmUmUi, 'st'+IntToStr(qmUmI));
end;
qmLog('ui model status by row: '+qmUmStLine);
