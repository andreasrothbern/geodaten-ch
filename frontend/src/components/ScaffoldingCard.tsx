import { useState } from 'react'
import type { ScaffoldingData, ScaffoldingSide } from '../types'
import { ServerSVG } from './BuildingVisualization/ServerSVG'

interface ScaffoldingCardProps {
  data: ScaffoldingData
  apiUrl: string
  onHeightChange?: (height: number) => void
  onFetchMeasuredHeight?: () => void
  fetchingHeight?: boolean
}

function isFromDatabase(source: string | undefined | null): boolean {
  return source?.startsWith('database:') ?? false
}

export function ScaffoldingCard({
  data,
  apiUrl,
  onHeightChange,
  onFetchMeasuredHeight,
  fetchingHeight = false
}: ScaffoldingCardProps) {
  const [showAllSides, setShowAllSides] = useState(false)
  const [manualHeight, setManualHeight] = useState<string>('')
  const [activeVizTab, setActiveVizTab] = useState<'cross-section' | 'elevation' | 'floor-plan'>('cross-section')

  const { dimensions, scaffolding, building, gwr_data, sides } = data

  // Check if measured height can be fetched (not already from database)
  const canFetchMeasuredHeight = !isFromDatabase(dimensions.height_source) && onFetchMeasuredHeight

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
        {data.viewer_3d_url && (
          <div className="bg-indigo-50 rounded-lg p-4 text-center">
            <p className="text-sm text-indigo-600 font-medium">3D Ansicht</p>
            <a
              href={data.viewer_3d_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block mt-2 px-3 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              🏠 3D Viewer
            </a>
          </div>
        )}
      </div>

      {/* Gebäude-Visualisierung - Server-generierte SVGs */}
      <div className="bg-white rounded-lg border shadow-sm">
        {/* Header with tabs */}
        <div className="flex items-center justify-between border-b px-4 py-2">
          <div className="flex gap-1">
            {[
              { id: 'cross-section' as const, label: 'Schnitt', icon: '📐' },
              { id: 'elevation' as const, label: 'Ansicht', icon: '🏛️' },
              { id: 'floor-plan' as const, label: 'Grundriss', icon: '📋' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveVizTab(tab.id)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  activeVizTab === tab.id
                    ? 'bg-red-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          {/* Download Button */}
          <a
            href={`${apiUrl}/api/v1/visualize/${activeVizTab}?address=${encodeURIComponent(data.address.matched)}&width=1000&height=700`}
            download={`${activeVizTab}_${data.address.matched.replace(/[^a-zA-Z0-9]/g, '_')}.svg`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors"
          >
            SVG
          </a>
        </div>

        {/* Visualization */}
        <div className="p-4 flex justify-center">
          <ServerSVG
            type={activeVizTab}
            address={data.address.matched}
            apiUrl={apiUrl}
            width={650}
            height={activeVizTab === 'floor-plan' ? 450 : 400}
          />
        </div>

        {/* NPK 114 Info */}
        <div className="border-t px-4 py-2 bg-blue-50 text-sm">
          <span className="font-medium text-blue-700">NPK 114: </span>
          <span className="text-blue-600">
            Ausmass = (Länge + 2×1.0m) × (Höhe + 1.0m)
          </span>
        </div>
      </div>

      {/* Höhenangaben - separate Spalten */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Geschätzte Höhe */}
        <div className="bg-amber-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-amber-600 font-medium">Höhe geschätzt</p>
              <p className="text-2xl font-bold text-amber-900">
                {dimensions.height_estimated_m
                  ? `${dimensions.height_estimated_m.toFixed(1)} m`
                  : '—'}
              </p>
              <p className="text-xs text-amber-600 mt-1">
                {dimensions.height_estimated_source === 'calculated_from_floors'
                  ? `Berechnet aus ${dimensions.floors} Geschossen`
                  : dimensions.height_estimated_source === 'default_by_category'
                  ? 'Standard (Gebäudekategorie)'
                  : 'Standard (10m)'}
              </p>
            </div>
          </div>
        </div>

        {/* Gemessene Höhe */}
        <div className={`rounded-lg p-4 ${dimensions.height_measured_m ? 'bg-emerald-50' : 'bg-gray-50'}`}>
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className={`text-sm font-medium ${dimensions.height_measured_m ? 'text-emerald-600' : 'text-gray-500'}`}>
                Höhe gemessen (swissBUILDINGS3D)
              </p>
              <p className={`text-2xl font-bold ${dimensions.height_measured_m ? 'text-emerald-900' : 'text-gray-400'}`}>
                {dimensions.height_measured_m
                  ? `${dimensions.height_measured_m.toFixed(1)} m`
                  : '—'}
              </p>
              {dimensions.height_measured_m ? (
                <div className="flex items-center gap-2 mt-1">
                  <p className="text-xs text-emerald-600">
                    Photogrammetrisch gemessen
                  </p>
                  {data.viewer_3d_url && (
                    <a
                      href={data.viewer_3d_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-emerald-700 hover:text-emerald-900 underline"
                    >
                      → 3D anzeigen
                    </a>
                  )}
                </div>
              ) : canFetchMeasuredHeight ? (
                <button
                  onClick={onFetchMeasuredHeight}
                  disabled={fetchingHeight}
                  className="mt-2 px-3 py-1 text-xs bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                >
                  {fetchingHeight ? (
                    <span className="flex items-center gap-1">
                      <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Lädt...
                    </span>
                  ) : (
                    '📡 Abrufen'
                  )}
                </button>
              ) : (
                <p className="text-xs text-gray-400 mt-1">Nicht verfügbar</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Detaillierte Höhen aus swissBUILDINGS3D */}
      {(dimensions.traufhoehe_m || dimensions.firsthoehe_m || dimensions.gebaeudehoehe_m) && (
        <div className="bg-gradient-to-r from-emerald-50 to-teal-50 rounded-lg p-4 border border-emerald-200">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg">📏</span>
            <h4 className="font-medium text-emerald-800">Gemessene Höhen (swissBUILDINGS3D)</h4>
            {data.viewer_3d_url && (
              <a
                href={data.viewer_3d_url}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto text-xs text-emerald-700 hover:text-emerald-900 underline"
              >
                → 3D Viewer
              </a>
            )}
          </div>
          <div className="grid grid-cols-3 gap-3">
            {/* Traufhöhe */}
            <div className="bg-white rounded-lg p-3 text-center border">
              <p className="text-xs text-gray-500 mb-1">Traufhöhe</p>
              <p className="text-xl font-bold text-emerald-700">
                {dimensions.traufhoehe_m ? `${dimensions.traufhoehe_m.toFixed(1)} m` : '—'}
              </p>
              <p className="text-xs text-gray-400">
                {dimensions.heights_estimated ? '~85% geschätzt' : 'Dachtraufe'}
              </p>
            </div>
            {/* Firsthöhe */}
            <div className="bg-white rounded-lg p-3 text-center border">
              <p className="text-xs text-gray-500 mb-1">Firsthöhe</p>
              <p className="text-xl font-bold text-teal-700">
                {dimensions.firsthoehe_m ? `${dimensions.firsthoehe_m.toFixed(1)} m` : '—'}
              </p>
              <p className="text-xs text-gray-400">
                {dimensions.heights_estimated ? '= Gebäudehöhe' : 'Dachfirst'}
              </p>
            </div>
            {/* Gebäudehöhe */}
            <div className="bg-white rounded-lg p-3 text-center border">
              <p className="text-xs text-gray-500 mb-1">Gebäudehöhe</p>
              <p className="text-xl font-bold text-cyan-700">
                {dimensions.gebaeudehoehe_m ? `${dimensions.gebaeudehoehe_m.toFixed(1)} m` : '—'}
              </p>
              <p className="text-xs text-gray-400">Gesamt</p>
            </div>
          </div>
          <p className="text-xs text-emerald-600 mt-2 text-center">
            {dimensions.heights_estimated
              ? 'Trauf-/Firsthöhe geschätzt aus Gesamthöhe'
              : 'Photogrammetrisch gemessen aus Luftbildern'}
            {data.height_refreshed && (
              <span className="ml-2 px-2 py-0.5 bg-emerald-200 text-emerald-800 rounded-full">
                ✓ Automatisch aktualisiert
              </span>
            )}
          </p>
        </div>
      )}

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
