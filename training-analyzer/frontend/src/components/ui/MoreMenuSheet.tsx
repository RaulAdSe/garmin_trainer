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
}

// Secondary navigation items for the More menu
const secondaryNavItems: SecondaryNavItem[] = [
  {
    href: '/zones',
    labelKey: 'zones',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
      </svg>
    ),
  },
  {
    href: '/goals',
    labelKey: 'goals',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
      </svg>
    ),
  },
  {
    href: '/plans',
    labelKey: 'plans',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
      </svg>
    ),
  },
  {
    href: '/connect',
    labelKey: 'connect',
    icon: (
      <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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

export function MoreMenuSheet({ isOpen, onClose, userLevel }: MoreMenuSheetProps) {
  const t = useTranslations('navigation');
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/';
    }
    return pathname.startsWith(href);
  };

  return (
    <BottomSheet isOpen={isOpen} onClose={onClose} title={t('more')}>
      <div className="px-4 py-3 space-y-1">
        {secondaryNavItems.map((item) => {
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

        {/* Divider */}
        <div className="my-3 border-t border-gray-800" />

        {/* Version info */}
        <div className="px-4 py-2 text-center">
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
        <span className="w-2 h-2 bg-teal-400 rounded-full" />
      )}
    </>
  );

  const baseClasses = clsx(
    'flex items-center gap-4 w-full px-4 py-4 rounded-xl transition-colors min-h-[56px] touch-manipulation'
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
      onClick={onClick}
      className={clsx(
        baseClasses,
        isActive
          ? 'bg-teal-900/50 text-teal-400'
          : 'text-gray-300 hover:bg-gray-800 active:bg-gray-700'
      )}
      aria-current={isActive ? 'page' : undefined}
    >
      {content}
    </Link>
  );
}

export default MoreMenuSheet;
