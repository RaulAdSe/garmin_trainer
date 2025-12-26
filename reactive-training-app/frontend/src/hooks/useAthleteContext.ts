import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { AthleteContext } from "@/lib/types";

export function useAthleteContext(targetDate?: string) {
  return useQuery<AthleteContext>({
    queryKey: ["athleteContext", targetDate],
    queryFn: () => apiClient.getAthleteContext(targetDate),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useReadiness(targetDate?: string) {
  return useQuery({
    queryKey: ["readiness", targetDate],
    queryFn: () => apiClient.getReadiness(targetDate),
    staleTime: 5 * 60 * 1000,
  });
}

export function useFitnessMetrics(days: number = 30) {
  return useQuery({
    queryKey: ["fitnessMetrics", days],
    queryFn: () => apiClient.getFitnessMetrics(days),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}
