import { isValidJwtStructure, validateTokenIssuer, RateLimiter } from '../utils/security';
import { 
  API_CONFIG, 
  COGNITO_CONFIG, 
  EXPECTED_ISSUER, 
  RATE_LIMIT_CONFIG, 
  STORAGE_KEYS 
} from '../config/constants';

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
export const COGNITO_DOMAIN = COGNITO_CONFIG.DOMAIN;
export const COGNITO_CLIENT_ID = COGNITO_CONFIG.CLIENT_ID;
export const REDIRECT_URI = COGNITO_CONFIG.REDIRECT_URI;

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
  
  // Validate token issuer
  if (!validateTokenIssuer(token, EXPECTED_ISSUER)) {
    console.warn('Invalid token issuer detected');
    clearToken();
    return null;
  }
  
  return token;
};

export const isTokenExpired = (token: string): boolean => {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000; // Convert to milliseconds
    return Date.now() >= exp;
  } catch {
    return true; // If we can't parse, consider it expired
  }
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
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.sub || null;
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
  
  if (!validateTokenIssuer(token, EXPECTED_ISSUER)) {
    throw new Error('Invalid token issuer');
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
