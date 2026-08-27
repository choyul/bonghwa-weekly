#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# check_deploy.sh — 배포 전 필수 기능 점검
#   "고쳤던 기능이 배포 과정에서 조용히 빠지는 일"을 막는다.
#   소스(v2)와 배포본(~/bonghwa-weekly)이 어긋나도 잡아낸다.
#   사용: bash build/check_deploy.sh
#   통과하면 exit 0, 하나라도 어긋나면 exit 1 (배포 중단)
# ═══════════════════════════════════════════════════════════════
SRC="$(cd "$(dirname "$0")/.." && pwd)"
# 배포 폴더. 시험 삼아 다른 폴더로 점검하고 싶으면 BW_DEPLOY 로 바꿀 수 있다.
DEPLOY="${BW_DEPLOY:-$HOME/bonghwa-weekly}"
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
must "$P" "shareSms"               "군민용: 공유 시트 못 쓸 때 '문자로 보내기'"
# 공유가 실패했는데 아무 일도 안 일어나면 사용자는 '고장'으로 느낀다 — 세 구멍을 다 막았는지 확인
must "$P" "try{ p=navigator.share(data); }" "군민용: 공유 호출이 바로 튕겨도 대체창"
must "$P" "typeof p.catch"        "군민용: 공유가 프로미스를 안 줘도 대체창"
must "$P" "const quick=Date.now()-t0<400" "군민용: 즉시 AbortError(실패)를 취소로 오해하지 않음"
must "$P" "shareExt"               "군민용: 카카오톡에서 '기본 브라우저로 열기'(선택지, 작은 링크)"
must "$P" "openExternal"           "군민용: 카카오톡 → 기본 브라우저 전환 스킴"
# nativeShare 안에서의 canShare 사전검사는 오탐으로 공유 시트가 죽는 원인 — 되살아나면 실패.
# (캘린더 .ics '파일' 공유의 canShare({files:...}) 는 정당한 사용이므로 건드리지 않는다)
if awk '/function nativeShare/,/^ \}/' "$P" | grep -q "canShare"; then
  no "군민용: nativeShare 안에 canShare() 사전검사가 되살아남 (공유 시트가 안 뜨는 원인)"
else ok "군민용: nativeShare 안에 canShare() 사전검사 없음(정상)"; fi
must "$DEPLOY/mayor.html" "navigator.share" "군수용: 지시 전달 공유 시트"

# 안드로이드 뒤로가기로 앱이 꺼지지 않게 하는 처리
must "$P" "backClosesOverlay"  "군민용: 뒤로가기가 팝업만 닫고 앱이 꺼지지 않음"
must "$P" "isSamsung"          "군민용: 삼성 인터넷 전용 설치 안내"

echo "── 3) 새소식/행사 전환 ──"
must "$P" "modetabs"    "군민용: 맨 위 [새소식/행사/언론속봉화] 전환 탭"
must "$P" "BW_EVENTS"   "군민용: 행사 데이터 읽기"
must "$P" "events.js"   "군민용: 행사 데이터 로드"
if [ -s "$DEPLOY/events.js" ]; then ok "events.js 존재($(wc -c < "$DEPLOY/events.js" | tr -d ' ')바이트)"
else no "events.js 가 없거나 비었습니다 — 행사 탭이 안 뜹니다"; fi

echo "── 3-2) 계절 마스코트 ──"
# 그림 파일 하나라도 빠지면 그 계절에 캐릭터 자리가 비어 보인다
MISS=""
for m in base s1 s2 s3 f1 f2 f3 w1 w2 w3; do
  if [ ! -s "$DEPLOY/mascot/$m.webp" ]; then MISS="$MISS $m"
  elif ! diff -q "$SRC/mascot/$m.webp" "$DEPLOY/mascot/$m.webp" >/dev/null 2>&1; then MISS="$MISS $m(다름)"; fi
done
if [ -n "$MISS" ]; then no "마스코트 그림이 빠졌거나 다릅니다:$MISS"
else ok "마스코트 10장(기본·여름3·가을3·겨울3) 모두 있음"; fi
must "$P" "MASCOT_SETS"   "군민용: 계절별 마스코트 목록"
must "$P" "mascot/'+MASCOT_KEY" "군민용: 마스코트 그림 연결"

echo "── 3-3) 카카오톡 미리보기(공유 카드) ──"
# 옛 이름 '봉화의 오늘' 이 그림이나 글에 남으면 공유할 때 그대로 보인다
must "$P" 'og:title" content="오늘의 봉화"'     "군민용: 미리보기 제목"
must "$P" 'og:site_name" content="오늘의 봉화"' "군민용: 미리보기 사이트 이름"
if grep -q "봉화의 오늘" "$P"; then no "군민용: 옛 이름 '봉화의 오늘' 이 남아 있습니다"
else ok "군민용: 옛 이름 '봉화의 오늘' 없음"; fi
if [ ! -s "$DEPLOY/og.png" ]; then no "og.png 가 없습니다 — 공유 카드에 그림이 안 뜹니다"
elif ! diff -q "$SRC/og.png" "$DEPLOY/og.png" >/dev/null 2>&1; then no "og.png 가 소스와 배포본에서 다름"
else ok "og.png 소스=배포본"; fi

echo "── 3-4) 안내 브로셔 ──"
if [ ! -s "$DEPLOY/guide.html" ]; then no "guide.html 이 없습니다 — 안내 주소가 안 열립니다"
elif ! diff -q "$SRC/guide.html" "$DEPLOY/guide.html" >/dev/null 2>&1; then no "guide.html 이 소스와 배포본에서 다름"
else ok "guide.html 소스=배포본 ($(( $(wc -c < "$DEPLOY/guide.html") / 1024 ))KB)"; fi
must "$DEPLOY/guide.html" "shareBtn"      "안내: 링크 복사 버튼"
must "$P" "function guideModal"           "군민용: 하단 [가이드] 로 안내 열기"
must "$P" 'data-t="more"'                 "군민용: 하단 탭에 [설정]"
must "$P" "moreGd"                        "군민용: 설정 시트에서 사용 안내 열기"
must "$P" "src=\"guide.html\""             "군민용: 안내 문서 연결"
must "$DEPLOY/guide.html" "guide.html'"   "안내: 복사되는 주소가 공개 주소인지"

echo "── 3-5) 홈 화면 아이콘의 날짜 ──"
# 홈 화면에 박히는 것은 SVG 가 아니라 manifest 가 가리키는 PNG 세 장이다.
# 이게 낡으면 오늘 설치한 사람도 옛 날짜를 보게 된다.
if grep -q "<text" "$DEPLOY/icon.svg"; then
  no "icon.svg 에 <text> 가 남아 있습니다 — 글꼴 없는 서버에서 네모로 그려집니다"
else ok "icon.svg 가 글꼴 없이도 그려집니다(글자를 전부 도형으로)"; fi
for f in icon-m192 icon-m512 icon-mmask512; do
  if [ ! -s "$DEPLOY/$f.png" ]; then no "$f.png 가 없습니다 — 홈 화면 아이콘이 안 나옵니다"
  elif [ -n "$(find "$DEPLOY/$f.png" -mtime +2 2>/dev/null)" ]; then
    echo "  ⚠️  $f.png 가 사흘 넘게 그대로입니다 — 자동 갱신(weekly.yml)이 도는지 확인하세요"
  else ok "$f.png 최신"; fi
done
must "$DEPLOY/build/make_icon_png.sh" "rsvg-convert" "아이콘: PNG 다시 그리기 스크립트"

echo "── 3-6) 공유 링크로 들어온 분께 설치 권유 ──"
must "$P" "url.searchParams.set('a','1')" "군민용: 공유 링크에 설치 권유 표시"
must "$P" "function offerInstall"          "군민용: 설치 권유 함수"
must "$P" "offerInstall('공유링크')"        "군민용: 공유로 들어오면 권유"
must "$P" "if(n>=2)return"                 "군민용: 두 번 사양하면 그만 권함"

echo "── 3-7) 헤더를 줄이고 옮긴 것들이 살아 있는지 ──"
# 헤더 단추 3개를 [⚙️ 설정] 시트로 옮겼다. 시트가 빠지면 바로가기 설치·글씨 크기·맞춤 설정이
# 통째로 사라지는데 눈에 잘 안 띈다 — 그래서 여기서 붙잡는다.
must "$P" "function moreModal"  "군민용: 설정 시트"
must "$P" "headerButtons:\\[\\]"  "군민용: 헤더에 단추 없음(설정 시트로 옮김)"
must "$P" "moreA2"              "군민용: 설정 - 바탕화면 바로가기"
must "$P" 'data-fs="2"'         "군민용: 설정 - 글씨 크기 3단계"
must "$P" "morePf"              "군민용: 설정 - 내 소식 맞춤 설정"
if grep -q 'class="bw-sub"' "$P"; then no "군민용: 헤더 부제가 되살아남 — 헤더는 한 줄로 유지"
else ok "군민용: 헤더가 한 줄(부제 없음)"; fi

echo "── 4) 전화 걸기 ──"
must "$DEPLOY/mayor.html" "navigator.contacts" "군수용: 저장된 연락처 선택(안드로이드)"
must "$DEPLOY/mayor.html" "tel:"               "군수용: 전화 걸기 폴백"

echo "── 5) 한 번 고친 버그가 되살아나지 않았는지 ──"
# (a) data.js 의 builtAt 에 실행시각을 넣으면 내용이 같아도 매일 커밋된다
if grep -q "builtAt: new Date()" "$DEPLOY/build/build.js"; then
  no "build.js: builtAt 이 실행시각으로 되돌아감 (매일 불필요하게 커밋됨)"
else ok "build.js: builtAt 고정값 유지"; fi
# (b) 서비스워커가 HTML/JS 를 캐시 우선으로 주면, 고쳐도 사용자에게 안 간다
if grep -q "cache-first" "$DEPLOY/sw.js" || grep -q "caches.match(e.request, *{ *ignoreSearch" "$DEPLOY/sw.js"; then
  no "sw.js: 앱 셸이 캐시 우선으로 되돌아감 (고친 내용이 사용자에게 전달되지 않음)"
else ok "sw.js: 네트워크 우선 유지"; fi
# (c) 소스와 배포본의 나머지 파일도 어긋나면 안 된다
for f in sw.js build/build.js; do
  if diff -q "$SRC/$f" "$DEPLOY/$f" >/dev/null 2>&1; then ok "$f 소스=배포본"
  else no "$f 가 소스와 배포본에서 다름"; fi
done

echo "── 6) 이용 통계가 살아 있는지 ──"
# 통계는 눈에 안 보여서, 빠져도 한참 뒤에야 안다 — 그래서 여기서 붙잡는다.
if [ ! -s "$DEPLOY/analytics.js" ]; then no "analytics.js 가 배포 폴더에 없습니다"
elif ! diff -q "$SRC/analytics.js" "$DEPLOY/analytics.js" >/dev/null 2>&1; then no "analytics.js 가 소스와 배포본에서 다름"
else ok "analytics.js 소스=배포본"; fi
must "$P" 'src="analytics.js"'   "군민용: 수집기 로드"
must "$P" "const AV=(n,k,t)=>"   "군민용: 통계 호출 도우미(화면)"
must "$P" "const AA=(n,k,t)=>"   "군민용: 통계 호출 도우미(누름)"
must "$P" "AV('소식상세'"        "군민용: 소식 상세 기록"
must "$P" "AA('공유_누름'"       "군민용: 공유 기록"
must "$P" "function trackState"  "군민용: 검색·필터·기간 기록"
must "$P" "AA('공유_대체창')"    "군민용: 공유 대체창 기록(카톡 인앱 비율 판단)"
# 수집 주소가 비어 있으면 통계가 아예 안 쌓인다 — 막지는 않고 알려만 준다(주소 없이도 앱은 정상)
if grep -q "PUT-WORKER-URL-HERE" "$DEPLOY/analytics.js" 2>/dev/null; then
  echo "  ⚠️  수집 주소가 아직 비어 있어 통계가 쌓이지 않습니다 — analytics/setup.sh 를 먼저 실행하세요(앱 동작에는 지장 없음)"
else ok "수집 주소가 채워져 있음"; fi
# 통계에 개인을 알아볼 값이 섞이면 안 된다
if grep -qE "localStorage.getItem\('bh\.(fav|prof)" "$DEPLOY/analytics.js" 2>/dev/null; then
  no "analytics.js 가 개인 저장분(관심·맞춤설정)을 읽고 있습니다"
else ok "analytics.js 가 개인 저장분을 건드리지 않음"; fi

echo "── 6-2) 봉화뉴스가 살아 있는지 · 저작권 선을 넘지 않았는지 ──"
# 뉴스는 남의 저작물을 다루는 화면이라, 기능이 빠지는 것보다
# '선을 넘은 채로 배포되는 것'이 훨씬 위험하다. 그래서 여기서 두 가지를 다 본다.
if [ ! -s "$DEPLOY/build/fetch_news.py" ]; then no "build/fetch_news.py 가 배포 폴더에 없습니다"
elif ! diff -q "$SRC/build/fetch_news.py" "$DEPLOY/build/fetch_news.py" >/dev/null 2>&1; then
  no "fetch_news.py 가 소스와 배포본에서 다름"
else ok "fetch_news.py 소스=배포본"; fi
must "$P" "load('news.js"        "군민용: 뉴스 자료 로드"
must "$P" "function buildNewsView" "군민용: 뉴스 화면"
must "$P" "function renderNews"    "군민용: 뉴스 목록 그리기"
must "$P" "data-m=\\\"news\\\""       "군민용: 뉴스 모드 탭"
must "$P" "nwMissed"             "군민용: 놓친 뉴스 계산"
# (가) 기사는 반드시 언론사 원문으로 '나가야' 한다 — 새 창 + noopener
must "$P" 'class="nw-card" href="${E(n.u)}" target="_blank" rel="noopener noreferrer"' \
                                 "저작권: 기사는 새 창으로 언론사 원문에 링크아웃"
# (나) 원문을 앱 안에 끼워 넣으면(프레이밍) 분쟁 소지가 생긴다
if grep -qE '<iframe[^>]*(n\.u|nw-)' "$P" 2>/dev/null; then
  no "저작권: 뉴스 원문을 iframe 으로 끼워 넣고 있습니다 — 링크아웃만 허용"
else ok "저작권: 뉴스 원문을 프레임으로 끼워 넣지 않음"; fi
# (다) 구글 뉴스 RSS 는 피드 자체가 "개인용 리더에서 개인적·비상업적으로만" 쓰라고 못 박고 있다.
#     커버리지가 넓어 자꾸 손이 가는 곳이라, 되살아나면 여기서 붙잡는다.
if grep -q "news\.google\.com" "$SRC/build/fetch_news.py" 2>/dev/null; then
  no "저작권: 구글 뉴스 RSS 를 쓰고 있습니다 — 공개 사이트 게시는 구글 약관 위반"
else ok "저작권: 구글 뉴스 RSS 를 쓰지 않음"; fi
must "$SRC/build/fetch_news.py" "RSS_FEEDS" "열쇠 없이도 도는 언론사 공식 RSS 수집원"
# (라) 본문·요약(리드문)을 담으면 복제권·2차적저작물작성권 침해 소지가 생긴다.
#     수집기가 description 을 저장하지 않는지, 실제 news.js 에 본문이 없는지 둘 다 본다.
if grep -qE '"(desc|description|body|summary|content)"\s*:' "$SRC/build/fetch_news.py" 2>/dev/null; then
  no "저작권: fetch_news.py 가 기사 본문/요약을 저장하려 합니다 — 제목·언론사·날짜·주소만 담을 것"
else ok "저작권: 수집기가 본문/요약을 저장하지 않음"; fi
if [ -s "$DEPLOY/news.js" ]; then
  if grep -qE '"(desc|description|body|summary|content)":' "$DEPLOY/news.js" 2>/dev/null; then
    no "저작권: news.js 에 기사 본문/요약이 들어 있습니다 — 배포 금지"
  else ok "저작권: news.js 에 본문/요약 없음"; fi
  if grep -q 'n\.news\.naver\.com' "$DEPLOY/news.js" 2>/dev/null; then
    echo "  ⚠️  일부 기사가 네이버 안쪽 주소로 걸려 있습니다(원문 주소가 없는 기사) — 대개는 정상입니다"
  else ok "저작권: 모든 기사가 언론사 원문 주소"; fi
else
  echo "  ⚠️  news.js 가 아직 없습니다 — 네이버 API 열쇠를 넣고 자동 갱신이 한 번 돌면 생깁니다(앱 동작에는 지장 없음)"
fi
# (마) 출처·저작권 고지가 화면에 남아 있어야 한다
must "$P" "기사의 저작권은 각 언론사에 있습니다" "저작권: 화면에 저작권 고지"

echo "── 7) 개인정보가 섞여 들어가지 않았는지 ──"
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
