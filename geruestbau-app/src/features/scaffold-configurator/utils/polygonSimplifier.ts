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

export interface Point {
  x: number;
  y: number;
}

export interface Side {
  index: number;
  start: Point;
  end: Point;
  length_m: number;
  direction: string;
  azimuth_deg: number;
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
 * Douglas-Peucker Algorithmus
 */
function douglasPeucker(points: Point[], epsilon: number): Point[] {
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
    // Alle Zwischenpunkte entfernen
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
 * Verschmilzt kollineare Segmente
 */
function mergeCollinearSegments(points: Point[], angleToleranceDeg: number): Point[] {
  if (points.length < 4) return points;

  // Prüfen ob geschlossen
  const closed = points[0].x === points[points.length - 1].x &&
                 points[0].y === points[points.length - 1].y;

  const workPoints = closed ? points.slice(0, -1) : points;

  const result: Point[] = [workPoints[0]];
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
 */
function calculateSides(points: Point[]): Side[] {
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

    sides.push({
      index: i,
      start: p1,
      end: p2,
      length_m: Math.round(length * 100) / 100,
      azimuth_deg: Math.round(facadeAzimuth * 10) / 10,
      direction: azimuthToDirection(facadeAzimuth),
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
 * @param polygon Array von [x, y] Koordinaten (LV95)
 * @param options Epsilon und Winkeltoleranz
 * @returns Vereinfachtes Polygon mit Fassaden
 */
export function simplifyPolygon(
  polygon: [number, number][],
  options: SimplifyOptions = {}
): SimplificationResult {
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

  // Convert to Point format
  const points: Point[] = polygon.map(([x, y]) => ({ x, y }));
  const originalCount = points.length;

  // Epsilon bestimmen
  let epsilon = options.epsilon;
  if (epsilon === null || epsilon === undefined) {
    epsilon = calculateDynamicEpsilon(points);
  }

  // epsilon === 0 means NO simplification (Original)
  if (epsilon === 0) {
    const sides = calculateSides(points);
    return {
      originalPoints: originalCount,
      simplifiedPoints: points.length,
      polygon: points,
      sides,
      epsilon: 0,
      angleToleranceDeg: 0,
    };
  }

  // Winkeltoleranz bestimmen
  const angleToleranceDeg = options.angleTolerance ?? getAngleToleranceForEpsilon(epsilon);

  // 1. Douglas-Peucker
  let simplified = douglasPeucker(points, epsilon);

  // 2. Kollineare Segmente verschmelzen
  simplified = mergeCollinearSegments(simplified, angleToleranceDeg);

  // 3. Fassaden berechnen
  const sides = calculateSides(simplified);

  return {
    originalPoints: originalCount,
    simplifiedPoints: simplified.length,
    polygon: simplified,
    sides,
    epsilon,
    angleToleranceDeg,
  };
}

/**
 * Konvertiert vereinfachte Seiten zum Frontend-Format
 *
 * NEU 14.01.2026 21:15: Fassaden-spezifische Höhen für Hanglage-Gebäude
 * Bei Gebäuden am Hang haben verschiedene Fassaden unterschiedliche Höhen.
 * facadeZMin/facadeZMax enthalten die Terrain- und Wandhöhen pro Richtung.
 *
 * @param sides - Vereinfachte Polygon-Seiten
 * @param defaultHeight - Globale Traufhöhe (Fallback)
 * @param facadeZMin - Terrain-Höhen pro Richtung (m ü.M.), z.B. {"N": 543.0, "S": 540.0}
 * @param facadeZMax - Wandoberkanten pro Richtung (m ü.M.), z.B. {"N": 555.0, "S": 555.0}
 */
export function sidesToFacades(
  sides: Side[],
  defaultHeight: number,
  facadeZMin?: Record<string, number>,
  facadeZMax?: Record<string, number>
): Array<{
  id: string;
  direction: FacadeDirection;
  length_m: number;
  height_m: number;
  slope_percent: number;
  start_point: [number, number];
  end_point: [number, number];
  // NEU: Fassaden-spezifische Höhen-Metadaten
  facade_z_min?: number;
  facade_z_max?: number;
  height_source?: 'wall_layer' | 'terrain_sampled' | 'global';
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
        height = dirZMax - dirZMin;
        zMin = dirZMin;
        zMax = dirZMax;
        // Quelle bestimmen (vereinfacht: wenn Daten da sind, dann aus 3D-Layer)
        heightSource = 'terrain_sampled';
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
      // NEU: Metadaten für UI-Anzeige
      facade_z_min: zMin,
      facade_z_max: zMax,
      height_source: heightSource,
    };
  });
}
