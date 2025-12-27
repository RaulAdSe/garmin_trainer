'use client';

import { useState, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { InsightCard, type CategorizedInsight, type InsightCategory } from './InsightCard';

interface InsightsListProps {
  insights: CategorizedInsight[];
  className?: string;
  groupByCategory?: boolean;
  initialVisibleCount?: number;
  showCategoryHeaders?: boolean;
}

// Category order for display
const categoryOrder: InsightCategory[] = [
  'achievement',
  'performance',
  'caution',
  'trend',
  'recommendation',
];

// Category display configuration
const categoryConfig: Record<InsightCategory, {
  label: string;
  icon: string;
  headerBgColor: string;
  headerTextColor: string;
}> = {
  performance: {
    label: 'Performance',
    icon: '\u{1F4AA}', // flexed biceps
    headerBgColor: 'bg-blue-900/30',
    headerTextColor: 'text-blue-400',
  },
  caution: {
    label: 'Areas to Watch',
    icon: '\u{26A0}\u{FE0F}', // warning
    headerBgColor: 'bg-amber-900/30',
    headerTextColor: 'text-amber-400',
  },
  trend: {
    label: 'Trends',
    icon: '\u{1F4C8}', // chart
    headerBgColor: 'bg-purple-900/30',
    headerTextColor: 'text-purple-400',
  },
  recommendation: {
    label: 'Recommendations',
    icon: '\u{1F4A1}', // lightbulb
    headerBgColor: 'bg-green-900/30',
    headerTextColor: 'text-green-400',
  },
  achievement: {
    label: 'Achievements',
    icon: '\u{1F525}', // fire
    headerBgColor: 'bg-orange-900/30',
    headerTextColor: 'text-orange-400',
  },
};

export function InsightsList({
  insights,
  className,
  groupByCategory = true,
  initialVisibleCount = 5,
  showCategoryHeaders = true,
}: InsightsListProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<InsightCategory>>(
    new Set(categoryOrder)
  );
  const [showAll, setShowAll] = useState(false);

  // Group insights by category
  const groupedInsights = useMemo(() => {
    if (!groupByCategory) {
      return null;
    }

    const groups = new Map<InsightCategory, CategorizedInsight[]>();

    // Initialize empty groups
    categoryOrder.forEach((category) => {
      groups.set(category, []);
    });

    // Populate groups
    insights.forEach((insight) => {
      const group = groups.get(insight.category);
      if (group) {
        group.push(insight);
      }
    });

    // Filter out empty groups
    return Array.from(groups.entries()).filter(([, items]) => items.length > 0);
  }, [insights, groupByCategory]);

  // Flat list for non-grouped view
  const sortedInsights = useMemo(() => {
    if (groupByCategory) {
      return null;
    }

    // Sort by importance then by category order
    return [...insights].sort((a, b) => {
      const importanceOrder = { high: 0, medium: 1, low: 2 };
      const importanceDiff = importanceOrder[a.importance] - importanceOrder[b.importance];
      if (importanceDiff !== 0) return importanceDiff;

      return categoryOrder.indexOf(a.category) - categoryOrder.indexOf(b.category);
    });
  }, [insights, groupByCategory]);

  const toggleCategory = (category: InsightCategory) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  if (!insights || insights.length === 0) {
    return null;
  }

  // Render grouped view
  if (groupByCategory && groupedInsights) {
    return (
      <div className={cn('space-y-4', className)}>
        {groupedInsights.map(([category, categoryInsights]) => {
          const config = categoryConfig[category];
          const isExpanded = expandedCategories.has(category);

          return (
            <div key={category} className="rounded-lg overflow-hidden">
              {/* Category header */}
              {showCategoryHeaders && (
                <button
                  onClick={() => toggleCategory(category)}
                  className={cn(
                    'w-full flex items-center justify-between px-4 py-2.5',
                    'transition-colors duration-150',
                    config.headerBgColor,
                    'hover:opacity-90'
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-base">{config.icon}</span>
                    <span className={cn('font-medium text-sm', config.headerTextColor)}>
                      {config.label}
                    </span>
                    <span className="text-xs text-gray-500 bg-gray-800/50 px-2 py-0.5 rounded-full">
                      {categoryInsights.length}
                    </span>
                  </div>
                  <ChevronIcon
                    className={cn(
                      'w-4 h-4 transition-transform duration-200',
                      config.headerTextColor,
                      !isExpanded && '-rotate-90'
                    )}
                  />
                </button>
              )}

              {/* Category insights */}
              <div
                className={cn(
                  'transition-all duration-200 ease-out overflow-hidden',
                  !isExpanded && 'max-h-0'
                )}
                style={{
                  maxHeight: isExpanded ? categoryInsights.length * 200 + 100 : 0,
                }}
              >
                <div className="space-y-2 p-2">
                  {categoryInsights.map((insight) => (
                    <InsightCard key={insight.id} insight={insight} />
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  // Render flat list view
  if (sortedInsights) {
    const visibleInsights = showAll
      ? sortedInsights
      : sortedInsights.slice(0, initialVisibleCount);
    const hasMore = sortedInsights.length > initialVisibleCount;

    return (
      <div className={cn('space-y-2', className)}>
        {visibleInsights.map((insight) => (
          <InsightCard key={insight.id} insight={insight} />
        ))}

        {/* Show more button */}
        {hasMore && !showAll && (
          <button
            onClick={() => setShowAll(true)}
            className={cn(
              'w-full py-2 text-sm text-gray-400 hover:text-gray-300',
              'border border-dashed border-gray-700 rounded-lg',
              'transition-colors duration-150 hover:bg-gray-800/50'
            )}
          >
            Show {sortedInsights.length - initialVisibleCount} more insights
          </button>
        )}

        {/* Show less button */}
        {hasMore && showAll && (
          <button
            onClick={() => setShowAll(false)}
            className={cn(
              'w-full py-2 text-sm text-gray-400 hover:text-gray-300',
              'border border-dashed border-gray-700 rounded-lg',
              'transition-colors duration-150 hover:bg-gray-800/50'
            )}
          >
            Show less
          </button>
        )}
      </div>
    );
  }

  return null;
}

// Compact insights summary badge
interface InsightsSummaryProps {
  insights: CategorizedInsight[];
  className?: string;
}

export function InsightsSummary({ insights, className }: InsightsSummaryProps) {
  const counts = useMemo(() => {
    const result: Partial<Record<InsightCategory, number>> = {};
    insights.forEach((insight) => {
      result[insight.category] = (result[insight.category] || 0) + 1;
    });
    return result;
  }, [insights]);

  if (insights.length === 0) {
    return null;
  }

  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {categoryOrder
        .filter((category) => counts[category])
        .map((category) => {
          const config = categoryConfig[category];
          return (
            <div
              key={category}
              className={cn(
                'inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs',
                config.headerBgColor,
                config.headerTextColor
              )}
            >
              <span>{config.icon}</span>
              <span>{counts[category]}</span>
            </div>
          );
        })}
    </div>
  );
}

// Icon components
function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-4 h-4', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

export default InsightsList;
