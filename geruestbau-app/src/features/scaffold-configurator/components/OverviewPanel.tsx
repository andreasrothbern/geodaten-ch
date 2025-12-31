/**
 * Overview Panel - Tab 1
 * Global settings, summary stats, and facade cards
 * (Placeholder - to be implemented in Phase 2)
 */

import { LayoutGrid } from 'lucide-react';
import { useScaffoldConfig, useTotals, useSettings, useElements } from '../hooks/useScaffoldConfig';
import { formatNumber, formatWeight } from '../utils/calculations';

export default function OverviewPanel() {
  const { buildingName, buildingAddress, setCurrentTab } = useScaffoldConfig();
  const totals = useTotals();
  const settings = useSettings();
  const elements = useElements();

  const facades = elements.filter((el) => el.type === 'facade');
  // corners available for future use
  void elements.filter((el) => el.type === 'corner');

  return (
    <div className="space-y-4">
      {/* Project Header */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="font-bold text-gray-800 text-lg">{buildingName || 'Projekt'}</h2>
            <p className="text-sm text-gray-500">{buildingAddress || 'Adresse'}</p>
          </div>
          <span className="bg-green-100 text-green-700 text-xs px-2.5 py-1 rounded-full font-medium flex items-center gap-1">
            <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
            Vollständig
          </span>
        </div>

        {/* Mini Floor Plan Placeholder */}
        <div className="mt-4 flex items-center gap-6">
          <div className="w-24 h-24 bg-gray-100 rounded-lg flex items-center justify-center">
            <LayoutGrid className="w-8 h-8 text-gray-400" />
          </div>
          <div className="flex-1 grid grid-cols-2 gap-2 text-sm">
            {facades.slice(0, 4).map((facade) => (
              <div key={facade.id} className="flex items-center gap-2">
                <span
                  className="w-3 h-3 rounded"
                  style={{ backgroundColor: facade.type === 'facade' ? facade.color : '#f59e0b' }}
                ></span>
                <span className="text-gray-600">
                  {facade.name} ({facade.type === 'facade' ? `${facade.length_m}m` : ''})
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Work Type Selection - Placeholder */}
      <div className="bg-white rounded-xl p-4 shadow-sm">
        <h3 className="font-semibold text-gray-700 mb-3">Art der Arbeiten</h3>
        <div className="flex gap-2">
          {(['facade', 'roof', 'full'] as const).map((type) => (
            <button
              key={type}
              className={`flex-1 py-2.5 px-3 border-2 rounded-xl text-sm font-medium transition-all ${
                settings?.work_type === type
                  ? 'bg-red-600 text-white border-red-600'
                  : 'border-gray-200 text-gray-700 hover:border-gray-300'
              }`}
            >
              {type === 'facade' && 'Fassade'}
              {type === 'roof' && 'Dacharbeiten'}
              {type === 'full' && 'Komplett'}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-xl p-4 text-white shadow-lg">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold flex items-center gap-2">
            Gesamtberechnung
          </h3>
          <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">
            {settings?.system === 'layher_blitz' ? 'Layher Blitz' : 'Layher Allround'}
          </span>
        </div>

        <div className="grid grid-cols-4 gap-2 mb-4">
          <div className="bg-white/20 rounded-lg p-2.5 text-center">
            <p className="text-2xl font-bold">{formatNumber(totals.scaffold_area_m2)}</p>
            <p className="text-xs text-white/80">m² Gerüst</p>
          </div>
          <div className="bg-white/20 rounded-lg p-2.5 text-center">
            <p className="text-2xl font-bold">{totals.facade_count}</p>
            <p className="text-xs text-white/80">Fassaden</p>
          </div>
          <div className="bg-white/20 rounded-lg p-2.5 text-center">
            <p className="text-2xl font-bold">{totals.corner_count}</p>
            <p className="text-xs text-white/80">Ecken</p>
          </div>
          <div className="bg-white/20 rounded-lg p-2.5 text-center">
            <p className="text-2xl font-bold">
              {Math.ceil(totals.max_height_m / (settings?.level_height_m || 2))}
            </p>
            <p className="text-xs text-white/80">Lagen</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-white/90">
          <p>Umfang: {totals.perimeter_m.toFixed(1)}m</p>
          <p>Höhe: {totals.max_height_m.toFixed(1)}m</p>
          <p>Gefälle: — (max)</p>
          <p>{formatWeight(totals.estimated_weight_kg)}</p>
        </div>
      </div>

      {/* Facade Cards */}
      <div className="space-y-3">
        <h3 className="font-semibold text-gray-700 flex items-center justify-between">
          <span>Fassaden & Ecken</span>
          <span className="text-xs text-gray-400 font-normal">{elements.length} Elemente</span>
        </h3>

        <div className="grid grid-cols-2 gap-3">
          {elements.map((el, index) => (
            <button
              key={el.id}
              onClick={() => {
                useScaffoldConfig.getState().jumpToElement(index);
              }}
              className={`text-left rounded-xl p-3 shadow-sm cursor-pointer transition-all hover:shadow-md ${
                el.type === 'corner'
                  ? 'bg-amber-50 border border-amber-200'
                  : 'bg-white border-l-4'
              }`}
              style={el.type === 'facade' ? { borderLeftColor: el.color } : undefined}
            >
              {el.type === 'corner' ? (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-amber-100 rounded-lg flex items-center justify-center">
                      <span className="text-amber-600 text-xs font-bold">⌐</span>
                    </div>
                    <span className="font-medium text-amber-800">{el.name}</span>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-gray-800">{el.name}</span>
                  </div>
                  <p className="text-lg font-bold text-gray-800">
                    {el.length_m}<span className="text-sm font-normal text-gray-500">m</span>
                  </p>
                  <div className="flex justify-between items-center mt-1">
                    <span className="text-xs text-gray-500">{el.fields}×{el.levels} Felder</span>
                    <span className="text-sm font-medium" style={{ color: el.color }}>
                      {Math.round(el.fields * el.levels * (settings?.field_width_m || 2.57) * (settings?.level_height_m || 2))}m²
                    </span>
                  </div>
                </>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Action Button */}
      <div className="flex gap-3">
        <button
          onClick={() => setCurrentTab('editor')}
          className="flex-1 py-3 bg-red-600 text-white rounded-xl font-medium hover:bg-red-700 shadow-sm flex items-center justify-center gap-2"
        >
          Im Editor bearbeiten
        </button>
      </div>
    </div>
  );
}
