import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { geruestbauApi } from '../api/geruestbau'
import StepIndicator from '../components/ui/StepIndicator'
import { ImportStep, ReviewStep, GeodataStep } from '../components/projects/import'
import type {
  ExtractedProjectData,
  GeruestbauData,
  BuildingEntry,
  OcrExtractionResult,
} from '../types/project'

const STEPS = [
  { id: 1, label: 'Import' },
  { id: 2, label: 'Prüfen' },
  { id: 3, label: 'Grunddaten' },
]

type ImportSource = 'pdf' | 'photo' | 'url' | 'manual'

export default function NewProjectPage() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(1)
  const [loading, setLoading] = useState(false)
  const [enrichmentComplete, setEnrichmentComplete] = useState(false)

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
  // NEU 01.02.2026: GPS-Fallback für iOS Safari (EXIF wird dort entfernt)
  const extractFromDocument = useCallback(
    async (file: File, gpsCoords?: { lat: number; lon: number }): Promise<OcrExtractionResult> => {
      const result = await geruestbauApi.extractFromDocument(file, gpsCoords)
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

  // Create project and enrich with GeruestbauData
  // NEU 18.01.2026: Parameter umgestellt von Geodata auf GeruestbauData
  // FIX 18.01.2026: geruestbaudata wird jetzt mitgesendet (kombiniert bei Multi-Building)
  const handleSubmit = useCallback(
    async (geruestbauData: GeruestbauData | null, buildings?: BuildingEntry[]) => {
      if (!projectData.project_name || !projectData.address) return

      setLoading(true)

      try {
        // NEU 18.01.2026: geruestbaudata mitsenden
        // Bei Single-Building: Einzelgebäude-Daten
        // Bei Multi-Building: Das KOMBINIERTE Objekt (Union-Polygon + äußere Fassaden)
        await geruestbauApi.createProject({
          name: projectData.project_name,
          address: projectData.address,
          egid: geruestbauData?.building.egid, // Bei Multi: "123+456+789"
          buildings: buildings, // Einzelne Gebäude für Details
          geruestbaudata: geruestbauData ?? undefined, // NEU: Das kombinierte Objekt
          client_name: projectData.client_name,
          client_contact: projectData.client_contact,
          deadline: projectData.submission_deadline,
        })

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
      <StepIndicator steps={STEPS} currentStep={currentStep} isComplete={enrichmentComplete} />

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
          // loadGeodata entfernt - SSE-Streaming wird verwendet
          onBack={() => {
            setEnrichmentComplete(false)
            setCurrentStep(2)
          }}
          onSubmit={handleSubmit}
          loading={loading}
          onLoadComplete={setEnrichmentComplete}
        />
      )}
    </div>
  )
}
