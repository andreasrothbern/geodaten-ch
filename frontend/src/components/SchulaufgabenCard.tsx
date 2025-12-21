import { useState } from 'react'

interface SchulaufgabenCardProps {
  address: string
  apiUrl: string
}

export function SchulaufgabenCard({ address, apiUrl }: SchulaufgabenCardProps) {
  const [authorName, setAuthorName] = useState('Teilnehmer GL 2025')
  const [projectDescription, setProjectDescription] = useState('Fassadensanierung')
  const [includeReflexion, setIncludeReflexion] = useState(true)
  const [downloading, setDownloading] = useState(false)

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const params = new URLSearchParams({
        address,
        author_name: authorName,
        project_description: projectDescription,
        include_reflexion: includeReflexion.toString()
      })

      const response = await fetch(`${apiUrl}/api/v1/document/materialbewirtschaftung?${params}`)

      if (!response.ok) {
        throw new Error('Fehler beim Generieren des Dokuments')
      }

      // Get filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = 'Materialbewirtschaftung.docx'
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="(.+)"/)
        if (match) filename = match[1]
      }

      // Download the file
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Download error:', err)
      alert('Fehler beim Generieren des Dokuments. Bitte versuchen Sie es erneut.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="card space-y-6">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        <span>Schulaufgaben</span>
      </h3>

      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
        <h4 className="font-medium text-blue-900 mb-2">
          Materialbewirtschaftung GL 2025
        </h4>
        <p className="text-sm text-blue-700 mb-4">
          Generiert ein vollstandiges Word-Dokument (ca. 20 Seiten) fur die
          Gruppenleiter-Schulung mit:
        </p>
        <ul className="text-sm text-blue-700 space-y-1 mb-4">
          <li>1. Baustellenbeschrieb</li>
          <li>2. Ausmass nach NPK 114 D/2012</li>
          <li>3. Materialliste Layher Blitz 70</li>
          <li>4. Personalbedarf</li>
          <li>5. Dokumentation Baustelle & Sicherheitskonzept</li>
          <li>6. Reflexion (Vorlage zum Ausfullen)</li>
          <li>7. Anhang (Gerustkarte, Checkliste)</li>
        </ul>
      </div>

      {/* Formular */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Adresse (Baustelle)
          </label>
          <input
            type="text"
            value={address}
            disabled
            className="w-full px-3 py-2 bg-gray-100 border border-gray-300 rounded-lg text-gray-700"
          />
          <p className="text-xs text-gray-500 mt-1">
            Basierend auf der aktuell geladenen Adresse
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Verfasser
          </label>
          <input
            type="text"
            value={authorName}
            onChange={(e) => setAuthorName(e.target.value)}
            placeholder="Ihr Name"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Bauvorhaben
          </label>
          <input
            type="text"
            value={projectDescription}
            onChange={(e) => setProjectDescription(e.target.value)}
            placeholder="z.B. Fassadensanierung"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="includeReflexion"
            checked={includeReflexion}
            onChange={(e) => setIncludeReflexion(e.target.checked)}
            className="rounded border-gray-300 text-red-600 focus:ring-red-500"
          />
          <label htmlFor="includeReflexion" className="text-sm text-gray-700">
            Reflexions-Vorlage inkludieren (Kapitel 6)
          </label>
        </div>
      </div>

      {/* Download Button */}
      <div className="flex justify-center pt-4">
        <button
          onClick={handleDownload}
          disabled={downloading || !address}
          className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2 text-lg font-medium"
        >
          {downloading ? (
            <>
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Wird generiert...
            </>
          ) : (
            <>
              Word-Dokument herunterladen
            </>
          )}
        </button>
      </div>

      {/* Info */}
      <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600">
        <p className="font-medium mb-2">Hinweise:</p>
        <ul className="space-y-1">
          <li>Das Dokument basiert auf der NPK 114 D/2012 Norm</li>
          <li>Alle Berechnungen sind automatisch aus den Geodaten generiert</li>
          <li>Bilder/Zeichnungen mussen manuell hinzugefugt werden (siehe API-Endpunkte fur SVG)</li>
          <li>Die Reflexion (Kapitel 6) ist eine Vorlage zum Ausfullen</li>
        </ul>
      </div>
    </div>
  )
}
