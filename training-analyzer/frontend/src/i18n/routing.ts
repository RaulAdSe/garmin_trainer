import { defineRouting } from 'next-intl/routing';
import { locales, defaultLocale, type Locale } from './config';

export const routing = defineRouting({
  locales,
  defaultLocale,
  localePrefix: 'always',
});

export type { Locale };
