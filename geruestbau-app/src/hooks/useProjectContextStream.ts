/**
 * useProjectContextStream - React Hook für SSE-basiertes Projekt-Kontext Streaming.
 *
 * Nutzt Server-Sent Events (SSE) für progressive Datenlieferung:
 * 1. centroid - Projekt-Mittelpunkt (~10ms)
 * 2. project_buildings - Projekt-Gebäude mit Polygonen (~20ms)
 * 3. blocked_facades - Blockierte Fassaden pro Gebäude (~50ms)
 * 4. neighbors - Nachbarn in Schichten (20m, 50m, 100m)
 * 5. complete - Abschluss-Signal
 *
 * @example
 * ```tsx
 * const { data, isLoading, error, start, stop } = useProjectContextStream();
 *
 * // Streaming starten
 * start(projectId);
 *
 * // Auf Events reagieren
 * useEffect(() => {
 *   if (data.blockedFacades) {
 *     markBlockedFacades(data.blockedFacades);
 *   }
 * }, [data.blockedFacades]);
 * ```
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { API_BASE } from '../api/client';

// =============================================================================
// Types
// =============================================================================

export interface CentroidData {
  center_e: number;
  center_n: number;
  project_egids: string[];
  building_count: number;
}

export interface ProjectBuildingData {
  egid: string;
  polygon: number[][] | null;
  center_e: number | null;
  center_n: number | null;
  traufhoehe_m: number | null;
  firsthoehe_m: number | null;
  gebaeudehoehe_m: number | null;
}

export interface BlockerInfo {
  facade_index: number;
  egid: string | null;
  distance_m: number;
  direction: string | null;
}

export interface BlockedFacadesData {
  [egid: string]: {
    blocked_indices: number[];
    total_facades: number;
    free_facades: number;
    blockers: BlockerInfo[];
  };
}

export interface NeighborBuilding {
  egid: string;
  polygon: number[][] | null;
  distance_m: number;
  direction: string | null;
  center_e: number | null;
  center_n: number | null;
  traufhoehe_m: number | null;
  firsthoehe_m: number | null;
}

export interface NeighborsData {
  radius_m: number;
  count: number;
  buildings: NeighborBuilding[];
}

export interface CompleteData {
  status: string;
  duration_ms: number;
  project_buildings: number;
  total_neighbors: number;
}

export interface ErrorData {
  code: string;
  message: string;
}

export interface StreamState {
  centroid: CentroidData | null;
  projectBuildings: ProjectBuildingData[] | null;
  blockedFacades: BlockedFacadesData | null;
  neighbors: Map<number, NeighborBuilding[]>; // radius -> buildings
  complete: CompleteData | null;
  error: ErrorData | null;
}

export interface StreamOptions {
  maxRadiusM?: number;
  includeBlockedFacades?: boolean;
  includeNeighbors?: boolean;
  onCentroid?: (data: CentroidData) => void;
  onProjectBuildings?: (data: ProjectBuildingData[]) => void;
  onBlockedFacades?: (data: BlockedFacadesData) => void;
  onNeighbors?: (data: NeighborsData) => void;
  onComplete?: (data: CompleteData) => void;
  onError?: (data: ErrorData) => void;
}

// =============================================================================
// Hook
// =============================================================================

export function useProjectContextStream(options: StreamOptions = {}) {
  const {
    maxRadiusM = 100,
    includeBlockedFacades = true,
    includeNeighbors = true,
    onCentroid,
    onProjectBuildings,
    onBlockedFacades,
    onNeighbors,
    onComplete,
    onError,
  } = options;

  const [isLoading, setIsLoading] = useState(false);
  const [data, setData] = useState<StreamState>({
    centroid: null,
    projectBuildings: null,
    blockedFacades: null,
    neighbors: new Map(),
    complete: null,
    error: null,
  });

  const eventSourceRef = useRef<EventSource | null>(null);
  const projectIdRef = useRef<string | null>(null);

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
   * Startet den Stream für ein Projekt.
   */
  const start = useCallback(
    (projectId: string) => {
      // Bestehenden Stream stoppen
      stop();

      projectIdRef.current = projectId;
      setIsLoading(true);
      setData({
        centroid: null,
        projectBuildings: null,
        blockedFacades: null,
        neighbors: new Map(),
        complete: null,
        error: null,
      });

      // SSE URL bauen
      const params = new URLSearchParams({
        max_radius_m: maxRadiusM.toString(),
        include_blocked_facades: includeBlockedFacades.toString(),
        include_neighbors: includeNeighbors.toString(),
      });

      const url = `${API_BASE}/api/v1/geruestbau/projects/${projectId}/context/stream?${params}`;

      // EventSource erstellen
      const es = new EventSource(url);
      eventSourceRef.current = es;

      // Event Listener registrieren
      es.addEventListener('centroid', (e) => {
        const eventData: CentroidData = JSON.parse(e.data);
        setData((prev) => ({ ...prev, centroid: eventData }));
        onCentroid?.(eventData);
      });

      es.addEventListener('project_buildings', (e) => {
        const eventData = JSON.parse(e.data);
        const buildings: ProjectBuildingData[] = eventData.buildings || [];
        setData((prev) => ({ ...prev, projectBuildings: buildings }));
        onProjectBuildings?.(buildings);
      });

      es.addEventListener('blocked_facades', (e) => {
        const eventData: BlockedFacadesData = JSON.parse(e.data);
        setData((prev) => ({ ...prev, blockedFacades: eventData }));
        onBlockedFacades?.(eventData);
      });

      es.addEventListener('neighbors', (e) => {
        const eventData: NeighborsData = JSON.parse(e.data);
        setData((prev) => {
          const newNeighbors = new Map(prev.neighbors);
          newNeighbors.set(eventData.radius_m, eventData.buildings);
          return { ...prev, neighbors: newNeighbors };
        });
        onNeighbors?.(eventData);
      });

      es.addEventListener('complete', (e) => {
        const eventData: CompleteData = JSON.parse(e.data);
        setData((prev) => ({ ...prev, complete: eventData }));
        setIsLoading(false);
        onComplete?.(eventData);
        es.close();
      });

      es.addEventListener('error', (e) => {
        // SSE error event kann auch MessageEvent sein
        let errorData: ErrorData;
        try {
          errorData = JSON.parse((e as MessageEvent).data);
        } catch {
          errorData = {
            code: 'CONNECTION_ERROR',
            message: 'Verbindung zum Server fehlgeschlagen',
          };
        }
        setData((prev) => ({ ...prev, error: errorData }));
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
      maxRadiusM,
      includeBlockedFacades,
      includeNeighbors,
      onCentroid,
      onProjectBuildings,
      onBlockedFacades,
      onNeighbors,
      onComplete,
      onError,
    ]
  );

  /**
   * Lädt den Kontext neu.
   */
  const reload = useCallback(() => {
    if (projectIdRef.current) {
      start(projectIdRef.current);
    }
  }, [start]);

  // Cleanup bei Unmount
  useEffect(() => {
    return () => {
      stop();
    };
  }, [stop]);

  return {
    data,
    isLoading,
    error: data.error,
    start,
    stop,
    reload,
    // Convenience getters
    centroid: data.centroid,
    projectBuildings: data.projectBuildings,
    blockedFacades: data.blockedFacades,
    neighbors: data.neighbors,
    isComplete: data.complete !== null,
  };
}

export default useProjectContextStream;
