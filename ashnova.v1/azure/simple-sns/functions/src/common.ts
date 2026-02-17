import { HttpRequest, HttpResponseInit } from '@azure/functions';
import jwt from 'jsonwebtoken';
import jwksClient from 'jwks-rsa';

export const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Requested-With',
  'Access-Control-Allow-Methods': 'GET,POST,DELETE,OPTIONS',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-XSS-Protection': '1; mode=block',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
} as const;

// JWKS client for Azure AD token verification
const client = jwksClient({
  jwksUri: `https://login.microsoftonline.com/${process.env.AZURE_AD_TENANT_ID}/discovery/v2.0/keys`,
  cache: true,
  cacheMaxAge: 86400000, // 24 hours
});

export const MAX_CONTENT_LENGTH = 5000;
export const MAX_LIMIT = 50;
export const DEFAULT_LIMIT = 20;
export const MAX_IMAGES_PER_POST = 16;
export const MAX_TAGS_PER_POST = 100;
export const MAX_TAG_LENGTH = 50;
export const PRESIGNED_URL_EXPIRY = 300; // 5 minutes
export const MIN_NICKNAME_LENGTH = 1;
export const MAX_NICKNAME_LENGTH = 50;
export const PROFILE_DOC_TYPE = 'profile';
export const PROFILE_ID_PREFIX = 'profile-';

export function buildProfileId(userId: string): string {
  return `${PROFILE_ID_PREFIX}${userId}`;
}

export function jsonResponse(status: number, body: unknown): HttpResponseInit {
  return {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store, no-cache, must-revalidate, private',
      'Pragma': 'no-cache',
      ...CORS_HEADERS,
    },
    jsonBody: body,
  };
}

export function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v || v.trim() === '') {
    throw new Error(`Missing or empty environment variable: ${name}`);
  }
  return v.trim();
}

export async function extractUserInfo(request: HttpRequest): Promise<{ userId: string; email?: string; nickname?: string } | null> {
  const authHeader = request.headers.get('authorization');
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }

  const token = authHeader.substring(7);

  return new Promise((resolve) => {
    // Decode token header to get kid (key ID)
    let decoded: any;
    try {
      decoded = jwt.decode(token, { complete: true });
      if (!decoded || !decoded.header || !decoded.header.kid) {
        console.error('Invalid token structure');
        return resolve(null);
      }
      
      // Log token details for debugging
      console.log('Token issuer:', decoded.payload.iss);
      console.log('Token audience:', decoded.payload.aud);
      console.log('Expected issuers:', [
        `https://login.microsoftonline.com/${process.env.AZURE_AD_TENANT_ID}/v2.0`,
        'https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/v2.0'
      ]);
      console.log('Expected audience:', process.env.AZURE_AD_CLIENT_ID);
    } catch (err) {
      console.error('Token decode error:', err);
      return resolve(null);
    }

    // Get signing key from JWKS
    const getKey = (header: any, callback: any) => {
      client.getSigningKey(header.kid, (err: any, key: any) => {
        if (err) {
          console.error('JWKS error:', err);
          return callback(err);
        }
        const signingKey = key?.getPublicKey();
        callback(null, signingKey);
      });
    };

    // Verify token
    jwt.verify(token, getKey, {
      // Note: Accepting Microsoft Graph audience since we use User.Read scope
      // In production, consider exposing custom API scopes
      issuer: [
        // v2.0 endpoint formats
        `https://login.microsoftonline.com/${process.env.AZURE_AD_TENANT_ID}/v2.0`,
        'https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/v2.0',
        // v1.0 endpoint formats (sts.windows.net)
        `https://sts.windows.net/${process.env.AZURE_AD_TENANT_ID}/`,
        'https://sts.windows.net/9188040d-6c67-4c5b-b112-36a304b66dad/',
      ],
      algorithms: ['RS256']
    }, (err: Error | null, decoded: unknown) => {
      if (err) {
        console.error('Token verification error:', err.message);
        console.error('Token details from decode:', decoded);
        return resolve(null);
      }

      const payload = typeof decoded === 'object' && decoded !== null
        ? (decoded as Record<string, unknown>)
        : {};

      // Extract user info from Azure AD token
      const userId =
        (typeof payload.oid === 'string' && payload.oid) ||
        (typeof payload.sub === 'string' && payload.sub) ||
        undefined;
      const email =
        (typeof payload.email === 'string' && payload.email) ||
        (typeof payload.preferred_username === 'string' && payload.preferred_username) ||
        (typeof payload.upn === 'string' && payload.upn) ||
        undefined;
      const nickname =
        (typeof payload.name === 'string' && payload.name) ||
        (typeof payload.preferred_username === 'string' && payload.preferred_username) ||
        (typeof payload.email === 'string' && payload.email) ||
        (typeof payload.upn === 'string' && payload.upn) ||
        undefined;

      if (!userId) {
        console.error('No user ID found in token');
        return resolve(null);
      }

      resolve({ userId, email, nickname });
    });
  });
}
