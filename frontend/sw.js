const CACHE_NAME = 'nextgen-tutor-v1';
const STATIC_ASSETS = [
    '/',
    '/frontend/whiteboard.js',
    '/frontend/offline-store.js',
];

const API_CACHE = 'nextgen-api-v1';
const CACHEABLE_API = [
    '/api/v1/curriculum/knowledge-graph',
    '/api/v1/curriculum/lessons',
    '/api/v1/gamification/achievements',
    '/api/v1/games/types',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch(() => {});
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter((key) => key !== CACHE_NAME && key !== API_CACHE)
                    .map((key) => caches.delete(key))
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    if (event.request.method !== 'GET') {
        if (!navigator.onLine) {
            event.respondWith(
                storeOfflineAction(event.request.clone()).then(() => {
                    return new Response(JSON.stringify({ queued: true, offline: true }), {
                        headers: { 'Content-Type': 'application/json' }
                    });
                })
            );
            return;
        }
        return;
    }

    if (CACHEABLE_API.some(path => url.pathname.includes(path))) {
        event.respondWith(networkFirstWithCache(event.request, API_CACHE));
        return;
    }

    if (url.pathname === '/' || url.pathname.endsWith('.js') || url.pathname.endsWith('.html')) {
        event.respondWith(networkFirstWithCache(event.request, CACHE_NAME));
        return;
    }
});

async function networkFirstWithCache(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch (e) {
        const cached = await caches.match(request);
        if (cached) return cached;
        return new Response(JSON.stringify({ error: 'offline', cached: false }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

async function storeOfflineAction(request) {
    try {
        const body = await request.json();
        const action = {
            url: request.url,
            method: request.method,
            headers: Object.fromEntries(request.headers.entries()),
            body: body,
            timestamp: Date.now(),
        };

        const cache = await caches.open('offline-actions');
        const existing = await cache.match('pending-actions');
        let actions = [];
        if (existing) {
            actions = await existing.json();
        }
        actions.push(action);
        await cache.put('pending-actions', new Response(JSON.stringify(actions)));
    } catch (e) {}
}

self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-offline-actions') {
        event.waitUntil(syncOfflineActions());
    }
});

async function syncOfflineActions() {
    const cache = await caches.open('offline-actions');
    const existing = await cache.match('pending-actions');
    if (!existing) return;

    const actions = await existing.json();
    const remaining = [];

    for (const action of actions) {
        try {
            await fetch(action.url, {
                method: action.method,
                headers: action.headers,
                body: JSON.stringify(action.body),
            });
        } catch (e) {
            remaining.push(action);
        }
    }

    if (remaining.length > 0) {
        await cache.put('pending-actions', new Response(JSON.stringify(remaining)));
    } else {
        await cache.delete('pending-actions');
    }
}
