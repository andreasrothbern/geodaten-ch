/**
 * SystemSelector - Select scaffold system (Layher Blitz/Allround) and bay width
 */

import { Zap, Circle } from 'lucide-react';
import type { ScaffoldSystem, BayWidth } from '../../types/scaffold.types';

interface SystemSelectorProps {
  system: ScaffoldSystem;
  bayWidth: BayWidth;
  onSystemChange: (system: ScaffoldSystem) => void;
  onBayWidthChange: (width: BayWidth) => void;
}

const SYSTEMS: {
  id: ScaffoldSystem;
  label: string;
  description: string;
  icon: React.ReactNode;
  iconBg: string;
  iconColor: string;
}[] = [
  {
    id: 'layher_blitz',
    label: 'Layher Blitz',
    description: '2.57m Feld • Standard',
    icon: <Zap className="w-5 h-5" />,
    iconBg: 'bg-red-100',
    iconColor: 'text-red-600',
  },
  {
    id: 'layher_allround',
    label: 'Layher Allround',
    description: 'Modular • Flexibel',
    icon: <Circle className="w-5 h-5" />,
    iconBg: 'bg-gray-100',
    iconColor: 'text-gray-400',
  },
];

const BAY_WIDTHS: { value: BayWidth; label: string }[] = [
  { value: 0.73, label: 'W09 (0.73m)' },
  { value: 1.09, label: 'W13 (1.09m)' },
];

export default function SystemSelector({
  system,
  bayWidth,
  onSystemChange,
  onBayWidthChange,
}: SystemSelectorProps) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm">
      <h3 className="font-semibold text-gray-700 mb-3">Gerüstsystem</h3>

      {/* System Selection */}
      <div className="grid grid-cols-2 gap-2">
        {SYSTEMS.map((s) => {
          const isActive = system === s.id;
          return (
            <button
              key={s.id}
              onClick={() => onSystemChange(s.id)}
              className={`p-3 border-2 rounded-xl text-left transition-all ${
                isActive
                  ? 'bg-red-50 border-red-500'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    isActive ? 'bg-red-100' : s.iconBg
                  }`}
                >
                  <span className={isActive ? 'text-red-600' : s.iconColor}>
                    {s.icon}
                  </span>
                </div>
                <div>
                  <p className="font-semibold text-gray-800">{s.label}</p>
                  <p className="text-xs text-gray-500">{s.description}</p>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Bay Width Selection */}
      <div className="mt-3 pt-3 border-t">
        <p className="text-sm text-gray-600 mb-2">Belagbreite</p>
        <div className="flex gap-2">
          {BAY_WIDTHS.map((bw) => (
            <button
              key={bw.value}
              onClick={() => onBayWidthChange(bw.value)}
              className={`flex-1 py-2 px-3 border-2 rounded-lg text-sm font-medium transition-all ${
                bayWidth === bw.value
                  ? 'bg-red-50 border-red-500 text-red-600'
                  : 'border-gray-200 text-gray-700 hover:border-gray-300'
              }`}
            >
              {bw.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
