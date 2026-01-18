import {
  Building2,
  Ruler,
  Layers,
  CheckCircle2,
  Mountain,
  Box,
  Landmark,
  Zap,
  Bot,
  Database,
  Settings,
  Cuboid,  // NEU 12.01.2026 23:00 - Icon für 3D-Daten
} from 'lucide-react'
import type { GeruestbauData, GeruestbauFassade, ZoneInfo } from '../../types/project'

/**
 * Props für BuildingDataCard
 * NEU 18.01.2026: Verwendet GeruestbauData statt Geodata
 */
interface BuildingDataCardProps {
  data: GeruestbauData
}

// Research Source Badge - zeigt woher die Daten stammen
function ResearchSourceBadge({ source }: { source?: string }) {
  switch (source) {
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

// NEU 18.01.2026 - Höhen-Qualitäts-Badge (aus facades[] oder heights.source)
// Zeigt die Qualität der Höhendaten basierend auf der Quelle
// FIX 18.01.2026: Auch heights.source prüfen für Legacy/Multi-Building Projekte
function Data3DQualityBadge({
  has3DLayers,
  facades,
  heightsSource
}: {
  has3DLayers?: boolean
  facades?: GeruestbauFassade[]
  heightsSource?: string  // NEU: heights.source für Legacy-Projekte
}) {
  // Prüfe height_source der ersten Fassade
  const firstSource = facades?.[0]?.height_source

  // Stufe 1: Echte 3D-Layer (höchste Präzision ±0.1m)
  // - has3DLayers gesetzt ODER
  // - facade height_source = wall_layer ODER
  // - heights.source = swissBUILDINGS3D (Legacy)
  if (has3DLayers === true || firstSource === 'wall_layer' || heightsSource === 'swissBUILDINGS3D') {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
        title="Echte 3D-Daten aus swissBUILDINGS3D (±0.1m Genauigkeit)"
      >
        <Cuboid className="w-3 h-3" />
        3D-Daten
      </span>
    )
  }

  // Stufe 2: Terrain-Sampling (gute Präzision ±0.5m)
  if (firstSource === 'terrain_sampled') {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
        title="Höhen aus swissALTI3D Terrain-Modell (±0.5m Genauigkeit)"
      >
        <Mountain className="w-3 h-3" />
        Terrain
      </span>
    )
  }

  // Stufe 3: Global/Fallback (geschätzt)
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700"
      title="Höhen geschätzt aus GWR-Daten oder Heuristik"
    >
      <Cuboid className="w-3 h-3" />
      Geschätzt
    </span>
  )
}

// Position Label für Zonen
function getPositionLabel(position?: string) {
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

// NEU 18.01.2026 - Fassaden-Höhen Anzeige (aus facades[])
// Zeigt Fassaden-Höhen mit Hanglage-Erkennung
function FacadeHeightsGrid({ facades }: { facades?: GeruestbauFassade[] }) {
  if (!facades || facades.length === 0) return null

  // Sortiere nach Richtung
  const directionOrder = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
  const sortedFacades = [...facades].sort(
    (a, b) => directionOrder.indexOf(a.direction) - directionOrder.indexOf(b.direction)
  )

  // Quelle für Badge
  const source = sortedFacades[0]?.height_source || 'global'
  const sourceLabel = {
    'wall_layer': '3D-Layer',
    'terrain_sampled': 'Terrain',
    'global': 'Global',
    'building_global': 'Global'
  }[source] || 'Global'

  const sourceColor = {
    'wall_layer': 'text-green-600 bg-green-50',
    'terrain_sampled': 'text-blue-600 bg-blue-50',
    'global': 'text-gray-600 bg-gray-50',
    'building_global': 'text-gray-600 bg-gray-50'
  }[source] || 'text-gray-600 bg-gray-50'

  // Hanglage-Erkennung: Terrain-Differenz > 0.5m
  const terrainValues = sortedFacades.map(f => Math.min(f.terrain_z_min, f.terrain_z_max))
  const minTerrain = Math.min(...terrainValues)
  const maxTerrain = Math.max(...terrainValues)
  const terrainDiff = maxTerrain - minTerrain
  const hasSlope = terrainDiff > 0.5

  // Höchste Fassade finden
  const maxHeight = Math.max(...sortedFacades.map(f => f.height_m))

  return (
    <div className="col-span-2 mt-2 pt-2 border-t border-green-200">
      <div className="flex items-center gap-2 mb-2">
        <Mountain className="w-4 h-4 text-green-600" />
        <span className="text-green-700 font-medium">
          Fassaden-Höhen
        </span>
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${sourceColor}`}>
          {sourceLabel}
        </span>
      </div>
      <div className="grid grid-cols-4 gap-1 text-xs">
        {sortedFacades.map((facade) => {
          // Markiere höchste Fassade bei Hanglage
          const isMax = hasSlope && facade.height_m === maxHeight

          return (
            <div
              key={facade.index}
              className={`flex flex-col items-center p-1.5 bg-white rounded border ${
                isMax ? 'border-orange-300 bg-orange-50' : 'border-green-100'
              } ${facade.is_blocked ? 'opacity-50' : ''}`}
            >
              <span className={`font-medium ${isMax ? 'text-orange-700' : 'text-green-700'}`}>
                {facade.direction}
              </span>
              <span className={isMax ? 'text-orange-600' : 'text-gray-500'}>
                {facade.height_m.toFixed(2)}m
              </span>
              {facade.is_blocked && (
                <span className="text-[9px] text-red-500">blockiert</span>
              )}
            </div>
          )
        })}
      </div>

      {/* Hanglage-Hinweis */}
      {hasSlope && (
        <div className="mt-2 p-2 bg-orange-50 border border-orange-200 rounded text-xs">
          <div className="flex items-center gap-1.5 text-orange-700 font-medium">
            <span>Hanglage erkannt</span>
          </div>
          <div className="text-orange-600 mt-1">
            Terrain-Differenz: {terrainDiff.toFixed(2)}m
          </div>
          <div className="text-orange-700 mt-1 font-medium">
            Gerüst am Grund ausnivellieren erforderlich
          </div>
        </div>
      )}
    </div>
  )
}

// Zonen-Liste Komponente
function ZonesList({ zones }: { zones: ZoneInfo[] }) {
  if (!zones || zones.length <= 1) return null

  return (
    <div className="col-span-2 mt-2 pt-2 border-t border-green-200">
      <div className="flex items-center gap-2 mb-2">
        <Box className="w-4 h-4 text-green-600" />
        <span className="text-green-700 font-medium">
          {zones.length} Gebäudezonen erkannt
        </span>
      </div>
      <div className="space-y-1 text-xs">
        {zones.map((zone) => (
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
                {zone.firsthoehe_m?.toFixed(1) ||
                  zone.traufhoehe_m?.toFixed(1) ||
                  zone.gebaeudehoehe_m?.toFixed(1) ||
                  '–'}{' '}
                m
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
  )
}

/**
 * BuildingDataCard - Zeigt Gebäudedaten in einer grünen Karte an
 *
 * NEU 18.01.2026: Verwendet GeruestbauData statt Geodata
 *
 * Verwendung:
 * - GeodataStep.tsx: Nach erfolgreichem Laden der Gebäudedaten
 * - ProjectDetailPage.tsx: Anzeige der gespeicherten Gebäudedaten
 * - ConfiguratorPage.tsx: Projekt-Info Anzeige
 */
export default function BuildingDataCard({ data }: BuildingDataCardProps) {
  const { building, facades, terrain, zones, complexity, research_source, heights } = data

  // Berechne Traufhöhe: Prioritäts-Reihenfolge
  // 1. facades[] → minHeight (beste Quelle)
  // 2. heights.traufhoehe_m (bereits berechnet - Legacy/Multi-Building)
  // 3. building.roof_dach_min_m - terrain.min_m (Rohdaten)
  const calcTraufhoehe = (): string => {
    // 1. Aus facades[] (NEU 18.01.2026)
    if (facades && facades.length > 0) {
      const minHeight = Math.min(...facades.map(f => f.height_m))
      return minHeight.toFixed(1)
    }
    // 2. Aus heights (Legacy/Multi-Building Projekte) - FIX 18.01.2026
    if (heights?.traufhoehe_m && heights.traufhoehe_m > 0) {
      return heights.traufhoehe_m.toFixed(1)
    }
    // 3. Aus Rohdaten berechnen
    if (building.roof_dach_min_m && terrain?.min_m) {
      return (building.roof_dach_min_m - terrain.min_m).toFixed(1)
    }
    return '–'
  }

  // Berechne Firsthöhe: Prioritäts-Reihenfolge
  // 1. heights.firsthoehe_m (bereits berechnet - Legacy/Multi-Building)
  // 2. building.roof_dach_max_m - terrain.min_m (Rohdaten)
  // 3. facades[] maxHeight * 1.2 (Schätzung)
  const calcFirsthoehe = (): string => {
    // 1. Aus heights (Legacy/Multi-Building Projekte) - FIX 18.01.2026
    if (heights?.firsthoehe_m && heights.firsthoehe_m > 0) {
      return heights.firsthoehe_m.toFixed(1)
    }
    // 2. Aus Rohdaten berechnen
    if (building.roof_dach_max_m && terrain?.min_m) {
      return (building.roof_dach_max_m - terrain.min_m).toFixed(1)
    }
    // 3. Aus facades[] schätzen
    if (facades && facades.length > 0) {
      const maxHeight = Math.max(...facades.map(f => f.height_m))
      return (maxHeight * 1.2).toFixed(1) // Schätzung +20% für Dach
    }
    return '–'
  }

  return (
    <div className="card border-green-200 bg-green-50">
      {/* Header mit Gebäudename und Badges */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-medium text-green-800 flex items-center gap-2">
            {building.name ? (
              <>
                <Landmark className="w-5 h-5" />
                {building.name}
              </>
            ) : (
              <>
                <CheckCircle2 className="w-5 h-5" />
                Gebäudedaten
              </>
            )}
          </h3>
          {complexity === 'complex' && (
            <span className="text-xs text-green-600 mt-0.5">Komplexes Gebäude</span>
          )}
        </div>
        {/* Badges */}
        <div className="flex items-center gap-2">
          <Data3DQualityBadge has3DLayers={building.has_3d_layers} facades={facades} heightsSource={heights?.source} />
          <ResearchSourceBadge source={research_source} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        {/* EGID */}
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-green-600" />
          <div>
            <span className="text-green-700">EGID:</span>{' '}
            <strong>{building.egid}</strong>
          </div>
        </div>

        {/* Traufhöhe */}
        <div className="flex items-center gap-2">
          <Ruler className="w-4 h-4 text-green-600" />
          <div>
            <span className="text-green-700">Traufhöhe:</span>{' '}
            <strong>{calcTraufhoehe()} m</strong>
          </div>
        </div>

        {/* Firsthöhe */}
        <div className="flex items-center gap-2">
          <Ruler className="w-4 h-4 text-green-600" />
          <div>
            <span className="text-green-700">Firsthöhe:</span>{' '}
            <strong>{calcFirsthoehe()} m</strong>
          </div>
        </div>

        {/* Fläche */}
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-green-600" />
          <div>
            <span className="text-green-700">Fläche:</span>{' '}
            <strong>{building.area_m2.toFixed(0)} m²</strong>
          </div>
        </div>

        {/* Umfang */}
        <div className="flex items-center gap-2">
          <Ruler className="w-4 h-4 text-green-600" />
          <div>
            <span className="text-green-700">Umfang:</span>{' '}
            <strong>{building.perimeter_m.toFixed(1)} m</strong>
          </div>
        </div>

        {/* Geländehöhe */}
        {terrain && (
          <div className="flex items-center gap-2">
            <Mountain className="w-4 h-4 text-green-600" />
            <div>
              <span className="text-green-700">Geländehöhe:</span>{' '}
              <strong>{terrain.height_m.toFixed(1)} m ü.M.</strong>
            </div>
          </div>
        )}

        {/* Hanglage */}
        {terrain?.slope_class && (
          <div className="flex items-center gap-2">
            <Mountain className="w-4 h-4 text-green-600" />
            <div>
              <span className="text-green-700">Hanglage:</span>{' '}
              <strong>
                {terrain.slope_class}
                {terrain.slope_m !== undefined && ` (${terrain.slope_m.toFixed(1)}m)`}
              </strong>
            </div>
          </div>
        )}

        {/* Fassaden-Höhen Grid (aus facades[]) */}
        <FacadeHeightsGrid facades={facades} />

        {/* Zonen */}
        {zones && <ZonesList zones={zones} />}
      </div>
    </div>
  )
}
