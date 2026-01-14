/**
 * ConfiguratorPage - Entry point for Scaffold Configurator
 *
 * Flow:
 * 1. If projectId provided: Load project and use stored building_data
 * 2. Check sessionStorage for pre-selected facades from FacadeSelectionPage
 * 3. Otherwise: User enters address and API fetches building data
 * 4. ScaffoldConfigurator is rendered with the data
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { Search, Building2, Loader2, AlertCircle } from 'lucide-react';
import BuildingDataCard from '../components/ui/BuildingDataCard';
// AddressAutocomplete deaktiviert - einfaches Textfeld stattdessen
// import AddressAutocomplete from '../components/ui/AddressAutocomplete';
import ScaffoldConfigurator from '../features/scaffold-configurator/components/ScaffoldConfigurator';
import { geruestbauApi, type NeighborBuilding, type AddressRangeResponse, type AddressRangeBuilding, type MultiBuildingData } from '../api/geruestbau';
import { API_BASE } from '../api/client';
import type { ProjectWithGeodata, Geodata } from '../types/project';
// NEU 10.01.2026 19:15 - SSE-Hook für Multi-Building blocked facades
import { useProjectContextStream, type BlockedFacadesData } from '../hooks/useProjectContextStream';
import type { SelectedFacade, RoofData, BuildingZone } from '../features/scaffold-configurator/types/scaffold.types';

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
  // Zonen-Daten für komplexe Gebäude (NEU 05.01.2026)
  zones?: BuildingZone[];
  building_name?: string;
  complexity?: 'simple' | 'moderate' | 'complex';
  research_source?: 'known_buildings' | 'claude_api' | 'cache' | 'auto' | 'unknown';
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
    // Polygon-Vereinfachung (optional)
    simplified_points?: number;
    epsilon_used?: number;
    angle_tolerance_deg?: number;
    // Zonen (NEU)
    zones_count?: number;
    research_source?: string;
  };
}

type LoadingState = 'idle' | 'loading' | 'success' | 'error';

// Helper: Detect if address contains a range (e.g., "2-10" or "2,4,6")
function isAddressRange(address: string): boolean {
  // Pattern: number-number (range) or number,number (list)
  const rangePattern = /\d+\s*[-–]\s*\d+/;  // 2-10, 2 - 10
  const listPattern = /\d+\s*[,/]\s*\d+/;   // 2,4 or 27/29
  return rangePattern.test(address) || listPattern.test(address);
}

// Helper: Calculate facade direction from start/end points
// Returns the direction the facade FACES (normal direction), not the edge direction
function calculateDirection(start: [number, number], end: [number, number]): string {
  const dx = end[0] - start[0];
  const dy = end[1] - start[1];

  // Edge angle (0=East, 90=North in math convention)
  const edgeAngle = Math.atan2(dy, dx) * (180 / Math.PI);

  // Facade normal is perpendicular to edge (90° rotation)
  // For counter-clockwise polygons, the outward normal is to the right (+90°)
  const normalAngle = edgeAngle + 90;

  // Normalize to 0-360
  const normalized = ((normalAngle % 360) + 360) % 360;

  // Map to cardinal directions (facade viewing direction)
  // Note: This uses math convention (0=East, 90=North, counterclockwise)
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

// FIX 11.01.2026 02:15 - Dach-Orientierung aus Polygon berechnen
// Gleiche Logik wie Backend (roof.py): First senkrecht zur LÄNGSTEN Seite
function calculateRoofOrientation(polygon: [number, number][]): 'O-W' | 'N-S' {
  if (!polygon || polygon.length < 3) return 'O-W';

  // Längste Seite finden
  let maxLength = 0;
  let longestSideVector = { dx: 1, dy: 0 }; // Default: Ost-West

  for (let i = 0; i < polygon.length; i++) {
    const p1 = polygon[i];
    const p2 = polygon[(i + 1) % polygon.length];

    const dx = p2[0] - p1[0];
    const dy = p2[1] - p1[1];
    const length = Math.sqrt(dx * dx + dy * dy);

    if (length > maxLength) {
      maxLength = length;
      longestSideVector = { dx, dy };
    }
  }

  // Azimut berechnen (0° = Nord, 90° = Ost)
  const { dx, dy } = longestSideVector;
  let azimuthDeg = Math.atan2(dx, dy) * (180 / Math.PI);
  if (azimuthDeg < 0) azimuthDeg += 360;

  // Klassifizierung nach Neigungsrichtung (wie Backend)
  // - Längste Seite ~O-W (azimuth 67.5-112.5 oder 247.5-292.5): Dach neigt O-W
  // - Längste Seite ~N-S (azimuth 0-22.5, 157.5-202.5, 337.5-360): Dach neigt N-S
  if ((azimuthDeg >= 67.5 && azimuthDeg < 112.5) ||
      (azimuthDeg >= 247.5 && azimuthDeg < 292.5)) {
    return 'O-W';  // Längste Seite läuft O-W → Dach neigt O-W
  } else {
    return 'N-S';  // Längste Seite läuft N-S → Dach neigt N-S
  }
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

// FIX 10.01.2026 22:30 - Cache invalidieren wenn Projekt sich ändert
// Vergleicht aktuelle projectId mit zuletzt geladener
function invalidateStoreIfProjectChanged(projectId: string | null) {
  if (!projectId) return;
  const lastProjectId = sessionStorage.getItem('lastLoadedProjectId');
  if (lastProjectId && lastProjectId !== projectId) {
    console.log(`[Cache] Project changed: ${lastProjectId} -> ${projectId}, clearing store cache`);
    localStorage.removeItem('scaffold-config-storage');
  }
  sessionStorage.setItem('lastLoadedProjectId', projectId);
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
  // Cast to expected type - each coordinate should be [e, n]
  return rawPolygon as [number, number][];
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
    // NEU 14.01.2026 21:45 - Fassaden-Höhen für Hanglage verwenden
    const facadeZMin = geodata.facade_z_min;
    const facadeZMax = geodata.facade_z_max;

    for (let i = 0; i < polygon.length - 1; i++) {
      const start = polygon[i];
      const end = polygon[i + 1];
      const length = calculateLength(start, end);

      // Skip very short segments (< 1m)
      if (length < 1) continue;

      calculatedPerimeter += length;

      const direction = calculateDirection(start, end);

      // NEU: Fassaden-spezifische Höhe wenn verfügbar (Hanglage)
      let facadeHeight = traufHeight;
      if (facadeZMin && facadeZMax) {
        const zMin = facadeZMin[direction];
        const zMax = facadeZMax[direction];
        if (zMin !== undefined && zMax !== undefined && zMax > zMin) {
          facadeHeight = zMax - zMin;
        }
      }

      facades.push({
        id: `facade-${i + 1}`,
        direction,
        length_m: Math.round(length * 100) / 100,
        height_m: facadeHeight,
        slope_percent: 0,
        start_point: start,
        end_point: end,
      });
    }
    if (!perimeter) perimeter = calculatedPerimeter;
  }

  // Get EGID from geodata or project
  const egid = geodata.egid ?? project.egid ?? 'unknown';

  // Convert ZoneInfo from geodata to BuildingZone format
  const zones: BuildingZone[] = (geodata.zones ?? []).map((z, i) => ({
    id: z.id || `zone_${i + 1}`,
    name: z.name,
    zone_type: z.zone_type,
    position: z.position,
    traufhoehe_m: z.traufhoehe_m,
    firsthoehe_m: z.firsthoehe_m,
    beruesten: z.beruesten ?? true,
    sonderkonstruktion: z.sonderkonstruktion ?? false,
  }));

  return {
    project_id: project.id,
    building: {
      egid,
      address: geodata.address ?? project.address,
      name: geodata.building_name || project.name,
      polygon: polygon,
      // polygon_original wird separat von der API geholt (nicht im Projekt gespeichert)
      trauf_height_m: traufHeight,
      first_height_m: firstHeight,
      center_e: geodata.center_e ?? geodata.coord_e ?? center[0],
      center_n: geodata.center_n ?? geodata.coord_n ?? center[1],
    },
    selected_facades: facades,
    roof: undefined,  // Roof data is fetched fresh from API
    // Zonen-Daten für komplexe Gebäude (FIX 05.01.2026)
    zones: zones,
    building_name: geodata.building_name,
    complexity: geodata.complexity ?? 'simple',
    research_source: geodata.research_source ?? 'unknown',
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
      // Zonen-Metadaten (NEU)
      zones_count: zones.length,
      research_source: geodata.research_source,
    },
  };
}

export default function ConfiguratorPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const location = useLocation();

  // Get projectId from URL if present
  const projectId = searchParams.get('projectId');

  // NEU 14.01.2026: force_refresh aus URL lesen für Cache-Bypass
  const forceRefreshParam = searchParams.get('force_refresh') === 'true';

  // Get project from Router State (passed from ProjectDetailPage)
  const passedProject = location.state?.project as ProjectWithGeodata | undefined;

  // State
  const [address, setAddress] = useState(searchParams.get('address') || '');
  const [loadingState, setLoadingState] = useState<LoadingState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [buildingData, setBuildingData] = useState<ConfiguratorBuildingData | null>(null);
  const [project, setProject] = useState<ProjectWithGeodata | null>(null);

  // Neighbors State (Phase 2)
  // Default to 0 (off) - neighbors loaded on-demand when user selects radius
  const [neighborsRadius, setNeighborsRadius] = useState<number>(0); // 0 = off (default), 20/50/100 = context radius
  const [neighbors, setNeighbors] = useState<NeighborBuilding[]>([]);
  const [blockedSides, setBlockedSides] = useState<string[]>([]);
  const [neighborsLoading, setNeighborsLoading] = useState(false);

  // NEU 10.01.2026 19:15 - Blocked Facades per EGID (für Multi-Building Support)
  // REFACTORED 10.01.2026 20:30 - SSE-Hook ohne Parameter, Options an start()
  const [blockedFacadesData, setBlockedFacadesData] = useState<BlockedFacadesData | null>(null);

  // NEU 10.01.2026 21:45 - SSE projectBuildings separat speichern (für verzögerte Anwendung)
  const [sseProjectBuildings, setSseProjectBuildings] = useState<typeof sseData.projectBuildings>(null);

  // SSE-Hook (stabile Referenzen, keine reaktiven Options)
  const { data: sseData, start: startSSE, stop: stopSSE } = useProjectContextStream();

  // Multi-Building State (Phase 3)
  const [addressRangeData, setAddressRangeData] = useState<AddressRangeResponse | null>(null);
  const [selectedBuildings, setSelectedBuildings] = useState<AddressRangeBuilding[]>([]);
  const [isMultiMode, setIsMultiMode] = useState(false);
  // FIX 11.01.2026 00:15 - Hybrid: Manual selection + SSE override
  // State für manuelle Auswahl (Multi-Building Mode bei Projekt-Erstellung)
  const [manualAdditionalBuildings, setManualAdditionalBuildings] = useState<MultiBuildingData[]>([]);
  const [loadingAdditionalBuildings, setLoadingAdditionalBuildings] = useState(false);

  // FIX 11.01.2026 - Derived value: SSE-Daten haben Priorität, dann manuelle Auswahl
  const additionalBuildings = useMemo<MultiBuildingData[]>(() => {
    // SSE-Daten haben Priorität (für gespeicherte Projekte)
    if (sseData.projectBuildings && sseData.projectBuildings.length > 1) {
      const additional = sseData.projectBuildings.slice(1)
        .filter(b => b.polygon && b.polygon.length >= 3)
        .map(b => ({
          egid: b.egid,
          address: '',
          polygon: b.polygon as [number, number][],
          center: [b.center_e ?? 0, b.center_n ?? 0] as [number, number],
          traufhoehe_m: b.traufhoehe_m ?? 0,
          firsthoehe_m: b.firsthoehe_m ?? 0,
        }));
      return additional;
    }
    // Fallback: Manuelle Auswahl (für neue Projekte)
    return manualAdditionalBuildings;
  }, [sseData.projectBuildings, manualAdditionalBuildings]);

  // Load project data: prefer Router State, fallback to API
  useEffect(() => {
    // FIX 10.01.2026 22:30 - Cache invalidieren wenn Projekt wechselt
    invalidateStoreIfProjectChanged(projectId);

    if (passedProject) {
      // Use project from Router State (no API call needed!)
      console.log('Using project from Router State (no API call)');
      handleProjectLoaded(passedProject);
    } else if (projectId) {
      // Fallback: Load from API (for direct links, bookmarks, reload)
      console.log('Loading project from API (fallback for direct link)');
      loadProjectData(projectId);
    }
  }, [projectId, passedProject]);

  // REFACTORED 10.01.2026 20:30 - SSE für Projekte, REST API als Fallback für Adress-Suche
  useEffect(() => {
    if (!buildingData?.building.egid) return;

    // Wenn Projekt vorhanden → SSE nutzen
    if (projectId) {
      startSSE(projectId, {
        maxRadiusM: 100,
        includeBlockedFacades: true,
        includeNeighbors: true,
      });
      return () => {
        stopSSE();
      };
    }

    // Fallback: REST API für Adress-basierte Suche (kein Projekt)
    const loadNeighbors = async () => {
      const effectiveRadius = Math.max(5, neighborsRadius);
      setNeighborsLoading(true);
      try {
        const neighborsResponse = await geruestbauApi.getNeighbors(
          buildingData.building.egid,
          effectiveRadius,
          true
        );
        setNeighbors(neighborsResponse.neighbors);
        setBlockedSides(neighborsResponse.blocked_sides);
      } catch (err) {
        console.warn('Failed to load neighbors:', err);
        setNeighbors([]);
        setBlockedSides([]);
      } finally {
        setNeighborsLoading(false);
      }
    };
    loadNeighbors();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [buildingData?.building.egid, projectId]); // NICHT startSSE/stopSSE - sie sind stabil!

  // SSE blocked_facades → blockedFacadesData + blockedSides
  // FIX 11.01.2026 01:20 - Verwende buildingData.egid für das aktuell angezeigte Gebäude
  useEffect(() => {
    if (sseData.blockedFacades) {
      setBlockedFacadesData(sseData.blockedFacades);

      const currentBuildingEgid = buildingData?.building.egid;
      const targetEgid = currentBuildingEgid && sseData.blockedFacades[currentBuildingEgid]
        ? currentBuildingEgid
        : Object.keys(sseData.blockedFacades)[0];

      if (targetEgid && sseData.blockedFacades[targetEgid]) {
        const directions = sseData.blockedFacades[targetEgid].blockers
          ?.map(b => b.direction)
          .filter((d): d is string => d !== null) ?? [];
        const uniqueDirections = [...new Set(directions)];
        if (uniqueDirections.length > 0) {
          setBlockedSides(uniqueDirections);
        }
      }
    }
  }, [sseData.blockedFacades, buildingData?.building.egid]);

  // NEU 10.01.2026 21:20 - SSE projectBuildings speichern für Höhen-Updates
  useEffect(() => {
    if (sseData.projectBuildings && sseData.projectBuildings.length > 0) {
      setSseProjectBuildings(sseData.projectBuildings);
    }
  }, [sseData.projectBuildings]);

  // NEU 10.01.2026 21:45 - SSE-Daten auf buildingData anwenden (verzögert)
  useEffect(() => {
    if (!sseProjectBuildings || sseProjectBuildings.length === 0) return;
    if (!buildingData) return;

    const firstBuilding = sseProjectBuildings[0];
    const updatedBuilding = { ...buildingData.building };
    let hasChanges = false;

    if (firstBuilding.traufhoehe_m != null && firstBuilding.traufhoehe_m !== updatedBuilding.trauf_height_m) {
      updatedBuilding.trauf_height_m = firstBuilding.traufhoehe_m;
      hasChanges = true;
    }
    if (firstBuilding.firsthoehe_m != null && firstBuilding.firsthoehe_m !== updatedBuilding.first_height_m) {
      updatedBuilding.first_height_m = firstBuilding.firsthoehe_m;
      hasChanges = true;
    }
    if (firstBuilding.polygon && firstBuilding.polygon.length >= 3) {
      updatedBuilding.polygon = firstBuilding.polygon as [number, number][];
      hasChanges = true;
    }
    if (firstBuilding.egid && firstBuilding.egid !== updatedBuilding.egid) {
      updatedBuilding.egid = firstBuilding.egid;
      hasChanges = true;
    }

    if (hasChanges) {
      const newTraufHeight = updatedBuilding.trauf_height_m;
      setBuildingData(prev => {
        if (!prev) return prev;
        const updatedFacades = prev.selected_facades.map(facade => {
          if (facade.height_m === 0 || facade.height_m === prev.building.trauf_height_m) {
            return { ...facade, height_m: newTraufHeight };
          }
          return facade;
        });
        return {
          ...prev,
          building: updatedBuilding,
          selected_facades: updatedFacades
        };
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sseProjectBuildings, buildingData?.building.egid]);

  // SSE neighbors → neighbors (alle Radien gesammelt)
  useEffect(() => {
    if (sseData.neighbors && sseData.neighbors.size > 0) {
      const allNeighbors: NeighborBuilding[] = [];
      const seenEgids = new Set<string>();
      sseData.neighbors.forEach((buildings) => {
        buildings.forEach(b => {
          if (!seenEgids.has(b.egid)) {
            seenEgids.add(b.egid);
            allNeighbors.push({
              egid: b.egid,
              distance_m: b.distance_m,
              direction: b.direction,
              polygon: b.polygon as [number, number][] | undefined,
            });
          }
        });
      });
      setNeighbors(allNeighbors);
    }
  }, [sseData.neighbors]);

  // Gefilterte Nachbarn basierend auf Slider (0=Aus, 20/50/100=Radius)
  // FIX 15.01.2026 01:45 - Separate Liste für Blocking (immer aktiv)
  const BLOCKING_THRESHOLD_M = 2.0;

  // Nachbarn für ANZEIGE (kontrolliert durch Slider)
  const filteredNeighbors = useMemo(() => {
    if (neighborsRadius === 0) return [];
    return neighbors.filter(n => n.distance_m <= neighborsRadius);
  }, [neighbors, neighborsRadius]);

  // Nachbarn für BLOCKING (immer aktiv, unabhängig vom Slider)
  // Enthält alle Nachbarn innerhalb von 2m für die Geometrie-basierte Blockierungsprüfung
  const blockingNeighbors = useMemo(() => {
    return neighbors.filter(n => n.distance_m <= BLOCKING_THRESHOLD_M);
  }, [neighbors]);

  // REST API Fallback bei Slider-Änderung (nur für Adress-Suche ohne Projekt)
  useEffect(() => {
    if (projectId) return; // SSE hat bereits alle Daten
    if (!buildingData?.building.egid) return;

    const loadNeighbors = async () => {
      const effectiveRadius = Math.max(5, neighborsRadius);
      setNeighborsLoading(true);
      try {
        const neighborsResponse = await geruestbauApi.getNeighbors(
          buildingData.building.egid,
          effectiveRadius,
          true
        );
        setNeighbors(neighborsResponse.neighbors);
        setBlockedSides(neighborsResponse.blocked_sides);
      } catch (err) {
        console.warn('Failed to load neighbors:', err);
      } finally {
        setNeighborsLoading(false);
      }
    };
    loadNeighbors();
  }, [buildingData?.building.egid, neighborsRadius, projectId]);

  // Process loaded project and set building data
  const handleProjectLoaded = async (loadedProject: ProjectWithGeodata) => {
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

          // NEU 12.01.2026 22:45 - Echte Dach-Daten verwenden wenn has_3d_layers=true
          const has3DLayers = loadedProject.geodata.has_3d_layers === true;
          const realRoofType = loadedProject.geodata.roof_type;
          const realRoofOrientation = loadedProject.geodata.roof_orientation;
          const realRoofAngle = loadedProject.geodata.roof_angle_deg;

          // Fallback-Berechnung nur wenn keine echten Daten
          const fallbackAngle = roofHeight > 0.5 ? Math.atan(roofHeight / 5) * (180 / Math.PI) : 0;
          const fallbackOrientation = calculateRoofOrientation(loadedProject.geodata.polygon as [number, number][]);

          // Priorität: Echte Daten > Fallback
          const roofAngle = realRoofAngle ?? fallbackAngle;
          const roofOrientation = realRoofOrientation ?? fallbackOrientation;
          const roofType = realRoofType ?? (roofAngle < 5 ? 'flachdach' : roofAngle < 45 ? 'satteldach' : 'steil');

          if (has3DLayers) {
            console.log(`Using REAL 3D-Layer roof data: type=${roofType}, orientation=${roofOrientation}, angle=${roofAngle}°`);
          }

          configData.roof = {
            roof_type: roofType,
            roof_angle_deg: roofAngle,
            roof_orientation: roofOrientation,
            trauf_to_first_m: roofHeight,
            scaffolding_height_m: first + 1,
            confidence: has3DLayers ? 0.95 : 0.7,  // Höhere Konfidenz bei echten Daten
            traufhoehe_m: trauf,
          };
        }

        setBuildingData(configData);
        setLoadingState('success');

        // FIX 15.01.2026 02:30 - Multi-Building Support: Lade zusätzliche Gebäude aus gespeichertem Projekt
        if (loadedProject.buildings && loadedProject.buildings.length > 1) {
          console.log(`[Multi-Building] Projekt hat ${loadedProject.buildings.length} Gebäude, lade zusätzliche...`);
          setLoadingAdditionalBuildings(true);

          try {
            // Lade Polygone für alle zusätzlichen Gebäude (ab Index 1)
            const additionalAddresses = loadedProject.buildings.slice(1).map(b => b.address);
            const additionalData = await Promise.all(
              additionalAddresses.map(addr => geruestbauApi.getBuildingPolygon(addr))
            );

            // Filtere fehlgeschlagene Ladevorgänge
            const validAdditional = additionalData.filter((d): d is MultiBuildingData => d !== null);
            setManualAdditionalBuildings(validAdditional);
            console.log(`[Multi-Building] ${validAdditional.length} zusätzliche Gebäude geladen`);
          } catch (err) {
            console.error('[Multi-Building] Fehler beim Laden zusätzlicher Gebäude:', err);
          } finally {
            setLoadingAdditionalBuildings(false);
          }
        }

        return;
      }
    }

    // Fallback: Use address to fetch from API (project not enriched yet)
    console.log('No geodata in cache, fetching from API');
    setAddress(loadedProject.address);
    await fetchBuildingData(loadedProject.address, loadedProject);

    // FIX 15.01.2026 02:30 - Multi-Building Support für Fallback-Pfad
    if (loadedProject.buildings && loadedProject.buildings.length > 1) {
      console.log(`[Multi-Building Fallback] Projekt hat ${loadedProject.buildings.length} Gebäude, lade zusätzliche...`);
      setLoadingAdditionalBuildings(true);

      try {
        const additionalAddresses = loadedProject.buildings.slice(1).map(b => b.address);
        const additionalData = await Promise.all(
          additionalAddresses.map(addr => geruestbauApi.getBuildingPolygon(addr))
        );
        const validAdditional = additionalData.filter((d): d is MultiBuildingData => d !== null);
        setManualAdditionalBuildings(validAdditional);
        console.log(`[Multi-Building Fallback] ${validAdditional.length} zusätzliche Gebäude geladen`);
      } catch (err) {
        console.error('[Multi-Building Fallback] Fehler beim Laden:', err);
      } finally {
        setLoadingAdditionalBuildings(false);
      }
    }
  };

  // Load project from API (fallback for direct links)
  const loadProjectData = async (id: string) => {
    setLoadingState('loading');
    setError(null);

    try {
      const loadedProject = await geruestbauApi.getProject(id);
      await handleProjectLoaded(loadedProject);
    } catch (err) {
      console.error('Error loading project:', err);
      setError(err instanceof Error ? err.message : 'Projekt konnte nicht geladen werden');
      setLoadingState('error');
    }
  };

  // Fetch building data from API
  // isRefresh: If true, don't change loadingState (for simplification changes)
  const fetchBuildingData = useCallback(async (
    selectedAddress: string,
    existingProject?: ProjectWithGeodata | null,
    epsilon?: number | null,
    isRefresh: boolean = false
  ) => {
    if (!isRefresh) {
      setLoadingState('loading');
    }
    setError(null);

    try {
      const params = new URLSearchParams({
        address: selectedAddress,
        include_roof: 'true',
      });

      // NEU 14.01.2026: force_refresh aus URL-Parameter übernehmen
      if (forceRefreshParam) {
        params.set('force_refresh', 'true');
      }

      // Add simplify_epsilon if set (null/undefined = dynamic)
      if (epsilon !== null && epsilon !== undefined) {
        params.set('simplify_epsilon', epsilon.toString());
      }

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
      // Don't change loadingState on refresh errors - keep showing current data
      if (!isRefresh) {
        setLoadingState('error');
      }
    }
  }, [projectId]);

  // Handle address selection from autocomplete (deaktiviert)
  // const handleAddressSelect = useCallback((suggestion: { label: string }) => {
  //   setAddress(suggestion.label);
  //   fetchBuildingData(suggestion.label, project);
  // }, [fetchBuildingData, project]);

  // Handle manual search (Enter key or button)
  const handleSearch = useCallback(async () => {
    if (address.length < 5) return;

    // Check if address contains a range (e.g., "Knospenweg 2-10")
    if (isAddressRange(address)) {
      setLoadingState('loading');
      setError(null);
      setIsMultiMode(true);
      try {
        const rangeData = await geruestbauApi.resolveAddressRange(address);
        setAddressRangeData(rangeData);
        setSelectedBuildings([]);
        setLoadingState('idle');

        if (rangeData.building_count === 0) {
          setError(`Keine Gebäude gefunden für: ${address}`);
        } else if (rangeData.building_count === 1) {
          // Single building found - load directly
          setIsMultiMode(false);
          fetchBuildingData(rangeData.buildings[0].address, project);
        }
        // Multiple buildings - show selection UI
      } catch (err) {
        console.error('Error resolving address range:', err);
        setError(err instanceof Error ? err.message : 'Adressbereich konnte nicht aufgelöst werden');
        setLoadingState('error');
        setIsMultiMode(false);
      }
    } else {
      // Single address - use existing logic
      setIsMultiMode(false);
      setAddressRangeData(null);
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
          {/* Project info if loaded - NEU 14.01.2026: BuildingDataCard verwenden */}
          {project && project.geodata && (
            <BuildingDataCard geodata={project.geodata} egid={project.egid} />
          )}
          {project && !project.geodata && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4">
              <h3 className="font-medium text-green-800">Projekt: {project.name}</h3>
              <p className="text-sm text-green-600">{project.address}</p>
              {loadingState === 'loading' && (
                <p className="text-sm text-green-600 mt-2 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Lade Gebäudedaten...
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

          {/* Multi-Building Selection (Phase 3) */}
          {isMultiMode && addressRangeData && addressRangeData.building_count > 1 && (
            <div className="bg-white rounded-xl shadow-sm p-4">
              <div className="flex items-center gap-2 mb-4">
                <Building2 className="w-5 h-5 text-blue-600" />
                <h2 className="font-semibold">
                  {addressRangeData.building_count} Gebäude gefunden
                </h2>
              </div>

              <p className="text-sm text-gray-600 mb-3">
                {addressRangeData.parsed.street}, {addressRangeData.parsed.city}
              </p>

              {/* Building selection list */}
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {addressRangeData.buildings.map((building) => {
                  const isSelected = selectedBuildings.some(b => b.egid === building.egid);
                  return (
                    <label
                      key={building.egid}
                      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                        isSelected
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {
                          if (isSelected) {
                            setSelectedBuildings(prev => prev.filter(b => b.egid !== building.egid));
                          } else {
                            setSelectedBuildings(prev => [...prev, building]);
                          }
                        }}
                        className="w-4 h-4 text-blue-600 rounded"
                      />
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{building.address}</p>
                        <p className="text-xs text-gray-500">EGID: {building.egid}</p>
                      </div>
                    </label>
                  );
                })}
              </div>

              {/* Action buttons */}
              <div className="flex gap-3 mt-4">
                <button
                  onClick={() => {
                    // Select all buildings
                    setSelectedBuildings(addressRangeData.buildings);
                  }}
                  className="flex-1 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                >
                  Alle auswählen
                </button>
                <button
                  onClick={async () => {
                    if (selectedBuildings.length === 1) {
                      // Single building - load directly
                      setIsMultiMode(false);
                      setManualAdditionalBuildings([]);
                      fetchBuildingData(selectedBuildings[0].address, project);
                    } else if (selectedBuildings.length > 1) {
                      // Multi-Building Projekt: Alle Gebäude sind Teil EINES Objekts
                      setIsMultiMode(false);
                      setLoadingAdditionalBuildings(true);

                      // Lade erstes Projekt-Gebäude (für Fassaden-Anzeige)
                      await fetchBuildingData(selectedBuildings[0].address, project);

                      // Lade Polygone für weitere Projekt-Gebäude parallel
                      const additionalAddresses = selectedBuildings.slice(1).map(b => b.address);
                      const additionalData = await Promise.all(
                        additionalAddresses.map(addr => geruestbauApi.getBuildingPolygon(addr))
                      );

                      // Filtere fehlgeschlagene Ladevorgänge
                      const validAdditional = additionalData.filter((d): d is MultiBuildingData => d !== null);
                      setManualAdditionalBuildings(validAdditional);
                      setLoadingAdditionalBuildings(false);

                      console.log(`Projekt mit ${1 + validAdditional.length} Gebäuden geladen`);
                    }
                  }}
                  disabled={selectedBuildings.length === 0 || loadingAdditionalBuildings}
                  className="flex-1 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loadingAdditionalBuildings
                    ? 'Lade Polygone...'
                    : selectedBuildings.length === 0
                    ? 'Gebäude auswählen'
                    : selectedBuildings.length === 1
                    ? 'Gebäude laden'
                    : `${selectedBuildings.length} Gebäude laden`}
                </button>
              </div>

              {/* Errors from range resolution */}
              {addressRangeData.error_count > 0 && (
                <div className="mt-3 text-xs text-amber-600 bg-amber-50 p-2 rounded">
                  {addressRangeData.error_count} Adressen nicht gefunden: {addressRangeData.errors.slice(0, 3).join(', ')}
                  {addressRangeData.errors.length > 3 && '...'}
                </div>
              )}
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
      // NEU 14.01.2026: Echte 3D-Dachgeometrie für präzise Visualisierung
      roof_geometry_coords: data.roof.roof_geometry_coords,
      has_roof_geometry: data.roof.has_roof_geometry,
      roof_dach_min_m: data.roof.roof_dach_min_m,
      roof_dach_max_m: data.roof.roof_dach_max_m,
    };
  };

  // Render Scaffold Configurator with loaded data
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Settings Bar */}
      <div className="bg-white border-b shadow-sm px-4 py-3">
        <div className="max-w-lg mx-auto space-y-3">
          {/* Neighbors Radius */}
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">
              Nachbargebäude:
            </label>
            <div className="flex items-center gap-3">
              {[
                { value: 0, label: 'Aus' },
                { value: 20, label: '20m' },
                { value: 50, label: '50m' },
                { value: 100, label: '100m' },
              ].map((option) => (
                <button
                  key={option.value}
                  onClick={() => setNeighborsRadius(option.value)}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    neighborsRadius === option.value
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {option.label}
                </button>
              ))}
              {neighborsLoading && (
                <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
              )}
            </div>
          </div>
          {/* ENTFERNT 11.01.2026 17:15 - Gelber Banner redundant, blockierte Fassaden werden im 2D/3D-View angezeigt */}
        </div>
      </div>

      {/* Scaffold Configurator */}
      {/* FIX 11.01.2026 01:10 - Projekt-Name/Adresse haben Vorrang (Multi-Building: "Knospenweg 4-6") */}
      <ScaffoldConfigurator
        projectId={buildingData.project_id}
        buildingName={project?.name || buildingData.building_name || buildingData.building.name}
        buildingAddress={project?.address || buildingData.building.address}
        buildingPolygon={buildingData.building.polygon}
        selectedFacades={convertToSelectedFacades(buildingData)}
        roof={convertRoofData(buildingData)}
        neighbors={filteredNeighbors}
        blockingNeighbors={blockingNeighbors}
        blockedSides={blockedSides}
        // NEU 10.01.2026 19:25 - Blocked Facades per EGID (Multi-Building Support via SSE)
        blockedFacadesData={blockedFacadesData}
        additionalBuildings={additionalBuildings}
        // Zonen-Daten für komplexe Gebäude (NEU 05.01.2026)
        zones={buildingData.zones}
        complexity={buildingData.complexity}
        researchSource={buildingData.research_source}
        // NEU 14.01.2026 21:30 - Fassaden-Höhen für Hanglage (pro Himmelsrichtung)
        facadeZMin={project?.geodata?.facade_z_min}
        facadeZMax={project?.geodata?.facade_z_max}
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
    </div>
  );
}
