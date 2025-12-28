/**
 * i18n Configuration - Single Source of Truth
 *
 * This file contains all i18n constants used across the application.
 * Import from here to ensure consistency across:
 * - middleware.ts (locale detection & redirects)
 * - next.config.ts (fallback redirects)
 * - routing.ts (next-intl configuration)
 *
 * When adding a new locale:
 * 1. Add to `locales` array below
 * 2. Create translation file in messages/{locale}.json
 * 3. No other files need updating
 */

export const locales = ['en', 'es'] as const;
export const defaultLocale = 'en' as const;

export type Locale = (typeof locales)[number];

/**
 * All application routes (without locale prefix).
 * Used by next.config.ts for fallback redirects.
 */
export const appRoutes = [
  '/workouts',
  '/workouts/:path*',
  '/plans',
  '/plans/:path*',
  '/design',
  '/goals',
  '/sync',
] as const;
