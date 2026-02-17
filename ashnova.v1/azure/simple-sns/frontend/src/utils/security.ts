/**
 * Security utilities for the application
 */

/**
 * Sanitize HTML content to prevent XSS attacks
 * This is a basic implementation - for production, consider using DOMPurify
 */
export const sanitizeHtml = (html: string): string => {
  const div = document.createElement('div');
  div.textContent = html;
  return div.innerHTML;
};

/**
 * Validate JWT token structure (basic check)
 */
export const isValidJwtStructure = (token: string): boolean => {
  const parts = token.split('.');
  if (parts.length !== 3) return false;
  
  try {
    // Try to decode each part
    base64UrlDecode(parts[0]); // header
    base64UrlDecode(parts[1]); // payload
    // signature is not base64url decoded here
    return true;
  } catch {
    return false;
  }
};

/**
 * Validate token origin (check issuer)
 */
export const validateTokenIssuer = (token: string, expectedIssuer: string): boolean => {
  try {
    const payload = JSON.parse(base64UrlDecode(token.split('.')[1]));
    return payload.iss === expectedIssuer;
  } catch {
    return false;
  }
};

const base64UrlDecode = (input: string): string => {
  const base64 = input.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
  return atob(padded);
};

/**
 * Check if URL is safe for redirect
 */
export const isSafeRedirectUrl = (url: string, allowedOrigins: string[]): boolean => {
  try {
    const urlObj = new URL(url);
    return allowedOrigins.some(origin => urlObj.origin === origin);
  } catch {
    return false;
  }
};

/**
 * Generate Content Security Policy header value
 */
export const generateCSP = (): string => {
  return [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'", // Vite needs unsafe-inline in dev
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "font-src 'self' data:",
    "connect-src 'self' https://*.execute-api.ap-northeast-1.amazonaws.com https://*.auth.ap-northeast-1.amazoncognito.com https://*.cloudfront.net https://*.s3.amazonaws.com",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ');
};

/**
 * Rate limiting helper (client-side)
 */
export class RateLimiter {
  private attempts: Map<string, number[]> = new Map();
  private readonly maxAttempts: number;
  private readonly windowMs: number;

  constructor(maxAttempts: number = 10, windowMs: number = 60000) {
    this.maxAttempts = maxAttempts;
    this.windowMs = windowMs;
  }

  isAllowed(key: string): boolean {
    const now = Date.now();
    const attempts = this.attempts.get(key) || [];
    
    // Remove old attempts outside the window
    const recentAttempts = attempts.filter(time => now - time < this.windowMs);
    
    if (recentAttempts.length >= this.maxAttempts) {
      return false;
    }
    
    recentAttempts.push(now);
    this.attempts.set(key, recentAttempts);
    return true;
  }

  reset(key: string): void {
    this.attempts.delete(key);
  }
}
