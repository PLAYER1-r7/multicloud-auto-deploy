import type { Request, Response } from '@google-cloud/functions-framework';
import * as admin from 'firebase-admin';

// Initialize Firebase Admin
if (!admin.apps.length) {
  admin.initializeApp();
}

export const db = admin.firestore();
export const storage = admin.storage();

export const MAX_IMAGES_PER_POST = 5;
export const MAX_TAGS_PER_POST = 10;
export const MAX_CONTENT_LENGTH = 5000;
export const MIN_NICKNAME_LENGTH = 1;
export const MAX_NICKNAME_LENGTH = 50;
export const SAS_URL_EXPIRY_MINUTES = 5;
export const USER_PROFILE_COLLECTION = 'userProfiles';
export const REQUIRE_EMAIL_VERIFIED = (process.env.REQUIRE_EMAIL_VERIFIED || '').toLowerCase() === 'true';

export interface UserInfo {
  userId: string;
  email?: string;
  nickname?: string;
}

export interface UserProfile {
  userId: string;
  nickname?: string;
  updatedAt?: string;
  createdAt?: string;
}

/**
 * Extract user info from Firebase Auth token
 */
export async function extractUserInfo(req: Request): Promise<UserInfo | null> {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }

  const token = authHeader.substring(7);
  try {
    const decodedToken = await admin.auth().verifyIdToken(token);
    if (REQUIRE_EMAIL_VERIFIED && decodedToken.email && decodedToken.email_verified !== true) {
      return null;
    }
    return {
      userId: decodedToken.uid,
      email: decodedToken.email,
      nickname: decodedToken.name || decodedToken.email || decodedToken.uid,
    };
  } catch (error) {
    console.error('Token verification failed:', error);
    return null;
  }
}

export async function getNicknameByUserId(userId: string): Promise<string | undefined> {
  const doc = await db.collection(USER_PROFILE_COLLECTION).doc(userId).get();
  if (!doc.exists) {
    return undefined;
  }
  const data = doc.data();
  if (!data || typeof data.nickname !== 'string') {
    return undefined;
  }
  const nickname = data.nickname.trim();
  return nickname ? nickname : undefined;
}

/**
 * JSON response helper
 */
export function jsonResponse(res: Response, statusCode: number, data: any) {
  setSecurityHeaders(res);
  res.status(statusCode).json(data);
}

/**
 * Security headers
 */
export function setSecurityHeaders(res: Response) {
  res.set('X-Content-Type-Options', 'nosniff');
  res.set('X-Frame-Options', 'DENY');
  res.set('Referrer-Policy', 'no-referrer');
  res.set('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');
  res.set('Strict-Transport-Security', 'max-age=63072000; includeSubDomains; preload');
}

/**
 * CORS headers - Allow all origins for simplicity
 */
export function setCorsHeaders(res: Response, req?: Request) {
  const originHeader = req?.headers.origin;
  const allowedOrigins = (process.env.ALLOWED_ORIGIN || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);
  const originCandidates = (originHeader || '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);
  const isAllowed = (value?: string) => {
    if (!value) return false;
    if (allowedOrigins.length === 0) {
      return value.startsWith('https://') || value.startsWith('http://localhost');
    }
    return allowedOrigins.includes(value);
  };
  const allowedOrigin = originCandidates.find((candidate) => isAllowed(candidate));

  if (allowedOrigins.length > 0 && originHeader && !allowedOrigin) {
    res.set('Vary', 'Origin');
    res.status(403).json({ message: 'Origin not allowed' });
    return false;
  }

  if (allowedOrigin) {
    res.set('Access-Control-Allow-Origin', allowedOrigin);
  } else if (allowedOrigins.length === 0) {
    res.set('Access-Control-Allow-Origin', '*');
  }
  
  res.set('Access-Control-Allow-Credentials', 'true');
  res.set('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Authorization, Content-Type');
  return true;
}

/**
 * Handle OPTIONS requests for CORS
 */
export function handleCorsOptions(req: Request, res: Response): boolean {
  if (req.method === 'OPTIONS') {
    if (!setCorsHeaders(res, req)) {
      return true;
    }
    setSecurityHeaders(res);
    res.status(204).send('');
    return true;
  }
  if (!setCorsHeaders(res, req)) {
    return true;
  }
  return false;
}

/**
 * Require environment variable
 */
export function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}
