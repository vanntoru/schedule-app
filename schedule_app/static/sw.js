const CACHE_NAME = 'schedule-app-v1';
const CACHE_URLS = [
  '/',
  '/static/css/styles.css',
  '/static/js/app.js',
  '/static/sw.js',
  '/manifest.json',
  '/icon-192.png',
];

self.addEventListener('install', () => {
  // Cache will be populated on-demand during fetch events
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      )
    )
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== location.origin) return;

  event.respondWith(
    fetch(request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.ok) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return networkResponse;
        }
        return caches.match(request).then((cached) => cached || networkResponse);
      })
      .catch(() => caches.match(request))
  );
});
