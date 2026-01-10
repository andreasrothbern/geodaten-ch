/**
 * Facade Panel - Tab 1
 * Facade selection with polygon visualization (like FacadeSelectionPage)
 * Uses the same UI but integrated into the tab system
 */

import { useMemo, useCallback } from 'react';
import { Check, ArrowRight, Compass, AlertTriangle, SlidersHorizontal } from 'lucide-react';
import { useScaffoldConfig, useElements, useSettings, useTotals } from '../hooks/useScaffoldConfig';
import type { ScaffoldFacade, SelectedFacade } from '../types/scaffold.types';
import { getFacadeColor } from '../types/scaffold.types';
import type { NeighborBuilding } from '../../../api/geruestbau';
import { simplifyPolygon, sidesToFacades } from '../utils/polygonSimplifier';

interface FacadePanelProps {
  neighbors?: NeighborBuilding[];
  blockedSides?: string[];
}

export default function FacadePanel({ neighbors = [], blockedSides = [] }: FacadePanelProps) {
  const {
    buildingName,
    buildingAddress,
    configuration,
    setCurrentTab,
    toggleFacadeEnabled,
    simplifyPolygonEpsilon,
    setSimplifyEpsilon,
    applySimplification,
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

  // Geometry-based blocking: Calculate distance from facade to neighbor polygons
  const BLOCKING_THRESHOLD_M = 2.0;

  // Point-to-segment distance (same algorithm as backend)
  const pointToSegmentDistance = useCallback((
    px: number, py: number,
    ax: number, ay: number,
    bx: number, by: number
  ): number => {
    const abx = bx - ax, aby = by - ay;
    const apx = px - ax, apy = py - ay;
    const abSq = abx * abx + aby * aby;
    if (abSq === 0) return Math.sqrt(apx * apx + apy * apy);
    const t = Math.max(0, Math.min(1, (apx * abx + apy * aby) / abSq));
    const dx = px - (ax + t * abx), dy = py - (ay + t * aby);
    return Math.sqrt(dx * dx + dy * dy);
  }, []);

  // Facade-to-polygon distance
  const facadeToPolygonDistance = useCallback((
    facadeStart: [number, number],
    facadeEnd: [number, number],
    neighborPolygon: [number, number][]
  ): number => {
    let minDist = Infinity;
    const [fx1, fy1] = facadeStart;
    const [fx2, fy2] = facadeEnd;

    // Check facade endpoints to neighbor edges
    for (let i = 0; i < neighborPolygon.length; i++) {
      const [p1x, p1y] = neighborPolygon[i];
      const [p2x, p2y] = neighborPolygon[(i + 1) % neighborPolygon.length];
      minDist = Math.min(minDist, pointToSegmentDistance(fx1, fy1, p1x, p1y, p2x, p2y));
      minDist = Math.min(minDist, pointToSegmentDistance(fx2, fy2, p1x, p1y, p2x, p2y));
    }

    // Check neighbor polygon points to facade edge
    for (const [px, py] of neighborPolygon) {
      minDist = Math.min(minDist, pointToSegmentDistance(px, py, fx1, fy1, fx2, fy2));
    }

    return minDist;
  }, [pointToSegmentDistance]);

  // Check if a facade is blocked by neighbors (geometry-based)
  const isFacadeBlocked = useCallback((facade: ScaffoldFacade): boolean => {
    if (!facade.start_point || !facade.end_point) return false;

    // Check distance to each neighbor polygon
    for (const neighbor of neighbors) {
      if (!neighbor.polygon || neighbor.polygon.length < 3) continue;
      const dist = facadeToPolygonDistance(
        facade.start_point as [number, number],
        facade.end_point as [number, number],
        neighbor.polygon as [number, number][]
      );
      if (dist < BLOCKING_THRESHOLD_M) {
        return true;
      }
    }

    // Fallback to direction-based check
    return blockedSides.includes(facade.direction);
  }, [neighbors, blockedSides, facadeToPolygonDistance]);

  // Get default height from existing facades
  const defaultHeight = useMemo(() => {
    if (facades.length > 0) {
      return facades[0].target_height_m;
    }
    return 10;
  }, [facades]);

  // Handle polygon simplification
  const handleSimplifyChange = useCallback((newEpsilon: number | null) => {
    if (!polygon || polygon.length < 3) return;

    setSimplifyEpsilon(newEpsilon);

    // Simplify polygon and calculate new facades
    const result = simplifyPolygon(polygon, { epsilon: newEpsilon });
    const newFacades: SelectedFacade[] = sidesToFacades(result.sides, defaultHeight);

    // Apply to store
    applySimplification(newFacades);

    console.log(`Vereinfachung: ${polygon.length} → ${result.simplifiedPoints} Punkte, ${newFacades.length} Fassaden (epsilon=${result.epsilon})`);
  }, [polygon, defaultHeight, setSimplifyEpsilon, applySimplification]);

  // Generate SVG for building polygon
  const polygonSvg = useMemo(() => {
    if (!polygon || polygon.length < 3 || facades.length === 0) return null;

    // Calculate bounds including neighbors
    const allPolygons = [polygon, ...neighbors.filter(n => n.polygon).map(n => n.polygon!)];
    const allXs = allPolygons.flatMap(p => p.map(pt => pt[0]));
    const allYs = allPolygons.flatMap(p => p.map(pt => pt[1]));

    const minX = Math.min(...allXs);
    const maxX = Math.max(...allXs);
    const minY = Math.min(...allYs);
    const maxY = Math.max(...allYs);

    const width = maxX - minX;
    const height = maxY - minY;
    const padding = Math.max(width, height) * 0.15;

    const viewBox = `${minX - padding} ${minY - padding} ${width + padding * 2} ${height + padding * 2}`;

    // Create main building polygon path
    const pathData = polygon.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ') + ' Z';

    // Create neighbor polygon paths
    const neighborElements = neighbors.filter(n => n.polygon && n.polygon.length >= 3).map((neighbor, idx) => {
      const neighborPath = neighbor.polygon!.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ') + ' Z';
      return (
        <path
          key={`neighbor-${idx}`}
          d={neighborPath}
          fill="#e5e7eb"
          stroke="#9ca3af"
          strokeWidth={width * 0.005}
          opacity={0.8}
        />
      );
    });

    // Create facade segments - thicker lines for better visibility
    const lineWidth = width * 0.06; // Dickere Linien für bessere Farbsichtbarkeit

    const facadeElements = facades.map((facade) => {
      if (!facade.start_point || !facade.end_point) return null;

      const isBlocked = isFacadeBlocked(facade);
      const isEnabled = facade.enabled && !isBlocked;
      const color = isBlocked ? '#9ca3af' : getFacadeColor(facade.direction);

      return (
        <g
          key={facade.id}
          onClick={() => !isBlocked && toggleFacadeEnabled(facade.id)}
          style={{ cursor: isBlocked ? 'not-allowed' : 'pointer' }}
        >
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
          {/* Visible facade line - uniform width */}
          <line
            x1={facade.start_point[0]}
            y1={facade.start_point[1]}
            x2={facade.end_point[0]}
            y2={facade.end_point[1]}
            stroke={isEnabled ? color : isBlocked ? '#9ca3af' : '#ccc'}
            strokeWidth={lineWidth}
            strokeLinecap="round"
            strokeDasharray={isBlocked ? `${lineWidth * 2} ${lineWidth}` : undefined}
          />
          {/* Blocked indicator */}
          {isBlocked && (
            <circle
              cx={(facade.start_point[0] + facade.end_point[0]) / 2}
              cy={(facade.start_point[1] + facade.end_point[1]) / 2}
              r={width * 0.02}
              fill="#ef4444"
              stroke="white"
              strokeWidth={width * 0.005}
            />
          )}
        </g>
      );
    });

    return (
      <svg viewBox={viewBox} className="w-full h-64 bg-gray-50 rounded-lg">
        {/* Transform to flip Y-axis (LV95 has Y increasing northward) */}
        <g transform={`translate(0, ${maxY + minY}) scale(1, -1)`}>
          {/* Neighbor buildings (behind main building) */}
          {neighborElements}
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
  }, [polygon, facades, neighbors, isFacadeBlocked, toggleFacadeEnabled]);

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

        {/* Polygon Simplification Slider */}
        {polygon && polygon.length > 4 && (
          <div className="mt-3 pt-3 border-t border-gray-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-gray-600 flex items-center gap-1">
                <SlidersHorizontal className="w-3 h-3" />
                Vereinfachung
              </span>
              <span className="text-xs text-gray-400">
                {facades.length} Fassaden
              </span>
            </div>
            <div className="flex gap-1">
              {[
                { label: 'Original', value: null },
                { label: 'Leicht', value: 0.3 },
                { label: 'Mittel', value: 0.8 },
                { label: 'Stark', value: 1.5 },
              ].map((option) => (
                <button
                  key={option.label}
                  onClick={() => handleSimplifyChange(option.value)}
                  className={`flex-1 py-1.5 px-2 text-xs rounded transition-colors ${
                    simplifyPolygonEpsilon === option.value
                      ? 'bg-red-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
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
            const isBlocked = isFacadeBlocked(facade);
            const isEnabled = facade.enabled && !isBlocked;
            const color = isBlocked ? '#9ca3af' : getFacadeColor(facade.direction);

            return (
              <button
                key={facade.id}
                onClick={() => !isBlocked && toggleFacadeEnabled(facade.id)}
                disabled={isBlocked}
                className={`w-full flex items-center justify-between p-3 rounded-lg border transition-all ${
                  isBlocked
                    ? 'border-gray-300 bg-gray-100 cursor-not-allowed opacity-60'
                    : isEnabled
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
                    <p className="font-medium flex items-center gap-2">
                      {facade.name}
                      {isBlocked && (
                        <span className="inline-flex items-center gap-1 text-xs text-red-600 bg-red-50 px-1.5 py-0.5 rounded">
                          <AlertTriangle className="w-3 h-3" />
                          Blockiert
                        </span>
                      )}
                    </p>
                    <p className="text-sm text-gray-500">{facade.length_m.toFixed(1)} m</p>
                  </div>
                </div>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                  isBlocked ? 'bg-red-200' : isEnabled ? 'bg-green-500 text-white' : 'bg-gray-200'
                }`}>
                  {isBlocked ? (
                    <AlertTriangle className="w-3 h-3 text-red-600" />
                  ) : isEnabled ? (
                    <Check className="w-4 h-4" />
                  ) : null}
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
