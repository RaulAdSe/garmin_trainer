# Garmin Insights

Two apps powered by Garmin Connect data, sharing a common data extraction infrastructure.

---

## Apps

### 1. WHOOP Dashboard (`whoop-dashboard/`)

WHOOP-style health dashboard that transforms Garmin data into actionable decisions.

> **Philosophy:** "Don't show data, tell me what to do."

```bash
cd whoop-dashboard
pip install -e ../shared/garmin_client -e .
whoop fetch --days 14
whoop show
```

**Features:**
- **Recovery Score** (0-100%) with GO/MODERATE/RECOVER decisions
- **Strain Score** (0-21) with target zones based on recovery
- **Sleep Analysis** with personalized targets and debt tracking
- **HRV & Body Battery** with direction indicators vs baseline
- **Causality Engine** detecting patterns in YOUR data
- **Next.js Dashboard** with dark mode, responsive design

**Quick Start:**
```bash
# Fetch data and view in terminal
whoop fetch --days 14
whoop show

# Run web dashboard
cd frontend && npm install && npm run dev
# Open http://localhost:3000
```

📚 **[View Documentation](whoop-dashboard/docs/README.md)**

---

### 2. Training Analyzer (`training-analyzer/`)

AI-powered workout analysis and coaching app with LLM integration.

> **Philosophy:** Train smarter with personalized AI coaching.

```bash
cd training-analyzer
pip install -e ".[dev]"
export OPENAI_API_KEY="your-key"
uvicorn training_analyzer.main:app --reload
```

**Features:**
- **Workout Analysis** - AI commentary on completed workouts
- **Training Plans** - Periodized plans from race goals
- **Workout Design** - Structured intervals with FIT export
- **Readiness Score** - Daily training readiness (0-100)
- **Fitness Metrics** - CTL/ATL/TSB/ACWR tracking
- **FIT Export** - Sync workouts to Garmin devices

**Quick Start:**
```bash
# Backend API (port 8000)
cd training-analyzer
pip install -e ".[dev]"
uvicorn training_analyzer.main:app --reload

# Frontend (port 3000)
cd frontend && npm install && npm run dev
```

📚 **[View Documentation](training-analyzer/docs/README.md)**

---

## Shared Infrastructure (`shared/`)

Common Garmin Connect client used by both apps:

- **Authentication** - OAuth via garth library
- **Data Fetching** - Sleep, stress, HRV, activities, body battery
- **SQLite Storage** - Local database with models
- **Baselines** - Personal baseline calculations
- **Causality** - Pattern detection in wellness data

---

## Project Structure

```
garmin_insights/
├── shared/
│   ├── garmin_client/           # Shared API client & database
│   │   ├── src/garmin_client/
│   │   │   ├── api/             # Garmin Connect API
│   │   │   └── db/              # SQLite models & storage
│   │   └── pyproject.toml
│   └── .garth_tokens/           # Auth tokens (gitignored)
│
├── whoop-dashboard/
│   ├── src/whoop_dashboard/     # Python CLI
│   ├── frontend/                # Next.js dashboard
│   ├── docs/                    # Documentation
│   │   ├── architecture.md
│   │   ├── api-reference.md
│   │   ├── getting-started.md
│   │   └── metrics-explained.md
│   ├── tests/
│   ├── wellness.db              # SQLite database
│   └── pyproject.toml
│
├── training-analyzer/
│   ├── src/training_analyzer/   # FastAPI backend
│   │   ├── agents/              # LangGraph AI agents
│   │   ├── api/                 # REST endpoints
│   │   ├── metrics/             # CTL/ATL/TSB calculations
│   │   ├── fit/                 # Garmin FIT encoder
│   │   └── ...
│   ├── frontend/                # Next.js dashboard
│   ├── docs/                    # Documentation
│   │   ├── architecture.md
│   │   ├── api-reference.md
│   │   ├── getting-started.md
│   │   └── metrics-explained.md
│   ├── tests/
│   ├── training.db              # SQLite database
│   └── pyproject.toml
│
├── n8n/                         # Automation workflows
│   ├── workflows/
│   └── tables/
│
├── progress/                    # Development notes
└── .env                         # Credentials (gitignored)
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Garmin Connect account

### Installation

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

# === WHOOP Dashboard ===
pip install -e whoop-dashboard
whoop fetch --days 14
whoop show

# Run web dashboard
cd whoop-dashboard/frontend
npm install && npm run dev
# Open http://localhost:3000

# === Training Analyzer ===
cd ../training-analyzer
pip install -e ".[dev]"
export OPENAI_API_KEY="your-key"
uvicorn training_analyzer.main:app --reload
# Open http://localhost:8000/docs

# Run frontend
cd frontend
npm install && npm run dev
# Open http://localhost:3000
```

---

## Data Flow

```
                    Garmin Connect API
                           │
                           ▼
                  shared/garmin_client
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
   whoop-dashboard   training-analyzer   n8n workflows
     (wellness)        (workouts)        (automation)
          │                │
          ▼                ▼
    wellness.db       training.db
          │                │
          ▼                ▼
   Next.js Dashboard  FastAPI + Next.js
```

---

## Key Metrics

### WHOOP Dashboard

| Metric | Range | Purpose |
|--------|-------|---------|
| Recovery | 0-100% | Body readiness (GO/MODERATE/RECOVER) |
| Strain | 0-21 | Daily cardiovascular load |
| Sleep | Hours | Duration, stages, debt |
| HRV | ms | Autonomic nervous system balance |

### Training Analyzer

| Metric | Formula | Purpose |
|--------|---------|---------|
| CTL | 42-day EWMA | Chronic Training Load = Fitness |
| ATL | 7-day EWMA | Acute Training Load = Fatigue |
| TSB | CTL - ATL | Training Stress Balance = Form |
| ACWR | ATL / CTL | Injury risk ratio |

---

## Documentation

Each app has comprehensive documentation:

| App | Documentation |
|-----|---------------|
| **WHOOP Dashboard** | [docs/](whoop-dashboard/docs/README.md) |
| **Training Analyzer** | [docs/](training-analyzer/docs/README.md) |

Documentation includes:
- Architecture & data flow
- API reference
- Getting started guide
- Metrics explained

---

## Tech Stack

| Component | WHOOP Dashboard | Training Analyzer |
|-----------|-----------------|-------------------|
| Backend | Python CLI | FastAPI |
| Frontend | Next.js 16, React 19 | Next.js 16, React 19 |
| AI/LLM | - | OpenAI GPT-4o, LangGraph |
| Database | SQLite | SQLite |
| Styling | Tailwind CSS 4 | Tailwind CSS 4 |
| Export | - | Garmin FIT |

---

## License

Private project.
