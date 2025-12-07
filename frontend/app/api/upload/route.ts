import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.INTERNAL_API_URL;

export async function POST(request: NextRequest) {
  try {
    // Get the authorization header if present
    const authHeader = request.headers.get('authorization');

    // Get the access code header for legacy auth (backward compatibility)
    const accessCodeHeader = request.headers.get('X-Access-Code');

    // Get the FormData from the request
    const formData = await request.formData();

    // Forward the request to the backend
    const headers: HeadersInit = {};
    if (authHeader) {
      headers['Authorization'] = authHeader;
    }
    if (accessCodeHeader) {
      headers['X-Access-Code'] = accessCodeHeader;
    }

    const response = await fetch(`${API_URL}/api/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    // Try to parse as JSON first (backend returns JSON for both success and error)
    let data;
    try {
      data = await response.json();
    } catch {
      // If JSON parsing fails, return a generic error
      return NextResponse.json(
        { success: false, error: 'Invalid response from backend' },
        { status: 500 }
      );
    }

    // Return the response with original status code and JSON body
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Upload proxy error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
