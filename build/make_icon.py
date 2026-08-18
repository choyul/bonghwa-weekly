#!/usr/bin/env python3
"""make_icon.py — 앱 아이콘 SVG 생성 (달력 숫자에 오늘 날짜)

  사용: python3 build/make_icon.py <출력.svg> [일자]
        일자를 안 주면 오늘 날짜를 쓴다.

바탕화면 아이콘은 한 번 만들어지면 OS가 그 이미지를 계속 쓰므로,
날짜는 '아이콘을 만든 날' 기준이다. 화면 안 파비콘은 매일 스스로 다시 그린다.
"""
import sys, datetime

def build(day):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
 <defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
   <stop offset="0" stop-color="#22C55E"/><stop offset="1" stop-color="#16A34A"/></linearGradient>
  <clipPath id="round"><rect width="512" height="512" rx="112"/></clipPath>
 </defs>
 <rect width="512" height="512" rx="112" fill="url(#bg)"/>
 <g clip-path="url(#round)">
  <circle cx="94" cy="132" r="38" fill="#F4B324"/>
  <path d="M-20 306 L56 232 L118 288 L188 220 L258 306 L258 392 L-20 392Z" fill="#0F7A38" opacity=".45"/>
  <path d="M-20 348 L44 296 L106 344 L170 294 L240 356 L240 412 L-20 412Z" fill="#0F7A38" opacity=".3"/>
 </g>
 <g stroke="#F4B324" stroke-width="21" stroke-linecap="round">
  <path d="M398 100 L384 144"/><path d="M454 136 L416 172"/><path d="M476 202 L430 214"/>
 </g>
 <rect x="242" y="96" width="28" height="34" rx="14" fill="#fff"/>
 <path d="M256 124c-66 0-100 72-106 138-6 66-19 118-34 152-5 12 2 25 16 25h248c14 0 21-13 16-25-15-34-28-86-34-152-6-66-40-138-106-138Z" fill="#fff"/>
 <text x="256" y="322" font-family="-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif"
       font-size="116" font-weight="800" fill="#16A34A" text-anchor="middle" letter-spacing="-3">봉화</text>
 <path d="M214 434h84c0 25-19 43-42 43s-42-18-42-43Z" fill="#F4B324"/>
 <g>
  <rect x="312" y="360" width="158" height="140" rx="24" fill="#fff"/>
  <path d="M312 384a24 24 0 0 1 24-24h110a24 24 0 0 1 24 24v31H312Z" fill="#F4B324"/>
  <rect x="346" y="342" width="16" height="38" rx="8" fill="#0F7A38"/>
  <rect x="420" y="342" width="16" height="38" rx="8" fill="#0F7A38"/>
  <text x="391" y="406" font-family="-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif"
        font-size="28" font-weight="800" fill="#fff" text-anchor="middle">오늘</text>
  <text x="391" y="476" font-family="-apple-system,'Apple SD Gothic Neo','Noto Sans KR',sans-serif"
        font-size="64" font-weight="800" fill="#16A34A" text-anchor="middle">{day}</text>
 </g>
</svg>
'''

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'icon.svg'
    day = sys.argv[2] if len(sys.argv) > 2 else str(datetime.date.today().day)
    open(out, 'w', encoding='utf-8').write(build(day))
    print(f'{out} 생성 (달력 숫자: {day})')
