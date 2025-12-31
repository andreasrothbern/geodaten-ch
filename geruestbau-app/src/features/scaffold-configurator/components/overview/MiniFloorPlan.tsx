/**
 * MiniFloorPlan - SVG visualization of building with selected facades
 */

import type { ScaffoldFacade, FacadeDirection } from '../../types/scaffold.types';
import { CORNER_COLOR } from '../../types/scaffold.types';

interface MiniFloorPlanProps {
  facades: ScaffoldFacade[];
  size?: number;
}

// Position mapping for each direction
const DIRECTION_POSITIONS: Record<FacadeDirection, {
  x1: number; y1: number; x2: number; y2: number;
}> = {
  'N':  { x1: 20, y1: 20, x2: 100, y2: 20 },
  'NE': { x1: 100, y1: 20, x2: 100, y2: 20 }, // Corner position
  'E':  { x1: 100, y1: 20, x2: 100, y2: 100 },
  'SE': { x1: 100, y1: 100, x2: 100, y2: 100 }, // Corner position
  'S':  { x1: 100, y1: 100, x2: 20, y2: 100 },
  'SW': { x1: 20, y1: 100, x2: 20, y2: 100 }, // Corner position
  'W':  { x1: 20, y1: 100, x2: 20, y2: 20 },
  'NW': { x1: 20, y1: 20, x2: 20, y2: 20 }, // Corner position
};

// Corner positions
const CORNER_POSITIONS: { direction: string; cx: number; cy: number }[] = [
  { direction: 'NW', cx: 20, cy: 20 },
  { direction: 'NE', cx: 100, cy: 20 },
  { direction: 'SE', cx: 100, cy: 100 },
  { direction: 'SW', cx: 20, cy: 100 },
];

export default function MiniFloorPlan({ facades, size = 96 }: MiniFloorPlanProps) {
  // Get facade directions that are selected
  const selectedDirections = new Set(facades.map(f => f.direction));

  // Determine which corners should be shown (between selected facades)
  const showCorners = facades.length >= 2;

  return (
    <div className="floor-plan-mini" style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.1))' }}>
      <svg viewBox="0 0 120 120" className="w-24 h-24" style={{ width: size, height: size }}>
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

        {/* Selected facades */}
        {facades.map((facade) => {
          const pos = DIRECTION_POSITIONS[facade.direction];
          if (!pos) return null;

          return (
            <line
              key={facade.id}
              x1={pos.x1}
              y1={pos.y1}
              x2={pos.x2}
              y2={pos.y2}
              stroke={facade.color}
              strokeWidth="5"
              strokeLinecap="round"
            />
          );
        })}

        {/* Corner circles (when multiple facades selected) */}
        {showCorners && CORNER_POSITIONS.map((corner) => {
          // Only show corner if adjacent facades are selected
          const adjacentDirections: Record<string, [FacadeDirection, FacadeDirection]> = {
            'NW': ['N', 'W'],
            'NE': ['N', 'E'],
            'SE': ['S', 'E'],
            'SW': ['S', 'W'],
          };
          const [dir1, dir2] = adjacentDirections[corner.direction];
          const hasAdjacent = selectedDirections.has(dir1) && selectedDirections.has(dir2);

          if (!hasAdjacent) return null;

          return (
            <circle
              key={corner.direction}
              cx={corner.cx}
              cy={corner.cy}
              r="6"
              fill={CORNER_COLOR}
            />
          );
        })}

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
            style={{ backgroundColor: facade.color }}
          />
          <span className="text-gray-600">
            {facade.name} ({facade.length_m}m)
          </span>
        </div>
      ))}
    </div>
  );
}
