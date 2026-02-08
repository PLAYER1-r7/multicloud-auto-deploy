import type { APIGatewayProxyResult } from "aws-lambda";

// 定数
export const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Requested-With",
  "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "X-XSS-Protection": "1; mode=block",
  "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
  "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
  "X-Rate-Limit-Limit": "100",
  "X-Rate-Limit-Remaining": "99",
  "X-Rate-Limit-Reset": "3600"
} as const;

export const MAX_CONTENT_LENGTH = 5000;
export const MAX_LIMIT = 50;
export const DEFAULT_LIMIT = 20;
export const MAX_IMAGES_PER_POST = 16;
export const MAX_TAGS_PER_POST = 100;
export const MAX_TAG_LENGTH = 50;
export const PRESIGNED_URL_EXPIRY = 300; // 5 minutes
export const MIN_NICKNAME_LENGTH = 1;
export const MAX_NICKNAME_LENGTH = 50;
export const USER_PROFILE_PK_PREFIX = 'USER#';
export const USER_PROFILE_SK = 'PROFILE';

export const buildUserProfileKey = (userId: string) => ({
  PK: `${USER_PROFILE_PK_PREFIX}${userId}`,
  SK: USER_PROFILE_SK,
});

export function json(statusCode: number, body: unknown): APIGatewayProxyResult {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store, no-cache, must-revalidate, private",
      "Pragma": "no-cache",
      ...CORS_HEADERS
    },
    body: JSON.stringify(body)
  };
}

export function getAllowedUsers(): Set<string> {
  const raw = process.env.ALLOWED_USERS ?? "userA,userB";
  return new Set(raw.split(",").map(s => s.trim()).filter(Boolean));
}

export function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v || v.trim() === '') {
    throw new Error(`Missing or empty environment variable: ${name}`);
  }
  return v.trim();
}

export function getEnvOrDefault(name: string, defaultValue: string): string {
  const v = process.env[name];
  return v && v.trim() !== '' ? v.trim() : defaultValue;
}

export function parseLimit(
  raw: string | undefined,
  max = MAX_LIMIT,
  def = DEFAULT_LIMIT
): number {
  const n = raw ? Number(raw) : def;
  if (!Number.isFinite(n) || n <= 0) return def;
  return Math.min(Math.floor(n), max);
}