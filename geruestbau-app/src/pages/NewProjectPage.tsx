import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { geruestbauApi } from '../api/geruestbau'
import StepIndicator from '../components/ui/StepIndicator'
import { ImportStep, ReviewStep, GeodataStep } from '../components/projects/import'
import type {
  ExtractedProjectData,
  Geodata,
  OcrExtractionResult,
} from '../types/project'

const STEPS = [
  { id: 1, label: 'Import' },
  { id: 2, label: 'Pruefen' },
  { id: 3, label: 'Geodaten' },
]

type ImportSource = 'pdf' | 'photo' | 'url' | 'manual'

export default function NewProjectPage() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(false)

  // Extracted/entered data
  const [projectData, setProjectData] = useState<ExtractedProjectData>({})
  const [source, setSource] = useState<ImportSource>('manual')
  const [confidence, setConfidence] = useState<number | undefined>()

  // Handle data from ImportStep
  const handleDataExtracted = useCallback(
    (data: ExtractedProjectData, extractionSource: ImportSource) => {
      setProjectData(data)
      setSource(extractionSource)
      setCurrentStep(2)
    },
    []
  )

  // Handle manual entry
  const handleManualEntry = useCallback(() => {
    setSource('manual')
    setCurrentStep(2)
  }, [])

  // Extract from document (PDF/photo)
  const extractFromDocument = useCallback(
    async (file: File): Promise<OcrExtractionResult> => {
      const result = await geruestbauApi.extractFromDocument(file)
      if (result.confidence) {
        setConfidence(result.confidence)
      }
      return result
    },
    []
  )

  // Extract from URL (simap.ch)
  const extractFromUrl = useCallback(
    async (url: string): Promise<OcrExtractionResult> => {
      const result = await geruestbauApi.extractFromUrl(url)
      if (result.confidence) {
        setConfidence(result.confidence)
      }
      return result
    },
    []
  )

  // Load geodata preview for address (optional preview)
  const loadGeodata = useCallback(
    async (address: string): Promise<Geodata | null> => {
      try {
        const response = await fetch(
          `${import.meta.env.VITE_API_URL || ''}/api/v1/smart-building/data?address=${encodeURIComponent(address)}`
        )
        if (!response.ok) return null
        const data = await response.json()

        // Map to Geodata format (flat structure)
        return {
          egid: data.egid || '',
          address: data.address_matched || address,
          traufhoehe_m: data.traufhoehe_m,
          firsthoehe_m: data.firsthoehe_m,
          gebaeudehoehe_m: data.firsthoehe_m,
          area_m2: data.area_m2,
          perimeter_m: data.perimeter_m,
          coord_e: data.coordinates?.e,
          coord_n: data.coordinates?.n,
        }
      } catch (error) {
        console.error('Fehler beim Laden der Geodaten:', error)
        return null
      }
    },
    []
  )

  // Create project and enrich with geodata
  const handleSubmit = useCallback(
    async (_geodataPreview: Geodata | null) => {
      if (!projectData.project_name || !projectData.address) return

      setLoading(true)

      try {
        // 1. Create project with basic data
        const project = await geruestbauApi.createProject({
          name: projectData.project_name,
          address: projectData.address,
          client_name: projectData.client_name,
          client_contact: projectData.client_contact,
          deadline: projectData.submission_deadline,
        })

        // 2. Enrich with geodata (saves to cache and updates EGID)
        await geruestbauApi.enrichProject(project.id)

        // Navigate to projects list
        navigate('/projects')
      } catch (error) {
        console.error('Fehler beim Erstellen:', error)
        alert('Fehler beim Erstellen des Projekts')
      } finally {
        setLoading(false)
      }
    },
    [projectData, navigate]
  )

  return (
    <div className="pb-24">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <button
          type="button"
          onClick={() => {
            if (currentStep > 1) {
              setCurrentStep(currentStep - 1)
            } else {
              navigate(-1)
            }
          }}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-lg font-semibold">Neues Projekt</h1>
          <p className="text-sm text-gray-500">Schritt {currentStep} von {STEPS.length}</p>
        </div>
      </div>

      {/* Step Indicator */}
      <StepIndicator steps={STEPS} currentStep={currentStep} />

      {/* Step Content */}
      {currentStep === 1 && (
        <ImportStep
          onDataExtracted={handleDataExtracted}
          onManualEntry={handleManualEntry}
          extractFromDocument={extractFromDocument}
          extractFromUrl={extractFromUrl}
        />
      )}

      {currentStep === 2 && (
        <ReviewStep
          data={projectData}
          source={source}
          confidence={confidence}
          onChange={setProjectData}
          onBack={() => setCurrentStep(1)}
          onNext={() => setCurrentStep(3)}
        />
      )}

      {currentStep === 3 && (
        <GeodataStep
          data={projectData}
          source={source}
          loadGeodata={loadGeodata}
          onBack={() => setCurrentStep(2)}
          onSubmit={handleSubmit}
          loading={loading}
        />
      )}
    </div>
  )
}
