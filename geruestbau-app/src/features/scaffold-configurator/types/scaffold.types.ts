/**
 * Scaffold Configurator - TypeScript Types
 * Based on SCAFFOLD_CONFIGURATOR_SPEC.md
 */

// ============ INPUT TYPES (from Facade Selection) ============

export interface ProjectInput {
  project_id: string;
  building: {
    egid: string;
    address: string;
    name: string;
    polygon: [number, number][]; // LV95 coordinates
    trauf_height_m: number;
    first_height_m: number;
  };
  selected_facades: SelectedFacade[];
}

export interface SelectedFacade {
  id: string;
  direction: FacadeDirection;
  length_m: number;
  height_m: number;
  slope_percent: number;
  photo_url?: string;
  detected_features?: DetectedFeature[];
  // Coordinates for 3D positioning (LV95)
  start_point?: [number, number];
  end_point?: [number, number];
}

export type FacadeDirection = 'N' | 'NE' | 'E' | 'SE' | 'S' | 'SW' | 'W' | 'NW';

export interface DetectedFeature {
  type: 'window' | 'door' | 'balcony' | 'obstacle' | 'recess';
  position: { x: number; y: number };
  size: { width: number; height: number };
}

// ============ SCAFFOLD CONFIGURATION ============

export type WorkType = 'facade' | 'roof' | 'full';
export type ScaffoldSystem = 'layher_blitz' | 'layher_allround';
export type FieldWidth = 2.57 | 3.07;
export type BayWidth = 0.73 | 1.09;

export interface ScaffoldSettings {
  work_type: WorkType;
  system: ScaffoldSystem;
  field_width_m: FieldWidth;
  level_height_m: number; // Always 2.0
  bay_width_m: BayWidth;
  safety_net: boolean;
  weather_cover: boolean;
}

// Roof data from backend calculation
export interface RoofData {
  roof_type: string;        // flachdach, satteldach, walmdach, pultdach, etc.
  roof_angle_deg: number;
  roof_orientation: string;
  trauf_to_first_m: number;
  scaffolding_height_m: number;
  confidence: number;
  // Dachüberstand (aus Sonnendach.ch oder Standard 40cm)
  roof_overhang_m?: number; // Default: 0.4m
  // Traufhöhe für 3D-Visualisierung (Gebäudehöhe bis Dachansatz)
  traufhoehe_m?: number;
}

// Zone data for complex buildings (from known_buildings or Claude API)
export interface BuildingZone {
  id: string;
  name: string;
  zone_type: 'hauptgebaeude' | 'anbau' | 'turm' | 'kuppel' | 'arkade' | 'vordach' | 'treppenhaus' | 'garage';
  position?: 'vorne' | 'zentral' | 'hinten' | 'flankierend';
  traufhoehe_m?: number;
  firsthoehe_m?: number;
  beruesten: boolean;
  sonderkonstruktion: boolean;
}

export interface ScaffoldConfiguration {
  project_id: string;
  created_at: string;
  updated_at: string;
  settings: ScaffoldSettings;
  elements: ScaffoldElement[];
  totals: ScaffoldTotals;
  // Building polygon (ORIGINAL from swissBUILDINGS3D, LV95 coordinates)
  // Note: Simplified polygon is now calculated on-the-fly by the Backend API
  buildingPolygon?: [number, number][];
  // Roof data for 3D visualization
  roof?: RoofData;
  // Zones for complex buildings (Bundeshaus, Münster, etc.)
  zones?: BuildingZone[];
  // Building metadata
  building_name?: string;
  complexity?: 'simple' | 'moderate' | 'complex';
}

export interface ScaffoldTotals {
  scaffold_area_m2: number;
  facade_count: number;
  corner_count: number;
  max_height_m: number;
  perimeter_m: number;
  estimated_weight_kg: number;
}

// ============ SCAFFOLD ELEMENTS ============

export type ScaffoldElement = ScaffoldFacade | ScaffoldCorner;

export interface ScaffoldFacade {
  type: 'facade';
  id: string;
  facade_ref: string;
  name: string;
  direction: FacadeDirection;
  length_m: number;
  target_height_m: number;
  slope_percent: number;
  fields: number;
  levels: number;
  color: string;
  enabled: boolean; // Whether this facade is included in scaffold
  modifications: FacadeModifications;
  // Coordinates for 3D positioning (LV95)
  start_point?: [number, number];
  end_point?: [number, number];
}

export interface FacadeModifications {
  removed_cells: Set<string>; // "field-level" keys, e.g., "3-5"
  lift_position: number | null;
  stairs_position: number | null;
}

export interface ScaffoldCorner {
  type: 'corner';
  id: string;
  name: string;
  connects: [string, string]; // IDs of connected facades
  corner_posts: number;
  diagonals: number;
  enabled: boolean;
}

// ============ OUTPUT TYPES ============

export interface ScaffoldOutput {
  configuration: ScaffoldConfiguration;
  element_details: ElementDetail[];
  geometry: ScaffoldGeometry;
}

export interface ElementDetail {
  element_id: string;
  type: 'facade' | 'corner';
  active_fields: number;
  removed_fields: number;
  area_m2: number;
  has_lift: boolean;
  has_stairs: boolean;
}

export interface ScaffoldGeometry {
  building_outline: [number, number][];
  scaffold_segments: ScaffoldSegment[];
  roof_outline?: [number, number][];
}

export interface ScaffoldSegment {
  facade_id: string;
  start_point: [number, number, number]; // x, y, z
  end_point: [number, number, number];
  height_m: number;
  fields: number;
  levels: number;
}

// ============ UI STATE ============

export type EditorTool = 'select' | 'remove' | 'removeRow' | 'removeLevel' | 'lift' | 'stairs';
export type MainTab = 'facade' | 'overview' | 'editor' | '3d';
export type View3D = 'isometric' | 'north' | 'east' | 'south' | 'west' | 'top';

export interface SVGDimensions {
  cellWidth: number;
  cellHeight: number;
  svgWidth: number;
  svgHeight: number;
  startX: number;
  startY: number;
  marginLeft: number;
  marginRight: number;
}

// ============ FACADE COLORS ============

// Intuitive color scheme: N=blue (cold), S=red (warm/sun), W=yellow (sunset), E=violet
export const FACADE_COLORS: Record<string, string> = {
  'N': '#3B82F6',   // Blue (north = cold)
  'NE': '#6366F1',  // Indigo
  'E': '#8B5CF6',   // Violet (east = sunrise)
  'SE': '#EC4899',  // Pink
  'S': '#EF4444',   // Red (south = warm/sun)
  'SW': '#F97316',  // Orange
  'W': '#EAB308',   // Yellow (west = sunset)
  'NW': '#22C55E',  // Green
  // German direction codes (aliases)
  'NO': '#6366F1',  // Indigo (NordOst)
  'O': '#8B5CF6',   // Violet (Ost)
  'SO': '#EC4899',  // Pink (SüdOst)
};

// Helper to get facade color by direction (with fallback)
export function getFacadeColor(direction: string, fallback = '#666666'): string {
  return FACADE_COLORS[direction] || fallback;
}

export const CORNER_COLOR = '#f59e0b'; // amber-500

// ============ CONSTANTS ============

export const SCAFFOLD_CONSTANTS = {
  LEVEL_HEIGHT_M: 2.0,
  BLITZ_FIELD_WIDTH_M: 2.57,
  ALLROUND_FIELD_WIDTH_M: 3.07,
  BAY_WIDTH_W09_M: 0.73,
  BAY_WIDTH_W13_M: 1.09,
  KG_PER_M2: 28, // Weight estimation
  CORNER_POSTS: 4,
  DIAGONALS_PER_LEVEL: 2,
} as const;

// ============ HELPER TYPES ============

export interface CarouselState {
  currentIndex: number;
  elements: ScaffoldElement[];
}

export interface VisibleElements {
  prev: ScaffoldElement;
  current: ScaffoldElement;
  next: ScaffoldElement;
}
