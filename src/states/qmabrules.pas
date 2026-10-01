state: qmAbRules
into: data/quartermaster/core.aix
helpers: qmlog, qmstr
requires: version
---
//! The about.cfg rules of one mod set (plan G15b; twin ref/about.py rules):
//! the boot runs it for the enabled mods in load order, the manager window
//! (qmUiAct) for the pending set after every command. It reads qm_about
//! (qmAbout) and the set from qm_abin, and writes qm_abr.
//!
//!   qm_abin  n, on<i> (1 active), ord<k> (every row in load order)
//!   qm_abr   n (at most 64), row<k> tag<k> code<k> text<k> oth<k> (the other
//!            row or -1), fail (1 when any is FAIL)
//!
//! One problem per broken rule, on the row that breaks it - the later of two
//! in load order: a requirement that is not active (FAIL), a version too low
//! (FAIL) or unknown (WARN), a Quartermaster too old (WARN), an incompatible
//! mod active (FAIL), two total conversions (FAIL) or two mods in one
//! exclusive slot (FAIL) unless one extends the other or one says it is
//! compatible with the other, and a load order that breaks a constraint
//! (WARN; the window's Auto-sort puts it right).
var qmArA : Integer = ParserSelectByKey('qm_about');
var qmArIn : Integer = ParserSelectByKey('qm_abin');
var qmArR : Integer = ParserSelectByKey('qm_abr');
if (qmArR=0) then
qmArR := ParserCreate('qm_abr');
ParserClearByHandle(qmArR);
ParserSetIntValueByKeyByHandle(qmArR, 'n', 0);
ParserSetIntValueByKeyByHandle(qmArR, 'fail', 0);
if (qmArA=0) or (qmArIn=0) then
exit;
var qmArN : Integer = ParserGetIntValueByKeyByHandle(qmArIn, 'n');
if (qmArN>ParserGetIntValueByKeyByHandle(qmArA, 'n')) then
qmArN := ParserGetIntValueByKeyByHandle(qmArA, 'n');
var qmArSelf : Integer = ParserGetIntValueByKeyByHandle(qmArA, 'self');
var qmArOn : array [0..255] of Integer;
var qmArOrd : array [0..255] of Integer;
var qmArPos : array [0..255] of Integer;
var qmArNm : array [0..255] of String;
var qmArTit : array [0..255] of String;
var qmArExt : array [0..255] of String;
var qmArCmp : array [0..255] of String;
var qmArExcl : array [0..255] of String;
var qmArTy : array [0..255] of String;
var qmArPn : Integer = 0;
var qmArI : Integer;
var qmArJ : Integer;
var qmArK : Integer;
var qmArM : Integer;
var qmArS : String;
var qmArT : String;
var qmArU : String;
var qmArRid : String;
var qmArVer : String;
var qmArHave : String;
var qmArHit : Integer;
var qmArNeed : Integer;
var qmArDone : Boolean;
for qmArI:=0 to qmArN-1 do
begin
   qmArS := IntToStr(qmArI);
   qmArOn[qmArI] := ParserGetIntValueByKeyByHandle(qmArIn, 'on'+qmArS);
   qmArOrd[qmArI] := ParserGetIntValueByKeyByHandle(qmArIn, 'ord'+qmArS);
   qmArNm[qmArI] := ParserGetValueByKeyByHandle(qmArA, 'nm'+qmArS);
   qmArTit[qmArI] := ParserGetValueByKeyByHandle(qmArA, 'tit'+qmArS);
   qmArExt[qmArI] := ParserGetValueByKeyByHandle(qmArA, 'ext'+qmArS);
   qmArCmp[qmArI] := ParserGetValueByKeyByHandle(qmArA, 'cmp'+qmArS);
   qmArExcl[qmArI] := ParserGetValueByKeyByHandle(qmArA, 'excl'+qmArS);
   qmArTy[qmArI] := ParserGetValueByKeyByHandle(qmArA, 'type'+qmArS);
end;
for qmArK:=0 to qmArN-1 do
if (qmArOrd[qmArK]>=0) and (qmArOrd[qmArK]<qmArN) then
qmArPos[qmArOrd[qmArK]] := qmArK;

procedure qmArAdd(const qmAaRow : Integer; const qmAaTag : String; const qmAaCode : String; const qmAaText : String; const qmAaOth : Integer);
begin
   if (qmArPn>=64) then
   exit;
   var qmAaK : String = IntToStr(qmArPn);
   ParserSetIntValueByKeyByHandle(qmArR, 'row'+qmAaK, qmAaRow);
   ParserSetValueByKeyByHandle(qmArR, 'tag'+qmAaK, qmAaTag);
   ParserSetValueByKeyByHandle(qmArR, 'code'+qmAaK, qmAaCode);
   ParserSetValueByKeyByHandle(qmArR, 'text'+qmAaK, qmAaText);
   ParserSetIntValueByKeyByHandle(qmArR, 'oth'+qmAaK, qmAaOth);
   if (qmAaTag='FAIL') then
   ParserSetIntValueByKeyByHandle(qmArR, 'fail', 1);
   qmArPn := qmArPn+1;
end;

//! The first row (in mods.ini order) that answers to `name`, active only or any.
function qmArFind(const qmAfName : String; const qmAfActive : Boolean) : Integer;
begin
   var qmAfJ : Integer;
   var qmAfHit : Integer = -1;
   for qmAfJ:=0 to qmArN-1 do
   if (qmAfHit<0) and ((qmArOn[qmAfJ]=1) or (not qmAfActive)) and (StrPos('|'+qmAfName+'|', qmArNm[qmAfJ])>0) then
   qmAfHit := qmAfJ;
   Result := qmAfHit;
end;

//! -1, 0, 1 for two version texts (digits and dots); a missing part is 0.
function qmArCmpVer(const qmAvA : String; const qmAvB : String) : Integer;
begin
   var qmAvX : String = qmAvA+'.';
   var qmAvY : String = qmAvB+'.';
   var qmAvP : Integer;
   var qmAvQ : Integer;
   var qmAvR : Integer = 0;
   var qmAvI : Integer;
   var qmAvJ : Integer;
   while (qmAvR=0) and ((qmAvX<>'') or (qmAvY<>'')) do
   begin
      qmAvI := 0;
      qmAvJ := 0;
      qmAvP := StrPos('.', qmAvX);
      if (qmAvP>0) then
      begin
         qmAvI := StrToInt(SubStr(qmAvX, 1, qmAvP-1));
         qmAvX := SubStr(qmAvX, qmAvP+1, StrLength(qmAvX)-qmAvP);
      end;
      qmAvQ := StrPos('.', qmAvY);
      if (qmAvQ>0) then
      begin
         qmAvJ := StrToInt(SubStr(qmAvY, 1, qmAvQ-1));
         qmAvY := SubStr(qmAvY, qmAvQ+1, StrLength(qmAvY)-qmAvQ);
      end;
      if (qmAvI<qmAvJ) then
      qmAvR := -1
      else
      if (qmAvI>qmAvJ) then
      qmAvR := 1;
   end;
   Result := qmAvR;
end;

//! One of the two extends the other (an add-on and its base).
function qmArRelated(const qmAeA : Integer; const qmAeB : Integer) : Boolean;
begin
   Result := ((qmArExt[qmAeA]<>'') and (StrPos('|'+qmArExt[qmAeA]+'|', qmArNm[qmAeB])>0)) or ((qmArExt[qmAeB]<>'') and (StrPos('|'+qmArExt[qmAeB]+'|', qmArNm[qmAeA])>0));
end;

//! One of the two lists a name of the other in compatibleWith.
function qmArCompat(const qmAcA : Integer; const qmAcB : Integer) : Boolean;
begin
   var qmAcHit : Boolean = False;
   var qmAcK : Integer;
   var qmAcN : String;
   var qmAcCount : Integer;
   qmAcCount := 0;
   for qmAcK:=1 to StrLength(qmArNm[qmAcB]) do
   if (SubStr(qmArNm[qmAcB], qmAcK, 1)='|') then
   qmAcCount := qmAcCount+1;
   for qmAcK:=1 to qmAcCount-1 do
   begin
      qmField(qmArNm[qmAcB], '|', qmAcK, qmAcN);
      if (qmAcN<>'') and (StrPos('|'+qmAcN+'|', qmArCmp[qmAcA])>0) then
      qmAcHit := True;
   end;
   qmAcCount := 0;
   for qmAcK:=1 to StrLength(qmArNm[qmAcA]) do
   if (SubStr(qmArNm[qmAcA], qmAcK, 1)='|') then
   qmAcCount := qmAcCount+1;
   for qmAcK:=1 to qmAcCount-1 do
   begin
      qmField(qmArNm[qmAcA], '|', qmAcK, qmAcN);
      if (qmAcN<>'') and (StrPos('|'+qmAcN+'|', qmArCmp[qmAcB])>0) then
      qmAcHit := True;
   end;
   Result := qmAcHit;
end;

for qmArK:=0 to qmArN-1 do
begin
   qmArI := qmArOrd[qmArK];
   if (qmArOn[qmArI]=1) and (qmArI<>qmArSelf) then
   begin
      qmArS := IntToStr(qmArI);
      qmArNeed := ParserGetIntValueByKeyByHandle(qmArA, 'rqn'+qmArS);
      qmArDone := False;
      for qmArM:=0 to qmArNeed do
      begin
         qmArRid := '';
         qmArVer := '';
         if (qmArM<qmArNeed) then
         begin
            qmArRid := ParserGetValueByKeyByHandle(qmArA, 'rqi'+qmArS+'_'+IntToStr(qmArM));
            qmArVer := ParserGetValueByKeyByHandle(qmArA, 'rqv'+qmArS+'_'+IntToStr(qmArM));
            if (qmArRid=qmArExt[qmArI]) then
            qmArDone := True;
         end
         else
         if (qmArExt[qmArI]<>'') and (not qmArDone) then
         qmArRid := qmArExt[qmArI];
         if (qmArRid<>'') then
         begin
            qmArHit := qmArFind(qmArRid, True);
            if (qmArHit<0) then
            begin
               qmArJ := qmArFind(qmArRid, False);
               if (qmArJ>=0) then
               qmArAdd(qmArI, 'FAIL', 'requires', qmArTit[qmArI]+' needs '+qmArTit[qmArJ]+', which is not active', qmArJ)
               else
               qmArAdd(qmArI, 'FAIL', 'requires', qmArTit[qmArI]+' needs '+qmArRid+', which is not installed', -1);
            end
            else
            if (qmArVer<>'') then
            begin
               qmArHave := ParserGetValueByKeyByHandle(qmArA, 'ver'+IntToStr(qmArHit));
               if (qmArHave='') then
               qmArAdd(qmArI, 'WARN', 'version', qmArTit[qmArI]+' needs '+qmArTit[qmArHit]+' '+qmArVer+' or later; its version is not known', qmArHit)
               else
               if (qmArCmpVer(qmArHave, qmArVer)<0) then
               qmArAdd(qmArI, 'FAIL', 'version', qmArTit[qmArI]+' needs '+qmArTit[qmArHit]+' '+qmArVer+' or later, not '+qmArHave, qmArHit);
            end;
         end;
      end;
      qmArT := ParserGetValueByKeyByHandle(qmArA, 'qmv'+qmArS);
      if (qmArT<>'') and (qmArCmpVer(${version}, qmArT)<0) then
      qmArAdd(qmArI, 'WARN', 'quartermaster', qmArTit[qmArI]+' is made for Quartermaster '+qmArT+' or later, this is '+${version}, -1);
      qmArT := ParserGetValueByKeyByHandle(qmArA, 'inc'+qmArS);
      qmArM := 0;
      for qmArJ:=1 to StrLength(qmArT) do
      if (SubStr(qmArT, qmArJ, 1)='|') then
      qmArM := qmArM+1;
      for qmArJ:=1 to qmArM-1 do
      begin
         qmField(qmArT, '|', qmArJ, qmArU);
         qmArHit := qmArFind(qmArU, True);
         if (qmArHit>=0) and (qmArHit<>qmArI) then
         qmArAdd(qmArI, 'FAIL', 'incompatible', qmArTit[qmArI]+' does not work with '+qmArTit[qmArHit], qmArHit);
      end;
   end;
end;
var qmArSlot : String;
var qmArL : Integer;
var qmArK2 : Integer;
for qmArK:=0 to qmArN-1 do
begin
   qmArI := qmArOrd[qmArK];
   if (qmArOn[qmArI]=1) and (qmArI<>qmArSelf) then
   for qmArK2:=0 to qmArK-1 do
   begin
      qmArJ := qmArOrd[qmArK2];
      if (qmArOn[qmArJ]=1) and (qmArJ<>qmArSelf) and (not qmArRelated(qmArI, qmArJ)) then
      begin
         if (qmArTy[qmArI]='totalconversion') and (qmArTy[qmArJ]='totalconversion') then
         qmArAdd(qmArI, 'FAIL', 'total', qmArTit[qmArJ]+' and '+qmArTit[qmArI]+' are both total conversions; only one can be active', qmArJ);
         if (not qmArCompat(qmArI, qmArJ)) then
         begin
            qmArL := 0;
            for qmArM:=1 to StrLength(qmArExcl[qmArI]) do
            if (SubStr(qmArExcl[qmArI], qmArM, 1)='|') then
            qmArL := qmArL+1;
            qmArDone := False;
            for qmArM:=1 to qmArL-1 do
            if (not qmArDone) then
            begin
               qmField(qmArExcl[qmArI], '|', qmArM, qmArSlot);
               if (StrPos('|'+qmArSlot+'|', qmArExcl[qmArJ])>0) then
               begin
                  qmArAdd(qmArI, 'FAIL', 'exclusive', qmArTit[qmArJ]+' and '+qmArTit[qmArI]+' both take the '+qmArSlot+' slot; only one can be active', qmArJ);
                  qmArDone := True;
               end;
            end;
         end;
      end;
   end;
end;
//! A load order set by hand (plan S11) that breaks a constraint.
for qmArK:=0 to qmArN-1 do
begin
   qmArI := qmArOrd[qmArK];
   if (qmArOn[qmArI]=1) and (qmArI<>qmArSelf) then
   begin
      qmArT := ParserGetValueByKeyByHandle(qmArA, 'pre'+IntToStr(qmArI));
      for qmArJ:=0 to qmArN-1 do
      if (StrPos('|'+IntToStr(qmArJ)+'|', qmArT)>0) and (qmArOn[qmArJ]=1) and (qmArPos[qmArJ]>qmArPos[qmArI]) then
      qmArAdd(qmArI, 'WARN', 'order', qmArTit[qmArI]+' should load after '+qmArTit[qmArJ], qmArJ);
   end;
end;
ParserSetIntValueByKeyByHandle(qmArR, 'n', qmArPn);
