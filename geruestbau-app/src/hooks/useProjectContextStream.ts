/**
 * useProjectContextStream - React Hook für SSE-basiertes Projekt-Kontext Streaming.
 *
 * REFACTORED 10.01.2026 20:30 - Options werden an start() übergeben, nicht als Hook-Parameter.
 * Das verhindert Endlosschleifen durch sich ändernde Dependencies.
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
 * const { data, isLoading, start, stop } = useProjectContextStream();
 *
 * // Streaming starten mit Options
 * useEffect(() => {
 *   if (projectId) {
 *     start(projectId, { maxRadiusM: 100 });
 *   }
 *   return () => stop();
 * }, [projectId]); // NICHT start/stop als Dependencies!
 *
 * // Auf Events reagieren
 * useEffect(() => {
 *   if (data.blockedFacades) {
 *     setBlockedFacadesData(data.blockedFacades);
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

// FIX 16.01.2026 17:00: traufhoehe_m/firsthoehe_m ENTFERNT!
export interface ProjectBuildingData {
  egid: string;
  polygon: number[][] | null;
  center_e: number | null;
  center_n: number | null;
  gebaeudehoehe_m: number | null;
  // Rohdaten für Höhenberechnung (NEU 16.01.2026)
  roof_dach_min_m?: number | null;
  roof_dach_max_m?: number | null;
  terrain_z_min?: number | null;
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

// FIX 16.01.2026 17:00: traufhoehe_m/firsthoehe_m ENTFERNT!
export interface NeighborBuilding {
  egid: string;
  polygon: number[][] | null;
  distance_m: number;
  direction: string | null;
  center_e: number | null;
  center_n: number | null;
  gebaeudehoehe_m?: number | null;
  // Rohdaten für Höhenberechnung
  roof_dach_min_m?: number | null;
  roof_dach_max_m?: number | null;
  terrain_z_min?: number | null;
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

// NEU: Options werden an start() übergeben, nicht als Hook-Parameter
export interface StartOptions {
  maxRadiusM?: number;
  includeBlockedFacades?: boolean;
  includeNeighbors?: boolean;
}

// =============================================================================
// Hook
// =============================================================================

export function useProjectContextStream() {
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
   * Stabile Referenz (keine Dependencies).
   */
  const stop = useCallback(() => {
    if (eventSourceRef.current) {
      console.log('[SSE] Stopping stream');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsLoading(false);
  }, []);

  /**
   * Startet den Stream für ein Projekt.
   * REFACTORED: Options werden hier übergeben, nicht als Hook-Parameter.
   * Stabile Referenz (nur stop als Dependency).
   */
  const start = useCallback(
    (projectId: string, options: StartOptions = {}) => {
      const {
        maxRadiusM = 100,
        includeBlockedFacades = true,
        includeNeighbors = true,
      } = options;

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
      console.log(`[SSE] Starting stream: ${url}`);

      // EventSource erstellen
      const es = new EventSource(url);
      eventSourceRef.current = es;

      // Event Listener registrieren
      es.addEventListener('centroid', (e) => {
        const eventData: CentroidData = JSON.parse(e.data);
        console.log(`[SSE] centroid: ${eventData.building_count} buildings`);
        setData((prev) => ({ ...prev, centroid: eventData }));
      });

      es.addEventListener('project_buildings', (e) => {
        const eventData = JSON.parse(e.data);
        const buildings: ProjectBuildingData[] = eventData.buildings || [];
        console.log(`[SSE] project_buildings: ${buildings.length} buildings`);
        setData((prev) => ({ ...prev, projectBuildings: buildings }));
      });

      es.addEventListener('blocked_facades', (e) => {
        const eventData: BlockedFacadesData = JSON.parse(e.data);
        const egids = Object.keys(eventData);
        const totalBlocked = egids.reduce((sum, egid) => sum + eventData[egid].blocked_indices.length, 0);
        console.log(`[SSE] blocked_facades: ${totalBlocked} blocked across ${egids.length} buildings`);
        setData((prev) => ({ ...prev, blockedFacades: eventData }));
      });

      es.addEventListener('neighbors', (e) => {
        const eventData: NeighborsData = JSON.parse(e.data);
        console.log(`[SSE] neighbors (${eventData.radius_m}m): ${eventData.count} buildings`);
        setData((prev) => {
          const newNeighbors = new Map(prev.neighbors);
          newNeighbors.set(eventData.radius_m, eventData.buildings);
          return { ...prev, neighbors: newNeighbors };
        });
      });

      es.addEventListener('complete', (e) => {
        const eventData: CompleteData = JSON.parse(e.data);
        console.log(`[SSE] complete: ${eventData.duration_ms}ms, ${eventData.total_neighbors} neighbors`);
        setData((prev) => ({ ...prev, complete: eventData }));
        setIsLoading(false);
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
        console.error(`[SSE] error:`, errorData);
        setData((prev) => ({ ...prev, error: errorData }));
        setIsLoading(false);
        es.close();
      });

      // Verbindungsfehler
      es.onerror = () => {
        if (es.readyState === EventSource.CLOSED) {
          console.log('[SSE] Connection closed');
          setIsLoading(false);
        }
      };
    },
    [stop] // NUR stop als Dependency - stabile Referenz!
  );

  /**
   * Lädt den Kontext neu (mit gleichen Options).
   */
  const reload = useCallback((options?: StartOptions) => {
    if (projectIdRef.current) {
      start(projectIdRef.current, options);
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
