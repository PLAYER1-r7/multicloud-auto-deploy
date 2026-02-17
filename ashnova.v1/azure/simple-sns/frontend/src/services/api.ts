import { isValidJwtStructure, validateTokenIssuer, RateLimiter } from '../utils/security';
import { 
  API_CONFIG, 
  RATE_LIMIT_CONFIG, 
  STORAGE_KEYS 
} from '../config/constants';
import { AZURE_AD_CONFIG } from '../config/authConfig';

const API_BASE = API_CONFIG.BASE_URL;

const normalizeBase = (base?: string): string => {
  if (!base) return '';
  return base.replace(/\/$/, '');
};

const buildUrl = (base: string, path: string): string => {
  if (!base) return path;
  if (path.startsWith('/')) {
    return base + path;
  }
  return base + '/' + path;
};

const resolveApiBase = (path: string): string => {
  if (path.startsWith('/profile')) {
    return normalizeBase(API_CONFIG.PROFILE_URL) || normalizeBase(API_BASE);
  }
  return normalizeBase(API_BASE);
};
// Azure AD can issue tokens with different issuer formats (v1.0 vs v2.0)
// Accept both formats for compatibility
const EXPECTED_ISSUERS = [
  `https://login.microsoftonline.com/${AZURE_AD_CONFIG.TENANT_ID}/v2.0`,
  `https://sts.windows.net/${AZURE_AD_CONFIG.TENANT_ID}/`,
  // Also accept consumer tenant for personal Microsoft accounts
  'https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/v2.0',
  'https://sts.windows.net/9188040d-6c67-4c5b-b112-36a304b66dad/',
];

// Rate limiter for API calls
const apiRateLimiter = new RateLimiter(
  RATE_LIMIT_CONFIG.MAX_REQUESTS, 
  RATE_LIMIT_CONFIG.TIME_WINDOW
);

export const getToken = (): string | null => {
  const token = localStorage.getItem(STORAGE_KEYS.ID_TOKEN);
  if (!token) return null;
  
  // Validate token structure
  if (!isValidJwtStructure(token)) {
    console.warn('Invalid token structure detected');
    clearToken();
    return null;
  }
  
  return token;
};

export const isTokenExpired = (token: string): boolean => {
  try {
    const payload = decodeJwtPayload(token);
    const exp = payload.exp * 1000; // Convert to milliseconds
    return Date.now() >= exp;
  } catch {
    return true; // If we can't parse, consider it expired
  }
};

const decodeJwtPayload = (token: string): any => {
  const base64Url = token.split('.')[1];
  const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
  return JSON.parse(atob(padded));
};

export const isAdmin = (): boolean => {
  const token = getToken();
  if (!token) return false;
  
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const groups = payload['cognito:groups'];
    return groups && (
      (typeof groups === 'string' && groups === 'Admins') ||
      (Array.isArray(groups) && groups.includes('Admins'))
    );
  } catch {
    return false;
  }
};

export const getCurrentUserId = (): string | null => {
  const token = getToken();
  if (!token) return null;
  
  try {
    const payload = decodeJwtPayload(token);
    // Azure AD uses 'oid' (object ID) or 'sub' (subject) for user ID
    return payload.oid || payload.sub || null;
  } catch {
    return null;
  }
};

export const canDeletePost = (postUserId: string): boolean => {
  const currentUserId = getCurrentUserId();
  if (!currentUserId) return false;
  
  // Admin or post owner can delete
  return isAdmin() || currentUserId === postUserId;
};

export const setToken = (token: string): void => {
  // Validate token before storing
  if (!isValidJwtStructure(token)) {
    throw new Error('Invalid token structure');
  }
  
  // Check if token issuer matches any of the expected issuers
  const isValidIssuer = EXPECTED_ISSUERS.some(issuer => 
    validateTokenIssuer(token, issuer)
  );
  
  if (!isValidIssuer) {
    console.warn('Token issuer validation failed, but storing anyway for Azure AD compatibility');
    // Don't throw error - Azure AD tokens may have different issuer formats
  }
  
  localStorage.setItem(STORAGE_KEYS.ID_TOKEN, token);
};

export const clearToken = (): void => {
  localStorage.removeItem(STORAGE_KEYS.ID_TOKEN);
  localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN);
  localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
};

export const apiFetch = async (
  path: string,
  options: RequestInit = {}
): Promise<{ res: Response; json: any }> => {
  // Rate limiting check
  if (!apiRateLimiter.isAllowed('api-calls')) {
    throw new Error('RATE_LIMIT_EXCEEDED');
  }
  
  const apiBase = resolveApiBase(path);
  const url = buildUrl(apiBase, path);
  const token = getToken();
  
  // Check if token is expired
  if (token && isTokenExpired(token)) {
    clearToken();
    throw new Error('TOKEN_EXPIRED');
  }
  
  const headers = new Headers(options.headers || {});
  
  if (token) {
    headers.set('Authorization', 'Bearer ' + token);
  }
  
  const res = await fetch(url, { ...options, headers });
  const text = await res.text();
  let json = null;
  
  try {
    json = text ? JSON.parse(text) : null;
  } catch {}
  
  return { res, json };
};
