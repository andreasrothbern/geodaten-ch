/**
 * WorkTypeSelector - Select work type (facade, roof, full)
 */

import { Building2, Home, Maximize2 } from 'lucide-react';
import type { WorkType } from '../../types/scaffold.types';

interface WorkTypeSelectorProps {
  value: WorkType;
  onChange: (type: WorkType) => void;
}

// FIX 27.01.2026: 'full' (Komplett) ersetzt durch 'roofer' (Spengler)
const WORK_TYPES: {
  id: WorkType;
  label: string;
  description: string;
  icon: React.ReactNode;
}[] = [
  {
    id: 'facade',
    label: 'Fassade',
    description: 'Bis Traufe',
    icon: <Building2 className="w-4 h-4" />,
  },
  {
    id: 'roof',
    label: 'Dacharbeiten',
    description: '+1m Schutz',
    icon: <Home className="w-4 h-4" />,
  },
  {
    id: 'roofer',
    label: 'Spengler',
    description: 'First -1m',
    icon: <Maximize2 className="w-4 h-4" />,
  },
];

export default function WorkTypeSelector({ value, onChange }: WorkTypeSelectorProps) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm">
      <h3 className="font-semibold text-gray-700 mb-3">Art der Arbeiten</h3>
      <div className="flex gap-2">
        {WORK_TYPES.map((type) => (
          <button
            key={type.id}
            onClick={() => onChange(type.id)}
            className={`flex-1 py-2.5 px-3 border-2 rounded-xl text-sm font-medium transition-all ${
              value === type.id
                ? 'bg-red-600 text-white border-red-600'
                : 'border-gray-200 text-gray-700 hover:border-gray-300'
            }`}
          >
            <span className="flex items-center justify-center gap-1.5">
              {type.icon}
              {type.label}
            </span>
            <span
              className={`block text-xs font-normal mt-0.5 ${
                value === type.id ? 'opacity-80' : 'text-gray-500'
              }`}
            >
              {type.description}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
