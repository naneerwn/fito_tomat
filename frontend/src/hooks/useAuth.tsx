import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import { AuthUser } from '../types/user';

type AuthContextValue = {
  user: AuthUser | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearAuthState = useCallback(() => {
    localStorage.removeItem('access');
    localStorage.removeItem('refresh');
    localStorage.removeItem('fd-user');
    setUser(null);
  }, []);

  const logout = useCallback(() => {
    clearAuthState();
    window.location.href = '/login';
  }, [clearAuthState]);

  const fetchProfile = useCallback(async () => {
    try {
      const { data } = await api.get('/users/me/');
      if (data) {
        setUser(data);
        localStorage.setItem('fd-user', JSON.stringify(data));
      }
    } catch {
      clearAuthState();
    } finally {
      setIsLoading(false);
    }
  }, [clearAuthState]);

  useEffect(() => {
    const cached = localStorage.getItem('fd-user');
    if (cached) {
      setUser(JSON.parse(cached));
    }

    const token = localStorage.getItem('access');
    if (token) {
      fetchProfile();
    } else {
      setIsLoading(false);
    }
  }, [fetchProfile]);

  const login = useCallback(
    async (username: string, password: string) => {
      setIsLoading(true);
      try {
        const { data } = await api.post('/auth/token/', { username, password });
        localStorage.setItem('access', data.access);
        localStorage.setItem('refresh', data.refresh);
        await fetchProfile();
      } catch (error) {
        clearAuthState();
        setIsLoading(false);
        throw error;
      }
    },
    [clearAuthState, fetchProfile],
  );

  const value = useMemo(
    () => ({
      user,
      isLoading,
      login,
      logout,
    }),
    [isLoading, login, logout, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}

