import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { getLogoutUrl, authProvider } from "../config/auth";

// ---- Types ----
interface AuthState {
  /** Decoded JWT token string stored in localStorage */
  token: string | null;
  /** Whether the user is authenticated */
  isLoggedIn: boolean;
}

interface AuthContextValue extends AuthState {
  /** Save tokens returned from auth provider callback / Firebase SDK */
  setTokens: (params: {
    idToken?: string;
    accessToken?: string;
    expiresIn?: number;
  }) => void;
  /** Clear tokens and redirect to provider logout */
  logout: (currentOrigin: string) => void;
}

// ---- Context ----
const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY_ACCESS = "access_token";
const TOKEN_KEY_ID = "id_token";

function readToken(): string | null {
  return (
    localStorage.getItem(TOKEN_KEY_ACCESS) ||
    localStorage.getItem(TOKEN_KEY_ID) ||
    null
  );
}

// ---- Provider ----
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(readToken);

  // Stay in sync across tabs
  useEffect(() => {
    const onStorage = () => setToken(readToken());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const setTokens = useCallback(
    ({
      idToken,
      accessToken,
      expiresIn = 3600,
    }: {
      idToken?: string;
      accessToken?: string;
      expiresIn?: number;
    }) => {
      if (accessToken) {
        localStorage.setItem(TOKEN_KEY_ACCESS, accessToken);
        // Auto-clear after expiresIn seconds
        setTimeout(() => {
          localStorage.removeItem(TOKEN_KEY_ACCESS);
          setToken(readToken());
        }, expiresIn * 1000);
      }
      if (idToken) {
        localStorage.setItem(TOKEN_KEY_ID, idToken);
        if (!accessToken) {
          setTimeout(() => {
            localStorage.removeItem(TOKEN_KEY_ID);
            setToken(readToken());
          }, expiresIn * 1000);
        }
      }
      setToken(readToken());
    },
    [],
  );

  const logout = useCallback((currentOrigin: string) => {
    localStorage.removeItem(TOKEN_KEY_ACCESS);
    localStorage.removeItem(TOKEN_KEY_ID);
    setToken(null);

    // Firebase: no hosted logout URL; the SDK sign-out is handled in LoginPage
    if (authProvider === "firebase") {
      return;
    }

    const snsTop = `${currentOrigin}/sns/`;
    const logoutUrl = getLogoutUrl(snsTop);
    if (logoutUrl && logoutUrl !== snsTop) {
      window.location.href = logoutUrl;
    }
  }, []);

  const value = useMemo(
    () => ({
      token,
      isLoggedIn: Boolean(token),
      setTokens,
      logout,
    }),
    [token, setTokens, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---- Hook ----
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
