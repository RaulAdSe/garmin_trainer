/**
 * Garmin Connect API client for Capacitor.
 * Handles OAuth authentication and wellness data fetching.
 *
 * Based on the garmin-connect npm package authentication flow.
 * Uses CapacitorHttp for native requests (bypasses CORS).
 */

import { Preferences } from '@capacitor/preferences';
import { CapacitorHttp, HttpResponse } from '@capacitor/core';
import { Capacitor } from '@capacitor/core';
import { db, SleepData, HRVData, StressData, ActivityData, WellnessRecord } from './database';
import { secureStorage } from './secure-storage';

// Use native HTTP on iOS/Android, fetch on web
const isNative = Capacitor.isNativePlatform();

// Native HTTP wrapper that falls back to fetch on web
async function nativeGet(url: string, headers?: Record<string, string>): Promise<{ data: unknown; status: number }> {
  try {
    if (isNative) {
      const response: HttpResponse = await CapacitorHttp.get({
        url,
        headers: headers || {},
      });
      return { data: response.data, status: response.status };
    } else {
      const response = await fetch(url, { headers, credentials: 'include' });
      const data = await response.json().catch(() => response.text());
      return { data, status: response.status };
    }
  } catch (error) {
    console.error('[HTTP] GET failed:', url, error);
    return { data: null, status: 0 }; // Return status 0 for network errors
  }
}

async function nativePost(
  url: string,
  body?: string | Record<string, unknown>,
  headers?: Record<string, string>
): Promise<{ data: unknown; status: number; headers: Record<string, string> }> {
  try {
    if (isNative) {
      const response: HttpResponse = await CapacitorHttp.post({
        url,
        headers: headers || {},
        data: body,
      });
      return { data: response.data, status: response.status, headers: response.headers };
    } else {
      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: typeof body === 'string' ? body : JSON.stringify(body),
        credentials: 'include',
      });
      const data = await response.json().catch(() => response.text());
      const respHeaders: Record<string, string> = {};
      response.headers.forEach((v, k) => respHeaders[k] = v);
      return { data, status: response.status, headers: respHeaders };
    }
  } catch (error) {
    console.error('[HTTP] POST failed:', url, error);
    return { data: null, status: 0, headers: {} };
  }
}

async function nativeGetText(url: string, headers?: Record<string, string>): Promise<{ data: string; status: number; headers: Record<string, string> }> {
  try {
    if (isNative) {
      const response: HttpResponse = await CapacitorHttp.get({
        url,
        headers: headers || {},
        responseType: 'text',
      });
      return { data: response.data as string, status: response.status, headers: response.headers };
    } else {
      const response = await fetch(url, { headers, credentials: 'include' });
      const data = await response.text();
      const respHeaders: Record<string, string> = {};
      response.headers.forEach((v, k) => respHeaders[k] = v);
      return { data, status: response.status, headers: respHeaders };
    }
  } catch (error) {
    console.error('[HTTP] GET text failed:', url, error);
    return { data: '', status: 0, headers: {} };
  }
}

// Helper to extract cookies from Set-Cookie header
function extractCookies(headers: Record<string, string>): string {
  const setCookie = headers['Set-Cookie'] || headers['set-cookie'] || '';
  if (!setCookie) return '';

  // Handle multiple cookies (can be array or semicolon-separated)
  const cookieStrings = Array.isArray(setCookie) ? setCookie : [setCookie];
  const cookies: string[] = [];

  for (const cookieStr of cookieStrings) {
    // Split by comma but be careful about expires dates
    const parts = cookieStr.split(/,(?=\s*[^;]+=[^;]+)/);
    for (const part of parts) {
      // Extract just the name=value part (before any ;)
      const nameValue = part.split(';')[0].trim();
      if (nameValue && nameValue.includes('=')) {
        cookies.push(nameValue);
      }
    }
  }

  return cookies.join('; ');
}

// Helper to merge cookies
function mergeCookies(existing: string, newCookies: string): string {
  if (!existing) return newCookies;
  if (!newCookies) return existing;

  const cookieMap = new Map<string, string>();

  // Parse existing cookies
  for (const cookie of existing.split('; ')) {
    const [name, ...valueParts] = cookie.split('=');
    if (name) cookieMap.set(name.trim(), valueParts.join('='));
  }

  // Add/update with new cookies
  for (const cookie of newCookies.split('; ')) {
    const [name, ...valueParts] = cookie.split('=');
    if (name) cookieMap.set(name.trim(), valueParts.join('='));
  }

  return Array.from(cookieMap.entries())
    .map(([name, value]) => `${name}=${value}`)
    .join('; ');
}

// Garmin Connect endpoints
const GARMIN_SSO_EMBED = 'https://sso.garmin.com/sso/embed';
const GC_MODERN = 'https://connect.garmin.com/modern';
const SIGNIN_URL = 'https://sso.garmin.com/sso/signin';
const OAUTH_URL = 'https://connectapi.garmin.com/oauth-service/oauth';
// Use connectapi.garmin.com for API calls (NOT connect.garmin.com/modern/proxy/)
const CONNECT_API = 'https://connectapi.garmin.com';

// OAuth1 consumer credentials (from https://thegarth.s3.amazonaws.com/oauth_consumer.json)
const OAUTH_CONSUMER_KEY = 'fc3e99d2-118c-44b8-8ae3-03370dde24c0';
const OAUTH_CONSUMER_SECRET = 'E08WAR897WEy2knn7aFBrvegVAf0AFdWBBF';

// Helper: percent encode for OAuth (RFC 3986)
function percentEncode(str: string): string {
  return encodeURIComponent(str)
    .replace(/!/g, '%21')
    .replace(/\*/g, '%2A')
    .replace(/'/g, '%27')
    .replace(/\(/g, '%28')
    .replace(/\)/g, '%29');
}

// Helper: generate HMAC-SHA1 signature for OAuth1
async function hmacSha1(key: string, message: string): Promise<string> {
  const encoder = new TextEncoder();
  const keyData = encoder.encode(key);
  const messageData = encoder.encode(message);

  const cryptoKey = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-1' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign('HMAC', cryptoKey, messageData);

  // Convert to base64
  const bytes = new Uint8Array(signature);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

// Helper: build OAuth1 authorization header with HMAC-SHA1
async function buildOAuth1Header(
  method: string,
  url: string,
  params: Record<string, string>,
  consumerKey: string,
  consumerSecret: string,
  tokenKey?: string,
  tokenSecret?: string
): Promise<string> {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const nonce = Math.random().toString(36).substring(2, 15) +
                Math.random().toString(36).substring(2, 15);

  // OAuth params
  const oauthParams: Record<string, string> = {
    oauth_consumer_key: consumerKey,
    oauth_nonce: nonce,
    oauth_signature_method: 'HMAC-SHA1',
    oauth_timestamp: timestamp,
    oauth_version: '1.0',
  };

  if (tokenKey) {
    oauthParams.oauth_token = tokenKey;
  }

  // Combine all params for signature base string
  const allParams: Record<string, string> = { ...oauthParams, ...params };

  // Sort and encode params
  const sortedParams = Object.keys(allParams)
    .sort()
    .map(key => `${percentEncode(key)}=${percentEncode(allParams[key])}`)
    .join('&');

  // Build signature base string
  const baseUrl = url.split('?')[0];
  const signatureBaseString = [
    method.toUpperCase(),
    percentEncode(baseUrl),
    percentEncode(sortedParams),
  ].join('&');

  // Build signing key
  const signingKey = `${percentEncode(consumerSecret)}&${percentEncode(tokenSecret || '')}`;

  // Generate signature
  const signature = await hmacSha1(signingKey, signatureBaseString);
  oauthParams.oauth_signature = signature;

  // Build Authorization header
  const headerParams = Object.keys(oauthParams)
    .sort()
    .map(key => `${percentEncode(key)}="${percentEncode(oauthParams[key])}"`)
    .join(', ');

  return `OAuth ${headerParams}`;
}

// Token storage keys
const TOKEN_KEY = 'garmin_tokens';

// Token expiry buffer - refresh if token expires within 5 minutes
const TOKEN_EXPIRY_BUFFER_MS = 5 * 60 * 1000;

// Retry configuration
const DEFAULT_RETRY_COUNT = 3;
const DEFAULT_RETRY_DELAY_MS = 1000;

// Types
interface OAuth1Token {
  oauth_token: string;
  oauth_token_secret: string;
}

interface OAuth2Token {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token?: string;
  expires_at?: number;
}

interface StoredTokens {
  oauth1: OAuth1Token | null;
  oauth2: OAuth2Token | null;
}

interface LoginResult {
  success: boolean;
  error?: string;
}

interface SyncResult {
  success: boolean;
  daysProcessed: number;
  error?: string;
}

class GarminService {
  private oauth1Token: OAuth1Token | null = null;
  private oauth2Token: OAuth2Token | null = null;
  // Token refresh queue - prevents multiple simultaneous refresh calls
  private refreshPromise: Promise<void> | null = null;
  // Track if tokens have been loaded from storage
  private tokensLoaded = false;
  private loadingTokens: Promise<void> | null = null;
  // Cached user display name (required for API calls)
  private displayName: string | null = null;

  constructor() {
    // Don't call loadTokens() here - it's async and can't be awaited in constructor
    // Tokens will be loaded lazily when needed
  }

  // Load tokens from Preferences (with deduplication)
  private async loadTokens(): Promise<void> {
    // If tokens are already loaded, skip
    if (this.tokensLoaded) return;

    // If currently loading, wait for that to complete
    if (this.loadingTokens) {
      await this.loadingTokens;
      return;
    }

    this.loadingTokens = this.doLoadTokens();
    await this.loadingTokens;
    this.loadingTokens = null;
  }

  private async doLoadTokens(): Promise<void> {
    try {
      const { value } = await Preferences.get({ key: TOKEN_KEY });
      if (value) {
        const tokens: StoredTokens = JSON.parse(value);
        this.oauth1Token = tokens.oauth1;
        this.oauth2Token = tokens.oauth2;
      }
      this.tokensLoaded = true;
      console.log('[Garmin] Tokens loaded from storage:', !!this.oauth2Token);
    } catch (error) {
      console.error('[Garmin] Failed to load tokens:', error);
      this.tokensLoaded = true; // Mark as loaded even on error to prevent infinite retries
    }
  }

  // Save tokens to Preferences
  private async saveTokens(): Promise<void> {
    try {
      const tokens: StoredTokens = {
        oauth1: this.oauth1Token,
        oauth2: this.oauth2Token,
      };
      await Preferences.set({
        key: TOKEN_KEY,
        value: JSON.stringify(tokens),
      });
    } catch (error) {
      console.error('Failed to save tokens:', error);
    }
  }

  // Clear tokens (logout)
  async logout(): Promise<void> {
    this.oauth1Token = null;
    this.oauth2Token = null;
    await Preferences.remove({ key: TOKEN_KEY });
    await Preferences.remove({ key: 'garmin_email' });
    await secureStorage.clearAll();
  }

  // Check if authenticated
  async isAuthenticated(): Promise<boolean> {
    // If we already have tokens in memory, use them (don't overwrite with stale storage)
    if (this.oauth2Token !== null) {
      return true;
    }
    // Otherwise, try to load from storage
    await this.loadTokens();
    return this.oauth2Token !== null;
  }

  // Login directly with Garmin SSO (on-device, no backend required)
  // This follows the exact approach from the Python garth library
  async login(email: string, password: string): Promise<LoginResult> {
    try {
      console.log('[Garmin] Starting direct SSO login...');

      // Store credentials
      await Preferences.set({ key: 'garmin_email', value: email });
      await secureStorage.setPassword(password);

      const SSO = 'https://sso.garmin.com/sso';
      const SSO_EMBED = `${SSO}/embed`;

      // Params for embed widget flow (matches garth library exactly)
      const embedParams = new URLSearchParams({
        'id': 'gauth-widget',
        'embedWidget': 'true',
        'gauthHost': SSO,
      });

      const signinParams = new URLSearchParams({
        'id': 'gauth-widget',
        'embedWidget': 'true',
        'gauthHost': SSO_EMBED,
        'service': SSO_EMBED,
        'source': SSO_EMBED,
        'redirectAfterAccountLoginUrl': SSO_EMBED,
        'redirectAfterAccountCreationUrl': SSO_EMBED,
      });

      // Use iOS User-Agent for real iOS devices
      const USER_AGENT = 'GCM-iOS-5.7.2.1';

      // Manual cookie jar - extract from Set-Cookie and pass to subsequent requests
      let cookieJar = '';

      // Helper to extract cookies from response headers
      const extractCookiesFromResponse = (headers: Record<string, string>): string => {
        // Check various header name cases
        const setCookieHeader = headers['Set-Cookie'] || headers['set-cookie'] ||
                                headers['SET-COOKIE'] || '';
        console.log('[Garmin] Raw Set-Cookie header:', setCookieHeader ? setCookieHeader.substring(0, 500) : 'empty');
        if (!setCookieHeader) return '';

        // Parse cookies - can be a single string or multiple values
        const cookieValues: string[] = [];
        const cookieStr = String(setCookieHeader);

        // Split on comma but not within cookie values (be careful with Expires dates)
        // Improved regex: only split on comma followed by a cookie name (word=)
        const parts = cookieStr.split(/,\s*(?=[A-Za-z_][A-Za-z0-9_]*=)/);
        for (const part of parts) {
          const nameValue = part.split(';')[0].trim();
          if (nameValue.includes('=')) {
            cookieValues.push(nameValue);
          }
        }

        console.log('[Garmin] Extracted cookies:', cookieValues.join(', '));
        return cookieValues.join('; ');
      };

      // Helper to merge cookies
      const addCookies = (newCookies: string) => {
        if (!newCookies) return;
        if (!cookieJar) {
          cookieJar = newCookies;
        } else {
          // Merge, overwriting duplicates
          const existing = new Map(cookieJar.split('; ').map(c => {
            const [k, ...v] = c.split('=');
            return [k, v.join('=')] as [string, string];
          }));
          for (const cookie of newCookies.split('; ')) {
            const [k, ...v] = cookie.split('=');
            existing.set(k, v.join('='));
          }
          cookieJar = Array.from(existing.entries()).map(([k, v]) => `${k}=${v}`).join('; ');
        }
      };

      // Step 1: Set cookies with embed request
      // CapacitorHttp on iOS stores cookies in shared HTTPCookieStorage automatically
      console.log('[Garmin] Setting cookies (via HTTPCookieStorage)...');
      const embedResponse = await CapacitorHttp.get({
        url: `${SSO_EMBED}?${embedParams.toString()}`,
        headers: {
          'User-Agent': USER_AGENT,
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        },
        responseType: 'text',
      });
      console.log('[Garmin] Embed response status:', embedResponse.status);
      // Still extract cookies for logging/debugging, but DON'T set Cookie header
      // URLSession will automatically use cookies from HTTPCookieStorage
      addCookies(extractCookiesFromResponse(embedResponse.headers));
      console.log('[Garmin] Cookies received from embed:', cookieJar ? 'yes' : 'no');

      // Step 2: Get CSRF token from signin page
      // DON'T set Cookie header - let URLSession handle cookies automatically
      console.log('[Garmin] Fetching CSRF token...');
      const signinUrl = `${SSO}/signin?${signinParams.toString()}`;
      const csrfResponse = await CapacitorHttp.get({
        url: signinUrl,
        headers: {
          'User-Agent': USER_AGENT,
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Referer': `${SSO_EMBED}?${embedParams.toString()}`,
          // NO Cookie header - let URLSession use HTTPCookieStorage automatically
        },
        responseType: 'text',
      });

      if (csrfResponse.status !== 200) {
        return { success: false, error: `Failed to load login page (${csrfResponse.status})` };
      }

      addCookies(extractCookiesFromResponse(csrfResponse.headers));
      console.log('[Garmin] Cookie jar after CSRF:', cookieJar ? 'has cookies' : 'empty');

      const csrfHtml = csrfResponse.data as string;

      // Extract CSRF token (exact regex from garth)
      const csrfMatch = csrfHtml.match(/name="_csrf"\s+value="(.+?)"/);
      if (!csrfMatch) {
        console.log('[Garmin] CSRF not found in response');
        return { success: false, error: 'Could not find CSRF token' };
      }
      const csrf = csrfMatch[1];
      console.log('[Garmin] CSRF token found');

      // Step 3: Submit login credentials WITH cookies
      console.log('[Garmin] Submitting credentials...');
      console.log('[Garmin] Cookie jar contents:', cookieJar);

      // Manually build URL-encoded form data string with proper encoding
      const formDataParts = [
        `username=${encodeURIComponent(email)}`,
        `password=${encodeURIComponent(password)}`,
        `embed=true`,
        `_csrf=${encodeURIComponent(csrf)}`,
      ];
      const formDataString = formDataParts.join('&');
      console.log('[Garmin] Form data (redacted password):', formDataString.replace(/password=[^&]+/, 'password=***'));

      // CapacitorHttp on iOS uses URLSession with shared HTTPCookieStorage
      // DON'T set Cookie header - let URLSession handle cookies automatically
      // Setting Cookie header manually can interfere with URLSession's automatic cookie handling
      console.log('[Garmin] POST login - relying on HTTPCookieStorage for cookies...');
      console.log('[Garmin] Expected cookies from previous requests:', cookieJar ? 'yes' : 'no');

      const loginResponse = await CapacitorHttp.post({
        url: signinUrl,
        headers: {
          'User-Agent': USER_AGENT,
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
          'Referer': signinUrl,
          'Origin': 'https://sso.garmin.com',
          // NO Cookie header - URLSession will automatically include cookies from HTTPCookieStorage
        },
        data: formDataString,
        responseType: 'text',
      });

      console.log('[Garmin] Login response status:', loginResponse.status);

      const responseText = loginResponse.data as string;

      // Check page title for success (garth checks for "Success" title)
      const titleMatch = responseText.match(/<title>(.+?)<\/title>/);
      const title = titleMatch ? titleMatch[1] : '';
      console.log('[Garmin] Response title:', title);

      if (title.includes('MFA')) {
        return { success: false, error: 'MFA required - not yet supported in app' };
      }

      if (title !== 'Success') {
        // Check for specific errors
        if (responseText.includes('locked') || responseText.includes('LOCKED')) {
          return { success: false, error: 'Account is locked. Please try again later.' };
        }
        if (title.toLowerCase().includes('error') ||
            responseText.toLowerCase().includes('credentials')) {
          return { success: false, error: 'Invalid email or password' };
        }
        console.log('[Garmin] Unexpected title, response snippet:', responseText.substring(0, 300));
        return { success: false, error: `Login failed - unexpected response: ${title}` };
      }

      // Extract ticket (exact regex from garth: embed\?ticket=([^"]+)")
      const ticketMatch = responseText.match(/embed\?ticket=([^"]+)"/);
      if (!ticketMatch) {
        console.log('[Garmin] No ticket in response');
        return { success: false, error: 'Login succeeded but no ticket received' };
      }

      const ticket = ticketMatch[1];
      console.log('[Garmin] Got ticket:', ticket.substring(0, 10) + '...');

      // Step 3: Exchange ticket for OAuth1 tokens using HMAC-SHA1 signing
      const preAuthUrl = `${OAUTH_URL}/preauthorized`;
      const preAuthQueryParams: Record<string, string> = {
        'ticket': ticket,
        'login-url': GARMIN_SSO_EMBED,
        'accepts-mfa-tokens': 'true',
      };

      console.log('[Garmin] Exchanging ticket for OAuth1...');
      const preAuthHeader = await buildOAuth1Header(
        'GET',
        preAuthUrl,
        preAuthQueryParams,
        OAUTH_CONSUMER_KEY,
        OAUTH_CONSUMER_SECRET
      );

      const preAuthQueryString = Object.entries(preAuthQueryParams)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join('&');

      const oauth1Response = await nativeGetText(
        `${preAuthUrl}?${preAuthQueryString}`,
        {
          'User-Agent': USER_AGENT,
          'Authorization': preAuthHeader,
        }
      );

      console.log('[Garmin] OAuth1 response status:', oauth1Response.status);

      if (oauth1Response.status !== 200) {
        console.log('[Garmin] OAuth1 error response:', oauth1Response.data?.substring(0, 300));
        return { success: false, error: `OAuth1 exchange failed (${oauth1Response.status})` };
      }

      // Parse OAuth1 response
      const oauth1Data = new URLSearchParams(oauth1Response.data);
      const oauth1Token = oauth1Data.get('oauth_token');
      const oauth1Secret = oauth1Data.get('oauth_token_secret');

      if (!oauth1Token || !oauth1Secret) {
        console.log('[Garmin] OAuth1 response:', oauth1Response.data.substring(0, 200));
        return { success: false, error: 'Failed to get OAuth1 tokens' };
      }

      this.oauth1Token = {
        oauth_token: oauth1Token,
        oauth_token_secret: oauth1Secret,
      };

      console.log('[Garmin] Got OAuth1 tokens, exchanging for OAuth2...');

      // Step 4: Exchange OAuth1 for OAuth2 using HMAC-SHA1 signing
      const oauth2Url = `${OAUTH_URL}/exchange/user/2.0`;
      const oauth2Header = await buildOAuth1Header(
        'POST',
        oauth2Url,
        {}, // No additional params for POST body
        OAUTH_CONSUMER_KEY,
        OAUTH_CONSUMER_SECRET,
        oauth1Token,
        oauth1Secret
      );

      const oauth2Response = await nativePost(
        oauth2Url,
        '',
        {
          'User-Agent': USER_AGENT,
          'Authorization': oauth2Header,
          'Content-Type': 'application/x-www-form-urlencoded',
        }
      );

      console.log('[Garmin] OAuth2 response status:', oauth2Response.status);

      if (oauth2Response.status !== 200) {
        console.log('[Garmin] OAuth2 error:', oauth2Response.data);
        return { success: false, error: `OAuth2 exchange failed (${oauth2Response.status})` };
      }

      const oauth2Data = oauth2Response.data as {
        access_token?: string;
        token_type?: string;
        expires_in?: number;
        refresh_token?: string;
        scope?: string;
      };

      console.log('[Garmin] OAuth2 response data:', JSON.stringify(oauth2Data, null, 2));
      console.log('[Garmin] OAuth2 scopes:', oauth2Data.scope);

      if (!oauth2Data.access_token) {
        return { success: false, error: 'No access token received' };
      }

      // Decode JWT to see claims
      try {
        const tokenParts = oauth2Data.access_token.split('.');
        if (tokenParts.length === 3) {
          const payload = JSON.parse(atob(tokenParts[1]));
          console.log('[Garmin] JWT payload:', JSON.stringify(payload, null, 2));
        }
      } catch (e) {
        console.log('[Garmin] Could not decode JWT');
      }

      this.oauth2Token = {
        access_token: oauth2Data.access_token,
        token_type: oauth2Data.token_type || 'Bearer',
        expires_in: oauth2Data.expires_in || 3600,
        refresh_token: oauth2Data.refresh_token,
        expires_at: Date.now() + ((oauth2Data.expires_in || 3600) * 1000),
      };

      // Save tokens
      await this.saveTokens();

      // Also save refresh token securely
      if (oauth2Data.refresh_token) {
        await secureStorage.setRefreshToken(oauth2Data.refresh_token);
      }

      console.log('[Garmin] Login successful! Token expires in', oauth2Data.expires_in, 'seconds');
      return { success: true };

    } catch (error) {
      console.error('[Garmin] Login error:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Login failed' };
    }
  }

  // Sync wellness data - uses direct Garmin API (on-device, no backend)
  async syncViaBackend(days: number = 7, onProgress?: (current: number, total: number) => void): Promise<SyncResult> {
    // Use direct on-device sync (no backend required)
    console.log('[Garmin] Starting direct on-device sync...');
    return this.sync(days, onProgress);
  }

  // Exchange ticket for OAuth1 token (legacy - kept for reference)
  private async exchangeTicketForOAuth1(ticket: string): Promise<LoginResult> {
    try {
      // Consumer credentials should be set via environment variables
      const CONSUMER_KEY = process.env.NEXT_PUBLIC_GARMIN_CONSUMER_KEY || '';
      const CONSUMER_SECRET = process.env.NEXT_PUBLIC_GARMIN_CONSUMER_SECRET || '';

      // Build OAuth1 authorization header for the preauthorized request
      const timestamp = Math.floor(Date.now() / 1000).toString();
      const nonce = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);

      const oauthParams: Record<string, string> = {
        oauth_consumer_key: CONSUMER_KEY,
        oauth_nonce: nonce,
        oauth_signature_method: 'HMAC-SHA1',
        oauth_timestamp: timestamp,
        oauth_version: '1.0',
      };

      // For preauthorized endpoint, signature base string uses empty token secret
      const baseUrl = `${OAUTH_URL}/preauthorized`;
      const queryParams = new URLSearchParams({
        ticket: ticket,
        'login-url': GARMIN_SSO_EMBED,
        'accepts-mfa-tokens': 'true',
      });

      // Create signature (simplified - just use consumer secret with empty token secret)
      // In proper OAuth1, this would be HMAC-SHA1 of the signature base string
      const signatureKey = `${encodeURIComponent(CONSUMER_SECRET)}&`;

      // For simplicity, we'll try the request without signature first
      // Garmin's preauthorized endpoint may not require full OAuth1 signing
      const url = `${baseUrl}?${queryParams.toString()}`;

      console.log('OAuth1 exchange URL:', url);

      const response = await nativeGetText(url, {
        'User-Agent': 'com.garmin.android.apps.connectmobile',
        'Accept': '*/*',
      });

      console.log('OAuth1 response status:', response.status);
      console.log('OAuth1 response data:', response.data?.substring(0, 200));

      if (response.status !== 200) {
        console.error('OAuth1 failed with status:', response.status);
        return { success: false, error: `OAuth1 failed (${response.status})` };
      }

      const text = response.data;

      // Parse the response - it should be URL-encoded params
      const params = new URLSearchParams(text);

      const oauth_token = params.get('oauth_token');
      const oauth_token_secret = params.get('oauth_token_secret');

      console.log('OAuth1 tokens received:', !!oauth_token, !!oauth_token_secret);

      if (!oauth_token || !oauth_token_secret) {
        // Maybe it's JSON?
        try {
          const jsonData = JSON.parse(text);
          if (jsonData.oauth_token && jsonData.oauth_token_secret) {
            this.oauth1Token = {
              oauth_token: jsonData.oauth_token,
              oauth_token_secret: jsonData.oauth_token_secret,
            };
            return { success: true };
          }
        } catch {
          // Not JSON
        }

        console.error('OAuth1 response format unexpected:', text.substring(0, 200));
        return { success: false, error: 'Invalid OAuth1 response format' };
      }

      this.oauth1Token = { oauth_token, oauth_token_secret };
      return { success: true };
    } catch (error) {
      console.error('OAuth1 exchange error:', error);
      return { success: false, error: 'OAuth1 exchange failed: ' + (error instanceof Error ? error.message : 'unknown') };
    }
  }

  // Exchange OAuth1 for OAuth2 token
  private async exchangeOAuth1ForOAuth2(): Promise<LoginResult> {
    if (!this.oauth1Token) {
      return { success: false, error: 'No OAuth1 token available' };
    }

    try {
      console.log('[Garmin] OAuth2 exchange starting...');

      // Use HMAC-SHA1 signing (same as login method)
      const oauth2Url = `${OAUTH_URL}/exchange/user/2.0`;
      const oauth2Header = await buildOAuth1Header(
        'POST',
        oauth2Url,
        {},
        OAUTH_CONSUMER_KEY,
        OAUTH_CONSUMER_SECRET,
        this.oauth1Token.oauth_token,
        this.oauth1Token.oauth_token_secret
      );

      const response = await nativePost(oauth2Url, '', {
        'User-Agent': 'com.garmin.android.apps.connectmobile',
        'Authorization': oauth2Header,
        'Content-Type': 'application/x-www-form-urlencoded',
      });

      console.log('OAuth2 response status:', response.status);

      if (response.status !== 200) {
        console.error('OAuth2 failed:', response.status, response.data);
        return { success: false, error: `OAuth2 failed (${response.status})` };
      }

      const data = response.data as { access_token?: string; token_type?: string; expires_in?: number; refresh_token?: string };

      if (!data.access_token) {
        console.error('No access token in response:', data);
        return { success: false, error: 'No access token received' };
      }

      this.oauth2Token = {
        access_token: data.access_token,
        token_type: data.token_type || 'Bearer',
        expires_in: data.expires_in || 3600,
        refresh_token: data.refresh_token,
        expires_at: Date.now() + ((data.expires_in || 3600) * 1000),
      };

      console.log('OAuth2 token received successfully');
      return { success: true };
    } catch (error) {
      console.error('OAuth2 exchange error:', error);
      return { success: false, error: 'OAuth2 exchange failed: ' + (error instanceof Error ? error.message : 'unknown') };
    }
  }

  /**
   * Check if the current token is expired or close to expiry.
   * Returns true if token is expired or will expire within TOKEN_EXPIRY_BUFFER_MS (5 minutes).
   */
  private isTokenExpired(): boolean {
    if (!this.oauth2Token) {
      return true;
    }
    if (!this.oauth2Token.expires_at) {
      // No expiry time set, assume valid
      return false;
    }
    // Token is "expired" if it expires within the buffer period
    return Date.now() >= (this.oauth2Token.expires_at - TOKEN_EXPIRY_BUFFER_MS);
  }

  /**
   * Ensure we have a valid token before making API requests.
   * Uses a refresh queue to prevent multiple simultaneous refresh calls.
   * @returns The valid access token
   * @throws Error if token refresh fails
   */
  private async ensureValidToken(): Promise<string> {
    if (!this.oauth2Token) {
      throw new Error('Not authenticated');
    }

    if (this.isTokenExpired()) {
      // If there's already a refresh in progress, wait for it
      if (!this.refreshPromise) {
        this.refreshPromise = this.refreshToken()
          .finally(() => {
            this.refreshPromise = null;
          });
      }
      await this.refreshPromise;
    }

    if (!this.oauth2Token) {
      throw new Error('Token refresh failed - not authenticated');
    }

    return this.oauth2Token.access_token;
  }

  /**
   * Helper to retry network requests with exponential backoff.
   * @param fn The async function to retry
   * @param retries Number of retry attempts (default: 3)
   * @param delay Initial delay in ms between retries (default: 1000ms)
   * @returns The result of the function
   * @throws The last error if all retries fail
   */
  private async fetchWithRetry<T>(
    fn: () => Promise<T>,
    retries: number = DEFAULT_RETRY_COUNT,
    delay: number = DEFAULT_RETRY_DELAY_MS
  ): Promise<T> {
    let lastError: Error | undefined;

    for (let attempt = 0; attempt < retries; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        console.warn(`Retry attempt ${attempt + 1}/${retries} failed:`, lastError.message);

        // Don't wait after the last attempt
        if (attempt < retries - 1) {
          // Exponential backoff: delay * (attempt + 1)
          const waitTime = delay * (attempt + 1);
          console.log(`Waiting ${waitTime}ms before next retry...`);
          await new Promise(resolve => setTimeout(resolve, waitTime));
        }
      }
    }

    throw lastError || new Error('Max retries exceeded');
  }

  /**
   * Make authenticated API request with automatic token refresh and retry logic.
   * @param endpoint The API endpoint to call
   * @param useRetry Whether to use retry logic for network failures (default: true)
   * @returns The response data or null if request fails
   */
  private async apiRequest<T>(endpoint: string, useRetry: boolean = true): Promise<T | null> {
    const makeRequest = async (): Promise<T | null> => {
      // Ensure we have a valid token before making the request
      const accessToken = await this.ensureValidToken();

      // Use connectapi.garmin.com directly (like garth library does)
      const apiUrl = `${CONNECT_API}${endpoint}`;
      console.log(`[Garmin] API Request: ${apiUrl}`);
      console.log(`[Garmin] Token present: ${!!accessToken}, length: ${accessToken?.length || 0}`);

      const response = await nativeGet(apiUrl, {
        'Authorization': `Bearer ${accessToken}`,
        'User-Agent': 'com.garmin.android.apps.connectmobile',
        'Accept': 'application/json',
        'DI-Units': 'metric',
        'NK': 'NT',
      });

      console.log(`[Garmin] Response status: ${response.status}`);

      if (response.status === 401) {
        // Token expired unexpectedly, force refresh and retry once
        console.log('Received 401, forcing token refresh...');
        this.refreshPromise = this.refreshToken().finally(() => {
          this.refreshPromise = null;
        });
        await this.refreshPromise;

        // Retry with new token
        const newToken = await this.ensureValidToken();
        const retryResponse = await nativeGet(apiUrl, {
          'Authorization': `Bearer ${newToken}`,
          'User-Agent': 'com.garmin.android.apps.connectmobile',
          'Accept': 'application/json',
          'DI-Units': 'metric',
          'NK': 'NT',
        });

        if (retryResponse.status !== 200) {
          console.error(`API request failed after token refresh: ${retryResponse.status}`);
          return null;
        }

        return retryResponse.data as T;
      }

      if (response.status !== 200) {
        console.error(`API request failed: ${response.status}`);
        return null;
      }

      return response.data as T;
    };

    try {
      if (useRetry) {
        return await this.fetchWithRetry(makeRequest);
      }
      return await makeRequest();
    } catch (error) {
      console.error('API request error:', error);
      return null;
    }
  }

  /**
   * Refresh the OAuth2 token.
   * This method is called when the token is expired or about to expire.
   */
  private async refreshToken(): Promise<void> {
    console.log('Refreshing OAuth2 token...');

    try {
      const result = await this.exchangeOAuth1ForOAuth2();
      if (result.success) {
        await this.saveTokens();
        console.log('Token refresh successful');
      } else {
        console.error('Token refresh failed:', result.error);
        throw new Error(result.error || 'Token refresh failed');
      }
    } catch (error) {
      console.error('Token refresh error:', error);
      throw error;
    }
  }

  // Fetch sleep data
  async fetchSleep(date: string): Promise<SleepData | null> {
    // Use the simpler dailySleep endpoint (works without displayName)
    const data = await this.apiRequest<Record<string, unknown>>(
      `/wellness-service/wellness/dailySleep?date=${date}`
    );

    console.log(`[Garmin] Sleep API response for ${date}:`, JSON.stringify(data, null, 2));

    return this.parseSleepData(date, data);
  }

  // Helper to parse sleep data response
  private parseSleepData(date: string, data: Record<string, unknown> | null): SleepData | null {
    if (!data) return null;

    const deep = (data.deepSleepSeconds as number) || 0;
    const light = (data.lightSleepSeconds as number) || 0;
    const rem = (data.remSleepSeconds as number) || 0;
    const awake = (data.awakeSleepSeconds as number) || 0;
    const total = deep + light + rem;
    const totalInBed = total + awake;
    const efficiency = totalInBed > 0 ? (total / totalInBed) * 100 : 0;

    const result = {
      date,
      sleep_start: data.sleepStartTimestampLocal as string || null,
      sleep_end: data.sleepEndTimestampLocal as string || null,
      total_sleep_seconds: total,
      deep_sleep_seconds: deep,
      light_sleep_seconds: light,
      rem_sleep_seconds: rem,
      awake_seconds: awake,
      sleep_score: (data.sleepScores as Record<string, Record<string, number>>)?.overall?.value || null,
      sleep_efficiency: Math.round(efficiency * 10) / 10,
      avg_spo2: data.avgOxygenSaturation as number || null,
      avg_respiration: data.avgSleepRespirationValue as number || null,
    };
    console.log(`[Garmin] Sleep parsed result for ${date}:`, JSON.stringify(result, null, 2));
    return result;
  }

  // Fetch HRV data
  async fetchHRV(date: string): Promise<HRVData | null> {
    const data = await this.apiRequest<Record<string, unknown>>(
      `/hrv-service/hrv/${date}`
    );

    console.log(`[Garmin] HRV API response for ${date}:`, JSON.stringify(data, null, 2));

    if (!data) return null;

    const summary = (data.hrvSummary || {}) as Record<string, unknown>;
    const baseline = (summary.baseline || {}) as Record<string, number>;

    return {
      date,
      hrv_weekly_avg: summary.weeklyAvg as number || null,
      hrv_last_night_avg: summary.lastNightAvg as number || null,
      hrv_last_night_5min_high: summary.lastNight5MinHigh as number || null,
      hrv_status: summary.status as string || null,
      baseline_low: baseline.lowUpper || null,
      baseline_balanced_low: baseline.balancedLow || null,
      baseline_balanced_upper: baseline.balancedUpper || null,
    };
  }

  // Fetch stress data
  async fetchStress(date: string): Promise<StressData | null> {
    // Fetch stress data
    const stressData = await this.apiRequest<Record<string, unknown>>(
      `/wellness-service/wellness/dailyStress/${date}`
    );

    // Fetch body battery data
    const bbResult = await this.apiRequest<Array<Record<string, unknown>>>(
      `/wellness-service/wellness/bodyBattery/reports/daily?startDate=${date}&endDate=${date}`
    );
    const bbData = bbResult && bbResult.length > 0 ? bbResult[0] : null;

    console.log(`[Garmin] Stress API response for ${date}:`, JSON.stringify(stressData, null, 2));
    console.log(`[Garmin] BodyBattery API response for ${date}:`, JSON.stringify(bbData, null, 2));

    if (!stressData && !bbData) return null;

    return {
      date,
      avg_stress_level: stressData?.overallStressLevel as number || null,
      max_stress_level: stressData?.maxStressLevel as number || null,
      rest_stress_duration: (stressData?.restStressDuration as number) || 0,
      low_stress_duration: (stressData?.lowStressDuration as number) || 0,
      medium_stress_duration: (stressData?.mediumStressDuration as number) || 0,
      high_stress_duration: (stressData?.highStressDuration as number) || 0,
      body_battery_charged: bbData?.charged as number || null,
      body_battery_drained: bbData?.drained as number || null,
      body_battery_high: bbData?.highBB as number || null,
      body_battery_low: bbData?.lowBB as number || null,
    };
  }

  // Fetch activity data
  async fetchActivity(date: string): Promise<ActivityData | null> {
    // Get displayName for user-specific endpoints
    const displayName = await this.fetchDisplayName();

    // Fetch steps
    const stepsData = await this.apiRequest<Array<Record<string, unknown>>>(
      `/usersummary-service/stats/steps/daily/${date}/${date}`
    );
    const daySteps = stepsData && stepsData.length > 0 ? stepsData[0] : null;

    // Fetch daily summary (requires displayName)
    let summaryData: Record<string, unknown> | null = null;
    if (displayName) {
      summaryData = await this.apiRequest<Record<string, unknown>>(
        `/usersummary-service/usersummary/daily/${displayName}?calendarDate=${date}`
      );
    } else {
      // Fallback without displayName
      summaryData = await this.apiRequest<Record<string, unknown>>(
        `/usersummary-service/usersummary/daily?calendarDate=${date}`
      );
    }

    console.log(`[Garmin] Steps API response for ${date}:`, JSON.stringify(daySteps, null, 2));
    console.log(`[Garmin] Summary API response for ${date}:`, JSON.stringify(summaryData, null, 2));

    let steps = (daySteps?.totalSteps as number) || 0;
    let stepsGoal = (daySteps?.stepGoal as number) || 10000;
    let totalDistanceM = (daySteps?.totalDistance as number) || 0;

    // Use summary data as fallback
    if (summaryData) {
      if (steps === 0) steps = (summaryData.totalSteps as number) || 0;
      if (stepsGoal === 10000) stepsGoal = (summaryData.dailyStepGoal as number) || 10000;
      if (totalDistanceM === 0) totalDistanceM = (summaryData.totalDistanceMeters as number) || 0;
    }

    const activeCalories = summaryData?.activeKilocalories as number || null;
    const totalCalories = summaryData?.totalKilocalories as number || null;
    const floorsClimbed = (summaryData?.floorsAscended as number) || 0;
    const moderate = (summaryData?.moderateIntensityMinutes as number) || 0;
    const vigorous = (summaryData?.vigorousIntensityMinutes as number) || 0;
    const intensityMinutes = moderate + vigorous;

    if (steps === 0 && activeCalories === null) return null;

    return {
      date,
      steps,
      steps_goal: stepsGoal,
      total_distance_m: totalDistanceM,
      active_calories: activeCalories,
      total_calories: totalCalories,
      intensity_minutes: intensityMinutes,
      floors_climbed: floorsClimbed,
    };
  }

  // Fetch resting heart rate
  async fetchRestingHeartRate(date: string): Promise<number | null> {
    // Get displayName for user-specific endpoints
    const displayName = await this.fetchDisplayName();

    let data: Record<string, unknown> | null = null;
    if (displayName) {
      data = await this.apiRequest<Record<string, unknown>>(
        `/wellness-service/wellness/dailyHeartRate/${displayName}?date=${date}`
      );
    } else {
      // Fallback without displayName
      data = await this.apiRequest<Record<string, unknown>>(
        `/wellness-service/wellness/dailyHeartRate?date=${date}`
      );
    }

    console.log(`[Garmin] HeartRate API response for ${date}:`, JSON.stringify(data, null, 2));

    if (!data) return null;
    const rhr = data.restingHeartRate as number;
    return rhr && rhr > 0 ? rhr : null;
  }

  // Fetch user's display name (required for API calls)
  async fetchDisplayName(): Promise<string | null> {
    if (this.displayName) {
      return this.displayName;
    }

    console.log('[Garmin] Fetching user display name...');

    // Try social profile first
    const socialProfile = await this.apiRequest<{ displayName?: string; userName?: string }>(
      '/userprofile-service/socialProfile'
    );

    if (socialProfile?.displayName) {
      this.displayName = socialProfile.displayName;
      console.log('[Garmin] Got displayName from socialProfile:', this.displayName);
      return this.displayName;
    }

    // Fallback to personal profile
    const personalProfile = await this.apiRequest<{ displayName?: string; userName?: string }>(
      '/userprofile-service/userprofile/personal'
    );

    if (personalProfile?.displayName) {
      this.displayName = personalProfile.displayName;
      console.log('[Garmin] Got displayName from personal profile:', this.displayName);
      return this.displayName;
    }

    // Try to extract from JWT token
    if (this.oauth2Token?.access_token) {
      try {
        const tokenParts = this.oauth2Token.access_token.split('.');
        if (tokenParts.length === 3) {
          const payload = JSON.parse(atob(tokenParts[1]));
          if (payload.sub) {
            this.displayName = payload.sub;
            console.log('[Garmin] Using sub from JWT as displayName:', this.displayName);
            return this.displayName;
          }
        }
      } catch (e) {
        console.log('[Garmin] Could not extract displayName from JWT');
      }
    }

    console.warn('[Garmin] Could not get displayName');
    return null;
  }

  // Debug: fetch user profile to verify API access
  async debugFetchProfile(): Promise<void> {
    console.log('[Garmin] DEBUG: Fetching user profile...');

    // Try different endpoints to see what works
    const endpoints = [
      '/userprofile-service/socialProfile',
      '/userprofile-service/userprofile/personal',
      '/device-service/deviceservice/device-info/all',
    ];

    for (const endpoint of endpoints) {
      const data = await this.apiRequest<Record<string, unknown>>(endpoint);
      console.log(`[Garmin] DEBUG ${endpoint}:`, JSON.stringify(data, null, 2));
    }
  }

  // Fetch all wellness data for a date
  async fetchWellness(date: string): Promise<WellnessRecord> {
    console.log(`Fetching wellness data for ${date}...`);

    const [sleep, hrv, stress, activity, rhr] = await Promise.all([
      this.fetchSleep(date),
      this.fetchHRV(date),
      this.fetchStress(date),
      this.fetchActivity(date),
      this.fetchRestingHeartRate(date),
    ]);

    return {
      date,
      wellness: {
        date,
        fetched_at: new Date().toISOString(),
        resting_heart_rate: rhr,
        training_readiness_score: null,
      },
      sleep,
      hrv,
      stress,
      activity,
    };
  }

  // Sync wellness data for multiple days
  async sync(days: number = 1, onProgress?: (current: number, total: number) => void): Promise<SyncResult> {
    try {
      const isAuth = await this.isAuthenticated();
      if (!isAuth) {
        return { success: false, daysProcessed: 0, error: 'Not authenticated' };
      }

      // DEBUG: Decode and log the cached JWT to see what scopes/claims it has
      if (this.oauth2Token?.access_token) {
        console.log('[Garmin] DEBUG: Analyzing cached token...');
        try {
          const tokenParts = this.oauth2Token.access_token.split('.');
          if (tokenParts.length === 3) {
            const header = JSON.parse(atob(tokenParts[0]));
            const payload = JSON.parse(atob(tokenParts[1]));
            console.log('[Garmin] JWT Header:', JSON.stringify(header, null, 2));
            console.log('[Garmin] JWT Payload:', JSON.stringify(payload, null, 2));
            console.log('[Garmin] JWT scopes:', payload.scope || payload.scp || 'NO SCOPES FOUND');
          }
        } catch (e) {
          console.log('[Garmin] Could not decode cached JWT:', e);
        }
      }

      // Initialize database
      await db.initialize();

      // DEBUG: Test API access first
      await this.debugFetchProfile();

      // Fetch and cache displayName before making API calls
      const displayName = await this.fetchDisplayName();
      console.log('[Garmin] Using displayName for API calls:', displayName);

      const today = new Date();
      console.log('[Garmin] DEBUG: Today date object:', today.toISOString());
      let processed = 0;

      for (let i = 0; i < days; i++) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        const dateStr = date.toISOString().split('T')[0];

        try {
          const wellness = await this.fetchWellness(dateStr);
          await db.saveWellness(wellness);
          processed++;

          if (onProgress) {
            onProgress(processed, days);
          }
        } catch (error) {
          console.error(`Failed to fetch ${dateStr}:`, error);
        }
      }

      return { success: true, daysProcessed: processed };
    } catch (error) {
      console.error('Sync error:', error);
      return { success: false, daysProcessed: 0, error: error instanceof Error ? error.message : 'Sync failed' };
    }
  }
}

// Singleton instance
export const garmin = new GarminService();
