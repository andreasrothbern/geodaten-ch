interface CrossSectionSVGProps {
  /** Building width in meters */
  widthM: number
  /** Eave height (Traufhöhe) in meters */
  eaveHeightM: number
  /** Ridge height (Firsthöhe) in meters - optional for flat roofs */
  ridgeHeightM?: number
  /** Roof type */
  roofType?: 'flat' | 'gable' | 'hip'
  /** Number of floors */
  floors?: number
  /** Show scaffold */
  showScaffold?: boolean
  /** Height source label */
  heightSource?: string
  /** SVG width */
  width?: number
  /** SVG height */
  height?: number
}

export function CrossSectionSVG({
  widthM,
  eaveHeightM,
  ridgeHeightM,
  roofType = 'gable',
  floors,
  showScaffold = true,
  heightSource,
  width = 400,
  height = 300
}: CrossSectionSVGProps) {
  // Calculate scale
  const margin = { top: 50, right: 80, bottom: 50, left: 50 }
  const drawWidth = width - margin.left - margin.right
  const drawHeight = height - margin.top - margin.bottom

  const maxHeight = ridgeHeightM || eaveHeightM
  const scaleX = drawWidth / (widthM + 4) // +4 for scaffold space
  const scaleY = drawHeight / (maxHeight + 2)
  const scale = Math.min(scaleX, scaleY)

  // Building dimensions in pixels
  const bWidth = widthM * scale
  const bEaveHeight = eaveHeightM * scale
  const bRidgeHeight = (ridgeHeightM || eaveHeightM) * scale

  // Positions
  const groundY = margin.top + drawHeight
  const buildingX = margin.left + (drawWidth - bWidth) / 2
  const scaffoldWidth = 12

  // Floor height calculation
  const floorHeight = floors ? bEaveHeight / floors : bEaveHeight / 3

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      className="bg-gray-50 rounded-lg border"
    >
      <defs>
        <pattern id="section-hatch" patternUnits="userSpaceOnUse" width="6" height="6">
          <path d="M-1,1 l3,-3 M0,6 l6,-6 M5,7 l3,-3" stroke="#666" strokeWidth="0.5" fill="none"/>
        </pattern>
        <pattern id="section-scaffold" patternUnits="userSpaceOnUse" width="8" height="8">
          <rect width="8" height="8" fill="#fff3cd"/>
          <line x1="0" y1="8" x2="8" y2="0" stroke="#ffc107" strokeWidth="0.5"/>
        </pattern>
      </defs>

      {/* Title */}
      <text x={width / 2} y="20" textAnchor="middle" fontFamily="Arial" fontSize="13" fontWeight="bold" fill="#333">
        Schnitt / Seitenansicht
      </text>

      {/* Ground line */}
      <line x1={margin.left - 20} y1={groundY} x2={width - margin.right + 20} y2={groundY} stroke="#333" strokeWidth="2"/>
      <rect x={margin.left - 20} y={groundY} width={width - margin.left - margin.right + 40} height="15" fill="#8B4513" opacity="0.2"/>

      {/* Height grid */}
      {[5, 10, 15, 20, 25, 30].filter(h => h <= maxHeight + 2).map(h => (
        <g key={h}>
          <line
            x1={margin.left}
            y1={groundY - h * scale}
            x2={width - margin.right}
            y2={groundY - h * scale}
            stroke="#ddd"
            strokeWidth="0.5"
            strokeDasharray="4,4"
          />
          <text x={margin.left - 5} y={groundY - h * scale + 3} textAnchor="end" fontFamily="Arial" fontSize="8" fill="#999">
            {h}m
          </text>
        </g>
      ))}

      {/* Left scaffold */}
      {showScaffold && (
        <g>
          <rect
            x={buildingX - scaffoldWidth - 8}
            y={groundY - bEaveHeight - 20}
            width={scaffoldWidth}
            height={bEaveHeight + 20}
            fill="url(#section-scaffold)"
            stroke="#ffc107"
            strokeWidth="1.5"
          />
          {/* Anchor points */}
          {[0.25, 0.5, 0.75].map((ratio, i) => (
            <circle
              key={i}
              cx={buildingX - scaffoldWidth / 2 - 8}
              cy={groundY - bEaveHeight * ratio}
              r="3"
              fill="#dc3545"
            />
          ))}
        </g>
      )}

      {/* Building body */}
      <rect
        x={buildingX}
        y={groundY - bEaveHeight}
        width={bWidth}
        height={bEaveHeight}
        fill="url(#section-hatch)"
        stroke="#333"
        strokeWidth="1.5"
      />

      {/* Floor lines */}
      {floors && Array.from({ length: floors - 1 }).map((_, i) => (
        <line
          key={i}
          x1={buildingX}
          y1={groundY - floorHeight * (i + 1)}
          x2={buildingX + bWidth}
          y2={groundY - floorHeight * (i + 1)}
          stroke="#666"
          strokeWidth="0.5"
          strokeDasharray="2,2"
        />
      ))}

      {/* Roof */}
      {roofType === 'gable' && ridgeHeightM && ridgeHeightM > eaveHeightM && (
        <polygon
          points={`
            ${buildingX},${groundY - bEaveHeight}
            ${buildingX + bWidth / 2},${groundY - bRidgeHeight}
            ${buildingX + bWidth},${groundY - bEaveHeight}
          `}
          fill="#8b7355"
          stroke="#333"
          strokeWidth="1.5"
        />
      )}

      {roofType === 'flat' && (
        <rect
          x={buildingX - 5}
          y={groundY - bEaveHeight - 8}
          width={bWidth + 10}
          height="8"
          fill="#666"
          stroke="#333"
        />
      )}

      {/* Right scaffold */}
      {showScaffold && (
        <g>
          <rect
            x={buildingX + bWidth + 8}
            y={groundY - bEaveHeight - 20}
            width={scaffoldWidth}
            height={bEaveHeight + 20}
            fill="url(#section-scaffold)"
            stroke="#ffc107"
            strokeWidth="1.5"
          />
          {/* Anchor points */}
          {[0.25, 0.5, 0.75].map((ratio, i) => (
            <circle
              key={i}
              cx={buildingX + bWidth + 8 + scaffoldWidth / 2}
              cy={groundY - bEaveHeight * ratio}
              r="3"
              fill="#dc3545"
            />
          ))}
        </g>
      )}

      {/* Height annotations */}
      <g fontFamily="Arial" fontSize="9" fill="#0066cc">
        {/* Eave height */}
        <line
          x1={width - margin.right + 5}
          y1={groundY - bEaveHeight}
          x2={width - margin.right + 25}
          y2={groundY - bEaveHeight}
          stroke="#0066cc"
          strokeWidth="0.5"
          strokeDasharray="2,2"
        />
        <text x={width - margin.right + 28} y={groundY - bEaveHeight + 3} fontSize="9">
          Traufe {eaveHeightM.toFixed(1)}m
        </text>

        {/* Ridge height */}
        {ridgeHeightM && ridgeHeightM > eaveHeightM && (
          <>
            <line
              x1={width - margin.right + 5}
              y1={groundY - bRidgeHeight}
              x2={width - margin.right + 25}
              y2={groundY - bRidgeHeight}
              stroke="#dc3545"
              strokeWidth="0.5"
              strokeDasharray="2,2"
            />
            <text x={width - margin.right + 28} y={groundY - bRidgeHeight + 3} fontSize="9" fill="#dc3545" fontWeight="bold">
              First {ridgeHeightM.toFixed(1)}m
            </text>
          </>
        )}

        {/* Ground */}
        <text x={width - margin.right + 28} y={groundY + 3} fontSize="8" fill="#333">
          ±0.00
        </text>
      </g>

      {/* Width annotation */}
      <g>
        <line x1={buildingX} y1={groundY + 25} x2={buildingX + bWidth} y2={groundY + 25} stroke="#333" strokeWidth="0.5"/>
        <line x1={buildingX} y1={groundY + 20} x2={buildingX} y2={groundY + 30} stroke="#333" strokeWidth="0.5"/>
        <line x1={buildingX + bWidth} y1={groundY + 20} x2={buildingX + bWidth} y2={groundY + 30} stroke="#333" strokeWidth="0.5"/>
        <text x={buildingX + bWidth / 2} y={groundY + 40} textAnchor="middle" fontFamily="Arial" fontSize="9">
          {widthM.toFixed(1)} m
        </text>
      </g>

      {/* Height source info */}
      {heightSource && (
        <text x={width / 2} y={height - 8} textAnchor="middle" fontFamily="Arial" fontSize="9" fill="#666">
          Höhe: {heightSource}
        </text>
      )}

      {/* Legend */}
      <g transform={`translate(${width - 100}, 40)`}>
        <rect x="0" y="0" width="90" height="50" fill="white" stroke="#ccc" rx="3"/>
        <circle cx="12" cy="15" r="3" fill="#dc3545"/>
        <text x="20" y="18" fontFamily="Arial" fontSize="8">Verankerung</text>
        <rect x="6" y="28" width="12" height="10" fill="url(#section-scaffold)" stroke="#ffc107"/>
        <text x="22" y="36" fontFamily="Arial" fontSize="8">Gerüst</text>
      </g>
    </svg>
  )
}
