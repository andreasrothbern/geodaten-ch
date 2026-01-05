export type ProjectStatus =
  | 'draft'
  | 'captured'
  | 'enriched'
  | 'reviewed'
  | 'planned'
  | 'configured'
  | 'quoted'
  | 'commissioned'
  | 'completed'

// Geodaten aus SmartBuildingService (gecacht in building_contexts.db)
export interface Geodata {
  egid: string
  address?: string
  polygon?: [number, number][]  // [[e, n], ...] - Original aus swissBUILDINGS3D
  polygon_simplified?: [number, number][]  // On-the-fly vereinfacht für Gerüstplanung
  traufhoehe_m?: number
  firsthoehe_m?: number
  gebaeudehoehe_m?: number
  area_m2?: number
  perimeter_m?: number
  center_e?: number
  center_n?: number
  coord_e?: number
  coord_n?: number
  fetched_at?: string
  // Enrichment-Daten (aus building_environment)
  terrain_height_m?: number
  slope_m?: number
  slope_class?: 'eben' | 'leicht' | 'mittel' | 'stark'
  // Zonen (aus building_contexts - komplexe Gebäude)
  zones?: ZoneInfo[]
  // Datenherkunft (für UI-Feedback)
  research_source?: 'known_buildings' | 'claude_api' | 'cache' | 'auto' | 'unknown'
  building_name?: string
  complexity?: 'simple' | 'moderate' | 'complex'
}

// Zone eines Gebäudes (aus building_contexts.db)
export interface ZoneInfo {
  id: string
  name: string
  zone_type: 'hauptgebaeude' | 'anbau' | 'turm' | 'kuppel' | 'arkade' | 'vordach' | 'treppenhaus' | 'garage'
  position?: 'vorne' | 'zentral' | 'hinten' | 'flankierend'  // Position für 3D-Darstellung
  traufhoehe_m?: number
  firsthoehe_m?: number
  gebaeudehoehe_m?: number
  beruesten: boolean
  sonderkonstruktion: boolean
  confidence: number
}

// Einzelnes Gebäude in Multi-Building Projekt
export interface BuildingEntry {
  egid: string
  address: string
  traufhoehe_m?: number
  firsthoehe_m?: number
  coordinates?: {
    lv95_e: number
    lv95_n: number
  }
  egid_source?: string
}

// Projekt-Overrides (manuelle Anpassungen)
export interface ProjectOverrides {
  polygon?: number[][]
  traufhoehe_m?: number
  firsthoehe_m?: number
  simplify_epsilon?: number
  simplify_angle_tolerance?: number
}

// Gerüst-Einstellungen
export interface ScaffoldSettings {
  system: string  // layher_blitz, layher_allround
  work_type: string  // facade, roof, full
  level_height_m: number
  field_length_ratio: number  // 0-100 Slider
}

// Fassaden-Öffnung (Fenster, Tür)
export interface FacadeOpening {
  type: string  // window, door
  floor: number
  position?: string  // left, center, right
  width_m?: number
  height_m?: number
  count: number
}

// Fassaden-Hindernis
export interface FacadeObstacle {
  type: string  // balcony, tree, awning, sign
  floor?: number
  position?: string
  depth_m?: number
  distance_m?: number
}

// Fassaden-Konfiguration
export interface FacadeConfig {
  index: number
  direction: string  // N, NE, E, SE, S, SW, W, NW
  length_m: number
  height_m: number
  slope_percent: number
  selected: boolean
  has_lift: boolean
  has_stairs: boolean
  openings: FacadeOpening[]
  obstacles: FacadeObstacle[]
  photos: string[]  // Photo IDs
  enrichment_source?: string
}

// Ecken-Konfiguration
export interface CornerConfig {
  index: number
  type: string  // standard, innen, aussen
}

// Zugangspunkt
export interface AccessPoint {
  facade_index: number
  position_m: number
  type: string  // lift, stairs
  width_m: number
}

// Komplette Gerüst-Konfiguration (JSON in projects.config)
export interface ScaffoldConfig {
  overrides: ProjectOverrides
  settings: ScaffoldSettings
  facades: FacadeConfig[]
  corners: CornerConfig[]
  access_points: AccessPoint[]
}

// Projekt (Basis)
export interface Project {
  id: string
  name: string
  address: string
  egid?: string
  buildings?: BuildingEntry[]  // Multi-Building Support
  status: ProjectStatus
  config?: ScaffoldConfig
  client_name?: string
  client_contact?: string
  deadline?: string
  created_at: string
  updated_at: string
}

// Projekt mit Geodaten (von GET /projects/{id})
export interface ProjectWithGeodata extends Project {
  geodata?: Geodata
}

// Projekt erstellen
export interface ProjectCreate {
  name: string
  address: string
  egid?: string
  buildings?: BuildingEntry[]  // Multi-Building Support
  client_name?: string
  client_contact?: string
  deadline?: string
}

// Projekt aktualisieren
export interface ProjectUpdate {
  name?: string
  status?: ProjectStatus
  client_name?: string
  client_contact?: string
  deadline?: string
  config?: ScaffoldConfig
}

// Photo Enrichment Status
export type EnrichmentStatus = 'pending' | 'processing' | 'completed' | 'failed'

// Enrichment-Daten (Claude Vision Analyse)
export interface EnrichmentData {
  model: string
  model_version?: string
  analyzed_at?: string
  confidence: number
  openings: FacadeOpening[]
  obstacles: FacadeObstacle[]
  scaffolding_hints: string[]
}

// Projekt-Foto
export interface ProjectPhoto {
  id: string
  project_id: string
  filename: string
  file_path: string
  file_size_bytes?: number
  mime_type?: string
  taken_at?: string
  uploaded_at: string
  facade_index?: number
  view_direction?: string
  enrichment_status: EnrichmentStatus
  enrichment_at?: string
  enrichment_data?: EnrichmentData
}

// OCR-Extraktions-Ergebnis vom Backend (für Import)
export interface ExtractedProjectData {
  project_name?: string
  address?: string
  client_name?: string
  client_contact?: string
  tender_number?: string
  submission_deadline?: string
  project_start?: string
  project_end?: string
  estimated_area_m2?: number
  requirements?: string[]
  simap_id?: string
  procedure?: 'open' | 'selective' | 'invitation' | 'negotiated'
  description?: string  // Optional description from manual entry
}

export interface OcrExtractionResult {
  success: boolean
  data?: ExtractedProjectData
  confidence: number
  raw_text?: string
  error?: string
  source_id?: string
}
