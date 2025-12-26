'use client';

import { useState, useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';

interface StreamingAnalysisProps {
  content: string;
  isStreaming: boolean;
  isComplete: boolean;
  error?: string | null;
  className?: string;
}

export function StreamingAnalysis({
  content,
  isStreaming,
  isComplete,
  error,
  className,
}: StreamingAnalysisProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [showCursor, setShowCursor] = useState(true);

  // Auto-scroll to bottom when content updates
  useEffect(() => {
    if (contentRef.current && isStreaming) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [content, isStreaming]);

  // Blinking cursor effect
  useEffect(() => {
    if (!isStreaming) {
      setShowCursor(false);
      return;
    }

    const interval = setInterval(() => {
      setShowCursor((prev) => !prev);
    }, 530);

    return () => clearInterval(interval);
  }, [isStreaming]);

  if (error) {
    return (
      <div className={cn('rounded-lg border border-red-200 bg-red-50 p-4', className)}>
        <div className="flex items-center gap-2 text-red-700">
          <ErrorIcon />
          <span className="font-medium">Analysis Error</span>
        </div>
        <p className="mt-2 text-sm text-red-600">{error}</p>
      </div>
    );
  }

  if (!content && !isStreaming) {
    return null;
  }

  return (
    <div
      className={cn(
        'rounded-lg border bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-100 overflow-hidden',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-100 bg-white/50">
        <div className="flex items-center gap-2">
          <SparklesIcon className="text-blue-500" />
          <span className="font-medium text-gray-900">AI Analysis</span>
        </div>
        {isStreaming && (
          <div className="flex items-center gap-2 text-sm text-blue-600">
            <LoadingDots />
            <span>Generating...</span>
          </div>
        )}
        {isComplete && (
          <div className="flex items-center gap-1 text-sm text-green-600">
            <CheckIcon />
            <span>Complete</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div
        ref={contentRef}
        className="p-4 max-h-96 overflow-y-auto"
      >
        <div className="prose prose-sm max-w-none">
          <StreamingContent content={content} showCursor={showCursor && isStreaming} />
        </div>
      </div>
    </div>
  );
}

// Streaming content with markdown-like rendering
interface StreamingContentProps {
  content: string;
  showCursor: boolean;
}

function StreamingContent({ content, showCursor }: StreamingContentProps) {
  // Parse the content and render with basic formatting
  const lines = content.split('\n');

  return (
    <div className="space-y-2">
      {lines.map((line, index) => {
        const isLast = index === lines.length - 1;

        // Empty line
        if (!line.trim()) {
          return <div key={index} className="h-2" />;
        }

        // Heading detection (## or ###)
        if (line.startsWith('### ')) {
          return (
            <h4 key={index} className="text-sm font-semibold text-gray-900 mt-4">
              {line.slice(4)}
              {isLast && showCursor && <Cursor />}
            </h4>
          );
        }

        if (line.startsWith('## ')) {
          return (
            <h3 key={index} className="text-base font-semibold text-gray-900 mt-4">
              {line.slice(3)}
              {isLast && showCursor && <Cursor />}
            </h3>
          );
        }

        // Bullet point
        if (line.startsWith('- ') || line.startsWith('* ')) {
          return (
            <div key={index} className="flex items-start gap-2 text-gray-700">
              <span className="text-blue-500 mt-1">-</span>
              <span>
                {line.slice(2)}
                {isLast && showCursor && <Cursor />}
              </span>
            </div>
          );
        }

        // Numbered list
        const numberedMatch = line.match(/^(\d+)\.\s(.+)$/);
        if (numberedMatch) {
          return (
            <div key={index} className="flex items-start gap-2 text-gray-700">
              <span className="text-blue-500 font-medium min-w-[1.5rem]">
                {numberedMatch[1]}.
              </span>
              <span>
                {numberedMatch[2]}
                {isLast && showCursor && <Cursor />}
              </span>
            </div>
          );
        }

        // Bold text detection
        const formattedLine = formatInlineStyles(line);

        // Regular paragraph
        return (
          <p key={index} className="text-gray-700">
            {formattedLine}
            {isLast && showCursor && <Cursor />}
          </p>
        );
      })}
    </div>
  );
}

// Format inline styles (bold, italic)
function formatInlineStyles(text: string): React.ReactNode {
  // Simple bold detection: **text**
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining) {
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);

    if (boldMatch && boldMatch.index !== undefined) {
      // Add text before the bold
      if (boldMatch.index > 0) {
        parts.push(remaining.slice(0, boldMatch.index));
      }
      // Add bold text
      parts.push(
        <strong key={key++} className="font-semibold">
          {boldMatch[1]}
        </strong>
      );
      remaining = remaining.slice(boldMatch.index + boldMatch[0].length);
    } else {
      // No more matches, add remaining text
      parts.push(remaining);
      break;
    }
  }

  return parts.length > 0 ? parts : text;
}

// Blinking cursor component
function Cursor() {
  return (
    <span className="inline-block w-2 h-4 ml-0.5 bg-blue-500 animate-pulse" />
  );
}

// Loading dots animation
function LoadingDots() {
  return (
    <div className="flex gap-1">
      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
    </div>
  );
}

// Skeleton loader for when starting
export function StreamingAnalysisSkeleton() {
  return (
    <div className="rounded-lg border bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-100 overflow-hidden animate-pulse">
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-100 bg-white/50">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 bg-blue-200 rounded" />
          <div className="w-24 h-4 bg-blue-200 rounded" />
        </div>
        <div className="flex items-center gap-2">
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 bg-blue-300 rounded-full" />
            <div className="w-1.5 h-1.5 bg-blue-300 rounded-full" />
            <div className="w-1.5 h-1.5 bg-blue-300 rounded-full" />
          </div>
          <div className="w-20 h-4 bg-blue-200 rounded" />
        </div>
      </div>
      <div className="p-4 space-y-3">
        <div className="h-4 bg-blue-200 rounded w-3/4" />
        <div className="h-4 bg-blue-200 rounded w-full" />
        <div className="h-4 bg-blue-200 rounded w-5/6" />
        <div className="h-4 bg-blue-200 rounded w-2/3" />
      </div>
    </div>
  );
}

// Icon components
function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg
      className={cn('w-5 h-5', className)}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

export default StreamingAnalysis;
