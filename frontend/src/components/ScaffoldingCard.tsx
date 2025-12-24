import { useState } from 'react'
import type { ScaffoldingData, BuildingContext } from '../types'
import { useUserPreferences, type WorkType, type ScaffoldType } from '../hooks/useUserPreferences'
import { InteractiveFloorPlan } from './InteractiveFloorPlan'
import { FacadeSelectionTable } from './FacadeSelectionTable'
import { LiftConfiguration } from './LiftConfiguration'
import { ZoneEditor } from './ZoneEditor'

interface LiftCalculation {
  lift_type: string
  height_m: number
  width_m: number
  levels: number
  area_m2: number
  npk_positions: { position: string; name: string; unit: string; quantity: number }[]
  weight_estimate_kg: number
  notes: string
}

export interface ScaffoldingConfig {
  selectedFacades: number[]
  workType: 'dacharbeiten' | 'fassadenarbeiten'
  scaffoldType: 'arbeitsgeruest' | 'schutzgeruest' | 'fanggeruest'
  scaffoldHeight: number
  totalLength: number
  totalArea: number
  lift?: LiftCalculation | null
}

interface ScaffoldingCardProps {
  data: ScaffoldingData
  apiUrl: string
  onCalculate?: (config: ScaffoldingConfig) => void
  // Lifted state from App.tsx for persistence across tab switches
  selectedFacades: number[]
  onFacadeToggle: (index: number) => void
  onSelectAll: () => void
  onDeselectAll: () => void
  // Polygon simplification control
  simplifyEpsilon: number | null
  onEpsilonChange: (epsilon: number | null) => void
}

export function ScaffoldingCard({
  data,
  apiUrl,
  onCalculate,
  selectedFacades,
  onFacadeToggle,
  onSelectAll,
  onDeselectAll,
  simplifyEpsilon,
  onEpsilonChange
}: ScaffoldingCardProps) {
  // Work type and scaffold type configuration
  const { preferences } = useUserPreferences()
  const [workType, setWorkType] = useState<WorkType>(preferences.defaultWorkType)
  const [scaffoldType, setScaffoldType] = useState<ScaffoldType>(preferences.defaultScaffoldType)
  const [liftEnabled, setLiftEnabled] = useState(false)
  const [liftCalculation, setLiftCalculation] = useState<LiftCalculation | null>(null)
  const [professionalMode, setProfessionalMode] = useState(false)
  const [buildingContext, setBuildingContext] = useState<BuildingContext | null>(null)
  const [showZoneEditor, setShowZoneEditor] = useState(false)

  const { dimensions, building, gwr_data, sides } = data

  // Calculate scaffold height based on work type
  const scaffoldHeight = workType === 'dacharbeiten'
    ? (dimensions.firsthoehe_m || dimensions.estimated_height_m || 0) + 1.0
    : (dimensions.traufhoehe_m || dimensions.estimated_height_m || 0)

  // Calculate perimeter and recommended epsilon
  const perimeter = sides.reduce((sum, s) => sum + s.length_m, 0)
  const recommendedEpsilon = perimeter > 200 ? 1.5 : perimeter > 50 ? 0.8 : 0.3
  const epsilonLabel = perimeter > 200 ? 'Grossprojekt' : perimeter > 50 ? 'MFH' : 'EFH'

  return (
    <div className="card space-y-6">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        Gerüstbau-Konfiguration
      </h3>

      {/* Fassaden-Auswahl mit interaktivem Grundriss */}
      <div className="space-y-4">
        <h4 className="font-medium text-gray-700">
          Fassaden-Auswahl ({selectedFacades.length} von {sides.filter(s => s.length_m > 0.5).length} ausgewählt)
        </h4>

        {/* Interactive Floor Plan */}
        <div className="border rounded-lg p-4 bg-white">
          <div className="flex items-center justify-between mb-3">
            <h5 className="text-sm font-medium text-gray-600">Grundriss - Klicken zum Auswählen</h5>
            <label className="flex items-center gap-2 cursor-pointer">
              <span className="text-xs text-gray-500">Professional</span>
              <div className="relative">
                <input
                  type="checkbox"
                  checked={professionalMode}
                  onChange={(e) => setProfessionalMode(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-red-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-red-600"></div>
              </div>
            </label>
          </div>
          <InteractiveFloorPlan
            address={data.address?.matched || ''}
            apiUrl={apiUrl}
            sides={sides}
            polygonCoordinates={data.polygon?.coordinates || []}
            selectedFacades={selectedFacades}
            onFacadeToggle={onFacadeToggle}
            onSelectAll={onSelectAll}
            onDeselectAll={onDeselectAll}
            height={280}
            eaveHeightM={dimensions.traufhoehe_m || dimensions.estimated_height_m}
            floors={dimensions.floors || gwr_data?.floors}
            areaM2={building?.footprint_area_m2}
            professional={professionalMode}
            zones={buildingContext?.zones}
            zugaenge={buildingContext?.zugaenge}
          />

          {/* Polygon Simplification Slider */}
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-600">Polygon-Vereinfachung</span>
              <span className="text-xs text-gray-500">
                Umfang: {perimeter.toFixed(0)}m ({epsilonLabel})
              </span>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="0.1"
                max="3.0"
                step="0.1"
                value={simplifyEpsilon ?? recommendedEpsilon}
                onChange={(e) => onEpsilonChange(parseFloat(e.target.value))}
                className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-red-600"
              />
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono font-medium text-gray-700 w-12 text-right">
                  {(simplifyEpsilon ?? recommendedEpsilon).toFixed(1)}m
                </span>
                {simplifyEpsilon !== null && (
                  <button
                    onClick={() => onEpsilonChange(null)}
                    className="text-xs px-2 py-1 bg-gray-200 hover:bg-gray-300 rounded text-gray-600"
                    title="Auto-Wert verwenden"
                  >
                    Auto
                  </button>
                )}
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              {simplifyEpsilon === null
                ? `Auto: ${recommendedEpsilon.toFixed(1)}m (${epsilonLabel})`
                : `Manuell gesetzt (Auto waere ${recommendedEpsilon.toFixed(1)}m)`}
              {' '}- Douglas-Peucker Toleranz
            </p>
          </div>
        </div>

        {/* Facade Selection Table */}
        <FacadeSelectionTable
          sides={sides}
          selectedFacades={selectedFacades}
          onFacadeToggle={onFacadeToggle}
          onSelectAll={onSelectAll}
          onDeselectAll={onDeselectAll}
          scaffoldHeight={scaffoldHeight}
          showArea={false}
        />

        {/* Selected Facade Summary */}
        {selectedFacades.length > 0 && (
          <div className="bg-green-50 rounded-lg p-4">
            <h5 className="font-medium text-green-800 mb-2">Ausgewählte Fassaden</h5>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div>
                <p className="text-green-600">Anzahl</p>
                <p className="font-bold text-green-900">{selectedFacades.length} Fassaden</p>
              </div>
              <div>
                <p className="text-green-600">Gesamtlänge</p>
                <p className="font-bold text-green-900">
                  {selectedFacades.reduce((sum, idx) => {
                    const side = sides.find(s => s.index === idx)
                    return sum + (side?.length_m || 0)
                  }, 0).toFixed(1)} m
                </p>
              </div>
              <div>
                <p className="text-green-600">Gerüsthöhe</p>
                <p className="font-bold text-green-900">{scaffoldHeight.toFixed(1)} m</p>
              </div>
              <div>
                <p className="text-green-600">Gerüstfläche</p>
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

      {/* Arbeitstyp und Gerustart Konfiguration */}
      <div className="bg-blue-50 rounded-lg p-4 space-y-4">
        <h4 className="font-medium text-blue-900">Arbeitstyp & Gerüstart</h4>

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
              ? 'Gerüst bis +1m über First (SUVA Vorschrift) - für Dachsanierung, Ziegel, Spengler'
              : 'Gerüst bis Traufhöhe - für Malen, Verputzen, Fassadendämmung'}
          </p>
        </div>

        {/* Gerustart */}
        <div>
          <p className="text-sm text-blue-700 mb-2">Gerüstart:</p>
          <select
            value={scaffoldType}
            onChange={(e) => setScaffoldType(e.target.value as ScaffoldType)}
            className="w-full md:w-auto px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="arbeitsgeruest">Arbeitsgerüst (Standard)</option>
            <option value="schutzgeruest">Schutzgerüst (Absturzsicherung)</option>
            <option value="fanggeruest">Fanggerüst (Material-/Personenauffang)</option>
          </select>
          <p className="text-xs text-blue-600 mt-2">
            {scaffoldType === 'arbeitsgeruest' && 'Für Arbeiten an der Fassade - Beläge, Leitern, Aufgänge (NPK 114.1xx)'}
            {scaffoldType === 'schutzgeruest' && 'Absturzsicherung bei Dacharbeiten - Fanglagen, Seitenschutz (NPK 114.2xx)'}
            {scaffoldType === 'fanggeruest' && 'Auffangen von herabfallenden Materialien oder Personen (NPK 114.3xx)'}
          </p>
        </div>

        {/* Berechnete Höhe anzeigen */}
        <div className="pt-3 border-t border-blue-200">
          <div className="flex items-center justify-between">
            <span className="text-sm text-blue-700">Berechnete Gerüsthöhe:</span>
            <span className="font-bold text-blue-900">
              {workType === 'dacharbeiten'
                ? `${((dimensions.firsthoehe_m || dimensions.estimated_height_m || 0) + 1.0).toFixed(1)} m`
                : `${(dimensions.traufhoehe_m || dimensions.estimated_height_m || 0).toFixed(1)} m`}
            </span>
          </div>
          <p className="text-xs text-blue-500 mt-1">
            {workType === 'dacharbeiten'
              ? `Firsthöhe ${(dimensions.firsthoehe_m || dimensions.estimated_height_m || 0).toFixed(1)}m + 1.0m SUVA`
              : `Traufhöhe (Unterdach)`}
          </p>
        </div>
      </div>

      {/* Gebäude-Zonen Editor */}
      {gwr_data?.egid && (
        <div className="space-y-2">
          <button
            onClick={() => setShowZoneEditor(!showZoneEditor)}
            className="flex items-center gap-2 text-sm text-amber-700 hover:text-amber-900"
          >
            <span>{showZoneEditor ? '▼' : '▶'}</span>
            <span>🏗️ Gebäude-Zonen {buildingContext ? `(${buildingContext.zones.length})` : ''}</span>
            {buildingContext?.complexity === 'complex' && (
              <span className="text-xs bg-amber-200 px-1.5 py-0.5 rounded">komplex</span>
            )}
          </button>
          {showZoneEditor && (
            <ZoneEditor
              egid={gwr_data.egid}
              onContextChange={setBuildingContext}
            />
          )}
        </div>
      )}

      {/* Gerüstlift Konfiguration */}
      <LiftConfiguration
        apiUrl={apiUrl}
        scaffoldHeight={scaffoldHeight}
        enabled={liftEnabled}
        onToggle={setLiftEnabled}
        onLiftCalculated={setLiftCalculation}
      />

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
                totalArea: totalLength * scaffoldHeight,
                lift: liftEnabled ? liftCalculation : null
              })
            }}
            className="w-full py-3 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center gap-2"
          >
            <span>Ausmass berechnen</span>
            <span>-&gt;</span>
          </button>
          <p className="text-xs text-gray-500 mt-2 text-center">
            NPK 114 Berechnung für {selectedFacades.length} Fassaden ({scaffoldHeight.toFixed(1)}m Höhe)
            {liftEnabled && liftCalculation && ` + Lift (${liftCalculation.area_m2.toFixed(1)} m²)`}
          </p>
        </div>
      )}
    </div>
  )
}
