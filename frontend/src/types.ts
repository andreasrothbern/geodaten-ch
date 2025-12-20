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
