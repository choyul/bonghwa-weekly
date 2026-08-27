#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_news.py — 봉화 관련 뉴스 수집 → news.js 생성
  사용: python3 build/fetch_news.py [출력경로=news.js] [보관일수=30]

═══ 수집원 두 갈래 — 열쇠가 없어도 돌아간다 ═══
  (가) 언론사 공식 RSS  … 열쇠·가입 **불필요**. 늘 켜져 있다.
  (나) 네이버 뉴스 검색 API … 열쇠가 있을 때만. 커버리지가 훨씬 넓다.
  둘 다 켜지면 합쳐서 중복을 지운다. (가)만으로도 화면은 채워진다.

  ※ RSS 는 '최근 N건'만 주기 때문에 **자주 받아야 놓치지 않는다.**
    실측(2026-08-27) — 피드 한 번에 담기는 시간 폭 / 그때 잡힌 봉화 기사:
      매일신문 1000건=168시간(7일)/9건 ← 가장 값지다 · 씨원뉴스 50건=25시간/6건
      이로운넷 50건=21시간/2건 · 경북도민일보 50건=18시간/1건 · 대경일보 50건=21시간/1건
      연합뉴스 지역 120건=3.3시간 · 뉴시스 속보 100건=1.7시간
      경북일보 50건=20시간 · 대구일보 50건=46시간 · 한국농어민신문 50건=40시간
      안동데일리 50건=0.7시간(전재 덤프라 사실상 못 따라감 — 넣되 기대하지 말 것)
    그래서 `.github/workflows/news.yml` 이 **2시간마다** 이 스크립트를 돌린다.
    아래 merge_previous 가 지난 news.js 와 합치므로 조금씩 쌓여 30일치가 된다.
    수집 주기를 늘리면(예: 하루 1회) 연합뉴스·뉴시스 기사를 대부분 놓친다.

═══ 네이버 열쇠를 쓸 경우 — '네이버 클라우드'에서 받는다 (개발자센터 아님) ═══
  네이버가 검색 API 를 개발자센터(developers.naver.com)에서
  **네이버 클라우드의 NAVER API HUB** 로 옮겼다. 그래서 개발자센터의
  '애플리케이션 등록 → 사용 API' 목록에는 **'검색'이 아예 없다.**
  신규 신청은 네이버 클라우드 플랫폼(ncloud.com) 계정으로 해야 한다.
    콘솔 → Services → NAVER API HUB → 이용 신청 → Application 등록
    → 사용할 API 에서 '검색' 선택 → 인증정보에서 Client ID / Client Secret 확인
  한도: NAVER 검색 월 775,000건, API Key 당 50 RPS (우리는 하루 수십 건이라 남아돈다).
  요금: 한시적 무료. **유료 전환 시 사전 공지 예정** — 공지가 뜨면 이 화면을 계속 둘지 다시 판단할 것.

  옛 개발자센터 열쇠(2026-07-30 이전 신청분)를 아직 가지고 있다면
  2027-06-30 까지는 그것도 쓸 수 있다. 그 경우에만 NAVER_API_LEGACY=1 로 실행한다.

═══ 저작권 때문에 반드시 지켜야 할 것 (고치기 전에 읽을 것) ═══
  이 파일이 담는 것은 **제목·언론사·날짜·원문주소** 네 가지뿐이다.
  네이버 API 가 함께 주는 `description`(기사 앞부분 = 리드문)은 **일부러 버린다.**
  리드문을 그대로 실으면 복제권·2차적저작물작성권 침해 소지가 생긴다.
  "요약이라도 넣어 달라"는 요청이 와도 넣지 말 것 — 요약도 침해가 될 수 있다.

  · 링크는 `originallink`(언론사 원문)를 우선 쓴다. 네이버 안쪽 페이지로 보내면
    언론사가 받아야 할 방문을 가로채는 모양이 된다.
  · 언론사 사이트를 직접 긁지 않는다. 대량 스크래핑은 저작권과 별개로
    부정경쟁방지법(성과 무단사용)·데이터베이스제작자의 권리에 걸린다.
  · 구글 뉴스 RSS 는 쓰지 않는다. 피드 자체에 "개인용 피드 리더에서
    개인적·비상업적 용도로만" 쓰라고 명시돼 있어 공개 사이트 게시는 약관 위반이다.

순수 표준 라이브러리만 사용(설치 불필요). GitHub Actions에서 매일 실행.
"""
import sys, os, re, json, time, html, hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from email.utils import parsedate_to_datetime

KST = timezone(timedelta(hours=9))
# RSS 를 주는 언론사 서버 중에는 낯선 UA 를 막는 곳이 있어 평범한 브라우저로 소개한다.
UA_BROWSER = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# 기본은 NAVER API HUB(네이버 클라우드). 파라미터·응답 필드는 옛 개발자센터와 같고
# 주소와 인증 헤더 이름만 다르다.
LEGACY = os.environ.get("NAVER_API_LEGACY", "").strip() not in ("", "0", "false")
if LEGACY:
    API  = "https://openapi.naver.com/v1/search/news.json?query={q}&display=100&start={start}&sort=date"
    HDR  = ("X-Naver-Client-Id", "X-Naver-Client-Secret")
    WHERE = "개발자센터(옛 방식)"
else:
    API  = "https://naverapihub.apigw.ntruss.com/search/v1/news?query={q}&display=100&start={start}&sort=date"
    HDR  = ("X-NCP-APIGW-API-KEY-ID", "X-NCP-APIGW-API-KEY")
    WHERE = "NAVER API HUB"

out_path = sys.argv[1] if len(sys.argv) > 1 else "news.js"
days     = int(sys.argv[2]) if len(sys.argv) > 2 else 30

CID = os.environ.get("NAVER_CLIENT_ID", "").strip()
CSE = os.environ.get("NAVER_CLIENT_SECRET", "").strip()

# 검색어 — '봉화'만 쓰면 봉화산·봉화대 같은 엉뚱한 기사가 쏟아진다.
# 지역이 확정되는 말을 앞에 붙여 정확도를 올리고, 아래 NEG 로 한 번 더 거른다.
QUERIES = ["봉화군", "경북 봉화", "봉화읍", "봉화 청량산", "봉화 분천"]

# 언론사가 스스로 열어 둔 공식 RSS. 발행사가 '가져가 읽으라'고 내놓은 것이라
# 긁는 것(스크래핑)과 성격이 다르다 — 여기 없는 주소를 함부로 늘리지 말 것.
# 통합 피드라 봉화 기사는 드물게 섞여 나온다. 아래 POS/NEG 로 걸러 쓴다.
# 어느 매체가 실제로 봉화를 다루는지 조사해서 고른 목록이다(2026-08-27 실측).
# 앞의 넷이 주력 — 나머지는 가끔 걸리는 보조.
# (언론사 이름, RSS 주소) — 이름은 상세 안내(news-about.html)에 그대로 실린다.
# 여기만 고치면 안내 페이지의 '지금 받고 있는 곳' 목록도 함께 바뀐다(news.js 에 실어 보낸다).
RSS_SOURCES = (
    ("매일신문",     "https://www.imaeil.com/rss"),                     # 1000건=7일치, 봉화 기사가 가장 많다
    ("씨원뉴스",     "https://www.c1news.kr/rss/allArticle.xml"),       # 지역 밀착, 봉화 밀도 최고
    ("경북도민일보", "https://www.hidomin.com/rss/allArticle.xml"),
    ("대경일보",     "https://www.dkilbo.com/rss/allArticle.xml"),
    ("이로운넷",     "https://www.eroun.net/rss/allArticle.xml"),
    ("연합뉴스",     "https://www.yna.co.kr/rss/local.xml"),
    ("뉴시스",       "https://www.newsis.com/RSS/sokbo.xml"),
    ("경북일보",     "https://www.kyongbuk.co.kr/rss/allArticle.xml"),
    ("대구일보",     "https://www.idaegu.com/rss/allArticle.xml"),
    ("안동데일리",   "https://www.andongdaily.com/rss/allArticle.xml"),
    ("한국농어민신문","https://www.agrinet.co.kr/rss/allArticle.xml"),
)
RSS_FEEDS = tuple(u for _, u in RSS_SOURCES)
# 봉화를 가장 많이 다루는 곳은 경북신문(kbsm.net)이지만 RSS 를 열어 두지 않았다.
# 긁는 것은 하지 않기로 했으므로(부정경쟁방지법) 빠져 있다 — 넣지 말 것.

# 제목에 이 말이 있으면 봉화군 기사가 아니다 (봉홧불·다른 지역 봉화산 등)
NEG = re.compile(
    r"봉화산|봉화대|봉홧불|봉화불|봉화를\s*(올|들)|봉화가\s*(올|타)|봉화\s*올리|"
    r"봉화산역|남원\s*봉화|장수\s*봉화|서울\s*봉화"
)
# 제목이 이 조건을 못 넘으면 버린다 — 최소한 '봉화'라는 말은 있어야 한다
POS = re.compile(r"봉화")

# 원문주소 도메인 → 언론사 이름. 없으면 도메인을 그대로 보여 준다.
PRESS = {
    "yna.co.kr": "연합뉴스", "yonhapnews.co.kr": "연합뉴스", "news1.kr": "뉴스1",
    "newsis.com": "뉴시스", "kyongbuk.co.kr": "경북일보", "kbmaeil.com": "경북매일",
    "imaeil.com": "매일신문", "yeongnam.com": "영남일보", "idaegu.com": "대구일보",
    "andongdaily.com": "안동데일리", "hkbs.co.kr": "환경일보",
    "dnews.co.kr": "대한경제", "kmaeil.com": "경기매일",
    "chosun.com": "조선일보", "donga.com": "동아일보", "joongang.co.kr": "중앙일보",
    "hani.co.kr": "한겨레", "khan.co.kr": "경향신문", "seoul.co.kr": "서울신문",
    "hankookilbo.com": "한국일보", "segye.com": "세계일보", "munhwa.com": "문화일보",
    "kmib.co.kr": "국민일보", "hankyung.com": "한국경제", "mk.co.kr": "매일경제",
    "sedaily.com": "서울경제", "fnnews.com": "파이낸셜뉴스", "edaily.co.kr": "이데일리",
    "mt.co.kr": "머니투데이", "asiae.co.kr": "아시아경제", "heraldcorp.com": "헤럴드경제",
    "ajunews.com": "아주경제", "etoday.co.kr": "이투데이", "newdaily.co.kr": "뉴데일리",
    "nocutnews.co.kr": "노컷뉴스", "ohmynews.com": "오마이뉴스", "pressian.com": "프레시안",
    "kbs.co.kr": "KBS", "imbc.com": "MBC", "sbs.co.kr": "SBS", "ytn.co.kr": "YTN",
    "jtbc.co.kr": "JTBC", "mbn.co.kr": "MBN", "tbc.co.kr": "TBC",
    "andongmbc.co.kr": "안동MBC", "dgmbc.com": "대구MBC",
    "agrinet.co.kr": "한국농어민신문", "nongmin.com": "농민신문",
    "c1news.kr": "씨원뉴스", "hidomin.com": "경북도민일보", "dkilbo.com": "대경일보",
    "eroun.net": "이로운넷", "gukjenews.com": "국제뉴스", "newscj.com": "천지일보",
    "kbsm.net": "경북신문", "newsgb.co.kr": "뉴스경북", "gyeongsangtoday.com": "경상투데이",
    "kwnews.co.kr": "강원일보", "newspim.com": "뉴스핌", "wowtv.co.kr": "한국경제TV",
    "gov.kr": "정책브리핑", "korea.kr": "정책브리핑",
}


def notice_keys():
    """열쇠가 없어도 RSS 로 돌아간다 — 막지 않고 안내만 한다."""
    if CID and CSE:
        return
    sys.stderr.write(
        "\n[안내] 네이버 API 열쇠가 없어 언론사 공식 RSS 로만 모읍니다.\n"
        "        그대로 두셔도 화면은 채워집니다. 더 많은 기사를 담고 싶으시면:\n"
        "  ※ 개발자센터(developers.naver.com)가 아닙니다 — 검색 API 는 네이버 클라우드로 옮겨졌습니다.\n"
        "  1) https://www.ncloud.com 가입·로그인 → 콘솔 → Services → NAVER API HUB\n"
        "  2) 이용 신청 → Application 등록 → 사용할 API 에서 '검색' 선택\n"
        "  3) 인증정보의 Client ID / Client Secret 을 환경변수로 넣고 다시 실행:\n"
        "       export NAVER_CLIENT_ID=...\n"
        "       export NAVER_CLIENT_SECRET=...\n"
        "     (GitHub Actions 에서는 저장소 Settings → Secrets 에 같은 이름으로 등록)\n"
        "  · 옛 개발자센터 열쇠를 이미 갖고 계시면 NAVER_API_LEGACY=1 을 함께 넣으세요(2027-06-30 까지).\n\n"
    )


def fetch(url):
    req = Request(url, headers={
        HDR[0]: CID,
        HDR[1]: CSE,
        "User-Agent": "BonghwaTodayBot/1.0",
    })
    for attempt in range(3):
        try:
            with urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:200]
            if e.code in (401, 403):
                sys.stderr.write(
                    f"  열쇠가 거부됐습니다({e.code}, {WHERE} 방식으로 불렀음): {body}\n"
                    "  · 네이버 클라우드(NAVER API HUB) 열쇠라면 그대로 두고,\n"
                    "    옛 개발자센터 열쇠라면 NAVER_API_LEGACY=1 을 넣고 다시 실행해 보세요.\n")
                return None                      # 재시도해도 소용없다
            sys.stderr.write(f"  재시도({e.code} {body})\n")
        except Exception as e:
            sys.stderr.write(f"  재시도({e})\n")
        time.sleep(1.5 * (attempt + 1))
    return None


def clean_title(x):
    """네이버가 검색어에 <b> 를 씌워 보내므로 태그를 걷어내고 엔티티를 되돌린다."""
    x = re.sub(r"<[^>]+>", "", x)
    x = html.unescape(x)
    return re.sub(r"\s+", " ", x).strip()


def press_of(url):
    host = (urlparse(url).hostname or "").lower()
    host = re.sub(r"^(www|m|news|view|biz|post|mnews|amp)\.", "", host)
    for dom, name in PRESS.items():
        if host == dom or host.endswith("." + dom):
            return name
    return host or "언론사"


def norm_url(url):
    """같은 기사가 m./www. 나 쿼리만 달리해 두 번 들어오는 것을 막는다."""
    p = urlparse(url)
    host = re.sub(r"^(www|m|mnews|amp)\.", "", (p.hostname or "").lower())
    return host + p.path.rstrip("/")


def title_key(t):
    """제목이 같으면(기호·공백 무시) 같은 기사로 본다 — 전재 기사 중복 제거."""
    return re.sub(r"[^가-힣a-z0-9]", "", t.lower())


class Bag:
    """모은 기사를 담는 그릇. 주소가 같거나 제목이 같으면 같은 기사로 보고 한 번만 담는다."""

    def __init__(self, cutoff):
        self.cutoff, self.by_url, self.by_title, self.dropped = cutoff, {}, {}, 0

    def add(self, title, url, dt):
        """담았으면 True. 봉화 기사가 아니거나 오래됐거나 이미 있으면 False.

        같은 기사가 여러 곳에 실렸을 때는 **먼저 보도한 곳**을 남긴다.
        예전에는 '먼저 훑은 곳'이 이겼는데, 그러면 RSS_FEEDS 배열 첫 줄에 있는
        매체가 언제나 이긴다 — 우리가 만든 편향이라 고쳤다.
        수집 순서를 바꿔도 결과가 같아야 한다(그래야 언론사에 떳떳하다).
        """
        if not title or not url.startswith("http") or dt is None:
            return False
        if dt < self.cutoff:
            return False
        if not POS.search(title) or NEG.search(title):
            self.dropped += 1
            return False
        nu, tk = norm_url(url), title_key(title)
        old = self.by_url.get(nu) or self.by_title.get(tk)
        if old is not None:
            if int(dt.timestamp()) >= old["ts"]:
                return False                      # 이미 있는 쪽이 더 먼저 보도했다
            # 새로 온 것이 더 먼저 보도한 기사 → 옛것을 걷어내고 갈아 끼운다
            self.by_url = {k: v for k, v in self.by_url.items() if v is not old}
            self.by_title = {k: v for k, v in self.by_title.items() if v is not old}
        rec = {
            "id": hashlib.sha1(nu.encode("utf-8")).hexdigest()[:12],
            "t": title,
            "u": url,
            "p": press_of(url),
            "d": dt.strftime("%Y-%m-%d"),
            "ts": int(dt.timestamp()),
        }
        self.by_url[nu] = rec
        self.by_title[tk] = rec
        return True

    def rows(self):
        return sorted(self.by_url.values(), key=lambda r: -r["ts"])


def any_date(s):
    """언론사마다 pubDate 적는 법이 달라서(RFC822 · '2026-08-27 13:30:39' 등) 다 받아 준다."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
        return d.astimezone(KST) if d.tzinfo else d.replace(tzinfo=KST)
    except Exception:
        pass
    for f in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y.%m.%d %H:%M"):
        try:
            return datetime.strptime(s, f).replace(tzinfo=KST)
        except ValueError:
            pass
    return None


def fetch_text(url):
    req = Request(url, headers={"User-Agent": UA_BROWSER})
    for attempt in range(2):
        try:
            with urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            sys.stderr.write(f"    재시도({e})\n")
            time.sleep(1.0 * (attempt + 1))
    return ""


def untag(x):
    """<![CDATA[...]]> 와 엔티티를 벗겨 알맹이만."""
    x = re.sub(r"^\s*<!\[CDATA\[|\]\]>\s*$", "", x.strip())
    return re.sub(r"\s+", " ", html.unescape(x)).strip()


def collect_rss(bag):
    """언론사 공식 RSS 에서 봉화 기사만 골라 담는다. 열쇠가 필요 없는 길.
       ※ RSS 의 <description> 에는 기사 앞부분이 통째로 들어 있다 — 읽지도 담지도 않는다(저작권)."""
    got = 0
    for feed in RSS_FEEDS:
        t = fetch_text(feed)
        if not t:
            continue
        n = 0
        for block in re.findall(r"<item[^>]*>(.*?)</item>", t, re.S | re.I):
            m_t = re.search(r"<title[^>]*>(.*?)</title>", block, re.S | re.I)
            m_l = re.search(r"<link[^>]*>(.*?)</link>", block, re.S | re.I)
            m_d = re.search(r"<pubDate[^>]*>(.*?)</pubDate>", block, re.S | re.I)
            if not (m_t and m_l):
                continue
            if bag.add(untag(m_t.group(1)), untag(m_l.group(1)), any_date(untag(m_d.group(1)) if m_d else "")):
                n += 1
        got += n
        sys.stderr.write(f"    {feed.split('/')[2]:22s} 봉화 {n}건\n")
        time.sleep(0.3)                            # 언론사 서버에 예의
    return got


def collect_naver(bag):
    """네이버 뉴스 검색 API. 열쇠가 있을 때만 부른다."""
    got = 0
    for q in QUERIES:
        for start in (1, 101):                    # 검색어당 최대 200건
            data = fetch(API.format(q=quote(q), start=start))
            if not data:
                return got                        # 열쇠가 거부됐으면 더 두드리지 않는다
            items = data.get("items", [])
            if not items:
                break
            oldest = None
            for it in items:
                # 링크: 언론사 원문 우선, 없을 때만 네이버 쪽
                url = (it.get("originallink") or "").strip() or (it.get("link") or "").strip()
                dt = any_date(it.get("pubDate", ""))
                if dt:
                    oldest = dt if oldest is None else min(oldest, dt)
                if bag.add(clean_title(it.get("title", "")), url, dt):
                    got += 1
            # 이 페이지가 통째로 보관기간보다 오래됐으면 다음 페이지는 볼 필요 없다
            if oldest and oldest < bag.cutoff:
                break
            time.sleep(0.2)                       # 네이버에 예의
    return got


def collect():
    bag = Bag(datetime.now(KST) - timedelta(days=days))

    sys.stderr.write("  언론사 공식 RSS …\n")
    n_rss = collect_rss(bag)

    n_api = 0
    if CID and CSE:
        sys.stderr.write(f"  네이버 뉴스 검색 API ({WHERE}) …\n")
        n_api = collect_naver(bag)
    else:
        sys.stderr.write("  네이버 API 는 건너뜀 (열쇠 없음 — RSS 만으로 모읍니다)\n")

    rows = bag.rows()
    sys.stderr.write(
        f"  모은 기사 {len(rows)}건 (RSS {n_rss} + 네이버 {n_api}, "
        f"봉화군 기사가 아니라 버린 것 {bag.dropped}건)\n")
    return rows


# ── 같은 사안을 여러 곳이 쓴 기사 걷어내기 ───────────────────────────────
# 제목이 글자까지 똑같지는 않지만 같은 보도자료를 받아쓴 기사가 자주 들어온다.
#   예) "'봉화 농산물 새 이름 찾는다'… 봉화군, 공동브랜드 네이밍 공모 추진"  (매일신문)
#       "봉화군, 농산물 공동브랜드 네이밍 공모전 접수 연장"                  (대경일보)
# 한글은 조사가 붙어 낱말 단위 비교가 잘 안 맞으므로 **글자 두 개씩(bigram)** 겹침을 본다.
# '봉화'·'봉화군'은 거의 모든 제목에 있어 닮음을 부풀리므로 빼고 센다.
#
# 실측(2026-08-27, 같은 날짜 쌍 전부): 진짜 중복 0.65 / 0.53, 그다음 남남이 0.05.
# 사이가 크게 벌어져 있어 0.35 를 threshold 로 둔다. 올리면 중복이 새고, 내리면 남남을 묶는다.
# **판단은 같은 날짜끼리만** 한다 — 날짜가 다르면 후속 보도일 수 있어 함부로 지우면 안 된다.
SIMILAR = 0.35


def title_bigrams(t):
    x = re.sub(r"[^가-힣a-z0-9]", "", t.lower())
    x = x.replace("봉화군", "").replace("봉화", "")
    return {x[i:i + 2] for i in range(len(x) - 1)}


def collapse_similar(rows):
    """같은 사안이면 **먼저 보도한 기사 하나만** 남긴다."""
    kept = []                                  # [(기사, 글자쌍)]
    dropped = 0
    # 먼저 보도된 것부터 훑으므로, 묶음에서 처음 담기는 것이 곧 가장 이른 기사다
    for r in sorted(rows, key=lambda x: x.get("ts", 0)):
        b = title_bigrams(r["t"])
        dup = False
        if b:
            for k, kb in kept:
                if k["d"] != r["d"] or not kb:
                    continue
                if len(b & kb) / min(len(b), len(kb)) >= SIMILAR:
                    dup = True
                    sys.stderr.write(f"    같은 사안으로 묶음: {r['t'][:34]} … ← {k['t'][:34]}\n")
                    break
        if not dup:
            kept.append((r, b))
        else:
            dropped += 1
    if dropped:
        sys.stderr.write(f"  같은 사안 중복 {dropped}건을 걷어냈습니다(먼저 보도한 기사만 남김)\n")
    return sorted((k for k, _ in kept), key=lambda r: -r.get("ts", 0))


def merge_previous(rows, path):
    """이번에 못 받은 옛 기사를 잃지 않도록 지난 news.js 와 합친다.
       네이버 검색은 뒤로 갈수록 결과가 흔들려서, 이게 없으면
       '지난 1주일' 목록이 날마다 들쭉날쭉해진다."""
    if not os.path.exists(path):
        return rows
    try:
        txt = open(path, encoding="utf-8").read()
        old = json.loads(txt[txt.index("{"):txt.rindex("}") + 1]).get("items", [])
    except Exception:
        return rows
    cutoff = int((datetime.now(KST) - timedelta(days=days)).timestamp())
    seen = {r["id"] for r in rows}
    kept = [r for r in old if r.get("id") not in seen and r.get("ts", 0) >= cutoff]
    if kept:
        sys.stderr.write(f"  지난 목록에서 이어받은 기사 {len(kept)}건\n")
    return sorted(rows + kept, key=lambda r: -r.get("ts", 0))


def main():
    notice_keys()
    sys.stderr.write("봉화 뉴스 수집 중…\n")
    rows = collect()
    if not rows and os.path.exists(out_path):
        sys.stderr.write("  받은 것이 없어 기존 news.js 를 그대로 둡니다\n")
        return 1
    rows = merge_previous(rows, out_path)
    rows = collapse_similar(rows)          # 같은 사안은 먼저 보도한 것만

    payload = {
        # builtAt 은 날짜까지만 — 시각까지 넣으면 내용이 같아도 날마다 커밋된다
        "builtAt": datetime.now(KST).strftime("%Y-%m-%d"),
        "days": days,
        "source": ("언론사 공식 RSS + 네이버 뉴스 검색" if (CID and CSE) else "언론사 공식 RSS"),
        # 상세 안내(news-about.html)가 이 둘을 읽어 '지금 받고 있는 곳'을 그린다.
        # 손으로 두 군데 적으면 반드시 어긋나므로 여기 한 곳에서만 나가게 한다.
        "everyHours": 2,
        "feeds": [{"p": name, "u": url} for name, url in RSS_SOURCES],
        "naver": bool(CID and CSE),
        "items": rows,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("/* 자동 생성 — build/fetch_news.py. 직접 수정 금지 */\n")
        f.write("/* 제목·언론사·날짜·원문주소만 담는다. 기사 본문·요약은 담지 않는다(저작권). */\n")
        f.write("window.BW_NEWS=" + body + ";\n")
    sys.stderr.write(f"  {out_path} 에 {len(rows)}건 저장\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
