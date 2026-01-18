/**
 * Polygon Union Utilities für Multi-Building Projekte
 * NEU 18.01.2026
 *
 * Vereinigt mehrere Gebäude-Polygone zu einem kombinierten Polygon
 * und extrahiert nur die äußeren Fassaden (Zwischenwände eliminiert).
 */

import * as turf from '@turf/turf'
import type { Feature, Polygon, MultiPolygon, Position } from 'geojson'
import type { GeruestbauData, GeruestbauFassade, GeruestbauCombined } from '../types/project'

/**
 * Berechnet das Union-Polygon aus mehreren Gebäuden
 * und gibt die kombinierten Daten zurück.
 *
 * @example
 * const buildings = [buildingData1, buildingData2, buildingData3]
 * const combined = combineBuildings(buildings)
 * // combined.polygon = Union-Polygon
 * // combined.facades = Nur äußere Fassaden (Zwischenwände eliminiert)
 */
export function combineBuildings(buildings: GeruestbauData[]): GeruestbauCombined | null {
  if (!buildings || buildings.length === 0) {
    console.warn('[combineBuildings] Keine Gebäude übergeben')
    return null
  }

  // Bei nur einem Gebäude: Direkt zurückgeben (kein Union nötig)
  if (buildings.length === 1) {
    const b = buildings[0]
    const slopeM = b.terrain?.slope_m ?? 0
    return {
      polygon: b.building.polygon as number[][],
      polygon_simplified: b.building.polygon_simplified,
      facades: b.facades ?? [],
      building_count: 1,
      egids: [b.building.egid],
      total_area_m2: b.building.area_m2,
      total_perimeter_m: b.building.perimeter_m,
      min_terrain_m: b.terrain?.min_m ?? 0,
      max_terrain_m: b.terrain?.max_m ?? 0,
      avg_traufhoehe_m: b.heights?.traufhoehe_m ?? b.facades?.[0]?.height_m ?? 0,
      max_firsthoehe_m: b.heights?.firsthoehe_m ?? 0,
      slope_m: slopeM,
      slope_class: b.terrain?.slope_class ?? 'eben',
      requires_level_compensation: b.terrain?.requires_level_compensation ?? false,
    }
  }

  try {
    // Konvertiere alle Polygone zu Turf Features
    const polygons = buildings
      .map(b => {
        const coords = b.building.polygon as number[][]
        if (!coords || coords.length < 3) return null

        // Schließe Polygon falls nicht geschlossen
        const closed = [...coords]
        if (closed[0][0] !== closed[closed.length - 1][0] ||
            closed[0][1] !== closed[closed.length - 1][1]) {
          closed.push(closed[0])
        }

        return turf.polygon([closed])
      })
      .filter((p): p is Feature<Polygon> => p !== null)

    if (polygons.length === 0) {
      console.warn('[combineBuildings] Keine gültigen Polygone')
      return null
    }

    // Union aller Polygone berechnen
    let unionPolygon: Feature<Polygon> = polygons[0]
    for (let i = 1; i < polygons.length; i++) {
      const result = turf.union(turf.featureCollection([unionPolygon, polygons[i]]))
      if (result && result.geometry.type === 'Polygon') {
        unionPolygon = result as Feature<Polygon>
      } else if (result && result.geometry.type === 'MultiPolygon') {
        // Falls Gebäude nicht zusammenhängen: Verwende das größte Polygon
        console.warn('[combineBuildings] MultiPolygon entstanden - Gebäude hängen nicht zusammen')
        const multiPoly = result.geometry as MultiPolygon
        const largest = multiPoly.coordinates.reduce(
          (acc: Position[][], coords: Position[][]) =>
            turf.area(turf.polygon(coords)) > turf.area(turf.polygon(acc)) ? coords : acc
        )
        unionPolygon = turf.polygon(largest)
      }
    }

    // Koordinaten extrahieren (ohne schließenden Punkt)
    const unionCoords = unionPolygon.geometry.coordinates[0]
    const polygon = unionCoords.slice(0, -1) as number[][]

    // Fassaden aus dem Union-Polygon berechnen
    const facades = calculateFacadesFromPolygon(polygon, buildings)

    // Statistiken berechnen
    const egids = buildings.map(b => b.building.egid)
    const totalArea = buildings.reduce((sum, b) => sum + b.building.area_m2, 0)
    const unionPerimeter = turf.length(turf.lineString([...polygon, polygon[0]]), { units: 'meters' })

    // Terrain-Statistiken aus allen Gebäuden
    const allTerrainMin = buildings.map(b => b.terrain?.min_m ?? Infinity).filter(v => v !== Infinity)
    const allTerrainMax = buildings.map(b => b.terrain?.max_m ?? -Infinity).filter(v => v !== -Infinity)
    const minTerrain = allTerrainMin.length > 0 ? Math.min(...allTerrainMin) : 0
    const maxTerrain = allTerrainMax.length > 0 ? Math.max(...allTerrainMax) : 0

    // Höhen-Statistiken
    const allTrauf = buildings.map(b => b.heights?.traufhoehe_m ?? b.facades?.[0]?.height_m ?? 0).filter(v => v > 0)
    const allFirst = buildings.map(b => b.heights?.firsthoehe_m ?? 0).filter(v => v > 0)
    const avgTrauf = allTrauf.length > 0 ? allTrauf.reduce((a, b) => a + b, 0) / allTrauf.length : 0
    const maxFirst = allFirst.length > 0 ? Math.max(...allFirst) : 0

    // Hanglage aus Terrain-Differenz
    const slopeM = maxTerrain - minTerrain
    const slopeClass = slopeM < 0.5 ? 'eben' :
                       slopeM < 1.5 ? 'leicht' :
                       slopeM < 3.0 ? 'mittel' : 'stark'

    return {
      polygon,
      facades,
      building_count: buildings.length,
      egids,
      total_area_m2: totalArea,
      total_perimeter_m: unionPerimeter,
      min_terrain_m: minTerrain,
      max_terrain_m: maxTerrain,
      avg_traufhoehe_m: avgTrauf,
      max_firsthoehe_m: maxFirst,
      slope_m: slopeM,
      slope_class: slopeClass as 'eben' | 'leicht' | 'mittel' | 'stark',
      requires_level_compensation: slopeM > 0.5,
    }
  } catch (error) {
    console.error('[combineBuildings] Fehler bei Union:', error)
    return null
  }
}

/**
 * Berechnet Fassaden aus einem Polygon.
 * Übernimmt Höhen aus den Original-Gebäuden wenn möglich.
 */
function calculateFacadesFromPolygon(
  polygon: number[][],
  originalBuildings: GeruestbauData[]
): GeruestbauFassade[] {
  const facades: GeruestbauFassade[] = []

  // Sammle alle Original-Fassaden für Höhen-Lookup
  const originalFacades = originalBuildings.flatMap(b => b.facades ?? [])

  // Default-Höhen aus Gebäuden
  const defaultHeight = originalBuildings[0]?.heights?.traufhoehe_m ??
                        originalBuildings[0]?.facades?.[0]?.height_m ?? 8
  const defaultTerrainZ = originalBuildings[0]?.terrain?.min_m ?? 0

  for (let i = 0; i < polygon.length; i++) {
    const start = polygon[i]
    const end = polygon[(i + 1) % polygon.length]

    // Länge berechnen
    const dx = end[0] - start[0]
    const dy = end[1] - start[1]
    const length = Math.sqrt(dx * dx + dy * dy)

    // Azimut berechnen (0° = Nord, 90° = Ost)
    const azimuth = (Math.atan2(dx, dy) * 180 / Math.PI + 360) % 360

    // Richtung aus Azimut
    const direction = azimuthToDirection(azimuth)

    // Versuche Höhen aus Original-Fassaden zu finden
    // Suche Fassade die am nächsten zu dieser Kante liegt
    const matchedFacade = findMatchingFacade(start, end, originalFacades)

    const terrainZMin = matchedFacade?.terrain_z_min ?? defaultTerrainZ
    const terrainZMax = matchedFacade?.terrain_z_max ?? defaultTerrainZ
    const wallZMax = matchedFacade?.wall_z_max ?? (defaultTerrainZ + defaultHeight)
    const heightM = matchedFacade?.height_m ?? defaultHeight

    facades.push({
      index: i,
      direction,
      start_point: start as [number, number],
      end_point: end as [number, number],
      length_m: length,
      azimuth_deg: azimuth,
      terrain_z_min: terrainZMin,
      terrain_z_max: terrainZMax,
      wall_z_max: wallZMax,
      height_m: heightM,
      slope_m: Math.abs(terrainZMax - terrainZMin),
      height_source: matchedFacade?.height_source ?? 'building_global',
      is_blocked: false,
    })
  }

  return facades
}

/**
 * Findet eine passende Original-Fassade für eine Kante.
 * Vergleicht Mittelpunkte der Kanten.
 */
function findMatchingFacade(
  start: number[],
  end: number[],
  originalFacades: GeruestbauFassade[]
): GeruestbauFassade | null {
  if (originalFacades.length === 0) return null

  const midX = (start[0] + end[0]) / 2
  const midY = (start[1] + end[1]) / 2

  let bestMatch: GeruestbauFassade | null = null
  let bestDist = Infinity

  for (const facade of originalFacades) {
    const facadeMidX = (facade.start_point[0] + facade.end_point[0]) / 2
    const facadeMidY = (facade.start_point[1] + facade.end_point[1]) / 2

    const dist = Math.sqrt(
      Math.pow(midX - facadeMidX, 2) +
      Math.pow(midY - facadeMidY, 2)
    )

    // Toleranz: 2m
    if (dist < bestDist && dist < 2) {
      bestDist = dist
      bestMatch = facade
    }
  }

  return bestMatch
}

/**
 * Konvertiert Azimut (0-360°) zu Himmelsrichtung.
 */
function azimuthToDirection(azimuth: number): string {
  const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
  const index = Math.round(azimuth / 45) % 8
  return directions[index]
}

/**
 * Prüft ob Multi-Building Gebäude zusammenhängen (für Union geeignet).
 * Gibt true zurück wenn alle Gebäude sich berühren oder überlappen.
 */
export function checkBuildingsConnected(buildings: GeruestbauData[]): boolean {
  if (buildings.length <= 1) return true

  try {
    const polygons = buildings
      .map(b => {
        const coords = b.building.polygon as number[][]
        if (!coords || coords.length < 3) return null
        const closed = [...coords]
        if (closed[0][0] !== closed[closed.length - 1][0] ||
            closed[0][1] !== closed[closed.length - 1][1]) {
          closed.push(closed[0])
        }
        return turf.polygon([closed])
      })
      .filter((p): p is Feature<Polygon> => p !== null)

    // Prüfe ob jedes Polygon mindestens ein anderes berührt
    for (let i = 0; i < polygons.length; i++) {
      let hasNeighbor = false
      for (let j = 0; j < polygons.length; j++) {
        if (i !== j) {
          // Buffer von 0.5m um "fast berührend" auch zu akzeptieren
          const buffered = turf.buffer(polygons[j], 0.5, { units: 'meters' })
          if (buffered && turf.booleanIntersects(polygons[i], buffered)) {
            hasNeighbor = true
            break
          }
        }
      }
      if (!hasNeighbor) {
        console.warn(`[checkBuildingsConnected] Gebäude ${i} hat keinen Nachbarn`)
        return false
      }
    }

    return true
  } catch (error) {
    console.error('[checkBuildingsConnected] Fehler:', error)
    return false
  }
}
