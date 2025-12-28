# iOS Deployment Guide

This guide covers deploying the WHOOP Dashboard as a native iOS app with on-device Garmin authentication.

---

## Overview

The iOS app is a fully standalone native application that:
- **Authenticates directly with Garmin** - No backend server required
- **Stores data locally** - Works offline after initial sync
- **Secures credentials** - Uses iOS Keychain for sensitive data

```
┌─────────────────────────────────────────────────────────────┐
│                      iOS Device                              │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Capacitor  │───▶│   Garmin     │───▶│  IndexedDB    │  │
│  │  WebView    │    │   OAuth      │    │  (Local DB)   │  │
│  └─────────────┘    └──────────────┘    └───────────────┘  │
│         │                  │                    │           │
│         │           ┌──────▼──────┐            │           │
│         │           │  iOS        │            │           │
│         │           │  Keychain   │            │           │
│         └───────────┴─────────────┴────────────┘           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                 ┌────────────────────────┐
                 │  connectapi.garmin.com │
                 │  (Garmin API)          │
                 └────────────────────────┘
```

---

## Prerequisites

- **macOS** with Xcode 15+
- **Node.js 18+** and npm
- **Apple ID** (free account works, but has limitations)
- **iPhone** running iOS 15+ (or Simulator)
- **Garmin Connect account** with wellness data

---

## Quick Start

### 1. Build the Frontend

```bash
cd whoop-dashboard/frontend

# Install dependencies
npm install

# Build static export
npm run build

# Sync to iOS
npx cap sync ios
```

### 2. Open in Xcode

```bash
npx cap open ios
```

### 3. Configure Signing

1. Select the "App" target in Xcode
2. Go to "Signing & Capabilities"
3. Select your Team (Apple ID)
4. Xcode auto-generates provisioning profile

### 4. Run on Device

1. Connect your iPhone via USB
2. Select your device in Xcode toolbar
3. Press Cmd+R to build and run
4. Trust the developer certificate on iPhone:
   - Settings → General → VPN & Device Management → Trust

---

## Authentication Flow

The app implements Garmin's SSO flow entirely on-device:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  User Login  │────▶│   SSO Embed  │────▶│   Get CSRF   │
│  (email/pw)  │     │   Cookies    │     │    Token     │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
      ┌───────────────────────────────────────────┘
      ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Submit     │────▶│   Exchange   │────▶│   Exchange   │
│   Creds      │     │   Ticket→    │     │   OAuth1→    │
│              │     │   OAuth1     │     │   OAuth2     │
└──────────────┘     └──────────────┘     └──────────────┘
```

### OAuth1 Signing (HMAC-SHA1)

The app uses proper OAuth1 signing with the Web Crypto API:

```typescript
// Signature base string
baseString = "POST&https%3A%2F%2Fconnectapi...&oauth_consumer_key%3D..."

// HMAC-SHA1 signature
signature = HMAC-SHA1(consumerSecret + "&" + tokenSecret, baseString)
```

### Token Storage

| Data | Storage | Security |
|------|---------|----------|
| OAuth1 Token | Capacitor Preferences | Encrypted at rest |
| OAuth2 Token | Capacitor Preferences | Encrypted at rest |
| Password | iOS Keychain | Hardware-backed |
| Refresh Token | iOS Keychain | Hardware-backed |

---

## API Integration

### Base URL

The app uses `connectapi.garmin.com` (NOT `connect.garmin.com/modern/proxy/`):

```typescript
const CONNECT_API = 'https://connectapi.garmin.com';
```

### Endpoints Used

| Endpoint | Data |
|----------|------|
| `/wellness-service/wellness/dailySleep` | Sleep data |
| `/hrv-service/hrv/{date}` | HRV metrics |
| `/wellness-service/wellness/dailyStress/{date}` | Stress levels |
| `/wellness-service/wellness/bodyBattery/reports/daily` | Body battery |
| `/usersummary-service/stats/steps/daily/{start}/{end}` | Step counts |
| `/wellness-service/wellness/dailyHeartRate/{user}` | Resting HR |
| `/userprofile-service/socialProfile` | User profile |

### Request Headers

```typescript
{
  'Authorization': 'Bearer {access_token}',
  'User-Agent': 'com.garmin.android.apps.connectmobile',
  'Accept': 'application/json',
  'DI-Units': 'metric',
  'NK': 'NT'
}
```

---

## Local Database

Data is stored locally using IndexedDB (via Dexie.js):

### Tables

| Table | Fields |
|-------|--------|
| `wellness` | date, fetched_at, resting_heart_rate |
| `sleep` | date, total_sleep_seconds, deep/light/rem, score |
| `hrv` | date, weekly_avg, last_night_avg, status |
| `stress` | date, avg_stress, body_battery_high/low |
| `activity` | date, steps, calories, intensity_minutes |

### Data Retention

- 90 days of data retained
- Automatic cleanup of older records
- Sufficient for trend analysis and baselines

---

## Offline Support

The app works fully offline after initial sync:

1. **Network Detection**: Uses Capacitor Network plugin
2. **Offline Banner**: Shows when connectivity lost
3. **Local Data**: All wellness data served from IndexedDB
4. **Queue Sync**: Pending syncs resume when online

```typescript
// Network status hook
const { isOnline, connectionType } = useNetworkStatus();
```

---

## Security Features

### Secure Storage

```typescript
// Password stored in Keychain
await secureStorage.setPassword(password);

// Retrieved only for re-authentication
const password = await secureStorage.getPassword();
```

### Token Refresh

- OAuth2 tokens expire after 1 hour
- Automatic refresh using OAuth1 token
- Queue prevents multiple simultaneous refreshes

### Error Handling

- Retry logic with exponential backoff
- 401 responses trigger token refresh
- User-friendly error messages

---

## Development

### Debug Build

```bash
# Start dev server
npm run dev

# In capacitor.config.ts, uncomment:
server: {
  url: 'http://YOUR_IP:3000',
  cleartext: true
}

# Sync and run
npx cap sync ios
npx cap open ios
```

### Production Build

```bash
# Build static export
npm run build

# Ensure server config is commented out in capacitor.config.ts

# Sync
npx cap sync ios
```

### Viewing Logs

1. In Xcode, go to View → Debug Area → Activate Console
2. Look for `[Garmin]` prefixed log messages
3. API responses are logged as JSON

---

## Troubleshooting

### "Login failed - unexpected response"

- Check Garmin credentials are correct
- Ensure no MFA is enabled on Garmin account
- Try logging in via Garmin Connect web first

### "Not authenticated"

- Tokens may have expired
- Log out and log back in
- Check Xcode console for token refresh errors

### Empty API Responses

- Verify using `connectapi.garmin.com` (not `connect.garmin.com`)
- Check console for actual API response
- Ensure OAuth2 token has correct scopes

### App Expires After 7 Days

This is an Apple limitation with free developer accounts:
- Re-run from Xcode to reinstall
- Or purchase Apple Developer Program ($99/year)

### Build Errors

```bash
# Clean and rebuild
cd ios/App
rm -rf Pods Podfile.lock
pod install
```

---

## App Store Deployment

To distribute via TestFlight or App Store:

1. **Apple Developer Program** ($99/year required)
2. **Create App ID** in Apple Developer Portal
3. **Create Provisioning Profile** for distribution
4. **Archive in Xcode**: Product → Archive
5. **Upload to App Store Connect**
6. **Submit for Review**

Note: Garmin authentication uses their public SSO - no special API keys required.

---

## Architecture Reference

See [architecture.md](./architecture.md) for:
- Complete system architecture
- Recovery/Strain calculation formulas
- Data flow diagrams
