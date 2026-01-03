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
// AddressAutocomplete deaktiviert - einfaches Textfeld stattdessen
// import AddressAutocomplete from '../components/ui/AddressAutocomplete';
import ScaffoldConfigurator from '../features/scaffold-configurator/components/ScaffoldConfigurator';
import { geruestbauApi } from '../api/geruestbau';
import { API_BASE } from '../api/client';
import type { ProjectWithGeodata, Geodata } from '../types/project';
import type { SelectedFacade, RoofData } from '../features/scaffold-configurator/types/scaffold.types';

interface ConfiguratorBuildingData {
  project_id: string;
  building: {
    egid: string;
    address: string;
    name: string;
    polygon: [number, number][];  // ORIGINAL from swissBUILDINGS3D (LV95)
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
  roof?: RoofData;
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
  if (normalized >= 315 || normalized < 45) return 'E';    // East-facing
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

// IMPORTANT: Clear Zustand store cache when new facade selection exists
// This prevents stale data from overriding fresh selections
function invalidateStoreIfNewSelection() {
  const hasNewSelection = sessionStorage.getItem('selectedFacades');
  if (hasNewSelection) {
    console.log('New facade selection detected - clearing Zustand store cache');
    localStorage.removeItem('scaffold-config-storage'); // Correct key from useScaffoldConfig
  }
}

// Call immediately on module load (before Zustand hydrates)
invalidateStoreIfNewSelection();

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

// Helper: Extract polygon from geodata (flat array format)
function extractPolygon(geodata: Geodata): [number, number][] | null {
  const rawPolygon = geodata.polygon;
  if (!rawPolygon || rawPolygon.length < 3) return null;
  return rawPolygon;
}

// Helper: Get height values from geodata
function extractHeights(geodata: Geodata): { trauf: number; first: number } {
  const trauf = geodata.traufhoehe_m ?? geodata.gebaeudehoehe_m ?? 10;
  const first = geodata.firsthoehe_m ?? trauf + 2;
  return { trauf, first };
}

// Helper: Convert geodata to configurator format
function convertGeodataToConfiguratorFormat(
  project: ProjectWithGeodata,
  geodata: Geodata
): ConfiguratorBuildingData | null {
  // Extract polygon
  const polygon = extractPolygon(geodata);
  if (!polygon || polygon.length < 3) {
    console.warn('No valid polygon in geodata');
    return null;
  }

  const center = calculateCenter(polygon);
  const heights = extractHeights(geodata);
  const traufHeight = heights.trauf;
  const firstHeight = heights.first;

  // Check if we have pre-selected facades from FacadeSelectionPage
  const preSelectedFacades = getSelectedFacadesFromSession(traufHeight);

  let facades: ConfiguratorBuildingData['selected_facades'];
  let perimeter = geodata.perimeter_m ?? 0;

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
    let calculatedPerimeter = 0;
    for (let i = 0; i < polygon.length - 1; i++) {
      const start = polygon[i];
      const end = polygon[i + 1];
      const length = calculateLength(start, end);

      // Skip very short segments (< 1m)
      if (length < 1) continue;

      calculatedPerimeter += length;

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
    if (!perimeter) perimeter = calculatedPerimeter;
  }

  // Get EGID from geodata or project
  const egid = geodata.egid ?? project.egid ?? 'unknown';

  return {
    project_id: project.id,
    building: {
      egid,
      address: geodata.address ?? project.address,
      name: project.name,
      polygon: polygon,
      // polygon_original wird separat von der API geholt (nicht im Projekt gespeichert)
      trauf_height_m: traufHeight,
      first_height_m: firstHeight,
      center_e: geodata.center_e ?? geodata.coord_e ?? center[0],
      center_n: geodata.center_n ?? geodata.coord_n ?? center[1],
    },
    selected_facades: facades,
    roof: undefined,  // Roof data is fetched fresh from API
    metadata: {
      source: preSelectedFacades ? 'facade_selection' : 'geodata_cache',
      polygon_points: polygon.length,
      facade_count: facades.length,
      perimeter_m: Math.round(perimeter * 100) / 100,
      area_m2: Math.round(geodata.area_m2 ?? calculateArea(polygon) * 100) / 100,
      roof_type: null,
      roof_surfaces_count: 0,
      height_source: 'geodata_cache',
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
  const [project, setProject] = useState<ProjectWithGeodata | null>(null);

  // Load project data if projectId is provided
  useEffect(() => {
    if (projectId) {
      loadProjectData(projectId);
    }
  }, [projectId]);

  // Load project and use geodata from cache + fresh data for polygon_original
  const loadProjectData = async (id: string) => {
    setLoadingState('loading');
    setError(null);

    try {
      const loadedProject = await geruestbauApi.getProject(id);
      setProject(loadedProject);

      // Check if project has geodata from cache
      if (loadedProject.geodata?.polygon) {
        const configData = convertGeodataToConfiguratorFormat(
          loadedProject,
          loadedProject.geodata
        );

        if (configData) {
          console.log('Using geodata from cache - polygon is ORIGINAL from swissBUILDINGS3D');

          // Calculate roof from cached heights if not present
          if (!configData.roof && loadedProject.geodata) {
            const trauf = loadedProject.geodata.traufhoehe_m ?? 10;
            const first = loadedProject.geodata.firsthoehe_m ?? trauf + 3;
            const roofHeight = first - trauf;
            const roofAngle = roofHeight > 0.5 ? Math.atan(roofHeight / 5) * (180 / Math.PI) : 0;

            configData.roof = {
              roof_type: roofAngle < 5 ? 'flachdach' : roofAngle < 45 ? 'satteldach' : 'steil',
              roof_angle_deg: roofAngle,
              roof_orientation: 'N-S',
              trauf_to_first_m: roofHeight,
              scaffolding_height_m: first + 1,
              confidence: 0.7,
              traufhoehe_m: trauf,
            };
          }

          setBuildingData(configData);
          setLoadingState('success');
          return;
        }
      }

      // Fallback: Use address to fetch from API (project not enriched yet)
      console.log('No geodata in cache, fetching from API');
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
    existingProject?: ProjectWithGeodata | null
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

      // DEBUG: Log the backend response to see if roof data is present
      console.log('=== BACKEND RESPONSE ===', {
        hasRoof: !!data.roof,
        roof: data.roof,
        fullResponse: data,
      });

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

  // Handle address selection from autocomplete (deaktiviert)
  // const handleAddressSelect = useCallback((suggestion: { label: string }) => {
  //   setAddress(suggestion.label);
  //   fetchBuildingData(suggestion.label, project);
  // }, [fetchBuildingData, project]);

  // Handle manual search (Enter key or button)
  const handleSearch = useCallback(() => {
    if (address.length >= 5) {
      fetchBuildingData(address, project);
    }
  }, [address, fetchBuildingData, project]);

  // Convert API response to SelectedFacade format (including coordinates for 3D)
  const convertToSelectedFacades = (data: ConfiguratorBuildingData): SelectedFacade[] => {
    return data.selected_facades.map((facade) => ({
      id: facade.id,
      direction: facade.direction as SelectedFacade['direction'],
      length_m: facade.length_m,
      height_m: facade.height_m,
      slope_percent: facade.slope_percent,
      start_point: facade.start_point,
      end_point: facade.end_point,
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
                <input
                  type="text"
                  className="input-field w-full"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="z.B. Bundesplatz 3, 3011 Bern"
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

  // Convert roof data to the format expected by ScaffoldConfigurator
  const convertRoofData = (data: ConfiguratorBuildingData) => {
    // DEBUG: Log roof conversion
    console.log('=== convertRoofData ===', {
      hasRoof: !!data.roof,
      roofData: data.roof,
    });

    if (!data.roof) {
      console.warn('WARNING: No roof data in buildingData!');
      return undefined;
    }
    return {
      roof_type: data.roof.roof_type,
      roof_angle_deg: data.roof.roof_angle_deg,
      roof_orientation: data.roof.roof_orientation,
      trauf_to_first_m: data.roof.trauf_to_first_m,
      scaffolding_height_m: data.roof.scaffolding_height_m,
      confidence: data.roof.confidence,
      // Preserve additional fields for 3D view
      roof_overhang_m: data.roof.roof_overhang_m,
      // Use traufhoehe from roof data (calculated by backend), fallback to building data
      traufhoehe_m: data.roof.traufhoehe_m ?? data.building.trauf_height_m,
    };
  };

  // Render Scaffold Configurator with loaded data
  return (
    <ScaffoldConfigurator
      projectId={buildingData.project_id}
      buildingName={buildingData.building.name}
      buildingAddress={buildingData.building.address}
      buildingPolygon={buildingData.building.polygon}
      selectedFacades={convertToSelectedFacades(buildingData)}
      roof={convertRoofData(buildingData)}
      onBack={() => {
        setBuildingData(null);
        setLoadingState('idle');
        // If we came from a project, go back to project details
        if (project) {
          navigate(`/projects/${project.id}`);
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
