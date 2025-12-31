/**
 * Scaffold Configurator Feature - Public API
 */

// Main component
export { default as ScaffoldConfigurator } from './components/ScaffoldConfigurator';

// Panels (for direct access if needed)
export { default as OverviewPanel } from './components/OverviewPanel';
export { default as EditorPanel } from './components/EditorPanel';
export { default as ThreeDPanel } from './components/ThreeDPanel';

// Hooks
export {
  useScaffoldConfig,
  useCurrentElement,
  useVisibleElements,
  useTotals,
  useSettings,
  useElements,
} from './hooks/useScaffoldConfig';

// Types
export type {
  ProjectInput,
  SelectedFacade,
  FacadeDirection,
  DetectedFeature,
  WorkType,
  ScaffoldSystem,
  FieldWidth,
  BayWidth,
  ScaffoldSettings,
  ScaffoldConfiguration,
  ScaffoldTotals,
  ScaffoldElement,
  ScaffoldFacade,
  ScaffoldCorner,
  FacadeModifications,
  ScaffoldOutput,
  ElementDetail,
  ScaffoldGeometry,
  ScaffoldSegment,
  EditorTool,
  MainTab,
  View3D,
  SVGDimensions,
  CarouselState,
  VisibleElements,
} from './types/scaffold.types';

export { FACADE_COLORS, CORNER_COLOR, SCAFFOLD_CONSTANTS } from './types/scaffold.types';

// Utilities
export {
  calculateTargetHeight,
  calculateFields,
  calculateLevels,
  calculateFacadeArea,
  calculateCornerMaterial,
  estimateWeight,
  calculateSvgDimensions,
  formatNumber,
  formatArea,
  formatLength,
  formatWeight,
  getWorkTypeInfo,
  getSystemInfo,
  getBayWidthInfo,
  getCellKey,
  parseCellKey,
} from './utils/calculations';
