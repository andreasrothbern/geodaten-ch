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
import type { ExtractedProjectData, GeruestbauData, BuildingEntry, ZoneInfo, GeruestbauFassade } from '../../../types/project'
import BuildingDataCard from '../../ui/BuildingDataCard'
import { useBuildingDataStream, type CompleteData, type ZonesData, type ErrorData } from '../../../hooks/useBuildingDataStream'
// NEU 18.01.2026: Union-Polygon für Multi-Building
import { combineBuildings } from '../../../utils/polygonUnion'

interface GeodataStepProps {
  data: ExtractedProjectData
  source: 'pdf' | 'photo' | 'url' | 'manual'
  loadGeodata?: (address: string) => Promise<GeruestbauData | null>  // Optional, nur für Fallback
  onBack: () => void
  onSubmit: (data: GeruestbauData | null, buildings?: BuildingEntry[]) => void
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

  const [geruestbauData, setGeruestbauData] = useState<GeruestbauData | null>(null)
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

  // ==========================================================================
  // SSE Streaming Hook für Single-Address
  // ==========================================================================
  const {
    start: startStream,
    isLoading: isStreamLoading,
    isDownloading,
  } = useBuildingDataStream({
    // includeResearch: Default true - Backend entscheidet automatisch
    // basierend auf Gebäude-Komplexität (Fläche, GKAT, Polygon-Punkte)
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
      // NEU 18.01.2026: Multi-Building Support mit Union-Polygon
      // Prüfe ob Multi-Format (buildings[] Array vorhanden)
      if (completeData.buildings && completeData.buildings.length > 0) {
        // MULTI-BUILDING: Alle Gebäude verarbeiten
        const buildingEntries: BuildingEntry[] = completeData.buildings.map(b => ({
          egid: b.egid,
          address: b.matched_address,
          coordinates: b.bundle.lv95_e && b.bundle.lv95_n ? {
            lv95_e: b.bundle.lv95_e,
            lv95_n: b.bundle.lv95_n,
          } : undefined,
          egid_source: 'swissBUILDINGS3D',
          // Volle Daten für Projekt-Speicherung
          polygon: b.bundle.polygon ?? undefined,
          sides: b.bundle.sides ?? undefined,
          roof_dach_min_m: b.bundle.roof_dach_min_m ?? undefined,
          roof_dach_max_m: b.bundle.roof_dach_max_m ?? undefined,
          gebaeudehoehe_m: b.bundle.gebaeudehoehe_m ?? undefined,
          terrain: b.bundle.terrain ?? undefined,
          zones: b.bundle.zones ?? undefined,
          has_3d_layers: b.bundle.has_3d_layers ?? false,
        }))
        setBuildings(buildingEntries)
        setIsMultiAddress(true)

        // NEU 18.01.2026: GeruestbauData für JEDES Gebäude erstellen
        const allBuildingData: GeruestbauData[] = completeData.buildings.map(b => {
          const bundle = b.bundle
          const buildingFacades: GeruestbauFassade[] = (bundle.sides ?? []).map((side, index) => {
            const direction = side.direction ?? 'N'
            const terrainZMin = bundle.terrain?.facade_z_min?.[direction] ?? bundle.terrain?.reference_height_m ?? 0
            const terrainZMax = bundle.terrain?.facade_z_max?.[direction] ?? bundle.terrain?.reference_height_m ?? 0
            const wallZMax = bundle.roof_dach_min_m ?? terrainZMin + 8
            const heightM = wallZMax - Math.min(terrainZMin, terrainZMax)
            return {
              index,
              direction,
              start_point: (side.start_point ?? [0, 0]) as [number, number],
              end_point: (side.end_point ?? [0, 0]) as [number, number],
              length_m: side.length_m ?? 0,
              azimuth_deg: side.azimuth_deg ?? 0,
              terrain_z_min: terrainZMin,
              terrain_z_max: terrainZMax,
              wall_z_max: wallZMax,
              height_m: heightM,
              slope_m: Math.abs(terrainZMax - terrainZMin),
              height_source: (bundle.terrain?.facade_heights_source as GeruestbauFassade['height_source']) ?? 'building_global',
              is_blocked: false,
            }
          })
          return {
            building: {
              egid: b.egid,
              address: b.matched_address,
              polygon: bundle.polygon ?? [],
              center_e: bundle.lv95_e ?? 0,
              center_n: bundle.lv95_n ?? 0,
              perimeter_m: bundle.perimeter_m ?? 0,
              area_m2: bundle.footprint_area_m2 ?? 0,
              name: bundle.building_name ?? undefined,
              has_3d_layers: bundle.has_3d_layers ?? false,
              roof_dach_min_m: bundle.roof_dach_min_m ?? undefined,
              roof_dach_max_m: bundle.roof_dach_max_m ?? undefined,
            },
            facades: buildingFacades,
            walls: [],
            roofs: [],
            terrain: {
              height_m: bundle.terrain?.reference_height_m ?? 0,
              min_m: bundle.terrain?.min_height_m ?? bundle.terrain?.reference_height_m ?? 0,
              max_m: bundle.terrain?.max_height_m ?? bundle.terrain?.reference_height_m ?? 0,
              slope_m: bundle.terrain?.slope_m ?? 0,
              slope_class: (bundle.terrain?.slope_class as 'eben' | 'leicht' | 'mittel' | 'stark') ?? 'eben',
              requires_level_compensation: (bundle.terrain?.slope_m ?? 0) > 0.5,
            },
            heights: {
              // FIX 18.01.2026: Berechne relative Höhen aus absoluten Werten
              // traufhoehe = roof_dach_min_m (Traufe m ü.M.) - terrain_min (Boden m ü.M.)
              traufhoehe_m: bundle.roof_dach_min_m && bundle.terrain?.min_height_m
                ? bundle.roof_dach_min_m - bundle.terrain.min_height_m
                : undefined,
              firsthoehe_m: bundle.roof_dach_max_m && bundle.terrain?.min_height_m
                ? bundle.roof_dach_max_m - bundle.terrain.min_height_m
                : undefined,
              gebaeudehoehe_m: bundle.gebaeudehoehe_m ?? undefined,
              source: bundle.has_3d_layers ? 'swissBUILDINGS3D' : 'gwr_estimated',
            },
            zones: (bundle.zones ?? []).map(z => ({
              ...z,
              zone_type: z.zone_type as ZoneInfo['zone_type'],
              traufhoehe_m: z.traufhoehe_m ?? undefined,
              firsthoehe_m: z.firsthoehe_m ?? undefined,
              sonderkonstruktion: ['turm', 'kuppel'].includes(z.zone_type),
              confidence: 1.0,
            })),
            fetched_at: new Date().toISOString(),
            data_quality: 'partial',
            complexity: bundle.complexity as GeruestbauData['complexity'],
            research_source: bundle.research_source as GeruestbauData['research_source'],
          } as GeruestbauData
        })

        // NEU 18.01.2026: Union-Polygon berechnen (Frontend als Single Source of Truth)
        const combined = combineBuildings(allBuildingData)
        if (combined) {
          console.log(`[Multi-Building] Union-Polygon erstellt: ${combined.building_count} Gebäude → ${combined.facades.length} äußere Fassaden`)

          // KOMBINIERTE Daten als Haupt-GeruestbauData verwenden
          // Das Union-Polygon enthält nur die äußeren Fassaden (Zwischenwände eliminiert!)
          const combinedData: GeruestbauData = {
            building: {
              egid: allBuildingData.map(b => b.building.egid).join('+'),  // z.B. "123+456+789"
              address: completeData.address,
              polygon: combined.polygon,
              center_e: combined.polygon.reduce((sum, p) => sum + p[0], 0) / combined.polygon.length,
              center_n: combined.polygon.reduce((sum, p) => sum + p[1], 0) / combined.polygon.length,
              perimeter_m: combined.total_perimeter_m,
              area_m2: combined.total_area_m2,
              name: `${combined.building_count} Gebäude kombiniert`,
              has_3d_layers: allBuildingData.some(b => b.building.has_3d_layers),
            },
            facades: combined.facades,  // NUR äußere Fassaden!
            walls: [],
            roofs: [],
            terrain: {
              height_m: (combined.min_terrain_m + combined.max_terrain_m) / 2,
              min_m: combined.min_terrain_m,
              max_m: combined.max_terrain_m,
              slope_m: combined.max_terrain_m - combined.min_terrain_m,
              slope_class: combined.slope_class,
              requires_level_compensation: combined.requires_level_compensation,
            },
            heights: {
              traufhoehe_m: combined.avg_traufhoehe_m,
              firsthoehe_m: combined.max_firsthoehe_m,
              gebaeudehoehe_m: combined.avg_traufhoehe_m,
              source: 'swissBUILDINGS3D',
            },
            zones: [],  // Kombinierte Gebäude haben keine separaten Zonen
            fetched_at: new Date().toISOString(),
            data_quality: 'complete',
            complexity: 'complex',
            research_source: 'auto',
          }
          setGeruestbauData(combinedData)
        } else {
          // Fallback: Erstes Gebäude verwenden wenn Union fehlschlägt
          console.warn('[Multi-Building] Union fehlgeschlagen, verwende erstes Gebäude als Fallback')
          setGeruestbauData(allBuildingData[0])
        }

        setLoadingStates((s) => ({ ...s, building3d: 'success', enrichment: 'success', research: 'success' }))
        setResearchStatus('done')
        return
      }

      // SINGLE-BUILDING: Stream komplett - GeruestbauData aus Bundle aufbauen
      // NEU 18.01.2026: Saubere GeruestbauData Struktur
      const bundle = completeData.bundle

      // Facades aus sides + terrain.facade_z_min/max erstellen
      const facades: GeruestbauFassade[] = (bundle.sides ?? []).map((side, index) => {
        const direction = side.direction ?? 'N'
        const terrainZMin = bundle.terrain?.facade_z_min?.[direction] ?? bundle.terrain?.reference_height_m ?? 0
        const terrainZMax = bundle.terrain?.facade_z_max?.[direction] ?? bundle.terrain?.reference_height_m ?? 0
        const wallZMax = bundle.roof_dach_min_m ?? terrainZMin + 8 // Fallback 8m Höhe
        const heightM = wallZMax - Math.min(terrainZMin, terrainZMax)

        return {
          index,
          direction,
          start_point: (side.start_point ?? [0, 0]) as [number, number],
          end_point: (side.end_point ?? [0, 0]) as [number, number],
          length_m: side.length_m ?? 0,
          azimuth_deg: side.azimuth_deg ?? 0,
          terrain_z_min: terrainZMin,
          terrain_z_max: terrainZMax,
          wall_z_max: wallZMax,
          height_m: heightM,
          slope_m: Math.abs(terrainZMax - terrainZMin),
          height_source: (bundle.terrain?.facade_heights_source as GeruestbauFassade['height_source']) ?? 'building_global',
          is_blocked: false,
        }
      })

      const newData: GeruestbauData = {
        building: {
          egid: completeData.egid ?? '',
          address: completeData.address,
          polygon: bundle.polygon ?? [],
          center_e: bundle.lv95_e ?? 0,
          center_n: bundle.lv95_n ?? 0,
          perimeter_m: bundle.perimeter_m ?? 0,
          area_m2: bundle.footprint_area_m2 ?? 0,
          name: bundle.building_name ?? undefined,
          has_3d_layers: bundle.has_3d_layers ?? false,
          roof_dach_min_m: bundle.roof_dach_min_m ?? undefined,
          roof_dach_max_m: bundle.roof_dach_max_m ?? undefined,
        },
        facades,
        walls: [],
        roofs: [],
        terrain: {
          height_m: bundle.terrain?.reference_height_m ?? 0,
          min_m: bundle.terrain?.min_height_m ?? bundle.terrain?.reference_height_m ?? 0,
          max_m: bundle.terrain?.max_height_m ?? bundle.terrain?.reference_height_m ?? 0,
          slope_m: bundle.terrain?.slope_m ?? 0,
          slope_class: (bundle.terrain?.slope_class as 'eben' | 'leicht' | 'mittel' | 'stark') ?? 'eben',
          requires_level_compensation: (bundle.terrain?.slope_m ?? 0) > 0.5,
        },
        zones: bundle.zones?.map(z => ({
          ...z,
          zone_type: z.zone_type as ZoneInfo['zone_type'],
          traufhoehe_m: z.traufhoehe_m ?? undefined,
          firsthoehe_m: z.firsthoehe_m ?? undefined,
          sonderkonstruktion: ['turm', 'kuppel'].includes(z.zone_type),
          confidence: 1.0,
        })) ?? [],
        fetched_at: new Date().toISOString(),
        data_quality: bundle.has_3d_layers ? 'complete' : 'partial',
        complexity: bundle.complexity as GeruestbauData['complexity'],
        research_source: (bundle.research_source as GeruestbauData['research_source']) ?? (bundle.zones && bundle.zones.length > 0 ? 'auto' : undefined),
      }
      setGeruestbauData(newData)
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
  // NEU 18.01.2026: SSE für alles (Single + Multi)
  const isLoading = isStreamLoading

  // ==========================================================================
  // Start Loading - NEU 18.01.2026: IMMER SSE verwenden (Single + Multi)
  // loadMultiAddress() wurde entfernt - Backend erkennt Multi automatisch
  // ==========================================================================
  const loadData = useCallback(() => {
    if (!data.address) return

    setError(null)
    setGeruestbauData(null)
    setBuildings([])
    setAddressErrors([])
    setResearchStatus('idle')
    setLoadingStates({ geocoding: 'loading', gwr: 'pending', building3d: 'pending', enrichment: 'pending', research: 'pending' })

    // Check if address contains a range (e.g., "2-10" or "1-9")
    const hasRange = /\d+\s*-\s*\d+/.test(data.address)
    setIsMultiAddress(hasRange)

    // NEU 18.01.2026: IMMER startStream() verwenden!
    // Backend erkennt automatisch Multi-Adresse und sendet {buildings: [...]}
    // loadMultiAddress() wird nicht mehr verwendet.
    startStream(data.address)
  }, [data.address, startStream])

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
              {loadingStates.research === 'success' && geruestbauData?.research_source && (
                <span className="text-xs">
                  {geruestbauData.research_source === 'known_buildings' && (
                    <span className="inline-flex items-center gap-1 text-emerald-600">
                      <Zap className="w-3 h-3" />
                      Bekanntes Gebäude
                    </span>
                  )}
                  {geruestbauData.research_source === 'claude_api' && (
                    <span className="inline-flex items-center gap-1 text-blue-600">
                      <Bot className="w-3 h-3" />
                      Claude analysiert
                    </span>
                  )}
                  {geruestbauData.research_source === 'cache' && (
                    <span className="inline-flex items-center gap-1 text-gray-600">
                      <Database className="w-3 h-3" />
                      Aus Cache
                    </span>
                  )}
                  {geruestbauData.research_source === 'auto' && (
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
            {/* FIX 22.01.2026: Use address+index as key - EGID may be duplicated for Reihenhäuser */}
            {buildings.map((building, index) => (
              <div
                key={`${building.address}_${index}`}
                className="flex items-center justify-between p-2 bg-white rounded border border-green-100"
              >
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4 text-green-600" />
                  <span className="font-medium">{building.address}</span>
                </div>
                {/* FIX 16.01.2026: traufhoehe_m entfernt - zeige nur EGID */}
                <div className="flex items-center gap-3 text-gray-500">
                  <span className="text-xs">EGID: {building.egid}</span>
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
      {!isMultiAddress && geruestbauData && <BuildingDataCard data={geruestbauData} />}

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
          onClick={() => onSubmit(geruestbauData, isMultiAddress ? buildings : undefined)}
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
