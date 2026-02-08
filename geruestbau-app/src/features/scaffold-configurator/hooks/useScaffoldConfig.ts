/**
 * Scaffold Configurator - Zustand Store
 * Central state management for scaffold configuration
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  ScaffoldConfiguration,
  ScaffoldSettings,
  ScaffoldElement,
  ScaffoldFacade,
  ScaffoldCorner,
  ScaffoldTotals,
  WorkType,
  ScaffoldSystem,
  BayWidth,
  EditorTool,
  MainTab,
  SelectedFacade,
  FacadeDirection,
  RoofData,
} from '../types/scaffold.types';
import { FACADE_COLORS } from '../types/scaffold.types';

// ============ STORE INTERFACE ============

interface ScaffoldConfigState {
  // Navigation
  currentTab: MainTab;
  currentElementIndex: number;
  currentTool: EditorTool;

  // Configuration
  configuration: ScaffoldConfiguration | null;

  // Project info (from input)
  projectId: string | null;
  buildingName: string;
  buildingAddress: string;

  // UI State
  isLoading: boolean;
  error: string | null;
  isDirty: boolean; // Has unsaved changes

  // Actions - Navigation
  setCurrentTab: (tab: MainTab) => void;
  navigateCarousel: (direction: -1 | 1) => void;
  jumpToElement: (index: number) => void;
  setTool: (tool: EditorTool) => void;

  // Actions - Settings
  setWorkType: (type: WorkType) => void;
  setSystem: (system: ScaffoldSystem) => void;
  setBayWidth: (width: BayWidth) => void;
  toggleOption: (option: 'safety_net' | 'weather_cover') => void;

  // Actions - Facade Management
  toggleFacadeEnabled: (facadeId: string) => void;
  toggleCornerEnabled: (cornerId: string) => void;

  // Actions - Editor
  toggleCell: (facadeId: string, field: number, level: number) => void;
  toggleRow: (facadeId: string, field: number) => void;
  toggleLevel: (facadeId: string, level: number) => void;
  setLift: (facadeId: string, position: number | null) => void;
  setStairs: (facadeId: string, position: number | null) => void;

  // Actions - Initialization
  initializeFromFacades: (
    projectId: string,
    buildingName: string,
    buildingAddress: string,
    facades: SelectedFacade[],
    buildingPolygon?: [number, number][],  // ORIGINAL from swissBUILDINGS3D
    roof?: RoofData
  ) => void;
  reset: () => void;

  // Actions - Polygon Simplification
  simplifyPolygonEpsilon: number | null;  // null = auto, number = fixed epsilon
  setSimplifyEpsilon: (epsilon: number | null) => void;
  applySimplification: (newFacades: SelectedFacade[]) => void;

  // Computed getters
  getCurrentElement: () => ScaffoldElement | null;
  getVisibleElements: () => { prev: ScaffoldElement; current: ScaffoldElement; next: ScaffoldElement } | null;
  calculateTotals: () => ScaffoldTotals;
  getFacadeStats: (facadeId: string) => { total: number; removed: number; area: number; extras: number } | null;
}

// ============ HELPER FUNCTIONS ============

// NEU 27.01.2026: Höhenberechnung wird jetzt aus 3D-Geometrie gemacht
// Siehe extractTerrainProfile() in polygonSimplifier.ts
// Die alte calculateHeightsFromRawData() wurde entfernt (verwendete aggregierte Werte statt 3D-Geometrie)

// ============ LAYHER BLITZ 70 ELEMENT SIZES ============
// NEU 07.02.2026: Mixed element sizes for optimal scaffolding

// Available frame heights (m) - sorted descending for greedy algorithm
const LAYHER_FRAME_HEIGHTS = [2.0, 1.5, 1.0, 0.5] as const;

// Available field widths (m) - sorted descending for greedy algorithm
const LAYHER_FIELD_WIDTHS = [3.07, 2.57, 2.07, 1.57, 1.09, 0.73] as const;

/**
 * FIX 07.02.2026: Optimierte Elementberechnung mit gemischten Größen
 *
 * Greedy-Algorithmus: Wählt größtes passendes Element, wiederholt bis Ziel erreicht.
 * Ziel: Möglichst nah am Zielwert, leicht darüber (Sicherheit) aber nicht zu viel.
 *
 * @param targetLength Ziel-Länge/Höhe in Metern
 * @param availableSizes Verfügbare Element-Größen (absteigend sortiert)
 * @param tolerance Wie viel unter dem Ziel ist akzeptabel (z.B. 0.1m)
 * @returns Array der gewählten Element-Größen
 */
const calculateOptimalElements = (
  targetLength: number,
  availableSizes: readonly number[],
  tolerance: number = 0.1
): number[] => {
  const elements: number[] = [];
  let remaining = targetLength;

  // Greedy: Wähle größtes Element das passt, wiederhole
  while (remaining > tolerance) {
    // Find largest element that doesn't exceed remaining + tolerance significantly
    let bestSize = availableSizes[availableSizes.length - 1]; // Smallest as fallback

    for (const size of availableSizes) {
      if (size <= remaining + tolerance) {
        bestSize = size;
        break; // First (largest) that fits
      }
    }

    // If even smallest exceeds target but we need at least one element
    if (elements.length === 0 && remaining < bestSize) {
      // Use smallest element that exceeds target minimally
      for (let i = availableSizes.length - 1; i >= 0; i--) {
        if (availableSizes[i] >= remaining) {
          bestSize = availableSizes[i];
          // Keep looking for smaller one that still covers
        }
      }
    }

    elements.push(bestSize);
    remaining -= bestSize;

    // Safety: Prevent infinite loop
    if (elements.length > 50) {
      console.warn('[calculateOptimalElements] Max iterations reached');
      break;
    }
  }

  return elements;
};

/**
 * Berechnet die Summe der Element-Größen
 */
const sumElements = (elements: number[]): number => {
  return elements.reduce((sum, el) => sum + el, 0);
};

const createDefaultSettings = (): ScaffoldSettings => ({
  work_type: 'roof',
  system: 'layher_blitz',
  field_width_m: 2.57,
  level_height_m: 2.0,
  bay_width_m: 0.73,
  safety_net: true,
  weather_cover: false,
});

// FIX 27.01.2026: 'full' ersetzt durch 'roofer' mit Giebel-Logik
// FIX 08.02.2026: baseHeightM ist jetzt trauf_height_m (bereits Traufhöhe!)
//                 → KEINE Giebel-Subtraktion mehr nötig!
//                 → Giebel-Info wird nur für 'roofer' Modus verwendet (Spengler braucht First-Zugang)
// FIX 07.02.2026: Mixed element sizes - greedy algorithm statt Math.ceil
const calculateFieldsAndLevels = (
  lengthM: number,
  baseHeightM: number,  // FIX 08.02.2026: Jetzt trauf_height_m (bereits Traufhöhe aus Wall-Polygon!)
  _fieldWidthM: number,  // UNUSED seit 07.02.2026 - gemischte Feldbreiten statt fixer Wert
  _levelHeightM: number, // UNUSED seit 07.02.2026 - gemischte Rahmenhöhen statt fixer Wert
  workType: WorkType,
  _firstHeightM?: number,  // UNUSED seit 05.02.2026 - behalten für API-Kompatibilität
  isGiebel?: boolean,     // Giebel-Fassade?
  giebelHeightM?: number  // Giebel-Dreieck-Höhe (für Spengler-Modus)
): {
  fields: number;
  levels: number;
  targetHeight: number;
  // NEU 07.02.2026: Detaillierte Element-Listen
  frameHeights?: number[];  // Z.B. [2.0, 2.0, 2.0, 1.0] = 7m
  fieldWidths?: number[];   // Z.B. [3.07, 3.07, 2.57] = 8.71m
  actualHeight?: number;    // Summe frameHeights
  actualLength?: number;    // Summe fieldWidths
} => {
  // FIX 08.02.2026: baseHeightM ist BEREITS die Traufhöhe (aus matchFacadeToWall.trauf_height_m)
  // Keine Giebel-Subtraktion mehr nötig!
  const traufHeightM = baseHeightM;

  // Target height based on work type
  let targetHeight: number;
  switch (workType) {
    case 'facade':
      // Gerüst bis Traufe
      targetHeight = traufHeightM;
      break;
    case 'roof':
      // Traufe + 1m Absturzsicherung
      targetHeight = traufHeightM + 1.0;
      break;
    case 'roofer':
      // Spengler: Bei Giebel-Fassaden bis First-1m, sonst Traufe-1m
      // FIX 08.02.2026: Bei Giebel-Fassaden die Giebel-Höhe ADDIEREN
      // da baseHeightM = Traufhöhe, aber Spengler braucht Zugang zum First
      if (isGiebel && giebelHeightM && giebelHeightM > 0) {
        // Giebel-Fassade: First-Höhe = Traufe + Giebel, dann -1m für Arbeitsplattform
        targetHeight = traufHeightM + giebelHeightM - 1.0;
      } else {
        // Trauf-Fassade: Traufe - 1m für Arbeitsplattform
        targetHeight = traufHeightM - 1.0;
      }
      break;
    default:
      targetHeight = traufHeightM;
  }

  // FIX 07.02.2026: Use mixed element sizes instead of Math.ceil
  // Height: Use optimal combination of 2.0m, 1.5m, 1.0m, 0.5m frames
  const frameHeights = calculateOptimalElements(targetHeight, LAYHER_FRAME_HEIGHTS, 0.1);
  const actualHeight = sumElements(frameHeights);
  const levels = frameHeights.length;

  // Length: Use optimal combination of field widths
  const fieldWidths = calculateOptimalElements(lengthM, LAYHER_FIELD_WIDTHS, 0.1);
  const actualLength = sumElements(fieldWidths);
  const fields = fieldWidths.length;

  // Debug logging
  console.log(`[calculateFieldsAndLevels] Target: ${targetHeight.toFixed(2)}m height, ${lengthM.toFixed(2)}m length`);
  console.log(`  → Height: ${frameHeights.join(' + ')} = ${actualHeight.toFixed(2)}m (${levels} frames)`);
  console.log(`  → Length: ${fieldWidths.join(' + ')} = ${actualLength.toFixed(2)}m (${fields} fields)`);

  return {
    fields,
    levels,
    targetHeight,
    frameHeights,
    fieldWidths,
    actualHeight,
    actualLength,
  };
};

// FIX 27.01.2026: firstHeight für Spengler-Modus hinzugefügt
// FIX 07.02.2026: Gemischte Elementgrößen für optimale Gerüstkonfiguration
const createFacadeElement = (
  facade: SelectedFacade,
  settings: ScaffoldSettings,
  globalTerrainDiff?: number,  // NEU 14.01.2026: Globale Terrain-Differenz für Hanglage
  firstHeight?: number         // NEU 27.01.2026: Firsthöhe für Spengler-Modus
): ScaffoldFacade => {
  // FIX 07.02.2026: Neue Felder für gemischte Elementgrößen
  const {
    fields,
    levels,
    targetHeight,
    frameHeights,
    fieldWidths,
    actualHeight,
    actualLength,
  } = calculateFieldsAndLevels(
    facade.length_m,
    facade.height_m,  // Traufhöhe (base)
    settings.field_width_m,
    settings.level_height_m,
    settings.work_type,
    firstHeight,           // Firsthöhe für Spengler
    facade.is_giebel,      // Giebel-Fassade?
    facade.giebel_height_m // Giebel-Dreieck-Höhe
  );

  const directionNames: Record<FacadeDirection, string> = {
    'N': 'Nord', 'NE': 'Nordost', 'E': 'Ost', 'SE': 'Südost',
    'S': 'Süd', 'SW': 'Südwest', 'W': 'West', 'NW': 'Nordwest',
  };

  return {
    type: 'facade',
    id: facade.id,
    facade_ref: facade.id,
    name: directionNames[facade.direction] || facade.direction,  // Fallback to raw direction code
    direction: facade.direction,
    length_m: facade.length_m,
    base_height_m: facade.height_m,  // FIX 27.01.2026: Originale Traufhöhe speichern
    first_height_m: firstHeight,     // NEU 27.01.2026: Firsthöhe für Spengler-Modus
    is_giebel: facade.is_giebel,     // NEU 27.01.2026: Giebel-Fassade?
    giebel_height_m: facade.giebel_height_m, // NEU 27.01.2026: Giebel-Dreieck-Höhe
    target_height_m: targetHeight,
    slope_percent: facade.slope_percent,
    fields,
    levels,
    // NEU 07.02.2026: Gemischte Elementgrößen für optimale Gerüstkonfiguration
    frameHeights,
    fieldWidths,
    actualHeight,
    actualLength,
    // Fallback color for unknown direction codes (supports both German NO/O/SO and English NE/E/SE)
    color: FACADE_COLORS[facade.direction] || '#6B7280',  // gray-500 as fallback
    enabled: false, // No facades enabled by default - user must select
    modifications: {
      removed_cells: new Set<string>(),
      lift_position: null,
      stairs_position: null,
    },
    // Include coordinates for 3D positioning
    start_point: facade.start_point,
    end_point: facade.end_point,
    // NEU 19.01.2026: Original-Polygon-Segmente für exakte 3D-Platzierung
    originalSegments: facade.originalSegments,
    // NEU 14.01.2026: Terrain-Daten für Hanglage-Darstellung
    terrain_z_min: facade.facade_z_min,
    terrain_z_max: facade.facade_z_max,
    terrain_diff_m: globalTerrainDiff,
    // NEU 27.01.2026: Terrain-Profil und Warnungen für Stellspindel-Berechnung
    terrain_profile: facade.terrain_profile,
    terrain_warnings: facade.terrain_warnings,
  };
};

const createCornerElement = (
  id: string,
  name: string,
  connects: [string, string],
  maxLevels: number
): ScaffoldCorner => ({
  type: 'corner',
  id,
  name,
  connects,
  corner_posts: 4,
  diagonals: maxLevels * 2,
  enabled: false, // Corners disabled by default (depend on facade selection)
});

// NEU 27.01.2026: roof Parameter für Firsthöhe (Spengler-Modus)
const createElementsFromFacades = (
  facades: SelectedFacade[],
  settings: ScaffoldSettings,
  roof?: RoofData
): ScaffoldElement[] => {
  const elements: ScaffoldElement[] = [];
  const facadeElements: ScaffoldFacade[] = [];

  // NEU 14.01.2026: Globale Terrain-Differenz berechnen für Hanglage
  const zMinValues = facades
    .map(f => f.facade_z_min)
    .filter((v): v is number => v !== undefined && !isNaN(v));
  const globalTerrainDiff = zMinValues.length > 0
    ? Math.max(...zMinValues) - Math.min(...zMinValues)
    : 0;
  const minTerrainZ = zMinValues.length > 0 ? Math.min(...zMinValues) : undefined;

  // NEU 27.01.2026: Firsthöhe relativ für Spengler-Modus berechnen
  // roof_dach_max_m (absolute Höhe ü.M.) - terrain_z_min = relative Firsthöhe
  let firstHeight: number | undefined;
  if (roof?.roof_dach_max_m && minTerrainZ !== undefined) {
    firstHeight = roof.roof_dach_max_m - minTerrainZ;
  } else if (roof?.terrain_z_min && roof?.roof_dach_max_m) {
    // Fallback: terrain_z_min aus roof verwenden
    firstHeight = roof.roof_dach_max_m - roof.terrain_z_min;
  }

  // Create facade elements
  facades.forEach((facade) => {
    const facadeEl = createFacadeElement(facade, settings, globalTerrainDiff, firstHeight);
    facadeElements.push(facadeEl);
  });

  // Interleave facades with corners
  const directionOrder: FacadeDirection[] = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const sortedFacades = [...facadeElements].sort((a, b) => {
    return directionOrder.indexOf(a.direction) - directionOrder.indexOf(b.direction);
  });

  sortedFacades.forEach((facade, index) => {
    elements.push(facade);

    // Add corner after each facade (connecting to next)
    if (sortedFacades.length > 1) {
      const nextFacade = sortedFacades[(index + 1) % sortedFacades.length];
      const cornerNames: Record<string, string> = {
        'N-E': 'Ecke NO', 'E-S': 'Ecke SO', 'S-W': 'Ecke SW', 'W-N': 'Ecke NW',
        'N-NE': 'Ecke N-NO', 'NE-E': 'Ecke NO-O', // etc.
      };
      const cornerKey = `${facade.direction}-${nextFacade.direction}`;
      const cornerId = `corner-${facade.direction.toLowerCase()}-${nextFacade.direction.toLowerCase()}`;
      const maxLevels = Math.max(facade.levels, nextFacade.levels);

      elements.push(createCornerElement(
        cornerId,
        cornerNames[cornerKey] || `Ecke ${facade.direction}/${nextFacade.direction}`,
        [facade.id, nextFacade.id],
        maxLevels
      ));
    }
  });

  return elements;
};

// ============ STORE IMPLEMENTATION ============

export const useScaffoldConfig = create<ScaffoldConfigState>()(
  persist(
    (set, get) => ({
      // Initial state
      currentTab: 'facade',
      currentElementIndex: 0,
      currentTool: 'select',
      configuration: null,
      projectId: null,
      buildingName: '',
      buildingAddress: '',
      isLoading: false,
      error: null,
      isDirty: false,
      simplifyPolygonEpsilon: null,  // null = auto

      // Navigation actions
      setCurrentTab: (tab) => {
        const { configuration, currentElementIndex } = get();

        // When switching to editor, ensure we're on an enabled element
        if (tab === 'editor' && configuration) {
          const currentEl = configuration.elements[currentElementIndex];
          if (!currentEl?.enabled) {
            // Find first enabled element
            const firstEnabledIdx = configuration.elements.findIndex(el => el.enabled);
            if (firstEnabledIdx !== -1) {
              set({ currentTab: tab, currentElementIndex: firstEnabledIdx });
              return;
            }
          }
        }

        set({ currentTab: tab });
      },

      navigateCarousel: (direction) => {
        const { configuration, currentElementIndex } = get();
        if (!configuration) return;

        const elements = configuration.elements;
        const total = elements.length;

        // Find next enabled element in the given direction
        let newIndex = currentElementIndex;
        for (let i = 0; i < total; i++) {
          newIndex = (newIndex + direction + total) % total;
          const el = elements[newIndex];
          // Skip disabled facades and corners of disabled facades
          if (el.type === 'facade' && el.enabled) break;
          if (el.type === 'corner' && el.enabled) break;
        }

        set({ currentElementIndex: newIndex });
      },

      jumpToElement: (index) => {
        const { configuration } = get();
        if (!configuration) return;

        if (index >= 0 && index < configuration.elements.length) {
          set({ currentElementIndex: index, currentTab: 'editor' });
        }
      },

      setTool: (tool) => set({ currentTool: tool }),

      // Settings actions
      setWorkType: (type) => {
        const { configuration } = get();
        if (!configuration) return;

        // DEBUG 02.02.2026: Log work type change
        console.log(`[setWorkType] Changing work type from ${configuration.settings.work_type} to ${type}`);

        const newSettings = { ...configuration.settings, work_type: type };

        // FIX 27.01.2026: Recalculate using base_height_m (not the old target_height_m hack)
        // NEU 27.01.2026: Giebel-Parameter für Spengler-Modus (roofer)
        // FIX 07.02.2026: Recalculate with mixed element sizes
        const newElements = configuration.elements.map((el) => {
          if (el.type === 'facade') {
            // Use base_height_m (original eaves height) as the basis for calculation
            const baseHeight = el.base_height_m || el.target_height_m;  // Fallback for old data
            const {
              fields,
              levels,
              targetHeight,
              frameHeights,
              fieldWidths,
              actualHeight,
              actualLength,
            } = calculateFieldsAndLevels(
              el.length_m,
              baseHeight,
              newSettings.field_width_m,
              newSettings.level_height_m,
              type,
              el.first_height_m,   // NEU 27.01.2026: Firsthöhe für Spengler
              el.is_giebel,        // NEU 27.01.2026: Giebel-Fassade?
              el.giebel_height_m   // NEU 27.01.2026: Giebel-Dreieck-Höhe
            );
            // DEBUG 02.02.2026: Log calculated values
            console.log(`[setWorkType] Facade ${el.id}: base=${baseHeight}m -> target=${targetHeight}m, levels=${levels}`);
            return {
              ...el,
              fields,
              levels,
              target_height_m: targetHeight,
              // NEU 07.02.2026: Gemischte Elementgrößen
              frameHeights,
              fieldWidths,
              actualHeight,
              actualLength,
            };
          }
          return el;
        });

        set({
          configuration: {
            ...configuration,
            settings: newSettings,
            elements: newElements,
            updated_at: new Date().toISOString(),
          },
          isDirty: true,
        });
      },

      setSystem: (system) => {
        const { configuration } = get();
        if (!configuration) return;

        const fieldWidth = system === 'layher_blitz' ? 2.57 : 3.07;
        const newSettings = { ...configuration.settings, system, field_width_m: fieldWidth as 2.57 | 3.07 };

        // FIX 07.02.2026: Recalculate with mixed element sizes (not just Math.ceil)
        const newElements = configuration.elements.map((el) => {
          if (el.type === 'facade') {
            const baseHeight = el.base_height_m || el.target_height_m;
            const {
              fields,
              levels,
              targetHeight,
              frameHeights,
              fieldWidths,
              actualHeight,
              actualLength,
            } = calculateFieldsAndLevels(
              el.length_m,
              baseHeight,
              newSettings.field_width_m,
              newSettings.level_height_m,
              configuration.settings.work_type,
              el.first_height_m,
              el.is_giebel,
              el.giebel_height_m
            );
            return {
              ...el,
              fields,
              levels,
              target_height_m: targetHeight,
              frameHeights,
              fieldWidths,
              actualHeight,
              actualLength,
            };
          }
          return el;
        });

        set({
          configuration: {
            ...configuration,
            settings: newSettings,
            elements: newElements,
            updated_at: new Date().toISOString(),
          },
          isDirty: true,
        });
      },

      setBayWidth: (width) => {
        const { configuration } = get();
        if (!configuration) return;

        set({
          configuration: {
            ...configuration,
            settings: { ...configuration.settings, bay_width_m: width },
            updated_at: new Date().toISOString(),
          },
          isDirty: true,
        });
      },

      toggleOption: (option) => {
        const { configuration } = get();
        if (!configuration) return;

        set({
          configuration: {
            ...configuration,
            settings: {
              ...configuration.settings,
              [option]: !configuration.settings[option],
            },
            updated_at: new Date().toISOString(),
          },
          isDirty: true,
        });
      },

      // Facade Management
      toggleFacadeEnabled: (facadeId) => {
        const { configuration, currentElementIndex } = get();
        if (!configuration) return;

        const newElements = configuration.elements.map((el) => {
          if (el.type === 'facade' && el.id === facadeId) {
            return { ...el, enabled: !el.enabled };
          }
          // Also toggle related corners
          if (el.type === 'corner') {
            const [id1, id2] = el.connects;
            // Find if this corner connects to the toggled facade
            const facade = configuration.elements.find(
              (e) => e.type === 'facade' && e.id === facadeId
            ) as ScaffoldFacade | undefined;
            if (facade && (id1 === facadeId || id2 === facadeId)) {
              // Corner is enabled only if BOTH facades are enabled
              const otherFacadeId = id1 === facadeId ? id2 : id1;
              const otherFacade = configuration.elements.find(
                (e) => e.type === 'facade' && e.id === otherFacadeId
              ) as ScaffoldFacade | undefined;
              const newFacadeEnabled = !facade.enabled;
              const cornerEnabled = newFacadeEnabled && (otherFacade?.enabled ?? false);
              return { ...el, enabled: cornerEnabled };
            }
          }
          return el;
        });

        // Check if current element became disabled, jump to first enabled
        const currentEl = newElements[currentElementIndex];
        let newIndex = currentElementIndex;
        if (currentEl && !currentEl.enabled) {
          const firstEnabledIdx = newElements.findIndex(el => el.enabled);
          if (firstEnabledIdx !== -1) {
            newIndex = firstEnabledIdx;
          }
        }

        set({
          configuration: {
            ...configuration,
            elements: newElements,
            updated_at: new Date().toISOString(),
          },
          currentElementIndex: newIndex,
          isDirty: true,
        });
      },

      toggleCornerEnabled: (cornerId) => {
        const { configuration } = get();
        if (!configuration) return;

        const newElements = configuration.elements.map((el) => {
          if (el.type === 'corner' && el.id === cornerId) {
            return { ...el, enabled: !el.enabled };
          }
          return el;
        });

        set({
          configuration: {
            ...configuration,
            elements: newElements,
            updated_at: new Date().toISOString(),
          },
          isDirty: true,
        });
      },

      // Editor actions
      toggleCell: (facadeId, field, level) => {
        const { configuration } = get();
        if (!configuration) return;

        const key = `${field}-${level}`;
        const newElements = configuration.elements.map((el) => {
          if (el.type === 'facade' && el.id === facadeId) {
            const newRemoved = new Set(el.modifications.removed_cells);
            if (newRemoved.has(key)) {
              newRemoved.delete(key);
            } else {
              newRemoved.add(key);
            }
            return {
              ...el,
              modifications: { ...el.modifications, removed_cells: newRemoved },
            };
          }
          return el;
        });

        set({
          configuration: { ...configuration, elements: newElements, updated_at: new Date().toISOString() },
          isDirty: true,
        });
      },

      toggleRow: (facadeId, field) => {
        const { configuration } = get();
        if (!configuration) return;

        const newElements = configuration.elements.map((el) => {
          if (el.type === 'facade' && el.id === facadeId) {
            const newRemoved = new Set(el.modifications.removed_cells);
            let removedCount = 0;

            // Count how many in this row are removed
            for (let l = 0; l < el.levels; l++) {
              if (newRemoved.has(`${field}-${l}`)) removedCount++;
            }

            // If more than half removed, restore all; otherwise remove all
            const restore = removedCount > el.levels / 2;
            for (let l = 0; l < el.levels; l++) {
              const key = `${field}-${l}`;
              if (restore) {
                newRemoved.delete(key);
              } else {
                newRemoved.add(key);
              }
            }

            return {
              ...el,
              modifications: { ...el.modifications, removed_cells: newRemoved },
            };
          }
          return el;
        });

        set({
          configuration: { ...configuration, elements: newElements, updated_at: new Date().toISOString() },
          isDirty: true,
        });
      },

      toggleLevel: (facadeId, level) => {
        const { configuration } = get();
        if (!configuration) return;

        const newElements = configuration.elements.map((el) => {
          if (el.type === 'facade' && el.id === facadeId) {
            const newRemoved = new Set(el.modifications.removed_cells);
            let removedCount = 0;

            // Count how many in this level are removed
            for (let f = 0; f < el.fields; f++) {
              if (newRemoved.has(`${f}-${level}`)) removedCount++;
            }

            // If more than half removed, restore all; otherwise remove all
            const restore = removedCount > el.fields / 2;
            for (let f = 0; f < el.fields; f++) {
              const key = `${f}-${level}`;
              if (restore) {
                newRemoved.delete(key);
              } else {
                newRemoved.add(key);
              }
            }

            return {
              ...el,
              modifications: { ...el.modifications, removed_cells: newRemoved },
            };
          }
          return el;
        });

        set({
          configuration: { ...configuration, elements: newElements, updated_at: new Date().toISOString() },
          isDirty: true,
        });
      },

      setLift: (facadeId, position) => {
        const { configuration } = get();
        if (!configuration) return;

        const newElements = configuration.elements.map((el) => {
          if (el.type === 'facade' && el.id === facadeId) {
            // If placing lift where stairs are, remove stairs
            const stairsPosition = el.modifications.stairs_position === position
              ? null
              : el.modifications.stairs_position;
            return {
              ...el,
              modifications: { ...el.modifications, lift_position: position, stairs_position: stairsPosition },
            };
          }
          return el;
        });

        set({
          configuration: { ...configuration, elements: newElements, updated_at: new Date().toISOString() },
          isDirty: true,
        });
      },

      setStairs: (facadeId, position) => {
        const { configuration } = get();
        if (!configuration) return;

        const newElements = configuration.elements.map((el) => {
          if (el.type === 'facade' && el.id === facadeId) {
            // If placing stairs where lift is, remove lift
            const liftPosition = el.modifications.lift_position === position
              ? null
              : el.modifications.lift_position;
            return {
              ...el,
              modifications: { ...el.modifications, stairs_position: position, lift_position: liftPosition },
            };
          }
          return el;
        });

        set({
          configuration: { ...configuration, elements: newElements, updated_at: new Date().toISOString() },
          isDirty: true,
        });
      },

      // Initialization
      initializeFromFacades: (projectId, buildingName, buildingAddress, facades, buildingPolygon, roof) => {
        const settings = createDefaultSettings();
        // NEU 27.01.2026: roof für Firsthöhe (Spengler-Modus) übergeben
        const elements = createElementsFromFacades(facades, settings, roof);
        const now = new Date().toISOString();

        const configuration: ScaffoldConfiguration = {
          project_id: projectId,
          created_at: now,
          updated_at: now,
          settings,
          elements,
          totals: {
            scaffold_area_m2: 0,
            facade_count: facades.length,
            corner_count: facades.length, // One corner per facade in a closed loop
            max_height_m: 0,
            perimeter_m: 0,
            estimated_weight_kg: 0,
          },
          // Store building polygon (ORIGINAL from swissBUILDINGS3D)
          buildingPolygon,
          // Store roof data for 3D visualization
          roof,
        };

        set({
          configuration,
          projectId,
          buildingName,
          buildingAddress,
          currentElementIndex: 0,
          currentTab: 'facade',
          currentTool: 'select',
          isDirty: false,
          error: null,
        });
      },

      reset: () => set({
        currentTab: 'facade',
        currentElementIndex: 0,
        currentTool: 'select',
        configuration: null,
        projectId: null,
        buildingName: '',
        buildingAddress: '',
        isLoading: false,
        error: null,
        isDirty: false,
        simplifyPolygonEpsilon: null,
      }),

      // Polygon Simplification Actions
      setSimplifyEpsilon: (epsilon) => set({ simplifyPolygonEpsilon: epsilon }),

      applySimplification: (newFacades) => {
        const { configuration } = get();
        if (!configuration) return;

        const settings = configuration.settings;
        // NEU 27.01.2026: roof für Firsthöhe (Spengler-Modus) übergeben
        const elements = createElementsFromFacades(newFacades, settings, configuration.roof);
        const now = new Date().toISOString();

        set({
          configuration: {
            ...configuration,
            elements,
            totals: {
              ...configuration.totals,
              facade_count: newFacades.length,
              corner_count: newFacades.length,
            },
            updated_at: now,
          },
          currentElementIndex: 0,
          isDirty: true,
        });
      },

      // Computed getters
      getCurrentElement: () => {
        const { configuration, currentElementIndex } = get();
        if (!configuration) return null;
        return configuration.elements[currentElementIndex] || null;
      },

      getVisibleElements: () => {
        const { configuration, currentElementIndex } = get();
        if (!configuration || configuration.elements.length === 0) return null;

        const elements = configuration.elements;
        const total = elements.length;
        const current = elements[currentElementIndex];

        // Find prev enabled element
        let prevIdx = currentElementIndex;
        for (let i = 0; i < total; i++) {
          prevIdx = (prevIdx - 1 + total) % total;
          const el = elements[prevIdx];
          if ((el.type === 'facade' || el.type === 'corner') && el.enabled) break;
        }

        // Find next enabled element
        let nextIdx = currentElementIndex;
        for (let i = 0; i < total; i++) {
          nextIdx = (nextIdx + 1) % total;
          const el = elements[nextIdx];
          if ((el.type === 'facade' || el.type === 'corner') && el.enabled) break;
        }

        return {
          prev: elements[prevIdx],
          current: current,
          next: elements[nextIdx],
        };
      },

      calculateTotals: () => {
        const { configuration } = get();
        if (!configuration) {
          return {
            scaffold_area_m2: 0,
            facade_count: 0,
            corner_count: 0,
            max_height_m: 0,
            perimeter_m: 0,
            estimated_weight_kg: 0,
          };
        }

        let totalArea = 0;
        let maxHeight = 0;
        let perimeter = 0;
        let facadeCount = 0;
        let cornerCount = 0;

        configuration.elements.forEach((el) => {
          if (el.type === 'facade') {
            if (!el.enabled) return; // Skip disabled facades
            facadeCount++;
            const totalCells = el.fields * el.levels;
            const removedCells = el.modifications.removed_cells.size;
            const activeCells = totalCells - removedCells;
            const cellArea = configuration.settings.field_width_m * configuration.settings.level_height_m;
            totalArea += activeCells * cellArea;
            maxHeight = Math.max(maxHeight, el.target_height_m);
            perimeter += el.length_m;
          } else if (el.type === 'corner' && el.enabled) {
            cornerCount++;
          }
        });

        const estimatedWeight = Math.round(totalArea * 28); // ~28 kg/m²

        return {
          scaffold_area_m2: Math.round(totalArea),
          facade_count: facadeCount,
          corner_count: cornerCount,
          max_height_m: maxHeight,
          perimeter_m: perimeter,
          estimated_weight_kg: estimatedWeight,
        };
      },

      getFacadeStats: (facadeId) => {
        const { configuration } = get();
        if (!configuration) return null;

        const facade = configuration.elements.find(
          (el) => el.type === 'facade' && el.id === facadeId
        ) as ScaffoldFacade | undefined;

        if (!facade) return null;

        const total = facade.fields * facade.levels;
        const removed = facade.modifications.removed_cells.size;
        const cellArea = configuration.settings.field_width_m * configuration.settings.level_height_m;
        const area = Math.round((total - removed) * cellArea);

        let extras = 0;
        if (facade.modifications.lift_position !== null) extras++;
        if (facade.modifications.stairs_position !== null) extras++;

        return { total, removed, area, extras };
      },
    }),
    {
      name: 'scaffold-config-storage',
      // Custom serialization for Set objects
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name);
          if (!str) return null;
          const parsed = JSON.parse(str);

          // FIX 02.02.2026: Migriere alte Konfigurationen ohne base_height_m
          // Das Feld wurde am 27.01.2026 hinzugefügt - alte Daten haben es nicht
          const workType = parsed.state?.configuration?.settings?.work_type;

          // Convert removed_cells arrays back to Sets AND migrate base_height_m
          if (parsed.state?.configuration?.elements) {
            parsed.state.configuration.elements = parsed.state.configuration.elements.map((el: any) => {
              if (el.type === 'facade') {
                // Migrate base_height_m if missing
                let baseHeight = el.base_height_m;
                if (baseHeight === undefined || baseHeight === null) {
                  // Rückrechnung aus target_height_m basierend auf work_type
                  const targetHeight = el.target_height_m || 0;
                  switch (workType) {
                    case 'facade':
                      baseHeight = targetHeight; // Keine Änderung
                      break;
                    case 'roof':
                      baseHeight = targetHeight - 1.0; // +1m Offset entfernen
                      break;
                    case 'roofer':
                      // Bei roofer ist die Berechnung komplex - Fallback auf target
                      baseHeight = targetHeight > 2 ? targetHeight - 2.0 : targetHeight;
                      break;
                    default:
                      baseHeight = targetHeight;
                  }
                  console.log(`[Storage] Migrated base_height_m for facade ${el.id}: ${baseHeight}m (from target ${targetHeight}m, workType: ${workType})`);
                }

                return {
                  ...el,
                  base_height_m: baseHeight,
                  modifications: el.modifications?.removed_cells ? {
                    ...el.modifications,
                    removed_cells: new Set(el.modifications.removed_cells),
                  } : el.modifications,
                };
              }
              return el;
            });
          }

          return parsed;
        },
        setItem: (name, value) => {
          // Convert Sets to arrays for JSON serialization
          const toStore = {
            ...value,
            state: {
              ...value.state,
              configuration: value.state.configuration ? {
                ...value.state.configuration,
                elements: value.state.configuration.elements.map((el: any) => {
                  if (el.type === 'facade' && el.modifications?.removed_cells instanceof Set) {
                    return {
                      ...el,
                      modifications: {
                        ...el.modifications,
                        removed_cells: Array.from(el.modifications.removed_cells),
                      },
                    };
                  }
                  return el;
                }),
              } : null,
            },
          };
          localStorage.setItem(name, JSON.stringify(toStore));
        },
        removeItem: (name) => localStorage.removeItem(name),
      },
    }
  )
);

// ============ SELECTOR HOOKS ============

export const useCurrentElement = () => useScaffoldConfig((state) => state.getCurrentElement());
export const useVisibleElements = () => useScaffoldConfig((state) => state.getVisibleElements());
export const useTotals = () => useScaffoldConfig((state) => state.calculateTotals());
export const useSettings = () => useScaffoldConfig((state) => state.configuration?.settings);
export const useElements = () => useScaffoldConfig((state) => state.configuration?.elements ?? []);
