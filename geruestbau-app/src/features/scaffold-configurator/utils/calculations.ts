/**
 * Scaffold Configurator - Calculation Utilities
 */

import type {
  ScaffoldFacade,
  ScaffoldSettings,
  WorkType,
  SVGDimensions,
} from '../types/scaffold.types';
import { SCAFFOLD_CONSTANTS } from '../types/scaffold.types';

/**
 * Calculate target height based on work type
 * FIX 27.01.2026: 'full' ersetzt durch 'roofer' (Spengler)
 *
 * @param baseHeight - Traufhöhe (base_height_m)
 * @param workType - Art der Arbeiten
 * @param firstHeight - Optional: Firsthöhe für Spengler (first_height_m)
 * @param isGiebel - Optional: Ist es eine Giebel-Fassade?
 * @param giebelHeight - Optional: Höhe des Giebel-Dreiecks
 */
export function calculateTargetHeight(
  baseHeight: number,
  workType: WorkType,
  firstHeight?: number,
  isGiebel?: boolean,
  giebelHeight?: number
): number {
  switch (workType) {
    case 'facade':
      return baseHeight; // Up to eaves (Traufe)
    case 'roof':
      return baseHeight + 1.0; // +1m fall protection (Absturzsicherung)
    case 'roofer':
      // Spengler: Gerüst bis First - 1m
      if (isGiebel && giebelHeight && giebelHeight > 0) {
        // Giebel-Fassade: Trapez-Form (base + giebel - 1m)
        return baseHeight + giebelHeight - 1.0;
      } else if (firstHeight && firstHeight > baseHeight) {
        // Trauf-Fassade: Rechteck bis First - 1m
        return firstHeight - 1.0;
      } else {
        // Fallback: baseHeight + 2m (geschätzte Giebelhöhe)
        return baseHeight + 2.0;
      }
    default:
      return baseHeight;
  }
}

/**
 * Calculate number of fields for a facade
 */
export function calculateFields(lengthM: number, fieldWidthM: number): number {
  return Math.ceil(lengthM / fieldWidthM);
}

/**
 * Calculate number of levels for a facade
 */
export function calculateLevels(targetHeightM: number, levelHeightM: number = SCAFFOLD_CONSTANTS.LEVEL_HEIGHT_M): number {
  return Math.ceil(targetHeightM / levelHeightM);
}

/**
 * Calculate scaffold area for a facade
 */
export function calculateFacadeArea(
  facade: ScaffoldFacade,
  settings: ScaffoldSettings
): number {
  const totalCells = facade.fields * facade.levels;
  const removedCells = facade.modifications.removed_cells.size;
  const activeCells = totalCells - removedCells;
  const cellArea = settings.field_width_m * settings.level_height_m;
  return activeCells * cellArea;
}

/**
 * Calculate corner material (posts and diagonals)
 */
export function calculateCornerMaterial(maxLevels: number): { posts: number; diagonals: number } {
  return {
    posts: SCAFFOLD_CONSTANTS.CORNER_POSTS,
    diagonals: maxLevels * SCAFFOLD_CONSTANTS.DIAGONALS_PER_LEVEL,
  };
}

/**
 * Estimate total weight based on scaffold area
 */
export function estimateWeight(areaM2: number): number {
  return Math.round(areaM2 * SCAFFOLD_CONSTANTS.KG_PER_M2);
}

/**
 * Calculate responsive SVG dimensions based on container width
 */
export function calculateSvgDimensions(
  containerWidth: number,
  fields: number,
  levels: number,
  showRoof: boolean = false
): SVGDimensions {
  const marginLeft = 45;
  const marginRight = 20;
  const availableWidth = containerWidth - marginLeft - marginRight;

  // Cell dimensions - responsive
  const cellWidth = Math.max(30, Math.min(50, availableWidth / fields));
  const cellHeight = Math.round(cellWidth * 0.6);

  // SVG dimensions
  const roofHeight = showRoof ? 35 : 0;
  const groundHeight = 30;
  const topPadding = 30;

  const svgWidth = marginLeft + (fields * cellWidth) + marginRight;
  const svgHeight = topPadding + roofHeight + (levels * cellHeight) + groundHeight + 20;

  const startX = marginLeft;
  const startY = svgHeight - groundHeight; // Ground level

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
}

/**
 * Format number with Swiss locale (apostrophe as thousand separator)
 */
export function formatNumber(num: number): string {
  return num.toLocaleString('de-CH');
}

/**
 * Format area with unit
 */
export function formatArea(areaM2: number): string {
  return `${formatNumber(Math.round(areaM2))} m²`;
}

/**
 * Format length with unit
 */
export function formatLength(lengthM: number, decimals: number = 1): string {
  return `${lengthM.toFixed(decimals)}m`;
}

/**
 * Format weight with unit
 */
export function formatWeight(weightKg: number): string {
  if (weightKg >= 1000) {
    return `~${(weightKg / 1000).toFixed(0)} Tonnen`;
  }
  return `~${formatNumber(weightKg)} kg`;
}

/**
 * Get work type display info
 * FIX 27.01.2026: 'full' ersetzt durch 'roofer' (Spengler)
 */
export function getWorkTypeInfo(workType: WorkType): { label: string; description: string; icon: string } {
  switch (workType) {
    case 'facade':
      return { label: 'Fassade', description: 'Bis Traufe', icon: 'building' };
    case 'roof':
      return { label: 'Dacharbeiten', description: '+1m Schutz', icon: 'home' };
    case 'roofer':
      return { label: 'Spengler', description: 'First -1m', icon: 'expand-alt' };
  }
}

/**
 * Get system display info
 */
export function getSystemInfo(system: 'layher_blitz' | 'layher_allround'): { label: string; fieldWidth: string } {
  switch (system) {
    case 'layher_blitz':
      return { label: 'Layher Blitz', fieldWidth: '2.57m Feld' };
    case 'layher_allround':
      return { label: 'Layher Allround', fieldWidth: '3.07m Feld' };
  }
}

/**
 * Get bay width display info
 */
export function getBayWidthInfo(width: 0.73 | 1.09): { label: string; code: string } {
  switch (width) {
    case 0.73:
      return { label: 'W09 (0.73m)', code: 'W09' };
    case 1.09:
      return { label: 'W13 (1.09m)', code: 'W13' };
  }
}

/**
 * Calculate cell key for removed_cells Set
 */
export function getCellKey(field: number, level: number): string {
  return `${field}-${level}`;
}

/**
 * Parse cell key back to field and level
 */
export function parseCellKey(key: string): { field: number; level: number } {
  const [field, level] = key.split('-').map(Number);
  return { field, level };
}
