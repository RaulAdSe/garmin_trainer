# Reactive Training App - Implementation Plan

## Overview

A reactive, AI-powered training app built on top of the existing `training-analyzer` backend. The app provides workout analysis, training plan generation, and structured workout design with Garmin export capabilities.

**Key Technologies:**
- Frontend: Next.js 16 + React 19 + Tailwind CSS
- Backend: FastAPI + LangGraph
- LLM: OpenAI GPT-5-mini (complex analysis) / GPT-5-nano (quick tasks)
- Export: Garmin FIT SDK for structured workouts

---

## 1. System Architecture

```
+-------------------+      +------------------------+      +------------------+
|   NEXT.JS 16+     |      |   PYTHON BACKEND       |      |   DATA STORES    |
|   React 19        |      |   FastAPI + LangGraph  |      |                  |
+-------------------+      +------------------------+      +------------------+
|                   |      |                        |      |                  |
|  Pages/Routes:    |<---->|  /api/v1/              |<---->|  SQLite DBs:     |
|  - Dashboard      |      |    - athlete/context   |      |  - training.db   |
|  - Workouts       | HTTP |    - analysis/         |      |  - wellness.db   |
|  - Plans          | JSON |    - plans/            |      |                  |
|  - Goals          |      |    - workouts/         |      +------------------+
|  - Export         |      |    - export/           |      |                  |
|                   |      |                        |      |  Garmin Connect  |
|  Components:      |      +------------------------+      |  (via garth)     |
|  - WorkoutCard    |      |                        |      |                  |
|  - AthleteContext |      |  LLM Orchestration:    |      +------------------+
|  - PlanBuilder    |      |  LangGraph + Agents    |      |                  |
|  - FITExporter    |      |  - AnalysisAgent       |      |  OpenAI API      |
|  - ReadinessGauge |      |  - PlanAgent           |      |  (GPT-5 models)  |
|                   |      |  - WorkoutDesignAgent  |      |                  |
+-------------------+      +------------------------+      +------------------+
         ^                          ^
         |                          |
         v                          v
+-------------------------------------------------------------------+
|                    EXISTING MODULES (Extend)                       |
+-------------------------------------------------------------------+
|  training-analyzer/                                                 |
|    - metrics/: HRSS, TRIMP, CTL/ATL/TSB, ACWR, zones               |
|    - recommendations/: readiness, workout, explain                  |
|    - analysis/: goals, weekly, trends                               |
|    - services/: coach                                               |
|                                                                     |
|  shared/garmin_client/                                              |
|    - api/client.py: Garmin Connect data fetching                   |
|    - db/database.py: Wellness data persistence                     |
+-------------------------------------------------------------------+
```

---

## 2. Implementation Phases

### Phase 0: Foundation (Core Infrastructure)

**Goal:** Set up project structure, API routes, and athlete context pipeline.

#### Tasks:
1. Create new Next.js 16 app at `/reactive-training-app/`
2. Set up FastAPI backend with CORS for Next.js
3. Implement athlete context endpoint that aggregates:
   - Current CTL/ATL/TSB/ACWR from `training.db`
   - Readiness score from CoachService
   - HR zones from user profile
   - VDOT and race predictions from goals.py
4. Create `useAthleteContext` React hook
5. Build `AthleteContextDisplay` component (sidebar)
6. Configure OpenAI client with GPT-5-nano/mini routing

#### Deliverables:
- Working API at `/api/v1/athlete/context`
- React component showing athlete metrics
- LLM client with model selection

---

### Phase 1: Workout Analysis & Feedback (Priority 1)

**Goal:** AI commentary on completed workouts - the user's first priority.

#### Tasks:

1. **Create Analysis Agent (LangGraph)**
   ```python
   class AnalysisAgent:
       def analyze_workout(self, workout_id: str, context: AthleteContext) -> Analysis:
           # Uses GPT-5-mini for complex analysis
           pass
   ```

2. **Extend CoachService** to provide:
   - Detailed workout data (splits, HR zones, pace distribution)
   - Comparison to similar past workouts
   - Goal-pace relevance

3. **API Endpoints:**
   - `POST /api/v1/analysis/workout/{workout_id}` - Analyze single workout
   - `GET /api/v1/analysis/recent?limit=10` - Get recent with analysis
   - `POST /api/v1/analysis/batch` - Batch analyze multiple

4. **Frontend Components:**
   - `WorkoutCard` with expandable AI analysis
   - `WorkoutAnalysisFeed` for recent workouts
   - Streaming response display

#### Prompt Template:
```
System: You are an experienced running coach analyzing a workout.

Athlete Context:
- CTL: {ctl} | ATL: {atl} | TSB: {tsb}
- VDOT: {vdot} | Target Race: {race_goal}
- Training paces: Easy {easy_pace}, Tempo {tempo_pace}, Interval {interval_pace}
- HR Zones: Z1 {z1}, Z2 {z2}, Z3 {z3}, Z4 {z4}, Z5 {z5}

Workout Data:
{workout_json}

Provide:
1. Execution summary (2-3 sentences)
2. What went well
3. Areas for improvement
4. How this fits into their training
```

---

### Phase 2: Training Plan Generation (Priority 2)

**Goal:** Periodized plans based on goals and current fitness.

#### Tasks:

1. **Create Plan Agent (LangGraph)**
   - Takes: Goal race, current CTL, weeks available, constraints
   - Produces: Multi-week periodized plan
   - Uses GPT-5-mini for plan structure, GPT-5-nano for individual sessions

2. **Plan Data Structures:**
   ```python
   @dataclass
   class TrainingPlan:
       goal: RaceGoal
       weeks: List[TrainingWeek]
       periodization: str  # "linear", "reverse", "block"
       peak_week: int

   @dataclass
   class TrainingWeek:
       week_number: int
       phase: str  # "base", "build", "peak", "taper"
       target_load: float
       sessions: List[PlannedSession]
   ```

3. **API Endpoints:**
   - `POST /api/v1/plans/generate` - Generate new plan
   - `GET /api/v1/plans/active` - Get current plan
   - `PUT /api/v1/plans/{id}/adjust` - Modify plan based on performance
   - `POST /api/v1/plans/adapt` - AI-assisted plan adaptation

4. **Frontend Components:**
   - `PlanCalendar` - Week-by-week view
   - `PlanGenerator` - Goal input + plan generation
   - `WeeklyView` - Detailed week with sessions
   - `PlanProgress` - Compliance and adaptation tracking

---

### Phase 3: Workout Design + Garmin Export (Priority 3)

**Goal:** AI-generated structured workouts exportable to Garmin.

#### Tasks:

1. **Workout Design Agent:**
   ```python
   @dataclass
   class WorkoutInterval:
       type: str  # "warmup", "work", "recovery", "cooldown"
       duration_sec: Optional[int]
       distance_m: Optional[int]
       target_pace_range: Tuple[int, int]  # sec/km
       target_hr_range: Tuple[int, int]
       repetitions: int = 1

   @dataclass
   class StructuredWorkout:
       name: str
       description: str
       sport: str  # "running"
       intervals: List[WorkoutInterval]
       estimated_duration_min: int
       estimated_load: float
   ```

2. **FIT File Generation:**
   - Use `fit-python` or `fitparse` library
   - Generate FIT workout files per Garmin spec
   - Include target pace, HR zones, intervals

3. **API Endpoints:**
   - `POST /api/v1/workouts/design` - AI designs workout
   - `GET /api/v1/workouts/{id}/fit` - Download FIT file
   - `POST /api/v1/workouts/{id}/export-garmin` - Push to Garmin Connect

4. **Frontend Components:**
   - `WorkoutDesigner` - Interactive interval builder
   - `AIWorkoutSuggestions` - AI-generated workout options
   - `FITExportButton` - Download/push to Garmin
   - `IntervalVisualizer` - Visual representation of workout

---

## 3. LLM Integration Strategy

### Model Selection

| Use Case | Model | Rationale |
|----------|-------|-----------|
| Quick summaries (< 100 tokens output) | GPT-5-nano | Cost-effective for short responses |
| Workout analysis | GPT-5-mini | Needs reasoning about metrics |
| Plan structure generation | GPT-5-mini | Complex multi-week planning |
| Individual session descriptions | GPT-5-nano | Template-based, simple |
| Workout interval design | GPT-5-mini | Needs to understand progression |
| Daily briefing narrative | GPT-5-nano | Rule-based with narrative polish |

### Pricing Reference
- GPT-5-nano: $0.05/1M input, $0.40/1M output
- GPT-5-mini: $0.25/1M input, $2/1M output

### Athlete Context Injection

Every LLM call includes:
```json
{
  "athlete_context": {
    "fitness": {
      "ctl": 45.2,
      "atl": 52.1,
      "tsb": -6.9,
      "acwr": 1.15,
      "risk_zone": "optimal"
    },
    "physiology": {
      "max_hr": 185,
      "rest_hr": 48,
      "lthr": 165,
      "vdot": 52.3
    },
    "hr_zones": {
      "z1": [100, 125],
      "z2": [125, 145],
      "z3": [145, 162],
      "z4": [162, 175],
      "z5": [175, 185]
    },
    "training_paces": {
      "easy": "5:30-6:00/km",
      "tempo": "4:45-5:00/km",
      "threshold": "4:25-4:35/km",
      "interval": "4:00-4:15/km"
    },
    "race_goals": [
      {
        "distance": "marathon",
        "target": "3:29:59",
        "date": "2024-04-15",
        "weeks_out": 16
      }
    ],
    "readiness": {
      "score": 78,
      "zone": "green"
    }
  }
}
```

---

## 4. Module Breakdown

### Frontend Modules (Next.js + React)

| Module | Responsibility | Priority |
|--------|---------------|----------|
| `components/athlete-context/` | Display VO2max, race times, HR zones, CTL/ATL/TSB | P0 (Core) |
| `components/workout-analysis/` | Completed workout cards with AI commentary | P1 (Phase 1) |
| `components/training-plans/` | Periodized plan display, calendar view | P2 (Phase 2) |
| `components/workout-designer/` | AI workout builder with intervals | P3 (Phase 3) |
| `components/fit-export/` | FIT file generation + Garmin export | P3 (Phase 3) |
| `components/readiness/` | Readiness gauge, daily briefing | P0 (Core) |
| `hooks/use-athlete-context.ts` | React hook for context injection | P0 |
| `hooks/use-llm-stream.ts` | Streaming LLM responses | P1 |
| `lib/api-client.ts` | Type-safe API client | P0 |

### Backend Modules (FastAPI + LangGraph)

| Module | Responsibility | Priority |
|--------|---------------|----------|
| `api/routes/athlete.py` | Athlete context endpoint | P0 |
| `api/routes/analysis.py` | Workout analysis endpoints | P1 |
| `api/routes/plans.py` | Training plan generation | P2 |
| `api/routes/workouts.py` | Workout design + intervals | P3 |
| `api/routes/export.py` | FIT file generation | P3 |
| `agents/analysis_agent.py` | LangGraph agent for workout analysis | P1 |
| `agents/plan_agent.py` | LangGraph agent for plan generation | P2 |
| `agents/workout_agent.py` | LangGraph agent for workout design | P3 |
| `agents/orchestrator.py` | Multi-agent coordinator | P2 |
| `llm/providers.py` | GPT-5-nano/mini model selection | P0 |
| `llm/prompts.py` | System prompts with context injection | P0 |
| `fit/encoder.py` | FIT SDK file generation | P3 |

---

## 5. API Endpoint Design

### Core Endpoints

```
# Athlete Context
GET  /api/v1/athlete/context              # Full athlete context
GET  /api/v1/athlete/readiness            # Today's readiness
GET  /api/v1/athlete/fitness-metrics      # CTL/ATL/TSB history

# Workout Analysis (Phase 1)
POST /api/v1/analysis/workout/{id}        # Analyze single workout
GET  /api/v1/analysis/workout/{id}        # Get cached analysis
GET  /api/v1/analysis/recent              # Recent workouts with analysis
POST /api/v1/analysis/batch               # Batch analyze

# Training Plans (Phase 2)
POST /api/v1/plans/generate               # Generate new plan
GET  /api/v1/plans                        # List all plans
GET  /api/v1/plans/{id}                   # Get plan details
PUT  /api/v1/plans/{id}                   # Update plan
DELETE /api/v1/plans/{id}                 # Delete plan
POST /api/v1/plans/{id}/adapt             # AI-adapt based on performance

# Workout Design (Phase 3)
POST /api/v1/workouts/design              # AI design workout
GET  /api/v1/workouts/{id}                # Get workout details
GET  /api/v1/workouts/{id}/fit            # Download FIT file
POST /api/v1/workouts/{id}/export-garmin  # Push to Garmin

# Goals
GET  /api/v1/goals                        # List goals
POST /api/v1/goals                        # Create goal
GET  /api/v1/goals/{id}/progress          # Goal progress
```

---

## 6. File Structure

```
/Users/rauladell/garmin_insights/reactive-training-app/
├── README.md
├── docker-compose.yml
│
├── backend/
│   ├── pyproject.toml
│   ├── src/
│   │   └── reactive_training/
│   │       ├── __init__.py
│   │       ├── main.py                 # FastAPI app
│   │       ├── config.py               # Settings
│   │       │
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── deps.py             # Dependencies (DB, services)
│   │       │   └── routes/
│   │       │       ├── athlete.py
│   │       │       ├── analysis.py
│   │       │       ├── plans.py
│   │       │       ├── workouts.py
│   │       │       └── export.py
│   │       │
│   │       ├── agents/
│   │       │   ├── __init__.py
│   │       │   ├── base.py             # LangGraph base agent
│   │       │   ├── analysis_agent.py
│   │       │   ├── plan_agent.py
│   │       │   ├── workout_agent.py
│   │       │   └── orchestrator.py
│   │       │
│   │       ├── llm/
│   │       │   ├── __init__.py
│   │       │   ├── providers.py        # GPT-5 client setup
│   │       │   ├── prompts.py          # Prompt templates
│   │       │   └── context_builder.py  # Athlete context injection
│   │       │
│   │       ├── fit/
│   │       │   ├── __init__.py
│   │       │   ├── encoder.py          # FIT file generation
│   │       │   └── types.py            # FIT data structures
│   │       │
│   │       └── models/
│   │           ├── __init__.py
│   │           ├── plans.py            # Training plan models
│   │           └── workouts.py         # Structured workout models
│   │
│   └── tests/
│       ├── conftest.py
│       ├── api/
│       ├── agents/
│       ├── llm/
│       └── fit/
│
├── frontend/
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   │
│   ├── src/
│   │   ├── app/                        # Next.js App Router
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx                # Dashboard home
│   │   │   ├── workouts/
│   │   │   │   ├── page.tsx            # Workout list
│   │   │   │   └── [id]/page.tsx       # Workout detail + analysis
│   │   │   ├── plans/
│   │   │   │   ├── page.tsx            # Plan list
│   │   │   │   ├── new/page.tsx        # Create plan
│   │   │   │   └── [id]/page.tsx       # Plan detail
│   │   │   ├── goals/
│   │   │   │   └── page.tsx            # Goal tracking
│   │   │   └── design/
│   │   │       └── page.tsx            # Workout designer
│   │   │
│   │   ├── components/
│   │   │   ├── athlete/
│   │   │   │   ├── AthleteContextSidebar.tsx
│   │   │   │   ├── ReadinessGauge.tsx
│   │   │   │   ├── FitnessMetrics.tsx
│   │   │   │   └── HRZonesBadge.tsx
│   │   │   ├── workouts/
│   │   │   │   ├── WorkoutCard.tsx
│   │   │   │   ├── WorkoutAnalysis.tsx
│   │   │   │   ├── WorkoutList.tsx
│   │   │   │   └── StreamingAnalysis.tsx
│   │   │   ├── plans/
│   │   │   │   ├── PlanCalendar.tsx
│   │   │   │   ├── WeekView.tsx
│   │   │   │   ├── SessionCard.tsx
│   │   │   │   ├── PlanGenerator.tsx
│   │   │   │   └── PlanProgress.tsx
│   │   │   ├── design/
│   │   │   │   ├── WorkoutDesigner.tsx
│   │   │   │   ├── IntervalBuilder.tsx
│   │   │   │   ├── IntervalVisualizer.tsx
│   │   │   │   ├── PaceSelector.tsx
│   │   │   │   └── FITExportButton.tsx
│   │   │   └── ui/
│   │   │       ├── Card.tsx
│   │   │       ├── Badge.tsx
│   │   │       ├── Chart.tsx
│   │   │       └── Modal.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAthleteContext.ts
│   │   │   ├── useLLMStream.ts
│   │   │   ├── useWorkouts.ts
│   │   │   ├── usePlans.ts
│   │   │   └── useFITExport.ts
│   │   │
│   │   ├── lib/
│   │   │   ├── api-client.ts
│   │   │   ├── types.ts
│   │   │   └── utils.ts
│   │   │
│   │   └── styles/
│   │       └── globals.css
│   │
│   └── __tests__/                      # Jest tests
│
└── shared/
    └── types/                          # Shared TypeScript types
        ├── athlete.ts
        ├── workout.ts
        └── plan.ts
```

---

## 7. Testing Strategy

### Unit Tests

| Module | Test Focus | Location |
|--------|------------|----------|
| `training-analyzer/` | Metrics calculations, readiness, recommendations | Existing 200+ tests |
| `api/routes/` | Endpoint validation, error handling | `tests/api/` |
| `agents/` | Agent logic without LLM (mocked) | `tests/agents/` |
| `fit/encoder.py` | FIT file structure validity | `tests/fit/` |
| React components | Rendering, user interaction | `__tests__/` (Jest) |

### Integration Tests

| Test | Description |
|------|-------------|
| Athlete context pipeline | DB -> CoachService -> API -> Frontend |
| Analysis flow | Workout ID -> Context -> LLM -> Response |
| Plan generation | Goal -> Agent -> Plan structure |
| FIT export | Workout -> FIT file -> Valid structure |

### LLM Tests

```python
def test_workout_analysis_prompt_contains_context():
    """Ensure athlete context is properly injected into prompts."""
    context = AthleteContextBuilder(mock_coach).build_context(['fitness', 'zones'])
    prompt = WorkoutAnalysisPrompt(context, mock_workout)

    assert "CTL: 45.2" in prompt.render()
    assert "Zone 2:" in prompt.render()

def test_model_selection():
    """Ensure correct model is selected for task complexity."""
    simple_task = LLMTask(type="summary", complexity="low")
    complex_task = LLMTask(type="analysis", complexity="high")

    assert select_model(simple_task) == "gpt-5-nano"
    assert select_model(complex_task) == "gpt-5-mini"
```

### E2E Tests (Playwright)

- Dashboard loads with athlete context
- Workout analysis flows correctly
- Plan generation creates valid structure
- FIT export produces downloadable file

---

## 8. Critical Files to Modify/Extend

### Existing Files (Extend)

1. **`training-analyzer/src/training_analyzer/services/coach.py`**
   - Add `get_llm_context()` method for athlete context injection

2. **`training-analyzer/src/training_analyzer/analysis/goals.py`**
   - Add `get_training_paces()` for LLM context

3. **`training-analyzer/src/training_analyzer/recommendations/workout.py`**
   - Add `WorkoutStructure` dataclass for intervals

4. **`shared/garmin_client/api/client.py`**
   - Add `export_fit_workout()` method (if Garmin Connect API supports it)

---

## 9. Dependencies

### Backend (Python)
```toml
[project]
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "langgraph>=0.0.25",
    "langchain-openai>=0.0.5",
    "openai>=1.10.0",
    "fit-python>=0.0.5",  # FIT file encoding
    "pydantic>=2.5.0",
]
```

### Frontend (Node.js)
```json
{
  "dependencies": {
    "next": "^16.1.0",
    "react": "^19.0.0",
    "tailwindcss": "^4.0.0",
    "@tanstack/react-query": "^5.0.0",
    "recharts": "^2.10.0",
    "date-fns": "^3.0.0"
  }
}
```

---

## 10. Research References

- **Garmin FIT SDK**: https://developer.garmin.com/fit/cookbook/encoding-workout-files/
- **garmin-workouts CLI**: https://github.com/mkuthan/garmin-workouts
- **OpenAI GPT-5 Models**: https://platform.openai.com/docs/models/gpt-5-mini
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/

---

## Next Steps

1. Start with **Phase 0**: Set up project structure
2. Implement athlete context endpoint and React hook
3. Build basic dashboard with readiness and fitness metrics
4. Move to **Phase 1**: Workout analysis with LangGraph agent
