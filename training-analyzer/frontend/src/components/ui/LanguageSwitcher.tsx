'use client';

import { useLocale, useTranslations } from 'next-intl';
import { useRouter, usePathname } from '@/i18n/navigation';
import { useState, useRef, useEffect } from 'react';
import { clsx } from 'clsx';
import { routing, type Locale } from '@/i18n/routing';

const localeNames: Record<Locale, { short: string; full: string; flag: string }> = {
  en: { short: 'EN', full: 'English', flag: '🇬🇧' },
  es: { short: 'ES', full: 'Español', flag: '🇪🇸' },
};

export function LanguageSwitcher({ compact = false }: { compact?: boolean }) {
  const locale = useLocale() as Locale;
  const router = useRouter();
  const pathname = usePathname();
  const t = useTranslations('language');
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLocaleChange = (newLocale: Locale) => {
    router.replace(pathname, { locale: newLocale });
    setIsOpen(false);
  };

  const currentLocale = localeNames[locale];

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'flex items-center gap-2 rounded-lg transition-colors',
          compact
            ? 'p-2 hover:bg-gray-800'
            : 'px-3 py-2 text-sm text-gray-400 hover:text-gray-200 hover:bg-gray-800'
        )}
        aria-label={t('title')}
        aria-expanded={isOpen}
      >
        <svg
          className="w-5 h-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"
          />
        </svg>
        {!compact && (
          <span className="hidden sm:inline">{currentLocale.short}</span>
        )}
        <svg
          className={clsx(
            'w-4 h-4 transition-transform',
            isOpen && 'rotate-180'
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-40 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50 overflow-hidden">
          {routing.locales.map((loc) => {
            const localeInfo = localeNames[loc];
            const isActive = loc === locale;
            return (
              <button
                key={loc}
                onClick={() => handleLocaleChange(loc)}
                className={clsx(
                  'w-full flex items-center gap-3 px-4 py-3 text-left transition-colors',
                  isActive
                    ? 'bg-teal-900/50 text-teal-400'
                    : 'text-gray-300 hover:bg-gray-700'
                )}
              >
                <span className="text-lg">{localeInfo.flag}</span>
                <span className="flex-1">{localeInfo.full}</span>
                {isActive && (
                  <svg className="w-4 h-4 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default LanguageSwitcher;
