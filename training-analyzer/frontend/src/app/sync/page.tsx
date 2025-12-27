'use client';

import { useRouter } from 'next/navigation';
import { GarminSync } from '@/components/garmin/GarminSync';
import { GarminSyncResponse } from '@/lib/api-client';

export default function SyncPage() {
  const router = useRouter();

  const handleSyncComplete = (result: GarminSyncResponse) => {
    // Optionally redirect to workouts after successful sync
    console.log('Sync completed:', result);
  };

  const handleClose = () => {
    router.back();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="animate-fadeIn">
        <h1 className="text-xl sm:text-2xl font-bold text-gray-100">
          Sync Activities
        </h1>
        <p className="text-sm sm:text-base text-gray-400 mt-1">
          Connect to Garmin to import your activities
        </p>
      </div>

      {/* Sync Component */}
      <div className="max-w-lg animate-slideUp">
        <GarminSync
          onSyncComplete={handleSyncComplete}
          onClose={handleClose}
        />
      </div>

      {/* Help Section */}
      <div className="max-w-lg bg-gray-900 rounded-lg border border-gray-800 p-6 animate-slideUp" style={{ animationDelay: '0.1s' }}>
        <h2 className="text-lg font-semibold text-gray-100 mb-4">
          How it works
        </h2>
        <ul className="space-y-3 text-sm text-gray-400">
          <li className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-teal-900/50 text-teal-400 text-xs font-medium shrink-0">
              1
            </span>
            <span>
              Enter your Garmin Connect credentials. Your password is only used for this sync request and is not stored.
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-teal-900/50 text-teal-400 text-xs font-medium shrink-0">
              2
            </span>
            <span>
              Select how many days of activities you want to import. More days means longer sync time.
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="flex items-center justify-center w-6 h-6 rounded-full bg-teal-900/50 text-teal-400 text-xs font-medium shrink-0">
              3
            </span>
            <span>
              Activities are downloaded and stored locally. You can then analyze them with AI-powered insights.
            </span>
          </li>
        </ul>
      </div>

      {/* Supported Features */}
      <div className="max-w-lg bg-gray-900 rounded-lg border border-gray-800 p-6 animate-slideUp" style={{ animationDelay: '0.2s' }}>
        <h2 className="text-lg font-semibold text-gray-100 mb-4">
          Supported Activity Types
        </h2>
        <div className="flex flex-wrap gap-2">
          {['Running', 'Cycling', 'Swimming', 'Walking', 'Hiking', 'Strength Training'].map((type) => (
            <span
              key={type}
              className="px-3 py-1.5 bg-gray-800 text-gray-300 text-sm rounded-full"
            >
              {type}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
