/**
 * Utility functions for AWS SDK operations
 * Provides retry logic, exponential backoff, and error handling
 */

import { logger } from './logger';

export interface RetryOptions {
  maxRetries?: number;
  initialDelayMs?: number;
  maxDelayMs?: number;
  backoffMultiplier?: number;
}

/**
 * Execute an async operation with exponential backoff retry
 */
export async function withRetry<T>(
  operation: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const {
    maxRetries = 3,
    initialDelayMs = 100,
    maxDelayMs = 5000,
    backoffMultiplier = 2,
  } = options;

  let lastError: Error | undefined;
  let delay = initialDelayMs;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      // Don't retry on certain errors
      if (isNonRetryableError(error)) {
        throw error;
      }

      if (attempt < maxRetries) {
        logger.warn('Operation failed, retrying', {
          attempt: attempt + 1,
          maxRetries,
          delay,
          error: lastError.message,
        });

        await sleep(delay);
        delay = Math.min(delay * backoffMultiplier, maxDelayMs);
      }
    }
  }

  logger.error('Operation failed after all retries', {
    maxRetries,
    error: lastError,
  });

  throw lastError;
}

/**
 * Check if an error should not be retried
 */
function isNonRetryableError(error: unknown): boolean {
  if (typeof error === 'object' && error !== null) {
    const err = error as any;
    // Don't retry validation errors, authentication errors, etc.
    const nonRetryableCodes = [
      'ValidationException',
      'InvalidParameterException',
      'AccessDeniedException',
      'UnauthorizedException',
      'NotAuthorizedException',
    ];
    return nonRetryableCodes.includes(err.name || err.code);
  }
  return false;
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Batch process items with concurrency control
 */
export async function batchProcess<T, R>(
  items: T[],
  processor: (item: T) => Promise<R>,
  concurrency: number = 5
): Promise<R[]> {
  const results: R[] = [];
  const executing: Promise<void>[] = [];

  for (const item of items) {
    const promise = processor(item).then((result) => {
      results.push(result);
    });

    executing.push(promise);

    if (executing.length >= concurrency) {
      await Promise.race(executing);
      executing.splice(
        executing.findIndex((p) => p === promise),
        1
      );
    }
  }

  await Promise.all(executing);
  return results;
}

/**
 * Chunk array into smaller arrays
 */
export function chunkArray<T>(array: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < array.length; i += size) {
    chunks.push(array.slice(i, i + size));
  }
  return chunks;
}

/**
 * Safe JSON parse with fallback
 */
export function safeJsonParse<T>(json: string, fallback: T): T {
  try {
    return JSON.parse(json) as T;
  } catch (error) {
    logger.warn('Failed to parse JSON', { error, json });
    return fallback;
  }
}

/**
 * Measure execution time of an async function
 */
export async function measureTime<T>(
  fn: () => Promise<T>,
  label: string
): Promise<{ result: T; duration: number }> {
  const start = Date.now();
  const result = await fn();
  const duration = Date.now() - start;

  logger.debug('Operation completed', { label, duration });

  return { result, duration };
}
