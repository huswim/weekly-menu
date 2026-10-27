const CACHE_PREFIX = 'weekly-table-';
const CACHE_NAME = CACHE_PREFIX + '037ff43f4ac4';
// Resolve resources relative to the worker, so the app works under /weekly-menu/ on GitHub Pages.
const BASE_PATH = new URL('.', self.location.href).pathname;
const CORE = ['', 'menu.json', 'pwa.js', 'manifest.webmanifest', 'assets/icons/icon-192.png', 'assets/icons/icon-512.png', 'assets/icons/apple-touch-icon.png'].map(path => BASE_PATH + path);
const OPTIONAL = ['assets/weekly-menu.pdf', 'assets/original-menu.jpeg'].map(path => BASE_PATH + path);
const ALLOWED = new Set([...CORE, ...OPTIONAL]);

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    // Reject redirects and HTML fallbacks so an authentication or error page
    // can never replace the offline app or menu data.
    for (const path of CORE) {
      const response = await fetch(new Request(path, { cache: 'reload' }));
      if (!isValid(response, path)) throw new Error('Unable to cache ' + path);
      await cache.put(path, response);
    }
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});
self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') self.skipWaiting();
});
function isValid(response, path) {
  if (!response.ok || response.redirected || response.type === 'opaque') return false;
  const contentType = response.headers.get('content-type') || '';
  if (path.endsWith('.json') || path.endsWith('.webmanifest')) return contentType.includes('json');
  if (path.endsWith('.js')) return /javascript/.test(contentType);
  if (path.endsWith('.png') || path.endsWith('.jpeg')) return contentType.startsWith('image/');
  if (path.endsWith('.pdf')) return contentType.includes('pdf');
  return contentType.includes('text/html');
}
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || !ALLOWED.has(url.pathname)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE_NAME);
    // This one-week menu is immutable. Serve the saved app and data
    // immediately; service-worker version updates replace the app cache.
    const saved = await cache.match(url.pathname);
    if (saved) return saved;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 4500);
    try {
      const response = await fetch(request, { signal: controller.signal, cache: 'no-cache' });
      if (isValid(response, url.pathname)) {
        await cache.put(url.pathname, response.clone()).catch(() => {});
      }
      if (response.status >= 500) {
        const cached = await cache.match(url.pathname);
        if (cached) return cached;
      }
      return response;
    } catch {
      const cached = await cache.match(url.pathname);
      if (cached) return cached;
      throw new Error('No offline copy available');
    } finally {
      clearTimeout(timeout);
    }
  })());
});
