/**
 * Authentication utilities for Notion OAuth integration.
 *
 * This module handles JWT session tokens and license keys stored in localStorage.
 * Tokens are obtained after successful Notion OAuth authentication.
 *
 * Note: User info is managed by AuthContext (frontend/contexts/AuthContext.tsx),
 * not cached in localStorage.
 */

const TOKEN_KEY = 'notes2notion_session_token';
const LICENSE_KEY = 'notes2notion_license_key';

/**
 * Get the current session token from localStorage
 */
export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Store session token in localStorage
 */
export function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Remove session token from localStorage
 */
export function clearToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Check if user is authenticated (has valid session token)
 */
export function isAuthenticated(): boolean {
  return getToken() !== null;
}

/**
 * Update user's default Notion page ID
 */
export async function updatePageId(pageId: string): Promise<boolean> {
  const token = getToken();
  if (!token) {
    return false;
  }

  try {
    // Use relative URL to call Next.js API proxy instead of direct backend call
    const response = await fetch('/api/user/page-id', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ page_id: pageId }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error('updatePageId: Failed with error:', errorData);
      return false;
    }

    const result = await response.json();

    // Note: User info refresh is handled by AuthContext.refreshUser()
    return true;
  } catch (error) {
    console.error('Failed to update page ID:', error);
    return false;
  }
}

/**
 * Get stored license key
 */
export function getLicenseKey(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(LICENSE_KEY);
}

/**
 * Store license key
 */
export function setLicenseKey(licenseKey: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(LICENSE_KEY, licenseKey.trim().toUpperCase());
}

/**
 * Clear license key
 */
export function clearLicenseKey(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(LICENSE_KEY);
}

/**
 * Check if user has valid license
 */
export function hasLicense(): boolean {
  return getLicenseKey() !== null;
}

/**
 * Logout: clear all stored auth data (token + license)
 */
export function logout(): void {
  clearToken();
  clearLicenseKey();
}
