# Workout Analysis Branch - Complete

**Date**: December 25, 2025
**Branch**: `workout-analysis`
**Status**: Complete - Ready for merge

---

## Overview

This branch implements a comprehensive **AI Training Coach** that transforms raw Garmin data into actionable training decisions. The system follows the principle: *"The best training tools are decision tools, not analysis tools."*

Rather than just showing metrics, this tool answers: **"What should I do today to improve?"**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRAINING ANALYZER                             │
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │   METRICS    │ → │  DECISION    │ → │     ANALYSIS         │ │
│  │   (Phase 1)  │   │  (Phase 2)   │   │     (Phase 3)        │ │
│  └──────────────┘   └──────────────┘   └──────────────────────┘ │
│        ↓                  ↓                     ↓                │
│  TSS, CTL/ATL,      Readiness,          Trends, Goals,          │
│  ACWR, HR Zones     Recommendations     Predictions             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Metrics Foundation

**Location**: `training-analyzer/src/training_analyzer/metrics/`

### Training Load Calculations (`load.py`)
- **HRSS (Heart Rate Stress Score)**: TSS equivalent for HR-based training
- **TRIMP (Training Impulse)**: Banister's exponential formula with gender-specific coefficients
- **Relative Effort**: Simplified load metric similar to Strava

### Fitness-Fatigue Model (`fitness.py`)
- **CTL (Chronic Training Load)**: 42-day EWMA representing fitness
- **ATL (Acute Training Load)**: 7-day EWMA representing fatigue
- **TSB (Training Stress Balance)**: CTL - ATL, indicates form/freshness
- **ACWR (Acute:Chronic Workload Ratio)**: Injury risk indicator
  - < 0.8: Undertrained
  - 0.8-1.3: Optimal (sweet spot)
  - 1.3-1.5: Caution
  - > 1.5: Danger zone

### Heart Rate Zones (`zones.py`)
- **Karvonen method**: Based on Heart Rate Reserve
- **LTHR method**: Based on Lactate Threshold Heart Rate
- **Zone time distribution**: Calculate % time in each zone
- **Max HR estimation**: Tanaka formula (208 - 0.7 × age)

### Database (`db/`)
- `user_profile`: Personal HR settings (max, rest, threshold, age, gender)
- `activity_metrics`: Enriched workout data with HRSS, TRIMP, zones
- `fitness_metrics`: Daily CTL/ATL/TSB/ACWR tracking

### Enrichment Service (`services/enrichment.py`)
- Reads raw activities from n8n database
- Calculates training metrics for each activity
- Aggregates daily loads for fitness calculation

---

## Phase 2: Decision Engine

**Location**: `training-analyzer/src/training_analyzer/recommendations/`

### Readiness Scoring (`readiness.py`)
Combines multiple factors into a 0-100 readiness score:

| Factor | Weight | Source |
|--------|--------|--------|
| HRV vs baseline | 25% | Wellness data |
| Sleep quality | 20% | Wellness data |
| Body Battery | 15% | Wellness data |
| Stress (inverted) | 10% | Wellness data |
| Training load balance | 20% | Fitness metrics |
| Recovery days | 10% | Activity history |

**Zones**:
- 🟢 Green (67-100): Ready for quality work
- 🟡 Yellow (34-66): Moderate training appropriate
- 🔴 Red (0-33): Focus on recovery

### Workout Recommendations (`workout.py`)
Decision rules based on:
1. **Readiness < 40**: Rest or recovery only
2. **ACWR > 1.5**: Rest (danger zone)
3. **ACWR > 1.3**: Easy day (caution)
4. **Yesterday was hard**: Easy day (hard/easy pattern)
5. **ACWR < 0.8 + high readiness**: Can push harder
6. **Normal**: Balance weekly load distribution

**Workout Types**: REST, RECOVERY, EASY, LONG, TEMPO, THRESHOLD, INTERVALS, SPEED

### Natural Language Explanations (`explain.py`)
- `explain_readiness()`: Factor-by-factor breakdown
- `explain_workout()`: Purpose and guidelines
- `generate_daily_narrative()`: Cohesive briefing paragraph
- `format_training_status()`: Formatted CTL/ATL/TSB display

### Coach Service (`services/coach.py`)
Integration layer that:
- Fetches wellness data from whoop-dashboard
- Gets fitness metrics from training-analyzer
- Produces complete daily briefings with recommendations

---

## Phase 3: Analysis & Integration

**Location**: `training-analyzer/src/training_analyzer/analysis/`

### Performance Trends (`trends.py`)
- **Fitness trends**: Track CTL changes over time (improving/maintaining/declining)
- **Pace-at-HR tracking**: Efficiency indicator (faster at same HR = fitter)
- **Overtraining detection**: Signals like high ACWR, negative TSB, declining HRV
- **ASCII charts**: Terminal-friendly visualizations

### Weekly Analysis (`weekly.py`)
- Volume metrics (distance, duration, load)
- Zone distribution with bar charts
- Week-over-week load comparison
- Recovery week detection
- Actionable insights generation

### Race Goals (`goals.py`)
- **Race distances**: 5K, 10K, Half Marathon, Marathon
- **Riegel prediction**: T2 = T1 × (D2/D1)^1.06
- **VDOT calculation**: Fitness metric from race performance
- **Training paces**: Easy, tempo, threshold, interval zones
- **Goal progress tracking**: Weeks remaining, CTL needed, on-track status

### Enhanced CLI
Beautiful terminal output using Rich library:

```bash
# Core
training-analyzer setup       # Configure HR profile
training-analyzer enrich      # Process activities
training-analyzer fitness     # Show CTL/ATL/TSB
training-analyzer status      # Current status

# Decisions
training-analyzer today       # Today's recommendation
training-analyzer why         # Explain recommendation
training-analyzer summary     # Weekly summary

# Analysis
training-analyzer trends      # Fitness trends
training-analyzer week        # Weekly analysis
training-analyzer goal        # Race goals
training-analyzer dashboard   # Complete overview
```

---

## Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_metrics.py | 41 | Load calculations, fitness model, HR zones |
| test_database.py | 24 | All database operations |
| test_enrichment.py | 13 | Activity enrichment pipeline |
| test_recommendations.py | 60 | Readiness, recommendations, explanations |
| test_analysis.py | 44 | Trends, weekly, goals, predictions |
| test_integration.py | 18 | End-to-end workflows |
| **Total** | **200** | All passing |

---

## Key Formulas

```python
# TRIMP (Banister)
delta_hr = (avg_hr - rest_hr) / (max_hr - rest_hr)
trimp = duration_min * delta_hr * 0.64 * exp(1.92 * delta_hr)  # male

# CTL (42-day exponential decay)
ctl = ctl_prev * exp(-1/42) + daily_load * (1 - exp(-1/42))

# ATL (7-day exponential decay)
atl = atl_prev * exp(-1/7) + daily_load * (1 - exp(-1/7))

# TSB (Form)
tsb = ctl - atl

# ACWR (Injury risk)
acwr = atl / ctl

# Race prediction (Riegel)
predicted_time = known_time * (target_distance / known_distance) ^ 1.06

# Karvonen HR zones
target_hr = ((max_hr - rest_hr) * intensity_pct) + rest_hr
```

---

## File Structure

```
training-analyzer/
├── src/training_analyzer/
│   ├── __init__.py
│   ├── cli.py                    # Click CLI with Rich output
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py           # TrainingDatabase class
│   │   └── schema.py             # SQLite schema
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── load.py               # HRSS, TRIMP, Relative Effort
│   │   ├── fitness.py            # CTL, ATL, TSB, ACWR
│   │   └── zones.py              # HR zone calculations
│   ├── recommendations/
│   │   ├── __init__.py
│   │   ├── readiness.py          # Readiness scoring
│   │   ├── workout.py            # Workout recommendations
│   │   └── explain.py            # Natural language explanations
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── trends.py             # Performance trends
│   │   ├── weekly.py             # Weekly analysis
│   │   └── goals.py              # Race goals & predictions
│   └── services/
│       ├── __init__.py
│       ├── enrichment.py         # Activity enrichment
│       └── coach.py              # Coach service integration
├── tests/
│   ├── __init__.py
│   ├── test_metrics.py
│   ├── test_database.py
│   ├── test_enrichment.py
│   ├── test_recommendations.py
│   ├── test_analysis.py
│   └── test_integration.py
├── pyproject.toml
└── README.md
```

---

## Dependencies Added

```toml
[project.dependencies]
click = "^8.1.7"
rich = "^13.7.0"
```

---

## Commits on This Branch

```
b55aefb Phase 3: Add analysis features and enhanced CLI
1da5185 Phase 2: Add decision engine with readiness and recommendations
a9ba667 Phase 1: Add training metrics foundation (TSS, CTL/ATL/TSB, ACWR)
```

---

## Next Steps (Future Work)

1. **Dashboard Integration**: Connect to Next.js frontend
2. **Notification System**: Push recommendations via n8n
3. **Historical Backfill**: Process all historical activities
4. **Multi-Sport Support**: Cycling, swimming power models
5. **Weather Integration**: Adjust for heat/altitude
6. **Social Features**: Training partner comparisons

---

## Research Foundation

This implementation is based on comprehensive research documented in:
`/research/TRAINER_AI_RESEARCH.md`

Key influences:
- Runna app design philosophy (decision tools > analysis tools)
- TrainingPeaks PMC model (CTL/ATL/TSB)
- Banister Impulse-Response model
- Jack Daniels VDOT system
- Tim Gabbett ACWR research
