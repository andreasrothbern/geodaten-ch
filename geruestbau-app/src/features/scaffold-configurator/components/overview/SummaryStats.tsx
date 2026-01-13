/**
 * SummaryStats - Gradient card with total scaffold statistics
 */

import { Calculator, Ruler, Mountain, Weight } from 'lucide-react';
import type { ScaffoldTotals, ScaffoldSettings } from '../../types/scaffold.types';
import { formatNumber, formatWeight } from '../../utils/calculations';

interface SummaryStatsProps {
  totals: ScaffoldTotals;
  settings: ScaffoldSettings;
  maxSlope?: number;
}

export default function SummaryStats({ totals, settings, maxSlope = 0 }: SummaryStatsProps) {
  const levels = Math.ceil(totals.max_height_m / settings.level_height_m);
  const systemLabel = settings.system === 'layher_blitz' ? 'Layher Blitz' : 'Layher Allround';

  return (
    <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-xl p-4 text-white shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold flex items-center gap-2">
          <Calculator className="w-4 h-4" />
          Gesamtberechnung
        </h3>
        <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">
          {systemLabel}
        </span>
      </div>

      {/* Main Stats Grid */}
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
          <p className="text-2xl font-bold">{levels}</p>
          <p className="text-xs text-white/80">Lagen</p>
        </div>
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm text-white/90">
        <p className="flex items-center gap-2">
          <Ruler className="w-4 h-4 opacity-70" />
          Umfang: {totals.perimeter_m.toFixed(1)}m
        </p>
        <p className="flex items-center gap-2">
          <Ruler className="w-4 h-4 opacity-70 rotate-90" />
          Höhe: {totals.max_height_m.toFixed(2)}m
        </p>
        <p className="flex items-center gap-2">
          <Mountain className="w-4 h-4 opacity-70" />
          Gefälle: {maxSlope.toFixed(1)}% (max)
        </p>
        <p className="flex items-center gap-2">
          <Weight className="w-4 h-4 opacity-70" />
          {formatWeight(totals.estimated_weight_kg)}
        </p>
      </div>
    </div>
  );
}
