#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_gosi.py — 봉화군 고시/공고 게시판 최근분 수집 → notices.js 생성
  사용: python3 build/fetch_gosi.py [출력경로=notices.js] [보관개월수=3]

- 목록에서 얻는 것만 담는다: 구분(고시/공고)·번호·제목·담당부서·등록일·상세ID
  (본문/첨부는 파싱하지 않고, 앱에서 봉화군 공식 상세 페이지로 링크 아웃)
- 등록일 기준 최근 N개월만. 그보다 오래된 페이지가 나오면 멈춘다.
- 순수 표준 라이브러리만 사용(설치 불필요). GitHub Actions에서 매일 실행.
"""
import sys, re, json, time, html
from datetime import date, timedelta
from urllib.request import Request, urlopen

BASE = "https://www.bonghwa.go.kr/portal/saeol/gosi"
LIST = BASE + "/list.do?seCode=01&mid=0201030000&page={page}"
VIEW = BASE + "/view.do?notAncmtMgtNo={id}&mid=0201030000"
UA = "Mozilla/5.0 (compatible; BonghwaTodayBot/1.0)"

out_path = sys.argv[1] if len(sys.argv) > 1 else "notices.js"
months   = int(sys.argv[2]) if len(sys.argv) > 2 else 3
MAX_PAGE = 40  # 안전장치

def cutoff_str():
    t = date.today()
    # N개월 전 (달 단위로 대충 30일*N — 넉넉히)
    c = t - timedelta(days=31 * months)
    return c.isoformat()

def fetch(url):
    for _ in range(2):
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=25) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            sys.stderr.write(f"  재시도({e})\n"); time.sleep(1.5)
    return ""

def clean(x):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x)).strip()

def parse_rows(t):
    out = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
        if "view.do" not in r:
            continue
        tds = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
        if len(tds) < 5:
            continue
        num   = html.unescape(clean(tds[1]))
        title = html.unescape(clean(tds[2]))
        dept  = html.unescape(clean(tds[3]))
        d     = clean(tds[4])
        m = re.search(r"notAncmtMgtNo=(\d+)", r)
        if not (m and re.match(r"\d{4}-\d{2}-\d{2}", d)):
            continue
        kind = "고시" if "고시" in num else ("공고" if "공고" in num else "공고")
        out.append({"id": m.group(1), "num": num, "title": title,
                    "dept": dept, "date": d, "kind": kind})
    return out

def main():
    cut = cutoff_str()
    items, seen = [], set()
    for p in range(1, MAX_PAGE + 1):
        t = fetch(LIST.format(page=p))
        if not t:
            break
        rows = parse_rows(t)
        if not rows:
            break
        fresh = [x for x in rows if x["date"] >= cut and x["id"] not in seen]
        for x in fresh:
            seen.add(x["id"]); items.append(x)
        oldest = min(x["date"] for x in rows)
        sys.stderr.write(f"page {p}: +{len(fresh)} (최소 등록일 {oldest})\n")
        if oldest < cut:  # 이 페이지에 컷오프보다 오래된 게 나오면 종료
            break
        time.sleep(0.8)
    items.sort(key=lambda x: (x["date"], x["id"]), reverse=True)
    latest = items[0]["date"] if items else date.today().isoformat()
    data = {"builtAt": latest, "viewBase": BASE + "/view.do",
            "months": months, "items": items}
    js = ("/* 자동 생성 — build/fetch_gosi.py. 직접 수정 금지 */\n"
          "window.BW_NOTICES=" + json.dumps(data, ensure_ascii=False) + ";")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(js)
    kb = round(len(js.encode("utf-8")) / 1024)
    print(f"notices.js 생성: {out_path} / {len(items)}건 / 최신 {latest} / {kb}KB")

if __name__ == "__main__":
    main()
