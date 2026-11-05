state: qmAboutLoc
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qmunesc, qmtext
requires: cp1250tab, cp1251tab, cp1252tab, cp1254tab
---
//! The texts a mod declares for other languages (docs/localisation.md; the
//! twin is ref/about.py localise): `name.<code>`, `group.<code>` and
//! `label.<code>` rows of about.cfg. qmAbout has read every file and ignores
//! these rows; this state, run right after it, reads each file again, checks
//! every such row (a WARN appended to the mod's problems, in file order) and
//! applies the rows of the language of the game to qm_about:
//!   name.<code> = <text>                 name<i>
//!   label.<code> = <setting id>;<text>   slb<i>_<k>
//!   group.<code> = <title>;<text>        sgr<i>_<k> of every setting under the
//!                                        title as declared; sgo<i>_<k> keeps
//!                                        that title, so a later row finds it
//!
//! The file is UTF-8. A text is turned into what the language's screen takes:
//! the bytes of its code page (cs pl hu 1250, ru uk 1251, tu 1254, the others
//! 1252), looked up in a table of four hex digits per byte 128..255 that the
//! build writes from the code page; for zh ja ko ASCII with backslash-u and
//! four hex digits for every character outside ASCII (and for a backslash),
//! which Core's wide-text path draws. Text that is not UTF-8, or holds a
//! character the language cannot show, is a WARN and the declared text stays.
//! Values are internal strings (bytes outside 32..122 as ~NNN), as in qmAbout.
var qmLcT0 : Float = _misc_GetRealTime;
var qmLcP : Integer = ParserSelectByKey('qm_about');
var qmLcLang : String;
var qmLcSi : String;
var qmLcLn : Integer;
var qmLcPos : Integer;
var qmLcRows : Integer = 0;
var qmLcTbl : String = ' !"#$%&''()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz';
var qmLcCodes : String = ',cs,de,es,fr,it,pl,po,ru,tu,uk,hu,nl,zh,ja,ko,en,';

procedure qmLcProb(const qmLpCode : String; const qmLpText : String);
begin
   var qmLpN : Integer = ParserGetIntValueByKeyByHandle(qmLcP, 'pn'+qmLcSi);
   var qmLpK : String = qmLcSi+'_'+IntToStr(qmLpN);
   ParserSetValueByKeyByHandle(qmLcP, 'pt'+qmLpK, 'WARN');
   ParserSetValueByKeyByHandle(qmLcP, 'pc'+qmLpK, qmLpCode);
   ParserSetValueByKeyByHandle(qmLcP, 'px'+qmLpK, qmLpText);
   ParserSetIntValueByKeyByHandle(qmLcP, 'pn'+qmLcSi, qmLpN+1);
end;

//! Spaces and tabs (~009) dropped at both ends (ref/about.py _strip).
procedure qmLcStrip(const qmLsS : String; var qmLsOut : String);
begin
   var qmLsGo : Boolean = True;
   var qmLsL : Integer;
   qmLsOut := qmLsS;
   while (qmLsGo) do
   begin
      qmLsGo := False;
      qmLsL := StrLength(qmLsOut);
      if (qmLsL>=1) and (SubStr(qmLsOut, 1, 1)=' ') then
      begin
         qmLsOut := SubStr(qmLsOut, 2, qmLsL-1);
         qmLsGo := True;
      end
      else
      if (qmLsL>=4) and (SubStr(qmLsOut, 1, 4)='~009') then
      begin
         qmLsOut := SubStr(qmLsOut, 5, qmLsL-4);
         qmLsGo := True;
      end
      else
      if (qmLsL>=1) and (SubStr(qmLsOut, qmLsL, 1)=' ') then
      begin
         qmLsOut := SubStr(qmLsOut, 1, qmLsL-1);
         qmLsGo := True;
      end
      else
      if (qmLsL>=4) and (SubStr(qmLsOut, qmLsL-3, 4)='~009') then
      begin
         qmLsOut := SubStr(qmLsOut, 1, qmLsL-4);
         qmLsGo := True;
      end;
   end;
end;

//! The internal form of one byte.
procedure qmLcByte(const qmLbB : Integer; var qmLbOut : String);
begin
   if (qmLbB>=32) and (qmLbB<=122) then
   qmLbOut := SubStr(qmLcTbl, qmLbB-31, 1)
   else
   begin
      qmLbOut := IntToStr(qmLbB);
      while (StrLength(qmLbOut)<3) do
      qmLbOut := '0'+qmLbOut;
      qmLbOut := '~'+qmLbOut;
   end;
end;

//! The next byte of an internal string at qmLcPos (a ~NNN is one), -1 at its end.
function qmLcNext(const qmLnS : String) : Integer;
begin
   var qmLnC : String;
   var qmLnD : String;
   if (qmLcPos>StrLength(qmLnS)) then
   Result := -1
   else
   begin
      qmLnC := SubStr(qmLnS, qmLcPos, 1);
      qmLnD := SubStr(qmLnS, qmLcPos+1, 3);
      if (qmLnC='~') and (StrLength(qmLnD)=3) and (qmIsDigits(qmLnD)) then
      begin
         Result := StrToInt(qmLnD);
         qmLcPos := qmLcPos+4;
      end
      else
      begin
         Result := Ord(qmLnC);
         qmLcPos := qmLcPos+1;
      end;
   end;
end;

//! Four upper-case hex digits of a number below 65536.
procedure qmLcHex4(const qmLhV : Integer; var qmLhOut : String);
begin
   var qmLhT : String = '0123456789ABCDEF';
   qmLhOut := SubStr(qmLhT, (qmLhV shr 12) and 15 + 1, 1)+SubStr(qmLhT, (qmLhV shr 8) and 15 + 1, 1)+SubStr(qmLhT, (qmLhV shr 4) and 15 + 1, 1)+SubStr(qmLhT, qmLhV and 15 + 1, 1);
end;

//! A UTF-8 text (internal form) for the screen of the language of the game
//! (ref/about.py l10n_text); '' when it cannot be written.
procedure qmLcConv(const qmLvS : String; var qmLvOut : String);
begin
   var qmLvOk : Boolean = True;
   var qmLvB : Integer;
   var qmLvCp : Integer = 0;
   var qmLvN : Integer;
   var qmLvK : Integer;
   var qmLvC : Integer;
   var qmLvX : String;
   var qmLvP : Integer;
   var qmLvT : String = ${cp1252tab};
   var qmLvEsc : Boolean = (StrPos(','+qmLcLang+',', ',zh,ja,ko,')>0);
   if (StrPos(','+qmLcLang+',', ',cs,pl,hu,')>0) then
   qmLvT := ${cp1250tab};
   if (StrPos(','+qmLcLang+',', ',ru,uk,')>0) then
   qmLvT := ${cp1251tab};
   if (qmLcLang='tu') then
   qmLvT := ${cp1254tab};
   qmLvOut := '';
   qmLcPos := 1;
   qmLvB := qmLcNext(qmLvS);
   while (qmLvOk) and (qmLvB>=0) do
   begin
      if (qmLvB<128) then
      begin
         if (qmLvEsc) and (qmLvB=92) then
         qmLvOut := qmLvOut+'\'+'u005C'
         else
         begin
            qmLcByte(qmLvB, qmLvX);
            qmLvOut := qmLvOut+qmLvX;
         end;
      end
      else
      begin
         qmLvN := -1;
         if (qmLvB>=194) and (qmLvB<=223) then
         begin
            qmLvN := 1;
            qmLvCp := qmLvB-192;
         end;
         if (qmLvB>=224) and (qmLvB<=239) then
         begin
            qmLvN := 2;
            qmLvCp := qmLvB-224;
         end;
         if (qmLvB>=240) and (qmLvB<=244) then
         begin
            qmLvN := 3;
            qmLvCp := qmLvB-240;
         end;
         if (qmLvN<0) then
         qmLvOk := False
         else
         for qmLvK:=1 to qmLvN do
         if (qmLvOk) then
         begin
            qmLvC := qmLcNext(qmLvS);
            if (qmLvC<128) or (qmLvC>191) then
            qmLvOk := False
            else
            qmLvCp := qmLvCp*64+(qmLvC-128);
         end;
         if (qmLvOk) then
         begin
            if (qmLvN=2) and (qmLvCp<2048) then qmLvOk := False;
            if (qmLvN=3) and ((qmLvCp<65536) or (qmLvCp>1114111)) then qmLvOk := False;
            if (qmLvCp>=55296) and (qmLvCp<=57343) then qmLvOk := False;
            if (qmLvCp>65535) then qmLvOk := False;
         end;
         if (qmLvOk) then
         begin
            qmLcHex4(qmLvCp, qmLvX);
            if (qmLvEsc) then
            qmLvOut := qmLvOut+'\u'+qmLvX
            else
            begin
               qmLvP := StrPos(qmLvX, qmLvT);
               while (qmLvP>0) and (((qmLvP-1) mod 4)<>0) do
               qmLvP := StrPosEx(qmLvX, qmLvT, qmLvP+1);
               if (qmLvP=0) then
               qmLvOk := False
               else
               begin
                  qmLcByte(128+(qmLvP-1) div 4, qmLvX);
                  qmLvOut := qmLvOut+qmLvX;
               end;
            end;
         end;
      end;
      qmLvB := qmLcNext(qmLvS);
   end;
   if (not qmLvOk) then
   qmLvOut := '';
end;

//! One line of the file: only the rows that declare texts for a language.
procedure qmLcLine(const qmLlL : String);
begin
   var qmLlS : String = qmLlL;
   var qmLlT : String;
   var qmLlEq : Integer;
   var qmLlKey : String;
   var qmLlVal : String;
   var qmLlDot : Integer;
   var qmLlBase : String;
   var qmLlCode : String;
   var qmLlTarget : String = '';
   var qmLlText : String;
   var qmLlSemi : Integer;
   var qmLlK : Integer;
   var qmLlHit : Integer = 0;
   var qmLlSn : Integer = ParserGetIntValueByKeyByHandle(qmLcP, 'sn'+qmLcSi);
   var qmLlOrig : String;
   var qmLlWant : String;
   var qmLlDone : String;
   var qmLlU : String;
   var qmLlKeyS : String;
   qmLcLn := qmLcLn+1;
   if (qmLcLn=1) and (SubStr(qmLlS, 1, 12)='~239~187~191') then
   qmLlS := SubStr(qmLlS, 13, StrLength(qmLlS)-12);
   qmLcStrip(qmLlS, qmLlT);
   qmLlS := qmLlT;
   if (qmLlS='') or (SubStr(qmLlS, 1, 1)='#') then
   exit;
   qmLlEq := StrPos('=', qmLlS);
   if (qmLlEq=0) then
   exit;
   qmLcStrip(SubStr(qmLlS, 1, qmLlEq-1), qmLlT);
   qmLowerAscii(qmLlT, qmLlKey);
   qmLcStrip(SubStr(qmLlS, qmLlEq+1, StrLength(qmLlS)-qmLlEq), qmLlVal);
   qmLlDot := StrPos('.', qmLlKey);
   if (qmLlDot=0) then
   exit;
   qmLlBase := SubStr(qmLlKey, 1, qmLlDot-1);
   qmLlCode := SubStr(qmLlKey, qmLlDot+1, StrLength(qmLlKey)-qmLlDot);
   if (StrPos('|'+qmLlBase+'|', '|name|group|label|')=0) or (StrLength(qmLlCode)=0) then
   exit;
   for qmLlK:=1 to StrLength(qmLlCode) do
   if (StrPos(SubStr(qmLlCode, qmLlK, 1), 'abcdefghijklmnopqrstuvwxyz')=0) then
   exit;
   qmLcRows := qmLcRows+1;
   if (StrPos(','+qmLlCode+',', qmLcCodes)=0) then
   begin
      qmLcProb('l10n-lang', 'line '+IntToStr(qmLcLn)+': '''+qmLlCode+''' is not a language of Quartermaster');
      exit;
   end;
   qmLlText := qmLlVal;
   if (qmLlBase<>'name') then
   begin
      qmLlSemi := StrPos(';', qmLlVal);
      if (qmLlSemi>0) then
      begin
         qmLcStrip(SubStr(qmLlVal, 1, qmLlSemi-1), qmLlTarget);
         qmLcStrip(SubStr(qmLlVal, qmLlSemi+1, StrLength(qmLlVal)-qmLlSemi), qmLlText);
      end;
      if (qmLlSemi=0) or (qmLlTarget='') then
      begin
         if (qmLlBase='label') then
         qmLcProb('l10n-fields', 'line '+IntToStr(qmLcLn)+': '+qmLlKey+' needs <setting id>;<text>')
         else
         qmLcProb('l10n-fields', 'line '+IntToStr(qmLcLn)+': '+qmLlKey+' needs <group title>;<text>');
         exit;
      end;
   end;
   if (qmLlText='') then
   begin
      qmLcProb('l10n-fields', 'line '+IntToStr(qmLcLn)+': '+qmLlKey+' has no text');
      exit;
   end;
   if (qmLlBase='label') then
   begin
      qmLowerAscii(qmLlTarget, qmLlU);
      qmLlTarget := qmLlU;
      for qmLlK:=0 to qmLlSn-1 do
      if (ParserGetValueByKeyByHandle(qmLcP, 'sid'+qmLcSi+'_'+IntToStr(qmLlK))=qmLlTarget) then
      qmLlHit := qmLlHit+1;
   end;
   if (qmLlBase='group') then
   begin
      qmUnesc(qmLlTarget, qmLlWant);
      for qmLlK:=0 to qmLlSn-1 do
      begin
         qmLlKeyS := qmLcSi+'_'+IntToStr(qmLlK);
         qmLlOrig := ParserGetValueByKeyByHandle(qmLcP, 'sgo'+qmLlKeyS);
         if (qmLlOrig='') then
         qmLlOrig := ParserGetValueByKeyByHandle(qmLcP, 'sgr'+qmLlKeyS);
         if (qmLlOrig=qmLlWant) then
         qmLlHit := qmLlHit+1;
      end;
   end;
   if (qmLlBase<>'name') and (qmLlHit=0) then
   begin
      if (qmLlBase='label') then
      qmLcProb('l10n-target', 'line '+IntToStr(qmLcLn)+': '+qmLlKey+' names a setting '''+qmLlTarget+''', which this file does not declare')
      else
      qmLcProb('l10n-target', 'line '+IntToStr(qmLcLn)+': '+qmLlKey+' names a group '''+qmLlTarget+''', which this file does not declare');
      exit;
   end;
   if (qmLlCode<>qmLcLang) then
   exit;
   qmLcConv(qmLlText, qmLlDone);
   if (qmLlDone='') then
   begin
      qmLcProb('l10n-chars', 'line '+IntToStr(qmLcLn)+': '+qmLlKey+' holds a character this language cannot show; the declared text stays');
      exit;
   end;
   qmUnesc(qmLlDone, qmLlU);
   if (qmLlBase='name') then
   ParserSetValueByKeyByHandle(qmLcP, 'name'+qmLcSi, qmLlU);
   if (qmLlBase='label') then
   for qmLlK:=0 to qmLlSn-1 do
   if (ParserGetValueByKeyByHandle(qmLcP, 'sid'+qmLcSi+'_'+IntToStr(qmLlK))=qmLlTarget) then
   ParserSetValueByKeyByHandle(qmLcP, 'slb'+qmLcSi+'_'+IntToStr(qmLlK), qmLlU);
   if (qmLlBase='group') then
   for qmLlK:=0 to qmLlSn-1 do
   begin
      qmLlKeyS := qmLcSi+'_'+IntToStr(qmLlK);
      qmLlOrig := ParserGetValueByKeyByHandle(qmLcP, 'sgo'+qmLlKeyS);
      if (qmLlOrig='') then
      qmLlOrig := ParserGetValueByKeyByHandle(qmLcP, 'sgr'+qmLlKeyS);
      if (qmLlOrig=qmLlWant) then
      begin
         ParserSetValueByKeyByHandle(qmLcP, 'sgo'+qmLlKeyS, qmLlOrig);
         ParserSetValueByKeyByHandle(qmLcP, 'sgr'+qmLlKeyS, qmLlU);
      end;
   end;
end;

var qmLcN : Integer = 0;
var qmLcI : Integer;
var qmLcFs : Integer;
var qmLcCur : String;
var qmLcDone : Boolean;
var qmLcInts : Integer;
var qmLcInt : Integer;
var qmLcSh : Integer;
var qmLcB : Integer;
var qmLcE : String;
var qmLcFiles : Integer = 0;
var qmLcPath : String;
if (qmLcP<>0) then
begin
   qmLang(qmLcLang);
   qmLcN := ParserGetIntValueByKeyByHandle(qmLcP, 'n');
   for qmLcI:=0 to qmLcN-1 do
   if (ParserGetIntValueByKeyByHandle(qmLcP, 'has'+IntToStr(qmLcI))=1) then
   begin
      qmLcSi := IntToStr(qmLcI);
      qmLcPath := ParserGetValueByKeyByHandle(qmLcP, 'dir'+qmLcSi)+'\about.cfg';
      qmLcLn := 0;
      qmLcFs := OpenFileRead(qmLcPath);
      qmLcCur := '';
      qmLcDone := False;
      qmLcInts := 0;
      while (not qmLcDone) and (qmLcInts<262144) do
      begin
         qmLcInt := 0;
         ReadInteger(qmLcFs, qmLcInt);
         qmLcInts := qmLcInts+1;
         for qmLcSh:=0 to 3 do
         if (not qmLcDone) then
         begin
            qmLcB := (qmLcInt shr (qmLcSh*8)) and 255;
            if (qmLcB=0) then
            qmLcDone := True
            else
            if (qmLcB=10) then
            begin
               qmLcLine(qmLcCur);
               qmLcCur := '';
            end
            else
            if (qmLcB<>13) then
            begin
               if (qmLcB>=32) and (qmLcB<=122) then
               qmLcCur := qmLcCur+SubStr(qmLcTbl, qmLcB-31, 1)
               else
               begin
                  qmLcE := IntToStr(qmLcB);
                  while (StrLength(qmLcE)<3) do
                  qmLcE := '0'+qmLcE;
                  qmLcCur := qmLcCur+'~'+qmLcE;
               end;
            end;
         end;
      end;
      CloseFile(qmLcFs);
      if (qmLcCur<>'') then
      qmLcLine(qmLcCur);
      qmLcFiles := qmLcFiles+1;
   end;
end;
qmLog('about l10n lang='+qmLcLang+' files='+IntToStr(qmLcFiles)+' rows='+IntToStr(qmLcRows)+' ms='+FloatToStr((_misc_GetRealTime-qmLcT0)*1000));
