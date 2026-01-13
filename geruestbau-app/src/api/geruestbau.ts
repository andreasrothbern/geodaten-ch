import { api, API_BASE } from './client'
import type { Project, ProjectWithGeodata, ProjectCreate, ProjectUpdate, OcrExtractionResult } from '../types/project'

// Neighbors API Types
export interface NeighborBuilding {
  egid: string
  distance_m: number
  direction: string | null
  polygon?: [number, number][]
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

export interface AddressRangeBuilding {
  address: string
  matched_address?: string  // Full address from geocoding
  egid: string
  egid_source?: string
  polygon?: [number, number][]
  traufhoehe_m?: number
  firsthoehe_m?: number
  coordinates?: {
    lv95_e: number
    lv95_n: number
  }
}

// Multi-Building Data for 3D View
export interface MultiBuildingData {
  egid: string
  address: string
  polygon: [number, number][]
  center: [number, number]  // LV95 coordinates
  traufhoehe_m: number
  firsthoehe_m: number
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
export interface BlockedFacadeInfo {
  facade_index: number
  egid: string | null
  distance_m: number
  direction: string | null
}

export interface BlockedFacadesResponse {
  egid: string
  blocked_indices: number[]
  total_facades: number
  free_facades: number
  blocked_facades: BlockedFacadeInfo[]
  query_time_ms: number
}

export const geruestbauApi = {
  // Projekte
  listProjects: () =>
    api.get<Project[]>('/api/v1/geruestbau/projects'),

  getProject: (id: string) =>
    api.get<ProjectWithGeodata>(`/api/v1/geruestbau/projects/${id}`),

  createProject: (data: ProjectCreate) =>
    api.post<Project>('/api/v1/geruestbau/projects', data),

  updateProject: (id: string, data: ProjectUpdate) =>
    api.put<Project>(`/api/v1/geruestbau/projects/${id}`, data),

  deleteProject: (id: string) =>
    api.delete(`/api/v1/geruestbau/projects/${id}`),

  // Geodaten
  enrichProject: (id: string) =>
    api.post<ProjectWithGeodata>(`/api/v1/geruestbau/projects/${id}/enrich`, {}),

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
  extractFromDocument: async (file: File): Promise<OcrExtractionResult> => {
    const formData = new FormData()
    formData.append('file', file)

    const response = await fetch(
      `${API_BASE}/api/v1/geruestbau/extract`,
      {
        method: 'POST',
        body: formData,
        // Note: Don't set Content-Type header for FormData
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

      return {
        egid: data.egid || 'unknown',
        address: data.address_matched || address,
        polygon: data.polygon,
        center: [data.coordinates_lv95?.[0] || 0, data.coordinates_lv95?.[1] || 0],
        traufhoehe_m: data.traufhoehe_m || 10,
        firsthoehe_m: data.firsthoehe_m || 13,
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
