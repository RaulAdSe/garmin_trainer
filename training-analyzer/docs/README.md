# trAIner Documentation

Welcome to the trAIner documentation. This folder contains comprehensive guides for understanding, setting up, and using the application.

---

## Quick Start

New to the project? Start here:

1. **[Getting Started](./getting-started.md)** - Installation and setup guide
2. **[API Reference](./api-reference.md)** - REST API endpoints

---

## Documentation Index

| Document | Description |
|----------|-------------|
| **[Getting Started](./getting-started.md)** | Installation, configuration, and basic usage |
| **[Architecture](./architecture.md)** | Technical architecture, data flow, and project structure |
| **[API Reference](./api-reference.md)** | REST API endpoints, request/response formats |
| **[Metrics Explained](./metrics-explained.md)** | Deep dive into CTL/ATL/TSB, ACWR, zones, readiness |
| **[Coaching App Plan](./coaching_app_plan.md)** | Implementation roadmap and feature plan |
| **[Runna Research](./runna_research.md)** | Training methodology research |

---

## Project Overview

trAIner is an **AI-powered coaching application** that transforms Garmin training data into actionable insights using a multi-agent LLM system.

### Core Features

| Feature | Description |
|---------|-------------|
| **Multi-Agent AI** | LangGraph agents using GPT-5-nano/mini for intelligent analysis |
| **Workout Analysis** | AI commentary on completed workouts with execution ratings |
| **Training Plans** | Periodized plans from race goals with adaptive adjustments |
| **Workout Design** | Structured intervals with FIT export for Garmin devices |
| **Readiness Score** | Daily training readiness (0-100) based on HRV, sleep, fatigue |
| **Fitness Metrics** | CTL/ATL/TSB/ACWR tracking with trend visualization |
| **Garmin Sync** | OAuth-based integration for automatic activity import |

### Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Python 3.11 |
| AI/LLM | OpenAI GPT-5-nano/mini + LangGraph |
| Frontend | Next.js 16 + React 19 + React Query |
| Database | SQLite with Repository Pattern |
| Styling | Tailwind CSS 4 |
| Export | Garmin FIT format |
| Testing | Pytest (778 tests across 26 files) |

---

## Architecture Summary

```
Garmin Connect → SQLite → FastAPI → LLM Agents → React Dashboard
      ↓              ↓          ↓           ↓            ↓
   OAuth         training.db   Services   Analysis    Trend Charts
                               + Repos    Plans       Day Selector
                                          Workouts    Period Toggle
```

---

## Quick Reference

### Running the App

```bash
# Backend (port 8000)
cd training-analyzer
uvicorn training_analyzer.main:app --reload

# Frontend (port 3000)
cd training-analyzer/frontend
npm run dev
```

### CLI Commands

```bash
training-analyzer status       # Training status
training-analyzer workouts     # Recent workouts
training-analyzer readiness    # Today's readiness
training-analyzer metrics      # CTL/ATL/TSB
```

### Key API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/garmin/oauth/start` | GET | Start Garmin OAuth |
| `/api/v1/garmin/sync` | POST | Sync activities |
| `/api/v1/athlete/context` | GET | Full athlete context |
| `/api/v1/athlete/readiness` | GET | Today's readiness |
| `/api/v1/workouts` | GET | List workouts (paginated) |
| `/api/v1/analysis/workout/{id}` | POST | Analyze workout |
| `/api/v1/plans/generate` | POST | Generate training plan |
| `/api/v1/workouts/design` | POST | Design workout |
| `/api/v1/workouts/{id}/fit` | GET | Download FIT file |

---

## Key Metrics

### Fitness-Fatigue Model

| Metric | Formula | Meaning |
|--------|---------|---------|
| **CTL** | 42-day EWMA | Chronic load = Fitness |
| **ATL** | 7-day EWMA | Acute load = Fatigue |
| **TSB** | CTL - ATL | Form (positive = fresh) |
| **ACWR** | ATL / CTL | Injury risk ratio |

### Readiness Zones

| Zone | Score | Action |
|------|-------|--------|
| Green | 67-100 | Quality training OK |
| Yellow | 34-66 | Moderate effort |
| Red | 0-33 | Rest/recovery |

### ACWR Risk Zones

| ACWR | Zone | Interpretation |
|------|------|----------------|
| < 0.8 | Undertrained | Increase gradually |
| 0.8-1.3 | **Optimal** | Sweet spot |
| 1.3-1.5 | Caution | Monitor closely |
| > 1.5 | Danger | Reduce load |

---

## Environment Variables

```env
# Required
OPENAI_API_KEY=sk-...

# Garmin OAuth
GARMIN_EMAIL=your-email
GARMIN_PASSWORD=your-password

# Optional
API_PORT=8000
DEBUG=false
TRAINING_DB_PATH=./training.db
```

---

## Testing

The project includes a comprehensive test suite with 778 tests across 26 files:

```bash
# Run all tests
pytest tests/ -v

# Run specific categories
pytest tests/agents/ -v    # Agent tests
pytest tests/api/ -v       # API tests
pytest tests/metrics/ -v   # Metric tests

# With coverage
pytest tests/ --cov=src/training_analyzer
```

---

## See Also

- **[README.md](../README.md)** - Project root documentation
- **[pyproject.toml](../pyproject.toml)** - Python dependencies
- **[tests/](../tests/)** - Test suite

