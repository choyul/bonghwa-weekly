#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# check_deploy.sh — 배포 전 필수 기능 점검
#   "고쳤던 기능이 배포 과정에서 조용히 빠지는 일"을 막는다.
#   소스(v2)와 배포본(~/bonghwa-weekly)이 어긋나도 잡아낸다.
#   사용: bash build/check_deploy.sh
#   통과하면 exit 0, 하나라도 어긋나면 exit 1 (배포 중단)
# ═══════════════════════════════════════════════════════════════
SRC="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY="$HOME/bonghwa-weekly"
FAIL=0

ok(){ echo "  ✅ $1"; }
no(){ echo "  ❌ $1"; FAIL=1; }

# $1=파일경로 $2=찾을문구 $3=설명
must(){
  if grep -q "$2" "$1" 2>/dev/null; then ok "$3"; else no "$3  ← '$2' 없음: $1"; fi
}

echo "── 1) 소스 ↔ 배포본이 같은지 ──"
# 배포본 index.html 은 소스 public.html 의 복사본이어야 한다
for pair in "public.html:index.html" "mayor.html:mayor.html" "staff.html:staff.html" "ui.js:ui.js" "core.js:core.js" "ui.css:ui.css"; do
  s="${pair%%:*}"; d="${pair##*:}"
  if [ ! -f "$DEPLOY/$d" ]; then no "$d 가 배포 폴더에 없음"; continue; fi
  if diff -q "$SRC/$s" "$DEPLOY/$d" >/dev/null 2>&1; then ok "$s = $d"
  else no "$s 와 $d 가 다름 — 복사가 누락됐습니다"; fi
done

echo "── 2) 공유하기(카톡·문자 시트)가 살아 있는지 ──"
P="$DEPLOY/index.html"
must "$P" "navigator.share"        "군민용: OS 공유 시트 호출부"
must "$P" "function nativeShare"   "군민용: 공유 공통 함수"
must "$P" "shareModal(url,data.text)" "군민용: 공유 실패 시 대체 모달 연결"
must "$P" "shareSms"               "군민용: 공유 시트 없을 때 '문자로 보내기'"
# nativeShare 안에서의 canShare 사전검사는 오탐으로 공유 시트가 죽는 원인 — 되살아나면 실패.
# (캘린더 .ics '파일' 공유의 canShare({files:...}) 는 정당한 사용이므로 건드리지 않는다)
if awk '/function nativeShare/,/^ \}/' "$P" | grep -q "canShare"; then
  no "군민용: nativeShare 안에 canShare() 사전검사가 되살아남 (공유 시트가 안 뜨는 원인)"
else ok "군민용: nativeShare 안에 canShare() 사전검사 없음(정상)"; fi
must "$DEPLOY/mayor.html" "navigator.share" "군수용: 지시 전달 공유 시트"

echo "── 3) 전화 걸기 ──"
must "$DEPLOY/mayor.html" "navigator.contacts" "군수용: 저장된 연락처 선택(안드로이드)"
must "$DEPLOY/mayor.html" "tel:"               "군수용: 전화 걸기 폴백"

echo "── 4) 개인정보가 섞여 들어가지 않았는지 ──"
if grep -rlE "01[016789]-[0-9]{3,4}-[0-9]{4}" "$DEPLOY/data.js" "$DEPLOY/md" 2>/dev/null | grep -q .; then
  no "데이터에 휴대폰번호가 들어 있습니다 — 커밋 금지"
else ok "데이터에 휴대폰번호 없음"; fi

echo ""
if [ $FAIL -eq 0 ]; then
  echo "✅ 전부 통과 — 배포해도 됩니다."
else
  echo "❌ 점검 실패 — 위 항목을 고친 뒤 다시 실행하세요. 배포하지 마세요."
fi
exit $FAIL
