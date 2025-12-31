import { api } from './client'
import type { Project, ProjectCreate } from '../types/project'

export const geruestbauApi = {
  // Projekte
  listProjects: () =>
    api.get<Project[]>('/api/v1/geruestbau/projects'),

  getProject: (id: string) =>
    api.get<Project>(`/api/v1/geruestbau/projects/${id}`),

  createProject: (data: ProjectCreate) =>
    api.post<Project>('/api/v1/geruestbau/projects', data),

  updateProject: (id: string, data: Partial<Project>) =>
    api.put<Project>(`/api/v1/geruestbau/projects/${id}`, data),

  deleteProject: (id: string) =>
    api.delete(`/api/v1/geruestbau/projects/${id}`),

  // Geodaten
  enrichProject: (id: string) =>
    api.post<Project>(`/api/v1/geruestbau/projects/${id}/enrich`, {}),

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
}
