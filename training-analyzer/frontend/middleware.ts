import createMiddleware from 'next-intl/middleware';
import { defineRouting } from 'next-intl/routing';
import { NextRequest, NextResponse } from 'next/server';

/**
 * Middleware Configuration for next-intl
 *
 * IMPORTANT: Why routing is defined inline here instead of importing from @/i18n/routing:
 *
 * 1. Path aliases (like @/) don't work reliably in Edge Runtime middleware.
 *    The middleware runs in a separate Edge Runtime environment where TypeScript
 *    path aliases may not be resolved, especially in production builds.
 *
 * 2. This is a known limitation when using the Edge Runtime with Next.js.
 *    See: https://nextjs.org/docs/app/building-your-application/rendering/edge-and-nodejs-runtimes
 *
 * 3. KEEP THIS CONFIGURATION IN SYNC with src/i18n/routing.ts manually.
 *    If you add a new locale, update BOTH files.
 *
 * Dev Mode SSG Limitation:
 * In Next.js 16+ with Turbopack, middleware may not run for SSG pages in development.
 * The fallback redirects in next.config.ts handle these edge cases.
 */

// Inline routing configuration - KEEP IN SYNC with src/i18n/routing.ts
const locales = ['en', 'es'] as const;
const defaultLocale = 'en';

const routing = defineRouting({
  locales,
  defaultLocale,
  // 'always' means all routes MUST have a locale prefix
  // e.g., /workouts -> redirects to /en/workouts
  localePrefix: 'always',
});

// Create the next-intl middleware
const intlMiddleware = createMiddleware(routing);

export default function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip API routes, static files, and Next.js internals
  // These should not have locale prefixes
  if (
    pathname.startsWith('/api') ||
    pathname.startsWith('/_next') ||
    pathname.startsWith('/_vercel') ||
    pathname.includes('.')
  ) {
    return NextResponse.next();
  }

  // Check if pathname already has a locale prefix
  const hasLocale = locales.some(
    (locale) => pathname === `/${locale}` || pathname.startsWith(`/${locale}/`)
  );

  // If no locale prefix and not root, redirect to default locale
  // This handles cases like /workouts -> /en/workouts
  if (!hasLocale && pathname !== '/') {
    const url = request.nextUrl.clone();
    url.pathname = `/${defaultLocale}${pathname}`;
    return NextResponse.redirect(url, 307);
  }

  // Let next-intl middleware handle:
  // - Locale detection from Accept-Language header
  // - Setting locale cookies
  // - Root path (/) redirect to default locale
  return intlMiddleware(request);
}

/**
 * Matcher configuration for the middleware.
 *
 * This pattern matches all paths EXCEPT:
 * - /api/* (API routes are locale-independent)
 * - /_next/* (Next.js internal routes)
 * - /_vercel/* (Vercel internal routes)
 * - Files with extensions (e.g., .js, .css, .png, .ico)
 */
export const config = {
  matcher: [
    // Match all paths except api, _next, _vercel, and files with extensions
    '/((?!api|_next|_vercel|.*\\..*).*)',
    // Also match the root path explicitly
    '/'
  ]
};
