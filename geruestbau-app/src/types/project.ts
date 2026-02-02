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

// =============================================================================
// DEPRECATED 18.01.2026: Geodata → Verwende GeruestbauData stattdessen!
// =============================================================================
// Probleme mit Geodata:
// - Flache Struktur (87 Felder durcheinander)
// - 4 verschiedene Koordinaten-Formate
// - Keine Fassaden-Höhen pro Fassade
// - Deprecated Felder (facade_z_min, facade_z_max)
//
// Migration: Verwende GeruestbauData mit:
// - facades: GeruestbauFassade[] (Höhen pro Fassade!)
// - building: GeruestbauBuilding (saubere Struktur)
// - terrain: GeruestbauTerrain (Hanglage-Daten)
// =============================================================================

/**
 * @deprecated Verwende GeruestbauData stattdessen!
 * Siehe Zeile 522 für die neue Struktur.
 */
export interface Geodata {
  egid?: string  // Optional - kann bei Geocoding-Fehler fehlen
  address?: string
  polygon?: number[][]  // [[e, n], ...] - Original aus swissBUILDINGS3D
  polygon_simplified?: number[][]  // On-the-fly vereinfacht für Gerüstplanung
  gebaeudehoehe_m?: number
  area_m2?: number
  footprint_area_m2?: number  // Grundfläche aus Polygon
  perimeter_m?: number
  center_e?: number
  center_n?: number
  coord_e?: number
  coord_n?: number
  coordinates?: {  // Alternative Koordinaten-Struktur
    lv95_e: number
    lv95_n: number
  }
  fetched_at?: string
  // Fassaden-Daten (aus swissBUILDINGS3D)
  sides?: Array<{
    index: number
    start: { x: number; y: number }
    end: { x: number; y: number }
    start_point: number[]
    end_point: number[]
    length_m: number
    azimuth_deg: number
    angle_deg: number
    normal_azimuth_deg: number
    direction: string
  }>
  // GWR-Daten
  gwr_floors?: number
  gwr_area_m2?: number
  gwr_category?: string
  gwr_category_code?: number
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
  // NEU 12.01.2026 22:45 - 3D-Layer Daten (swissBUILDINGS3D Roof/Wall)
  has_3d_layers?: boolean
  has_roof_geometry?: boolean
  roof_dach_min_m?: number  // Traufhöhe absolut (m ü.M.)
  roof_dach_max_m?: number  // Firsthöhe absolut (m ü.M.)
  roof_gebaeudeeinheit?: string
  // NEU 14.01.2026: Echte 3D-Dachgeometrie als Koordinaten-Array
  // Format: Array von Polygonen, jedes Polygon ist Array von [E, N, Z] Punkten
  roof_geometry_coords?: number[][][]
  // Dach-Analyse Daten
  roof_type?: string  // flachdach, satteldach, walmdach, etc.
  roof_orientation?: string  // 'N-S' oder 'O-W' (First-Verlauf)
  roof_angle_deg?: number  // Dachneigung in Grad
  // NEU 14.01.2026 (T4) - Fassaden-Höhen aus Wall-Layer
  /** @deprecated Use building_walls instead for geometric matching */
  facade_z_min?: Record<string, number>  // {"N": 541.0, "E": 543.5, ...}
  /** @deprecated Use building_walls instead for geometric matching */
  facade_z_max?: Record<string, number>  // {"N": 550.0, "E": 552.0, ...}
  /** @deprecated Use building_walls instead for geometric matching */
  facade_heights_source?: 'wall_layer' | 'terrain_sampled' | 'global' | 'building_global'
  // NEU 15.01.2026 BUG-024: Building Walls direkt aus DB (DB-Naming!)
  // FIX: Volle 3D-Geometrie, ALLE Polygone (nicht nur erstes)
  building_walls?: BuildingWall[]
  // NEU 15.01.2026 23:30: Building Roofs direkt aus DB (DB-Naming!)
  // Volle 3D-Dach-Geometrie für echtes Dach-Rendering im 3D-View
  building_roofs?: BuildingRoof[]
}

// NEU 15.01.2026 BUG-024: Building Wall aus building_walls Tabelle
// Felder exakt wie in der DB - konsistentes Naming durchgehend!
// Für geometrisches Matching mit vereinfachten Fassaden verwendet
export interface BuildingWall {
  gebaeudeeinheit: string       // PRIMARY KEY aus swissBUILDINGS3D
  egid: number | null           // Gebäude-Referenz
  z_min: number | null          // Terrain-Höhe (m ü.M.) - Bodenniveau der Wand
  z_max: number | null          // Trauf-Höhe (m ü.M.) - Oberkante der Wand
  geometry_type: 'Polygon' | 'MultiPolygon' | 'LineString' | null
  // FIX 19.01.2026: Umbenennung coords_3d → geometry (konsistent mit DB geometry_wkb)
  // Volle 3D-Koordinaten aus geometry_wkb konvertiert:
  // - Polygon: [[[x,y,z], ...], [[hole], ...]]  (Array of rings)
  // - MultiPolygon: [[[[x,y,z], ...]], [...]]   (Array of polygons, each with rings)
  // - LineString: [[x,y,z], ...]
  geometry: number[][][] | number[][][][] | number[][] | null
}

// NEU 15.01.2026 23:30: Building Roof aus building_roofs Tabelle
// Felder exakt wie in der DB - konsistentes Naming durchgehend!
// Für echte 3D-Dach-Darstellung im 3D-View
export interface BuildingRoof {
  gebaeudeeinheit: string       // PRIMARY KEY aus swissBUILDINGS3D
  egid: number | null           // Gebäude-Referenz
  dach_min: number | null       // Trauf-Höhe (m ü.M.) - Unterkante Dach
  dach_max: number | null       // First-Höhe (m ü.M.) - Oberkante Dach
  roof_form: string | null      // Dachform: satteldach, flachdach, walmdach, etc.
  roof_angle_deg: number | null // Dachneigung in Grad
  roof_orientation: string | null  // First-Richtung: 'N-S', 'O-W', 'NW-SO', etc.
  geometry_type: 'Polygon' | 'MultiPolygon' | 'LineString' | null
  // FIX 19.01.2026: Umbenennung coords_3d → geometry (konsistent mit DB geometry_wkb)
  // Volle 3D-Koordinaten aus geometry_wkb konvertiert:
  // - Polygon: [[[x,y,z], ...], [[hole], ...]]  (Array of rings)
  // - MultiPolygon: [[[[x,y,z], ...]], [...]]   (Array of polygons, each with rings)
  // - LineString: [[x,y,z], ...]
  geometry: number[][][] | number[][][][] | number[][] | null
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
// FIX 16.01.2026 17:00: traufhoehe_m/firsthoehe_m ENTFERNT!
// NEU 18.01.2026: Volle 3D-Daten für Multi-Building SSE Support
export interface BuildingEntry {
  egid: string
  address: string
  coordinates?: {
    lv95_e: number
    lv95_n: number
  }
  egid_source?: string
  // NEU 18.01.2026: Volle 3D-Daten aus SSE-Stream
  polygon?: number[][]
  sides?: Array<{
    index: number
    start: { x: number; y: number }
    end: { x: number; y: number }
    start_point: number[]
    end_point: number[]
    length_m: number
    azimuth_deg: number
    angle_deg: number
    normal_azimuth_deg: number
    direction: string
  }>
  roof_dach_min_m?: number
  roof_dach_max_m?: number
  gebaeudehoehe_m?: number
  terrain?: {
    reference_height_m: number
    min_height_m: number
    max_height_m: number
    slope_m?: number  // FIX 31.01.2026: Optional - wird im Frontend aus building_walls berechnet
    slope_class?: 'eben' | 'leicht' | 'mittel' | 'stark'  // FIX 31.01.2026: Optional
    facade_z_min?: Record<string, number>
    facade_z_max?: Record<string, number>
    facade_heights_source?: 'wall_layer' | 'terrain_sampled' | 'global'  // FIX 31.01.2026: 'global' wie SSE
  }
  zones?: Array<{
    id: string
    name: string
    zone_type: string
    traufhoehe_m: number | null
    firsthoehe_m: number | null
    beruesten: boolean
  }>
  has_3d_layers?: boolean
}

// Projekt-Overrides (manuelle Anpassungen)
// FIX 16.01.2026 17:00: traufhoehe_m/firsthoehe_m ENTFERNT!
export interface ProjectOverrides {
  polygon?: number[][]
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
// NEU 18.01.2026: geruestbaudata hinzugefügt für Single/Multi-Building Support
export interface ProjectCreate {
  name: string
  address: string
  egid?: string
  buildings?: BuildingEntry[]  // Multi-Building Support
  // NEU: Kombinierte Gebäudedaten (bei Multi-Building: das Union-Polygon)
  geruestbaudata?: GeruestbauData
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

// NEU 01.02.2026: Erweiterte Foto-Analyse
export interface GpsData {
  lat: number
  lon: number
  altitude_m?: number
  lv95_e?: number
  lv95_n?: number
  compass_direction?: number
  compass_direction_text?: string
}

export interface BuildingAnalysis {
  floors_count?: number
  height_estimate_m?: number
  roof_type?: string  // flachdach, satteldach, walmdach, pultdach
  roof_angle_deg?: number
  facade_material?: string
  facade_direction?: string
  visible_address?: string
  obstacles?: string[]
  windows_pattern?: string
  building_condition?: string
  neighboring_buildings?: string
  special_features?: string[]
}

export interface SketchAnalysis {
  sketch_type?: string  // grundriss, ansicht, schnitt, detail
  work_type?: string  // fassade, spengler, dach, komplett
  dimensions_found?: Record<string, number>
  notes_text?: string
  address_found?: string
  address_required?: boolean
  scale?: string
}

// NEU 01.02.2026: Terrain-/Umgebungs-Analyse aus Foto
export interface TerrainAnalysis {
  // Terrain/Hanglage
  slope_estimate?: string  // eben, leicht, mittel, stark
  slope_direction?: string  // N, S, E, W, bergauf, bergab
  ground_type?: string  // asphalt, kies, rasen, erde, pflaster

  // Zufahrt
  access_type?: string  // strasse, weg, eingeschraenkt, nicht_sichtbar
  access_width?: string  // lkw_moeglich, lieferwagen, nur_fussgaenger

  // Umgebung
  neighboring_distance?: string  // angrenzend, 2-5m, >5m, freistehend
  trees_nearby?: boolean
  power_lines?: boolean
  street_furniture?: string[]  // laterne, hydrant, parkplatz

  // Gerüst-Hindernisse
  balconies_count?: number
  awnings_count?: number
  bay_windows?: boolean  // Erker
  overhangs?: string[]  // dachvorsprung, vordach
  other_obstacles?: string[]  // sonnenstoren, klimaanlage

  // Notizen
  scaffold_notes?: string
}

export interface OcrExtractionResult {
  success: boolean
  data?: ExtractedProjectData
  confidence: number
  raw_text?: string
  error?: string
  source_id?: string

  // NEU 01.02.2026: Smart Photo Analyzer
  image_type?: 'building_photo' | 'document' | 'sketch' | 'technical_plan' | 'mixed' | 'unknown'
  gps_data?: GpsData
  photo_timestamp?: string
  building_analysis?: BuildingAnalysis
  sketch_analysis?: SketchAnalysis

  // Pre-loaded 3D-Daten (bei GPS-Koordinaten) - LEGACY
  preloaded_egid?: string
  preloaded_building_name?: string
  preloaded_address?: string
  preloaded_traufhoehe_m?: number
  preloaded_firsthoehe_m?: number
  preloaded_roof_type?: string
  preloaded_polygon?: number[][]

  // NEU 01.02.2026: GWR-Daten via identify_buildings()
  suggested_egid?: string
  suggested_address?: string
  suggested_street?: string
  suggested_house_number?: string
  suggested_postal_code?: string
  suggested_city?: string
  suggested_floors?: number
  suggested_construction_year?: number
  suggested_building_category?: string

  // NEU 01.02.2026: Terrain-/Umgebungs-Analyse
  terrain_analysis?: TerrainAnalysis

  // NEU 02.02.2026: Alle Gebäude-Kandidaten im GPS-Radius für User-Auswahl
  nearby_buildings?: Array<{
    egid: string | null
    address: string
    street?: string
    house_number?: string
    postal_code?: number
    city?: string
    floors?: number
    distance_m?: number
  }>
}

// =============================================================================
// NEU 16.01.2026 10:00: GeruestbauData - Strukturierte Gebäudedaten
// =============================================================================
// Ersetzt das flache Geodata Interface mit klarer hierarchischer Struktur.
// SmartBuildingService liefert Originaldaten, geruestbau-app entscheidet Verwendung.

/**
 * Gebäude-Grunddaten (Identifikation + Geometrie)
 * NEU 18.01.2026: Erweitert um Anzeige-Felder (name, has_3d_layers, etc.)
 */
export interface GeruestbauBuilding {
  egid: string
  address: string
  polygon: number[][]  // [[e, n], ...] - Original aus swissBUILDINGS3D
  polygon_simplified?: number[][]  // Vereinfacht für Gerüstplanung
  center_e: number
  center_n: number
  perimeter_m: number
  area_m2: number

  // NEU 18.01.2026: Anzeige-Felder
  name?: string  // Gebäudename (z.B. "Bundeshaus", "Berner Münster")
  has_3d_layers?: boolean  // Ob 3D-Layer (Wall, Roof) vorhanden sind

  // Dach-Rohdaten (m ü.M.) - für Höhenberechnung
  roof_dach_min_m?: number  // Traufhöhe absolut (aus building_roofs)
  roof_dach_max_m?: number  // Firsthöhe absolut (aus building_roofs)
}

/**
 * Höhendaten mit Quellenangabe
 * FIX 18.01.2026: traufhoehe_m/firsthoehe_m wieder hinzugefügt (optional, für Legacy-Projekte)
 * Korrekte Höhen berechnen: roof_dach_min_m - terrain_z_min
 * Siehe STREAMING_ARCHITECTURE.md L.11
 */
export interface GeruestbauHeights {
  gebaeudehoehe_m?: number  // Gebäudehöhe relativ (m)
  terrain_height_m?: number  // Geländehöhe (m ü.M.)
  source?: 'swissBUILDINGS3D' | 'gwr_estimated' | 'manual'
  // NEU 18.01.2026: Legacy-Felder für gespeicherte Projekte
  traufhoehe_m?: number  // Traufhöhe relativ (m) - für Fallback
  firsthoehe_m?: number  // Firsthöhe relativ (m) - für Fallback
}

/**
 * Terrain-/Hanglage-Daten
 */
export interface GeruestbauTerrain {
  height_m: number  // Zentrum-Höhe (m ü.M.)
  min_m: number  // Niedrigster Punkt am Polygon
  max_m: number  // Höchster Punkt am Polygon
  slope_m: number  // Höhendifferenz
  slope_class: 'eben' | 'leicht' | 'mittel' | 'stark'
  requires_level_compensation: boolean
}

/**
 * ASTRA Strassen-/Zugangsdaten (optional, geplant)
 */
export interface GeruestbauAstra {
  nearest_road_m: number
  road_type: string
  access_points: AccessPoint[]
}

// =============================================================================
// NEU 18.01.2026: GeruestbauFassade - Fassade mit Höhen pro Fassade
// =============================================================================
// Beste Genauigkeit: Terrain-Höhe am Fassaden-Startpunkt (swissALTI3D)
// Ermöglicht korrekte Gerüsthöhen-Berechnung bei Hanglagen

/**
 * Fassade mit allen Höhendaten für präzise Gerüstplanung
 *
 * Höhen-Berechnung:
 * - terrain_z_min: Terrain-Höhe am Startpunkt (m ü.M.) - von swissALTI3D
 * - terrain_z_max: Terrain-Höhe am Endpunkt (m ü.M.) - von swissALTI3D
 * - wall_z_max: Traufhöhe absolut (m ü.M.) - von building_roofs.dach_min
 * - height_m: Gerüsthöhe = wall_z_max - min(terrain_z_min, terrain_z_max)
 *
 * Bei Hanglage variiert terrain_z_min/max pro Fassade → unterschiedliche Gerüsthöhen!
 */
export interface GeruestbauFassade {
  // Identifikation
  index: number
  direction: string  // N, NE, E, SE, S, SW, W, NW

  // Geometrie (LV95 Koordinaten)
  start_point: [number, number]  // [E, N]
  end_point: [number, number]    // [E, N]
  length_m: number
  azimuth_deg: number  // 0=Nord, 90=Ost, 180=Süd, 270=West

  // HÖHEN PRO FASSADE (swissALTI3D Terrain-Sampling)
  terrain_z_min: number    // Terrain am Startpunkt (m ü.M.)
  terrain_z_max: number    // Terrain am Endpunkt (m ü.M.)
  wall_z_max: number       // Traufhöhe absolut (m ü.M.) - aus building_roofs.dach_min

  // BERECHNETE WERTE
  height_m: number         // Gerüsthöhe = wall_z_max - min(terrain_z_min, terrain_z_max)
  slope_m: number          // Terrain-Gefälle entlang Fassade = |terrain_z_max - terrain_z_min|

  // Quelle der Höhendaten
  // - wall_layer: Aus 3D-Layer (höchste Präzision)
  // - terrain_sampled: Aus swissALTI3D pro Fassade (gute Präzision)
  // - global / building_global: Fallback (gleiche Höhe für alle)
  height_source: 'wall_layer' | 'terrain_sampled' | 'global' | 'building_global'

  // Status (für Gerüstplanung)
  is_blocked?: boolean     // Durch Nachbargebäude blockiert
  blocked_by_egid?: string // EGID des blockierenden Gebäudes
}

/**
 * Datenqualitäts-Metadaten
 */
export type GeruestbauDataQuality = 'complete' | 'partial' | 'minimal'

// =============================================================================
// NEU 18.01.2026: GeruestbauCombined - Kombinierte Daten für Multi-Building
// =============================================================================
// Bei Multi-Building-Projekten (z.B. "Knospenweg 1-3") werden alle Gebäude
// als EIN Objekt behandelt. Das kombinierte Polygon enthält nur die ÄUSSEREN
// Fassaden (innere Wände zwischen Gebäuden sind eliminiert).

/**
 * Kombinierte Gebäudedaten für Multi-Building Projekte
 *
 * Anwendungsfall: "Knospenweg 1-3" (2 Reihenhäuser)
 * - Einzeln: 8 Fassaden (je 4 pro Gebäude)
 * - Kombiniert: 4 Fassaden (nur Aussenkanten, innere Wand eliminiert)
 *
 * Algorithmus:
 * 1. unary_union(polygon1, polygon2, ...) → kombiniertes Polygon
 * 2. _calculate_sides(combined) → nur Aussenkanten
 * 3. Terrain-Sampling für jede kombinierte Fassade
 */
export interface GeruestbauCombined {
  // Kombiniertes Polygon (Union aller Gebäude)
  polygon: number[][]              // [[E, N], ...] - Aussen-Kontur
  polygon_simplified?: number[][]  // Vereinfacht für Anzeige

  // Kombinierte ÄUSSERE Fassaden (mit Höhen pro Fassade!)
  facades: GeruestbauFassade[]

  // Statistiken
  building_count: number           // Anzahl Gebäude im Verbund
  egids: string[]                  // Liste aller EGIDs
  total_area_m2: number            // Summierte Grundfläche
  total_perimeter_m: number        // Umfang des kombinierten Polygons

  // Höhen-Zusammenfassung (für Übersicht)
  min_terrain_m: number            // Niedrigstes Terrain aller Fassaden
  max_terrain_m: number            // Höchstes Terrain aller Fassaden
  avg_traufhoehe_m: number         // Durchschnittliche Traufhöhe
  max_firsthoehe_m: number         // Höchste Firsthöhe

  // Hanglage-Info
  slope_m: number                  // max_terrain - min_terrain
  slope_class: 'eben' | 'leicht' | 'mittel' | 'stark'
  requires_level_compensation: boolean  // slope_m > 0.5
}

/**
 * GeruestbauData - Hauptinterface für strukturierte Gebäudedaten
 *
 * NEU 18.01.2026: Erweitert um `facades` mit Höhen pro Fassade
 *
 * Verwendung:
 * - SmartBuildingService liefert diese Struktur
 * - Wird im Projekt gespeichert (geruestbau.db)
 * - Frontend lädt aus Cache wenn Projekt geöffnet wird
 *
 * Datenfluss:
 * 1. Backend: SmartBuildingService sammelt alle Daten
 * 2. Backend: Terrain-Sampling pro Fassade (swissALTI3D)
 * 3. API: /api/v1/geruestbau/... liefert GeruestbauData
 * 4. Frontend: Zeigt Fassaden mit individuellen Höhen an
 */
export interface GeruestbauData {
  // Gebäude-Grunddaten
  building: GeruestbauBuilding

  // NEU 18.01.2026: FASSADEN MIT HÖHEN PRO FASSADE (primäre Quelle!)
  // Jede Fassade hat eigene terrain_z_min/max für korrekte Gerüsthöhen bei Hanglage
  facades: GeruestbauFassade[]

  // 3D-Layer Daten (swissBUILDINGS3D)
  walls: BuildingWall[]
  roofs: BuildingRoof[]

  // Terrain-/Hanglage-Daten (Zusammenfassung)
  terrain: GeruestbauTerrain

  // Zonen (bei komplexen Gebäuden)
  zones: ZoneInfo[]

  // ASTRA Strassen-/Zugangsdaten (optional, geplant)
  astra?: GeruestbauAstra

  // Metadaten
  fetched_at: string  // ISO 8601 Timestamp
  data_quality: GeruestbauDataQuality
  missing_data?: string[]  // Felder die nicht geladen werden konnten

  // NEU 18.01.2026: Anzeige-Metadaten
  complexity?: 'simple' | 'moderate' | 'complex'  // Gebäude-Komplexität
  research_source?: 'known_buildings' | 'claude_api' | 'cache' | 'auto'  // Datenquelle

  // @deprecated - Use facades[].height_m instead
  heights?: GeruestbauHeights
}

/**
 * Projekt mit GeruestbauData (neu)
 * Ersetzt ProjectWithGeodata für neue Projekte
 *
 * NEU 16.01.2026: buildings_data als Record<EGID, GeruestbauData>
 * NEU 18.01.2026: combined für Multi-Building (kombiniertes Polygon + Fassaden)
 *
 * Single-Building: Ein Eintrag in buildings_data, kein combined
 * Multi-Building: Mehrere Einträge + combined mit äusseren Fassaden
 */
export interface ProjectWithGeruestbaudata extends Project {
  /**
   * Gebäudedaten indexiert nach EGID.
   * Ermöglicht Single- und Multi-Building Projekte mit gleicher Struktur.
   * @example
   * // Single-Building:
   * buildings_data: { "1234567": { building: {...}, facades: [...], ... } }
   * // Multi-Building:
   * buildings_data: {
   *   "1234567": { building: {...}, facades: [...], ... },
   *   "1234568": { building: {...}, facades: [...], ... }
   * }
   */
  buildings_data?: Record<string, GeruestbauData>

  /**
   * NEU 18.01.2026: Kombinierte Daten für Multi-Building Projekte
   * Enthält das Union-Polygon und nur die ÄUSSEREN Fassaden.
   *
   * @example
   * // "Knospenweg 1-3" (2 Reihenhäuser):
   * combined: {
   *   polygon: [...],           // Union-Polygon
   *   facades: [...],           // 4 äussere Fassaden (nicht 8!)
   *   building_count: 2,
   *   egids: ["1234567", "1234568"],
   *   ...
   * }
   */
  combined?: GeruestbauCombined

  /** @deprecated Use buildings_data instead */
  geruestbaudata?: GeruestbauData
  /** @deprecated Use buildings_data instead */
  geodata?: Geodata
}

// =============================================================================
// Hilfsfunktionen für buildings_data Zugriff (NEU 16.01.2026)
// =============================================================================

/**
 * Holt Gebäudedaten für eine bestimmte EGID.
 * Immer explizit mit EGID arbeiten - alle Gebäude sind gleichwertig.
 */
export function getBuildingData(
  project: ProjectWithGeruestbaudata,
  egid: string
): GeruestbauData | null {
  if (project.buildings_data && project.buildings_data[egid]) {
    return project.buildings_data[egid]
  }
  // Fallback: Legacy prüfen
  if (project.geruestbaudata?.building.egid === egid) {
    return project.geruestbaudata
  }
  return null
}

/**
 * Holt alle EGIDs im Projekt.
 */
export function getBuildingEgids(project: ProjectWithGeruestbaudata): string[] {
  if (project.buildings_data) {
    return Object.keys(project.buildings_data)
  }
  // Fallback: Legacy
  if (project.geruestbaudata?.building.egid) {
    return [project.geruestbaudata.building.egid]
  }
  // Fallback: buildings Array
  if (project.buildings?.length) {
    return project.buildings.map(b => b.egid)
  }
  return []
}

/**
 * Iteriert über alle Gebäude im Projekt.
 * Gibt Tupel von [egid, data] zurück.
 */
export function forEachBuilding(
  project: ProjectWithGeruestbaudata,
  callback: (egid: string, data: GeruestbauData) => void
): void {
  if (project.buildings_data) {
    Object.entries(project.buildings_data).forEach(([egid, data]) => {
      callback(egid, data)
    })
  } else if (project.geruestbaudata?.building.egid) {
    callback(project.geruestbaudata.building.egid, project.geruestbaudata)
  }
}

/**
 * Anzahl Gebäude im Projekt.
 */
export function getBuildingCount(project: ProjectWithGeruestbaudata): number {
  if (project.buildings_data) {
    return Object.keys(project.buildings_data).length
  }
  if (project.geruestbaudata) {
    return 1
  }
  return project.buildings?.length ?? 0
}

/**
 * Prüft ob das Projekt Multi-Building ist (mehr als ein Gebäude).
 */
export function isMultiBuilding(project: ProjectWithGeruestbaudata): boolean {
  return getBuildingCount(project) > 1
}

// =============================================================================
// Konvertierungs-Hilfsfunktionen (Rückwärtskompatibilität)
// =============================================================================

/**
 * Hilfsfunktion: Konvertiert GeruestbauData zu flachem Geodata-Format
 * Für Rückwärtskompatibilität mit bestehendem Frontend-Code
 * NEU 16.01.2026
 * FIX 18.01.2026: Konvertiere facades → sides + facade_z_min/max
 */
export function convertGeruestbaudataToGeodata(data: GeruestbauData): Geodata {
  // FIX 18.01.2026: facades[] kann leer oder undefined sein bei Legacy-Daten
  const facades = data.facades ?? []

  // Konvertiere facades → sides (altes Format)
  const sides = facades.map(f => ({
    index: f.index,
    start: { x: f.start_point[0], y: f.start_point[1] },
    end: { x: f.end_point[0], y: f.end_point[1] },
    start_point: f.start_point,
    end_point: f.end_point,
    length_m: f.length_m,
    azimuth_deg: f.azimuth_deg,
    angle_deg: f.azimuth_deg,
    normal_azimuth_deg: (f.azimuth_deg + 90) % 360,
    direction: f.direction,
  }))

  // Konvertiere facades → facade_z_min/max (gruppiert nach direction)
  const facadeZMin: Record<string, number> = {}
  const facadeZMax: Record<string, number> = {}
  for (const f of facades) {
    facadeZMin[f.direction] = f.terrain_z_min
    facadeZMax[f.direction] = f.wall_z_max
  }

  // FIX 18.01.2026: Rohdaten für Höhenberechnung extrahieren
  // Priorität: roofs[].dach_min > heights.traufhoehe_m + terrain.min_m > facades[].height_m
  const firstRoof = data.roofs?.[0]
  const terrainMin = data.terrain?.min_m ?? data.terrain?.height_m ?? 0

  // roof_dach_min_m: Traufhöhe absolut (m ü.M.)
  // FIX: null zu undefined konvertieren (BuildingRoof.dach_min ist number | null)
  let roofDachMin: number | undefined = firstRoof?.dach_min ?? undefined
  if (roofDachMin === undefined && data.heights?.traufhoehe_m) {
    // Fallback: Relative Traufhöhe + Terrain = Absolute Höhe
    roofDachMin = terrainMin + data.heights.traufhoehe_m
  }

  // roof_dach_max_m: Firsthöhe absolut (m ü.M.)
  let roofDachMax: number | undefined = firstRoof?.dach_max ?? undefined
  if (roofDachMax === undefined && data.heights?.firsthoehe_m) {
    roofDachMax = terrainMin + data.heights.firsthoehe_m
  }

  // gebaeudehoehe_m: Relative Höhe (für Fallbacks)
  const gebaeudehoehe = data.heights?.gebaeudehoehe_m
    ?? data.heights?.traufhoehe_m  // FIX: traufhoehe als Fallback
    ?? facades[0]?.height_m
    ?? 0

  return {
    egid: data.building.egid,
    address: data.building.address,
    polygon: data.building.polygon,
    polygon_simplified: data.building.polygon_simplified,
    center_e: data.building.center_e,
    center_n: data.building.center_n,
    coord_e: data.building.center_e,
    coord_n: data.building.center_n,
    perimeter_m: data.building.perimeter_m,
    area_m2: data.building.area_m2,
    footprint_area_m2: data.building.area_m2,
    // Sides (altes Format)
    sides: sides,
    // Heights - FIX 18.01.2026: Korrekte Rohdaten für extractHeights()
    gebaeudehoehe_m: gebaeudehoehe,
    roof_dach_min_m: roofDachMin,  // NEU: Für extractHeights()
    roof_dach_max_m: roofDachMax,  // NEU: Für extractHeights()
    // Facade heights (altes Format)
    facade_z_min: facadeZMin,
    facade_z_max: facadeZMax,
    facade_heights_source: facades[0]?.height_source || 'building_global',
    // Terrain
    terrain_height_m: data.terrain?.height_m ?? terrainMin,
    slope_m: data.terrain?.slope_m,
    slope_class: data.terrain?.slope_class,
    // 3D-Layer
    building_walls: data.walls,
    building_roofs: data.roofs,
    has_3d_layers: data.walls?.length > 0,
    // Zones
    zones: data.zones,
    // Metadata
    fetched_at: data.fetched_at,
  }
}

/**
 * Hilfsfunktion: Konvertiert Geodata zu GeruestbauData
 * Für Migration bestehender Projekte
 * FIX 16.01.2026 17:00: traufhoehe_m/firsthoehe_m ENTFERNT!
 * NEU 18.01.2026: facades[] aus sides[] konvertieren
 */
export function convertGeodataToGeruestbaudata(geodata: Geodata): GeruestbauData | null {
  if (!geodata.egid || !geodata.polygon) {
    return null
  }

  // NEU 18.01.2026: Konvertiere sides → facades mit Höhen pro Fassade
  const facades: GeruestbauFassade[] = (geodata.sides || []).map((side, idx) => {
    const direction = side.direction || 'N'
    // Hole Terrain-Höhen aus facade_z_min/max wenn vorhanden
    const terrainZMin = geodata.facade_z_min?.[direction] ?? geodata.terrain_height_m ?? 0
    const terrainZMax = geodata.facade_z_max?.[direction] ?? terrainZMin
    // wall_z_max = Traufhöhe (roof_dach_min_m) oder geschätzt
    const wallZMax = geodata.roof_dach_min_m ?? (terrainZMin + (geodata.gebaeudehoehe_m || 10))

    return {
      index: side.index ?? idx,
      direction: direction,
      start_point: side.start_point as [number, number] || [side.start?.x || 0, side.start?.y || 0],
      end_point: side.end_point as [number, number] || [side.end?.x || 0, side.end?.y || 0],
      length_m: side.length_m || 0,
      azimuth_deg: side.azimuth_deg || 0,
      terrain_z_min: terrainZMin,
      terrain_z_max: terrainZMax,
      wall_z_max: wallZMax,
      height_m: wallZMax - Math.min(terrainZMin, terrainZMax),
      slope_m: Math.abs(terrainZMax - terrainZMin),
      height_source: geodata.facade_heights_source || 'building_global',
    }
  })

  return {
    building: {
      egid: geodata.egid,
      address: geodata.address || '',
      polygon: geodata.polygon,
      polygon_simplified: geodata.polygon_simplified,
      center_e: geodata.center_e || geodata.coord_e || 0,
      center_n: geodata.center_n || geodata.coord_n || 0,
      perimeter_m: geodata.perimeter_m || 0,
      area_m2: geodata.area_m2 || geodata.footprint_area_m2 || 0,
    },
    facades: facades,
    heights: {
      // FIX 16.01.2026 17:00: traufhoehe_m/firsthoehe_m ENTFERNT!
      // Frontend berechnet: roof_dach_min_m - terrain_z_min
      gebaeudehoehe_m: geodata.gebaeudehoehe_m || 0,
      terrain_height_m: geodata.terrain_height_m || 0,
      source: 'swissBUILDINGS3D',
    },
    walls: geodata.building_walls || [],
    roofs: geodata.building_roofs || [],
    terrain: {
      height_m: geodata.terrain_height_m || 0,
      min_m: geodata.terrain_height_m || 0,
      max_m: (geodata.terrain_height_m || 0) + (geodata.slope_m || 0),
      slope_m: geodata.slope_m || 0,
      slope_class: geodata.slope_class || 'eben',
      requires_level_compensation: (geodata.slope_m || 0) > 0.5,
    },
    zones: geodata.zones || [],
    astra: undefined,  // ASTRA-Daten noch nicht implementiert
    fetched_at: geodata.fetched_at || new Date().toISOString(),
    data_quality: geodata.building_walls?.length ? 'complete' : 'partial',
    missing_data: [],
  }
}
