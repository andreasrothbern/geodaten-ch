export type ProjectStatus =
  | 'draft'
  | 'captured'
  | 'enriched'
  | 'reviewed'
  | 'planned'
  | 'quoted'
  | 'commissioned'

export interface Project {
  id: string
  name: string
  address: string
  status: ProjectStatus
  egid?: string
  client_name?: string
  client_contact?: string
  deadline?: string
  description?: string
  building_data?: BuildingData
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  address: string
  client_name?: string
  client_contact?: string
  deadline?: string
  description?: string
}

export interface BuildingData {
  geocode?: {
    coordinates: { e: number; n: number }
    lat: number
    lon: number
  }
  gwr?: {
    egid: string
    address: string
    floors: number
    category: string
    year_built?: number
  }
  polygon?: {
    type: string
    coordinates: number[][][]
  }
  heights?: {
    traufhoehe_m?: number
    firsthoehe_m?: number
    gebaeudehoehe_m?: number
    source: string
  }
  enriched_at?: string
}

export interface ScaffoldZone {
  name: string
  zone_type: string
  height_m: number
  width_m: number
  fields: number
  levels: number
  requires_special: boolean
}

export interface ScaffoldConfig {
  project_id: string
  system: string
  bay_width: string
  zones: ScaffoldZone[]
  total_area_m2: number
  total_anchors: number
  access_points: number
}
