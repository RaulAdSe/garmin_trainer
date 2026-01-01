# Level Rewards & Feature Gating System

## Overview

The level rewards system creates a **tangible progression path** where users unlock new features as they train more. This drives retention by giving users clear goals beyond just "get fitter."

## Core Principle

> **AI-powered training is the heart of the app.** The core value proposition (AI workout analysis, dashboard, workout history) must always be available to every user from day one.

Features that are gated should be **enhancements** that make the experience richer, not the core functionality.

---

## Level Progression Roadmap

### Always Available (No Level Required)
These features are the core value proposition and should never be locked:

| Feature | Description |
|---------|-------------|
| Basic Dashboard | Fitness metrics, readiness score, training load |
| Workout History | View and browse all synced workouts |
| AI Workout Analysis | AI-powered analysis of each workout |
| Garmin Sync | Import workouts from Garmin Connect |

### Level-Gated Features

| Level | Title | Features Unlocked | XP Required |
|-------|-------|-------------------|-------------|
| 1 | Training Rookie | *Starting tier - core features available* | 0 |
| 3 | Eager Learner | Trend Analysis (7/30/90 day views) | ~170 |
| 5 | Dedicated Athlete | Advanced Metrics (TSB charts, fatigue modeling) | ~335 |
| 8 | Committed Trainer | AI Coach Chat, Personalized Tips | ~605 |
| 10 | Serious Athlete | Training Plan Generation, Race Predictions | ~1000 |
| 15 | Advanced Performer | Custom Workout Design, Garmin FIT Export | ~1740 |
| 20 | Training Expert | Periodization Planner, Peak Optimization | ~2830 |
| 25 | Elite Performer | Coach Mode (multi-athlete management) | ~3950 |
| 30 | Training Master | All Features + Beta Access to new features | ~5200 |

---

## UI/UX Requirements

### Locked Feature Display

Locked features should be **visible but clearly locked**, creating anticipation:

```
┌─────────────────────────────────────┐
│  [Icon]  Training Plan Generation   │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  🔒  Unlocks at Level 10    │   │
│  │                             │   │
│  │  [Progress bar: 7/10]       │   │
│  └─────────────────────────────┘   │
│                                     │
│  Generate AI-powered training       │
│  plans tailored to your goals...    │
│                                     │
└─────────────────────────────────────┘
```

#### Visual States

1. **Locked State**
   - Grayed out / reduced opacity (e.g., `opacity-50`)
   - Lock icon overlay
   - Hover tooltip: "Unlocks at Level X"
   - Show progress toward unlock level

2. **Almost Unlocked State** (within 1 level)
   - Slightly more visible (e.g., `opacity-70`)
   - Pulsing glow effect
   - Hover: "Almost there! X XP to unlock"

3. **Unlocked State**
   - Full color, interactive
   - Brief celebration animation on first unlock
   - "NEW" badge for 7 days after unlock

### Navigation Integration

In the sidebar/navigation:

```
Dashboard          ✓
Workouts           ✓
Achievements       ✓
───────────────────
Plans              🔒 Lvl 10
Workout Design     🔒 Lvl 15
AI Coach           🔒 Lvl 8
───────────────────
Coach Mode         🔒 Lvl 25
```

---

## Implementation Notes

### Feature Flags in Frontend

```typescript
// Check if feature is unlocked
const isFeatureUnlocked = (feature: string, level: number): boolean => {
  const FEATURE_UNLOCK_LEVELS: Record<string, number> = {
    'trend_analysis': 3,
    'advanced_metrics': 5,
    'ai_coach_chat': 8,
    'training_plans': 10,
    'workout_design': 15,
    'periodization': 20,
    'coach_mode': 25,
  };

  return level >= (FEATURE_UNLOCK_LEVELS[feature] ?? 0);
};
```

### Locked Feature Component

```tsx
interface LockedFeatureProps {
  feature: string;
  currentLevel: number;
  requiredLevel: number;
  children: React.ReactNode;
}

function LockedFeatureGate({ feature, currentLevel, requiredLevel, children }: LockedFeatureProps) {
  const isUnlocked = currentLevel >= requiredLevel;

  if (isUnlocked) {
    return <>{children}</>;
  }

  return (
    <div className="relative opacity-50 pointer-events-none">
      {children}
      <div className="absolute inset-0 flex items-center justify-center bg-gray-900/60">
        <Tooltip content={`Unlocks at Level ${requiredLevel}`}>
          <LockIcon className="w-8 h-8 text-gray-400" />
        </Tooltip>
      </div>
    </div>
  );
}
```

---

## Retention Psychology

### Why This Works

1. **Sunk Cost Fallacy** - Users who've invested XP don't want to lose progress
2. **Variable Rewards** - Achievement unlocks provide dopamine hits
3. **Social Proof** - Titles and levels create identity ("I'm a Serious Athlete")
4. **Loss Aversion** - Visible locked features create FOMO
5. **Goal Gradient Effect** - Progress bars accelerate engagement near completion

### XP Sources

| Action | XP Earned |
|--------|-----------|
| Complete any workout | 10 XP |
| First workout ever | 10 XP (bonus) |
| 3-day streak | 25 XP |
| 7-day streak | 50 XP |
| 14-day streak | 75 XP |
| 30-day streak | 100 XP |
| VO2 Max improvement (3%) | 50 XP |
| VO2 Max improvement (5%) | 75 XP |
| VO2 Max improvement (10%) | 100 XP |
| New CTL record | 50 XP |
| Complete 5 interval workouts | 40 XP |
| Complete 20 interval workouts | 75 XP |
| 60 minutes in Zone 5 | 75 XP |

---

## Current Status

### Implemented
- [x] Level calculation and XP system
- [x] Achievement unlock logic
- [x] Sports science-based VO2 Max achievements
- [x] Level rewards data structure in backend
- [x] Level rewards roadmap component
- [x] Translations for all level rewards

### TODO

#### AI Coach Chat
- [ ] **AI Coach Chat UI** - API exists (`/chat`), frontend missing
  - Simple chat interface with message bubbles
  - Suggested questions on empty state
  - Conversation history management
- [ ] **Chat Agent: Add workout analysis access** - Currently the ChatAgent only sees summary activity stats (distance, duration, avg_hr, load). It does NOT have access to:
  - AI-generated workout commentary (stored in `workout_analysis` table)
  - Zone time distributions
  - Lap/segment analysis
  - Pace variability, HR drift metrics
  - Interval detection
  - Execution score cards

  **Fix:** When intent is `workout_detail`, the ChatAgent should:
  1. Fetch stored workout analysis from DB (if exists)
  2. Or call `condense_workout_data()` to generate stats on the fly
  3. Include this rich context in the LLM prompt

#### Feature Gating UI
- [ ] Locked feature overlay component with "Unlocks at Level X" tooltip
- [ ] Navigation items with lock indicators
- [ ] "Almost unlocked" animations (within 1 level)
- [ ] First-unlock celebration modal

#### Level-Gated Features (to build)
- [ ] Training Plan Generation page (Level 10)
- [ ] Custom Workout Design page (Level 15)
- [ ] Periodization Planner (Level 20)
- [ ] Coach Mode - multi-athlete management (Level 25)

---

## Questions to Resolve

1. **Should locked features be clickable?**
   - Option A: Click shows "Unlock at Level X" modal with progress
   - Option B: Completely non-interactive (current proposal)

2. **What about users who pay?**
   - Should there be a premium tier that bypasses levels?
   - Or keep it pure gamification (no pay-to-unlock)?

3. **Level decay?**
   - Should inactivity cause level loss?
   - Or once earned, always earned?

---

## Related Files

- `src/services/achievement_service.py` - LEVEL_REWARDS dict
- `src/models/gamification.py` - LevelReward model
- `frontend/src/components/gamification/LevelRewards.tsx` - Roadmap UI
- `frontend/src/lib/types.ts` - LevelReward type
- `frontend/src/messages/en.json` - Translations
