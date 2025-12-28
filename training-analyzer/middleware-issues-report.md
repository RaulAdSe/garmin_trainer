# Technical Report: Middleware and Routing Issues in Training-Analyzer Frontend

## Executive Summary

The training-analyzer frontend was migrated from standard Next.js routing to `next-intl` internationalized routing with locale prefixes (`/en/`, `/es/`). This migration introduced 404 errors on routes like `/workouts` due to mismatches between the middleware configuration, routing setup, and page structure.

---

## 1. Issues Discovered in middleware.ts

**File:** `frontend/middleware.ts`

### Current Implementation (Fixed State)

The current middleware is a custom implementation that handles locale detection and redirection:

```typescript
export default function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip internal Next.js paths and static files
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.includes('.') // files with extensions
  ) {
    return NextResponse.next();
  }

  // Check if the pathname already has a locale prefix
  const pathnameHasLocale = locales.some(
    (locale) => pathname.startsWith(`/${locale}/`) || pathname === `/${locale}`
  );

  if (pathnameHasLocale) {
    return NextResponse.next();
  }

  // No locale prefix found - redirect to default locale
  const url = request.nextUrl.clone();
  url.pathname = `/${defaultLocale}${pathname}`;
  return NextResponse.redirect(url, 307);
}
```

### Issues That Were Present (Historical)

1. **Conflicting Matcher Patterns**: The original middleware matcher included both old non-locale routes AND locale routes, causing conflicts where Next.js would match `/workouts` before the middleware could redirect to `/en/workouts`.

2. **Missing Integration with next-intl Middleware**: The middleware is a custom implementation rather than using `createMiddleware` from `next-intl`, which could cause subtle inconsistencies with the i18n system.

3. **Dev Mode SSG Limitation**: As noted in the code comment, middleware may not run in dev mode for SSG pages in Next.js 16+, requiring fallback redirects in `next.config.ts`.

---

## 2. Issues Found in routing.ts

**File:** `frontend/src/i18n/routing.ts`

### Current Configuration

```typescript
export const routing = defineRouting({
  locales: ['en', 'es'],
  defaultLocale: 'en',
  localePrefix: 'always'
});
```

### Analysis

The routing configuration itself is correct. The key setting is `localePrefix: 'always'`, which means:

- All routes MUST have a locale prefix
- `/` must redirect to `/en`
- `/workouts` must redirect to `/en/workouts`
- `/en/workouts` renders the page directly

**No direct issues in routing.ts**, but this configuration creates dependencies that were not properly handled elsewhere:

1. The middleware must redirect all non-locale-prefixed paths
2. All `Link` components must use the i18n-aware version from `@/i18n/navigation`
3. The `next.config.ts` must have fallback redirects

---

## 3. Issues in next.config.ts

**File:** `frontend/next.config.ts`

### Current Configuration

The configuration includes extensive redirect rules as a fallback mechanism:

```typescript
async redirects() {
  return [
    { source: '/', destination: '/en', permanent: false },
    { source: '/workouts', destination: '/en/workouts', permanent: false },
    { source: '/workouts/:path*', destination: '/en/workouts/:path*', permanent: false },
    // ... more routes
  ];
}
```

### Issues

1. **Redundant Redirects**: Both middleware and `next.config.ts` handle the same redirects. This is intentional as a fallback but creates maintenance overhead.

2. **Manual Route Enumeration**: Every new route must be manually added to the redirects list, which is error-prone.

3. **Plugin Integration**: The config uses `next-intl/plugin` correctly:
   ```typescript
   const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');
   export default withNextIntl(nextConfig);
   ```

---

## 4. Root Causes of /workouts Returning 404

### Primary Cause: Page Structure Migration

All pages were moved from the root `app/` directory to `app/[locale]/`:

| Old Location | New Location |
|--------------|--------------|
| `src/app/page.tsx` | `src/app/[locale]/page.tsx` |
| `src/app/workouts/page.tsx` | `src/app/[locale]/workouts/page.tsx` |
| `src/app/workouts/[id]/page.tsx` | `src/app/[locale]/workouts/[id]/page.tsx` |
| ... | ... |

When a user visits `/workouts`:
1. No page exists at `src/app/workouts/page.tsx` (deleted)
2. The actual page is at `src/app/[locale]/workouts/page.tsx`
3. Without proper middleware redirect, Next.js returns 404

### Secondary Causes

1. **Middleware Not Running in Dev Mode**: For SSG pages, middleware may be skipped in development, causing direct 404s without redirect attempts.

2. **Wrong Link Imports in Components**: If any page used `next/link` instead of `@/i18n/navigation`, clicking those links would navigate to `/workouts` instead of `/en/workouts`.

3. **Root Layout Conflict**: The root layout and `[locale]/layout.tsx` could conflict if both try to handle locale-specific rendering.

### Request Flow That Causes 404

```
1. User visits: http://localhost:3000/workouts
   |
2. If middleware doesn't run (SSG dev mode):
   |---> Next.js looks for: src/app/workouts/page.tsx
   |---> File doesn't exist
   |---> 404 Error

3. If middleware runs correctly:
   |---> Middleware detects no locale prefix
   |---> Redirects 307 to /en/workouts
   |---> Next.js routes to: src/app/[locale]/workouts/page.tsx
   |---> Page renders correctly
```

---

## 5. Fixes Applied / Recommended

### Fixes Already Applied

| Issue | File | Fix Applied |
|-------|------|-------------|
| Middleware locale detection | `middleware.ts` | Custom middleware with explicit redirect logic |
| Fallback redirects | `next.config.ts` | Added redirect rules for all routes |
| Navigation links | `Navigation.tsx` | Uses `@/i18n/navigation` Link component |
| i18n navigation exports | `src/i18n/navigation.ts` | Created with `createNavigation(routing)` |
| Root layout html/body tags | `src/app/layout.tsx` | Added html/body with suppressHydrationWarning |
| Locale layout simplified | `src/app/[locale]/layout.tsx` | Removed duplicate html/body, kept NextIntlClientProvider |

### Current File Structure (Correct)

```
frontend/
  middleware.ts                    # Handles locale detection/redirect
  src/
    app/
      layout.tsx                   # Root layout with html/body
      providers.tsx                # React providers
      [locale]/
        layout.tsx                 # Locale-specific layout with NextIntlClientProvider
        page.tsx                   # Dashboard
        workouts/
          page.tsx                 # Workouts list
          [id]/page.tsx           # Workout detail
        plans/
          page.tsx                 # Plans list
          new/page.tsx            # New plan
          [id]/page.tsx           # Plan detail
        sync/page.tsx             # Sync page
        design/page.tsx           # Design page
        goals/page.tsx            # Goals page
    i18n/
      routing.ts                   # Locale configuration
      navigation.ts                # i18n-aware Link, useRouter, usePathname
      request.ts                   # Server-side locale handling
    messages/
      en.json                      # English translations
      es.json                      # Spanish translations
```

### Remaining Recommendations

1. **Consider using next-intl's createMiddleware**: Replace the custom middleware with the official `createMiddleware` from `next-intl` for better integration.

2. **Remove redundant redirects from next.config.ts**: Once middleware is confirmed working in all scenarios, the fallback redirects can be removed to reduce maintenance overhead.

3. **Audit all Link imports**: Ensure no pages accidentally use `next/link` instead of `@/i18n/navigation`.

4. **Clear .next cache after changes**: Always delete `.next/` folder and restart after middleware changes.

---

## Testing Checklist

Verify the following after any changes:

- [ ] `curl -I http://localhost:3000/` returns 307 redirect to `/en`
- [ ] `curl -I http://localhost:3000/workouts` returns 307 redirect to `/en/workouts`
- [ ] `curl -I http://localhost:3000/en/workouts` returns 200 OK
- [ ] `curl -I http://localhost:3000/es/workouts` returns 200 OK
- [ ] Navigation links work without full page reload
- [ ] Active nav state highlights correctly
- [ ] Language switcher changes locale in URL

---

## Key Takeaways

1. **Locale prefix "always" requires all routes to have locale**: With `localePrefix: 'always'`, middleware must redirect every non-prefixed route.

2. **next-intl's usePathname strips locale**: When using `usePathname()` from `@/i18n/navigation`, the path `/en/workouts` returns `/workouts` (no locale prefix).

3. **Dual-layer redirect strategy**: Both middleware and `next.config.ts` redirects provide redundancy for SSG edge cases.

4. **Page migration is essential**: Old pages at `src/app/workouts/` must be deleted after migration to `src/app/[locale]/workouts/`.

5. **Root layout must have html/body**: Next.js requires the root layout to contain `<html>` and `<body>` tags - the `[locale]/layout.tsx` provides locale-specific providers only.
