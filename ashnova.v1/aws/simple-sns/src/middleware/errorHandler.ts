import type { APIGatewayProxyResult } from 'aws-lambda';
import { CORS_HEADERS } from '../common';
import { formatError, isAppError } from '../utils/errors';
import { logger } from '../utils/logger';

/**
 * Standard error handler middleware for Lambda functions
 */
export function handleError(error: unknown, context?: string): APIGatewayProxyResult {
  const errorInfo = formatError(error);
  
  // Log error with context
  if (isAppError(error) && error.statusCode < 500) {
    logger.warn('Client error', {
      context,
      statusCode: error.statusCode,
      message: error.message,
      details: error.details,
    });
  } else {
    logger.error('Server error', {
      context,
      statusCode: errorInfo.statusCode,
      message: errorInfo.message,
      error: error instanceof Error ? {
        name: error.name,
        message: error.message,
        stack: error.stack,
      } : error,
    });
  }

  const responseBody: { message: string; details?: unknown } = {
    message: errorInfo.message,
  };
  if (errorInfo.details !== undefined) {
    responseBody.details = errorInfo.details;
  }

  return {
    statusCode: errorInfo.statusCode,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      ...CORS_HEADERS,
    },
    body: JSON.stringify(responseBody),
  };
}

/**
 * Extract user info from Lambda authorizer claims
 */
export function extractUserInfo(claims: Record<string, any> | undefined): {
  userId: string;
  isAdmin: boolean;
} | null {
  if (!claims || !claims.sub) {
    return null;
  }

  const groups = claims['cognito:groups'];
  const isAdmin = groups && (
    (typeof groups === 'string' && groups === 'Admins') ||
    (Array.isArray(groups) && groups.includes('Admins'))
  );

  return {
    userId: claims.sub,
    isAdmin: !!isAdmin,
  };
}
