import { useState, useEffect, useCallback } from 'react'
import type { ScaffoldingData } from '../types'
import { ServerSVG, preloadAllSvgs } from './BuildingVisualization/ServerSVG'
import { useUserPreferences, type WorkType, type ScaffoldType } from '../hooks/useUserPreferences'
import { InteractiveFloorPlan } from './InteractiveFloorPlan'
import { FacadeSelectionTable } from './FacadeSelectionTable'

export interface ScaffoldingConfig {
  selectedFacades: number[]
  workType: 'dacharbeiten' | 'fassadenarbeiten'
  scaffoldType: 'arbeitsgeruest' | 'schutzgeruest' | 'fanggeruest'
  scaffoldHeight: number
  totalLength: number
  totalArea: number
}

interface ScaffoldingCardProps {
  data: ScaffoldingData
  apiUrl: string
  onCalculate?: (config: ScaffoldingConfig) => void
}

export function ScaffoldingCard({
  data,
  apiUrl,
  onCalculate
}: ScaffoldingCardProps) {
  const [activeVizTab, setActiveVizTab] = useState<'cross-section' | 'elevation' | 'floor-plan'>('cross-section')

  // Work type and scaffold type configuration
  const { preferences } = useUserPreferences()
  const [workType, setWorkType] = useState<WorkType>(preferences.defaultWorkType)
  const [scaffoldType, setScaffoldType] = useState<ScaffoldType>(preferences.defaultScaffoldType)

  // Facade selection state - initially all facades selected
  const [selectedFacades, setSelectedFacades] = useState<number[]>([])

  const { dimensions, scaffolding, building, gwr_data, sides } = data

  // Initialize selected facades when sides data is loaded
  useEffect(() => {
    if (sides && sides.length > 0 && selectedFacades.length === 0) {
      // Select all facades by default
      setSelectedFacades(sides.filter(s => s.length_m > 0.5).map(s => s.index))
    }
  }, [sides])

  // Calculate scaffold height based on work type
  const scaffoldHeight = workType === 'dacharbeiten'
    ? (dimensions.firsthoehe_m || dimensions.estimated_height_m || 0) + 1.0
    : (dimensions.traufhoehe_m || dimensions.estimated_height_m || 0)

  // Facade selection handlers
  const handleFacadeToggle = useCallback((index: number) => {
    setSelectedFacades(prev =>
      prev.includes(index)
        ? prev.filter(i => i !== index)
        : [...prev, index]
    )
  }, [])

  const handleSelectAllFacades = useCallback(() => {
    setSelectedFacades(sides.filter(s => s.length_m > 0.5).map(s => s.index))
  }, [sides])

  const handleDeselectAllFacades = useCallback(() => {
    setSelectedFacades([])
  }, [])

  // Preload all SVG visualizations when component mounts
  useEffect(() => {
    if (data.address?.matched && apiUrl) {
      preloadAllSvgs(data.address.matched, apiUrl)
    }
  }, [data.address?.matched, apiUrl])

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

      {/* Arbeitstyp und Gerustart Konfiguration */}
      <div className="bg-blue-50 rounded-lg p-4 space-y-4">
        <h4 className="font-medium text-blue-900">Gerustkonfiguration</h4>

        {/* Arbeitstyp */}
        <div>
          <p className="text-sm text-blue-700 mb-2">Arbeitstyp:</p>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setWorkType('dacharbeiten')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
                workType === 'dacharbeiten'
                  ? 'bg-red-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              <span>&#127968;</span> Dacharbeiten
            </button>
            <button
              onClick={() => setWorkType('fassadenarbeiten')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 ${
                workType === 'fassadenarbeiten'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              <span>&#127912;</span> Fassadenarbeiten
            </button>
          </div>
          <p className="text-xs text-blue-600 mt-2">
            {workType === 'dacharbeiten'
              ? 'Gerust bis +1m uber First (SUVA Vorschrift) - fur Dachsanierung, Ziegel, Spengler'
              : 'Gerust bis Traufhohe - fur Malen, Verputzen, Fassadendammung'}
          </p>
        </div>

        {/* Gerustart */}
        <div>
          <p className="text-sm text-blue-700 mb-2">Gerustart:</p>
          <select
            value={scaffoldType}
            onChange={(e) => setScaffoldType(e.target.value as ScaffoldType)}
            className="w-full md:w-auto px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="arbeitsgeruest">Arbeitsgerust (Standard)</option>
            <option value="schutzgeruest">Schutzgerust (Absturzsicherung)</option>
            <option value="fanggeruest">Fanggerust (Material-/Personenauffang)</option>
          </select>
          <p className="text-xs text-blue-600 mt-2">
            {scaffoldType === 'arbeitsgeruest' && 'Fur Arbeiten an der Fassade - Belagen, Leitern, Aufgange (NPK 114.1xx)'}
            {scaffoldType === 'schutzgeruest' && 'Absturzsicherung bei Dacharbeiten - Fanglagen, Seitenschutz (NPK 114.2xx)'}
            {scaffoldType === 'fanggeruest' && 'Auffangen von herabfallenden Materialien oder Personen (NPK 114.3xx)'}
          </p>
        </div>

        {/* Berechnete Hohe anzeigen */}
        <div className="pt-3 border-t border-blue-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-blue-700">Berechnete Gerusthöhe:</span>
            <span className="font-bold text-blue-900">
              {workType === 'dacharbeiten'
                ? `${((dimensions.firsthoehe_m || dimensions.estimated_height_m || 0) + 1.0).toFixed(1)} m`
                : `${(dimensions.traufhoehe_m || dimensions.estimated_height_m || 0).toFixed(1)} m`}
            </span>
          </div>
          <p className="text-xs text-blue-500 mt-1">
            {workType === 'dacharbeiten'
              ? `Firsthohe ${(dimensions.firsthoehe_m || dimensions.estimated_height_m || 0).toFixed(1)}m + 1.0m SUVA`
              : `Traufhohe (Unterdach)`}
          </p>
        </div>
      </div>

      {/* Fassaden-Auswahl mit interaktivem Grundriss */}
      <div className="space-y-4">
        <h4 className="font-medium text-gray-700">
          Fassaden-Auswahl ({selectedFacades.length} von {sides.filter(s => s.length_m > 0.5).length} ausgewahlt)
        </h4>

        {/* Interactive Floor Plan */}
        <div className="border rounded-lg p-4 bg-white">
          <h5 className="text-sm font-medium text-gray-600 mb-3">Grundriss - Klicken zum Auswahlen</h5>
          <InteractiveFloorPlan
            address={data.address?.matched || ''}
            apiUrl={apiUrl}
            sides={sides}
            polygonCoordinates={data.polygon?.coordinates || []}
            selectedFacades={selectedFacades}
            onFacadeToggle={handleFacadeToggle}
            onSelectAll={handleSelectAllFacades}
            onDeselectAll={handleDeselectAllFacades}
            height={280}
            eaveHeightM={dimensions.traufhoehe_m || dimensions.estimated_height_m}
            floors={dimensions.floors || gwr_data?.floors}
            areaM2={building?.footprint_area_m2}
          />
        </div>

        {/* Facade Selection Table */}
        <FacadeSelectionTable
          sides={sides}
          selectedFacades={selectedFacades}
          onFacadeToggle={handleFacadeToggle}
          onSelectAll={handleSelectAllFacades}
          onDeselectAll={handleDeselectAllFacades}
          scaffoldHeight={scaffoldHeight}
          showArea={false}
        />

        {/* Selected Facade Summary */}
        {selectedFacades.length > 0 && (
          <div className="bg-green-50 rounded-lg p-4">
            <h5 className="font-medium text-green-800 mb-2">Ausgewahlte Fassaden</h5>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div>
                <p className="text-green-600">Anzahl</p>
                <p className="font-bold text-green-900">{selectedFacades.length} Fassaden</p>
              </div>
              <div>
                <p className="text-green-600">Gesamtlange</p>
                <p className="font-bold text-green-900">
                  {selectedFacades.reduce((sum, idx) => {
                    const side = sides.find(s => s.index === idx)
                    return sum + (side?.length_m || 0)
                  }, 0).toFixed(1)} m
                </p>
              </div>
              <div>
                <p className="text-green-600">Gerusthohe</p>
                <p className="font-bold text-green-900">{scaffoldHeight.toFixed(1)} m</p>
              </div>
              <div>
                <p className="text-green-600">Gerustflache</p>
                <p className="font-bold text-green-900">
                  {(selectedFacades.reduce((sum, idx) => {
                    const side = sides.find(s => s.index === idx)
                    return sum + (side?.length_m || 0)
                  }, 0) * scaffoldHeight).toFixed(0)} m2
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Berechnung starten */}
      {selectedFacades.length > 0 && onCalculate && (
        <div className="border-t pt-4">
          <button
            onClick={() => {
              const totalLength = selectedFacades.reduce((sum, idx) => {
                const side = sides.find(s => s.index === idx)
                return sum + (side?.length_m || 0)
              }, 0)
              onCalculate({
                selectedFacades,
                workType,
                scaffoldType,
                scaffoldHeight,
                totalLength,
                totalArea: totalLength * scaffoldHeight
              })
            }}
            className="w-full py-3 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
          >
            <span>Ausmass berechnen</span>
            <span>→</span>
          </button>
          <p className="text-xs text-gray-500 mt-2 text-center">
            NPK 114 Berechnung fur {selectedFacades.length} Fassaden ({scaffoldHeight.toFixed(1)}m Hohe)
          </p>
        </div>
      )}

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
