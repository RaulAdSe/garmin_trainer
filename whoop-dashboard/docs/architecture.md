# WHOOP Dashboard Architecture

This document explains the technical architecture and data flow of the WHOOP Dashboard application.

---

## Overview

The WHOOP Dashboard is a **WHOOP-style wellness dashboard** that transforms Garmin Connect data into actionable health insights. It follows the philosophy: **"Don't show data, tell me what to do."**

```
┌──────────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│   Garmin Connect     │────▶│   Python CLI      │────▶│   SQLite DB       │
│   (Data Source)      │     │   (Data Fetcher)  │     │   (wellness.db)   │
└──────────────────────┘     └───────────────────┘     └─────────┬─────────┘
                                                                  │
                                                                  ▼
                                                       ┌───────────────────┐
                                                       │   Next.js API     │
                                                       │   (Data Layer)    │
                                                       └─────────┬─────────┘
                                                                  │
                                                                  ▼
                                                       ┌───────────────────┐
                                                       │   React Frontend  │
                                                       │   (Dashboard UI)  │
                                                       └───────────────────┘
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Data Fetching** | Python 3.10+ | CLI to fetch data from Garmin Connect |
| **Data Storage** | SQLite | Local database (`wellness.db`) |
| **Backend API** | Next.js API Routes | Serve data to frontend |
| **Frontend** | React 19 + Next.js 16 | Dashboard UI |
| **Styling** | Tailwind CSS 4 | Utility-first CSS |
| **Database Access** | better-sqlite3 | Synchronous SQLite for Node.js |

---

## Project Structure

```
whoop-dashboard/
├── docs/                    # Documentation (you are here)
├── frontend/                # Next.js frontend application
│   ├── src/
│   │   └── app/
│   │       ├── api/         # API routes
│   │       │   └── wellness/
│   │       │       ├── today/route.ts    # Today's data endpoint
│   │       │       └── history/route.ts  # Historical data endpoint
│   │       ├── page.tsx     # Main dashboard page
│   │       ├── layout.tsx   # Root layout
│   │       └── globals.css  # Global styles
│   ├── package.json
│   └── tsconfig.json
├── src/
│   └── whoop_dashboard/
│       ├── __init__.py
│       └── cli.py           # Python CLI for data fetching
├── tests/
│   └── test_recovery.py     # Recovery calculation tests
├── pyproject.toml           # Python project config
├── VISION.md                # Product vision document
└── wellness.db              # SQLite database (generated)
```

---

## Data Flow

### 1. Data Fetching (Python CLI → SQLite)

The `whoop` CLI fetches data from Garmin Connect via the shared `garmin_client` library:

```bash
# Fetch today's data
whoop fetch

# Backfill last 7 days
whoop fetch --days 7

# Show today's recovery
whoop show
```

**Data fetched per day:**
- Sleep data (duration, stages, efficiency)
- HRV data (nightly average, weekly baseline, status)
- Stress data (body battery charged/drained, stress levels)
- Activity data (steps, calories, intensity minutes)

### 2. Data Storage (SQLite Schema)

The `wellness.db` database contains these tables:

| Table | Purpose |
|-------|---------|
| `daily_wellness` | Master table with date, resting HR |
| `sleep_data` | Sleep duration, stages (deep/REM/light), score |
| `hrv_data` | HRV last night average, weekly average, status |
| `stress_data` | Body battery levels, average stress |
| `activity_data` | Steps, goals, calories, intensity minutes |

### 3. API Layer (Next.js Routes)

Two API endpoints serve the frontend:

**`GET /api/wellness/today`**
- Returns today's (or most recent) wellness data
- Calculates personal baselines from last 30 days
- Computes recovery score, strain, insights
- Generates weekly summary with causality data

**`GET /api/wellness/history?days=N`**
- Returns N days of historical data
- Each day includes calculated baselines
- Used for trend charts and comparisons

### 4. Frontend (React Dashboard)

The single-page dashboard (`page.tsx`) provides:

- **Overview tab**: Recovery score, strain, daily stats, weekly insights
- **Recovery tab**: Recovery trend, contributing factors
- **Strain tab**: Strain target, breakdown, trend
- **Sleep tab**: Sleep stages, debt calculation, personalized targets

---

## Key Components

### Recovery Calculation

Recovery score (0-100%) is calculated from three weighted factors:

```typescript
// HRV Factor (1.5x weight) - Primary signal
hrvRatio = current_hrv / personal_7d_baseline
hrvScore = min(100, max(0, hrvRatio * 80 + 20))

// Sleep Factor (1.0x weight)
sleepRatio = actual_hours / personal_7d_baseline
sleepScore = min(100, max(0, sleepRatio * 85 + 15))

// Body Battery Factor (1.0x weight)
bbScore = body_battery_charged

// Weighted average
recovery = (hrvScore * 1.5 + sleepScore * 1.0 + bbScore * 1.0) / 3.5
```

### Strain Calculation

Strain score (0-21) uses a logarithmic scale:

```typescript
strain = 0
strain += min(8, steps / 2000)              // Steps contribution
strain += min(8, body_battery_drained / 12) // Energy expenditure
strain += min(5, intensity_minutes / 20)    // Active exercise
strain = min(21, strain)
```

### Personal Baselines

Unlike population averages, baselines are calculated from YOUR data:

```typescript
// Rolling averages from historical data
hrv_7d_avg = average(last 7 days of HRV values)
sleep_7d_avg = average(last 7 days of sleep hours)
rhr_7d_avg = average(last 7 days of resting HR)
```

### Direction Indicators

Each metric includes a direction indicator showing change from baseline:

```typescript
{
  direction: 'up' | 'down' | 'stable',
  change_pct: number,    // e.g., +12% from baseline
  baseline: number,      // Your 7-day average
  current: number        // Today's value
}
```

---

## Dependencies

### Python (Backend)

```toml
[project]
dependencies = [
    "garmin-client",  # Local shared package for Garmin API
]
```

### Node.js (Frontend)

```json
{
  "dependencies": {
    "better-sqlite3": "^12.5.0",  // SQLite access
    "next": "16.1.1",             // React framework
    "react": "19.2.3"             // UI library
  }
}
```

---

## Configuration

### Database Path

The frontend expects `wellness.db` one directory up from the frontend folder:

```typescript
const dbPath = path.join(process.cwd(), '..', 'wellness.db');
```

### Garmin Tokens

The CLI looks for Garmin authentication tokens in:

```
../shared/.garth_tokens/
```

---

## Development

### Running the Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

### Running the CLI

```bash
# From project root
pip install -e .
whoop fetch --days 14
whoop show
```

### Running Tests

```bash
cd whoop-dashboard
pytest tests/
```

