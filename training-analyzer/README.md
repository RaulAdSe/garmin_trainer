# Training Analyzer

AI-powered workout analysis and coaching app with Garmin integration. Provides personalized training insights, plan generation, and workout design with FIT file export.

## Features

- **Workout Analysis**: AI-powered commentary on completed workouts
- **Training Metrics**: CTL/ATL/TSB, ACWR, HR zones, training load
- **Plan Generation**: Periodized training plans based on race goals
- **Workout Design**: Structured interval workouts with FIT export
- **Readiness Score**: Daily training readiness based on fatigue and recovery

## Project Structure

```
training-analyzer/
├── src/training_analyzer/          # Python backend
│   ├── analysis/                   # Goals, trends, weekly analysis
│   ├── api/                        # FastAPI routes
│   │   └── routes/                 # Endpoint handlers
│   ├── agents/                     # LLM agents (analysis, plan, workout)
│   ├── db/                         # Database access
│   ├── fit/                        # FIT file encoder
│   ├── llm/                        # LLM providers and prompts
│   ├── metrics/                    # Fitness, load, zones calculations
│   ├── models/                     # Pydantic models
│   ├── recommendations/            # Readiness, workout recommendations
│   ├── services/                   # Business logic services
│   ├── cli.py                      # Command-line interface
│   ├── config.py                   # App configuration
│   ├── exceptions.py               # Custom exceptions
│   └── main.py                     # FastAPI app entry point
├── frontend/                       # Next.js 16 + React 19 frontend
│   ├── src/
│   │   ├── app/                    # App router pages
│   │   ├── components/             # React components
│   │   ├── hooks/                  # Custom hooks
│   │   └── lib/                    # API client, types, utils
│   └── package.json
├── tests/                          # Test suite
├── docs/                           # Documentation
│   ├── coaching_app_plan.md        # Implementation plan
│   └── runna_research.md           # Training methodology research
├── training.db                     # SQLite database
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
# Run analysis commands
training-analyzer status
training-analyzer workouts --last 7
training-analyzer readiness
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/athlete/context` | GET | Full athlete context for LLM |
| `/api/v1/athlete/readiness` | GET | Today's readiness score |
| `/api/v1/analysis/workout/{id}` | POST | Analyze a workout |
| `/api/v1/plans/generate` | POST | Generate training plan |
| `/api/v1/workouts/design` | POST | Design structured workout |
| `/api/v1/workouts/{id}/fit` | GET | Download FIT file |

## Configuration

Create a `.env` file:

```env
OPENAI_API_KEY=your-key
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

## Tech Stack

- **Backend**: FastAPI, Pydantic, SQLite
- **Frontend**: Next.js 16, React 19, Tailwind CSS 4
- **AI**: OpenAI GPT-4o, LangGraph agents
- **Export**: Garmin FIT SDK

## Documentation

See `docs/coaching_app_plan.md` for the full implementation plan and architecture.

