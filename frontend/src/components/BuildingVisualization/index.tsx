import { useState } from 'react'
import { FloorPlanSVG } from './FloorPlanSVG'
import { CrossSectionSVG } from './CrossSectionSVG'

type ViewType = 'floorplan' | 'section'

interface BuildingVisualizationProps {
  /** Polygon coordinates */
  polygon: [number, number][]
  /** Building width */
  widthM: number
  /** Building depth */
  depthM: number
  /** Eave height */
  eaveHeightM: number
  /** Ridge height (optional) */
  ridgeHeightM?: number
  /** Number of floors */
  floors?: number
  /** EGID */
  egid?: number
  /** Footprint area */
  areaM2?: number
  /** Height source description */
  heightSource?: string
  /** Roof type */
  roofType?: 'flat' | 'gable' | 'hip'
}

export function BuildingVisualization({
  polygon,
  widthM,
  depthM,
  eaveHeightM,
  ridgeHeightM,
  floors,
  egid,
  areaM2,
  heightSource,
  roofType = 'gable'
}: BuildingVisualizationProps) {
  const [activeView, setActiveView] = useState<ViewType>('floorplan')
  const [showScaffold, setShowScaffold] = useState(true)

  const tabs: { id: ViewType; label: string; icon: string }[] = [
    { id: 'floorplan', label: 'Grundriss', icon: '📐' },
    { id: 'section', label: 'Schnitt', icon: '📏' }
  ]

  return (
    <div className="bg-white rounded-lg border shadow-sm">
      {/* Header with tabs */}
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex gap-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveView(tab.id)}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                activeView === tab.id
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={showScaffold}
            onChange={(e) => setShowScaffold(e.target.checked)}
            className="rounded border-gray-300 text-red-600 focus:ring-red-500"
          />
          Gerüst anzeigen
        </label>
      </div>

      {/* Visualization */}
      <div className="p-4 flex justify-center">
        {activeView === 'floorplan' && (
          <FloorPlanSVG
            polygon={polygon}
            widthM={widthM}
            depthM={depthM}
            egid={egid}
            areaM2={areaM2}
            showScaffold={showScaffold}
          />
        )}

        {activeView === 'section' && (
          <CrossSectionSVG
            widthM={widthM}
            eaveHeightM={eaveHeightM}
            ridgeHeightM={ridgeHeightM}
            floors={floors}
            roofType={roofType}
            showScaffold={showScaffold}
            heightSource={heightSource}
          />
        )}
      </div>

      {/* NPK 114 Info */}
      <div className="border-t px-4 py-2 bg-blue-50 text-sm">
        <span className="font-medium text-blue-700">NPK 114: </span>
        <span className="text-blue-600">
          Ausmass = (Länge + 2×1.0m) × (Höhe + 1.0m)
        </span>
      </div>
    </div>
  )
}

// Re-export individual components
export { FloorPlanSVG } from './FloorPlanSVG'
export { CrossSectionSVG } from './CrossSectionSVG'
