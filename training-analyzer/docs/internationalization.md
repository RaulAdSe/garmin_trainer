# Internationalization (i18n) Implementation

This document describes the internationalization setup for the Training Analyzer frontend, including the architecture, configuration, known issues, and solutions.

## Overview

The frontend uses **next-intl** (v4.6.1) with Next.js 16 App Router to provide multi-language support. Currently supported locales:

- **English (en)** - Default
- **Spanish (es)**

## Architecture

### File Structure

```
frontend/
├── middleware.ts                    # Handles locale detection and redirects
├── next.config.ts                   # Next.js config with i18n plugin and fallback redirects
├── src/
│   ├── app/
│   │   ├── layout.tsx               # Root layout (html/body tags)
│   │   ├── providers.tsx            # React Query and other providers
│   │   └── [locale]/                # All pages under dynamic locale segment
│   │       ├── layout.tsx           # Locale layout with NextIntlClientProvider
│   │       ├── page.tsx             # Dashboard
│   │       ├── workouts/
│   │       │   ├── page.tsx         # Workouts list
│   │       │   └── [id]/page.tsx    # Workout detail
│   │       ├── plans/
│   │       │   ├── page.tsx         # Training plans list
│   │       │   ├── new/page.tsx     # Create new plan
│   │       │   └── [id]/page.tsx    # Plan detail
│   │       ├── design/page.tsx      # Workout designer
│   │       ├── goals/page.tsx       # Goals management
│   │       └── sync/page.tsx        # Data sync page
│   ├── i18n/
│   │   ├── routing.ts               # Locale configuration
│   │   ├── navigation.ts            # i18n-aware navigation utilities
│   │   └── request.ts               # Server-side locale handling
│   └── messages/
│       ├── en.json                  # English translations
│       └── es.json                  # Spanish translations
```

### Key Configuration Files

#### 1. Routing Configuration (`src/i18n/routing.ts`)

```typescript
import { defineRouting } from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['en', 'es'],
  defaultLocale: 'en',
  localePrefix: 'always'  // All URLs require locale prefix
});

export type Locale = (typeof routing.locales)[number];
```

#### 2. Navigation Utilities (`src/i18n/navigation.ts`)

```typescript
import { createNavigation } from 'next-intl/navigation';
import { routing } from './routing';

export const { Link, redirect, usePathname, useRouter, getPathname } =
  createNavigation(routing);
```

**Important:** Always import `Link`, `useRouter`, and `usePathname` from `@/i18n/navigation` instead of `next/link` or `next/navigation` to ensure proper locale handling.

#### 3. Middleware (`middleware.ts`)

```typescript
import createMiddleware from 'next-intl/middleware';
import { defineRouting } from 'next-intl/routing';

const routing = defineRouting({
  locales: ['en', 'es'],
  defaultLocale: 'en',
  localePrefix: 'always'
});

export default createMiddleware(routing);

export const config = {
  matcher: ['/((?!api|_next|_vercel|.*\\..*).*)', '/']
};
```

#### 4. Next.js Config (`next.config.ts`)

```typescript
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig = {
  async rewrites() {
    return [
      { source: "/api/v1/:path*", destination: "http://localhost:8000/api/v1/:path*" }
    ];
  },
  // Fallback redirects for dev mode (see Known Issues)
  async redirects() {
    return [
      { source: '/', destination: '/en', permanent: false },
      { source: '/workouts', destination: '/en/workouts', permanent: false },
      // ... more routes
    ];
  }
};

export default withNextIntl(nextConfig);
```

## URL Structure

With `localePrefix: 'always'`, all routes require a locale prefix:

| User Visits | Redirects To | Renders |
|-------------|--------------|---------|
| `/` | `/en` | Dashboard |
| `/workouts` | `/en/workouts` | Workouts list |
| `/en/workouts` | - | Workouts list (English) |
| `/es/workouts` | - | Workouts list (Spanish) |

## Components

### Language Switcher (`src/components/ui/LanguageSwitcher.tsx`)

A dropdown component that allows users to switch between available locales. Uses `useRouter` and `usePathname` from `@/i18n/navigation` to preserve the current path while changing the locale.

### Navigation (`src/components/ui/Navigation.tsx`)

The main navigation component uses `Link` from `@/i18n/navigation` to ensure all navigation links are locale-aware.

## Translation Files

Translation files are stored in `src/messages/` as JSON:

```json
// en.json
{
  "navigation": {
    "dashboard": "Dashboard",
    "workouts": "Workouts",
    "plans": "Plans",
    "design": "Design",
    "goals": "Goals",
    "sync": "Sync"
  },
  "dashboard": {
    "title": "Training Dashboard",
    "subtitle": "Your personalized training insights"
  }
  // ... more translations
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

## Known Issues and Solutions

### Issue 1: Middleware Not Running in Dev Mode (SSG Pages)

**Problem:** Next.js 16 development mode with Turbopack/Webpack doesn't always execute middleware for statically generated pages. This causes 404 errors when visiting `/workouts` instead of redirecting to `/en/workouts`.

**Solution:** Added fallback redirects in `next.config.ts` that work in both dev and production modes. The middleware handles production, while redirects provide dev fallback.

**Production:** Middleware works correctly, providing:
- Locale detection from `Accept-Language` header
- Cookie-based locale persistence
- Proper 307 redirects

**Development:** Falls back to `next.config.ts` redirects.

### Issue 2: Path Aliases in Middleware

**Problem:** The `@/` path alias from `tsconfig.json` doesn't always resolve correctly in middleware files.

**Solution:** Inline the routing configuration directly in `middleware.ts` instead of importing from `@/i18n/routing`.

### Issue 3: Wrong Link/Router Imports

**Problem:** Using `next/link` or `next/navigation` instead of `@/i18n/navigation` causes navigation to non-locale-prefixed URLs.

**Solution:** Audit and fix all imports:
- `import Link from 'next/link'` → `import { Link } from '@/i18n/navigation'`
- `import { useRouter } from 'next/navigation'` → `import { useRouter } from '@/i18n/navigation'`
- `import { usePathname } from 'next/navigation'` → `import { usePathname } from '@/i18n/navigation'`

**Note:** `useParams`, `useSearchParams`, and `notFound` should still be imported from `next/navigation` as they are not part of next-intl's navigation exports.

### Issue 4: Root Layout HTML/Body Tags

**Problem:** Next.js requires `<html>` and `<body>` tags in the root layout, but having them in both root and locale layouts causes hydration errors.

**Solution:**
- `src/app/layout.tsx` (root): Contains `<html>` and `<body>` tags
- `src/app/[locale]/layout.tsx`: Only contains `NextIntlClientProvider` wrapper, no HTML/body tags

## Testing Checklist

After any i18n changes, verify:

```bash
# Root redirects to default locale
curl -I http://localhost:3000/
# Expected: 307 redirect to /en

# Non-prefixed routes redirect
curl -I http://localhost:3000/workouts
# Expected: 307 redirect to /en/workouts

# Locale-prefixed routes work
curl -I http://localhost:3000/en/workouts
# Expected: 200 OK

curl -I http://localhost:3000/es/workouts
# Expected: 200 OK

# API proxy still works
curl http://localhost:3000/api/v1/workouts/
# Expected: JSON response
```

## Adding a New Locale

1. Add locale to `src/i18n/routing.ts`:
   ```typescript
   locales: ['en', 'es', 'fr']  // Add 'fr'
   ```

2. Update middleware inline config if needed

3. Create translation file `src/messages/fr.json`

4. Add redirect fallback in `next.config.ts`:
   ```typescript
   { source: '/workouts', destination: '/fr/workouts', permanent: false }
   ```

## Adding a New Page

1. Create page in `src/app/[locale]/your-page/page.tsx`

2. Add translations to all locale files in `src/messages/`

3. Add navigation link using `Link` from `@/i18n/navigation`

4. Add redirect fallback in `next.config.ts`:
   ```typescript
   { source: '/your-page', destination: '/en/your-page', permanent: false }
   ```
