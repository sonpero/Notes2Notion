/**
 * OAuth Callback Route for Notion Authentication
 *
 * This Next.js API route handles the OAuth callback from Notion.
 * It receives the authorization code, exchanges it for a session token,
 * and redirects the user back to the home page.
 */

import { NextRequest, NextResponse } from 'next/server';

// Force dynamic rendering - do not prerender this route at build time
export const dynamic = 'force-dynamic';

// Use internal Docker service name for server-side API calls
// NEXT_PUBLIC_API_URL is for client-side calls only
const API_URL = process.env.INTERNAL_API_URL;

// Frontend public URL for OAuth redirects
// Required environment variable - must be set in production and local environments
const FRONTEND_URL = process.env.FRONTEND_URL;

export async function GET(request: NextRequest) {
  try {
    // Validate FRONTEND_URL is set
    if (!FRONTEND_URL) {
      console.error('FRONTEND_URL environment variable is not set');
      throw new Error('FRONTEND_URL environment variable is required');
    }

    // Extract authorization code from URL parameters
    const searchParams = request.nextUrl.searchParams;
    const code = searchParams.get('code');
    const state = searchParams.get('state');  // NEW: Get state parameter
    const error = searchParams.get('error');

    // Check if user denied authorization
    if (error) {
      console.error('OAuth error:', error);
      return NextResponse.redirect(
        new URL(`/?error=${encodeURIComponent(error)}`, FRONTEND_URL)
      );
    }

    // Validate that we received a code
    if (!code) {
      console.error('No authorization code received');
      return NextResponse.redirect(
        new URL('/?error=no_code', FRONTEND_URL)
      );
    }

    // NEW: Decode license key from state parameter
    let licenseKey = null;
    if (state) {
      try {
        const decoded = JSON.parse(atob(state));
        licenseKey = decoded.license;
      } catch (e) {
        console.error('Failed to decode state:', e);
      }
    }

    // Exchange authorization code for session token
    // NEW: Include license_key in the request
    const response = await fetch(`${API_URL}/api/oauth/callback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        code,
        license_key: licenseKey  // NEW: Pass license key to backend
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      console.error('Token exchange failed:', errorData);
      // Use message if available, otherwise use error field
      const errorMessage = errorData.message || errorData.error || 'OAuth authentication failed';
      return NextResponse.redirect(
        new URL(`/?error=${encodeURIComponent(errorMessage)}`, FRONTEND_URL)
      );
    }

    const data = await response.json();
    const { session_token, workspace_name, needs_page_setup } = data;

    // Create redirect URL with token in URL fragment (will be extracted by client-side JS)
    // We use URL fragment (#) because it's not sent to the server and is more secure
    const redirectUrl = new URL('/', FRONTEND_URL);
    redirectUrl.hash = `token=${session_token}&workspace=${encodeURIComponent(workspace_name)}&needs_setup=${needs_page_setup}`;

    return NextResponse.redirect(redirectUrl);
  } catch (error) {
    console.error('OAuth callback error:', error);
    return NextResponse.redirect(
      new URL('/?error=callback_failed', FRONTEND_URL)
    );
  }
}
