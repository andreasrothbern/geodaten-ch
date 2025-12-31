/**
 * GlobalOptions - Toggle switches for safety net and weather cover
 */

import { Shield, Cloud } from 'lucide-react';

interface GlobalOptionsProps {
  safetyNet: boolean;
  weatherCover: boolean;
  onSafetyNetChange: (enabled: boolean) => void;
  onWeatherCoverChange: (enabled: boolean) => void;
}

export default function GlobalOptions({
  safetyNet,
  weatherCover,
  onSafetyNetChange,
  onWeatherCoverChange,
}: GlobalOptionsProps) {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm">
      <h3 className="font-semibold text-gray-700 mb-3">Zusatzoptionen</h3>

      <div className="space-y-3">
        {/* Safety Net Toggle */}
        <label className="flex items-center justify-between cursor-pointer group">
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
                safetyNet ? 'bg-blue-100' : 'bg-gray-100 group-hover:bg-gray-200'
              }`}
            >
              <Shield
                className={`w-5 h-5 transition-colors ${
                  safetyNet ? 'text-blue-600' : 'text-gray-400'
                }`}
              />
            </div>
            <div>
              <p className="font-medium text-gray-800">Schutznetz</p>
              <p className="text-xs text-gray-500">Fangnetz nach SUVA</p>
            </div>
          </div>
          <button
            role="switch"
            aria-checked={safetyNet}
            onClick={() => onSafetyNetChange(!safetyNet)}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              safetyNet ? 'bg-blue-600' : 'bg-gray-300'
            }`}
          >
            <span
              className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                safetyNet ? 'translate-x-6' : 'translate-x-0'
              }`}
            />
          </button>
        </label>

        {/* Weather Cover Toggle */}
        <label className="flex items-center justify-between cursor-pointer group">
          <div className="flex items-center gap-3">
            <div
              className={`w-10 h-10 rounded-lg flex items-center justify-center transition-colors ${
                weatherCover ? 'bg-blue-100' : 'bg-gray-100 group-hover:bg-gray-200'
              }`}
            >
              <Cloud
                className={`w-5 h-5 transition-colors ${
                  weatherCover ? 'text-blue-600' : 'text-gray-400'
                }`}
              />
            </div>
            <div>
              <p className="font-medium text-gray-800">Wetterschutz</p>
              <p className="text-xs text-gray-500">Plane/Netz gegen Regen</p>
            </div>
          </div>
          <button
            role="switch"
            aria-checked={weatherCover}
            onClick={() => onWeatherCoverChange(!weatherCover)}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              weatherCover ? 'bg-blue-600' : 'bg-gray-300'
            }`}
          >
            <span
              className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                weatherCover ? 'translate-x-6' : 'translate-x-0'
              }`}
            />
          </button>
        </label>
      </div>
    </div>
  );
}
