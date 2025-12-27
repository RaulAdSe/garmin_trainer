/**
 * PWA hooks for service worker, offline support, and notifications.
 */

import { useState, useEffect, useCallback } from 'react';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

interface PWAState {
  isInstalled: boolean;
  isOnline: boolean;
  isUpdateAvailable: boolean;
  canInstall: boolean;
  notificationPermission: NotificationPermission;
}

interface UsePWAReturn extends PWAState {
  install: () => Promise<boolean>;
  update: () => void;
  requestNotificationPermission: () => Promise<boolean>;
  sendNotification: (title: string, options?: NotificationOptions) => void;
  subscribeToPush: () => Promise<PushSubscription | null>;
}

/**
 * Hook for PWA functionality
 */
export function usePWA(): UsePWAReturn {
  const [state, setState] = useState<PWAState>({
    isInstalled: false,
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
    isUpdateAvailable: false,
    canInstall: false,
    notificationPermission: 'default',
  });

  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null);

  // Check if app is installed
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const checkInstalled = () => {
      const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
      const isIOSStandalone = (window.navigator as any).standalone === true;
      
      setState(prev => ({
        ...prev,
        isInstalled: isStandalone || isIOSStandalone,
      }));
    };

    checkInstalled();
    
    // Listen for display mode changes
    const mediaQuery = window.matchMedia('(display-mode: standalone)');
    mediaQuery.addEventListener('change', checkInstalled);

    return () => mediaQuery.removeEventListener('change', checkInstalled);
  }, []);

  // Register service worker
  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;

    navigator.serviceWorker.register('/sw.js')
      .then((reg) => {
        console.log('Service worker registered');
        setRegistration(reg);

        // Check for updates
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                setState(prev => ({ ...prev, isUpdateAvailable: true }));
              }
            });
          }
        });
      })
      .catch((error) => {
        console.error('Service worker registration failed:', error);
      });
  }, []);

  // Listen for install prompt
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setState(prev => ({ ...prev, canInstall: true }));
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);

    return () => window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
  }, []);

  // Track online/offline status
  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleOnline = () => setState(prev => ({ ...prev, isOnline: true }));
    const handleOffline = () => setState(prev => ({ ...prev, isOnline: false }));

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Check notification permission
  useEffect(() => {
    if (typeof window === 'undefined' || !('Notification' in window)) return;

    setState(prev => ({
      ...prev,
      notificationPermission: Notification.permission,
    }));
  }, []);

  // Install the PWA
  const install = useCallback(async (): Promise<boolean> => {
    if (!deferredPrompt) {
      console.log('No install prompt available');
      return false;
    }

    try {
      await deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      
      setDeferredPrompt(null);
      setState(prev => ({ ...prev, canInstall: false }));

      if (outcome === 'accepted') {
        setState(prev => ({ ...prev, isInstalled: true }));
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Install failed:', error);
      return false;
    }
  }, [deferredPrompt]);

  // Update the service worker
  const update = useCallback(() => {
    if (registration?.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
      window.location.reload();
    }
  }, [registration]);

  // Request notification permission
  const requestNotificationPermission = useCallback(async (): Promise<boolean> => {
    if (!('Notification' in window)) {
      console.log('Notifications not supported');
      return false;
    }

    try {
      const permission = await Notification.requestPermission();
      setState(prev => ({ ...prev, notificationPermission: permission }));
      return permission === 'granted';
    } catch (error) {
      console.error('Notification permission request failed:', error);
      return false;
    }
  }, []);

  // Send a local notification
  const sendNotification = useCallback((title: string, options?: NotificationOptions) => {
    if (state.notificationPermission !== 'granted') {
      console.log('Notification permission not granted');
      return;
    }

    if (registration) {
      registration.showNotification(title, {
        icon: '/icons/icon-192x192.png',
        badge: '/icons/badge-72x72.png',
        ...options,
      });
    } else {
      new Notification(title, {
        icon: '/icons/icon-192x192.png',
        ...options,
      });
    }
  }, [state.notificationPermission, registration]);

  // Subscribe to push notifications
  const subscribeToPush = useCallback(async (): Promise<PushSubscription | null> => {
    if (!registration) {
      console.log('No service worker registration');
      return null;
    }

    try {
      // Get VAPID public key from server
      const response = await fetch('/api/push/vapid-public-key');
      const { publicKey } = await response.json();

      const keyArray = urlBase64ToUint8Array(publicKey);
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: keyArray.buffer as ArrayBuffer,
      });

      // Send subscription to server
      await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(subscription),
      });

      return subscription;
    } catch (error) {
      console.error('Push subscription failed:', error);
      return null;
    }
  }, [registration]);

  return {
    ...state,
    install,
    update,
    requestNotificationPermission,
    sendNotification,
    subscribeToPush,
  };
}

/**
 * Hook for offline data management
 */
export function useOfflineData<T>(key: string, fetchFn: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isFromCache, setIsFromCache] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadData = async () => {
      setIsLoading(true);
      setError(null);

      // Try to load from IndexedDB cache first
      try {
        const cached = await getFromCache<T>(key);
        if (cached && !cancelled) {
          setData(cached);
          setIsFromCache(true);
        }
      } catch (e) {
        // Cache miss is fine
      }

      // Fetch fresh data
      try {
        const fresh = await fetchFn();
        if (!cancelled) {
          setData(fresh);
          setIsFromCache(false);
          await saveToCache(key, fresh);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e : new Error('Fetch failed'));
          // Keep cached data if available
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    loadData();

    return () => {
      cancelled = true;
    };
  }, [key, fetchFn]);

  return { data, isLoading, error, isFromCache };
}

// Helper functions

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }

  return outputArray;
}

async function getFromCache<T>(key: string): Promise<T | null> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('training-analyzer', 1);
    
    request.onerror = () => reject(request.error);
    
    request.onsuccess = () => {
      const db = request.result;
      
      if (!db.objectStoreNames.contains('offline-data')) {
        resolve(null);
        return;
      }
      
      const tx = db.transaction('offline-data', 'readonly');
      const store = tx.objectStore('offline-data');
      const getRequest = store.get(key);
      
      getRequest.onsuccess = () => resolve(getRequest.result?.data || null);
      getRequest.onerror = () => reject(getRequest.error);
    };
    
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains('offline-data')) {
        db.createObjectStore('offline-data', { keyPath: 'key' });
      }
    };
  });
}

async function saveToCache<T>(key: string, data: T): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('training-analyzer', 1);
    
    request.onerror = () => reject(request.error);
    
    request.onsuccess = () => {
      const db = request.result;
      const tx = db.transaction('offline-data', 'readwrite');
      const store = tx.objectStore('offline-data');
      
      store.put({ key, data, timestamp: Date.now() });
      
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    };
  });
}


