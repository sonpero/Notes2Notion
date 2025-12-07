"use client";

import { useState, useEffect, useRef } from 'react';
import { updatePageId, getToken } from '../lib/auth';

interface PageIdSetupProps {
  workspaceName: string;
  onComplete: () => void;
}

interface NotionPage {
  id: string;
  title: string;
  icon?: string;
  parent_type?: string;
  parent_id?: string;
  parent_title?: string;
}

// Extended interface to include depth level
interface NotionPageWithDepth extends NotionPage {
  depth?: number;
}

// Helper function to normalize Notion IDs (remove dashes for comparison)
const normalizeId = (notionId: string | undefined): string | null => {
  if (!notionId) return null;
  return notionId.replace(/-/g, '');
};

// Helper function to calculate page depth and sort by hierarchy
const sortPagesByHierarchy = (pages: NotionPage[]): NotionPageWithDepth[] => {
  // Create a map with normalized IDs for reliable lookup
  const pageMap = new Map(pages.map(p => [normalizeId(p.id), p]));
  const sorted: NotionPageWithDepth[] = [];
  const processed = new Set<string>();

  const addPageAndChildren = (page: NotionPage, depth: number = 0) => {
    const normalizedPageId = normalizeId(page.id);
    if (!normalizedPageId || processed.has(normalizedPageId)) return;

    sorted.push({ ...page, depth });
    processed.add(normalizedPageId);

    // Find and add children with increased depth using normalized IDs
    const normalizedParentId = normalizeId(page.id);
    pages
      .filter(p => normalizeId(p.parent_id) === normalizedParentId)
      .forEach(child => addPageAndChildren(child, depth + 1));
  };

  // First add root level pages (workspace or database parents)
  pages
    .filter(p => p.parent_type !== 'page_id')
    .forEach(page => addPageAndChildren(page, 0));

  // Then add any remaining pages (in case of missing parents)
  pages
    .filter(p => {
      const normalizedId = normalizeId(p.id);
      return normalizedId && !processed.has(normalizedId);
    })
    .forEach(page => addPageAndChildren(page, 0));

  return sorted;
};

export default function PageIdSetup({ workspaceName, onComplete }: PageIdSetupProps) {
  const [pages, setPages] = useState<NotionPageWithDepth[]>([]);
  const [filteredPages, setFilteredPages] = useState<NotionPageWithDepth[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedPage, setSelectedPage] = useState<NotionPage | null>(null);
  const [isLoadingPages, setIsLoadingPages] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Load pages on mount
  useEffect(() => {
    loadPages();
  }, []);

  // Filter pages based on search query
  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredPages(pages);
    } else {
      const query = searchQuery.toLowerCase();
      setFilteredPages(
        pages.filter(page =>
          page.title.toLowerCase().includes(query)
        )
      );
    }
  }, [searchQuery, pages]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const loadPages = async () => {
    setIsLoadingPages(true);
    setError(null);

    try {
      const token = getToken();
      if (!token) {
        setError('Session expirée. Veuillez vous reconnecter.');
        return;
      }

      const response = await fetch('/api/notion/search', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: '' }),
      });

      if (!response.ok) {
        throw new Error('Échec du chargement des pages');
      }

      const data = await response.json();
      const sortedPages = sortPagesByHierarchy(data.pages || []);
      setPages(sortedPages);
      setFilteredPages(sortedPages);
    } catch (err) {
      console.error('Error loading pages:', err);
      setError('Impossible de charger vos pages Notion. Veuillez réessayer.');
    } finally {
      setIsLoadingPages(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedPage) {
      setError('Veuillez sélectionner une page');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const success = await updatePageId(selectedPage.id);

      if (success) {
        // Let parent handle the refresh (will reload the page)
        onComplete();
      } else {
        setError('Échec de la configuration de la page. Veuillez réessayer.');
      }
    } catch (err) {
      console.error('Error in handleSubmit:', err);
      setError('Une erreur s\'est produite. Veuillez réessayer.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePageSelect = (page: NotionPage) => {
    setSelectedPage(page);
    setSearchQuery(page.title);
    setIsDropdownOpen(false);
    setError(null);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Configurer la page par défaut
          </h2>
          <p className="text-gray-600">
            Connecté à : <span className="font-semibold">{workspaceName}</span>
          </p>
        </div>

        <div className="mb-6">
          <p className="text-gray-700 mb-4">
            Sélectionnez la page Notion où vos notes manuscrites seront créées.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Page Selector */}
          <div className="mb-6 relative" ref={dropdownRef}>
            <label htmlFor="pageSearch" className="block text-sm font-medium text-gray-700 mb-2">
              Rechercher et sélectionner une page
            </label>

            <div className="relative">
              <input
                type="text"
                id="pageSearch"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setIsDropdownOpen(true);
                }}
                onFocus={() => setIsDropdownOpen(true)}
                placeholder={isLoadingPages ? "Chargement des pages..." : "Tapez pour rechercher une page..."}
                className="w-full px-4 py-3 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent"
                disabled={isLoadingPages || isSubmitting}
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                {isLoadingPages ? (
                  <svg className="animate-spin h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                )}
              </div>
            </div>

            {/* Dropdown */}
            {isDropdownOpen && !isLoadingPages && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-auto">
                {filteredPages.length === 0 ? (
                  <div className="px-4 py-6 text-center">
                    <p className="text-sm text-gray-600 mb-3">
                      {searchQuery ? 'Aucune page trouvée' : 'Aucune page accessible'}
                    </p>
                    {!searchQuery && pages.length === 0 && (
                      <div className="text-xs text-gray-500">
                        <p className="mb-3">
                          Vous n'avez partagé aucune page avec Notes2Notion lors de la connexion.
                        </p>
                        <button
                          onClick={() => {
                            const clientId = process.env.NEXT_PUBLIC_NOTION_CLIENT_ID;
                            const redirectUri = process.env.NEXT_PUBLIC_NOTION_REDIRECT_URI;

                            if (clientId && redirectUri) {
                              const authUrl = new URL('https://api.notion.com/v1/oauth/authorize');
                              authUrl.searchParams.set('client_id', clientId);
                              authUrl.searchParams.set('response_type', 'code');
                              authUrl.searchParams.set('owner', 'user');
                              authUrl.searchParams.set('redirect_uri', redirectUri);

                              window.location.href = authUrl.toString();
                            }
                          }}
                          className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors text-sm"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                          Partager une page avec Notes2Notion
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  filteredPages.map((page) => {
                    const depth = page.depth || 0;
                    const indentationPx = depth * 20; // 20px per level

                    return (
                      <button
                        key={page.id}
                        type="button"
                        onClick={() => handlePageSelect(page)}
                        className={`w-full py-3 text-left hover:bg-gray-50 flex items-center gap-2 transition-colors ${
                          selectedPage?.id === page.id ? 'bg-gray-100' : ''
                        }`}
                        style={{ paddingLeft: `${16 + indentationPx}px`, paddingRight: '16px' }}
                      >
                        {/* Visual hierarchy indicator */}
                        {depth > 0 && (
                          <div className="flex items-center gap-1 flex-shrink-0">
                            <span className="text-gray-300">
                              {'│ '.repeat(depth - 1)}
                            </span>
                            <span className="text-gray-400">└─</span>
                          </div>
                        )}

                        {page.icon && (
                          <span className="text-lg flex-shrink-0">{page.icon}</span>
                        )}

                        <div className="flex-1 min-w-0">
                          <span className={`block truncate ${depth === 0 ? 'text-sm font-medium text-gray-900' : 'text-sm text-gray-700'}`}>
                            {page.title}
                          </span>
                          {page.parent_title && depth > 0 && (
                            <span className="block truncate text-xs text-gray-400 mt-0.5">
                              dans: {page.parent_title}
                            </span>
                          )}
                        </div>

                        {selectedPage?.id === page.id && (
                          <svg className="h-5 w-5 text-black flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </button>
                    );
                  })
                )}
              </div>
            )}
          </div>

          {/* Selected Page Preview */}
          {selectedPage && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm text-green-800 mb-1 font-medium">Page sélectionnée :</p>
              <div className="flex items-center gap-2">
                {selectedPage.icon && (
                  <span className="text-xl">{selectedPage.icon}</span>
                )}
                <span className="text-sm text-green-900 font-semibold">{selectedPage.title}</span>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting || !selectedPage || isLoadingPages}
            className="w-full bg-black text-white py-3 px-6 rounded-lg font-medium hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? 'Enregistrement...' : 'Continuer'}
          </button>
        </form>

        <p className="mt-4 text-xs text-gray-500 text-center">
          Vous pourrez modifier ceci plus tard dans les paramètres de votre compte
        </p>
      </div>
    </div>
  );
}
