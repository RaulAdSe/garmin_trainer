'use client';

import { useCallback, useState } from 'react';
import { Link, useRouter } from '@/i18n/navigation';
import { PlanGenerator } from '@/components/plans/PlanGenerator';
import { useGeneratePlanStream } from '@/hooks/usePlans';
import type { GeneratePlanRequest, TrainingPlan } from '@/lib/types';

export default function NewPlanPage() {
  const router = useRouter();
  const [showSuccess, setShowSuccess] = useState(false);
  const [generatedPlan, setGeneratedPlan] = useState<TrainingPlan | null>(null);

  const { generate, isGenerating, progress, error, generatedPlan: streamedPlan, reset } = useGeneratePlanStream();

  const handleGenerate = useCallback((request: GeneratePlanRequest) => {
    generate(request);
  }, [generate]);

  // Handle streaming completion
  if (streamedPlan && !generatedPlan && !showSuccess) {
    setGeneratedPlan(streamedPlan);
    setShowSuccess(true);
  }

  const handleCreateAnother = () => {
    setGeneratedPlan(null);
    setShowSuccess(false);
    reset();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/plans"
          className="p-2 rounded-lg hover:bg-gray-800 transition-colors"
        >
          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </Link>
        <h1 className="text-2xl font-bold text-gray-100">Create Plan</h1>
      </div>

      {/* Content */}
      <div className="max-w-4xl">
        {!showSuccess ? (
          <PlanGenerator
            onGenerate={handleGenerate}
            onCancel={() => router.push('/plans')}
            isGenerating={isGenerating}
            generationProgress={progress}
            generatedPlan={generatedPlan}
            error={error}
          />
        ) : generatedPlan ? (
          <div className="space-y-6">
            {/* Success message */}
            <div className="bg-teal-900/30 border border-teal-800 rounded-xl p-8 text-center">
              <div className="w-16 h-16 bg-teal-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-teal-300 mb-2">
                Plan Created Successfully
              </h2>
              <p className="text-teal-400/80">
                {generatedPlan.name || `${generatedPlan.totalWeeks}-Week Training Plan`}
              </p>
            </div>

            {/* Actions */}
            <div className="flex flex-col items-center gap-3">
              <button
                onClick={() => router.push(`/plans/${generatedPlan.id}`)}
                className="w-full max-w-xs px-8 py-4 bg-teal-600 text-white font-semibold rounded-xl hover:bg-teal-500 transition-colors text-lg"
              >
                View Plan
              </button>
              <button
                onClick={handleCreateAnother}
                className="text-sm text-gray-400 hover:text-gray-300 transition-colors"
              >
                Create another plan
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
