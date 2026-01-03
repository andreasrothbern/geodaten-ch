import { useState, useEffect } from 'react'
import {
  MapPin,
  Building2,
  Ruler,
  Layers,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import type { ExtractedProjectData, Geodata } from '../../../types/project'

interface GeodataStepProps {
  data: ExtractedProjectData
  source: 'pdf' | 'photo' | 'url' | 'manual'
  loadGeodata: (address: string) => Promise<Geodata | null>
  onBack: () => void
  onSubmit: (geodata: Geodata | null) => void
  loading: boolean
}

interface LoadingState {
  geocoding: 'pending' | 'loading' | 'success' | 'error'
  gwr: 'pending' | 'loading' | 'success' | 'error'
  building3d: 'pending' | 'loading' | 'success' | 'error'  // Höhen + Polygon aus swissBUILDINGS3D
}

export default function GeodataStep({
  data,
  source: _source,  // Reserved for future source-specific handling
  loadGeodata,
  onBack,
  onSubmit,
  loading,
}: GeodataStepProps) {
  void _source  // Suppress unused variable warning
  const [geodata, setGeodata] = useState<Geodata | null>(null)
  const [loadingStates, setLoadingStates] = useState<LoadingState>({
    geocoding: 'pending',
    gwr: 'pending',
    building3d: 'pending',
  })
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const loadData = async () => {
    if (!data.address) return

    setIsLoading(true)
    setError(null)
    setGeodata(null)

    // Simulate progressive loading
    setLoadingStates({ geocoding: 'loading', gwr: 'pending', building3d: 'pending' })

    try {
      // Small delay to show animation
      await new Promise((r) => setTimeout(r, 300))
      setLoadingStates((s) => ({ ...s, geocoding: 'success', gwr: 'loading' }))

      await new Promise((r) => setTimeout(r, 200))
      setLoadingStates((s) => ({ ...s, gwr: 'success', building3d: 'loading' }))

      // Actually load the data (swissBUILDINGS3D: Höhen + Polygon in einem Aufruf)
      const result = await loadGeodata(data.address)

      setLoadingStates((s) => ({ ...s, building3d: 'success' }))
      setGeodata(result)

      if (!result) {
        setError('Keine Gebäudedaten gefunden')
      }
    } catch (err) {
      console.error('Fehler beim Laden der Grunddaten:', err)
      setError('Fehler beim Laden der Grunddaten')
      setLoadingStates({
        geocoding: 'error',
        gwr: 'error',
        building3d: 'error',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [data.address])

  const getStatusIcon = (status: 'pending' | 'loading' | 'success' | 'error') => {
    switch (status) {
      case 'loading':
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />
      default:
        return <div className="w-4 h-4 rounded-full bg-gray-200" />
    }
  }

  return (
    <div className="space-y-4">
      {/* Address Header */}
      <div className="card bg-gray-50 border-gray-200">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-gray-600" />
          <span className="text-sm text-gray-700">{data.address}</span>
        </div>
      </div>

      {/* Loading Progress */}
      <div className="card">
        <h3 className="font-medium mb-4">Grunddaten werden geladen...</h3>

        <div className="space-y-3">
          <div className="flex items-center gap-3">
            {getStatusIcon(loadingStates.geocoding)}
            <span className="text-sm">Adresse geocodieren (swisstopo)</span>
          </div>
          <div className="flex items-center gap-3">
            {getStatusIcon(loadingStates.gwr)}
            <span className="text-sm">GWR-Daten abrufen (EGID, Geschosse)</span>
          </div>
          <div className="flex items-center gap-3">
            {getStatusIcon(loadingStates.building3d)}
            <span className="text-sm">3D-Gebäudedaten laden (swissBUILDINGS3D)</span>
          </div>
        </div>
      </div>

      {/* Building Data Card */}
      {geodata && (
        <div className="card border-green-200 bg-green-50">
          <h3 className="font-medium text-green-800 mb-3 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5" />
            Gebäude gefunden
          </h3>

          <div className="grid grid-cols-2 gap-4 text-sm">
            {geodata.egid && (
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-green-600" />
                <div>
                  <span className="text-green-700">EGID:</span>{' '}
                  <strong>{geodata.egid}</strong>
                </div>
              </div>
            )}

            {geodata.traufhoehe_m && (
              <div className="flex items-center gap-2">
                <Ruler className="w-4 h-4 text-green-600" />
                <div>
                  <span className="text-green-700">Traufhöhe:</span>{' '}
                  <strong>{geodata.traufhoehe_m.toFixed(1)} m</strong>
                </div>
              </div>
            )}

            {geodata.firsthoehe_m && (
              <div className="flex items-center gap-2">
                <Ruler className="w-4 h-4 text-green-600" />
                <div>
                  <span className="text-green-700">Firsthöhe:</span>{' '}
                  <strong>{geodata.firsthoehe_m.toFixed(1)} m</strong>
                </div>
              </div>
            )}

            {geodata.area_m2 && (
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-green-600" />
                <div>
                  <span className="text-green-700">Fläche:</span>{' '}
                  <strong>{geodata.area_m2.toFixed(0)} m²</strong>
                </div>
              </div>
            )}

            {geodata.perimeter_m && (
              <div className="flex items-center gap-2">
                <Ruler className="w-4 h-4 text-green-600" />
                <div>
                  <span className="text-green-700">Umfang:</span>{' '}
                  <strong>{geodata.perimeter_m.toFixed(1)} m</strong>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="card border-yellow-200 bg-yellow-50">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-yellow-800">{error}</p>
              <p className="text-sm text-yellow-700 mt-1">
                Das Projekt kann trotzdem erstellt werden. Grunddaten können später
                manuell ergänzt werden.
              </p>
              <button
                type="button"
                onClick={loadData}
                className="mt-2 text-sm text-yellow-800 hover:text-yellow-900 inline-flex items-center gap-1"
              >
                <RefreshCw className="w-4 h-4" />
                Erneut versuchen
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Summary */}
      <div className="card">
        <h3 className="font-medium mb-3">Zusammenfassung</h3>
        <dl className="text-sm space-y-2">
          <div className="flex justify-between">
            <dt className="text-gray-600">Projekt:</dt>
            <dd className="font-medium">{data.project_name}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-600">Adresse:</dt>
            <dd className="font-medium">{data.address}</dd>
          </div>
          {data.client_name && (
            <div className="flex justify-between">
              <dt className="text-gray-600">Auftraggeber:</dt>
              <dd className="font-medium">{data.client_name}</dd>
            </div>
          )}
          {data.submission_deadline && (
            <div className="flex justify-between">
              <dt className="text-gray-600">Eingabefrist:</dt>
              <dd className="font-medium">
                {new Date(data.submission_deadline).toLocaleDateString('de-CH')}
              </dd>
            </div>
          )}
        </dl>
      </div>

      {/* Navigation Buttons */}
      <div className="flex gap-3">
        <button
          type="button"
          onClick={onBack}
          disabled={loading}
          className="btn-secondary flex-1"
        >
          Zurück
        </button>
        <button
          type="button"
          onClick={() => onSubmit(geodata)}
          disabled={loading || isLoading}
          className="btn-primary flex-1 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Wird erstellt...
            </>
          ) : (
            'Projekt erstellen'
          )}
        </button>
      </div>
    </div>
  )
}
