/* sw.js — 서비스워커 (§5.6 캐싱 처리)
   - data.js : network-first  → 갱신 즉시 반영, 오프라인 시 캐시
   - 앱 셸(HTML/JS/아이콘) : cache-first → 빠른 로딩
   앱 셸을 바꾸면 CACHE 버전을 올릴 것. */
'use strict';
const CACHE = 'bw-shell-v1';
const SHELL = ['./mayor.html', './staff.html', './public.html', './core.js', './ui.js', './ui.css', './icon.svg',
  './mayor.webmanifest', './staff.webmanifest', './public.webmanifest', './manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks =>
    Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;

  /* data.js — network-first (쿼리 v= 는 무시하고 항상 최신 시도) */
  if (url.pathname.endsWith('/data.js')) {
    e.respondWith(
      fetch(e.request).then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put('./data.js', copy));
        return res;
      }).catch(() => caches.match('./data.js'))
    );
    return;
  }
  /* 앱 셸 — cache-first */
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(hit => hit ||
      fetch(e.request).then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
        return res;
      })
    )
  );
});
