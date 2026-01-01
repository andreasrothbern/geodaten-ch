#!/usr/bin/env python3
"""Write the updated ProjectDetailPage.tsx content."""

content = '''import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  Camera,
  Ruler,
  FileText,
  MapPin,
  Building2,
  Calendar,
  ArrowRight,
  Layers,
  CheckCircle2,
} from 'lucide-react'
import { geruestbauApi } from '../api/geruestbau'
import type { Project } from '../types/project'

// Progress step configuration (same as ProjectsPage)
const PROGRESS_STEPS = [
  { id: 1, label: 'Import', shortLabel: 'Import' },
  { id: 2, label: 'Fassaden', shortLabel: 'Fassaden' },
  { id: 3, label: 'Geruest', shortLabel: 'Geruest' },
  { id: 4, label: 'Dokumente', shortLabel: 'Doku' },
  { id: 5, label: 'Export', shortLabel: 'Export' },
]

// Map project status to progress step
function getProgressStep(status: string): number {
  switch (status) {
    case 'draft':
      return 1
    case 'captured':
      return 2
    case 'enriched':
      return 2
    case 'reviewed':
      return 3
    case 'planned':
      return 4
    case 'quoted':
      return 5
    case 'commissioned':
      return 6
    default:
      return 1
  }
}

function ProgressSteps({ currentStep }: { currentStep: number }) {
  return (
    <div className="mt-4">
      <div className="flex items-center gap-1">
        {PROGRESS_STEPS.map((step, index) => {
          const isCompleted = step.id < currentStep
          const isCurrent = step.id === currentStep
          const isPending = step.id > currentStep
          return (
            <div key={step.id} className="flex items-center flex-1 last:flex-none">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-all duration-300 ${
                  isCompleted ? 'bg-green-500 text-white' : ''
                } ${isCurrent ? 'bg-red-600 text-white animate-pulse' : ''} ${
                  isPending ? 'bg-gray-200 text-gray-400' : ''
                }`}
              >
                {isCompleted ? '\\u2713' : step.id}
              </div>
              {index < PROGRESS_STEPS.length - 1 && (
                <div
                  className={`flex-1 h-1 mx-1 rounded ${isCompleted ? 'bg-green-500' : ''} ${
                    isCurrent ? 'bg-red-300' : ''
                  } ${isPending ? 'bg-gray-200' : ''}`}
                />
              )}
            </div>
          )
        })}
      </div>
      <div className="flex justify-between text-xs text-gray-400 mt-1 px-0.5">
        {PROGRESS_STEPS.map((step) => (
          <span
            key={step.id}
            className={step.id === currentStep ? 'text-red-600 font-medium' : ''}
          >
            {step.shortLabel}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
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

  const currentStep = getProgressStep(project.status)
  const needsFacadeSelection = ['draft', 'captured', 'enriched'].includes(project.status)

  return (
    <div className="space-y-4 pb-24">
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
          <div className="text-xs text-gray-400 mt-2">EGID: {project.egid}</div>
        )}

        {/* Progress Steps */}
        <ProgressSteps currentStep={currentStep} />
      </div>

      {/* Next Step Action - prominent CTA */}
      {needsFacadeSelection && (
        <button
          onClick={() => navigate(`/projects/${id}/facades`)}
          className="w-full card bg-red-600 text-white hover:bg-red-700 transition-colors"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Layers className="w-6 h-6" />
              <div className="text-left">
                <p className="font-semibold">Fassaden auswaehlen</p>
                <p className="text-sm text-red-200">Naechster Schritt</p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5" />
          </div>
        </button>
      )}

      {/* Gebaeudedaten */}
      {project.building_data && (
        <div className="card">
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-green-500" />
            Gebaeudedaten
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {project.building_data.heights?.traufhoehe_m && (
              <div>
                <span className="text-gray-500">Traufhoehe:</span>
                <span className="font-medium ml-2">
                  {project.building_data.heights.traufhoehe_m.toFixed(1)} m
                </span>
              </div>
            )}
            {project.building_data.heights?.firsthoehe_m && (
              <div>
                <span className="text-gray-500">Firsthoehe:</span>
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
          to={`/configurator?projectId=${id}`}
          className="card flex flex-col items-center py-6"
        >
          <Ruler className="text-primary-600 mb-2" size={32} />
          <span className="font-medium">Geruest</span>
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
'''

if __name__ == '__main__':
    path = 'C:/Users/vonro/projects/lawil/geodaten-ch/geruestbau-app/src/pages/ProjectDetailPage.tsx'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Written {len(content)} bytes to ProjectDetailPage.tsx')
