/**
 * Facade Panel - Tab 1
 * Facade selection with mini floor plan
 */

import { useMemo } from 'react';
import { Check, ArrowRight } from 'lucide-react';
import { useScaffoldConfig, useElements } from '../hooks/useScaffoldConfig';
import type { ScaffoldFacade } from '../types/scaffold.types';

// Sub-components
import ProjectHeader from './overview/ProjectHeader';
import MiniFloorPlan, { FloorPlanLegend } from './overview/MiniFloorPlan';

export default function FacadePanel() {
  const {
    buildingName,
    buildingAddress,
    setCurrentTab,
    toggleFacadeEnabled,
  } = useScaffoldConfig();

  const elements = useElements();

  // Filter facades from elements
  const facades = useMemo(() => {
    return elements.filter((el): el is ScaffoldFacade => el.type === 'facade');
  }, [elements]);

  const enabledCount = facades.filter(f => f.enabled).length;
  const canProceed = enabledCount > 0;

  return (
    <div className="space-y-4">
      {/* Project Header with Mini Floor Plan */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <ProjectHeader
          buildingName={buildingName}
          buildingAddress={buildingAddress}
          isComplete={enabledCount > 0}
        />

        {/* Mini Floor Plan + Legend */}
        <div className="mt-4 flex items-center gap-6">
          <MiniFloorPlan facades={facades.filter(f => f.enabled)} size={96} />
          <FloorPlanLegend facades={facades.filter(f => f.enabled)} />
        </div>
      </div>

      {/* Facade Selection */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <h3 className="font-semibold text-gray-700 mb-3 flex items-center justify-between">
          <span>Fassaden auswählen</span>
          <span className="text-xs text-gray-400 font-normal">
            {enabledCount} / {facades.length} aktiv
          </span>
        </h3>
        <div className="grid grid-cols-2 gap-2">
          {facades.map((facade) => (
            <button
              key={facade.id}
              onClick={() => toggleFacadeEnabled(facade.id)}
              className={`flex items-center justify-between p-3 rounded-lg border transition-all ${
                facade.enabled
                  ? 'border-green-300 bg-green-50'
                  : 'border-gray-200 bg-gray-50 opacity-60'
              }`}
            >
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: facade.color }}
                />
                <div className="text-left">
                  <p className="font-medium text-sm">{facade.name}</p>
                  <p className="text-xs text-gray-500">{facade.length_m.toFixed(1)} m</p>
                </div>
              </div>
              <div className={`w-5 h-5 rounded-full flex items-center justify-center ${
                facade.enabled ? 'bg-green-500 text-white' : 'bg-gray-200'
              }`}>
                {facade.enabled && <Check className="w-3 h-3" />}
              </div>
            </button>
          ))}
        </div>

        {facades.length === 0 && (
          <div className="text-center py-8 text-gray-400">
            <p>Keine Fassaden verfügbar</p>
          </div>
        )}
      </div>

      {/* Selection Actions */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <div className="flex gap-2">
          <button
            onClick={() => facades.forEach(f => !f.enabled && toggleFacadeEnabled(f.id))}
            className="flex-1 py-2 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
            disabled={enabledCount === facades.length}
          >
            Alle auswählen
          </button>
          <button
            onClick={() => facades.forEach(f => f.enabled && toggleFacadeEnabled(f.id))}
            className="flex-1 py-2 text-sm border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
            disabled={enabledCount === 0}
          >
            Keine auswählen
          </button>
        </div>
      </div>

      {/* Action Button */}
      <button
        onClick={() => setCurrentTab('overview')}
        disabled={!canProceed}
        className={`w-full py-3 rounded-xl font-medium shadow-sm flex items-center justify-center gap-2 transition-colors ${
          canProceed
            ? 'bg-red-600 text-white hover:bg-red-700'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        }`}
      >
        Weiter zur Konfiguration
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}
