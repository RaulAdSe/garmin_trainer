# Training Analyzer - Structure Cleanup & Verification

**Date:** 2025-12-26  
**Branch:** `workout-analysis`

---

## Summary

Cleaned up the `training-analyzer` project structure and fixed all import issues after a previous reorganization. The app now has a flat layout and all 381 tests pass.

---

## What the App Does

**Training Analyzer** is an AI-powered workout analysis and coaching application that transforms raw Garmin activity data into actionable training insights. Think of it as a personal running coach that:

1. **Understands your fitness level** from your training history
2. **Tells you what to do today** based on fatigue and recovery
3. **Analyzes every workout** with AI-powered feedback
4. **Creates training plans** for your race goals
5. **Designs workouts** you can export directly to your Garmin watch

---

## How It Works

### The Big Picture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Garmin Connect │────▶│   n8n Workflow   │────▶│   SQLite DB     │
│   (your watch)  │     │   (auto-sync)    │     │  (training.db)  │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌─────────────────────────────────┼─────────────────────────────────┐
                        │                                 ▼                                 │
                        │  ┌──────────────────────────────────────────────────────────┐    │
                        │  │                    EnrichmentService                      │    │
                        │  │  • Calculates HRSS (heart rate stress score)             │    │
                        │  │  • Calculates TRIMP (training impulse)                   │    │
                        │  │  • Determines HR zone distribution (Z1-Z5)               │    │
                        │  └──────────────────────────────────────────────────────────┘    │
                        │                                 │                                 │
                        │                                 ▼                                 │
                        │  ┌──────────────────────────────────────────────────────────┐    │
                        │  │                      CoachService                         │    │
                        │  │  • Computes CTL/ATL/TSB (fitness-fatigue model)          │    │
                        │  │  • Calculates readiness score (GO/MODERATE/RECOVER)      │    │
                        │  │  • Generates daily recommendations                        │    │
                        │  └──────────────────────────────────────────────────────────┘    │
                        │                                 │                                 │
                        │                    Training Analyzer Backend                      │
                        └─────────────────────────────────┼─────────────────────────────────┘
                                                          │
                           ┌──────────────────────────────┼──────────────────────────────┐
                           ▼                              ▼                              ▼
                    ┌─────────────┐              ┌─────────────┐              ┌─────────────┐
                    │   CLI       │              │  REST API   │              │  Frontend   │
                    │  (Rich)     │              │  (FastAPI)  │              │  (Next.js)  │
                    └─────────────┘              └─────────────┘              └─────────────┘
```

### Step-by-Step Flow

#### 1. Data Ingestion
- **n8n workflow** syncs activities from Garmin Connect API daily
- Raw data includes: duration, distance, heart rate, pace, GPS

#### 2. Enrichment (the magic)
When you run `training-analyzer enrich`:
- **HRSS** = Training load based on HR zones and duration
- **TRIMP** = Banister's training impulse formula
- **Zone %** = Time in each HR zone (Z1-Z5)

#### 3. Fitness Modeling
The app calculates your **fitness-fatigue model** daily:
- **CTL** (Chronic Training Load) = 42-day exponential average → your fitness
- **ATL** (Acute Training Load) = 7-day exponential average → your fatigue
- **TSB** (Training Stress Balance) = CTL - ATL → your "form"
- **ACWR** = ATL/CTL → injury risk (sweet spot: 0.8-1.3)

#### 4. Daily Recommendation
Based on TSB and recent load, the app decides:
- **🟢 GO** (TSB > 5): You're fresh, hit it hard
- **🟡 MODERATE** (-10 < TSB < 5): Steady training
- **🔴 RECOVER** (TSB < -10): You're fatigued, easy day

#### 5. AI Analysis
When you analyze a workout:
- LLM receives: workout data + athlete context + similar past workouts
- LLM returns: summary, what worked, observations, recommendations, execution rating

---

## Core Features (Detailed)

### 1. Workout Analysis (LLM-powered)
```
POST /api/v1/analysis/workout/{activity_id}
```
- AI reads your workout metrics (pace, HR, zones, duration)
- Compares to your recent similar workouts
- Considers your current fatigue level (TSB)
- Returns structured feedback:
  - **Summary**: "Strong tempo run with consistent pacing"
  - **What worked**: ["Held target pace", "Negative split"]
  - **Observations**: ["Cardiac drift in last 10 min"]
  - **Recommendations**: ["Longer warmup next time"]
  - **Rating**: GOOD

### 2. Training Metrics
| Metric | Formula | What It Means |
|--------|---------|---------------|
| CTL | 42-day exp avg of daily load | Your aerobic fitness |
| ATL | 7-day exp avg of daily load | Your recent fatigue |
| TSB | CTL - ATL | Your freshness/form |
| ACWR | ATL / CTL | Injury risk indicator |
| HRSS | f(HR zones, duration) | Training stress per workout |

### 3. Training Plan Generation
```
POST /api/v1/plans/generate
{
  "goal": { "race_date": "2025-04-15", "distance": "marathon", "target_time": "3:30:00" },
  "constraints": { "days_per_week": 5, "long_run_day": "sunday" }
}
```
- Calculates weeks until race
- Selects periodization type (linear/block/reverse)
- Distributes phases: BASE → BUILD → PEAK → TAPER
- Generates weekly sessions respecting constraints
- Outputs full plan with target paces and loads

### 4. Workout Design + FIT Export
```
POST /api/v1/workouts/design
{ "workout_type": "tempo", "duration_min": 50 }
```
- Creates structured workout with intervals:
  - Warmup (10 min easy)
  - Work (20 min @ tempo pace)
  - Cooldown (10 min easy)
- Each interval has: duration, target pace range, target HR zone
- Export to FIT file → sync to Garmin watch

### 5. Readiness Score
```
GET /api/v1/athlete/readiness
→ { "score": 75, "zone": "green", "recommendation": "GO", "strain_target": 80-100 }
```
Uses:
- TSB (form)
- Recent sleep quality (if available)
- Days since last hard session
- Accumulated weekly load

---

## User Journeys

### Morning: "What should I do today?"
```bash
training-analyzer today
```
→ Shows readiness score, recommended workout type, strain target

### After a Run: "How did that go?"
1. Garmin syncs automatically
2. Open frontend → Workouts → Click workout
3. Hit "Analyze" → AI provides feedback

### Planning: "I have a marathon in 16 weeks"
1. Frontend → Goals → Add Marathon goal
2. Plans → Generate Plan
3. Review weeks, adjust constraints
4. Activate plan → Get daily workout suggestions

### Before a Workout: "Give me today's session"
1. Frontend → Design Workout
2. Select type (tempo/intervals/long)
3. Download FIT file
4. Sync to Garmin watch

---

## Database Usage

**Yes, the app uses SQLite** (`training.db`).

### Tables

| Table | Purpose |
|-------|---------|
| `user_profile` | Max HR, rest HR, threshold HR, age, gender, weight |
| `activity_metrics` | Enriched workouts with HRSS, TRIMP, zone distribution |
| `fitness_metrics` | Daily CTL, ATL, TSB, ACWR, risk zone |
| `race_goals` | Race targets with date, distance, target time |
| `weekly_summaries` | Aggregated weekly training stats and insights |

### Data Flow

```
Garmin Connect API → Raw Activities (n8n sync)
        ↓
   EnrichmentService → Calculates HRSS, TRIMP, zones
        ↓
   TrainingDatabase → Stores enriched metrics
        ↓
   CoachService → Provides readiness, recommendations
        ↓
   API/CLI → Serves to frontend or terminal
```

---

## Project Structure (After Cleanup)

```
training-analyzer/
├── training_analyzer/        # Python backend (MOVED from src/)
│   ├── agents/               # LLM agents (analysis, plan, workout)
│   ├── analysis/             # Goals, trends, weekly analysis
│   ├── api/                  # FastAPI routes
│   │   └── routes/           # athlete, analysis, plans, workouts, export
│   ├── db/                   # SQLite database layer
│   ├── fit/                  # FIT file encoder for Garmin
│   ├── llm/                  # LLM providers and prompts
│   ├── metrics/              # Fitness, load, zones calculations
│   ├── models/               # Pydantic/dataclass models
│   ├── recommendations/      # Readiness, workout recommendations
│   ├── services/             # Business logic (coach, enrichment, plans)
│   ├── cli.py                # Rich CLI (1000+ lines)
│   ├── config.py             # Settings
│   ├── exceptions.py         # Custom exception hierarchy
│   └── main.py               # FastAPI app entry point
├── frontend/                 # Next.js 16 + React 19
│   └── src/
│       ├── app/              # Pages (workouts, plans, goals, design)
│       ├── components/       # UI components
│       ├── hooks/            # Custom hooks (useWorkouts, usePlans, etc.)
│       └── lib/              # API client, types
├── tests/                    # 381 passing tests
├── docs/                     # Planning documents
├── training.db               # SQLite database
└── pyproject.toml            # Package config
```

---

## API Endpoints

| Route | Method | Description |
|-------|--------|-------------|
| `/api/v1/athlete/context` | GET | Full athlete context for LLM |
| `/api/v1/athlete/readiness` | GET | Today's readiness score |
| `/api/v1/analysis/workout/{id}` | POST | Analyze a workout with AI |
| `/api/v1/analysis/recent` | GET | Recent workouts with analysis |
| `/api/v1/plans/generate` | POST | Generate periodized training plan |
| `/api/v1/plans/{id}` | GET/PUT/DELETE | Plan CRUD |
| `/api/v1/plans/{id}/activate` | POST | Activate a plan |
| `/api/v1/workouts/design` | POST | Design structured workout |
| `/api/v1/workouts/{id}/fit` | GET | Download FIT file |
| `/api/v1/export/fit` | POST | Export workout to FIT |

---

## CLI Commands

```bash
training-analyzer setup --max-hr 185 --rest-hr 50
training-analyzer enrich --days 30      # Enrich activities with metrics
training-analyzer fitness --days 7      # Show fitness metrics
training-analyzer status                # Current training status
training-analyzer today                 # Today's recommendation
training-analyzer summary --days 7      # Weekly summary
training-analyzer why                   # Explain recommendation
training-analyzer trends --weeks 4      # Fitness trends
training-analyzer week --weeks 1        # Weekly analysis
training-analyzer goal                  # Race goals
training-analyzer dashboard             # Full dashboard
```

---

## Fixes Applied Today

### 1. Fixed module name imports (reactive_training → training_analyzer)
- 6 test files updated
- 1 source file updated (exception_handlers.py logger name)

### 2. Added missing model types
- `PlanStatus` enum (DRAFT, ACTIVE, PAUSED, COMPLETED, ARCHIVED)
- `CompletionStatus` enum (PENDING, COMPLETED, SKIPPED, PARTIAL)
- Type aliases for backward compatibility

### 3. Fixed plan_service.py imports
- Used aliases to map old names to new types

### 4. Added missing test fixtures
- `mock_athlete_context` and `mock_workout` fixtures

### 5. Simplified directory structure
- Moved `src/training_analyzer/` → `training_analyzer/`
- Removed unnecessary `src/` directory
- Updated `pyproject.toml` package paths

---

## Verification

```bash
# Backend tests
cd /Users/rauladell/garmin_insights/training-analyzer
python3 -m pytest tests/ --tb=short
# Result: 381 passed, 46 warnings

# Frontend build
cd frontend && npm run build
# Result: Compiled successfully
```

---

## Running the App

```bash
# Backend API
cd /Users/rauladell/garmin_insights/training-analyzer
python3 -m uvicorn training_analyzer.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev
# → http://localhost:3000

# CLI
training-analyzer status
```

---

## Tech Stack

- **Backend**: FastAPI, Pydantic, SQLite
- **Frontend**: Next.js 16, React 19, Tailwind CSS 4
- **AI**: OpenAI GPT-4, LangGraph agents
- **Export**: Garmin FIT SDK (custom encoder)
- **CLI**: Rich (tables, panels, progress bars)

