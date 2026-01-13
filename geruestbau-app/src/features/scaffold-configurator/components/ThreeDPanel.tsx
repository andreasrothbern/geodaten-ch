/**
 * 3D Panel - Tab 3
 * 3D visualization using IFC.js (@thatopen/components)
 */

import { useState, Suspense } from 'react';
import { RotateCw, ZoomIn, Home } from 'lucide-react';
import { useScaffoldConfig, useTotals, useSettings } from '../hooks/useScaffoldConfig';
import { formatNumber } from '../utils/calculations';
import type { View3D, BuildingZone } from '../types/scaffold.types';
import type { NeighborBuilding, MultiBuildingData } from '../../../api/geruestbau';
import { ScaffoldScene } from './threeDView';

interface ThreeDPanelProps {
  neighbors?: NeighborBuilding[];
  blockedSides?: string[];
  additionalBuildings?: MultiBuildingData[];
  zones?: BuildingZone[];
  complexity?: 'simple' | 'moderate' | 'complex';
}

export default function ThreeDPanel({ neighbors = [], blockedSides = [], additionalBuildings = [], zones = [], complexity = 'simple' }: ThreeDPanelProps) {
  const { setCurrentTab, configuration } = useScaffoldConfig();
  const totals = useTotals();
  const settings = useSettings();
  const [activeView, setActiveView] = useState<View3D>('isometric');

  // Building polygon is now always the ORIGINAL from swissBUILDINGS3D
  const polygonPointCount = configuration?.buildingPolygon?.length || 0;

  const views: { id: View3D; label: string }[] = [
    { id: 'isometric', label: 'Isometrisch' },
    { id: 'north', label: 'Nord' },
    { id: 'east', label: 'Ost' },
    { id: 'south', label: 'Süd' },
    { id: 'west', label: 'West' },
    { id: 'top', label: 'Draufsicht' },
  ];

  const handleResetView = () => {
    setActiveView('isometric');
  };

  if (!configuration) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500">Keine Konfiguration geladen</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 3D Viewer */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="relative" style={{ minHeight: '400px' }}>
          {/* 3D Scene */}
          <Suspense
            fallback={
              <div className="absolute inset-0 flex items-center justify-center bg-sky-50">
                <div className="text-center">
                  <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                  <p className="text-gray-600">3D-Szene wird geladen...</p>
                </div>
              </div>
            }
          >
            <ScaffoldScene
              configuration={configuration}
              activeView={activeView}
              onViewChange={setActiveView}
              neighbors={neighbors}
              blockedSides={blockedSides}
              additionalBuildings={additionalBuildings}
              zones={zones}
              complexity={complexity}
            />
          </Suspense>

          {/* 3D Controls */}
          <div className="absolute bottom-4 left-4 flex gap-2">
            <button
              className="p-2.5 bg-white rounded-lg shadow hover:bg-gray-50 transition-colors"
              title="Drehen (Maus ziehen)"
            >
              <RotateCw className="w-5 h-5 text-gray-600" />
            </button>
            <button
              className="p-2.5 bg-white rounded-lg shadow hover:bg-gray-50 transition-colors"
              title="Zoom (Mausrad)"
            >
              <ZoomIn className="w-5 h-5 text-gray-600" />
            </button>
            <button
              onClick={handleResetView}
              className="p-2.5 bg-white rounded-lg shadow hover:bg-gray-50 transition-colors"
              title="Ansicht zurücksetzen"
            >
              <Home className="w-5 h-5 text-gray-600" />
            </button>

            {/* Polygon info badge */}
            {polygonPointCount > 0 && (
              <span className="px-3 py-2 bg-white rounded-lg shadow text-sm text-gray-500">
                {polygonPointCount} Punkte
              </span>
            )}
          </div>

          {/* View Selector */}
          <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg overflow-hidden">
            {views.map((view) => (
              <button
                key={view.id}
                onClick={() => setActiveView(view.id)}
                className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors ${
                  activeView === view.id ? 'font-medium bg-gray-50' : 'text-gray-600'
                }`}
              >
                {activeView === view.id && <span className="text-red-500 mr-2">●</span>}
                {view.label}
              </button>
            ))}
          </div>

          {/* Compass */}
          <div className="absolute top-4 left-4 w-14 h-14 bg-white rounded-full shadow-lg flex items-center justify-center">
            <div className="relative w-10 h-10">
              <span className="absolute top-0 left-1/2 -translate-x-1/2 text-xs text-red-600 font-bold">N</span>
              <span className="absolute bottom-0 left-1/2 -translate-x-1/2 text-xs text-gray-400">S</span>
              <span className="absolute left-0 top-1/2 -translate-y-1/2 text-xs text-gray-400">W</span>
              <span className="absolute right-0 top-1/2 -translate-y-1/2 text-xs text-gray-400">O</span>
            </div>
          </div>

          {/* Info Badge */}
          <div className="absolute bottom-4 right-4 bg-white/95 rounded-lg shadow-lg px-3 py-2 text-sm">
            <p className="font-medium text-gray-800">
              {settings?.work_type === 'facade' ? 'Fassadengerüst' : settings?.work_type === 'roof' ? 'Dachschutz' : 'Volleinrüstung'}
            </p>
            <p className="text-gray-500 text-xs">{formatNumber(totals.scaffold_area_m2)} m² • {totals.facade_count} Fassaden</p>
          </div>
        </div>

        {/* Legend */}
        <div className="p-4 border-t bg-white">
          <div className="flex flex-wrap gap-4 text-sm">
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-red-500 rounded"></span>Nord
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-rose-500 rounded"></span>Ost
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-pink-500 rounded"></span>Süd
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-orange-500 rounded"></span>West
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-amber-500 rounded"></span>Lift
            </span>
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 bg-green-500 rounded"></span>Treppe
            </span>
          </div>
        </div>
      </div>

      {/* Summary Card */}
      <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-4 text-white shadow-lg">
        <h3 className="font-semibold mb-3 flex items-center gap-2">
          📋 Zusammenfassung
        </h3>
        <div className="grid grid-cols-2 gap-3 text-sm mb-4">
          <div>
            <p className="text-green-100">Gerüstfläche</p>
            <p className="text-xl font-bold">{formatNumber(totals.scaffold_area_m2)} m²</p>
          </div>
          <div>
            <p className="text-green-100">Elemente</p>
            <p className="text-xl font-bold">{totals.facade_count} + {totals.corner_count}</p>
          </div>
          <div>
            <p className="text-green-100">Max. Höhe</p>
            <p className="font-bold">
              {totals.max_height_m.toFixed(2)}m ({Math.ceil(totals.max_height_m / (settings?.level_height_m || 2))} Lagen)
            </p>
          </div>
          <div>
            <p className="text-green-100">System</p>
            <p className="font-bold">{settings?.system === 'layher_blitz' ? 'Layher Blitz' : 'Layher Allround'}</p>
          </div>
        </div>
        <div className="border-t border-white/20 pt-3 space-y-1 text-sm">
          <p className="flex items-center gap-2">✅ Alle Fassaden konfiguriert</p>
          <p className="flex items-center gap-2">✅ Höhenausgleich für Gefälle eingeplant</p>
          {totals.max_height_m > 15 && (
            <p className="flex items-center gap-2 text-yellow-200">⚠️ Statik-Prüfung empfohlen ({'>'}15m)</p>
          )}
        </div>
      </div>

      {/* IFC.js Info */}
      <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
        <div className="flex gap-3">
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
            <span className="text-blue-600 font-bold text-sm">IFC</span>
          </div>
          <div>
            <h4 className="font-semibold text-blue-800">IFC.js Integration</h4>
            <p className="text-sm text-blue-700 mt-1">
              3D-Ansicht basiert auf @thatopen/components (IFC.js).
              Export nach IFC/DXF für LayPLAN in Entwicklung.
            </p>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => setCurrentTab('editor')}
          className="flex-1 py-3 border border-gray-300 bg-white rounded-xl font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          ← Bearbeiten
        </button>
        <button className="flex-1 py-3 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 shadow-sm transition-colors">
          📦 Materialliste
        </button>
      </div>
    </div>
  );
}
