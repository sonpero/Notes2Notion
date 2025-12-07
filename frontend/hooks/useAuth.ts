import { useContext } from 'react';
import { AuthContext, AuthState, UserInfo } from '../contexts/AuthContext';

/**
 * Hook to access the authentication context
 * Returns the full AuthState including user, loading, error, and action functions
 */
export function useAuth(): AuthState {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}

/**
 * Hook that requires authentication
 * Returns the user info if authenticated, throws an error otherwise
 * Use this in components that should only be accessible to authenticated users
 */
export function useRequireAuth(): UserInfo {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    throw new Error('useRequireAuth called while still loading');
  }

  if (!user) {
    throw new Error('useRequireAuth called without authentication');
  }

  return user;
}
