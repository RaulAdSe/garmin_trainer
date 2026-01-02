'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTouchChart } from '@/hooks/useTouchChart';
import type { TouchableChartWrapperProps, TimeRange } from '@/types/touch-chart';

/**
 * Wrapper component that adds touch-friendly interactions to Recharts components.
 * Supports tap-to-pin tooltips, swipe scrubbing, and pinch-to-zoom.
 */
export function TouchableChartWrapper({
  children,
  dataLength,
  fullTimeRange,
  onActiveIndexChange,
  onTimeRangeChange,
  config,
  className = '',
  renderPinnedTooltip,
  showExploreHint = true,
  hintStorageKey = 'workout-chart-hint-dismissed',
}: TouchableChartWrapperProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerRect, setContainerRect] = useState<DOMRect | null>(null);

  // Initialize touch hook
  const {
    touchState,
    pinnedTooltip,
    pinchState,
    timeRange,
    showHint,
    handlers,
    unpinTooltip,
    resetZoom,
    dismissHint,
    scrubIndex,
  } = useTouchChart(dataLength, fullTimeRange, config, hintStorageKey);

  // Update container rect on mount and resize
  useEffect(() => {
    const updateRect = () => {
      if (containerRef.current) {
        setContainerRect(containerRef.current.getBoundingClientRect());
      }
    };

    updateRect();

    const resizeObserver = new ResizeObserver(updateRect);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  // Notify parent of active index changes from scrubbing
  useEffect(() => {
    onActiveIndexChange?.(scrubIndex);
  }, [scrubIndex, onActiveIndexChange]);

  // Notify parent of pinned tooltip changes
  useEffect(() => {
    if (pinnedTooltip) {
      onActiveIndexChange?.(pinnedTooltip.dataIndex);
    }
  }, [pinnedTooltip, onActiveIndexChange]);

  // Notify parent of time range changes (zoom)
  useEffect(() => {
    onTimeRangeChange?.(timeRange || fullTimeRange);
  }, [timeRange, fullTimeRange, onTimeRangeChange]);

  // Handle click outside to unpin tooltip (for mouse users)
  const handleContainerClick = useCallback((e: React.MouseEvent) => {
    // Only unpin if clicking directly on container, not on chart elements
    if (e.target === containerRef.current && pinnedTooltip) {
      unpinTooltip();
    }
  }, [pinnedTooltip, unpinTooltip]);

  // Calculate tooltip position within bounds
  const tooltipPosition = useMemo(() => {
    if (!pinnedTooltip || !containerRect) return null;

    const padding = 8;
    const tooltipWidth = 120;
    const tooltipHeight = 60;

    let x = pinnedTooltip.x;
    let y = pinnedTooltip.y - tooltipHeight - padding;

    // Keep tooltip within bounds
    if (x + tooltipWidth / 2 > containerRect.width - padding) {
      x = containerRect.width - tooltipWidth / 2 - padding;
    }
    if (x - tooltipWidth / 2 < padding) {
      x = tooltipWidth / 2 + padding;
    }
    if (y < padding) {
      y = pinnedTooltip.y + padding + 20; // Show below if not enough room above
    }

    return { x, y };
  }, [pinnedTooltip, containerRect]);

  // Determine if we should show hint
  const shouldShowHint = showExploreHint && showHint && dataLength > 0;

  return (
    <div
      ref={containerRef}
      className={`relative touch-pan-y ${className}`}
      onClick={handleContainerClick}
      {...handlers}
      style={{
        // Prevent default touch behaviors that interfere with our gestures
        touchAction: pinchState.isPinching ? 'none' : 'pan-y',
      }}
    >
      {/* Chart content */}
      {children}

      {/* Touch hint overlay */}
      {shouldShowHint && (
        <TouchHint onDismiss={dismissHint} />
      )}

      {/* Pinned tooltip */}
      {pinnedTooltip && tooltipPosition && renderPinnedTooltip && (
        <div
          className="absolute pointer-events-none z-50 animate-in fade-in duration-150"
          style={{
            left: tooltipPosition.x,
            top: tooltipPosition.y,
            transform: 'translateX(-50%)',
          }}
        >
          {renderPinnedTooltip(pinnedTooltip.dataIndex, tooltipPosition)}
        </div>
      )}

      {/* Scrub indicator line */}
      {touchState.isTouching && scrubIndex !== null && containerRect && (
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-amber-400/80 pointer-events-none z-40"
          style={{
            left: (scrubIndex / (dataLength - 1)) * containerRect.width,
          }}
        />
      )}

      {/* Zoom reset button */}
      {timeRange && (
        <button
          onClick={resetZoom}
          className="absolute top-2 right-2 z-50 px-2 py-1 text-xs font-medium
                     bg-gray-800/90 hover:bg-gray-700 text-gray-300 rounded-md
                     border border-gray-600 transition-colors duration-200
                     flex items-center gap-1"
          aria-label="Reset zoom"
        >
          <svg
            className="w-3 h-3"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7"
            />
          </svg>
          Reset
        </button>
      )}

      {/* Pinch zoom indicator */}
      {pinchState.isPinching && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-40">
          <div className="bg-gray-900/80 text-gray-200 text-sm font-medium px-3 py-1.5 rounded-full">
            {timeRange ? (
              `${formatZoomLevel(timeRange, fullTimeRange)}x`
            ) : (
              'Pinch to zoom'
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Touch hint component shown on first load
 */
interface TouchHintProps {
  onDismiss: () => void;
}

function TouchHint({ onDismiss }: TouchHintProps) {
  // Auto-dismiss after 5 seconds
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <div
      className="absolute inset-0 flex items-center justify-center z-50 bg-gray-900/40
                 animate-in fade-in duration-300"
      onClick={onDismiss}
    >
      <div
        className="bg-gray-800/95 border border-gray-600 rounded-xl px-4 py-3
                   shadow-xl max-w-xs text-center space-y-2"
      >
        <div className="flex items-center justify-center gap-2 text-gray-200">
          <svg
            className="w-5 h-5 text-amber-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 11.5V14m0-2.5v-6a1.5 1.5 0 113 0m-3 6a1.5 1.5 0 00-3 0v2a7.5 7.5 0 0015 0v-5a1.5 1.5 0 00-3 0m-6-3V11m0-5.5v-1a1.5 1.5 0 013 0v1m0 0V11m0-5.5a1.5 1.5 0 013 0v3m0 0V11"
            />
          </svg>
          <span className="font-medium">Tap to explore</span>
        </div>
        <p className="text-xs text-gray-400">
          Tap to pin values, swipe to scrub timeline, pinch to zoom
        </p>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDismiss();
          }}
          className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          Got it
        </button>
      </div>
    </div>
  );
}

/**
 * Format zoom level as multiplier
 */
function formatZoomLevel(currentRange: TimeRange, fullRange: TimeRange): string {
  const currentDuration = currentRange.end - currentRange.start;
  const fullDuration = fullRange.end - fullRange.start;
  const zoomLevel = fullDuration / currentDuration;
  return zoomLevel.toFixed(1);
}

/**
 * Default pinned tooltip renderer
 * Can be used as a fallback or reference implementation
 */
export function DefaultPinnedTooltip({
  value,
  label,
  unit,
  color = 'text-teal-400',
}: {
  value: string | number;
  label: string;
  unit?: string;
  color?: string;
}) {
  return (
    <div className="bg-gray-800 border border-amber-500/50 rounded-lg px-3 py-2 shadow-xl">
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      <div className={`text-sm font-medium ${color}`}>
        {value}{unit}
      </div>
      <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 w-0 h-0
                      border-l-[6px] border-l-transparent
                      border-r-[6px] border-r-transparent
                      border-t-[6px] border-t-amber-500/50" />
    </div>
  );
}

export default TouchableChartWrapper;
