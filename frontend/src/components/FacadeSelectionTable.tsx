/**
 * Facade Selection Table Component
 *
 * Displays a table of all building facades with checkboxes for selection.
 * Syncs with InteractiveFloorPlan component.
 */

import type { ScaffoldingSide } from '../types'

interface FacadeSelectionTableProps {
  sides: ScaffoldingSide[]
  selectedFacades: number[]
  onFacadeToggle: (index: number) => void
  onSelectAll: () => void
  onDeselectAll: () => void
  scaffoldHeight: number
  showArea?: boolean
}

export function FacadeSelectionTable({
  sides,
  selectedFacades,
  onFacadeToggle,
  onSelectAll,
  onDeselectAll,
  scaffoldHeight,
  showArea = true
}: FacadeSelectionTableProps) {
  // Filter to relevant sides (> 0.5m)
  const relevantSides = sides.filter(s => s.length_m > 0.5)

  // Calculate totals
  const selectedLength = selectedFacades.reduce((sum, idx) => {
    const side = sides.find(s => s.index === idx)
    return sum + (side?.length_m || 0)
  }, 0)
  const selectedArea = selectedLength * scaffoldHeight

  const totalLength = relevantSides.reduce((sum, s) => sum + s.length_m, 0)
  // totalArea available for future use: totalLength * scaffoldHeight

  return (
    <div className="space-y-3">
      {/* Header with selection controls */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="font-medium text-gray-700">
          Fassaden-Auswahl ({selectedFacades.length} / {relevantSides.length})
        </h4>
        <div className="flex gap-2">
          <button
            onClick={onSelectAll}
            className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
          >
            Alle
          </button>
          <button
            onClick={onDeselectAll}
            className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors"
          >
            Keine
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto border rounded-lg">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-100">
              <th className="px-3 py-2 text-left w-10">
                <input
                  type="checkbox"
                  checked={selectedFacades.length === relevantSides.length}
                  onChange={() => {
                    if (selectedFacades.length === relevantSides.length) {
                      onDeselectAll()
                    } else {
                      onSelectAll()
                    }
                  }}
                  className="rounded border-gray-300"
                />
              </th>
              <th className="px-3 py-2 text-left">Nr.</th>
              <th className="px-3 py-2 text-right">Lange</th>
              <th className="px-3 py-2 text-right">Hohe</th>
              <th className="px-3 py-2 text-center">Richtung</th>
              {showArea && <th className="px-3 py-2 text-right">Flache</th>}
            </tr>
          </thead>
          <tbody>
            {relevantSides.map((side) => {
              const isSelected = selectedFacades.includes(side.index)
              // Nutze facade_area_m2 von API (basiert auf traufhoehe_m), Fallback auf scaffoldHeight
              const area = side.facade_area_m2 ?? (side.length_m * scaffoldHeight)

              return (
                <tr
                  key={side.index}
                  className={`border-t cursor-pointer transition-colors ${
                    isSelected ? 'bg-red-50' : 'hover:bg-gray-50'
                  }`}
                  onClick={() => onFacadeToggle(side.index)}
                >
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onFacadeToggle(side.index)}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded border-gray-300"
                    />
                  </td>
                  <td className="px-3 py-2 font-medium">
                    <span className={isSelected ? 'text-red-700' : 'text-gray-700'}>
                      [{side.index + 1}]
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right font-mono">
                    {side.length_m.toFixed(2)} m
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-gray-500">
                    {side.traufhoehe_m ? `${side.traufhoehe_m.toFixed(1)} m` : '-'}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className="inline-block px-2 py-0.5 bg-gray-100 rounded text-xs">
                      {side.direction}
                    </span>
                  </td>
                  {showArea && (
                    <td className="px-3 py-2 text-right font-mono text-gray-500">
                      {area.toFixed(1)} m2
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
          {/* Summary row */}
          <tfoot>
            <tr className="bg-gray-50 border-t-2 font-medium">
              <td className="px-3 py-2" colSpan={2}>
                Ausgewahlt:
              </td>
              <td className="px-3 py-2 text-right font-mono text-red-600">
                {selectedLength.toFixed(1)} m
              </td>
              <td className="px-3 py-2 text-right font-mono text-gray-400 text-xs">
                (global)
              </td>
              <td className="px-3 py-2 text-center text-gray-500">
                von {totalLength.toFixed(1)} m
              </td>
              {showArea && (
                <td className="px-3 py-2 text-right font-mono text-red-600">
                  {selectedArea.toFixed(0)} m2
                </td>
              )}
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Info */}
      {selectedFacades.length === 0 && (
        <p className="text-sm text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
          Wahlen Sie mindestens eine Fassade aus, um das Gerust zu berechnen.
        </p>
      )}
    </div>
  )
}
