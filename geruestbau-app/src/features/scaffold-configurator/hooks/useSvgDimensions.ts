/**
 * useSvgDimensions - Calculate responsive SVG dimensions for scaffold grid
 */

import { useMemo } from 'react';
import type { ScaffoldFacade, ScaffoldSettings, SVGDimensions } from '../types/scaffold.types';

interface UseSvgDimensionsOptions {
  containerWidth: number;
  facade: ScaffoldFacade;
  settings?: ScaffoldSettings; // Reserved for future use (e.g., field width adjustments)
  showRoof?: boolean;
}

export function useSvgDimensions({
  containerWidth,
  facade,
  showRoof = false,
}: UseSvgDimensionsOptions): SVGDimensions {
  return useMemo(() => {
    const marginLeft = 50; // Space for height markers
    const marginRight = 20;
    const marginTop = showRoof ? 60 : 30; // Extra space for roof
    const marginBottom = 50; // Space for width markers + ground

    const availableWidth = Math.max(200, containerWidth - marginLeft - marginRight);

    // Calculate cell dimensions based on available width
    const cellWidth = Math.max(25, Math.min(50, availableWidth / facade.fields));
    const cellHeight = Math.round(cellWidth * 0.7); // Aspect ratio ~1.4:1

    // Total grid dimensions
    const gridWidth = facade.fields * cellWidth;
    const gridHeight = facade.levels * cellHeight;

    // SVG dimensions
    const svgWidth = marginLeft + gridWidth + marginRight;
    const svgHeight = marginTop + gridHeight + marginBottom;

    // Starting position (bottom-left of grid)
    const startX = marginLeft;
    const startY = marginTop + gridHeight;

    return {
      cellWidth,
      cellHeight,
      svgWidth,
      svgHeight,
      startX,
      startY,
      marginLeft,
      marginRight,
    };
  }, [containerWidth, facade.fields, facade.levels, showRoof]);
}

/**
 * Calculate position for a specific cell
 */
export function getCellPosition(
  field: number,
  level: number,
  dims: SVGDimensions
): { x: number; y: number; width: number; height: number } {
  const padding = Math.max(1, dims.cellWidth * 0.04);
  return {
    x: dims.startX + field * dims.cellWidth + padding,
    y: dims.startY - (level + 1) * dims.cellHeight + padding,
    width: dims.cellWidth - padding * 2,
    height: dims.cellHeight - padding * 2,
  };
}

/**
 * Calculate height marker positions
 */
export function getHeightMarkers(
  levels: number,
  levelHeight: number,
  dims: SVGDimensions
): { y: number; label: string }[] {
  const markers: { y: number; label: string }[] = [];

  // Ground level
  markers.push({
    y: dims.startY,
    label: '±0.00',
  });

  // Each level
  for (let i = 1; i <= levels; i++) {
    markers.push({
      y: dims.startY - i * dims.cellHeight,
      label: `+${(i * levelHeight).toFixed(2)}`,
    });
  }

  return markers;
}

/**
 * Calculate width marker positions
 */
export function getWidthMarkers(
  fields: number,
  fieldWidth: number,
  dims: SVGDimensions
): { x: number; label: string }[] {
  const markers: { x: number; label: string }[] = [];

  for (let i = 0; i <= fields; i++) {
    markers.push({
      x: dims.startX + i * dims.cellWidth,
      label: (i * fieldWidth).toFixed(1),
    });
  }

  return markers;
}

export default useSvgDimensions;
