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

export interface ScaffoldConfiguration {
  project_id: string;
  created_at: string;
  updated_at: string;
  settings: ScaffoldSettings;
  elements: ScaffoldElement[];
  totals: ScaffoldTotals;
  // Building polygon for 3D visualization (LV95 coordinates)
  buildingPolygon?: [number, number][];
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
export type MainTab = 'overview' | 'editor' | '3d';
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

export const FACADE_COLORS: Record<FacadeDirection, string> = {
  'N': '#ef4444',  // red-500
  'NE': '#f43f5e', // rose-500
  'E': '#f43f5e',  // rose-500
  'SE': '#ec4899', // pink-500
  'S': '#ec4899',  // pink-500
  'SW': '#f97316', // orange-500
  'W': '#f97316',  // orange-500
  'NW': '#ef4444', // red-500
};

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
