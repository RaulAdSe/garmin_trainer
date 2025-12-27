/**
 * Centralized error handling for the WHOOP Dashboard application.
 * Provides error categorization, user-friendly messages, and recovery options.
 */

// Error type categories
export enum ErrorType {
  NETWORK = 'NETWORK',
  AUTH = 'AUTH',
  API = 'API',
  STORAGE = 'STORAGE',
  UNKNOWN = 'UNKNOWN',
}

// Structured application error
export interface AppError {
  type: ErrorType;
  message: string;
  userMessage: string;
  recoverable: boolean;
  retryAction?: () => Promise<void>;
}

// User-friendly error messages for each error type
export const ERROR_MESSAGES: Record<ErrorType, string> = {
  [ErrorType.NETWORK]: 'Unable to connect. Check your internet connection.',
  [ErrorType.AUTH]: 'Session expired. Please log in again.',
  [ErrorType.API]: 'Garmin service unavailable. Try again later.',
  [ErrorType.STORAGE]: 'Unable to save data. Storage may be full.',
  [ErrorType.UNKNOWN]: 'Something went wrong. Please try again.',
};

// Common error patterns for categorization
const NETWORK_ERROR_PATTERNS = [
  'failed to fetch',
  'network error',
  'net::err',
  'networkerror',
  'econnrefused',
  'enotfound',
  'timeout',
  'aborted',
  'no internet',
  'offline',
];

const AUTH_ERROR_PATTERNS = [
  'unauthorized',
  'unauthenticated',
  'authentication failed',
  'invalid credentials',
  'session expired',
  'token expired',
  'login required',
  'access denied',
  '401',
  '403',
];

const STORAGE_ERROR_PATTERNS = [
  'quota exceeded',
  'storage full',
  'indexeddb',
  'localstorage',
  'storage',
  'disk full',
  'no space',
];

/**
 * Determines if an error matches any pattern in the given list
 */
function matchesPatterns(message: string, patterns: string[]): boolean {
  const lowerMessage = message.toLowerCase();
  return patterns.some((pattern) => lowerMessage.includes(pattern));
}

/**
 * Extracts error message from various error types
 */
function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  if (error && typeof error === 'object') {
    const errorObj = error as Record<string, unknown>;
    if (typeof errorObj.message === 'string') {
      return errorObj.message;
    }
    if (typeof errorObj.error === 'string') {
      return errorObj.error;
    }
  }
  return 'An unknown error occurred';
}

/**
 * Extracts HTTP status code from error if available
 */
function extractStatusCode(error: unknown): number | null {
  if (error && typeof error === 'object') {
    const errorObj = error as Record<string, unknown>;
    if (typeof errorObj.status === 'number') {
      return errorObj.status;
    }
    if (typeof errorObj.statusCode === 'number') {
      return errorObj.statusCode;
    }
  }
  return null;
}

/**
 * Categorizes an error based on its message and properties
 */
function categorizeError(error: unknown): ErrorType {
  const message = extractErrorMessage(error);
  const statusCode = extractStatusCode(error);

  // Check for auth errors by status code first
  if (statusCode === 401 || statusCode === 403) {
    return ErrorType.AUTH;
  }

  // Check for API errors by status code (5xx errors)
  if (statusCode && statusCode >= 500 && statusCode < 600) {
    return ErrorType.API;
  }

  // Check patterns in order of specificity
  if (matchesPatterns(message, AUTH_ERROR_PATTERNS)) {
    return ErrorType.AUTH;
  }

  if (matchesPatterns(message, NETWORK_ERROR_PATTERNS)) {
    return ErrorType.NETWORK;
  }

  if (matchesPatterns(message, STORAGE_ERROR_PATTERNS)) {
    return ErrorType.STORAGE;
  }

  // Check for fetch/API related errors
  if (error instanceof TypeError && message.includes('fetch')) {
    return ErrorType.NETWORK;
  }

  // Default to API error for server responses, otherwise unknown
  if (statusCode && statusCode >= 400) {
    return ErrorType.API;
  }

  return ErrorType.UNKNOWN;
}

/**
 * Determines if an error is recoverable (can be retried)
 */
function isRecoverable(errorType: ErrorType): boolean {
  switch (errorType) {
    case ErrorType.NETWORK:
      return true; // Network issues are often temporary
    case ErrorType.API:
      return true; // API issues may resolve on retry
    case ErrorType.AUTH:
      return false; // Auth errors require user action (re-login)
    case ErrorType.STORAGE:
      return false; // Storage errors typically need user intervention
    case ErrorType.UNKNOWN:
      return true; // Give unknown errors benefit of the doubt
    default:
      return false;
  }
}

/**
 * Main error handling function.
 * Categorizes an error and returns a structured AppError with user-friendly messaging.
 *
 * @param error - The caught error (can be any type)
 * @param retryAction - Optional function to retry the failed operation
 * @returns Structured AppError object
 *
 * @example
 * try {
 *   await fetchData();
 * } catch (error) {
 *   const appError = handleError(error, fetchData);
 *   showErrorBanner(appError);
 * }
 */
export function handleError(
  error: unknown,
  retryAction?: () => Promise<void>
): AppError {
  const errorType = categorizeError(error);
  const message = extractErrorMessage(error);
  const recoverable = isRecoverable(errorType);

  return {
    type: errorType,
    message,
    userMessage: ERROR_MESSAGES[errorType],
    recoverable,
    retryAction: recoverable && retryAction ? retryAction : undefined,
  };
}

/**
 * Creates a custom AppError with specified properties.
 * Useful for creating errors programmatically.
 *
 * @example
 * throw createAppError(ErrorType.AUTH, 'Token invalid', true);
 */
export function createAppError(
  type: ErrorType,
  message: string,
  recoverable: boolean = isRecoverable(type),
  retryAction?: () => Promise<void>
): AppError {
  return {
    type,
    message,
    userMessage: ERROR_MESSAGES[type],
    recoverable,
    retryAction,
  };
}

/**
 * Type guard to check if an object is an AppError
 */
export function isAppError(error: unknown): error is AppError {
  return (
    error !== null &&
    typeof error === 'object' &&
    'type' in error &&
    'message' in error &&
    'userMessage' in error &&
    'recoverable' in error &&
    Object.values(ErrorType).includes((error as AppError).type)
  );
}
