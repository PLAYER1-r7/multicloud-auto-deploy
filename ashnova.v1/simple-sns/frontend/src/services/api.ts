import { isValidJwtStructure, validateTokenIssuer, RateLimiter } from '../utils/security';

const API_BASE = import.meta.env.VITE_API_BASE || 
  'https://1y5w2smpb4.execute-api.ap-northeast-1.amazonaws.com/prod';
const PROFILE_URL = import.meta.env.VITE_API_PROFILE_URL || '';

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
    return normalizeBase(PROFILE_URL) || normalizeBase(API_BASE);
  }
  return normalizeBase(API_BASE);
};

export const COGNITO_DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN || 
  'https://simple-sns-2026-kr070001.auth.ap-northeast-1.amazoncognito.com';

const COGNITO_REGION = 'ap-northeast-1';
const COGNITO_USER_POOL_ID = 'ap-northeast-1_lLb8qq7Rq';
const EXPECTED_ISSUER = `https://cognito-idp.${COGNITO_REGION}.amazonaws.com/${COGNITO_USER_POOL_ID}`;

// Rate limiter for API calls (100 requests per minute)
const apiRateLimiter = new RateLimiter(100, 60000);

export const COGNITO_CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID || 
  '34t49tr84ufqq77flj8uspumck';

// 開発環境と本番環境で適切なREDIRECT_URIを設定
export const REDIRECT_URI = import.meta.env.VITE_REDIRECT_URI || window.location.origin + '/';

export const getToken = (): string | null => {
  const token = localStorage.getItem('id_token');
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
  
  localStorage.setItem('id_token', token);
};

export const clearToken = (): void => {
  localStorage.removeItem('id_token');
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
