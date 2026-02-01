import { api, API_BASE } from './client'
import type { Project, ProjectWithGeruestbaudata, ProjectCreate, ProjectUpdate, OcrExtractionResult } from '../types/project'

// Neighbors API Types
export interface NeighborBuilding {
  egid: string
  distance_m: number
  direction: string | null
  polygon?: [number, number][]
  center_e?: number | null
  center_n?: number | null
  // NEU 21.01.2026: Höhendaten für heuristisches Dach
  gebaeudehoehe_m?: number | null
  roof_dach_min_m?: number | null
  roof_dach_max_m?: number | null
  terrain_z_min?: number | null
}

export interface NeighborsResponse {
  target_egid: string
  target_polygon: [number, number][]
  neighbors: NeighborBuilding[]
  blocked_sides: string[]
  query_time_ms: number
}

// Address Range API Types
export interface AddressRangeParsed {
  street: string
  city: string
  numbers: string[]
  range_type: 'single' | 'range' | 'explicit'
}

// FIX 16.01.2026 17:00: traufhoehe_m/firsthoehe_m ENTFERNT!
// Korrekte Höhen aus: roof_dach_min_m - terrain_z_min
export interface AddressRangeBuilding {
  address: string
  matched_address?: string  // Full address from geocoding
  egid: string
  egid_source?: string
  polygon?: [number, number][]
  // Rohdaten für Höhenberechnung (NEU 16.01.2026)
  roof_dach_min_m?: number   // Trauf absolut (m ü.M.)
  roof_dach_max_m?: number   // First absolut (m ü.M.)
  terrain_z_min?: number     // Niedrigstes Terrain (m ü.M.)
  gebaeudehoehe_m?: number   // Gebäudehöhe (relativ)
  coordinates?: {
    lv95_e: number
    lv95_n: number
  }
}

// =============================================================================
// NEU 19.01.2026: Objekt-basierte Architektur
// Ein Projekt = Ein Objekt. "polygon" ist IMMER vorhanden.
// =============================================================================

/**
 * Metadaten eines Gebäudes im Projekt (für projectBuildings[])
 * Nur Identifikation, keine Geometrie - die kommt aus "polygon"
 */
export interface ProjectBuildingMetadata {
  egid: string
  address: string
  center_e: number
  center_n: number
}

/**
 * Fassade des Objekt-Polygons (facades_object)
 */
export interface ObjectFacade {
  index: number
  direction: string
  length_m: number
  height_m: number
  start_point: [number, number]
  end_point: [number, number]
  azimuth_deg: number
}

/**
 * Objekt-Daten vom Backend (object_data in SSE Response)
 * Enthält "polygon" - das Objekt-Polygon für Gerüstplanung
 * Bei Single-Building: Das eine Polygon
 * Bei Multi-Building: Union aller Polygone (äussere Kontur)
 */
export interface ObjectData {
  polygon: [number, number][]         // Das Objekt-Polygon (IMMER vorhanden)
  facades_object: ObjectFacade[]      // Fassaden des Objekt-Polygons
  roof_object?: {
    z_min: number | null              // Tiefste Traufe (m ü.M.)
    z_max: number | null              // Höchster First (m ü.M.)
  }
  projectBuildings: ProjectBuildingMetadata[]  // Metadaten aller Gebäude
  total_area_m2: number
  total_perimeter_m: number
  avg_traufhoehe_m: number | null
  building_count: number
}

// =============================================================================
// DEPRECATED: Alte Interfaces (für Rückwärtskompatibilität)
// =============================================================================

/**
 * @deprecated Use ObjectFacade instead
 */
export interface MultiBuildingFacade {
  id: string
  direction: string
  length_m: number
  height_m: number
  start_point: [number, number]
  end_point: [number, number]
}

/**
 * @deprecated Use ObjectData + ProjectBuildingMetadata instead
 * Wird noch verwendet in Legacy-Code der additionalBuildings verwendet
 */
export interface MultiBuildingData {
  egid: string
  address: string
  polygon: [number, number][]
  center: [number, number]  // LV95 coordinates
  // Rohdaten für Höhenberechnung (NEU 16.01.2026)
  roof_dach_min_m?: number   // Trauf absolut (m ü.M.)
  roof_dach_max_m?: number   // First absolut (m ü.M.)
  terrain_z_min?: number     // Niedrigstes Terrain (m ü.M.)
  gebaeudehoehe_m?: number   // Gebäudehöhe (relativ) als Fallback
  // NEU 18.01.2026 BUG-027: Fassaden für Gerüst
  facades?: MultiBuildingFacade[]
}

export interface AddressRangeResponse {
  parsed: AddressRangeParsed
  buildings: AddressRangeBuilding[]
  building_count: number
  errors: string[]
  error_count: number
}

// Material Estimate API Types (NEU 15.01.2026)
export interface MaterialItem {
  article_id: string
  name: string
  category: string
  unit: string
  quantity_min: number
  quantity_typical: number
  quantity_max: number
  unit_weight_kg: number | null
  total_weight_kg: number | null
}

export interface MaterialEstimateSummary {
  total_pieces: number
  total_weight_kg: number
  total_weight_tons: number
  weight_per_m2_kg: number
  has_leveling: boolean
  leveling_pieces: number
  leveling_weight_kg: number
}

export interface MaterialEstimateResponse {
  system_id: string
  scaffold_area_m2: number
  short_field_ratio: number
  terrain_diff_m: number
  field_count: number
  materials: MaterialItem[]
  summary: MaterialEstimateSummary
}

// Blocked Facades API Types

// NEU 23.01.2026: Partielle Blockierung - nur Teile einer Fassade blockiert
export interface BlockedSegment {
  start_ratio: number  // 0.0-1.0 Position auf Fassade (0=Start, 1=Ende)
  end_ratio: number    // 0.0-1.0 Position auf Fassade
  blocker_egid: string
  min_distance_m: number
}

export interface BlockerInfo {
  egid: string
  distance_m: number
  direction: string  // N, NE, E, SE, S, SW, W, NW
}

export interface BlockedFacadeInfo {
  facade_index: number
  egid: string | null
  distance_m: number
  direction: string | null
  // NEU 23.01.2026: Partielle Blockierung
  blocked_segments?: BlockedSegment[]
  blockers?: BlockerInfo[]
  fully_blocked?: boolean  // true wenn >= 90% blockiert
}

export interface BlockedFacadesResponse {
  egid: string
  blocked_indices: number[]
  total_facades: number
  free_facades: number
  blocked_facades: BlockedFacadeInfo[]
  query_time_ms: number
}

// NEU 19.01.2026: Geodaten per API laden (Architektur-Trennung)
// Siehe: docs/architecture/ARCHITECTURE.md
export interface GeodataBuilding {
  egid: string
  polygon?: [number, number][]
  center_e?: number
  center_n?: number
  distance_m: number
  traufhoehe_m?: number
  firsthoehe_m?: number
  gebaeudehoehe_m?: number
  walls?: Array<{
    z_min: number
    z_max: number
    // FIX 20.01.2026: geometry_type aus API
    geometry_type?: 'Polygon' | 'MultiPolygon' | null
    // FIX 19.01.2026: Umbenennung coords_3d → geometry (konsistent mit DB geometry_wkb)
    // Polygon: [[[x,y,z], ...]] | MultiPolygon: [[[[x,y,z], ...]]]
    geometry?: number[][][] | number[][][][]
  }>
  // FIX 21.01.2026: geometry und geometry_type hinzufügen (wie Walls)
  roofs?: Array<{
    dach_min: number
    dach_max: number
    geometry_type?: 'Polygon' | 'MultiPolygon' | null
    // Polygon: [[[x,y,z], ...]] | MultiPolygon: [[[[x,y,z], ...]]]
    geometry?: number[][][] | number[][][][]
  }>
}

export interface ProjectGeodataResponse {
  // NEU 19.01.2026: Ein Projekt = Ein Objekt
  // polygon ist IMMER das Union-Polygon (auch bei Single-Building)
  polygon: [number, number][] | null  // Das Projekt-Polygon (Union aller Gebäude)
  project_buildings: GeodataBuilding[]  // Details für 3D-View (walls, roofs)
  neighbors: GeodataBuilding[]
  center: { e: number; n: number }
  radius_m: number
  buildings_count: number
  project_egids: string[]
  query_time_ms: number
}

export const geruestbauApi = {
  // Projekte
  listProjects: () =>
    api.get<Project[]>('/api/v1/geruestbau/projects'),

  getProject: (id: string) =>
    api.get<ProjectWithGeruestbaudata>(`/api/v1/geruestbau/projects/${id}`),

  // NEU 19.01.2026: Geodaten per API laden (ersetzt buildings_data)
  // Siehe: docs/architecture/ARCHITECTURE.md → "Koordinaten-basierte API Strategie"
  getProjectGeodata: async (
    projectId: string,
    radiusM: number = 100,
    includeWalls: boolean = true,
    includeRoofs: boolean = true
  ): Promise<ProjectGeodataResponse> => {
    const params = new URLSearchParams({
      radius_m: radiusM.toString(),
      include_walls: includeWalls.toString(),
      include_roofs: includeRoofs.toString(),
    })
    const response = await fetch(
      `${API_BASE}/api/v1/geruestbau/projects/${projectId}/geodata?${params}`
    )
    if (!response.ok) {
      throw new Error(`Geodata API error: ${response.status}`)
    }
    return response.json()
  },

  createProject: (data: ProjectCreate) =>
    api.post<Project>('/api/v1/geruestbau/projects', data),

  updateProject: (id: string, data: ProjectUpdate) =>
    api.put<Project>(`/api/v1/geruestbau/projects/${id}`, data),

  deleteProject: (id: string) =>
    api.delete(`/api/v1/geruestbau/projects/${id}`),

  // Fotos
  uploadPhoto: async (projectId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(
      `/api/v1/geruestbau/projects/${projectId}/photos`,
      { method: 'POST', body: formData }
    )
    return response.json()
  },

  analyzePhoto: (projectId: string, photoId: string) =>
    api.post(`/api/v1/geruestbau/projects/${projectId}/photos/${photoId}/analyze`, {}),

  // Export
  exportProject: (projectId: string, format: 'pdf' | 'xlsx' = 'pdf') =>
    api.post(`/api/v1/geruestbau/projects/${projectId}/export?format=${format}`, {}),

  // OCR-Extraktion aus Dokument (PDF/Foto)
  // NEU 01.02.2026: Optional GPS-Koordinaten (Fallback für iOS Safari)
  extractFromDocument: async (
    file: File,
    gpsCoords?: { lat: number; lon: number }
  ): Promise<OcrExtractionResult> => {
    const formData = new FormData()
    formData.append('file', file)

    // GPS als Query-Parameter falls vorhanden (Fallback für iOS Safari capture)
    let url = `${API_BASE}/api/v1/geruestbau/extract`
    if (gpsCoords) {
      url += `?fallback_lat=${gpsCoords.lat}&fallback_lon=${gpsCoords.lon}`
    }

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      // Note: Don't set Content-Type header for FormData
    })

    if (!response.ok) {
      const errorText = await response.text()
      return {
        success: false,
        confidence: 0,
        error: `Fehler: ${response.status} - ${errorText}`,
      }
    }

    return response.json()
  },

  // Adress-Bereich auflösen (z.B. "Knospenweg 2-10, Bern")
  resolveAddressRange: async (address: string): Promise<AddressRangeResponse> => {
    const response = await fetch(
      `${API_BASE}/api/v1/geruestbau/address/resolve?address=${encodeURIComponent(address)}`
    )
    if (!response.ok) {
      throw new Error(`Address resolve error: ${response.status}`)
    }
    return response.json()
  },

  // Nachbargebäude (für 3D-View und blockierte Fassaden)
  getNeighbors: async (egid: string, radiusM: number = 10, includePolygons: boolean = true) => {
    const response = await fetch(
      `${API_BASE}/api/v1/geruestbau/building/${egid}/neighbors?radius_m=${radiusM}&include_polygons=${includePolygons}`
    )
    if (!response.ok) {
      throw new Error(`Neighbors API error: ${response.status}`)
    }
    return response.json() as Promise<NeighborsResponse>
  },

  // Blockierte Fassaden (durch Nachbargebäude)
  getBlockedFacades: async (
    egid: string,
    excludeEgids?: string[],
    thresholdM: number = 2.0
  ): Promise<BlockedFacadesResponse> => {
    const params = new URLSearchParams({
      threshold_m: thresholdM.toString(),
    })
    if (excludeEgids && excludeEgids.length > 0) {
      params.set('exclude_egids', excludeEgids.join(','))
    }
    const response = await fetch(
      `${API_BASE}/api/v1/geruestbau/building/${egid}/blocked-facades?${params}`
    )
    if (!response.ok) {
      throw new Error(`Blocked Facades API error: ${response.status}`)
    }
    return response.json()
  },

  // Gebäude-Polygon für Multi-Building 3D-View
  getBuildingPolygon: async (address: string): Promise<MultiBuildingData | null> => {
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/smart-building/data?address=${encodeURIComponent(address)}&include_research=false&include_zones=false`
      )
      if (!response.ok) {
        console.warn(`Failed to get polygon for ${address}: ${response.status}`)
        return null
      }
      const data = await response.json()

      // Extract polygon and heights from smart-building response
      if (!data.polygon || data.polygon.length < 3) {
        console.warn(`No polygon for ${address}`)
        return null
      }

      // FIX 16.01.2026 17:00: Rohdaten statt berechnete Höhen
      return {
        egid: data.egid || 'unknown',
        address: data.address_matched || address,
        polygon: data.polygon,
        center: [data.coordinates_lv95?.[0] || 0, data.coordinates_lv95?.[1] || 0],
        // Rohdaten für korrekte Höhenberechnung
        roof_dach_min_m: data.roof?.roof_dach_min_m,
        roof_dach_max_m: data.roof?.roof_dach_max_m,
        terrain_z_min: data.roof?.terrain_z_min,
        gebaeudehoehe_m: data.gebaeudehoehe_m,
      }
    } catch (err) {
      console.warn(`Error fetching polygon for ${address}:`, err)
      return null
    }
  },

  // Materialliste schätzen (NEU 15.01.2026)
  estimateMaterials: async (params: {
    systemId?: string
    areaM2: number
    shortFieldRatio?: number
    terrainDiffM?: number
    fieldCount?: number
  }): Promise<MaterialEstimateResponse> => {
    const searchParams = new URLSearchParams({
      system_id: params.systemId || 'blitz70',
      area_m2: params.areaM2.toString(),
      short_field_ratio: (params.shortFieldRatio ?? 0.33).toString(),
      terrain_diff_m: (params.terrainDiffM ?? 0).toString(),
      field_count: (params.fieldCount ?? 0).toString(),
    })
    const response = await fetch(
      `${API_BASE}/api/v1/catalog/estimate?${searchParams}`
    )
    if (!response.ok) {
      throw new Error(`Material estimate error: ${response.status}`)
    }
    return response.json()
  },

  // NEU 01.02.2026: Upload mit Extraction-Result speichern
  uploadWithExtractionResult: async (
    projectId: string,
    file: File,
    extractionResult: OcrExtractionResult,
    direction?: string
  ): Promise<{ id: string; project_id: string; filename: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('extraction_result', JSON.stringify(extractionResult))
    if (direction) {
      formData.append('direction', direction)
    }

    const response = await fetch(
      `${API_BASE}/api/v1/geruestbau/projects/${projectId}/uploads`,
      {
        method: 'POST',
        body: formData,
      }
    )

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Upload failed: ${response.status} - ${errorText}`)
    }

    return response.json()
  },

  // URL-Import (simap.ch)
  extractFromUrl: async (url: string): Promise<OcrExtractionResult> => {
    const response = await fetch(
      `${API_BASE}/api/v1/geruestbau/import/url`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      }
    )

    if (!response.ok) {
      const errorText = await response.text()
      return {
        success: false,
        confidence: 0,
        error: `Fehler: ${response.status} - ${errorText}`,
      }
    }

    return response.json()
  },
}
