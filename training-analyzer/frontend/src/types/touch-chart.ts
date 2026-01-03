// Types for touch-friendly chart interactions

/**
 * Current state of touch interaction
 */
export interface TouchState {
  /** Whether user is currently touching the chart */
  isTouching: boolean;
  /** Starting X coordinate of touch */
  startX: number;
  /** Starting Y coordinate of touch */
  startY: number;
  /** Current X coordinate during touch move */
  currentX: number;
  /** Current Y coordinate during touch move */
  currentY: number;
  /** Number of active touch points (for pinch detection) */
  touchCount: number;
}

/**
 * State for a tooltip that has been pinned by tapping
 */
export interface PinnedTooltip {
  /** Index of the data point in the chart data array */
  dataIndex: number;
  /** X coordinate for tooltip positioning */
  x: number;
  /** Y coordinate for tooltip positioning */
  y: number;
}

/**
 * State for pinch-to-zoom gesture
 */
export interface PinchState {
  /** Whether pinch gesture is active */
  isPinching: boolean;
  /** Initial distance between two touch points */
  initialDistance: number;
  /** Current distance between two touch points */
  currentDistance: number;
  /** Center X of pinch gesture */
  centerX: number;
  /** Center Y of pinch gesture */
  centerY: number;
}

/**
 * Time range for chart zoom
 */
export interface TimeRange {
  /** Start timestamp in seconds */
  start: number;
  /** End timestamp in seconds */
  end: number;
}

/**
 * Configuration options for touch chart behavior
 */
export interface TouchChartConfig {
  /** Minimum swipe distance to trigger scrub (in pixels) */
  swipeThreshold?: number;
  /** Enable pinch-to-zoom */
  enablePinchZoom?: boolean;
  /** Enable tap-to-pin tooltip */
  enableTapToPin?: boolean;
  /** Enable swipe scrubbing */
  enableSwipeScrub?: boolean;
  /** Minimum zoom level (percentage of total range) */
  minZoom?: number;
  /** Maximum zoom level (percentage of total range) */
  maxZoom?: number;
  /** Debounce delay for touch move events (ms) */
  touchMoveDebounce?: number;
}

/**
 * Return type for the useTouchChart hook
 */
export interface UseTouchChartReturn {
  /** Current touch state */
  touchState: TouchState;
  /** Currently pinned tooltip (null if none) */
  pinnedTooltip: PinnedTooltip | null;
  /** Current pinch state */
  pinchState: PinchState;
  /** Current visible time range */
  timeRange: TimeRange | null;
  /** Whether this is the user's first interaction */
  showHint: boolean;
  /** Touch event handlers to attach to chart container */
  handlers: {
    onTouchStart: (e: React.TouchEvent) => void;
    onTouchMove: (e: React.TouchEvent) => void;
    onTouchEnd: (e: React.TouchEvent) => void;
    onTouchCancel: (e: React.TouchEvent) => void;
  };
  /** Pin a tooltip at specific data index */
  pinTooltip: (dataIndex: number, x: number, y: number) => void;
  /** Unpin the current tooltip */
  unpinTooltip: () => void;
  /** Reset zoom to full range */
  resetZoom: () => void;
  /** Dismiss the hint */
  dismissHint: () => void;
  /** Current data index being scrubbed to */
  scrubIndex: number | null;
  /** Set zoom level programmatically */
  setZoomRange: (range: TimeRange) => void;
  /** Current active index (from scrub or pinned tooltip) for syncing */
  activeIndex: number | null;
  /** Set active index externally (for synced charts) */
  setActiveIndex: (index: number | null) => void;
  /** Whether the chart is in synced mode */
  isSynced: boolean;
}

/**
 * Context for synchronizing multiple charts
 */
export interface ChartSyncContextValue {
  /** Current active index across all synced charts */
  activeIndex: number | null;
  /** Set the active index (called when any chart changes) */
  setActiveIndex: (index: number | null) => void;
  /** Current time range for synced zoom */
  timeRange: TimeRange | null;
  /** Set time range (called when any chart zooms) */
  setTimeRange: (range: TimeRange | null) => void;
  /** Register a chart for sync */
  registerChart: (id: string) => void;
  /** Unregister a chart */
  unregisterChart: (id: string) => void;
}

/**
 * Props for the TouchableChartWrapper component
 */
export interface TouchableChartWrapperProps {
  /** Child Recharts component(s) */
  children: React.ReactNode;
  /** Total data length for index calculations */
  dataLength: number;
  /** Full time range of the data */
  fullTimeRange: TimeRange;
  /** Callback when active index changes (for synced charts) */
  onActiveIndexChange?: (index: number | null) => void;
  /** Callback when time range changes (zoom) */
  onTimeRangeChange?: (range: TimeRange) => void;
  /** Configuration options */
  config?: TouchChartConfig;
  /** Additional class name */
  className?: string;
  /** Custom tooltip renderer for pinned tooltips */
  renderPinnedTooltip?: (dataIndex: number, position: { x: number; y: number }) => React.ReactNode;
  /** Whether to show the explore hint on first load */
  showExploreHint?: boolean;
  /** Storage key for hint dismissal persistence */
  hintStorageKey?: string;
}
