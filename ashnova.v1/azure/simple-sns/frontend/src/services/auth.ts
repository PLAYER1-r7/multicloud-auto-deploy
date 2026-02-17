// Azure AD MSAL authentication
// MSAL handles all authentication flows, so this file is no longer needed
// Login/logout is now handled by useMsalAuth hook

// Kept for backward compatibility - these are now no-ops
// Actual authentication is handled by MSAL in App.tsx and useMsalAuth hook

export const login = async (): Promise<void> => {
  console.warn('auth.login() is deprecated. Use useMsalAuth hook instead.');
};

export const logout = (): void => {
  console.warn('auth.logout() is deprecated. Use useMsalAuth hook instead.');
};

// This function is no longer needed with MSAL as token exchange is handled automatically
export const exchangeCodeForToken = async (_code: string): Promise<void> => {
  // MSAL handles token exchange automatically via redirect handling
  return Promise.resolve();
};
