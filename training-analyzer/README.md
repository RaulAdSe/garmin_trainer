# Training Analyzer

AI-powered workout analysis and coaching app with Garmin integration. Provides personalized training insights, plan generation, workout design with FIT file export, and a comprehensive dashboard for tracking fitness metrics.

## Features

- **Multi-Agent AI System**: LangGraph-based agents using GPT-5-nano/mini for intelligent analysis
- **Workout Analysis**: AI-powered commentary on completed workouts with execution ratings
- **Training Metrics**: CTL/ATL/TSB, ACWR, HR zones, training load with trend visualization
- **Plan Generation**: Periodized training plans based on race goals
- **Workout Design**: Structured interval workouts with FIT export for Garmin devices
- **Readiness Score**: Daily training readiness based on fatigue, HRV, and recovery
- **Interactive Dashboard**: Real-time fitness trends, day selector, and period toggles (14D/30D/90D)
- **Garmin Sync**: OAuth-based integration with Garmin Connect for automatic data import

## Project Structure

```
training-analyzer/
├── src/
│   └── training_analyzer/          # Python backend package
│       ├── agents/                 # LangGraph agents (analysis, plan, workout)
│       ├── analysis/               # Goals, trends, weekly analysis
│       ├── api/                    # FastAPI routes
│       │   └── routes/
│       │       ├── analysis.py     # Workout analysis endpoints
│       │       ├── athlete.py      # Athlete context endpoints
│       │       ├── garmin.py       # Garmin sync & OAuth
│       │       ├── plans.py        # Plan management
│       │       └── workouts.py     # Workout design & listing
│       ├── db/                     # Database layer with repository pattern
│       │   ├── database.py         # TrainingDatabase class
│       │   └── repository.py       # Data access patterns
│       ├── fit/                    # FIT file encoder
│       ├── llm/                    # LLM providers, prompts, context building
│       ├── metrics/                # Fitness, load, zones calculations
│       ├── models/                 # Pydantic models
│       ├── recommendations/        # Readiness, workout recommendations
│       ├── services/               # Business logic services
│       ├── cli.py                  # Command-line interface
│       ├── config.py               # App configuration
│       └── main.py                 # FastAPI app entry point
├── frontend/                       # Next.js 16 + React 19 frontend
│   ├── src/
│   │   ├── app/                    # App router pages
│   │   │   ├── dashboard/          # Main dashboard with trends
│   │   │   ├── workouts/           # Workout list & analysis
│   │   │   └── plans/              # Training plan management
│   │   ├── components/             # React components
│   │   │   ├── dashboard/          # Dashboard-specific components
│   │   │   ├── workouts/           # WorkoutCard, WorkoutList
│   │   │   └── ui/                 # Shared UI components
│   │   ├── hooks/                  # Custom hooks (useWorkouts, usePlans)
│   │   └── lib/                    # API client, types, utils
│   └── package.json
├── tests/                          # Comprehensive test suite (778 tests)
│   ├── agents/                     # Agent tests
│   ├── api/                        # API route tests
│   ├── db/                         # Database tests
│   ├── metrics/                    # Metric calculation tests
│   └── services/                   # Service tests
├── docs/                           # Documentation
└── pyproject.toml
```

## Quick Start

### Backend (FastAPI)

```bash
cd training-analyzer

# Install dependencies
pip install -e ".[dev]"

# Set environment variables
export OPENAI_API_KEY="your-key"
export GARMIN_EMAIL="your-email"
export GARMIN_PASSWORD="your-password"

# Run the API server
uvicorn training_analyzer.main:app --reload --port 8000
```

### Frontend (Next.js)

```bash
cd training-analyzer/frontend

# Install dependencies
npm install

# Run the dev server
npm run dev
```

### CLI

```bash
# View training status
training-analyzer status

# List recent workouts
training-analyzer workouts --last 7

# Check readiness
training-analyzer readiness

# View fitness metrics
training-analyzer metrics --days 30
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/garmin/oauth/start` | GET | Start Garmin OAuth flow |
| `/api/v1/garmin/sync` | POST | Sync activities from Garmin |
| `/api/v1/athlete/context` | GET | Full athlete context for LLM |
| `/api/v1/athlete/readiness` | GET | Today's readiness score |
| `/api/v1/workouts` | GET | List workouts with pagination |
| `/api/v1/analysis/workout/{id}` | POST | Analyze a workout |
| `/api/v1/plans/generate` | POST | Generate training plan |
| `/api/v1/workouts/design` | POST | Design structured workout |
| `/api/v1/workouts/{id}/fit` | GET | Download FIT file |

## Configuration

Create a `.env` file:

```env
# Required
OPENAI_API_KEY=your-key

# Garmin OAuth
GARMIN_EMAIL=your-email
GARMIN_PASSWORD=your-password

# Optional
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
TRAINING_DB_PATH=./training.db
```

## Tech Stack

- **Backend**: FastAPI, Pydantic v2, SQLite with repository pattern
- **Frontend**: Next.js 16, React 19, React Query, Tailwind CSS 4
- **AI**: OpenAI GPT-5-nano/mini, LangGraph multi-agent system
- **Export**: Garmin FIT SDK (fit-tool)
- **Testing**: Pytest with 778 tests across 26 files

## Testing

```bash
cd training-analyzer
pytest tests/ -v

# Run specific test category
pytest tests/agents/ -v
pytest tests/api/ -v
pytest tests/metrics/ -v
```

## Documentation

- [Architecture](docs/architecture.md) - Technical architecture and data flow
- [API Reference](docs/api-reference.md) - Complete API documentation
- [Getting Started](docs/getting-started.md) - Setup and usage guide
- [Metrics Explained](docs/metrics-explained.md) - How metrics are calculated
- [Coaching App Plan](docs/coaching_app_plan.md) - Implementation roadmap
