/**
 * Request validation and sanitization middleware
 * Provides additional security checks and input sanitization
 */

import type { APIGatewayProxyEvent } from 'aws-lambda';
import { ValidationError } from '../utils/errors';

/**
 * Sanitize user input to prevent XSS and injection attacks
 */
export function sanitizeInput(input: string): string {
  return input
    .trim()
    .replace(/<script[^>]*>.*?<\/script>/gi, '')
    .replace(/<iframe[^>]*>.*?<\/iframe>/gi, '')
    .replace(/javascript:/gi, '')
    .replace(/on\w+\s*=/gi, '');
}

/**
 * Validate request size to prevent DOS attacks
 */
export function validateRequestSize(event: APIGatewayProxyEvent, maxSize: number = 1024 * 1024): void {
  const bodySize = event.body ? Buffer.byteLength(event.body, 'utf8') : 0;
  
  if (bodySize > maxSize) {
    throw new ValidationError(`Request body too large: ${bodySize} bytes (max ${maxSize} bytes)`);
  }
}

/**
 * Validate required headers
 */
export function validateRequiredHeaders(
  event: APIGatewayProxyEvent,
  requiredHeaders: string[]
): void {
  const headers = event.headers || {};
  const lowerHeaders = Object.keys(headers).reduce((acc, key) => {
    const value = headers[key];
    if (value) {
      acc[key.toLowerCase()] = value;
    }
    return acc;
  }, {} as Record<string, string>);

  for (const header of requiredHeaders) {
    if (!lowerHeaders[header.toLowerCase()]) {
      throw new ValidationError(`Missing required header: ${header}`);
    }
  }
}

/**
 * Extract and validate pagination parameters
 */
export function extractPaginationParams(event: APIGatewayProxyEvent): {
  limit: number;
  offset: number;
  nextToken?: string;
} {
  const params = event.queryStringParameters || {};
  const limit = Math.min(parseInt(params.limit || '20', 10), 100);
  const offset = Math.max(parseInt(params.offset || '0', 10), 0);
  const nextToken = params.nextToken;

  if (isNaN(limit) || isNaN(offset)) {
    throw new ValidationError('Invalid pagination parameters');
  }

  return { limit, offset, nextToken };
}

/**
 * Rate limiting check (basic implementation)
 * In production, use Redis or DynamoDB for distributed rate limiting
 */
const rateLimitStore = new Map<string, { count: number; resetAt: number }>();

export function checkRateLimit(
  identifier: string,
  maxRequests: number = 100,
  windowMs: number = 60000
): void {
  const now = Date.now();
  const entry = rateLimitStore.get(identifier);

  if (entry && entry.resetAt > now) {
    if (entry.count >= maxRequests) {
      throw new ValidationError('Rate limit exceeded. Please try again later.');
    }
    entry.count++;
  } else {
    rateLimitStore.set(identifier, {
      count: 1,
      resetAt: now + windowMs,
    });
  }

  // Cleanup old entries periodically
  if (Math.random() < 0.01) {
    for (const [key, value] of rateLimitStore.entries()) {
      if (value.resetAt < now) {
        rateLimitStore.delete(key);
      }
    }
  }
}
