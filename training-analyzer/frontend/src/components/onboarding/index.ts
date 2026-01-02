// Onboarding components barrel export

// New 3-phase onboarding flow
export { OnboardingFlow, OnboardingWrapper, OnboardingComplete } from './OnboardingFlow';
export { WelcomeStep } from './WelcomeStep';
export { ConnectionStep } from './ConnectionStep';
export { ProfileStep } from './ProfileStep';
export { FeatureIntroStep, FeatureHint } from './FeatureIntroStep';

// Legacy onboarding components (for backward compatibility)
export { ContextualTooltip, HighlightWrapper } from './ContextualTooltip';
export type { ContextualTooltipProps, TooltipPosition } from './ContextualTooltip';

export { TooltipTriggers, OnboardingProvider } from './TooltipTriggers';

export { PurposeStep } from './PurposeStep';
