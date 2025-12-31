import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Camera, Ruler, FileText, MapPin, Building2, Calendar } from 'lucide-react'
import { geruestbauApi } from '../api/geruestbau'
import type { Project } from '../types/project'

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (id) {
      loadProject(id)
    }
  }, [id])

  const loadProject = async (projectId: string) => {
    try {
      const data = await geruestbauApi.getProject(projectId)
      setProject(data)
    } catch (error) {
      console.error('Fehler:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full"></div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">Projekt nicht gefunden</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Projekt-Info */}
      <div className="card">
        <h2 className="text-xl font-bold">{project.name}</h2>
        <div className="flex items-center gap-2 text-gray-500 mt-2">
          <MapPin size={16} />
          <span className="text-sm">{project.address}</span>
        </div>
        {project.client_name && (
          <div className="flex items-center gap-2 text-gray-500 mt-1">
            <Building2 size={16} />
            <span className="text-sm">{project.client_name}</span>
          </div>
        )}
        {project.egid && (
          <div className="text-xs text-gray-400 mt-2">
            EGID: {project.egid}
          </div>
        )}
      </div>

      {/* Gebäudedaten */}
      {project.building_data && (
        <div className="card">
          <h3 className="font-semibold mb-3">Gebäudedaten</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {project.building_data.heights?.traufhoehe_m && (
              <div>
                <span className="text-gray-500">Traufhöhe:</span>
                <span className="font-medium ml-2">
                  {project.building_data.heights.traufhoehe_m.toFixed(1)} m
                </span>
              </div>
            )}
            {project.building_data.heights?.firsthoehe_m && (
              <div>
                <span className="text-gray-500">Firsthöhe:</span>
                <span className="font-medium ml-2">
                  {project.building_data.heights.firsthoehe_m.toFixed(1)} m
                </span>
              </div>
            )}
            {project.building_data.gwr?.floors && (
              <div>
                <span className="text-gray-500">Geschosse:</span>
                <span className="font-medium ml-2">{project.building_data.gwr.floors}</span>
              </div>
            )}
            {project.building_data.gwr?.year_built && (
              <div>
                <span className="text-gray-500">Baujahr:</span>
                <span className="font-medium ml-2">{project.building_data.gwr.year_built}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Aktionen */}
      <div className="grid grid-cols-2 gap-3">
        <Link
          to={`/projects/${id}/photos`}
          className="card flex flex-col items-center py-6"
        >
          <Camera className="text-primary-600 mb-2" size={32} />
          <span className="font-medium">Fotos</span>
        </Link>
        <Link
          to={`/projects/${id}/scaffold`}
          className="card flex flex-col items-center py-6"
        >
          <Ruler className="text-primary-600 mb-2" size={32} />
          <span className="font-medium">Gerüst</span>
        </Link>
      </div>

      {/* Export */}
      <button className="card w-full flex items-center justify-center gap-2 py-4">
        <FileText className="text-gray-600" size={20} />
        <span className="font-medium">Offerte exportieren</span>
      </button>

      {/* Meta */}
      <div className="text-xs text-gray-400 text-center">
        <div className="flex items-center justify-center gap-1">
          <Calendar size={12} />
          Erstellt: {new Date(project.created_at).toLocaleDateString('de-CH')}
        </div>
      </div>
    </div>
  )
}
