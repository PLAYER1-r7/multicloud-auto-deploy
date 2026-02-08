import { useState, useEffect } from 'react';
import {
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  setPersistence,
  browserLocalPersistence,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged,
  onIdTokenChanged,
  User,
} from 'firebase/auth';
import { auth } from '../config/firebase';
import { setToken, clearToken, getToken } from '../services/api';

export const useFirebaseAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string>('');

  useEffect(() => {
    setPersistence(auth, browserLocalPersistence).catch((error) => {
      console.error('Failed to set auth persistence:', error);
    });

    const handleAuthUser = async (user: User | null) => {
      setUser(user);
      if (user) {
        try {
          const token = await user.getIdToken();
          setToken(token);
        } catch (error) {
          console.error('Failed to cache token:', error);
          setAuthError('Failed to cache token');
          clearToken();
        }
      } else {
        clearToken();
      }
      setLoading(false);
    };

    const unsubscribeAuth = onAuthStateChanged(auth, handleAuthUser);
    const unsubscribeToken = onIdTokenChanged(auth, handleAuthUser);

    return () => {
      unsubscribeAuth();
      unsubscribeToken();
    };
  }, []);

  useEffect(() => {
    const handleRedirect = async () => {
      try {
        const result = await getRedirectResult(auth);
        if (result?.user) {
          setUser(result.user);
          try {
            const token = await result.user.getIdToken();
            setToken(token);
          } catch (error) {
            console.error('Failed to cache token after redirect:', error);
            setAuthError('Failed to cache token after redirect');
          }
          return;
        }

        if (auth.currentUser) {
          setUser(auth.currentUser);
          try {
            const token = await auth.currentUser.getIdToken();
            setToken(token);
          } catch (error) {
            console.error('Failed to cache token from current user:', error);
            setAuthError('Failed to cache token from current user');
          }
        }

        // Fallback: wait for auth state to settle after redirect
        const timeouts = [500, 1500, 3000];
        timeouts.forEach((delay) => {
          setTimeout(async () => {
            if (auth.currentUser) {
              setUser(auth.currentUser);
              try {
                const token = await auth.currentUser.getIdToken();
                setToken(token);
              } catch (error) {
                console.error('Failed to cache token in fallback:', error);
                setAuthError('Failed to cache token in fallback');
              }
            }
          }, delay);
        });
      } catch (error) {
        console.error('Redirect login failed:', error);
        setAuthError(`Redirect login failed: ${String(error)}`);
      }
    };

    handleRedirect();
  }, []);

  const login = async () => {
    const provider = new GoogleAuthProvider();
    try {
      await setPersistence(auth, browserLocalPersistence);
      const result = await signInWithPopup(auth, provider);
      if (result?.user) {
        setUser(result.user);
        try {
          const token = await result.user.getIdToken();
          setToken(token);
        } catch (error) {
          console.error('Failed to cache token after popup:', error);
          setAuthError(`Failed to cache token after popup: ${String(error)}`);
        }
        return;
      }
      await signInWithRedirect(auth, provider);
    } catch (error) {
      console.error('Popup login failed, falling back to redirect:', error);
      setAuthError(`Popup login failed: ${String(error)}`);
      try {
        await signInWithRedirect(auth, provider);
      } catch (redirectError) {
        console.error('Redirect login failed:', redirectError);
        setAuthError(`Redirect login failed: ${String(redirectError)}`);
      }
    }
  };

  const logout = async () => {
    try {
      await signOut(auth);
      clearToken();
    } catch (error) {
      console.error('Logout failed:', error);
      throw error;
    }
  };

  const getAccessToken = async (): Promise<string | null> => {
    if (!user) return null;
    try {
      const token = await user.getIdToken();
      setToken(token);
      return token;
    } catch (error) {
      console.error('Failed to get token:', error);
      return null;
    }
  };

  const isAuthenticated = !!user || !!getToken();

  return {
    user,
    loading,
    isAuthenticated,
    authError,
    // Backward compatible names
    login,
    logout,
    getAccessToken,
    // UI expected names
    signIn: login,
    signOut: logout,
    getIdToken: getAccessToken,
  };
};
