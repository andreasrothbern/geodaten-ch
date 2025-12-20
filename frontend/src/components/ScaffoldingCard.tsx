import { useState } from 'react'
import type { ScaffoldingData, ScaffoldingSide } from '../types'

interface ScaffoldingCardProps {
  data: ScaffoldingData
  onHeightChange?: (height: number) => void
}

const HEIGHT_SOURCE_LABELS: Record<string, string> = {
  manual: 'Manuell eingegeben',
  calculated_from_floors: 'Berechnet aus Geschossen',
  default_by_category: 'Standard (Gebäudekategorie)',
  default_standard: 'Standard (10m)',
  unknown: 'Unbekannt',
}

// Funktion um Datenbank-Quellen zu erkennen
function getHeightSourceLabel(source: string | undefined | null): string {
  if (!source) return 'Unbekannt'
  if (source.startsWith('database:')) {
    const dbSource = source.replace('database:', '')
    return `swissBUILDINGS3D (${dbSource})`
  }
  return HEIGHT_SOURCE_LABELS[source] || source
}

function isFromDatabase(source: string | undefined | null): boolean {
  return source?.startsWith('database:') ?? false
}

export function ScaffoldingCard({ data, onHeightChange }: ScaffoldingCardProps) {
  const [showAllSides, setShowAllSides] = useState(false)
  const [manualHeight, setManualHeight] = useState<string>('')

  const { dimensions, scaffolding, building, gwr_data, sides } = data

  // Nur relevante Seiten anzeigen (> 1m)
  const relevantSides = sides.filter((s) => s.length_m > 1)
  const displaySides = showAllSides ? relevantSides : relevantSides.slice(0, 8)

  const handleHeightSubmit = () => {
    const height = parseFloat(manualHeight)
    if (height > 0 && onHeightChange) {
      onHeightChange(height)
    }
  }

  return (
    <div className="card space-y-6">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        <span>🏗️</span> Gerüstbau-Daten
      </h3>

      {/* Hauptkennzahlen */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-blue-50 rounded-lg p-4 text-center">
          <p className="text-sm text-blue-600 font-medium">Fassadenlänge</p>
          <p className="text-2xl font-bold text-blue-900">
            {dimensions.perimeter_m.toFixed(1)} m
          </p>
        </div>
        <div className={`rounded-lg p-4 text-center ${isFromDatabase(dimensions.height_source) ? 'bg-emerald-50' : 'bg-green-50'}`}>
          <p className={`text-sm font-medium ${isFromDatabase(dimensions.height_source) ? 'text-emerald-600' : 'text-green-600'}`}>
            {isFromDatabase(dimensions.height_source) ? 'Höhe (gemessen)' : 'Höhe (geschätzt)'}
          </p>
          <p className={`text-2xl font-bold ${isFromDatabase(dimensions.height_source) ? 'text-emerald-900' : 'text-green-900'}`}>
            {dimensions.estimated_height_m
              ? `${dimensions.estimated_height_m.toFixed(1)} m`
              : '—'}
          </p>
          <p className={`text-xs mt-1 ${isFromDatabase(dimensions.height_source) ? 'text-emerald-600' : 'text-green-600'}`}>
            {getHeightSourceLabel(dimensions.height_source)}
          </p>
        </div>
        <div className="bg-orange-50 rounded-lg p-4 text-center">
          <p className="text-sm text-orange-600 font-medium">Gerüstfläche</p>
          <p className="text-2xl font-bold text-orange-900">
            {scaffolding.estimated_scaffold_area_m2
              ? `${scaffolding.estimated_scaffold_area_m2.toFixed(0)} m²`
              : '—'}
          </p>
        </div>
        <div className="bg-purple-50 rounded-lg p-4 text-center">
          <p className="text-sm text-purple-600 font-medium">Grundfläche</p>
          <p className="text-2xl font-bold text-purple-900">
            {building.footprint_area_m2.toFixed(0)} m²
          </p>
        </div>
      </div>

      {/* Manuelle Höheneingabe */}
      <div className="bg-gray-50 rounded-lg p-4">
        <p className="text-sm font-medium text-gray-700 mb-2">
          Höhe manuell anpassen:
        </p>
        <div className="flex gap-2">
          <input
            type="number"
            step="0.5"
            min="1"
            max="200"
            placeholder="z.B. 12.5"
            value={manualHeight}
            onChange={(e) => setManualHeight(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
          />
          <span className="flex items-center text-gray-500">m</span>
          <button
            onClick={handleHeightSubmit}
            disabled={!manualHeight || parseFloat(manualHeight) <= 0}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            Aktualisieren
          </button>
        </div>
      </div>

      {/* Gebäudemasse */}
      <div>
        <h4 className="font-medium text-gray-700 mb-3">Gebäudemasse</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div className="bg-white border rounded-lg p-3">
            <p className="text-gray-500">Breite</p>
            <p className="font-semibold">{building.bounding_box.width_m.toFixed(1)} m</p>
          </div>
          <div className="bg-white border rounded-lg p-3">
            <p className="text-gray-500">Tiefe</p>
            <p className="font-semibold">{building.bounding_box.depth_m.toFixed(1)} m</p>
          </div>
          <div className="bg-white border rounded-lg p-3">
            <p className="text-gray-500">Geschosse</p>
            <p className="font-semibold">{dimensions.floors || '—'}</p>
          </div>
          <div className="bg-white border rounded-lg p-3">
            <p className="text-gray-500">EGID</p>
            <p className="font-semibold">{gwr_data.egid}</p>
          </div>
        </div>
      </div>

      {/* Fassadenseiten */}
      <div>
        <h4 className="font-medium text-gray-700 mb-3">
          Fassadenseiten ({scaffolding.main_sides_count} Hauptseiten, {scaffolding.number_of_sides} total)
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="px-3 py-2 text-left">Nr.</th>
                <th className="px-3 py-2 text-right">Länge</th>
                <th className="px-3 py-2 text-center">Richtung</th>
                <th className="px-3 py-2 text-right">Fläche*</th>
              </tr>
            </thead>
            <tbody>
              {displaySides.map((side: ScaffoldingSide) => (
                <tr key={side.index} className="border-b hover:bg-gray-50">
                  <td className="px-3 py-2">{side.index}</td>
                  <td className="px-3 py-2 text-right font-mono">
                    {side.length_m.toFixed(2)} m
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className="inline-block px-2 py-1 bg-gray-100 rounded text-xs">
                      {side.direction}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-gray-500">
                    {dimensions.estimated_height_m
                      ? `${(side.length_m * dimensions.estimated_height_m).toFixed(1)} m²`
                      : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {relevantSides.length > 8 && (
            <button
              onClick={() => setShowAllSides(!showAllSides)}
              className="mt-2 text-sm text-red-600 hover:underline"
            >
              {showAllSides
                ? 'Weniger anzeigen'
                : `Alle ${relevantSides.length} Seiten anzeigen`}
            </button>
          )}
        </div>
        <p className="text-xs text-gray-400 mt-2">
          * Geschätzte Fassadenfläche pro Seite (Länge × Höhe)
        </p>
      </div>

      {/* Export-Hinweis */}
      <div className="border-t pt-4 text-sm text-gray-500">
        <p>
          📐 Polygon mit {data.polygon.coordinates.length} Eckpunkten |{' '}
          Koordinatensystem: {data.polygon.coordinate_system}
        </p>
      </div>
    </div>
  )
}
