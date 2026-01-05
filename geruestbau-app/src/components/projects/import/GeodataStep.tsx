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
  Mountain,
  Box,
  Zap,
  Bot,
  Database,
  Settings,
  Landmark,
} from 'lucide-react'
import type { ExtractedProjectData, Geodata, BuildingEntry } from '../../../types/project'
import { geruestbauApi } from '../../../api/geruestbau'

interface GeodataStepProps {
  data: ExtractedProjectData
  source: 'pdf' | 'photo' | 'url' | 'manual'
  loadGeodata: (address: string) => Promise<Geodata | null>
  onBack: () => void
  onSubmit: (geodata: Geodata | null, buildings?: BuildingEntry[]) => void
  loading: boolean
  onLoadComplete?: (success: boolean) => void
}

interface LoadingState {
  geocoding: 'pending' | 'loading' | 'success' | 'error'
  gwr: 'pending' | 'loading' | 'success' | 'error'
  building3d: 'pending' | 'loading' | 'success' | 'error'  // Höhen + Polygon aus swissBUILDINGS3D
  terrain: 'pending' | 'loading' | 'success' | 'error'     // Terrain + Hanglage
  research: 'pending' | 'loading' | 'success' | 'error'    // Gebäude-Recherche (known_buildings / Claude API)
}

// Status-Detail für Recherche-Phase
type ResearchStatus = 'idle' | 'checking_known' | 'calling_claude' | 'done'

export default function GeodataStep({
  data,
  source: _source,  // Reserved for future source-specific handling
  loadGeodata,
  onBack,
  onSubmit,
  loading,
  onLoadComplete,
}: GeodataStepProps) {
  void _source  // Suppress unused variable warning
  const [geodata, setGeodata] = useState<Geodata | null>(null)
  const [buildings, setBuildings] = useState<BuildingEntry[]>([])
  const [addressErrors, setAddressErrors] = useState<{ address: string; error: string }[]>([])
  const [isMultiAddress, setIsMultiAddress] = useState(false)
  const [loadingStates, setLoadingStates] = useState<LoadingState>({
    geocoding: 'pending',
    gwr: 'pending',
    building3d: 'pending',
    terrain: 'pending',
    research: 'pending',
  })
  const [researchStatus, setResearchStatus] = useState<ResearchStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const loadData = async () => {
    if (!data.address) return

    setIsLoading(true)
    setError(null)
    setGeodata(null)
    setBuildings([])
    setAddressErrors([])
    setIsMultiAddress(false)

    // Simulate progressive loading
    setLoadingStates({ geocoding: 'loading', gwr: 'pending', building3d: 'pending', terrain: 'pending', research: 'pending' })
    setResearchStatus('idle')

    try {
      // Check if address contains a range (e.g., "2-10" or "1-9")
      const hasRange = /\d+\s*-\s*\d+/.test(data.address)

      if (hasRange) {
        // Multi-Address: Use address resolution API
        setIsMultiAddress(true)

        await new Promise((r) => setTimeout(r, 100))
        setLoadingStates((s) => ({ ...s, geocoding: 'success', gwr: 'loading' }))

        const resolved = await geruestbauApi.resolveAddressRange(data.address)

        await new Promise((r) => setTimeout(r, 100))
        setLoadingStates((s) => ({ ...s, gwr: 'success', building3d: 'loading' }))

        if (resolved.buildings && resolved.buildings.length > 0) {
          // Convert to BuildingEntry format
          const buildingEntries: BuildingEntry[] = resolved.buildings.map(b => ({
            egid: b.egid,
            address: b.matched_address || b.address,
            traufhoehe_m: b.traufhoehe_m,
            firsthoehe_m: b.firsthoehe_m,
            coordinates: b.coordinates,
            egid_source: 'swissBUILDINGS3D',
          }))
          setBuildings(buildingEntries)

          // Use first building for geodata display
          const firstBuilding = resolved.buildings[0]
          setGeodata({
            egid: firstBuilding.egid,
            address: firstBuilding.matched_address || firstBuilding.address,
            traufhoehe_m: firstBuilding.traufhoehe_m,
            firsthoehe_m: firstBuilding.firsthoehe_m,
          })
          setLoadingStates((s) => ({ ...s, building3d: 'success', terrain: 'loading', research: 'loading' }))

          // For multi-address projects, enrichment is done per-building when configuring
          // Mark as success since the basic data is loaded
          await new Promise((r) => setTimeout(r, 100))
          setLoadingStates((s) => ({ ...s, terrain: 'success', research: 'success' }))
        } else {
          setError(`Keine Gebäude gefunden für: ${data.address}`)
          setLoadingStates((s) => ({ ...s, building3d: 'error', terrain: 'error', research: 'error' }))
        }

        // Store address errors for display
        if (resolved.errors && resolved.errors.length > 0) {
          setAddressErrors(resolved.errors.map(e => ({ address: e, error: 'Adresse nicht gefunden' })))
        }
      } else {
        // Single Address: Use existing loadGeodata
        await new Promise((r) => setTimeout(r, 100))
        setLoadingStates((s) => ({ ...s, geocoding: 'success', gwr: 'loading' }))

        await new Promise((r) => setTimeout(r, 100))
        setLoadingStates((s) => ({ ...s, gwr: 'success', building3d: 'loading' }))

        // Show research status while loading (Backend macht beides parallel)
        setLoadingStates((s) => ({ ...s, terrain: 'loading', research: 'loading' }))
        setResearchStatus('checking_known')

        const result = await loadGeodata(data.address)
        setLoadingStates((s) => ({ ...s, building3d: 'success' }))
        setGeodata(result)

        if (!result) {
          setError('Keine Gebäudedaten gefunden')
          setLoadingStates((s) => ({ ...s, terrain: 'error', research: 'error' }))
          setResearchStatus('done')
        } else {
          // Update research status based on actual result
          if (result.research_source === 'known_buildings') {
            setResearchStatus('done')
          } else if (result.research_source === 'claude_api') {
            setResearchStatus('calling_claude')
            await new Promise((r) => setTimeout(r, 200)) // Brief pause to show Claude status
            setResearchStatus('done')
          } else {
            setResearchStatus('done')
          }

          // Mark terrain and research as success
          setLoadingStates((s) => ({
            ...s,
            terrain: result.terrain_height_m ? 'success' : 'success', // Even without terrain, mark as success
            research: result.zones && result.zones.length > 0 ? 'success' : 'success',
          }))
        }
      }
    } catch (err) {
      console.error('Fehler beim Laden der Grunddaten:', err)
      setError('Fehler beim Laden der Grunddaten')
      setLoadingStates({
        geocoding: 'error',
        gwr: 'error',
        building3d: 'error',
        terrain: 'error',
        research: 'error',
      })
      setResearchStatus('done')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [data.address])

  // Notify parent when loading completes
  useEffect(() => {
    if (!isLoading && onLoadComplete) {
      const allSuccess =
        loadingStates.geocoding === 'success' &&
        loadingStates.gwr === 'success' &&
        loadingStates.building3d === 'success' &&
        (loadingStates.terrain === 'success' || loadingStates.terrain === 'pending') &&
        (loadingStates.research === 'success' || loadingStates.research === 'pending')
      onLoadComplete(allSuccess)
    }
  }, [isLoading, loadingStates, onLoadComplete])

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

  // Research Source Badge - zeigt woher die Daten stammen
  const getResearchSourceBadge = (researchSource?: string) => {
    switch (researchSource) {
      case 'known_buildings':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">
            <Zap className="w-3 h-3" />
            Bekanntes Gebäude
          </span>
        )
      case 'claude_api':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            <Bot className="w-3 h-3" />
            Claude analysiert
          </span>
        )
      case 'cache':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
            <Database className="w-3 h-3" />
            Aus Cache
          </span>
        )
      case 'auto':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
            <Settings className="w-3 h-3" />
            Automatisch
          </span>
        )
      default:
        return null
    }
  }

  // Position Label für Zonen
  const getPositionLabel = (position?: string) => {
    switch (position) {
      case 'vorne':
        return 'Front'
      case 'zentral':
        return 'Zentral'
      case 'hinten':
        return 'Hinten'
      case 'flankierend':
        return 'Seite'
      default:
        return null
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
            <span className="text-sm">Adresse auflösen</span>
          </div>
          <div className="flex items-center gap-3">
            {getStatusIcon(loadingStates.gwr)}
            <span className="text-sm">Grundstück identifizieren</span>
          </div>
          <div className="flex items-center gap-3">
            {getStatusIcon(loadingStates.building3d)}
            <span className="text-sm">3D-Daten laden</span>
          </div>
          <div className="flex items-center gap-3">
            {getStatusIcon(loadingStates.terrain)}
            <span className="text-sm">Terrain & Hanglage</span>
          </div>
          <div className="flex items-center gap-3">
            {getStatusIcon(loadingStates.research)}
            <div className="flex items-center gap-2">
              <span className="text-sm">Gebäude-Recherche</span>
              {/* Live-Status der Recherche */}
              {loadingStates.research === 'loading' && (
                <span className="text-xs text-blue-600 font-medium">
                  {researchStatus === 'checking_known' && (
                    <span className="inline-flex items-center gap-1">
                      <Zap className="w-3 h-3" />
                      Prüfe bekannte Gebäude...
                    </span>
                  )}
                  {researchStatus === 'calling_claude' && (
                    <span className="inline-flex items-center gap-1">
                      <Bot className="w-3 h-3" />
                      Claude API analysiert...
                    </span>
                  )}
                </span>
              )}
              {/* Ergebnis-Badge nach Abschluss */}
              {loadingStates.research === 'success' && geodata?.research_source && (
                <span className="text-xs">
                  {geodata.research_source === 'known_buildings' && (
                    <span className="inline-flex items-center gap-1 text-emerald-600">
                      <Zap className="w-3 h-3" />
                      Bekanntes Gebäude
                    </span>
                  )}
                  {geodata.research_source === 'claude_api' && (
                    <span className="inline-flex items-center gap-1 text-blue-600">
                      <Bot className="w-3 h-3" />
                      Claude analysiert
                    </span>
                  )}
                  {geodata.research_source === 'cache' && (
                    <span className="inline-flex items-center gap-1 text-gray-600">
                      <Database className="w-3 h-3" />
                      Aus Cache
                    </span>
                  )}
                  {geodata.research_source === 'auto' && (
                    <span className="inline-flex items-center gap-1 text-yellow-600">
                      <Settings className="w-3 h-3" />
                      Automatisch
                    </span>
                  )}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Building Data Card - Multi-Address: Found */}
      {isMultiAddress && buildings.length > 0 && (
        <div className="card border-green-200 bg-green-50">
          <h3 className="font-medium text-green-800 mb-3 flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5" />
            {buildings.length} Gebäude gefunden
          </h3>

          <div className="space-y-2 text-sm max-h-48 overflow-y-auto">
            {buildings.map((building) => (
              <div
                key={building.egid}
                className="flex items-center justify-between p-2 bg-white rounded border border-green-100"
              >
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-green-600" />
                  <span className="font-medium">{building.address}</span>
                </div>
                <div className="flex items-center gap-3 text-gray-500">
                  <span className="text-xs">EGID: {building.egid}</span>
                  {building.traufhoehe_m && (
                    <span className="text-xs">H: {building.traufhoehe_m.toFixed(1)}m</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Address Errors - Multi-Address: Not Found */}
      {isMultiAddress && addressErrors.length > 0 && (
        <div className="card border-red-200 bg-red-50">
          <h3 className="font-medium text-red-800 mb-3 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            {addressErrors.length} Adresse{addressErrors.length > 1 ? 'n' : ''} nicht gefunden
          </h3>

          <div className="space-y-2 text-sm">
            {addressErrors.map((err, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2 p-2 bg-white rounded border border-red-100"
              >
                <Building2 className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <span className="font-medium text-red-700">{err.address}</span>
                  <p className="text-xs text-red-600 mt-0.5">{err.error}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Building Data Card - Single Address */}
      {!isMultiAddress && geodata && (
        <div className="card border-green-200 bg-green-50">
          {/* Header mit Gebäudename und Research-Source Badge */}
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="font-medium text-green-800 flex items-center gap-2">
                {geodata.building_name ? (
                  <>
                    <Landmark className="w-5 h-5" />
                    {geodata.building_name}
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-5 h-5" />
                    Gebäude gefunden
                  </>
                )}
              </h3>
              {geodata.complexity === 'complex' && (
                <span className="text-xs text-green-600 mt-0.5">Komplexes Gebäude</span>
              )}
            </div>
            {getResearchSourceBadge(geodata.research_source)}
          </div>

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

            {/* Enrichment: Terrain */}
            {geodata.terrain_height_m && (
              <div className="flex items-center gap-2">
                <Mountain className="w-4 h-4 text-green-600" />
                <div>
                  <span className="text-green-700">Geländehöhe:</span>{' '}
                  <strong>{geodata.terrain_height_m.toFixed(1)} m ü.M.</strong>
                </div>
              </div>
            )}

            {/* Enrichment: Hanglage */}
            {geodata.slope_class && (
              <div className="flex items-center gap-2">
                <Mountain className="w-4 h-4 text-green-600" />
                <div>
                  <span className="text-green-700">Hanglage:</span>{' '}
                  <strong>
                    {geodata.slope_class}
                    {geodata.slope_m !== undefined && ` (${geodata.slope_m.toFixed(1)}m)`}
                  </strong>
                </div>
              </div>
            )}

            {/* Enrichment: Zonen */}
            {geodata.zones && geodata.zones.length > 1 && (
              <div className="col-span-2 mt-2 pt-2 border-t border-green-200">
                <div className="flex items-center gap-2 mb-2">
                  <Box className="w-4 h-4 text-green-600" />
                  <span className="text-green-700 font-medium">
                    {geodata.zones.length} Gebäudezonen erkannt
                  </span>
                </div>
                <div className="space-y-1 text-xs">
                  {geodata.zones.map((zone) => (
                    <div
                      key={zone.id}
                      className="flex items-center justify-between p-1.5 bg-white rounded border border-green-100"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{zone.name}</span>
                        {zone.position && (
                          <span className="px-1.5 py-0.5 rounded bg-green-50 text-green-600 text-[10px]">
                            {getPositionLabel(zone.position)}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-gray-500">
                        <span>
                          {zone.firsthoehe_m?.toFixed(1) || zone.traufhoehe_m?.toFixed(1) || zone.gebaeudehoehe_m?.toFixed(1) || '–'} m
                        </span>
                        {zone.sonderkonstruktion && (
                          <span className="px-1 py-0.5 rounded bg-amber-50 text-amber-700 text-[10px]">
                            Spezial
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
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
          onClick={() => onSubmit(geodata, isMultiAddress ? buildings : undefined)}
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
