'use client';

import { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';

// Insight categories with their styling
export type InsightCategory = 'performance' | 'caution' | 'trend' | 'recommendation' | 'achievement';

export interface CategorizedInsight {
  id: string;
  category: InsightCategory;
  icon: string;
  text: string;
  detail?: string;
  importance: 'high' | 'medium' | 'low';
}

interface InsightCardProps {
  insight: CategorizedInsight;
  className?: string;
  defaultExpanded?: boolean;
}

// Category styling configuration
const categoryStyles: Record<InsightCategory, {
  bgColor: string;
  borderColor: string;
  iconBgColor: string;
  textColor: string;
  accentColor: string;
}> = {
  performance: {
    bgColor: 'bg-blue-900/20',
    borderColor: 'border-blue-800/50',
    iconBgColor: 'bg-blue-900/50',
    textColor: 'text-blue-300',
    accentColor: 'text-blue-400',
  },
  caution: {
    bgColor: 'bg-amber-900/20',
    borderColor: 'border-amber-800/50',
    iconBgColor: 'bg-amber-900/50',
    textColor: 'text-amber-300',
    accentColor: 'text-amber-400',
  },
  trend: {
    bgColor: 'bg-purple-900/20',
    borderColor: 'border-purple-800/50',
    iconBgColor: 'bg-purple-900/50',
    textColor: 'text-purple-300',
    accentColor: 'text-purple-400',
  },
  recommendation: {
    bgColor: 'bg-green-900/20',
    borderColor: 'border-green-800/50',
    iconBgColor: 'bg-green-900/50',
    textColor: 'text-green-300',
    accentColor: 'text-green-400',
  },
  achievement: {
    bgColor: 'bg-orange-900/20',
    borderColor: 'border-orange-800/50',
    iconBgColor: 'bg-orange-900/50',
    textColor: 'text-orange-300',
    accentColor: 'text-orange-400',
  },
};

const categoryLabels: Record<InsightCategory, string> = {
  performance: 'Performance',
  caution: 'Caution',
  trend: 'Trend',
  recommendation: 'Recommendation',
  achievement: 'Achievement',
};

export function InsightCard({ insight, className, defaultExpanded = false }: InsightCardProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState<number>(0);

  const styles = categoryStyles[insight.category];
  const hasDetail = !!insight.detail;

  // Measure content height for smooth animation
  useEffect(() => {
    if (contentRef.current) {
      setContentHeight(contentRef.current.scrollHeight);
    }
  }, [insight.detail]);

  const handleToggle = () => {
    if (hasDetail) {
      setIsExpanded(!isExpanded);
    }
  };

  return (
    <div
      className={cn(
        'rounded-lg border transition-all duration-200',
        styles.bgColor,
        styles.borderColor,
        hasDetail && 'cursor-pointer hover:border-opacity-80',
        className
      )}
    >
      {/* Header - always visible */}
      <div
        className="flex items-start gap-3 p-3"
        onClick={handleToggle}
        role={hasDetail ? 'button' : undefined}
        aria-expanded={hasDetail ? isExpanded : undefined}
        tabIndex={hasDetail ? 0 : undefined}
        onKeyDown={(e) => {
          if (hasDetail && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            handleToggle();
          }
        }}
      >
        {/* Icon */}
        <div className={cn(
          'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-lg',
          styles.iconBgColor
        )}>
          {insight.icon}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Category label */}
          <span className={cn('text-xs font-medium uppercase tracking-wide', styles.accentColor)}>
            {categoryLabels[insight.category]}
          </span>

          {/* Main text */}
          <p className="text-gray-200 text-sm mt-0.5 leading-relaxed">
            {insight.text}
          </p>
        </div>

        {/* Expand indicator */}
        {hasDetail && (
          <div className={cn(
            'flex-shrink-0 w-6 h-6 flex items-center justify-center transition-transform duration-200',
            isExpanded && 'rotate-180'
          )}>
            <ChevronIcon className={styles.accentColor} />
          </div>
        )}
      </div>

      {/* Expandable detail section */}
      {hasDetail && (
        <div
          className="overflow-hidden transition-all duration-200 ease-out"
          style={{
            maxHeight: isExpanded ? contentHeight : 0,
            opacity: isExpanded ? 1 : 0,
          }}
        >
          <div
            ref={contentRef}
            className="px-3 pb-3 pt-0"
          >
            <div className="pl-11 border-l-2 border-gray-700/50 ml-4">
              <p className="text-gray-400 text-sm leading-relaxed pl-3">
                {insight.detail}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Compact variant for inline use
interface InsightBadgeProps {
  category: InsightCategory;
  icon: string;
  text: string;
  className?: string;
}

export function InsightBadge({ category, icon, text, className }: InsightBadgeProps) {
  const styles = categoryStyles[category];

  return (
    <div className={cn(
      'inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm',
      styles.bgColor,
      styles.textColor,
      className
    )}>
      <span>{icon}</span>
      <span>{text}</span>
    </div>
  );
}

// Helper function to parse insights from analysis text
export function parseInsightsFromAnalysis(
  whatWentWell: string[] = [],
  improvements: string[] = [],
  recommendations: string[] = []
): CategorizedInsight[] {
  const insights: CategorizedInsight[] = [];
  let id = 0;

  // What went well -> achievements/performance
  whatWentWell.forEach((item) => {
    insights.push({
      id: `insight-${id++}`,
      category: item.toLowerCase().includes('personal best') ||
                item.toLowerCase().includes('pr') ||
                item.toLowerCase().includes('record')
        ? 'achievement'
        : 'performance',
      icon: item.toLowerCase().includes('personal best') ||
            item.toLowerCase().includes('pr') ||
            item.toLowerCase().includes('record')
        ? '\u{1F525}' // fire emoji
        : '\u{1F4AA}', // flexed biceps emoji
      text: item,
      importance: 'medium',
    });
  });

  // Improvements -> caution
  improvements.forEach((item) => {
    insights.push({
      id: `insight-${id++}`,
      category: 'caution',
      icon: '\u{26A0}\u{FE0F}', // warning emoji
      text: item,
      importance: 'medium',
    });
  });

  // Recommendations
  recommendations.forEach((item) => {
    insights.push({
      id: `insight-${id++}`,
      category: 'recommendation',
      icon: '\u{1F4A1}', // lightbulb emoji
      text: item,
      importance: 'medium',
    });
  });

  return insights;
}

// Icon components
function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-4 h-4', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

export default InsightCard;
