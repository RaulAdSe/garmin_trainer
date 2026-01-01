import createMiddleware from 'next-intl/middleware';
import { defineRouting } from 'next-intl/routing';
import { NextRequest, NextResponse } from 'next/server';
import { locales, defaultLocale } from './src/i18n/config';

/**
 * Middleware for i18n locale handling.
 *
 * Uses relative import from src/i18n/config.ts (not path aliases)
 * because Edge Runtime doesn't reliably resolve TypeScript path aliases.
 */

const routing = defineRouting({
  locales,
  defaultLocale,
  localePrefix: 'always',
});

const intlMiddleware = createMiddleware(routing);

export default function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // For API routes, forward the Authorization header to the backend
  if (pathname.startsWith('/api')) {
    const requestHeaders = new Headers(request.headers);
    // Ensure Authorization header is preserved through the rewrite
    const authHeader = request.headers.get('Authorization');
    if (authHeader) {
      requestHeaders.set('Authorization', authHeader);
    }
    return NextResponse.next({
      request: {
        headers: requestHeaders,
      },
    });
  }

  // Skip static files and Next.js internals
  if (
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
  if (!hasLocale && pathname !== '/') {
    const url = request.nextUrl.clone();
    url.pathname = `/${defaultLocale}${pathname}`;
    return NextResponse.redirect(url, 307);
  }

  // Let next-intl handle locale detection and root path redirect
  return intlMiddleware(request);
}

export const config = {
  // Include API routes for header forwarding, exclude static files
  matcher: ['/((?!_next|_vercel|.*\\..*).*)', '/'],
};
