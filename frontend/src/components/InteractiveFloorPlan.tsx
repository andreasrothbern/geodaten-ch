/**
 * Interactive Floor Plan Component
 *
 * Displays the building floor plan SVG with clickable facade segments.
 * Allows users to select/deselect individual facades for scaffolding calculation.
 */

import { useState, useEffect, useRef } from 'react'
import type { ScaffoldingSide } from '../types'

interface InteractiveFloorPlanProps {
  address: string
  apiUrl: string
  sides: ScaffoldingSide[]
  polygonCoordinates: number[][]  // Polygon-Koordinaten für SVG-Generierung
  selectedFacades: number[]
  onFacadeToggle: (index: number) => void
  onSelectAll?: () => void
  onDeselectAll?: () => void
  height?: number
  // Gebäudedaten für NPK-Anzeige im SVG
  eaveHeightM?: number | null
  floors?: number | null
  areaM2?: number | null
  // Professional Mode: hochwertige Zeichnung mit Titelblock, Schraffur, Massstab
  professional?: boolean
  projectName?: string
  authorName?: string
}

export function InteractiveFloorPlan({
  address,
  apiUrl,
  sides,
  polygonCoordinates,
  selectedFacades,
  onFacadeToggle,
  onSelectAll,
  onDeselectAll,
  height = 300,
  eaveHeightM,
  floors,
  areaM2,
  professional = false,
  projectName,
  authorName
}: InteractiveFloorPlanProps) {
  const [svgContent, setSvgContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const containerRef = useRef<HTMLDivElement>(null)

  // Fetch SVG from server using POST with sides/polygon data
  useEffect(() => {
    const fetchSvg = async () => {
      setLoading(true)
      setError(null)
      try {
        // Sende die gleichen Daten, die auch die Tabelle verwendet
        // compact: true für grössere Darstellung (ohne Info-Boxen)
        const response = await fetch(`${apiUrl}/api/v1/visualize/floor-plan`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            address,
            sides: sides,
            polygon_coordinates: polygonCoordinates,
            width: professional ? 1200 : 600,  // Professional: 1200px Breite
            height: professional ? 900 : height,  // Professional: 900px Höhe
            eave_height_m: eaveHeightM,
            floors: floors,
            area_m2: areaM2,
            compact: !professional,  // Compact mode nur wenn nicht professional
            professional: professional,
            project_name: projectName || address,
            author_name: authorName || 'Lawil Gerüstbau AG'
          })
        })
        if (!response.ok) {
          throw new Error('SVG konnte nicht geladen werden')
        }
        const svg = await response.text()
        setSvgContent(svg)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fehler beim Laden')
      } finally {
        setLoading(false)
      }
    }

    if (address && sides.length > 0 && polygonCoordinates.length > 0) {
      fetchSvg()
    }
  }, [address, apiUrl, sides, polygonCoordinates, height, eaveHeightM, floors, areaM2, professional, projectName, authorName])

  // Add click handlers to facade segments after SVG is loaded (only once)
  useEffect(() => {
    if (!containerRef.current || !svgContent) return

    const container = containerRef.current
    const segments = container.querySelectorAll('.facade-segment')
    const handlers: Array<{ element: Element; handler: () => void }> = []

    segments.forEach((segment) => {
      const indexAttr = segment.getAttribute('data-facade-index')
      if (indexAttr !== null) {
        const index = parseInt(indexAttr, 10)

        // Add click handler
        const handleClick = () => {
          console.log('Facade clicked:', index)
          onFacadeToggle(index)
        }

        segment.addEventListener('click', handleClick)
        handlers.push({ element: segment, handler: handleClick })
      }
    })

    // Cleanup - remove all listeners when effect re-runs or unmounts
    return () => {
      handlers.forEach(({ element, handler }) => {
        element.removeEventListener('click', handler)
      })
    }
  }, [svgContent, onFacadeToggle]) // Note: removed selectedFacades from dependencies

  // Update visual selection state separately (without re-attaching listeners)
  useEffect(() => {
    if (!containerRef.current || !svgContent) return

    const container = containerRef.current
    const segments = container.querySelectorAll('.facade-segment')

    segments.forEach((segment) => {
      const indexAttr = segment.getAttribute('data-facade-index')
      if (indexAttr !== null) {
        const index = parseInt(indexAttr, 10)

        // Update selected state
        if (selectedFacades.includes(index)) {
          segment.classList.add('selected')
        } else {
          segment.classList.remove('selected')
        }
      }
    })
  }, [svgContent, selectedFacades])

  // Zoom handlers
  const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.25, 3))
  const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.25, 0.5))
  const handleZoomReset = () => setZoom(1)

  // Calculate summary stats
  const selectedCount = selectedFacades.length
  const totalCount = sides.length
  const selectedLength = selectedFacades.reduce((sum, idx) => {
    const side = sides.find(s => s.index === idx)
    return sum + (side?.length_m || 0)
  }, 0)
  const totalLength = sides.reduce((sum, s) => sum + s.length_m, 0)

  if (loading) {
    return (
      <div className="bg-gray-50 rounded-lg p-8 text-center">
        <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
        <p className="text-gray-500">Grundriss wird geladen...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 rounded-lg p-4 text-center text-red-600">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-2">
          {onSelectAll && (
            <button
              onClick={onSelectAll}
              className="px-3 py-1.5 text-sm bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors"
            >
              Alle auswählen
            </button>
          )}
          {onDeselectAll && (
            <button
              onClick={onDeselectAll}
              className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Keine auswählen
            </button>
          )}
        </div>
        <div className="flex items-center gap-4">
          {/* Zoom Controls */}
          <div className="flex items-center gap-1 border rounded-lg p-1 bg-gray-50">
            <button
              onClick={handleZoomOut}
              disabled={zoom <= 0.5}
              className="w-7 h-7 flex items-center justify-center text-gray-600 hover:bg-gray-200 rounded disabled:opacity-30 disabled:cursor-not-allowed"
              title="Verkleinern"
            >
              -
            </button>
            <button
              onClick={handleZoomReset}
              className="px-2 h-7 text-xs text-gray-600 hover:bg-gray-200 rounded font-mono"
              title="Zurücksetzen"
            >
              {Math.round(zoom * 100)}%
            </button>
            <button
              onClick={handleZoomIn}
              disabled={zoom >= 3}
              className="w-7 h-7 flex items-center justify-center text-gray-600 hover:bg-gray-200 rounded disabled:opacity-30 disabled:cursor-not-allowed"
              title="Vergrössern"
            >
              +
            </button>
          </div>
          <div className="text-sm text-gray-600">
            <span className="font-medium">{selectedCount}</span> von {totalCount} Fassaden ausgewählt
            ({selectedLength.toFixed(1)}m von {totalLength.toFixed(1)}m)
          </div>
        </div>
      </div>

      {/* Professional Mode Hinweis */}
      {professional && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-sm text-amber-800">
          Professional Mode aktiv - 1200×900px mit Titelblock, Schraffur und Massstab
        </div>
      )}

      {/* SVG Container with zoom */}
      <div
        className="bg-white border rounded-lg overflow-auto"
        style={{ maxHeight: professional ? 950 : Math.max(height * 1.5, 450) }}
      >
        <div
          ref={containerRef}
          className="p-4 transition-transform duration-200 origin-top-left"
          style={{
            transform: `scale(${zoom})`,
            transformOrigin: 'center center',
            minHeight: height,
            width: zoom > 1 ? `${100 / zoom}%` : '100%'
          }}
          dangerouslySetInnerHTML={{ __html: svgContent }}
        />
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-gray-600 rounded"></div>
          <span>Nicht ausgewählt</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-blue-500 rounded"></div>
          <span>Hover</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-red-500 rounded"></div>
          <span>Ausgewählt (Gerüst)</span>
        </div>
      </div>

      {/* Tip */}
      <p className="text-xs text-gray-400">
        Klicken Sie auf eine Fassade im Grundriss, um sie für das Gerüst auszuwählen oder abzuwählen.
      </p>
    </div>
  )
}
