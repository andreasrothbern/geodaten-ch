/**
 * Custom Hooks für die Gerüstbau-App.
 */

// Project Context Streaming (für 3D-View, Nachbarn, blockierte Fassaden)
export {
  useProjectContextStream,
  type CentroidData,
  type ProjectBuildingData,
  type BlockedFacadesData,
  type BlockerInfo,
  type NeighborBuilding,
  type NeighborsData,
  type CompleteData as ProjectCompleteData,
  type ErrorData as ProjectErrorData,
  type StreamState as ProjectStreamState,
  type StartOptions as ProjectStreamOptions,
} from './useProjectContextStream';

// Building Data Streaming (für Projekt-Erstellung)
export {
  useBuildingDataStream,
  type StreamStep,
  type GeocodingData,
  type GWRData,
  type PolygonData,
  type HeightsData,
  type TerrainData,
  type ZoneData,
  type ZonesData,
  type ResearchData,
  type CompleteData as BuildingCompleteData,
  type BuildingDataBundle,
  type ErrorData as BuildingErrorData,
  type StreamState as BuildingStreamState,
  type StreamOptions as BuildingStreamOptions,
} from './useBuildingDataStream';
