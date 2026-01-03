'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
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
  /** Icon variant for active state (filled) */
  activeIcon?: React.ReactNode;
}

// Home icon - outline
const HomeIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
);

// Home icon - filled
const HomeIconFilled = () => (
  <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
    <path d="M11.47 3.84a.75.75 0 011.06 0l8.69 8.69a.75.75 0 101.06-1.06l-8.689-8.69a2.25 2.25 0 00-3.182 0l-8.69 8.69a.75.75 0 001.061 1.06l8.69-8.69z" />
    <path d="M12 5.432l8.159 8.159c.03.03.06.058.091.086v6.198c0 1.035-.84 1.875-1.875 1.875H15a.75.75 0 01-.75-.75v-4.5a.75.75 0 00-.75-.75h-3a.75.75 0 00-.75.75V21a.75.75 0 01-.75.75H5.625a1.875 1.875 0 01-1.875-1.875v-6.198a2.29 2.29 0 00.091-.086L12 5.43z" />
  </svg>
);

// Workouts icon - outline (bolt)
const WorkoutsIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
  </svg>
);

// Workouts icon - filled
const WorkoutsIconFilled = () => (
  <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
    <path fillRule="evenodd" d="M14.615 1.595a.75.75 0 01.359.852L12.982 9.75h7.268a.75.75 0 01.548 1.262l-10.5 11.25a.75.75 0 01-1.272-.71l1.992-7.302H3.75a.75.75 0 01-.548-1.262l10.5-11.25a.75.75 0 01.913-.143z" clipRule="evenodd" />
  </svg>
);

// Chat icon - outline
const ChatIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
  </svg>
);

// Chat icon - filled
const ChatIconFilled = () => (
  <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
    <path fillRule="evenodd" d="M4.804 21.644A6.707 6.707 0 006 21.75a6.721 6.721 0 003.583-1.029c.774.182 1.584.279 2.417.279 5.322 0 9.75-3.97 9.75-9 0-5.03-4.428-9-9.75-9s-9.75 3.97-9.75 9c0 2.409 1.025 4.587 2.674 6.192.232.226.277.428.254.543a3.73 3.73 0 01-.814 1.686.75.75 0 00.44 1.223zM8.25 10.875a1.125 1.125 0 100 2.25 1.125 1.125 0 000-2.25zM10.875 12a1.125 1.125 0 112.25 0 1.125 1.125 0 01-2.25 0zm4.875-1.125a1.125 1.125 0 100 2.25 1.125 1.125 0 000-2.25z" clipRule="evenodd" />
  </svg>
);

// Progress icon - outline (chart)
const ProgressIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>
);

// Progress icon - filled
const ProgressIconFilled = () => (
  <svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.375 2.25c-1.035 0-1.875.84-1.875 1.875v15.75c0 1.035.84 1.875 1.875 1.875h.75c1.035 0 1.875-.84 1.875-1.875V4.125c0-1.036-.84-1.875-1.875-1.875h-.75zM9.75 8.625c0-1.036.84-1.875 1.875-1.875h.75c1.036 0 1.875.84 1.875 1.875v11.25c0 1.035-.84 1.875-1.875 1.875h-.75a1.875 1.875 0 01-1.875-1.875V8.625zM3 13.125c0-1.036.84-1.875 1.875-1.875h.75c1.036 0 1.875.84 1.875 1.875v6.75c0 1.035-.84 1.875-1.875 1.875h-.75A1.875 1.875 0 013 19.875v-6.75z" />
  </svg>
);

// Primary navigation items (4 main + More = 5 total for bottom nav)
const primaryNavItems: NavItem[] = [
  {
    href: '/',
    labelKey: 'dashboard',
    icon: <HomeIcon />,
    activeIcon: <HomeIconFilled />,
  },
  {
    href: '/workouts',
    labelKey: 'workouts',
    icon: <WorkoutsIcon />,
    activeIcon: <WorkoutsIconFilled />,
  },
  {
    href: '/chat',
    labelKey: 'chat',
    icon: <ChatIcon />,
    activeIcon: <ChatIconFilled />,
  },
  {
    href: '/achievements',
    labelKey: 'progress',
    icon: <ProgressIcon />,
    activeIcon: <ProgressIconFilled />,
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

// More icon - outline (hamburger menu)
function MoreIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

// More icon - filled (dots)
function MoreIconFilled({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path fillRule="evenodd" d="M4.5 12a1.5 1.5 0 113 0 1.5 1.5 0 01-3 0zm6 0a1.5 1.5 0 113 0 1.5 1.5 0 01-3 0zm6 0a1.5 1.5 0 113 0 1.5 1.5 0 01-3 0z" clipRule="evenodd" />
    </svg>
  );
}

export function BottomNavigation() {
  const t = useTranslations('navigation');
  const pathname = usePathname();
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const { data: userProgress } = useUserProgress();
  const userLevel = userProgress?.level?.level ?? 1;
  const navRef = useRef<HTMLElement>(null);

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

  // Handle keyboard navigation within the nav bar
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      const items = navRef.current?.querySelectorAll<HTMLElement>('[role="menuitem"], button, a');
      if (!items) return;

      const currentIndex = Array.from(items).findIndex(item => item === document.activeElement);
      if (currentIndex === -1) return;

      e.preventDefault();
      const direction = e.key === 'ArrowRight' ? 1 : -1;
      const nextIndex = (currentIndex + direction + items.length) % items.length;
      items[nextIndex].focus();
    }
  }, []);

  return (
    <>
      <nav
        ref={navRef}
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-gray-900/95 backdrop-blur-sm border-t border-gray-800"
        role="navigation"
        aria-label={t('openMenu')}
        onKeyDown={handleKeyDown}
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
      >
        {/* Minimum touch target container - ensures 48px height */}
        <div className="flex items-stretch justify-around min-h-[64px] px-1">
          {primaryNavItems.map((item) => {
            const { isLocked, requiredLevel } = getFeatureLockInfo(item.href, userLevel);
            return (
              <BottomNavItem
                key={item.href}
                href={item.href}
                icon={item.icon}
                activeIcon={item.activeIcon}
                label={t(item.labelKey)}
                isActive={isActive(item.href)}
                isLocked={isLocked}
                requiredLevel={requiredLevel}
              />
            );
          })}

          {/* More button - minimum 48x48px touch target */}
          <button
            onClick={handleOpenMore}
            className={clsx(
              'flex flex-col items-center justify-center gap-0.5',
              'flex-1 min-w-[48px] min-h-[48px]',
              'px-2 py-2 rounded-lg',
              'transition-colors duration-150',
              'touch-manipulation select-none',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900',
              'active:scale-95',
              isMoreMenuActive
                ? 'text-teal-400'
                : 'text-gray-400 hover:text-gray-200 active:text-teal-400'
            )}
            aria-label={t('more')}
            aria-expanded={isMoreOpen}
            aria-haspopup="dialog"
            role="menuitem"
          >
            {isMoreMenuActive ? (
              <MoreIconFilled className="w-6 h-6" />
            ) : (
              <MoreIcon className="w-6 h-6" />
            )}
            <span className="text-[10px] font-medium truncate leading-tight">{t('more')}</span>
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
  activeIcon,
  label,
  isActive,
  isLocked = false,
  requiredLevel = 0,
}: {
  href: string;
  icon: React.ReactNode;
  activeIcon?: React.ReactNode;
  label: string;
  isActive: boolean;
  isLocked?: boolean;
  requiredLevel?: number;
}) {
  // Use filled icon for active state if available
  const displayIcon = isActive && activeIcon ? activeIcon : icon;

  const content = (
    <>
      <div className="relative">
        <span className={clsx(isLocked && 'opacity-40')}>{displayIcon}</span>
        {isLocked && (
          <LockIcon className="w-3 h-3 absolute -top-0.5 -right-1 text-gray-500" />
        )}
      </div>
      <span
        className={clsx(
          'text-[10px] font-medium truncate max-w-full leading-tight',
          isLocked && 'opacity-40'
        )}
      >
        {isLocked ? `Lvl ${requiredLevel}` : label}
      </span>
    </>
  );

  const baseClasses = clsx(
    'flex flex-col items-center justify-center gap-0.5',
    'flex-1 min-w-[48px] min-h-[48px]',
    'px-2 py-2 rounded-lg',
    'transition-colors duration-150',
    'touch-manipulation select-none',
    'focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900',
    'active:scale-95'
  );

  if (isLocked) {
    return (
      <div
        className={clsx(baseClasses, 'text-gray-500 cursor-not-allowed')}
        aria-label={`${label} - Unlocks at Level ${requiredLevel}`}
        role="menuitem"
        aria-disabled="true"
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
      role="menuitem"
    >
      {content}
    </Link>
  );
}

export default BottomNavigation;
