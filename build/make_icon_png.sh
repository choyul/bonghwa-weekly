#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# make_icon_png.sh — icon.svg / icon-maskable.svg → 홈 화면용 PNG 세 장
#   휴대폰 홈 화면에 박히는 것은 SVG 가 아니라 이 PNG 들이다.
#   (public.webmanifest 가 이 세 파일을 가리킨다)
#   글자가 전부 도형이라 글꼴이 하나도 없는 서버에서도 똑같이 그려진다.
#   rsvg-convert 가 없으면 아무 것도 하지 않고 조용히 넘어간다.
# ═══════════════════════════════════════════════════════════════
set -e
cd "$(dirname "$0")/.."

if ! command -v rsvg-convert >/dev/null 2>&1; then
  echo "  (rsvg-convert 가 없어 PNG 는 그대로 둡니다)"
  exit 0
fi

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
rsvg-convert -w 192 -h 192 icon.svg          -o "$tmp/icon-m192.png"
rsvg-convert -w 512 -h 512 icon.svg          -o "$tmp/icon-m512.png"
rsvg-convert -w 512 -h 512 icon-maskable.svg -o "$tmp/icon-mmask512.png"
# 아이폰 홈 화면용 — 180×180, 모서리를 우리가 둥글리지 않은 네모(투명 없음)
python3 build/make_icon.py "$tmp/icon-ios.svg" --ios >/dev/null
rsvg-convert -w 180 -h 180 -b '#22C55E' "$tmp/icon-ios.svg" -o "$tmp/apple-touch-icon.png"

# 그리기가 잘못되면(빈 그림 등) 예전 것을 지키는 편이 낫다
for f in icon-m192 icon-m512 icon-mmask512 apple-touch-icon; do
  sz=$(wc -c < "$tmp/$f.png" | tr -d ' ')
  if [ "$sz" -lt 3000 ]; then
    echo "  ❌ $f.png 이 너무 작습니다($sz 바이트) — 그리기 실패로 보고 예전 것을 그대로 둡니다"
    exit 1
  fi
done
for f in icon-m192 icon-m512 icon-mmask512 apple-touch-icon; do
  mv "$tmp/$f.png" "$f.png"
  echo "  $f.png ($(( $(wc -c < "$f.png") / 1024 ))KB)"
done
