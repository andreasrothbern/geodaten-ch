import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Search,
  Plus,
  Clock,
  FileText,
  Send,
  CheckCircle,
  ArrowRight,
  Building2,
  Ruler,
  FolderPlus,
} from 'lucide-react'
import { geruestbauApi } from '../api/geruestbau'
import type { Project, ProjectStatus } from '../types/project'

// Progress step configuration (4 steps: Import → Gerüst → Doku → Export)
const PROGRESS_STEPS = [
  { id: 1, label: 'Import', shortLabel: 'Import' },
  { id: 2, label: 'Gerüst', shortLabel: 'Gerüst' },
  { id: 3, label: 'Dokumente', shortLabel: 'Doku' },
  { id: 4, label: 'Export', shortLabel: 'Export' },
]

// Map project status to progress step (4 steps total)
function getProgressStep(status: ProjectStatus): number {
  switch (status) {
    case 'draft':
      return 1
    case 'captured':
    case 'enriched':
    case 'reviewed':
      return 2  // Gerüst step (combined Fassaden + Gerüst)
    case 'planned':
      return 3  // Doku
    case 'quoted':
      return 4  // Export
    case 'commissioned':
      return 5  // Completed (beyond last step)
    default:
      return 1
  }
}

// Status display configuration
interface StatusConfig {
  label: string
  icon: typeof Clock
  bgColor: string
  textColor: string
  borderColor: string
  nextStep: string
}

const STATUS_CONFIG: Record<ProjectStatus, StatusConfig> = {
  draft: {
    label: 'Neu erstellt',
    icon: FolderPlus,
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    borderColor: 'border-green-100',
    nextStep: 'Gerüst konfigurieren',
  },
  captured: {
    label: 'Erfasst',
    icon: Building2,
    bgColor: 'bg-amber-50',
    textColor: 'text-amber-700',
    borderColor: 'border-amber-100',
    nextStep: 'Grunddaten laden',
  },
  enriched: {
    label: 'Konfiguration',
    icon: Clock,
    bgColor: 'bg-amber-50',
    textColor: 'text-amber-700',
    borderColor: 'border-amber-100',
    nextStep: 'Gerüst konfigurieren',
  },
  reviewed: {
    label: 'Geprüft',
    icon: Ruler,
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-100',
    nextStep: 'Dokumente erstellen',
  },
  planned: {
    label: 'Bereit für Export',
    icon: FileText,
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-100',
    nextStep: 'Offerte erstellen',
  },
  quoted: {
    label: 'Offerte gesendet',
    icon: Send,
    bgColor: 'bg-purple-50',
    textColor: 'text-purple-700',
    borderColor: 'border-purple-100',
    nextStep: 'Warte auf Rückmeldung',
  },
  commissioned: {
    label: 'Abgeschlossen',
    icon: CheckCircle,
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-600',
    borderColor: 'border-gray-100',
    nextStep: '',
  },
}

type FilterType = 'all' | 'inProgress' | 'quotes' | 'orders' | 'archive'

const FILTERS: { id: FilterType; label: string; statuses: ProjectStatus[] }[] = [
  { id: 'all', label: 'Alle', statuses: [] },
  { id: 'inProgress', label: 'In Arbeit', statuses: ['draft', 'captured', 'enriched', 'reviewed', 'planned'] },
  { id: 'quotes', label: 'Offerten', statuses: ['quoted'] },
  { id: 'orders', label: 'Aufträge', statuses: ['commissioned'] },
  { id: 'archive', label: 'Archiv', statuses: ['commissioned'] },
]

function ProgressSteps({ currentStep }: { currentStep: number }) {
  return (
    <div className="mt-3">
      <div className="flex items-center gap-1">
        {PROGRESS_STEPS.map((step, index) => {
          const isCompleted = step.id < currentStep
          const isCurrent = step.id === currentStep
          const isPending = step.id > currentStep
          return (
            <div key={step.id} className="flex items-center flex-1 last:flex-none">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium transition-all duration-300 ${isCompleted ? 'bg-green-500 text-white' : ''} ${isCurrent ? 'bg-red-600 text-white animate-pulse' : ''} ${isPending ? 'bg-gray-200 text-gray-400' : ''}`}>
                {isCompleted ? '\u2713' : step.id}
              </div>
              {index < PROGRESS_STEPS.length - 1 && (
                <div className={`flex-1 h-1 mx-1 rounded ${isCompleted ? 'bg-green-500' : ''} ${isCurrent ? 'bg-red-300' : ''} ${isPending ? 'bg-gray-200' : ''}`} />
              )}
            </div>
          )
        })}
      </div>
      <div className="flex justify-between text-xs text-gray-400 mt-1 px-0.5">
        {PROGRESS_STEPS.map((step) => (
          <span key={step.id} className={step.id === currentStep ? 'text-red-600 font-medium' : ''}>
            {step.shortLabel}
          </span>
        ))}
      </div>
    </div>
  )
}

function ProjectCard({ project }: { project: Project }) {
  const config = STATUS_CONFIG[project.status] || STATUS_CONFIG.draft
  const StatusIcon = config.icon
  const progressStep = getProgressStep(project.status)
  const isArchived = project.status === 'commissioned'

  const getRelativeTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)
    if (diffMins < 60) return `vor ${diffMins} Min.`
    if (diffHours < 24) return `vor ${diffHours} Std.`
    if (diffDays < 7) return `vor ${diffDays} Tagen`
    return date.toLocaleDateString('de-CH')
  }

  return (
    <Link to={`/projects/${project.id}`} className={`block bg-white rounded-xl shadow-sm overflow-hidden transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 ${isArchived ? 'opacity-75' : ''}`}>
      <div className="p-4">
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h3 className="font-semibold text-gray-800 truncate">{project.name}</h3>
              <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${config.bgColor} ${config.textColor}`}>
                <StatusIcon size={12} />
                {config.label}
              </span>
            </div>
            <p className="text-sm text-gray-500 truncate">{project.address}</p>
          </div>
          <span className="text-xs text-gray-400 whitespace-nowrap ml-2">{getRelativeTime(project.updated_at)}</span>
        </div>
        {!isArchived && <ProgressSteps currentStep={progressStep} />}
        {isArchived && project.building_data && (
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-400">
            <span><Ruler size={14} className="inline mr-1" />{project.building_data.heights?.traufhoehe_m?.toFixed(1) || '?'} m</span>
            <span><CheckCircle size={14} className="inline mr-1 text-green-500" />Abgeschlossen</span>
          </div>
        )}
      </div>
      {!isArchived && config.nextStep && (
        <div className={`px-4 py-2 border-t ${config.borderColor} ${config.bgColor}`}>
          <p className={`text-sm ${config.textColor} flex items-center gap-2`}>
            <ArrowRight size={14} />
            Naechster Schritt: {config.nextStep}
          </p>
        </div>
      )}
    </Link>
  )
}

function QuickStats({ projects }: { projects: Project[] }) {
  const stats = useMemo(() => {
    const inProgress = projects.filter((p) => ['draft', 'captured', 'enriched', 'reviewed', 'planned'].includes(p.status)).length
    const quotes = projects.filter((p) => p.status === 'quoted').length
    const completed = projects.filter((p) => p.status === 'commissioned').length
    return { total: projects.length, inProgress, quotes, completed }
  }, [projects])

  return (
    <div className="grid grid-cols-4 gap-2 mb-4">
      <div className="bg-white rounded-xl p-3 text-center shadow-sm">
        <p className="text-2xl font-bold text-gray-800">{stats.total}</p>
        <p className="text-xs text-gray-500">Projekte</p>
      </div>
      <div className="bg-white rounded-xl p-3 text-center shadow-sm">
        <p className="text-2xl font-bold text-amber-500">{stats.inProgress}</p>
        <p className="text-xs text-gray-500">In Arbeit</p>
      </div>
      <div className="bg-white rounded-xl p-3 text-center shadow-sm">
        <p className="text-2xl font-bold text-blue-500">{stats.quotes}</p>
        <p className="text-xs text-gray-500">Offerten</p>
      </div>
      <div className="bg-white rounded-xl p-3 text-center shadow-sm">
        <p className="text-2xl font-bold text-green-500">{stats.completed}</p>
        <p className="text-xs text-gray-500">Abgeschlossen</p>
      </div>
    </div>
  )
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeFilter, setActiveFilter] = useState<FilterType>('all')

  useEffect(() => { loadProjects() }, [])

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

  const filteredProjects = useMemo(() => {
    let result = projects
    const filter = FILTERS.find((f) => f.id === activeFilter)
    if (filter && filter.statuses.length > 0) {
      result = result.filter((p) => filter.statuses.includes(p.status))
    }
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter((p) => p.name.toLowerCase().includes(query) || p.address.toLowerCase().includes(query) || p.client_name?.toLowerCase().includes(query))
    }
    return result
  }, [projects, activeFilter, searchQuery])

  const filterCounts = useMemo(() => {
    const counts: Record<FilterType, number> = { all: projects.length, inProgress: 0, quotes: 0, orders: 0, archive: 0 }
    projects.forEach((p) => {
      if (['draft', 'captured', 'enriched', 'reviewed', 'planned'].includes(p.status)) counts.inProgress++
      if (p.status === 'quoted') counts.quotes++
      if (p.status === 'commissioned') { counts.orders++; counts.archive++ }
    })
    return counts
  }, [projects])

  if (loading) {
    return <div className="flex items-center justify-center py-12"><div className="animate-spin w-8 h-8 border-4 border-red-600 border-t-transparent rounded-full"></div></div>
  }

  if (error) {
    return <div className="text-center py-12"><p className="text-red-600">{error}</p><button onClick={loadProjects} className="btn-secondary mt-4">Erneut versuchen</button></div>
  }

  return (
    <div className="pb-24">
      <QuickStats projects={projects} />
      <div className="flex gap-2 mb-4 overflow-x-auto pb-2 -mx-4 px-4">
        {FILTERS.map((filter) => (
          <button key={filter.id} onClick={() => setActiveFilter(filter.id)} className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors duration-200 ${activeFilter === filter.id ? 'bg-red-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>
            {filter.label} ({filterCounts[filter.id]})
          </button>
        ))}
      </div>
      <div className="relative mb-4">
        <input type="text" placeholder="Projekt suchen..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="w-full pl-10 pr-4 py-3 bg-white rounded-xl border-0 shadow-sm focus:ring-2 focus:ring-red-500" />
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
      </div>
      {filteredProjects.length === 0 ? (
        <div className="text-center py-12">
          <Building2 className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          {projects.length === 0 ? (<><h3 className="text-lg font-semibold text-gray-700">Keine Projekte</h3><p className="text-gray-500 mt-2">Erstellen Sie Ihr erstes Projekt</p></>) : (<><h3 className="text-lg font-semibold text-gray-700">Keine Treffer</h3><p className="text-gray-500 mt-2">Versuchen Sie einen anderen Suchbegriff</p></>)}
        </div>
      ) : (
        <div className="space-y-3">{filteredProjects.map((project) => <ProjectCard key={project.id} project={project} />)}</div>
      )}
      <Link to="/projects/new" className="fixed bottom-20 right-4 w-14 h-14 bg-red-600 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-red-700 transition-colors z-50" style={{ boxShadow: '0 4px 12px rgba(220, 38, 38, 0.4)' }}>
        <Plus size={28} />
      </Link>
    </div>
  )
}
