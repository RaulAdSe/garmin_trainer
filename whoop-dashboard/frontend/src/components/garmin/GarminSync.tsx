'use client';

import { useState, useEffect, useCallback } from 'react';
import { garmin } from '@/services/garmin';

interface GarminSyncProps {
  onSyncComplete?: (result: GarminSyncResponse) => void;
  onClose?: () => void;
  className?: string;
}

interface SyncedDay {
  date: string;
  has_sleep: boolean;
  has_hrv: boolean;
  has_stress: boolean;
  has_activity: boolean;
}

export interface GarminSyncResponse {
  success: boolean;
  synced_count: number;
  message: string;
  new_days: number;
  updated_days: number;
  synced_days: SyncedDay[];
}

type SyncState = 'idle' | 'syncing' | 'success' | 'error';

const REMEMBER_EMAIL_KEY = 'garmin-wellness-sync-email';

export function GarminSync({ onSyncComplete, onClose, className }: GarminSyncProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [days, setDays] = useState(30);
  const [rememberEmail, setRememberEmail] = useState(false);
  const [syncState, setSyncState] = useState<SyncState>('idle');
  const [syncProgress, setSyncProgress] = useState<{ current: number; total: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GarminSyncResponse | null>(null);

  useEffect(() => {
    const savedEmail = localStorage.getItem(REMEMBER_EMAIL_KEY);
    if (savedEmail) {
      setEmail(savedEmail);
      setRememberEmail(true);
    }
  }, []);

  useEffect(() => {
    if (rememberEmail && email) {
      localStorage.setItem(REMEMBER_EMAIL_KEY, email);
    } else if (!rememberEmail) {
      localStorage.removeItem(REMEMBER_EMAIL_KEY);
    }
  }, [rememberEmail, email]);

  const handleSync = useCallback(async () => {
    if (!email || !password) {
      setError('Please enter your Garmin Connect email and password');
      return;
    }

    setSyncState('syncing');
    setError(null);
    setResult(null);
    setSyncProgress({ current: 0, total: days });

    try {
      // Step 1: Login to Garmin
      const loginResult = await garmin.login(email, password);
      if (!loginResult.success) {
        throw new Error(loginResult.error || 'Login failed');
      }

      // Step 2: Sync wellness data
      const syncResult = await garmin.sync(days, (current, total) => {
        setSyncProgress({ current, total });
      });

      if (!syncResult.success) {
        throw new Error(syncResult.error || 'Sync failed');
      }

      // Build response
      const data: GarminSyncResponse = {
        success: true,
        synced_count: syncResult.daysProcessed,
        message: `Successfully synced ${syncResult.daysProcessed} days of wellness data`,
        new_days: syncResult.daysProcessed,
        updated_days: 0,
        synced_days: [],
      };

      setResult(data);
      setSyncState('success');
      setPassword('');
      setSyncProgress(null);

      if (onSyncComplete) {
        onSyncComplete(data);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to sync wellness data';
      setError(errorMessage);
      setSyncState('error');
      setSyncProgress(null);
    }
  }, [email, password, days, onSyncComplete]);

  const handleReset = useCallback(() => {
    setSyncState('idle');
    setError(null);
    setResult(null);
  }, []);

  const isSubmitDisabled = !email || !password || syncState === 'syncing';

  return (
    <div className={`bg-zinc-900 rounded-2xl border border-zinc-800 ${className || ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-teal-500/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Garmin Connect</h2>
            <p className="text-sm text-zinc-500">Sync your wellness data</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-white transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Content */}
      <div className="p-6">
        {syncState === 'success' && result ? (
          <SyncResult result={result} onReset={handleReset} onClose={onClose} />
        ) : (
          <form onSubmit={(e) => { e.preventDefault(); handleSync(); }} className="space-y-4">
            {/* Email */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-zinc-400">Garmin Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                autoComplete="email"
                disabled={syncState === 'syncing'}
                className="w-full px-4 py-2.5 rounded-xl bg-zinc-800 border border-zinc-700 text-white placeholder-zinc-500 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none transition-colors disabled:opacity-50"
              />
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-zinc-400">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Your Garmin Connect password"
                autoComplete="current-password"
                disabled={syncState === 'syncing'}
                className="w-full px-4 py-2.5 rounded-xl bg-zinc-800 border border-zinc-700 text-white placeholder-zinc-500 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none transition-colors disabled:opacity-50"
              />
            </div>

            {/* Days */}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-zinc-400">Days to sync</label>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                disabled={syncState === 'syncing'}
                className="w-full px-4 py-2.5 rounded-xl bg-zinc-800 border border-zinc-700 text-white focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none transition-colors disabled:opacity-50"
              >
                <option value={7}>Last 7 days</option>
                <option value={14}>Last 14 days</option>
                <option value={30}>Last 30 days</option>
                <option value={60}>Last 60 days</option>
                <option value={90}>Last 90 days</option>
                <option value={180}>Last 180 days</option>
              </select>
              <p className="text-xs text-zinc-500 mt-1">More days = better baselines for trend analysis</p>
            </div>

            {/* Remember */}
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={rememberEmail}
                onChange={(e) => setRememberEmail(e.target.checked)}
                className="w-4 h-4 rounded border-zinc-600 bg-zinc-800 text-teal-500 focus:ring-teal-500 focus:ring-offset-zinc-900"
              />
              <span className="text-sm text-zinc-500">Remember my email</span>
            </label>

            {/* Info */}
            <div className="flex items-start gap-2 p-3 bg-zinc-800/50 rounded-xl">
              <svg className="w-4 h-4 text-zinc-500 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-xs text-zinc-500">
                Syncs sleep, HRV, stress, body battery, and activity data. Your password is not stored.
              </p>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-start gap-2 p-3 bg-red-900/20 border border-red-800/50 rounded-xl">
                <svg className="w-4 h-4 text-red-400 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={isSubmitDisabled}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-teal-500 text-white font-medium hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {syncState === 'syncing' ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span>
                      {syncProgress
                        ? `Syncing ${syncProgress.current}/${syncProgress.total}...`
                        : 'Connecting...'}
                    </span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span>Sync Wellness Data</span>
                  </>
                )}
              </button>
              {onClose && (
                <button
                  type="button"
                  onClick={onClose}
                  disabled={syncState === 'syncing'}
                  className="px-4 py-2.5 rounded-xl border border-zinc-700 text-zinc-400 font-medium hover:bg-zinc-800 disabled:opacity-50 transition-colors"
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function SyncResult({
  result,
  onReset,
  onClose,
}: {
  result: GarminSyncResponse;
  onReset: () => void;
  onClose?: () => void;
}) {
  return (
    <div className="space-y-4">
      {/* Success header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-teal-500/20 flex items-center justify-center">
          <svg className="w-5 h-5 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-medium text-white">Sync Complete</h3>
          <p className="text-sm text-zinc-500">{result.message}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-zinc-800 rounded-xl p-3 text-center">
          <div className="text-xs text-zinc-500 uppercase tracking-wide">Total Days</div>
          <div className="text-xl font-semibold text-white mt-1">{result.synced_count}</div>
        </div>
        <div className="bg-zinc-800 rounded-xl p-3 text-center">
          <div className="text-xs text-zinc-500 uppercase tracking-wide">New</div>
          <div className="text-xl font-semibold text-teal-400 mt-1">{result.new_days}</div>
        </div>
        <div className="bg-zinc-800 rounded-xl p-3 text-center">
          <div className="text-xs text-zinc-500 uppercase tracking-wide">Updated</div>
          <div className="text-xl font-semibold text-blue-400 mt-1">{result.updated_days}</div>
        </div>
      </div>

      {/* Synced days preview */}
      {result.synced_days && result.synced_days.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-zinc-400">Recent Days Synced</h4>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {result.synced_days.slice(0, 5).map((day) => (
              <div key={day.date} className="flex items-center justify-between p-2 bg-zinc-800 rounded-lg">
                <span className="text-sm text-white">{day.date}</span>
                <div className="flex gap-1">
                  {day.has_sleep && <span className="px-2 py-0.5 text-xs bg-purple-500/20 text-purple-400 rounded">Sleep</span>}
                  {day.has_hrv && <span className="px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded">HRV</span>}
                  {day.has_stress && <span className="px-2 py-0.5 text-xs bg-orange-500/20 text-orange-400 rounded">Stress</span>}
                  {day.has_activity && <span className="px-2 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded">Activity</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <button
          onClick={onReset}
          className="flex-1 px-4 py-2.5 rounded-xl border border-zinc-700 text-zinc-400 font-medium hover:bg-zinc-800 transition-colors"
        >
          Sync Again
        </button>
        {onClose && (
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-xl bg-teal-500 text-white font-medium hover:bg-teal-600 transition-colors"
          >
            Done
          </button>
        )}
      </div>
    </div>
  );
}

export default GarminSync;
