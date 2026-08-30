#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_notice.py — 봉화군 홈페이지 '공지사항' 게시판 목록 수집 → build/cache/notice_posts.json

  사용: python3 build/fetch_notice.py [보관개월수=24]

왜 만들었나
  '오늘의 봉화'의 주간업무 항목 중에는 군 홈페이지 공지사항에 같은 내용이 올라와 있는 것이
  많다(신청 접수, 모집, 채용 등). 군민이 바로 원문·첨부를 볼 수 있게 그 글로 이어 주려면
  먼저 공지사항 목록을 갖고 있어야 한다. 이 파일은 '목록'만 모은다 —
  본문은 봉화군 공식 페이지에서 보게 하고, 여기서는 제목·부서·등록일만 쓴다.

  고시·공고(fetch_gosi.py)와 다른 게시판이다. 이쪽은 bcIdx=100 / mid=0201010000.

  이어받기(증분): 이미 받아 둔 캐시에 있는 글이 한 페이지 전부를 채우면 거기서 멈춘다.
  매일 도는 자동 갱신에서 120쪽을 다시 훑지 않기 위한 것.
"""
import sys, re, json, os, time, html
from datetime import date, timedelta
from urllib.request import Request, urlopen

BASE  = "https://www.bonghwa.go.kr/portal/board/post"
LIST  = BASE + "/list.do?bcIdx=100&mid=0201010000&page={page}"
VIEW  = BASE + "/view.do?bcIdx=100&mid=0201010000&idx={idx}"
UA    = "Mozilla/5.0 (compatible; BonghwaTodayBot/1.0)"

HERE  = os.path.dirname(os.path.abspath(__file__))
OUT   = os.path.join(HERE, "cache", "notice_posts.json")
MAX_PAGE = 400          # 안전장치 (10건/쪽)

months = int(sys.argv[1]) if len(sys.argv) > 1 else 24


def fetch(url):
    for _ in range(3):
        try:
            req = Request(url, headers={"User-Agent": UA})
            with urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            sys.stderr.write(f"  재시도({e})\n"); time.sleep(2)
    return ""


def clean(x):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x))).strip()


def parse_rows(t):
    """목록 표의 한 줄 = 글 하나. 제목 링크는 onclick 이라 data-req-get-p-idx 에서 글번호를 꺼낸다."""
    out = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
        m = re.search(r'data-req-get-p-idx="(\d+)"', r)
        if not m:
            continue
        def td(cls):
            g = re.search(r'<td class="' + cls + r'"[^>]*>(.*?)</td>', r, re.S)
            return clean(g.group(1)) if g else ""
        d = td("list_date")[:10]
        if not re.match(r"\d{4}-\d{2}-\d{2}", d):
            continue
        out.append({
            "idx":   m.group(1),
            "no":    td("list_num"),
            "title": td("list_tit"),
            "dept":  td("list_part"),
            "writer": td("list_write"),
            "date":  d,
        })
    return out


def main():
    cut = (date.today() - timedelta(days=31 * months)).isoformat()
    old = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                for x in json.load(f).get("items", []):
                    old[x["idx"]] = x
        except Exception as e:
            sys.stderr.write(f"캐시 읽기 실패 — 처음부터 받는다({e})\n")

    items, seen, added = dict(old), set(), 0
    for p in range(1, MAX_PAGE + 1):
        t = fetch(LIST.format(page=p))
        if not t:
            break
        rows = parse_rows(t)
        if not rows:
            break
        new = [x for x in rows if x["idx"] not in old]
        for x in rows:
            items[x["idx"]] = x
            seen.add(x["idx"])
        added += len(new)
        oldest = min(x["date"] for x in rows)
        if p % 10 == 0 or new:
            sys.stderr.write(f"page {p}: 새 글 {len(new)} (최소 등록일 {oldest})\n")
        if oldest < cut:
            break
        # 이 페이지가 통째로 이미 갖고 있는 글이면 그 아래도 다 갖고 있다 — 멈춘다.
        if old and not new:
            sys.stderr.write(f"page {p}: 모두 기존 글 — 이어받기 종료\n")
            break
        time.sleep(0.5)

    keep = sorted((x for x in items.values() if x["date"] >= cut),
                  key=lambda x: (x["date"], int(x["idx"])), reverse=True)
    data = {"builtAt": keep[0]["date"] if keep else date.today().isoformat(),
            "months": months,
            "viewBase": BASE + "/view.do?bcIdx=100&mid=0201010000&idx=",
            "items": keep}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)
    print(f"공지사항 캐시: {OUT} / {len(keep)}건 (새로 받은 글 {added}건) / "
          f"{keep[-1]['date'] if keep else '-'} ~ {keep[0]['date'] if keep else '-'}")


if __name__ == "__main__":
    main()
