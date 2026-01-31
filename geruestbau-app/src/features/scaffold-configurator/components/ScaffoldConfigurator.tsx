/**
 * Scaffold Configurator - Main Container Component
 * Manages tab navigation between Overview, Editor, and 3D views
 */

import { useEffect, useRef } from 'react';
import { ArrowLeft, LayoutGrid, Edit3, Box, MoreVertical, Layers } from 'lucide-react';
import { useScaffoldConfig } from '../hooks/useScaffoldConfig';
import type { MainTab, SelectedFacade, RoofData, BuildingZone } from '../types/scaffold.types';
import type { BuildingWall } from '../../../types/project';
import type { NeighborBuilding, ObjectData } from '../../../api/geruestbau';
// NEU 10.01.2026 19:25 - Blocked Facades per EGID (Multi-Building Support)
import type { BlockedFacadesData } from '../../../hooks/useProjectContextStream';

// Panels
import FacadePanel from './FacadePanel';
import OverviewPanel from './OverviewPanel';
import EditorPanel from './EditorPanel';
import ThreeDPanel from './ThreeDPanel';

interface ScaffoldConfiguratorProps {
  projectId: string;
  buildingName: string;
  buildingAddress: string;
  buildingPolygon?: [number, number][];  // ORIGINAL from swissBUILDINGS3D (LV95)
  selectedFacades: SelectedFacade[];
  roof?: RoofData;
  neighbors?: NeighborBuilding[];  // Neighboring buildings for 3D view (filtered by slider)
  blockingNeighbors?: NeighborBuilding[];  // FIX 15.01.2026 01:45 - Neighbors for blocking check (always active, within 2m)
  blockedSides?: string[];  // Facade directions blocked by neighbors (fallback)
  // NEU 10.01.2026 19:25 - Blocked Facades per EGID (Multi-Building Support via SSE)
  blockedFacadesData?: BlockedFacadesData | null;
  // NEU 19.01.2026: Objekt-Architektur - Ein Projekt = Ein Objekt
  // objectData enthält "polygon" (Union) und projectBuildings (Metadaten)
  objectData?: ObjectData;
  // Zonen-Daten für komplexe Gebäude (NEU 05.01.2026)
  zones?: BuildingZone[];
  complexity?: 'simple' | 'moderate' | 'complex';
  researchSource?: 'known_buildings' | 'claude_api' | 'cache' | 'auto' | 'unknown';
  // NEU 14.01.2026 21:30 - Fassaden-Höhen für Hanglage (pro Himmelsrichtung)
  /** @deprecated Use buildingWalls instead (BUG-024) */
  facadeZMin?: Record<string, number>;  // Terrain-Höhen (m ü.M.)
  /** @deprecated Use buildingWalls instead (BUG-024) */
  facadeZMax?: Record<string, number>;  // Wandoberkanten (m ü.M.)
  // NEU 15.01.2026 BUG-024: BuildingWall direkt aus building_walls DB-Tabelle
  buildingWalls?: BuildingWall[];
  onBack?: () => void;
  onComplete?: () => void; // Will be used when completing configuration
}

export default function ScaffoldConfigurator({
  projectId,
  buildingName,
  buildingAddress,
  buildingPolygon,
  selectedFacades,
  roof,
  neighbors = [],
  blockingNeighbors = [],
  blockedSides = [],
  blockedFacadesData,
  objectData,
  zones = [],
  complexity = 'simple',
  researchSource,
  facadeZMin,
  facadeZMax,
  buildingWalls = [],  // NEU 15.01.2026 BUG-024
  onBack,
  onComplete: _onComplete, // Will be used when completing configuration
}: ScaffoldConfiguratorProps) {
  void _onComplete; // Reserved for future use
  void researchSource; // Reserved for future use (display in 3D info panel)
  const {
    currentTab,
    setCurrentTab,
    initializeFromFacades,
    configuration,
  } = useScaffoldConfig();

  // FIX 25.01.2026: Ref to prevent infinite loop in height-based re-initialization
  // The heightsNeedUpdate check can trigger re-init, but after init the heights may still differ
  // This ref ensures we only attempt height-based re-init once per project
  const heightReinitAttemptedRef = useRef<string | null>(null);

  // Initialize configuration on mount
  useEffect(() => {
    // DEBUG: Log roof prop to track data flow
    console.log('=== ScaffoldConfigurator mount ===', {
      projectId,
      hasRoof: !!roof,
      roof,
      hasConfiguration: !!configuration,
      configurationRoof: configuration?.roof,
    });

    // Check if existing configuration facades have coordinates
    const facadesHaveCoordinates = configuration?.elements?.some(
      el => el.type === 'facade' && el.start_point && el.end_point
    ) ?? false;

    // FIX 10.01.2026 23:15 - Check if heights need update (SSE delivered new heights)
    // FIX 21.01.2026: Auch re-initialisieren wenn Höhen signifikant unterschiedlich sind (>1m oder >20%)
    const configMaxHeight = configuration?.elements?.filter(el => el.type === 'facade')
      .reduce((max, el) => Math.max(max, (el as { target_height_m?: number }).target_height_m ?? 0), 0) ?? 0;
    const facadesMaxHeight = selectedFacades.reduce((max, f) => Math.max(max, f.height_m), 0);

    // Re-initialize if heights differ significantly
    const heightDiff = Math.abs(configMaxHeight - facadesMaxHeight);
    const heightsDifferSignificantly = heightDiff > 1.0 ||
      (configMaxHeight > 0 && heightDiff / configMaxHeight > 0.2);
    const heightsNeedUpdate = facadesMaxHeight > 0 && (configMaxHeight === 0 || heightsDifferSignificantly);

    if (heightsNeedUpdate && configuration) {
      console.log(`[ScaffoldConfigurator] Heights differ: config=${configMaxHeight.toFixed(2)}m vs facades=${facadesMaxHeight.toFixed(2)}m (diff=${heightDiff.toFixed(2)}m)`);
    }

    if (!configuration || configuration.project_id !== projectId) {
      console.log('Initializing from facades with roof:', roof);
      initializeFromFacades(projectId, buildingName, buildingAddress, selectedFacades, buildingPolygon, roof);
    } else if (roof && !configuration.roof) {
      // Update roof data if configuration exists but roof was missing (from old cache)
      console.log('Updating roof data in existing configuration:', roof);
      initializeFromFacades(projectId, buildingName, buildingAddress, selectedFacades, buildingPolygon, roof);
    } else if (!facadesHaveCoordinates && selectedFacades.some(f => f.start_point && f.end_point)) {
      // Re-initialize if cached config has no coordinates but new data does (FIX 10.01.2026)
      console.log('Re-initializing: Cached facades missing coordinates, new facades have them');
      initializeFromFacades(projectId, buildingName, buildingAddress, selectedFacades, buildingPolygon, roof);
    } else if (heightsNeedUpdate && heightReinitAttemptedRef.current !== projectId) {
      // FIX 21.01.2026 - Re-initialize if heights differ significantly (new 3D data vs cached)
      // FIX 25.01.2026 - Only attempt once per project to prevent infinite loop (BUG-030 related)
      console.log(`Re-initializing: Heights differ significantly (config=${configMaxHeight.toFixed(2)}m → facades=${facadesMaxHeight.toFixed(2)}m)`);
      heightReinitAttemptedRef.current = projectId;
      initializeFromFacades(projectId, buildingName, buildingAddress, selectedFacades, buildingPolygon, roof);
    }
  }, [projectId, buildingName, buildingAddress, selectedFacades, buildingPolygon, roof, configuration, initializeFromFacades]);

  const tabs: { id: MainTab; label: string; icon: React.ReactNode }[] = [
    { id: 'facade', label: 'Fassade', icon: <Layers className="w-4 h-4" /> },
    { id: 'overview', label: 'Gerüst', icon: <LayoutGrid className="w-4 h-4" /> },
    { id: 'editor', label: 'Editor', icon: <Edit3 className="w-4 h-4" /> },
    { id: '3d', label: '3D', icon: <Box className="w-4 h-4" /> },
  ];

  return (
    <div className="min-h-screen bg-gray-100 pb-20">
      {/* Header */}
      <header className="bg-red-600 text-white px-4 py-3 sticky top-0 z-50 shadow-lg">
        <div className="flex items-center justify-between max-w-4xl mx-auto">
          <button
            onClick={onBack}
            className="p-2 -ml-2 hover:bg-red-700 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div className="text-center">
            <h1 className="font-semibold text-lg">Gerüst konfigurieren</h1>
            <p className="text-xs text-red-200">{buildingName}</p>
          </div>
          <button className="p-2 hover:bg-red-700 rounded-lg transition-colors">
            <MoreVertical className="w-6 h-6" />
          </button>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="bg-white border-b sticky top-[60px] z-40 shadow-sm">
        <div className="max-w-4xl mx-auto flex">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setCurrentTab(tab.id)}
              className={`flex-1 py-3 text-sm font-medium text-center transition-colors flex items-center justify-center gap-1.5 ${
                currentTab === tab.id
                  ? 'bg-red-600 text-white'
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto p-4">
        {currentTab === 'facade' && <FacadePanel neighbors={neighbors} blockingNeighbors={blockingNeighbors} blockedSides={blockedSides} blockedFacadesData={blockedFacadesData} objectData={objectData} facadeZMin={facadeZMin} facadeZMax={facadeZMax} buildingWalls={buildingWalls} />}
        {currentTab === 'overview' && <OverviewPanel />}
        {currentTab === 'editor' && <EditorPanel />}
        {currentTab === '3d' && <ThreeDPanel neighbors={neighbors} blockedSides={blockedSides} objectData={objectData} zones={zones} complexity={complexity} buildingWalls={buildingWalls} />}
      </main>
    </div>
  );
}
