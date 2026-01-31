/**
 * useBuildingDataStream - React Hook für SSE-basiertes Laden von Gebäudedaten.
 *
 * Nutzt Server-Sent Events (SSE) für progressive Datenlieferung bei Projekt-Erstellung:
 * 1. geocoding - Adress-Match, Koordinaten (~50ms)
 * 2. gwr - GWR-Daten (Geschosse, Kategorie) (~100ms)
 * 3. polygon - Gebäude-Polygon (~200ms oder ~5s bei Download)
 * 4. heights - Höhendaten (~50ms)
 * 5. terrain - Terrain-Höhe, Hanglage (~200ms)
 * 6. zones - Zonen-Analyse (~500ms)
 * 7. research - Gebäudename (~1s)
 * 8. complete - Vollständiges Bundle
 *
 * @example
 * ```tsx
 * const {
 *   data,
 *   isLoading,
 *   currentStep,
 *   progress,
 *   start
 * } = useBuildingDataStream({
 *   onPolygon: (data) => renderPolygon(data.polygon),
 *   onComplete: (data) => createProject(data.bundle)
 * });
 *
 * // Starten mit Adresse
 * start("Kramgasse 10, Bern");
 *
 * // Progress anzeigen
 * <ProgressBar value={progress} label={currentStep} />
 * ```
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { API_BASE } from '../api/client';

// =============================================================================
// Types
// =============================================================================

export type StreamStep =
  | 'idle'
  | 'geocoding'
  | 'gwr'
  | 'polygon'
  | 'polygon_progress'
  | 'heights'
  | 'terrain'
  | 'zones'
  | 'research'
  | 'complete'
  | 'error';

export interface GeocodingData {
  matched_address: string;
  egid: string | null;
  coordinates: {
    lv95_e: number;
    lv95_n: number;
  };
  duration_ms: number;
}

export interface GWRData {
  egid: string | null;
  floors: number | null;
  area_m2: number | null;
  category: number | null;
  year_built: number | null;
  apartments: number | null;
  duration_ms: number;
  error?: string;
}

export interface PolygonData {
  polygon: number[][] | null;
  sides: Array<{
    start: { x: number; y: number };
    end: { x: number; y: number };
    length_m: number;
  }> | null;
  perimeter_m: number | null;
  area_m2: number | null;
  egid: string | null;
  cache_hit: boolean;
  duration_ms: number;
  error?: string;
}

// FIX 16.01.2026 17:00: traufhoehe_m/firsthoehe_m ENTFERNT!
// Korrekte Höhen berechnen: roof_dach_min_m - terrain_z_min
export interface HeightsData {
  gebaeudehoehe_m: number | null;
  source: string;
  duration_ms: number;
  // 3D-Layer Daten (swissBUILDINGS3D Roof/Wall)
  has_3d_layers?: boolean;
  has_roof_geometry?: boolean;
  roof_dach_min_m?: number | null;  // Traufhöhe absolut (m ü.M.)
  roof_dach_max_m?: number | null;  // Firsthöhe absolut (m ü.M.)
  terrain_z_min?: number | null;    // Niedrigstes Terrain (m ü.M.) für korrekte Berechnung
  roof_gebaeudeeinheit?: string | null;
  // Dach-Analyse Daten (für 3D-Viewer)
  roof_type?: string | null;  // flachdach, satteldach, walmdach, etc.
  roof_orientation?: string | null;  // 'N-S' oder 'O-W' (First-Verlauf)
  roof_angle_deg?: number | null;  // Dachneigung in Grad
}

// FIX 29.01.2026: slope_m/slope_class ENTFERNT (Frontend berechnet aus building_walls.geometry)
export interface TerrainData {
  terrain_height_m: number | null;
  min_terrain_m?: number;
  max_terrain_m?: number;
  // DEPRECATED 29.01.2026: slope_m, slope_class - Frontend berechnet aus building_walls.geometry
  // NEU 14.01.2026 (T3/T4) - Fassaden-Höhen aus Wall-Layer
  facade_z_min?: Record<string, number>;
  facade_z_max?: Record<string, number>;
  facade_heights_source?: 'wall_layer' | 'terrain_sampled' | 'global';
  duration_ms: number;
  error?: string;
}

export interface ZoneData {
  id: string;
  name: string;
  zone_type: string;
  traufhoehe_m: number | null;
  firsthoehe_m: number | null;
  beruesten: boolean;
}

export interface ZonesData {
  zones: ZoneData[];
  complexity: 'simple' | 'complex';
  source: string;
  building_name?: string;
  duration_ms: number;
  error?: string;
}

export interface ResearchData {
  building_name: string | null;
  building_type?: string;
  architectural_style?: string;
  source: string;
  duration_ms: number;
  error?: string;
}

export interface CompleteData {
  status: string;
  duration_ms: number;
  address: string;
  egid: string | null;
  summary: {
    has_polygon: boolean;
    has_heights: boolean;
    has_terrain: boolean;
    zones_count: number;
    complexity: string;
  };
  bundle: BuildingDataBundle;
  // NEU 18.01.2026: Multi-Building Support
  building_count?: number;
  buildings?: Array<{
    egid: string;
    matched_address: string;
    summary: {
      has_polygon: boolean;
      has_heights: boolean;
      has_terrain: boolean;
      zones_count: number;
      complexity: string;
      quality: string;
    };
    bundle: BuildingDataBundle;
  }>;
  // NEU 19.01.2026: Objekt-Daten (Ein Projekt = Ein Objekt)
  // "polygon" ist IMMER vorhanden (Single- und Multi-Building)
  object_data?: {
    polygon: [number, number][];            // Das Objekt-Polygon (IMMER vorhanden)
    facades_object: Array<{                 // Fassaden des Objekt-Polygons
      index: number;
      direction: string;
      start_point: [number, number];
      end_point: [number, number];
      length_m: number;
      azimuth_deg: number;
      height_m: number;
    }>;
    roof_object?: {
      z_min: number | null;                 // Tiefste Traufe (m ü.M.)
      z_max: number | null;                 // Höchster First (m ü.M.)
    };
    projectBuildings: Array<{               // Metadaten aller Gebäude im Projekt
      egid: string;
      address: string;
      center_e: number;
      center_n: number;
    }>;
    total_area_m2: number;
    total_perimeter_m: number;
    avg_traufhoehe_m: number | null;
    building_count: number;
  };
}

// Bundle-Struktur wie vom Backend geliefert (flach, nicht nested)
export interface BuildingDataBundle {
  // Adresse
  address_input: string;
  address_matched: string | null;
  // Identifikation
  egid: string | null;
  lv95_e: number | null;
  lv95_n: number | null;
  // Polygon & Fassaden
  polygon: number[][] | null;
  sides: Array<{
    index: number;
    start: { x: number; y: number };
    end: { x: number; y: number };
    start_point: number[];
    end_point: number[];
    length_m: number;
    azimuth_deg: number;
    angle_deg: number;
    normal_azimuth_deg: number;
    direction: string;
  }> | null;
  perimeter_m: number | null;
  footprint_area_m2: number | null;
  // Höhen - FIX 16.01.2026: traufhoehe_m/firsthoehe_m ENTFERNT!
  gebaeudehoehe_m: number | null;
  // GWR-Daten
  gwr_floors: number | null;
  gwr_area_m2: number | null;
  gwr_category: string | null;
  gwr_category_code: number | null;
  // Terrain - FIX 29.01.2026: slope_m/slope_class ENTFERNT (Frontend berechnet)
  terrain: {
    reference_height_m: number;
    min_height_m: number;
    max_height_m: number;
    // DEPRECATED 29.01.2026: slope_m, slope_class - Frontend berechnet aus building_walls.geometry
    // NEU 14.01.2026 (T3/T4) - Fassaden-Höhen aus Wall-Layer
    facade_z_min?: Record<string, number>;
    facade_z_max?: Record<string, number>;
    facade_heights_source?: 'wall_layer' | 'terrain_sampled' | 'global';
  } | null;
  // Zonen
  zones: ZoneData[] | null;
  complexity: string | null;
  // Research
  building_name: string | null;
  building_type: string | null;
  architectural_style: string | null;
  research_source: string | null;
  // NEU 12.01.2026 22:15 - 3D-Layer Daten (swissBUILDINGS3D Roof/Wall)
  has_3d_layers?: boolean;
  has_roof_geometry?: boolean;
  roof_dach_min_m?: number | null;  // Traufhöhe absolut (m ü.M.)
  roof_dach_max_m?: number | null;  // Firsthöhe absolut (m ü.M.)
  roof_gebaeudeeinheit?: string | null;
  // NEU 12.01.2026 22:45 - Dach-Analyse Daten (für 3D-Viewer)
  roof_type?: string | null;  // flachdach, satteldach, walmdach, etc.
  roof_orientation?: string | null;  // 'N-S' oder 'O-W' (First-Verlauf)
  roof_angle_deg?: number | null;  // Dachneigung in Grad
}

export interface ErrorData {
  code: string;
  message: string;
  step: string;
}

export interface StreamState {
  geocoding: GeocodingData | null;
  gwr: GWRData | null;
  polygon: PolygonData | null;
  heights: HeightsData | null;
  terrain: TerrainData | null;
  zones: ZonesData | null;
  research: ResearchData | null;
  complete: CompleteData | null;
  error: ErrorData | null;
  isDownloading: boolean; // True wenn Tile-Download läuft
}

export interface StreamOptions {
  includeResearch?: boolean;
  includeZones?: boolean;
  includeTerrain?: boolean;
  forceRefresh?: boolean;
  onGeocoding?: (data: GeocodingData) => void;
  onGWR?: (data: GWRData) => void;
  onPolygon?: (data: PolygonData) => void;
  onHeights?: (data: HeightsData) => void;
  onTerrain?: (data: TerrainData) => void;
  onZones?: (data: ZonesData) => void;
  onResearch?: (data: ResearchData) => void;
  onComplete?: (data: CompleteData) => void;
  onError?: (data: ErrorData) => void;
  onProgress?: (step: StreamStep, progress: number) => void;
}

// =============================================================================
// Constants
// =============================================================================

const STEP_ORDER: StreamStep[] = [
  'geocoding',
  'gwr',
  'polygon',
  'heights',
  'terrain',
  'zones',
  'research',
  'complete',
];

const STEP_LABELS: Record<StreamStep, string> = {
  idle: 'Bereit',
  geocoding: 'Adresse suchen...',
  gwr: 'GWR-Daten laden...',
  polygon: 'Gebäudegeometrie laden...',
  polygon_progress: 'Gebäudedaten herunterladen...',
  heights: 'Höhendaten laden...',
  terrain: 'Terrain analysieren...',
  zones: 'Zonen analysieren...',
  research: 'Gebäude recherchieren...',
  complete: 'Fertig',
  error: 'Fehler',
};

// =============================================================================
// Hook
// =============================================================================

export function useBuildingDataStream(options: StreamOptions = {}) {
  const {
    includeResearch = true,
    includeZones = true,
    includeTerrain = true,
    forceRefresh = false,
    onGeocoding,
    onGWR,
    onPolygon,
    onHeights,
    onTerrain,
    onZones,
    onResearch,
    onComplete,
    onError,
    onProgress,
  } = options;

  const [isLoading, setIsLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState<StreamStep>('idle');
  const [data, setData] = useState<StreamState>({
    geocoding: null,
    gwr: null,
    polygon: null,
    heights: null,
    terrain: null,
    zones: null,
    research: null,
    complete: null,
    error: null,
    isDownloading: false,
  });

  const eventSourceRef = useRef<EventSource | null>(null);
  const addressRef = useRef<string | null>(null);

  /**
   * Berechnet Fortschritt (0-100) basierend auf aktuellem Schritt.
   */
  const getProgress = useCallback((step: StreamStep): number => {
    const idx = STEP_ORDER.indexOf(step);
    if (idx === -1) return 0;
    return Math.round(((idx + 1) / STEP_ORDER.length) * 100);
  }, []);

  /**
   * Stoppt den aktuellen Stream.
   */
  const stop = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsLoading(false);
  }, []);

  /**
   * Startet den Stream für eine Adresse.
   */
  const start = useCallback(
    (address: string) => {
      // Bestehenden Stream stoppen
      stop();

      addressRef.current = address;
      setIsLoading(true);
      setCurrentStep('geocoding');
      setData({
        geocoding: null,
        gwr: null,
        polygon: null,
        heights: null,
        terrain: null,
        zones: null,
        research: null,
        complete: null,
        error: null,
        isDownloading: false,
      });

      // SSE URL bauen
      const params = new URLSearchParams({
        address,
        include_research: includeResearch.toString(),
        include_zones: includeZones.toString(),
        include_terrain: includeTerrain.toString(),
        force_refresh: forceRefresh.toString(),
      });

      const url = `${API_BASE}/api/v1/geruestbau/building/data/stream?${params}`;

      // EventSource erstellen
      const es = new EventSource(url);
      eventSourceRef.current = es;

      // Event Listener
      es.addEventListener('geocoding', (e) => {
        const eventData: GeocodingData = JSON.parse(e.data);
        setData((prev) => ({ ...prev, geocoding: eventData }));
        setCurrentStep('geocoding');
        onProgress?.('geocoding', getProgress('geocoding'));
        onGeocoding?.(eventData);
      });

      es.addEventListener('gwr', (e) => {
        const eventData: GWRData = JSON.parse(e.data);
        setData((prev) => ({ ...prev, gwr: eventData }));
        setCurrentStep('gwr');
        onProgress?.('gwr', getProgress('gwr'));
        onGWR?.(eventData);
      });

      es.addEventListener('polygon_progress', () => {
        // Tile-Download läuft
        setData((prev) => ({ ...prev, isDownloading: true }));
        setCurrentStep('polygon_progress');
        onProgress?.('polygon_progress', getProgress('polygon'));
      });

      es.addEventListener('polygon', (e) => {
        const eventData: PolygonData = JSON.parse(e.data);
        setData((prev) => ({ ...prev, polygon: eventData, isDownloading: false }));
        setCurrentStep('polygon');
        onProgress?.('polygon', getProgress('polygon'));
        onPolygon?.(eventData);
      });

      es.addEventListener('heights', (e) => {
        const eventData: HeightsData = JSON.parse(e.data);
        setData((prev) => ({ ...prev, heights: eventData }));
        setCurrentStep('heights');
        onProgress?.('heights', getProgress('heights'));
        onHeights?.(eventData);
      });

      es.addEventListener('terrain', (e) => {
        const eventData: TerrainData = JSON.parse(e.data);
        setData((prev) => ({ ...prev, terrain: eventData }));
        setCurrentStep('terrain');
        onProgress?.('terrain', getProgress('terrain'));
        onTerrain?.(eventData);
      });

      es.addEventListener('zones', (e) => {
        const eventData: ZonesData = JSON.parse(e.data);
        setData((prev) => ({ ...prev, zones: eventData }));
        setCurrentStep('zones');
        onProgress?.('zones', getProgress('zones'));
        onZones?.(eventData);
      });

      es.addEventListener('research', (e) => {
        const eventData: ResearchData = JSON.parse(e.data);
        setData((prev) => ({ ...prev, research: eventData }));
        setCurrentStep('research');
        onProgress?.('research', getProgress('research'));
        onResearch?.(eventData);
      });

      es.addEventListener('complete', (e) => {
        const eventData: CompleteData = JSON.parse(e.data);
        setData((prev) => ({ ...prev, complete: eventData }));
        setCurrentStep('complete');
        setIsLoading(false);
        onProgress?.('complete', 100);
        onComplete?.(eventData);
        es.close();
      });

      es.addEventListener('error', (event) => {
        let errorData: ErrorData;
        try {
          errorData = JSON.parse((event as MessageEvent).data);
        } catch {
          errorData = {
            code: 'CONNECTION_ERROR',
            message: 'Verbindung zum Server fehlgeschlagen',
            step: 'unknown',
          };
        }
        setData((prev) => ({ ...prev, error: errorData }));
        setCurrentStep('error');
        setIsLoading(false);
        onError?.(errorData);
        es.close();
      });

      // Verbindungsfehler
      es.onerror = () => {
        if (es.readyState === EventSource.CLOSED) {
          setIsLoading(false);
        }
      };
    },
    [
      stop,
      includeResearch,
      includeZones,
      includeTerrain,
      forceRefresh,
      getProgress,
      onGeocoding,
      onGWR,
      onPolygon,
      onHeights,
      onTerrain,
      onZones,
      onResearch,
      onComplete,
      onError,
      onProgress,
    ]
  );

  /**
   * Lädt die Daten neu.
   */
  const reload = useCallback(() => {
    if (addressRef.current) {
      start(addressRef.current);
    }
  }, [start]);

  // Cleanup bei Unmount
  useEffect(() => {
    return () => {
      stop();
    };
  }, [stop]);

  return {
    // State
    data,
    isLoading,
    currentStep,
    stepLabel: STEP_LABELS[currentStep],
    progress: getProgress(currentStep),
    error: data.error,
    isDownloading: data.isDownloading,

    // Actions
    start,
    stop,
    reload,

    // Convenience getters
    geocoding: data.geocoding,
    gwr: data.gwr,
    polygon: data.polygon,
    heights: data.heights,
    terrain: data.terrain,
    zones: data.zones,
    research: data.research,
    bundle: data.complete?.bundle ?? null,
    isComplete: data.complete !== null,

    // Computed
    address: data.geocoding?.matched_address ?? null,
    egid: data.polygon?.egid ?? data.geocoding?.egid ?? null,
    coordinates: data.geocoding?.coordinates ?? null,
  };
}

export default useBuildingDataStream;
