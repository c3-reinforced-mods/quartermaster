helpers: qmtext
requires:
---
//! Measuring, wrapping and cutting a text that holds characters written as a
//! backslash, u and four hex digits (Chinese, Japanese and Korean; docs/
//! localisation.md). Core's wide-text path draws such a text where it goes
//! through the interface wrappers of lib/gui.script (_gui_CreateText), but a
//! call Quartermaster makes on the engine itself - the measure of a text, its
//! wrap, a cut with `...` - sees the escapes as six plain characters. These
//! routines do the same work on the characters, with the layout rules of
//! Core's own (src/gui_wide.pas _upatch_WideLayout in Core): a character
//! outside ASCII is as wide as a line is high plus a seventh, a space a third
//! of that line, a run of ASCII is measured in the bitmap font and made a
//! quarter wider (the wide font's Latin letters are wider), a tag %name(...)%
//! has no width. A text without an escape goes to the engine as it always did,
//! so every other language is untouched.
//!
//! qmWideHas   whether the text holds an escape
//! qmCharLen   its length in characters (an escape is one)
//! qmHead      its first n characters
//! qmRect      GetGUIElementFontTextRect for a font of gUIConst.font
//! qmRectF     GetGUIElementFontTextFormatRect
//! qmWrap      GetGUIWrappedTextByFont, lines parted by a carriage return and a line feed
function qmWideEscAt(const qmWeS : String; const qmWeAt : Integer) : Boolean;
begin
   var qmWeK : Integer;
   Result := False;
   if (qmWeAt+5<=StrLength(qmWeS)) then
   if (SubStr(qmWeS, qmWeAt, 2)='\u') then
   begin
      Result := True;
      for qmWeK:=2 to 5 do
      if (StrPos(SubStr(qmWeS, qmWeAt+qmWeK, 1), '0123456789ABCDEF')=0) then
      Result := False;
   end;
end;

function qmWideHas(const qmWhS : String) : Boolean;
begin
   var qmWhAt : Integer = StrPos('\u', qmWhS);
   Result := False;
   while (qmWhAt>0) and (not Result) do
   begin
      if (qmWideEscAt(qmWhS, qmWhAt)) then
      Result := True
      else
      qmWhAt := StrPosEx('\u', qmWhS, qmWhAt+1);
   end;
end;

function qmCharLen(const qmClS : String) : Integer;
begin
   var qmClI : Integer = 1;
   var qmClN : Integer = 0;
   var qmClL : Integer = StrLength(qmClS);
   while (qmClI<=qmClL) do
   begin
      if (qmWideEscAt(qmClS, qmClI)) then
      qmClI := qmClI+6
      else
      qmClI := qmClI+1;
      qmClN := qmClN+1;
   end;
   Result := qmClN;
end;

procedure qmHead(const qmHdS : String; const qmHdN : Integer; var qmHdOut : String);
begin
   var qmHdI : Integer = 1;
   var qmHdK : Integer = 0;
   var qmHdL : Integer = StrLength(qmHdS);
   while (qmHdI<=qmHdL) and (qmHdK<qmHdN) do
   begin
      if (qmWideEscAt(qmHdS, qmHdI)) then
      qmHdI := qmHdI+6
      else
      qmHdI := qmHdI+1;
      qmHdK := qmHdK+1;
   end;
   qmHdOut := SubStr(qmHdS, 1, qmHdI-1);
end;

//! The end of a tag %name(args)% that starts at i, 0 when the % is a character of the text.
function qmWideTagEnd(const qmWtS : String; const qmWtAt : Integer) : Integer;
begin
   var qmWtEnd : Integer = StrPosEx('%', qmWtS, qmWtAt+1);
   var qmWtTag : String;
   Result := 0;
   if (qmWtEnd>qmWtAt+1) and (qmWtEnd-qmWtAt<=48) then
   begin
      qmWtTag := SubStr(qmWtS, qmWtAt+1, qmWtEnd-qmWtAt-1);
      if (StrPos(' ', qmWtTag)=0) and (StrPos(SubStr(qmWtTag, 1, 1), 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')>0) then
      Result := qmWtEnd;
   end;
end;

//! The language of the game: -1 when it is drawn from bitmap fonts, 0 Chinese,
//! 1 Japanese, 2 Korean (Core's _upatch_WideLang).
function qmWideKind : Integer;
begin
   var qmWkLang : String;
   qmLang(qmWkLang);
   Result := -1;
   if (qmWkLang='zh') then Result := 0;
   if (qmWkLang='ja') then Result := 1;
   if (qmWkLang='ko') then Result := 2;
end;

//! The bitmap font a name stands for (a wide name w?_ or w?2_ loses its prefix).
procedure qmBitmapFont(const qmBfName : String; var qmBfPlain : String);
begin
   qmBfPlain := qmBfName;
   if (StrLength(qmBfName)>3) and (SubStr(qmBfName, 1, 1)='w') then
   begin
      if (SubStr(qmBfName, 3, 1)='_') then
      qmBfPlain := SubStr(qmBfName, 4, StrLength(qmBfName)-3)
      else
      if (SubStr(qmBfName, 3, 1)='2') and (SubStr(qmBfName, 4, 1)='_') then
      qmBfPlain := SubStr(qmBfName, 5, StrLength(qmBfName)-4);
   end;
end;

//! The wide font that goes with a bitmap font of the game, for the script of
//! the text: w<z|j|k>_<name>, w<z|j|k>2_<name> from a screen 1536 high up
//! (data/hud/fontwide.lib of Core).
procedure qmWideFont(const qmWfBase : String; const qmWfKind : Integer; var qmWfName : String);
begin
   var qmWfLetter : String = 'z';
   var qmWfScale : String = '';
   var qmWfPlain : String;
   if (qmWfKind=1) then qmWfLetter := 'j';
   if (qmWfKind=2) then qmWfLetter := 'k';
   qmBitmapFont(qmWfBase, qmWfPlain);
   if (qmWfPlain='') then qmWfPlain := 'default';
   if (GetViewerHeight>1535) then qmWfScale := '2';
   qmWfName := 'w'+qmWfLetter+qmWfScale+'_'+qmWfPlain;
end;

//! The layout of a text: its width and height, and with wrap on, the text
//! broken into lines of at most `width` (escapes and tags kept).
procedure qmWideLayout(const qmWlFont : String; const qmWlText : String; const qmWlWidth : Integer; const qmWlWrap : Boolean; var qmWlRes : String; var qmWlW : Integer; var qmWlH : Integer);
begin
   var qmWlBase : String;
   var qmWlWide : String;
   qmBitmapFont(qmWlFont, qmWlBase);
   qmWideFont(qmWlBase, 0, qmWlWide);
   var qmWlFh : Integer = GetGUIElementFontHeight(qmWlWide);
   if (qmWlFh<=0) then
   qmWlFh := GetGUIElementFontHeight(qmWlBase)+3
   else
   if (GetViewerHeight>1535) then
   qmWlFh := qmWlFh div 2;
   var qmWlLine : String = '';
   var qmWlLineW : Integer = 0;
   var qmWlLines : Integer = 1;
   var qmWlLen : Integer = StrLength(qmWlText);
   var qmWlI : Integer = 1;
   var qmWlC : String;
   var qmWlB : Integer;
   var qmWlUnit : String;
   var qmWlUnitW : Integer;
   var qmWlNext : Integer;
   var qmWlBreak : Boolean;
   var qmWlSkip : Boolean;
   var qmWlTe : Integer;
   var qmWlJ : Integer;
   var qmWlStop : Boolean;
   var qmWlD : String;
   var qmWlMh : Integer;
   qmWlRes := '';
   qmWlW := 0;
   while (qmWlI<=qmWlLen) do
   begin
      qmWlC := SubStr(qmWlText, qmWlI, 1);
      qmWlB := Ord(qmWlC);
      qmWlUnit := qmWlC;
      qmWlUnitW := 0;
      qmWlNext := qmWlI+1;
      qmWlBreak := False;
      qmWlSkip := False;
      if (qmWlB=13) or (qmWlB=10) then
      begin
         qmWlBreak := True;
         if (qmWlB=13) and (SubStr(qmWlText, qmWlI+1, 1)=#10) then
         qmWlNext := qmWlI+2;
      end
      else
      if (qmWlC='%') and (qmWideTagEnd(qmWlText, qmWlI)>0) then
      begin
         qmWlTe := qmWideTagEnd(qmWlText, qmWlI);
         qmWlUnit := SubStr(qmWlText, qmWlI, qmWlTe-qmWlI+1);
         qmWlNext := qmWlTe+1;
      end
      else
      if (qmWideEscAt(qmWlText, qmWlI)) then
      begin
         qmWlUnit := SubStr(qmWlText, qmWlI, 6);
         qmWlNext := qmWlI+6;
         qmWlUnitW := (qmWlFh*23) div 20;
      end
      else
      if (qmWlC=' ') then
      begin
         qmWlUnitW := qmWlFh div 3;
         if (qmWlWrap) and (qmWlLineW+qmWlUnitW>qmWlWidth) then
         qmWlSkip := True;
      end
      else
      begin
         qmWlJ := qmWlI+1;
         qmWlStop := False;
         while (qmWlJ<=qmWlLen) and (not qmWlStop) do
         begin
            qmWlD := SubStr(qmWlText, qmWlJ, 1);
            if (qmWlD=' ') or (qmWlD='%') or (Ord(qmWlD)=13) or (Ord(qmWlD)=10) or (qmWideEscAt(qmWlText, qmWlJ)) then
            qmWlStop := True
            else
            qmWlJ := qmWlJ+1;
         end;
         qmWlUnit := SubStr(qmWlText, qmWlI, qmWlJ-qmWlI);
         qmWlNext := qmWlJ;
         GetGUIElementFontTextRect(qmWlBase, qmWlUnit, qmWlUnitW, qmWlMh);
         qmWlUnitW := (qmWlUnitW*5) div 4;
      end;
      if (qmWlBreak) then
      begin
         qmWlRes := qmWlRes+qmWlLine+#13+#10;
         if (qmWlLineW>qmWlW) then qmWlW := qmWlLineW;
         qmWlLine := '';
         qmWlLineW := 0;
         qmWlLines := qmWlLines+1;
      end
      else
      if (not qmWlSkip) or (qmWlLineW+qmWlUnitW<=qmWlWidth) then
      begin
         if (qmWlWrap) and (qmWlLineW>0) and (qmWlLineW+qmWlUnitW>qmWlWidth) then
         begin
            qmWlRes := qmWlRes+qmWlLine+#13+#10;
            if (qmWlLineW>qmWlW) then qmWlW := qmWlLineW;
            qmWlLine := '';
            qmWlLineW := 0;
            qmWlLines := qmWlLines+1;
         end;
         qmWlLine := qmWlLine+qmWlUnit;
         qmWlLineW := qmWlLineW+qmWlUnitW;
      end;
      qmWlI := qmWlNext;
   end;
   qmWlRes := qmWlRes+qmWlLine;
   if (qmWlLineW>qmWlW) then qmWlW := qmWlLineW;
   qmWlH := qmWlLines*(((qmWlFh*7) div 5)+2);
end;

procedure qmRect(const qmRcFont : Integer; const qmRcText : String; var qmRcW : Integer; var qmRcH : Integer);
begin
   var qmRcRes : String;
   if (qmWideHas(qmRcText)) then
   qmWideLayout(gUIConst.font[qmRcFont], qmRcText, 0, False, qmRcRes, qmRcW, qmRcH)
   else
   GetGUIElementFontTextRect(gUIConst.font[qmRcFont], qmRcText, qmRcW, qmRcH);
end;

procedure qmRectF(const qmRfFont : Integer; const qmRfText : String; var qmRfW : Integer; var qmRfH : Integer);
begin
   var qmRfRes : String;
   if (qmWideHas(qmRfText)) then
   qmWideLayout(gUIConst.font[qmRfFont], qmRfText, 0, False, qmRfRes, qmRfW, qmRfH)
   else
   GetGUIElementFontTextFormatRect(gUIConst.font[qmRfFont], qmRfText, qmRfW, qmRfH);
end;

procedure qmWrap(const qmWpFont : Integer; const qmWpText : String; const qmWpWidth : Integer; var qmWpOut : String);
begin
   var qmWpW : Integer;
   var qmWpH : Integer;
   if (qmWideHas(qmWpText)) then
   qmWideLayout(gUIConst.font[qmWpFont], qmWpText, qmWpWidth, True, qmWpOut, qmWpW, qmWpH)
   else
   qmWpOut := GetGUIWrappedTextByFont(gUIConst.font[qmWpFont], qmWpText, qmWpWidth);
end;

//! The coded form (four hex digits a character, what WideStringAssignStringCoded
//! reads) of a text, its tags left out, and the kind of its script (0 Han,
//! 1 kana, 2 Hangul). A byte of 128..159 is the Unicode of the Windows code page.
procedure qmWideCode(const qmWcText : String; var qmWcOut : String; var qmWcKind : Integer);
begin
   const qmWcHex = '0123456789ABCDEF';
   const qmWcAnsi = '20AC0020201A0192201E20262020202102C620300160203901520020017D0020002020182019201C201D20222013201402DC21220161203A01530020017E0178';
   var qmWcLen : Integer = StrLength(qmWcText);
   var qmWcI : Integer = 1;
   var qmWcC : String;
   var qmWcTag : Integer;
   var qmWcU : String;
   var qmWcN : Integer;
   var qmWcB : Integer;
   qmWcOut := '';
   qmWcKind := 0;
   while (qmWcI<=qmWcLen) do
   begin
      qmWcC := SubStr(qmWcText, qmWcI, 1);
      qmWcTag := 0;
      if (qmWcC='%') then
      qmWcTag := qmWideTagEnd(qmWcText, qmWcI);
      if (qmWcTag>0) then
      qmWcI := qmWcTag+1
      else
      if (qmWcC='\') and (qmWideEscAt(qmWcText, qmWcI)) then
      begin
         qmWcU := SubStr(qmWcText, qmWcI+2, 4);
         qmWcOut := qmWcOut+qmWcU;
         qmWcN := StrToInt('$'+qmWcU);
         if (qmWcN>=12352) and (qmWcN<=12543) then qmWcKind := 1;
         if (qmWcN>=44032) and (qmWcN<=55203) and (qmWcKind=0) then qmWcKind := 2;
         qmWcI := qmWcI+6;
      end
      else
      begin
         qmWcB := Ord(qmWcC);
         if (qmWcB<32) and (qmWcB<>10) and (qmWcB<>13) then
         qmWcB := 32;
         if (qmWcB>=128) and (qmWcB<160) then
         qmWcOut := qmWcOut+SubStr(qmWcAnsi, (qmWcB-128)*4+1, 4)
         else
         qmWcOut := qmWcOut+'00'+SubStr(qmWcHex, (qmWcB div 16)+1, 1)+SubStr(qmWcHex, (qmWcB mod 16)+1, 1);
         qmWcI := qmWcI+1;
      end;
   end;
end;

//! A wide list has no columns: the cells of a row (parted by a tab) are set
//! apart with spaces so that each starts where the column of the list starts.
procedure qmWideColumns(const qmWkList : Integer; const qmWkText : String; var qmWkOut : String);
begin
   var qmWkTabs : Integer = GetGUIListBoxTabsCount(qmWkList);
   var qmWkFont : String;
   var qmWkRes : String;
   var qmWkSw : Integer;
   var qmWkH : Integer;
   var qmWkX : Integer = 0;
   var qmWkStart : Integer = 0;
   var qmWkCell : Integer = 0;
   var qmWkSeg : String = '';
   var qmWkLen : Integer = StrLength(qmWkText);
   var qmWkI : Integer = 1;
   var qmWkC : String;
   var qmWkW : Integer;
   var qmWkR : Float;
   var qmWkB : Float;
   var qmWkG : Float;
   var qmWkA : Float;
   var qmWkCw : Integer;
   qmWkOut := qmWkText;
   if (qmWkTabs>1) and (StrPos(#9, qmWkText)>0) then
   begin
      qmWkOut := '';
      qmWkFont := GetGUIElementFont(qmWkList);
      qmWideLayout(qmWkFont, ' ', 0, False, qmWkRes, qmWkSw, qmWkH);
      if (qmWkSw<=0) then qmWkSw := 4;
      while (qmWkI<=qmWkLen+1) do
      begin
         qmWkC := '';
         if (qmWkI<=qmWkLen) then qmWkC := SubStr(qmWkText, qmWkI, 1);
         if (qmWkI>qmWkLen) or (qmWkC=#9) then
         begin
            qmWkW := 0;
            if (qmWkSeg<>'') then
            qmWideLayout(qmWkFont, qmWkSeg, 0, False, qmWkRes, qmWkW, qmWkH);
            while (qmWkX+qmWkSw<=qmWkStart) do
            begin
               qmWkOut := qmWkOut+' ';
               qmWkX := qmWkX+qmWkSw;
            end;
            qmWkOut := qmWkOut+qmWkSeg;
            qmWkX := qmWkX+qmWkW;
            qmWkSeg := '';
            if (qmWkCell<qmWkTabs) then
            begin
               GetGUIListBoxTabProperty(qmWkList, qmWkCell, qmWkR, qmWkB, qmWkG, qmWkA, qmWkCw);
               qmWkStart := qmWkStart+qmWkCw;
            end;
            qmWkCell := qmWkCell+1;
         end
         else
         qmWkSeg := qmWkSeg+qmWkC;
         qmWkI := qmWkI+1;
      end;
   end;
end;

//! The wide text of an item of a wide list, made from the text the item holds.
procedure qmWideSetItem(const qmWsList : Integer; const qmWsIndex : Integer; const qmWsText : String);
begin
   var qmWsCols : String;
   var qmWsCode : String;
   var qmWsKind : Integer;
   qmWideColumns(qmWsList, qmWsText, qmWsCols);
   qmWideCode(qmWsCols, qmWsCode, qmWsKind);
   WideStringAssignStringCoded(61001, qmWsCode);
   SetGUIListBoxItemWideValue(qmWsList, qmWsIndex, 61001);
   SetGUIListBoxItemValue(qmWsList, qmWsIndex, qmWsText);
end;

//! GUIListBoxAddItem for a text that may hold escapes: in a wide language
//! every list is a wide list, so that its items and its font agree; the item
//! keeps its own text as its value. Any other language, and any text without
//! an escape, goes the way it always went (Core's upatchListAdd).
procedure qmListAdd(const qmLaList : Integer; const qmLaText : String; const qmLaTag : Integer);
begin
   var qmLaBase : String;
   var qmLaWide : String;
   var qmLaKind : Integer = qmWideKind;
   GUIListBoxAddItem(qmLaList, qmLaText, qmLaTag);
   if (qmLaKind>=0) and (qmWideHas(qmLaText)) then
   begin
      if (not GetGUIListBoxWideMode(qmLaList)) then
      begin
         qmBitmapFont(GetGUIElementFont(qmLaList), qmLaBase);
         qmWideFont(qmLaBase, qmLaKind, qmLaWide);
         SetGUIListBoxWideMode(qmLaList, True);
         SetGUIElementFont(qmLaList, qmLaWide);
      end;
      qmWideSetItem(qmLaList, GetGUIListBoxItemsCount(qmLaList)-1, qmLaText);
   end;
end;

//! SetGUIElementText for a text that may hold escapes (a button's own text):
//! drawn from the wide font of the size of the element, the bitmap text
//! cleared. Any other text goes the way it always went (Core's upatchSetText).
procedure qmSetText(const qmStEl : Integer; const qmStText : String);
begin
   var qmStFont : String;
   var qmStPlain : String;
   var qmStCode : String;
   var qmStKind : Integer;
   var qmStWide : String;
   if (qmWideHas(qmStText)) then
   begin
      qmStFont := GetGUIElementFont(qmStEl);
      qmBitmapFont(qmStFont, qmStPlain);
      qmWideCode(qmStText, qmStCode, qmStKind);
      qmWideFont(qmStPlain, qmStKind, qmStWide);
      SetGUIElementText(qmStEl, '');
      SetGUIElementFont(qmStEl, qmStWide);
      WideStringAssignStringCoded(61000, qmStCode);
      SetGUIElementWideText(qmStEl, 61000);
   end
   else
   SetGUIElementText(qmStEl, qmStText);
end;
