/**
 * Secure Storage Service for iOS Keychain storage.
 * Uses capacitor-secure-storage-plugin for encrypted credential storage.
 *
 * This service provides secure storage for sensitive data like passwords
 * and refresh tokens using the iOS Keychain (AES-256 encryption).
 *
 * Based on the deployment plan Phase 2: Security Hardening.
 */

import { Capacitor } from '@capacitor/core';
import { Preferences } from '@capacitor/preferences';

// Storage keys for secure credentials
const STORAGE_KEYS = {
  PASSWORD: 'garmin_password',
  REFRESH_TOKEN: 'garmin_refresh_token',
  ACCESS_TOKEN: 'garmin_access_token',
} as const;

// Type for storage keys
type StorageKey = typeof STORAGE_KEYS[keyof typeof STORAGE_KEYS];

// Error types for secure storage operations
export enum SecureStorageErrorType {
  NOT_AVAILABLE = 'NOT_AVAILABLE',
  STORAGE_FAILED = 'STORAGE_FAILED',
  RETRIEVAL_FAILED = 'RETRIEVAL_FAILED',
  CLEAR_FAILED = 'CLEAR_FAILED',
  UNKNOWN = 'UNKNOWN',
}

export interface SecureStorageError {
  type: SecureStorageErrorType;
  message: string;
  originalError?: unknown;
}

/**
 * Result type for secure storage operations
 */
export type SecureStorageResult<T> =
  | { success: true; data: T }
  | { success: false; error: SecureStorageError };

/**
 * Secure Storage Service
 *
 * Provides secure storage for sensitive credentials using iOS Keychain
 * when running on native platforms. Falls back to Preferences on web
 * (with a warning, as this is not secure for production use).
 */
class SecureStorageService {
  private isNative: boolean;
  private SecureStorage: typeof import('@aparajita/capacitor-secure-storage').SecureStorage | null = null;
  private initialized = false;
  private initPromise: Promise<void> | null = null;

  constructor() {
    this.isNative = Capacitor.isNativePlatform();
  }

  /**
   * Initialize the secure storage plugin.
   * Must be called before using any storage methods.
   */
  private async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }

    if (this.initPromise) {
      return this.initPromise;
    }

    this.initPromise = this.doInitialize();
    return this.initPromise;
  }

  private async doInitialize(): Promise<void> {
    if (this.isNative) {
      try {
        // Dynamically import the secure storage plugin
        const module = await import('@aparajita/capacitor-secure-storage');
        this.SecureStorage = module.SecureStorage;
        this.initialized = true;
        console.log('[SecureStorage] Initialized with native Keychain storage');
      } catch (error) {
        console.warn('[SecureStorage] Failed to load secure storage plugin, falling back to Preferences:', error);
        this.SecureStorage = null;
        this.initialized = true;
      }
    } else {
      console.warn('[SecureStorage] Running on web - using Preferences fallback (NOT SECURE for production)');
      this.initialized = true;
    }
  }

  /**
   * Store a value securely.
   */
  private async set(key: StorageKey, value: string): Promise<SecureStorageResult<void>> {
    try {
      await this.initialize();

      if (this.SecureStorage) {
        // Use native secure storage (iOS Keychain)
        // API: set(key: string, data: DataType, convertDate?: boolean, sync?: boolean, access?: KeychainAccess)
        await this.SecureStorage.set(key, value);
      } else {
        // Fallback to Preferences (not secure, but works on web)
        await Preferences.set({ key, value });
      }

      return { success: true, data: undefined };
    } catch (error) {
      console.error(`[SecureStorage] Failed to set ${key}:`, error);
      return {
        success: false,
        error: {
          type: SecureStorageErrorType.STORAGE_FAILED,
          message: `Failed to store ${key}`,
          originalError: error,
        },
      };
    }
  }

  /**
   * Retrieve a value from secure storage.
   */
  private async get(key: StorageKey): Promise<SecureStorageResult<string | null>> {
    try {
      await this.initialize();

      if (this.SecureStorage) {
        // Use native secure storage (iOS Keychain)
        // API: get(key: string, convertDate?: boolean, sync?: boolean) - returns null if not found
        const result = await this.SecureStorage.get(key);
        return { success: true, data: result as string | null };
      } else {
        // Fallback to Preferences
        const result = await Preferences.get({ key });
        return { success: true, data: result.value };
      }
    } catch (error) {
      console.error(`[SecureStorage] Failed to get ${key}:`, error);
      return {
        success: false,
        error: {
          type: SecureStorageErrorType.RETRIEVAL_FAILED,
          message: `Failed to retrieve ${key}`,
          originalError: error,
        },
      };
    }
  }

  /**
   * Remove a specific key from secure storage.
   */
  private async remove(key: StorageKey): Promise<SecureStorageResult<void>> {
    try {
      await this.initialize();

      if (this.SecureStorage) {
        // API: remove(key: string, sync?: boolean) - returns true if existed, false if not
        await this.SecureStorage.remove(key);
      } else {
        await Preferences.remove({ key });
      }

      return { success: true, data: undefined };
    } catch (error) {
      console.error(`[SecureStorage] Failed to remove ${key}:`, error);
      return {
        success: false,
        error: {
          type: SecureStorageErrorType.CLEAR_FAILED,
          message: `Failed to remove ${key}`,
          originalError: error,
        },
      };
    }
  }

  // ==================== Public API ====================

  /**
   * Store the Garmin password securely in the iOS Keychain.
   */
  async setPassword(password: string): Promise<void> {
    const result = await this.set(STORAGE_KEYS.PASSWORD, password);
    if (!result.success) {
      throw new Error(result.error.message);
    }
  }

  /**
   * Retrieve the stored Garmin password from the iOS Keychain.
   * Returns null if no password is stored.
   */
  async getPassword(): Promise<string | null> {
    const result = await this.get(STORAGE_KEYS.PASSWORD);
    if (!result.success) {
      console.error('[SecureStorage] Error getting password:', result.error);
      return null;
    }
    return result.data;
  }

  /**
   * Store the OAuth refresh token securely in the iOS Keychain.
   */
  async setRefreshToken(token: string): Promise<void> {
    const result = await this.set(STORAGE_KEYS.REFRESH_TOKEN, token);
    if (!result.success) {
      throw new Error(result.error.message);
    }
  }

  /**
   * Retrieve the stored OAuth refresh token from the iOS Keychain.
   * Returns null if no token is stored.
   */
  async getRefreshToken(): Promise<string | null> {
    const result = await this.get(STORAGE_KEYS.REFRESH_TOKEN);
    if (!result.success) {
      console.error('[SecureStorage] Error getting refresh token:', result.error);
      return null;
    }
    return result.data;
  }

  /**
   * Store the OAuth access token securely.
   * Note: Access tokens are typically short-lived and could also be kept in memory.
   */
  async setAccessToken(token: string): Promise<void> {
    const result = await this.set(STORAGE_KEYS.ACCESS_TOKEN, token);
    if (!result.success) {
      throw new Error(result.error.message);
    }
  }

  /**
   * Retrieve the stored OAuth access token.
   * Returns null if no token is stored.
   */
  async getAccessToken(): Promise<string | null> {
    const result = await this.get(STORAGE_KEYS.ACCESS_TOKEN);
    if (!result.success) {
      console.error('[SecureStorage] Error getting access token:', result.error);
      return null;
    }
    return result.data;
  }

  /**
   * Clear all securely stored credentials.
   * Should be called on logout to remove sensitive data.
   */
  async clearAll(): Promise<void> {
    const errors: SecureStorageError[] = [];

    // Remove each key individually to ensure all are attempted
    for (const key of Object.values(STORAGE_KEYS)) {
      const result = await this.remove(key);
      if (!result.success) {
        errors.push(result.error);
      }
    }

    if (errors.length > 0) {
      console.error('[SecureStorage] Some keys failed to clear:', errors);
      // Throw if all failed, otherwise just log the warning
      if (errors.length === Object.values(STORAGE_KEYS).length) {
        throw new Error('Failed to clear secure storage');
      }
    }

    console.log('[SecureStorage] All credentials cleared');
  }

  /**
   * Check if secure storage is available (native platform with plugin).
   */
  async isSecureStorageAvailable(): Promise<boolean> {
    await this.initialize();
    return this.SecureStorage !== null;
  }

  /**
   * Check if the app is running on a native platform.
   */
  isNativePlatform(): boolean {
    return this.isNative;
  }

  /**
   * Migrate credentials from Preferences to SecureStorage.
   * Call this once during app upgrade to migrate existing credentials.
   */
  async migrateFromPreferences(): Promise<void> {
    if (!this.isNative) {
      console.log('[SecureStorage] Skipping migration - not on native platform');
      return;
    }

    await this.initialize();

    if (!this.SecureStorage) {
      console.log('[SecureStorage] Skipping migration - secure storage not available');
      return;
    }

    console.log('[SecureStorage] Checking for credentials to migrate...');

    // Try to migrate password
    const { value: password } = await Preferences.get({ key: STORAGE_KEYS.PASSWORD });
    if (password) {
      try {
        await this.setPassword(password);
        await Preferences.remove({ key: STORAGE_KEYS.PASSWORD });
        console.log('[SecureStorage] Migrated password to secure storage');
      } catch (error) {
        console.error('[SecureStorage] Failed to migrate password:', error);
      }
    }

    // Try to migrate refresh token (if stored in preferences)
    const { value: refreshToken } = await Preferences.get({ key: STORAGE_KEYS.REFRESH_TOKEN });
    if (refreshToken) {
      try {
        await this.setRefreshToken(refreshToken);
        await Preferences.remove({ key: STORAGE_KEYS.REFRESH_TOKEN });
        console.log('[SecureStorage] Migrated refresh token to secure storage');
      } catch (error) {
        console.error('[SecureStorage] Failed to migrate refresh token:', error);
      }
    }

    console.log('[SecureStorage] Migration complete');
  }
}

// Export singleton instance
export const secureStorage = new SecureStorageService();

// Also export the class for testing purposes
export { SecureStorageService };

// Legacy export for backwards compatibility with deployment plan example
export const SecureCredentials = {
  setPassword: (password: string) => secureStorage.setPassword(password),
  getPassword: () => secureStorage.getPassword(),
  setRefreshToken: (token: string) => secureStorage.setRefreshToken(token),
  getRefreshToken: () => secureStorage.getRefreshToken(),
  clearAll: () => secureStorage.clearAll(),
};
