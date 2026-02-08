/**
 * Azure AD configuration for Simple-SNS
 * Supports Microsoft personal accounts, work/school accounts
 */

import { Configuration, PopupRequest } from '@azure/msal-browser';

// Azure AD settings
export const AZURE_AD_CONFIG = {
  TENANT_ID: import.meta.env.VITE_AZURE_AD_TENANT_ID || 'a3182bec-d835-4ce3-af06-04579abf597e',
  CLIENT_ID: import.meta.env.VITE_AZURE_AD_CLIENT_ID || '00433640-13d1-4482-aa1b-db5f039197bf',
  REDIRECT_URI: import.meta.env.VITE_REDIRECT_URI || window.location.origin,
} as const;

// MSAL configuration
export const msalConfig: Configuration = {
  auth: {
    clientId: AZURE_AD_CONFIG.CLIENT_ID,
    // Use v2.0 endpoint for modern tokens
    authority: `https://login.microsoftonline.com/${AZURE_AD_CONFIG.TENANT_ID}/v2.0`,
    redirectUri: AZURE_AD_CONFIG.REDIRECT_URI,
    postLogoutRedirectUri: AZURE_AD_CONFIG.REDIRECT_URI,
  },
  cache: {
    cacheLocation: 'localStorage',
  },
  system: {
    // Disable authority validation to allow both v1.0 and v2.0 tokens
    loggerOptions: {
      loggerCallback: (level: any, message: string, containsPii: boolean) => {
        if (containsPii) return;
        console.log(message);
      },
    },
  }
};

// Scopes for login request
export const loginRequest: PopupRequest = {
  scopes: ['User.Read', 'openid', 'profile', 'email'],
};

// Token request scopes
export const tokenRequest = {
  scopes: ['User.Read'],
};
