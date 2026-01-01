/**
 * MiniFloorPlan - SVG visualization of building with selected facades
 * Shows the actual building polygon with facade highlighting
 */

import type { ScaffoldFacade } from '../../types/scaffold.types';
import { getFacadeColor } from '../../types/scaffold.types';

interface MiniFloorPlanProps {
  facades: ScaffoldFacade[];       // Enabled/selected facades
  allFacades: ScaffoldFacade[];    // All facades for rendering
  polygon?: [number, number][];    // Building polygon coordinates
  size?: number;
}

export default function MiniFloorPlan({
  facades,
  allFacades,
  polygon,
  size = 96,
}: MiniFloorPlanProps) {
  // Get enabled facade IDs for quick lookup
  const enabledIds = new Set(facades.map(f => f.id));

  // If we have a polygon with coordinates, render the real shape
  if (polygon && polygon.length >= 3 && allFacades.some(f => f.start_point && f.end_point)) {
    // Calculate bounds
    const xs = polygon.map(p => p[0]);
    const ys = polygon.map(p => p[1]);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const width = maxX - minX;
    const height = maxY - minY;
    const padding = Math.max(width, height) * 0.15;

    const viewBox = `${minX - padding} ${minY - padding} ${width + padding * 2} ${height + padding * 2}`;

    // Create polygon path
    const pathData = polygon.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ') + ' Z';

    // Facade line thickness based on selection
    const strokeWidthEnabled = width * 0.04;
    const strokeWidthDisabled = width * 0.015;

    return (
      <div className="floor-plan-mini" style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.1))' }}>
        <svg viewBox={viewBox} style={{ width: size, height: size }}>
          {/* Transform to flip Y-axis (LV95 has Y increasing northward) */}
          <g transform={`translate(0, ${maxY + minY}) scale(1, -1)`}>
            {/* Building outline */}
            <path
              d={pathData}
              fill="#f3f4f6"
              stroke="#d1d5db"
              strokeWidth={width * 0.01}
            />

            {/* All facade lines - enabled ones highlighted */}
            {allFacades.map((facade) => {
              if (!facade.start_point || !facade.end_point) return null;

              const isEnabled = enabledIds.has(facade.id);

              return (
                <line
                  key={facade.id}
                  x1={facade.start_point[0]}
                  y1={facade.start_point[1]}
                  x2={facade.end_point[0]}
                  y2={facade.end_point[1]}
                  stroke={isEnabled ? getFacadeColor(facade.direction) : '#d1d5db'}
                  strokeWidth={isEnabled ? strokeWidthEnabled : strokeWidthDisabled}
                  strokeLinecap="round"
                />
              );
            })}
          </g>

          {/* North arrow */}
          <g transform={`translate(${maxX + padding * 0.6}, ${minY + padding * 0.4})`}>
            <circle r={width * 0.06} fill="white" stroke="#666" strokeWidth={width * 0.008} />
            <text
              textAnchor="middle"
              dy={width * 0.025}
              fontSize={width * 0.05}
              fontWeight="bold"
              fill="#dc2626"
              style={{ transform: 'scaleY(-1)', transformOrigin: 'center' }}
            >
              N
            </text>
          </g>
        </svg>
      </div>
    );
  }

  // Fallback: simple rectangle representation if no polygon
  return (
    <div className="floor-plan-mini" style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.1))' }}>
      <svg viewBox="0 0 120 120" style={{ width: size, height: size }}>
        {/* Building outline */}
        <rect
          x="20"
          y="20"
          width="80"
          height="80"
          fill="#f3f4f6"
          stroke="#d1d5db"
          strokeWidth="2"
          rx="2"
        />

        {/* Compass indicator */}
        <text
          x="60"
          y="12"
          textAnchor="middle"
          fill="#9ca3af"
          fontSize="8"
          fontWeight="bold"
        >
          N
        </text>

        {/* Simple indicator showing count */}
        <text
          x="60"
          y="65"
          textAnchor="middle"
          fill="#666"
          fontSize="12"
        >
          {facades.length} Fassade{facades.length !== 1 ? 'n' : ''}
        </text>
      </svg>
    </div>
  );
}

// Legend component to show facade colors
interface FloorPlanLegendProps {
  facades: ScaffoldFacade[];
}

export function FloorPlanLegend({ facades }: FloorPlanLegendProps) {
  return (
    <div className="flex-1 grid grid-cols-2 gap-2 text-sm">
      {facades.map((facade) => (
        <div key={facade.id} className="flex items-center gap-2">
          <span
            className="w-3 h-3 rounded"
            style={{ backgroundColor: getFacadeColor(facade.direction) }}
          />
          <span className="text-gray-600">
            {facade.name} ({facade.length_m.toFixed(1)}m)
          </span>
        </div>
      ))}
    </div>
  );
}
