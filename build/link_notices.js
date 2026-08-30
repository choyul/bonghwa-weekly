/* ═══════════════════════════════════════════════════════════════
   link_notices.js — 주간업무 항목 ↔ 봉화군 홈페이지 '공지사항' 글 잇기

   사용: node build/link_notices.js [data.js] [build/cache/notice_posts.json] [출력=notice_links.js]

   왜 만들었나
     '오늘의 봉화'에 실리는 소식 중 상당수는 군 홈페이지 공지사항에 원문과 첨부가 있다.
     군민이 그 글을 다시 찾아 헤매지 않게 바로가기를 달아 준다.
     다만 **틀린 글로 이어지면 안 하느니만 못하다.** 그래서 네 관문을 다 지난 짝만 남긴다.

       ① 주관부서   같은 과여야 한다. 조직개편으로 이름이 바뀐 과는 별칭표로 잇는다.
                    (공지사항 게시판은 옛 글에도 '지금' 부서명을 보여 준다)
       ② 등록일     그 주차 언저리(앞 60일 ~ 뒤 45일)여야 한다.
       ③ 연도·회차·월  한쪽에 있는데 서로 어긋나면 그 자리에서 버린다.
                    '2026년 …사업 신청'과 '2027년 …사업 신청'은 글자로는 거의 같지만 다른 글이다.
       ④ 핵심어     제목에서 행정 상투어(신청·접수·안내·모집…)를 걷어낸 뒤,
                    **한쪽에만 있는 낱말이 하나라도 있으면 버린다.**
                    이 관문이 '고추재배 ↔ 양채류재배', '벼 ↔ 감자', '일반 ↔ 장애인' 처럼
                    글자는 거의 같은데 알맹이가 다른 짝을 걸러 낸다(→ build/notice_words.js).

     ③④ 를 지난 것에만 글자 2-gram 유사도(흔한 조각은 값을 낮춘 가중 다이스)를 매겨
     높은 순으로 최대 세 개까지 남긴다.

   결과: notice_links.js → window.BW_NLINKS = {base, map:{ "부서|제목키": [{i,t,d}] }}
   ═══════════════════════════════════════════════════════════════ */
'use strict';
const fs = require('fs'), path = require('path');
const BW = require('../core.js');
const { norm, conflicts } = require('./notice_words.js');

const dataPath  = process.argv[2] || path.join(__dirname, '..', 'data.js');
const cachePath = process.argv[3] || path.join(__dirname, 'cache', 'notice_posts.json');
const outPath   = process.argv[4] || path.join(__dirname, '..', 'notice_links.js');

/* ── 조직개편으로 이름이 바뀐 과 ──
   주간계획은 그때그때의 이름을, 공지사항 게시판은 지금의 이름을 보여 준다.
   2025-01-06 개편 전 다섯 주치가 여기에 걸린다. 한 과가 둘로 나뉜 경우는 양쪽 다 허용.
   농업기술센터·보건소 이름으로 올라온 글은 실제로는 산하 과의 일이다. */
const DEPT_ALIAS = {
  '기획감사실': ['기획예산실'],
  '인구전략과': ['미래전략과'],
  '가족청소년과': ['교육가족과'],
  '안전건설과': ['안전재난과', '건설교통과'],
  '도시교통과': ['도시계획과', '건설교통과'],
  '보건정책과': ['보건소'],
  '건강관리과': ['보건소'],
  '농정축산과': ['농업기술센터'],
  '농촌활력과': ['농업기술센터'],
  '유통특작과': ['농업기술센터'],
  '농업기술과': ['농업기술센터'],
};
const deptSet = d => new Set([d].concat(DEPT_ALIAS[d] || []));

/* ── 기준값 ── 표본을 손으로 확인하며 맞췄다. 낮추면 틀린 짝이 붙는다. */
const CFG = {
  backDays: 60,      /* 공지가 주차 시작보다 이만큼 앞서 올라온 것까지 본다 */
  fwdDays: 45,       /* 주차 시작 뒤 이만큼 늦게 올라온 것까지 본다 */
  minScore: 0.45,    /* 가중 2-gram 다이스 하한 (④ 관문이 이미 거른 뒤라 낮아도 된다) */
  minShared: 4,      /* 겹치는 2-gram 개수 하한 */
  maxPerItem: 3,
};

function bigrams(s) {
  const out = new Set();
  for (let i = 0; i + 1 < s.length; i++) out.add(s.slice(i, i + 2));
  if (s.length === 1) out.add(s);
  return out;
}
const years = s => new Set(String(s).match(/(?:19|20)\d{2}/g) || []);
const months = s => new Set((String(s).match(/(?<!\d)(1[0-2]|[1-9])\s*월(?![세일간])/g) || [])
  .map(x => x.replace(/\s/g, '')));
/* 회차 — '제12회'·'2차'·'16기'. '2회차'는 '2차'로 본다.
   단위(회/차/기)가 서로 다르면 견주지 않는다 — '2회차 운영'과 '(1박2일, 4회)'는 다른 셈법이다. */
function rounds(s) {
  const o = new Set();
  for (const m of String(s).matchAll(/제?\s*(\d+)\s*(회차|차|회|기)(?![가-힣])/g))
    o.add((m[2] === '회차' ? '차' : m[2]) + m[1]);
  return o;
}
/* 같은 갈래(연도끼리·월끼리·'차'끼리)에서 값이 서로 어긋나면 다른 글이다 */
const clash = (a, b) => {
  if (!a.size || !b.size) return false;
  const unit = x => x.replace(/\d+/g, '');
  const units = new Set([...a].map(unit).filter(u => [...b].some(y => unit(y) === u)));
  for (const u of units) {
    const A = [...a].filter(x => unit(x) === u), B = [...b].filter(x => unit(x) === u);
    if (!A.some(x => B.includes(x))) return true;
  }
  return false;
};
const dayNo = s => Math.round(new Date(s + 'T00:00:00').getTime() / 864e5);

/* ── 자료 읽기 ── */
global.window = {};
require(path.resolve(dataPath));
const D = global.window.BW_DATA;
const cache = JSON.parse(fs.readFileSync(cachePath, 'utf-8'));

/* 같은 글이 두 부서 이름으로 두 번 올라온 경우가 있다(예: 유통특작과 / 농업기술센터).
   군민에게 같은 제목을 두 줄로 보여 줄 이유가 없으므로 제목+등록일로 하나만 남긴다. */
const seenTitle = new Map();
const posts = [];
for (const p of cache.items) {
  const n = norm(p.title);
  if (n.length < 4) continue;
  const k = n + '@' + p.date;
  if (seenTitle.has(k)) { seenTitle.get(k).depts.push(p.dept); continue; }
  const rec = { ...p, _n: n, _y: years(p.title), _m: months(p.title), _r: rounds(p.title), depts: [p.dept] };
  seenTitle.set(k, rec); posts.push(rec);
}

/* idf — 흔한 조각('사업'·'안내'·'봉화군'·'2026')은 겹쳐도 근거가 못 된다 */
const docs = posts.map(p => p._n).concat(D.occ.map(o => norm(o.item.title)));
const df = new Map();
for (const d of docs) for (const g of bigrams(d)) df.set(g, (df.get(g) || 0) + 1);
const N = docs.length;
const idf = g => Math.log(N / (1 + (df.get(g) || 0)));

function dice(A, B) {
  let inter = 0, wa = 0, wb = 0, shared = 0;
  for (const g of A) { const w = idf(g); wa += w; if (B.has(g)) { inter += w; shared++; } }
  for (const g of B) wb += idf(g);
  return { s: (wa + wb) ? 2 * inter / (wa + wb) : 0, shared };
}

/* 부서별로 나눠 둔다 — 5,600 × 2,800 전수 비교는 느리다 */
const byDept = new Map();
for (const p of posts) for (const d of p.depts) {
  if (!byDept.has(d)) byDept.set(d, []);
  byDept.get(d).push(p);
}

const map = {};
let pairs = 0;
for (const o of D.occ) {
  const title = o.item.title || '';
  const n = norm(title);
  if (n.length < 6) continue;                 /* 너무 짧은 제목은 짝지어도 믿을 수 없다 */
  const A = bigrams(n);
  const ay = years(title), am = months(title), ar = rounds(title);
  const w0 = dayNo(o.week);
  const hit = [];
  const done = new Set();
  for (const dp of deptSet(o.dept)) for (const p of (byDept.get(dp) || [])) {
    if (done.has(p.idx)) continue;
    const dd = dayNo(p.date) - w0;
    if (dd < -CFG.backDays || dd > CFG.fwdDays) continue;
    if (clash(ay, p._y) || clash(am, p._m) || clash(ar, p._r)) continue;
    const [only1, only2] = conflicts(title, p.title);
    if (only1.length || only2.length) continue;
    const r = dice(A, bigrams(p._n));
    if (r.s < CFG.minScore || r.shared < CFG.minShared) continue;
    done.add(p.idx);
    hit.push({ i: p.idx, t: p.title, d: p.date, s: +r.s.toFixed(3) });
  }
  if (!hit.length) continue;
  const key = o.dept + '|' + BW.normKey(title);
  const cur = map[key] || (map[key] = []);
  for (const c of hit) if (!cur.some(x => x.i === c.i)) { cur.push(c); pairs++; }
  cur.sort((a, b) => b.s - a.s || (a.d < b.d ? 1 : -1));
  if (cur.length > CFG.maxPerItem) { pairs -= cur.length - CFG.maxPerItem; cur.length = CFG.maxPerItem; }
}
/* 같은 제목이 날짜만 달리해 다시 올라온 경우(재공고 등)는 최근 것 하나만 보여 준다 */
for (const k of Object.keys(map)) {
  const seen = new Set();
  map[k] = map[k].filter(x => { const t = norm(x.t); if (seen.has(t)) { pairs--; return false; } seen.add(t); return true; });
}
for (const k of Object.keys(map)) map[k] = map[k].map(({ i, t, d }) => ({ i, t, d }));

const out = {
  /* data.js 와 같은 이유로 고정값을 쓴다 — 내용이 같으면 매일 커밋되지 않아야 한다 */
  builtAt: cache.builtAt,
  base: cache.viewBase,
  map
};
const js = '/* 자동 생성 파일 — build/link_notices.js 로 재생성. 직접 수정 금지 */\n' +
  'window.BW_NLINKS=' + JSON.stringify(out) + ';';
fs.writeFileSync(outPath, js);
console.log(`notice_links.js 생성: ${outPath}`);
console.log(`  공지 ${posts.length}건 / 이어진 업무 ${Object.keys(map).length}개 / 짝 ${pairs}개 / ` +
  `${Math.round(Buffer.byteLength(js) / 1024)}KB`);
