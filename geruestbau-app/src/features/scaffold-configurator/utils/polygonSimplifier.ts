/**
 * Douglas-Peucker Polygon Simplification
 *
 * Lokale Vereinfachung von Gebäude-Polygonen für schnelle Fassaden-Auswahl.
 * Läuft komplett im Browser - kein API-Call nötig.
 *
 * @example
 * const result = simplifyPolygon(polygon, { epsilon: 0.5 });
 * console.log(result.sides); // Vereinfachte Fassaden
 */

import type { FacadeDirection } from '../types/scaffold.types';
import type { BuildingWall } from '../../../types/project';

export interface Point {
  x: number;
  y: number;
}

// NEU 19.01.2026: Punkt mit Original-Index für Tracking bei Vereinfachung
interface IndexedPoint extends Point {
  originalIndex: number;
}

export interface Side {
  index: number;
  start: Point;
  end: Point;
  length_m: number;
  direction: string;
  azimuth_deg: number;
  // NEU 19.01.2026: Original-Polygon-Indizes für exakte 3D-Platzierung
  // Bei Vereinfachung: [startIdx, ...zwischenPunkte, endIdx] im Original-Polygon
  originalIndices?: number[];
}

export interface SimplificationResult {
  originalPoints: number;
  simplifiedPoints: number;
  polygon: Point[];
  sides: Side[];
  epsilon: number;
  angleToleranceDeg: number;
}

// Epsilon -> Winkeltoleranz Mapping (wie im Backend)
const EPSILON_TO_ANGLE: Record<number, number> = {
  0.3: 5,
  0.5: 8,
  1.0: 12,
  2.0: 20,
  3.0: 30,
};

/**
 * Berechnet Winkeltoleranz basierend auf Epsilon (mit Interpolation)
 */
function getAngleToleranceForEpsilon(epsilon: number): number {
  const entries = Object.entries(EPSILON_TO_ANGLE)
    .map(([e, a]) => [parseFloat(e), a] as [number, number])
    .sort((a, b) => a[0] - b[0]);

  // Unter Minimum
  if (epsilon <= entries[0][0]) return entries[0][1];
  // Über Maximum
  if (epsilon >= entries[entries.length - 1][0]) return entries[entries.length - 1][1];

  // Interpolieren
  for (let i = 0; i < entries.length - 1; i++) {
    const [e1, a1] = entries[i];
    const [e2, a2] = entries[i + 1];
    if (epsilon >= e1 && epsilon <= e2) {
      const t = (epsilon - e1) / (e2 - e1);
      return a1 + t * (a2 - a1);
    }
  }

  return 8; // Default
}

/**
 * Senkrechter Abstand eines Punktes zu einer Linie
 */
function perpendicularDistance(point: Point, lineStart: Point, lineEnd: Point): number {
  const dx = lineEnd.x - lineStart.x;
  const dy = lineEnd.y - lineStart.y;
  const lineLengthSq = dx * dx + dy * dy;

  if (lineLengthSq === 0) {
    return Math.sqrt(
      (point.x - lineStart.x) ** 2 + (point.y - lineStart.y) ** 2
    );
  }

  // Projektion
  const t = Math.max(0, Math.min(1,
    ((point.x - lineStart.x) * dx + (point.y - lineStart.y) * dy) / lineLengthSq
  ));

  const nearestX = lineStart.x + t * dx;
  const nearestY = lineStart.y + t * dy;

  return Math.sqrt((point.x - nearestX) ** 2 + (point.y - nearestY) ** 2);
}

/**
 * Douglas-Peucker Algorithmus (mit Index-Tracking für Original-Segmente)
 * NEU 19.01.2026: Behält originalIndex für exakte 3D-Platzierung bei
 */
function douglasPeucker(points: IndexedPoint[], epsilon: number): IndexedPoint[] {
  if (points.length < 3) return points;

  // Finde Punkt mit maximaler Distanz
  let maxDist = 0;
  let maxIdx = 0;

  for (let i = 1; i < points.length - 1; i++) {
    const dist = perpendicularDistance(points[i], points[0], points[points.length - 1]);
    if (dist > maxDist) {
      maxDist = dist;
      maxIdx = i;
    }
  }

  if (maxDist > epsilon) {
    // Rekursiv beide Teile vereinfachen
    const left = douglasPeucker(points.slice(0, maxIdx + 1), epsilon);
    const right = douglasPeucker(points.slice(maxIdx), epsilon);
    return [...left.slice(0, -1), ...right];
  } else {
    // Alle Zwischenpunkte entfernen - aber Original-Indizes behalten!
    return [points[0], points[points.length - 1]];
  }
}

/**
 * Winkel zwischen zwei Segmenten in Grad
 */
function segmentAngle(p1: Point, p2: Point): number {
  return Math.atan2(p2.y - p1.y, p2.x - p1.x) * (180 / Math.PI);
}

/**
 * Winkeldifferenz (0-180)
 */
function angleDifference(a1: number, a2: number): number {
  let diff = Math.abs(a1 - a2) % 360;
  return Math.min(diff, 360 - diff);
}

/**
 * Verschmilzt kollineare Segmente (mit Index-Tracking)
 * NEU 19.01.2026: Behält originalIndex für exakte 3D-Platzierung bei
 */
function mergeCollinearSegments(points: IndexedPoint[], angleToleranceDeg: number): IndexedPoint[] {
  if (points.length < 4) return points;

  // Prüfen ob geschlossen
  const closed = points[0].x === points[points.length - 1].x &&
                 points[0].y === points[points.length - 1].y;

  const workPoints = closed ? points.slice(0, -1) : points;

  const result: IndexedPoint[] = [workPoints[0]];
  let currentAngle = segmentAngle(workPoints[0], workPoints[1]);

  for (let i = 1; i < workPoints.length - 1; i++) {
    const nextAngle = segmentAngle(workPoints[i], workPoints[i + 1]);

    if (angleDifference(currentAngle, nextAngle) > angleToleranceDeg) {
      // Signifikante Richtungsänderung -> Punkt behalten
      result.push(workPoints[i]);
      currentAngle = nextAngle;
    }
  }

  // Letzten Punkt hinzufügen
  result.push(workPoints[workPoints.length - 1]);

  if (closed) {
    result.push(result[0]);
  }

  return result;
}

/**
 * Azimut zu Himmelsrichtung
 */
function azimuthToDirection(azimuth: number): string {
  const normalized = ((azimuth % 360) + 360) % 360;

  if (normalized >= 337.5 || normalized < 22.5) return 'N';
  if (normalized < 67.5) return 'NE';
  if (normalized < 112.5) return 'E';
  if (normalized < 157.5) return 'SE';
  if (normalized < 202.5) return 'S';
  if (normalized < 247.5) return 'SW';
  if (normalized < 292.5) return 'W';
  return 'NW';
}

/**
 * Berechnet Fassaden aus vereinfachtem Polygon
 *
 * WICHTIG: direction ist die Richtung der Fassaden-NORMALEN (wohin die Fassade zeigt),
 * nicht die Richtung der Kante! Eine Kante die Ost-West verläuft hat eine Nord- oder Süd-Fassade.
 *
 * Bei GIS-Polygonen (gegen Uhrzeigersinn für äussere Ringe) ist die äussere Normale
 * 90° nach rechts gedreht zur Kantenrichtung.
 *
 * NEU 19.01.2026: Berechnet originalIndices für exakte 3D-Gerüst-Platzierung.
 * Wenn IndexedPoint[] übergeben wird, werden die Original-Indizes für jede Seite gespeichert.
 */
function calculateSides(points: Point[] | IndexedPoint[]): Side[] {
  const sides: Side[] = [];

  for (let i = 0; i < points.length - 1; i++) {
    const p1 = points[i];
    const p2 = points[i + 1];

    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const length = Math.sqrt(dx * dx + dy * dy);

    // Kantenrichtung (Azimut der Kante, 0 = Nord, im Uhrzeigersinn)
    let edgeAzimuth = Math.atan2(dx, dy) * (180 / Math.PI);
    if (edgeAzimuth < 0) edgeAzimuth += 360;

    // Fassaden-Normalrichtung: 90° nach rechts gedreht (äussere Normale)
    // Bei GIS-Polygonen gegen Uhrzeigersinn zeigt dies nach aussen
    let facadeAzimuth = (edgeAzimuth + 90) % 360;

    // NEU 19.01.2026: Original-Indizes berechnen wenn verfügbar
    let originalIndices: number[] | undefined;
    const ip1 = p1 as IndexedPoint;
    const ip2 = p2 as IndexedPoint;
    if (typeof ip1.originalIndex === 'number' && typeof ip2.originalIndex === 'number') {
      // Sammle alle Indizes von startIdx bis endIdx (einschließlich)
      const startIdx = ip1.originalIndex;
      const endIdx = ip2.originalIndex;
      originalIndices = [];
      for (let j = startIdx; j <= endIdx; j++) {
        originalIndices.push(j);
      }
    }

    sides.push({
      index: i,
      start: p1,
      end: p2,
      length_m: Math.round(length * 100) / 100,
      azimuth_deg: Math.round(facadeAzimuth * 10) / 10,
      direction: azimuthToDirection(facadeAzimuth),
      originalIndices,
    });
  }

  return sides;
}

/**
 * Dynamisches Epsilon basierend auf Polygon-Umfang
 */
function calculateDynamicEpsilon(points: Point[]): number {
  let perimeter = 0;
  for (let i = 0; i < points.length - 1; i++) {
    const dx = points[i + 1].x - points[i].x;
    const dy = points[i + 1].y - points[i].y;
    perimeter += Math.sqrt(dx * dx + dy * dy);
  }

  if (perimeter > 200) return 1.5; // Grosses Gebäude
  if (perimeter > 50) return 0.8;  // MFH
  return 0.3; // EFH
}

export interface SimplifyOptions {
  epsilon?: number | null;  // null = dynamic
  angleTolerance?: number;  // Override for angle tolerance
}

/**
 * Hauptfunktion: Vereinfacht ein Polygon für Fassaden-Auswahl
 *
 * NEU 19.01.2026: Speichert Original-Polygon-Referenz für exakte 3D-Gerüst-Platzierung.
 * Jede vereinfachte Seite enthält `originalIndices` mit den Indizes aller Original-Punkte,
 * die zu dieser Seite gehören. Das ermöglicht das Gerüst entlang der echten Konturen zu platzieren.
 *
 * @param polygon Array von [x, y] Koordinaten (LV95)
 * @param options Epsilon und Winkeltoleranz
 * @returns Vereinfachtes Polygon mit Fassaden (inkl. Original-Referenzen)
 */
export function simplifyPolygon(
  polygon: [number, number][],
  options: SimplifyOptions = {}
): SimplificationResult & { originalPolygon?: [number, number][] } {
  if (!polygon || polygon.length < 3) {
    return {
      originalPoints: polygon?.length || 0,
      simplifiedPoints: 0,
      polygon: [],
      sides: [],
      epsilon: 0,
      angleToleranceDeg: 0,
    };
  }

  // NEU 19.01.2026: Convert to IndexedPoint format (mit Original-Index)
  const indexedPoints: IndexedPoint[] = polygon.map(([x, y], index) => ({
    x,
    y,
    originalIndex: index,
  }));
  const originalCount = indexedPoints.length;

  // Epsilon bestimmen
  let epsilon = options.epsilon;
  if (epsilon === null || epsilon === undefined) {
    epsilon = calculateDynamicEpsilon(indexedPoints);
  }

  // epsilon === 0 means NO simplification (Original)
  if (epsilon === 0) {
    const sides = calculateSides(indexedPoints);
    return {
      originalPoints: originalCount,
      simplifiedPoints: indexedPoints.length,
      polygon: indexedPoints,
      sides,
      epsilon: 0,
      angleToleranceDeg: 0,
      originalPolygon: polygon,
    };
  }

  // Winkeltoleranz bestimmen
  const angleToleranceDeg = options.angleTolerance ?? getAngleToleranceForEpsilon(epsilon);

  // 1. Douglas-Peucker (behält Original-Indizes bei)
  let simplified = douglasPeucker(indexedPoints, epsilon);

  // 2. Kollineare Segmente verschmelzen (behält Original-Indizes bei)
  simplified = mergeCollinearSegments(simplified, angleToleranceDeg);

  // 3. Fassaden berechnen (mit Original-Indizes)
  const sides = calculateSides(simplified);

  return {
    originalPoints: originalCount,
    simplifiedPoints: simplified.length,
    polygon: simplified,
    sides,
    epsilon,
    angleToleranceDeg,
    originalPolygon: polygon,  // NEU: Original-Polygon für 3D-Platzierung
  };
}

/**
 * Konvertiert vereinfachte Seiten zum Frontend-Format
 *
 * NEU 14.01.2026 21:15: Fassaden-spezifische Höhen für Hanglage-Gebäude
 * Bei Gebäuden am Hang haben verschiedene Fassaden unterschiedliche Höhen.
 * facadeZMin/facadeZMax enthalten die Terrain- und Wandhöhen pro Richtung.
 *
 * NEU 19.01.2026: originalSegments für exakte 3D-Gerüst-Platzierung.
 * Wenn originalPolygon und originalIndices vorhanden sind, werden die echten
 * Polygon-Kanten für die 3D-Platzierung berechnet (statt vereinfachter Linien).
 *
 * @param sides - Vereinfachte Polygon-Seiten (mit originalIndices)
 * @param defaultHeight - Globale Traufhöhe (Fallback)
 * @param facadeZMin - Terrain-Höhen pro Richtung (m ü.M.), z.B. {"N": 543.0, "S": 540.0}
 * @param facadeZMax - Wandoberkanten pro Richtung (m ü.M.), z.B. {"N": 555.0, "S": 555.0}
 * @param originalPolygon - Original-Polygon für 3D-Platzierung (optional)
 */
export function sidesToFacades(
  sides: Side[],
  defaultHeight: number,
  facadeZMin?: Record<string, number>,
  facadeZMax?: Record<string, number>,
  originalPolygon?: [number, number][]
): Array<{
  id: string;
  direction: FacadeDirection;
  length_m: number;
  height_m: number;
  slope_percent: number;
  start_point: [number, number];
  end_point: [number, number];
  // NEU 19.01.2026: Original-Polygon-Segmente für exakte 3D-Platzierung
  originalSegments?: Array<{ start: [number, number]; end: [number, number] }>;
  // NEU: Fassaden-spezifische Höhen-Metadaten
  facade_z_min?: number;
  facade_z_max?: number;
  height_source?: 'wall_layer' | 'terrain_sampled' | 'global' | 'building_walls';
}> {
  return sides.map((side, idx) => {
    // Fassaden-spezifische Höhe wenn verfügbar
    let height = defaultHeight;
    let zMin: number | undefined;
    let zMax: number | undefined;
    let heightSource: 'wall_layer' | 'terrain_sampled' | 'global' = 'global';

    if (facadeZMin && facadeZMax) {
      const dirZMin = facadeZMin[side.direction];
      const dirZMax = facadeZMax[side.direction];

      if (dirZMin !== undefined && dirZMax !== undefined && dirZMax > dirZMin) {
        // FIX 15.01.2026 BUG-023: height bleibt defaultHeight (Traufhöhe)!
        // Die Terrain-Differenz wird über terrain_diff_m für Stellspindeln abgebildet,
        // NICHT über unterschiedliche Gerüsthöhen pro Fassade.
        // ENTFERNT: height = dirZMax - dirZMin;
        zMin = dirZMin;
        zMax = dirZMax;
        heightSource = 'terrain_sampled';
      }
    }

    // NEU 19.01.2026: Original-Segmente aus originalIndices berechnen
    let originalSegments: Array<{ start: [number, number]; end: [number, number] }> | undefined;
    if (originalPolygon && side.originalIndices && side.originalIndices.length >= 2) {
      originalSegments = [];
      for (let i = 0; i < side.originalIndices.length - 1; i++) {
        const startIdx = side.originalIndices[i];
        const endIdx = side.originalIndices[i + 1];
        if (startIdx < originalPolygon.length && endIdx < originalPolygon.length) {
          originalSegments.push({
            start: originalPolygon[startIdx],
            end: originalPolygon[endIdx],
          });
        }
      }
    }

    return {
      id: `facade-${idx + 1}`,
      direction: side.direction as FacadeDirection,
      length_m: side.length_m,
      height_m: height,
      slope_percent: 0,
      start_point: [side.start.x, side.start.y],
      end_point: [side.end.x, side.end.y],
      originalSegments,  // NEU: Für 3D-Gerüst-Platzierung
      // NEU: Metadaten für UI-Anzeige
      facade_z_min: zMin,
      facade_z_max: zMax,
      height_source: heightSource,
    };
  });
}

// ============================================================================
// NEU 15.01.2026 BUG-024: Geometrisches Matching für BuildingWall
// ============================================================================

/**
 * Berechnet minimale Distanz zwischen einem Punkt und einem Linien-Segment
 */
function pointToSegmentDistance(
  px: number, py: number,
  x1: number, y1: number,
  x2: number, y2: number
): number {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const lenSq = dx * dx + dy * dy;

  if (lenSq === 0) {
    return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2);
  }

  // Projektion auf Linie
  const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / lenSq));
  const nearX = x1 + t * dx;
  const nearY = y1 + t * dy;

  return Math.sqrt((px - nearX) ** 2 + (py - nearY) ** 2);
}

/**
 * Prüft ob zwei Linien-Segmente sich überlappen (mit Toleranz)
 *
 * @param s1 Fassaden-Segment (start, end)
 * @param s2 Wall-Segment (start, end)
 * @param tolerance Maximale Distanz für Matching (in Meter)
 * @returns true wenn Überlappung erkannt
 */
function segmentsOverlap(
  s1Start: [number, number], s1End: [number, number],
  s2Start: [number, number], s2End: [number, number],
  tolerance: number = 2.0
): boolean {
  // Prüfe ob Endpunkte von s1 nahe an s2 liegen
  const d1 = pointToSegmentDistance(s1Start[0], s1Start[1], s2Start[0], s2Start[1], s2End[0], s2End[1]);
  const d2 = pointToSegmentDistance(s1End[0], s1End[1], s2Start[0], s2Start[1], s2End[0], s2End[1]);

  // Prüfe auch umgekehrt: Endpunkte von s2 nahe an s1
  const d3 = pointToSegmentDistance(s2Start[0], s2Start[1], s1Start[0], s1Start[1], s1End[0], s1End[1]);
  const d4 = pointToSegmentDistance(s2End[0], s2End[1], s1Start[0], s1Start[1], s1End[0], s1End[1]);

  // Mindestens 2 Punkte müssen nahe sein für Überlappung
  const closeCount = [d1, d2, d3, d4].filter(d => d < tolerance).length;
  return closeCount >= 2;
}

/**
 * Ergebnis des Wall-Matchings mit per-Polygon z-Werten
 * NEU 15.01.2026: Per-Polygon z-Werte statt globale Wall z_min/z_max
 */
export interface WallMatchResult {
  wall: BuildingWall;
  polygon_z_min: number;  // Min z aus dem gematchten Polygon
  polygon_z_max: number;  // Max z aus dem gematchten Polygon
  wall_height: number;    // polygon_z_max - polygon_z_min
  // NEU 24.01.2026 P3: Giebel-Erkennung
  is_giebel: boolean;     // True wenn Wand-Höhe > Traufhöhe (dachMin)
  giebel_height_m?: number;  // Giebel-Höhe über Traufe (wall_z_max - dachMin)
  // NEU 27.01.2026: Terrain-Profil für Stellspindel-Berechnung
  terrain_profile?: TerrainProfilePoint[];
}

/**
 * NEU 27.01.2026: Terrain-Profil-Punkt für Stellspindel-Berechnung
 *
 * Jeder Punkt repräsentiert die Terrain-Höhe an einer Position entlang der Fassade.
 * position_m = 0 am Fassaden-Start, position_m = facade_length am Ende.
 */
export interface TerrainProfilePoint {
  position_m: number;      // Position entlang der Fassade (0 = Start)
  z_terrain: number;       // Terrain-Höhe (m ü.M.)
  z_traufe: number;        // Trauf-Höhe an diesem Punkt (m ü.M.)
  scaffold_height_m: number;  // Gerüst-Höhe = z_traufe - z_terrain
}

/**
 * NEU 27.01.2026: Extrahiert Terrain-Profil aus Wall-Polygon für Stellspindel-Berechnung
 *
 * Das Wall-Polygon enthält 3D-Vertices. Die unteren Vertices (nahe z_min) repräsentieren
 * das Terrain entlang der Fassade. Diese Funktion extrahiert diese Punkte und sortiert
 * sie nach Position entlang der Fassade.
 *
 * Beispiel:
 *   Wall-Polygon:  [A]───[B]    z ≈ 562m (Traufe)
 *                   │     │
 *                  [D]───[C]    z = 555.8m → 556.5m (Terrain, variiert!)
 *
 *   Terrain-Profil: [{pos: 0, z: 555.8}, {pos: 6, z: 556.1}, {pos: 12, z: 556.5}]
 *
 * @param coords3d 3D-Koordinaten des Wall-Polygons [[x,y,z], ...]
 * @param facadeStart Start der Fassade [E, N]
 * @param facadeEnd Ende der Fassade [E, N]
 * @param zThresholdRatio Anteil der Wandhöhe unter dem ein Vertex als "Terrain" gilt (default: 0.3 = untere 30%)
 * @returns Sortiertes Array von Terrain-Profil-Punkten
 */
export function extractTerrainProfile(
  coords3d: number[][],
  facadeStart: [number, number],
  facadeEnd: [number, number],
  zThresholdRatio: number = 0.3
): TerrainProfilePoint[] {
  if (!coords3d || coords3d.length < 3) return [];

  // 1. z_min und z_max des Polygons berechnen
  let z_min = Infinity;
  let z_max = -Infinity;
  for (const coord of coords3d) {
    if (coord.length >= 3) {
      const z = coord[2];
      if (z < z_min) z_min = z;
      if (z > z_max) z_max = z;
    }
  }
  if (!isFinite(z_min) || !isFinite(z_max) || z_max <= z_min) return [];

  // 2. Schwellenwert für "Terrain-Vertices" (untere X% der Wandhöhe)
  const wallHeight = z_max - z_min;
  const zThreshold = z_min + wallHeight * zThresholdRatio;

  // 3. Fassaden-Richtung und Länge berechnen
  const facadeDx = facadeEnd[0] - facadeStart[0];
  const facadeDy = facadeEnd[1] - facadeStart[1];
  const facadeLength = Math.sqrt(facadeDx * facadeDx + facadeDy * facadeDy);
  if (facadeLength < 0.1) return [];

  // Einheitsvektor der Fassade
  const facadeUnitX = facadeDx / facadeLength;
  const facadeUnitY = facadeDy / facadeLength;

  // 4. Terrain-Vertices extrahieren und auf Fassade projizieren
  const terrainPoints: TerrainProfilePoint[] = [];

  for (const coord of coords3d) {
    if (coord.length < 3) continue;
    const [x, y, z] = coord;

    // Nur Vertices im unteren Bereich (Terrain)
    if (z > zThreshold) continue;

    // Projektion auf Fassaden-Linie: position = (P - Start) · Einheitsvektor
    const dx = x - facadeStart[0];
    const dy = y - facadeStart[1];
    const position = dx * facadeUnitX + dy * facadeUnitY;

    // Nur Punkte innerhalb der Fassaden-Länge (mit kleiner Toleranz)
    if (position < -0.5 || position > facadeLength + 0.5) continue;

    // Trauf-Höhe = z_max (obere Kante des Wand-Polygons)
    // Bei komplexen Polygonen könnte man hier den entsprechenden oberen Vertex suchen,
    // aber für die meisten Wände ist z_max konstant
    terrainPoints.push({
      position_m: Math.max(0, Math.min(facadeLength, position)),
      z_terrain: z,
      z_traufe: z_max,
      scaffold_height_m: z_max - z,
    });
  }

  // 5. Nach Position sortieren
  terrainPoints.sort((a, b) => a.position_m - b.position_m);

  // 6. Duplikate entfernen (Punkte die sehr nah beieinander liegen)
  const uniquePoints: TerrainProfilePoint[] = [];
  for (const point of terrainPoints) {
    const lastPoint = uniquePoints[uniquePoints.length - 1];
    if (!lastPoint || Math.abs(point.position_m - lastPoint.position_m) > 0.1) {
      uniquePoints.push(point);
    }
  }

  return uniquePoints;
}

/**
 * NEU 27.01.2026: Berechnet Stellspindel-Höhen aus Terrain-Profil
 *
 * Die Stellspindel gleicht das Terrain-Gefälle aus. Der niedrigste Punkt
 * braucht keine Spindel (Referenz), alle anderen Punkte brauchen eine
 * Spindel entsprechend der Höhendifferenz.
 *
 * @param terrainProfile Terrain-Profil aus extractTerrainProfile()
 * @returns Array von Stellspindel-Höhen pro Position (0 = keine Spindel nötig)
 */
export function calculateLevelingSpindles(
  terrainProfile: TerrainProfilePoint[]
): Array<{ position_m: number; spindle_height_m: number }> {
  if (terrainProfile.length === 0) return [];

  // Niedrigsten Terrain-Punkt finden (Referenz)
  const minTerrain = Math.min(...terrainProfile.map((p) => p.z_terrain));

  return terrainProfile.map((point) => ({
    position_m: point.position_m,
    spindle_height_m: point.z_terrain - minTerrain,
  }));
}

/**
 * Extrahiert 2D-Koordinaten UND 3D-Koordinaten aus BuildingWall
 * NEU 15.01.2026: Erweitert um 3D-Koordinaten für z-Wert Extraktion
 */
function extractWallRingsWithZ(wall: BuildingWall): Array<{
  coords2d: [number, number][];
  coords3d: number[][];  // Original 3D-Koordinaten für z-Wert Extraktion
}> {
  const result: Array<{ coords2d: [number, number][]; coords3d: number[][] }> = [];

  // FIX 19.01.2026: Umbenennung coords_3d → geometry (konsistent mit DB geometry_wkb)
  if (!wall.geometry || !wall.geometry_type) return result;

  if (wall.geometry_type === 'Polygon') {
    const rings = wall.geometry as number[][][];
    for (const ring of rings) {
      result.push({
        coords2d: ring.map((c) => [c[0], c[1]] as [number, number]),
        coords3d: ring,
      });
    }
  } else if (wall.geometry_type === 'MultiPolygon') {
    const polygons = wall.geometry as number[][][][];
    for (const polygon of polygons) {
      for (const ring of polygon) {
        result.push({
          coords2d: ring.map((c) => [c[0], c[1]] as [number, number]),
          coords3d: ring,
        });
      }
    }
  } else if (wall.geometry_type === 'LineString') {
    const coords = wall.geometry as number[][];
    result.push({
      coords2d: coords.map((c) => [c[0], c[1]] as [number, number]),
      coords3d: coords,
    });
  }

  return result;
}

/**
 * Extrahiert z_min und z_max aus einem 3D-Ring
 */
function extractZFromRing(coords3d: number[][]): { z_min: number; z_max: number } {
  let z_min = Infinity;
  let z_max = -Infinity;

  for (const coord of coords3d) {
    if (coord.length >= 3) {
      const z = coord[2];
      if (z < z_min) z_min = z;
      if (z > z_max) z_max = z;
    }
  }

  return { z_min, z_max };
}

/**
 * Findet die beste BuildingWall-Übereinstimmung für eine Fassade
 * und extrahiert z-Werte aus dem spezifischen gematchten Polygon
 *
 * NEU 15.01.2026: Erweitert um per-Polygon z-Werte
 * FIX 15.01.2026 22:30: Toleranz 3.0m, MAX HEIGHT Strategie
 *
 * Bei mehreren Matches wird die Wand mit der GRÖSSTEN HÖHE gewählt,
 * da kleine Wandsegmente (Fenster, Vorsprünge) niedrigere Höhen haben.
 *
 * @param facadeStart Startpunkt der Fassade [E, N]
 * @param facadeEnd Endpunkt der Fassade [E, N]
 * @param buildingWalls Alle verfügbaren BuildingWall-Daten
 * @param tolerance Matching-Toleranz in Metern (default: 3.0m - erhöht wegen Offset zwischen Gebäude- und Wall-Polygon)
 * @returns WallMatchResult mit per-Polygon z-Werten oder undefined
 */
export function matchFacadeToWall(
  facadeStart: [number, number],
  facadeEnd: [number, number],
  buildingWalls: BuildingWall[],
  tolerance: number = 3.0,  // FIX: Erhöht von 2.0m wegen Koordinaten-Offset
  dachMin?: number  // NEU 24.01.2026 P3: Für Giebel-Erkennung
): WallMatchResult | undefined {
  // Sammle ALLE Matches
  const allMatches: Array<{
    wall: BuildingWall;
    coords3d: number[][];
    height: number;
    avgDist: number;
  }> = [];

  for (const wall of buildingWalls) {
    const rings = extractWallRingsWithZ(wall);

    for (const { coords2d, coords3d } of rings) {
      // Berechne Höhe dieses Polygons
      const { z_min, z_max } = extractZFromRing(coords3d);
      const polyHeight = isFinite(z_max) && isFinite(z_min) ? z_max - z_min : 0;

      // Prüfe jedes Segment im Ring
      for (let i = 0; i < coords2d.length - 1; i++) {
        const wallStart = coords2d[i];
        const wallEnd = coords2d[i + 1];

        if (segmentsOverlap(facadeStart, facadeEnd, wallStart, wallEnd, tolerance)) {
          // Berechne durchschnittliche Distanz
          const d1 = pointToSegmentDistance(facadeStart[0], facadeStart[1], wallStart[0], wallStart[1], wallEnd[0], wallEnd[1]);
          const d2 = pointToSegmentDistance(facadeEnd[0], facadeEnd[1], wallStart[0], wallStart[1], wallEnd[0], wallEnd[1]);
          const avgDist = (d1 + d2) / 2;

          allMatches.push({ wall, coords3d, height: polyHeight, avgDist });
          break; // Nur ein Match pro Ring nötig
        }
      }
    }
  }

  if (allMatches.length === 0) return undefined;

  // FIX: Wähle das Match mit der GRÖSSTEN HÖHE (Hauptwand statt Fenster)
  // Bei gleicher Höhe: kürzeste Distanz
  allMatches.sort((a, b) => {
    if (Math.abs(a.height - b.height) > 0.5) {
      return b.height - a.height; // Grösste Höhe zuerst
    }
    return a.avgDist - b.avgDist; // Bei ähnlicher Höhe: kürzeste Distanz
  });

  const bestMatch = allMatches[0];

  // Extrahiere z-Werte aus dem gematchten Polygon
  const { z_min, z_max } = extractZFromRing(bestMatch.coords3d);

  if (!isFinite(z_min) || !isFinite(z_max)) {
    // Fallback auf globale Wall-Werte wenn keine z-Koordinaten im Ring
    if (bestMatch.wall.z_min !== null && bestMatch.wall.z_max !== null) {
      // NEU 24.01.2026 P3: Giebel-Erkennung
      const isGiebel = dachMin !== undefined && bestMatch.wall.z_max > dachMin + 0.5;
      const giebelHeightM = isGiebel && dachMin !== undefined ? bestMatch.wall.z_max - dachMin : undefined;
      return {
        wall: bestMatch.wall,
        polygon_z_min: bestMatch.wall.z_min,
        polygon_z_max: bestMatch.wall.z_max,
        wall_height: bestMatch.wall.z_max - bestMatch.wall.z_min,
        is_giebel: isGiebel,
        giebel_height_m: giebelHeightM,
      };
    }
    return undefined;
  }

  // NEU 24.01.2026 P3: Giebel-Erkennung
  const isGiebel = dachMin !== undefined && z_max > dachMin + 0.5;
  const giebelHeightM = isGiebel && dachMin !== undefined ? z_max - dachMin : undefined;

  // NEU 27.01.2026: Terrain-Profil für Stellspindel-Berechnung
  const terrainProfile = extractTerrainProfile(bestMatch.coords3d, facadeStart, facadeEnd);

  return {
    wall: bestMatch.wall,
    polygon_z_min: z_min,
    polygon_z_max: z_max,
    wall_height: z_max - z_min,
    is_giebel: isGiebel,
    giebel_height_m: giebelHeightM,
    terrain_profile: terrainProfile.length > 0 ? terrainProfile : undefined,
  };
}

/**
 * Konvertiert vereinfachte Seiten zum Frontend-Format MIT BuildingWall-Matching
 *
 * NEU 15.01.2026 BUG-024: Ersetzt alte facadeZMin/facadeZMax Logik durch
 * geometrisches Matching mit building_walls aus der DB.
 *
 * @param sides - Vereinfachte Polygon-Seiten
 * @param defaultHeight - Globale Traufhöhe (Fallback)
 * @param buildingWalls - BuildingWall[] direkt aus building_walls DB-Tabelle
 */
export function sidesToFacadesWithWalls(
  sides: Side[],
  defaultHeight: number,
  buildingWalls: BuildingWall[] = []
): Array<{
  id: string;
  direction: FacadeDirection;
  length_m: number;
  height_m: number;
  slope_percent: number;
  start_point: [number, number];
  end_point: [number, number];
  facade_z_min?: number;
  facade_z_max?: number;
  height_source: 'building_walls' | 'global';
  matched_wall?: {
    gebaeudeeinheit: string;
    geometry_type: string | null;
  };
}> {
  return sides.map((side, idx) => {
    let height = defaultHeight;
    let zMin: number | undefined;
    let zMax: number | undefined;
    let heightSource: 'building_walls' | 'global' = 'global';
    let matchedWall: { gebaeudeeinheit: string; geometry_type: string | null } | undefined;

    // Versuche Wall-Matching wenn buildingWalls vorhanden
    if (buildingWalls.length > 0) {
      const facadeStart: [number, number] = [side.start.x, side.start.y];
      const facadeEnd: [number, number] = [side.end.x, side.end.y];

      const matchResult = matchFacadeToWall(facadeStart, facadeEnd, buildingWalls);

      if (matchResult) {
        // Wall gefunden mit per-Polygon z-Werten (für Terrain-Höhen)
        zMin = matchResult.polygon_z_min;
        zMax = matchResult.polygon_z_max;
        // FIX 18.01.2026 BUG-026: NICHT wall_height als Fassaden-Höhe verwenden!
        // Giebel-Fassaden haben höhere Wände (bis First), aber das Gerüst soll
        // bei "Fassadenarbeit" nur bis zur TRAUFE gehen.
        // Die Gerüsthöhe bleibt defaultHeight (= Traufhöhe aus API).
        // ENTFERNT: height = matchResult.wall_height;
        heightSource = 'building_walls';
        matchedWall = {
          gebaeudeeinheit: matchResult.wall.gebaeudeeinheit,
          geometry_type: matchResult.wall.geometry_type,
        };
      }
    }

    return {
      id: `facade-${idx + 1}`,
      direction: side.direction as FacadeDirection,
      length_m: side.length_m,
      height_m: height,
      slope_percent: 0,
      start_point: [side.start.x, side.start.y],
      end_point: [side.end.x, side.end.y],
      facade_z_min: zMin,
      facade_z_max: zMax,
      height_source: heightSource,
      matched_wall: matchedWall,
    };
  });
}
