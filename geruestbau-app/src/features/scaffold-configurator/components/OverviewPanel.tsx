/**
 * Overview Panel - Tab 1
 * Global settings, summary stats, and facade cards
 */

import { useState, useMemo, useEffect } from 'react';
import { useScaffoldConfig, useTotals, useSettings, useElements } from '../hooks/useScaffoldConfig';
import type { ScaffoldFacade, WorkType, ScaffoldSystem, BayWidth } from '../types/scaffold.types';

// Sub-components
import ProjectHeader from './overview/ProjectHeader';
import MiniFloorPlan, { FloorPlanLegend } from './overview/MiniFloorPlan';
import WorkTypeSelector from './overview/WorkTypeSelector';
import SystemSelector from './overview/SystemSelector';
import SummaryStats from './overview/SummaryStats';
import FacadeCards from './overview/FacadeCards';
import GlobalOptions from './overview/GlobalOptions';

export default function OverviewPanel() {
  const {
    buildingName,
    buildingAddress,
    configuration,
    setCurrentTab,
    setWorkType,
    setSystem,
    setBayWidth,
    toggleOption,
  } = useScaffoldConfig();

  const totals = useTotals();
  const settings = useSettings();
  const elements = useElements();

  // Local state for facade cards carousel
  const [facadeCardIndex, setFacadeCardIndex] = useState(0);

  // Filter facades from elements - all facades and enabled only
  const allFacades = useMemo(() => {
    return elements.filter((el): el is ScaffoldFacade => el.type === 'facade');
  }, [elements]);

  // Only enabled facades for display and calculations
  const facades = useMemo(() => {
    return allFacades.filter(f => f.enabled);
  }, [allFacades]);

  // Reset carousel index if out of bounds when facades change
  useEffect(() => {
    if (facadeCardIndex >= facades.length && facades.length > 0) {
      setFacadeCardIndex(0);
    }
  }, [facades.length, facadeCardIndex]);

  // Calculate max slope from enabled facades
  const maxSlope = useMemo(() => {
    return facades.reduce((max, f) => Math.max(max, f.slope_percent), 0);
  }, [facades]);

  // Handle carousel navigation
  const handleNavigate = (direction: 'prev' | 'next') => {
    if (facades.length === 0) return;
    setFacadeCardIndex((prev) => {
      if (direction === 'prev') {
        return (prev - 1 + facades.length) % facades.length;
      }
      return (prev + 1) % facades.length;
    });
  };

  // Handle facade selection from cards
  const handleSelectFacade = (index: number) => {
    setFacadeCardIndex(index);
  };

  if (!settings) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Keine Konfiguration geladen</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Project Header with Mini Floor Plan */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <ProjectHeader
          buildingName={buildingName}
          buildingAddress={buildingAddress}
          isComplete={facades.length === allFacades.length && allFacades.length > 0}
        />

        {/* Mini Floor Plan + Legend */}
        <div className="mt-4 flex items-center gap-6">
          <MiniFloorPlan
            facades={facades}
            allFacades={allFacades}
            polygon={configuration?.buildingPolygon}
            size={96}
          />
          <FloorPlanLegend facades={facades} />
        </div>
      </div>

      {/* Work Type Selection */}
      <WorkTypeSelector
        value={settings.work_type}
        onChange={(type: WorkType) => setWorkType(type)}
      />

      {/* System & Bay Width Selection */}
      <SystemSelector
        system={settings.system}
        bayWidth={settings.bay_width_m}
        onSystemChange={(system: ScaffoldSystem) => setSystem(system)}
        onBayWidthChange={(width: BayWidth) => setBayWidth(width)}
      />

      {/* Summary Stats */}
      <SummaryStats totals={totals} settings={settings} maxSlope={maxSlope} />

      {/* Global Options (Safety Net, Weather Cover) */}
      <GlobalOptions
        safetyNet={settings.safety_net}
        weatherCover={settings.weather_cover}
        onSafetyNetChange={() => toggleOption('safety_net')}
        onWeatherCoverChange={() => toggleOption('weather_cover')}
      />

      {/* Facade Cards Carousel */}
      {facades.length > 0 && (
        <div>
          <h3 className="font-semibold text-gray-700 mb-3 flex items-center justify-between">
            <span>Fassaden Details</span>
            <span className="text-xs text-gray-400 font-normal">
              {facadeCardIndex + 1} / {facades.length}
            </span>
          </h3>
          <FacadeCards
            facades={facades}
            settings={settings}
            currentIndex={facadeCardIndex}
            onNavigate={handleNavigate}
            onSelectFacade={handleSelectFacade}
          />
        </div>
      )}

      {/* Action Button */}
      <div className="flex gap-3">
        <button
          onClick={() => setCurrentTab('editor')}
          className="flex-1 py-3 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 shadow-sm flex items-center justify-center gap-2 transition-colors"
        >
          Im Editor bearbeiten
        </button>
      </div>
    </div>
  );
}
