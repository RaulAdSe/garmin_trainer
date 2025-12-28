import type { NextConfig } from 'next';
import createNextIntlPlugin from 'next-intl/plugin';
import { defaultLocale, appRoutes } from './src/i18n/config';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ];
  },

  /**
   * Fallback redirects for development mode.
   * In production, middleware.ts handles all redirects.
   * Routes are imported from src/i18n/config.ts (single source of truth).
   */
  async redirects() {
    return [
      { source: '/', destination: `/${defaultLocale}`, permanent: false },
      ...appRoutes.map((route) => ({
        source: route,
        destination: `/${defaultLocale}${route}`,
        permanent: false,
      })),
    ];
  },
};

export default withNextIntl(nextConfig);
