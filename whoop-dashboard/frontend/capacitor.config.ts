import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.garmin.whoopdashboard',
  appName: 'WHOOP Dashboard',
  webDir: 'out',
  ios: {
    // Allow loading external resources (Garmin API)
    allowsLinkPreview: false,
  },
  plugins: {
    CapacitorHttp: {
      // Enable native HTTP for all requests (bypasses CORS)
      enabled: true,
    },
    CapacitorSQLite: {
      iosDatabaseLocation: 'Library/CapacitorDatabase',
    },
  },
};

export default config;
