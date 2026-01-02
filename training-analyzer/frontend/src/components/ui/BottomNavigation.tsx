'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/i18n/navigation';
import { clsx } from 'clsx';
import { useUserProgress } from '@/hooks/useAchievements';
import { MoreMenuSheet } from './MoreMenuSheet';

// Feature unlock levels based on gamification system
const FEATURE_UNLOCK_LEVELS: Record<string, number> = {
  ai_coach_chat: 8,
};

// Map nav item href to feature key for gating
const NAV_FEATURE_MAP: Record<string, string> = {
  '/chat': 'ai_coach_chat',
};

interface NavItem {
  href: string;
  labelKey: string;
  icon: React.ReactNode;
}

// Primary navigation items (5 max for bottom nav)
const primaryNavItems: NavItem[] = [
  {
    href: '/',
    labelKey: 'dashboard',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    href: '/workouts',
    labelKey: 'workouts',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  {
    href: '/chat',
    labelKey: 'chat',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
  },
  {
    href: '/achievements',
    labelKey: 'progress',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
];

// Helper to check if a feature is locked
function getFeatureLockInfo(href: string, userLevel: number): { isLocked: boolean; requiredLevel: number } {
  const featureKey = NAV_FEATURE_MAP[href];
  if (!featureKey) {
    return { isLocked: false, requiredLevel: 0 };
  }
  const requiredLevel = FEATURE_UNLOCK_LEVELS[featureKey] ?? 0;
  return { isLocked: userLevel < requiredLevel, requiredLevel };
}

// Lock icon component
function LockIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
    </svg>
  );
}

// More icon
function MoreIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

export function BottomNavigation() {
  const t = useTranslations('navigation');
  const pathname = usePathname();
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const { data: userProgress } = useUserProgress();
  const userLevel = userProgress?.level?.level ?? 1;

  const isActive = useCallback(
    (href: string) => {
      if (href === '/') {
        return pathname === '/';
      }
      return pathname.startsWith(href);
    },
    [pathname]
  );

  // Check if any of the "More" menu items are active
  const isMoreMenuActive = ['/zones', '/goals', '/plans', '/recovery', '/patterns', '/economy', '/race-pacing', '/connect', '/settings'].some((path) =>
    pathname.startsWith(path)
  );

  const handleOpenMore = useCallback(() => {
    setIsMoreOpen(true);
  }, []);

  const handleCloseMore = useCallback(() => {
    setIsMoreOpen(false);
  }, []);

  return (
    <>
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-gray-900/95 backdrop-blur-sm border-t border-gray-800"
        role="navigation"
        aria-label="Bottom navigation"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        <div className="flex items-stretch justify-around h-16 px-1">
          {primaryNavItems.map((item) => {
            const { isLocked, requiredLevel } = getFeatureLockInfo(item.href, userLevel);
            return (
              <BottomNavItem
                key={item.href}
                href={item.href}
                icon={item.icon}
                label={t(item.labelKey)}
                isActive={isActive(item.href)}
                isLocked={isLocked}
                requiredLevel={requiredLevel}
              />
            );
          })}

          {/* More button */}
          <button
            onClick={handleOpenMore}
            className={clsx(
              'flex flex-col items-center justify-center gap-1 flex-1 min-w-[48px] min-h-[48px] px-2 py-2 rounded-lg transition-colors touch-manipulation',
              isMoreMenuActive
                ? 'text-teal-400'
                : 'text-gray-400 hover:text-gray-200 active:text-teal-400'
            )}
            aria-label={t('more')}
            aria-expanded={isMoreOpen}
            aria-haspopup="dialog"
          >
            <MoreIcon className="w-6 h-6" />
            <span className="text-[10px] font-medium truncate">{t('more')}</span>
          </button>
        </div>
      </nav>

      {/* More menu sheet */}
      <MoreMenuSheet
        isOpen={isMoreOpen}
        onClose={handleCloseMore}
        userLevel={userLevel}
      />
    </>
  );
}

function BottomNavItem({
  href,
  icon,
  label,
  isActive,
  isLocked = false,
  requiredLevel = 0,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
  isLocked?: boolean;
  requiredLevel?: number;
}) {
  const content = (
    <>
      <div className="relative">
        <span className={clsx(isLocked && 'opacity-40')}>{icon}</span>
        {isLocked && (
          <LockIcon className="w-3 h-3 absolute -top-0.5 -right-1 text-gray-500" />
        )}
      </div>
      <span
        className={clsx(
          'text-[10px] font-medium truncate max-w-full',
          isLocked && 'opacity-40'
        )}
      >
        {isLocked ? `Lvl ${requiredLevel}` : label}
      </span>
    </>
  );

  const baseClasses = clsx(
    'flex flex-col items-center justify-center gap-1 flex-1 min-w-[48px] min-h-[48px] px-2 py-2 rounded-lg transition-colors touch-manipulation'
  );

  if (isLocked) {
    return (
      <div
        className={clsx(baseClasses, 'text-gray-500 cursor-not-allowed')}
        aria-label={`${label} - Unlocks at Level ${requiredLevel}`}
      >
        {content}
      </div>
    );
  }

  return (
    <Link
      href={href}
      className={clsx(
        baseClasses,
        isActive
          ? 'text-teal-400'
          : 'text-gray-400 hover:text-gray-200 active:text-teal-400'
      )}
      aria-current={isActive ? 'page' : undefined}
      aria-label={label}
    >
      {content}
    </Link>
  );
}

export default BottomNavigation;
