import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, CheckCircle2, Loader2 } from 'lucide-react'
import { geruestbauApi } from '../api/geruestbau'
import FileUpload from '../components/ui/FileUpload'
import type { TenderData, OcrExtractionResult } from '../types/project'

interface FormData {
  name: string
  address: string
  client_name: string
  client_contact: string
  description: string
  tender_number: string
  submission_deadline: string
  project_start: string
  project_end: string
  is_urgent: boolean
  requires_special: boolean
}

export default function NewProjectPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [extractionResult, setExtractionResult] = useState<OcrExtractionResult | null>(null)
  const [form, setForm] = useState<FormData>({
    name: '',
    address: '',
    client_name: '',
    client_contact: '',
    description: '',
    tender_number: '',
    submission_deadline: '',
    project_start: '',
    project_end: '',
    is_urgent: false,
    requires_special: false,
  })

  const handleFileSelect = useCallback(async (file: File) => {
    setSelectedFile(file)
    setExtractionResult(null)
    setExtracting(true)

    try {
      const result = await geruestbauApi.extractFromDocument(file)
      setExtractionResult(result)

      if (result.success && result.data) {
        // Auto-fill form with extracted data
        setForm((prev) => ({
          ...prev,
          name: result.data?.project_name || prev.name,
          address: result.data?.address || prev.address,
          client_name: result.data?.client_name || prev.client_name,
          client_contact: result.data?.client_contact || prev.client_contact,
          description: result.data?.description || prev.description,
          tender_number: result.data?.tender_number || prev.tender_number,
          submission_deadline: result.data?.submission_deadline || prev.submission_deadline,
          project_start: result.data?.project_start || prev.project_start,
          project_end: result.data?.project_end || prev.project_end,
        }))
      }
    } catch (error) {
      console.error('Fehler bei OCR-Extraktion:', error)
      setExtractionResult({
        success: false,
        confidence: 0,
        error: 'Fehler beim Analysieren des Dokuments',
      })
    } finally {
      setExtracting(false)
    }
  }, [])

  const handleClearFile = useCallback(() => {
    setSelectedFile(null)
    setExtractionResult(null)
  }, [])

  const handleCameraCapture = useCallback(() => {
    // Create a file input that only accepts camera
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.capture = 'environment' // Use back camera
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (file) {
        handleFileSelect(file)
      }
    }
    input.click()
  }, [handleFileSelect])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      // Prepare tender data
      const tenderData: TenderData = {
        tender_number: form.tender_number || undefined,
        submission_deadline: form.submission_deadline || undefined,
        project_start: form.project_start || undefined,
        project_end: form.project_end || undefined,
        is_urgent: form.is_urgent,
        requires_special: form.requires_special,
        source: selectedFile
          ? selectedFile.type === 'application/pdf'
            ? 'pdf'
            : 'photo'
          : 'manual',
        confidence: extractionResult?.confidence,
        raw_text: extractionResult?.raw_text,
      }

      const project = await geruestbauApi.createProject({
        name: form.name,
        address: form.address,
        client_name: form.client_name || undefined,
        client_contact: form.client_contact || undefined,
        description: form.description || undefined,
        deadline: form.submission_deadline || undefined,
        tender_data: tenderData,
      })

      // Automatisch Geodaten abrufen
      await geruestbauApi.enrichProject(project.id)
      navigate(`/projects/${project.id}`)
    } catch (error) {
      console.error('Fehler beim Erstellen:', error)
      alert('Fehler beim Erstellen des Projekts')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 pb-24">
      {/* File Upload Section */}
      <div className="card">
        <FileUpload
          onFileSelect={handleFileSelect}
          onCameraCapture={handleCameraCapture}
          loading={extracting}
          disabled={loading}
          selectedFile={selectedFile}
          onClear={handleClearFile}
        />

        {/* Extraction Result */}
        {extractionResult && (
          <div
            className={`mt-4 p-3 rounded-lg flex items-start gap-2 ${
              extractionResult.success
                ? 'bg-green-50 text-green-800'
                : 'bg-red-50 text-red-800'
            }`}
          >
            {extractionResult.success ? (
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            )}
            <div>
              {extractionResult.success ? (
                <>
                  <p className="font-medium">Daten erfolgreich extrahiert</p>
                  <p className="text-sm opacity-80">
                    Konfidenz: {Math.round((extractionResult.confidence || 0) * 100)}%
                    — Bitte Daten prüfen
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
        )}
      </div>

      {/* Manual/Extracted Data Form */}
      <div className="card">
        <div className="space-y-4">
          {/* Project Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Projektname *
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="z.B. Gerüst Kirche St. Peter"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
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
              placeholder="Strasse Nr, PLZ Ort"
              value={form.address}
              onChange={(e) => setForm({ ...form, address: e.target.value })}
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Geodaten werden automatisch von geodaten-ch abgerufen
            </p>
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
                value={form.client_name}
                onChange={(e) => setForm({ ...form, client_name: e.target.value })}
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
                value={form.client_contact}
                onChange={(e) => setForm({ ...form, client_contact: e.target.value })}
              />
            </div>
          </div>

          {/* Tender Number */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Ausschreibungs-Nr.
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="z.B. 2024-BER-12345"
              value={form.tender_number}
              onChange={(e) => setForm({ ...form, tender_number: e.target.value })}
            />
          </div>

          {/* Dates */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Eingabefrist
              </label>
              <input
                type="date"
                className="input-field"
                value={form.submission_deadline}
                onChange={(e) =>
                  setForm({ ...form, submission_deadline: e.target.value })
                }
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Projektstart
              </label>
              <input
                type="date"
                className="input-field"
                value={form.project_start}
                onChange={(e) => setForm({ ...form, project_start: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Projektende
              </label>
              <input
                type="date"
                className="input-field"
                value={form.project_end}
                onChange={(e) => setForm({ ...form, project_end: e.target.value })}
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Beschreibung
            </label>
            <textarea
              className="input-field min-h-[100px]"
              placeholder="Projektdetails, besondere Anforderungen..."
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>

          {/* Checkboxes */}
          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="w-5 h-5 rounded border-gray-300 text-primary-600
                           focus:ring-primary-500 cursor-pointer"
                checked={form.is_urgent}
                onChange={(e) => setForm({ ...form, is_urgent: e.target.checked })}
              />
              <span className="text-gray-700">Dringend</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="w-5 h-5 rounded border-gray-300 text-primary-600
                           focus:ring-primary-500 cursor-pointer"
                checked={form.requires_special}
                onChange={(e) =>
                  setForm({ ...form, requires_special: e.target.checked })
                }
              />
              <span className="text-gray-700">Sonderkonstruktion erforderlich</span>
            </label>
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        className="btn-primary flex items-center justify-center gap-2"
        disabled={loading || extracting || !form.name || !form.address}
      >
        {loading ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Wird erstellt...
          </>
        ) : (
          'Projekt erstellen & Geodaten abrufen'
        )}
      </button>
    </form>
  )
}
