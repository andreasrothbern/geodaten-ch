/**
 * ScaffoldGrid - Interactive SVG grid for scaffold editing
 */

import { useRef, useEffect, useState, useCallback } from 'react';
import type { ScaffoldFacade, ScaffoldSettings, EditorTool } from '../../types/scaffold.types';
import { useSvgDimensions, getCellPosition, getHeightMarkers, getWidthMarkers } from '../../hooks/useSvgDimensions';

interface ScaffoldGridProps {
  facade: ScaffoldFacade;
  settings: ScaffoldSettings;
  currentTool: EditorTool;
  onCellClick: (field: number, level: number) => void;
  onRowClick: (field: number) => void;
  onLevelClick: (level: number) => void;
  onLiftClick: (field: number) => void;
  onStairsClick: (field: number) => void;
}

export default function ScaffoldGrid({
  facade,
  settings,
  currentTool,
  onCellClick,
  onRowClick,
  onLevelClick,
  onLiftClick,
  onStairsClick,
}: ScaffoldGridProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(300);

  // Observe container width for responsive sizing
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Calculate SVG dimensions
  const showRoof = settings.work_type === 'roof' || settings.work_type === 'full';
  const dims = useSvgDimensions({
    containerWidth,
    facade,
    settings,
    showRoof,
  });

  // Height and width markers
  const heightMarkers = getHeightMarkers(facade.levels, settings.level_height_m, dims);
  const widthMarkers = getWidthMarkers(facade.fields, settings.field_width_m, dims);

  // Handle cell click based on current tool
  const handleCellClick = useCallback(
    (field: number, level: number) => {
      switch (currentTool) {
        case 'remove':
          onCellClick(field, level);
          break;
        case 'removeRow':
          onRowClick(field);
          break;
        case 'removeLevel':
          onLevelClick(level);
          break;
        case 'lift':
          onLiftClick(field);
          break;
        case 'stairs':
          onStairsClick(field);
          break;
        default:
          // Select tool - just show info
          break;
      }
    },
    [currentTool, onCellClick, onRowClick, onLevelClick, onLiftClick, onStairsClick]
  );

  // Render a single cell
  const renderCell = (field: number, level: number) => {
    const pos = getCellPosition(field, level, dims);
    const key = `${field}-${level}`;
    const isRemoved = facade.modifications.removed_cells.has(key);
    const hasLift = facade.modifications.lift_position === field;
    const hasStairs = facade.modifications.stairs_position === field;

    // Determine cell color (with fallback for old localStorage data)
    const facadeColor = facade.color || '#6B7280';
    let fill = facadeColor;
    let stroke = darkenColor(facadeColor, 30);
    let opacity = 0.9;

    if (isRemoved) {
      fill = '#fecaca';
      stroke = '#fca5a5';
      opacity = 0.4;
    } else if (hasLift) {
      // Cells in lift column get special coloring
      fill = '#fef3c7';
      stroke = '#f59e0b';
    } else if (hasStairs) {
      // Cells in stairs column get special coloring
      fill = '#dcfce7';
      stroke = '#22c55e';
    }

    return (
      <rect
        key={key}
        x={pos.x}
        y={pos.y}
        width={pos.width}
        height={pos.height}
        rx={2}
        fill={fill}
        stroke={stroke}
        strokeWidth={1}
        opacity={opacity}
        className="cursor-pointer hover:opacity-100 transition-opacity"
        onClick={() => handleCellClick(field, level)}
      />
    );
  };

  // Render all cells
  const renderCells = () => {
    const cells: JSX.Element[] = [];
    for (let level = 0; level < facade.levels; level++) {
      for (let field = 0; field < facade.fields; field++) {
        cells.push(renderCell(field, level));
      }
    }
    return cells;
  };

  // Render lift overlay
  const renderLiftOverlay = () => {
    if (facade.modifications.lift_position === null) return null;

    const field = facade.modifications.lift_position;
    const x = dims.startX + field * dims.cellWidth;
    const y = dims.startY - facade.levels * dims.cellHeight;
    const width = dims.cellWidth;
    const height = facade.levels * dims.cellHeight;

    return (
      <g className="lift-overlay">
        <rect
          x={x + 2}
          y={y + 2}
          width={width - 4}
          height={height - 4}
          fill="none"
          stroke="#f59e0b"
          strokeWidth={3}
          strokeDasharray="6 3"
          rx={4}
        />
        <rect
          x={x + width / 2 - 12}
          y={y + height / 2 - 12}
          width={24}
          height={24}
          fill="#f59e0b"
          rx={4}
        />
        <text
          x={x + width / 2}
          y={y + height / 2 + 5}
          textAnchor="middle"
          fill="white"
          fontSize={12}
          fontWeight="bold"
        >
          L
        </text>
      </g>
    );
  };

  // Render stairs overlay
  const renderStairsOverlay = () => {
    if (facade.modifications.stairs_position === null) return null;

    const field = facade.modifications.stairs_position;
    const x = dims.startX + field * dims.cellWidth;
    const y = dims.startY - facade.levels * dims.cellHeight;
    const width = dims.cellWidth;
    const height = facade.levels * dims.cellHeight;

    return (
      <g className="stairs-overlay">
        <rect
          x={x + 2}
          y={y + 2}
          width={width - 4}
          height={height - 4}
          fill="none"
          stroke="#22c55e"
          strokeWidth={3}
          strokeDasharray="6 3"
          rx={4}
        />
        <rect
          x={x + width / 2 - 12}
          y={y + height / 2 - 12}
          width={24}
          height={24}
          fill="#22c55e"
          rx={4}
        />
        <text
          x={x + width / 2}
          y={y + height / 2 + 5}
          textAnchor="middle"
          fill="white"
          fontSize={12}
          fontWeight="bold"
        >
          T
        </text>
      </g>
    );
  };

  // Render roof (triangular gable)
  const renderRoof = () => {
    if (!showRoof) return null;

    const roofHeight = settings.work_type === 'full' ? 40 : 20;
    const buildingTop = dims.startY - facade.levels * dims.cellHeight;
    const buildingLeft = dims.startX;
    const buildingRight = dims.startX + facade.fields * dims.cellWidth;
    const buildingCenter = (buildingLeft + buildingRight) / 2;

    return (
      <g className="roof">
        <polygon
          points={`
            ${buildingLeft},${buildingTop}
            ${buildingCenter},${buildingTop - roofHeight}
            ${buildingRight},${buildingTop}
          `}
          fill="url(#roofGradient)"
          stroke="#7c3aed"
          strokeWidth={2}
        />
      </g>
    );
  };

  // Render building outline
  const renderBuildingOutline = () => {
    const top = dims.startY - facade.levels * dims.cellHeight;
    const bottom = dims.startY;
    const left = dims.startX;
    const right = dims.startX + facade.fields * dims.cellWidth;

    return (
      <rect
        x={left}
        y={top}
        width={right - left}
        height={bottom - top}
        fill="none"
        stroke="#374151"
        strokeWidth={2}
      />
    );
  };

  // Render ground
  const renderGround = () => {
    return (
      <g className="ground">
        <line
          x1={dims.startX - 10}
          y1={dims.startY}
          x2={dims.startX + facade.fields * dims.cellWidth + 10}
          y2={dims.startY}
          stroke="#374151"
          strokeWidth={2}
        />
        <pattern id="groundHatch" patternUnits="userSpaceOnUse" width={8} height={8}>
          <path d="M0,8 L8,0" stroke="#666" strokeWidth={0.5} />
        </pattern>
        <rect
          x={dims.startX - 10}
          y={dims.startY}
          width={facade.fields * dims.cellWidth + 20}
          height={15}
          fill="url(#groundHatch)"
        />
      </g>
    );
  };

  // Render height markers
  const renderHeightMarkers = () => {
    return (
      <g className="height-markers">
        {heightMarkers.map((marker, idx) => (
          <g key={idx}>
            <line
              x1={dims.startX - 5}
              y1={marker.y}
              x2={dims.startX}
              y2={marker.y}
              stroke="#6b7280"
              strokeWidth={1}
            />
            <text
              x={dims.startX - 8}
              y={marker.y + 4}
              textAnchor="end"
              fill="#6b7280"
              fontSize={10}
            >
              {marker.label}
            </text>
          </g>
        ))}
        {/* Height axis line */}
        <line
          x1={dims.startX - 5}
          y1={dims.startY}
          x2={dims.startX - 5}
          y2={dims.startY - facade.levels * dims.cellHeight}
          stroke="#d1d5db"
          strokeWidth={1}
        />
      </g>
    );
  };

  // Render width markers
  const renderWidthMarkers = () => {
    const y = dims.startY + 25;
    return (
      <g className="width-markers">
        {widthMarkers.map((marker, idx) => (
          <g key={idx}>
            <line
              x1={marker.x}
              y1={dims.startY}
              x2={marker.x}
              y2={dims.startY + 5}
              stroke="#6b7280"
              strokeWidth={1}
            />
            <text
              x={marker.x}
              y={y}
              textAnchor="middle"
              fill="#6b7280"
              fontSize={10}
            >
              {marker.label}
            </text>
          </g>
        ))}
        {/* Width axis line */}
        <line
          x1={dims.startX}
          y1={dims.startY + 5}
          x2={dims.startX + facade.fields * dims.cellWidth}
          y2={dims.startY + 5}
          stroke="#d1d5db"
          strokeWidth={1}
        />
      </g>
    );
  };

  // Render slope indicator
  const renderSlopeIndicator = () => {
    if (facade.slope_percent <= 0) return null;

    const slopeHeight = (facade.slope_percent / 100) * facade.fields * dims.cellWidth;
    const right = dims.startX + facade.fields * dims.cellWidth;

    return (
      <g className="slope-indicator">
        <line
          x1={dims.startX}
          y1={dims.startY}
          x2={right}
          y2={dims.startY - slopeHeight}
          stroke="#f97316"
          strokeWidth={2}
          strokeDasharray="4 2"
        />
        <text
          x={right + 5}
          y={dims.startY - slopeHeight / 2}
          fill="#f97316"
          fontSize={9}
        >
          {facade.slope_percent.toFixed(1)}%
        </text>
      </g>
    );
  };

  return (
    <div ref={containerRef} className="scaffold-grid w-full overflow-hidden">
      <svg
        viewBox={`0 0 ${dims.svgWidth} ${dims.svgHeight}`}
        preserveAspectRatio="xMidYMid meet"
        className="w-full h-auto"
        style={{ minHeight: 200 }}
      >
        {/* Defs */}
        <defs>
          <linearGradient id="roofGradient" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#a78bfa" />
          </linearGradient>
          <pattern id="groundHatch" patternUnits="userSpaceOnUse" width={8} height={8}>
            <path d="M0,8 L8,0" stroke="#666" strokeWidth={0.5} />
          </pattern>
        </defs>

        {/* Background */}
        <rect x={0} y={0} width={dims.svgWidth} height={dims.svgHeight} fill="#f8fafc" />

        {/* Sky gradient for top area */}
        <rect
          x={dims.startX}
          y={0}
          width={facade.fields * dims.cellWidth}
          height={dims.startY - facade.levels * dims.cellHeight}
          fill="linear-gradient(to bottom, #e0f2fe, #f8fafc)"
        />

        {/* Render layers */}
        {renderGround()}
        {renderRoof()}
        {renderBuildingOutline()}
        {renderHeightMarkers()}
        {renderWidthMarkers()}
        {renderCells()}
        {renderLiftOverlay()}
        {renderStairsOverlay()}
        {renderSlopeIndicator()}

        {/* Facade name label */}
        <text
          x={dims.startX + (facade.fields * dims.cellWidth) / 2}
          y={dims.svgHeight - 5}
          textAnchor="middle"
          fill="#374151"
          fontSize={11}
          fontWeight="600"
        >
          {facade.name} ({facade.length_m.toFixed(1)}m)
        </text>
      </svg>
    </div>
  );
}

// Helper function to darken a color
function darkenColor(hex: string, percent: number): string {
  const num = parseInt(hex.replace('#', ''), 16);
  const amt = Math.round(2.55 * percent);
  const R = Math.max(0, (num >> 16) - amt);
  const G = Math.max(0, ((num >> 8) & 0x00ff) - amt);
  const B = Math.max(0, (num & 0x0000ff) - amt);
  return `#${(0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1)}`;
}
