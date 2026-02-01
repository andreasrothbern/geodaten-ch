import { useState } from 'react'
import {
  ExternalLink,
  Link2,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Pen,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react'
import FileUpload from '../../ui/FileUpload'
// AddressAutocomplete deaktiviert - einfaches Textfeld stattdessen
// import AddressAutocomplete from '../../ui/AddressAutocomplete'
import type { OcrExtractionResult, ExtractedProjectData } from '../../../types/project'

interface ImportStepProps {
  onDataExtracted: (
    data: ExtractedProjectData,
    source: 'pdf' | 'photo' | 'url' | 'manual',
    file?: File  // NEU 01.02.2026: Datei für späteres Speichern
  ) => void
  onManualEntry?: () => void  // Optional callback for manual entry mode
  extractFromDocument: (file: File, gpsCoords?: { lat: number; lon: number }) => Promise<OcrExtractionResult>
  extractFromUrl: (url: string) => Promise<OcrExtractionResult>
}

// simap.ch URL with CPV codes for scaffolding
const SIMAP_FILTER_URL =
  'https://www.simap.ch/de?cpvCodes=["44212310","45262100"]&newestPubTypes=["tender"]&orderAddressCountryOnlySwitzerland=true'

export default function ImportStep({
  onDataExtracted,
  onManualEntry: _onManualEntry,  // Reserved for future use
  extractFromDocument,
  extractFromUrl,
}: ImportStepProps) {
  void _onManualEntry  // Suppress unused variable warning
  const [extractingDoc, setExtractingDoc] = useState(false)
  const [extractingUrl, setExtractingUrl] = useState(false)
  const [urlInput, setUrlInput] = useState('')
  const [urlError, setUrlError] = useState<string | null>(null)
  const [extractionResult, setExtractionResult] = useState<OcrExtractionResult | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [isManualOpen, setIsManualOpen] = useState(false)

  // Manual entry form state
  const [manualForm, setManualForm] = useState({
    project_name: '',
    address: '',
    client_name: '',
    description: '',
    submission_deadline: '',
  })

  const isSimapUrl = (url: string) => url.includes('simap.ch')

  // NEU 01.02.2026: Integrierte GPS-Fallback-Logik für Bilder
  const handleFileSelect = async (file: File) => {
    setSelectedFile(file)
    setExtractionResult(null)
    setExtractingDoc(true)

    // Bei Bildern: Versuche GPS via Geolocation API zu holen (Fallback für iOS Safari)
    let gpsCoords: { lat: number; lon: number } | undefined
    if (file.type.startsWith('image/')) {
      try {
        if ('geolocation' in navigator) {
          const position = await new Promise<GeolocationPosition>((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
              enableHighAccuracy: true,
              timeout: 5000,
              maximumAge: 60000  // Cache for 1 minute
            })
          })
          gpsCoords = {
            lat: position.coords.latitude,
            lon: position.coords.longitude
          }
          console.log('[ImportStep] GPS-Fallback geholt:', gpsCoords)
        }
      } catch (error) {
        console.log('[ImportStep] GPS nicht verfügbar:', error)
        // Kein Problem - Backend nutzt EXIF wenn vorhanden
      }
    }

    try {
      const result = await extractFromDocument(file, gpsCoords)
      setExtractionResult(result)

      if (result.success) {
        // NEU 01.02.2026: Unterschiedliche Quellen für Daten
        let extractedData = result.data

        // Bei Gebäudefoto: suggested_address oder preloaded_address verwenden
        // NEU 01.02.2026: suggested_address hat Priorität (aus identify_buildings)
        const resolvedAddress = result.suggested_address || result.preloaded_address
        if (result.image_type === 'building_photo' && resolvedAddress) {
          extractedData = {
            ...extractedData,
            address: resolvedAddress,
            // Beschreibung aus Foto-Analyse
            description: result.building_analysis ?
              `${result.building_analysis.floors_count || '?'} Geschosse, ${result.building_analysis.roof_type || 'Dach unbekannt'}${result.building_analysis.obstacles?.length ? `, Hindernisse: ${result.building_analysis.obstacles.join(', ')}` : ''}`
              : undefined,
          }
        }

        // Bei Skizze: Adresse aus Analyse oder zum Nachfragen markieren
        if (result.image_type === 'sketch' && result.sketch_analysis) {
          if (result.sketch_analysis.address_found) {
            extractedData = {
              ...extractedData,
              address: result.sketch_analysis.address_found,
            }
          }
          if (result.sketch_analysis.work_type) {
            extractedData = {
              ...extractedData,
              description: `Arbeitstyp: ${result.sketch_analysis.work_type}`,
            }
          }
        }

        if (extractedData) {
          const source = result.image_type === 'building_photo' ? 'photo' :
                        (file.type === 'application/pdf' ? 'pdf' : 'photo')
          // NEU 01.02.2026: Datei mitsenden für späteres Speichern
          onDataExtracted(extractedData, source, file)
        }
      }
    } catch (error) {
      console.error('Fehler bei OCR-Extraktion:', error)
      setExtractionResult({
        success: false,
        confidence: 0,
        error: 'Fehler beim Analysieren des Dokuments',
      })
    } finally {
      setExtractingDoc(false)
    }
  }

  const handleClearFile = () => {
    setSelectedFile(null)
    setExtractionResult(null)
  }

  const handleUrlExtract = async () => {
    if (!urlInput.trim()) {
      setUrlError('Bitte URL eingeben')
      return
    }

    if (!isSimapUrl(urlInput)) {
      setUrlError('Nur simap.ch URLs werden unterstützt')
      return
    }

    setUrlError(null)
    setExtractingUrl(true)

    try {
      const result = await extractFromUrl(urlInput)
      setExtractionResult(result)

      if (result.success && result.data) {
        onDataExtracted(result.data, 'url')
      }
    } catch (error) {
      console.error('Fehler bei URL-Import:', error)
      setExtractionResult({
        success: false,
        confidence: 0,
        error: 'Fehler beim Auslesen der URL',
      })
    } finally {
      setExtractingUrl(false)
    }
  }

  const handleManualSubmit = () => {
    if (!manualForm.project_name.trim() || !manualForm.address.trim()) {
      return
    }

    onDataExtracted(
      {
        project_name: manualForm.project_name,
        address: manualForm.address,
        client_name: manualForm.client_name || undefined,
        description: manualForm.description || undefined,
        submission_deadline: manualForm.submission_deadline || undefined,
      },
      'manual'
    )
  }

  return (
    <div className="space-y-4">
      {/* Unified File Upload Section */}
      <div className="card">
        <FileUpload
          onFileSelect={handleFileSelect}
          loading={extractingDoc}
          disabled={extractingDoc || extractingUrl}
          selectedFile={selectedFile}
          onClear={handleClearFile}
        />

        {/* Extraction Result */}
        {extractionResult && (
          <div
            className={`mt-4 p-3 rounded-lg ${
              extractionResult.success
                ? 'bg-green-50 text-green-800'
                : 'bg-red-50 text-red-800'
            }`}
          >
            <div className="flex items-start gap-2">
              {extractionResult.success ? (
                <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                {extractionResult.success ? (
                  <>
                    <p className="font-medium">
                      {extractionResult.image_type === 'building_photo' && 'Gebäudefoto erkannt'}
                      {extractionResult.image_type === 'document' && 'Dokument erkannt'}
                      {extractionResult.image_type === 'sketch' && 'Skizze erkannt'}
                      {extractionResult.image_type === 'technical_plan' && 'Technische Zeichnung erkannt'}
                      {extractionResult.image_type === 'mixed' && 'Gemischtes Bild erkannt'}
                      {(!extractionResult.image_type || extractionResult.image_type === 'unknown') && 'Daten erfolgreich extrahiert'}
                    </p>
                    <p className="text-sm opacity-80">
                      Konfidenz: {Math.round((extractionResult.confidence || 0) * 100)}%
                    </p>
                  </>
                ) : (
                  <>
                    <p className="font-medium">Extraktion fehlgeschlagen</p>
                    <p className="text-sm opacity-80">{extractionResult.error}</p>
                  </>
                )}
              </div>
            </div>

            {/* NEU 01.02.2026: Erweiterte Ergebnisse */}
            {extractionResult.success && (
              <div className="mt-3 pt-3 border-t border-green-200 space-y-2 text-sm">
                {/* GPS-Daten */}
                {extractionResult.gps_data && (
                  <div className="flex items-center gap-2">
                    <span className="font-medium">📍 GPS:</span>
                    <span>
                      {extractionResult.gps_data.lat?.toFixed(4)}, {extractionResult.gps_data.lon?.toFixed(4)}
                      {extractionResult.gps_data.compass_direction_text && (
                        <span className="ml-2 text-green-600">
                          (Blickrichtung: {extractionResult.gps_data.compass_direction_text})
                        </span>
                      )}
                    </span>
                  </div>
                )}

                {/* Pre-loaded Gebäudedaten */}
                {extractionResult.preloaded_egid && (
                  <div className="bg-green-100 p-2 rounded">
                    <p className="font-medium">🏠 3D-Daten geladen:</p>
                    <ul className="ml-4 mt-1 space-y-0.5">
                      {extractionResult.preloaded_address && (
                        <li>Adresse: {extractionResult.preloaded_address}</li>
                      )}
                      <li>EGID: {extractionResult.preloaded_egid}</li>
                      {extractionResult.preloaded_traufhoehe_m && (
                        <li>Traufhöhe: {extractionResult.preloaded_traufhoehe_m.toFixed(1)}m</li>
                      )}
                      {extractionResult.preloaded_roof_type && (
                        <li>Dachtyp: {extractionResult.preloaded_roof_type}</li>
                      )}
                    </ul>
                  </div>
                )}

                {/* Gebäudefoto-Analyse */}
                {extractionResult.building_analysis && (
                  <div className="space-y-1">
                    {extractionResult.building_analysis.floors_count && (
                      <p>🏗️ Geschosse: {extractionResult.building_analysis.floors_count}</p>
                    )}
                    {extractionResult.building_analysis.roof_type && (
                      <p>🏠 Dachform: {extractionResult.building_analysis.roof_type}</p>
                    )}
                    {extractionResult.building_analysis.facade_material && (
                      <p>🧱 Fassade: {extractionResult.building_analysis.facade_material}</p>
                    )}
                    {extractionResult.building_analysis.obstacles && extractionResult.building_analysis.obstacles.length > 0 && (
                      <p>⚠️ Hindernisse: {extractionResult.building_analysis.obstacles.join(', ')}</p>
                    )}
                    {extractionResult.building_analysis.visible_address && (
                      <p>📮 Sichtbare Adresse: {extractionResult.building_analysis.visible_address}</p>
                    )}
                  </div>
                )}

                {/* Skizze-Analyse */}
                {extractionResult.sketch_analysis && (
                  <div className="space-y-1">
                    {extractionResult.sketch_analysis.sketch_type && (
                      <p>📐 Skizzentyp: {extractionResult.sketch_analysis.sketch_type}</p>
                    )}
                    {extractionResult.sketch_analysis.work_type && (
                      <p>🔧 Arbeitstyp: {extractionResult.sketch_analysis.work_type}</p>
                    )}
                    {extractionResult.sketch_analysis.address_required && (
                      <p className="text-orange-600 font-medium">
                        ⚠️ Keine Adresse erkannt - bitte manuell eingeben
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* simap.ch Search Box */}
      <div className="card bg-blue-50 border-blue-200">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-blue-100 rounded-lg">
            <ExternalLink className="w-5 h-5 text-blue-600" />
          </div>
          <div className="flex-1">
            <h3 className="font-medium text-blue-900">
              Gerüstbau-Ausschreibungen finden
            </h3>
            <p className="text-sm text-blue-700 mt-1">
              simap.ch mit voreingestelltem Filter öffnen
            </p>
            <a
              href={SIMAP_FILTER_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 mt-2 px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              simap.ch öffnen
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        </div>
      </div>

      {/* URL Import Box */}
      <div className="card">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-gray-100 rounded-lg">
            <Link2 className="w-5 h-5 text-gray-600" />
          </div>
          <div className="flex-1">
            <h3 className="font-medium">Projekt-Link einfügen</h3>
            <p className="text-sm text-gray-600 mt-1">
              Kopiere den Link von simap.ch und füge ihn ein:
            </p>

            <div className="mt-3 space-y-2">
              <div className="relative">
                <input
                  type="url"
                  className={`input-field pr-10 ${urlError ? 'border-red-500' : ''}`}
                  placeholder="https://simap.ch/de/project-detail/..."
                  value={urlInput}
                  onChange={(e) => {
                    setUrlInput(e.target.value)
                    setUrlError(null)
                  }}
                  disabled={extractingDoc || extractingUrl}
                />
                {urlInput && isSimapUrl(urlInput) && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-green-600 text-xs">
                    ✓ simap.ch
                  </span>
                )}
              </div>

              {urlError && (
                <p className="text-sm text-red-600">{urlError}</p>
              )}

              <button
                type="button"
                onClick={handleUrlExtract}
                disabled={extractingDoc || extractingUrl || !urlInput.trim()}
                className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {extractingUrl ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                Daten auslesen
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="flex items-center gap-4">
        <div className="flex-1 h-px bg-gray-200" />
        <span className="text-sm text-gray-500">oder</span>
        <div className="flex-1 h-px bg-gray-200" />
      </div>

      {/* Manual Entry Toggle */}
      <div className="card">
        <button
          type="button"
          onClick={() => setIsManualOpen(!isManualOpen)}
          className="w-full flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gray-100 rounded-lg">
              <Pen className="w-5 h-5 text-gray-600" />
            </div>
            <div className="text-left">
              <h3 className="font-medium">Manuell erfassen</h3>
              <p className="text-sm text-gray-600">Ohne Dokument</p>
            </div>
          </div>
          {isManualOpen ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </button>

        {isManualOpen && (
          <div className="mt-4 pt-4 border-t space-y-4">
            {/* Project Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Projekttitel *
              </label>
              <input
                type="text"
                className="input-field"
                placeholder="z.B. Gerüst Kirche St. Peter"
                value={manualForm.project_name}
                onChange={(e) =>
                  setManualForm({ ...manualForm, project_name: e.target.value })
                }
              />
            </div>

            {/* Address */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Adresse *
              </label>
              <input
                type="text"
                className="input-field"
                value={manualForm.address}
                onChange={(e) =>
                  setManualForm({ ...manualForm, address: e.target.value })
                }
                placeholder="Strasse Nr, PLZ Ort"
                required
              />
              <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                Gebäudedaten werden automatisch geladen
              </p>
            </div>

            {/* Client */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Auftraggeber
              </label>
              <input
                type="text"
                className="input-field"
                placeholder="Name / Firma"
                value={manualForm.client_name}
                onChange={(e) =>
                  setManualForm({ ...manualForm, client_name: e.target.value })
                }
              />
            </div>

            {/* Deadline */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Eingabefrist
              </label>
              <input
                type="date"
                className="input-field"
                value={manualForm.submission_deadline}
                onChange={(e) =>
                  setManualForm({
                    ...manualForm,
                    submission_deadline: e.target.value,
                  })
                }
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Beschreibung
              </label>
              <textarea
                className="input-field min-h-[80px]"
                placeholder="Projektdetails..."
                value={manualForm.description}
                onChange={(e) =>
                  setManualForm({ ...manualForm, description: e.target.value })
                }
              />
            </div>

            {/* Submit Button */}
            <button
              type="button"
              onClick={handleManualSubmit}
              disabled={!manualForm.project_name.trim() || !manualForm.address.trim()}
              className="btn-primary w-full"
            >
              Weiter
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
