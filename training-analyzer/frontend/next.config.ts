import type { NextConfig } from "next";
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig: NextConfig = {
  // Proxy API requests to FastAPI backend
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://localhost:8000/api/v1/:path*",
      },
    ];
  },
  /**
   * Fallback redirects for development mode.
   *
   * In Next.js 16+ with Turbopack, middleware may not run reliably for
   * statically generated pages in development mode. These redirects serve
   * as a fallback to ensure locale prefixes are added.
   *
   * In production, the middleware.ts handles all locale redirects.
   * These redirects have lower priority than middleware, so they won't
   * interfere in production.
   */
  async redirects() {
    // KEEP IN SYNC with routes in src/app/[locale]/ and middleware.ts locales
    const defaultLocale = 'en';

    return [
      // Root path fallback - middleware handles Accept-Language detection,
      // but this ensures a fallback to default locale if middleware doesn't run
      { source: '/', destination: `/${defaultLocale}`, permanent: false },

      // All other routes - redirect to default locale version
      { source: '/workouts', destination: `/${defaultLocale}/workouts`, permanent: false },
      { source: '/workouts/:path*', destination: `/${defaultLocale}/workouts/:path*`, permanent: false },
      { source: '/plans', destination: `/${defaultLocale}/plans`, permanent: false },
      { source: '/plans/:path*', destination: `/${defaultLocale}/plans/:path*`, permanent: false },
      { source: '/design', destination: `/${defaultLocale}/design`, permanent: false },
      { source: '/goals', destination: `/${defaultLocale}/goals`, permanent: false },
      { source: '/sync', destination: `/${defaultLocale}/sync`, permanent: false },
    ];
  },
};

export default withNextIntl(nextConfig);
