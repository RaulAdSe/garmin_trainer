"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

export type DashboardViewMode = "focus" | "full";

const STORAGE_KEY = "trainer-dashboard-view-mode";

interface DashboardToggleProps {
  viewMode: DashboardViewMode;
  onViewModeChange: (mode: DashboardViewMode) => void;
  className?: string;
}

export function DashboardToggle({
  viewMode,
  onViewModeChange,
  className,
}: DashboardToggleProps) {
  const t = useTranslations("focusView");

  return (
    <div
      className={cn(
        "inline-flex items-center bg-gray-800 rounded-lg p-1 gap-1",
        className
      )}
      role="group"
      aria-label={t("viewModeLabel")}
    >
      <button
        type="button"
        onClick={() => onViewModeChange("focus")}
        className={cn(
          "px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200",
          viewMode === "focus"
            ? "bg-gray-700 text-white shadow-sm"
            : "text-gray-400 hover:text-gray-200 hover:bg-gray-700/50"
        )}
        aria-pressed={viewMode === "focus"}
      >
        <span className="flex items-center gap-1.5">
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          {t("focusMode")}
        </span>
      </button>
      <button
        type="button"
        onClick={() => onViewModeChange("full")}
        className={cn(
          "px-3 py-1.5 text-sm font-medium rounded-md transition-all duration-200",
          viewMode === "full"
            ? "bg-gray-700 text-white shadow-sm"
            : "text-gray-400 hover:text-gray-200 hover:bg-gray-700/50"
        )}
        aria-pressed={viewMode === "full"}
      >
        <span className="flex items-center gap-1.5">
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
            />
          </svg>
          {t("fullMode")}
        </span>
      </button>
    </div>
  );
}

// Custom hook to persist and retrieve dashboard view mode preference
export function useDashboardViewMode(): [
  DashboardViewMode,
  (mode: DashboardViewMode) => void,
  boolean
] {
  const [viewMode, setViewMode] = useState<DashboardViewMode>("focus");
  const [isLoaded, setIsLoaded] = useState(false);

  // Load saved preference from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "focus" || saved === "full") {
        setViewMode(saved);
      }
    } catch (error) {
      // localStorage might not be available (SSR, private mode, etc.)
      console.warn("Could not read dashboard view preference:", error);
    }
    setIsLoaded(true);
  }, []);

  // Save preference to localStorage when it changes
  const setViewModeAndPersist = (mode: DashboardViewMode) => {
    setViewMode(mode);
    try {
      localStorage.setItem(STORAGE_KEY, mode);
    } catch (error) {
      console.warn("Could not save dashboard view preference:", error);
    }
  };

  return [viewMode, setViewModeAndPersist, isLoaded];
}
