const CACHE_NAME = 'schedule-app-v1';
const CACHE_URLS = [
  '/',
  '/static/css/styles.css',
  '/static/css/a11y.css',
  '/static/css/print.css',
  '/static/css/tailwind.min.css',
  '/static/js/app.js',
  '/static/sw.js',
  '/static/manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CACHE_URLS)),
  );
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

  // ---------------------------------------------------------------------
  // Fallback for Tailwind CDN script. When offline, replace the external
  // script with a local CSS file to maintain styling.
  // ---------------------------------------------------------------------
  if (url.hostname === 'cdn.tailwindcss.com') {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match('/static/css/tailwind.min.css').then((resp) => {
          if (!resp) return new Response('', { status: 404 });
          const js =
            "(function(){var l=document.createElement('link');l.rel='stylesheet';l.href='/static/css/tailwind.min.css';document.head.appendChild(l);})();";
          return new Response(js, {
            headers: { 'Content-Type': 'application/javascript' },
          });
        })
      )
    );
    return;
  }

  if (url.origin !== location.origin) return;

  event.respondWith(
    fetch(request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.ok) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          return networkResponse;
        }
        return caches
          .match(request)
          .then((cached) => cached || networkResponse);
      })
      .catch((err) =>
        caches.match(request).then((r) => r || Promise.reject(err))
      )
  );
});
