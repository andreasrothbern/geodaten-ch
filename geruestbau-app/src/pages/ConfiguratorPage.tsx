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
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, Building2, Loader2, AlertCircle } from 'lucide-react';
import BuildingDataCard from '../components/ui/BuildingDataCard';
// AddressAutocomplete deaktiviert - einfaches Textfeld stattdessen
// import AddressAutocomplete from '../components/ui/AddressAutocomplete';
import ScaffoldConfigurator from '../features/scaffold-configurator/components/ScaffoldConfigurator';
import { geruestbauApi, type NeighborBuilding, type AddressRangeResponse, type AddressRangeBuilding, type GeodataBuilding, type ObjectData, type ProjectGeodataResponse } from '../api/geruestbau';
import { API_BASE } from '../api/client';
import type { ProjectWithGeruestbaudata, Geodata, BuildingWall, BuildingRoof, GeruestbauData } from '../types/project';
import { convertGeruestbaudataToGeodata, getBuildingEgids } from '../types/project';
// NEU 10.01.2026 19:15 - SSE-Hook für Multi-Building blocked facades
import { useProjectContextStream, type BlockedFacadesData } from '../hooks/useProjectContextStream';
import type { SelectedFacade, RoofData, BuildingZone } from '../features/scaffold-configurator/types/scaffold.types';
// NEU 15.01.2026 BUG-024: Import für geometrisches Wall-Matching bei Initialisierung
// NEU 18.01.2026 BUG-027: Import für Fassaden-Berechnung bei Multi-Building
import { matchFacadeToWall, simplifyPolygon, sidesToFacades } from '../features/scaffold-configurator/utils/polygonSimplifier';

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
  // NEU 15.01.2026 BUG-024: BuildingWall direkt aus building_walls DB-Tabelle
  building_walls?: BuildingWall[];
  // NEU 15.01.2026 23:30: BuildingRoof direkt aus building_roofs DB-Tabelle
  building_roofs?: BuildingRoof[];
  // NEU 16.01.2026 14:50: Terrain-Höhen pro Fassade für konsistente 3D-Berechnung
  facade_z_min?: Record<string, number>;  // Terrain-Höhe pro Himmelsrichtung (m ü.M.)
  facade_z_max?: Record<string, number>;  // Oberkante pro Himmelsrichtung (m ü.M.)
  // NEU 19.01.2026: Objekt-Daten (Ein Projekt = Ein Objekt)
  // "polygon" ist IMMER vorhanden (Single- und Multi-Building)
  object_data?: ObjectData;
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
// FIX 24.01.2026: Auch localStorage-Cache prüfen (sessionStorage kann leer sein nach Page Refresh)
function invalidateStoreIfProjectChanged(projectId: string | null) {
  if (!projectId) return;

  let shouldClear = false;

  // 1. sessionStorage-basierte Prüfung (schnell)
  const lastProjectId = sessionStorage.getItem('lastLoadedProjectId');
  if (lastProjectId && lastProjectId !== projectId) {
    console.log(`[Cache] Project changed (sessionStorage): ${lastProjectId} -> ${projectId}`);
    shouldClear = true;
  }

  // 2. FIX 24.01.2026: localStorage-Cache prüfen (falls sessionStorage leer)
  // Dies fängt den Fall ab, wenn sessionStorage nach Page Refresh/Browser Neustart leer ist
  if (!shouldClear) {
    try {
      const cacheStr = localStorage.getItem('scaffold-config-storage');
      if (cacheStr) {
        const cache = JSON.parse(cacheStr);
        const cachedProjectId = cache?.state?.projectId;
        if (cachedProjectId && cachedProjectId !== projectId) {
          console.log(`[Cache] Project changed (localStorage): ${cachedProjectId} -> ${projectId}`);
          shouldClear = true;
        }
      }
    } catch (e) {
      // JSON parse error - clear cache to be safe
      console.log('[Cache] Invalid cache, clearing');
      shouldClear = true;
    }
  }

  if (shouldClear) {
    localStorage.removeItem('scaffold-config-storage');
  }

  sessionStorage.setItem('lastLoadedProjectId', projectId);
}

// Call immediately on module load (before Zustand hydrates)
invalidateStoreIfNewSelection();

// NEU 19.01.2026: Konvertiert ProjectGeodataResponse zu ConfiguratorBuildingData
// Ein Projekt = Ein Objekt. Verwendet das Union-Polygon aus der API.
function convertGeodataResponseToConfiguratorFormat(
  geodataResponse: ProjectGeodataResponse,
  projectId: string,
  address: string
): ConfiguratorBuildingData | null {
  // Das Union-Polygon ist IMMER das Projekt-Polygon
  if (!geodataResponse.polygon || geodataResponse.polygon.length < 3) {
    console.warn('[convertGeodataResponse] No valid polygon from API');
    return null;
  }

  const polygon = geodataResponse.polygon as [number, number][];
  const projectBuildings = geodataResponse.project_buildings;

  // FIX 21.01.2026: Walls und Roofs ZUERST extrahieren, dann Höhen daraus berechnen
  // Die 3D-Daten (z_min/z_max) sind die Wahrheit - keine API-berechneten Werte verwenden!
  const allWalls: BuildingWall[] = projectBuildings.flatMap((b: GeodataBuilding) =>
    (b.walls ?? []).map((w, idx: number) => ({
      gebaeudeeinheit: `${b.egid}_wall_${idx}`,
      egid: parseInt(b.egid) || null,
      z_min: w.z_min,
      z_max: w.z_max,
      geometry_type: w.geometry_type ?? 'Polygon',
      geometry: w.geometry ?? null,
    }))
  );

  const allRoofs: BuildingRoof[] = projectBuildings.flatMap((b: GeodataBuilding) =>
    (b.roofs ?? []).map((r, idx: number) => ({
      gebaeudeeinheit: `${b.egid}_roof_${idx}`,
      egid: parseInt(b.egid) || null,
      dach_min: r.dach_min,
      dach_max: r.dach_max,
      roof_form: null,
      roof_angle_deg: null,
      roof_orientation: null,
      geometry_type: r.geometry_type ?? null,
      geometry: r.geometry ?? null,
    }))
  );

  // FIX 04.02.2026: Keine Magic Numbers! Höhen kommen aus 3D-Rohdaten oder bleiben undefined.
  // Die Gerüsthöhe ist KONSTANT (= Traufhöhe). Terrain-Differenzen werden
  // durch Stellspindeln/Ausgleichsrahmen am Boden ausgeglichen, NICHT durch
  // Variation der Gerüsthöhe! Siehe: NPK 114, 3D_LAYER_USAGE_SCAFFOLDING.md
  let traufHeight: number | undefined = undefined;
  let firstHeight: number | undefined = undefined;

  // Hilfsfunktion: Extrahiere min/max Z aus verschachtelter Geometrie
  // Wird NUR für Terrain-Z-Werte verwendet (Stellspindel-Berechnung), NICHT für Gerüsthöhe!
  const extractZFromGeometry = (geometry: unknown): { minZ: number; maxZ: number } => {
    let minZ = Infinity;
    let maxZ = -Infinity;

    const processCoord = (coord: number[]) => {
      if (coord.length >= 3) {
        minZ = Math.min(minZ, coord[2]);
        maxZ = Math.max(maxZ, coord[2]);
      }
    };

    const processGeom = (geom: unknown) => {
      if (Array.isArray(geom)) {
        if (geom.length > 0 && typeof geom[0] === 'number') {
          processCoord(geom as number[]);
        } else {
          geom.forEach(g => processGeom(g));
        }
      }
    };

    processGeom(geometry);
    return { minZ, maxZ };
  };

  // Terrain-Z-Werte aus Wall-Geometrie extrahieren (NUR für Hanglage/Stellspindeln)
  let geometryWallMinZ = Infinity;
  let geometryWallMaxZ = -Infinity;

  allWalls.forEach(wall => {
    if (wall.geometry) {
      const { minZ, maxZ } = extractZFromGeometry(wall.geometry);
      if (isFinite(minZ)) geometryWallMinZ = Math.min(geometryWallMinZ, minZ);
      if (isFinite(maxZ)) geometryWallMaxZ = Math.max(geometryWallMaxZ, maxZ);
    }
  });

  // FIX 04.02.2026: Höhen aus 3D-Rohdaten berechnen (Frontend = Berechnung)
  // Traufhöhe = roof.dach_min - wall.z_min (Dach-Unterkante minus Terrain)
  // Firsthöhe = max(wall.z_max, roof.dach_max) - wall.z_min (Gebäude-Oberkante minus Terrain)
  // WICHTIG: wall.z_max kann HÖHER sein als roof.dach_max (Attika, Aufbauten)!
  // Das Gerüst muss die ganze Fassade abdecken, nicht nur bis zum Dach.

  if (allWalls.length > 0) {
    const wallZMins = allWalls.filter(w => w.z_min != null).map(w => w.z_min!);
    const wallZMaxs = allWalls.filter(w => w.z_max != null).map(w => w.z_max!);
    const roofMins = allRoofs.filter(r => r.dach_min != null).map(r => r.dach_min!);
    const roofMaxs = allRoofs.filter(r => r.dach_max != null).map(r => r.dach_max!);
    const terrainRef = wallZMins.length > 0 ? Math.min(...wallZMins) : 0;

    if (terrainRef > 0) {
      // Traufhöhe = Dach-Unterkante - Terrain
      if (roofMins.length > 0) {
        traufHeight = Math.min(...roofMins) - terrainRef;
        console.log(`[convertGeodataResponse] Traufhöhe: dach_min(${Math.min(...roofMins).toFixed(1)}) - terrain(${terrainRef.toFixed(1)}) = ${traufHeight.toFixed(2)}m`);
      }

      // Firsthöhe = Höchster Punkt der Fassade - Terrain
      // wall.z_max ist massgebend (nicht dach_max), weil Attika/Aufbauten über dem Dach liegen können
      const wallTop = wallZMaxs.length > 0 ? Math.max(...wallZMaxs) : 0;
      const roofTop = roofMaxs.length > 0 ? Math.max(...roofMaxs) : 0;
      const buildingTop = Math.max(wallTop, roofTop);
      if (buildingTop > terrainRef) {
        firstHeight = buildingTop - terrainRef;
        console.log(`[convertGeodataResponse] Firsthöhe: buildingTop(${buildingTop.toFixed(1)}) - terrain(${terrainRef.toFixed(1)}) = ${firstHeight.toFixed(2)}m`);
      }

      // Flachdach: dach_min ≈ dach_max → Traufhöhe = Gebäudehöhe (kein Dachansatz)
      if (roofMins.length > 0 && roofMaxs.length > 0) {
        const dachDiff = Math.max(...roofMaxs) - Math.min(...roofMins);
        if (dachDiff < 0.5 && firstHeight !== undefined) {
          traufHeight = firstHeight;
          console.log(`[convertGeodataResponse] Flachdach erkannt (dach_diff=${dachDiff.toFixed(2)}m) → Traufhöhe = Firsthöhe = ${traufHeight.toFixed(2)}m`);
        }
      }
    }
  }

  // Fallback auf gebaeudehoehe_m — nur wenn keine 3D-Daten vorhanden
  if (traufHeight === undefined && projectBuildings.length > 0) {
    const gebHoehen = projectBuildings
      .map((b: GeodataBuilding) => b.gebaeudehoehe_m)
      .filter((v: number | undefined): v is number => v !== null && v !== undefined && v > 0);
    if (gebHoehen.length > 0) {
      traufHeight = Math.max(...gebHoehen);
      firstHeight = traufHeight;
      console.log(`[convertGeodataResponse] Höhe aus gebaeudehoehe_m (Fallback): ${traufHeight.toFixed(2)}m`);
    }
  }

  // Terrain-Info loggen (für Debugging, zeigt Hanglage-Situation)
  if (isFinite(geometryWallMinZ) && isFinite(geometryWallMaxZ)) {
    const terrainRange = geometryWallMaxZ - geometryWallMinZ;
    console.log(`[convertGeodataResponse] Terrain Z-Range: ${geometryWallMinZ.toFixed(1)} - ${geometryWallMaxZ.toFixed(1)}m (Differenz: ${terrainRange.toFixed(2)}m) → für Stellspindel-Berechnung`);
  }

  // Fassaden aus Union-Polygon berechnen
  // NEU 19.01.2026: originalPolygon für exakte 3D-Gerüst-Platzierung übergeben
  // FIX 25.01.2026: epsilon: 0 = KEINE Vereinfachung beim Laden (Original-Polygon)
  // Der Benutzer kann dann im FacadePanel mit dem Slider vereinfachen
  const simplifyResult = simplifyPolygon(polygon, { epsilon: 0 });
  const facades = sidesToFacades(
    simplifyResult.sides,
    traufHeight ?? 0,
    undefined,  // facadeZMin
    undefined,  // facadeZMax
    polygon     // originalPolygon - für 3D-Platzierung
  );

  // Zentrum berechnen
  const centerE = polygon.reduce((sum, p) => sum + p[0], 0) / polygon.length;
  const centerN = polygon.reduce((sum, p) => sum + p[1], 0) / polygon.length;

  // Perimeter und Fläche berechnen
  const perimeter = simplifyResult.sides.reduce((sum, s) => sum + s.length_m, 0);
  const area = calculateArea(polygon);

  // Dach-Daten berechnen
  const roofHeight = (firstHeight ?? 0) - (traufHeight ?? 0);
  const roofOrientation = calculateRoofOrientation(polygon);
  const roofAngle = roofHeight > 0.5 ? Math.atan(roofHeight / 5) * (180 / Math.PI) : 0;
  const roofType = roofAngle < 5 ? 'flachdach' : roofAngle < 45 ? 'satteldach' : 'steil';

  // EGID: Bei Multi-Building alle EGIDs kombinieren
  const combinedEgid = geodataResponse.project_egids.join('+');

  console.log(`[convertGeodataResponse] Union-Polygon mit ${polygon.length} Punkten, ${projectBuildings.length} Gebäude(n), Höhe=${traufHeight ?? 'undefined'}m`);
  console.log(`[convertGeodataResponse] Walls: ${allWalls.length}, erster geometry_type: ${allWalls[0]?.geometry_type}, hat geometry: ${!!allWalls[0]?.geometry}`);
  console.log(`[convertGeodataResponse] Roofs: ${allRoofs.length}, erster geometry_type: ${allRoofs[0]?.geometry_type}, hat geometry: ${!!allRoofs[0]?.geometry}`);

  // FIX 21.01.2026: Extrahiere 3D-Dachgeometrie aus allRoofs für ScaffoldScene
  let roofGeometryCoords: number[][][] | undefined = undefined;
  let hasRoofGeometry = false;
  let roofDachMinM: number | undefined = undefined;
  let roofDachMaxM: number | undefined = undefined;

  if (allRoofs.length > 0) {
    const firstRoof = allRoofs[0];
    if (firstRoof.geometry && firstRoof.geometry_type) {
      if (firstRoof.geometry_type === 'MultiPolygon') {
        // Flatten: Extrahiere alle Polygone (nur exterior rings)
        roofGeometryCoords = (firstRoof.geometry as number[][][][]).map(
          (polygon) => polygon[0] // Nur exterior ring
        );
      } else if (firstRoof.geometry_type === 'Polygon') {
        roofGeometryCoords = [firstRoof.geometry[0]] as number[][][];
      }
      hasRoofGeometry = true;
      console.log('[convertGeodataResponse] 3D-Roof-Geometrie extrahiert:', {
        type: firstRoof.geometry_type,
        polygons: roofGeometryCoords?.length ?? 0,
      });
    }
    roofDachMinM = firstRoof.dach_min ?? undefined;
    roofDachMaxM = firstRoof.dach_max ?? undefined;
  }

  // terrain_z_min: Niedrigste Terrain-Höhe aus Wall z_min
  let terrainZMin: number | undefined = undefined;
  if (allWalls.length > 0) {
    const wallZMins = allWalls.map(w => w.z_min).filter((z): z is number => z !== null && z !== undefined);
    if (wallZMins.length > 0) {
      terrainZMin = Math.min(...wallZMins);
    }
  }

  return {
    project_id: projectId,
    building: {
      egid: combinedEgid,
      address: address,
      name: address,
      polygon: polygon,
      trauf_height_m: traufHeight ?? 0,
      first_height_m: firstHeight ?? 0,
      center_e: centerE,
      center_n: centerN,
    },
    selected_facades: facades.map(f => ({
      id: f.id,
      direction: f.direction,
      length_m: f.length_m,
      height_m: f.height_m,
      slope_percent: 0,
      start_point: f.start_point,
      end_point: f.end_point,
      // NEU 19.01.2026: Original-Segmente für exakte 3D-Gerüst-Platzierung
      originalSegments: f.originalSegments,
    })),
    roof: {
      roof_type: roofType,
      roof_angle_deg: roofAngle,
      roof_orientation: roofOrientation,
      trauf_to_first_m: roofHeight,
      scaffolding_height_m: (firstHeight ?? 0) + 1,
      confidence: hasRoofGeometry ? 0.95 : 0.7,
      traufhoehe_m: traufHeight ?? 0,
      // FIX 21.01.2026: 3D-Roof-Daten für ScaffoldScene
      roof_geometry_coords: roofGeometryCoords,
      has_roof_geometry: hasRoofGeometry,
      roof_dach_min_m: roofDachMinM,
      roof_dach_max_m: roofDachMaxM,
      terrain_z_min: terrainZMin,
    },
    building_walls: allWalls.length > 0 ? allWalls : undefined,
    // FIX 21.01.2026: Auch building_roofs für 3D-View
    building_roofs: allRoofs.length > 0 ? allRoofs : undefined,
    metadata: {
      source: 'geodata_api',
      polygon_points: polygon.length,
      facade_count: facades.length,
      perimeter_m: Math.round(perimeter * 10) / 10,
      area_m2: Math.round(area * 10) / 10,
      roof_type: roofType,
      roof_surfaces_count: 0,
      height_source: traufHeight !== 8 ? 'swissBUILDINGS3D' : 'estimated',
      confidence: 0.7,
    },
  };
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

// Helper: Extract polygon from geodata (flat array format)
function extractPolygon(geodata: Geodata): [number, number][] | null {
  const rawPolygon = geodata.polygon;
  if (!rawPolygon || rawPolygon.length < 3) return null;
  // Cast to expected type - each coordinate should be [e, n]
  return rawPolygon as [number, number][];
}

// Helper: Get height values from geodata
// FIX 04.02.2026: wall.z_max für Firsthöhe (Attika/Aufbauten können über Dach liegen)
function extractHeights(geodata: Geodata): { trauf: number; first: number } {
  let trauf: number | null = null;
  let first: number | null = null;

  // Terrain-Referenz: niedrigster Punkt
  let terrainMin = geodata.terrain_height_m ?? 0;
  if (geodata.facade_z_min) {
    terrainMin = Math.min(...Object.values(geodata.facade_z_min));
  }
  // wall.z_min als Terrain wenn building_walls verfügbar
  if (geodata.building_walls && geodata.building_walls.length > 0) {
    const wallZMins = geodata.building_walls
      .map(w => w.z_min)
      .filter((z): z is number => z != null);
    if (wallZMins.length > 0) {
      terrainMin = Math.min(...wallZMins);
    }
  }

  if (terrainMin > 0) {
    // Traufhöhe = Dach-Unterkante - Terrain
    if (geodata.roof_dach_min_m != null) {
      trauf = geodata.roof_dach_min_m - terrainMin;
    }

    // Firsthöhe = Höchster Punkt (wall.z_max ODER dach_max) - Terrain
    let buildingTop = 0;
    if (geodata.building_walls && geodata.building_walls.length > 0) {
      const wallZMaxs = geodata.building_walls
        .map(w => w.z_max)
        .filter((z): z is number => z != null);
      if (wallZMaxs.length > 0) buildingTop = Math.max(...wallZMaxs);
    }
    if (geodata.roof_dach_max_m != null) {
      buildingTop = Math.max(buildingTop, geodata.roof_dach_max_m);
    }
    if (buildingTop > terrainMin) {
      first = buildingTop - terrainMin;
    }

    // Flachdach: dach_min ≈ dach_max → Traufhöhe = Gebäudehöhe
    if (geodata.roof_dach_min_m != null && geodata.roof_dach_max_m != null) {
      const dachDiff = geodata.roof_dach_max_m - geodata.roof_dach_min_m;
      if (dachDiff < 0.5 && first != null) {
        trauf = first;
      }
    }
  }

  // Fallback auf gebaeudehoehe_m, sonst 0
  const finalTrauf = trauf ?? geodata.gebaeudehoehe_m ?? 0;
  const finalFirst = first ?? finalTrauf;
  return { trauf: finalTrauf, first: finalFirst };
}

// Helper: Convert geodata to configurator format
function convertGeodataToConfiguratorFormat(
  project: ProjectWithGeruestbaudata,
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
    // FIX 24.01.2026: facade_z_min/max werden in convertToSelectedFacades() aus
    // building_walls extrahiert (für Terrain-Visualisierung). NICHT HIER verwenden!
    // NPK 114: Gerüsthöhe ist konstant = Traufhöhe für ALLE Fassaden.

    for (let i = 0; i < polygon.length - 1; i++) {
      const start = polygon[i];
      const end = polygon[i + 1];
      const length = calculateLength(start, end);

      // Skip very short segments (< 1m)
      if (length < 1) continue;

      calculatedPerimeter += length;

      const direction = calculateDirection(start, end);

      // FIX 24.01.2026: Gerüsthöhe ist IMMER traufHeight (NPK 114)!
      // ENTFERNT: facadeHeight = zMax - zMin (war FALSCH bei Giebel-Fassaden)
      // Die z_min/z_max Werte werden weiterhin für facade_z_min/max gespeichert
      // (für Stellspindel-Visualisierung), aber NICHT für die Gerüsthöhe verwendet.
      const facadeHeight = traufHeight;

      facades.push({
        id: `facade-${i + 1}`,
        direction,
        length_m: Math.round(length * 100) / 100,
        height_m: facadeHeight,  // FIX 24.01.2026: Immer traufHeight, nicht zMax-zMin!
        slope_percent: 0,
        start_point: start,
        end_point: end,
        // HINWEIS: facade_z_min/max werden später in convertToSelectedFacades()
        // aus building_walls extrahiert (für Terrain-Visualisierung, nicht Höhe!)
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

  // Get projectId from URL if present
  const projectId = searchParams.get('projectId');

  // NEU 14.01.2026: force_refresh aus URL lesen für Cache-Bypass
  const forceRefreshParam = searchParams.get('force_refresh') === 'true';

  // FIX 21.01.2026 01:00: Router State nicht mehr verwendet - IMMER geodata API aufrufen
  // Die API liefert building_walls für 3D-Wände, Router State hat diese nicht.

  // State
  const [address, setAddress] = useState(searchParams.get('address') || '');
  const [loadingState, setLoadingState] = useState<LoadingState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [buildingData, setBuildingData] = useState<ConfiguratorBuildingData | null>(null);
  const [project, setProject] = useState<ProjectWithGeruestbaudata | null>(null);

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
  // NEU 19.01.2026: Objekt-Architektur - Ein Projekt = Ein Objekt
  // object_data enthält "polygon" (Union aller Gebäude) und projectBuildings (Metadaten)
  const [addressRangeData, setAddressRangeData] = useState<AddressRangeResponse | null>(null);
  const [selectedBuildings, setSelectedBuildings] = useState<AddressRangeBuilding[]>([]);
  const [isMultiMode, setIsMultiMode] = useState(false);
  const [loadingMultiBuilding, setLoadingMultiBuilding] = useState(false);

  // Load project data: ALWAYS use geodata API for building_walls
  // FIX 21.01.2026 01:00: Router State hat keine building_walls - IMMER API aufrufen!
  useEffect(() => {
    // FIX 10.01.2026 22:30 - Cache invalidieren wenn Projekt wechselt
    invalidateStoreIfProjectChanged(projectId);

    if (projectId) {
      // FIX 21.01.2026 01:00: IMMER loadProjectData aufrufen!
      // Die geodata API liefert building_walls für 3D-Wände.
      // Router State (passedProject) hat diese nicht, daher NICHT mehr verwenden.
      console.log('Loading project via geodata API (includes building_walls)');
      loadProjectData(projectId);
    }
  }, [projectId]);

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
  // FIX 24.01.2026: SSE soll API-Höhen NICHT überschreiben!
  // Die API liefert bereits korrekte relative Höhen (traufhoehe_m).
  // SSE-Berechnung aus wallMaxZ war FALSCH (Giebelspitze statt Traufe).
  useEffect(() => {
    if (!sseProjectBuildings || sseProjectBuildings.length === 0) return;
    if (!buildingData) return;

    // FIX 24.01.2026: Wenn API bereits gültige Traufhöhe geliefert hat, SSE-Update ÜBERSPRINGEN!
    // Die API berechnet traufhoehe_m = dach_min - terrain_min (korrekt)
    // SSE wallMaxZ-Fallback war FALSCH (enthält Giebelspitze, nicht Traufe)
    const apiTraufHeight = buildingData.building.trauf_height_m;
    if (apiTraufHeight && apiTraufHeight > 0 && apiTraufHeight < 50) {
      // API-Höhe ist plausibel (0-50m) - NICHT überschreiben
      console.log(`[SSE-Heights] API lieferte bereits trauf_height_m=${apiTraufHeight.toFixed(2)}m - SSE-Update übersprungen`);
      return;
    }

    // Ab hier: Nur wenn API KEINE gültige Höhe hatte (Fallback)
    const updatedBuilding = { ...buildingData.building };
    let hasChanges = false;

    // FIX 19.01.2026: Höhen aus ALLEN Gebäuden aggregieren (höchste Werte)
    let maxTrauf: number | null = null;
    let maxFirst: number | null = null;
    let minTerrainZ: number | null = null;

    for (const building of sseProjectBuildings) {
      if (building.terrain_z_min != null) {
        if (minTerrainZ === null || building.terrain_z_min < minTerrainZ) {
          minTerrainZ = building.terrain_z_min;
        }
      }
      if (building.roof_dach_min_m != null) {
        if (maxTrauf === null || building.roof_dach_min_m > maxTrauf) {
          maxTrauf = building.roof_dach_min_m;
        }
      }
      if (building.roof_dach_max_m != null) {
        if (maxFirst === null || building.roof_dach_max_m > maxFirst) {
          maxFirst = building.roof_dach_max_m;
        }
      }
    }

    console.log(`[SSE-Heights] Fallback-Berechnung: ${sseProjectBuildings.length} Gebäude, maxTrauf=${maxTrauf}, maxFirst=${maxFirst}, minTerrainZ=${minTerrainZ}`);

    // Terrain-Referenz aus Walls (für konsistente 3D-Darstellung)
    let effectiveTerrainZ = minTerrainZ;
    let wallMinZ = Infinity;

    if (buildingData.building_walls && buildingData.building_walls.length > 0) {
      for (const wall of buildingData.building_walls) {
        if (wall.z_min != null && wall.z_min < wallMinZ) {
          wallMinZ = wall.z_min;
        }
        // Auch aus geometry extrahieren falls z_min nicht gesetzt
        if (wall.geometry) {
          const processCoord = (coord: number[]) => {
            if (coord.length >= 3 && coord[2] < wallMinZ) {
              wallMinZ = coord[2];
            }
          };
          const processGeom = (geom: unknown) => {
            if (Array.isArray(geom)) {
              if (geom.length > 0 && typeof geom[0] === 'number') {
                processCoord(geom as number[]);
              } else {
                geom.forEach(g => processGeom(g));
              }
            }
          };
          processGeom(wall.geometry);
        }
      }
      if (wallMinZ !== Infinity) {
        console.log(`[SSE-Heights] Verwende wallMinZ=${wallMinZ.toFixed(1)} als Terrain-Referenz`);
        effectiveTerrainZ = wallMinZ;
      }
      // FIX 24.01.2026: ENTFERNT! wallMaxZ als Traufhöhe war FALSCH!
      // wallMaxZ enthält Giebelspitze (z.B. 567m), nicht Traufe (z.B. 562m)
      // Ergebnis war: 567 - 556 = 11m statt korrekt 562 - 556 = 6m
      // Die API liefert bereits korrekte traufhoehe_m - diese NICHT überschreiben!
    }

    // Relative Höhen berechnen (nur wenn SSE roof_dach_min_m hat)
    if (maxTrauf != null && effectiveTerrainZ != null) {
      const calculatedTrauf = maxTrauf - effectiveTerrainZ;
      if (calculatedTrauf !== updatedBuilding.trauf_height_m) {
        console.log(`[SSE-Heights] Fallback: Setze trauf_height_m=${calculatedTrauf.toFixed(2)}m`);
        updatedBuilding.trauf_height_m = calculatedTrauf;
        hasChanges = true;
      }
    }
    if (maxFirst != null && effectiveTerrainZ != null) {
      const calculatedFirst = maxFirst - effectiveTerrainZ;
      if (calculatedFirst !== updatedBuilding.first_height_m) {
        updatedBuilding.first_height_m = calculatedFirst;
        hasChanges = true;
      }
    }

    // Polygon NICHT mehr aus SSE übernehmen - kommt vom /geodata API als Union
    // FIX 19.01.2026: Das Polygon ist bereits das korrekte Union-Polygon

    // EGID: NICHT mehr aus SSE überschreiben!
    // FIX 19.01.2026: Das EGID wird beim Laden via /geodata korrekt gesetzt
    // (kombiniertes EGID wie "1234+5678" bei Multi-Building)
    // SSE-Daten sind NUR für Höhen-Updates, nicht für EGID

    if (hasChanges) {
      const newTraufHeight = updatedBuilding.trauf_height_m;
      console.log(`[SSE-Heights] Aktualisiere Traufhöhe: ${newTraufHeight.toFixed(2)}m`);
      setBuildingData(prev => {
        if (!prev) return prev;
        const oldTraufHeight = prev.building.trauf_height_m;
        // FIX 21.01.2026: Fassadenhöhen aktualisieren wenn:
        // - height_m ist 0 (nicht gesetzt)
        // - height_m entspricht der ALTEN Traufhöhe (nicht manuell geändert)
        // - height_m ist kleiner als die neue Traufhöhe UND nahe der alten (< 1m Differenz)
        //   Dies fängt den Fall ab, wenn Fassaden mit API-Wert erstellt wurden
        const updatedFacades = prev.selected_facades.map(facade => {
          const shouldUpdate = facade.height_m === 0
            || facade.height_m === oldTraufHeight
            || (facade.height_m < newTraufHeight && Math.abs(facade.height_m - oldTraufHeight) < 1);
          if (shouldUpdate) {
            console.log(`[SSE-Heights] Fassade ${facade.id}: ${facade.height_m.toFixed(2)}m → ${newTraufHeight.toFixed(2)}m`);
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
  // FIX 25.01.2026 BUG-030: Verwende SSE blocking_neighbors (Polygon-zu-Polygon Distanz)
  // statt Center-to-Center Filterung. Das SSE Event enthält nur Nachbarn die
  // tatsächlich Fassaden blockieren (Polygon-Distanz < 2m).
  const blockingNeighbors = useMemo((): NeighborBuilding[] => {
    // SSE blocking_neighbors hat korrekte Polygon-zu-Polygon Distanzen
    if (sseData.blockingNeighbors && sseData.blockingNeighbors.length > 0) {
      console.log(`[Blocking] Using SSE blocking_neighbors: ${sseData.blockingNeighbors.length} buildings`);
      // Konvertiere SSE-Format (number[][] | null) zu geruestbau.NeighborBuilding Format ([number, number][] | undefined)
      return sseData.blockingNeighbors.map(n => ({
        egid: n.egid,
        distance_m: n.distance_m,
        direction: n.direction,
        polygon: n.polygon ? n.polygon as [number, number][] : undefined,
        center_e: n.center_e,
        center_n: n.center_n,
        gebaeudehoehe_m: n.gebaeudehoehe_m,
        roof_dach_min_m: n.roof_dach_min_m,
        roof_dach_max_m: n.roof_dach_max_m,
      }));
    }
    // Fallback für nicht-SSE Modus (z.B. Adress-Suche ohne Projekt)
    const fallback = neighbors.filter(n => n.distance_m <= BLOCKING_THRESHOLD_M);
    if (fallback.length > 0) {
      console.log(`[Blocking] Using fallback (center distance filter): ${fallback.length} buildings`);
    }
    return fallback;
  }, [sseData.blockingNeighbors, neighbors]);

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
  const handleProjectLoaded = async (loadedProject: ProjectWithGeruestbaudata) => {
    // NEU 16.01.2026: buildings_data mit EGID als Key verwenden
    // Alle Gebäude sind gleichwertig - wir nehmen das erste für die Anzeige
    const egids = getBuildingEgids(loadedProject);
    const firstEgid = egids[0] || loadedProject.egid;

    // Gebäudedaten für die EGID laden
    let geodata: Geodata | null = null;
    if (firstEgid && loadedProject.buildings_data?.[firstEgid]) {
      // NEU: buildings_data mit EGID-Key
      geodata = convertGeruestbaudataToGeodata(loadedProject.buildings_data[firstEgid]);
      console.log(`[handleProjectLoaded] Using buildings_data for EGID ${firstEgid}`);
    } else if (loadedProject.geruestbaudata) {
      // Legacy-Fallback: geruestbaudata direkt
      geodata = convertGeruestbaudataToGeodata(loadedProject.geruestbaudata);
      console.log('[handleProjectLoaded] Legacy fallback: using geruestbaudata');
    }

    // Für bestehenden Code: Project mit geodata setzen
    const projectWithGeodata: ProjectWithGeruestbaudata = {
      ...loadedProject,
      geodata: geodata || undefined,
    };
    setProject(projectWithGeodata);

    // Check if project has geodata
    if (geodata?.polygon) {
      const configData = convertGeodataToConfiguratorFormat(
        projectWithGeodata,
        geodata
      );

      if (configData) {
        console.log('Using geruestbaudata from project - polygon is ORIGINAL from swissBUILDINGS3D');

        // Calculate roof from cached heights if not present
        // FIX 16.01.2026 17:00: Korrekte Berechnung aus Rohdaten
        if (!configData.roof && geodata) {
          const heights = extractHeights(geodata);  // Verwendet korrigierte Berechnung
          const trauf = heights.trauf;
          const first = heights.first;
          const roofHeight = first - trauf;

          // NEU 12.01.2026 22:45 - Echte Dach-Daten verwenden wenn has_3d_layers=true
          const has3DLayers = geodata.has_3d_layers === true;
          const realRoofType = geodata.roof_type;
          const realRoofOrientation = geodata.roof_orientation;
          const realRoofAngle = geodata.roof_angle_deg;

          // Fallback-Berechnung nur wenn keine echten Daten
          const fallbackAngle = roofHeight > 0.5 ? Math.atan(roofHeight / 5) * (180 / Math.PI) : 0;
          const fallbackOrientation = calculateRoofOrientation(geodata.polygon as [number, number][]);

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

        // NEU 19.01.2026: Objekt-Architektur
        // object_data wird vom Backend geliefert und enthält:
        // - polygon: Das Objekt-Polygon (IMMER vorhanden)
        // - projectBuildings: Metadaten aller Gebäude
        // - facades_object: Fassaden des Objekt-Polygons
        if (configData.object_data) {
          console.log(`[Objekt-Architektur] object_data vorhanden mit ${configData.object_data.building_count} Gebäude(n)`);
        } else if (egids.length > 1) {
          // Legacy-Fallback: Alte Projekte ohne object_data
          console.log(`[Legacy Multi-Building] Projekt hat ${egids.length} Gebäude, aber kein object_data - benötigt Migration`);
        }

        return;
      }
    }

    // Fallback: Use address to fetch from API (project not enriched yet)
    console.log('No geodata in cache, fetching from API');
    setAddress(loadedProject.address);
    await fetchBuildingData(loadedProject.address, loadedProject);
  };

  // Load project from API (fallback for direct links)
  // NEU 19.01.2026: Geodaten werden per separater API geladen (Architektur-Trennung)
  const loadProjectData = async (id: string) => {
    setLoadingState('loading');
    setError(null);

    // FIX 24.01.2026: Cache IMMER löschen bevor API-Daten geladen werden!
    // Die API liefert frische Höhendaten - der Cache darf diese NICHT überschreiben.
    // Problem war: Gleiche projectId = Cache wurde nicht invalidiert = falsche Höhen blieben.
    console.log('[loadProjectData] Clearing scaffold cache to ensure fresh API data');
    localStorage.removeItem('scaffold-config-storage');

    try {
      // 1. Projekt-Metadaten laden
      const loadedProject = await geruestbauApi.getProject(id);
      setProject(loadedProject);

      // 2. NEU: Geodaten per API laden (statt aus buildings_data/geruestbaudata)
      console.log('[loadProjectData] Loading geodata via API...');
      const geodataResponse = await geruestbauApi.getProjectGeodata(id, 100, true, true);
      console.log(`[loadProjectData] Geodata loaded: ${geodataResponse.project_buildings.length} project buildings, ${geodataResponse.neighbors.length} neighbors`);

      // DEBUG 21.01.2026: Detailliertes Logging für 3D-Walls-Problem
      const allApiWalls = geodataResponse.project_buildings.flatMap(b => b.walls ?? []);
      const wallsWithGeometry = allApiWalls.filter(w => w.geometry && w.geometry.length > 0);
      console.log(`[loadProjectData] DEBUG: ${allApiWalls.length} walls in API response, ${wallsWithGeometry.length} mit geometry`);
      if (wallsWithGeometry.length > 0) {
        console.log('[loadProjectData] DEBUG: Erste Wall mit geometry:', {
          z_min: wallsWithGeometry[0].z_min,
          z_max: wallsWithGeometry[0].z_max,
          geometry_type: wallsWithGeometry[0].geometry_type,
          geometry_len: wallsWithGeometry[0].geometry?.length
        });
      } else if (allApiWalls.length > 0) {
        console.log('[loadProjectData] DEBUG: KEINE Wall hat geometry! Erste Wall:', allApiWalls[0]);
      }

      // 3. Projekt-Polygon verarbeiten
      // NEU 19.01.2026: Ein Projekt = Ein Objekt. Das Union-Polygon kommt vom Backend.
      // Kein "Hauptgebäude" vs "Zusatzgebäude" - nur EIN Objekt-Polygon.
      const configData = convertGeodataResponseToConfiguratorFormat(
        geodataResponse,
        id,
        loadedProject.address
      );

      if (configData) {
        if (geodataResponse.project_buildings.length > 1) {
          console.log(`[loadProjectData] Multi-Building Projekt: ${geodataResponse.project_buildings.length} Gebäude → 1 Union-Polygon`);
        }

        console.log('[loadProjectData] Using geodata from API - Objekt-basierte Architektur aktiv');

        // DEBUG 21.01.2026: Prüfen ob building_walls in configData vorhanden
        const configWalls = configData.building_walls ?? [];
        const configWallsWithGeometry = configWalls.filter(w => w.geometry && w.geometry.length > 0);
        console.log(`[loadProjectData] DEBUG: configData hat ${configWalls.length} walls, ${configWallsWithGeometry.length} mit geometry`);

        setBuildingData(configData);
        setLoadingState('success');
        return; // Erfolgreich geladen via neue API
      }

      // 4. Fallback: Alte Methode (für Projekte ohne gespeicherte EGIDs)
      console.log('[loadProjectData] Fallback to legacy handleProjectLoaded');
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
    existingProject?: ProjectWithGeruestbaudata | null,
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
  // NEU 15.01.2026 BUG-024: Wendet building_walls Matching an für korrekte Höhen
  // NEU 24.01.2026 P3: Giebel-Erkennung mit dachMin Parameter
  const convertToSelectedFacades = (data: ConfiguratorBuildingData): SelectedFacade[] => {
    const buildingWalls = data.building_walls || [];
    // NEU 24.01.2026 P3: dachMin für Giebel-Erkennung (absolute Traufhöhe m ü.M.)
    const dachMin = data.roof?.roof_dach_min_m;

    return data.selected_facades.map((facade) => {
      let facadeZMin: number | undefined;
      let facadeZMax: number | undefined;
      let heightSource: 'building_walls' | 'global' | undefined;
      // FIX 15.01.2026 22:30: height_m aus Wall-Match statt API
      let heightM = facade.height_m;

      // NEU 15.01.2026 BUG-024: Geometrisches Matching mit building_walls
      // Extrahiert z-Werte für Terrain-Höhen, NICHT für Gerüsthöhe!
      // FIX 18.01.2026 BUG-026: wall_height NICHT als Fassaden-Höhe verwenden!
      // Giebel-Fassaden haben höhere Wände (bis First), aber das Gerüst soll
      // bei "Fassadenarbeit" nur bis zur TRAUFE gehen.
      // NEU 24.01.2026 P3: Giebel-Erkennung mit dachMin
      let isGiebel = false;
      let giebelHeightM: number | undefined;
      // NEU 27.01.2026: Terrain-Profil und Warnungen für Stellspindel-Berechnung
      let terrainProfile: SelectedFacade['terrain_profile'];
      let terrainWarnings: SelectedFacade['terrain_warnings'];

      if (buildingWalls.length > 0 && facade.start_point && facade.end_point) {
        const matchResult = matchFacadeToWall(
          facade.start_point,
          facade.end_point,
          buildingWalls,
          10.0,  // FIX 05.02.2026: Toleranz erhöht für besseres Matching
          dachMin  // NEU 24.01.2026 P3: Für Giebel-Erkennung
        );

        if (matchResult) {
          facadeZMin = matchResult.polygon_z_min;
          facadeZMax = matchResult.polygon_z_max;
          // FIX 05.02.2026: Maximum-Höhe vom höchsten Polygon entlang dieser Fassade.
          // wall_height = polygon_z_max - polygon_z_min für das Polygon mit der grössten Höhe.
          // Sicher: Lieber zu viel Gerüst als zu wenig (kann im Editor reduziert werden).
          heightM = matchResult.wall_height;
          heightSource = 'building_walls';
          // NEU 24.01.2026 P3: Giebel-Info übernehmen
          isGiebel = matchResult.is_giebel;
          giebelHeightM = matchResult.giebel_height_m;
          // NEU 27.01.2026: Terrain-Profil und Warnungen für Stellspindel-Berechnung
          terrainProfile = matchResult.terrain_profile;
          terrainWarnings = matchResult.terrain_warnings;
        }
      }

      return {
        id: facade.id,
        direction: facade.direction as SelectedFacade['direction'],
        length_m: facade.length_m,
        height_m: heightM,
        slope_percent: facade.slope_percent,
        start_point: facade.start_point,
        end_point: facade.end_point,
        facade_z_min: facadeZMin,
        facade_z_max: facadeZMax,
        height_source: heightSource,
        // NEU 24.01.2026 P3: Giebel-Erkennung
        is_giebel: isGiebel,
        giebel_height_m: giebelHeightM,
        // NEU 27.01.2026: Terrain-Profil und Warnungen für Stellspindel-Berechnung
        terrain_profile: terrainProfile,
        terrain_warnings: terrainWarnings,
      };
    });
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
          {/* FIX 04.02.2026: BuildingDataCard aus live Geodata-API, NICHT aus gespeicherter geruestbaudata */}
          {buildingData ? (() => {
            const bd = buildingData;
            const terrainRef = bd.roof?.terrain_z_min ?? 0;
            // Direkt die berechneten Werte verwenden — keine Magic Number Vergleiche
            const traufM = bd.building.trauf_height_m > 0 ? bd.building.trauf_height_m : undefined;
            const firstM = bd.building.first_height_m > 0 ? bd.building.first_height_m : undefined;
            const geruestbauData: GeruestbauData = {
              building: {
                egid: bd.building.egid,
                address: bd.building.address,
                polygon: bd.building.polygon as number[][],
                center_e: bd.building.center_e,
                center_n: bd.building.center_n,
                perimeter_m: bd.metadata?.perimeter_m ?? 0,
                area_m2: bd.metadata?.area_m2 ?? 0,
                has_3d_layers: (bd.building_walls?.length ?? 0) > 0,
                roof_dach_min_m: bd.roof?.roof_dach_min_m,
                roof_dach_max_m: bd.roof?.roof_dach_max_m,
              },
              facades: bd.selected_facades.map((f, idx) => ({
                index: idx,
                direction: f.direction,
                start_point: f.start_point,
                end_point: f.end_point,
                length_m: f.length_m,
                azimuth_deg: 0,
                terrain_z_min: terrainRef,
                terrain_z_max: terrainRef,
                wall_z_max: (bd.roof?.roof_dach_min_m ?? 0),
                height_m: f.height_m,
                slope_m: 0,
                height_source: (bd.building_walls?.length ?? 0) > 0 ? 'wall_layer' as const : 'global' as const,
              })),
              walls: bd.building_walls ?? [],
              roofs: bd.building_roofs ?? [],
              terrain: {
                height_m: terrainRef,
                min_m: terrainRef,
                max_m: terrainRef,
                slope_m: 0,
                slope_class: 'eben',
                requires_level_compensation: false,
              },
              zones: [],
              fetched_at: new Date().toISOString(),
              data_quality: (bd.building_walls?.length ?? 0) > 0 ? 'complete' : 'partial',
              heights: {
                traufhoehe_m: traufM,
                firsthoehe_m: firstM,
                source: (bd.building_walls?.length ?? 0) > 0 ? 'swissBUILDINGS3D' : 'gwr_estimated',
              },
            };
            return <BuildingDataCard data={geruestbauData} />;
          })() : project && (
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
                    // NEU 19.01.2026: Objekt-Architektur
                    // Multi-Building verwendet jetzt das Backend für "polygon" (Union)
                    setIsMultiMode(false);
                    setLoadingMultiBuilding(true);

                    try {
                      if (selectedBuildings.length === 1) {
                        // Single building - load directly
                        await fetchBuildingData(selectedBuildings[0].address, project);
                      } else if (selectedBuildings.length > 1) {
                        // Multi-Building: Lade mit kombinierter Adresse
                        // FIX 22.01.2026: combinedAddress VERWENDEN statt nur erste Adresse!
                        // Backend SmartBuildingService parst komma-getrennte Adressen
                        const combinedAddress = selectedBuildings.map(b => b.address).join(', ');
                        console.log(`[Objekt-Architektur] Lade ${selectedBuildings.length} Gebäude: ${combinedAddress}`);
                        await fetchBuildingData(combinedAddress, project);
                      }
                    } finally {
                      setLoadingMultiBuilding(false);
                    }
                  }}
                  disabled={selectedBuildings.length === 0 || loadingMultiBuilding}
                  className="flex-1 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loadingMultiBuilding
                    ? 'Lade Gebäudedaten...'
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
      buildingRoofs: data.building_roofs?.length ?? 0,
    });

    if (!data.roof) {
      console.warn('WARNING: No roof data in buildingData!');
      return undefined;
    }

    // NEU 15.01.2026 23:45: building_roofs.geometry für echte 3D-Dachgeometrie
    // FIX 19.01.2026: Umbenennung coords_3d → geometry (konsistent mit DB geometry_wkb)
    // Falls building_roofs vorhanden, extrahiere geometry als roof_geometry_coords
    let roofGeometryCoords = data.roof.roof_geometry_coords;
    let hasRoofGeometry = data.roof.has_roof_geometry;
    let roofDachMinM = data.roof.roof_dach_min_m;
    let roofDachMaxM = data.roof.roof_dach_max_m;

    if (data.building_roofs && data.building_roofs.length > 0) {
      // FIX 21.01.2026: ALLE Dächer kombinieren (nicht nur das erste!)
      // Bei Multi-Building-Projekten gibt es mehrere building_roofs
      const allRoofPolygons: number[][][] = [];
      let combinedDachMin: number | undefined;
      let combinedDachMax: number | undefined;

      data.building_roofs.forEach((roof, index) => {
        if (roof.geometry && roof.geometry_type) {
          // MultiPolygon: geometry ist [[[Polygon1]], [[Polygon2]], ...]
          // Polygon: geometry ist [[[Ring1], [Hole1], ...]]
          if (roof.geometry_type === 'MultiPolygon') {
            // Flatten: Extrahiere alle Polygone (nur exterior rings)
            const polygons = (roof.geometry as number[][][][]).map(
              (polygon) => polygon[0] // Nur exterior ring
            );
            allRoofPolygons.push(...polygons);
          } else if (roof.geometry_type === 'Polygon') {
            // Einzelnes Polygon: geometry ist [[[x,y,z], ...]]
            allRoofPolygons.push(roof.geometry[0] as number[][]);
          }

          console.log(`[BUILDING-ROOFS] Dach ${index + 1}/${data.building_roofs!.length}:`, {
            type: roof.geometry_type,
            polygons: roof.geometry_type === 'MultiPolygon'
              ? (roof.geometry as number[][][][]).length
              : 1,
          });
        }

        // dach_min/dach_max: Minimum und Maximum über alle Dächer
        if (roof.dach_min != null) {
          combinedDachMin = combinedDachMin === undefined
            ? roof.dach_min
            : Math.min(combinedDachMin, roof.dach_min);
        }
        if (roof.dach_max != null) {
          combinedDachMax = combinedDachMax === undefined
            ? roof.dach_max
            : Math.max(combinedDachMax, roof.dach_max);
        }
      });

      if (allRoofPolygons.length > 0) {
        roofGeometryCoords = allRoofPolygons;
        hasRoofGeometry = true;
        console.log('[BUILDING-ROOFS] Kombinierte Dächer:', {
          totalRoofs: data.building_roofs.length,
          totalPolygons: allRoofPolygons.length,
          dachMin: combinedDachMin,
          dachMax: combinedDachMax,
        });
      }

      if (combinedDachMin !== undefined) {
        roofDachMinM = combinedDachMin;
      }
      if (combinedDachMax !== undefined) {
        roofDachMaxM = combinedDachMax;
      }
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
      // NEU 15.01.2026 23:45: Echte 3D-Dachgeometrie aus building_roofs (Prio) oder roof_geometry_coords
      roof_geometry_coords: roofGeometryCoords,
      has_roof_geometry: hasRoofGeometry,
      roof_dach_min_m: roofDachMinM,
      roof_dach_max_m: roofDachMaxM,
      // NEU 16.01.2026 14:50: Niedrigste Terrain-Höhe für konsistente Gebäude/Dach-Berechnung
      // Wird in ScaffoldScene verwendet um buildingHeight = dach_min - terrain_z_min zu berechnen
      terrain_z_min: data.facade_z_min
        ? Math.min(...Object.values(data.facade_z_min))
        : undefined,
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
        // NEU 19.01.2026: Objekt-Architektur - object_data statt additionalBuildings
        objectData={buildingData.object_data}
        // Zonen-Daten für komplexe Gebäude (NEU 05.01.2026)
        zones={buildingData.zones}
        complexity={buildingData.complexity}
        researchSource={buildingData.research_source}
        // NEU 14.01.2026 21:30 - Fassaden-Höhen für Hanglage (pro Himmelsrichtung)
        facadeZMin={project?.geodata?.facade_z_min}
        facadeZMax={project?.geodata?.facade_z_max}
        // NEU 15.01.2026 BUG-024: BuildingWall für koordinatenbasiertes Matching
        buildingWalls={buildingData.building_walls}
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
