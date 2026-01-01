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
    buildingPolygon?: [number, number][],
    roof?: RoofData
  ) => void;
  reset: () => void;

  // Computed getters
  getCurrentElement: () => ScaffoldElement | null;
  getVisibleElements: () => { prev: ScaffoldElement; current: ScaffoldElement; next: ScaffoldElement } | null;
  calculateTotals: () => ScaffoldTotals;
  getFacadeStats: (facadeId: string) => { total: number; removed: number; area: number; extras: number } | null;
}

// ============ HELPER FUNCTIONS ============

const createDefaultSettings = (): ScaffoldSettings => ({
  work_type: 'roof',
  system: 'layher_blitz',
  field_width_m: 2.57,
  level_height_m: 2.0,
  bay_width_m: 0.73,
  safety_net: true,
  weather_cover: false,
});

const calculateFieldsAndLevels = (
  lengthM: number,
  heightM: number,
  fieldWidthM: number,
  levelHeightM: number,
  workType: WorkType
): { fields: number; levels: number; targetHeight: number } => {
  // Target height based on work type
  let targetHeight: number;
  switch (workType) {
    case 'facade':
      targetHeight = heightM;
      break;
    case 'roof':
      targetHeight = heightM + 1.0; // +1m fall protection
      break;
    case 'full':
      targetHeight = heightM + 2.5; // Up to ridge
      break;
  }

  const fields = Math.ceil(lengthM / fieldWidthM);
  const levels = Math.ceil(targetHeight / levelHeightM);

  return { fields, levels, targetHeight };
};

const createFacadeElement = (
  facade: SelectedFacade,
  settings: ScaffoldSettings
): ScaffoldFacade => {
  const { fields, levels, targetHeight } = calculateFieldsAndLevels(
    facade.length_m,
    facade.height_m,
    settings.field_width_m,
    settings.level_height_m,
    settings.work_type
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
    target_height_m: targetHeight,
    slope_percent: facade.slope_percent,
    fields,
    levels,
    // Fallback color for unknown direction codes (supports both German NO/O/SO and English NE/E/SE)
    color: FACADE_COLORS[facade.direction] || '#6B7280',  // gray-500 as fallback
    enabled: true, // All facades enabled by default
    modifications: {
      removed_cells: new Set<string>(),
      lift_position: null,
      stairs_position: null,
    },
    // Include coordinates for 3D positioning
    start_point: facade.start_point,
    end_point: facade.end_point,
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
  enabled: true,
});

const createElementsFromFacades = (
  facades: SelectedFacade[],
  settings: ScaffoldSettings
): ScaffoldElement[] => {
  const elements: ScaffoldElement[] = [];
  const facadeElements: ScaffoldFacade[] = [];

  // Create facade elements
  facades.forEach((facade) => {
    const facadeEl = createFacadeElement(facade, settings);
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

        const newSettings = { ...configuration.settings, work_type: type };

        // Recalculate fields/levels for all facades
        const newElements = configuration.elements.map((el) => {
          if (el.type === 'facade') {
            const { fields, levels, targetHeight } = calculateFieldsAndLevels(
              el.length_m,
              el.target_height_m - (configuration.settings.work_type === 'roof' ? 1.0 : configuration.settings.work_type === 'full' ? 2.5 : 0),
              newSettings.field_width_m,
              newSettings.level_height_m,
              type
            );
            return { ...el, fields, levels, target_height_m: targetHeight };
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

        // Recalculate fields for all facades
        const newElements = configuration.elements.map((el) => {
          if (el.type === 'facade') {
            const fields = Math.ceil(el.length_m / fieldWidth);
            return { ...el, fields };
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
        const elements = createElementsFromFacades(facades, settings);
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
          // Store building polygon for 3D visualization
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
      }),

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

          // Convert removed_cells arrays back to Sets
          if (parsed.state?.configuration?.elements) {
            parsed.state.configuration.elements = parsed.state.configuration.elements.map((el: any) => {
              if (el.type === 'facade' && el.modifications?.removed_cells) {
                return {
                  ...el,
                  modifications: {
                    ...el.modifications,
                    removed_cells: new Set(el.modifications.removed_cells),
                  },
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
