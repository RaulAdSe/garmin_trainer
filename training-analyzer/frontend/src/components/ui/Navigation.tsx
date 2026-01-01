'use client';

import { useState, useCallback, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/i18n/navigation';
import { clsx } from 'clsx';
import { LanguageSwitcher } from './LanguageSwitcher';
import { useUserProgress } from '@/hooks/useAchievements';

// Feature unlock levels based on gamification system
const FEATURE_UNLOCK_LEVELS: Record<string, number> = {
  'trend_analysis': 3,
  'advanced_metrics': 5,
  'ai_coach_chat': 8,
  'training_plans': 10,
  'workout_design': 15,
  'periodization': 20,
  'coach_mode': 25,
};

// Map nav item href to feature key for gating
const NAV_FEATURE_MAP: Record<string, string> = {
  '/plans': 'training_plans',
  '/design': 'workout_design',
  '/chat': 'ai_coach_chat',
  '/coach': 'coach_mode',
};

interface NavItem {
  href: string;
  labelKey: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  // === Primary (daily use) ===
  {
    href: '/',
    labelKey: 'dashboard',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    href: '/workouts',
    labelKey: 'workouts',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  // === Training Knowledge ===
  {
    href: '/zones',
    labelKey: 'zones',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
      </svg>
    ),
  },
  // === Planning & Goals ===
  {
    href: '/goals',
    labelKey: 'goals',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
      </svg>
    ),
  },
  {
    href: '/plans',
    labelKey: 'plans',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
      </svg>
    ),
  },
  // === AI Features ===
  {
    href: '/chat',
    labelKey: 'chat',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
  },
  // === Progress & Motivation ===
  {
    href: '/achievements',
    labelKey: 'achievements',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
      </svg>
    ),
  },
  // === Setup & Utilities ===
  {
    href: '/connect',
    labelKey: 'connect',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
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

export function Navigation() {
  const t = useTranslations('navigation');
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { data: userProgress } = useUserProgress();
  const userLevel = userProgress?.level?.level ?? 1;

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [pathname]);

  // Close mobile menu when clicking outside
  useEffect(() => {
    if (!isMobileMenuOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('[data-mobile-menu]') && !target.closest('[data-menu-toggle]')) {
        setIsMobileMenuOpen(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [isMobileMenuOpen]);

  // Prevent body scroll when mobile menu is open
  useEffect(() => {
    if (isMobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobileMenuOpen]);

  const toggleMobileMenu = useCallback(() => {
    setIsMobileMenuOpen((prev) => !prev);
  }, []);

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/';
    }
    return pathname.startsWith(href);
  };

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex md:flex-col md:w-64 lg:w-72 bg-gray-900 border-r border-gray-800 p-4 lg:p-6 shrink-0">
        <div className="mb-8 flex items-start justify-between">
          <Link href="/" className="flex items-center gap-3">
            <img
              src="/icons/logo.png"
              alt="trAIner logo"
              width={40}
              height={40}
              className="rounded-lg"
            />
            <div>
              <h1 className="text-xl lg:text-2xl font-bold text-teal-400">
                {t('appName')}
              </h1>
              <p className="text-sm text-gray-500">{t('appSubtitle')}</p>
            </div>
          </Link>
          <LanguageSwitcher compact />
        </div>
        <nav className="space-y-1 flex-1" role="navigation" aria-label="Main navigation">
          {navItems.map((item) => {
            const { isLocked, requiredLevel } = getFeatureLockInfo(item.href, userLevel);
            return (
              <NavLink
                key={item.href}
                href={item.href}
                icon={item.icon}
                isActive={isActive(item.href)}
                isLocked={isLocked}
                requiredLevel={requiredLevel}
                lockLabel={t('lockedLevel', { level: requiredLevel })}
              >
                {t(item.labelKey)}
              </NavLink>
            );
          })}
        </nav>
        <div className="pt-4 border-t border-gray-800">
          <p className="text-xs text-gray-600 text-center">
            {t('version')}
          </p>
        </div>
      </aside>

      {/* Mobile Header */}
      <header className="md:hidden fixed top-0 left-0 right-0 z-40 bg-gray-900/95 backdrop-blur-sm border-b border-gray-800 safe-area-inset-top">
        <div className="flex items-center justify-between px-4 h-14">
          <Link href="/" className="flex items-center gap-2">
            <img
              src="/icons/logo.png"
              alt="trAIner logo"
              width={32}
              height={32}
              className="rounded-md"
            />
            <span className="text-lg font-bold text-teal-400">trAIner</span>
          </Link>
          <div className="flex items-center gap-2">
            <LanguageSwitcher compact />
            <button
              data-menu-toggle
              onClick={toggleMobileMenu}
              className="p-2 -mr-2 rounded-lg hover:bg-gray-800 transition-colors touch-manipulation"
              aria-label={isMobileMenuOpen ? t('closeMenu') : t('openMenu')}
              aria-expanded={isMobileMenuOpen}
            >
              {isMobileMenuOpen ? (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      {isMobileMenuOpen && (
        <div
          className="md:hidden fixed inset-0 z-30 bg-black/60 backdrop-blur-sm"
          aria-hidden="true"
        />
      )}

      {/* Mobile Menu Panel */}
      <div
        data-mobile-menu
        className={clsx(
          'md:hidden fixed top-14 left-0 right-0 bottom-0 z-30 bg-gray-900 transform transition-transform duration-300 ease-in-out overflow-y-auto',
          isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <nav className="p-4 space-y-2" role="navigation" aria-label="Mobile navigation">
          {navItems.map((item) => {
            const { isLocked, requiredLevel } = getFeatureLockInfo(item.href, userLevel);
            return (
              <MobileNavLink
                key={item.href}
                href={item.href}
                icon={item.icon}
                isActive={isActive(item.href)}
                onClick={() => setIsMobileMenuOpen(false)}
                isLocked={isLocked}
                requiredLevel={requiredLevel}
                lockLabel={t('lockedLevel', { level: requiredLevel })}
              >
                {t(item.labelKey)}
              </MobileNavLink>
            );
          })}
        </nav>
      </div>

      {/* Mobile Bottom Navigation */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-gray-900/95 backdrop-blur-sm border-t border-gray-800 safe-area-inset-bottom"
        role="navigation"
        aria-label="Bottom navigation"
      >
        <div className="flex items-center justify-around h-16 px-1">
          {navItems.slice(0, 6).map((item) => {
            const { isLocked, requiredLevel } = getFeatureLockInfo(item.href, userLevel);
            return (
              <BottomNavLink
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
        </div>
      </nav>

      {/* Spacer for mobile header */}
      <div className="md:hidden h-14 shrink-0" />
    </>
  );
}

function NavLink({
  href,
  icon,
  children,
  isActive,
  isLocked = false,
  requiredLevel = 0,
  lockLabel,
}: {
  href: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  isActive: boolean;
  isLocked?: boolean;
  requiredLevel?: number;
  lockLabel?: string;
}) {
  const content = (
    <>
      <span className={clsx(isLocked && 'opacity-50')}>{icon}</span>
      <span className={clsx('flex-1', isLocked && 'opacity-50')}>{children}</span>
      {isLocked && (
        <span className="flex items-center gap-1 text-xs text-gray-500" title={lockLabel}>
          <LockIcon className="w-3.5 h-3.5" />
          <span className="text-[10px] font-medium">Lvl {requiredLevel}</span>
        </span>
      )}
    </>
  );

  if (isLocked) {
    return (
      <div
        className="flex items-center gap-3 px-4 py-3 rounded-lg text-gray-500 cursor-not-allowed"
        title={lockLabel}
      >
        {content}
      </div>
    );
  }

  return (
    <Link
      href={href}
      className={clsx(
        'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
        isActive
          ? 'bg-teal-900/50 text-teal-400 font-medium'
          : 'text-gray-300 hover:bg-gray-800 hover:text-teal-400'
      )}
      aria-current={isActive ? 'page' : undefined}
    >
      {content}
    </Link>
  );
}

function MobileNavLink({
  href,
  icon,
  children,
  isActive,
  onClick,
  isLocked = false,
  requiredLevel = 0,
  lockLabel,
}: {
  href: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  isActive: boolean;
  onClick: () => void;
  isLocked?: boolean;
  requiredLevel?: number;
  lockLabel?: string;
}) {
  const content = (
    <>
      <span className={clsx('w-6 h-6', isLocked && 'opacity-50')}>{icon}</span>
      <span className={clsx('text-lg flex-1', isLocked && 'opacity-50')}>{children}</span>
      {isLocked && (
        <span className="flex items-center gap-1.5 text-gray-500">
          <LockIcon className="w-4 h-4" />
          <span className="text-xs font-medium">Lvl {requiredLevel}</span>
        </span>
      )}
    </>
  );

  if (isLocked) {
    return (
      <div
        className="flex items-center gap-4 px-4 py-4 rounded-xl min-h-[56px] text-gray-500 cursor-not-allowed"
        title={lockLabel}
      >
        {content}
      </div>
    );
  }

  return (
    <Link
      href={href}
      onClick={onClick}
      className={clsx(
        'flex items-center gap-4 px-4 py-4 rounded-xl transition-colors min-h-[56px] touch-manipulation',
        isActive
          ? 'bg-teal-900/50 text-teal-400 font-medium'
          : 'text-gray-300 hover:bg-gray-800 active:bg-gray-700'
      )}
      aria-current={isActive ? 'page' : undefined}
    >
      {content}
    </Link>
  );
}

function BottomNavLink({
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
          <LockIcon className="w-2.5 h-2.5 absolute -top-0.5 -right-1 text-gray-500" />
        )}
      </div>
      <span className={clsx(
        'text-[10px] font-medium truncate max-w-full',
        isLocked && 'opacity-40'
      )}>
        {isLocked ? `Lvl ${requiredLevel}` : label}
      </span>
    </>
  );

  if (isLocked) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-1 min-w-[64px] min-h-[48px] px-3 py-2 rounded-lg text-gray-500 cursor-not-allowed"
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
        'flex flex-col items-center justify-center gap-1 min-w-[64px] min-h-[48px] px-3 py-2 rounded-lg transition-colors touch-manipulation',
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

export default Navigation;
