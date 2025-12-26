'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import Link from 'next/link';
import { clsx } from 'clsx';
import { PlanGenerator } from '@/components/plans/PlanGenerator';
import { PlanCalendar } from '@/components/plans/PlanCalendar';
import { useGeneratePlanStream, useGeneratePlan } from '@/hooks/usePlans';
import type { GeneratePlanRequest, TrainingPlan } from '@/lib/types';

export default function NewPlanPage() {
  const router = useRouter();
  const [useStreaming, setUseStreaming] = useState(true);
  const [showPreview, setShowPreview] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState<TrainingPlan | null>(null);

  // Streaming generation
  const streamingGeneration = useGeneratePlanStream();

  // Non-streaming generation (fallback)
  const nonStreamingGeneration = useGeneratePlan();

  const handleGenerate = useCallback(
    (request: GeneratePlanRequest) => {
      if (useStreaming) {
        streamingGeneration.generate(request);
      } else {
        nonStreamingGeneration.mutate(request, {
          onSuccess: (plan) => {
            setGeneratedPlan(plan);
            setShowPreview(true);
          },
        });
      }
    },
    [useStreaming, streamingGeneration, nonStreamingGeneration]
  );

  // Handle when streaming completes
  const handleStreamingComplete = useCallback(() => {
    if (streamingGeneration.generatedPlan) {
      setGeneratedPlan(streamingGeneration.generatedPlan);
      setShowPreview(true);
    }
  }, [streamingGeneration.generatedPlan]);

  // Check if streaming just completed
  if (
    streamingGeneration.generatedPlan &&
    !generatedPlan &&
    !showPreview
  ) {
    handleStreamingComplete();
  }

  const handleViewPlan = () => {
    if (generatedPlan) {
      router.push(`/plans/${generatedPlan.id}`);
    }
  };

  const handleCreateAnother = () => {
    setGeneratedPlan(null);
    setShowPreview(false);
    streamingGeneration.reset();
  };

  const isGenerating = useStreaming
    ? streamingGeneration.isGenerating
    : nonStreamingGeneration.isPending;

  const error = useStreaming
    ? streamingGeneration.error
    : nonStreamingGeneration.error instanceof Error
      ? nonStreamingGeneration.error
      : null;

  const progress = useStreaming ? streamingGeneration.progress : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/plans"
          className="p-2 rounded-lg hover:bg-gray-800 transition-colors"
        >
          <svg
            className="w-5 h-5 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">
            Create Training Plan
          </h1>
          <p className="text-gray-400 mt-1">
            Generate an AI-powered training plan tailored to your goals
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl">
        {!showPreview ? (
          <>
            {/* Streaming toggle */}
            <div className="mb-6 flex items-center justify-end gap-2">
              <span className="text-sm text-gray-400">Real-time generation</span>
              <button
                onClick={() => setUseStreaming(!useStreaming)}
                className={clsx(
                  'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                  useStreaming ? 'bg-teal-600' : 'bg-gray-700'
                )}
              >
                <span
                  className={clsx(
                    'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                    useStreaming ? 'translate-x-6' : 'translate-x-1'
                  )}
                />
              </button>
            </div>

            {/* Generator */}
            <PlanGenerator
              onGenerate={handleGenerate}
              onCancel={() => router.push('/plans')}
              isGenerating={isGenerating}
              generationProgress={progress}
              generatedPlan={generatedPlan}
              error={error}
            />

            {/* Info box */}
            <div className="mt-8 bg-teal-900/30 border border-teal-800 rounded-xl p-6">
              <h3 className="font-semibold text-teal-300 mb-2 flex items-center gap-2">
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                How it works
              </h3>
              <ul className="text-sm text-teal-200/80 space-y-2">
                <li className="flex items-start gap-2">
                  <span className="w-5 h-5 rounded-full bg-teal-800 text-teal-300 flex items-center justify-center text-xs font-bold shrink-0">
                    1
                  </span>
                  Set your race goal, target time, and race date
                </li>
                <li className="flex items-start gap-2">
                  <span className="w-5 h-5 rounded-full bg-teal-800 text-teal-300 flex items-center justify-center text-xs font-bold shrink-0">
                    2
                  </span>
                  Configure your training preferences and availability
                </li>
                <li className="flex items-start gap-2">
                  <span className="w-5 h-5 rounded-full bg-teal-800 text-teal-300 flex items-center justify-center text-xs font-bold shrink-0">
                    3
                  </span>
                  Our AI generates a personalized periodized plan
                </li>
                <li className="flex items-start gap-2">
                  <span className="w-5 h-5 rounded-full bg-teal-800 text-teal-300 flex items-center justify-center text-xs font-bold shrink-0">
                    4
                  </span>
                  Review, activate, and start training!
                </li>
              </ul>
            </div>
          </>
        ) : generatedPlan ? (
          <div className="space-y-6">
            {/* Success banner */}
            <div className="bg-teal-900/30 border border-teal-800 rounded-xl p-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-teal-800 rounded-full flex items-center justify-center">
                  <svg
                    className="w-6 h-6 text-teal-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
                <div>
                  <h3 className="font-semibold text-teal-300">
                    Plan Generated Successfully!
                  </h3>
                  <p className="text-sm text-teal-400">
                    Your {generatedPlan.totalWeeks}-week training plan is ready.
                  </p>
                </div>
              </div>
            </div>

            {/* Quick stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 text-center">
                <p className="text-2xl font-bold text-gray-100">
                  {generatedPlan.totalWeeks}
                </p>
                <p className="text-sm text-gray-500">Weeks</p>
              </div>
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 text-center">
                <p className="text-2xl font-bold text-gray-100">
                  {generatedPlan.weeks.reduce(
                    (acc, w) => acc + w.sessions.filter((s) => s.sessionType !== 'rest').length,
                    0
                  )}
                </p>
                <p className="text-sm text-gray-500">Sessions</p>
              </div>
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 text-center">
                <p className="text-2xl font-bold text-gray-100">
                  {generatedPlan.constraints.daysPerWeek}
                </p>
                <p className="text-sm text-gray-500">Days/Week</p>
              </div>
              <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 text-center">
                <p className="text-2xl font-bold text-gray-100 capitalize">
                  {generatedPlan.periodizationType}
                </p>
                <p className="text-sm text-gray-500">Periodization</p>
              </div>
            </div>

            {/* Plan preview */}
            <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-800">
                <h3 className="font-semibold text-gray-100">Plan Preview</h3>
              </div>
              <div className="p-6">
                <PlanCalendar plan={generatedPlan} />
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={handleViewPlan}
                className="px-8 py-3 bg-teal-600 text-white font-medium rounded-lg hover:bg-teal-500 transition-colors"
              >
                View Full Plan
              </button>
              <button
                onClick={handleCreateAnother}
                className="px-8 py-3 bg-gray-800 text-gray-300 font-medium rounded-lg hover:bg-gray-700 transition-colors"
              >
                Create Another Plan
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
