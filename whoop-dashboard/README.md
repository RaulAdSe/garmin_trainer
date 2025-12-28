# WHOOP Dashboard

WHOOP-style wellness dashboard that transforms Garmin Connect data into actionable health insights. Follows the philosophy: **"Don't show data, tell me what to do."**

## Features

- **Recovery Score (0-100%)**: How ready your body is today based on HRV, sleep, and body battery
- **Strain Score (0-21)**: Logarithmic scale showing daily exertion from activities
- **Personal Baselines**: Compare to YOUR averages, not population norms
- **Actionable Insights**: GO / MODERATE / RECOVER decisions with explanations
- **Causality Engine**: Detects patterns and correlations in YOUR data
- **Sleep Analysis**: Tonight's personalized sleep target based on strain and debt
- **Trend Visualization**: 14-day trends with direction indicators
- **Native iOS App**: Standalone app with on-device Garmin authentication (no backend required)
- **Offline Support**: Works without internet after initial sync
- **Secure Storage**: iOS Keychain for credentials, IndexedDB for wellness data

## Project Structure

```
whoop-dashboard/
├── frontend/                       # Next.js 16 + React 19 frontend
│   ├── src/
│   │   └── app/
│   │       ├── api/               # API routes
│   │       │   └── wellness/
│   │       │       ├── today/route.ts    # Today's data endpoint
│   │       │       └── history/route.ts  # Historical data endpoint
│   │       ├── page.tsx           # Main dashboard page
│   │       ├── layout.tsx         # Root layout
│   │       └── globals.css        # Global styles
│   ├── ios/                       # Capacitor iOS project
│   │   └── App/                   # Xcode project
│   ├── capacitor.config.ts        # Capacitor configuration
│   └── package.json
├── src/
│   └── whoop_dashboard/
│       ├── __init__.py
│       ├── cli.py                 # Python CLI for data fetching
│       └── services/              # Data fetching services
├── tests/                         # Test suite (13 tests)
│   └── test_recovery.py           # Recovery calculation tests
├── docs/                          # Documentation
├── pyproject.toml                 # Python project config
├── VISION.md                      # Product vision document
└── wellness.db                    # SQLite database (generated)
```

## Quick Start

### 1. Install Python CLI

```bash
# Install shared Garmin client
cd ../shared/garmin_client
pip install -e .

# Install whoop-dashboard CLI
cd ../../whoop-dashboard
pip install -e .
```

### 2. Fetch Your Data

```bash
# Authenticate and fetch last 14 days
whoop fetch --days 14

# View today's recovery
whoop show

# Database statistics
whoop stats
```

### 3. Run the Dashboard

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

## CLI Commands

```bash
whoop fetch              # Fetch today's data
whoop fetch --days 7     # Backfill 7 days
whoop fetch --date 2024-12-25  # Specific date
whoop show               # Show today's recovery
whoop stats              # Database statistics
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/wellness/today` | Today's data with recovery, strain, insights |
| `GET /api/wellness/history?days=14` | Historical data for trends |

## Recovery Zones

| Zone | Range | Action |
|------|-------|--------|
| GREEN | 67-100% | Push hard, high intensity OK |
| YELLOW | 34-66% | Moderate effort, technique work |
| RED | 0-33% | Recovery focus, rest |

## Tech Stack

- **Frontend**: Next.js 16, React 19, Tailwind CSS 4
- **iOS**: Capacitor with static export
- **Data Fetching**: Python CLI with Garmin Connect API
- **Storage**: SQLite (`wellness.db`)
- **Database Access**: better-sqlite3

## iOS Native App

The iOS app is a **standalone native application** with on-device Garmin authentication:

```bash
cd frontend
npm install && npm run build
npx cap sync ios
npx cap open ios
# Build and run in Xcode (Cmd+R)
```

**Features:**
- Direct Garmin SSO login (OAuth1 with HMAC-SHA1 → OAuth2)
- Offline support with local IndexedDB storage
- Secure credential storage via iOS Keychain
- Auto token refresh

**Note:** Free Apple Developer accounts require reinstalling every 7 days.

See [docs/ios-deployment.md](docs/ios-deployment.md) for complete guide.

## Testing

```bash
cd whoop-dashboard
pytest tests/ -v
```

## Documentation

- [Architecture](docs/architecture.md) - Technical architecture and data flow
- [iOS Deployment](docs/ios-deployment.md) - Native iOS app setup and deployment
- [Getting Started](docs/getting-started.md) - Setup and usage guide
- [API Reference](docs/api-reference.md) - API documentation
- [Metrics Explained](docs/metrics-explained.md) - How metrics are calculated
