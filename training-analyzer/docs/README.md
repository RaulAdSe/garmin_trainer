# Training Analyzer Documentation

Welcome to the Training Analyzer documentation. This folder contains comprehensive guides for understanding, setting up, and using the application.

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

Training Analyzer is an **AI-powered coaching application** that transforms Garmin training data into actionable insights.

### Core Features

| Feature | Description |
|---------|-------------|
| **Workout Analysis** | AI commentary on completed workouts |
| **Training Plans** | Periodized plans from race goals |
| **Workout Design** | Structured intervals with FIT export |
| **Readiness Score** | Daily training readiness (0-100) |
| **Fitness Metrics** | CTL/ATL/TSB/ACWR tracking |

### Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Python 3.11 |
| AI/LLM | OpenAI GPT-4o + LangGraph |
| Frontend | Next.js 16 + React 19 |
| Database | SQLite |
| Export | Garmin FIT format |

---

## Architecture Summary

```
Garmin Data → SQLite → FastAPI → LLM Agents → React Dashboard
                ↓          ↓           ↓
            Metrics    Analysis    FIT Export
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
| `/api/v1/athlete/context` | GET | Full athlete context |
| `/api/v1/athlete/readiness` | GET | Today's readiness |
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
| 🟢 Green | 67-100 | Quality training OK |
| 🟡 Yellow | 34-66 | Moderate effort |
| 🔴 Red | 0-33 | Rest/recovery |

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

# Optional
API_PORT=8000
DEBUG=false
TRAINING_DB_PATH=./training.db
```

---

## See Also

- **[README.md](../README.md)** - Project root documentation
- **[pyproject.toml](../pyproject.toml)** - Python dependencies
- **[tests/](../tests/)** - Test suite


