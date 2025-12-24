// API Types für Frontend

export interface Coordinates {
  lv95_e: number
  lv95_n: number
  wgs84_lon?: number
  wgs84_lat?: number
}

export interface GeocodingResult {
  input_address: string
  matched_address: string
  confidence: number
  coordinates: Coordinates
}

export interface BuildingInfo {
  egid: number
  address: string
  street?: string
  house_number?: string
  postal_code?: number
  city?: string
  canton?: string
  construction_year?: number
  building_category?: string
  building_category_code?: number
  building_status?: string
  floors?: number
  apartments?: number
  area_m2?: number
  heating_type?: string
  heating_energy?: string
  hot_water_energy?: string
  coordinates?: Coordinates
  geometry?: object
  last_update?: string
}

export interface LookupResult {
  address: GeocodingResult
  buildings: BuildingInfo[]
  buildings_count: number
}

export interface AddressSearchResult {
  label: string
  street?: string
  house_number?: string
  postal_code?: string
  city?: string
  canton?: string
  coordinates: Coordinates
  feature_id?: string
}

// Gerüstbau-Daten Types
export interface ScaffoldingSide {
  index: number
  start: { x: number; y: number }
  end: { x: number; y: number }
  length_m: number
  direction: string
  angle_deg: number
  // Höhen pro Fassade (initial: globale Höhe, später: individuelle Höhenzonen)
  traufhoehe_m: number | null
  firsthoehe_m: number | null
  facade_area_m2: number | null
}

export interface ScaffoldingData {
  address: {
    input?: string
    matched: string
    coordinates: {
      lv95_e: number
      lv95_n: number
    }
  }
  gwr_data: {
    egid: number
    building_category?: string
    construction_year?: number
    floors?: number
    area_m2_gwr?: number
  }
  building: {
    egid: number
    footprint_area_m2: number
    bounding_box: {
      width_m: number
      depth_m: number
    }
  }
  dimensions: {
    perimeter_m: number
    estimated_height_m: number | null
    height_source: string
    floors: number | null
    // Separate Höhenangaben
    height_estimated_m: number | null
    height_estimated_source: string | null
    height_measured_m: number | null
    height_measured_source: string | null
    // Detaillierte Höhen aus swissBUILDINGS3D
    traufhoehe_m: number | null      // Dachhöhe min - Terrain (Eave)
    firsthoehe_m: number | null      // Dachhöhe max - Terrain (Ridge)
    gebaeudehoehe_m: number | null   // Gesamthöhe (Building)
    heights_estimated?: boolean      // True wenn Trauf/First aus Gesamthöhe geschätzt
  }
  scaffolding: {
    facade_length_total_m: number
    estimated_scaffold_area_m2: number | null
    number_of_sides: number
    main_sides_count: number
  }
  sides: ScaffoldingSide[]
  polygon: {
    coordinates: [number, number][]
    coordinate_system: string
  }
  viewer_3d_url?: string
  // Auto-Refresh Flags
  needs_height_refresh?: boolean
  height_refreshed?: boolean
  height_refresh_error?: string
  // Configuration (from API)
  configuration?: {
    work_type: string
    scaffold_type: string
  }
}

// Scaffolding Configuration Types
export type WorkType = 'dacharbeiten' | 'fassadenarbeiten'
export type ScaffoldType = 'arbeitsgeruest' | 'schutzgeruest' | 'fanggeruest'
export type ScaffoldingSystem = 'blitz70' | 'allround' | 'combined'
export type WidthClass = 'W06' | 'W09' | 'W12'

export interface ScaffoldingConfiguration {
  selectedFacades: number[]
  workType: WorkType
  scaffoldType: ScaffoldType
  systemId: ScaffoldingSystem
  widthClass: WidthClass
  liftEnabled: boolean
  liftPosition?: number
}

export interface FacadeSelection {
  index: number
  selected: boolean
  length_m: number
  direction: string
  area_m2: number
}

// Building Context Types (Höhenzonen für komplexe Gebäude)
export type ZoneType =
  | 'hauptgebaeude'
  | 'anbau'
  | 'turm'
  | 'kuppel'
  | 'arkade'
  | 'vordach'
  | 'treppenhaus'
  | 'garage'
  | 'unknown'

export type ComplexityLevel = 'simple' | 'moderate' | 'complex'
export type ContextSource = 'auto' | 'claude' | 'manual'

export interface BuildingZone {
  id: string
  name: string
  type: ZoneType
  polygon_point_indices?: number[]
  sub_polygon?: [number, number][]
  traufhoehe_m?: number
  firsthoehe_m?: number
  gebaeudehoehe_m: number
  terrain_hoehe_m?: number
  terrain_min_m?: number
  terrain_max_m?: number
  fassaden_ids: string[]
  beruesten: boolean
  sonderkonstruktion: boolean
  confidence: number
  notes?: string
}

export interface BuildingContext {
  egid: string
  adresse?: string
  zones: BuildingZone[]
  zone_adjacency?: Record<string, string[]>
  complexity: ComplexityLevel
  has_height_variations: boolean
  has_setbacks: boolean
  has_towers: boolean
  has_annexes: boolean
  has_special_features: boolean
  terrain_slope_percent?: number
  terrain_aspect?: string
  source: ContextSource
  confidence: number
  validated_by_user: boolean
  reasoning?: string
  created_at: string
  updated_at: string
}

export interface BuildingContextResponse {
  status: 'found' | 'created' | 'not_found' | 'error'
  context?: BuildingContext
  needs_validation: boolean
  message?: string
}

export interface AnalyzeResponse {
  status: 'success' | 'error' | 'already_exists'
  context?: BuildingContext
  cost_estimate_usd?: number
  message?: string
}
