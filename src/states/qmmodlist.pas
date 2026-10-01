state: qmModList
into: data/quartermaster/core.aix
helpers: qmlog, qmstr
requires:
---
//! The mod list (plan G3) into the named parser qm_mods; ref/index.py and
//! ref/order.py are the twin.
//!
//! ModLibraryGetData is called exactly the way the shipped scripts call it
//! (data/gui/menu.inc/showmainmenu.inc:186, data/scripts/lib/init.script:172),
//! one variable per var parameter. It lists every registered mod, disabled
//! ones too, in mods.ini order.
//!
//! Quartermaster's own folder is the last enabled mod that has
//! data\quartermaster\core.aix: the hook loaded core.aix through the overlay,
//! which serves the last enabled copy. FileAge on the mod's own path is a
//! plain file-system call (it ignores the overlay), so it tests that folder.
//! Any other folder with that file is a second copy of Quartermaster; it is
//! kept out of the scan list e<j> (ref/index.py scanned_mods), so its hook
//! files and outputs never become merge inputs. FileAge answers -1 for a
//! missing file without an ERROR line, so every row is asked, disabled ones
//! too: an Apply may switch one on (qmOrder rebuilds the list from core<i>).
//!
//! Canonical order (plan S11, ref/order.py): Workshop items by id as a
//! zero-padded string, local folders by ASCII-folded name, anything else by
//! its folded dir, Quartermaster last; ties by the raw dir, then by position.
//! An insertion sort that only moves an entry past strictly greater ones keeps
//! the input position as the last tie-break.
//!
//! Keys written (all identifier-like: the parser folds and trims keys):
//!   n, self                       count, Quartermaster's index or -1
//!   dir<i> tag<i> tit<i> last<i>  the engine's fields
//!   on<i>                         1 enabled, 0 disabled
//!   core<i>                       1 when the folder ships core.aix
//!   ini<i>                        FileAge(<dir>\mod.ini): proves the dir form
//!   org<i>                        w l c o s (Workshop, local, local copy of a
//!                                 Workshop item, other, Quartermaster)
//!   fo<i> id<i>                   origin letter (w l o) and identity used by
//!                                 the fingerprint (ref/fingerprint.py)
//!   pos<i> ord<k>                 canonical position of mod i / mod at k
//!   en, e<j>                      enabled mods other than Quartermaster and
//!                                 its other copies, in canonical order: the
//!                                 ones the index scans
var qmMlMods : Integer = ParserSelectByKey('qm_mods');
if (qmMlMods=0) then
qmMlMods := ParserCreate('qm_mods');
ParserClearByHandle(qmMlMods);
var qmMlRt : Integer = ParserSelectByKey('qm_rt');
if (qmMlRt=0) then
qmMlRt := ParserCreate('qm_rt');
var qmMlCount : Integer = ModLibraryGetCount;
if (qmMlCount>256) then
begin
   qmLog('mods: '+IntToStr(qmMlCount)+' registered, only the first 256 are indexed');
   qmMlCount := 256;
end;
var qmMlDir : array [0..255] of String;
var qmMlNorm : array [0..255] of String;
var qmMlTagA : array [0..255] of String;
var qmMlKey : array [0..255] of String;
var qmMlId : array [0..255] of String;
var qmMlOrg : array [0..255] of Integer;
var qmMlOn : array [0..255] of Integer;
var qmMlCore : array [0..255] of Integer;
var qmMlOrd : array [0..255] of Integer;
var qmMlTag : String;
var qmMlD : String;
var qmMlLast : String;
var qmMlTit : String;
var qmMlOwn : String;
var qmMlDesc : String;
var qmMlTags : String;
var qmMlUrl : String;
var qmMlNote : String;
var qmMlNumf : Integer;
var qmMlVis : Integer;
var qmMlDis : Boolean;
var qmMlAcc : Boolean;
var qmMlBan : Boolean;
var qmMlRoot : Boolean;
var qmMlI : Integer;
var qmMlJ : Integer;
var qmMlK : Integer;
var qmMlC : Integer;
var qmMlGo : Boolean;
var qmMlN : String;
var qmMlLow : String;
var qmMlSelfLow : String = '';
var qmMlRest : String;
var qmMlLetter : String;
var qmMlSelf : Integer = -1;
var qmMlEn : Integer = 0;
var qmMlW : String = '..\..\workshop\content\333420\';
for qmMlI:=0 to qmMlCount-1 do
begin
   //! For a folder without mod.ini the engine leaves the title and `last`
   //! untouched: they would still hold the row before's (run b4, 2026-09-29).
   qmMlTit := '';
   qmMlLast := '';
   ModLibraryGetData(qmMlI, qmMlTag, qmMlD, qmMlLast, qmMlTit, qmMlOwn, qmMlDesc, qmMlTags, qmMlUrl, qmMlNote, qmMlNumf, qmMlVis, qmMlDis, qmMlAcc, qmMlBan, qmMlRoot);
   qmMlDir[qmMlI] := qmMlD;
   qmMlTagA[qmMlI] := qmMlTag;
   if (qmMlDis) then
   qmMlOn[qmMlI] := 0
   else
   qmMlOn[qmMlI] := 1;
   ParserSetValueByKeyByHandle(qmMlMods, 'dir'+IntToStr(qmMlI), qmMlD);
   ParserSetValueByKeyByHandle(qmMlMods, 'tag'+IntToStr(qmMlI), qmMlTag);
   ParserSetValueByKeyByHandle(qmMlMods, 'tit'+IntToStr(qmMlI), qmMlTit);
   ParserSetValueByKeyByHandle(qmMlMods, 'last'+IntToStr(qmMlI), qmMlLast);
   ParserSetIntValueByKeyByHandle(qmMlMods, 'on'+IntToStr(qmMlI), qmMlOn[qmMlI]);
   ParserSetIntValueByKeyByHandle(qmMlMods, 'ini'+IntToStr(qmMlI), FileAge(qmMlD+'\mod.ini'));
   qmMlCore[qmMlI] := 0;
   if (FileAge(qmMlD+'\data\quartermaster\core.aix')<>-1) then
   qmMlCore[qmMlI] := 1;
   ParserSetIntValueByKeyByHandle(qmMlMods, 'core'+IntToStr(qmMlI), qmMlCore[qmMlI]);
   if (not qmMlDis) and (qmMlCore[qmMlI]=1) then
   qmMlSelf := qmMlI;
   //! ref/order.py _norm_dir without the case fold: / as \, trailing \ dropped.
   qmMlN := qmMlD;
   while (StrPos('/', qmMlN)>0) do
   qmMlN := StrReplace(qmMlN, '/', '\');
   while (StrLength(qmMlN)>0) and (SubStr(qmMlN, StrLength(qmMlN), 1)='\') do
   qmMlN := SubStr(qmMlN, 1, StrLength(qmMlN)-1);
   qmMlNorm[qmMlI] := qmMlN;
end;
if (qmMlSelf>=0) then
qmLowerAscii(qmMlNorm[qmMlSelf], qmMlSelfLow);
for qmMlI:=0 to qmMlCount-1 do
begin
   qmLowerAscii(qmMlNorm[qmMlI], qmMlLow);
   qmMlOrg[qmMlI] := 2;
   qmMlId[qmMlI] := qmMlDir[qmMlI];
   qmLowerAscii(qmMlDir[qmMlI], qmMlN);
   qmMlKey[qmMlI] := qmMlN;
   if (qmMlSelf>=0) and (qmMlLow=qmMlSelfLow) then
   begin
      qmMlOrg[qmMlI] := 3;
      qmMlKey[qmMlI] := '';
   end
   else
   if (SubStr(qmMlLow, 1, StrLength(qmMlW))=qmMlW) then
   begin
      qmMlRest := SubStr(qmMlNorm[qmMlI], StrLength(qmMlW)+1, StrLength(qmMlNorm[qmMlI])-StrLength(qmMlW));
      if (qmIsDigits(qmMlRest)) then
      begin
         qmMlOrg[qmMlI] := 0;
         qmMlId[qmMlI] := qmMlRest;
         while (StrLength(qmMlRest)>0) and (SubStr(qmMlRest, 1, 1)='0') do
         qmMlRest := SubStr(qmMlRest, 2, StrLength(qmMlRest)-1);
         while (StrLength(qmMlRest)<20) do
         qmMlRest := '0'+qmMlRest;
         qmMlKey[qmMlI] := qmMlRest;
      end;
   end
   else
   if (SubStr(qmMlLow, 1, 5)='mods\') then
   begin
      qmMlRest := SubStr(qmMlNorm[qmMlI], 6, StrLength(qmMlNorm[qmMlI])-5);
      if (qmMlRest<>'') and (StrPos('\', qmMlRest)=0) then
      begin
         qmMlOrg[qmMlI] := 1;
         qmMlId[qmMlI] := qmMlRest;
         qmLowerAscii(qmMlRest, qmMlN);
         qmMlKey[qmMlI] := qmMlN;
      end;
   end;
end;
for qmMlI:=0 to qmMlCount-1 do
begin
   qmMlJ := qmMlI;
   qmMlGo := True;
   while (qmMlGo) and (qmMlJ>0) do
   begin
      qmMlK := qmMlOrd[qmMlJ-1];
      qmMlC := 0;
      if (qmMlOrg[qmMlI]<qmMlOrg[qmMlK]) then
      qmMlC := -1
      else
      if (qmMlOrg[qmMlI]>qmMlOrg[qmMlK]) then
      qmMlC := 1;
      if (qmMlC=0) then
      qmMlC := qmCmpStr(qmMlKey[qmMlI], qmMlKey[qmMlK]);
      if (qmMlC=0) then
      qmMlC := qmCmpStr(qmMlDir[qmMlI], qmMlDir[qmMlK]);
      if (qmMlC<0) then
      begin
         qmMlOrd[qmMlJ] := qmMlK;
         qmMlJ := qmMlJ-1;
      end
      else
      qmMlGo := False;
   end;
   qmMlOrd[qmMlJ] := qmMlI;
end;
//! Canonical order v2 (plan S11, Phase B; twin ref/about.py canonical_v2):
//! the about.cfg constraints qmAbout left in qm_about pre<i> (rows that load
//! before row i), by Kahn's sort over the order above - of the rows whose
//! predecessors are all placed, the earliest goes next; while none is ready
//! the earliest one left goes, and it is recorded as a cycle (cycn, cyc<k>).
//! Quartermaster keeps its place, last. No qm_about, no change.
var qmMlAb : Integer = ParserSelectByKey('qm_about');
var qmMlPre : array [0..255] of String;
var qmMlPlaced : array [0..255] of Integer;
var qmMlLeft : array [0..255] of Integer;
var qmMlLn : Integer = 0;
var qmMlOut : Integer = 0;
var qmMlCyc : Integer = 0;
var qmMlPick : Integer;
var qmMlReady : Boolean;
var qmMlP : Integer;
if (qmMlAb<>0) and (ParserGetIntValueByKeyByHandle(qmMlAb, 'n')=qmMlCount) then
begin
   for qmMlI:=0 to qmMlCount-1 do
   begin
      qmMlPre[qmMlI] := ParserGetValueByKeyByHandle(qmMlAb, 'pre'+IntToStr(qmMlI));
      qmMlPlaced[qmMlI] := 0;
   end;
   for qmMlK:=0 to qmMlCount-1 do
   if (qmMlOrd[qmMlK]<>qmMlSelf) then
   begin
      qmMlLeft[qmMlLn] := qmMlOrd[qmMlK];
      qmMlLn := qmMlLn+1;
   end;
   while (qmMlOut<qmMlLn) do
   begin
      qmMlPick := -1;
      for qmMlK:=0 to qmMlLn-1 do
      if (qmMlPick<0) and (qmMlLeft[qmMlK]>=0) then
      begin
         qmMlI := qmMlLeft[qmMlK];
         qmMlReady := True;
         for qmMlJ:=0 to qmMlCount-1 do
         if (qmMlPlaced[qmMlJ]=0) and (StrPos('|'+IntToStr(qmMlJ)+'|', qmMlPre[qmMlI])>0) then
         qmMlReady := False;
         if (qmMlReady) then
         qmMlPick := qmMlK;
      end;
      if (qmMlPick<0) then
      begin
         //! A cycle: broken at the earliest row another row left still
         //! waits for.
         for qmMlK:=0 to qmMlLn-1 do
         if (qmMlPick<0) and (qmMlLeft[qmMlK]>=0) then
         begin
            for qmMlJ:=0 to qmMlLn-1 do
            if (qmMlLeft[qmMlJ]>=0) and (StrPos('|'+IntToStr(qmMlLeft[qmMlK])+'|', qmMlPre[qmMlLeft[qmMlJ]])>0) then
            qmMlPick := qmMlK;
         end;
         if (qmMlPick<0) then
         begin
            qmMlK := 0;
            while (qmMlLeft[qmMlK]<0) do
            qmMlK := qmMlK+1;
            qmMlPick := qmMlK;
         end;
         ParserSetIntValueByKeyByHandle(qmMlMods, 'cyc'+IntToStr(qmMlCyc), qmMlLeft[qmMlPick]);
         qmMlCyc := qmMlCyc+1;
      end;
      qmMlP := qmMlLeft[qmMlPick];
      qmMlOrd[qmMlOut] := qmMlP;
      qmMlPlaced[qmMlP] := 1;
      qmMlLeft[qmMlPick] := -1;
      qmMlOut := qmMlOut+1;
   end;
   if (qmMlSelf>=0) then
   qmMlOrd[qmMlOut] := qmMlSelf;
   if (qmMlCyc>0) then
   qmLog('mods: the about.cfg load-order rules form a cycle ('+IntToStr(qmMlCyc)+' placed by canonical order)');
end;
ParserSetIntValueByKeyByHandle(qmMlMods, 'cycn', qmMlCyc);
for qmMlK:=0 to qmMlCount-1 do
begin
   qmMlI := qmMlOrd[qmMlK];
   ParserSetIntValueByKeyByHandle(qmMlMods, 'ord'+IntToStr(qmMlK), qmMlI);
   ParserSetIntValueByKeyByHandle(qmMlMods, 'pos'+IntToStr(qmMlI), qmMlK);
   qmMlLetter := 's';
   if (qmMlOrg[qmMlI]=0) then
   qmMlLetter := 'w';
   if (qmMlOrg[qmMlI]=1) then
   begin
      if (qmMlTagA[qmMlI]<>'') and (qmMlTagA[qmMlI]<>'0') then
      qmMlLetter := 'c'
      else
      qmMlLetter := 'l';
   end;
   if (qmMlOrg[qmMlI]=2) then
   qmMlLetter := 'o';
   ParserSetValueByKeyByHandle(qmMlMods, 'org'+IntToStr(qmMlI), qmMlLetter);
   qmMlLetter := 'o';
   if (qmMlOrg[qmMlI]=0) then
   qmMlLetter := 'w';
   if (qmMlOrg[qmMlI]=1) then
   qmMlLetter := 'l';
   ParserSetValueByKeyByHandle(qmMlMods, 'fo'+IntToStr(qmMlI), qmMlLetter);
   ParserSetValueByKeyByHandle(qmMlMods, 'id'+IntToStr(qmMlI), qmMlId[qmMlI]);
   if (qmMlOn[qmMlI]=1) and (qmMlI<>qmMlSelf) and (qmMlCore[qmMlI]=0) then
   begin
      ParserSetIntValueByKeyByHandle(qmMlMods, 'e'+IntToStr(qmMlEn), qmMlI);
      qmMlEn := qmMlEn+1;
   end;
   if (qmMlOn[qmMlI]=1) and (qmMlI<>qmMlSelf) and (qmMlCore[qmMlI]=1) then
   qmLog('mods: '+qmMlDir[qmMlI]+' is another copy of Quartermaster (it ships data\quartermaster\core.aix); not indexed');
   qmLog('mod '+IntToStr(qmMlI)+' pos='+IntToStr(qmMlK)+' on='+IntToStr(qmMlOn[qmMlI])+' origin='+ParserGetValueByKeyByHandle(qmMlMods, 'org'+IntToStr(qmMlI))+' dir='+qmMlDir[qmMlI]+' tag='+qmMlTagA[qmMlI]+' ini='+IntToStr(ParserGetIntValueByKeyByHandle(qmMlMods, 'ini'+IntToStr(qmMlI)))+' tit='+ParserGetValueByKeyByHandle(qmMlMods, 'tit'+IntToStr(qmMlI)));
end;
ParserSetIntValueByKeyByHandle(qmMlMods, 'n', qmMlCount);
ParserSetIntValueByKeyByHandle(qmMlMods, 'self', qmMlSelf);
ParserSetIntValueByKeyByHandle(qmMlMods, 'en', qmMlEn);
if (qmMlSelf>=0) then
ParserSetValueByKeyByHandle(qmMlRt, 'qmdir', qmMlDir[qmMlSelf])
else
ParserSetValueByKeyByHandle(qmMlRt, 'qmdir', '');
qmLog('mods n='+IntToStr(qmMlCount)+' enabled others='+IntToStr(qmMlEn)+' self='+IntToStr(qmMlSelf));
