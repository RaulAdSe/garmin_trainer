'use client';

import { Link } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import PacingPlanGenerator from '@/components/race/PacingPlanGenerator';

export default function RacePacingPage() {
  const t = useTranslations('racePacing');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/"
          className="p-2 rounded-lg hover:bg-gray-800 transition-colors"
        >
          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Race Pacing Planner</h1>
          <p className="text-sm text-gray-400 mt-1">
            Generate optimal pacing strategies for your race
          </p>
        </div>
      </div>

      {/* Pacing Plan Generator */}
      <PacingPlanGenerator />
    </div>
  );
}

