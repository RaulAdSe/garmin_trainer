# Training Analyzer Architecture

This document explains the technical architecture and data flow of the Training Analyzer application.

---

## Overview

Training Analyzer is an **AI-powered coaching application** that combines Garmin training data with LLM intelligence to provide personalized workout analysis, training plan generation, and structured workout design.

```
┌──────────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│   Garmin Connect     │────▶│   SQLite DB       │────▶│   FastAPI Backend │
│   (Data Source)      │     │   (training.db)   │     │   (API + Services)│
└──────────────────────┘     └───────────────────┘     └─────────┬─────────┘
                                                                  │
                                      ┌───────────────────────────┼──────────────────┐
                                      │                           │                  │
                                      ▼                           ▼                  ▼
                              ┌───────────────┐         ┌───────────────┐   ┌───────────────┐
                              │ LLM Agents    │         │ Metrics       │   │ FIT Encoder   │
                              │ (LangGraph)   │         │ (Calculations)│   │ (Garmin Export)│
                              └───────────────┘         └───────────────┘   └───────────────┘
                                      │
                                      ▼
                              ┌───────────────────┐
                              │   Next.js Frontend │
                              │   (React Dashboard)│
                              └───────────────────┘
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend API** | FastAPI | REST API with async support |
| **AI/LLM** | OpenAI GPT-4o + LangGraph | Intelligent agents for analysis |
| **Data Storage** | SQLite | Local database (`training.db`) |
| **Frontend** | Next.js 16 + React 19 | Modern React dashboard |
| **Styling** | Tailwind CSS 4 | Utility-first CSS |
| **Export** | FIT SDK (fit-tool) | Garmin workout export |
| **Validation** | Pydantic v2 | Data models and validation |

---

## Project Structure

```
training-analyzer/
├── src/
│   └── training_analyzer/          # Python backend package
│       ├── agents/                 # LangGraph-based AI agents
│       │   ├── analysis_agent.py   # Workout analysis agent
│       │   ├── plan_agent.py       # Training plan generation
│       │   └── workout_agent.py    # Structured workout design
│       ├── analysis/               # Training analysis logic
│       │   ├── goals.py            # Race goals and VDOT calculations
│       │   ├── trends.py           # Performance trend detection
│       │   └── weekly.py           # Weekly summaries
│       ├── api/                    # FastAPI routes
│       │   └── routes/
│       │       ├── analysis.py     # Workout analysis endpoints
│       │       ├── athlete.py      # Athlete context endpoints
│       │       ├── export.py       # FIT export endpoints
│       │       ├── plans.py        # Plan management endpoints
│       │       └── workouts.py     # Workout design endpoints
│       ├── db/                     # Database layer
│       │   ├── database.py         # Database access
│       │   └── schema.py           # SQLite schema
│       ├── fit/                    # Garmin FIT file encoding
│       │   └── encoder.py          # FIT file generator
│       ├── llm/                    # LLM integration
│       │   ├── context_builder.py  # Athlete context for prompts
│       │   ├── prompts.py          # System/user prompts
│       │   └── providers.py        # OpenAI client wrapper
│       ├── metrics/                # Training metrics
│       │   ├── fitness.py          # CTL/ATL/TSB/ACWR calculations
│       │   ├── load.py             # Training load (HRSS/TRIMP)
│       │   └── zones.py            # HR zone calculations
│       ├── models/                 # Pydantic models
│       │   ├── analysis.py         # Analysis request/response
│       │   ├── plans.py            # Training plan models
│       │   └── workouts.py         # Structured workout models
│       ├── recommendations/        # Recommendation logic
│       │   ├── readiness.py        # Daily readiness score
│       │   └── workout.py          # Workout recommendations
│       ├── services/               # Business logic
│       │   ├── coach.py            # Coach service (daily briefing)
│       │   ├── plan_service.py     # Plan management
│       │   └── workout_service.py  # Workout operations
│       ├── cli.py                  # Command-line interface
│       ├── config.py               # App configuration
│       ├── exceptions.py           # Custom exceptions
│       └── main.py                 # FastAPI app entry point
├── frontend/                       # Next.js frontend
│   └── src/
│       ├── app/                    # App router pages
│       ├── components/             # React components
│       ├── hooks/                  # Custom hooks (useWorkouts, usePlans)
│       └── lib/                    # API client, types, utils
├── tests/                          # Test suite
├── docs/                           # Documentation
├── training.db                     # SQLite database
└── pyproject.toml                  # Python project config
```

---

## Core Components

### 1. LLM Agents (LangGraph)

Three specialized agents handle different AI tasks:

| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| **AnalysisAgent** | Analyze completed workouts | Workout data + context | Structured analysis with ratings |
| **PlanAgent** | Generate training plans | Goal + constraints + fitness | Periodized multi-week plan |
| **WorkoutAgent** | Design structured workouts | Workout type + duration | Interval structure with paces |

```python
# Example: Analysis Agent flow
workout_data → Build Context → Call LLM → Parse Response → WorkoutAnalysisResult
```

### 2. Fitness Metrics (Banister Model)

The Fitness-Fatigue model calculates training load balance:

- **CTL** (Chronic Training Load): 42-day EWMA = "Fitness"
- **ATL** (Acute Training Load): 7-day EWMA = "Fatigue"
- **TSB** (Training Stress Balance): CTL - ATL = "Form"
- **ACWR** (Acute:Chronic Workload Ratio): ATL / CTL = Injury risk

### 3. Readiness System

Combines multiple factors into a 0-100 readiness score:

| Factor | Weight | Source |
|--------|--------|--------|
| HRV | 25% | Wellness data (HRV vs baseline) |
| Sleep | 20% | Sleep duration and quality |
| Body Battery | 15% | Garmin Body Battery |
| Stress | 10% | Inverse of stress level |
| Training Load | 20% | TSB and ACWR |
| Recovery Days | 10% | Days since hard workout |

### 4. FIT Export

Encodes structured workouts to Garmin FIT format:

```python
StructuredWorkout → FITEncoder → .fit file → Garmin device
```

Supports:
- Warmup, work, recovery, cooldown intervals
- Target HR zones and paces
- Repeat sets

---

## Data Flow

### Workout Analysis Flow

```
1. User selects workout from list
2. Frontend calls POST /api/v1/analysis/workout/{id}
3. API gets workout data from training.db
4. API builds athlete context (fitness, goals, zones)
5. AnalysisAgent receives workout + context
6. LLM generates structured analysis
7. Response cached for future requests
8. Frontend displays analysis with ratings
```

### Plan Generation Flow

```
1. User provides goal (race, date, target time)
2. User sets constraints (days/week, max hours)
3. Frontend calls POST /api/v1/plans/generate
4. API calculates athlete context from current CTL
5. PlanAgent builds periodized structure
6. LLM generates week-by-week sessions
7. Plan stored and returned to frontend
8. User can activate, adapt, or export plan
```

### Workout Design Flow

```
1. User selects workout type (easy, tempo, intervals, etc.)
2. Frontend calls POST /api/v1/workouts/design
3. API builds athlete context (paces, HR zones)
4. WorkoutAgent creates interval structure
5. Workout stored with ID
6. User can download as FIT file
7. FIT synced to Garmin device
```

---

## API Architecture

### Route Organization

```
/api/v1/
├── athlete/
│   ├── GET /context          # Full athlete context for LLM
│   ├── GET /readiness        # Today's readiness score
│   └── GET /fitness-metrics  # CTL/ATL/TSB history
├── analysis/
│   ├── POST /workout/{id}    # Analyze a workout
│   ├── GET  /workout/{id}    # Get cached analysis
│   ├── GET  /recent          # Recent workouts with summaries
│   └── POST /batch           # Batch analyze multiple
├── plans/
│   ├── POST /generate        # Generate new plan
│   ├── GET  /                # List all plans
│   ├── GET  /active          # Get active plan
│   ├── GET  /{id}            # Get specific plan
│   ├── PUT  /{id}            # Update plan
│   ├── POST /{id}/activate   # Set as active
│   └── POST /{id}/adapt      # AI-assisted adaptation
├── workouts/
│   ├── POST /design          # Design structured workout
│   ├── GET  /{id}            # Get workout
│   ├── GET  /{id}/fit        # Download FIT file
│   └── POST /quick/{type}    # Quick workout generation
└── export/
    └── GET /{id}/fit         # FIT file export
```

### Dependency Injection

```python
# FastAPI dependencies
def get_training_db() -> TrainingDatabase:
    """Get training database connection."""

def get_coach_service() -> CoachService:
    """Get coach service with business logic."""

# Usage in routes
@router.get("/readiness")
async def get_readiness(coach_service = Depends(get_coach_service)):
    return coach_service.get_daily_briefing(date.today())
```

---

## Configuration

### Environment Variables

```env
# Required
OPENAI_API_KEY=sk-...

# Optional
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
CORS_ORIGINS=http://localhost:3000
TRAINING_DB_PATH=./training.db
WELLNESS_DB_PATH=../whoop-dashboard/wellness.db
```

### Config Loading

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # ... more settings

    class Config:
        env_file = ".env"
```

---

## Dependencies

### Python Backend

```toml
[project.dependencies]
fastapi = ">=0.109.0"
uvicorn = ">=0.27.0"
pydantic = ">=2.5.0"
openai = ">=1.10.0"
langgraph = ">=0.0.25"
langchain-openai = ">=0.0.5"
fit-tool = ">=0.9.13"
rich = ">=13.0"
python-dotenv = ">=1.0.0"
```

### Frontend

```json
{
  "dependencies": {
    "next": "16.x",
    "react": "19.x",
    "tailwindcss": "4.x"
  }
}
```

---

## Security Considerations

1. **API Keys**: OpenAI key stored in environment, never in code
2. **CORS**: Configurable allowed origins
3. **Local Data**: All data stays local in SQLite
4. **No Auth**: Currently designed for single-user local use

---

## Development

### Running the Backend

```bash
cd training-analyzer
pip install -e ".[dev]"
export OPENAI_API_KEY="your-key"
uvicorn training_analyzer.main:app --reload --port 8000
```

### Running the Frontend

```bash
cd training-analyzer/frontend
npm install
npm run dev
# Opens at http://localhost:3000
```

### Running Tests

```bash
cd training-analyzer
pytest tests/ -v
```

---

## Extension Points

The architecture is designed for extension:

1. **New Agents**: Add new LangGraph agents in `agents/`
2. **New Metrics**: Add calculation modules in `metrics/`
3. **New Export Formats**: Add encoders in `fit/` or new `export/`
4. **New Data Sources**: Add integrations in `services/`


