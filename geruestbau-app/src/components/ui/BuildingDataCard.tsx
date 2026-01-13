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
import type { Geodata, ZoneInfo } from '../../types/project'

interface BuildingDataCardProps {
  geodata: Geodata
  egid?: string  // Optional override (z.B. aus Projekt-Daten)
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

// NEU 14.01.2026 17:45 - Höhen-Qualitäts-Badge (verbessert)
// Zeigt die Qualität der Höhendaten basierend auf der Quelle
function Data3DQualityBadge({
  has3DLayers,
  facadeHeightsSource
}: {
  has3DLayers?: boolean
  facadeHeightsSource?: string
}) {
  // Stufe 1: Echte 3D-Layer (höchste Präzision ±0.1m)
  if (has3DLayers === true || facadeHeightsSource === 'wall_layer') {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800"
        title="Echte 3D-Daten aus swissBUILDINGS3D (±0.1m Genauigkeit)"
      >
        <Cuboid className="w-3 h-3" />
        3D-Daten ✓
      </span>
    )
  }

  // Stufe 2: Terrain-Sampling (gute Präzision ±0.5m)
  if (facadeHeightsSource === 'terrain_sampled') {
    return (
      <span
        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
        title="Höhen aus swissALTI3D Terrain-Modell (±0.5m Genauigkeit)"
      >
        <Mountain className="w-3 h-3" />
        Terrain ✓
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

// NEU 14.01.2026 (T4) - Fassaden-Höhen Anzeige
// Zeigt Fassaden-Höhen aus Wall-Layer wenn verfügbar
function FacadeHeightsInfo({
  facadeZMin,
  facadeZMax,
  source
}: {
  facadeZMin?: Record<string, number>
  facadeZMax?: Record<string, number>
  source?: string
}) {
  if (!facadeZMin || Object.keys(facadeZMin).length === 0) return null

  const sourceLabel = {
    'wall_layer': '3D-Layer',
    'terrain_sampled': 'Terrain',
    'global': 'Global'
  }[source || 'global'] || 'Global'

  const sourceColor = {
    'wall_layer': 'text-green-600 bg-green-50',
    'terrain_sampled': 'text-blue-600 bg-blue-50',
    'global': 'text-gray-600 bg-gray-50'
  }[source || 'global'] || 'text-gray-600 bg-gray-50'

  // Sortiere Richtungen: N, NE, E, SE, S, SW, W, NW
  const directionOrder = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
  const sortedDirections = Object.keys(facadeZMin).sort(
    (a, b) => directionOrder.indexOf(a) - directionOrder.indexOf(b)
  )

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
        {sortedDirections.map((dir) => {
          const zMin = facadeZMin[dir]
          const zMax = facadeZMax?.[dir]
          const height = zMax && zMin ? (zMax - zMin).toFixed(1) : '–'

          return (
            <div
              key={dir}
              className="flex flex-col items-center p-1.5 bg-white rounded border border-green-100"
            >
              <span className="font-medium text-green-700">{dir}</span>
              <span className="text-gray-500">
                {height !== '–' ? `${height}m` : '–'}
              </span>
            </div>
          )
        })}
      </div>
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
 * Verwendung:
 * - GeodataStep.tsx: Nach erfolgreichem Laden der Gebäudedaten
 * - ProjectDetailPage.tsx: Anzeige der gespeicherten Gebäudedaten
 */
export default function BuildingDataCard({ geodata, egid }: BuildingDataCardProps) {
  const displayEgid = egid || geodata.egid

  return (
    <div className="card border-green-200 bg-green-50">
      {/* Header mit Gebäudename und Badges */}
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
                Gebäudedaten
              </>
            )}
          </h3>
          {geodata.complexity === 'complex' && (
            <span className="text-xs text-green-600 mt-0.5">Komplexes Gebäude</span>
          )}
        </div>
        {/* NEU 12.01.2026 23:00 - Badges nebeneinander */}
        <div className="flex items-center gap-2">
          <Data3DQualityBadge has3DLayers={geodata.has_3d_layers} facadeHeightsSource={geodata.facade_heights_source} />
          <ResearchSourceBadge source={geodata.research_source} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        {displayEgid && (
          <div className="flex items-center gap-2">
            <Building2 className="w-4 h-4 text-green-600" />
            <div>
              <span className="text-green-700">EGID:</span>{' '}
              <strong>{displayEgid}</strong>
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

        {geodata.terrain_height_m && (
          <div className="flex items-center gap-2">
            <Mountain className="w-4 h-4 text-green-600" />
            <div>
              <span className="text-green-700">Geländehöhe:</span>{' '}
              <strong>{geodata.terrain_height_m.toFixed(1)} m ü.M.</strong>
            </div>
          </div>
        )}

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

        {/* Fassaden-Höhen (NEU 14.01.2026 T4) */}
        <FacadeHeightsInfo
          facadeZMin={geodata.facade_z_min}
          facadeZMax={geodata.facade_z_max}
          source={geodata.facade_heights_source}
        />

        {/* Zonen */}
        {geodata.zones && <ZonesList zones={geodata.zones} />}
      </div>
    </div>
  )
}
