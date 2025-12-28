# UI Panels Documentation

This document describes the main UI panels in the Training Analyzer frontend application.

## Overview

The application features six main panels accessible from the left navigation sidebar:

| Panel | Route | Purpose |
|-------|-------|---------|
| Dashboard | `/[locale]` | Overview with readiness and fitness metrics |
| Workouts | `/[locale]/workouts` | Browse and analyze past workouts |
| Plans | `/[locale]/plans` | AI-generated training plans |
| Design | `/[locale]/design` | Custom workout designer |
| Goals | `/[locale]/goals` | Set and track training goals |
| Sync | `/[locale]/sync` | Sync data from Garmin |

## Dashboard (`/[locale]`)

The main dashboard displays:

- **Readiness Score** - Daily readiness based on HRV, sleep, and recovery data
- **Fitness Level** - Current VO2max estimate and training load
- **Recent Workouts** - Quick view of latest activities
- **Weekly Summary** - Training volume and intensity distribution

## Workouts Panel (`/[locale]/workouts`)

### Workouts List (`/[locale]/workouts`)

Displays a paginated list of all workouts with:

- Workout type icon and name
- Date and duration
- Key metrics (distance, pace, heart rate)
- Source badge (Garmin, manual, etc.)

**Features:**
- Pagination with configurable page size
- Filter by workout type
- Sort by date, duration, or distance

### Workout Detail (`/[locale]/workouts/[id]`)

Detailed view of a single workout including:

- **Summary Card** - Type, date, duration, distance
- **Metrics Section** - Heart rate zones, pace/power data
- **Map View** - GPS track visualization (if available)
- **Lap Data** - Split times and per-lap metrics
- **AI Analysis** - Explainability panel showing data sources

## Plans Panel (`/[locale]/plans`)

### Plans List (`/[locale]/plans`)

Shows all training plans with:

- Plan name and goal
- Duration (weeks)
- Status (active, completed, draft)
- Progress indicator

### New Plan (`/[locale]/plans/new`)

AI-powered plan generator using the `PlanGenerator` component:

**Input Fields:**
- Goal type (race, fitness, weight loss)
- Target event/date
- Current fitness level
- Available training days per week
- Preferred workout types

**Output:**
- Periodized training plan
- Weekly structure with workout types
- Progressive overload schedule
- Recovery weeks built in

### Plan Detail (`/[locale]/plans/[id]`)

Detailed view of a training plan:

- **Calendar View** - Visual weekly/monthly layout
- **Workout List** - All scheduled workouts
- **Progress Tracking** - Completed vs planned
- **Adjustments** - AI suggestions based on actual performance

## Design Panel (`/[locale]/design`)

The `WorkoutDesigner` component provides a drag-and-drop interface for creating custom workouts.

### Features

- **Workout Type Selection** - Running, cycling, swimming, strength
- **Interval Builder** - Create complex interval structures
- **Zone Targets** - Set heart rate or power zones for each segment
- **Duration/Distance** - Specify workout length
- **Save & Export** - Save to library or export to device

### Workout Structure

```
Workout
├── Warm-up (duration, target zone)
├── Main Set
│   ├── Interval 1 (work duration, rest duration, repeats)
│   ├── Interval 2
│   └── ...
├── Cool-down (duration, target zone)
└── Notes
```

## Goals Panel (`/[locale]/goals`)

Track training goals and progress:

### Goal Types

- **Performance Goals** - Target pace, power, or time for specific distances
- **Volume Goals** - Weekly/monthly distance or duration targets
- **Consistency Goals** - Workout frequency targets
- **Event Goals** - Race preparation with countdown

### Features

- **Progress Visualization** - Charts showing progress toward goals
- **Milestone Tracking** - Sub-goals and checkpoints
- **AI Recommendations** - Suggestions to stay on track
- **Historical Comparison** - Compare current progress to past goals

## Sync Panel (`/[locale]/sync`)

Data synchronization interface:

### Supported Sources

- **Garmin Connect** - Automatic sync of workouts and wellness data
- **Manual Upload** - Import FIT, GPX, or TCX files

### Sync Features

- **Last Sync Status** - Timestamp and result of last sync
- **Sync History** - Log of all sync operations
- **Manual Trigger** - Force sync button
- **Connection Status** - OAuth connection health

## Navigation Component

The `Navigation` component (`src/components/ui/Navigation.tsx`) provides:

- Responsive sidebar (collapsible on mobile)
- Active state highlighting based on current route
- Locale-aware links using `@/i18n/navigation`
- Language switcher integration

### Implementation Notes

```typescript
// Always use i18n-aware Link
import { Link, usePathname } from '@/i18n/navigation';

// usePathname returns path WITHOUT locale prefix
const pathname = usePathname(); // '/workouts' not '/en/workouts'

// Check active state
const isActive = pathname === '/workouts' || pathname.startsWith('/workouts/');
```

## Shared Components

### DataSourceBadge (`src/components/explain/DataSourceBadge.tsx`)

Displays the source of data with appropriate styling:

- Garmin (blue)
- WHOOP (orange)
- Manual (gray)
- AI-generated (purple)

### WorkoutCard (`src/components/workouts/WorkoutCard.tsx`)

Reusable card component for displaying workout summaries in lists.

## Responsive Design

All panels follow responsive design principles:

- **Desktop (>1024px)** - Full sidebar, multi-column layouts
- **Tablet (768-1024px)** - Collapsible sidebar, adapted grid
- **Mobile (<768px)** - Bottom navigation, single column, touch-optimized

## Styling

The application uses Tailwind CSS with a dark theme:

- Background: `bg-gray-950`
- Cards: `bg-gray-900`
- Text: `text-gray-100` (primary), `text-gray-400` (secondary)
- Accent: Various colors per workout type
