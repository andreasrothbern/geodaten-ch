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
}
