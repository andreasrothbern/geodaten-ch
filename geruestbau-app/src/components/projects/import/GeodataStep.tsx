import { useState, useEffect, useCallback } from 'react'
import {
  MapPin,
  Building2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  Zap,
  Bot,
  Database,
  Settings,
  Download,
} from 'lucide-react'
import type { ExtractedProjectData, Geodata, BuildingEntry, ZoneInfo } from '../../../types/project'
import BuildingDataCard from '../../ui/BuildingDataCard'
import { geruestbauApi } from '../../../api/geruestbau'
import { useBuildingDataStream, type CompleteData, type ZonesData, type ErrorData } from '../../../hooks/useBuildingDataStream'

interface GeodataStepProps {
  data: ExtractedProjectData
  source: 'pdf' | 'photo' | 'url' | 'manual'
  loadGeodata?: (address: string) => Promise<Geodata | null>  // Optional, nur für Fallback
  onBack: () => void
  onSubmit: (geodata: Geodata | null, buildings?: BuildingEntry[]) => void
  loading: boolean
  onLoadComplete?: (success: boolean) => void
}

interface LoadingState {
  geocoding: 'pending' | 'loading' | 'success' | 'error'
  gwr: 'pending' | 'loading' | 'success' | 'error'
  building3d: 'pending' | 'loading' | 'success' | 'error'  // Höhen + Polygon aus swissBUILDINGS3D
  enrichment: 'pending' | 'loading' | 'success' | 'error'  // Enrichment: Terrain + Hanglage (nach 3D-Daten)
  research: 'pending' | 'loading' | 'success' | 'error'    // Gebäude-Recherche (parallel mit Enrichment)
}

// Status-Detail für Recherche-Phase
type ResearchStatus = 'idle' | 'checking_known' | 'calling_claude' | 'done'

export default function GeodataStep({
  data,
  source: _source,  // Reserved for future source-specific handling
  loadGeodata: _loadGeodata,  // Unused - kept for backwards compatibility
  onBack,
  onSubmit,
  loading,
  onLoadComplete,
}: GeodataStepProps) {
  void _source  // Suppress unused variable warning
  void _loadGeodata  // Unused - we use streaming now

  const [geodata, setGeodata] = useState<Geodata | null>(null)
  const [buildings, setBuildings] = useState<BuildingEntry[]>([])
  const [addressErrors, setAddressErrors] = useState<{ address: string; error: string }[]>([])
  const [isMultiAddress, setIsMultiAddress] = useState(false)
  const [loadingStates, setLoadingStates] = useState<LoadingState>({
    geocoding: 'pending',
    gwr: 'pending',
    building3d: 'pending',
    enrichment: 'pending',
    research: 'pending',
  })
  const [researchStatus, setResearchStatus] = useState<ResearchStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const [isLoadingMulti, setIsLoadingMulti] = useState(false)

  // ==========================================================================
  // SSE Streaming Hook für Single-Address
  // ==========================================================================
  const {
    start: startStream,
    isLoading: isStreamLoading,
    isDownloading,
  } = useBuildingDataStream({
    includeResearch: false,  // Research wird separat im zones-Step gemacht
    includeZones: true,
    includeTerrain: true,

    // Event Callbacks - Update loading states progressiv
    onGeocoding: useCallback(() => {
      setLoadingStates((s) => ({ ...s, geocoding: 'success', gwr: 'loading' }))
    }, []),

    onGWR: useCallback(() => {
      setLoadingStates((s) => ({ ...s, gwr: 'success', building3d: 'loading' }))
    }, []),

    onPolygon: useCallback(() => {
      setLoadingStates((s) => ({ ...s, building3d: 'success', enrichment: 'loading' }))
    }, []),

    onTerrain: useCallback(() => {
      setLoadingStates((s) => ({ ...s, enrichment: 'success', research: 'loading' }))
      setResearchStatus('checking_known')
    }, []),

    onZones: useCallback((zonesData: ZonesData) => {
      // Zones enthält auch building_name wenn vorhanden
      if (zonesData.source === 'claude') {
        setResearchStatus('calling_claude')
      }
      setLoadingStates((s) => ({ ...s, research: 'success' }))
      setResearchStatus('done')
    }, []),

    onComplete: useCallback((completeData: CompleteData) => {
      // Stream komplett - Geodata aus Bundle aufbauen
      const bundle = completeData.bundle
      const newGeodata: Geodata = {
        egid: completeData.egid ?? undefined,
        address: completeData.address,
        traufhoehe_m: bundle.traufhoehe_m ?? undefined,
        firsthoehe_m: bundle.firsthoehe_m ?? undefined,
        gebaeudehoehe_m: bundle.gebaeudehoehe_m ?? undefined,
        terrain_height_m: bundle.terrain?.reference_height_m,
        slope_class: bundle.terrain?.slope_class,
        polygon: bundle.polygon ?? undefined,
        sides: bundle.sides ?? undefined,
        perimeter_m: bundle.perimeter_m ?? undefined,
        footprint_area_m2: bundle.footprint_area_m2 ?? undefined,
        gwr_floors: bundle.gwr_floors ?? undefined,
        gwr_area_m2: bundle.gwr_area_m2 ?? undefined,
        gwr_category: bundle.gwr_category ?? undefined,
        gwr_category_code: bundle.gwr_category_code ?? undefined,
        zones: bundle.zones?.map(z => ({
          ...z,
          zone_type: z.zone_type as ZoneInfo['zone_type'],
          traufhoehe_m: z.traufhoehe_m ?? undefined,
          firsthoehe_m: z.firsthoehe_m ?? undefined,
          sonderkonstruktion: ['turm', 'kuppel'].includes(z.zone_type),
          confidence: 1.0,
        })) ?? undefined,
        complexity: (bundle.complexity as Geodata['complexity']) ?? undefined,
        building_name: bundle.building_name ?? undefined,
        research_source: (bundle.research_source as Geodata['research_source']) ?? (bundle.zones && bundle.zones.length > 0 ? 'auto' : undefined),
        coordinates: bundle.lv95_e && bundle.lv95_n ? {
          lv95_e: bundle.lv95_e,
          lv95_n: bundle.lv95_n,
        } : undefined,
      }
      setGeodata(newGeodata)
      setResearchStatus('done')
    }, []),

    onError: useCallback((errorData: ErrorData) => {
      setError(errorData.message)
      setLoadingStates((s) => ({
        ...s,
        geocoding: s.geocoding === 'loading' ? 'error' : s.geocoding,
        gwr: s.gwr === 'loading' ? 'error' : s.gwr,
        building3d: s.building3d === 'loading' ? 'error' : s.building3d,
        enrichment: s.enrichment === 'loading' ? 'error' : s.enrichment,
        research: s.research === 'loading' ? 'error' : s.research,
      }))
      setResearchStatus('done')
    }, []),
  })

  // Kombinierter Loading-State
  const isLoading = isStreamLoading || isLoadingMulti

  // ==========================================================================
  // Multi-Address Laden (Range wie "2-10")
  // ==========================================================================
  const loadMultiAddress = useCallback(async (address: string) => {
    setIsLoadingMulti(true)
    setError(null)
    setGeodata(null)
    setBuildings([])
    setAddressErrors([])
    setIsMultiAddress(true)
    setLoadingStates({ geocoding: 'loading', gwr: 'pending', building3d: 'pending', enrichment: 'pending', research: 'pending' })

    try {
      setLoadingStates((s) => ({ ...s, geocoding: 'success', gwr: 'loading' }))
      const resolved = await geruestbauApi.resolveAddressRange(address)
      setLoadingStates((s) => ({ ...s, gwr: 'success', building3d: 'loading' }))

      if (resolved.buildings && resolved.buildings.length > 0) {
        const buildingEntries: BuildingEntry[] = resolved.buildings.map(b => ({
          egid: b.egid,
          address: b.matched_address || b.address,
          traufhoehe_m: b.traufhoehe_m,
          firsthoehe_m: b.firsthoehe_m,
          coordinates: b.coordinates,
          egid_source: 'swissBUILDINGS3D',
        }))
        setBuildings(buildingEntries)

        const firstBuilding = resolved.buildings[0]
        setGeodata({
          egid: firstBuilding.egid,
          address: firstBuilding.matched_address || firstBuilding.address,
          traufhoehe_m: firstBuilding.traufhoehe_m,
          firsthoehe_m: firstBuilding.firsthoehe_m,
        })
        setLoadingStates((s) => ({ ...s, building3d: 'success', enrichment: 'success', research: 'success' }))
      } else {
        setError(`Keine Gebäude gefunden für: ${address}`)
        setLoadingStates((s) => ({ ...s, building3d: 'error', enrichment: 'error', research: 'error' }))
      }

      if (resolved.errors && resolved.errors.length > 0) {
        setAddressErrors(resolved.errors.map(e => ({ address: e, error: 'Adresse nicht gefunden' })))
      }
    } catch (err) {
      console.error('Fehler beim Laden der Grunddaten:', err)
      setError('Fehler beim Laden der Grunddaten')
      setLoadingStates({ geocoding: 'error', gwr: 'error', building3d: 'error', enrichment: 'error', research: 'error' })
    } finally {
      setIsLoadingMulti(false)
    }
  }, [])

  // ==========================================================================
  // Start Loading - Entscheidung Single vs Multi
  // ==========================================================================
  const loadData = useCallback(() => {
    if (!data.address) return

    setError(null)
    setGeodata(null)
    setBuildings([])
    setAddressErrors([])
    setResearchStatus('idle')
    setLoadingStates({ geocoding: 'loading', gwr: 'pending', building3d: 'pending', enrichment: 'pending', research: 'pending' })

    // Check if address contains a range (e.g., "2-10" or "1-9")
    const hasRange = /\d+\s*-\s*\d+/.test(data.address)

    if (hasRange) {
      setIsMultiAddress(true)
      loadMultiAddress(data.address)
    } else {
      setIsMultiAddress(false)
      startStream(data.address)
    }
  }, [data.address, loadMultiAddress, startStream])

  // Initial load
  useEffect(() => {
    loadData()
  }, [data.address])  // Only re-run when address changes, not loadData

  // Notify parent when loading completes
  useEffect(() => {
    if (!isLoading && onLoadComplete) {
      const allSuccess =
        loadingStates.geocoding === 'success' &&
        loadingStates.gwr === 'success' &&
        loadingStates.building3d === 'success' &&
        (loadingStates.enrichment === 'success' || loadingStates.enrichment === 'pending') &&
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
            <div className="flex items-center gap-2">
              <span className="text-sm">3D-Daten laden</span>
              {/* Tile-Download Indikator */}
              {isDownloading && loadingStates.building3d === 'loading' && (
                <span className="text-xs text-blue-600 font-medium inline-flex items-center gap-1">
                  <Download className="w-3 h-3 animate-bounce" />
                  Lade Gebäudedaten von swisstopo...
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            {getStatusIcon(loadingStates.enrichment)}
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

      {/* Building Data Card - Single Address (Shared Component) */}
      {!isMultiAddress && geodata && <BuildingDataCard geodata={geodata} />}

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
