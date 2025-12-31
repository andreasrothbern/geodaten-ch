/**
 * 3D Panel - Tab 3
 * 3D visualization placeholder (IFC.js/xeokit to be implemented later)
 */

import { Box, RotateCw, ZoomIn, Home, Code } from 'lucide-react';
import { useScaffoldConfig, useTotals, useSettings } from '../hooks/useScaffoldConfig';
import { formatNumber } from '../utils/calculations';

export default function ThreeDPanel() {
  const { setCurrentTab } = useScaffoldConfig();
  const totals = useTotals();
  const settings = useSettings();

  const views = [
    { id: 'isometric', label: 'Isometrisch', active: true },
    { id: 'north', label: 'Nord', active: false },
    { id: 'east', label: 'Ost', active: false },
    { id: 'south', label: 'Süd', active: false },
    { id: 'west', label: 'West', active: false },
    { id: 'top', label: 'Draufsicht', active: false },
  ];

  return (
    <div className="space-y-4">
      {/* 3D Viewer Placeholder */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div
          className="relative"
          style={{
            minHeight: '400px',
            background: 'linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 50%, #e0f2fe 100%)',
          }}
        >
          {/* Placeholder 3D Illustration */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="w-24 h-24 bg-white/80 rounded-2xl mx-auto mb-4 flex items-center justify-center shadow-lg">
                <Box className="w-12 h-12 text-blue-500" />
              </div>
              <h3 className="text-lg font-semibold text-gray-700">3D-Visualisierung</h3>
              <p className="text-sm text-gray-500 mt-1">Wird in Phase 4 implementiert</p>
              <p className="text-xs text-gray-400 mt-2">
                {totals.facade_count} Fassaden • {formatNumber(totals.scaffold_area_m2)} m²
              </p>
            </div>
          </div>

          {/* 3D Controls */}
          <div className="absolute bottom-4 left-4 flex gap-2">
            <button className="p-2.5 bg-white rounded-lg shadow hover:bg-gray-50 transition-colors">
              <RotateCw className="w-5 h-5 text-gray-600" />
            </button>
            <button className="p-2.5 bg-white rounded-lg shadow hover:bg-gray-50 transition-colors">
              <ZoomIn className="w-5 h-5 text-gray-600" />
            </button>
            <button className="p-2.5 bg-white rounded-lg shadow hover:bg-gray-50 transition-colors">
              <Home className="w-5 h-5 text-gray-600" />
            </button>
          </div>

          {/* View Selector */}
          <div className="absolute top-4 right-4 bg-white rounded-lg shadow-lg overflow-hidden">
            {views.map((view, index) => (
              <button
                key={view.id}
                className={`block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 ${
                  view.active ? 'font-medium bg-gray-50' : 'text-gray-600'
                } ${index > 0 && view.id === 'top' ? 'border-t' : ''}`}
              >
                {view.active && <span className="text-red-500 mr-2">●</span>}
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
            <p className="font-medium text-gray-800">Volleinrüstung</p>
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
              <span className="w-4 h-4 bg-amber-500 rounded"></span>Ecken
            </span>
          </div>
        </div>
      </div>

      {/* Implementation Note */}
      <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
        <div className="flex gap-3">
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
            <Code className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <h4 className="font-semibold text-blue-800">3D-Visualisierung: Library-Auswahl</h4>
            <p className="text-sm text-blue-700 mt-1 mb-3">
              Für die echte 3D-Darstellung stehen zwei Optionen zur Verfügung:
            </p>

            <div className="space-y-2">
              <div className="bg-white/60 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-blue-900">Three.js</span>
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">Schneller Start</span>
                </div>
                <p className="text-xs text-blue-600 mt-1">
                  + Flexibel, grosse Community<br />
                  + Gute Performance<br />
                  − Kein nativer IFC-Support
                </p>
              </div>

              <div className="bg-white/60 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-blue-900">IFC.js / xeokit</span>
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Empfohlen für BIM</span>
                </div>
                <p className="text-xs text-blue-600 mt-1">
                  + Nativer IFC Import/Export<br />
                  + BIM-Workflows (LayPLAN kompatibel)<br />
                  + swissBUILDINGS3D direkt ladbar<br />
                  − Steilere Lernkurve
                </p>
              </div>
            </div>

            <p className="text-xs text-blue-600 mt-3 italic">
              💡 Empfehlung: IFC.js/xeokit für direkten Export nach LayPLAN und DXF
            </p>
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
              {totals.max_height_m.toFixed(1)}m ({Math.ceil(totals.max_height_m / (settings?.level_height_m || 2))} Lagen)
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

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => setCurrentTab('editor')}
          className="flex-1 py-3 border border-gray-300 bg-white rounded-xl font-medium text-gray-700 hover:bg-gray-50"
        >
          ← Bearbeiten
        </button>
        <button className="flex-1 py-3 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 shadow-sm">
          📦 Materialliste
        </button>
      </div>
    </div>
  );
}
