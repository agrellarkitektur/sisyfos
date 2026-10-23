/*
 * Sisyfos – service worker (fri programvara under GNU GPL v3 eller senare)
 * Gör att appen startar utan nät. Sidan hämtas i första hand från servern (så att en ny version syns
 * direkt) och sparas då i cachen; utan nät används den senast sparade. Boken ligger aldrig här –
 * den finns i webbläsarens databas. Inget skickas någonstans.
 */
const VERSION = '0.10.0';
const CACHE = 'sisyfos-' + VERSION;
const ASSETS = ['./', './index.html', './manifest.webmanifest', './icon.svg', './favicon-32.png', './icon-192.png', './icon-512.png', './icon-maskable-512.png', './apple-touch-icon.png'];

self.addEventListener('install', ev => {
  ev.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS.map(u => new Request(u, { cache: 'reload' })))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', ev => {
  ev.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('sisyfos-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('message', ev => { if (ev.data === 'version') ev.source?.postMessage({ t: 'sw', version: VERSION }); });

const timeout = (p, ms) => new Promise((res, rej) => { const t = setTimeout(() => rej(new Error('timeout')), ms); p.then(v => { clearTimeout(t); res(v); }, e => { clearTimeout(t); rej(e); }); });

self.addEventListener('fetch', ev => {
  const req = ev.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin) return;
  const scope = new URL(self.registration.scope);
  if (!url.pathname.startsWith(scope.pathname)) return;
  const rel = url.pathname.slice(scope.pathname.length);
  // Bara appens egna filer – allt annat (t.ex. gamla versioner i undermappar) går direkt till nätet
  const isPage = req.mode === 'navigate' && (rel === '' || rel === 'index.html');
  const isAsset = ASSETS.includes('./' + rel);
  if (!isPage && !isAsset) return;
  if (isPage || rel === 'index.html' || rel === '') {
    // Nätet först (ny version direkt), cachen om nätet inte svarar inom 4 sekunder
    ev.respondWith((async () => {
      const c = await caches.open(CACHE);
      try {
        // Ny begäran (inte navigeringsbegäran med extra inställningar – det tillåter inte alla webbläsare)
        const res = await timeout(fetch(new Request(url.href, { cache: 'no-cache', credentials: 'same-origin' })), 4000);
        if (res.ok) c.put('./index.html', res.clone());
        return res;
      } catch (_) {
        return (await c.match('./index.html')) || (await c.match('./')) || Response.error();
      }
    })());
    return;
  }
  // Ikoner och manifest: cachen först, uppdateras i bakgrunden
  ev.respondWith((async () => {
    const c = await caches.open(CACHE), hit = await c.match(req);
    const net = fetch(req).then(res => { if (res.ok) c.put(req, res.clone()); return res; }).catch(() => null);
    return hit || (await net) || Response.error();
  })());
});
