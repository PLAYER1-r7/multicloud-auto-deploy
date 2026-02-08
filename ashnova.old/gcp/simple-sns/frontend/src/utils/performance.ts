/**
 * パフォーマンス監視ユーティリティ
 */

interface PerformanceMetrics {
  name: string;
  duration: number;
  timestamp: number;
}

class PerformanceMonitor {
  private metrics: PerformanceMetrics[] = [];
  private readonly maxMetrics = 100;

  /**
   * 処理時間を計測
   */
  measure<T>(name: string, fn: () => T): T {
    const start = performance.now();
    try {
      const result = fn();
      return result;
    } finally {
      const duration = performance.now() - start;
      this.recordMetric(name, duration);
      
      // 開発環境でログ出力
      if (import.meta.env.DEV) {
        console.log(`⏱️ [Performance] ${name}: ${duration.toFixed(2)}ms`);
      }
    }
  }

  /**
   * 非同期処理の時間を計測
   */
  async measureAsync<T>(name: string, fn: () => Promise<T>): Promise<T> {
    const start = performance.now();
    try {
      const result = await fn();
      return result;
    } finally {
      const duration = performance.now() - start;
      this.recordMetric(name, duration);
      
      if (import.meta.env.DEV) {
        console.log(`⏱️ [Performance] ${name}: ${duration.toFixed(2)}ms`);
      }
    }
  }

  /**
   * メトリクスを記録
   */
  private recordMetric(name: string, duration: number): void {
    this.metrics.push({
      name,
      duration,
      timestamp: Date.now(),
    });

    // 古いメトリクスを削除
    if (this.metrics.length > this.maxMetrics) {
      this.metrics.shift();
    }
  }

  /**
   * 統計情報を取得
   */
  getStats(name?: string): {
    count: number;
    avg: number;
    min: number;
    max: number;
    total: number;
  } | null {
    const filtered = name 
      ? this.metrics.filter(m => m.name === name)
      : this.metrics;

    if (filtered.length === 0) return null;

    const durations = filtered.map(m => m.duration);
    return {
      count: filtered.length,
      avg: durations.reduce((a, b) => a + b, 0) / durations.length,
      min: Math.min(...durations),
      max: Math.max(...durations),
      total: durations.reduce((a, b) => a + b, 0),
    };
  }

  /**
   * すべてのメトリクスをクリア
   */
  clear(): void {
    this.metrics = [];
  }

  /**
   * メトリクス一覧を取得
   */
  getMetrics(): PerformanceMetrics[] {
    return [...this.metrics];
  }
}

// シングルトンインスタンスをエクスポート
export const performanceMonitor = new PerformanceMonitor();

/**
 * 関数をデコレートしてパフォーマンスを計測
 */
export function measurePerformance<T extends (...args: any[]) => any>(
  name: string,
  fn: T
): T {
  return ((...args: Parameters<T>) => {
    return performanceMonitor.measure(name, () => fn(...args));
  }) as T;
}

/**
 * 非同期関数をデコレートしてパフォーマンスを計測
 */
export function measurePerformanceAsync<T extends (...args: any[]) => Promise<any>>(
  name: string,
  fn: T
): T {
  return (async (...args: Parameters<T>) => {
    return await performanceMonitor.measureAsync(name, () => fn(...args));
  }) as T;
}
