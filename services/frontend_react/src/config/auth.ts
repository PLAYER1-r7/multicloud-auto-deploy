/**
 * Auth provider config — injected at build time via VITE_AUTH_PROVIDER.
 *
 * AWS  : Cognito implicit flow  (response_type=token)
 * Azure: Azure AD implicit flow (response_type=id_token, fragment #id_token=…)
 * Firebase: Firebase SDK Google Sign-In (popup)
 */

export type AuthProvider = "aws" | "azure" | "firebase" | "none";

const PROVIDER = (import.meta.env.VITE_AUTH_PROVIDER as AuthProvider) || "none";

/* ---- Cognito (AWS) ---- */
const COGNITO_DOMAIN = import.meta.env.VITE_COGNITO_DOMAIN || "";
const COGNITO_CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID || "";
const COGNITO_REDIRECT = import.meta.env.VITE_COGNITO_REDIRECT_URI || "";
const COGNITO_LOGOUT = import.meta.env.VITE_COGNITO_LOGOUT_URI || "";

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
export function getLoginUrl(): string {
  if (PROVIDER === "aws" && COGNITO_DOMAIN && COGNITO_CLIENT_ID) {
    return (
      `https://${COGNITO_DOMAIN}/login` +
      `?client_id=${COGNITO_CLIENT_ID}` +
      `&response_type=token` +
      `&scope=${SCOPE}` +
      `&redirect_uri=${COGNITO_REDIRECT}`
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
  if (
    PROVIDER === "aws" &&
    COGNITO_DOMAIN &&
    COGNITO_CLIENT_ID &&
    COGNITO_LOGOUT
  ) {
    return (
      `https://${COGNITO_DOMAIN}/logout` +
      `?client_id=${COGNITO_CLIENT_ID}` +
      `&logout_uri=${COGNITO_LOGOUT}`
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
