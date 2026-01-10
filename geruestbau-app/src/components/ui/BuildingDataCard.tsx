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
                Gebäudedaten
              </>
            )}
          </h3>
          {geodata.complexity === 'complex' && (
            <span className="text-xs text-green-600 mt-0.5">Komplexes Gebäude</span>
          )}
        </div>
        <ResearchSourceBadge source={geodata.research_source} />
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

        {/* Zonen */}
        {geodata.zones && <ZonesList zones={geodata.zones} />}
      </div>
    </div>
  )
}
