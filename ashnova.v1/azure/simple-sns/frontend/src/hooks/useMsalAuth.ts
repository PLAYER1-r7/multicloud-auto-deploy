import { useMsal } from '@azure/msal-react';
import { InteractionStatus } from '@azure/msal-browser';
import { loginRequest } from '../config/authConfig';

// リダイレクト中フラグ（グローバルで管理）
let isRedirecting = false;

export const useMsalAuth = () => {
  const { instance, accounts, inProgress } = useMsal();
  
  const isAuthenticated = accounts.length > 0;
  const account = accounts[0];
  
  const login = async () => {
    if (inProgress === InteractionStatus.None) {
      try {
        // リダイレクト方式に変更（ポップアップよりも安定）
        await instance.loginRedirect({
          ...loginRequest,
          prompt: 'select_account',
        });
      } catch (error) {
        console.error('Login failed:', error);
        throw error;
      }
    }
  };
  
  const logout = async () => {
    if (inProgress !== InteractionStatus.None) {
      console.warn('Cannot logout while another operation is in progress');
      return;
    }
    
    try {
      // リダイレクト方式に変更
      await instance.logoutRedirect({
        postLogoutRedirectUri: window.location.origin,
      });
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };
  
  const getAccessToken = async (): Promise<string | null> => {
    if (!account) return null;
    
    // MSALの処理中は待つ
    if (inProgress !== InteractionStatus.None) {
      return null;
    }
    
    try {
      // まず、キャッシュからトークンを取得
      const response = await instance.acquireTokenSilent({
        scopes: loginRequest.scopes,
        account,
        forceRefresh: false,
      });
      
      if (response) {
        if (response.idToken) {
          console.log('✓ Token acquired via MSAL (cached)');
          return response.idToken;
        }
        // Fallback: explicitly request idToken only
        const idTokenResponse = await instance.acquireTokenSilent({
          scopes: ['openid', 'profile', 'email'],
          account,
          forceRefresh: false,
        });
        if (idTokenResponse?.idToken) {
          console.log('✓ ID token acquired via silent');
          return idTokenResponse.idToken;
        }
      }
    } catch (error: any) {
      // バリデーションエラーの場合、強制的に新しいトークンを取得
      console.log('MSAL validation error, forcing refresh:', error.message);
      
      try {
        const refreshResponse = await instance.acquireTokenSilent({
          scopes: loginRequest.scopes,
          account,
          forceRefresh: true,  // 強制的に新しいトークンを取得
        });
        
        if (refreshResponse) {
          if (refreshResponse.idToken) {
            console.log('✓ Token acquired via force refresh');
            return refreshResponse.idToken;
          }
          const idTokenResponse = await instance.acquireTokenSilent({
            scopes: ['openid', 'profile', 'email'],
            account,
            forceRefresh: true,
          });
          if (idTokenResponse?.idToken) {
            console.log('✓ ID token acquired via force refresh');
            return idTokenResponse.idToken;
          }
        }
      } catch (refreshError: any) {
        console.log('Force refresh also failed:', refreshError.message);
      }
    }
    
    return null;
  };
  
  const getUserId = (): string | null => {
    return account?.localAccountId || account?.homeAccountId || null;
  };
  
  const getUserEmail = (): string | null => {
    return account?.username || null;
  };
  
  const getUserName = (): string | null => {
    return account?.name || null;
  };
  
  return {
    isAuthenticated,
    account,
    login,
    logout,
    getAccessToken,
    getUserId,
    getUserEmail,
    getUserName,
    inProgress,
  };
};
