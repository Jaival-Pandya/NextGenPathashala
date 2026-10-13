/* Privacy-first PWA shell cache. Never cache authenticated API responses or HTML dashboards. */
const CACHE_NAME = 'nextgenpathashala-shell-v6-classroom-assessments';
const SHELL_ASSETS = [
  '/static/css/style.css',
  '/static/css/landing.css',
  '/static/css/lovable-ui.css',
  '/static/js/app.js',
  '/static/manifest.webmanifest',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/offline'
];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL_ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;
  // API payloads, authentication pages and all personalized HTML remain network-only.
  if (url.pathname.startsWith('/api/')) return;
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
      if (response.ok && response.type === 'basic') caches.open(CACHE_NAME).then(cache => cache.put(request, response.clone()));
      return response;
    })));
    return;
  }
  if (request.mode === 'navigate') {
    // Never cache personalized pages, but show a generic fallback if a navigation fails offline.
    event.respondWith(fetch(request).catch(() => caches.match('/offline')));
  }
});
