"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/contexts/auth-context";
import { OnboardingProvider } from "@/contexts/onboarding-context";
import { PreferencesProvider } from "@/contexts/preferences-context";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <PreferencesProvider>
          <OnboardingProvider>
            {children}
          </OnboardingProvider>
        </PreferencesProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
