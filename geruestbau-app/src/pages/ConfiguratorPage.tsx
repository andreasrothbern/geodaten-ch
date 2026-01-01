/**
 * ConfiguratorPage - Entry point for Scaffold Configurator
 *
 * Flow:
 * 1. If projectId provided: Load project and use stored building_data
 * 2. Check sessionStorage for pre-selected facades from FacadeSelectionPage
 * 3. Otherwise: User enters address and API fetches building data
 * 4. ScaffoldConfigurator is rendered with the data
 */

import { useState, useCallback, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, Building2, Loader2, AlertCircle } from 'lucide-react';
import AddressAutocomplete from '../components/ui/AddressAutocomplete';
import ScaffoldConfigurator from '../features/scaffold-configurator/components/ScaffoldConfigurator';
import { geruestbauApi } from '../api/geruestbau';
import type { Project, BuildingData as StoredBuildingData } from '../types/project';
import type { SelectedFacade } from '../features/scaffold-configurator/types/scaffold.types';

// API Base URL - use environment variable or default
const API_BASE = import.meta.env.VITE_API_URL || 'https://acceptable-trust-production.up.railway.app';

interface ConfiguratorBuildingData {
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

// Helper: Calculate facade direction from start/end points
function calculateDirection(start: [number, number], end: [number, number]): string {
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  const angle = Math.atan2(dy, dx) * (180 / Math.PI);

  // Normalize angle to 0-360
  const normalized = (angle + 360) % 360;

  // Map to cardinal directions (perpendicular to facade = viewing direction)
  if (normalized >= 315 || normalized < 45) return 'O';    // East-facing
  if (normalized >= 45 && normalized < 135) return 'N';    // North-facing
  if (normalized >= 135 && normalized < 225) return 'W';   // West-facing
  return 'S'; // South-facing
}

// Helper: Calculate facade length
function calculateLength(start: [number, number], end: [number, number]): number {
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  return Math.sqrt(dx * dx + dy * dy);
}

// Helper: Calculate polygon center
function calculateCenter(polygon: [number, number][]): [number, number] {
  const n = polygon.length;
  const sumE = polygon.reduce((acc, p) => acc + p[0], 0);
  const sumN = polygon.reduce((acc, p) => acc + p[1], 0);
  return [sumE / n, sumN / n];
}

// Helper: Calculate polygon area (Shoelace formula)
function calculateArea(polygon: [number, number][]): number {
  let area = 0;
  const n = polygon.length;
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n;
    area += polygon[i][0] * polygon[j][1];
    area -= polygon[j][0] * polygon[i][1];
  }
  return Math.abs(area) / 2;
}

// Helper: Get selected facades from sessionStorage (from FacadeSelectionPage)
interface SelectedSide {
  index: number;
  start: { x: number; y: number };
  end: { x: number; y: number };
  length_m: number;
  direction: string;
  angle_deg: number;
}

function getSelectedFacadesFromSession(traufHeight: number): ConfiguratorBuildingData['selected_facades'] | null {
  try {
    const stored = sessionStorage.getItem('selectedFacades');
    if (!stored) return null;

    const sides: SelectedSide[] = JSON.parse(stored);
    if (!sides || sides.length === 0) return null;

    // Convert to configurator format
    return sides.map((side) => ({
      id: `facade-${side.index + 1}`,
      direction: side.direction,
      length_m: Math.round(side.length_m * 100) / 100,
      height_m: traufHeight,
      slope_percent: 0,
      start_point: [side.start.x, side.start.y] as [number, number],
      end_point: [side.end.x, side.end.y] as [number, number],
    }));
  } catch (e) {
    console.warn('Failed to parse selectedFacades from sessionStorage:', e);
    return null;
  }
}

// Helper: Extract polygon from stored data (handles both flat array and GeoJSON formats)
function extractPolygon(storedData: StoredBuildingData): [number, number][] | null {
  const rawPolygon = storedData.polygon;
  if (!rawPolygon) return null;

  // Check if it's a flat array [[e, n], ...]
  if (Array.isArray(rawPolygon) && rawPolygon.length > 0) {
    const first = rawPolygon[0];
    if (Array.isArray(first) && typeof first[0] === 'number') {
      return rawPolygon as [number, number][];
    }
  }

  // Check if it's GeoJSON format { type: "Polygon", coordinates: [[[e,n],...]] }
  const geoJson = rawPolygon as { type?: string; coordinates?: number[][][] };
  if (geoJson.coordinates && geoJson.coordinates[0]) {
    return geoJson.coordinates[0] as [number, number][];
  }

  return null;
}

// Helper: Get height values from stored data (handles both direct and nested formats)
function extractHeights(storedData: StoredBuildingData): { trauf: number; first: number } {
  // Direct format from SmartBuilding API
  const directTrauf = (storedData as Record<string, unknown>).traufhoehe_m as number | undefined;
  const directFirst = (storedData as Record<string, unknown>).firsthoehe_m as number | undefined;

  if (directTrauf !== undefined) {
    return { trauf: directTrauf, first: directFirst ?? directTrauf + 2 };
  }

  // Nested format (heights object)
  const heights = storedData.heights;
  if (heights) {
    return {
      trauf: heights.traufhoehe_m ?? 10,
      first: heights.firsthoehe_m ?? (heights.traufhoehe_m ?? 10) + 2,
    };
  }

  return { trauf: 10, first: 12 };
}

// Helper: Convert stored building_data to configurator format
function convertStoredDataToConfiguratorFormat(
  project: Project,
  storedData: StoredBuildingData
): ConfiguratorBuildingData | null {
  // Extract polygon (handles both formats)
  const polygon = extractPolygon(storedData);
  if (!polygon || polygon.length < 3) {
    console.warn('No valid polygon in stored building_data');
    return null;
  }

  const center = calculateCenter(polygon);
  const heights = extractHeights(storedData);
  const traufHeight = heights.trauf;
  const firstHeight = heights.first;

  // Check if we have pre-selected facades from FacadeSelectionPage
  const preSelectedFacades = getSelectedFacadesFromSession(traufHeight);

  let facades: ConfiguratorBuildingData['selected_facades'];
  let perimeter = 0;

  if (preSelectedFacades && preSelectedFacades.length > 0) {
    // Use pre-selected facades from FacadeSelectionPage
    console.log(`Using ${preSelectedFacades.length} pre-selected facades from FacadeSelectionPage`);
    facades = preSelectedFacades;
    perimeter = facades.reduce((sum, f) => sum + f.length_m, 0);
    // Clear sessionStorage after use
    sessionStorage.removeItem('selectedFacades');
  } else {
    // Calculate ALL facades from polygon (fallback)
    facades = [];
    for (let i = 0; i < polygon.length - 1; i++) {
      const start = polygon[i];
      const end = polygon[i + 1];
      const length = calculateLength(start, end);

      // Skip very short segments (< 1m)
      if (length < 1) continue;

      perimeter += length;

      facades.push({
        id: `facade-${i + 1}`,
        direction: calculateDirection(start, end),
        length_m: Math.round(length * 100) / 100,
        height_m: traufHeight,
        slope_percent: 0,
        start_point: start,
        end_point: end,
      });
    }
  }

  // Get EGID from various sources
  const egid = (storedData as Record<string, unknown>).egid as string | undefined
    ?? storedData.gwr?.egid
    ?? project.egid
    ?? 'unknown';

  return {
    project_id: project.id,
    building: {
      egid,
      address: project.address,
      name: project.name,
      polygon: polygon,
      trauf_height_m: traufHeight,
      first_height_m: firstHeight,
      center_e: center[0],
      center_n: center[1],
    },
    selected_facades: facades,
    metadata: {
      source: preSelectedFacades ? 'facade_selection' : 'stored_project',
      polygon_points: polygon.length,
      facade_count: facades.length,
      perimeter_m: Math.round(perimeter * 100) / 100,
      area_m2: Math.round(calculateArea(polygon) * 100) / 100,
      roof_type: null,
      roof_surfaces_count: 0,
      height_source: storedData.heights?.source || 'stored',
      confidence: 1.0,
    },
  };
}

export default function ConfiguratorPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Get projectId from URL if present
  const projectId = searchParams.get('projectId');

  // State
  const [address, setAddress] = useState(searchParams.get('address') || '');
  const [loadingState, setLoadingState] = useState<LoadingState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [buildingData, setBuildingData] = useState<ConfiguratorBuildingData | null>(null);
  const [project, setProject] = useState<Project | null>(null);

  // Load project data if projectId is provided
  useEffect(() => {
    if (projectId) {
      loadProjectData(projectId);
    }
  }, [projectId]);

  // Load project and use stored building_data
  const loadProjectData = async (id: string) => {
    setLoadingState('loading');
    setError(null);

    try {
      const loadedProject = await geruestbauApi.getProject(id);
      setProject(loadedProject);

      // Check if project has stored building_data
      if (loadedProject.building_data) {
        const configData = convertStoredDataToConfiguratorFormat(
          loadedProject,
          loadedProject.building_data
        );

        if (configData) {
          console.log('Using stored building_data from project');
          setBuildingData(configData);
          setLoadingState('success');
          return;
        }
      }

      // Fallback: Use address to fetch from API
      console.log('No stored building_data, fetching from API');
      setAddress(loadedProject.address);
      await fetchBuildingData(loadedProject.address, loadedProject);

    } catch (err) {
      console.error('Error loading project:', err);
      setError(err instanceof Error ? err.message : 'Projekt konnte nicht geladen werden');
      setLoadingState('error');
    }
  };

  // Fetch building data from API
  const fetchBuildingData = useCallback(async (
    selectedAddress: string,
    existingProject?: Project | null
  ) => {
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

      const data: ConfiguratorBuildingData = await response.json();

      // If we have an existing project, use its ID
      if (existingProject) {
        data.project_id = existingProject.id;
      }

      setBuildingData(data);
      setLoadingState('success');

      // Update URL with address for sharing (only if no projectId)
      if (!projectId) {
        const newUrl = new URL(window.location.href);
        newUrl.searchParams.set('address', selectedAddress);
        window.history.replaceState({}, '', newUrl.toString());
      }

    } catch (err) {
      console.error('Error fetching building data:', err);
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler');
      setLoadingState('error');
    }
  }, [projectId]);

  // Handle address selection from autocomplete
  const handleAddressSelect = useCallback((suggestion: { label: string }) => {
    setAddress(suggestion.label);
    fetchBuildingData(suggestion.label, project);
  }, [fetchBuildingData, project]);

  // Handle manual search (Enter key or button)
  const handleSearch = useCallback(() => {
    if (address.length >= 5) {
      fetchBuildingData(address, project);
    }
  }, [address, fetchBuildingData, project]);

  // Convert API response to SelectedFacade format
  const convertToSelectedFacades = (data: ConfiguratorBuildingData): SelectedFacade[] => {
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
            <h1 className="text-xl font-bold">Geruest Konfigurator</h1>
            <p className="text-red-200 text-sm">
              {project ? project.name : 'Gebaeude auswaehlen'}
            </p>
          </div>
        </header>

        <div className="max-w-lg mx-auto p-4 space-y-6">
          {/* Project info if loaded */}
          {project && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4">
              <h3 className="font-medium text-green-800">Projekt: {project.name}</h3>
              <p className="text-sm text-green-600">{project.address}</p>
              {loadingState === 'loading' && (
                <p className="text-sm text-green-600 mt-2 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Lade Gebaeudedaten...
                </p>
              )}
            </div>
          )}

          {/* Search Card - show if no project or loading failed */}
          {(!project || loadingState === 'error') && (
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
                      Lade Gebaeudedaten...
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4" />
                      Gebaeude laden
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Error Message */}
          {loadingState === 'error' && error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-red-800">Fehler beim Laden</p>
                <p className="text-sm text-red-600 mt-1">{error}</p>
                <p className="text-xs text-red-500 mt-2">
                  Tipp: Nicht alle Kantone unterstuetzen Gebaeudedaten. Versuche eine Adresse in BE, SO, BS, ZH, AG, SG, TG, BL oder SH.
                </p>
              </div>
            </div>
          )}

          {/* Info Card - only show if no project */}
          {!project && loadingState !== 'loading' && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
              <h3 className="font-medium text-blue-800 mb-2">So funktioniert's</h3>
              <ol className="text-sm text-blue-700 space-y-1.5">
                <li className="flex items-start gap-2">
                  <span className="bg-blue-200 text-blue-800 rounded-full w-5 h-5 flex items-center justify-center text-xs font-medium flex-shrink-0">1</span>
                  Adresse eingeben und auswaehlen
                </li>
                <li className="flex items-start gap-2">
                  <span className="bg-blue-200 text-blue-800 rounded-full w-5 h-5 flex items-center justify-center text-xs font-medium flex-shrink-0">2</span>
                  Gebaeudedaten werden automatisch geladen
                </li>
                <li className="flex items-start gap-2">
                  <span className="bg-blue-200 text-blue-800 rounded-full w-5 h-5 flex items-center justify-center text-xs font-medium flex-shrink-0">3</span>
                  Geruest im Editor konfigurieren
                </li>
              </ol>
            </div>
          )}

          {/* Example addresses - only show if no project */}
          {!project && loadingState !== 'loading' && (
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
                      fetchBuildingData(example, project);
                    }}
                    className="text-xs text-blue-600 hover:underline px-2 py-1 bg-blue-50 rounded"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          )}
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
        // If we came from a project, go back to facade selection
        if (project) {
          navigate(`/projects/${project.id}/facades`);
        }
      }}
      onComplete={() => {
        // Navigate back to project or projects list
        if (project) {
          navigate(`/projects/${project.id}`);
        } else {
          navigate('/projects');
        }
      }}
    />
  );
}
