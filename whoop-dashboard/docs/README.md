# WHOOP Dashboard Documentation

Welcome to the WHOOP Dashboard documentation. This folder contains comprehensive guides for understanding, setting up, and using the dashboard.

---

## Quick Start

New to the project? Start here:

1. **[Getting Started](./getting-started.md)** - Installation and setup guide
2. **[VISION.md](../VISION.md)** - Product philosophy and roadmap

---

## Documentation Index

| Document | Description |
|----------|-------------|
| **[Getting Started](./getting-started.md)** | Installation, configuration, and basic usage |
| **[iOS Deployment](./ios-deployment.md)** | Native iOS app setup, authentication, and deployment |
| **[Architecture](./architecture.md)** | Technical architecture, data flow, and project structure |
| **[API Reference](./api-reference.md)** | REST API endpoints, request/response formats |
| **[Metrics Explained](./metrics-explained.md)** | Deep dive into recovery, strain, sleep, and HRV calculations |

---

## Project Overview

The WHOOP Dashboard transforms Garmin Connect data into actionable health insights, following the philosophy:

> **"Don't show data, tell me what to do."**

### Core Features

| Feature | Description |
|---------|-------------|
| **Recovery Score** | 0-100% readiness based on HRV, sleep, body battery |
| **Strain Score** | 0-21 logarithmic scale of daily exertion |
| **Personal Baselines** | Compared to YOUR averages, not population norms |
| **Actionable Insights** | GO / MODERATE / RECOVER decisions |
| **Causality Engine** | Detects patterns and correlations in YOUR data |
| **Sleep Targets** | Personalized sleep need based on strain and debt |
| **Native iOS App** | Standalone app with on-device Garmin authentication |
| **Offline Support** | Works without internet after initial sync |
| **Secure Storage** | iOS Keychain for credentials |

### Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 16 + React 19 |
| Styling | Tailwind CSS 4 |
| iOS App | Capacitor + CapacitorHttp |
| iOS Auth | OAuth1 (HMAC-SHA1) → OAuth2 |
| iOS Storage | IndexedDB (Dexie) + iOS Keychain |
| Web Data Fetching | Python CLI + garth library |
| Web Storage | SQLite (`wellness.db`) |
| Database Access | better-sqlite3 / Dexie |

---

## Architecture Summary

**Option A: Web Dashboard** (requires Python CLI)
```
Garmin Connect → Python CLI → SQLite → Next.js API → React Dashboard
     ↓              ↓           ↓           ↓            ↓
  Raw data      Fetch &     Store &     Serve &      Display &
               transform   persist     calculate    visualize
```

**Option B: iOS Native App** (standalone, no backend)
```
Garmin Connect ←→ iOS App (Capacitor) → IndexedDB
     ↓                    ↓                  ↓
  OAuth1/2         On-device auth      Local storage
                         ↓
                   iOS Keychain (secure)
```

---

## Quick Reference

### CLI Commands

```bash
whoop fetch              # Fetch today's data
whoop fetch --days 7     # Backfill 7 days
whoop show               # Show today's recovery
whoop stats              # Database stats
```

### Running the Dashboard

```bash
cd frontend
npm run dev
# Opens at http://localhost:3000
```

### iOS Native App

```bash
cd frontend
npm install && npm run build   # Build static export
npx cap sync ios               # Sync to iOS project
npx cap open ios               # Open in Xcode
# Build and run (Cmd+R)
```

**Features:** On-device Garmin login, offline support, iOS Keychain storage.
**Note:** Free Apple accounts require reinstall every 7 days.
See **[iOS Deployment Guide](./ios-deployment.md)** for complete setup.

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/wellness/today` | Today's data with insights |
| `GET /api/wellness/history?days=14` | Historical data |

---

## Recovery Zones

| Zone | Range | Action |
|------|-------|--------|
| GREEN | 67-100% | Push hard, high intensity OK |
| YELLOW | 34-66% | Moderate effort, technique work |
| RED | 0-33% | Recovery focus, rest |

---

## Strain Targets

Based on recovery, your target strain is:

| Recovery | Target Strain | Recommendation |
|----------|---------------|----------------|
| GREEN 67%+ | 14-21 | Intervals, racing, PRs |
| YELLOW 34-66% | 8-14 | Steady cardio, technique |
| RED <34% | 0-8 | Recovery activities only |

---

## See Also

- **[VISION.md](../VISION.md)** - Full product vision and roadmap
- **[pyproject.toml](../pyproject.toml)** - Python dependencies
- **[frontend/package.json](../frontend/package.json)** - Node.js dependencies

