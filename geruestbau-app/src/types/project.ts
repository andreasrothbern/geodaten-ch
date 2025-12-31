export type ProjectStatus =
  | 'draft'
  | 'captured'
  | 'enriched'
  | 'reviewed'
  | 'planned'
  | 'quoted'
  | 'commissioned'

// Tender/Ausschreibungs-Daten (aus PDF, Foto, simap.ch)
export interface TenderData {
  tender_number?: string        // Ausschreibungs-Nr.
  submission_deadline?: string  // Eingabefrist
  project_start?: string        // Projektstart
  project_end?: string          // Projektende
  is_urgent?: boolean           // Dringend
  requires_special?: boolean    // Sonderkonstruktion erforderlich
  estimated_area_m2?: number    // Geschätzte Gerüstfläche
  source?: 'pdf' | 'photo' | 'simap' | 'manual'  // Erfassungsmethode
  raw_text?: string             // Original-Text aus OCR
  confidence?: number           // OCR-Konfidenz (0-1)
}

// Gebäudedaten aus geodaten-ch API
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

// Vollständiges Projekt
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
  tender_data?: TenderData
  created_at: string
  updated_at: string
}

// Projekt erstellen (Input)
export interface ProjectCreate {
  name: string
  address: string
  client_name?: string
  client_contact?: string
  deadline?: string
  description?: string
  tender_data?: TenderData
}

// Gerüst-Zonen
export interface ScaffoldZone {
  name: string
  zone_type: string
  height_m: number
  width_m: number
  fields: number
  levels: number
  requires_special: boolean
}

// Gerüst-Konfiguration
export interface ScaffoldConfig {
  project_id: string
  system: string
  bay_width: string
  zones: ScaffoldZone[]
  total_area_m2: number
  total_anchors: number
  access_points: number
}

// Extrahierte Projektdaten (von PDF, URL oder manueller Eingabe)
export interface ExtractedProjectData {
  project_name?: string
  address?: string
  client_name?: string
  client_contact?: string
  description?: string
  tender_number?: string
  submission_deadline?: string
  project_start?: string
  project_end?: string
  estimated_area_m2?: number
  requirements?: string[]
  // simap.ch spezifische Daten
  simap_id?: string
  procedure?: 'open' | 'selective' | 'invitation' | 'negotiated'
}

// OCR-Extraktions-Ergebnis vom Backend
export interface OcrExtractionResult {
  success: boolean
  data?: ExtractedProjectData
  confidence: number
  raw_text?: string
  error?: string
  source_id?: string  // z.B. simap.ch Projekt-ID
}
