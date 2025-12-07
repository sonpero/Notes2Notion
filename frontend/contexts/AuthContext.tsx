"use client";

import React, { createContext, useState, useEffect, useRef, ReactNode } from 'react';
import { getToken, clearToken, clearLicenseKey } from '../lib/auth';

export interface UserInfo {
  workspace_name: string;
  has_page_id: boolean;
  bot_id: string;
}

export interface AuthState {
  user: UserInfo | null;
  isLoading: boolean;
  error: string | null;
  refreshUser: () => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthState | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const channel = useRef<BroadcastChannel | null>(null);

  // Fetch user info from backend
  const fetchUserInfo = async () => {
    const token = getToken();
    if (!token) {
      setIsLoading(false);
      setUser(null);
      return;
    }

    try {
      const response = await fetch('/api/user/info', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.status === 401) {
        // Token invalid or expired
        clearToken();
        setUser(null);
        setError('Session expirée. Veuillez vous reconnecter.');
        setIsLoading(false);
        return;
      }

      if (response.status === 403) {
        // License invalid
        setUser(null);
        setError('Licence invalide. Veuillez vérifier votre clé.');
        setIsLoading(false);
        return;
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const userInfo: UserInfo = await response.json();
      setUser(userInfo);
      setError(null);
      setIsLoading(false);
    } catch (err) {
      console.error('Failed to fetch user info:', err);

      // Distinguish network errors from other errors
      if (err instanceof TypeError && err.message.includes('fetch')) {
        setError('Impossible de se connecter au serveur. Vérifiez votre connexion internet.');
      } else {
        setError('Une erreur est survenue. Veuillez réessayer.');
      }

      setIsLoading(false);
    }
  };

  // Refresh user info manually
  const refreshUser = async () => {
    setIsLoading(true);
    setError(null);
    await fetchUserInfo();

    // Broadcast to other tabs
    if (channel.current) {
      channel.current.postMessage({ type: 'user_updated' });
    }
  };

  // Logout function
  const logout = () => {
    clearToken();
    clearLicenseKey();
    setUser(null);
    setError(null);

    // Broadcast to other tabs
    if (channel.current) {
      channel.current.postMessage({ type: 'logout' });
    }
  };

  // Setup BroadcastChannel for cross-tab sync
  useEffect(() => {
    // Only run in browser
    if (typeof window === 'undefined') return;

    try {
      channel.current = new BroadcastChannel('notes2notion_auth');

      channel.current.onmessage = (event) => {
        if (event.data.type === 'logout') {
          // Another tab logged out
          setUser(null);
          clearToken();
        } else if (event.data.type === 'user_updated') {
          // Another tab updated user data - refresh from API
          fetchUserInfo();
        }
      };
    } catch (err) {
      // BroadcastChannel not supported (graceful fallback)
    }

    return () => {
      if (channel.current) {
        channel.current.close();
      }
    };
  }, []);

  // Initial setup: clean old localStorage and fetch user if authenticated
  useEffect(() => {
    // Clean up old localStorage keys (migration)
    if (typeof window !== 'undefined') {
      localStorage.removeItem('notes2notion_user_info');
      localStorage.removeItem('notes2notion_needs_page_setup');
    }

    // Fetch user info if token exists
    fetchUserInfo();
  }, []);

  const value: AuthState = {
    user,
    isLoading,
    error,
    refreshUser,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
