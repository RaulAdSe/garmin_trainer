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

// Use native HTTP on iOS/Android, fetch on web
const isNative = Capacitor.isNativePlatform();

// Native HTTP wrapper that falls back to fetch on web
async function nativeGet(url: string, headers?: Record<string, string>): Promise<{ data: unknown; status: number }> {
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
}

async function nativePost(
  url: string,
  body?: string | Record<string, unknown>,
  headers?: Record<string, string>
): Promise<{ data: unknown; status: number; headers: Record<string, string> }> {
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
}

async function nativeGetText(url: string, headers?: Record<string, string>): Promise<{ data: string; status: number }> {
  if (isNative) {
    const response: HttpResponse = await CapacitorHttp.get({
      url,
      headers: headers || {},
      responseType: 'text',
    });
    return { data: response.data as string, status: response.status };
  } else {
    const response = await fetch(url, { headers, credentials: 'include' });
    const data = await response.text();
    return { data, status: response.status };
  }
}

// Garmin Connect endpoints
const GARMIN_SSO_EMBED = 'https://sso.garmin.com/sso/embed';
const GC_MODERN = 'https://connect.garmin.com/modern';
const SIGNIN_URL = 'https://sso.garmin.com/sso/signin';
const OAUTH_URL = 'https://connectapi.garmin.com/oauth-service/oauth';
const CONNECT_API = 'https://connect.garmin.com';

// Token storage keys
const TOKEN_KEY = 'garmin_tokens';

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
  private isRefreshing = false;
  private refreshQueue: Array<() => void> = [];

  constructor() {
    this.loadTokens();
  }

  // Load tokens from Preferences
  private async loadTokens(): Promise<void> {
    try {
      const { value } = await Preferences.get({ key: TOKEN_KEY });
      if (value) {
        const tokens: StoredTokens = JSON.parse(value);
        this.oauth1Token = tokens.oauth1;
        this.oauth2Token = tokens.oauth2;
      }
    } catch (error) {
      console.error('Failed to load tokens:', error);
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
  }

  // Check if authenticated
  async isAuthenticated(): Promise<boolean> {
    await this.loadTokens();
    return this.oauth2Token !== null;
  }

  // Login and sync via backend API (training-analyzer)
  // The backend uses Python's garminconnect library which properly handles authentication
  async login(email: string, password: string): Promise<LoginResult> {
    try {
      // Store credentials for sync (not sent anywhere yet)
      await Preferences.set({ key: 'garmin_email', value: email });
      // Note: In production, use secure storage for password
      await Preferences.set({ key: 'garmin_password', value: password });

      // Mark as "authenticated" - actual auth happens during sync
      this.oauth2Token = {
        access_token: 'pending_sync',
        token_type: 'Bearer',
        expires_in: 3600,
        expires_at: Date.now() + 3600000,
      };
      await this.saveTokens();

      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, error: error instanceof Error ? error.message : 'Failed to save credentials' };
    }
  }

  // Sync via backend API
  async syncViaBackend(days: number = 7, onProgress?: (current: number, total: number) => void): Promise<SyncResult> {
    try {
      const { value: email } = await Preferences.get({ key: 'garmin_email' });
      const { value: password } = await Preferences.get({ key: 'garmin_password' });

      if (!email || !password) {
        return { success: false, daysProcessed: 0, error: 'Not authenticated' };
      }

      // Try to call the training-analyzer backend API
      // Default to localhost for development, can be configured for production
      const backendUrl = 'http://localhost:8000';

      console.log('Syncing via backend API...');
      onProgress?.(0, days);

      const response = await nativePost(
        `${backendUrl}/api/v1/garmin/sync-wellness`,
        JSON.stringify({ email, password, days }),
        {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        }
      );

      if (response.status !== 200) {
        const errorData = response.data as { detail?: string };
        const errorMsg = errorData?.detail || `Backend sync failed (${response.status})`;

        // If backend is not available, fall back to direct sync attempt
        if (response.status === 0 || errorMsg.includes('fetch')) {
          console.log('Backend not available, attempting direct sync...');
          return this.sync(days, onProgress);
        }

        return { success: false, daysProcessed: 0, error: errorMsg };
      }

      const syncData = response.data as { success: boolean; synced_count: number; message: string };
      console.log('Sync complete, fetching wellness data...');
      onProgress?.(Math.floor(days * 0.8), days);

      // Now fetch the wellness data from the backend and save it locally
      const historyResponse = await nativeGet(`${backendUrl}/api/v1/garmin/wellness-history?days=${days}`, {
        'Accept': 'application/json',
      });

      if (historyResponse.status === 200) {
        const historyData = historyResponse.data as {
          success: boolean;
          days: Array<{
            date: string;
            resting_heart_rate: number | null;
            sleep_hours: number | null;
            sleep_score: number | null;
            deep_sleep_pct: number | null;
            rem_sleep_pct: number | null;
            hrv: number | null;
            hrv_status: string | null;
            body_battery_high: number | null;
            body_battery_low: number | null;
            body_battery_charged: number | null;
            body_battery_drained: number | null;
            avg_stress: number | null;
            steps: number | null;
            steps_goal: number | null;
            active_calories: number | null;
            intensity_minutes: number | null;
          }>;
        };

        if (historyData.success && historyData.days) {
          console.log(`Saving ${historyData.days.length} days to local storage...`);
          await db.initialize();

          for (const day of historyData.days) {
            const sleepSeconds = day.sleep_hours ? day.sleep_hours * 3600 : 0;
            const deepPct = day.deep_sleep_pct || 0;
            const remPct = day.rem_sleep_pct || 0;

            await db.saveWellness({
              date: day.date,
              wellness: {
                date: day.date,
                fetched_at: new Date().toISOString(),
                resting_heart_rate: day.resting_heart_rate,
                training_readiness_score: null,
              },
              sleep: sleepSeconds > 0 ? {
                date: day.date,
                sleep_start: null,
                sleep_end: null,
                total_sleep_seconds: sleepSeconds,
                deep_sleep_seconds: Math.round(sleepSeconds * deepPct / 100),
                light_sleep_seconds: Math.round(sleepSeconds * (100 - deepPct - remPct) / 100),
                rem_sleep_seconds: Math.round(sleepSeconds * remPct / 100),
                awake_seconds: 0,
                sleep_score: day.sleep_score,
                sleep_efficiency: null,
                avg_spo2: null,
                avg_respiration: null,
              } : null,
              hrv: day.hrv ? {
                date: day.date,
                hrv_weekly_avg: null,
                hrv_last_night_avg: day.hrv,
                hrv_last_night_5min_high: null,
                hrv_status: day.hrv_status,
                baseline_low: null,
                baseline_balanced_low: null,
                baseline_balanced_upper: null,
              } : null,
              stress: day.body_battery_charged ? {
                date: day.date,
                avg_stress_level: day.avg_stress,
                max_stress_level: null,
                rest_stress_duration: 0,
                low_stress_duration: 0,
                medium_stress_duration: 0,
                high_stress_duration: 0,
                body_battery_charged: day.body_battery_charged,
                body_battery_drained: day.body_battery_drained,
                body_battery_high: day.body_battery_high,
                body_battery_low: day.body_battery_low,
              } : null,
              activity: day.steps ? {
                date: day.date,
                steps: day.steps,
                steps_goal: day.steps_goal || 10000,
                total_distance_m: 0,
                active_calories: day.active_calories,
                total_calories: null,
                intensity_minutes: day.intensity_minutes || 0,
                floors_climbed: 0,
              } : null,
            });
          }
          console.log('Local storage updated successfully');
        }
      }

      onProgress?.(days, days);

      return {
        success: syncData.success,
        daysProcessed: syncData.synced_count,
        error: syncData.success ? undefined : syncData.message,
      };
    } catch (error) {
      console.error('Backend sync error:', error);

      // Fall back to direct sync
      console.log('Falling back to direct sync...');
      return this.sync(days, onProgress);
    }
  }

  // Exchange ticket for OAuth1 token
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
      const CONSUMER_KEY = process.env.NEXT_PUBLIC_GARMIN_CONSUMER_KEY || '';

      // Build simple OAuth1 header with the token
      const timestamp = Math.floor(Date.now() / 1000).toString();
      const nonce = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);

      // For the exchange endpoint, we need OAuth1 header with token
      const authHeader = [
        `OAuth oauth_consumer_key="${CONSUMER_KEY}"`,
        `oauth_token="${this.oauth1Token.oauth_token}"`,
        `oauth_signature_method="HMAC-SHA1"`,
        `oauth_timestamp="${timestamp}"`,
        `oauth_nonce="${nonce}"`,
        `oauth_version="1.0"`,
        `oauth_signature="placeholder"`,
      ].join(', ');

      console.log('OAuth2 exchange starting...');

      const response = await nativePost(`${OAUTH_URL}/exchange/user/2.0`, '', {
        'User-Agent': 'com.garmin.android.apps.connectmobile',
        'Authorization': authHeader,
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

  // Make authenticated API request
  private async apiRequest<T>(endpoint: string): Promise<T | null> {
    if (!this.oauth2Token) {
      throw new Error('Not authenticated');
    }

    // Check if token needs refresh
    if (this.oauth2Token.expires_at && Date.now() >= this.oauth2Token.expires_at) {
      await this.refreshToken();
    }

    try {
      const response = await nativeGet(`${CONNECT_API}${endpoint}`, {
        'Authorization': `Bearer ${this.oauth2Token.access_token}`,
        'User-Agent': 'com.garmin.android.apps.connectmobile',
        'Accept': 'application/json',
      });

      if (response.status === 401) {
        // Token expired, try refresh
        await this.refreshToken();
        return this.apiRequest(endpoint);
      }

      if (response.status !== 200) {
        console.error(`API request failed: ${response.status}`);
        return null;
      }

      return response.data as T;
    } catch (error) {
      console.error('API request error:', error);
      return null;
    }
  }

  // Refresh OAuth2 token
  private async refreshToken(): Promise<void> {
    if (this.isRefreshing) {
      // Wait for current refresh to complete
      return new Promise((resolve) => {
        this.refreshQueue.push(resolve);
      });
    }

    this.isRefreshing = true;

    try {
      const result = await this.exchangeOAuth1ForOAuth2();
      if (result.success) {
        await this.saveTokens();
      }
    } finally {
      this.isRefreshing = false;
      // Notify waiting requests
      this.refreshQueue.forEach((resolve) => resolve());
      this.refreshQueue = [];
    }
  }

  // Fetch sleep data
  async fetchSleep(date: string): Promise<SleepData | null> {
    const data = await this.apiRequest<Record<string, unknown>>(
      `/wellness-service/wellness/dailySleep?date=${date}`
    );

    if (!data) return null;

    const deep = (data.deepSleepSeconds as number) || 0;
    const light = (data.lightSleepSeconds as number) || 0;
    const rem = (data.remSleepSeconds as number) || 0;
    const awake = (data.awakeSleepSeconds as number) || 0;
    const total = deep + light + rem;
    const totalInBed = total + awake;
    const efficiency = totalInBed > 0 ? (total / totalInBed) * 100 : 0;

    return {
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
  }

  // Fetch HRV data
  async fetchHRV(date: string): Promise<HRVData | null> {
    const data = await this.apiRequest<Record<string, unknown>>(
      `/hrv-service/hrv/${date}`
    );

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
    // Fetch steps
    const stepsData = await this.apiRequest<Array<Record<string, unknown>>>(
      `/usersummary-service/stats/steps/daily/${date}/${date}`
    );
    const daySteps = stepsData && stepsData.length > 0 ? stepsData[0] : null;

    // Fetch daily summary
    const summaryData = await this.apiRequest<Record<string, unknown>>(
      `/usersummary-service/usersummary/daily/${date}`
    );

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
    const data = await this.apiRequest<Record<string, unknown>>(
      `/wellness-service/wellness/dailyHeartRate?date=${date}`
    );

    if (!data) return null;
    const rhr = data.restingHeartRate as number;
    return rhr && rhr > 0 ? rhr : null;
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

      // Initialize database
      await db.initialize();

      const today = new Date();
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
