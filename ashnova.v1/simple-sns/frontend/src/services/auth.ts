import { COGNITO_DOMAIN, COGNITO_CLIENT_ID, REDIRECT_URI, setToken, clearToken } from './api';

const b64url = (bytes: Uint8Array): string => {
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
};

const sha256 = async (str: string): Promise<Uint8Array> => {
  const buf = new TextEncoder().encode(str);
  const digest = await crypto.subtle.digest('SHA-256', buf);
  return new Uint8Array(digest);
};

const randStr = (len = 64): string => {
  const a = new Uint8Array(len);
  crypto.getRandomValues(a);
  return b64url(a);
};

export const login = async (): Promise<void> => {
  const verifier = randStr(64);
  const challenge = b64url(await sha256(verifier));
  sessionStorage.setItem('pkce_verifier', verifier);

  const url = new URL(COGNITO_DOMAIN + '/oauth2/authorize');
  url.searchParams.set('response_type', 'code');
  url.searchParams.set('client_id', COGNITO_CLIENT_ID);
  url.searchParams.set('redirect_uri', REDIRECT_URI);
  url.searchParams.set('scope', 'openid email profile');
  url.searchParams.set('code_challenge_method', 'S256');
  url.searchParams.set('code_challenge', challenge);
  
  window.location.href = url.toString();
};

export const exchangeCodeForToken = async (code: string): Promise<void> => {
  const verifier = sessionStorage.getItem('pkce_verifier');
  if (!verifier) throw new Error('Missing PKCE verifier');

  const body = new URLSearchParams();
  body.set('grant_type', 'authorization_code');
  body.set('client_id', COGNITO_CLIENT_ID);
  body.set('code', code);
  body.set('redirect_uri', REDIRECT_URI);
  body.set('code_verifier', verifier);

  const res = await fetch(COGNITO_DOMAIN + '/oauth2/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });

  const json = await res.json();
  if (!res.ok) throw new Error(JSON.stringify(json));

  setToken(json.id_token);
  sessionStorage.removeItem('pkce_verifier');
};

export const logout = (): void => {
  clearToken();

  const url = new URL(COGNITO_DOMAIN + '/logout');
  url.searchParams.set('client_id', COGNITO_CLIENT_ID);
  url.searchParams.set('logout_uri', window.location.origin + '/');

  window.location.assign(url.toString());
};
