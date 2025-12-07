"use client";

import { useState, useEffect } from "react";

interface LicenseKeyPromptProps {
  onLicenseValidated: () => void;
}

export default function LicenseKeyPrompt({ onLicenseValidated }: LicenseKeyPromptProps) {
  const [licenseKey, setLicenseKey] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [error, setError] = useState("");

  // Check if we already have a valid license key in localStorage
  useEffect(() => {
    const storedLicense = localStorage.getItem("notes2notion_license_key");
    if (storedLicense) {
      verifyLicenseKey(storedLicense, true);
    }
  }, []);

  const verifyLicenseKey = async (key: string, silent: boolean = false) => {
    if (!silent) {
      setIsVerifying(true);
      setError("");
    }

    try {
      // Use Next.js API route proxy instead of direct backend call
      const response = await fetch('/api/license/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ license_key: key }),
      });

      const data = await response.json();

      if (data.valid) {
        localStorage.setItem("notes2notion_license_key", key.trim().toUpperCase());
        onLicenseValidated();
      } else {
        if (!silent) {
          setError(data.message || "Clé de licence invalide");
        }
        localStorage.removeItem("notes2notion_license_key");
      }
    } catch (err) {
      console.error('License validation error:', err);
      if (!silent) {
        setError("Erreur de vérification de la licence");
      }
      localStorage.removeItem("notes2notion_license_key");
    } finally {
      if (!silent) {
        setIsVerifying(false);
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!licenseKey.trim()) {
      setError("Veuillez entrer une clé de licence");
      return;
    }

    await verifyLicenseKey(licenseKey);
  };

  const formatLicenseKey = (value: string) => {
    // Auto-format as BETA-XXXX-XXXX-XXXX
    const cleaned = value.replace(/[^A-Z0-9]/gi, '').toUpperCase();
    const parts = [];

    if (cleaned.startsWith('BETA')) {
      parts.push('BETA');
      const rest = cleaned.substring(4);
      for (let i = 0; i < rest.length; i += 4) {
        parts.push(rest.substring(i, i + 4));
      }
    } else {
      for (let i = 0; i < cleaned.length; i += 4) {
        parts.push(cleaned.substring(i, i + 4));
      }
    }

    return parts.join('-');
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatLicenseKey(e.target.value);
    setLicenseKey(formatted);
  };

  const handleReset = () => {
    localStorage.removeItem("notes2notion_license_key");
    setLicenseKey("");
    setError("");
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-5 bg-gradient-to-br from-primary/10 to-secondary/10">
      <div className="bg-white rounded-3xl shadow-2xl p-8 max-w-md w-full">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">🔑</div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            Clé de licence BETA
          </h1>
          <p className="text-gray-600 text-sm">
            Entrez votre clé de licence pour accéder à Notes2Notion
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="licenseKey" className="block text-sm font-medium text-gray-700 mb-2">
              Clé de licence
            </label>
            <input
              id="licenseKey"
              type="text"
              value={licenseKey}
              onChange={handleInputChange}
              className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:ring-2 focus:ring-primary focus:border-transparent outline-none transition-all font-mono text-center"
              placeholder="BETA-XXXX-XXXX-XXXX"
              disabled={isVerifying}
              autoFocus
              maxLength={19}
            />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isVerifying || !licenseKey.trim()}
            className="w-full btn-gradient disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isVerifying ? (
              <>
                <span className="loading-spinner mr-2"></span>
                Vérification...
              </>
            ) : (
              <>
                <span className="mr-2">✓</span>
                Valider la licence
              </>
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-xs text-gray-500">
            Cette clé vous a été fournie lors de votre inscription à la BETA
          </p>
        </div>

        {/* Hidden reset button for development */}
        <button
          onClick={handleReset}
          className="mt-4 w-full text-xs text-gray-400 hover:text-gray-600 transition-colors"
        >
          Réinitialiser le code stocké
        </button>
      </div>
    </div>
  );
}
