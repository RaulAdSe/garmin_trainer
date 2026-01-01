'use client';

import { useAuth } from '@/contexts/auth-context';
import { useRouter } from 'next/navigation';
import { useEffect, ReactNode } from 'react';

type SubscriptionTier = 'free' | 'pro' | 'enterprise';

interface ProtectedRouteProps {
  children: ReactNode;
  /**
   * Minimum subscription tier required to access this route.
   * If not specified, any authenticated user can access.
   */
  requiredTier?: SubscriptionTier;
  /**
   * Custom loading component to display while checking authentication.
   */
  loadingComponent?: ReactNode;
  /**
   * Custom upgrade prompt component for insufficient subscription tier.
   */
  upgradeComponent?: ReactNode;
}

const TIER_RANK: Record<SubscriptionTier, number> = {
  free: 0,
  pro: 1,
  enterprise: 2,
};

/**
 * Route guard component that protects routes requiring authentication.
 * Optionally enforces subscription tier requirements.
 *
 * Usage:
 * ```tsx
 * <ProtectedRoute>
 *   <DashboardPage />
 * </ProtectedRoute>
 *
 * <ProtectedRoute requiredTier="pro">
 *   <PremiumFeaturePage />
 * </ProtectedRoute>
 * ```
 */
export function ProtectedRoute({
  children,
  requiredTier,
  loadingComponent,
  upgradeComponent,
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  // Show loading state
  if (isLoading) {
    return loadingComponent ?? (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect if not authenticated (render nothing while redirecting)
  if (!isAuthenticated) {
    return null;
  }

  // Check subscription tier if required
  if (requiredTier && user) {
    const userTierRank = TIER_RANK[user.subscription_tier];
    const requiredTierRank = TIER_RANK[requiredTier];

    if (userTierRank < requiredTierRank) {
      return upgradeComponent ?? (
        <div className="flex items-center justify-center h-screen">
          <div className="text-center max-w-md p-6 bg-white rounded-lg shadow-lg">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Upgrade Required
            </h2>
            <p className="text-gray-600 mb-4">
              This feature requires a {requiredTier} subscription.
            </p>
            <p className="text-sm text-gray-500">
              Your current plan: <span className="font-medium">{user.subscription_tier}</span>
            </p>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
}

/**
 * Hook to check if the current user has access to a specific tier.
 */
export function useHasTierAccess(requiredTier: SubscriptionTier): boolean {
  const { user } = useAuth();

  if (!user) {
    return false;
  }

  const userTierRank = TIER_RANK[user.subscription_tier];
  const requiredTierRank = TIER_RANK[requiredTier];

  return userTierRank >= requiredTierRank;
}
