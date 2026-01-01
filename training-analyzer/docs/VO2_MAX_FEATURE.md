# VO2 Max Feature

## Overview

VO2 Max (maximal oxygen uptake) is a key indicator of cardiovascular fitness and endurance performance. This feature adds VO2 Max tracking and gamification to the Training Analyzer dashboard.

## Features Added

### 1. Dashboard VO2 Max Card

A new card on the main dashboard displays:
- **Current VO2 Max value** with a circular progress indicator
- **Fitness level classification** (Elite, Excellent, Good, Fair, Below Average)
- **Trend indicator** showing if VO2 Max is improving, stable, or declining
- **Percentage change** over the last 90 days
- **Peak comparison** showing current vs. historical peak
- **Mini chart** showing the last 30 data points

### 2. VO2 Max Achievements

Four new achievements reward users for reaching VO2 Max milestones:

| Achievement | VO2 Max Threshold | XP | Rarity |
|-------------|-------------------|-----|--------|
| Aerobic Breakthrough | 40 ml/kg/min | 50 | Common |
| Cardio Champion | 50 ml/kg/min | 75 | Rare |
| Oxygen Elite | 55 ml/kg/min | 100 | Epic |
| Aerobic Machine | 60 ml/kg/min | 150 | Legendary |

### 3. API Endpoints

The existing `/athlete/vo2max-trend` endpoint is used to fetch:
- Historical VO2 Max data points
- Trend direction and percentage change
- Current and peak values for running and cycling

## Data Source

VO2 Max data is synced from Garmin Connect via the `/garmin/sync-fitness` endpoint. Garmin provides:
- `vo2max_running` - Running-specific VO2 Max
- `vo2max_cycling` - Cycling-specific VO2 Max (if available)
- `fitness_age` - Calculated fitness age
- Race time predictions based on VO2 Max

## VO2 Max Fitness Levels

| VO2 Max (ml/kg/min) | Classification |
|---------------------|----------------|
| 60+ | Elite |
| 52-60 | Excellent |
| 45-52 | Good |
| 38-45 | Fair |
| <38 | Below Average |

*Note: These thresholds are simplified. Actual fitness classifications vary by age and gender.*

## Files Modified

### Frontend
- `frontend/src/lib/types.ts` - Added VO2MaxTrend types
- `frontend/src/lib/api-client.ts` - Added getVO2MaxTrend function
- `frontend/src/hooks/useAthleteContext.ts` - Added useVO2MaxTrend hook
- `frontend/src/hooks/index.ts` - Exported new hooks
- `frontend/src/components/athlete/VO2MaxCard.tsx` - New VO2 Max display component
- `frontend/src/app/[locale]/page.tsx` - Added VO2 Max card to dashboard
- `frontend/src/messages/en.json` - English translations
- `frontend/src/messages/es.json` - Spanish translations

### Backend
- `src/services/achievement_service.py` - Added VO2 Max achievements and checking logic
- `src/api/routes/gamification.py` - Added VO2 Max context to achievement checking

## Internationalization

The feature supports both English and Spanish:

**English:**
- Title: "VO2 Max"
- Card Title: "Aerobic Capacity"
- Trend labels: "improving", "stable", "declining"

**Spanish:**
- Title: "VO2 Máx"
- Card Title: "Capacidad Aeróbica"
- Trend labels: "mejorando", "estable", "bajando"

## How to Improve VO2 Max

VO2 Max improves with consistent aerobic training:
1. **High-intensity intervals** (3-5 min at 90-95% max HR)
2. **Tempo runs** at lactate threshold pace
3. **Long runs** to build aerobic base
4. **Consistent training** over weeks and months

The app uses VO2 Max data to:
- Calculate personalized training paces
- Estimate recovery times
- Predict race performance
