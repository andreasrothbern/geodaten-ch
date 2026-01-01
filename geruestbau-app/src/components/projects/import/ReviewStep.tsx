import { FileText, Link2, Camera, Pen, AlertCircle } from 'lucide-react'
// AddressAutocomplete deaktiviert - einfaches Textfeld stattdessen
// import AddressAutocomplete from '../../ui/AddressAutocomplete'
import type { ExtractedProjectData } from '../../../types/project'

interface ReviewStepProps {
  data: ExtractedProjectData
  source: 'pdf' | 'photo' | 'url' | 'manual'
  confidence?: number
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
  onChange,
  onBack,
  onNext,
}: ReviewStepProps) {
  const SourceIcon = sourceIcons[source]
  const isFromExtraction = source !== 'manual'

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
          <p className="text-xs text-gray-500 mt-2 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            Bitte die extrahierten Daten überprüfen und ggf. korrigieren
          </p>
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
