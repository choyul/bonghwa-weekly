/* 군민용 — 매주 자동 갱신되므로 항상 최신을 우선한다.
   네트워크 먼저 받고, 안 될 때만(오프라인) 캐시로 보여준다. */
'use strict';
const CACHE='bonghwa-public-v2';   /* 올리면 옛 캐시를 지운다 — 아이콘 등 바뀐 파일 반영 */
self.addEventListener('install',e=>self.skipWaiting());
self.addEventListener('activate',e=>e.waitUntil(
  caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())
));
self.addEventListener('fetch',e=>{
  const u=new URL(e.request.url);
  if(u.origin!==location.origin||e.request.method!=='GET')return;
  e.respondWith(
    fetch(e.request).then(res=>{
      const copy=res.clone(); caches.open(CACHE).then(c=>c.put(e.request,copy)); return res;
    }).catch(()=>caches.match(e.request))
  );
});
