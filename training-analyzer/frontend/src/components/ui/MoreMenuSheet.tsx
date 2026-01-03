'use client';

import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/i18n/navigation';
import { clsx } from 'clsx';
import { BottomSheet } from './BottomSheet';

// Feature unlock levels for secondary nav items
const FEATURE_UNLOCK_LEVELS: Record<string, number> = {
  training_plans: 10,
};

const NAV_FEATURE_MAP: Record<string, string> = {
  '/plans': 'training_plans',
};

interface MoreMenuSheetProps {
  isOpen: boolean;
  onClose: () => void;
  userLevel: number;
}

interface SecondaryNavItem {
  href: string;
  labelKey: string;
  icon: React.ReactNode;
  /** Group identifier for visual separation */
  group?: 'training' | 'analysis' | 'connect' | 'settings';
}

// Secondary navigation items for the More menu - organized by group
const secondaryNavItems: SecondaryNavItem[] = [
  // Training group
  {
    href: '/zones',
    labelKey: 'zones',
    group: 'training',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
      </svg>
    ),
  },
  {
    href: '/goals',
    labelKey: 'goals',
    group: 'training',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
      </svg>
    ),
  },
  {
    href: '/plans',
    labelKey: 'plans',
    group: 'training',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
      </svg>
    ),
  },
  // Analysis group
  {
    href: '/recovery',
    labelKey: 'recovery',
    group: 'analysis',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
      </svg>
    ),
  },
  {
    href: '/patterns',
    labelKey: 'patterns',
    group: 'analysis',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    href: '/economy',
    labelKey: 'economy',
    group: 'analysis',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
  },
  {
    href: '/race-pacing',
    labelKey: 'racePacing',
    group: 'analysis',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  // Connect group
  {
    href: '/connect',
    labelKey: 'connect',
    group: 'connect',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
    ),
  },
  // Settings group
  {
    href: '/settings',
    labelKey: 'settings',
    group: 'settings',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
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

export function MoreMenuSheet({ isOpen, onClose, userLevel }: MoreMenuSheetProps) {
  const t = useTranslations('navigation');
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/';
    }
    return pathname.startsWith(href);
  };

  // Group items by their group property
  const trainingItems = secondaryNavItems.filter(item => item.group === 'training');
  const analysisItems = secondaryNavItems.filter(item => item.group === 'analysis');
  const connectItems = secondaryNavItems.filter(item => item.group === 'connect');
  const settingsItems = secondaryNavItems.filter(item => item.group === 'settings');

  const renderGroup = (items: SecondaryNavItem[]) => (
    <>
      {items.map((item) => {
        const { isLocked, requiredLevel } = getFeatureLockInfo(item.href, userLevel);
        return (
          <MenuNavItem
            key={item.href}
            href={item.href}
            icon={item.icon}
            label={t(item.labelKey)}
            isActive={isActive(item.href)}
            isLocked={isLocked}
            requiredLevel={requiredLevel}
            onClick={onClose}
          />
        );
      })}
    </>
  );

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title={t('more')}>
      <div className="px-4 py-3">
        {/* Training section */}
        <nav className="space-y-1" role="menu" aria-label="Training navigation">
          {renderGroup(trainingItems)}
        </nav>

        {/* Analysis section */}
        <div className="my-3 border-t border-gray-800" />
        <nav className="space-y-1" role="menu" aria-label="Analysis navigation">
          {renderGroup(analysisItems)}
        </nav>

        {/* Connect section */}
        <div className="my-3 border-t border-gray-800" />
        <nav className="space-y-1" role="menu" aria-label="Connect navigation">
          {renderGroup(connectItems)}
        </nav>

        {/* Settings section */}
        <div className="my-3 border-t border-gray-800" />
        <nav className="space-y-1" role="menu" aria-label="Settings navigation">
          {renderGroup(settingsItems)}
        </nav>

        {/* Version info */}
        <div className="mt-4 px-4 py-2 text-center">
          <p className="text-xs text-gray-600">{t('version')}</p>
        </div>
      </div>
    </BottomSheet>
  );
}

function MenuNavItem({
  href,
  icon,
  label,
  isActive,
  isLocked = false,
  requiredLevel = 0,
  onClick,
}: {
  href: string;
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
  isLocked?: boolean;
  requiredLevel?: number;
  onClick: () => void;
}) {
  const content = (
    <>
      <span className={clsx('shrink-0', isLocked && 'opacity-50')}>{icon}</span>
      <span className={clsx('flex-1 text-base font-medium', isLocked && 'opacity-50')}>
        {label}
      </span>
      {isLocked && (
        <span className="flex items-center gap-1.5 text-gray-500">
          <LockIcon className="w-4 h-4" />
          <span className="text-xs font-medium">Lvl {requiredLevel}</span>
        </span>
      )}
      {isActive && !isLocked && (
        <span className="w-2 h-2 bg-teal-400 rounded-full shrink-0" />
      )}
    </>
  );

  // Base classes with minimum 48px touch target
  const baseClasses = clsx(
    'flex items-center gap-4 w-full',
    'px-4 py-3 rounded-xl',
    'min-h-[48px]',
    'transition-colors duration-150',
    'touch-manipulation select-none',
    'focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 focus-visible:ring-inset',
    'active:scale-[0.98]'
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
      onClick={onClick}
      className={clsx(
        baseClasses,
        isActive
          ? 'bg-teal-900/50 text-teal-400'
          : 'text-gray-300 hover:bg-gray-800 active:bg-gray-700'
      )}
      aria-current={isActive ? 'page' : undefined}
      role="menuitem"
    >
      {content}
    </Link>
  );
}

export default MoreMenuSheet;
