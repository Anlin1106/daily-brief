/* The Daily Brief · Service Worker
   目标：装到主屏后可离线打开、离线收听已缓存音频。
   策略：
   - 页面骨架（index.html / manifest / 图标）预缓存
   - data/news.js 走"网络优先，失败回退缓存"，保证每天更新能拿到最新一期
   - data/audio/** 走"缓存优先"（文件按日期命名，天然不可变），离线也能听
*/
const VERSION = 'brief-v3';   // v3: 连播按文件名对齐条目 + 音频内容指纹; 改动 index.html 时必须升版本, 否则已装用户拿不到新页面
const SHELL = [
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(VERSION)
      .then(c => c.addAll(SHELL).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin && !url.pathname.includes('/data/audio/')) return;

  // 数据文件：网络优先，断网时用上次缓存
  if (url.pathname.endsWith('/data/news.js') || url.pathname.endsWith('/data/news.json')) {
    e.respondWith(
      fetch(req).then(res => {
        const copy = res.clone();
        caches.open(VERSION).then(c => c.put(req, copy)).catch(() => {});
        return res;
      }).catch(() => caches.match(req).then(hit => hit || Response.error()))
    );
    return;
  }

  // 音频：缓存优先（按日期命名，内容不变），首次播放后自动缓存
  if (url.pathname.includes('/data/audio/')) {
    e.respondWith(
      caches.match(req).then(hit => hit || fetch(req).then(res => {
        if (res.ok || res.type === 'opaque') {
          const copy = res.clone();
          caches.open(VERSION).then(c => c.put(req, copy)).catch(() => {});
        }
        return res;
      }))
    );
    return;
  }

  // 页面骨架：缓存优先，后台更新
  if (req.mode === 'navigate' || url.pathname.endsWith('/index.html')) {
    e.respondWith(
      caches.match('./index.html').then(hit => {
        const net = fetch(req).then(res => {
          const copy = res.clone();
          caches.open(VERSION).then(c => c.put('./index.html', copy)).catch(() => {});
          return res;
        }).catch(() => hit);
        return hit || net;
      })
    );
    return;
  }

  e.respondWith(caches.match(req).then(hit => hit || fetch(req)));
});
