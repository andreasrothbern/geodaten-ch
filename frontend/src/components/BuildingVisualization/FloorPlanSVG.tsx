import { useMemo } from 'react'

interface FloorPlanSVGProps {
  /** Polygon coordinates in LV95 format [[x,y], ...] */
  polygon: [number, number][]
  /** Building width in meters */
  widthM: number
  /** Building depth in meters */
  depthM: number
  /** EGID for display */
  egid?: number
  /** Total area in m² */
  areaM2?: number
  /** Show scaffold positions */
  showScaffold?: boolean
  /** SVG width in pixels */
  width?: number
  /** SVG height in pixels */
  height?: number
}

export function FloorPlanSVG({
  polygon,
  widthM,
  depthM,
  egid,
  areaM2,
  showScaffold = true,
  width = 400,
  height = 350
}: FloorPlanSVGProps) {
  // Normalize polygon to start at 0,0 and calculate scale
  const { normalizedPolygon, scale } = useMemo(() => {
    if (!polygon || polygon.length < 3) {
      return { normalizedPolygon: [], scale: 1 }
    }

    const xs = polygon.map(p => p[0])
    const ys = polygon.map(p => p[1])
    const minX = Math.min(...xs)
    const minY = Math.min(...ys)
    const maxX = Math.max(...xs)
    const maxY = Math.max(...ys)

    const polyWidth = maxX - minX
    const polyHeight = maxY - minY

    // Calculate scale to fit in drawing area (with margins)
    const drawingWidth = width - 100 // margins
    const drawingHeight = height - 120
    const scaleX = drawingWidth / polyWidth
    const scaleY = drawingHeight / polyHeight
    const scale = Math.min(scaleX, scaleY) * 0.85

    // Center the polygon
    const scaledWidth = polyWidth * scale
    const scaledHeight = polyHeight * scale
    const offsetX = (width - scaledWidth) / 2
    const offsetY = 60 + (drawingHeight - scaledHeight) / 2

    // Normalize and flip Y (SVG y increases downward)
    const normalized = polygon.map(([x, y]) => [
      (x - minX) * scale + offsetX,
      (maxY - y) * scale + offsetY // flip Y
    ] as [number, number])

    return { normalizedPolygon: normalized, scale }
  }, [polygon, width, height])

  // Create polygon path
  const polygonPath = normalizedPolygon.length > 0
    ? `M ${normalizedPolygon.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' L ')} Z`
    : ''

  // Calculate scaffold offset (in pixels, ~1m from building)
  const scaffoldOffset = scale * 1.0

  // Create scaffold path (offset from building)
  const scaffoldPath = useMemo(() => {
    if (!showScaffold || normalizedPolygon.length < 3) return ''

    // Simple offset - expand polygon outward
    const center = normalizedPolygon.reduce(
      (acc, p) => [acc[0] + p[0] / normalizedPolygon.length, acc[1] + p[1] / normalizedPolygon.length],
      [0, 0]
    )

    const offsetPolygon = normalizedPolygon.map(([x, y]) => {
      const dx = x - center[0]
      const dy = y - center[1]
      const len = Math.sqrt(dx * dx + dy * dy)
      if (len === 0) return [x, y]
      const factor = (len + scaffoldOffset) / len
      return [
        center[0] + dx * factor,
        center[1] + dy * factor
      ]
    })

    return `M ${offsetPolygon.map(p => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' L ')} Z`
  }, [normalizedPolygon, showScaffold, scaffoldOffset])

  if (polygon.length < 3) {
    return (
      <div className="flex items-center justify-center bg-gray-100 rounded-lg" style={{ width, height }}>
        <p className="text-gray-500">Keine Polygon-Daten verfügbar</p>
      </div>
    )
  }

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      className="bg-gray-50 rounded-lg border"
    >
      <defs>
        {/* Building hatch pattern */}
        <pattern id="building-hatch" patternUnits="userSpaceOnUse" width="6" height="6">
          <path d="M-1,1 l3,-3 M0,6 l6,-6 M5,7 l3,-3" stroke="#666" strokeWidth="0.5" fill="none"/>
        </pattern>

        {/* Scaffold pattern */}
        <pattern id="scaffold-fill" patternUnits="userSpaceOnUse" width="8" height="8">
          <rect width="8" height="8" fill="#fff3cd"/>
          <line x1="0" y1="8" x2="8" y2="0" stroke="#ffc107" strokeWidth="0.5"/>
        </pattern>
      </defs>

      {/* Title */}
      <text x={width / 2} y="20" textAnchor="middle" fontFamily="Arial" fontSize="13" fontWeight="bold" fill="#333">
        Grundriss mit Gerüstposition
      </text>

      {/* Scaffold (behind building) */}
      {showScaffold && scaffoldPath && (
        <path
          d={scaffoldPath}
          fill="url(#scaffold-fill)"
          stroke="#ffc107"
          strokeWidth="1.5"
          opacity="0.8"
        />
      )}

      {/* Building polygon */}
      <path
        d={polygonPath}
        fill="url(#building-hatch)"
        stroke="#333"
        strokeWidth="2"
      />

      {/* North arrow */}
      <g transform={`translate(${width - 30}, ${height - 40})`}>
        <polygon points="0,-12 4,4 0,0 -4,4" fill="#333"/>
        <text x="0" y="12" textAnchor="middle" fontFamily="Arial" fontSize="10" fontWeight="bold">N</text>
      </g>

      {/* Scale bar */}
      <g transform="translate(20, 320)">
        <line x1="0" y1="0" x2={scale * 10} y2="0" stroke="#333" strokeWidth="2"/>
        <line x1="0" y1="-4" x2="0" y2="4" stroke="#333" strokeWidth="2"/>
        <line x1={scale * 10} y1="-4" x2={scale * 10} y2="4" stroke="#333" strokeWidth="2"/>
        <text x={scale * 5} y="14" textAnchor="middle" fontFamily="Arial" fontSize="9">10 m</text>
      </g>

      {/* Dimensions */}
      <text x={width / 2} y={height - 8} textAnchor="middle" fontFamily="Arial" fontSize="10" fill="#666">
        {widthM.toFixed(1)}m × {depthM.toFixed(1)}m
        {areaM2 && ` | ${areaM2.toFixed(0)} m²`}
        {egid && ` | EGID: ${egid}`}
      </text>

      {/* Legend */}
      <g transform="translate(20, 40)">
        <rect x="0" y="0" width="90" height="50" fill="white" stroke="#ccc" rx="3"/>
        <rect x="8" y="10" width="14" height="10" fill="url(#building-hatch)" stroke="#333"/>
        <text x="26" y="18" fontFamily="Arial" fontSize="8">Gebäude</text>
        {showScaffold && (
          <>
            <rect x="8" y="28" width="14" height="10" fill="url(#scaffold-fill)" stroke="#ffc107"/>
            <text x="26" y="36" fontFamily="Arial" fontSize="8">Gerüst W09</text>
          </>
        )}
      </g>
    </svg>
  )
}
