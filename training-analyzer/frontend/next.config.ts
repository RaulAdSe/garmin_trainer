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
  // Redirects for dev mode fallback (middleware handles production)
  async redirects() {
    return [
      { source: '/', destination: '/en', permanent: false },
      { source: '/workouts', destination: '/en/workouts', permanent: false },
      { source: '/workouts/:path*', destination: '/en/workouts/:path*', permanent: false },
      { source: '/plans', destination: '/en/plans', permanent: false },
      { source: '/plans/:path*', destination: '/en/plans/:path*', permanent: false },
      { source: '/design', destination: '/en/design', permanent: false },
      { source: '/goals', destination: '/en/goals', permanent: false },
      { source: '/sync', destination: '/en/sync', permanent: false },
    ];
  },
};

export default withNextIntl(nextConfig);
