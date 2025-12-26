# Garmin Insights - LLM Context Document

This document provides comprehensive context about the Garmin Insights project for LLM consumption. Use this as the entry point to understand the codebase.

---

## Project Overview

**Garmin Insights** is a monorepo containing **two applications** that transform Garmin wearable data into actionable health and training insights. Both apps share a common data infrastructure but serve different purposes.

### The Two Apps

| App | Purpose | Philosophy |
|-----|---------|------------|
| **WHOOP Dashboard** | Daily wellness monitoring | "Don't show data, tell me what to do" |
| **Training Analyzer** | AI-powered coaching | "Train smarter with personalized AI" |

### How They Relate

```
                    Garmin Connect (wearable data)
                              │
                              ▼
                    shared/garmin_client
                     (common data layer)
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
      whoop-dashboard                 training-analyzer
    ┌─────────────────┐             ┌─────────────────┐
    │ Wellness Focus  │             │ Training Focus  │
    │ - Recovery      │             │ - Workouts      │
    │ - Sleep         │             │ - Plans         │
    │ - HRV           │             │ - CTL/ATL/TSB   │
    │ - Body Battery  │             │ - AI Analysis   │
    └─────────────────┘             └─────────────────┘
```

---

## App 1: WHOOP Dashboard

### What It Does

Transforms daily Garmin wellness data into a WHOOP-style dashboard with a single daily decision: **GO**, **MODERATE**, or **RECOVER**.

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Recovery Score** | 0-100% readiness calculated from HRV, sleep, body battery |
| **Strain Score** | 0-21 logarithmic scale of daily cardiovascular load |
| **Personal Baselines** | All metrics compared to YOUR averages, not population norms |
| **Causality Engine** | Detects patterns (e.g., "8k+ steps → +14% recovery") |

### Tech Stack

- **Backend**: Python CLI (`whoop` command)
- **Frontend**: Next.js 16 + React 19
- **Database**: SQLite (`wellness.db`)
- **API**: Next.js API routes

### Key Files

```
whoop-dashboard/
├── src/whoop_dashboard/
│   └── cli.py                    # CLI commands (fetch, show, stats)
├── frontend/src/
│   ├── app/page.tsx              # Main dashboard component (~1400 lines)
│   └── app/api/wellness/
│       ├── today/route.ts        # Today's data + baselines + causality
│       └── history/route.ts      # Historical data for charts
├── docs/
│   ├── architecture.md           # Technical architecture
│   ├── api-reference.md          # API endpoints
│   ├── getting-started.md        # Setup guide
│   └── metrics-explained.md      # How recovery/strain calculated
└── VISION.md                     # Product philosophy & roadmap
```

### Core Calculations

**Recovery Score:**
```
recovery = weighted_avg(
    hrv_score × 1.5,      # HRV vs 7-day baseline
    sleep_score × 1.0,    # Sleep vs personal need
    body_battery × 1.0    # Garmin Body Battery
)
```

**Recovery Zones:**
- 🟢 GREEN (67-100%): Push hard
- 🟡 YELLOW (34-66%): Moderate effort
- 🔴 RED (0-33%): Recovery focus

---

## App 2: Training Analyzer

### What It Does

AI-powered coaching app that analyzes workouts, generates training plans, designs structured workouts, and exports to Garmin devices.

### Key Concepts

| Concept | Description |
|---------|-------------|
| **CTL** | Chronic Training Load (42-day EWMA) = "Fitness" |
| **ATL** | Acute Training Load (7-day EWMA) = "Fatigue" |
| **TSB** | Training Stress Balance (CTL - ATL) = "Form" |
| **ACWR** | Acute:Chronic Workload Ratio = Injury risk |
| **Readiness** | 0-100 score combining recovery + training load |

### Tech Stack

- **Backend**: FastAPI (Python 3.11)
- **AI/LLM**: OpenAI GPT-4o + LangGraph agents
- **Frontend**: Next.js 16 + React 19
- **Database**: SQLite (`training.db`)
- **Export**: Garmin FIT format

### Key Files

```
training-analyzer/
├── src/training_analyzer/
│   ├── main.py                   # FastAPI app entry
│   ├── agents/
│   │   ├── analysis_agent.py     # Workout analysis LLM agent
│   │   ├── plan_agent.py         # Training plan generation
│   │   └── workout_agent.py      # Structured workout design
│   ├── api/routes/
│   │   ├── analysis.py           # POST /analysis/workout/{id}
│   │   ├── athlete.py            # GET /athlete/context
│   │   ├── plans.py              # POST /plans/generate
│   │   └── workouts.py           # POST /workouts/design
│   ├── metrics/
│   │   ├── fitness.py            # CTL/ATL/TSB calculations
│   │   ├── zones.py              # HR zone calculations
│   │   └── load.py               # HRSS/TRIMP
│   ├── fit/
│   │   └── encoder.py            # FIT file generation
│   └── recommendations/
│       └── readiness.py          # Readiness score calculation
├── frontend/src/
│   ├── app/                      # Pages (workouts, plans, goals)
│   ├── components/               # React components
│   └── hooks/                    # Custom hooks
├── docs/
│   ├── architecture.md           # Technical architecture
│   ├── api-reference.md          # REST API documentation
│   ├── getting-started.md        # Setup guide
│   ├── metrics-explained.md      # Fitness-Fatigue model details
│   ├── coaching_app_plan.md      # Implementation roadmap
│   └── runna_research.md         # Training methodology research
└── README.md                     # App overview
```

### Core Calculations

**Fitness-Fatigue Model (Banister):**
```
CTL_n = CTL_{n-1} × e^(-1/42) + load × (1 - e^(-1/42))
ATL_n = ATL_{n-1} × e^(-1/7) + load × (1 - e^(-1/7))
TSB = CTL - ATL
ACWR = ATL / CTL
```

**ACWR Risk Zones:**
- < 0.8: Undertrained
- 0.8-1.3: Optimal (sweet spot)
- 1.3-1.5: Caution
- > 1.5: Danger

---

## Shared Infrastructure

### garmin_client (`shared/garmin_client/`)

Common library for Garmin Connect API access:

```
shared/garmin_client/
├── src/garmin_client/
│   ├── api/
│   │   └── client.py       # Garmin Connect API wrapper
│   └── db/
│       ├── database.py     # SQLite operations
│       └── models.py       # Data models
├── baselines.py            # Personal baseline calculations
├── causality.py            # Pattern detection
└── insights.py             # Insight generation
```

### Data Sources

| Endpoint | Data | Used By |
|----------|------|---------|
| Daily Sleep | Duration, stages, efficiency | Both |
| HRV | Nightly average, weekly baseline | Both |
| Body Battery | Charged/drained amounts | WHOOP |
| Stress | Average stress level | WHOOP |
| Activities | Workouts with HR, pace, etc. | Training |

---

## Documentation Map

### For Understanding Each App

| Document | Location | Content |
|----------|----------|---------|
| WHOOP Architecture | `whoop-dashboard/docs/architecture.md` | Data flow, components |
| WHOOP Metrics | `whoop-dashboard/docs/metrics-explained.md` | Recovery, strain, sleep calculations |
| Training Architecture | `training-analyzer/docs/architecture.md` | Agents, API, services |
| Training Metrics | `training-analyzer/docs/metrics-explained.md` | CTL/ATL/TSB, ACWR, zones |

### For API Integration

| Document | Location |
|----------|----------|
| WHOOP API | `whoop-dashboard/docs/api-reference.md` |
| Training API | `training-analyzer/docs/api-reference.md` |

### For Vision/Roadmap

| Document | Location |
|----------|----------|
| WHOOP Vision | `whoop-dashboard/VISION.md` |
| Training Roadmap | `training-analyzer/docs/coaching_app_plan.md` |

---

## Key Patterns & Conventions

### Directory Structure (Both Apps)

```
app/
├── src/package_name/    # Python package (src layout)
├── frontend/            # Next.js app
├── docs/                # Documentation
├── tests/               # Test suite
├── *.db                 # SQLite database
└── pyproject.toml       # Python config
```

### API Patterns (Training Analyzer)

- REST API with FastAPI
- Pydantic models for validation
- Dependency injection for services
- In-memory caching for LLM results
- Streaming support for long operations

### Frontend Patterns (Both)

- Next.js App Router
- React Server Components where applicable
- Tailwind CSS for styling
- Custom hooks for data fetching
- Dark mode by default

---

## Quick Reference

### Running WHOOP Dashboard

```bash
cd whoop-dashboard
pip install -e ../shared/garmin_client -e .
whoop fetch --days 14
whoop show
# Frontend: cd frontend && npm run dev
```

### Running Training Analyzer

```bash
cd training-analyzer
pip install -e ".[dev]"
export OPENAI_API_KEY="your-key"
uvicorn training_analyzer.main:app --reload
# Frontend: cd frontend && npm run dev
```

---

## Summary for LLM

When working with this codebase:

1. **Two separate apps** sharing common data infrastructure
2. **WHOOP Dashboard** = Wellness focus (recovery, sleep, strain)
3. **Training Analyzer** = Training focus (workouts, plans, AI coaching)
4. Both use **SQLite** for local storage
5. Both have **Next.js frontends**
6. Training Analyzer uses **OpenAI + LangGraph** for AI features
7. All metrics use **personal baselines**, not population averages
8. Documentation is in each app's `docs/` folder

