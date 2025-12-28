# Internationalization (i18n) Implementation

This document describes the internationalization setup for the Training Analyzer frontend.

## Overview

The frontend uses **next-intl** (v4.6.1) with Next.js 16 App Router. Currently supported locales:

- **English (en)** - Default
- **Spanish (es)**

## Architecture

### Single Source of Truth

All i18n configuration lives in `src/i18n/config.ts`:

```typescript
// src/i18n/config.ts
export const locales = ['en', 'es'] as const;
export const defaultLocale = 'en' as const;
export type Locale = (typeof locales)[number];

export const appRoutes = [
  '/workouts',
  '/workouts/:path*',
  '/plans',
  '/plans/:path*',
  '/design',
  '/goals',
  '/sync',
] as const;
```

All other files import from this config:

```
src/i18n/config.ts     ← Single source of truth
       ↓
  ┌────┴────────────┬─────────────────┐
  ↓                 ↓                 ↓
routing.ts    middleware.ts    next.config.ts
```

### File Structure

```
frontend/
├── middleware.ts              # Locale detection and redirects
├── next.config.ts             # Fallback redirects (imports from config)
├── src/
│   ├── i18n/
│   │   ├── config.ts          # ⭐ SINGLE SOURCE OF TRUTH
│   │   ├── routing.ts         # next-intl routing (imports from config)
│   │   ├── navigation.ts      # i18n-aware Link, useRouter, etc.
│   │   └── request.ts         # Server-side locale handling
│   ├── messages/
│   │   ├── en.json            # English translations
│   │   └── es.json            # Spanish translations
│   └── app/
│       ├── layout.tsx         # Root layout (minimal, passes children)
│       └── [locale]/          # All pages under dynamic locale segment
│           ├── layout.tsx     # Locale layout (<html lang={locale}>)
│           ├── not-found.tsx  # 404 page
│           ├── page.tsx       # Dashboard
│           ├── workouts/
│           ├── plans/
│           ├── design/
│           ├── goals/
│           └── sync/
```

## Adding a New Locale

**Edit only `src/i18n/config.ts`:**

```typescript
// Before
export const locales = ['en', 'es'] as const;

// After
export const locales = ['en', 'es', 'fr'] as const;
```

Then create the translation file:

```bash
cp src/messages/en.json src/messages/fr.json
# Edit fr.json with French translations
```

That's it. No other files need editing.

## Adding a New Route/Page

### Step 1: Add route to config

```typescript
// src/i18n/config.ts
export const appRoutes = [
  '/workouts',
  '/workouts/:path*',
  '/plans',
  '/plans/:path*',
  '/design',
  '/goals',
  '/sync',
  '/settings',        // ← Add new route
] as const;
```

### Step 2: Create the page

```bash
mkdir -p src/app/[locale]/settings
touch src/app/[locale]/settings/page.tsx
```

```typescript
// src/app/[locale]/settings/page.tsx
import { useTranslations } from 'next-intl';

export default function SettingsPage() {
  const t = useTranslations('settings');
  return <h1>{t('title')}</h1>;
}
```

### Step 3: Add translations

```json
// src/messages/en.json
{
  "settings": {
    "title": "Settings"
  }
}

// src/messages/es.json
{
  "settings": {
    "title": "Configuración"
  }
}
```

### Step 4: Add navigation (optional)

```typescript
import { Link } from '@/i18n/navigation';

<Link href="/settings">Settings</Link>
```

## URL Structure

With `localePrefix: 'always'`, all routes require a locale prefix:

| User Visits | Redirects To | Renders |
|-------------|--------------|---------|
| `/` | `/en` | Dashboard |
| `/workouts` | `/en/workouts` | Workouts list |
| `/en/workouts` | - | Workouts list (English) |
| `/es/workouts` | - | Workouts list (Spanish) |

## Navigation

**Always use i18n-aware navigation:**

```typescript
// ✅ Correct
import { Link, useRouter, usePathname } from '@/i18n/navigation';

// ❌ Wrong - will break locale handling
import Link from 'next/link';
import { useRouter } from 'next/navigation';
```

**Note:** `useParams`, `useSearchParams`, and `notFound` should still be imported from `next/navigation`.

## Translation Files

```json
// src/messages/en.json
{
  "navigation": {
    "dashboard": "Dashboard",
    "workouts": "Workouts"
  },
  "dashboard": {
    "title": "Training Dashboard"
  }
}
```

### Using Translations

```typescript
import { useTranslations } from 'next-intl';

function MyComponent() {
  const t = useTranslations('dashboard');
  return <h1>{t('title')}</h1>;
}
```

## Components

### Language Switcher

`src/components/ui/LanguageSwitcher.tsx` - Dropdown to switch locales while preserving current path.

### Navigation

`src/components/ui/Navigation.tsx` - Uses `Link` from `@/i18n/navigation` for locale-aware links.

## Technical Details

### Why config.ts exists

Edge Runtime (where middleware runs) doesn't reliably resolve TypeScript path aliases (`@/`). By using relative imports from a shared config file, we avoid duplication while maintaining compatibility.

### Middleware behavior

1. Skips API routes, static files, Next.js internals
2. Redirects non-locale paths → `/en/*` (307)
3. Lets next-intl handle locale detection for root path

### Fallback redirects

`next.config.ts` has fallback redirects for development mode where middleware may not run for SSG pages (Next.js 16 + Turbopack limitation).

## Testing

```bash
# Root redirects to default locale
curl -s -o /dev/null -w "%{http_code} %{redirect_url}" http://localhost:3000/
# Expected: 307 http://localhost:3000/en

# Non-prefixed routes redirect
curl -s -o /dev/null -w "%{http_code} %{redirect_url}" http://localhost:3000/workouts
# Expected: 307 http://localhost:3000/en/workouts

# Locale-prefixed routes work
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/en/workouts
# Expected: 200

curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/es/workouts
# Expected: 200

# HTML lang attribute is dynamic
curl -s http://localhost:3000/en | grep -o '<html[^>]*>'
# Expected: <html lang="en" ...>

curl -s http://localhost:3000/es | grep -o '<html[^>]*>'
# Expected: <html lang="es" ...>
```
