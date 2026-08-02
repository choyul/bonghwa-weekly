#!/usr/bin/env python3
"""fetch_events.py — 봉화군 '주간행사계획' 첨부를 받아 날짜별 행사 목록(events.js)으로 만든다.

  사용: python3 build/fetch_events.py <출력파일> [가져올_개월수]
  예:   python3 build/fetch_events.py events.js 6

주간업무계획(fetch_latest.py)과 같은 게시물에 붙어 있는 '주간행사계획' 첨부를 쓴다.
최근 주는 pdf, 예전 주는 hwp 인데 kordoc 이 둘 다 같은 표(마크다운)로 바꿔 준다.

표 생김새 (한 줄이 하루):
  | 8. 03<br>(월) | 09:00 8월 정례회의<br>(군청 대회의실 180명)<br>… | 10:00 …<br>(… 6명) |
  2번째 칸 = 군 행사, 3번째 칸 = 읍면·기관단체·기타
이미 담아 둔 주는 다시 받지 않는다(증분).
"""
import subprocess, json, re, urllib.parse, os, sys, tempfile, shutil
from datetime import date, timedelta

BASE = 'https://www.bonghwa.go.kr'
MID = '0201020000'


def month_starts(n):
    """오늘부터 n개월 전까지의 '달 1일' 목록"""
    out, d = [], date.today().replace(day=1)
    for _ in range(n):
        out.append(d)
        d = (d - timedelta(days=1)).replace(day=1)
    return list(reversed(out))


def parse_table(md, week_start):
    """kordoc 이 만든 마크다운 표 → 행사 목록. 날짜는 주 시작일(월)에서 요일 순서로 센다."""
    events = []
    rows = [l for l in md.split('\n') if l.startswith('|')]
    body = [r for r in rows if not re.match(r'^\|\s*(구\s*분|---)', r)]
    for i, row in enumerate(body):
        cells = [c.strip() for c in row.strip().strip('|').split('|')]
        if len(cells) < 3:
            continue
        # 첫 칸이 '8. 03<br>(월)' 형태여야 하루짜리 줄이다
        m = re.match(r'^(\d{1,2})\.\s*(\d{1,2})', cells[0].replace('<br>', ' '))
        if not m:
            continue
        day = week_start + timedelta(days=len(events) and 0 or 0)  # 자리표시(아래에서 다시 계산)
        # 표의 월/일을 그대로 믿되, 주 시작일 기준 ±10일 안이어야 한다(연말연시 해 넘김 대비)
        mo, dy = int(m.group(1)), int(m.group(2))
        cand = None
        for yr in (week_start.year, week_start.year + 1, week_start.year - 1):
            try:
                c = date(yr, mo, dy)
            except ValueError:
                continue
            if abs((c - week_start).days) <= 10:
                cand = c
                break
        if not cand:
            continue
        day = cand
        for kind, cell in (('군', cells[1]), ('기관', cells[2])):
            cur = None
            for part in [p.strip() for p in cell.split('<br>') if p.strip()]:
                t = re.match(r'^(\d{1,2}:\d{2})\s*(.+)$', part)
                if t:
                    cur = {'date': day.isoformat(), 'time': t.group(1),
                           'title': t.group(2).strip(), 'place': '', 'people': '', 'kind': kind}
                    events.append(cur)
                    continue
                p = re.match(r'^\((.+)\)$', part)
                if p and cur:
                    inside = p.group(1).strip()
                    pm = re.search(r'([\d,]+)\s*명\s*$', inside)
                    if pm:
                        cur['people'] = pm.group(1).replace(',', '')
                        inside = inside[:pm.start()].rstrip(' ,').strip()
                    cur['place'] = inside
                elif cur and not t:
                    # 시간 없이 이어지는 줄은 제목에 붙인다
                    cur['title'] = (cur['title'] + ' ' + part).strip()
    return events


def main():
    if len(sys.argv) < 2:
        print('usage: fetch_events.py <out.js> [months]'); return 1
    out_path = sys.argv[1]
    months = int(sys.argv[2]) if len(sys.argv) > 2 else 6

    have = {}
    if os.path.exists(out_path):                      # 이미 받은 주는 건너뛴다
        try:
            txt = open(out_path, encoding='utf-8').read()
            j = json.loads(txt[txt.index('{'):txt.rindex('}') + 1])
            for it in j.get('items', []):
                have.setdefault(it.get('week'), []).append(it)
        except Exception:
            have = {}

    cj = tempfile.mktemp(suffix='.cookies')
    work = tempfile.mkdtemp(prefix='bwev')

    def curl(url, data=None, out=None, head=False):
        cmd = ['curl', '-s', '-b', cj, '-c', cj, url]
        if head:
            cmd = ['curl', '-sI', '-b', cj, '-c', cj, url]
        if data:
            cmd += ['--data', data]
        if out:
            cmd += ['-o', out, '-w', '%{http_code}']
        r = subprocess.run(cmd, capture_output=True)
        return r.stdout.decode('utf-8', 'replace')

    curl(f'{BASE}/portal/dytWrk/calendar.do?mid={MID}', out='/dev/null')

    posts = {}
    for ms in month_starts(months):
        raw = curl(f'{BASE}/portal/dytWrk/monthly/list/fetch.do', f'start={ms:%Y-%m-%d}&mid={MID}')
        for sday, idx in zip(re.findall(r'"COL_SDAY":"([^"]+)"', raw),
                             re.findall(r'"IDX":"?(\d+)"?', raw)):
            posts[sday] = idx

    items, fetched = [], 0
    for sday in sorted(posts):
        if sday in have:                               # 이미 있는 주는 그대로 재사용
            items += have[sday]
            continue
        idx = posts[sday]
        html = curl(f'{BASE}/portal/dytWrk/view.do?mid={MID}', f'idx={idx}&goTo={sday}')
        pairs = list(dict.fromkeys(re.findall(r"yhLib\.file\.download\('([^']+)','([^']*)'\)", html)))
        got = None
        for a, fsn in pairs:
            url = f'{BASE}/common/file/download.do?atchFileId={a}&fileSn={fsn}'
            hdr = curl(url, head=True)
            fm = re.search(r'filename="?([^"\r\n]+)"?', hdr)
            fn = urllib.parse.unquote(fm.group(1)).strip() if fm else ''
            if '주간행사계획' not in fn:
                continue
            ext = os.path.splitext(fn)[1] or '.hwp'
            dst = os.path.join(work, f'{sday}{ext}')
            if curl(url, out=dst).strip().endswith('200') and os.path.getsize(dst) > 0:
                got = dst
            break
        if not got:
            print(f'  {sday}: 주간행사계획 첨부 없음'); continue
        r = subprocess.run(['npx', '-y', 'kordoc', got, '-d', work, '--silent'],
                           capture_output=True)
        md_path = os.path.splitext(got)[0] + '.md'
        if r.returncode != 0 or not os.path.exists(md_path):
            print(f'  {sday}: 변환 실패'); continue
        md = open(md_path, encoding='utf-8').read()
        ev = parse_table(md, date.fromisoformat(sday))
        for e in ev:
            e['week'] = sday
        items += ev
        fetched += 1
        print(f'  {sday}: 행사 {len(ev)}건')

    shutil.rmtree(work, ignore_errors=True)
    items.sort(key=lambda e: (e['date'], e['time']))
    weeks = sorted({e['week'] for e in items})
    data = {'builtAt': (weeks[-1] if weeks else ''), 'weeks': weeks, 'items': items}
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('/* 자동 생성 파일 — build/fetch_events.py 로 재생성. 직접 수정 금지 */\n')
        f.write('window.BW_EVENTS=' + json.dumps(data, ensure_ascii=False) + ';\n')
    print(f'새로 받은 주 {fetched}개 · 행사 {len(items)}건 → {out_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
