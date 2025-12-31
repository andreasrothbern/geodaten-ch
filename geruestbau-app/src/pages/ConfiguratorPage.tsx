/**
 * ConfiguratorPage - Entry point for Scaffold Configurator
 *
 * Flow:
 * 1. User enters address
 * 2. API fetches building data (polygon, facades, heights)
 * 3. ScaffoldConfigurator is rendered with the data
 */

import { useState, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, Building2, Loader2, AlertCircle } from 'lucide-react';
import AddressAutocomplete from '../components/ui/AddressAutocomplete';
import ScaffoldConfigurator from '../features/scaffold-configurator/components/ScaffoldConfigurator';
import type { SelectedFacade } from '../features/scaffold-configurator/types/scaffold.types';

// API Base URL - use environment variable or default
const API_BASE = import.meta.env.VITE_API_URL || 'https://acceptable-trust-production.up.railway.app';

interface BuildingData {
  project_id: string;
  building: {
    egid: string;
    address: string;
    name: string;
    polygon: [number, number][];
    trauf_height_m: number;
    first_height_m: number;
    center_e: number;
    center_n: number;
  };
  selected_facades: Array<{
    id: string;
    direction: string;
    length_m: number;
    height_m: number;
    slope_percent: number;
    start_point: [number, number];
    end_point: [number, number];
  }>;
  metadata: {
    source: string;
    polygon_points: number;
    facade_count: number;
    perimeter_m: number;
    area_m2: number;
    roof_type: string | null;
    roof_surfaces_count: number;
    height_source: string;
    confidence: number;
  };
}

type LoadingState = 'idle' | 'loading' | 'success' | 'error';

export default function ConfiguratorPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // State
  const [address, setAddress] = useState(searchParams.get('address') || '');
  const [loadingState, setLoadingState] = useState<LoadingState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [buildingData, setBuildingData] = useState<BuildingData | null>(null);

  // Fetch building data from API
  const fetchBuildingData = useCallback(async (selectedAddress: string) => {
    setLoadingState('loading');
    setError(null);

    try {
      const params = new URLSearchParams({
        address: selectedAddress,
        include_roof: 'true',
      });

      const response = await fetch(`${API_BASE}/api/v1/geruestbau/configurator/facades?${params}`);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data: BuildingData = await response.json();
      setBuildingData(data);
      setLoadingState('success');

      // Update URL with address for sharing
      const newUrl = new URL(window.location.href);
      newUrl.searchParams.set('address', selectedAddress);
      window.history.replaceState({}, '', newUrl.toString());

    } catch (err) {
      console.error('Error fetching building data:', err);
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
      setLoadingState('error');
    }
  }, []);

  // Handle address selection from autocomplete
  const handleAddressSelect = useCallback((suggestion: { label: string }) => {
    setAddress(suggestion.label);
    fetchBuildingData(suggestion.label);
  }, [fetchBuildingData]);

  // Handle manual search (Enter key or button)
  const handleSearch = useCallback(() => {
    if (address.length >= 5) {
      fetchBuildingData(address);
    }
  }, [address, fetchBuildingData]);

  // Convert API response to SelectedFacade format
  const convertToSelectedFacades = (data: BuildingData): SelectedFacade[] => {
    return data.selected_facades.map((facade) => ({
      id: facade.id,
      direction: facade.direction as SelectedFacade['direction'],
      length_m: facade.length_m,
      height_m: facade.height_m,
      slope_percent: facade.slope_percent,
    }));
  };

  // Render address search form
  if (loadingState !== 'success' || !buildingData) {
    return (
      <div className="min-h-screen bg-gray-100">
        {/* Header */}
        <header className="bg-red-600 text-white px-4 py-4 shadow-lg">
          <div className="max-w-lg mx-auto">
            <h1 className="text-xl font-bold">Gerüst Konfigurator</h1>
            <p className="text-red-200 text-sm">Gebäude auswählen</p>
          </div>
        </header>

        <div className="max-w-lg mx-auto p-4 space-y-6">
          {/* Search Card */}
          <div className="bg-white rounded-xl shadow-sm p-4">
            <div className="flex items-center gap-2 mb-4">
              <Building2 className="w-5 h-5 text-red-600" />
              <h2 className="font-semibold">Adresse eingeben</h2>
            </div>

            <div className="space-y-3">
              <AddressAutocomplete
                value={address}
                onChange={setAddress}
                onSelect={handleAddressSelect}
                placeholder="z.B. Bundesplatz 3, 3011 Bern"
                className="w-full"
              />

              <button
                onClick={handleSearch}
                disabled={loadingState === 'loading' || address.length < 5}
                className="w-full btn-primary flex items-center justify-center gap-2"
              >
                {loadingState === 'loading' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Lade Gebäudedaten...
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    Gebäude laden
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Error Message */}
          {loadingState === 'error' && error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-red-800">Fehler beim Laden</p>
                <p className="text-sm text-red-600 mt-1">{error}</p>
                <p className="text-xs text-red-500 mt-2">
                  Tipp: Nicht alle Kantone unterstützen Gebäudedaten. Versuche eine Adresse in BE, SO, BS, ZH, AG, SG, TG, BL oder SH.
                </p>
              </div>
            </div>
          )}

          {/* Info Card */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <h3 className="font-medium text-blue-800 mb-2">So funktioniert's</h3>
            <ol className="text-sm text-blue-700 space-y-1.5">
              <li className="flex items-start gap-2">
                <span className="bg-blue-200 text-blue-800 rounded-full w-5 h-5 flex items-center justify-center text-xs font-medium flex-shrink-0">1</span>
                Adresse eingeben und auswählen
              </li>
              <li className="flex items-start gap-2">
                <span className="bg-blue-200 text-blue-800 rounded-full w-5 h-5 flex items-center justify-center text-xs font-medium flex-shrink-0">2</span>
                Gebäudedaten werden automatisch geladen
              </li>
              <li className="flex items-start gap-2">
                <span className="bg-blue-200 text-blue-800 rounded-full w-5 h-5 flex items-center justify-center text-xs font-medium flex-shrink-0">3</span>
                Gerüst im Editor konfigurieren
              </li>
            </ol>
          </div>

          {/* Example addresses */}
          <div className="text-center">
            <p className="text-xs text-gray-500 mb-2">Beispieladressen:</p>
            <div className="flex flex-wrap justify-center gap-2">
              {[
                'Bundesplatz 3, 3011 Bern',
                'Kramgasse 10, 3011 Bern',
                'Marktplatz 10, 4051 Basel',
              ].map((example) => (
                <button
                  key={example}
                  onClick={() => {
                    setAddress(example);
                    fetchBuildingData(example);
                  }}
                  className="text-xs text-blue-600 hover:underline px-2 py-1 bg-blue-50 rounded"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Render Scaffold Configurator with loaded data
  return (
    <ScaffoldConfigurator
      projectId={buildingData.project_id}
      buildingName={buildingData.building.name}
      buildingAddress={buildingData.building.address}
      selectedFacades={convertToSelectedFacades(buildingData)}
      onBack={() => {
        setBuildingData(null);
        setLoadingState('idle');
      }}
      onComplete={() => {
        // TODO: Save configuration and navigate
        navigate('/projects');
      }}
    />
  );
}
