/**
 * Performance monitoring middleware
 * Tracks Lambda execution metrics and performance
 */

import { logger } from '../utils/logger';

export interface PerformanceMetrics {
  functionName: string;
  executionTime: number;
  memoryUsed: number;
  coldStart: boolean;
  timestamp: string;
}

let isColdStart = true;

/**
 * Measure Lambda function execution time and memory usage
 */
export function measurePerformance<T>(
  functionName: string,
  fn: () => Promise<T>
): Promise<T> {
  const startTime = Date.now();
  const startMemory = process.memoryUsage().heapUsed;
  const coldStart = isColdStart;
  isColdStart = false;

  return fn()
    .then((result) => {
      const executionTime = Date.now() - startTime;
      const memoryUsed = process.memoryUsage().heapUsed - startMemory;

      const metrics: PerformanceMetrics = {
        functionName,
        executionTime,
        memoryUsed,
        coldStart,
        timestamp: new Date().toISOString(),
      };

      logger.info('Performance metrics', metrics);

      // Log warning for slow operations
      if (executionTime > 3000) {
        logger.warn('Slow operation detected', {
          functionName,
          executionTime,
        });
      }

      return result;
    })
    .catch((error) => {
      const executionTime = Date.now() - startTime;
      logger.error('Function execution failed', {
        functionName,
        executionTime,
        coldStart,
        error,
      });
      throw error;
    });
}

/**
 * Get current memory usage statistics
 */
export function getMemoryStats() {
  const usage = process.memoryUsage();
  return {
    heapUsed: Math.round(usage.heapUsed / 1024 / 1024),
    heapTotal: Math.round(usage.heapTotal / 1024 / 1024),
    external: Math.round(usage.external / 1024 / 1024),
    rss: Math.round(usage.rss / 1024 / 1024),
  };
}
