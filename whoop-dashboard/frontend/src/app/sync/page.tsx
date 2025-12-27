'use client';

import { useRouter } from 'next/navigation';
import { GarminSync, GarminSyncResponse } from '@/components/garmin/GarminSync';

export default function SyncPage() {
  const router = useRouter();

  const handleSyncComplete = (result: GarminSyncResponse) => {
    console.log('Sync completed:', result);
  };

  const handleClose = () => {
    router.push('/');
  };

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Navigation */}
      <nav className="flex items-center justify-between px-4 py-3 border-b border-zinc-900">
        <button
          onClick={() => router.push('/')}
          className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          <span>Back to Dashboard</span>
        </button>
      </nav>

      {/* Main Content */}
      <main className="max-w-lg mx-auto p-4 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">Sync Wellness Data</h1>
          <p className="text-zinc-500 mt-1">
            Connect to Garmin to import your health metrics
          </p>
        </div>

        {/* Sync Component */}
        <GarminSync
          onSyncComplete={handleSyncComplete}
          onClose={handleClose}
        />

        {/* Help Section */}
        <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            How it works
          </h2>
          <ul className="space-y-3 text-sm text-zinc-400">
            <li className="flex items-start gap-3">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-teal-900/50 text-teal-400 text-xs font-medium shrink-0">
                1
              </span>
              <span>
                Enter your Garmin Connect credentials. Your password is only used for this sync and is not stored.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-teal-900/50 text-teal-400 text-xs font-medium shrink-0">
                2
              </span>
              <span>
                Select how many days of data to import. More days means longer sync time.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-teal-900/50 text-teal-400 text-xs font-medium shrink-0">
                3
              </span>
              <span>
                Your wellness data is saved locally. The dashboard will update with your metrics.
              </span>
            </li>
          </ul>
        </div>

        {/* Supported Data Types */}
        <div className="bg-zinc-900 rounded-2xl border border-zinc-800 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">
            Data Types Synced
          </h2>
          <div className="flex flex-wrap gap-2">
            {[
              { name: 'Sleep', color: 'purple' },
              { name: 'HRV', color: 'green' },
              { name: 'Stress', color: 'orange' },
              { name: 'Body Battery', color: 'yellow' },
              { name: 'Steps', color: 'blue' },
              { name: 'Resting HR', color: 'red' },
            ].map((type) => (
              <span
                key={type.name}
                className={`px-3 py-1.5 bg-${type.color}-500/20 text-${type.color}-400 text-sm rounded-full`}
                style={{
                  backgroundColor: `color-mix(in srgb, var(--${type.color}-500, #888) 20%, transparent)`,
                  color: `var(--${type.color}-400, #aaa)`,
                }}
              >
                {type.name}
              </span>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="px-3 py-1.5 bg-purple-500/20 text-purple-400 text-sm rounded-full">Sleep</span>
            <span className="px-3 py-1.5 bg-green-500/20 text-green-400 text-sm rounded-full">HRV</span>
            <span className="px-3 py-1.5 bg-orange-500/20 text-orange-400 text-sm rounded-full">Stress</span>
            <span className="px-3 py-1.5 bg-yellow-500/20 text-yellow-400 text-sm rounded-full">Body Battery</span>
            <span className="px-3 py-1.5 bg-blue-500/20 text-blue-400 text-sm rounded-full">Steps</span>
            <span className="px-3 py-1.5 bg-red-500/20 text-red-400 text-sm rounded-full">Resting HR</span>
          </div>
        </div>
      </main>
    </div>
  );
}
