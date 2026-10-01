helpers: qmstr
requires:
---
//! Fixed-point numbers of the int and float settings (ref/about.py
//! parse_setting, fixed_text): a value is a text with exactly `places`
//! decimals, worked with as an Integer scaled by 10^places, so the game and
//! the twin show the same text - no Float formatting is involved.
//!
//! qmNumOk      `-?[0-9]+`, or with places > 0 also `-?[0-9]+.[0-9]+`
//! qmNumScaled  a checked text as the scaled Integer (extra decimals cut)
//! qmNumText    a scaled Integer as the text, always `places` decimals
function qmNumOk(const qmNkS : String; const qmNkD : Integer) : Boolean;
begin
   var qmNkT : String = qmNkS;
   var qmNkP : Integer;
   if (SubStr(qmNkT, 1, 1)='-') then
   qmNkT := SubStr(qmNkT, 2, StrLength(qmNkT)-1);
   qmNkP := StrPos('.', qmNkT);
   if (qmNkD>0) and (qmNkP>0) then
   Result := qmIsDigits(SubStr(qmNkT, 1, qmNkP-1)) and qmIsDigits(SubStr(qmNkT, qmNkP+1, StrLength(qmNkT)-qmNkP))
   else
   Result := qmIsDigits(qmNkT);
end;

function qmNumScaled(const qmNsS : String; const qmNsD : Integer) : Integer;
begin
   var qmNsT : String = qmNsS;
   var qmNsNeg : Boolean = (SubStr(qmNsT, 1, 1)='-');
   var qmNsP : Integer;
   var qmNsW : String;
   var qmNsF : String = '';
   var qmNsV : Integer;
   var qmNsI : Integer;
   var qmNsM : Integer = 1;
   if (qmNsNeg) then
   qmNsT := SubStr(qmNsT, 2, StrLength(qmNsT)-1);
   qmNsP := StrPos('.', qmNsT);
   qmNsW := qmNsT;
   if (qmNsP>0) then
   begin
      qmNsW := SubStr(qmNsT, 1, qmNsP-1);
      qmNsF := SubStr(qmNsT, qmNsP+1, StrLength(qmNsT)-qmNsP);
   end;
   while (StrLength(qmNsF)<qmNsD) do
   qmNsF := qmNsF+'0';
   qmNsF := SubStr(qmNsF, 1, qmNsD);
   for qmNsI:=1 to qmNsD do
   qmNsM := qmNsM*10;
   qmNsV := StrToInt(qmNsW)*qmNsM;
   if (qmNsF<>'') then
   qmNsV := qmNsV+StrToInt(qmNsF);
   if (qmNsNeg) then
   qmNsV := -qmNsV;
   Result := qmNsV;
end;

procedure qmNumText(const qmNtV : Integer; const qmNtD : Integer; var qmNtOut : String);
begin
   var qmNtA : Integer = qmNtV;
   var qmNtP : Integer = 1;
   var qmNtI : Integer;
   var qmNtF : String;
   for qmNtI:=1 to qmNtD do
   qmNtP := qmNtP*10;
   if (qmNtA<0) then
   qmNtA := -qmNtA;
   if (qmNtD=0) then
   qmNtOut := IntToStr(qmNtA)
   else
   begin
      qmNtF := IntToStr(qmNtA mod qmNtP);
      while (StrLength(qmNtF)<qmNtD) do
      qmNtF := '0'+qmNtF;
      qmNtOut := IntToStr(qmNtA div qmNtP)+'.'+qmNtF;
   end;
   if (qmNtV<0) then
   qmNtOut := '-'+qmNtOut;
end;
