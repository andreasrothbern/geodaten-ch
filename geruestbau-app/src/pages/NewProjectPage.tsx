import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { geruestbauApi } from '../api/geruestbau'
import StepIndicator from '../components/ui/StepIndicator'
import { ImportStep, ReviewStep, GeodataStep } from '../components/projects/import'
import type {
  ExtractedProjectData,
  TenderData,
  BuildingData,
  BuildingDataInput,
  OcrExtractionResult,
} from '../types/project'

// Konvertiere Frontend BuildingData zu Backend BuildingDataInput
function convertToBackendFormat(data: BuildingData | null): BuildingDataInput | undefined {
  if (!data) return undefined

  return {
    egid: data.gwr?.egid,
    coordinates: data.geocode?.coordinates ? {
      e: data.geocode.coordinates.e,
      n: data.geocode.coordinates.n,
      lat: data.geocode.lat,
      lon: data.geocode.lon,
    } : undefined,
    polygon: data.polygon?.coordinates?.[0],
    traufhoehe_m: data.heights?.traufhoehe_m,
    firsthoehe_m: data.heights?.firsthoehe_m,
    gebaeudehoehe_m: data.heights?.gebaeudehoehe_m,
    height_source: data.heights?.source,
    floors: data.gwr?.floors,
    building_type: data.gwr?.category,
    year_built: data.gwr?.year_built,
  }
}

const STEPS = [
  { id: 1, label: 'Import' },
  { id: 2, label: 'Prüfen' },
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
  const [rawText, setRawText] = useState<string | undefined>()

  // Handle data from ImportStep
  const handleDataExtracted = useCallback(
    (data: ExtractedProjectData, extractionSource: ImportSource) => {
      setProjectData(data)
      setSource(extractionSource)
      setCurrentStep(2) // Go to review step
    },
    []
  )

  // Handle manual entry (skip review, go straight to geodata)
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
      if (result.raw_text) {
        setRawText(result.raw_text)
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

  // Load geodata for address
  const loadGeodata = useCallback(
    async (address: string): Promise<BuildingData | null> => {
      try {
        const response = await fetch(
          `${import.meta.env.VITE_GEODATEN_API_URL || 'https://acceptable-trust-production.up.railway.app'}/api/v1/smart-building/data?address=${encodeURIComponent(address)}`
        )
        if (!response.ok) return null
        const data = await response.json()

        // Map SmartBuilding response to BuildingData
        return {
          geocode: data.coordinates
            ? {
                coordinates: { e: data.coordinates.e, n: data.coordinates.n },
                lat: data.coordinates.lat || 0,
                lon: data.coordinates.lon || 0,
              }
            : undefined,
          gwr: data.egid
            ? {
                egid: data.egid,
                address: data.address_matched || address,
                floors: data.floors || 0,
                category: data.building_type || '',
                year_built: data.year_built,
              }
            : undefined,
          heights: data.traufhoehe_m
            ? {
                traufhoehe_m: data.traufhoehe_m,
                firsthoehe_m: data.firsthoehe_m,
                gebaeudehoehe_m: data.firsthoehe_m,
                source: data.height_source || 'estimated',
              }
            : undefined,
          polygon: data.polygon
            ? {
                type: 'Polygon',
                coordinates: [data.polygon],
              }
            : undefined,
        }
      } catch (error) {
        console.error('Fehler beim Laden der Geodaten:', error)
        return null
      }
    },
    []
  )

  // Create project - jetzt MIT building_data!
  const handleSubmit = useCallback(
    async (buildingData: BuildingData | null) => {
      if (!projectData.project_name || !projectData.address) return

      setLoading(true)

      try {
        const tenderData: TenderData = {
          tender_number: projectData.tender_number,
          submission_deadline: projectData.submission_deadline,
          project_start: projectData.project_start,
          project_end: projectData.project_end,
          estimated_area_m2: projectData.estimated_area_m2,
          source: source === 'url' ? 'simap' : source,
          confidence: confidence,
          raw_text: rawText,
        }

        // Geodaten fuer 3D-Modell konvertieren und mitsenden
        const buildingDataInput = convertToBackendFormat(buildingData)

        const project = await geruestbauApi.createProject({
          name: projectData.project_name,
          address: projectData.address,
          client_name: projectData.client_name,
          client_contact: projectData.client_contact,
          description: projectData.description,
          deadline: projectData.submission_deadline,
          tender_data: tenderData,
          building_data: buildingDataInput,  // Geodaten werden jetzt gespeichert!
        })

        // Navigate to project detail
        navigate(`/projects/${project.id}`)
      } catch (error) {
        console.error('Fehler beim Erstellen:', error)
        alert('Fehler beim Erstellen des Projekts')
      } finally {
        setLoading(false)
      }
    },
    [projectData, source, confidence, rawText, navigate]
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
