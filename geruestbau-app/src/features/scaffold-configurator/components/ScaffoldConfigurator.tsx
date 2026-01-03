/**
 * Scaffold Configurator - Main Container Component
 * Manages tab navigation between Overview, Editor, and 3D views
 */

import { useEffect } from 'react';
import { ArrowLeft, LayoutGrid, Edit3, Box, MoreVertical, Layers } from 'lucide-react';
import { useScaffoldConfig } from '../hooks/useScaffoldConfig';
import type { MainTab, SelectedFacade, RoofData } from '../types/scaffold.types';

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
  onBack,
  onComplete: _onComplete, // Will be used when completing configuration
}: ScaffoldConfiguratorProps) {
  void _onComplete; // Reserved for future use
  const {
    currentTab,
    setCurrentTab,
    initializeFromFacades,
    configuration,
  } = useScaffoldConfig();

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

    if (!configuration || configuration.project_id !== projectId) {
      console.log('Initializing from facades with roof:', roof);
      initializeFromFacades(projectId, buildingName, buildingAddress, selectedFacades, buildingPolygon, roof);
    } else if (roof && !configuration.roof) {
      // Update roof data if configuration exists but roof was missing (from old cache)
      console.log('Updating roof data in existing configuration:', roof);
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
        {currentTab === 'facade' && <FacadePanel />}
        {currentTab === 'overview' && <OverviewPanel />}
        {currentTab === 'editor' && <EditorPanel />}
        {currentTab === '3d' && <ThreeDPanel />}
      </main>
    </div>
  );
}
