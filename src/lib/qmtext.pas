helpers:
requires:
---
//! The texts of Quartermaster in the language of the game (docs/localisation.md,
//! plan G19). A text in the code is written qmT('English'): the build turns it
//! into a lookup in the named parser qm_text (tools/hbuild.py, expand_texts)
//! and adds `qmTextLoad;` to the start of every state that has one, which
//! fills the parser once from data/quartermaster/text/<code>.cfg. The files
//! are written by the build from src/text/<code>.cfg in the code page of the
//! language (Chinese, Japanese and Korean as ASCII with backslash-u and four
//! hex digits for each character, drawn by Core's wide-text path); their keys
//! are lower-case with underscores, since the engine's parser takes a dot for
//! a path. A language without a file of its own, or whose file does not load,
//! reads English, which every build ships. The parser survives a map load.
//!
//! qmLang      the two-letter folder of the game's tables
//!             (.\data\locale\pl\table.lng is pl), en when there is none
//! qmTextLoad  the language's file into qm_text, again when the language changed
//!
//! A routine that makes a String hands it back through its last, var
//! parameter (src/lib/qmstr.pas), and keeps its own parameter and local names.
procedure qmLang(var qmLgOut : String);
begin
   qmLgOut := 'en';
   var qmLgPath : String = StrToLowerCase(GetLocaleTableFileName());
   var qmLgAt : Integer = StrPos('locale\', qmLgPath);
   if (qmLgAt>0) then
   qmLgOut := SubStr(qmLgPath, qmLgAt+7, 2);
end;

procedure qmTextLoad;
begin
   var qmTlLang : String;
   var qmTlP : Integer = ParserSelectByKey('qm_text');
   var qmTlOk : Boolean = False;
   var qmTlLoad : Boolean = False;
   qmLang(qmTlLang);
   if (qmTlP=0) then
   begin
      qmTlP := ParserCreate('qm_text');
      qmTlLoad := True;
   end
   else
   if (ParserGetValueByKeyByHandle(qmTlP, 'qmlang')<>qmTlLang) then
   begin
      //! The language of the game changed under a running game (Settings applies
      //! a pick at once): the texts read so far are in the old code page.
      ParserClearByHandle(qmTlP);
      qmTlLoad := True;
   end;
   if (qmTlLoad) then
   begin
      if (StrPos(','+qmTlLang+',', ',cs,de,es,fr,it,pl,po,ru,tu,uk,hu,nl,zh,ja,ko,')>0) then
      qmTlOk := ParserLoadFromFileByHandle(qmTlP, '.\data\quartermaster\text\'+qmTlLang+'.cfg');
      if (not qmTlOk) then
      ParserLoadFromFileByHandle(qmTlP, '.\data\quartermaster\text\en.cfg');
      ParserSetValueByKeyByHandle(qmTlP, 'qmlang', qmTlLang);
   end;
end;
