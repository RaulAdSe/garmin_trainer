# trAIner Architecture

This document explains the technical architecture and data flow of the trAIner application.

---

## Overview

trAIner is an **AI-powered coaching application** that combines Garmin training data with a multi-agent LLM system to provide personalized workout analysis, training plan generation, and structured workout design.

```
┌──────────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│   Garmin Connect     │────▶│   SQLite DB       │────▶│   FastAPI Backend │
│   (OAuth + Sync)     │     │   (training.db)   │     │   (API + Services)│
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
| **Backend API** | FastAPI | REST API with async support, dependency injection |
| **AI/LLM** | OpenAI GPT-5-nano/mini + LangGraph | Multi-agent system for intelligent analysis |
| **Data Storage** | SQLite + Repository Pattern | Local database with clean data access |
| **Frontend** | Next.js 16 + React 19 | Modern React dashboard with App Router |
| **State Management** | React Query | Server state management with caching |
| **Styling** | Tailwind CSS 4 | Utility-first CSS framework |
| **Export** | FIT SDK (fit-tool) | Garmin workout export |
| **Validation** | Pydantic v2 | Data models and validation |
| **Testing** | Pytest | 778 tests across 26 files |

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
│       │       ├── garmin.py       # Garmin OAuth & sync
│       │       ├── export.py       # FIT export endpoints
│       │       ├── plans.py        # Plan management endpoints
│       │       └── workouts.py     # Workout design & listing
│       ├── db/                     # Database layer
│       │   ├── database.py         # TrainingDatabase class
│       │   ├── repository.py       # Repository pattern implementation
│       │   └── schema.py           # SQLite schema definitions
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
│       │   ├── garmin_service.py   # Garmin sync service
│       │   ├── plan_service.py     # Plan management
│       │   └── workout_service.py  # Workout operations
│       ├── cli.py                  # Command-line interface
│       ├── config.py               # App configuration (pydantic-settings)
│       ├── exceptions.py           # Custom exceptions
│       └── main.py                 # FastAPI app entry point
├── frontend/                       # Next.js frontend
│   └── src/
│       ├── app/                    # App router pages
│       │   ├── dashboard/          # Main dashboard
│       │   ├── workouts/           # Workout list & details
│       │   └── plans/              # Training plans
│       ├── components/             # React components
│       │   ├── dashboard/          # TrendCharts, MetricCards, DaySelector
│       │   ├── workouts/           # WorkoutCard, WorkoutList
│       │   └── ui/                 # Shared UI components
│       ├── hooks/                  # Custom hooks
│       │   ├── useWorkouts.ts      # Workout data with React Query
│       │   ├── usePlans.ts         # Plan management hooks
│       │   └── useDashboard.ts     # Dashboard data hooks
│       └── lib/                    # API client, types, utils
│           ├── api-client.ts       # Fetch wrapper with error handling
│           ├── types.ts            # TypeScript type definitions
│           └── utils.ts            # Utility functions
├── tests/                          # Comprehensive test suite
│   ├── agents/                     # Agent unit tests
│   ├── api/                        # API integration tests
│   ├── db/                         # Database tests
│   ├── metrics/                    # Metric calculation tests
│   └── services/                   # Service layer tests
├── docs/                           # Documentation
└── pyproject.toml                  # Python project config
```

---

## Core Components

### 1. Multi-Agent LLM System (LangGraph)

Three specialized agents handle different AI tasks using GPT-5-nano (fast) and GPT-5-mini (quality):

| Agent | Purpose | Model | Input | Output |
|-------|---------|-------|-------|--------|
| **AnalysisAgent** | Analyze completed workouts | GPT-5-mini | Workout data + context | Structured analysis with ratings |
| **PlanAgent** | Generate training plans | GPT-5-mini | Goal + constraints + fitness | Periodized multi-week plan |
| **WorkoutAgent** | Design structured workouts | GPT-5-nano | Workout type + duration | Interval structure with paces |

```python
# Example: Analysis Agent flow
workout_data → Build Context → Call LLM → Parse Response → WorkoutAnalysisResult
                    ↓
            [Fitness metrics, HR zones, recent workouts, goals]
```

### 2. Repository Pattern (Database Layer)

Clean separation of data access from business logic:

```python
# Repository pattern for data access
class WorkoutRepository:
    def get_by_id(self, workout_id: str) -> Workout | None
    def get_recent(self, limit: int = 10) -> list[Workout]
    def get_with_pagination(self, page: int, size: int) -> PaginatedResult
    def save_analysis(self, workout_id: str, analysis: Analysis) -> None

# Used by services
class WorkoutService:
    def __init__(self, repository: WorkoutRepository):
        self.repository = repository
```

### 3. Fitness Metrics (Banister Model)

The Fitness-Fatigue model calculates training load balance:

- **CTL** (Chronic Training Load): 42-day EWMA = "Fitness"
- **ATL** (Acute Training Load): 7-day EWMA = "Fatigue"
- **TSB** (Training Stress Balance): CTL - ATL = "Form"
- **ACWR** (Acute:Chronic Workload Ratio): ATL / CTL = Injury risk

### 4. Readiness System

Combines multiple factors into a 0-100 readiness score:

| Factor | Weight | Source |
|--------|--------|--------|
| HRV | 25% | Wellness data (HRV vs baseline) |
| Sleep | 20% | Sleep duration and quality |
| Body Battery | 15% | Garmin Body Battery |
| Stress | 10% | Inverse of stress level |
| Training Load | 20% | TSB and ACWR |
| Recovery Days | 10% | Days since hard workout |

### 5. Garmin Integration

OAuth-based authentication and activity sync:

```python
# OAuth flow
/api/v1/garmin/oauth/start → Redirect to Garmin → /api/v1/garmin/oauth/callback

# Sync activities
POST /api/v1/garmin/sync
{
  "start_date": "2024-01-01",
  "end_date": "2024-12-27"
}
```

### 6. FIT Export

Encodes structured workouts to Garmin FIT format:

```python
StructuredWorkout → FITEncoder → .fit file → Garmin device
```

Supports:
- Warmup, work, recovery, cooldown intervals
- Target HR zones and paces
- Repeat sets

---

## Frontend Architecture

### React Query State Management

Server state is managed with React Query for automatic caching and refetching:

```typescript
// Workout data hook with pagination
function useWorkouts(filters: WorkoutFilters) {
  return useQuery({
    queryKey: ['workouts', filters],
    queryFn: () => apiClient.getWorkouts(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Mutation for workout analysis
function useAnalyzeWorkout() {
  return useMutation({
    mutationFn: (workoutId: string) => apiClient.analyzeWorkout(workoutId),
    onSuccess: () => queryClient.invalidateQueries(['workouts']),
  });
}
```

### Component Architecture

```
Dashboard Page
├── DaySelector (date navigation)
├── PeriodToggle (14D/30D/90D)
├── MetricCards (CTL, ATL, TSB, ACWR)
└── TrendCharts (interactive charts)

Workouts Page
├── WorkoutList
│   ├── FilterBar (search, type, date range)
│   ├── WorkoutCard[] (individual workouts)
│   └── Pagination
└── WorkoutDetail
    ├── WorkoutSummary
    ├── AnalysisPanel
    └── SplitsTable
```

---

## Data Flow

### Garmin Sync Flow

```
1. User initiates OAuth flow
2. Redirect to Garmin Connect for authorization
3. Callback with authorization code
4. Exchange for access token
5. Fetch activities for date range
6. Transform and store in training.db
7. Calculate fitness metrics
8. Frontend refreshes data
```

### Workout Analysis Flow

```
1. User selects workout from list
2. Frontend calls POST /api/v1/analysis/workout/{id}
3. API checks for cached analysis in DB
4. If not cached:
   a. API gets workout data from training.db
   b. API builds athlete context (fitness, goals, zones)
   c. AnalysisAgent receives workout + context
   d. LLM generates structured analysis
   e. Analysis stored in DB
5. Response returned to frontend
6. Frontend displays analysis with ratings
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

---

## API Architecture

### Route Organization

```
/api/v1/
├── garmin/
│   ├── GET /oauth/start         # Start OAuth flow
│   ├── GET /oauth/callback      # OAuth callback
│   ├── POST /sync               # Sync activities
│   └── GET /status              # Sync status
├── athlete/
│   ├── GET /context             # Full athlete context for LLM
│   ├── GET /readiness           # Today's readiness score
│   └── GET /fitness-metrics     # CTL/ATL/TSB history
├── workouts/
│   ├── GET /                    # List with pagination
│   ├── GET /{id}                # Get workout details
│   ├── POST /design             # Design structured workout
│   ├── GET /{id}/fit            # Download FIT file
│   └── POST /quick/{type}       # Quick workout generation
├── analysis/
│   ├── POST /workout/{id}       # Analyze a workout
│   ├── GET /workout/{id}        # Get cached analysis
│   ├── GET /recent              # Recent workouts with summaries
│   └── POST /batch              # Batch analyze multiple
├── plans/
│   ├── POST /generate           # Generate new plan
│   ├── GET /                    # List all plans
│   ├── GET /active              # Get active plan
│   ├── GET /{id}                # Get specific plan
│   ├── PUT /{id}                # Update plan
│   ├── POST /{id}/activate      # Set as active
│   └── POST /{id}/adapt         # AI-assisted adaptation
└── export/
    └── GET /{id}/fit            # FIT file export
```

### Dependency Injection

```python
# FastAPI dependencies
def get_training_db() -> TrainingDatabase:
    """Get training database connection."""

def get_workout_repository(db = Depends(get_training_db)) -> WorkoutRepository:
    """Get workout repository."""

def get_coach_service(repo = Depends(get_workout_repository)) -> CoachService:
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

# Garmin OAuth
GARMIN_EMAIL=your-email
GARMIN_PASSWORD=your-password

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
    garmin_email: str | None = None
    garmin_password: str | None = None
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = ConfigDict(env_file=".env")
```

---

## Testing

### Test Structure

```
tests/
├── agents/                  # Agent unit tests (mocked LLM)
├── api/                     # API integration tests
├── db/                      # Database and repository tests
├── metrics/                 # Metric calculation tests
├── services/                # Service layer tests
└── conftest.py              # Shared fixtures
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific category
pytest tests/api/ -v

# With coverage
pytest tests/ --cov=src/training_analyzer --cov-report=html
```

---

## Security Considerations

1. **API Keys**: OpenAI key stored in environment, never in code
2. **CORS**: Configurable allowed origins
3. **Local Data**: All data stays local in SQLite
4. **No Auth**: Currently designed for single-user local use
5. **Garmin OAuth**: Tokens stored securely in shared directory

---

## Extension Points

The architecture is designed for extension:

1. **New Agents**: Add new LangGraph agents in `agents/`
2. **New Metrics**: Add calculation modules in `metrics/`
3. **New Export Formats**: Add encoders in `fit/` or new `export/`
4. **New Data Sources**: Add integrations in `services/`
5. **New Repositories**: Add data access patterns in `db/repository.py`
