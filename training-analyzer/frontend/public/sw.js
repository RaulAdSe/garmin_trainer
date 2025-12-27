/**
 * Service Worker for Training Analyzer PWA
 * 
 * Features:
 * - Offline workout viewing
 * - Background sync for activity uploads
 * - Push notifications for training reminders
 * - Cache-first strategy for static assets
 * - Network-first for API data with fallback
 */

const CACHE_NAME = 'training-analyzer-v1';
const STATIC_CACHE = 'static-v1';
const DYNAMIC_CACHE = 'dynamic-v1';
const WORKOUT_CACHE = 'workouts-v1';

// Assets to cache immediately on install
const STATIC_ASSETS = [
  '/',
  '/workouts',
  '/plans',
  '/goals',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
];

// API routes to cache with network-first strategy
const CACHEABLE_API_ROUTES = [
  '/api/workouts',
  '/api/plans',
  '/api/athlete',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys()
      .then((keys) => {
        return Promise.all(
          keys
            .filter((key) => key !== STATIC_CACHE && key !== DYNAMIC_CACHE && key !== WORKOUT_CACHE)
            .map((key) => {
              console.log('[SW] Removing old cache:', key);
              return caches.delete(key);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache with different strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip external requests
  if (url.origin !== location.origin) {
    return;
  }
  
  // API requests - network first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstWithCache(request, DYNAMIC_CACHE));
    return;
  }
  
  // Workout pages - cache with network update
  if (url.pathname.startsWith('/workouts/')) {
    event.respondWith(staleWhileRevalidate(request, WORKOUT_CACHE));
    return;
  }
  
  // Static assets - cache first
  event.respondWith(cacheFirst(request, STATIC_CACHE));
});

/**
 * Cache-first strategy
 * Try cache, fall back to network, cache the response
 */
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  
  if (cached) {
    return cached;
  }
  
  try {
    const response = await fetch(request);
    
    if (response.ok) {
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    // Return offline page if available
    const offlinePage = await cache.match('/offline.html');
    if (offlinePage) {
      return offlinePage;
    }
    
    return new Response('Offline', { status: 503 });
  }
}

/**
 * Network-first with cache fallback
 * Try network, fall back to cache if offline
 */
async function networkFirstWithCache(request, cacheName) {
  const cache = await caches.open(cacheName);
  
  try {
    const response = await fetch(request);
    
    if (response.ok) {
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    
    if (cached) {
      console.log('[SW] Serving from cache (offline):', request.url);
      return cached;
    }
    
    return new Response(
      JSON.stringify({ error: 'Offline', cached: false }),
      { 
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

/**
 * Stale-while-revalidate
 * Return cached immediately, update cache in background
 */
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  
  // Fetch in background regardless
  const fetchPromise = fetch(request)
    .then((response) => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => null);
  
  // Return cached immediately if available
  if (cached) {
    return cached;
  }
  
  // Otherwise wait for fetch
  const response = await fetchPromise;
  
  if (response) {
    return response;
  }
  
  return new Response('Offline', { status: 503 });
}

// Background sync for workout uploads
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);
  
  if (event.tag === 'sync-workouts') {
    event.waitUntil(syncWorkouts());
  }
  
  if (event.tag === 'sync-activities') {
    event.waitUntil(syncActivities());
  }
});

/**
 * Sync pending workouts
 */
async function syncWorkouts() {
  try {
    // Get pending workouts from IndexedDB
    const db = await openDatabase();
    const tx = db.transaction('pending-workouts', 'readonly');
    const store = tx.objectStore('pending-workouts');
    const pending = await store.getAll();
    
    for (const workout of pending) {
      try {
        await fetch('/api/workouts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(workout),
        });
        
        // Remove from pending on success
        const deleteTx = db.transaction('pending-workouts', 'readwrite');
        await deleteTx.objectStore('pending-workouts').delete(workout.id);
      } catch (error) {
        console.error('[SW] Failed to sync workout:', workout.id, error);
      }
    }
  } catch (error) {
    console.error('[SW] Sync workouts failed:', error);
  }
}

/**
 * Sync pending activities
 */
async function syncActivities() {
  console.log('[SW] Syncing activities...');
  // Implementation similar to syncWorkouts
}

/**
 * Open IndexedDB database
 */
function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('training-analyzer', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      
      if (!db.objectStoreNames.contains('pending-workouts')) {
        db.createObjectStore('pending-workouts', { keyPath: 'id' });
      }
      
      if (!db.objectStoreNames.contains('cached-workouts')) {
        db.createObjectStore('cached-workouts', { keyPath: 'id' });
      }
      
      if (!db.objectStoreNames.contains('pending-activities')) {
        db.createObjectStore('pending-activities', { keyPath: 'id' });
      }
    };
  });
}

// Push notification handling
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');
  
  if (!event.data) {
    return;
  }
  
  const data = event.data.json();
  
  const options = {
    body: data.body || 'Training notification',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/',
      type: data.type,
    },
    actions: data.actions || [],
    tag: data.tag || 'training-notification',
    renotify: data.renotify || false,
    requireInteraction: data.requireInteraction || false,
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title || 'Training Analyzer', options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.notification.tag);
  
  event.notification.close();
  
  const url = event.notification.data?.url || '/';
  
  // Handle action buttons
  if (event.action === 'view-workout') {
    event.waitUntil(clients.openWindow('/workouts'));
    return;
  }
  
  if (event.action === 'dismiss') {
    return;
  }
  
  // Default: open the app
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Focus existing window if open
        for (const client of clientList) {
          if (client.url.includes(self.location.origin) && 'focus' in client) {
            client.navigate(url);
            return client.focus();
          }
        }
        
        // Open new window
        return clients.openWindow(url);
      })
  );
});

// Periodic background sync for training data
self.addEventListener('periodicsync', (event) => {
  console.log('[SW] Periodic sync:', event.tag);
  
  if (event.tag === 'sync-training-data') {
    event.waitUntil(syncTrainingData());
  }
});

async function syncTrainingData() {
  try {
    // Fetch latest activities from connected platforms
    const response = await fetch('/api/sync/activities');
    
    if (response.ok) {
      // Update cached data
      const cache = await caches.open(DYNAMIC_CACHE);
      await cache.put('/api/workouts', response.clone());
    }
  } catch (error) {
    console.error('[SW] Training data sync failed:', error);
  }
}

console.log('[SW] Service worker loaded');


