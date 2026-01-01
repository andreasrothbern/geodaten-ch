#!/usr/bin/env python3
"""Write the updated ConfiguratorPage.tsx with fixed data format handling."""

content = '''/**
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
import type { Project } from '../types/project';
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

// Backend stored building_data format (different from frontend BuildingData type!)
interface StoredBuildingData {
  egid?: string;
  polygon?: number[][] | { type: string; coordinates: number[][][] };  // Can be flat array OR GeoJSON
  traufhoehe_m?: number;
  firsthoehe_m?: number;
  gebaeudehoehe_m?: number;
  height_source?: string;
  floors?: number;
  building_type?: string;
  year_built?: number;
  perimeter_m?: number;
  area_m2?: number;
  sides?: Array<{
    index: number;
    start: { x: number; y: number };
    end: { x: number; y: number };
    length_m: number;
    direction: string;
  }>;
  // Also support frontend format
  heights?: {
    traufhoehe_m?: number;
    firsthoehe_m?: number;
    source?: string;
  };
  gwr?: {
    egid?: string;
  };
}

type LoadingState = 'idle' | 'loading' | 'success' | 'error';

// Helper: Calculate facade direction from start/end points
function calculateDirection(start: [number, number], end: [number, number]): string {
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];
  const angle = Math.atan2(dy, dx) * (180 / Math.PI);
  const normalized = (angle + 360) % 360;
  if (normalized >= 315 || normalized < 45) return 'O';
  if (normalized >= 45 && normalized < 135) return 'N';
  if (normalized >= 135 && normalized < 225) return 'W';
  return 'S';
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
}

function getSelectedFacadesFromSession(traufHeight: number): ConfiguratorBuildingData['selected_facades'] | null {
  try {
    const stored = sessionStorage.getItem('selectedFacades');
    if (!stored) return null;

    const sides: SelectedSide[] = JSON.parse(stored);
    if (!sides || sides.length === 0) return null;

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

// Helper: Extract polygon from stored data (handles both formats)
function extractPolygon(storedData: StoredBuildingData): [number, number][] | null {
  if (!storedData.polygon) return null;

  // Check if it's a flat array [[e, n], ...]
  if (Array.isArray(storedData.polygon) && storedData.polygon.length > 0) {
    if (Array.isArray(storedData.polygon[0]) && typeof storedData.polygon[0][0] === 'number') {
      return storedData.polygon as [number, number][];
    }
  }

  // Check if it's GeoJSON format { type: 'Polygon', coordinates: [[[e, n], ...]] }
  const geoJson = storedData.polygon as { type: string; coordinates: number[][][] };
  if (geoJson.coordinates && geoJson.coordinates[0]) {
    return geoJson.coordinates[0] as [number, number][];
  }

  return null;
}

// Helper: Convert stored building_data to configurator format
function convertStoredDataToConfiguratorFormat(
  project: Project,
  storedData: StoredBuildingData
): ConfiguratorBuildingData | null {
  // Extract polygon (handles both flat array and GeoJSON)
  const polygon = extractPolygon(storedData);
  if (!polygon || polygon.length < 3) {
    console.warn('No valid polygon in stored building_data');
    return null;
  }

  const center = calculateCenter(polygon);

  // Get heights - support both direct and nested format
  const traufHeight = storedData.traufhoehe_m || storedData.heights?.traufhoehe_m || 10;
  const firstHeight = storedData.firsthoehe_m || storedData.heights?.firsthoehe_m || traufHeight + 2;

  // Check if we have pre-selected facades from FacadeSelectionPage
  const preSelectedFacades = getSelectedFacadesFromSession(traufHeight);

  let facades: ConfiguratorBuildingData['selected_facades'];
  let perimeter = 0;

  if (preSelectedFacades && preSelectedFacades.length > 0) {
    // Use pre-selected facades from FacadeSelectionPage
    console.log(`Using ${preSelectedFacades.length} pre-selected facades from FacadeSelectionPage`);
    facades = preSelectedFacades;
    perimeter = facades.reduce((sum, f) => sum + f.length_m, 0);
    sessionStorage.removeItem('selectedFacades');
  } else if (storedData.sides && storedData.sides.length > 0) {
    // Use pre-calculated sides from backend
    console.log(`Using ${storedData.sides.length} pre-calculated sides from backend`);
    facades = storedData.sides.map((side) => ({
      id: `facade-${side.index + 1}`,
      direction: side.direction,
      length_m: Math.round(side.length_m * 100) / 100,
      height_m: traufHeight,
      slope_percent: 0,
      start_point: [side.start.x, side.start.y] as [number, number],
      end_point: [side.end.x, side.end.y] as [number, number],
    }));
    perimeter = facades.reduce((sum, f) => sum + f.length_m, 0);
  } else {
    // Calculate facades from polygon (fallback)
    facades = [];
    for (let i = 0; i < polygon.length - 1; i++) {
      const start = polygon[i];
      const end = polygon[i + 1];
      const length = calculateLength(start, end);
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

  const egid = storedData.egid || storedData.gwr?.egid || project.egid || 'unknown';

  return {
    project_id: project.id,
    building: {
      egid: egid,
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
      perimeter_m: storedData.perimeter_m || Math.round(perimeter * 100) / 100,
      area_m2: storedData.area_m2 || Math.round(calculateArea(polygon) * 100) / 100,
      roof_type: null,
      roof_surfaces_count: 0,
      height_source: storedData.height_source || storedData.heights?.source || 'stored',
      confidence: 1.0,
    },
  };
}

export default function ConfiguratorPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get('projectId');

  const [address, setAddress] = useState(searchParams.get('address') || '');
  const [loadingState, setLoadingState] = useState<LoadingState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [buildingData, setBuildingData] = useState<ConfiguratorBuildingData | null>(null);
  const [project, setProject] = useState<Project | null>(null);

  useEffect(() => {
    if (projectId) {
      loadProjectData(projectId);
    }
  }, [projectId]);

  const loadProjectData = async (id: string) => {
    setLoadingState('loading');
    setError(null);

    try {
      const loadedProject = await geruestbauApi.getProject(id);
      setProject(loadedProject);

      if (loadedProject.building_data) {
        const configData = convertStoredDataToConfiguratorFormat(
          loadedProject,
          loadedProject.building_data as StoredBuildingData
        );

        if (configData) {
          console.log('Using stored building_data from project');
          setBuildingData(configData);
          setLoadingState('success');
          return;
        }
      }

      console.log('No stored building_data, fetching from API');
      setAddress(loadedProject.address);
      await fetchBuildingData(loadedProject.address, loadedProject);

    } catch (err) {
      console.error('Error loading project:', err);
      setError(err instanceof Error ? err.message : 'Projekt konnte nicht geladen werden');
      setLoadingState('error');
    }
  };

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

      if (existingProject) {
        data.project_id = existingProject.id;
      }

      setBuildingData(data);
      setLoadingState('success');

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

  const handleAddressSelect = useCallback((suggestion: { label: string }) => {
    setAddress(suggestion.label);
    fetchBuildingData(suggestion.label, project);
  }, [fetchBuildingData, project]);

  const handleSearch = useCallback(() => {
    if (address.length >= 5) {
      fetchBuildingData(address, project);
    }
  }, [address, fetchBuildingData, project]);

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
        <header className="bg-red-600 text-white px-4 py-4 shadow-lg">
          <div className="max-w-lg mx-auto">
            <h1 className="text-xl font-bold">Geruest Konfigurator</h1>
            <p className="text-red-200 text-sm">
              {project ? project.name : 'Gebaeude auswaehlen'}
            </p>
          </div>
        </header>

        <div className="max-w-lg mx-auto p-4 space-y-6">
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

          {loadingState === 'error' && error && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-red-800">Fehler beim Laden</p>
                <p className="text-sm text-red-600 mt-1">{error}</p>
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
        if (project) {
          navigate(`/projects/${project.id}/facades`);
        }
      }}
      onComplete={() => {
        if (project) {
          navigate(`/projects/${project.id}`);
        } else {
          navigate('/projects');
        }
      }}
    />
  );
}
'''

if __name__ == '__main__':
    path = 'C:/Users/vonro/projects/lawil/geodaten-ch/geruestbau-app/src/pages/ConfiguratorPage.tsx'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Written {len(content)} bytes to ConfiguratorPage.tsx')
