import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.INTERNAL_API_URL;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(`${API_URL}/api/license/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('License validation proxy error:', error);
    return NextResponse.json(
      { valid: false, message: 'Erreur de validation' },
      { status: 500 }
    );
  }
}
