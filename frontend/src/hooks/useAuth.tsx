/**
 * useAuth.tsx — React context that manages JWT authentication state.
 *
 * Persists the JWT in localStorage under the key "orca_token".
 * Exposes a consistent interface for both authenticated users and guests.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  getMe,
  login as authLogin,
  logout as authLogout,
  register as authRegister,
  type LoginPayload,
  type RegisterPayload,
  type UserOut,
} from "@/services/authService";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuthState {
  user: UserOut | null;
  isAuthenticated: boolean;
  isGuest: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextValue | null>(null);

// ---------------------------------------------------------------------------
// Storage helpers
// ---------------------------------------------------------------------------

const TOKEN_KEY = "orca_token";

function storeToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function readToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount: try to restore the session from a stored token.
  useEffect(() => {
    const token = readToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    getMe()
      .then((u) => {
        setUser(u);
      })
      .catch(() => {
        // Token is invalid/expired — clear it so the user sees guest mode.
        clearToken();
        setUser(null);
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  const login = useCallback(async (payload: LoginPayload) => {
    const response = await authLogin(payload);
    storeToken(response.access_token);
    setUser(response.user);
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    const response = await authRegister(payload);
    storeToken(response.access_token);
    setUser(response.user);
  }, []);

  const logout = useCallback(async () => {
    await authLogout();
    clearToken();
    setUser(null);
  }, []);

  const value: AuthContextValue = {
    user,
    isAuthenticated: user !== null,
    isGuest: user === null,
    isLoading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within <AuthProvider>");
  }
  return ctx;
}
