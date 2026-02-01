import { useState } from 'react'
import { FileText, Link2, Camera, Pen, AlertCircle, Info, X } from 'lucide-react'
// AddressAutocomplete deaktiviert - einfaches Textfeld stattdessen
// import AddressAutocomplete from '../../ui/AddressAutocomplete'
import type { ExtractedProjectData, OcrExtractionResult } from '../../../types/project'

interface ReviewStepProps {
  data: ExtractedProjectData
  source: 'pdf' | 'photo' | 'url' | 'manual'
  confidence?: number
  extractionResult?: OcrExtractionResult | null  // NEU 01.02.2026
  onChange: (data: ExtractedProjectData) => void
  onBack: () => void
  onNext: () => void
}

const sourceIcons = {
  pdf: FileText,
  photo: Camera,
  url: Link2,
  manual: Pen,
}

const sourceLabels = {
  pdf: 'PDF-Dokument',
  photo: 'Foto',
  url: 'simap.ch',
  manual: 'Manuell erfasst',
}

export default function ReviewStep({
  data,
  source,
  confidence,
  extractionResult,
  onChange,
  onBack,
  onNext,
}: ReviewStepProps) {
  const SourceIcon = sourceIcons[source]
  const isFromExtraction = source !== 'manual'
  // NEU 01.02.2026: State für Analyse-Details Popup
  const [showAnalysisDetails, setShowAnalysisDetails] = useState(false)

  // Prüfen ob Analyse-Details vorhanden
  const hasAnalysisDetails = extractionResult && (
    extractionResult.building_analysis ||
    extractionResult.terrain_analysis ||
    extractionResult.gps_data ||
    extractionResult.suggested_address
  )

  const updateField = <K extends keyof ExtractedProjectData>(
    field: K,
    value: ExtractedProjectData[K] | string
  ) => {
    onChange({ ...data, [field]: value || undefined })
  }

  const isValid = data.project_name?.trim() && data.address?.trim()

  return (
    <div className="space-y-4">
      {/* Source Badge */}
      <div className="card bg-gray-50 border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SourceIcon className="w-4 h-4 text-gray-600" />
            <span className="text-sm text-gray-700">
              Quelle: <strong>{sourceLabels[source]}</strong>
            </span>
          </div>
          {isFromExtraction && confidence !== undefined && (
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                confidence >= 0.8
                  ? 'bg-green-100 text-green-700'
                  : confidence >= 0.5
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-red-100 text-red-700'
              }`}
            >
              Konfidenz: {Math.round(confidence * 100)}%
            </span>
          )}
        </div>
        {isFromExtraction && (
          <div className="relative">
            <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
              {hasAnalysisDetails ? (
                <button
                  type="button"
                  onClick={() => setShowAnalysisDetails(!showAnalysisDetails)}
                  className="p-0.5 rounded-full hover:bg-gray-200 transition-colors"
                  title="Analyse-Details anzeigen"
                >
                  <Info className="w-3 h-3 text-gray-500" />
                </button>
              ) : (
                <AlertCircle className="w-3 h-3" />
              )}
              Bitte die extrahierten Daten überprüfen und ggf. korrigieren
            </p>

            {/* NEU 01.02.2026: Analyse-Details Popup */}
            {showAnalysisDetails && extractionResult && (
              <div className="absolute left-0 top-6 z-50 w-80 max-h-96 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs">
                <div className="flex justify-between items-center mb-2 border-b pb-2">
                  <span className="font-semibold text-gray-700">Analyse-Details</span>
                  <button
                    type="button"
                    onClick={() => setShowAnalysisDetails(false)}
                    className="p-0.5 hover:bg-gray-100 rounded"
                  >
                    <X className="w-4 h-4 text-gray-500" />
                  </button>
                </div>

                {/* GPS-Daten */}
                {extractionResult.gps_data && (
                  <div className="mb-2">
                    <p className="font-medium text-gray-600">GPS-Position:</p>
                    <p className="text-gray-500 ml-2">
                      {extractionResult.gps_data.lat?.toFixed(5)}, {extractionResult.gps_data.lon?.toFixed(5)}
                      {extractionResult.gps_data.compass_direction_text && (
                        <span className="ml-1">(Blick: {extractionResult.gps_data.compass_direction_text})</span>
                      )}
                    </p>
                  </div>
                )}

                {/* Vorgeschlagene Adresse */}
                {extractionResult.suggested_address && (
                  <div className="mb-2">
                    <p className="font-medium text-gray-600">Erkannte Adresse:</p>
                    <p className="text-gray-500 ml-2">{extractionResult.suggested_address}</p>
                    {extractionResult.suggested_egid && (
                      <p className="text-gray-400 ml-2 text-[10px]">EGID: {extractionResult.suggested_egid}</p>
                    )}
                  </div>
                )}

                {/* Gebäude-Analyse */}
                {extractionResult.building_analysis && (
                  <div className="mb-2">
                    <p className="font-medium text-gray-600">Gebäude-Analyse:</p>
                    <ul className="text-gray-500 ml-2 space-y-0.5">
                      {extractionResult.building_analysis.floors_count && (
                        <li>Geschosse: {extractionResult.building_analysis.floors_count}</li>
                      )}
                      {extractionResult.building_analysis.roof_type && (
                        <li>Dachform: {extractionResult.building_analysis.roof_type}</li>
                      )}
                      {extractionResult.building_analysis.facade_material && (
                        <li>Fassade: {extractionResult.building_analysis.facade_material}</li>
                      )}
                      {extractionResult.building_analysis.obstacles && extractionResult.building_analysis.obstacles.length > 0 && (
                        <li className="text-orange-600">Hindernisse: {extractionResult.building_analysis.obstacles.join(', ')}</li>
                      )}
                    </ul>
                  </div>
                )}

                {/* Terrain-Analyse */}
                {extractionResult.terrain_analysis && (
                  <div className="mb-2">
                    <p className="font-medium text-gray-600">Terrain & Umgebung:</p>
                    <ul className="text-gray-500 ml-2 space-y-0.5">
                      {extractionResult.terrain_analysis.slope_estimate && (
                        <li>Hanglage: {extractionResult.terrain_analysis.slope_estimate}</li>
                      )}
                      {extractionResult.terrain_analysis.ground_type && (
                        <li>Untergrund: {extractionResult.terrain_analysis.ground_type}</li>
                      )}
                      {extractionResult.terrain_analysis.access_type && (
                        <li>Zufahrt: {extractionResult.terrain_analysis.access_type}</li>
                      )}
                      {extractionResult.terrain_analysis.access_width && (
                        <li>Zufahrtsbreite: {extractionResult.terrain_analysis.access_width}</li>
                      )}
                      {extractionResult.terrain_analysis.neighboring_distance && (
                        <li>Nachbargebäude: {extractionResult.terrain_analysis.neighboring_distance}</li>
                      )}
                      {extractionResult.terrain_analysis.trees_nearby && (
                        <li className="text-orange-600">Bäume in der Nähe</li>
                      )}
                      {extractionResult.terrain_analysis.power_lines && (
                        <li className="text-red-600">Stromleitungen!</li>
                      )}
                      {(extractionResult.terrain_analysis.balconies_count ?? 0) > 0 && (
                        <li>Balkone: {extractionResult.terrain_analysis.balconies_count}</li>
                      )}
                      {extractionResult.terrain_analysis.scaffold_notes && (
                        <li className="italic">{extractionResult.terrain_analysis.scaffold_notes}</li>
                      )}
                    </ul>
                  </div>
                )}

                {/* Bildtyp */}
                {extractionResult.image_type && (
                  <div className="mt-2 pt-2 border-t text-gray-400">
                    Bildtyp: {extractionResult.image_type}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Form */}
      <div className="card space-y-4">
        {/* Project Name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Projekttitel *
          </label>
          <input
            type="text"
            className="input-field"
            placeholder="z.B. Gerüst Kirche St. Peter"
            value={data.project_name || ''}
            onChange={(e) => updateField('project_name', e.target.value)}
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
            value={data.address || ''}
            onChange={(e) => updateField('address', e.target.value)}
            placeholder="Strasse Nr, PLZ Ort"
            required
          />
        </div>

        {/* Client Info */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Auftraggeber
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="Name / Firma"
              value={data.client_name || ''}
              onChange={(e) => updateField('client_name', e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Kontakt
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="Tel / E-Mail"
              value={data.client_contact || ''}
              onChange={(e) => updateField('client_contact', e.target.value)}
            />
          </div>
        </div>

        {/* Tender Number */}
        {(data.tender_number || source === 'url') && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Ausschreibungs-Nr.
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="z.B. 2024-BER-12345"
              value={data.tender_number || ''}
              onChange={(e) => updateField('tender_number', e.target.value)}
            />
          </div>
        )}

        {/* Dates */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Eingabefrist
            </label>
            <input
              type="date"
              className="input-field"
              value={data.submission_deadline || ''}
              onChange={(e) => updateField('submission_deadline', e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Projektstart
            </label>
            <input
              type="date"
              className="input-field"
              value={data.project_start || ''}
              onChange={(e) => updateField('project_start', e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Projektende
            </label>
            <input
              type="date"
              className="input-field"
              value={data.project_end || ''}
              onChange={(e) => updateField('project_end', e.target.value)}
            />
          </div>
        </div>

        {/* Procedure (if from simap.ch) */}
        {(data.procedure || source === 'url') && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Verfahren
            </label>
            <select
              className="input-field"
              value={data.procedure || ''}
              onChange={(e) => {
                const val = e.target.value as ExtractedProjectData['procedure']
                onChange({ ...data, procedure: val || undefined })
              }}
            >
              <option value="">-- wählen --</option>
              <option value="open">Offenes Verfahren</option>
              <option value="selective">Selektives Verfahren</option>
              <option value="invitation">Einladungsverfahren</option>
              <option value="negotiated">Freihändiges Verfahren</option>
            </select>
          </div>
        )}

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Beschreibung
          </label>
          <textarea
            className="input-field min-h-[100px]"
            placeholder="Projektdetails, besondere Anforderungen..."
            value={data.description || ''}
            onChange={(e) => updateField('description', e.target.value)}
          />
        </div>
      </div>

      {/* Navigation Buttons */}
      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          className="btn-secondary flex-1"
        >
          Zurück
        </button>
        <button
          type="button"
          onClick={onNext}
          disabled={!isValid}
          className="btn-primary flex-1"
        >
          Weiter
        </button>
      </div>
    </div>
  )
}
