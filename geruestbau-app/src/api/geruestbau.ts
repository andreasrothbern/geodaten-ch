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
