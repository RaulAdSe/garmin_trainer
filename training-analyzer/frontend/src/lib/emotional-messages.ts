/**
 * Emotional Support Messaging Library
 *
 * Provides contextual supportive messages based on athlete state and training context.
 * Messages are designed to be empathetic, supportive, and encouraging.
 */

export type EmotionalContext =
  | 'red_zone_readiness'
  | 'streak_break'
  | 'plateau'
  | 'bad_workout'
  | 'comeback'
  | 'consistency_milestone'
  | 'recovery_day';

export type MessageTone = 'empathetic' | 'supportive' | 'encouraging';

export interface EmotionalMessageData {
  message: string;
  tone: MessageTone;
  actionSuggestion?: string;
  recoveryTips?: string[];
  alternativeActivities?: string[];
}

export interface EmotionalMessage extends EmotionalMessageData {
  context: EmotionalContext;
}

/**
 * Message bank with multiple variations per context
 * Using i18n keys for translation support
 */
export const MESSAGE_BANK: Record<EmotionalContext, EmotionalMessageData[]> = {
  red_zone_readiness: [
    {
      message: 'emotional.redZone.message1',
      tone: 'empathetic',
      actionSuggestion: 'emotional.redZone.action1',
      recoveryTips: [
        'emotional.redZone.tip1',
        'emotional.redZone.tip2',
        'emotional.redZone.tip3',
      ],
      alternativeActivities: [
        'emotional.activities.yoga',
        'emotional.activities.walking',
        'emotional.activities.foamRolling',
        'emotional.activities.meditation',
      ],
    },
    {
      message: 'emotional.redZone.message2',
      tone: 'supportive',
      actionSuggestion: 'emotional.redZone.action2',
      recoveryTips: [
        'emotional.redZone.tip4',
        'emotional.redZone.tip5',
        'emotional.redZone.tip6',
      ],
      alternativeActivities: [
        'emotional.activities.easySwim',
        'emotional.activities.stretching',
        'emotional.activities.breathwork',
        'emotional.activities.massage',
      ],
    },
    {
      message: 'emotional.redZone.message3',
      tone: 'encouraging',
      actionSuggestion: 'emotional.redZone.action3',
      recoveryTips: [
        'emotional.redZone.tip7',
        'emotional.redZone.tip8',
        'emotional.redZone.tip9',
      ],
      alternativeActivities: [
        'emotional.activities.visualization',
        'emotional.activities.mobility',
        'emotional.activities.easyCycling',
        'emotional.activities.reading',
      ],
    },
  ],
  streak_break: [
    {
      message: 'emotional.streakBreak.message1',
      tone: 'empathetic',
      actionSuggestion: 'emotional.streakBreak.action1',
    },
    {
      message: 'emotional.streakBreak.message2',
      tone: 'supportive',
      actionSuggestion: 'emotional.streakBreak.action2',
    },
    {
      message: 'emotional.streakBreak.message3',
      tone: 'encouraging',
      actionSuggestion: 'emotional.streakBreak.action3',
    },
  ],
  plateau: [
    {
      message: 'emotional.plateau.message1',
      tone: 'empathetic',
      actionSuggestion: 'emotional.plateau.action1',
    },
    {
      message: 'emotional.plateau.message2',
      tone: 'supportive',
      actionSuggestion: 'emotional.plateau.action2',
    },
    {
      message: 'emotional.plateau.message3',
      tone: 'encouraging',
      actionSuggestion: 'emotional.plateau.action3',
    },
  ],
  bad_workout: [
    {
      message: 'emotional.badWorkout.message1',
      tone: 'empathetic',
      actionSuggestion: 'emotional.badWorkout.action1',
    },
    {
      message: 'emotional.badWorkout.message2',
      tone: 'supportive',
      actionSuggestion: 'emotional.badWorkout.action2',
    },
    {
      message: 'emotional.badWorkout.message3',
      tone: 'encouraging',
      actionSuggestion: 'emotional.badWorkout.action3',
    },
  ],
  comeback: [
    {
      message: 'emotional.comeback.message1',
      tone: 'encouraging',
      actionSuggestion: 'emotional.comeback.action1',
    },
    {
      message: 'emotional.comeback.message2',
      tone: 'supportive',
      actionSuggestion: 'emotional.comeback.action2',
    },
    {
      message: 'emotional.comeback.message3',
      tone: 'empathetic',
      actionSuggestion: 'emotional.comeback.action3',
    },
  ],
  consistency_milestone: [
    {
      message: 'emotional.consistency.message1',
      tone: 'encouraging',
      actionSuggestion: 'emotional.consistency.action1',
    },
    {
      message: 'emotional.consistency.message2',
      tone: 'supportive',
      actionSuggestion: 'emotional.consistency.action2',
    },
    {
      message: 'emotional.consistency.message3',
      tone: 'empathetic',
      actionSuggestion: 'emotional.consistency.action3',
    },
  ],
  recovery_day: [
    {
      message: 'emotional.recoveryDay.message1',
      tone: 'empathetic',
      actionSuggestion: 'emotional.recoveryDay.action1',
      recoveryTips: [
        'emotional.recoveryDay.tip1',
        'emotional.recoveryDay.tip2',
        'emotional.recoveryDay.tip3',
      ],
      alternativeActivities: [
        'emotional.activities.easyWalking',
        'emotional.activities.yoga',
        'emotional.activities.swimming',
        'emotional.activities.foamRolling',
      ],
    },
    {
      message: 'emotional.recoveryDay.message2',
      tone: 'supportive',
      actionSuggestion: 'emotional.recoveryDay.action2',
      recoveryTips: [
        'emotional.recoveryDay.tip4',
        'emotional.recoveryDay.tip5',
        'emotional.recoveryDay.tip6',
      ],
      alternativeActivities: [
        'emotional.activities.stretching',
        'emotional.activities.easyCycling',
        'emotional.activities.meditation',
        'emotional.activities.natureWalk',
      ],
    },
    {
      message: 'emotional.recoveryDay.message3',
      tone: 'encouraging',
      actionSuggestion: 'emotional.recoveryDay.action3',
      recoveryTips: [
        'emotional.recoveryDay.tip7',
        'emotional.recoveryDay.tip8',
        'emotional.recoveryDay.tip9',
      ],
      alternativeActivities: [
        'emotional.activities.easySwim',
        'emotional.activities.mobility',
        'emotional.activities.lightHike',
        'emotional.activities.dance',
      ],
    },
  ],
};

/**
 * Get a random message for a given context
 */
export function getRandomMessage(
  context: EmotionalContext,
  preferredTone?: MessageTone
): EmotionalMessageData | null {
  const messages = MESSAGE_BANK[context];
  if (!messages || messages.length === 0) return null;

  let filteredMessages = messages;
  if (preferredTone) {
    const filtered = messages.filter((m) => m.tone === preferredTone);
    if (filtered.length > 0) {
      filteredMessages = filtered;
    }
  }

  const randomIndex = Math.floor(Math.random() * filteredMessages.length);
  return filteredMessages[randomIndex];
}

/**
 * Get all messages for a given context
 */
export function getAllMessages(context: EmotionalContext): EmotionalMessageData[] {
  return MESSAGE_BANK[context] || [];
}

/**
 * Detect appropriate context from athlete data
 */
export interface AthleteContextData {
  readinessScore?: number;
  currentStreak?: number;
  previousStreak?: number;
  daysSinceLastWorkout?: number;
  weeksWithoutImprovement?: number;
  lastWorkoutScore?: number;
  daysSinceComeback?: number;
  consecutiveTrainingDays?: number;
}

export function detectEmotionalContext(data: AthleteContextData): EmotionalContext | null {
  // Priority order for context detection

  // 1. Red zone readiness is highest priority
  if (data.readinessScore !== undefined && data.readinessScore < 40) {
    return 'red_zone_readiness';
  }

  // 2. Streak break detection
  if (
    data.currentStreak === 0 &&
    data.previousStreak !== undefined &&
    data.previousStreak >= 7
  ) {
    return 'streak_break';
  }

  // 3. Comeback detection
  if (
    data.daysSinceComeback !== undefined &&
    data.daysSinceComeback <= 7 &&
    data.daysSinceLastWorkout !== undefined &&
    data.daysSinceLastWorkout > 14
  ) {
    return 'comeback';
  }

  // 4. Bad workout detection
  if (data.lastWorkoutScore !== undefined && data.lastWorkoutScore < 50) {
    return 'bad_workout';
  }

  // 5. Plateau detection
  if (data.weeksWithoutImprovement !== undefined && data.weeksWithoutImprovement >= 3) {
    return 'plateau';
  }

  // 6. Consistency milestone detection
  if (data.consecutiveTrainingDays !== undefined) {
    const milestones = [7, 14, 21, 30, 60, 90, 180, 365];
    if (milestones.includes(data.consecutiveTrainingDays)) {
      return 'consistency_milestone';
    }
  }

  // 7. Recovery day detection
  if (
    data.readinessScore !== undefined &&
    data.readinessScore >= 40 &&
    data.readinessScore < 60
  ) {
    return 'recovery_day';
  }

  return null;
}

/**
 * Get tone color for styling
 */
export function getToneColor(tone: MessageTone): {
  bg: string;
  border: string;
  text: string;
  icon: string;
} {
  switch (tone) {
    case 'empathetic':
      return {
        bg: 'bg-purple-900/30',
        border: 'border-purple-700/50',
        text: 'text-purple-300',
        icon: 'text-purple-400',
      };
    case 'supportive':
      return {
        bg: 'bg-blue-900/30',
        border: 'border-blue-700/50',
        text: 'text-blue-300',
        icon: 'text-blue-400',
      };
    case 'encouraging':
      return {
        bg: 'bg-teal-900/30',
        border: 'border-teal-700/50',
        text: 'text-teal-300',
        icon: 'text-teal-400',
      };
    default:
      return {
        bg: 'bg-gray-800/50',
        border: 'border-gray-700/50',
        text: 'text-gray-300',
        icon: 'text-gray-400',
      };
  }
}

/**
 * Get context icon name
 */
export function getContextIcon(context: EmotionalContext): string {
  switch (context) {
    case 'red_zone_readiness':
      return 'battery-low';
    case 'streak_break':
      return 'flame-off';
    case 'plateau':
      return 'trending-neutral';
    case 'bad_workout':
      return 'cloud-rain';
    case 'comeback':
      return 'sunrise';
    case 'consistency_milestone':
      return 'trophy';
    case 'recovery_day':
      return 'heart-pulse';
    default:
      return 'message-circle';
  }
}

/**
 * Get human-readable context label
 */
export function getContextLabel(context: EmotionalContext): string {
  switch (context) {
    case 'red_zone_readiness':
      return 'emotional.context.redZone';
    case 'streak_break':
      return 'emotional.context.streakBreak';
    case 'plateau':
      return 'emotional.context.plateau';
    case 'bad_workout':
      return 'emotional.context.badWorkout';
    case 'comeback':
      return 'emotional.context.comeback';
    case 'consistency_milestone':
      return 'emotional.context.consistencyMilestone';
    case 'recovery_day':
      return 'emotional.context.recoveryDay';
    default:
      return 'emotional.context.general';
  }
}
