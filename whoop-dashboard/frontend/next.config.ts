import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export for Capacitor iOS app
  output: 'export',
  // Required for static export routing to work in Capacitor
  trailingSlash: true,
  // Disable image optimization (not supported in static export)
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
