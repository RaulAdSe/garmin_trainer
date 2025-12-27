# WHOOP Dashboard: On-Device Mobile Deployment Plan

> **Goal**: Deploy the WHOOP Dashboard as a standalone iOS app with minimal infrastructure, running entirely on-device without a cloud backend.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture Analysis](#2-current-architecture-analysis)
3. [Architecture Decision](#3-architecture-decision)
4. [Implementation Phases](#4-implementation-phases)
5. [Technical Deep Dives](#5-technical-deep-dives)
6. [Security Considerations](#6-security-considerations)
7. [Testing Strategy](#7-testing-strategy)
8. [Deployment Guide](#8-deployment-guide)
9. [Future Enhancements](#9-future-enhancements)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Executive Summary

### The Decision: Fully On-Device Architecture

After analyzing the codebase and evaluating four architecture options, **on-device deployment** is the optimal choice for this project:

| Criteria | On-Device | Cloud Backend | Cloud DB Only |
|----------|-----------|---------------|---------------|
| Setup Time | 5-15 hours | 40-60 hours | 20-30 hours |
| Monthly Cost | $0 | $20-100 | $5-50 |
| Privacy | Excellent | Poor | Medium |
| Offline Support | Full | None | Partial |
| Maintenance | None | High | Medium |
| Complexity | Low | High | Medium |

### Why On-Device Works

1. **Single user application** - No need for multi-user infrastructure
2. **All calculations are client-side** - Recovery scores, trends, and analytics already computed in React
3. **Direct API access** - Garmin API can be called directly from mobile via CapacitorHttp
4. **Existing infrastructure** - Capacitor iOS project already configured and generated
5. **Privacy-first** - Health data never leaves the device

### What You Get

- Native iOS app installable on your phone
- All wellness data stored locally
- Works offline after initial sync
- Zero operational overhead
- Complete data privacy

---

## 2. Current Architecture Analysis

### 2.1 Tech Stack Overview

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                    │
├─────────────────────────────────────────────────────────┤
│  Framework:     Next.js 16.1.1 (React 19)               │
│  Build:         Static export (output: 'export')         │
│  Mobile:        Capacitor 8.x                            │
│  Storage:       @capacitor/preferences                   │
│  HTTP:          CapacitorHttp (native, bypasses CORS)    │
│  Styling:       Tailwind CSS 4                           │
│  Language:      TypeScript                               │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    iOS APP (Capacitor)                   │
├─────────────────────────────────────────────────────────┤
│  Location:      /frontend/ios/App/                       │
│  Target:        iOS 14+                                  │
│  Bundle ID:     com.whoopdashboard.app (configurable)    │
│  Web Dir:       out/ (Next.js static export)             │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
┌──────────────┐     OAuth2      ┌──────────────────┐
│   Garmin     │◄───────────────►│   Phone App      │
│  Connect API │                 │                  │
└──────────────┘                 │  ┌────────────┐  │
                                 │  │CredStorage │  │
       Wellness Data             │  │ (Keychain) │  │
            │                    │  └────────────┘  │
            ▼                    │                  │
┌──────────────────┐             │  ┌────────────┐  │
│  Sleep, HRV,     │────────────►│  │   Local    │  │
│  Stress, Activity│             │  │  Storage   │  │
└──────────────────┘             │  │(Preferences│  │
                                 │  └────────────┘  │
                                 │        │         │
                                 │        ▼         │
                                 │  ┌────────────┐  │
                                 │  │   React    │  │
                                 │  │ Components │  │
                                 │  └────────────┘  │
                                 └──────────────────┘
```

### 2.3 Current State Assessment

#### Already Complete
- [x] Capacitor 8.x configured (`capacitor.config.ts`)
- [x] iOS project generated (`/frontend/ios/`)
- [x] Next.js static export configured
- [x] CapacitorHttp integration for native HTTP
- [x] Garmin OAuth2 authentication flow
- [x] Preferences-based local storage
- [x] All UI components and calculations
- [x] Recovery score, strain, and trend calculations

#### Needs Work
- [ ] Secure credential storage (currently plain text)
- [ ] Robust token refresh mechanism
- [ ] Error handling and retry logic
- [ ] Offline state indicators
- [ ] iOS build testing on real device
- [ ] App Store preparation (optional)

### 2.4 File Structure

```
whoop-dashboard/
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js pages
│   │   ├── components/             # React components
│   │   └── services/
│   │       ├── garmin.ts           # Garmin API client
│   │       └── database.ts         # Local storage service
│   ├── ios/
│   │   └── App/
│   │       ├── App/
│   │       │   ├── AppDelegate.swift
│   │       │   └── Info.plist
│   │       ├── App.xcworkspace     # Open this in Xcode
│   │       └── Podfile             # iOS dependencies
│   ├── capacitor.config.ts         # Capacitor configuration
│   ├── next.config.ts              # Next.js configuration
│   └── package.json
└── cli/                            # Python CLI (not needed for mobile)
```

---

## 3. Architecture Decision

### 3.1 Options Evaluated

#### Option A: Full Cloud Backend
```
Phone → Your API Server → Garmin API → Your Database → Phone
```
- **Pros**: Centralized control, easy updates, multi-device sync
- **Cons**: $20-100/mo hosting, deployment complexity, privacy concerns, maintenance burden
- **Verdict**: Overkill for single-user app

#### Option B: Cloud Database Only (Firebase/Supabase)
```
Phone → Cloud DB (Supabase) + Direct Garmin API calls
```
- **Pros**: Real-time sync, backup included
- **Cons**: Still needs Garmin auth handling, adds complexity, $5-50/mo
- **Verdict**: Adds dependency without solving core problems

#### Option C: Fully On-Device (SELECTED)
```
Phone: [Secure Storage] → Garmin API → [Local Storage] → [UI]
```
- **Pros**: Zero cost, full privacy, offline-first, no ops
- **Cons**: Single device, manual backup needed
- **Verdict**: Perfect fit for personal health dashboard

#### Option D: Hybrid (Future Enhancement)
```
Phone: [Local + Secure Storage] + Optional iCloud Backup
```
- **Pros**: Best of both worlds
- **Cons**: More implementation time
- **Verdict**: Good future enhancement after MVP

### 3.2 Why On-Device is the Right Choice

1. **Data Sensitivity**: Health data should stay on your device
2. **Usage Pattern**: Single user, single device - no sync needed
3. **Cost Efficiency**: $0 vs $20-100/month for cloud
4. **Simplicity**: No servers to maintain, no deployments to manage
5. **Reliability**: Works without internet after initial sync
6. **Already Built**: 80% of the work is done

---

## 4. Implementation Phases

### Phase 1: MVP Deployment (Week 1)
> Get the current app running on your phone

#### Tasks

- [ ] **1.1** Verify development environment
  - Xcode 15+ installed
  - Node 18+ installed
  - CocoaPods installed (`sudo gem install cocoapods`)

- [ ] **1.2** Build and sync iOS project
  ```bash
  cd frontend
  npm install
  npm run build
  npx cap sync ios
  ```

- [ ] **1.3** Open in Xcode and configure signing
  ```bash
  npx cap open ios
  ```
  - Select your Apple Developer team
  - Update bundle identifier if needed
  - Select your physical device

- [ ] **1.4** Run on device
  - Connect iPhone via USB
  - Trust the computer on iPhone
  - Click Run in Xcode

- [ ] **1.5** Test basic functionality
  - Login with Garmin credentials
  - Sync wellness data
  - View dashboard metrics

#### Success Criteria
- App installs and launches on phone
- Can authenticate with Garmin
- Data displays in the UI

---

### Phase 2: Security Hardening (Week 2)
> Secure credential storage and improve reliability

#### Tasks

- [ ] **2.1** Install secure storage plugin
  ```bash
  npm install @capacitor-community/secure-storage
  npx cap sync ios
  ```

- [ ] **2.2** Create secure storage service
  ```typescript
  // src/services/secure-storage.ts
  import { SecureStorage } from '@capacitor-community/secure-storage';

  export const SecureCredentials = {
    async setPassword(password: string): Promise<void> {
      await SecureStorage.set({
        key: 'garmin_password',
        value: password
      });
    },

    async getPassword(): Promise<string | null> {
      try {
        const result = await SecureStorage.get({ key: 'garmin_password' });
        return result.value;
      } catch {
        return null;
      }
    },

    async clearAll(): Promise<void> {
      await SecureStorage.clear();
    }
  };
  ```

- [ ] **2.3** Migrate credential storage
  - Update `garmin.ts` to use SecureStorage for passwords
  - Keep Preferences for non-sensitive data (settings, cached data)

- [ ] **2.4** Implement proper token refresh
  ```typescript
  // Add to GarminClient class
  private refreshQueue: Promise<void> | null = null;

  async ensureValidToken(): Promise<string> {
    if (this.isTokenExpired()) {
      if (!this.refreshQueue) {
        this.refreshQueue = this.refreshToken()
          .finally(() => { this.refreshQueue = null; });
      }
      await this.refreshQueue;
    }
    return this.oauth2Token.access_token;
  }
  ```

- [ ] **2.5** Add retry logic for network failures
  ```typescript
  async fetchWithRetry<T>(
    fn: () => Promise<T>,
    retries = 3,
    delay = 1000
  ): Promise<T> {
    for (let i = 0; i < retries; i++) {
      try {
        return await fn();
      } catch (error) {
        if (i === retries - 1) throw error;
        await new Promise(r => setTimeout(r, delay * (i + 1)));
      }
    }
    throw new Error('Max retries exceeded');
  }
  ```

#### Success Criteria
- Passwords stored in iOS Keychain (not plain text)
- Token refresh works without user re-login
- Network errors retry automatically

---

### Phase 3: UX Polish (Week 3)
> Improve user experience and error handling

#### Tasks

- [ ] **3.1** Add offline indicator
  ```typescript
  // src/hooks/useNetworkStatus.ts
  import { Network } from '@capacitor/network';
  import { useState, useEffect } from 'react';

  export function useNetworkStatus() {
    const [isOnline, setIsOnline] = useState(true);

    useEffect(() => {
      Network.getStatus().then(status => setIsOnline(status.connected));

      const listener = Network.addListener('networkStatusChange', status => {
        setIsOnline(status.connected);
      });

      return () => { listener.remove(); };
    }, []);

    return isOnline;
  }
  ```

- [ ] **3.2** Add last sync indicator
  ```typescript
  // Store and display last successful sync time
  const [lastSync, setLastSync] = useState<Date | null>(null);

  // In UI: "Last synced: 5 minutes ago"
  ```

- [ ] **3.3** Improve error messages
  - Replace generic errors with user-friendly messages
  - Add "Retry" buttons for recoverable errors
  - Show helpful guidance for auth failures

- [ ] **3.4** Add pull-to-refresh
  ```typescript
  // Implement native pull-to-refresh for data sync
  ```

- [ ] **3.5** Add loading states
  - Skeleton loaders for data
  - Progress indicators for sync
  - Disabled states during operations

#### Success Criteria
- User always knows connection status
- Errors are clear and actionable
- App feels responsive and polished

---

### Phase 4: Production Ready (Week 4)
> Final hardening and optional App Store preparation

#### Tasks

- [ ] **4.1** Add data backup/export
  ```typescript
  // Export wellness data as JSON for backup
  async function exportData(): Promise<string> {
    const data = await getAllWellnessData();
    return JSON.stringify(data, null, 2);
  }
  ```

- [ ] **4.2** Add app icon and splash screen
  - Create 1024x1024 app icon
  - Generate all required sizes
  - Add to iOS project

- [ ] **4.3** Configure app metadata
  - Update `Info.plist` with proper descriptions
  - Add privacy usage descriptions
  - Set minimum iOS version

- [ ] **4.4** Test edge cases
  - First launch experience
  - Token expiration during use
  - Network loss during sync
  - App backgrounding/foregrounding

- [ ] **4.5** (Optional) App Store submission
  - Create App Store Connect listing
  - Generate screenshots
  - Write description and keywords
  - Submit for review

#### Success Criteria
- App handles all edge cases gracefully
- Data can be backed up and restored
- Ready for daily use or App Store

---

## 5. Technical Deep Dives

### 5.1 Garmin Authentication Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Authentication Flow                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. User enters email/password                               │
│              │                                               │
│              ▼                                               │
│  2. App calls Garmin SSO endpoint                           │
│     POST https://sso.garmin.com/sso/signin                  │
│              │                                               │
│              ▼                                               │
│  3. Garmin returns OAuth2 tokens                            │
│     {                                                        │
│       access_token: "...",                                   │
│       refresh_token: "...",                                  │
│       expires_in: 3600                                       │
│     }                                                        │
│              │                                               │
│              ▼                                               │
│  4. App stores tokens securely                              │
│     - access_token → Memory (ephemeral)                     │
│     - refresh_token → Keychain (persistent)                 │
│              │                                               │
│              ▼                                               │
│  5. App fetches wellness data                               │
│     GET /wellness-api/... with Bearer token                 │
│              │                                               │
│              ▼                                               │
│  6. On token expiry, use refresh_token                      │
│     POST /oauth/token with refresh_token                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Local Storage Strategy

```typescript
// Storage hierarchy

// 1. SECURE STORAGE (iOS Keychain)
// - Encrypted by OS
// - Survives app reinstall (optional)
// - Use for: passwords, refresh tokens
SecureStorage.set({ key: 'garmin_password', value: '...' });
SecureStorage.set({ key: 'refresh_token', value: '...' });

// 2. PREFERENCES (UserDefaults wrapper)
// - Fast key-value storage
// - JSON serialized
// - Use for: settings, cached data, wellness records
Preferences.set({ key: 'wellness_data', value: JSON.stringify(data) });
Preferences.set({ key: 'last_sync', value: timestamp });
Preferences.set({ key: 'user_settings', value: JSON.stringify(settings) });

// 3. MEMORY (Runtime only)
// - Lost on app close
// - Use for: access tokens, temporary state
this.accessToken = response.access_token;
```

### 5.3 Offline-First Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Offline-First Flow                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  App Launch                                                  │
│      │                                                       │
│      ▼                                                       │
│  Load cached data from Preferences                          │
│      │                                                       │
│      ▼                                                       │
│  Display UI immediately (cached data)                       │
│      │                                                       │
│      ▼                                                       │
│  Check network status                                        │
│      │                                                       │
│      ├─── Offline ──► Show "Offline" indicator              │
│      │                 Use cached data only                  │
│      │                                                       │
│      └─── Online ───► Background sync                       │
│                           │                                  │
│                           ▼                                  │
│                       Fetch new data                         │
│                           │                                  │
│                           ▼                                  │
│                       Merge with cache                       │
│                           │                                  │
│                           ▼                                  │
│                       Update UI                              │
│                           │                                  │
│                           ▼                                  │
│                       Save to Preferences                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.4 Error Handling Strategy

```typescript
// Centralized error handling

enum ErrorType {
  NETWORK = 'NETWORK',
  AUTH = 'AUTH',
  API = 'API',
  STORAGE = 'STORAGE',
  UNKNOWN = 'UNKNOWN'
}

interface AppError {
  type: ErrorType;
  message: string;
  userMessage: string;
  recoverable: boolean;
  retryAction?: () => Promise<void>;
}

const ERROR_MESSAGES: Record<ErrorType, string> = {
  NETWORK: 'Unable to connect. Check your internet connection.',
  AUTH: 'Session expired. Please log in again.',
  API: 'Garmin service unavailable. Try again later.',
  STORAGE: 'Unable to save data. Storage may be full.',
  UNKNOWN: 'Something went wrong. Please try again.'
};

function handleError(error: unknown): AppError {
  if (error instanceof TypeError && error.message.includes('network')) {
    return {
      type: ErrorType.NETWORK,
      message: error.message,
      userMessage: ERROR_MESSAGES.NETWORK,
      recoverable: true
    };
  }
  // ... handle other error types
}
```

---

## 6. Security Considerations

### 6.1 Credential Storage

| Data | Storage | Encryption | Persistence |
|------|---------|------------|-------------|
| Email | Preferences | None (not sensitive) | Survives reinstall |
| Password | Keychain | AES-256 (iOS) | Configurable |
| Access Token | Memory | N/A | Lost on app close |
| Refresh Token | Keychain | AES-256 (iOS) | Survives reinstall |
| Wellness Data | Preferences | None | Survives reinstall |

### 6.2 Security Best Practices

1. **Never log credentials**
   ```typescript
   // BAD
   console.log('Logging in with:', email, password);

   // GOOD
   console.log('Logging in with:', email, '[REDACTED]');
   ```

2. **Clear sensitive data on logout**
   ```typescript
   async function logout() {
     await SecureStorage.clear();
     this.accessToken = null;
     this.refreshToken = null;
   }
   ```

3. **Validate all API responses**
   ```typescript
   function validateWellnessData(data: unknown): WellnessData {
     // Validate structure before using
     if (!data || typeof data !== 'object') {
       throw new Error('Invalid wellness data');
     }
     // ... validate fields
   }
   ```

4. **Use HTTPS only**
   - CapacitorHttp enforces HTTPS by default
   - No HTTP fallback

### 6.3 Privacy Considerations

- All health data stored locally on device
- No data sent to third-party servers
- No analytics or tracking
- User can export/delete all data

---

## 7. Testing Strategy

### 7.1 Manual Testing Checklist

#### Authentication
- [ ] Fresh login with valid credentials
- [ ] Login with invalid credentials (error message)
- [ ] Login with expired session
- [ ] Logout and re-login
- [ ] Token refresh after 1 hour

#### Data Sync
- [ ] Initial sync (empty state)
- [ ] Incremental sync (existing data)
- [ ] Sync with network error (retry)
- [ ] Sync cancellation
- [ ] Large data sync (30+ days)

#### Offline Mode
- [ ] Launch app offline (cached data)
- [ ] Sync attempt offline (error message)
- [ ] Transition online → offline
- [ ] Transition offline → online

#### Edge Cases
- [ ] App backgrounded during sync
- [ ] App killed during sync
- [ ] Low storage warning
- [ ] iOS permission prompts

### 7.2 Device Testing Matrix

| Device | iOS Version | Status |
|--------|-------------|--------|
| iPhone 15 Pro | iOS 17 | Primary test device |
| iPhone 12 | iOS 16 | Secondary |
| iPhone SE | iOS 15 | Minimum supported |

### 7.3 Performance Benchmarks

| Operation | Target | Acceptable |
|-----------|--------|------------|
| App launch | < 2s | < 3s |
| Data sync (7 days) | < 5s | < 10s |
| UI navigation | < 100ms | < 200ms |
| Chart rendering | < 500ms | < 1s |

---

## 8. Deployment Guide

### 8.1 Development Build (For Testing)

```bash
# 1. Install dependencies
cd whoop-dashboard/frontend
npm install

# 2. Build Next.js static export
npm run build

# 3. Sync with iOS project
npx cap sync ios

# 4. Open in Xcode
npx cap open ios

# 5. In Xcode:
#    - Select your team in Signing & Capabilities
#    - Select your connected iPhone
#    - Click Run (⌘R)
```

### 8.2 Production Build (For Daily Use)

```bash
# 1. Build optimized production bundle
NODE_ENV=production npm run build

# 2. Sync with iOS
npx cap sync ios

# 3. In Xcode:
#    - Select "Any iOS Device" as target
#    - Product → Archive
#    - Distribute App → Development (for personal use)
#    - OR App Store Connect (for App Store)
```

### 8.3 Updating the App

```bash
# After code changes:
npm run build
npx cap sync ios
# Then run from Xcode
```

### 8.4 Troubleshooting Build Issues

**CocoaPods errors:**
```bash
cd ios/App
pod install --repo-update
```

**Signing errors:**
- Ensure Apple Developer account is added to Xcode
- Check bundle identifier is unique
- Verify provisioning profiles

**Build failures:**
```bash
# Clean and rebuild
rm -rf ios/App/Pods
rm -rf ios/App/App.xcworkspace
npx cap sync ios
cd ios/App && pod install
```

---

## 9. Future Enhancements

### 9.1 Short Term (1-2 months)

- [ ] **Background sync**: Fetch data periodically without opening app
- [ ] **Widgets**: iOS home screen widgets showing recovery score
- [ ] **Notifications**: Daily recovery summary notification
- [ ] **Apple Health integration**: Sync data to Apple Health

### 9.2 Medium Term (3-6 months)

- [ ] **iCloud backup**: Automatic backup of wellness data
- [ ] **Watch app**: Apple Watch companion app
- [ ] **Siri shortcuts**: "Hey Siri, what's my recovery score?"
- [ ] **Data export**: Export to CSV/PDF

### 9.3 Long Term (6+ months)

- [ ] **Android support**: Capacitor supports Android
- [ ] **Multi-account**: Support multiple Garmin accounts
- [ ] **AI insights**: Local ML for personalized recommendations
- [ ] **Social features**: Optional sharing with friends (would require backend)

---

## 10. Troubleshooting

### Common Issues

#### "App crashes on launch"
1. Check Xcode console for crash logs
2. Verify all Capacitor plugins are synced
3. Clean build folder (Cmd+Shift+K) and rebuild

#### "Cannot authenticate with Garmin"
1. Verify credentials are correct
2. Check network connectivity
3. Try logging out and back in
4. Check if Garmin servers are up

#### "Data not syncing"
1. Check network status indicator
2. Pull to refresh
3. Check last sync timestamp
4. Verify token hasn't expired

#### "App shows old data"
1. Pull to refresh
2. Check last sync time
3. Force close and reopen app
4. Clear cache in settings

#### "Storage full warning"
1. Export data backup
2. Clear old data (Settings → Clear Cache)
3. Check device storage

### Debug Mode

```typescript
// Enable debug logging
const DEBUG = true;

function log(...args: unknown[]) {
  if (DEBUG) {
    console.log('[WHOOP]', new Date().toISOString(), ...args);
  }
}
```

### Getting Help

1. Check Capacitor docs: https://capacitorjs.com/docs
2. Check Next.js docs: https://nextjs.org/docs
3. Garmin API issues: Check Garmin Connect status page

---

## Appendix A: Command Reference

```bash
# Development
npm run dev              # Start Next.js dev server
npm run build            # Build for production
npm run lint             # Run linter

# Capacitor
npx cap sync ios         # Sync web assets to iOS
npx cap open ios         # Open in Xcode
npx cap run ios          # Build and run on device

# iOS Specific
cd ios/App && pod install    # Install iOS dependencies
cd ios/App && pod update     # Update iOS dependencies

# Debugging
npx cap doctor           # Check Capacitor setup
```

## Appendix B: Environment Setup

### Required Software
- macOS 12+ (for Xcode)
- Xcode 15+ with iOS 17 SDK
- Node.js 18+
- npm 9+
- CocoaPods (`sudo gem install cocoapods`)

### Apple Developer Account
- Free account works for personal device testing
- Paid account ($99/year) needed for App Store or TestFlight

### Recommended VS Code Extensions
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- iOS Debug

---

## Appendix C: File Changes Summary

### Files to Create
- `src/services/secure-storage.ts` - Keychain wrapper
- `src/hooks/useNetworkStatus.ts` - Network monitoring
- `src/hooks/useOfflineData.ts` - Offline-first data handling

### Files to Modify
- `src/services/garmin.ts` - Add secure storage, token refresh
- `src/services/database.ts` - Add migration from Preferences to Keychain
- `src/app/page.tsx` - Add offline indicator, last sync time
- `capacitor.config.ts` - Add plugins configuration
- `package.json` - Add new dependencies

### Dependencies to Add
```json
{
  "@capacitor-community/secure-storage": "^5.0.0",
  "@capacitor/network": "^5.0.0"
}
```

---

*Document created: December 2024*
*Last updated: December 2024*
*Version: 1.0*
