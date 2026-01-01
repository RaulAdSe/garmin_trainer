import { useQuery } from "@tanstack/react-query";
import { getAthleteContext, getReadiness, getFitnessMetrics, getVO2MaxTrend } from "@/lib/api-client";
import type { AthleteContext, VO2MaxTrend } from "@/lib/types";

export function useAthleteContext(targetDate?: string) {
  return useQuery<AthleteContext>({
    queryKey: ["athleteContext", targetDate],
    queryFn: () => getAthleteContext(targetDate),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useReadiness(targetDate?: string) {
  return useQuery({
    queryKey: ["readiness", targetDate],
    queryFn: () => getReadiness(targetDate),
    staleTime: 5 * 60 * 1000,
  });
}

export function useFitnessMetrics(days: number = 30) {
  return useQuery({
    queryKey: ["fitnessMetrics", days],
    queryFn: () => getFitnessMetrics(days),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useVO2MaxTrend(days: number = 90) {
  return useQuery<VO2MaxTrend>({
    queryKey: ["vo2maxTrend", days],
    queryFn: () => getVO2MaxTrend(days),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}
