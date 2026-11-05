helpers:
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

//! The layout of a text: its width and height, and with wrap on, the text
//! broken into lines of at most `width` (escapes and tags kept).
procedure qmWideLayout(const qmWlFont : Integer; const qmWlText : String; const qmWlWidth : Integer; const qmWlWrap : Boolean; var qmWlRes : String; var qmWlW : Integer; var qmWlH : Integer);
begin
   var qmWlFh : Integer = GetGUIElementFontHeight(gUIConst.font[qmWlFont])+3;
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
         GetGUIElementFontTextRect(gUIConst.font[qmWlFont], qmWlUnit, qmWlUnitW, qmWlMh);
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
   qmWideLayout(qmRcFont, qmRcText, 0, False, qmRcRes, qmRcW, qmRcH)
   else
   GetGUIElementFontTextRect(gUIConst.font[qmRcFont], qmRcText, qmRcW, qmRcH);
end;

procedure qmRectF(const qmRfFont : Integer; const qmRfText : String; var qmRfW : Integer; var qmRfH : Integer);
begin
   var qmRfRes : String;
   if (qmWideHas(qmRfText)) then
   qmWideLayout(qmRfFont, qmRfText, 0, False, qmRfRes, qmRfW, qmRfH)
   else
   GetGUIElementFontTextFormatRect(gUIConst.font[qmRfFont], qmRfText, qmRfW, qmRfH);
end;

procedure qmWrap(const qmWpFont : Integer; const qmWpText : String; const qmWpWidth : Integer; var qmWpOut : String);
begin
   var qmWpW : Integer;
   var qmWpH : Integer;
   if (qmWideHas(qmWpText)) then
   qmWideLayout(qmWpFont, qmWpText, qmWpWidth, True, qmWpOut, qmWpW, qmWpH)
   else
   qmWpOut := GetGUIWrappedTextByFont(gUIConst.font[qmWpFont], qmWpText, qmWpWidth);
end;
