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
  width = 650,
  height = 420
}: CrossSectionSVGProps) {
  // Calculate scale
  const margin = { top: 60, right: 120, bottom: 70, left: 60 }
  const drawWidth = width - margin.left - margin.right
  const drawHeight = height - margin.top - margin.bottom

  const maxHeight = ridgeHeightM || eaveHeightM
  const scaleX = drawWidth / (widthM + 6) // +6 for scaffold space
  const scaleY = drawHeight / (maxHeight + 3)
  const scale = Math.min(scaleX, scaleY)

  // Building dimensions in pixels
  const bWidth = widthM * scale
  const bEaveHeight = eaveHeightM * scale
  const bRidgeHeight = (ridgeHeightM || eaveHeightM) * scale

  // Positions
  const groundY = margin.top + drawHeight
  const buildingX = margin.left + (drawWidth - bWidth) / 2
  const scaffoldWidth = 15

  // Floor height calculation
  const floorCount = floors || Math.round(eaveHeightM / 2.8)
  const floorHeight = bEaveHeight / floorCount

  // Height grid values
  const gridHeights = [5, 10, 15, 20, 25, 30, 40, 50].filter(h => h <= maxHeight + 5)

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width={width}
      height={height}
      className="rounded-lg border"
    >
      <defs>
        {/* Building hatch pattern */}
        <pattern id="section-hatch" patternUnits="userSpaceOnUse" width="8" height="8">
          <path d="M-2,2 l4,-4 M0,8 l8,-8 M6,10 l4,-4" stroke="#666" strokeWidth="0.5" fill="none"/>
        </pattern>

        {/* Scaffold pattern */}
        <pattern id="section-scaffold" patternUnits="userSpaceOnUse" width="10" height="10">
          <rect width="10" height="10" fill="#fff3cd"/>
          <line x1="0" y1="10" x2="10" y2="0" stroke="#ffc107" strokeWidth="0.5"/>
        </pattern>

        {/* Window pattern */}
        <pattern id="windows" patternUnits="userSpaceOnUse" width="20" height="25">
          <rect width="20" height="25" fill="#e8e8e8"/>
          <rect x="3" y="3" width="14" height="18" fill="#4a90a4" stroke="#333" strokeWidth="0.5"/>
        </pattern>
      </defs>

      {/* Sky background */}
      <rect width={width} height={groundY} fill="#e8f4fc"/>

      {/* Ground */}
      <rect x="0" y={groundY} width={width} height={height - groundY} fill="#d4c4b0"/>

      {/* Title */}
      <text x={width / 2} y="22" textAnchor="middle" fontFamily="Arial" fontSize="14" fontWeight="bold" fill="#333">
        Gebäudeschnitt mit Gerüstposition
      </text>
      <text x={width / 2} y="38" textAnchor="middle" fontFamily="Arial" fontSize="10" fill="#666">
        {heightSource || 'Seitenansicht'}
      </text>

      {/* Ground line */}
      <line x1={margin.left - 20} y1={groundY} x2={width - margin.right + 20} y2={groundY} stroke="#333" strokeWidth="2"/>

      {/* Height grid */}
      {gridHeights.map(h => (
        <g key={h}>
          <line
            x1={margin.left}
            y1={groundY - h * scale}
            x2={width - margin.right}
            y2={groundY - h * scale}
            stroke="#ccc"
            strokeWidth="0.5"
            strokeDasharray="4,4"
          />
          <text x={margin.left - 8} y={groundY - h * scale + 3} textAnchor="end" fontFamily="Arial" fontSize="9" fill="#999">
            {h}m
          </text>
        </g>
      ))}

      {/* Left scaffold */}
      {showScaffold && (
        <g>
          <rect
            x={buildingX - scaffoldWidth - 10}
            y={groundY - bEaveHeight - 25}
            width={scaffoldWidth}
            height={bEaveHeight + 25}
            fill="url(#section-scaffold)"
            stroke="#ffc107"
            strokeWidth="2"
          />
          {/* Scaffold label */}
          <text
            x={buildingX - scaffoldWidth / 2 - 10}
            y={groundY - bEaveHeight / 2}
            textAnchor="middle"
            fontFamily="Arial"
            fontSize="8"
            fill="#996600"
            transform={`rotate(-90, ${buildingX - scaffoldWidth / 2 - 10}, ${groundY - bEaveHeight / 2})`}
          >
            Gerüst W09
          </text>
          {/* Anchor points */}
          {[0.2, 0.4, 0.6, 0.8].map((ratio, i) => (
            <circle
              key={i}
              cx={buildingX - scaffoldWidth / 2 - 10}
              cy={groundY - bEaveHeight * ratio}
              r="4"
              fill="#dc3545"
            />
          ))}
        </g>
      )}

      {/* Building body with window pattern */}
      <rect
        x={buildingX}
        y={groundY - bEaveHeight}
        width={bWidth}
        height={bEaveHeight}
        fill="#e0e0e0"
        stroke="#333"
        strokeWidth="1.5"
      />

      {/* Windows */}
      <rect
        x={buildingX + 10}
        y={groundY - bEaveHeight + 10}
        width={bWidth - 20}
        height={bEaveHeight - 20}
        fill="url(#windows)"
      />

      {/* Floor lines */}
      {Array.from({ length: floorCount - 1 }).map((_, i) => (
        <line
          key={i}
          x1={buildingX}
          y1={groundY - floorHeight * (i + 1)}
          x2={buildingX + bWidth}
          y2={groundY - floorHeight * (i + 1)}
          stroke="#999"
          strokeWidth="1"
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
          y={groundY - bEaveHeight - 10}
          width={bWidth + 10}
          height="10"
          fill="#666"
          stroke="#333"
        />
      )}

      {/* Right scaffold */}
      {showScaffold && (
        <g>
          <rect
            x={buildingX + bWidth + 10}
            y={groundY - bEaveHeight - 25}
            width={scaffoldWidth}
            height={bEaveHeight + 25}
            fill="url(#section-scaffold)"
            stroke="#ffc107"
            strokeWidth="2"
          />
          {/* Anchor points */}
          {[0.2, 0.4, 0.6, 0.8].map((ratio, i) => (
            <circle
              key={i}
              cx={buildingX + bWidth + 10 + scaffoldWidth / 2}
              cy={groundY - bEaveHeight * ratio}
              r="4"
              fill="#dc3545"
            />
          ))}
        </g>
      )}

      {/* Height annotations on right */}
      <g fontFamily="Arial" fontSize="9">
        {/* Ground level */}
        <line x1={width - margin.right + 10} y1={groundY} x2={width - margin.right + 35} y2={groundY} stroke="#333" strokeWidth="0.5"/>
        <text x={width - margin.right + 40} y={groundY + 3} fill="#333">±0.00 m</text>

        {/* Eave height */}
        <line
          x1={width - margin.right + 10}
          y1={groundY - bEaveHeight}
          x2={width - margin.right + 35}
          y2={groundY - bEaveHeight}
          stroke="#0066cc"
          strokeWidth="0.5"
          strokeDasharray="2,2"
        />
        <text x={width - margin.right + 40} y={groundY - bEaveHeight + 3} fill="#0066cc">
          Traufe {eaveHeightM.toFixed(1)}m
        </text>

        {/* Ridge height */}
        {ridgeHeightM && ridgeHeightM > eaveHeightM && (
          <>
            <line
              x1={width - margin.right + 10}
              y1={groundY - bRidgeHeight}
              x2={width - margin.right + 35}
              y2={groundY - bRidgeHeight}
              stroke="#dc3545"
              strokeWidth="0.5"
              strokeDasharray="2,2"
            />
            <text x={width - margin.right + 40} y={groundY - bRidgeHeight + 3} fill="#dc3545" fontWeight="bold">
              First {ridgeHeightM.toFixed(1)}m
            </text>
          </>
        )}
      </g>

      {/* Width annotation bottom */}
      <g>
        <line x1={buildingX} y1={groundY + 25} x2={buildingX + bWidth} y2={groundY + 25} stroke="#333" strokeWidth="1"/>
        <line x1={buildingX} y1={groundY + 18} x2={buildingX} y2={groundY + 32} stroke="#333" strokeWidth="1"/>
        <line x1={buildingX + bWidth} y1={groundY + 18} x2={buildingX + bWidth} y2={groundY + 32} stroke="#333" strokeWidth="1"/>
        <text x={buildingX + bWidth / 2} y={groundY + 45} textAnchor="middle" fontFamily="Arial" fontSize="11" fontWeight="bold">
          {widthM.toFixed(1)} m
        </text>
      </g>

      {/* Legend */}
      <g transform={`translate(${width - 145}, 55)`}>
        <rect x="0" y="0" width="135" height="80" fill="white" stroke="#ccc" rx="4"/>
        <text x="10" y="18" fontFamily="Arial" fontSize="10" fontWeight="bold" fill="#333">Legende</text>

        <rect x="10" y="28" width="18" height="12" fill="url(#section-scaffold)" stroke="#ffc107"/>
        <text x="32" y="38" fontFamily="Arial" fontSize="9">Fassadengerüst</text>

        <circle cx="19" cy="55" r="4" fill="#dc3545"/>
        <text x="32" y="58" fontFamily="Arial" fontSize="9">Verankerung</text>

        <rect x="10" y="65" width="18" height="8" fill="#8b7355" stroke="#333"/>
        <text x="32" y="72" fontFamily="Arial" fontSize="9">Dach</text>
      </g>

      {/* NPK 114 Info Box */}
      <g transform={`translate(${margin.left}, ${height - 55})`}>
        <rect x="0" y="0" width="260" height="45" fill="#e8f5e9" stroke="#4caf50" rx="4"/>
        <text x="10" y="15" fontFamily="Arial" fontSize="10" fontWeight="bold" fill="#2e7d32">
          NPK 114 Ausmass:
        </text>
        <text x="10" y="28" fontFamily="Arial" fontSize="9" fill="#333">
          Ausmasshöhe: {eaveHeightM.toFixed(1)}m + 1.0m = {(eaveHeightM + 1).toFixed(1)}m
        </text>
        <text x="10" y="40" fontFamily="Arial" fontSize="9" fill="#333">
          Geschosse: {floorCount} | Breitenklasse: W09
        </text>
      </g>

      {/* Scale bar */}
      <g transform={`translate(${width - 130}, ${height - 35})`}>
        <line x1="0" y1="0" x2={scale * 10} y2="0" stroke="#333" strokeWidth="2"/>
        <line x1="0" y1="-5" x2="0" y2="5" stroke="#333" strokeWidth="2"/>
        <line x1={scale * 10} y1="-5" x2={scale * 10} y2="5" stroke="#333" strokeWidth="2"/>
        <text x={scale * 5} y="15" textAnchor="middle" fontFamily="Arial" fontSize="9">10 m</text>
      </g>
    </svg>
  )
}
