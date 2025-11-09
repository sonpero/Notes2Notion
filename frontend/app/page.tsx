"use client";

import { useState, useEffect } from "react";
import CameraCapture from "@/components/CameraCapture";
import RefreshHandler from "@/components/RefreshHandler";
import AccessCodePrompt from "@/components/AccessCodePrompt";

export default function Home() {
  // Check if we're in development mode using custom env var
  // This can be controlled via APP_ENV in docker-compose.yml or .env file
  // NEXT_PUBLIC_* variables are available in the browser
  const isDevelopment = process.env.NEXT_PUBLIC_APP_ENV === 'development';
  const [testMode, setTestMode] = useState(false);
  const [hasAccess, setHasAccess] = useState(false);
  const [isCheckingAccess, setIsCheckingAccess] = useState(true);

  const [notionConnected, setNotionConnected] = useState(false);
  // Check if user already has a stored access code
  useEffect(() => {
    const storedCode = localStorage.getItem("notes2notion_access_code");
    if (storedCode) {
      setHasAccess(true);
    }
    setIsCheckingAccess(false);

    // Check Notion connection
    const token = localStorage.getItem("notion_access_token");
    if (token) setNotionConnected(true);
  }, []);

  const handleNotionLogin = () => {
    const clientId = process.env.NEXT_PUBLIC_NOTION_MCP_CLIENT_ID;
    const redirectUri = encodeURIComponent(`${window.location.origin}/notion/callback`);
    const state = crypto.randomUUID();
    localStorage.setItem("notion_oauth_state", state);

    const authUrl =
      `https://mcp.notion.com/authorize?response_type=code` +
      `&client_id=${clientId}` +
      `&redirect_uri=${redirectUri}` +
      `&state=${state}`;

    window.location.href = authUrl;
  };
  const handleRefresh = () => {
    window.location.reload();
  };

  const handleAccessGranted = () => {
    setHasAccess(true);
  };

  // Show loading state while checking for stored access code
  if (isCheckingAccess) {
    return null;
  }

  // Show access code prompt if user doesn't have access
  if (!hasAccess) {
    return <AccessCodePrompt onAccessGranted={handleAccessGranted} />;
  }

  // Show main application
  return (
    <main className="min-h-screen flex items-center justify-center p-5">
      <RefreshHandler />

      <div className="bg-white rounded-3xl shadow-2xl p-8 max-w-lg w-full relative">
        {/* Refresh button - top right corner */}
        <button
          onClick={handleRefresh}
          className="absolute top-4 right-4 p-2 rounded-full bg-gray-100 hover:bg-gray-200 transition-colors"
          aria-label="Rafraîchir"
          title="Rafraîchir l'application"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            className="w-5 h-5 text-gray-600"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99"
            />
          </svg>
        </button>

        <div className="text-center mb-6">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            📸 Notes2Notion
          </h1>
          <p className="text-gray-600 text-sm">
            Capturez vos notes manuscrites
          </p>
        </div>

        {/* Test Mode Toggle - Only in development */}
        {isDevelopment && (
          <div className="mb-6 p-4 bg-gray-50 rounded-xl">
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <span className="font-semibold text-gray-800">Mode Test</span>
                <p className="text-xs text-gray-600">
                  {testMode
                    ? "🧪 Aucun appel LLM (mock content)"
                    : "🚀 Appels LLM activés (production)"}
                </p>
              </div>
              <div className="relative">
                <input
                  type="checkbox"
                  checked={testMode}
                  onChange={(e) => setTestMode(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-14 h-8 bg-gray-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/30 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[4px] after:start-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all peer-checked:bg-primary"></div>
              </div>
            </label>
          </div>
        )}
        {!notionConnected && (
          <button
            onClick={handleNotionLogin}
            className="mb-4 w-full py-3 bg-black text-white rounded-xl"
          >
            Connect Notion
          </button>
        )}
        {/* Camera Capture Component */}
        {/* In production, testMode is always false */}
        <CameraCapture testMode={isDevelopment ? testMode : false} />

        {/* PWA Install Prompt Info */}
        <div className="mt-6 text-center text-xs text-gray-500">
          <p>💡 Installez cette app sur votre téléphone pour un accès rapide</p>
        </div>
      </div>
    </main>
  );
}
