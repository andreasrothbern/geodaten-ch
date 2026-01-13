/**
 * FacadeCards - Carousel of facade detail cards
 */

import { ChevronLeft, ChevronRight, Ruler, ArrowUpFromLine, Percent } from 'lucide-react';
import type { ScaffoldFacade, ScaffoldSettings } from '../../types/scaffold.types';
import { formatNumber } from '../../utils/calculations';

interface FacadeCardsProps {
  facades: ScaffoldFacade[];
  settings: ScaffoldSettings;
  currentIndex: number;
  onNavigate: (direction: 'prev' | 'next') => void;
  onSelectFacade: (index: number) => void;
}

export default function FacadeCards({
  facades,
  settings,
  currentIndex,
  onNavigate,
  onSelectFacade,
}: FacadeCardsProps) {
  if (facades.length === 0) {
    return (
      <div className="bg-gray-50 rounded-xl p-6 text-center text-gray-500">
        Keine Fassaden ausgewählt
      </div>
    );
  }

  const currentFacade = facades[currentIndex];
  const area = currentFacade.length_m * currentFacade.target_height_m;

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden">
      {/* Carousel Navigation Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
        <button
          onClick={() => onNavigate('prev')}
          disabled={facades.length <= 1}
          className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-30"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>

        {/* Pagination Dots */}
        <div className="flex gap-1.5">
          {facades.map((facade, i) => (
            <button
              key={facade.id}
              onClick={() => onSelectFacade(i)}
              className={`w-2 h-2 rounded-full transition-all ${
                i === currentIndex
                  ? 'bg-red-500 w-4'
                  : 'bg-gray-300 hover:bg-gray-400'
              }`}
              aria-label={`Fassade ${i + 1}`}
            />
          ))}
        </div>

        <button
          onClick={() => onNavigate('next')}
          disabled={facades.length <= 1}
          className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-30"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Facade Detail Card */}
      <div className="p-4">
        {/* Facade Header */}
        <div className="flex items-center gap-3 mb-4">
          <div
            className="w-3 h-12 rounded"
            style={{ backgroundColor: currentFacade.color }}
          />
          <div>
            <h4 className="font-semibold text-gray-800">{currentFacade.name}</h4>
            <p className="text-sm text-gray-500">
              {currentFacade.fields} Felder × {currentFacade.levels} Lagen
            </p>
          </div>
          <div className="ml-auto">
            <span className="text-2xl font-bold text-gray-800">
              {formatNumber(area)}
            </span>
            <span className="text-sm text-gray-500 ml-1">m²</span>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <Ruler className="w-4 h-4 mx-auto text-gray-400 mb-1" />
            <p className="text-lg font-semibold text-gray-800">
              {currentFacade.length_m.toFixed(1)}m
            </p>
            <p className="text-xs text-gray-500">Länge</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <ArrowUpFromLine className="w-4 h-4 mx-auto text-gray-400 mb-1" />
            <p className="text-lg font-semibold text-gray-800">
              {currentFacade.target_height_m.toFixed(2)}m
            </p>
            <p className="text-xs text-gray-500">Höhe</p>
            {/* NEU 13.01.2026 - Terrain-Höhe bei Hanglage anzeigen */}
            {currentFacade.terrain_z_min !== undefined && (
              <p className="text-xs text-blue-500 mt-0.5">
                Terrain: {currentFacade.terrain_z_min.toFixed(1)}m ü.M.
              </p>
            )}
          </div>
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <Percent className="w-4 h-4 mx-auto text-gray-400 mb-1" />
            <p className="text-lg font-semibold text-gray-800">
              {currentFacade.slope_percent.toFixed(1)}%
            </p>
            <p className="text-xs text-gray-500">Gefälle</p>
          </div>
        </div>

        {/* NEU 13.01.2026 - Hanglage-Hinweis wenn Terrain-Differenz > 0.5m */}
        {currentFacade.terrain_diff_m !== undefined && currentFacade.terrain_diff_m > 0.5 && (
          <div className="mt-2 px-2 py-1 bg-amber-50 border border-amber-200 rounded text-xs text-amber-700">
            ⚠️ Hanglage: {currentFacade.terrain_diff_m.toFixed(1)}m Höhendifferenz → Ausnivellierung erforderlich
          </div>
        )}

        {/* Equipment Badges */}
        {(currentFacade.modifications.lift_position !== null ||
          currentFacade.modifications.stairs_position !== null) && (
          <div className="flex gap-2 mt-3">
            {currentFacade.modifications.lift_position !== null && (
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full font-medium">
                Aufzug bei Feld {currentFacade.modifications.lift_position + 1}
              </span>
            )}
            {currentFacade.modifications.stairs_position !== null && (
              <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full font-medium">
                Treppe bei Feld {currentFacade.modifications.stairs_position + 1}
              </span>
            )}
          </div>
        )}

        {/* System Info */}
        <div className="mt-3 pt-3 border-t text-xs text-gray-500 flex justify-between">
          <span>
            {settings.system === 'layher_blitz' ? 'Blitz' : 'Allround'} ·{' '}
            {settings.field_width_m}m Felder
          </span>
          <span>W{settings.bay_width_m === 0.73 ? '09' : '13'}</span>
        </div>
      </div>
    </div>
  );
}
