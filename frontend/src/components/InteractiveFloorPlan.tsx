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
  selectedFacades: number[]
  onFacadeToggle: (index: number) => void
  onSelectAll?: () => void
  onDeselectAll?: () => void
  height?: number
}

export function InteractiveFloorPlan({
  address,
  apiUrl,
  sides,
  selectedFacades,
  onFacadeToggle,
  onSelectAll,
  onDeselectAll,
  height = 300
}: InteractiveFloorPlanProps) {
  const [svgContent, setSvgContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Fetch SVG from server
  useEffect(() => {
    const fetchSvg = async () => {
      setLoading(true)
      setError(null)
      try {
        const params = new URLSearchParams({
          address,
          height: height.toString()
        })
        const response = await fetch(`${apiUrl}/api/v1/visualize/floor-plan?${params}`)
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

    if (address) {
      fetchSvg()
    }
  }, [address, apiUrl, height])

  // Add click handlers to facade segments after SVG is loaded
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

        // Add click handler
        const handleClick = () => {
          onFacadeToggle(index)
        }

        segment.addEventListener('click', handleClick)

        // Cleanup
        return () => {
          segment.removeEventListener('click', handleClick)
        }
      }
    })
  }, [svgContent, selectedFacades, onFacadeToggle])

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
              Alle auswahlen
            </button>
          )}
          {onDeselectAll && (
            <button
              onClick={onDeselectAll}
              className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Keine auswahlen
            </button>
          )}
        </div>
        <div className="text-sm text-gray-600">
          <span className="font-medium">{selectedCount}</span> von {totalCount} Fassaden ausgewahlt
          ({selectedLength.toFixed(1)}m von {totalLength.toFixed(1)}m)
        </div>
      </div>

      {/* SVG Container */}
      <div
        ref={containerRef}
        className="bg-white border rounded-lg p-4 overflow-hidden"
        style={{ minHeight: height }}
        dangerouslySetInnerHTML={{ __html: svgContent }}
      />

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-sm text-gray-600">
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-gray-600 rounded"></div>
          <span>Nicht ausgewahlt</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-blue-500 rounded"></div>
          <span>Hover</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-1 bg-red-500 rounded"></div>
          <span>Ausgewahlt (Gerust)</span>
        </div>
      </div>

      {/* Tip */}
      <p className="text-xs text-gray-400">
        Klicken Sie auf eine Fassade im Grundriss, um sie fur das Gerust auszuwahlen oder abzuwahlen.
      </p>
    </div>
  )
}
