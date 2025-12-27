'use client';

import { useState, useRef, useEffect } from 'react';
import { cn } from '@/lib/utils';

interface AnalysisSummaryProps {
  summary: string;
  keyTakeaways?: string[];
  whatNext?: string[];
  fullAnalysis?: string;
  className?: string;
  isStreaming?: boolean;
}

export function AnalysisSummary({
  summary,
  keyTakeaways = [],
  whatNext = [],
  fullAnalysis,
  className,
  isStreaming = false,
}: AnalysisSummaryProps) {
  const [showFullAnalysis, setShowFullAnalysis] = useState(false);
  const fullAnalysisRef = useRef<HTMLDivElement>(null);
  const [fullAnalysisHeight, setFullAnalysisHeight] = useState<number>(0);

  // Measure full analysis height for animation
  useEffect(() => {
    if (fullAnalysisRef.current) {
      setFullAnalysisHeight(fullAnalysisRef.current.scrollHeight);
    }
  }, [fullAnalysis]);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Main Summary - Always Visible */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-teal-900/50 flex items-center justify-center">
            <SummaryIcon className="w-4 h-4 text-teal-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium text-teal-400 mb-1">Summary</h3>
            <p className="text-gray-200 text-sm leading-relaxed">
              {summary}
              {isStreaming && <BlinkingCursor />}
            </p>
          </div>
        </div>
      </div>

      {/* Key Takeaways Section */}
      {keyTakeaways.length > 0 && (
        <div className="bg-gray-800/30 rounded-lg border border-gray-700/50 p-4">
          <h3 className="flex items-center gap-2 text-sm font-medium text-gray-100 mb-3">
            <CheckCircleIcon className="w-4 h-4 text-green-400" />
            Key Takeaways
          </h3>
          <ul className="space-y-2">
            {keyTakeaways.map((item, index) => (
              <TakeawayItem key={index} text={item} type="success" />
            ))}
          </ul>
        </div>
      )}

      {/* What's Next Section */}
      {whatNext.length > 0 && (
        <div className="bg-gray-800/30 rounded-lg border border-gray-700/50 p-4">
          <h3 className="flex items-center gap-2 text-sm font-medium text-gray-100 mb-3">
            <ArrowForwardIcon className="w-4 h-4 text-purple-400" />
            What&apos;s Next
          </h3>
          <ul className="space-y-2">
            {whatNext.map((item, index) => (
              <NextStepItem key={index} text={item} />
            ))}
          </ul>
        </div>
      )}

      {/* Full Analysis - Collapsible */}
      {fullAnalysis && (
        <div className="rounded-lg border border-gray-700/50 overflow-hidden">
          <button
            onClick={() => setShowFullAnalysis(!showFullAnalysis)}
            className={cn(
              'w-full flex items-center justify-between px-4 py-3',
              'bg-gray-800/20 hover:bg-gray-800/40 transition-colors duration-150'
            )}
          >
            <div className="flex items-center gap-2">
              <DocumentIcon className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-300">Full Analysis</span>
            </div>
            <ChevronIcon
              className={cn(
                'w-4 h-4 text-gray-400 transition-transform duration-200',
                showFullAnalysis && 'rotate-180'
              )}
            />
          </button>

          <div
            className="overflow-hidden transition-all duration-300 ease-out"
            style={{
              maxHeight: showFullAnalysis ? fullAnalysisHeight + 32 : 0,
              opacity: showFullAnalysis ? 1 : 0,
            }}
          >
            <div ref={fullAnalysisRef} className="p-4 border-t border-gray-700/50">
              <div className="prose prose-sm prose-invert max-w-none">
                <MarkdownContent content={fullAnalysis} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Takeaway item component
interface TakeawayItemProps {
  text: string;
  type: 'success' | 'warning';
}

function TakeawayItem({ text, type }: TakeawayItemProps) {
  return (
    <li className="flex items-start gap-2">
      {type === 'success' ? (
        <CheckIcon className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
      ) : (
        <WarningIcon className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
      )}
      <span className="text-gray-300 text-sm">{text}</span>
    </li>
  );
}

// Next step item component
interface NextStepItemProps {
  text: string;
}

function NextStepItem({ text }: NextStepItemProps) {
  return (
    <li className="flex items-start gap-2">
      <ArrowRightIcon className="w-4 h-4 text-purple-400 mt-0.5 flex-shrink-0" />
      <span className="text-gray-300 text-sm">{text}</span>
    </li>
  );
}

// Simple markdown content renderer
interface MarkdownContentProps {
  content: string;
}

function MarkdownContent({ content }: MarkdownContentProps) {
  const lines = content.split('\n');

  return (
    <div className="space-y-2">
      {lines.map((line, index) => {
        // Empty line
        if (!line.trim()) {
          return <div key={index} className="h-2" />;
        }

        // Heading detection
        if (line.startsWith('### ')) {
          return (
            <h4 key={index} className="text-sm font-semibold text-gray-100 mt-4">
              {line.slice(4)}
            </h4>
          );
        }

        if (line.startsWith('## ')) {
          return (
            <h3 key={index} className="text-base font-semibold text-gray-100 mt-4">
              {line.slice(3)}
            </h3>
          );
        }

        // Bullet point
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return (
            <div key={index} className="flex items-start gap-2 text-gray-300">
              <span className="text-teal-400 mt-1 flex-shrink-0">-</span>
              <span>{line.slice(2)}</span>
            </div>
          );
        }

        // Numbered list
        const numberedMatch = line.match(/^(\d+)\.\s(.+)$/);
        if (numberedMatch) {
          return (
            <div key={index} className="flex items-start gap-2 text-gray-300">
              <span className="text-teal-400 font-medium min-w-[1.5rem]">
                {numberedMatch[1]}.
              </span>
              <span>{numberedMatch[2]}</span>
            </div>
          );
        }

        // Regular paragraph
        return (
          <p key={index} className="text-gray-300 text-sm">
            {line}
          </p>
        );
      })}
    </div>
  );
}

// Blinking cursor for streaming
function BlinkingCursor() {
  return <span className="inline-block w-2 h-4 ml-0.5 bg-teal-400 animate-pulse" />;
}

// Score Card Component for displaying metrics
interface ScoreCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  color?: 'default' | 'success' | 'warning' | 'danger';
  icon?: React.ReactNode;
  tooltip?: string;
  className?: string;
}

export function ScoreCard({
  label,
  value,
  sublabel,
  color = 'default',
  icon,
  className,
}: ScoreCardProps) {
  const colorStyles = {
    default: 'border-gray-700 bg-gray-800/50',
    success: 'border-green-800/50 bg-green-900/20',
    warning: 'border-amber-800/50 bg-amber-900/20',
    danger: 'border-red-800/50 bg-red-900/20',
  };

  const valueColors = {
    default: 'text-gray-100',
    success: 'text-green-400',
    warning: 'text-amber-400',
    danger: 'text-red-400',
  };

  return (
    <div className={cn(
      'rounded-lg border p-3',
      colorStyles[color],
      className
    )}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
          <p className={cn('text-xl font-semibold mt-0.5', valueColors[color])}>
            {value}
          </p>
          {sublabel && (
            <p className="text-xs text-gray-500 mt-0.5">{sublabel}</p>
          )}
        </div>
        {icon && (
          <div className="flex-shrink-0">{icon}</div>
        )}
      </div>
    </div>
  );
}

// Score Cards Grid
interface ScoreCardsGridProps {
  children: React.ReactNode;
  className?: string;
}

export function ScoreCardsGrid({ children, className }: ScoreCardsGridProps) {
  return (
    <div className={cn(
      'grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3',
      className
    )}>
      {children}
    </div>
  );
}

// Icon components
function SummaryIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-5 h-5', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-5 h-5', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-4 h-4', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  );
}

function WarningIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-4 h-4', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  );
}

function ArrowForwardIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-5 h-5', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M13 7l5 5m0 0l-5 5m5-5H6"
      />
    </svg>
  );
}

function ArrowRightIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-4 h-4', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  );
}

function DocumentIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-4 h-4', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 6h16M4 12h16M4 18h7"
      />
    </svg>
  );
}

function ChevronIcon({ className }: { className?: string }) {
  return (
    <svg className={cn('w-4 h-4', className)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

export default AnalysisSummary;
