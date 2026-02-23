/**
 * Auth provider config — injected at build time via VITE_AUTH_PROVIDER.
 *
 * AWS  : Cognito PKCE authorization code flow  (response_type=code)
 * Azure: Azure AD implicit flow (response_type=id_token, fragment #id_token=…)
 * Firebase: Firebase SDK Google Sign-In (popup)
 */

export type AuthProvider = "aws" | "azure" | "firebase" | "none";

const PROVIDER = (import.meta.env.VITE_AUTH_PROVIDER as AuthProvider) || "none";

/* ---- Cognito (AWS) ---- */
export const COGNITO_DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN || "";
export const COGNITO_CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID || "";
// VITE_COGNITO_REDIRECT_URI / VITE_COGNITO_LOGOUT_URI はフォールバック用。
// 実行時は window.location.origin を使い、アクセス元ドメイン（CloudFront or カスタムドメイン）
// に合わせた redirect_uri を動的に生成する。
const COGNITO_REDIRECT_FALLBACK =
  import.meta.env.VITE_COGNITO_REDIRECT_URI || "";
const COGNITO_LOGOUT_FALLBACK = import.meta.env.VITE_COGNITO_LOGOUT_URI || "";

// ========================================
// PKCE (Proof Key for Code Exchange) helpers
// ========================================
function base64urlEncode(buffer: Uint8Array): string {
  return btoa(String.fromCharCode(...Array.from(buffer)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
}

function generateCodeVerifier(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return base64urlEncode(array);
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return base64urlEncode(new Uint8Array(digest));
}

const PKCE_VERIFIER_KEY = "pkce_code_verifier";

function cognitoRedirectUri(): string {
  if (typeof window !== "undefined") {
    return `${window.location.origin}/sns/auth/callback`;
  }
  return COGNITO_REDIRECT_FALLBACK;
}

function cognitoLogoutUri(): string {
  if (typeof window !== "undefined") {
    return `${window.location.origin}/sns/`;
  }
  return COGNITO_LOGOUT_FALLBACK;
}

/* ---- Azure AD ---- */
const AZURE_TENANT = import.meta.env.VITE_AZURE_TENANT_ID || "";
const AZURE_CLIENT = import.meta.env.VITE_AZURE_CLIENT_ID || "";
const AZURE_REDIRECT = import.meta.env.VITE_AZURE_REDIRECT_URI || "";
const AZURE_LOGOUT = import.meta.env.VITE_AZURE_LOGOUT_URI || "";

/* ---- Firebase ---- */
export const FIREBASE_CONFIG = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "",
};

const SCOPE = "openid+email+profile";

/* ---- Derived URLs ---- */
export async function getLoginUrl(): Promise<string> {
  if (PROVIDER === "aws" && COGNITO_DOMAIN && COGNITO_CLIENT_ID) {
    const verifier = generateCodeVerifier();
    const challenge = await generateCodeChallenge(verifier);
    sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
    const redirectUri = encodeURIComponent(cognitoRedirectUri());
    return (
      `https://${COGNITO_DOMAIN}/oauth2/authorize` +
      `?client_id=${COGNITO_CLIENT_ID}` +
      `&response_type=code` +
      `&scope=${SCOPE}` +
      `&redirect_uri=${redirectUri}` +
      `&code_challenge=${challenge}` +
      `&code_challenge_method=S256`
    );
  }
  if (PROVIDER === "azure" && AZURE_TENANT && AZURE_CLIENT) {
    return (
      `https://login.microsoftonline.com/${AZURE_TENANT}/oauth2/v2.0/authorize` +
      `?client_id=${AZURE_CLIENT}` +
      `&response_type=id_token` +
      `&response_mode=fragment` +
      `&scope=${SCOPE}` +
      `&redirect_uri=${AZURE_REDIRECT}` +
      `&nonce=${Math.random().toString(36).slice(2)}`
    );
  }
  // firebase → handled in LoginPage via SDK
  return "";
}

export function getLogoutUrl(postLogoutUri: string): string {
  if (PROVIDER === "aws" && COGNITO_DOMAIN && COGNITO_CLIENT_ID) {
    const logoutUri = encodeURIComponent(cognitoLogoutUri());
    return (
      `https://${COGNITO_DOMAIN}/logout` +
      `?client_id=${COGNITO_CLIENT_ID}` +
      `&logout_uri=${logoutUri}`
    );
  }
  if (PROVIDER === "azure" && AZURE_TENANT) {
    const post = AZURE_LOGOUT || postLogoutUri;
    return (
      `https://login.microsoftonline.com/${AZURE_TENANT}/oauth2/v2.0/logout` +
      `?post_logout_redirect_uri=${post}`
    );
  }
  return postLogoutUri;
}

export const authProvider: AuthProvider = PROVIDER;
export const isFirebase = PROVIDER === "firebase";

// ========================================
// PKCE トークン交換 (authorization code → tokens)
// Cognito /oauth2/token エンドポイントでコードをトークンに交換する
// ========================================
export interface TokenResult {
  idToken?: string;
  accessToken?: string;
  expiresIn: number;
}

export async function getTokenFromCode(code: string): Promise<TokenResult> {
  if (!COGNITO_DOMAIN || !COGNITO_CLIENT_ID) {
    throw new Error("Cognito configuration missing");
  }

  const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
  if (!verifier)
    throw new Error("PKCE code_verifier not found in sessionStorage");
  sessionStorage.removeItem(PKCE_VERIFIER_KEY);

  const params = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: COGNITO_CLIENT_ID,
    code,
    redirect_uri: cognitoRedirectUri(),
    code_verifier: verifier,
  });

  const res = await fetch(`https://${COGNITO_DOMAIN}/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: params.toString(),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`Token exchange failed (${res.status}): ${errText}`);
  }

  const json = await res.json();
  return {
    idToken: json.id_token,
    accessToken: json.access_token,
    expiresIn: json.expires_in ?? 3600,
  };
}
