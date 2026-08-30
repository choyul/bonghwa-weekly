'use strict';
/* ── 행정 문서에 늘 붙는 말 ──
   이런 말만 겹치는 것은 '같은 일'이라는 근거가 못 된다. 낱말 단위로만 걷어낸다
   (문자열 전체에서 지우면 '일시 상향'이 '시상'을 품은 것으로 보여 엉뚱하게 부서진다). */
const GENERIC = [
  '봉화군', '봉화읍', '봉화', '경상북도', '경북', '우리군', '관내', '군민', '주민',
  '신청', '신청서', '접수', '안내', '공고', '알림', '게시', '홍보', '모집', '선발', '선정', '심사', '발표', '결과',
  '개최', '개막', '개강', '운영', '실시', '시행', '추진', '계획', '방침', '점검', '조사', '수요', '확인', '관리', '정비',
  '지원', '사업', '사업비', '교부', '지급', '배부', '제작', '설치', '구입', '신규', '공모', '지침', '평가',
  '교육', '강좌', '과정', '프로그램', '행사', '설명회', '간담회', '회의', '보고', '훈련', '수강', '이용', '보급',
  '참가', '참여', '대상', '대상자', '참가자', '수강생', '교육생', '신청자', '희망자', '참석', '당첨자',
  '기간', '일정', '연장', '변경', '추가', '최종', '예정', '완료', '개시', '마감', '철저', '협조', '수립', '집중',
  '상반기', '하반기', '분기', '연간', '정기', '수시', '일부', '전면', '통합', '합동', '공동', '실적',
  '국비', '도비', '군비', '융자', '대출',
  '관련', '따른', '위한', '사항', '내용', '현황', '자료', '서식', '명단', '목록', '공지', '소식'
].sort((a, b) => b.length - a.length);

const ENDS = /[제회차기년월일호건및등분]+$/;
const HEAD = /^[제회차기년월일호건및등분]+/;
const JOSA = /(에서|에게|으로|에|의|을|를|은|는|로|와|과|도|만)$/;

const norm = s => String(s || '').normalize('NFC').toLowerCase().replace(/[^0-9a-z가-힣]/g, '');
const tokens = t => String(t || '').split(/[^0-9A-Za-z가-힣]+/).filter(Boolean);

/* 낱말 하나에서 '이 일을 이 일이게 하는' 조각만 남긴다 */
function stripTok(raw) {
  let w = norm(raw);
  for (const g of GENERIC) if (g.length >= 2) w = w.split(g).join('');
  w = w.replace(/[0-9]/g, '');
  let p; do { p = w; w = w.replace(HEAD, '').replace(ENDS, ''); } while (w !== p);
  const j = w.replace(JOSA, '');                  /* 붙은 조사는 떼되, 남는 줄기가 두 글자는 돼야 한다 */
  if (j.length >= 2) w = j;
  return w;
}
const coreWords = t => [...new Set(tokens(t).map(stripTok).filter(w => w.length >= 2))];
const stripAll = t => tokens(t).map(stripTok).join('');

/* 낱말이 상대 제목에 '충분히' 들어 있는가 —
   완전 일치만 따지면 '후계농업경영인'과 '후계농업경영인육성'이 남남이 된다.
   가장 긴 공통 조각이 낱말의 70% 이상이면 같은 말로 본다. */
function lcsLen(a, b) {
  let best = 0, prev = new Array(b.length + 1).fill(0);
  for (let i = 1; i <= a.length; i++) {
    const cur = new Array(b.length + 1).fill(0);
    for (let j = 1; j <= b.length; j++)
      if (a[i - 1] === b[j - 1]) { cur[j] = prev[j - 1] + 1; if (cur[j] > best) best = cur[j]; }
    prev = cur;
  }
  return best;
}
const covered = (w, other) =>
  other.includes(w) || lcsLen(w, other) >= Math.max(2, Math.ceil(w.length * 0.7));

/* 두 제목 사이에 '한쪽에만 있는 핵심어'가 있으면 다른 글이다 */
function conflicts(a, b) {
  const sa = stripAll(a), sb = stripAll(b);
  return [coreWords(a).filter(w => !covered(w, sb)), coreWords(b).filter(w => !covered(w, sa))];
}
module.exports = { GENERIC, norm, coreWords, stripAll, covered, conflicts };
