/**
 * Facade Panel - Tab 1
 * Facade selection with polygon visualization (like FacadeSelectionPage)
 * Uses the same UI but integrated into the tab system
 */

import { useMemo } from 'react';
import { Check, ArrowRight, Compass } from 'lucide-react';
import { useScaffoldConfig, useElements, useSettings, useTotals } from '../hooks/useScaffoldConfig';
import type { ScaffoldFacade } from '../types/scaffold.types';

// Direction colors for visual distinction (same as FacadeSelectionPage)
const DIRECTION_COLORS: Record<string, string> = {
  'N': '#3B82F6',  // Blue
  'NE': '#6366F1', // Indigo
  'E': '#8B5CF6',  // Violet
  'SE': '#EC4899', // Pink
  'S': '#EF4444',  // Red
  'SW': '#F97316', // Orange
  'W': '#EAB308',  // Yellow
  'NW': '#22C55E', // Green
  // German direction codes
  'NO': '#6366F1', // Indigo
  'O': '#8B5CF6',  // Violet
  'SO': '#EC4899', // Pink
};

export default function FacadePanel() {
  const {
    buildingName,
    buildingAddress,
    configuration,
    setCurrentTab,
    toggleFacadeEnabled,
  } = useScaffoldConfig();

  const elements = useElements();
  const settings = useSettings();
  const totals = useTotals();

  // Filter facades from elements
  const facades = useMemo(() => {
    return elements.filter((el): el is ScaffoldFacade => el.type === 'facade');
  }, [elements]);

  // Get building polygon from configuration
  const polygon = configuration?.buildingPolygon;

  const enabledCount = facades.filter(f => f.enabled).length;
  const canProceed = enabledCount > 0;

  // Calculate total length of enabled facades
  const totalEnabledLength = useMemo(() => {
    return facades
      .filter(f => f.enabled)
      .reduce((sum, f) => sum + f.length_m, 0);
  }, [facades]);

  // Calculate estimated scaffold area
  const estimatedArea = useMemo(() => {
    const avgHeight = facades.length > 0
      ? facades.filter(f => f.enabled).reduce((sum, f) => sum + f.target_height_m, 0) / Math.max(1, enabledCount)
      : 10;
    return totalEnabledLength * avgHeight;
  }, [facades, totalEnabledLength, enabledCount]);

  // Select all facades
  const selectAll = () => {
    facades.forEach(f => {
      if (!f.enabled) toggleFacadeEnabled(f.id);
    });
  };

  // Deselect all facades
  const deselectAll = () => {
    facades.forEach(f => {
      if (f.enabled) toggleFacadeEnabled(f.id);
    });
  };

  // Generate SVG for building polygon
  const polygonSvg = useMemo(() => {
    if (!polygon || polygon.length < 3 || facades.length === 0) return null;

    // Calculate bounds
    const xs = polygon.map(p => p[0]);
    const ys = polygon.map(p => p[1]);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const width = maxX - minX;
    const height = maxY - minY;
    const padding = Math.max(width, height) * 0.15;

    const viewBox = `${minX - padding} ${minY - padding} ${width + padding * 2} ${height + padding * 2}`;

    // Create polygon path
    const pathData = polygon.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ') + ' Z';

    // Create facade segments
    const facadeElements = facades.map((facade) => {
      if (!facade.start_point || !facade.end_point) return null;

      const isEnabled = facade.enabled;
      const color = DIRECTION_COLORS[facade.direction] || facade.color || '#666';
      const midX = (facade.start_point[0] + facade.end_point[0]) / 2;
      const midY = (facade.start_point[1] + facade.end_point[1]) / 2;

      return (
        <g key={facade.id} onClick={() => toggleFacadeEnabled(facade.id)} style={{ cursor: 'pointer' }}>
          {/* Invisible hit area for easier clicking */}
          <line
            x1={facade.start_point[0]}
            y1={facade.start_point[1]}
            x2={facade.end_point[0]}
            y2={facade.end_point[1]}
            stroke="transparent"
            strokeWidth={width * 0.08}
            strokeLinecap="round"
          />
          {/* Visible facade line */}
          <line
            x1={facade.start_point[0]}
            y1={facade.start_point[1]}
            x2={facade.end_point[0]}
            y2={facade.end_point[1]}
            stroke={isEnabled ? color : '#ccc'}
            strokeWidth={isEnabled ? width * 0.03 : width * 0.018}
            strokeLinecap="round"
          />
          {/* Selection indicator (checkmark area) */}
          <circle
            cx={midX}
            cy={midY}
            r={width * 0.035}
            fill={isEnabled ? color : '#fff'}
            stroke={color}
            strokeWidth={width * 0.008}
          />
          {/* Label */}
          <text
            x={midX}
            y={midY}
            dy={width * 0.07}
            textAnchor="middle"
            fontSize={width * 0.035}
            fill={isEnabled ? '#333' : '#999'}
            fontWeight={isEnabled ? 'bold' : 'normal'}
          >
            {facade.direction} ({facade.length_m.toFixed(1)}m)
          </text>
        </g>
      );
    });

    return (
      <svg viewBox={viewBox} className="w-full h-64 bg-gray-50 rounded-lg">
        {/* Transform to flip Y-axis (LV95 has Y increasing northward) */}
        <g transform={`translate(0, ${maxY + minY}) scale(1, -1)`}>
          {/* Building outline */}
          <path
            d={pathData}
            fill="#f3f4f6"
            stroke="#ddd"
            strokeWidth={width * 0.005}
          />
          {/* Selectable facades */}
          {facadeElements}
        </g>
        {/* North arrow */}
        <g transform={`translate(${maxX + padding * 0.5}, ${minY + padding * 0.5})`}>
          <circle r={width * 0.05} fill="white" stroke="#333" strokeWidth={width * 0.004} />
          <text textAnchor="middle" dy={width * 0.02} fontSize={width * 0.04} fontWeight="bold" fill="#dc2626">N</text>
        </g>
      </svg>
    );
  }, [polygon, facades, toggleFacadeEnabled]);

  return (
    <div className="space-y-4">
      {/* Building Info */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-gray-800">{buildingName || 'Gebäude'}</h2>
          {configuration?.project_id && (
            <span className="text-xs text-gray-400">ID: {configuration.project_id.slice(0, 8)}</span>
          )}
        </div>
        <p className="text-sm text-gray-500">{buildingAddress}</p>
        {settings && (
          <div className="flex gap-4 mt-2 text-sm text-gray-600">
            <span>Traufhöhe: {totals.max_height_m.toFixed(1)}m</span>
          </div>
        )}
      </div>

      {/* Polygon Visualization */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-700 flex items-center gap-2">
            <Compass className="w-4 h-4" />
            Gebäudegrundriss
          </h3>
          <div className="flex gap-2">
            <button
              onClick={selectAll}
              disabled={enabledCount === facades.length}
              className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Alle
            </button>
            <button
              onClick={deselectAll}
              disabled={enabledCount === 0}
              className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Keine
            </button>
          </div>
        </div>

        {polygonSvg || (
          <div className="h-64 bg-gray-50 rounded-lg flex items-center justify-center text-gray-400">
            Kein Polygon verfügbar
          </div>
        )}

        <p className="text-xs text-gray-400 mt-2 text-center">
          Tippen Sie auf eine Fassade, um sie auszuwählen
        </p>
      </div>

      {/* Facade List */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <h3 className="font-semibold text-gray-700 mb-3">Fassaden ({facades.length})</h3>
        <div className="space-y-2">
          {facades.map((facade) => {
            const isEnabled = facade.enabled;
            const color = DIRECTION_COLORS[facade.direction] || facade.color || '#666';

            return (
              <button
                key={facade.id}
                onClick={() => toggleFacadeEnabled(facade.id)}
                className={`w-full flex items-center justify-between p-3 rounded-lg border transition-all ${
                  isEnabled
                    ? 'border-green-300 bg-green-50'
                    : 'border-gray-200 bg-white hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <div className="text-left">
                    <p className="font-medium">{facade.name}</p>
                    <p className="text-sm text-gray-500">{facade.length_m.toFixed(1)} m</p>
                  </div>
                </div>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                  isEnabled ? 'bg-green-500 text-white' : 'bg-gray-200'
                }`}>
                  {isEnabled && <Check className="w-4 h-4" />}
                </div>
              </button>
            );
          })}
        </div>

        {facades.length === 0 && (
          <div className="text-center py-8 text-gray-400">
            <p>Keine Fassaden verfügbar</p>
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="bg-red-50 border border-red-200 rounded-xl p-4">
        <h3 className="font-semibold text-red-800 mb-2">Zusammenfassung</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-red-600">Ausgewählte Fassaden</p>
            <p className="text-xl font-bold text-red-800">{enabledCount}</p>
          </div>
          <div>
            <p className="text-red-600">Gesamtlänge</p>
            <p className="text-xl font-bold text-red-800">{totalEnabledLength.toFixed(1)} m</p>
          </div>
          <div>
            <p className="text-red-600">Gerüsthöhe</p>
            <p className="text-xl font-bold text-red-800">{totals.max_height_m.toFixed(1)} m</p>
          </div>
          <div>
            <p className="text-red-600">Geschätzte Fläche</p>
            <p className="text-xl font-bold text-red-800">{Math.round(estimatedArea)} m²</p>
          </div>
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
