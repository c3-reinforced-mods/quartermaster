state: qmAbout
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qmunesc
requires: maxsettings, rawsettings
---
//! Every registered mod's about.cfg (plan G4; the grammar and the twin are
//! ref/about.py, the author's side docs/authoring.md) into the named parser
//! qm_about. qmBoot runs it first, before qmModList: the canonical load
//! order takes the files' load-order rules (pre<i>), the rules of the active
//! set (qmAbRules) and the settings (qmSettings) read the rest.
//!
//! The file is read with the raw reader's size-unknown path (OpenFileRead +
//! ReadInteger with the variable preset to 0, src/lib/qmraw.pas): a mod's
//! file has no known size. Each line is handled as soon as it is complete,
//! so no line pool is declared - a String array costs time on every call of
//! the state that declares it. Lines are internal strings (bytes outside
//! 32..122 as ~NNN): `|` is ~124, a tab ~009, a BOM ~239~187~191. Texts the
//! window shows (name, labels, choices, key and text defaults) are stored as
//! the bytes they stand for (qmUnesc).
//!
//! Keys, per registered row i (ModLibraryGetData order):
//!   n                        rows (at most 256)
//!   has<i>                   1 when the mod ships about.cfg
//!   dir<i>                   the engine's dir (the window matches its rows by it)
//!   tit<i> nm<i>             the title shown; the names it answers to,
//!                            `|a|b|` (declared id, Workshop number or local
//!                            folder name; Quartermaster `|quartermaster|`)
//!   self                     Quartermaster's row (last enabled with core.aix)
//!   id<i> name<i> ver<i> qmv<i> gb<i> type<i> ext<i>
//!   excl<i> aft<i> bef<i> inc<i> cmp<i>   `|a|b|` lists
//!   rqn<i> rqi<i>_<k> rqv<i>_<k>          requires: id, version or ''
//!   pre<i>                   rows that load before it: `|j|k|`
//!   pn<i> pt pc px<i>_<k>    the file's problems: tag, code, text
//!   sn<i> and per setting k: sid sty sdf slb ssc<i>_<k> (id, type, default,
//!                            label, scope), slo shi sst sdc<i>_<k> (numbers,
//!                            scaled by 10^decimals), sop<i>_<k> (`|a|b|`
//!                            choices), smx<i>_<k> (text length, 0 = any),
//!                            sgr<i>_<k> (the title of the `group` line it
//!                            stands under, '' without one)
var qmAbT0 : Float = _misc_GetRealTime;
var qmAbSall : Integer = 0;
var qmAbP : Integer = ParserSelectByKey('qm_about');
if (qmAbP=0) then
qmAbP := ParserCreate('qm_about');
ParserClearByHandle(qmAbP);
var qmAbN : Integer = ModLibraryGetCount;
if (qmAbN>256) then
qmAbN := 256;
var qmAbSi : String = '';
var qmAbPn : Integer = 0;
var qmAbSn : Integer = 0;
var qmAbSids : String = '|';
var qmAbSeen : String = '|';
var qmAbLn : Integer = 0;
var qmAbRn : Integer = 0;
//! Each kept `setting` value with the group it stands under in front,
//! `<group>|<value>`: an internal string never holds `|` (it is ~124), and a
//! second array would cost time on every call.
var qmAbRs : array [0..${rawsettings}-1] of String;
var qmAbGroup : String = '';
var qmAbGp : Integer;
var qmAbV : array [0..6] of String;
var qmAbL : array [0..6] of String;
var qmAbPre : array [0..255] of String;
var qmAbNames : array [0..255] of String;
var qmAbSelfRow : Integer = -1;
var qmAbSelfDir : String = '';
var qmAbKn : String;
var qmAbIdSet : String = 'abcdefghijklmnopqrstuvwxyz0123456789_.-';
var qmAbSidSet : String = 'abcdefghijklmnopqrstuvwxyz0123456789_';

procedure qmAbProb(const qmApTag : String; const qmApCode : String; const qmApText : String);
begin
   var qmApK : String = qmAbSi+'_'+IntToStr(qmAbPn);
   ParserSetValueByKeyByHandle(qmAbP, 'pt'+qmApK, qmApTag);
   ParserSetValueByKeyByHandle(qmAbP, 'pc'+qmApK, qmApCode);
   ParserSetValueByKeyByHandle(qmAbP, 'px'+qmApK, qmApText);
   qmAbPn := qmAbPn+1;
end;

//! Spaces and tabs (~009) dropped at both ends (ref/about.py _strip).
procedure qmAbStrip(const qmAsS : String; var qmAsOut : String);
begin
   var qmAsGo : Boolean = True;
   var qmAsL : Integer;
   qmAsOut := qmAsS;
   while (qmAsGo) do
   begin
      qmAsGo := False;
      qmAsL := StrLength(qmAsOut);
      if (qmAsL>=1) and (SubStr(qmAsOut, 1, 1)=' ') then
      begin
         qmAsOut := SubStr(qmAsOut, 2, qmAsL-1);
         qmAsGo := True;
      end
      else
      if (qmAsL>=4) and (SubStr(qmAsOut, 1, 4)='~009') then
      begin
         qmAsOut := SubStr(qmAsOut, 5, qmAsL-4);
         qmAsGo := True;
      end
      else
      if (qmAsL>=1) and (SubStr(qmAsOut, qmAsL, 1)=' ') then
      begin
         qmAsOut := SubStr(qmAsOut, 1, qmAsL-1);
         qmAsGo := True;
      end
      else
      if (qmAsL>=4) and (SubStr(qmAsOut, qmAsL-3, 4)='~009') then
      begin
         qmAsOut := SubStr(qmAsOut, 1, qmAsL-4);
         qmAsGo := True;
      end;
   end;
end;

//! Non-empty, every character in `set`.
function qmAbIn(const qmAiS : String; const qmAiSet : String) : Boolean;
begin
   var qmAiOk : Boolean = (StrLength(qmAiS)>0);
   var qmAiI : Integer;
   for qmAiI:=1 to StrLength(qmAiS) do
   if (StrPos(SubStr(qmAiS, qmAiI, 1), qmAiSet)=0) then
   qmAiOk := False;
   Result := qmAiOk;
end;

//! Digits and dots, a digit at both ends, no two dots together.
function qmAbIsVer(const qmAvS : String) : Boolean;
begin
   var qmAvL : Integer = StrLength(qmAvS);
   var qmAvOk : Boolean = qmAbIn(qmAvS, '0123456789.');
   if (qmAvOk) then
   begin
      if (SubStr(qmAvS, 1, 1)='.') or (SubStr(qmAvS, qmAvL, 1)='.') or (StrPos('..', qmAvS)>0) then
      qmAvOk := False;
   end;
   Result := qmAvOk;
end;

//! `-?[0-9]+`, and with `dec` also `-?[0-9]+(.[0-9]+)?`.
function qmAbIsNum(const qmAnS : String; const qmAnDec : Boolean) : Boolean;
begin
   var qmAnT : String = qmAnS;
   var qmAnP : Integer;
   var qmAnOk : Boolean;
   if (SubStr(qmAnT, 1, 1)='-') then
   qmAnT := SubStr(qmAnT, 2, StrLength(qmAnT)-1);
   qmAnP := StrPos('.', qmAnT);
   if (qmAnDec) and (qmAnP>0) then
   qmAnOk := qmIsDigits(SubStr(qmAnT, 1, qmAnP-1)) and qmIsDigits(SubStr(qmAnT, qmAnP+1, StrLength(qmAnT)-qmAnP))
   else
   qmAnOk := qmIsDigits(qmAnT);
   Result := qmAnOk;
end;

function qmAbPlaces(const qmAqS : String) : Integer;
begin
   var qmAqP : Integer = StrPos('.', qmAqS);
   if (qmAqP>0) then
   Result := StrLength(qmAqS)-qmAqP
   else
   Result := 0;
end;

function qmAbPow(const qmAwD : Integer) : Integer;
begin
   var qmAwR : Integer = 1;
   var qmAwI : Integer;
   for qmAwI:=1 to qmAwD do
   qmAwR := qmAwR*10;
   Result := qmAwR;
end;

//! A number text (already checked) as an integer scaled by 10^places.
function qmAbScaled(const qmAcS : String; const qmAcD : Integer) : Integer;
begin
   var qmAcT : String = qmAcS;
   var qmAcNeg : Boolean = (SubStr(qmAcT, 1, 1)='-');
   var qmAcP : Integer;
   var qmAcW : String;
   var qmAcF : String = '';
   var qmAcV : Integer;
   if (qmAcNeg) then
   qmAcT := SubStr(qmAcT, 2, StrLength(qmAcT)-1);
   qmAcP := StrPos('.', qmAcT);
   qmAcW := qmAcT;
   if (qmAcP>0) then
   begin
      qmAcW := SubStr(qmAcT, 1, qmAcP-1);
      qmAcF := SubStr(qmAcT, qmAcP+1, StrLength(qmAcT)-qmAcP);
   end;
   while (StrLength(qmAcF)<qmAcD) do
   qmAcF := qmAcF+'0';
   qmAcF := SubStr(qmAcF, 1, qmAcD);
   qmAcV := StrToInt(qmAcW)*qmAbPow(qmAcD);
   if (qmAcF<>'') then
   qmAcV := qmAcV+StrToInt(qmAcF);
   if (qmAcNeg) then
   qmAcV := -qmAcV;
   Result := qmAcV;
end;

//! ref/about.py fixed_text: always `places` decimals.
procedure qmAbFixed(const qmAfV : Integer; const qmAfD : Integer; var qmAfOut : String);
begin
   var qmAfA : Integer = qmAfV;
   var qmAfP : Integer = qmAbPow(qmAfD);
   var qmAfF : String;
   if (qmAfA<0) then
   qmAfA := -qmAfA;
   if (qmAfD=0) then
   qmAfOut := IntToStr(qmAfA)
   else
   begin
      qmAfF := IntToStr(qmAfA mod qmAfP);
      while (StrLength(qmAfF)<qmAfD) do
      qmAfF := '0'+qmAfF;
      qmAfOut := IntToStr(qmAfA div qmAfP)+'.'+qmAfF;
   end;
   if (qmAfV<0) then
   qmAfOut := '-'+qmAfOut;
end;

//! Fields of `s` at a one-character separator.
function qmAbFields(const qmAdS : String; const qmAdSep : String) : Integer;
begin
   var qmAdN : Integer = 1;
   var qmAdI : Integer;
   for qmAdI:=1 to StrLength(qmAdS) do
   if (SubStr(qmAdS, qmAdI, 1)=qmAdSep) then
   qmAdN := qmAdN+1;
   Result := qmAdN;
end;

//! One `setting = ...` value (ref/about.py parse_setting); a usable one is
//! stored as setting qmAbSn, under the group `qmAgGrp`.
procedure qmAbSetting(const qmAgV : String; const qmAgGrp : String);
begin
   var qmAgF : array [0..5] of String;
   var qmAgNf : Integer = qmAbFields(qmAgV, ';');
   var qmAgK : Integer;
   var qmAgT : String;
   var qmAgTs : String;
   var qmAgId : String;
   var qmAgTy : String;
   var qmAgDf : String;
   var qmAgLb : String;
   var qmAgEx : String = '';
   var qmAgSc : String = 'local';
   var qmAgOk : Boolean = True;
   var qmAgKey : String;
   var qmAgParts : array [0..3] of String;
   var qmAgPn : Integer;
   var qmAgRest : String;
   var qmAgP : Integer;
   var qmAgDec : Boolean;
   var qmAgD : Integer;
   var qmAgLo : Integer = 0;
   var qmAgHi : Integer = 0;
   var qmAgSt : Integer = 0;
   var qmAgVal : Integer;
   var qmAgOpts : String = '|';
   var qmAgOn : Integer = 0;
   var qmAgHas : Boolean;
   var qmAgMx : Integer = 0;
   var qmAgU : String;
   for qmAgK:=0 to 5 do
   begin
      qmField(qmAgV, ';', qmAgK, qmAgT);
      qmAbStrip(qmAgT, qmAgF[qmAgK]);
   end;
   if (qmAgNf<4) then
   begin
      qmAbProb('WARN', 'setting-fields', 'setting '''+qmAgV+''' needs id;type;default;label');
      exit;
   end;
   qmLowerAscii(qmAgF[0], qmAgId);
   qmLowerAscii(qmAgF[1], qmAgTy);
   qmAgDf := qmAgF[2];
   qmAgLb := qmAgF[3];
   if (qmAgNf>4) then
   qmAgEx := qmAgF[4];
   if (qmAgNf>5) then
   qmLowerAscii(qmAgF[5], qmAgSc);
   if (not qmAbIn(qmAgId, qmAbSidSet)) then
   begin
      qmAbProb('WARN', 'setting-id', 'setting id '''+qmAgF[0]+''' is not a-z, 0-9, _');
      exit;
   end;
   if (StrPos('|'+qmAgTy+'|', '|bool|int|float|choice|key|text|')=0) then
   begin
      qmAbProb('WARN', 'setting-type', 'setting '+qmAgId+': type '''+qmAgF[1]+''' is not one of bool, int, float, choice, key, text');
      exit;
   end;
   if (qmAgSc='') then
   qmAgSc := 'local';
   if (qmAgSc<>'local') and (qmAgSc<>'host') then
   begin
      qmAbProb('WARN', 'setting-scope', 'setting '+qmAgId+': scope '''+qmAgF[5]+''' is not local or host');
      qmAgSc := 'local';
   end;
   if (qmAgLb='') then
   qmAgLb := qmAgId;
   qmAgD := 0;
   if (qmAgTy='bool') then
   begin
      qmLowerAscii(qmAgDf, qmAgT);
      if (StrPos('|'+qmAgT+'|', '|1|true|yes|on|')>0) then
      qmAgDf := '1'
      else
      if (StrPos('|'+qmAgT+'|', '|0|false|no|off|')>0) then
      qmAgDf := '0'
      else
      begin
         qmAbProb('WARN', 'setting-default', 'setting '+qmAgId+': '''+qmAgDf+''' is not a bool; 0 used');
         qmAgDf := '0';
      end;
   end;
   if (qmAgTy='int') or (qmAgTy='float') then
   begin
      qmAgDec := (qmAgTy='float');
      qmAgPn := 0;
      if (qmAgEx<>'') then
      begin
         qmAgRest := qmAgEx;
         qmAgP := StrPos('..', qmAgRest);
         while (qmAgP>0) and (qmAgPn<3) do
         begin
            qmAbStrip(SubStr(qmAgRest, 1, qmAgP-1), qmAgParts[qmAgPn]);
            qmAgPn := qmAgPn+1;
            qmAgRest := SubStr(qmAgRest, qmAgP+2, StrLength(qmAgRest)-qmAgP-1);
            qmAgP := StrPos('..', qmAgRest);
         end;
         if (qmAgP>0) then
         qmAgPn := 9
         else
         begin
            qmAbStrip(qmAgRest, qmAgParts[qmAgPn]);
            qmAgPn := qmAgPn+1;
         end;
      end;
      if (qmAgPn<>2) and (qmAgPn<>3) then
      qmAgOk := False
      else
      for qmAgK:=0 to qmAgPn-1 do
      if (not qmAbIsNum(qmAgParts[qmAgK], qmAgDec)) then
      qmAgOk := False;
      if (not qmAgOk) then
      begin
         qmAbProb('WARN', 'setting-range', 'setting '+qmAgId+': range '''+qmAgEx+''' is not min..max or min..max..step');
         exit;
      end;
      if (not qmAbIsNum(qmAgDf, qmAgDec)) then
      begin
         qmAbProb('WARN', 'setting-default', 'setting '+qmAgId+': default '''+qmAgDf+''' is not a number');
         exit;
      end;
      if (qmAgDec) then
      begin
         qmAgD := qmAbPlaces(qmAgDf);
         for qmAgK:=0 to qmAgPn-1 do
         if (qmAbPlaces(qmAgParts[qmAgK])>qmAgD) then
         qmAgD := qmAbPlaces(qmAgParts[qmAgK]);
      end;
      qmAgLo := qmAbScaled(qmAgParts[0], qmAgD);
      qmAgHi := qmAbScaled(qmAgParts[1], qmAgD);
      if (qmAgPn=3) then
      qmAgSt := qmAbScaled(qmAgParts[2], qmAgD)
      else
      qmAgSt := qmAbPow(qmAgD);
      if (qmAgLo>qmAgHi) or (qmAgSt<=0) then
      begin
         qmAbProb('WARN', 'setting-range', 'setting '+qmAgId+': range '''+qmAgEx+''' is empty');
         exit;
      end;
      qmAgVal := qmAbScaled(qmAgDf, qmAgD);
      if (qmAgVal<qmAgLo) or (qmAgVal>qmAgHi) then
      begin
         qmAbProb('WARN', 'setting-default', 'setting '+qmAgId+': default '+qmAgDf+' is outside '+qmAgEx+'; clamped');
         if (qmAgVal<qmAgLo) then
         qmAgVal := qmAgLo;
         if (qmAgVal>qmAgHi) then
         qmAgVal := qmAgHi;
      end;
      qmAbFixed(qmAgVal, qmAgD, qmAgDf);
   end;
   if (qmAgTy='choice') then
   begin
      qmAgRest := qmAgEx;
      while (StrPos('~124', qmAgRest)>0) do
      qmAgRest := StrReplace(qmAgRest, '~124', '|');
      qmAgHas := False;
      for qmAgK:=0 to qmAbFields(qmAgRest, '|')-1 do
      begin
         qmField(qmAgRest, '|', qmAgK, qmAgT);
         qmAbStrip(qmAgT, qmAgTs);
         qmAgT := qmAgTs;
         if (qmAgT<>'') then
         begin
            if (qmAgOn=0) then
            qmAgKey := qmAgT;
            if (qmAgT=qmAgDf) then
            qmAgHas := True;
            qmUnesc(qmAgT, qmAgU);
            qmAgOpts := qmAgOpts+qmAgU+'|';
            qmAgOn := qmAgOn+1;
         end;
      end;
      if (qmAgOn=0) then
      begin
         qmAbProb('WARN', 'setting-options', 'setting '+qmAgId+': no options (a|b|c)');
         exit;
      end;
      if (not qmAgHas) then
      begin
         qmAbProb('WARN', 'setting-default', 'setting '+qmAgId+': default '''+qmAgDf+''' is not an option; the first one used');
         qmAgDf := qmAgKey;
      end;
   end;
   if (qmAgTy='key') and (qmAgDf='') then
   begin
      qmAbProb('WARN', 'setting-default', 'setting '+qmAgId+': a key setting needs a default key');
      exit;
   end;
   if (qmAgTy='text') and (qmAgEx<>'') then
   begin
      if (not qmAbIsNum(qmAgEx, False)) or (SubStr(qmAgEx, 1, 1)='-') then
      qmAbProb('WARN', 'setting-range', 'setting '+qmAgId+': max length '''+qmAgEx+''' is not a number')
      else
      if (StrToInt(qmAgEx)<1) then
      qmAbProb('WARN', 'setting-range', 'setting '+qmAgId+': max length '''+qmAgEx+''' is not a number')
      else
      begin
         qmAgMx := StrToInt(qmAgEx);
         qmUnesc(qmAgDf, qmAgU);
         if (StrLength(qmAgU)>qmAgMx) then
         begin
            qmAgDf := '';
            qmAbProb('WARN', 'setting-default', 'setting '+qmAgId+': default is longer than '+IntToStr(qmAgMx)+'; empty used');
         end;
      end;
   end;
   if (StrPos('|'+qmAgId+'|', qmAbSids)>0) then
   begin
      qmAbProb('WARN', 'setting-twice', 'setting '+qmAgId+' is declared twice; the first one counts');
      exit;
   end;
   if (qmAbSn>=${maxsettings}) then
   begin
      qmAbProb('WARN', 'setting-many', 'more than '+IntToStr(${maxsettings})+' settings; setting '+qmAgId+' dropped');
      exit;
   end;
   qmAbSids := qmAbSids+qmAgId+'|';
   qmAgKey := qmAbSi+'_'+IntToStr(qmAbSn);
   ParserSetValueByKeyByHandle(qmAbP, 'sid'+qmAgKey, qmAgId);
   ParserSetValueByKeyByHandle(qmAbP, 'sty'+qmAgKey, qmAgTy);
   qmUnesc(qmAgDf, qmAgU);
   ParserSetValueByKeyByHandle(qmAbP, 'sdf'+qmAgKey, qmAgU);
   qmUnesc(qmAgLb, qmAgU);
   ParserSetValueByKeyByHandle(qmAbP, 'slb'+qmAgKey, qmAgU);
   ParserSetValueByKeyByHandle(qmAbP, 'ssc'+qmAgKey, qmAgSc);
   ParserSetIntValueByKeyByHandle(qmAbP, 'slo'+qmAgKey, qmAgLo);
   ParserSetIntValueByKeyByHandle(qmAbP, 'shi'+qmAgKey, qmAgHi);
   ParserSetIntValueByKeyByHandle(qmAbP, 'sst'+qmAgKey, qmAgSt);
   ParserSetIntValueByKeyByHandle(qmAbP, 'sdc'+qmAgKey, qmAgD);
   ParserSetValueByKeyByHandle(qmAbP, 'sop'+qmAgKey, qmAgOpts);
   ParserSetIntValueByKeyByHandle(qmAbP, 'smx'+qmAgKey, qmAgMx);
   qmUnesc(qmAgGrp, qmAgU);
   ParserSetValueByKeyByHandle(qmAbP, 'sgr'+qmAgKey, qmAgU);
   qmAbSn := qmAbSn+1;
end;

//! One line of the file (ref/about.py parse_lines, the loop body).
procedure qmAbLine(const qmAlL : String);
begin
   var qmAlS : String = qmAlL;
   var qmAlEq : Integer;
   var qmAlK : String;
   var qmAlV : String;
   var qmAlT : String;
   var qmAlX : Integer;
   qmAbLn := qmAbLn+1;
   if (qmAbLn=1) and (SubStr(qmAlS, 1, 12)='~239~187~191') then
   qmAlS := SubStr(qmAlS, 13, StrLength(qmAlS)-12);
   qmAbStrip(qmAlS, qmAlT);
   qmAlS := qmAlT;
   if (qmAlS='') or (SubStr(qmAlS, 1, 1)='#') then
   exit;
   qmAlEq := StrPos('=', qmAlS);
   if (qmAlEq=0) then
   begin
      qmAbProb('WARN', 'line', 'line '+IntToStr(qmAbLn)+' is not key = value');
      exit;
   end;
   qmAbStrip(SubStr(qmAlS, 1, qmAlEq-1), qmAlT);
   qmLowerAscii(qmAlT, qmAlK);
   qmAbStrip(SubStr(qmAlS, qmAlEq+1, StrLength(qmAlS)-qmAlEq), qmAlV);
   qmAlX := StrPos('|'+qmAlK+'|', '|id|name|version|quartermaster|gamebuild|type|extends|');
   if (qmAlX>0) then
   begin
      if (StrPos('|'+qmAlK+'|', qmAbSeen)>0) then
      qmAbProb('WARN', 'repeated', 'line '+IntToStr(qmAbLn)+': '+qmAlK+' is given twice; the last one counts');
      qmAbSeen := qmAbSeen+qmAlK+'|';
      if (qmAlK='id') then qmAbV[0] := qmAlV;
      if (qmAlK='name') then qmAbV[1] := qmAlV;
      if (qmAlK='version') then qmAbV[2] := qmAlV;
      if (qmAlK='quartermaster') then qmAbV[3] := qmAlV;
      if (qmAlK='gamebuild') then qmAbV[4] := qmAlV;
      if (qmAlK='type') then qmAbV[5] := qmAlV;
      if (qmAlK='extends') then qmAbV[6] := qmAlV;
      exit;
   end;
   //! A heading for the settings that follow, up to the next one.
   if (qmAlK='group') then
   begin
      if (qmAlV='') then
      qmAbProb('WARN', 'group', 'line '+IntToStr(qmAbLn)+': group needs a title; ignored')
      else
      qmAbGroup := qmAlV;
      exit;
   end;
   if (qmAlK='setting') then
   begin
      if (qmAbRn>=${rawsettings}) then
      qmAbProb('WARN', 'setting-lines', 'line '+IntToStr(qmAbLn)+': more than '+IntToStr(${rawsettings})+' setting lines; ignored')
      else
      begin
         qmAbRs[qmAbRn] := qmAbGroup+'|'+qmAlV;
         qmAbRn := qmAbRn+1;
      end;
      exit;
   end;
   qmAlX := -1;
   if (qmAlK='exclusive') then qmAlX := 0;
   if (qmAlK='requires') then qmAlX := 1;
   if (qmAlK='loadafter') then qmAlX := 2;
   if (qmAlK='loadbefore') then qmAlX := 3;
   if (qmAlK='incompatiblewith') then qmAlX := 4;
   if (qmAlK='compatiblewith') then qmAlX := 5;
   if (qmAlK='extradirs') then qmAlX := 6;
   if (qmAlX<0) then
   begin
      qmAbProb('WARN', 'unknown', 'line '+IntToStr(qmAbLn)+': unknown key '''+qmAlK+'''');
      exit;
   end;
   qmAbL[qmAlX] := qmAbL[qmAlX]+';'+qmAlV;
end;

//! A `;` list's items, stripped, empty ones dropped, as `|a|b|` - only for
//! ids, which never hold `|` (checked by the caller).
procedure qmAbList(const qmAtKey : String; const qmAtName : String; const qmAtX : Integer);
begin
   var qmAtOut : String = '|';
   var qmAtK : Integer;
   var qmAtT : String;
   var qmAtU : String;
   var qmAtI : String;
   for qmAtK:=0 to qmAbFields(qmAbL[qmAtX], ';')-1 do
   begin
      qmField(qmAbL[qmAtX], ';', qmAtK, qmAtT);
      qmAbStrip(qmAtT, qmAtU);
      qmAtT := qmAtU;
      if (qmAtT<>'') then
      begin
         qmLowerAscii(qmAtT, qmAtI);
         if (not qmAbIn(qmAtI, qmAbIdSet)) then
         qmAbProb('WARN', 'list', qmAtName+' '''+qmAtT+''' is not a mod id; ignored')
         else
         if (StrPos('|'+qmAtI+'|', qmAtOut)=0) then
         qmAtOut := qmAtOut+qmAtI+'|';
      end;
   end;
   if (qmAtOut='|') then
   qmAtOut := '';
   ParserSetValueByKeyByHandle(qmAbP, qmAtKey+qmAbSi, qmAtOut);
end;

var qmAbTag, qmAbDir, qmAbLast, qmAbTit, qmAbOwn, qmAbDesc, qmAbTags, qmAbUrl, qmAbNote : String;
var qmAbNumf, qmAbVis : Integer;
var qmAbDis, qmAbAcc, qmAbBan, qmAbRoot : Boolean;
var qmAbI : Integer;
var qmAbJ : Integer;
var qmAbK : Integer;
var qmAbM : Integer;
var qmAbT : String;
//! A second variable for a result: a variable passed both by value and as
//! a var parameter comes back damaged in the game (probe runs of 2026-09-29).
var qmAbTu : String;
var qmAbU : String;
var qmAbX : String;
var qmAbLow : String;
var qmAbRest : String;
var qmAbW : String = '..\..\workshop\content\333420\';
var qmAbTbl : String = ' !"#$%&''()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz';
var qmAbFs : Integer;
var qmAbInt : Integer;
var qmAbSh : Integer;
var qmAbB : Integer;
var qmAbCur : String;
var qmAbE : String;
var qmAbDone : Boolean;
var qmAbInts : Integer;
var qmAbFiles : Integer = 0;
var qmAbPath : String;
var qmAbRq : Integer;
var qmAbRid : String;
var qmAbRv : String;
var qmAbP2 : Integer;
for qmAbI:=0 to qmAbN-1 do
begin
   ModLibraryGetData(qmAbI, qmAbTag, qmAbDir, qmAbLast, qmAbTit, qmAbOwn, qmAbDesc, qmAbTags, qmAbUrl, qmAbNote, qmAbNumf, qmAbVis, qmAbDis, qmAbAcc, qmAbBan, qmAbRoot);
   if (not qmAbDis) and (FileAge(qmAbDir+'\data\quartermaster\core.aix')<>-1) then
   begin
      qmAbSelfRow := qmAbI;
      qmAbSelfDir := qmAbDir;
   end;
end;
for qmAbI:=0 to qmAbN-1 do
begin
   //! For a folder without mod.ini the engine leaves the title and `last`
   //! untouched: they would still hold the row before's (run b4, 2026-09-29).
   qmAbTit := '';
   qmAbLast := '';
   ModLibraryGetData(qmAbI, qmAbTag, qmAbDir, qmAbLast, qmAbTit, qmAbOwn, qmAbDesc, qmAbTags, qmAbUrl, qmAbNote, qmAbNumf, qmAbVis, qmAbDis, qmAbAcc, qmAbBan, qmAbRoot);
   qmAbSi := IntToStr(qmAbI);
   if (qmAbTit='') then
   qmAbTit := qmAbLast;
   if (qmAbTit='') then
   qmAbTit := qmAbDir;
   ParserSetValueByKeyByHandle(qmAbP, 'tit'+qmAbSi, qmAbTit);
   ParserSetValueByKeyByHandle(qmAbP, 'dir'+qmAbSi, qmAbDir);
   qmAbPn := 0;
   qmAbSn := 0;
   qmAbSids := '|';
   qmAbSeen := '|';
   qmAbLn := 0;
   qmAbRn := 0;
   qmAbGroup := '';
   qmAbPre[qmAbI] := '|';
   for qmAbK:=0 to 6 do
   begin
      qmAbV[qmAbK] := '';
      qmAbL[qmAbK] := '';
   end;
   qmAbPath := qmAbDir+'\about.cfg';
   //! No about.cfg of its own: Quartermaster's list entry for a Workshop mod
   //! (ref/about.py known_name), read the same way; kn<i> = 1, has<i> stays 0.
   qmAbKn := '';
   if (FileAge(qmAbPath)=-1) and (qmAbSelfDir<>'') and (StrLength(qmAbDir)>StrLength(qmAbW)) and (SubStr(qmAbDir, 1, StrLength(qmAbW))=qmAbW) then
   begin
      qmAbKn := qmAbSelfDir+'\data\quartermaster\known\'+SubStr(qmAbDir, StrLength(qmAbW)+1, StrLength(qmAbDir))+'.cfg';
      if (FileAge(qmAbKn)<>-1) then
      begin
         qmAbPath := qmAbKn;
         ParserSetIntValueByKeyByHandle(qmAbP, 'kn'+qmAbSi, 1);
      end
      else
      qmAbKn := '';
   end;
   if (FileAge(qmAbPath)<>-1) then
   begin
      qmAbFiles := qmAbFiles+1;
      if (qmAbKn='') then
      ParserSetIntValueByKeyByHandle(qmAbP, 'has'+qmAbSi, 1)
      else
      ParserSetIntValueByKeyByHandle(qmAbP, 'has'+qmAbSi, 0);
      qmAbFs := OpenFileRead(qmAbPath);
      qmAbCur := '';
      qmAbDone := False;
      qmAbInts := 0;
      while (not qmAbDone) and (qmAbInts<262144) do
      begin
         qmAbInt := 0;
         ReadInteger(qmAbFs, qmAbInt);
         qmAbInts := qmAbInts+1;
         for qmAbSh:=0 to 3 do
         if (not qmAbDone) then
         begin
            qmAbB := (qmAbInt shr (qmAbSh*8)) and 255;
            if (qmAbB=0) then
            qmAbDone := True
            else
            if (qmAbB=10) then
            begin
               qmAbLine(qmAbCur);
               qmAbCur := '';
            end
            else
            if (qmAbB<>13) then
            begin
               if (qmAbB>=32) and (qmAbB<=122) then
               qmAbCur := qmAbCur+SubStr(qmAbTbl, qmAbB-31, 1)
               else
               begin
                  qmAbE := IntToStr(qmAbB);
                  while (StrLength(qmAbE)<3) do
                  qmAbE := '0'+qmAbE;
                  qmAbCur := qmAbCur+'~'+qmAbE;
               end;
            end;
         end;
      end;
      CloseFile(qmAbFs);
      if (qmAbCur<>'') then
      qmAbLine(qmAbCur);
      //! The values, in ref/about.py parse_lines order (its problems too).
      if (StrPos('|id|', qmAbSeen)>0) then
      begin
         qmLowerAscii(qmAbV[0], qmAbT);
         if (not qmAbIn(qmAbT, qmAbIdSet)) then
         begin
            qmAbProb('FAIL', 'id', 'id '''+qmAbV[0]+''' is not a-z, 0-9, _ . -');
            qmAbT := '';
         end;
         ParserSetValueByKeyByHandle(qmAbP, 'id'+qmAbSi, qmAbT);
      end;
      qmUnesc(qmAbV[1], qmAbU);
      ParserSetValueByKeyByHandle(qmAbP, 'name'+qmAbSi, qmAbU);
      ParserSetValueByKeyByHandle(qmAbP, 'gb'+qmAbSi, qmAbV[4]);
      if (StrPos('|version|', qmAbSeen)>0) then
      begin
         if (not qmAbIsVer(qmAbV[2])) then
         qmAbProb('WARN', 'version', 'version '''+qmAbV[2]+''' is not digits and dots')
         else
         ParserSetValueByKeyByHandle(qmAbP, 'ver'+qmAbSi, qmAbV[2]);
      end;
      if (StrPos('|quartermaster|', qmAbSeen)>0) then
      begin
         if (not qmAbIsVer(qmAbV[3])) then
         qmAbProb('WARN', 'version', 'quartermaster '''+qmAbV[3]+''' is not digits and dots')
         else
         ParserSetValueByKeyByHandle(qmAbP, 'qmv'+qmAbSi, qmAbV[3]);
      end;
      ParserSetValueByKeyByHandle(qmAbP, 'type'+qmAbSi, 'mod');
      if (StrPos('|type|', qmAbSeen)>0) then
      begin
         qmLowerAscii(qmAbV[5], qmAbT);
         if (StrPos('|'+qmAbT+'|', '|mod|totalconversion|library|')=0) then
         qmAbProb('FAIL', 'type', 'type '''+qmAbV[5]+''' is not mod, totalConversion or library')
         else
         ParserSetValueByKeyByHandle(qmAbP, 'type'+qmAbSi, qmAbT);
      end;
      if (StrPos('|extends|', qmAbSeen)>0) then
      begin
         qmLowerAscii(qmAbV[6], qmAbT);
         if (not qmAbIn(qmAbT, qmAbIdSet)) then
         qmAbProb('FAIL', 'extends', 'extends '''+qmAbV[6]+''' is not a mod id')
         else
         ParserSetValueByKeyByHandle(qmAbP, 'ext'+qmAbSi, qmAbT);
      end;
      //! exclusive: slots, FAIL for an unknown one.
      qmAbX := '|';
      for qmAbK:=0 to qmAbFields(qmAbL[0], ';')-1 do
      begin
         qmField(qmAbL[0], ';', qmAbK, qmAbT);
         qmAbStrip(qmAbT, qmAbTu);
         qmAbT := qmAbTu;
         if (qmAbT<>'') then
         begin
            qmLowerAscii(qmAbT, qmAbU);
            if (StrPos('|'+qmAbU+'|', '|camera|ai|ui|balance|economy|sound|graphics|hotkeys|')=0) then
            qmAbProb('FAIL', 'exclusive', 'exclusive '''+qmAbT+''' is not one of camera, ai, ui, balance, economy, sound, graphics, hotkeys')
            else
            if (StrPos('|'+qmAbU+'|', qmAbX)=0) then
            qmAbX := qmAbX+qmAbU+'|';
         end;
      end;
      if (qmAbX='|') then
      qmAbX := '';
      ParserSetValueByKeyByHandle(qmAbP, 'excl'+qmAbSi, qmAbX);
      //! requires: id or id>=version, FAIL otherwise.
      qmAbRq := 0;
      for qmAbK:=0 to qmAbFields(qmAbL[1], ';')-1 do
      begin
         qmField(qmAbL[1], ';', qmAbK, qmAbT);
         qmAbStrip(qmAbT, qmAbTu);
         qmAbT := qmAbTu;
         if (qmAbT<>'') then
         begin
            qmAbRid := qmAbT;
            qmAbRv := '';
            qmAbP2 := StrPos('>=', qmAbT);
            if (qmAbP2>0) then
            begin
               qmAbStrip(SubStr(qmAbT, 1, qmAbP2-1), qmAbRid);
               qmAbStrip(SubStr(qmAbT, qmAbP2+2, StrLength(qmAbT)-qmAbP2-1), qmAbRv);
            end;
            qmLowerAscii(qmAbRid, qmAbTu);
            qmAbRid := qmAbTu;
            if (not qmAbIn(qmAbRid, qmAbIdSet)) or ((qmAbP2>0) and (not qmAbIsVer(qmAbRv))) then
            qmAbProb('FAIL', 'requires', 'requires '''+qmAbT+''' is not id or id>=version')
            else
            begin
               ParserSetValueByKeyByHandle(qmAbP, 'rqi'+qmAbSi+'_'+IntToStr(qmAbRq), qmAbRid);
               ParserSetValueByKeyByHandle(qmAbP, 'rqv'+qmAbSi+'_'+IntToStr(qmAbRq), qmAbRv);
               qmAbRq := qmAbRq+1;
            end;
         end;
      end;
      ParserSetIntValueByKeyByHandle(qmAbP, 'rqn'+qmAbSi, qmAbRq);
      qmAbList('aft', 'loadafter', 2);
      qmAbList('bef', 'loadbefore', 3);
      qmAbList('inc', 'incompatiblewith', 4);
      qmAbList('cmp', 'compatiblewith', 5);
      for qmAbK:=0 to qmAbRn-1 do
      begin
         qmAbGp := StrPos('|', qmAbRs[qmAbK]);
         qmAbSetting(SubStr(qmAbRs[qmAbK], qmAbGp+1, StrLength(qmAbRs[qmAbK])-qmAbGp), SubStr(qmAbRs[qmAbK], 1, qmAbGp-1));
      end;
   end
   else
   begin
      ParserSetIntValueByKeyByHandle(qmAbP, 'has'+qmAbSi, 0);
      ParserSetValueByKeyByHandle(qmAbP, 'type'+qmAbSi, 'mod');
   end;
   ParserSetIntValueByKeyByHandle(qmAbP, 'pn'+qmAbSi, qmAbPn);
   ParserSetIntValueByKeyByHandle(qmAbP, 'sn'+qmAbSi, qmAbSn);
   qmAbSall := qmAbSall+qmAbSn;
   //! The names (ref/about.py names): the declared id, then the folder's
   //! identity (ref/order.py identity), ASCII case folded.
   qmAbT := '|';
   if (qmAbI=qmAbSelfRow) then
   qmAbT := '|quartermaster|'
   else
   begin
      if (ParserGetValueByKeyByHandle(qmAbP, 'id'+qmAbSi)<>'') then
      qmAbT := qmAbT+ParserGetValueByKeyByHandle(qmAbP, 'id'+qmAbSi)+'|';
      qmAbX := qmAbDir;
      while (StrPos('/', qmAbX)>0) do
      qmAbX := StrReplace(qmAbX, '/', '\');
      while (StrLength(qmAbX)>0) and (SubStr(qmAbX, StrLength(qmAbX), 1)='\') do
      qmAbX := SubStr(qmAbX, 1, StrLength(qmAbX)-1);
      qmLowerAscii(qmAbX, qmAbLow);
      qmAbU := '';
      if (SubStr(qmAbLow, 1, StrLength(qmAbW))=qmAbW) then
      begin
         qmAbRest := SubStr(qmAbX, StrLength(qmAbW)+1, StrLength(qmAbX)-StrLength(qmAbW));
         if (qmIsDigits(qmAbRest)) then
         qmAbU := qmAbRest;
      end
      else
      if (SubStr(qmAbLow, 1, 5)='mods\') then
      begin
         qmAbRest := SubStr(qmAbLow, 6, StrLength(qmAbLow)-5);
         if (qmAbRest<>'') and (StrPos('\', qmAbRest)=0) then
         qmAbU := qmAbRest;
      end;
      if (qmAbU<>'') and (StrPos('|'+qmAbU+'|', qmAbT)=0) then
      qmAbT := qmAbT+qmAbU+'|';
   end;
   qmAbNames[qmAbI] := qmAbT;
   ParserSetValueByKeyByHandle(qmAbP, 'nm'+qmAbSi, qmAbT);
end;
//! Load-order constraints (ref/about.py edges): requires, extends and
//! loadAfter put the named row before this one, loadBefore this one before
//! the named row; the first registered row with the name, never
//! Quartermaster, never the row itself.
procedure qmAbPut(const qmAuName : String; const qmAuRow : Integer; const qmAuAfter : Boolean);
begin
   var qmAuJ : Integer;
   var qmAuHit : Integer = -1;
   for qmAuJ:=0 to qmAbN-1 do
   if (qmAuHit<0) and (StrPos('|'+qmAuName+'|', qmAbNames[qmAuJ])>0) then
   qmAuHit := qmAuJ;
   if (qmAuHit<0) or (qmAuHit=qmAuRow) or (qmAuHit=qmAbSelfRow) then
   exit;
   if (qmAuAfter) then
   begin
      if (StrPos('|'+IntToStr(qmAuHit)+'|', qmAbPre[qmAuRow])=0) then
      qmAbPre[qmAuRow] := qmAbPre[qmAuRow]+IntToStr(qmAuHit)+'|';
   end
   else
   if (StrPos('|'+IntToStr(qmAuRow)+'|', qmAbPre[qmAuHit])=0) then
   qmAbPre[qmAuHit] := qmAbPre[qmAuHit]+IntToStr(qmAuRow)+'|';
end;

for qmAbI:=0 to qmAbN-1 do
if (qmAbI<>qmAbSelfRow) and (ParserGetIntValueByKeyByHandle(qmAbP, 'has'+IntToStr(qmAbI))=1) then
begin
   qmAbSi := IntToStr(qmAbI);
   for qmAbK:=0 to ParserGetIntValueByKeyByHandle(qmAbP, 'rqn'+qmAbSi)-1 do
   qmAbPut(ParserGetValueByKeyByHandle(qmAbP, 'rqi'+qmAbSi+'_'+IntToStr(qmAbK)), qmAbI, True);
   if (ParserGetValueByKeyByHandle(qmAbP, 'ext'+qmAbSi)<>'') then
   qmAbPut(ParserGetValueByKeyByHandle(qmAbP, 'ext'+qmAbSi), qmAbI, True);
   qmAbT := ParserGetValueByKeyByHandle(qmAbP, 'aft'+qmAbSi);
   for qmAbK:=1 to qmAbFields(qmAbT, '|')-2 do
   begin
      qmField(qmAbT, '|', qmAbK, qmAbU);
      qmAbPut(qmAbU, qmAbI, True);
   end;
   qmAbT := ParserGetValueByKeyByHandle(qmAbP, 'bef'+qmAbSi);
   for qmAbK:=1 to qmAbFields(qmAbT, '|')-2 do
   begin
      qmField(qmAbT, '|', qmAbK, qmAbU);
      qmAbPut(qmAbU, qmAbI, False);
   end;
end;
for qmAbI:=0 to qmAbN-1 do
ParserSetValueByKeyByHandle(qmAbP, 'pre'+IntToStr(qmAbI), qmAbPre[qmAbI]);
ParserSetIntValueByKeyByHandle(qmAbP, 'n', qmAbN);
ParserSetIntValueByKeyByHandle(qmAbP, 'self', qmAbSelfRow);
ParserSetIntValueByKeyByHandle(qmAbP, 'files', qmAbFiles);
//! With the settings read and the time it took: a file may declare a thousand.
qmLog('about files='+IntToStr(qmAbFiles)+' of '+IntToStr(qmAbN)+' settings='+IntToStr(qmAbSall)+' ms='+FloatToStr((_misc_GetRealTime-qmAbT0)*1000));
