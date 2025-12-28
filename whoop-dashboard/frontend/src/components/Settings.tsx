'use client';

import { useState, useCallback, useEffect } from 'react';
import { db } from '@/services/database';
import { ExportDataButton } from './ExportDataButton';

// App version from package.json
const APP_VERSION = '0.1.0';

interface SettingsProps {
  onClose?: () => void;
  className?: string;
}

interface DataStats {
  total_days: number;
  earliest_date: string | null;
  latest_date: string | null;
  lastSync: string | null;
}

export function Settings({ onClose, className }: SettingsProps) {
  const [clearing, setClearing] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [clearSuccess, setClearSuccess] = useState(false);
  const [stats, setStats] = useState<DataStats | null>(null);

  // Load stats on mount
  useEffect(() => {
    async function loadStats() {
      const dbStats = await db.getStats();
      const lastSync = await db.getLastSync();
      setStats({
        ...dbStats,
        lastSync: lastSync ? lastSync.toLocaleString() : null,
      });
    }
    loadStats();
  }, [clearSuccess]);

  const handleClearCache = useCallback(async () => {
    setClearing(true);
    try {
      await db.clear();
      setClearSuccess(true);
      setShowClearConfirm(false);
      // Reset after showing success
      setTimeout(() => setClearSuccess(false), 2000);
    } catch (err) {
      console.error('Failed to clear cache:', err);
    } finally {
      setClearing(false);
    }
  }, []);

  return (
    <div className={`bg-zinc-900 rounded-2xl border border-zinc-800 ${className || ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-zinc-700/50 flex items-center justify-center">
            <svg className="w-5 h-5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Settings</h2>
            <p className="text-sm text-zinc-500">Manage your data and app settings</p>
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
      <div className="p-6 space-y-6">
        {/* Data Stats */}
        {stats && (
          <div className="space-y-3">
            <h3 className="text-sm font-medium text-zinc-400 uppercase tracking-wide">Data Summary</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-zinc-800/50 rounded-xl p-3">
                <div className="text-xs text-zinc-500">Days Stored</div>
                <div className="text-lg font-semibold text-white mt-1">{stats.total_days}</div>
              </div>
              <div className="bg-zinc-800/50 rounded-xl p-3">
                <div className="text-xs text-zinc-500">Date Range</div>
                <div className="text-sm font-medium text-white mt-1">
                  {stats.earliest_date && stats.latest_date
                    ? `${stats.earliest_date} - ${stats.latest_date}`
                    : 'No data'}
                </div>
              </div>
            </div>
            {stats.lastSync && (
              <div className="text-xs text-zinc-500">
                Last sync: {stats.lastSync}
              </div>
            )}
          </div>
        )}

        {/* Export Data */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-zinc-400 uppercase tracking-wide">Data Backup</h3>
          <ExportDataButton />
          <p className="text-xs text-zinc-500">
            Download your wellness data as a JSON file for backup or analysis.
          </p>
        </div>

        {/* Clear Cache */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-zinc-400 uppercase tracking-wide">Clear Cache</h3>

          {!showClearConfirm ? (
            <button
              onClick={() => setShowClearConfirm(true)}
              className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-zinc-800 border border-zinc-700 text-red-400 font-medium hover:bg-zinc-700 transition-colors"
            >
              {clearSuccess ? (
                <>
                  <svg className="w-5 h-5 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-teal-400">Cache Cleared!</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  <span>Clear All Data</span>
                </>
              )}
            </button>
          ) : (
            <div className="space-y-3">
              <div className="p-3 bg-red-900/20 border border-red-800/50 rounded-xl">
                <p className="text-sm text-red-400">
                  Are you sure? This will delete all stored wellness data. This action cannot be undone.
                </p>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => setShowClearConfirm(false)}
                  disabled={clearing}
                  className="flex-1 px-4 py-2.5 rounded-xl border border-zinc-700 text-zinc-400 font-medium hover:bg-zinc-800 disabled:opacity-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleClearCache}
                  disabled={clearing}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-red-600 text-white font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  {clearing ? (
                    <>
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      <span>Clearing...</span>
                    </>
                  ) : (
                    'Yes, Clear All'
                  )}
                </button>
              </div>
            </div>
          )}
          <p className="text-xs text-zinc-500">
            Remove all cached wellness data. You&apos;ll need to sync again after clearing.
          </p>
        </div>

        {/* App Info */}
        <div className="pt-4 border-t border-zinc-800">
          <div className="flex items-center justify-between text-sm">
            <span className="text-zinc-500">App Version</span>
            <span className="text-zinc-400 font-mono">{APP_VERSION}</span>
          </div>
          <div className="flex items-center justify-between text-sm mt-2">
            <span className="text-zinc-500">Data Retention</span>
            <span className="text-zinc-400">{db.getRetentionDays()} days</span>
          </div>
        </div>

        {/* Close button */}
        {onClose && (
          <button
            onClick={onClose}
            className="w-full px-4 py-2.5 rounded-xl bg-teal-500 text-white font-medium hover:bg-teal-600 transition-colors"
          >
            Done
          </button>
        )}
      </div>
    </div>
  );
}

export default Settings;
