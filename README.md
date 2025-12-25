# Garmin Insights

Two apps powered by Garmin Connect data, sharing a common data extraction infrastructure.

## Apps

### 1. WHOOP Dashboard (`whoop-dashboard/`)
WHOOP-style health dashboard showing daily Recovery score, Sleep, Strain, and key metrics.

```bash
cd whoop-dashboard
pip install -e ../shared/garmin_client -e .
whoop fetch --days 7
whoop show
```

**Features:**
- Recovery score (0-100%) with green/yellow/red zones
- Sleep analysis (duration, stages, efficiency)
- HRV & Body Battery tracking
- Next.js web dashboard

### 2. Training Analyzer (`training-analyzer/`)
AI-powered workout analysis with per-activity coaching feedback.

```bash
cd training-analyzer
pip install -e ../shared/garmin_client -e .
training fetch
training analyze
```

**Features:**
- Per-workout AI coaching
- Pace & HR analysis
- Training load tracking
- Performance trends

## Shared Infrastructure (`shared/`)

Common Garmin Connect client used by both apps:
- Authentication (garth library)
- Data fetching (sleep, stress, HRV, activities)
- SQLite storage

## Project Structure

```
.
├── shared/
│   ├── garmin_client/       # Shared API client & database
│   │   ├── src/
│   │   │   ├── api/         # Garmin Connect API
│   │   │   └── db/          # SQLite models & storage
│   │   └── pyproject.toml
│   └── .garth_tokens/       # Auth tokens (gitignored)
│
├── whoop-dashboard/
│   ├── src/whoop_dashboard/ # Python backend
│   ├── frontend/            # Next.js dashboard
│   ├── tests/
│   └── pyproject.toml
│
├── training-analyzer/
│   ├── src/training_analyzer/
│   ├── tests/
│   └── pyproject.toml
│
├── n8n/                     # Automation workflows
└── .env                     # Credentials (gitignored)
```

## Setup

```bash
# Clone and setup
git clone <repo>
cd garmin_insights

# Create virtualenv
python3 -m venv .venv
source .venv/bin/activate

# Set credentials
echo 'GARMIN_EMAIL="your@email.com"' >> .env
echo 'GARMIN_PASSWORD="yourpassword"' >> .env
source .env && export GARMIN_EMAIL GARMIN_PASSWORD

# Install shared client
pip install -e shared/garmin_client

# Install and run whoop dashboard
pip install -e whoop-dashboard
whoop fetch --days 7
whoop show

# Run the web dashboard
cd whoop-dashboard/frontend
npm install
npm run dev
# Open http://localhost:3000
```

## Data Flow

```
Garmin Connect API
       │
       ▼
shared/garmin_client  ─────────────────────┐
       │                                   │
       ├─────────────────┐                 │
       ▼                 ▼                 ▼
whoop-dashboard    training-analyzer    n8n workflows
   (wellness)         (workouts)        (automation)
```
