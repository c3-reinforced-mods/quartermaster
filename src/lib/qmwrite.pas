helpers: qmlog, qmval, qmidxkey
requires: rawcap, inchead, phasebdata
---
//! The writer (plan G12, S7, S9): the only code that writes, deletes or even
//! names a path in Quartermaster's data mirror, <QmDir>\data\. ref/validate.py
//! writable/deletable and ref/manifest.py are the twins; tests/test_m4_guard.py
//! checks that no other source writes there.
//!
//! The mirror's roots live in qmWrBase and qmWrDst, set by qmWrOpen and read
//! nowhere else. A caller hands over paths relative to data\ (vanilla.idx
//! spelling) and never holds a root, so it cannot write into the mirror by any
//! other way.
//!
//! Two spellings of one folder. qmWrBase, <game>\<qmdir>\data\ by absolute
//! path, is what Quartermaster reads the mirror by (it did, in run m5compile:
//! the pristine hook lines, the manifest's FileAge). qmWrDst, <qmdir>\data\ as
//! the mod list gives it - relative to the game folder - is what it writes and
//! deletes by: the one form seen to replace a file the engine has loaded from a
//! mod folder (run r7: FileStream over mods\HarmonyProbe\data\gui\menu.inc\
//! eventhud.inc, which the reloaded GUI then ran, r7.0.log:40-47; capability
//! probe 1 wrote and deleted mod files by relative path). Run m5compile wrote
//! the hook outputs over the loaded shipped copies by absolute path and every
//! write came back unconfirmed (0.cos_260928_115653.log:37-40), while a new
//! file (the manifest) by absolute path was fine. Each write logs one [qm]
//! line with what it saw before and after, both spellings, so the next run
//! shows which step fails if this one still does. In a SelfTest sandbox both
//! roots are the same absolute save-folder path (verified since M2).
//!   - qmWrOutput writes a staged candidate only after reading it back and
//!     finding that the compiled validation copy of exactly that content set
//!     its flag (qmValCheck): nothing reaches the mirror unvalidated (S7).
//!   - qmWrDelete removes an earlier generation's output and confirms it with
//!     FileAge = -1 (S9; DeleteFileStream is silent on a missing file and
//!     works on files the engine loaded, capability probe 1). The hook files
//!     are never deleted: the shipped hooked copies must stay (S5).
//!   - qmWrManifest writes the manifest, one fixed file the engine never loads
//!     as code (ref/manifest.py).
//! No Copy or Move: they raise when the target folder is missing (probe 1);
//! the FileStream writer creates missing folders (probe 2).
//!
//! qmWrOpen(box)   '' = the real mirror, <game>\<qm_rt qmdir>\data\, with the
//!                 work folder <save>\quartermaster\; a label of a..z and 0..9 =
//!                 a SelfTest sandbox under <save>\qm_test\out\m4\<box>\ (its
//!                 qmdir\data\ and work\). 1 when a root is set.
//! qmWrCheckPath   1 when a path may be written: an .inc on the Phase A merge
//!                 allow-list (plan S3: qm_index class `merge`, under
//!                 gui\menu.inc\, gui\common.inc\ or scripts\), not on the
//!                 never-generate list (plan S2), plain lower case
//! qmWrIsHook      one of the hook files of plan S5 (ref/planner.py HOOK_FILES)
//! qmWrOutput      1 written, 2 not written because the file there already
//!                 has this token (the same engine view - key lines and Code
//!                 values, so the raw writer's 0-3 padding spaces and the
//!                 unpadded shipped copies compare equal: the file keeps its
//!                 bytes and its FileAge, and nothing changed for a restart to
//!                 pick up), 0 refused (not validated, path refused, staged
//!                 file unreadable), -1 the write was not confirmed
//! qmWrCheckData  1 for a data file with a record profile (Phase B)
//! qmWrDataOut     a data candidate of qmDataMerge, gated by qm_val d<seq>:
//!                 1 written, 2 the same lines there already, 0 refused,
//!                 -1 not confirmed
//! qmWrDelete      1 deleted, 0 still there, -1 refused (an .inc of the
//!                 allow-list or a data file, never a hook file)
//! qmWrReadManifest the previous manifest's Code values into pool[at..]
//! qmWrHookDir     where Quartermaster's pristine hook lines are shipped, for
//!                 reading: data\quartermaster\hooks\<file name> in the mirror
//!                 (the hooked copies under gui\menu.inc\ are outputs and
//!                 are overwritten, so the lines need a second home)
var qmWrBase : String = '';
var qmWrDst : String = '';
var qmWrWork : String = '';

function qmWrOpen(const qmWoBox : String) : Integer;
begin
   var qmWoDir : String = '';
   var qmWoRt : Integer = ParserSelectByKey('qm_rt');
   var qmWoI : Integer;
   var qmWoOk : Boolean = (StrLength(qmWoBox)<=32);
   qmWrBase := '';
   qmWrDst := '';
   Result := 0;
   if (qmWoBox='') then
   begin
      qmWrWork := GetAppSaveDirectoryPath+'quartermaster\';
      if (qmWoRt<>0) then
      qmWoDir := ParserGetValueByKeyByHandle(qmWoRt, 'qmdir');
      if (qmWoDir<>'') then
      begin
         qmWrBase := ExtractFilePath(GetApplicationFileName)+qmWoDir+'\data\';
         qmWrDst := qmWoDir+'\data\';
         Result := 1;
      end;
   end
   else
   if (qmWoBox='*trial') then
   begin
      //! The activation check's trial (plan G15b, M8): a whole generation for
      //! the pending set, into <save>\quartermaster\trial\ and never into a
      //! mod folder. `*` keeps the name out of the SelfTest labels.
      qmWrWork := GetAppSaveDirectoryPath+'quartermaster\trial\work\';
      qmWrBase := GetAppSaveDirectoryPath+'quartermaster\trial\qmdir\data\';
      qmWrDst := qmWrBase;
      Result := 1;
   end
   else
   begin
      for qmWoI:=1 to StrLength(qmWoBox) do
      if (StrPos(SubStr(qmWoBox, qmWoI, 1), 'abcdefghijklmnopqrstuvwxyz0123456789')=0) then
      qmWoOk := False;
      if (qmWoOk) then
      begin
         qmWrWork := GetAppSaveDirectoryPath+'qm_test\out\m4\'+qmWoBox+'\work\';
         qmWrBase := GetAppSaveDirectoryPath+'qm_test\out\m4\'+qmWoBox+'\qmdir\data\';
         qmWrDst := qmWrBase;
         Result := 1;
      end
      else
      qmWrWork := GetAppSaveDirectoryPath+'qm_test\out\m4\refused\work\';
   end;
end;

function qmWrCheckPath(const qmWcRel : String) : Integer;
begin
   var qmWcL : Integer = StrLength(qmWcRel);
   var qmWcOk : Boolean = (qmWcL>4) and (qmWcL<=200);
   var qmWcI : Integer;
   var qmWcIdx : Integer;
   var qmWcKeys : Integer;
   var qmWcKey : String;
   var qmWcK : Integer;
   Result := 0;
   for qmWcI:=1 to qmWcL do
   if (StrPos(SubStr(qmWcRel, qmWcI, 1), 'abcdefghijklmnopqrstuvwxyz0123456789_.-\')=0) then
   qmWcOk := False;
   if (qmWcOk) then
   qmWcOk := (SubStr(qmWcRel, qmWcL-3, 4)='.inc') and (StrPos('..', qmWcRel)=0) and (SubStr(qmWcRel, 1, 1)<>'\') and (StrPos('\\', qmWcRel)=0);
   if (qmWcOk) then
   qmWcOk := (SubStr(qmWcRel, 1, 13)='gui\menu.inc\') or (SubStr(qmWcRel, 1, 15)='gui\common.inc\') or (SubStr(qmWcRel, 1, 8)='scripts\');
   if (qmWcOk) then
   qmWcOk := (qmWcRel<>'gui\menu.inc\docreate.inc') and (qmWcRel<>'scripts\common.inc\initmap.inc');
   if (qmWcOk) then
   begin
      qmWcOk := False;
      qmWcIdx := ParserSelectByKey('qm_index');
      qmWcKeys := ParserSelectByKey('qm_index_keys');
      if (qmWcIdx<>0) and (qmWcKeys<>0) then
      begin
         qmIdxKey(qmWcRel, qmWcKey);
         qmWcK := ParserGetIntValueByKeyByHandle(qmWcKeys, qmWcKey);
         if (ParserGetValueByKeyByHandle(qmWcIdx, 'p'+IntToStr(qmWcK))=qmWcRel) and (ParserGetValueByKeyByHandle(qmWcIdx, 'c'+IntToStr(qmWcK))='merge') then
         qmWcOk := True;
      end;
   end;
   if (qmWcOk) then
   Result := 1;
end;

function qmWrIsHook(const qmWhRel : String) : Boolean;
begin
   Result := (StrPos('|'+qmWhRel+'|', '|gui\menu.inc\cameracontrol.inc|gui\menu.inc\initminimap.inc|gui\menu.inc\doprogress.inc|gui\menu.inc\eventmainmenu.inc|gui\menu.inc\onlanevent.inc|')>0);
end;

//! A data file with a record profile (plan S3, Phase B; ref/planner.py
//! PHASE_B_DATA): the only other files the writer may write or delete.
function qmWrCheckData(const qmWxRel : String) : Integer;
begin
   Result := 0;
   if (qmWxRel<>'') and (StrPos('|'+qmWxRel+'|', ${phasebdata})>0) then
   Result := 1;
end;

//! The token of a data file's first qmWkN lines in pool[0..]: qhash of the
//! lines, LF after each - what qmDataMerge puts in qm_val d<seq>.
procedure qmWrDataToken(var qmWkPool : array [0..${rawcap}] of String; const qmWkN : Integer; var qmWkOut : String);
begin
   var qmWkH1 : Integer = 0;
   var qmWkH2 : Integer = 0;
   var qmWkL : Integer = 0;
   var qmWkK : Integer;
   for qmWkK:=0 to qmWkN-1 do
   begin
      qmHashStr(qmWkPool[qmWkK], qmWkH1, qmWkH2, qmWkL);
      qmHashByte(10, qmWkH1, qmWkH2, qmWkL);
   end;
   qmHashText(qmWkH1, qmWkH2, qmWkL, qmWkOut);
end;

//! Lines past qmWlN of pool[0..qmWlAll-1] are only the raw writer's padding:
//! at most one more line, of spaces (ref/textio.py readback_extra_line).
function qmWrOnlyPad(var qmWlPool : array [0..${rawcap}] of String; const qmWlN : Integer; const qmWlAll : Integer) : Boolean;
begin
   var qmWlT : String;
   Result := (qmWlAll=qmWlN);
   if (qmWlAll=qmWlN+1) then
   begin
      qmWlT := qmWlPool[qmWlN];
      while (StrPos(' ', qmWlT)>0) do
      qmWlT := StrReplace(qmWlT, ' ', '');
      Result := (qmWlT='') and (StrLength(qmWlPool[qmWlN])<=3);
   end;
end;

//! A data candidate of qmDataMerge: the first qmWdLines lines of the staged
//! file, written as they are (the raw writer: CR LF after each line) only
//! when qm_val d<seq> holds their token - set by qmDataMerge after the record
//! checks and the engine parser's trial load passed (plan S10). 1 written,
//! 2 the file there has these lines already, 0 refused, -1 not confirmed.
function qmWrDataOut(const qmWdRel : String; const qmWdStaged : String; const qmWdLines : Integer; const qmWdSeq : Integer; var qmWdPool : array [0..${rawcap}] of String) : Integer;
begin
   var qmWdN : Integer = -2;
   var qmWdTok : String = '';
   var qmWdOld : String = '-';
   var qmWdFlag : Integer = 0;
   var qmWdA0 : Integer = -1;
   var qmWdA1 : Integer = -1;
   var qmWdVal : Integer = ParserSelectByKey('qm_val');
   Result := 0;
   if (qmWrDst='') or (qmWrCheckData(qmWdRel)=0) or (qmWdLines<=0) then
   begin
      qmLog('write '+qmWdRel+' refused: no mirror root or not a data file Quartermaster merges');
      exit;
   end;
   qmWdA0 := FileAge(qmWrBase+qmWdRel);
   if (qmWdA0<>-1) then
   begin
      qmRawRead(qmWrBase+qmWdRel, -1, qmWdPool, qmWdN);
      if (qmWdN>=qmWdLines) then
      if qmWrOnlyPad(qmWdPool, qmWdLines, qmWdN) then
      qmWrDataToken(qmWdPool, qmWdLines, qmWdOld);
   end;
   qmRawRead(qmWdStaged, -1, qmWdPool, qmWdN);
   if (qmWdN>=qmWdLines) then
   if qmWrOnlyPad(qmWdPool, qmWdLines, qmWdN) then
   qmWrDataToken(qmWdPool, qmWdLines, qmWdTok);
   //! The gate for data: the checks of exactly these lines passed.
   if (qmWdTok<>'') and (qmWdVal<>0) then
   if (ParserGetValueByKeyByHandle(qmWdVal, 'd'+IntToStr(qmWdSeq))=qmWdTok) then
   qmWdFlag := 1;
   if (qmWdFlag=1) then
   begin
      if (qmWdTok=qmWdOld) then
      Result := 2
      else
      begin
         qmRawWrite(qmWrDst+qmWdRel, qmWdPool, qmWdLines);
         qmWdA1 := FileAge(qmWrDst+qmWdRel);
         if (qmWdA1<>-1) then
         Result := 1
         else
         Result := -1;
      end;
   end;
   qmLog('write data '+qmWdRel+' result='+IntToStr(Result)+' old='+qmWdOld+' staged='+IntToStr(qmWdN)+':'+qmWdTok+' flag='+IntToStr(qmWdFlag)+' lines='+IntToStr(qmWdLines)+' to '+qmWrDst+qmWdRel);
end;

function qmWrOutput(const qmWtRel : String; const qmWtStaged : String; const qmWtSize : Integer; const qmWtSeq : Integer; var qmWtPool : array [0..${rawcap}] of String; var qmWtHead : array [0..${inchead}] of String) : Integer;
begin
   var qmWtNh : Integer = 0;
   var qmWtN : Integer = -1;
   var qmWtForm : Integer = 0;
   var qmWtTok : String = '';
   var qmWtOld : String = '-';
   var qmWtBack : String = '-';
   var qmWtVia : String = 'abs';
   var qmWtRead : String = '';
   var qmWtTarget : String = '';
   var qmWtK : Integer;
   var qmWtBytes : Integer = 0;
   var qmWtOn : Integer = -3;
   var qmWtSn : Integer = -3;
   var qmWtBn : Integer = -3;
   var qmWtFlag : Integer = 0;
   var qmWtEnd : Integer = -1;
   var qmWtA0 : Integer = -1;
   var qmWtD0 : Integer = -1;
   var qmWtA1 : Integer = -1;
   var qmWtD1 : Integer = -1;
   Result := 0;
   if (qmWrBase<>'') and (qmWrCheckPath(qmWtRel)=1) then
   begin
      //! The file there now, read first: its token decides whether to write.
      qmWtRead := qmWrBase+qmWtRel;
      qmWtTarget := qmWrDst+qmWtRel;
      qmWtA0 := FileAge(qmWtRead);
      qmWtD0 := FileAge(qmWtTarget);
      if (qmWtA0<>-1) then
      qmIncReadAt(qmWtRead, -1, qmWtPool, 0, qmWtHead, qmWtNh, qmWtOn, qmWtForm);
      //! Nothing read by the absolute spelling (run m5compile could not tell a
      //! shipped copy equal to its candidate): the writing spelling once more.
      if (qmWtOn<=0) and (qmWtD0<>-1) and (qmWtTarget<>qmWtRead) then
      begin
         qmIncReadAt(qmWtTarget, -1, qmWtPool, 0, qmWtHead, qmWtNh, qmWtOn, qmWtForm);
         qmWtVia := 'dst';
      end;
      if (qmWtOn>=0) then
      qmValToken(qmWtPool, 0, qmWtOn, qmWtHead, qmWtNh, 0, qmWtOld);
      qmIncReadAt(qmWtStaged, qmWtSize, qmWtPool, 0, qmWtHead, qmWtNh, qmWtSn, qmWtForm);
      qmWtN := qmWtSn;
   end
   else
   qmLog('write '+qmWtRel+' refused: no mirror root or not a path Quartermaster may write');
   if (qmWtN>=0) then
   qmValToken(qmWtPool, 0, qmWtN, qmWtHead, qmWtNh, 0, qmWtTok);
   //! The gate: the validation copy of exactly these lines compiled and set
   //! its flag to their token. Nothing else opens the mirror for writing.
   if (qmWtTok<>'') then
   qmWtFlag := qmValCheck(qmWtSeq, qmWtTok);
   if (qmWtFlag=1) then
   begin
      if (qmWtTok=qmWtOld) then
      Result := 2
      else
      begin
         qmIncBegin(qmWtTarget, qmWtHead, qmWtNh, qmWtN);
         for qmWtK:=0 to qmWtN-1 do
         qmIncLine(qmWtPool[qmWtK]);
         qmWtEnd := qmIncEnd(qmWtBytes);
         qmWtA1 := FileAge(qmWtRead);
         qmWtD1 := FileAge(qmWtTarget);
         if (qmWtEnd=1) and (qmWtD1<>-1) then
         Result := 1
         else
         Result := -1;
         //! What is there now, read back by the reading spelling: evidence only.
         if (qmWtA1<>-1) then
         begin
            qmIncReadAt(qmWtRead, -1, qmWtPool, 0, qmWtHead, qmWtNh, qmWtBn, qmWtForm);
            if (qmWtBn>=0) then
            qmValToken(qmWtPool, 0, qmWtBn, qmWtHead, qmWtNh, 0, qmWtBack);
         end;
      end;
   end;
   if (qmWtRead<>'') then
   qmLog('write '+qmWtRel+' result='+IntToStr(Result)+' before abs='+IntToStr(qmWtA0)+' dst='+IntToStr(qmWtD0)+' old='+qmWtVia+':'+IntToStr(qmWtOn)+':'+qmWtOld+' staged='+IntToStr(qmWtSn)+':'+qmWtTok+' flag='+IntToStr(qmWtFlag)+' end='+IntToStr(qmWtEnd)+' bytes='+IntToStr(qmWtBytes)+' after abs='+IntToStr(qmWtA1)+' dst='+IntToStr(qmWtD1)+' back='+IntToStr(qmWtBn)+':'+qmWtBack+' to '+qmWtTarget);
end;

//! A player's own local mod folder (plan G17, M11): `mods\<name>`, one
//! level, no `..`, not Quartermaster's own folder. The only folders outside
//! the mirror the writer touches, and only at the player's request.
function qmWrLocalDir(const qmWlDir : String) : Boolean;
begin
   var qmWlRest : String = SubStr(qmWlDir, 6, StrLength(qmWlDir)-5);
   var qmWlRt : Integer = ParserSelectByKey('qm_rt');
   var qmWlSelf : String = '';
   if (qmWlRt<>0) then
   qmWlSelf := ParserGetValueByKeyByHandle(qmWlRt, 'qmdir');
   Result := SameText(SubStr(qmWlDir, 1, 5), 'mods\') and (qmWlRest<>'') and (StrPos('\', qmWlRest)=0) and (StrPos('/', qmWlRest)=0) and (StrPos('..', qmWlRest)=0) and (not SameText(qmWlDir, qmWlSelf));
end;

//! A new mod's folder name (ref/createmod.py folder_of): A-Z a-z 0-9 _,
//! 1..40 characters, a letter first.
function qmWrFolderOk(const qmWfF : String) : Boolean;
begin
   var qmWfI : Integer;
   Result := (StrLength(qmWfF)>=1) and (StrLength(qmWfF)<=40) and (StrPos(SubStr(qmWfF, 1, 1), 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')>0);
   for qmWfI:=1 to StrLength(qmWfF) do
   if (StrPos(SubStr(qmWfF, qmWfI, 1), 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_')=0) then
   Result := False;
end;

//! Create mod: mods\<folder>\mod.ini, about.cfg and data\readme.txt, each an
//! internal string with ~013~010 line ends. Refused when the folder name is
//! not one Quartermaster makes, a registered mod has that folder, or any of
//! the three files exists. 1 when the three are there afterwards.
function qmWrNewMod(const qmWnF : String; const qmWnIni : String; const qmWnAbout : String; const qmWnReadme : String) : Integer;
begin
   var qmWnDir : String = 'mods\'+qmWnF;
   var qmWnI : Integer;
   var qmWnTag, qmWnD, qmWnLast, qmWnTit, qmWnOwn, qmWnDesc, qmWnTags, qmWnUrl, qmWnNote : String;
   var qmWnNumf, qmWnVis : Integer;
   var qmWnDis, qmWnAcc, qmWnBan, qmWnRoot : Boolean;
   var qmWnOk : Boolean = qmWrFolderOk(qmWnF);
   Result := 0;
   for qmWnI:=0 to ModLibraryGetCount-1 do
   begin
      ModLibraryGetData(qmWnI, qmWnTag, qmWnD, qmWnLast, qmWnTit, qmWnOwn, qmWnDesc, qmWnTags, qmWnUrl, qmWnNote, qmWnNumf, qmWnVis, qmWnDis, qmWnAcc, qmWnBan, qmWnRoot);
      if SameText(qmWnD, qmWnDir) then
      qmWnOk := False;
   end;
   if (FileAge(qmWnDir+'\mod.ini')<>-1) or (FileAge(qmWnDir+'\about.cfg')<>-1) or (FileAge(qmWnDir+'\data\readme.txt')<>-1) then
   qmWnOk := False;
   if (not qmWnOk) then
   begin
      qmLog('write new mod '+qmWnDir+' refused');
      exit;
   end;
   qmRawWriteStr(qmWnDir+'\mod.ini', qmWnIni);
   qmRawWriteStr(qmWnDir+'\about.cfg', qmWnAbout);
   qmRawWriteStr(qmWnDir+'\data\readme.txt', qmWnReadme);
   if (FileAge(qmWnDir+'\mod.ini')<>-1) and (FileAge(qmWnDir+'\about.cfg')<>-1) and (FileAge(qmWnDir+'\data\readme.txt')<>-1) then
   Result := 1;
   qmLog('write new mod '+qmWnDir+' result='+IntToStr(Result));
end;

//! Edit game file: the pristine vanilla file data\<rel> copied byte for byte
//! into the local mod <dir>, under the same path (CopyFileStream; the target
//! folders are made first by a stream write, since a copy into a missing
//! folder raises - capability probe 1). Refused for a mod that is not a local
//! one, a path with `..`, a vanilla file that is not there, or a target that
//! exists. 1 copied, 0 refused, -1 the copy did not arrive.
function qmWrCopyVanilla(const qmWvDir : String; const qmWvRel : String) : Integer;
begin
   var qmWvSrc : String = ExtractFilePath(GetApplicationFileName)+'data\'+qmWvRel;
   var qmWvDst : String = qmWvDir+'\data\'+qmWvRel;
   Result := 0;
   if (not qmWrLocalDir(qmWvDir)) or (qmWvRel='') or (StrPos('..', qmWvRel)>0) or (SubStr(qmWvRel, 1, 1)='\') or (FileAge(qmWvSrc)=-1) or (FileAge(qmWvDst)<>-1) then
   begin
      qmLog('write copy '+qmWvRel+' into '+qmWvDir+' refused');
      exit;
   end;
   OpenFileStreamForWrite(qmWvDst);
   FileStreamWriteInteger(0);
   CloseFileStream;
   CopyFileStream(qmWvSrc, qmWvDst);
   Result := -1;
   if (FileAge(qmWvDst)<>-1) then
   Result := 1;
   qmLog('write copy '+qmWvRel+' into '+qmWvDir+' result='+IntToStr(Result));
end;

//! Create about.cfg: the draft (an internal string) as <dir>\about.cfg of a
//! local mod that has none - never over an existing one.
function qmWrAboutDraft(const qmWbDir : String; const qmWbText : String) : Integer;
begin
   Result := 0;
   if (not qmWrLocalDir(qmWbDir)) or (FileAge(qmWbDir+'\about.cfg')<>-1) then
   begin
      qmLog('write about.cfg of '+qmWbDir+' refused');
      exit;
   end;
   qmRawWriteStr(qmWbDir+'\about.cfg', qmWbText);
   if (FileAge(qmWbDir+'\about.cfg')<>-1) then
   Result := 1
   else
   Result := -1;
   qmLog('write about.cfg of '+qmWbDir+' result='+IntToStr(Result));
end;

function qmWrDelete(const qmWeRel : String) : Integer;
begin
   Result := -1;
   if (qmWrDst<>'') and ((qmWrCheckPath(qmWeRel)=1) or (qmWrCheckData(qmWeRel)=1)) and (not qmWrIsHook(qmWeRel)) then
   begin
      DeleteFileStream(qmWrDst+qmWeRel);
      if (FileAge(qmWrDst+qmWeRel)=-1) then
      Result := 1
      else
      Result := 0;
   end;
end;

procedure qmWrReadManifest(var qmWqPool : array [0..${rawcap}] of String; const qmWqAt : Integer; var qmWqHead : array [0..${inchead}] of String; var qmWqN : Integer);
begin
   var qmWqNh : Integer = 0;
   var qmWqForm : Integer = 0;
   qmWqN := -2;
   if (qmWrBase<>'') then
   qmIncReadAt(qmWrBase+'quartermaster\state\manifest.cfg', -1, qmWqPool, qmWqAt, qmWqHead, qmWqNh, qmWqN, qmWqForm);
end;

procedure qmWrHookDir(var qmWjOut : String);
begin
   qmWjOut := '';
   if (qmWrBase<>'') then
   qmWjOut := qmWrBase+'quartermaster\hooks\';
end;

function qmWrManifest(var qmWmPool : array [0..${rawcap}] of String; const qmWmAt : Integer; const qmWmN : Integer; var qmWmHead : array [0..${inchead}] of String) : Integer;
begin
   var qmWmK : Integer;
   var qmWmBytes : Integer = 0;
   Result := 0;
   if (qmWrDst<>'') then
   begin
      qmWmHead[0] := 'Name = qmManifest';
      qmWmHead[1] := 'Format = 1';
      qmIncBegin(qmWrDst+'quartermaster\state\manifest.cfg', qmWmHead, 2, qmWmN);
      for qmWmK:=0 to qmWmN-1 do
      qmIncLine(qmWmPool[qmWmAt+qmWmK]);
      if (qmIncEnd(qmWmBytes)=1) and (FileAge(qmWrDst+'quartermaster\state\manifest.cfg')<>-1) then
      Result := 1;
   end;
end;
