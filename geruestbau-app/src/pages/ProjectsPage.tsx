import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, Building2 } from 'lucide-react'
import { geruestbauApi } from '../api/geruestbau'
import type { Project } from '../types/project'

const statusLabels: Record<string, { label: string; color: string }> = {
  draft: { label: 'Entwurf', color: 'bg-gray-100 text-gray-600' },
  captured: { label: 'Erfasst', color: 'bg-yellow-100 text-yellow-700' },
  enriched: { label: 'Angereichert', color: 'bg-blue-100 text-blue-700' },
  reviewed: { label: 'Geprüft', color: 'bg-purple-100 text-purple-700' },
  planned: { label: 'Geplant', color: 'bg-green-100 text-green-700' },
  quoted: { label: 'Offeriert', color: 'bg-orange-100 text-orange-700' },
  commissioned: { label: 'Beauftragt', color: 'bg-primary-100 text-primary-700' },
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      const data = await geruestbauApi.listProjects()
      setProjects(data)
    } catch (err) {
      setError('Fehler beim Laden der Projekte')
      console.error(err)
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

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">{error}</p>
        <button onClick={loadProjects} className="btn-secondary mt-4">
          Erneut versuchen
        </button>
      </div>
    )
  }

  if (projects.length === 0) {
    return (
      <div className="text-center py-12">
        <Building2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-700">Keine Projekte</h3>
        <p className="text-gray-500 mt-2">Erstellen Sie Ihr erstes Projekt</p>
        <Link to="/projects/new" className="btn-primary mt-6 inline-block">
          Neues Projekt
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {projects.map((project) => {
        const status = statusLabels[project.status] || statusLabels.draft
        return (
          <Link
            key={project.id}
            to={`/projects/${project.id}`}
            className="card flex items-center gap-3"
          >
            <div className="flex-1">
              <h3 className="font-semibold">{project.name}</h3>
              <p className="text-sm text-gray-500 truncate">{project.address}</p>
              <span className={`text-xs px-2 py-1 rounded-full mt-2 inline-block ${status.color}`}>
                {status.label}
              </span>
            </div>
            <ChevronRight className="text-gray-400" size={20} />
          </Link>
        )
      })}
    </div>
  )
}
