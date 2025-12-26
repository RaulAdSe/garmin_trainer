# Workout Analysis Branch Progress

**Date:** 2025-12-25
**Branch:** `workout-analysis`
**Base:** `main`

## Overview

This branch transforms the Garmin dashboard from a raw data display into a WHOOP-inspired actionable insights platform. The philosophy follows "brutal condensation" - thousands of data points reduced to one clear decision: GO, MODERATE, or RECOVER.

## Features Implemented

### Phase 1: Training Metrics Foundation
- **TSS (Training Stress Score):** Quantifies training load from each workout
- **CTL (Chronic Training Load):** 42-day rolling fitness proxy
- **ATL (Acute Training Load):** 7-day rolling fatigue proxy
- **TSB (Training Stress Balance):** CTL - ATL = form indicator
- **ACWR (Acute:Chronic Workload Ratio):** Injury risk metric

### Phase 2: Personal Baselines
- Rolling averages (7-day and 30-day) for HRV, sleep, RHR
- Direction indicators showing trend vs personal baseline (↑↓)
- Recovery calculation now uses YOUR baselines, not population averages
- "Your HRV vs your 7-day avg, not 'normal'" philosophy

### Phase 3: Actionable Insights
- **GO/MODERATE/RECOVER screen:** First thing you see is a decision
- **Strain targets:** Based on recovery zone (Green: 14-21, Yellow: 8-14, Red: 0-8)
- **Sleep debt tracking:** Accumulated debt over 7 days
- **Personalized sleep targets:** Baseline + strain adjustment + debt repayment
- Workout recommendations based on recovery state

### Phase 4: Causality Engine
- **Pattern detection:** Correlates behaviors with outcomes
  - Workout timing impact on next-day recovery
  - Sleep consistency effects
  - Step count correlations
  - Alcohol/late night detection
- **Streak tracking:** Green days, sleep consistency, step goals
- **Trend alerts:** Multi-day declining/improving HRV, sleep, recovery
- **Weekly summaries:** Zone breakdown with week-over-week comparison

### Phase 5: Info Buttons (Latest)
- `?` button on every metric card
- Modal with educational content:
  - What the metric measures
  - How it impacts health
  - Actionable tips for improvement
- Covers: recovery, strain, sleep, HRV, RHR, body battery, sleep stages, sleep debt

## File Changes

### Whoop Dashboard (`whoop-dashboard/`)
- `frontend/src/app/page.tsx` - Complete UI overhaul with WHOOP-style design
- `VISION.md` - Philosophy and roadmap documentation

### Shared Garmin Client (`shared/garmin_client/`)
- `baselines.py` - Rolling averages, direction indicators, personal baselines
- `insights.py` - Strain targets, sleep needs, daily insights
- `causality.py` - Pattern detection, streaks, trend alerts, weekly summaries
- `__init__.py` - Exports for all new modules

### Training Analyzer (`training-analyzer/`)
- Enhanced CLI with analysis features
- Database schema updates for training metrics
- Analysis module for TSS/CTL/ATL/TSB calculations

## Commits (chronological)

1. `4edf1ad` - Stage 0 complete: Garmin data ingestion working
2. `68d5db0` - Phase 2: Personal baselines with rolling averages
3. `a8659a9` - Phase 3: Actionable insights with strain targets
4. `a9ba667` - Phase 1: Add training metrics foundation
5. `711e448` - Phase 4: Causality engine with pattern detection
6. `1da5185` - Phase 2: Add decision engine with readiness
7. `21103b8` - Add info buttons to metric cards
8. `b55aefb` - Phase 3: Add analysis features and enhanced CLI

## Architecture

```
garmin_insights/
├── shared/
│   └── garmin_client/          # Shared Python package
│       ├── api/client.py       # Garmin Connect API
│       ├── db/                 # SQLite database layer
│       ├── baselines.py        # Personal baseline calculations
│       ├── insights.py         # Actionable insights engine
│       └── causality.py        # Pattern detection & streaks
├── whoop-dashboard/
│   └── frontend/               # Next.js 16 dashboard
│       └── src/app/page.tsx    # Main WHOOP-style UI
└── training-analyzer/          # Training load analysis CLI
```

## Key Design Decisions

1. **Personal over population:** All comparisons use YOUR baselines
2. **Decision-first:** Big GO/MODERATE/RECOVER before any numbers
3. **Strain matches recovery:** Higher recovery = higher strain target
4. **Sleep is calculated:** Tonight's target = baseline + strain adjustment + debt repayment
5. **Patterns matter:** Detect correlations between behaviors and outcomes

## Next Steps

- [ ] Add respiration rate tracking
- [ ] Training Readiness API integration
- [ ] Stress patterns analysis
- [ ] Weekly email summaries
- [ ] Mobile PWA optimization
