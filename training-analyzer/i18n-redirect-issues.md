# i18n Redirect & 404 Issues Analysis

## Executive Summary

The training-analyzer frontend was migrated from standard Next.js routing to `next-intl` internationalized routing with locale prefixes (`/en/`, `/es/`). This migration introduced 404 errors due to mismatches between the routing configuration, middleware, and component navigation.

---

## Root Causes Identified

### 1. Middleware Matcher Configuration (CRITICAL)

**File:** `frontend/middleware.ts`

**Problem:** The original middleware matcher included both old non-locale routes AND locale routes, causing conflicts:

```typescript
// BROKEN - Conflicting patterns
export const config = {
  matcher: [
    '/',
    '/workouts',           // Old non-locale routes
    '/workouts/:path*',
    '/plans',
    '/plans/:path*',
    // ...more non-locale routes
    '/(en|es)',            // New locale routes
    '/(en|es)/:path*'
  ]
};
```

**Why it breaks:**
- Next.js matches `/workouts` before the middleware can redirect to `/en/workouts`
- The route `/workouts` no longer exists (pages moved to `[locale]/workouts/`)
- Results in 404 instead of redirect

**Solution:** Simplified matcher + explicit redirect logic:

```typescript
export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)']
};

export default function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip API routes and static files
  if (pathname.startsWith('/api') || pathname.startsWith('/_next') || pathname.includes('.')) {
    return NextResponse.next();
  }

  // Check if pathname already has a locale
  const hasLocale = routing.locales.some(
    locale => pathname === `/${locale}` || pathname.startsWith(`/${locale}/`)
  );

  // If no locale, redirect to default locale
  if (!hasLocale && pathname !== '/') {
    const url = request.nextUrl.clone();
    url.pathname = `/${routing.defaultLocale}${pathname}`;
    return NextResponse.redirect(url);
  }

  return intlMiddleware(request);
}
```

---

### 2. Root Layout Structure

**Files:**
- `frontend/src/app/layout.tsx`
- `frontend/src/app/[locale]/layout.tsx`

**Problem:** Original root layout called `getLocale()` causing async context conflicts with `[locale]/layout.tsx`.

**Current Solution (Applied by Linter):**

Root layout owns `<html>`/`<body>` with static lang:

```typescript
// src/app/layout.tsx - Owns html/body structure
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="bg-gray-950 text-gray-100 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
```

Locale layout provides i18n context without html/body:

```typescript
// src/app/[locale]/layout.tsx - Provides i18n context
export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;
  const messages = await getMessages();

  return (
    <NextIntlClientProvider messages={messages} locale={locale}>
      <Providers>
        <div className="flex min-h-screen flex-col md:flex-row">
          <Navigation />
          <main>{children}</main>
        </div>
      </Providers>
    </NextIntlClientProvider>
  );
}
```

**Trade-off:** The `<html lang="en">` is hardcoded. For full accessibility compliance, you may want to dynamically update this via client-side effect or use the alternative approach where `[locale]/layout.tsx` owns html/body.

---

### 3. Wrong Link Imports in Pages

**Files affected:**
- `src/app/[locale]/plans/page.tsx`
- `src/app/[locale]/plans/new/page.tsx`
- `src/app/[locale]/plans/[id]/page.tsx`
- `src/app/[locale]/workouts/[id]/page.tsx`

**Problem:** Pages use `next/link` instead of i18n-aware Link:

```typescript
// BROKEN - Regular Next.js Link
import Link from 'next/link';

<Link href="/plans/new">Create Plan</Link>  // Goes to /plans/new (404!)
```

**Why it breaks:**
- `next/link` doesn't add locale prefix
- Navigates to `/plans/new` instead of `/en/plans/new`
- Route doesn't exist, 404 error

**Solution:** Use i18n navigation exports:

```typescript
// FIXED - i18n-aware Link
import { Link } from '@/i18n/navigation';

<Link href="/plans/new">Create Plan</Link>  // Goes to /en/plans/new
```

Same applies to `useRouter`:

```typescript
// BROKEN
import { useRouter } from 'next/navigation';

// FIXED
import { useRouter } from '@/i18n/navigation';
```

---

### 4. Navigation Active State Logic

**File:** `frontend/src/components/ui/Navigation.tsx`

**Status:** Actually NOT broken (but easy to misdiagnose)

The `usePathname` from `@/i18n/navigation` returns paths **without** the locale prefix:
- User at `/en/workouts` → `usePathname()` returns `/workouts`
- This matches the hardcoded href values correctly

```typescript
// This works correctly because next-intl's usePathname strips locale
const isActive = (href: string) => {
  if (href === '/') return pathname === '/';
  return pathname.startsWith(href);
};
```

---

## Routing Configuration

**File:** `frontend/src/i18n/routing.ts`

```typescript
export const routing = defineRouting({
  locales: ['en', 'es'],
  defaultLocale: 'en',
  localePrefix: 'always'  // All routes MUST have locale prefix
});
```

With `localePrefix: 'always'`:
- `/` → redirects to `/en`
- `/workouts` → should redirect to `/en/workouts`
- `/en/workouts` → renders page

---

## File Structure Changes

### Deleted (moved to `[locale]/`):
```
src/app/page.tsx                    → src/app/[locale]/page.tsx
src/app/workouts/page.tsx           → src/app/[locale]/workouts/page.tsx
src/app/workouts/[id]/page.tsx      → src/app/[locale]/workouts/[id]/page.tsx
src/app/plans/page.tsx              → src/app/[locale]/plans/page.tsx
src/app/plans/new/page.tsx          → src/app/[locale]/plans/new/page.tsx
src/app/plans/[id]/page.tsx         → src/app/[locale]/plans/[id]/page.tsx
src/app/sync/page.tsx               → src/app/[locale]/sync/page.tsx
src/app/design/page.tsx             → src/app/[locale]/design/page.tsx
src/app/goals/page.tsx              → src/app/[locale]/goals/page.tsx
```

### New i18n files:
```
frontend/middleware.ts              # Handles locale detection/redirect
frontend/src/i18n/routing.ts        # Locale configuration
frontend/src/i18n/navigation.ts     # i18n-aware Link, useRouter, usePathname
frontend/src/i18n/request.ts        # Server-side locale handling
frontend/src/messages/en.json       # English translations
frontend/src/messages/es.json       # Spanish translations
```

---

## Request Flow (After Fixes)

```
1. User visits: http://localhost:3000/workouts
   ↓
2. Middleware matches path (not static, not API)
   ↓
3. Middleware checks: has locale prefix? NO
   ↓
4. Middleware redirects: 307 → /en/workouts
   ↓
5. Browser follows redirect to /en/workouts
   ↓
6. Middleware matches: has locale? YES (en)
   ↓
7. next-intl middleware processes request
   ↓
8. Routes to: src/app/[locale]/workouts/page.tsx
   ↓
9. Page renders with locale context
```

---

## Summary of Fixes Applied

| Issue | File | Fix Applied | Status |
|-------|------|-------------|--------|
| Middleware matcher conflicts | `middleware.ts` | Inline routing config + explicit redirect logic for non-locale paths | FIXED |
| Dev mode SSG limitation | `next.config.ts` | Added fallback redirects for dev mode (middleware may not run for SSG) | FIXED |
| Root layout conflict | `src/app/layout.tsx` | Static html/body with `suppressHydrationWarning` | Already Fixed |
| Locale layout structure | `src/app/[locale]/layout.tsx` | Provider wrapper only (no html/body) | Already Fixed |
| Wrong Link import | `plans/page.tsx` | Uses `@/i18n/navigation` | Already Fixed |
| Wrong Link import | `plans/new/page.tsx` | Uses `@/i18n/navigation` | Already Fixed |
| Wrong Link/Router import | `plans/[id]/page.tsx` | Uses `@/i18n/navigation` | Already Fixed |
| Wrong Link import | `workouts/[id]/page.tsx` | Uses `@/i18n/navigation` | Already Fixed |
| Navigation component | `Navigation.tsx` | Uses `@/i18n/navigation` | Already Fixed |
| Language switcher | `LanguageSwitcher.tsx` | Uses `@/i18n/navigation` | Already Fixed |

---

## Key Implementation Notes

### 1. Middleware Edge Runtime Limitation

Path aliases like `@/` don't work reliably in Edge Runtime middleware. The routing configuration is defined inline in `middleware.ts` and must be kept in sync with `src/i18n/routing.ts` manually.

### 2. Dev Mode SSG Limitation

In Next.js 16+ with Turbopack, middleware may not run for statically generated pages in development. Fallback redirects in `next.config.ts` handle these edge cases.

---

## Testing Checklist

After applying fixes, verify:

- [x] `curl http://localhost:3000/` -> 307 redirect to `/en`
- [x] `curl http://localhost:3000/workouts` -> 307 redirect to `/en/workouts`
- [x] `curl http://localhost:3000/en/workouts` -> 200 OK
- [x] `curl http://localhost:3000/es/workouts` -> 200 OK
- [x] Navigation links work without full page reload
- [x] Active nav state highlights correctly
- [x] Language switcher changes locale in URL
- [x] Build succeeds with `npm run build`

---

## Common Pitfalls

1. **Don't mix `next/link` and `@/i18n/navigation` Link** - Always use i18n Link in `[locale]/` pages

2. **Middleware caching** - After middleware changes, delete `.next/` folder and restart

3. **Matcher order matters** - More specific patterns should come first

4. **next-intl's usePathname strips locale** - `/en/workouts` returns `/workouts`

5. **Root layout must be minimal** - Let `[locale]/layout.tsx` handle locale-specific setup

6. **Edge Runtime path aliases** - Don't use `@/` imports in middleware.ts - define routing inline

7. **Keep routing in sync** - If you add a locale, update both `middleware.ts` AND `src/i18n/routing.ts`
