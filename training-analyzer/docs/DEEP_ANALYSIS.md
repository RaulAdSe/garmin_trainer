# trAIner App: Deep Expert Analysis

> **A multi-disciplinary evaluation for building an AI training platform accessible to everyone**

This document presents findings from three expert perspectives: Behavioral Psychology, UI/UX Design, and Sports Science. The goal is to identify opportunities to make the app **attractive**, **easy to use**, and **genuinely useful** for anyone wanting to improve their fitness with an AI trainer.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Behavioral Psychology Analysis](#behavioral-psychology-analysis)
3. [UI/UX Expert Analysis](#uiux-expert-analysis)
4. [Sports Science Analysis](#sports-science-analysis)
5. [Cross-Disciplinary Themes](#cross-disciplinary-themes)
6. [Priority Recommendations Matrix](#priority-recommendations-matrix)
7. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

### Current Strengths

| Area | What Works Well |
|------|-----------------|
| **Gamification** | Solid level/XP/achievement system with 30+ achievements |
| **Data Visualization** | Synchronized charts, Recharts implementation |
| **Load Monitoring** | Proper CTL/ATL/TSB with ACWR injury risk zones |
| **AI Integration** | Streaming analysis, context-aware recommendations |
| **Tech Stack** | Modern (Next.js 16, React 19, Tailwind 4) |

### Critical Gaps

| Area | What's Missing |
|------|----------------|
| **Beginner Experience** | No onboarding, complex dashboard, intimidating metrics |
| **Emotional Connection** | App feels like a dashboard, not a coach |
| **Recovery Science** | Basic sleep/HRV, no nutrition, stress underweighted |
| **Mobile UX** | Hover-based charts, 6-item bottom nav, dense dashboard |
| **Social/Relatedness** | Zero community features despite category existing |

### The Core Problem

> The app is built for **data-literate intermediate athletes** but wants to serve **anyone who wants to improve**.

This creates a fundamental tension between feature richness and accessibility.

---

## Behavioral Psychology Analysis

### Motivation Framework Assessment

#### Extrinsic Motivation: 8/10
- XP rewards, level progression, achievement unlocks
- Feature gating creates tangible rewards
- Celebration modals with animations

#### Intrinsic Motivation: 5/10
- **Missing**: Connection to "why" the user trains
- **Missing**: Flow state recognition
- **Missing**: Personal transformation narratives

> *"Self-Determination Theory (Deci & Ryan, 2000) shows intrinsic motivation produces more sustained engagement than extrinsic rewards alone."*

### Hook Model Analysis (Nir Eyal)

| Stage | Current State | Assessment |
|-------|--------------|------------|
| **Trigger** | No push notifications, relies on Garmin sync | Weak |
| **Action** | Sync workout, view analysis | Moderate |
| **Variable Reward** | AI insights, achievement unlocks, XP | Strong |
| **Investment** | Streak maintenance, level progression | Moderate |

**Critical Gap**: No proactive engagement triggers. Users must remember to open the app.

### Self-Determination Theory Scorecard

| Dimension | Score | Notes |
|-----------|-------|-------|
| **Autonomy** | 7/10 | Readiness suggests but doesn't dictate; feature gating feels controlling for beginners |
| **Competence** | 8/10 | Strong progress visibility, XP/levels, but over-indexes on consistency vs performance |
| **Relatedness** | 3/10 | **CRITICAL GAP** - Social category exists but no features implemented |

### Psychological Interventions (Top 10)

1. **Purpose Anchoring**
   - Ask "Why do you train?" during onboarding
   - Reference this purpose during difficult moments
   - *Basis: Meaning-making increases persistence (Steger, 2009)*

2. **Dynamic Streak Recovery**
   - When streak breaks, offer "Comeback Challenge" with bonus XP
   - Frame as: "Every champion has comebacks"
   - *Basis: Growth Mindset (Dweck, 2006)*

3. **Implementation Intention Prompts**
   - "When specifically will you train this week?"
   - "What might prevent you, and what's your backup plan?"
   - *Basis: 23% increase in goal achievement (Gollwitzer, 1999)*

4. **Identity Commitment Ritual**
   - At Level 3, prompt identity statement: "I am someone who..."
   - Display on profile
   - *Basis: Public commitment increases consistency (Cialdini, 2006)*

5. **Progressive Dashboard Complexity**
   - L1-4: Simplified view (Readiness + Streak + Next Workout)
   - L5+: Full CTL/ATL/TSB with explanation tooltips
   - *Basis: Cognitive load reduction (Sweller, 1988)*

6. **Guaranteed Early Wins**
   - "First Sync" (immediate)
   - "First Analysis Read" (day 1-2)
   - "First Week Warrior" (7 days any activity)
   - *Basis: Early success builds self-efficacy (Bandura, 1977)*

7. **Emotional Support for Red Zones**
   - Replace clinical "Recovery Focus" with:
   - "Your body is asking for rest. Recovery isn't falling behind—it's building strength."
   - *Basis: Psychologica (Edmondson, 1999)*

8. **Earn-Your-Freeze Tokens**
   - Change from static allocation to earned reward
   - "Complete 3 quality workouts to earn a streak protection token"
   - *Basis: Effort justification (Aronson & Mills, 1959)*

9. **Social Proof Layer**
   - "2,340 athletes trained today"
   - "You're in the top 15% for consistency this month"
   - No social network required
   - *Basis: Social proof motivates without comparison anxiety (Cialdini, 2006)*

10. **Peak Performance Celebrations**
    - Detect and celebrate PRs with unique animation
    - Track pace PRs, distance PRs, consistency PRs
    - *Basis: Peak experiences create positive memory anchors (Csikszentmihalyi, 1990)*

---

## UI/UX Expert Analysis

### Information Architecture Issues

**Navigation Overload**
- 8 items in sidebar (approaches Miller's Law limit of 7±2)
- No visual separators between nav groups
- Bottom nav has 6 items—too many for mobile
- "Connect" is buried but critical for onboarding

**Dashboard Competition**
```
Current Dashboard (7 competing elements):
┌──────────────────────────┐
│ Gamification Header      │ ← Attention 1
├──────────────────────────┤
│ Readiness Gauge          │ ← Should be hero
├──────────────────────────┤
│ VO2Max │ Today's Training│ ← Attention 2
├──────────────────────────┤
│ Training Balance         │ ← Attention 3
├──────────────────────────┤
│ Quick Actions            │ ← Attention 4
├──────────────────────────┤
│ Race Goals               │ ← Attention 5
└──────────────────────────┘
```

### Mobile Experience Critical Issues

| Issue | Problem | Impact |
|-------|---------|--------|
| **Touch targets** | Some buttons <44px | Frustrated taps |
| **Chart interactions** | Hover-based | Broken on touch |
| **Dense dashboard** | Same content as desktop | Overwhelmed users |
| **No pull-to-refresh** | Missing on workout list | Poor mobile feel |

### Accessibility Gaps (WCAG)

- `text-gray-400` on `bg-gray-950` is borderline AA (4.5:1)
- Charts lack ARIA labels for data points
- Locked items missing `aria-disabled="true"`
- Chart interactions are mouse-only (no keyboard alternatives)

### Onboarding Flow (Currently Missing)

**Recommended 3-Phase Approach:**

```
Phase 1: Connection Setup
┌─────────────────────────────────────┐
│        Welcome to trAIner           │
│                                     │
│  [Connect Garmin] [Connect Strava]  │
│                                     │
│  "Import your first 30 days of      │
│   training data to get started"     │
└─────────────────────────────────────┘

Phase 2: Profile Configuration
- Goal setting (race target, weekly volume)
- Zone calibration (or auto-detect)
- Preferred units

Phase 3: Progressive Feature Introduction
- Week 1: Dashboard + Workouts basics
- Week 2: "Why?" explanations on metrics
- Week 3: Achievement system
- Week 4: AI Chat preview (level-gated tease)
```

### UI/UX Recommendations (Top 10)

1. **Redesign Mobile Bottom Navigation**
   ```
   ┌───────┬───────┬───────┬───────┬───────┐
   │ Home  │Workouts│ Chat │Progress│ More  │
   │   ○   │   ○   │   ○  │   ○   │   ○   │
   └───────┴───────┴───────┴───────┴───────┘
   ```
   - Reduce to 5 items
   - "More" opens full menu
   - Touch targets 48px minimum

2. **Touch-Friendly Chart Interactions**
   - Tap-to-pin tooltip
   - Swipe to scrub timeline
   - Pinch-to-zoom time range
   - "Tap and hold to explore" hint

3. **Dashboard Focus Mode Toggle**
   ```
   Focus View:
   ┌─────────────────────────────────────┐
   │         READINESS: 78              │
   │       Ready for Quality            │
   │                                     │
   │  Today: 45min Easy Run             │
   │  "Your body is recovered."         │
   │                                     │
   │      [View Full Dashboard]          │
   └─────────────────────────────────────┘
   ```

4. **Enhanced Achievement Previews**
   - Replace grayscale with blurred preview
   - Show progress bar: "32/42 km - 10km to go!"
   - Keep motivation visible

5. **Contextual Onboarding Tooltips**
   - Trigger 1: No workouts → Connection prompt
   - Trigger 2: First workout → Readiness Gauge explanation
   - Trigger 3: First analysis → XP earning explanation

6. **Data Freshness Indicators**
   ```
   Dashboard                    Updated 2h ago [↻]
   ```
   - Show last sync time
   - Stale data warning after 3 days

7. **Mobile Filter Bottom Sheet**
   - Replace 4-column grid with slide-up sheet
   - Better touch experience

8. **Content-Aware Skeleton Loaders**
   - Match final layout shape
   - Reduce perceived loading time

9. **Haptic Feedback Patterns**
   - Achievement unlock: `[100, 50, 100]ms`
   - Level up: `[200, 100, 200, 100, 400]ms`
   - Successful sync: `[50]ms`

10. **Chart Comparison Mode**
    ```
    Heart Rate   [Compare to: Best 10K ▼]
    ─────────────────────────────────────
        Current ━━━━━━━━━━━
        Best 10K ┄┄┄┄┄┄┄┄┄┄┄

    "5 bpm higher at 5km vs your PR pace"
    ```

---

## Sports Science Analysis

### Training Principles Assessment

| Principle | Implementation | Gap Severity |
|-----------|---------------|--------------|
| **Progressive Overload** | 5% weekly TSS increase | Medium - too linear |
| **Specificity** | Multi-sport agents, race-specific workouts | Low |
| **Recovery** | Rest days, cutback weeks, TSB-based | Medium |
| **Supercompensation** | Not modeled | High |
| **Polarized Training** | Not validated (80/20 rule) | High |

### Load Monitoring: What Works

**CTL/ATL/TSB**: Correctly implemented with EWMA
**ACWR Risk Zones**: Proper Gabbett zones (0.8-1.3 optimal)

### Load Monitoring: Critical Gaps

1. **ACWR Spike Detection Missing**
   - No week-over-week change alerts
   - Research shows >15% weekly increase = injury risk

2. **Training Monotony/Strain Not Tracked**
   ```python
   monotony = weekly_load_mean / weekly_load_std_dev
   strain = weekly_load * monotony
   # Alert if monotony > 2.0 or strain > 6000
   ```

3. **External vs Internal Load**
   - Only internal load (HR-based) tracked
   - Missing distance/duration constraints

### Recovery Science Gaps

| Factor | Current | Needed |
|--------|---------|--------|
| **Sleep** | Duration + quality score | Sleep debt, stages, consistency |
| **HRV** | RMSSD only | CV, trend analysis, LF/HF ratio |
| **Nutrition** | None | Post-workout timing, energy availability |
| **Life Stress** | Basic input | Multiplier effect on training tolerance |

### Zone System Comparison

| Zone Type | Current | Needed |
|-----------|---------|--------|
| **HR Zones** | 5-zone (Friel) | ✓ Adequate |
| **Pace Zones** | Missing | Daniels' VDOT system |
| **Power Zones** | Missing | Stryd/Garmin FTP-based |

### Beginner vs Advanced Support

**Current State**: Heavily weighted toward intermediate-advanced athletes

**Beginner Needs (Couch-to-5K):**

| Need | Current | Gap |
|------|---------|-----|
| Run/walk intervals | None | Critical |
| 10% weekly mileage cap | 5% TSS (different metric) | High |
| RPE-based intensity | HR-focused | High |
| Form/technique cues | None | Medium |
| Simplified metrics | CTL/ATL/TSB shown | High |

### Race Preparation Gaps

1. **Taper Protocol**
   - Current: Linear 50% reduction
   - Needed: Exponential decay (Mujika protocol)
   - Duration should vary by race distance

2. **Race Week**
   - No carb loading guidance
   - No sharpening session structure
   - No travel/time zone considerations

3. **Pacing Strategy**
   - No course profile analysis
   - No weather-adjusted targets
   - No split strategy recommendations

### Sports Science Recommendations (Top 10)

1. **ACWR Spike Detection** (Safety-Critical)
   - Alert when weekly load increases >15%
   - Week-over-week comparison on dashboard

2. **Training Monotony/Strain Metrics**
   - Calculate and display injury risk factors
   - Alert when thresholds exceeded

3. **Exponential Taper Implementation**
   ```python
   taper_load = peak_load * exp(-decay * days_before_race)
   # 5K: 5-7 days, Marathon: 14-21 days
   ```

4. **Pace Zone System (Daniels' VDOT)**
   - Easy, Marathon, Threshold, Interval, Repetition
   - Display target paces per workout

5. **Beginner Mode**
   - Simplified dashboard
   - Run/walk interval support
   - 10% weekly mileage cap
   - RPE-based (no HR required)

6. **Enhanced Recovery Module**
   - 7-day rolling sleep debt
   - HRV trend with coefficient of variation
   - Post-workout recovery time estimation

7. **Running Economy Tracking**
   ```python
   economy = pace_seconds_per_km / avg_hr
   # "At 5:00/km, you average 150 bpm - improved 3%"
   ```

8. **Cardiac Drift Detection**
   - First half vs second half HR comparison
   - Alert if drift >5% (aerobic base deficiency)

9. **AI Coach Pattern Recognition**
   - Correlate workout timing with performance
   - Identify optimal individual TSB range
   - Predict peak fitness date

10. **Race Pacing Strategy Generator**
    - Course profile integration
    - Weather-adjusted targets
    - Split strategy recommendations

---

## Cross-Disciplinary Themes

Three themes emerged across all expert analyses:

### Theme 1: The Beginner Problem

All three experts identified that the app alienates beginners:

| Perspective | Finding |
|-------------|---------|
| **Psychology** | Feature gating can feel controlling; complex metrics create competence anxiety |
| **UI/UX** | Dense dashboard, no onboarding, no progressive disclosure |
| **Sports Science** | Metrics designed for athletes with established CTL; no run/walk, no RPE-based training |

**Unified Recommendation**: Create "Beginner Mode" with simplified UI, RPE-based training, run/walk intervals, and progressive feature reveal.

### Theme 2: Emotional Disconnect

| Perspective | Finding |
|-------------|---------|
| **Psychology** | App celebrates highs but doesn't support lows; no recovery narrative |
| **UI/UX** | Dashboard is informational not emotional; no personal touch |
| **Sports Science** | Recovery shown as clinical "Recovery Focus" rather than supportive guidance |

**Unified Recommendation**: Add empathetic messaging, purpose anchoring, comeback narratives, and celebration of small wins.

### Theme 3: Missing Social Layer

| Perspective | Finding |
|-------------|---------|
| **Psychology** | Relatedness is weakest SDT pillar; social category exists but empty |
| **UI/UX** | No community features despite competitive apps having them |
| **Sports Science** | No training partners, group challenges, or comparative insights |

**Unified Recommendation**: Add anonymous social proof ("2,340 athletes trained today"), optional community features, and comparative percentile rankings.

---

## Priority Recommendations Matrix

### Tier 1: Critical (Safety + Accessibility)

| # | Recommendation | Impact | Effort | Owner |
|---|----------------|--------|--------|-------|
| 1 | ACWR spike detection alerts | High | Low | Backend |
| 2 | Touch-friendly chart interactions | High | Medium | Frontend |
| 3 | Mobile bottom nav redesign (5 items) | High | Low | Frontend |
| 4 | Accessibility fixes (ARIA, contrast) | Medium | Low | Frontend |

### Tier 2: High (Core Experience)

| # | Recommendation | Impact | Effort | Owner |
|---|----------------|--------|--------|-------|
| 5 | Beginner Mode toggle | High | High | Full Stack |
| 6 | Onboarding flow (3 phases) | High | Medium | Frontend |
| 7 | Dashboard focus mode | High | Medium | Frontend |
| 8 | Pace zones (Daniels VDOT) | High | Medium | Backend |
| 9 | Purpose anchoring in onboarding | High | Low | Frontend |
| 10 | Guaranteed early wins (achievements) | Medium | Low | Backend |

### Tier 3: Medium (Engagement)

| # | Recommendation | Impact | Effort | Owner |
|---|----------------|--------|--------|-------|
| 11 | Dynamic streak recovery | Medium | Low | Full Stack |
| 12 | Social proof layer | Medium | Medium | Full Stack |
| 13 | Enhanced recovery module | Medium | High | Backend |
| 14 | Emotional support messaging | Medium | Low | Frontend |
| 15 | PR detection + celebration | Medium | Medium | Full Stack |

### Tier 4: Advanced (Differentiation)

| # | Recommendation | Impact | Effort | Owner |
|---|----------------|--------|--------|-------|
| 16 | Race pacing strategy generator | Medium | High | Backend |
| 17 | AI pattern recognition | Medium | High | Backend |
| 18 | Chart comparison mode | Medium | Medium | Frontend |
| 19 | Running economy tracking | Low | Medium | Backend |
| 20 | Haptic feedback system | Low | Low | Frontend |

---

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)

**Focus**: Safety, accessibility, and mobile basics

- [ ] ACWR spike detection with alerts
- [ ] Mobile bottom nav redesign
- [ ] Touch chart interactions (tap-to-pin, swipe scrub)
- [ ] ARIA labels and contrast fixes
- [ ] Data freshness indicators

**Success Metric**: Mobile usability score improves; zero injury risk alerts missed

### Phase 2: Onboarding (Weeks 5-8) ✅ COMPLETED

**Focus**: New user experience

- [x] 3-phase onboarding flow
- [x] Purpose anchoring question
- [x] Guaranteed early win achievements
- [x] Dashboard focus mode
- [x] Contextual tooltips

**Success Metric**: Day-7 retention increases 20%

> **Implementation**: See [Implementation 6](#implementation-6-phase-2---onboarding--new-user-experience-completed) for details.

### Phase 3: Beginner Mode (Weeks 9-12)

**Focus**: Accessibility for everyone

- [ ] Beginner mode toggle
- [ ] Simplified dashboard view
- [ ] RPE-based training option
- [ ] Run/walk interval support
- [ ] Pace zones (VDOT)

**Success Metric**: Beginner segment (CTL <30) retention matches overall

### Phase 4: Emotional Connection (Weeks 13-16)

**Focus**: From dashboard to coach

- [ ] Dynamic streak recovery
- [ ] Emotional support messaging
- [ ] PR detection and celebration
- [ ] Identity commitment feature
- [ ] Social proof layer

**Success Metric**: NPS increases; "coach-like" mentioned in feedback

### Phase 5: Advanced Features (Weeks 17+) ⚠️ BACKEND COMPLETE, FRONTEND PENDING

**Focus**: Differentiation and power users

- [x] Enhanced recovery module (Backend ✅, Frontend ❌)
- [x] AI pattern recognition (Backend ✅, Frontend ❌)
- [x] Race pacing generator (Backend ✅, Frontend ⚠️ Component exists but not integrated)
- [x] Chart comparison mode (Backend ✅, Frontend ⚠️ Component exists but not integrated)
- [x] Running economy tracking (Backend ✅, Frontend ❌)

**Status Summary:**
- **Backend**: All 5 features fully implemented with services and API routes
- **Frontend**: Components exist for race pacing and chart comparison, but not integrated into pages. Recovery, patterns, and economy have no frontend UI yet.

**Success Metric**: Power user engagement increases; competitive advantage established

> **Implementation**: See [Implementation 7](#implementation-7-phase-5---advanced-features-backend-complete) for details.

---

## Conclusion

The trAIner app has **strong technical foundations** and a **well-designed gamification system**. However, it currently serves intermediate athletes better than beginners or casual users.

**The path to "usable by anyone who wants to improve":**

1. **Lower the barrier** - Beginner mode, RPE training, run/walk
2. **Guide the journey** - Onboarding, progressive disclosure, tooltips
3. **Build connection** - Purpose anchoring, emotional support, identity
4. **Ensure safety** - ACWR alerts, injury prevention, recovery science
5. **Polish the experience** - Touch interactions, mobile-first, accessibility

The AI trainer vision is achievable. The foundation is solid. The gap is primarily in **accessibility and emotional design**—making the app feel like a supportive coach rather than a sophisticated dashboard.

---

## Appendix: Research References

| Topic | Citation |
|-------|----------|
| Self-Determination Theory | Deci & Ryan (2000). American Psychologist |
| Hook Model | Eyal N (2014). Hooked: How to Build Habit-Forming Products |
| Growth Mindset | Dweck C (2006). Mindset: The New Psychology of Success |
| Implementation Intentions | Gollwitzer PM (1999). American Psychologist |
| ACWR Injury Risk | Gabbett TJ (2016). Br J Sports Med |
| Polarized Training | Seiler S (2009). Int J Sports Physiol Perform |
| VDOT Pacing | Daniels J (2014). Daniels' Running Formula |
| Taper Protocols | Mujika I (2009). Tapering and Peaking |
| Cognitive Load | Sweller J (1988). Cognitive Science |
| Peak-End Rule | Kahneman D (2011). Thinking, Fast and Slow |

---

# Part 2: Detailed Implementation Specifications

The following sections provide production-ready implementation details for each major feature area, created by specialized development agents.

---

## Implementation 1: Beginner Mode

### Overview

Beginner Mode transforms the app experience for new athletes by:
- Simplifying the dashboard to essential metrics
- Replacing HR-based training with RPE (Rate of Perceived Exertion)
- Providing run/walk interval templates (Couch-to-5K style)
- Enforcing the 10% weekly mileage cap for injury prevention

### Database Schema

```sql
-- User preferences for app behavior
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    beginner_mode_enabled INTEGER DEFAULT 0,
    beginner_mode_start_date TEXT,
    show_hr_metrics INTEGER DEFAULT 1,
    show_advanced_metrics INTEGER DEFAULT 1,
    preferred_intensity_scale TEXT DEFAULT 'hr',  -- 'hr' | 'rpe' | 'pace'
    weekly_mileage_cap_enabled INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Manual workout entries (RPE-based, no HR required)
CREATE TABLE IF NOT EXISTS manual_workouts (
    activity_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    activity_type TEXT DEFAULT 'running',
    date TEXT NOT NULL,
    duration_min INTEGER NOT NULL,
    distance_km REAL,
    rpe INTEGER NOT NULL,  -- 1-10 RPE scale
    avg_hr INTEGER,        -- Optional
    max_hr INTEGER,        -- Optional
    estimated_load REAL NOT NULL,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

### TypeScript Types

```typescript
// Intensity Scale Types
export type IntensityScale = 'hr' | 'rpe' | 'pace';
export type RPELevel = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10;

export interface UserPreferences {
  beginnerModeEnabled: boolean;
  beginnerModeStartDate: string | null;
  showHRMetrics: boolean;
  showAdvancedMetrics: boolean;
  preferredIntensityScale: IntensityScale;
  weeklyMileageCapEnabled: boolean;
}

export interface RPEDescription {
  level: RPELevel;
  label: string;
  description: string;
  color: string;
  breathingCue: string;
  talkTest: string;
}

// Dashboard Configuration
export interface DashboardConfig {
  showReadinessGauge: boolean;
  showVO2MaxCard: boolean;
  showTrainingBalance: boolean;
  showGamificationHeader: boolean;
  showRaceGoals: boolean;
  showQuickActions: boolean;
  showFocusView: boolean;
  showRunWalkTemplates: boolean;
  showMileageCap: boolean;
}

export const BEGINNER_DASHBOARD_CONFIG: DashboardConfig = {
  showReadinessGauge: true,
  showVO2MaxCard: false,        // Hide - too advanced
  showTrainingBalance: false,   // Hide CTL/ATL
  showGamificationHeader: true,
  showRaceGoals: false,
  showQuickActions: true,
  showFocusView: true,          // NEW: Simplified focus
  showRunWalkTemplates: true,   // NEW: C25K-style templates
  showMileageCap: true,         // NEW: Weekly limit
};
```

### Key Components

| Component | File Path | Purpose |
|-----------|-----------|---------|
| `PreferencesProvider` | `contexts/preferences-context.tsx` | Global preferences state |
| `BeginnerModeToggle` | `components/settings/BeginnerModeToggle.tsx` | Settings toggle |
| `FocusView` | `components/dashboard/FocusView.tsx` | Simplified dashboard |
| `RPEScale` | `components/beginner/RPEScale.tsx` | RPE selector |
| `RunWalkBuilder` | `components/beginner/RunWalkBuilder.tsx` | Interval builder |
| `RunWalkTimer` | `components/beginner/RunWalkTimer.tsx` | Guided session timer |
| `WeeklyMileageAlert` | `components/beginner/WeeklyMileageAlert.tsx` | 10% cap warning |

### Backend Endpoints

```python
# Preferences API
GET  /api/preferences           # Get user preferences
PUT  /api/preferences           # Update preferences
POST /api/preferences/toggle-beginner-mode  # Toggle beginner mode

# Manual Workout API (RPE-based)
POST /api/workouts/manual       # Log workout with RPE

# Mileage Cap API
GET  /api/athlete/mileage-cap   # Get current cap status
POST /api/athlete/mileage-cap/check  # Check if planned run exceeds cap
```

### 10% Mileage Cap Calculation

```python
def calculate_mileage_cap(
    previous_week_km: float,
    current_week_km: float,
    cap_percentage: float = 0.10,
    minimum_base_km: float = 5.0,
) -> MileageCapResult:
    """
    Calculate weekly mileage cap based on the 10% rule.
    """
    base_km = max(previous_week_km, minimum_base_km)
    allowed_increase = base_km * cap_percentage
    weekly_limit = base_km + allowed_increase
    remaining_km = max(0, weekly_limit - current_week_km)

    return MileageCapResult(
        current_week_km=current_week_km,
        previous_week_km=previous_week_km,
        weekly_limit_km=weekly_limit,
        remaining_km=remaining_km,
        is_exceeded=current_week_km > weekly_limit,
    )
```

---

## Implementation 2: Mobile UX Improvements

### Bottom Navigation Redesign

**Current**: 6 items causing cognitive overload
**New**: 5 items with "More" menu

```typescript
// Primary nav items (always visible)
const PRIMARY_NAV_ITEMS = [
  { id: 'home', href: '/', icon: HomeIcon },
  { id: 'workouts', href: '/workouts', icon: BoltIcon },
  { id: 'chat', href: '/chat', icon: ChatIcon, requiredLevel: 8 },
  { id: 'achievements', href: '/achievements', icon: ChartIcon },
  { id: 'more', href: '#', icon: MenuIcon, isMore: true },
];

// Secondary items (in "More" sheet)
const SECONDARY_NAV_ITEMS = [
  { id: 'zones', href: '/zones' },
  { id: 'goals', href: '/goals' },
  { id: 'plans', href: '/plans', requiredLevel: 10 },
  { id: 'connect', href: '/connect' },
];
```

### Touch Chart Interactions

```typescript
interface UseTouchChartReturn {
  // Touch state
  touchState: TouchState;
  pinchState: PinchState;
  pinnedTooltip: PinnedTooltip | null;

  // Transform state
  scale: number;
  offsetX: number;

  // Event handlers
  handleTouchStart: (e: React.TouchEvent) => void;
  handleTouchMove: (e: React.TouchEvent) => void;
  handleTouchEnd: (e: React.TouchEvent) => void;
  handleTap: (e: React.TouchEvent, dataIndex: number) => void;

  // Actions
  resetZoom: () => void;
  clearPinnedTooltip: () => void;
}
```

**Features**:
- **Tap-to-pin**: Tap a data point to pin tooltip
- **Swipe scrub**: Horizontal swipe to scrub timeline
- **Pinch-to-zoom**: Two-finger zoom on time range
- **Synchronized touch**: Touch on one chart highlights all charts

### Pull-to-Refresh

```typescript
interface PullToRefreshOptions {
  threshold: number;        // 80px default
  maxPullDistance: number;  // 120px default
  resistance: number;       // 2.5x pull resistance
  onRefresh: () => Promise<void>;
}
```

### Haptic Feedback System

```typescript
const VIBRATION_PATTERNS: Record<HapticPattern, number[]> = {
  light: [10],
  medium: [20],
  heavy: [30],
  selection: [10, 10, 10],
  success: [10, 30, 10],
  warning: [30, 20, 30],
  error: [50, 50, 50, 50, 50],
};

// Usage
const { triggerHaptic } = useHaptic();
triggerHaptic('success');  // On achievement unlock
triggerHaptic('selection'); // On nav item tap
```

### CSS Additions

```css
/* Touch target enforcement */
.touch-target-48 {
  min-width: 48px;
  min-height: 48px;
}

/* Momentum scrolling */
.momentum-scroll {
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

/* Safe area handling */
.safe-area-inset-bottom {
  padding-bottom: max(env(safe-area-inset-bottom), 16px);
}
```

---

## Implementation 3: Safety Features

### ACWR Spike Detection

```python
@dataclass
class ACWRSpikeAlert:
    """Alert for dangerous training load increases."""
    alert_type: str  # 'spike_warning' | 'spike_danger'
    current_week_load: float
    previous_week_load: float
    change_percentage: float
    risk_level: str  # 'moderate' | 'high' | 'critical'
    message: str
    recommendation: str

def detect_acwr_spike(
    current_week_load: float,
    previous_week_load: float,
    warning_threshold: float = 0.15,  # 15%
    danger_threshold: float = 0.25,   # 25%
) -> Optional[ACWRSpikeAlert]:
    """
    Detect dangerous week-over-week load increases.
    Research shows >15% weekly increase = elevated injury risk.
    """
    if previous_week_load <= 0:
        return None

    change_pct = (current_week_load - previous_week_load) / previous_week_load

    if change_pct > danger_threshold:
        return ACWRSpikeAlert(
            alert_type='spike_danger',
            change_percentage=change_pct * 100,
            risk_level='critical',
            message=f"Training load increased {change_pct*100:.0f}% - high injury risk!",
            recommendation="Reduce intensity for next 2-3 days",
        )
    elif change_pct > warning_threshold:
        return ACWRSpikeAlert(
            alert_type='spike_warning',
            change_percentage=change_pct * 100,
            risk_level='moderate',
            message=f"Training load increased {change_pct*100:.0f}% - monitor closely",
            recommendation="Consider easier sessions this week",
        )
    return None
```

### Training Monotony & Strain

```python
def calculate_monotony_strain(daily_loads: List[float]) -> Dict[str, Any]:
    """
    Calculate training monotony and strain metrics.

    Monotony = weekly_load_mean / weekly_load_std_dev
    Strain = weekly_load * monotony

    Thresholds:
    - Monotony > 2.0: High injury risk
    - Strain > 6000: Excessive training stress
    """
    if len(daily_loads) < 7:
        return None

    weekly_load = sum(daily_loads)
    mean_load = weekly_load / len(daily_loads)
    std_dev = (sum((x - mean_load) ** 2 for x in daily_loads) / len(daily_loads)) ** 0.5

    monotony = mean_load / std_dev if std_dev > 0 else float('inf')
    strain = weekly_load * monotony

    return {
        'monotony': monotony,
        'strain': strain,
        'monotony_risk': monotony > 2.0,
        'strain_risk': strain > 6000,
    }
```

### Alert Types

```python
class SafetyAlertType(str, Enum):
    ACWR_SPIKE = "acwr_spike"
    MONOTONY_HIGH = "monotony_high"
    STRAIN_EXCESSIVE = "strain_excessive"
    CONSECUTIVE_INTENSITY = "consecutive_intensity"
    CTL_DROP = "ctl_drop"
    TSB_EXTENDED_NEGATIVE = "tsb_extended_negative"
    WEEKLY_DISTANCE_SPIKE = "weekly_distance_spike"

# Example alerts
ALERT_TEMPLATES = {
    SafetyAlertType.CONSECUTIVE_INTENSITY: {
        'message': "3 consecutive days at high intensity - injury risk elevated",
        'severity': 'warning',
    },
    SafetyAlertType.CTL_DROP: {
        'message': "CTL dropped 20% - risk of injury upon resumption",
        'severity': 'info',
    },
    SafetyAlertType.TSB_EXTENDED_NEGATIVE: {
        'message': "TSB below -25 for 2 weeks - overtraining syndrome risk",
        'severity': 'danger',
    },
}
```

---

## Implementation 4: Emotional Design

### Purpose Anchoring

```sql
CREATE TABLE IF NOT EXISTS user_purpose (
    user_id TEXT PRIMARY KEY,
    primary_purpose TEXT NOT NULL,  -- 'health', 'family', 'competition', 'stress_relief', 'community'
    secondary_purpose TEXT,
    purpose_statement TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**Purpose Options**:
| ID | Label | Icon | Sample Message |
|----|-------|------|----------------|
| health | Health & Longevity | ❤️ | "Every workout is an investment in your future self." |
| family | Family & Loved Ones | 👨‍👩‍👧‍👦 | "Training today so you can play with your grandchildren tomorrow." |
| competition | Competition & Achievement | 🏆 | "Champions are made in training, not on race day." |
| stress_relief | Stress Relief & Mental Health | 🧘 | "Movement is medicine for the mind." |
| community | Community & Connection | 🤝 | "You're part of a global community of athletes." |

### Comeback Challenge

```sql
CREATE TABLE IF NOT EXISTS comeback_challenges (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    triggered_at TEXT NOT NULL,
    previous_streak INTEGER NOT NULL,
    status TEXT DEFAULT 'active',  -- 'active', 'completed', 'expired'
    day1_completed_at TEXT,
    day2_completed_at TEXT,
    day3_completed_at TEXT,
    xp_multiplier REAL DEFAULT 1.5,
    bonus_xp_earned INTEGER DEFAULT 0,
    expires_at TEXT NOT NULL,  -- 7 days
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**Trigger Conditions**:
- Previous streak ≥ 3 days
- No active comeback challenge exists

**Mechanics**:
- 3-day challenge to restore streak
- 1.5x XP multiplier during challenge
- Expires after 7 days

### PR Detection

```python
PR_THRESHOLDS = {
    "running": {
        "pace": {"min_distance_km": 1.0},
        "distance": {"min_duration_min": 10},
        "elevation": {"min_distance_km": 3.0},
    },
    "cycling": {
        "pace": {"min_distance_km": 5.0},
        "power": {"min_duration_min": 20},
    },
}

# PR Types
class PRType(str, Enum):
    PACE = "pace"         # Fastest pace (lower is better)
    DISTANCE = "distance" # Longest distance
    DURATION = "duration" # Longest workout
    ELEVATION = "elevation" # Most elevation gain
    POWER = "power"       # Highest avg power (cycling)
```

### Emotional Support Messages

```typescript
const EMOTIONAL_MESSAGE_BANK: Record<EmotionalContext, EmotionalMessage[]> = {
  red_zone_readiness: [
    {
      message: "Your body is telling you something important. Rest isn't weakness - it's wisdom.",
      tone: 'empathetic',
      actionSuggestion: 'Consider a light walk or stretching instead.',
    },
  ],
  streak_break: [
    {
      message: "Life happens. One day doesn't erase all your progress.",
      tone: 'supportive',
    },
  ],
  plateau: [
    {
      message: "Plateaus are your body consolidating gains. They often precede breakthroughs.",
      tone: 'encouraging',
    },
  ],
  bad_workout: [
    {
      message: "Some days the legs just aren't there. That's normal and okay.",
      tone: 'empathetic',
    },
  ],
};
```

### Identity Commitment

```sql
CREATE TABLE IF NOT EXISTS identity_statements (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL UNIQUE,
    statement TEXT NOT NULL,  -- "...runs every morning"
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_reinforced_at TEXT,
    reinforcement_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**Templates**:
- "trains consistently, no matter what"
- "prioritizes their health every day"
- "shows up even when it's hard"
- "values discipline over motivation"

### Social Proof

```typescript
interface SocialProofStats {
  athletesTrainedToday: number;
  workoutsCompletedToday: number;
  pacePercentile?: number;      // "faster than 75% of athletes"
  streakPercentile?: number;    // "longer streak than 80%"
  levelPercentile?: number;     // "top 15% by level"
}
```

---

## Implementation 5: Sports Science Features

### Pace Zones (Daniels' VDOT)

```python
def calculate_vdot(race_distance_m: float, race_time_sec: float) -> float:
    """
    Calculate VDOT using Daniels' formula.

    VDOT relates running velocity to oxygen cost.
    """
    velocity = race_distance_m / race_time_sec  # m/s

    # Oxygen cost (ml/kg/min)
    oxygen_cost = -4.60 + 0.182258 * velocity * 60 + 0.000104 * (velocity * 60) ** 2

    # Time in minutes
    time_min = race_time_sec / 60

    # Percent VO2max sustained
    pct_max = 0.8 + 0.1894393 * math.exp(-0.012778 * time_min) + \
              0.2989558 * math.exp(-0.1932605 * time_min)

    vdot = oxygen_cost / pct_max
    return vdot

# Zone Definitions
VDOT_ZONES = {
    'easy': (0.59, 0.74),      # 59-74% VO2max
    'marathon': (0.75, 0.84),   # 75-84% VO2max
    'threshold': (0.83, 0.88),  # 83-88% VO2max
    'interval': (0.95, 1.00),   # 95-100% VO2max
    'repetition': (1.05, 1.20), # 105-120% VO2max
}
```

### Enhanced Recovery Module

```python
def calculate_sleep_debt(
    sleep_records: List[SleepRecord],
    target_hours: float = 8.0,
    lookback_days: int = 7,
) -> SleepDebtResult:
    """
    Calculate 7-day rolling sleep debt.
    """
    total_debt = sum(
        max(0, target_hours - record.duration_hours)
        for record in sleep_records[-lookback_days:]
    )

    impact = (
        'minimal' if total_debt < 3 else
        'moderate' if total_debt < 7 else
        'significant' if total_debt < 14 else
        'severe'
    )

    return SleepDebtResult(
        total_debt_hours=total_debt,
        impact_level=impact,
        recommendation=get_sleep_recommendation(impact),
    )

def calculate_hrv_cv(hrv_values: List[float]) -> float:
    """
    Calculate HRV Coefficient of Variation (more stable than raw HRV).
    CV% = (std_dev / mean) * 100
    """
    mean_hrv = sum(hrv_values) / len(hrv_values)
    variance = sum((x - mean_hrv) ** 2 for x in hrv_values) / len(hrv_values)
    std_dev = variance ** 0.5
    return (std_dev / mean_hrv) * 100
```

### Cardiac Drift Detection

```python
def analyze_cardiac_drift(
    hr_data: List[int],
    pace_data: List[float],
    duration_sec: int,
) -> CardiacDriftResult:
    """
    Analyze cardiac drift by comparing first vs second half.

    Decoupling % = ((EF1 - EF2) / EF1) * 100
    Where EF = pace / HR (Efficiency Factor)
    """
    midpoint = len(hr_data) // 2

    # First half
    avg_hr_1 = sum(hr_data[:midpoint]) / midpoint
    avg_pace_1 = sum(pace_data[:midpoint]) / midpoint
    ef_1 = avg_pace_1 / avg_hr_1

    # Second half
    avg_hr_2 = sum(hr_data[midpoint:]) / (len(hr_data) - midpoint)
    avg_pace_2 = sum(pace_data[midpoint:]) / (len(pace_data) - midpoint)
    ef_2 = avg_pace_2 / avg_hr_2

    decoupling_pct = ((ef_1 - ef_2) / ef_1) * 100

    assessment = (
        'excellent' if decoupling_pct < 2 else
        'good' if decoupling_pct < 5 else
        'developing' if decoupling_pct < 7.5 else
        'deficiency' if decoupling_pct < 10 else
        'significant_deficiency'
    )

    return CardiacDriftResult(
        decoupling_pct=decoupling_pct,
        assessment=assessment,
        first_half_ef=ef_1,
        second_half_ef=ef_2,
    )
```

### Exponential Taper

```python
TAPER_PARAMS = {
    '5k': {'duration_days': 7, 'time_constant': 3.0, 'final_volume_pct': 0.50},
    '10k': {'duration_days': 10, 'time_constant': 4.0, 'final_volume_pct': 0.45},
    'half_marathon': {'duration_days': 14, 'time_constant': 5.0, 'final_volume_pct': 0.40},
    'marathon': {'duration_days': 21, 'time_constant': 7.0, 'final_volume_pct': 0.35},
    'ultra': {'duration_days': 28, 'time_constant': 10.0, 'final_volume_pct': 0.30},
}

def calculate_taper_load(
    baseline_load: float,
    days_before_race: int,
    time_constant: float,
) -> float:
    """
    Calculate training load using exponential decay.
    Load(day) = Baseline * e^(-day/time_constant)
    """
    return baseline_load * math.exp(-days_before_race / time_constant)
```

### Race Pacing Strategy

```python
# Weather Adjustments
WEATHER_ADJUSTMENTS = {
    'temperature': 0.015,  # +1.5% per degree above 12C
    'humidity': 0.005,     # +0.5% per 10% above 50%
    'headwind_light': 0.02,
    'headwind_moderate': 0.04,
    'headwind_strong': 0.06,
}

# Elevation Adjustments
def adjust_pace_for_elevation(base_pace_sec: float, grade_pct: float) -> float:
    """
    Adjust pace for elevation.
    Uphill: +15 sec/km per 1% grade
    Downhill: -7 sec/km per 1% grade (capped)
    """
    if grade_pct > 0:
        return base_pace_sec + (grade_pct * 15)
    else:
        adjustment = abs(grade_pct) * 7
        return max(base_pace_sec - adjustment, base_pace_sec - 20)
```

---

## File Structure Summary

### New Frontend Files

```
frontend/src/
├── contexts/
│   └── preferences-context.tsx
├── components/
│   ├── beginner/
│   │   ├── RPEScale.tsx
│   │   ├── RunWalkBuilder.tsx
│   │   ├── RunWalkTimer.tsx
│   │   └── WeeklyMileageAlert.tsx
│   ├── dashboard/
│   │   └── FocusView.tsx
│   ├── emotional/
│   │   ├── PurposeOnboarding.tsx
│   │   ├── ComebackChallengeCard.tsx
│   │   ├── PRCelebrationModal.tsx
│   │   ├── EmotionalMessageCard.tsx
│   │   ├── IdentityStatementEditor.tsx
│   │   └── SocialProofBanner.tsx
│   ├── ui/
│   │   ├── BottomNavigation.tsx
│   │   ├── MoreMenuSheet.tsx
│   │   ├── BottomSheet.tsx
│   │   └── PullToRefresh.tsx
│   └── charts/
│       └── TouchableChartWrapper.tsx
├── hooks/
│   ├── useHaptic.ts
│   ├── usePullToRefresh.ts
│   └── useTouchChart.ts
└── types/
    ├── navigation.ts
    ├── touch-chart.ts
    └── haptic.ts
```

### New Backend Files

```
src/
├── api/routes/
│   ├── preferences.py
│   ├── emotional.py
│   └── safety.py
├── services/
│   ├── mileage_cap.py
│   ├── emotional_service.py
│   ├── pr_detection_service.py
│   ├── safety_service.py
│   ├── recovery_service.py
│   ├── taper_service.py
│   └── race_pacing_service.py
├── metrics/
│   ├── vdot.py
│   ├── running_economy.py
│   └── cardiac_drift.py
└── models/
    └── emotional.py
```

---

## Quick Reference: API Endpoints

### Beginner Mode
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/preferences` | Get user preferences |
| PUT | `/api/preferences` | Update preferences |
| POST | `/api/preferences/toggle-beginner-mode` | Toggle beginner mode |
| POST | `/api/workouts/manual` | Log RPE-based workout |
| GET | `/api/athlete/mileage-cap` | Get weekly cap status |

### Emotional Design
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/emotional/purpose` | Get user purpose |
| POST | `/api/emotional/purpose` | Set user purpose |
| GET | `/api/emotional/comeback-challenge` | Get active challenge |
| POST | `/api/emotional/comeback-challenge/record` | Record challenge workout |
| GET | `/api/emotional/prs` | Get personal records |
| GET | `/api/emotional/social-proof` | Get social proof stats |

### Safety
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/safety/alerts` | Get active safety alerts |
| POST | `/api/safety/alerts/{id}/acknowledge` | Acknowledge alert |
| GET | `/api/safety/load-analysis` | Get load analysis |

### Sports Science
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/pace-zones/calculate-vdot` | Calculate VDOT |
| GET | `/api/pace-zones/my-zones` | Get pace zones |
| GET | `/api/recovery/score` | Get recovery score |
| GET | `/api/recovery/sleep-debt` | Get sleep debt |
| POST | `/api/taper/generate` | Generate taper plan |
| POST | `/api/race-pacing/generate` | Generate race plan |

---

## Implementation 6: Phase 2 - Onboarding & New User Experience (COMPLETED)

This section documents the completed Phase 2 implementation focusing on new user experience improvements.

### 6.1 Three-Phase Onboarding Flow

**Files Created:**
- `frontend/src/components/onboarding/OnboardingFlow.tsx` - Main orchestrator
- `frontend/src/components/onboarding/WelcomeStep.tsx` - Welcome screen
- `frontend/src/components/onboarding/ConnectionStep.tsx` - Garmin/Strava connection
- `frontend/src/components/onboarding/ProfileStep.tsx` - User profile setup
- `frontend/src/components/onboarding/FeatureIntroStep.tsx` - Feature introduction
- `frontend/src/contexts/onboarding-context.tsx` - State management

**Flow Structure:**
```
Step 1: Welcome
├── App introduction
├── Value proposition
└── Get started CTA

Step 2: Connection
├── Garmin Connect option
├── Strava option (coming soon)
└── Skip option (limited features)

Step 3: Profile
├── Training goals selection
├── Experience level
├── Preferred units
└── Weekly availability
```

**Key Features:**
- Progress indicator with step dots
- Animated transitions between steps
- Persistence via localStorage
- Skip functionality with feature limitations warning
- Auto-detection of returning users

### 6.2 Purpose Anchoring

**Files Created:**
- `frontend/src/components/onboarding/PurposeStep.tsx` - Purpose selection during onboarding
- `frontend/src/components/dashboard/PurposeReminder.tsx` - Dashboard reminder widget
- `frontend/src/hooks/usePurpose.ts` - Purpose state management

**Purpose Options:**
| ID | Label | Icon | Motivation Message |
|----|-------|------|-------------------|
| `health` | Health & Longevity | ❤️ | "Every workout is an investment in your future self." |
| `family` | Family & Loved Ones | 👨‍👩‍👧‍👦 | "Training today so you can keep up with those you love." |
| `competition` | Competition & Achievement | 🏆 | "Champions are made in training, not on race day." |
| `stress_relief` | Mental Wellness | 🧘 | "Movement is medicine for the mind." |
| `community` | Community & Connection | 🤝 | "You're part of a global community of athletes." |

**PurposeReminder Component:**
- Displays on dashboard when readiness is low (red/yellow zone)
- Shows personalized message based on selected purpose
- Reinforces "why" during difficult moments
- Dismissible but reappears on new sessions

### 6.3 Early Win Achievements

**Files Modified:**
- `src/services/achievement_service.py` - Added early win achievements
- `src/models/gamification.py` - Added `early_win` category
- `src/api/routes/gamification.py` - Added check endpoint

**New Achievements (category: `early_win`):**
| ID | Name | XP | Trigger |
|----|------|-----|---------|
| `early_first_steps` | First Steps 👋 | 15 | First login after connection |
| `early_profile_complete` | Profile Complete 📝 | 20 | Complete profile setup |
| `early_first_workout` | First Workout Logged 🏃 | 25 | Log first workout (synced/manual) |
| `early_bird` | Early Bird 🌅 | 15 | Login before 7am |
| `night_owl` | Night Owl 🦉 | 15 | Login after 10pm |
| `early_explorer` | Explorer 🧭 | 15 | Visit 3 different pages |

**API Endpoint:**
```python
POST /api/gamification/check-early-achievements
{
  "context": {
    "just_logged_in": true,
    "profile_completed": false,
    "first_workout_synced": false,
    "login_hour": 6,
    "pages_visited": ["dashboard", "workouts"]
  }
}
```

**Design Principles:**
- Guaranteed within first session
- Low XP values (15-25) to avoid devaluing later achievements
- Negative `display_order` to appear first in achievement list
- Creates immediate positive reinforcement

### 6.4 Dashboard Focus Mode

**Files Created:**
- `frontend/src/components/dashboard/FocusView.tsx` - Simplified dashboard view
- `frontend/src/components/dashboard/DashboardToggle.tsx` - Toggle button

**Focus View Design:**
```
┌─────────────────────────────────────┐
│         READINESS: 78               │
│       Ready for Quality             │
│                                     │
│  "Your body is recovered and        │
│   ready for a challenge."           │
│                                     │
│  Today's Suggestion:                │
│  45min Easy Run                     │
│                                     │
│      [View Full Dashboard]          │
└─────────────────────────────────────┘
```

**Key Features:**
- Single hero metric (Readiness score)
- Motivational message based on zone (green/yellow/red)
- Today's suggested workout
- One-tap expansion to full dashboard
- Preference persisted in localStorage
- Defaults to Focus View for users level < 5

**Zone-Based Messaging:**
| Zone | Score | Message | Sub-message |
|------|-------|---------|-------------|
| Green | ≥75 | "Ready for Quality" | "Your body is recovered and ready for a challenge." |
| Yellow | 50-74 | "Good for Steady" | "A moderate effort today will build your base." |
| Red | <50 | "Focus on Recovery" | "Rest is when adaptation happens. Honor your body." |

### 6.5 Contextual Tooltips

**Files Created:**
- `frontend/src/components/onboarding/ContextualTooltip.tsx` - Tooltip component
- `frontend/src/components/onboarding/TooltipTriggers.tsx` - Trigger definitions
- `frontend/src/hooks/useContextualTooltips.ts` - Tooltip state management

**Tooltip Triggers:**
| ID | Trigger Condition | Message |
|----|-------------------|---------|
| `no_workouts` | User has no workouts | "Connect your device to import your training history" |
| `first_workout_synced` | Just synced first workout | "Great! Your first workout is here. Tap to see the analysis." |
| `first_analysis_viewed` | Viewing first analysis | "This is your workout breakdown. XP is earned by viewing analyses." |
| `first_achievement_earned` | First achievement unlocked | "You earned your first achievement! Keep going to unlock more." |
| `level_up` | User just leveled up | "Level up! You've unlocked {feature}." |

**Implementation Details:**
```typescript
interface TooltipConditions {
  hasNoWorkouts: boolean;
  justSyncedFirstWorkout: boolean;
  viewingFirstAnalysis: boolean;
  justEarnedFirstAchievement: boolean;
  justLeveledUp: boolean;
  currentLevel?: number;
  unlockedFeatures?: string[];
}
```

**Features:**
- One tooltip shown at a time (priority-based)
- Dismiss persisted to localStorage
- Won't show again after dismissed
- Animated entrance/exit
- Positioned contextually near relevant UI element

### 6.6 i18n Support

**Files Modified:**
- `frontend/src/messages/en.json` - English translations
- `frontend/src/messages/es.json` - Spanish translations

**Translation Keys Added:**
```json
{
  "onboarding": {
    "welcome": { "title", "subtitle", "getStarted" },
    "connection": { "title", "garmin", "strava", "skip" },
    "profile": { "title", "goals", "experience", "units" },
    "purpose": { "title", "health", "family", "competition", "mental", "community" }
  },
  "focusView": {
    "readyForQuality", "readyForQualityMessage",
    "goodForSteady", "goodForSteadyMessage",
    "focusOnRecovery", "focusOnRecoveryMessage",
    "viewFullDashboard"
  },
  "tooltips": {
    "noWorkouts", "firstWorkout", "firstAnalysis", "firstAchievement", "levelUp"
  }
}
```

### 6.7 File Structure Summary

```
frontend/src/
├── components/
│   ├── dashboard/
│   │   ├── FocusView.tsx          # Simplified dashboard
│   │   ├── DashboardToggle.tsx    # Focus/Full toggle
│   │   └── PurposeReminder.tsx    # Purpose motivation widget
│   └── onboarding/
│       ├── OnboardingFlow.tsx     # Main orchestrator
│       ├── WelcomeStep.tsx        # Step 1
│       ├── ConnectionStep.tsx     # Step 2
│       ├── ProfileStep.tsx        # Step 3
│       ├── PurposeStep.tsx        # Purpose selection
│       ├── FeatureIntroStep.tsx   # Feature introduction
│       ├── ContextualTooltip.tsx  # Tooltip component
│       ├── TooltipTriggers.tsx    # Trigger definitions
│       └── index.ts               # Exports
├── contexts/
│   └── onboarding-context.tsx     # Onboarding state
├── hooks/
│   ├── usePurpose.ts              # Purpose hook
│   └── useContextualTooltips.ts   # Tooltips hook
└── messages/
    ├── en.json                    # +243 lines
    └── es.json                    # +243 lines

src/
├── services/
│   └── achievement_service.py     # +220 lines (early wins)
├── models/
│   └── gamification.py            # +60 lines (early win types)
└── api/routes/
    └── gamification.py            # +50 lines (check endpoint)
```

### 6.8 Success Metrics

Phase 2 targets from the roadmap:
- **Day-7 retention increase**: 20% improvement target
- **First-session completion**: Track onboarding completion rate
- **Early achievement unlock rate**: >80% of new users should earn at least one

**Tracking Points:**
1. Onboarding step completion rates
2. Purpose selection distribution
3. Focus view vs full dashboard preference
4. Tooltip dismiss rates
5. Early achievement unlock timing

---

## Implementation 7: Phase 5 - Advanced Features (BACKEND COMPLETE)

This section documents the Phase 5 implementation. **Backend is 100% complete** with all services and API routes implemented. **Frontend integration is pending** - components exist for race pacing and chart comparison but are not yet integrated into pages. Recovery, patterns, and economy features need frontend UI development.

### 7.1 Enhanced Recovery Module

**Files Created:**
- `src/services/recovery_module_service.py` - Core recovery analysis service (896 lines)
- `src/api/routes/recovery.py` - Recovery API endpoints
- `src/models/recovery.py` - Recovery data models

**Key Features:**
1. **7-Day Rolling Sleep Debt Analysis**
   - Tracks sleep debt accumulation over rolling 7-day window
   - Impact levels: minimal, moderate, significant, severe
   - Personalized recommendations based on debt level

2. **HRV Trend Analysis**
   - Coefficient of Variation (CV) calculation for HRV stability
   - Trend direction detection (improving, stable, declining)
   - Relative to baseline comparison
   - Minimum 7 days of data required for analysis

3. **Post-Workout Recovery Time Estimation**
   - Factors in workout intensity, duration, and HRSS
   - Adjusts based on current TSB, sleep debt, and HRV status
   - VO2max consideration for personalized estimates
   - Returns recovery time in hours with confidence level

4. **Overall Recovery Score**
   - Combines all recovery factors into single score (0-100)
   - Recovery status: excellent, good, fair, poor, critical
   - Data freshness tracking
   - Comprehensive recommendations

**API Endpoints:**
- `GET /api/recovery/` - Get complete recovery module data
- `GET /api/recovery/sleep-debt` - Get sleep debt analysis
- `GET /api/recovery/hrv-trend` - Get HRV trend analysis
- `GET /api/recovery/recovery-time` - Get recovery time estimate

**Example Response:**
```json
{
  "success": true,
  "data": {
    "recovery_score": 78,
    "recovery_status": "good",
    "sleep_debt": {
      "total_debt_hours": 3.5,
      "impact_level": "moderate",
      "recommendation": "Aim for 8.5 hours tonight"
    },
    "hrv_trend": {
      "trend_direction": "improving",
      "cv_percent": 8.2,
      "relative_to_baseline": 1.05
    },
    "recovery_time": {
      "estimated_hours": 24,
      "confidence": "high"
    }
  }
}
```

### 7.2 AI Pattern Recognition Service

**Files Created:**
- `src/services/pattern_recognition_service.py` - Pattern analysis service
- `src/api/routes/patterns.py` - Pattern recognition API endpoints
- `src/models/patterns.py` - Pattern data models

**Key Features:**
1. **Timing Pattern Analysis**
   - Performance by time of day (early morning, morning, afternoon, evening, night)
   - Performance by day of week
   - Identifies optimal training windows
   - Minimum 10 workouts required for analysis

2. **TSB Performance Correlation**
   - Identifies optimal TSB range for peak performance
   - Performance statistics by TSB zone (negative, low, optimal, high)
   - Individual optimal TSB range calculation
   - Correlation strength analysis

3. **Fitness Prediction**
   - CTL trajectory projection (7, 14, 30 days)
   - Peak fitness date prediction
   - Confidence intervals based on historical data
   - Planned event consideration

4. **Performance Correlations**
   - Multi-factor correlation analysis
   - Identifies factors most correlated with performance
   - Statistical significance testing

**API Endpoints:**
- `GET /api/patterns/timing` - Get timing pattern analysis
- `GET /api/patterns/tsb-optimal` - Get optimal TSB range
- `GET /api/patterns/fitness-prediction` - Get fitness predictions
- `GET /api/patterns/correlations` - Get performance correlations

**Example Response:**
```json
{
  "optimal_time_slot": {
    "time_of_day": "morning",
    "avg_performance_score": 0.85,
    "workout_count": 42
  },
  "optimal_day": {
    "day_of_week": "tuesday",
    "avg_performance_score": 0.82
  },
  "optimal_tsb_range": {
    "min": 5.0,
    "max": 15.0,
    "avg_performance": 0.88
  }
}
```

### 7.3 Race Pacing Generator

**Files Created:**
- `src/services/race_pacing_service.py` - Pacing plan generation service (409 lines)
- `src/api/routes/race_pacing.py` - Race pacing API endpoints
- `src/models/race_pacing.py` - Pacing data models
- `frontend/src/components/race/PacingPlanGenerator.tsx` - Frontend UI component

**Key Features:**
1. **Pacing Strategy Selection**
   - Even split: Consistent pace throughout
   - Negative split: Faster second half (recommended for most distances)
   - Positive split: Faster first half (rarely optimal)
   - Variable: Terrain-adjusted pacing

2. **Weather Adjustments**
   - Temperature adjustments (+1.5% per degree above 12°C)
   - Humidity adjustments (+0.5% per 10% above 60%)
   - Wind adjustments (headwind/tailwind)
   - Altitude adjustments

3. **Elevation Profile Support**
   - Uphill adjustments (+8% pace per 1% grade)
   - Downhill adjustments (-3% pace per 1% grade, capped)
   - Net elevation gain consideration
   - Per-km elevation adjustments

4. **Split Generation**
   - Per-km or per-mile splits
   - Cumulative time tracking
   - Elevation-adjusted pace per split
   - Strategy-specific pace modifiers
   - Split notes and recommendations

**API Endpoints:**
- `POST /api/race-pacing/pacing-plan` - Generate pacing plan
- `POST /api/race-pacing/weather-adjustment` - Calculate weather adjustments
- `GET /api/race-pacing/strategies` - Get available strategies

**Example Request:**
```json
{
  "target_time_sec": 10800,
  "distance_km": 21.0975,
  "race_distance": "half_marathon",
  "strategy": "negative",
  "weather_conditions": {
    "temperature_c": 18,
    "humidity_pct": 65,
    "wind_speed_kmh": 15
  },
  "course_profile": {
    "total_elevation_gain_m": 200,
    "net_elevation_gain_m": 50
  }
}
```

### 7.4 Chart Comparison Mode

**Files Created:**
- `frontend/src/hooks/useChartComparison.ts` - Comparison state management hook
- `frontend/src/components/charts/ComparisonChart.tsx` - Comparison chart component
- `frontend/src/components/charts/ComparisonSelector.tsx` - Comparison selector UI
- `frontend/src/components/charts/ComparisonLegend.tsx` - Comparison legend
- `frontend/src/types/comparison.ts` - Comparison type definitions
- `src/api/routes/comparison.py` - Comparison API endpoints (backend)

**Key Features:**
1. **Workout Comparison**
   - Compare any two workouts side-by-side
   - Normalized time series alignment
   - Multiple normalization modes (percentage, distance, time)
   - Quick selection presets (PR, best 10K, last week, etc.)

2. **Multi-Metric Comparison**
   - Heart rate comparison
   - Pace comparison
   - Power comparison (cycling)
   - Cadence comparison
   - Elevation comparison

3. **Visual Features**
   - Overlaid line charts with different styles
   - Difference area shading between lines
   - Synchronized tooltips
   - Statistical summary display
   - Toggle comparison on/off

4. **Comparison Statistics**
   - Average difference calculation
   - Peak difference identification
   - Performance delta percentages
   - Zone distribution comparison

**API Endpoints:**
- `GET /api/comparison/comparable/{activity_id}` - Get comparable workouts
- `GET /api/comparison/normalized/{activity_id}` - Get normalized data
- `POST /api/comparison/compare` - Compare two workouts

**Usage Example:**
```typescript
const {
  isComparisonEnabled,
  comparableWorkouts,
  selectComparison,
  comparisonData,
} = useChartComparison({ activityId: workout.id });

// Enable comparison mode
enableComparison();

// Select a workout to compare
selectComparison('workout-123');

// Display comparison chart
<ComparisonChart
  primaryData={workoutData}
  comparisonData={comparisonData}
  metric="heart_rate"
  showDifference={true}
/>
```

### 7.5 Running Economy Tracking

**Files Created:**
- `src/services/running_economy_service.py` - Running economy service (215 lines)
- `src/api/routes/economy.py` - Economy API endpoints
- `src/models/running_economy.py` - Economy data models

**Key Features:**
1. **Economy Ratio Calculation**
   - Formula: `pace_seconds_per_km / avg_hr`
   - Lower values indicate better economy
   - Personal best tracking
   - Comparison to best economy

2. **Pace Zone Economy Analysis**
   - Economy by pace zone (easy, tempo, threshold, interval)
   - Zone-specific economy trends
   - Identifies most efficient zones
   - Improvement tracking per zone

3. **Cardiac Drift Detection**
   - First half vs second half HR comparison
   - Decoupling percentage calculation
   - Severity classification (minimal, moderate, significant)
   - Aerobic base deficiency detection

4. **Economy Trends**
   - 7, 30, 90-day trend analysis
   - Improvement/decline detection
   - Statistical significance testing
   - Confidence intervals

**API Endpoints:**
- `GET /api/economy/current` - Get current economy metrics
- `GET /api/economy/trend` - Get economy trend analysis
- `GET /api/economy/cardiac-drift/{activity_id}` - Get cardiac drift analysis
- `GET /api/economy/pace-zones` - Get economy by pace zone

**Example Response:**
```json
{
  "has_data": true,
  "current": {
    "economy_ratio": 2.05,
    "pace_sec_per_km": 300,
    "avg_hr": 146,
    "pace_zone": "easy",
    "comparison_to_best": -2.4,
    "economy_label": "Good"
  },
  "trend": {
    "direction": "improving",
    "change_percent": 3.2,
    "confidence": "high"
  }
}
```

### 7.6 File Structure Summary

```
src/
├── services/
│   ├── recovery_module_service.py      # 896 lines
│   ├── pattern_recognition_service.py  # Pattern analysis
│   ├── race_pacing_service.py       # 409 lines
│   └── running_economy_service.py     # 215 lines
├── api/routes/
│   ├── recovery.py                    # Recovery endpoints
│   ├── patterns.py                    # Pattern endpoints
│   ├── race_pacing.py                 # Pacing endpoints
│   ├── economy.py                     # Economy endpoints
│   └── comparison.py                  # Comparison endpoints
└── models/
    ├── recovery.py                    # Recovery models
    ├── patterns.py                    # Pattern models
    ├── race_pacing.py                 # Pacing models
    └── running_economy.py             # Economy models

frontend/src/
├── components/
│   ├── charts/
│   │   ├── ComparisonChart.tsx        # Comparison visualization
│   │   ├── ComparisonSelector.tsx     # Comparison UI
│   │   └── ComparisonLegend.tsx        # Legend component
│   └── race/
│       └── PacingPlanGenerator.tsx     # Pacing plan UI
├── hooks/
│   └── useChartComparison.ts           # Comparison hook
└── types/
    └── comparison.ts                   # Comparison types
```

### 7.7 Frontend Integration Status

**Completed:**
- ✅ Backend services and API routes for all 5 features
- ✅ Frontend components created for:
  - `ComparisonChart.tsx` - Chart comparison visualization
  - `PacingPlanGenerator.tsx` - Race pacing plan generator
  - `useChartComparison.ts` - Comparison state management hook

**Pending:**
- ❌ **Recovery Module UI**: No frontend pages/components
  - Need: Recovery dashboard page or widget
  - Need: Sleep debt visualization
  - Need: HRV trend charts
  - Need: Recovery time estimates display

- ❌ **Pattern Recognition UI**: No frontend pages/components
  - Need: Pattern analysis dashboard
  - Need: Timing pattern visualizations
  - Need: TSB optimal range display
  - Need: Fitness prediction charts

- ⚠️ **Race Pacing Generator**: Component exists but not integrated
  - Component: `PacingPlanGenerator.tsx` exists
  - Missing: Page route (e.g., `/race-pacing` or `/plans/race-pacing`)
  - Missing: Navigation link to access the feature

- ⚠️ **Chart Comparison Mode**: Components exist but not integrated
  - Components: `ComparisonChart.tsx`, `ComparisonSelector.tsx` exist
  - Missing: Integration into workout detail page
  - Missing: UI to enable/disable comparison mode

- ❌ **Running Economy UI**: No frontend pages/components
  - Need: Economy metrics display
  - Need: Economy trend charts
  - Need: Cardiac drift visualization
  - Need: Pace zone economy analysis

### 7.8 Next Steps for Frontend Integration

**Priority 1: Quick Wins (Components Already Exist)**
1. Create `/race-pacing` page and integrate `PacingPlanGenerator`
2. Add comparison toggle to workout detail page
3. Integrate `ComparisonChart` into workout charts section

**Priority 2: New UI Development**
4. Create recovery dashboard page (`/recovery`)
5. Create pattern analysis page (`/patterns` or `/insights`)
6. Create economy tracking page (`/economy`)

**Priority 3: Dashboard Integration**
7. Add recovery score widget to main dashboard
8. Add pattern insights summary to dashboard
9. Add economy quick view to dashboard

### 7.9 Success Metrics

Phase 5 targets from the roadmap:
- **Power user engagement**: Track usage of advanced features
- **Competitive advantage**: Differentiation through unique features
- **Feature adoption**: Monitor usage rates for each feature

**Tracking Points:**
1. Recovery module usage frequency
2. Pattern recognition insights generated
3. Pacing plans generated
4. Workout comparisons performed
5. Economy trend analysis views
6. Feature-specific user retention

**Current Status**: Backend ready for frontend integration. Frontend work needed to make features accessible to users.
