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

// Terrain-Daten Types (swissALTI3D)
export interface TerrainData {
  terrain_height_m: number       // Absolute Höhe m ü.M.
  min_terrain_m?: number         // Minimale Terrain-Höhe um Gebäude
  max_terrain_m?: number         // Maximale Terrain-Höhe um Gebäude
  terrain_slope_m?: number       // Differenz (Hanglage)
}

// Dach-Daten Types (Option C - heuristisch berechnet)
export interface RoofData {
  roof_type: 'flachdach' | 'pultdach' | 'satteldach' | 'satteldach_mit_turm' | 'walmdach' | 'mansarddach' | 'kuppel' | 'unknown'
  roof_angle_deg: number | null    // Dachneigung in Grad
  roof_orientation?: string        // z.B. "O-W" oder "N-S"
  first_azimuth_deg?: number       // Ausrichtung des Firstes
  roof_area_m2?: number            // Geschätzte Dachfläche
  scaffolding_height_m?: number    // Gerüsthöhe für Dacharbeiten
  confidence: number               // 0-1, wie verlässlich die Berechnung
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
    terrain?: TerrainData  // Terrain-Höhe aus swissALTI3D
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
  // Dach-Daten (Option C - heuristisch berechnet)
  roof?: RoofData
  // Auto-Refresh Flags
  needs_height_refresh?: boolean
  height_refreshed?: boolean
  height_refresh_error?: string
  // Configuration (from API)
  configuration?: {
    work_type: string
    scaffold_type: string
  }
  // SmartBuildingService Daten (NEU)
  smart_building?: {
    building_name?: string
    building_type?: string
    architectural_style?: string
    complexity?: string
    zones_count?: number
    data_sources?: string[]
    overall_quality?: string
    research_confidence?: number
    warnings?: string[]
    errors?: string[]
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

export interface AccessPoint {
  id: string
  fassade_id: string
  position_percent: number
  grund?: string
}

export interface BuildingContext {
  egid: string
  adresse?: string
  building_name?: string  // Name des Gebäudes (z.B. "Bundeshaus", "Berner Münster")
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
  zugaenge: AccessPoint[]
  zugaenge_hinweise: string[]
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

// ============================================================================
// SmartBuildingService Types (NEU)
// ============================================================================

export type DataSource =
  | 'swisstopo_geocoding'
  | 'swisstopo_gwr'
  | 'swissbuildings3d'
  | 'swissalti3d'
  | 'geodienste_wfs'
  | 'claude_research'
  | 'claude_analysis'
  | 'calculated'
  | 'manual'
  | 'cache'

export type DataQuality = 'high' | 'medium' | 'low' | 'unknown'

export interface SmartTerrainProfile {
  reference_height_m: number
  min_height_m?: number
  max_height_m?: number
  slope_m?: number
  facade_heights?: Record<string, number>
  is_sloped: boolean
  slope_direction?: string
  requires_level_compensation: boolean
  max_compensation_m?: number
}

export interface SmartZoneInfo {
  id: string
  name: string
  zone_type: string
  traufhoehe_m?: number
  firsthoehe_m?: number
  gebaeudehoehe_m?: number
  fassaden_ids: string[]
  polygon_point_indices?: number[]
  beruesten: boolean
  sonderkonstruktion: boolean
  geruesthoehe_m?: number
  confidence: number
  source: DataSource
  notes?: string
}

export interface SmartAccessPoint {
  id: string
  fassade_id: string
  position_percent: number
  reason: string
  suva_compliant: boolean
  max_escape_distance_m?: number
}

export interface SmartBuildingSide {
  index?: number
  length_m: number
  direction: string
  angle_deg?: number
  start?: { x: number; y: number }
  end?: { x: number; y: number }
}

/**
 * SmartBuildingService API Response
 *
 * Einheitliches Datenmodell für alle Gebäudedaten.
 * Wird von /api/v1/smart-building/data zurückgegeben.
 */
export interface SmartBuildingData {
  // Identifikation
  egid?: string
  address_input?: string
  address_matched?: string
  lv95_e?: number
  lv95_n?: number

  // Gebäude-Identifikation (aus Claude-Recherche)
  building_name?: string
  building_type?: string
  architectural_style?: string
  construction_year?: number

  // GWR-Daten
  gwr_category?: string
  gwr_category_code?: number
  gwr_floors?: number
  gwr_area_m2?: number
  gwr_dwellings?: number

  // Geometrie
  polygon?: [number, number][]
  polygon_source?: DataSource
  polygon_simplified?: boolean
  sides?: SmartBuildingSide[]
  perimeter_m?: number
  footprint_area_m2?: number
  bbox_width_m?: number
  bbox_depth_m?: number

  // Höhendaten
  traufhoehe_m?: number
  firsthoehe_m?: number
  gebaeudehoehe_m?: number
  height_source?: DataSource
  height_quality?: DataQuality
  estimated_height_m?: number
  floors_estimated?: number

  // Terrain
  terrain?: SmartTerrainProfile

  // Dach
  roof_type?: string
  roof_angle_deg?: number
  roof_orientation?: string
  roof_area_m2?: number
  roof_confidence?: number

  // Zonen
  zones: SmartZoneInfo[]
  complexity: 'simple' | 'moderate' | 'complex'
  has_height_variations: boolean
  has_towers: boolean
  has_annexes: boolean
  has_courtyards: boolean

  // Zugänge
  access_points: SmartAccessPoint[]
  suva_compliant: boolean
  max_escape_distance_m?: number

  // Nachbarn (TODO)
  neighbors?: any[]
  has_blocking_neighbors: boolean

  // Meta
  data_sources: DataSource[]
  collection_timestamp?: string
  overall_quality: DataQuality
  research_confidence: number
  analysis_confidence: number
  warnings: string[]
  errors: string[]
}

/**
 * Konvertiert SmartBuildingData zu ScaffoldingData für Abwärtskompatibilität
 */
export function smartToScaffoldingData(smart: SmartBuildingData): ScaffoldingData {
  const activeHeight = smart.firsthoehe_m || smart.traufhoehe_m || smart.gebaeudehoehe_m || smart.estimated_height_m || 10

  return {
    address: {
      input: smart.address_input,
      matched: smart.address_matched || '',
      coordinates: {
        lv95_e: smart.lv95_e || 0,
        lv95_n: smart.lv95_n || 0,
      },
      terrain: smart.terrain ? {
        terrain_height_m: smart.terrain.reference_height_m,
        min_terrain_m: smart.terrain.min_height_m,
        max_terrain_m: smart.terrain.max_height_m,
        terrain_slope_m: smart.terrain.slope_m,
      } : undefined,
    },
    gwr_data: {
      egid: parseInt(smart.egid || '0') || 0,
      building_category: smart.gwr_category,
      construction_year: smart.construction_year,
      floors: smart.gwr_floors,
      area_m2_gwr: smart.gwr_area_m2,
    },
    building: {
      egid: parseInt(smart.egid || '0') || 0,
      footprint_area_m2: smart.footprint_area_m2 || smart.gwr_area_m2 || 0,
      bounding_box: {
        width_m: smart.bbox_width_m || 10,
        depth_m: smart.bbox_depth_m || 10,
      },
    },
    dimensions: {
      perimeter_m: smart.perimeter_m || 40,
      estimated_height_m: activeHeight,
      height_source: smart.height_source || 'unknown',
      floors: smart.gwr_floors || smart.floors_estimated || null,
      height_estimated_m: smart.estimated_height_m || null,
      height_estimated_source: smart.estimated_height_m ? 'Geschosse' : null,
      height_measured_m: smart.gebaeudehoehe_m || null,
      height_measured_source: smart.traufhoehe_m ? 'swissBUILDINGS3D' : null,
      traufhoehe_m: smart.traufhoehe_m || null,
      firsthoehe_m: smart.firsthoehe_m || null,
      gebaeudehoehe_m: smart.gebaeudehoehe_m || null,
    },
    scaffolding: {
      facade_length_total_m: smart.perimeter_m || 40,
      estimated_scaffold_area_m2: (smart.perimeter_m || 40) * activeHeight,
      number_of_sides: smart.sides?.length || 4,
      main_sides_count: smart.sides?.filter(s => (s.length_m || 0) > 3)?.length || 4,
    },
    sides: (smart.sides || []).map((s, i) => ({
      index: s.index ?? i,
      start: s.start || { x: 0, y: 0 },
      end: s.end || { x: 0, y: 0 },
      length_m: s.length_m || 0,
      direction: s.direction || '',
      angle_deg: s.angle_deg || 0,
      traufhoehe_m: smart.traufhoehe_m || null,
      firsthoehe_m: smart.firsthoehe_m || null,
      facade_area_m2: (s.length_m || 0) * activeHeight,
    })),
    polygon: {
      coordinates: smart.polygon || [],
      coordinate_system: 'LV95 (EPSG:2056)',
    },
    viewer_3d_url: smart.egid ? `https://3d.geo.admin.ch/#/embed?egid=${smart.egid}` : undefined,
    roof: smart.roof_type ? {
      roof_type: smart.roof_type as RoofData['roof_type'],
      roof_angle_deg: smart.roof_angle_deg || null,
      roof_orientation: smart.roof_orientation,
      roof_area_m2: smart.roof_area_m2,
      confidence: smart.roof_confidence || 0.5,
    } : undefined,
    configuration: {
      work_type: 'dacharbeiten',
      scaffold_type: 'arbeitsgeruest',
    },
    // SmartService-spezifische Daten
    smart_building: {
      building_name: smart.building_name,
      building_type: smart.building_type,
      architectural_style: smart.architectural_style,
      complexity: smart.complexity,
      zones_count: smart.zones?.length || 0,
      data_sources: smart.data_sources,
      overall_quality: smart.overall_quality,
      research_confidence: smart.research_confidence,
      warnings: smart.warnings,
      errors: smart.errors,
    },
  }
}

