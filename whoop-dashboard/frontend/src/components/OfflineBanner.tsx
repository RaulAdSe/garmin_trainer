'use client';

/**
 * OfflineBanner component displays a warning when the user is offline.
 * Part of Phase 3 (UX Polish) - Offline indicator.
 */

interface OfflineBannerProps {
  className?: string;
}

/**
 * A simple banner showing "You're offline" with a wifi-off icon.
 * Styled in amber/yellow to indicate warning with smooth fade animation.
 * Positioned at top of screen.
 */
export function OfflineBanner({ className = '' }: OfflineBannerProps) {
  return (
    <div
      role="alert"
      aria-live="polite"
      className={`
        animate-fade-in
        bg-amber-900/30 border-b border-amber-800/50
        px-4 py-2
        ${className}
      `}
    >
      <div className="flex items-center justify-center gap-2 max-w-lg mx-auto">
        {/* Wifi-off icon */}
        <svg
          className="w-4 h-4 text-amber-400 shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"
          />
        </svg>
        <span className="text-amber-400 text-sm font-medium">
          You&apos;re offline
        </span>
      </div>
    </div>
  );
}

export default OfflineBanner;
