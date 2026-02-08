/**
 * Custom error classes for better error handling
 */

export class AppError extends Error {
  constructor(
    public statusCode: number,
    message: string,
    public details?: unknown
  ) {
    super(message);
    this.name = 'AppError';
    Error.captureStackTrace(this, this.constructor);
  }
}

export class ValidationError extends AppError {
  constructor(message: string, details?: unknown) {
    super(400, message, details);
    this.name = 'ValidationError';
  }
}

export class AuthenticationError extends AppError {
  constructor(message: string = '認証が必要です') {
    super(401, message);
    this.name = 'AuthenticationError';
  }
}

export class AuthorizationError extends AppError {
  constructor(message: string = 'この操作を実行する権限がありません') {
    super(403, message);
    this.name = 'AuthorizationError';
  }
}

export class NotFoundError extends AppError {
  constructor(message: string = 'リソースが見つかりません') {
    super(404, message);
    this.name = 'NotFoundError';
  }
}

export class ConflictError extends AppError {
  constructor(message: string = 'リソースが既に存在します') {
    super(409, message);
    this.name = 'ConflictError';
  }
}

export class RateLimitError extends AppError {
  constructor(message: string = 'リクエスト数が制限を超えました') {
    super(429, message);
    this.name = 'RateLimitError';
  }
}

export class InternalServerError extends AppError {
  constructor(message: string = 'Internal Server Error', details?: unknown) {
    super(500, message, details);
    this.name = 'InternalServerError';
  }
}

/**
 * Error handler utility
 */
export function isAppError(error: unknown): error is AppError {
  return error instanceof AppError;
}

export function formatError(error: unknown): { statusCode: number; message: string; details?: unknown } {
  if (isAppError(error)) {
    const result: { statusCode: number; message: string; details?: unknown } = {
      statusCode: error.statusCode,
      message: error.message,
    };
    if (error.details !== undefined) {
      result.details = error.details;
    }
    return result;
  }

  if (error instanceof Error) {
    return {
      statusCode: 500,
      message: 'Internal Server Error',
      details: process.env.NODE_ENV !== 'production' ? error.message : undefined,
    };
  }

  return {
    statusCode: 500,
    message: 'Unknown error occurred',
  };
}
