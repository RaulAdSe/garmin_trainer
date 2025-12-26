'use client';

import type { WorkoutAnalysis as WorkoutAnalysisType, Workout } from '@/lib/types';
import {
  cn,
  getEffortLevelColor,
  getEffortLevelLabel,
} from '@/lib/utils';

interface WorkoutAnalysisProps {
  analysis: WorkoutAnalysisType;
  workout?: Workout;
  className?: string;
}

export function WorkoutAnalysis({
  analysis,
  workout,
  className,
}: WorkoutAnalysisProps) {
  return (
    <div className={cn('space-y-6', className)}>
      {/* Summary Section */}
      <AnalysisSection title="Summary" icon={<SummaryIcon />}>
        <p className="text-gray-700 leading-relaxed">{analysis.summary}</p>

        {/* Effort Level Badge */}
        {analysis.effortLevel && (
          <div className="mt-3 flex items-center gap-2">
            <span className="text-sm text-gray-500">Effort Level:</span>
            <span
              className="px-2 py-0.5 text-sm font-medium rounded-full text-white"
              style={{ backgroundColor: getEffortLevelColor(analysis.effortLevel) }}
            >
              {getEffortLevelLabel(analysis.effortLevel)}
            </span>
          </div>
        )}
      </AnalysisSection>

      {/* What Went Well Section */}
      {analysis.whatWentWell && analysis.whatWentWell.length > 0 && (
        <AnalysisSection
          title="What Went Well"
          icon={<CheckIcon />}
          iconColor="text-green-500"
          bgColor="bg-green-50"
          borderColor="border-green-100"
        >
          <ul className="space-y-2">
            {analysis.whatWentWell.map((item, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="text-green-500 mt-1 flex-shrink-0">
                  <PlusIcon />
                </span>
                <span className="text-gray-700">{item}</span>
              </li>
            ))}
          </ul>
        </AnalysisSection>
      )}

      {/* Areas to Improve Section */}
      {analysis.improvements && analysis.improvements.length > 0 && (
        <AnalysisSection
          title="Areas to Improve"
          icon={<ImprovementIcon />}
          iconColor="text-amber-500"
          bgColor="bg-amber-50"
          borderColor="border-amber-100"
        >
          <ul className="space-y-2">
            {analysis.improvements.map((item, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="text-amber-500 mt-1 flex-shrink-0">
                  <AlertIcon />
                </span>
                <span className="text-gray-700">{item}</span>
              </li>
            ))}
          </ul>
        </AnalysisSection>
      )}

      {/* Training Context Section */}
      {analysis.trainingContext && (
        <AnalysisSection
          title="Training Context"
          icon={<ContextIcon />}
          iconColor="text-blue-500"
          bgColor="bg-blue-50"
          borderColor="border-blue-100"
        >
          <p className="text-gray-700 leading-relaxed">{analysis.trainingContext}</p>
        </AnalysisSection>
      )}

      {/* Recommendations Section */}
      {analysis.recommendations && analysis.recommendations.length > 0 && (
        <AnalysisSection
          title="Recommendations"
          icon={<RecommendationIcon />}
          iconColor="text-purple-500"
          bgColor="bg-purple-50"
          borderColor="border-purple-100"
        >
          <ul className="space-y-2">
            {analysis.recommendations.map((item, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="text-purple-500 mt-1 flex-shrink-0">
                  <ArrowRightIcon />
                </span>
                <span className="text-gray-700">{item}</span>
              </li>
            ))}
          </ul>
        </AnalysisSection>
      )}

      {/* Recovery Recommendation */}
      {analysis.recoveryRecommendation && (
        <AnalysisSection
          title="Recovery Recommendation"
          icon={<RecoveryIcon />}
          iconColor="text-teal-500"
          bgColor="bg-teal-50"
          borderColor="border-teal-100"
        >
          <p className="text-gray-700 leading-relaxed">{analysis.recoveryRecommendation}</p>
        </AnalysisSection>
      )}

      {/* Additional Sections */}
      {analysis.sections && analysis.sections.length > 0 && (
        <div className="space-y-4">
          {analysis.sections.map((section, index) => (
            <AnalysisSection key={index} title={section.title} icon={<SectionIcon />}>
              <p className="text-gray-700 leading-relaxed">{section.content}</p>
            </AnalysisSection>
          ))}
        </div>
      )}

      {/* Metadata */}
      <div className="flex items-center justify-between text-xs text-gray-400 pt-4 border-t border-gray-100">
        <span>
          Generated: {new Date(analysis.generatedAt).toLocaleString()}
        </span>
        {analysis.modelUsed && (
          <span>Model: {analysis.modelUsed}</span>
        )}
      </div>
    </div>
  );
}

// Analysis Section Component
interface AnalysisSectionProps {
  title: string;
  icon: React.ReactNode;
  iconColor?: string;
  bgColor?: string;
  borderColor?: string;
  children: React.ReactNode;
}

function AnalysisSection({
  title,
  icon,
  iconColor = 'text-gray-500',
  bgColor = 'bg-gray-50',
  borderColor = 'border-gray-100',
  children,
}: AnalysisSectionProps) {
  return (
    <div className={cn('rounded-lg border p-4', bgColor, borderColor)}>
      <h4 className="flex items-center gap-2 font-medium text-gray-900 mb-3">
        <span className={iconColor}>{icon}</span>
        {title}
      </h4>
      {children}
    </div>
  );
}

// Loading Skeleton
export function WorkoutAnalysisSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Summary skeleton */}
      <div className="bg-gray-50 rounded-lg border border-gray-100 p-4">
        <div className="h-5 bg-gray-200 rounded w-24 mb-3" />
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-5/6" />
          <div className="h-4 bg-gray-200 rounded w-4/6" />
        </div>
      </div>

      {/* What went well skeleton */}
      <div className="bg-gray-50 rounded-lg border border-gray-100 p-4">
        <div className="h-5 bg-gray-200 rounded w-32 mb-3" />
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-4/5" />
        </div>
      </div>

      {/* Improvements skeleton */}
      <div className="bg-gray-50 rounded-lg border border-gray-100 p-4">
        <div className="h-5 bg-gray-200 rounded w-36 mb-3" />
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-3/4" />
        </div>
      </div>
    </div>
  );
}

// Icon Components
function SummaryIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  );
}

function ImprovementIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
      />
    </svg>
  );
}

function AlertIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      />
    </svg>
  );
}

function ContextIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
      />
    </svg>
  );
}

function RecommendationIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
      />
    </svg>
  );
}

function ArrowRightIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
    </svg>
  );
}

function RecoveryIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
      />
    </svg>
  );
}

function SectionIcon() {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 6h16M4 12h16M4 18h7"
      />
    </svg>
  );
}

export default WorkoutAnalysis;
