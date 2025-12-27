# Getting Started

This guide will help you set up and run the Training Analyzer locally.

---

## Prerequisites

- **Python 3.11+** for the FastAPI backend
- **Node.js 18+** for the Next.js frontend
- **OpenAI API Key** for AI-powered features
- **Garmin Connect account** for activity data

---

## Installation

### 1. Clone/Navigate to the Project

```bash
cd /path/to/garmin_insights/training-analyzer
```

### 2. Install Python Dependencies

```bash
# Install in development mode
pip install -e ".[dev]"
```

This installs:
- FastAPI and Uvicorn
- OpenAI and LangGraph for LLM features
- Pydantic for data validation
- FIT-tool for Garmin export
- Pytest for testing

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 4. Configure Environment

Create a `.env` file in the `training-analyzer` directory:

```env
# Required: OpenAI API key
OPENAI_API_KEY=sk-your-key-here

# Garmin OAuth (for syncing activities)
GARMIN_EMAIL=your-garmin-email
GARMIN_PASSWORD=your-garmin-password

# Optional: API configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Optional: Database paths
TRAINING_DB_PATH=./training.db
WELLNESS_DB_PATH=../whoop-dashboard/wellness.db

# Optional: CORS (for frontend development)
CORS_ORIGINS=http://localhost:3000
```

---

## Running the Application

### Start the Backend (FastAPI)

```bash
cd training-analyzer
uvicorn training_analyzer.main:app --reload --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc

### Start the Frontend (Next.js)

```bash
cd training-analyzer/frontend
npm run dev
```

The dashboard will be available at http://localhost:3000

---

## Syncing Garmin Data

### First-Time Setup

1. Navigate to the dashboard at http://localhost:3000
2. Click "Connect Garmin" or go to Settings
3. Complete the OAuth flow to authorize access
4. Select date range and sync activities

### Via API

```bash
# Sync last 90 days of activities
curl -X POST http://localhost:8000/api/v1/garmin/sync \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-10-01",
    "end_date": "2024-12-27"
  }'
```

---

## Using the CLI

The Training Analyzer includes a powerful CLI for quick access:

```bash
# Check current training status
training-analyzer status

# View recent workouts
training-analyzer workouts --last 7

# Get today's readiness
training-analyzer readiness

# Analyze a specific workout
training-analyzer analyze <workout_id>

# View fitness metrics
training-analyzer metrics --days 30
```

---

## Core Features

### 1. Dashboard

The main dashboard provides:
- **Day Selector**: Navigate between days to view historical data
- **Period Toggle**: Switch between 14D, 30D, and 90D trend views
- **Metric Cards**: CTL, ATL, TSB, ACWR with trend indicators
- **Trend Charts**: Interactive visualizations of fitness metrics

### 2. Workout List

View and manage your workouts:
- **Filtering**: By type, date range, and search
- **Pagination**: Server-side pagination for large datasets
- **Analysis**: One-click AI analysis for each workout

### 3. Workout Analysis

Get AI-powered insights on your completed workouts:

**Via API:**
```bash
curl -X POST http://localhost:8000/api/v1/analysis/workout/12345
```

**Via Frontend:**
1. Navigate to "Workouts" page
2. Click on any workout
3. Click "Analyze" to generate AI commentary

**What you get:**
- Execution rating (Excellent/Good/Moderate/Needs Improvement)
- What went well
- Areas for improvement
- How it fits in your training context

### 4. Training Plan Generation

Create periodized plans based on your goals:

**Via API:**
```bash
curl -X POST http://localhost:8000/api/v1/plans/generate \
  -H "Content-Type: application/json" \
  -d '{
    "goal": {
      "race_date": "2025-06-15",
      "distance": "half",
      "target_time": "1:45:00"
    },
    "constraints": {
      "days_per_week": 5,
      "max_weekly_hours": 8
    }
  }'
```

**Via Frontend:**
1. Navigate to "Plans" > "New Plan"
2. Enter your race goal
3. Set your constraints
4. Click "Generate Plan"

**What you get:**
- Periodized structure (Base > Build > Peak > Taper)
- Week-by-week sessions
- Target paces and HR zones
- Load progression

### 5. Workout Design

Create structured workouts for your Garmin:

**Via API:**
```bash
curl -X POST http://localhost:8000/api/v1/workouts/design \
  -H "Content-Type: application/json" \
  -d '{
    "workout_type": "intervals",
    "duration_min": 55
  }'
```

**Download as FIT:**
```bash
curl http://localhost:8000/api/v1/workouts/{id}/fit --output workout.fit
```

**Workout Types:**
- `easy` - Recovery/base runs
- `tempo` - Sustained threshold effort
- `intervals` - VO2max intervals with recovery
- `threshold` - Cruise intervals
- `long` - Extended aerobic endurance
- `fartlek` - Speed play with varied intensity

### 6. Readiness Score

Check your daily training readiness:

**Via API:**
```bash
curl http://localhost:8000/api/v1/athlete/readiness
```

**Readiness Zones:**
| Zone | Score | Recommendation |
|------|-------|----------------|
| Green | 67-100 | Great day for quality training |
| Yellow | 34-66 | Moderate intensity OK |
| Red | 0-33 | Rest or very light activity |

---

## FIT File Export

Export structured workouts to your Garmin device:

### Method 1: USB Transfer

1. Design a workout via API or frontend
2. Download the FIT file
3. Connect Garmin device via USB
4. Copy file to `/Garmin/NewFiles/` on device
5. Safely eject and sync

### Method 2: Garmin Connect Import

1. Download the FIT file
2. Go to Garmin Connect web
3. Navigate to Training > Workouts
4. Click Import and select the FIT file

---

## Running Tests

The project includes 778 tests across 26 files:

```bash
# Run all tests
cd training-analyzer
pytest tests/ -v

# Run specific categories
pytest tests/agents/ -v    # Agent tests
pytest tests/api/ -v       # API integration tests
pytest tests/metrics/ -v   # Metric calculation tests
pytest tests/db/ -v        # Database tests

# With coverage
pytest tests/ --cov=src/training_analyzer --cov-report=html
```

---

## Configuration Options

### API Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `API_HOST` | 0.0.0.0 | Server bind address |
| `API_PORT` | 8000 | Server port |
| `DEBUG` | false | Enable debug logging |
| `CORS_ORIGINS` | localhost:3000 | Allowed frontend origins |

### LLM Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `OPENAI_API_KEY` | Required | Your OpenAI API key |
| `LLM_MODEL` | gpt-5-mini | Model for analysis |
| `LLM_FAST_MODEL` | gpt-5-nano | Model for quick summaries |

---

## Troubleshooting

### "OpenAI API key not found"

Ensure `.env` file exists with:
```env
OPENAI_API_KEY=sk-your-key-here
```

### "Database not found"

Check database paths in config:
```env
TRAINING_DB_PATH=./training.db
```

### "CORS error" in frontend

Ensure backend is running and CORS is configured:
```env
CORS_ORIGINS=http://localhost:3000
```

### Workout analysis is slow

First-time analysis calls the LLM. Subsequent requests are cached in the database.

### Garmin sync fails

1. Check your Garmin credentials in `.env`
2. Try re-authenticating via the OAuth flow
3. Check the API logs for specific errors

---

## Next Steps

- Read [Architecture](./architecture.md) for technical details
- Check [API Reference](./api-reference.md) for all endpoints
- See [Metrics Explained](./metrics-explained.md) for calculations
- Review [coaching_app_plan.md](./coaching_app_plan.md) for roadmap
