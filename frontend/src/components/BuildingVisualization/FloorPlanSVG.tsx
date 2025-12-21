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
  width = 500,
  height = 420
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
        {/* Building hatch pattern - larger for better visibility */}
        <pattern id="building-hatch" patternUnits="userSpaceOnUse" width="8" height="8">
          <path d="M-2,2 l4,-4 M0,8 l8,-8 M6,10 l4,-4" stroke="#666" strokeWidth="0.5" fill="none"/>
        </pattern>

        {/* Scaffold pattern - striped for better visibility */}
        <pattern id="scaffold-fill" patternUnits="userSpaceOnUse" width="12" height="12">
          <rect width="12" height="12" fill="#fff3cd"/>
          <rect x="0" y="0" width="12" height="2" fill="#ffc107" opacity="0.5"/>
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
      <g transform={`translate(${width - 30}, ${height - 50})`}>
        <polygon points="0,-15 5,5 0,0 -5,5" fill="#333"/>
        <text x="0" y="15" textAnchor="middle" fontFamily="Arial" fontSize="10" fontWeight="bold">N</text>
      </g>

      {/* Scale bar */}
      <g transform={`translate(20, ${height - 50})`}>
        <line x1="0" y1="0" x2={scale * 10} y2="0" stroke="#333" strokeWidth="2"/>
        <line x1="0" y1="-5" x2="0" y2="5" stroke="#333" strokeWidth="2"/>
        <line x1={scale * 10} y1="-5" x2={scale * 10} y2="5" stroke="#333" strokeWidth="2"/>
        <text x={scale * 5} y="15" textAnchor="middle" fontFamily="Arial" fontSize="10">10 m</text>
      </g>

      {/* Dimensions */}
      <text x={width / 2} y={height - 8} textAnchor="middle" fontFamily="Arial" fontSize="10" fill="#666">
        {widthM.toFixed(1)}m × {depthM.toFixed(1)}m
        {areaM2 && ` | ${areaM2.toFixed(0)} m²`}
        {egid && ` | EGID: ${egid}`}
      </text>

      {/* Legend - positioned in top right like showcase */}
      <g transform={`translate(${width - 150}, 40)`}>
        <rect x="0" y="0" width="140" height={showScaffold ? 85 : 50} fill="white" stroke="#ccc" rx="4"/>
        <text x="10" y="18" fontFamily="Arial" fontSize="11" fontWeight="bold" fill="#333">Legende</text>
        <rect x="10" y="28" width="20" height="12" fill="url(#building-hatch)" stroke="#333"/>
        <text x="35" y="38" fontFamily="Arial" fontSize="10">Gebäude</text>
        {showScaffold && (
          <>
            <rect x="10" y="48" width="20" height="12" fill="url(#scaffold-fill)" stroke="#ffc107"/>
            <text x="35" y="58" fontFamily="Arial" fontSize="10">Gerüst W09</text>
            <circle cx="20" cy="75" r="4" fill="#dc3545"/>
            <text x="35" y="79" fontFamily="Arial" fontSize="10">Verankerung</text>
          </>
        )}
      </g>

      {/* Anchor points on scaffold perimeter */}
      {showScaffold && normalizedPolygon.length >= 3 && (() => {
        const center = normalizedPolygon.reduce(
          (acc, p) => [acc[0] + p[0] / normalizedPolygon.length, acc[1] + p[1] / normalizedPolygon.length],
          [0, 0]
        )
        // Place anchors at every 3rd vertex on the scaffold
        return normalizedPolygon.filter((_, i) => i % 3 === 0).map(([x, y], i) => {
          const dx = x - center[0]
          const dy = y - center[1]
          const len = Math.sqrt(dx * dx + dy * dy)
          if (len === 0) return null
          const factor = (len + scaffoldOffset * 0.5) / len
          const ax = center[0] + dx * factor
          const ay = center[1] + dy * factor
          return (
            <circle key={i} cx={ax} cy={ay} r="4" fill="#dc3545" opacity="0.9"/>
          )
        })
      })()}
    </svg>
  )
}
