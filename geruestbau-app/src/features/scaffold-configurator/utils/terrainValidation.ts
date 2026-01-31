/**
 * Terrain-Validierung für Gerüstbau
 *
 * Pragmatische Validierung der Terrain-Daten basierend auf Layher Blitz 70 Spezifikationen.
 * Generiert strukturierte Warnungen für den Benutzer.
 *
 * @see KONTEXT_Materialbewirtschaftung_Geruestbau.md
 * @see create_layher_catalog.py (Artikelnummern)
 *
 * NEU 27.01.2026
 */

import type { TerrainProfilePoint } from './polygonSimplifier';

// =============================================================================
// LAYHER BLITZ 70 SPEZIFIKATIONEN
// =============================================================================

/**
 * Fussspindel-Varianten (Verstellbereich)
 * Artikelnummern aus Layher Blitz Katalog 2025/2026
 * FIX 28.01.2026: Korrigierte Art.-Nr. und max. Höhen gemäss Katalog
 */
export const SPINDLE_VARIANTS = {
  SPINDLE_60: { artNr: '4001.060', maxHeight_m: 0.41, name: 'Fußspindel 60' },
  SPINDLE_80: { artNr: '4002.080', maxHeight_m: 0.55, name: 'Fußspindel 80 verstärkt' },
  SPINDLE_110: { artNr: '4002.110', maxHeight_m: 0.79, name: 'Fußspindel 110 verstärkt' },
  SPINDLE_150: { artNr: '4002.130', maxHeight_m: 0.82, name: 'Fußspindel 150 verstärkt' },
} as const;

/**
 * Ausgleichsrahmen für Hanglagen (wenn Spindel nicht reicht)
 * FIX 28.01.2026: Korrigierte Art.-Nr. und kombinierten max. Ausgleich (Rahmen + Spindel 80)
 */
export const LEVELING_FRAMES = {
  FRAME_066: { artNr: '1773.066', height_m: 0.66, name: 'Ausgleichsrahmen 0.66m', forSlope: 'bis 1.21m (+ Spindel 80)' },
  FRAME_100: { artNr: '1773.100', height_m: 1.00, name: 'Ausgleichsrahmen 1.00m', forSlope: 'bis 1.55m (+ Spindel 80)' },
  FRAME_150: { artNr: '1773.150', height_m: 1.50, name: 'Ausgleichsrahmen 1.50m', forSlope: 'bis 2.05m (+ Spindel 80)' },
  FRAME_200: { artNr: '1773.200', height_m: 2.00, name: 'Ausgleichsrahmen 2.00m', forSlope: 'bis 2.55m (+ Spindel 80)' },
} as const;

/**
 * Hanglage-Klassifikation (aus data-flow.md)
 * FIX 28.01.2026: Angepasst an Layher Spindel-Kapazitäten
 */
export type SlopeClass = 'eben' | 'leicht' | 'mittel' | 'stark';

export const SLOPE_THRESHOLDS = {
  EBEN_MAX: 0.41,     // ≤ 41cm = Fußspindel 60 reicht (Standard)
  LEICHT_MAX: 0.82,   // ≤ 82cm = Fußspindel 150 reicht (grösste Spindel)
  MITTEL_MAX: 2.55,   // ≤ 2.55m = Ausgleichsrahmen 2.00m + Spindel 80 (55cm)
  // > 2.55m = spezielle Fundamentierung (stark)
} as const;

/**
 * Standard-Feldlängen Layher Blitz 70
 */
export const FIELD_LENGTHS = {
  LONG: 3.07,
  STANDARD: 2.57,
  SHORT: 2.07,
} as const;

// =============================================================================
// WARNUNG-TYPEN
// =============================================================================

export type TerrainWarningSeverity = 'info' | 'warning' | 'error';

export type TerrainWarningCode =
  | 'SPINDLE_SUFFICIENT'      // Info: Stellspindel reicht
  | 'SPINDLE_60_NEEDED'       // Info: 60cm Spindel empfohlen
  | 'SPINDLE_80_NEEDED'       // Warning: 80cm Spindel nötig
  | 'LEVELING_FRAME_NEEDED'   // Warning: Ausgleichsrahmen nötig
  | 'SPECIAL_FOUNDATION'      // Error: Spezielle Fundamentierung nötig
  | 'CORNER_HEIGHT_DIFF'      // Warning: Ecke mit Höhendifferenz
  | 'STEEP_GRADIENT'          // Warning: Steiles Gefälle innerhalb eines Feldes
  | 'MANUAL_CHECK_RECOMMENDED'; // Info: Vor-Ort-Prüfung empfohlen

export interface TerrainWarning {
  code: TerrainWarningCode;
  severity: TerrainWarningSeverity;
  message: string;
  details?: string;
  recommendation?: string;
  // Optionale Daten für Visualisierung
  position_m?: number;        // Position entlang der Fassade
  height_diff_m?: number;     // Relevante Höhendifferenz
  suggestedMaterial?: string; // Empfohlenes Material (Artikelnummer)
}

// =============================================================================
// VALIDIERUNGS-FUNKTIONEN
// =============================================================================

/**
 * Klassifiziert die Hanglage basierend auf der Terrain-Differenz
 */
export function classifySlope(terrainDiff_m: number): SlopeClass {
  const diff = Math.abs(terrainDiff_m);
  if (diff < SLOPE_THRESHOLDS.EBEN_MAX) return 'eben';
  if (diff < SLOPE_THRESHOLDS.LEICHT_MAX) return 'leicht';
  if (diff < SLOPE_THRESHOLDS.MITTEL_MAX) return 'mittel';
  return 'stark';
}

/**
 * Ermittelt die benötigte Spindel-Variante für eine Höhendifferenz
 * FIX 28.01.2026: Korrigierte Schwellenwerte gemäss Layher Katalog
 */
export function getRequiredSpindle(heightDiff_m: number): {
  spindle: typeof SPINDLE_VARIANTS[keyof typeof SPINDLE_VARIANTS] | null;
  needsLevelingFrame: boolean;
  levelingFrame?: typeof LEVELING_FRAMES[keyof typeof LEVELING_FRAMES];
} {
  const diff = Math.abs(heightDiff_m);

  // Stellspindeln reichen (gemäss Katalog max. Spindelweg)
  if (diff <= SPINDLE_VARIANTS.SPINDLE_60.maxHeight_m) {
    // ≤ 41cm: Standard-Fußspindel 60
    return { spindle: SPINDLE_VARIANTS.SPINDLE_60, needsLevelingFrame: false };
  }
  if (diff <= SPINDLE_VARIANTS.SPINDLE_80.maxHeight_m) {
    // ≤ 55cm: Fußspindel 80 verstärkt
    return { spindle: SPINDLE_VARIANTS.SPINDLE_80, needsLevelingFrame: false };
  }
  if (diff <= SPINDLE_VARIANTS.SPINDLE_110.maxHeight_m) {
    // ≤ 79cm: Fußspindel 110 verstärkt
    return { spindle: SPINDLE_VARIANTS.SPINDLE_110, needsLevelingFrame: false };
  }
  if (diff <= SPINDLE_VARIANTS.SPINDLE_150.maxHeight_m) {
    // ≤ 82cm: Fußspindel 150 verstärkt
    return { spindle: SPINDLE_VARIANTS.SPINDLE_150, needsLevelingFrame: false };
  }

  // Ausgleichsrahmen nötig (Spindel 80 + Rahmen)
  // Katalog: Rahmen + Spindel 80 (55cm) = max. kombinierte Höhe
  const maxWithFrame066 = LEVELING_FRAMES.FRAME_066.height_m + SPINDLE_VARIANTS.SPINDLE_80.maxHeight_m; // 1.21m
  const maxWithFrame100 = LEVELING_FRAMES.FRAME_100.height_m + SPINDLE_VARIANTS.SPINDLE_80.maxHeight_m; // 1.55m
  const maxWithFrame150 = LEVELING_FRAMES.FRAME_150.height_m + SPINDLE_VARIANTS.SPINDLE_80.maxHeight_m; // 2.05m
  const maxWithFrame200 = LEVELING_FRAMES.FRAME_200.height_m + SPINDLE_VARIANTS.SPINDLE_80.maxHeight_m; // 2.55m

  if (diff <= maxWithFrame066) {
    return {
      spindle: SPINDLE_VARIANTS.SPINDLE_80,
      needsLevelingFrame: true,
      levelingFrame: LEVELING_FRAMES.FRAME_066,
    };
  }
  if (diff <= maxWithFrame100) {
    return {
      spindle: SPINDLE_VARIANTS.SPINDLE_80,
      needsLevelingFrame: true,
      levelingFrame: LEVELING_FRAMES.FRAME_100,
    };
  }
  if (diff <= maxWithFrame150) {
    return {
      spindle: SPINDLE_VARIANTS.SPINDLE_80,
      needsLevelingFrame: true,
      levelingFrame: LEVELING_FRAMES.FRAME_150,
    };
  }
  if (diff <= maxWithFrame200) {
    return {
      spindle: SPINDLE_VARIANTS.SPINDLE_80,
      needsLevelingFrame: true,
      levelingFrame: LEVELING_FRAMES.FRAME_200,
    };
  }

  // Über 2.55m: Spezielle Fundamentierung
  return { spindle: null, needsLevelingFrame: true };
}

/**
 * Validiert ein Terrain-Profil und generiert Warnungen
 *
 * @param terrainProfile Terrain-Profil aus extractTerrainProfile()
 * @param facadeLength_m Fassaden-Länge in Metern
 * @param fieldLength_m Feld-Länge (default: 2.57m)
 * @returns Array von strukturierten Warnungen
 */
export function validateTerrainProfile(
  terrainProfile: TerrainProfilePoint[],
  facadeLength_m: number,
  fieldLength_m: number = FIELD_LENGTHS.STANDARD
): TerrainWarning[] {
  const warnings: TerrainWarning[] = [];

  if (!terrainProfile || terrainProfile.length === 0) {
    return warnings;
  }

  // 1. Gesamt-Terrain-Differenz
  const zValues = terrainProfile.map((p) => p.z_terrain);
  const minZ = Math.min(...zValues);
  const maxZ = Math.max(...zValues);
  const totalDiff = maxZ - minZ;

  const slopeClass = classifySlope(totalDiff);
  const spindleInfo = getRequiredSpindle(totalDiff);

  // Gesamt-Bewertung
  // FIX 28.01.2026: Korrigierte Schwellenwerte gemäss Layher Katalog
  if (slopeClass === 'eben') {
    warnings.push({
      code: 'SPINDLE_SUFFICIENT',
      severity: 'info',
      message: `Ebenes Terrain (${totalDiff.toFixed(2)}m Differenz)`,
      details: 'Standard-Fußspindel 60 (max. 41cm) reicht aus.',
      recommendation: 'Keine besonderen Massnahmen nötig.',
      height_diff_m: totalDiff,
      suggestedMaterial: SPINDLE_VARIANTS.SPINDLE_60.artNr,
    });
  } else if (slopeClass === 'leicht') {
    if (totalDiff <= SPINDLE_VARIANTS.SPINDLE_80.maxHeight_m) {
      // ≤ 55cm
      warnings.push({
        code: 'SPINDLE_60_NEEDED',
        severity: 'info',
        message: `Leichte Hanglage (${totalDiff.toFixed(2)}m Differenz)`,
        details: 'Fußspindel 80 verstärkt (max. 55cm) empfohlen.',
        recommendation: 'Stellspindeln nach Terrain-Profil einstellen.',
        height_diff_m: totalDiff,
        suggestedMaterial: SPINDLE_VARIANTS.SPINDLE_80.artNr,
      });
    } else {
      // 55-82cm (Spindel 110 oder 150)
      const spindle = totalDiff <= SPINDLE_VARIANTS.SPINDLE_110.maxHeight_m
        ? SPINDLE_VARIANTS.SPINDLE_110
        : SPINDLE_VARIANTS.SPINDLE_150;
      warnings.push({
        code: 'SPINDLE_80_NEEDED',
        severity: 'warning',
        message: `Hanglage (${totalDiff.toFixed(2)}m Differenz)`,
        details: `${spindle.name} (max. ${(spindle.maxHeight_m * 100).toFixed(0)}cm) nötig.`,
        recommendation: 'Längere Stellspindeln verwenden.',
        height_diff_m: totalDiff,
        suggestedMaterial: spindle.artNr,
      });
    }
  } else if (slopeClass === 'mittel') {
    warnings.push({
      code: 'LEVELING_FRAME_NEEDED',
      severity: 'warning',
      message: `Starke Hanglage (${totalDiff.toFixed(2)}m Differenz)`,
      details: `Ausgleichsrahmen erforderlich: ${spindleInfo.levelingFrame?.name || 'nach Bedarf'}`,
      recommendation: 'Ausgleichsrahmen + Stellspindeln kombinieren.',
      height_diff_m: totalDiff,
      suggestedMaterial: spindleInfo.levelingFrame?.artNr,
    });
  } else {
    // stark (> 3.0m)
    warnings.push({
      code: 'SPECIAL_FOUNDATION',
      severity: 'error',
      message: `Extreme Hanglage (${totalDiff.toFixed(2)}m Differenz)`,
      details: 'Standard-Gerüstbau nicht möglich.',
      recommendation: 'Vor-Ort-Begehung und Spezialplanung erforderlich.',
      height_diff_m: totalDiff,
    });
  }

  // 2. Gefälle innerhalb einzelner Felder prüfen
  // (Wichtig: Wenn ein Feld > 40cm Gefälle hat, braucht man evtl. gestufte Spindeln)
  if (terrainProfile.length >= 2) {
    const numFields = Math.ceil(facadeLength_m / fieldLength_m);

    for (let i = 0; i < numFields; i++) {
      const fieldStart = i * fieldLength_m;
      const fieldEnd = Math.min((i + 1) * fieldLength_m, facadeLength_m);

      // Finde Terrain-Punkte in diesem Feld
      const pointsInField = terrainProfile.filter(
        (p) => p.position_m >= fieldStart - 0.1 && p.position_m <= fieldEnd + 0.1
      );

      if (pointsInField.length >= 2) {
        const fieldZValues = pointsInField.map((p) => p.z_terrain);
        const fieldMinZ = Math.min(...fieldZValues);
        const fieldMaxZ = Math.max(...fieldZValues);
        const fieldDiff = fieldMaxZ - fieldMinZ;

        // Warnung wenn Gefälle innerhalb eines Feldes > 20cm
        // (Dann sind die beiden Ständer eines Feldes unterschiedlich hoch)
        if (fieldDiff > 0.20) {
          warnings.push({
            code: 'STEEP_GRADIENT',
            severity: fieldDiff > 0.40 ? 'warning' : 'info',
            message: `Feld ${i + 1}: ${(fieldDiff * 100).toFixed(0)}cm Gefälle`,
            details: `Position ${fieldStart.toFixed(1)}m - ${fieldEnd.toFixed(1)}m`,
            recommendation:
              fieldDiff > 0.40
                ? 'Ständer-Spindeln unterschiedlich einstellen oder Feld teilen.'
                : 'Spindeln anpassen.',
            position_m: (fieldStart + fieldEnd) / 2,
            height_diff_m: fieldDiff,
          });
        }
      }
    }
  }

  // 3. Empfehlung für Vor-Ort-Prüfung bei komplexem Terrain
  if (terrainProfile.length >= 4 || slopeClass !== 'eben') {
    warnings.push({
      code: 'MANUAL_CHECK_RECOMMENDED',
      severity: 'info',
      message: 'Vor-Ort-Prüfung empfohlen',
      details: `${terrainProfile.length} Terrain-Punkte erfasst.`,
      recommendation: 'Terrain vor Montage mit Nivelliergerät prüfen.',
    });
  }

  return warnings;
}

/**
 * Validiert Ecken zwischen zwei Fassaden
 *
 * @param facade1ZMin Terrain-Höhe Ende Fassade 1
 * @param facade2ZMin Terrain-Höhe Start Fassade 2 (Ecke)
 * @param cornerIndex Index der Ecke (für Referenz)
 * @returns Warnung wenn Höhendifferenz > 10cm
 */
export function validateCornerTerrain(
  facade1ZMin: number | undefined,
  facade2ZMin: number | undefined,
  cornerIndex: number
): TerrainWarning | null {
  if (facade1ZMin === undefined || facade2ZMin === undefined) {
    return null;
  }

  const diff = Math.abs(facade1ZMin - facade2ZMin);

  if (diff > 0.10) {
    return {
      code: 'CORNER_HEIGHT_DIFF',
      severity: diff > 0.30 ? 'warning' : 'info',
      message: `Ecke ${cornerIndex + 1}: ${(diff * 100).toFixed(0)}cm Höhendifferenz`,
      details: `Fassaden treffen auf unterschiedlichen Terrain-Höhen.`,
      recommendation:
        diff > 0.30
          ? 'Eck-Ständer muss beide Höhen ausgleichen. Spezielle Montage erforderlich.'
          : 'Eck-Spindel entsprechend einstellen.',
      height_diff_m: diff,
    };
  }

  return null;
}

/**
 * Aggregiert Warnungen zu einer Zusammenfassung
 */
export function summarizeWarnings(warnings: TerrainWarning[]): {
  hasErrors: boolean;
  hasWarnings: boolean;
  errorCount: number;
  warningCount: number;
  infoCount: number;
  maxHeightDiff_m: number;
  suggestedSpindle: string | null;
  needsLevelingFrame: boolean;
} {
  const errorCount = warnings.filter((w) => w.severity === 'error').length;
  const warningCount = warnings.filter((w) => w.severity === 'warning').length;
  const infoCount = warnings.filter((w) => w.severity === 'info').length;

  const heightDiffs = warnings
    .filter((w) => w.height_diff_m !== undefined)
    .map((w) => w.height_diff_m as number);
  const maxHeightDiff_m = heightDiffs.length > 0 ? Math.max(...heightDiffs) : 0;

  const spindleInfo = getRequiredSpindle(maxHeightDiff_m);

  return {
    hasErrors: errorCount > 0,
    hasWarnings: warningCount > 0,
    errorCount,
    warningCount,
    infoCount,
    maxHeightDiff_m,
    suggestedSpindle: spindleInfo.spindle?.artNr || null,
    needsLevelingFrame: spindleInfo.needsLevelingFrame,
  };
}