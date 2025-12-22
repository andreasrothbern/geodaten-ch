/**
 * Settings Panel Component
 *
 * Slide-out panel for managing user preferences.
 * Accessed via gear icon in the header.
 */

import { useState } from 'react'
import {
  useUserPreferences,
  type FloorHeight,
  type ScaffoldingSystem,
  type WidthClass,
  type RoofForm,
  type WorkType,
  type ScaffoldType,
} from '../hooks/useUserPreferences'

interface SettingsPanelProps {
  isOpen: boolean
  onClose: () => void
}

export function SettingsPanel({ isOpen, onClose }: SettingsPanelProps) {
  const { preferences, updatePreferences, DEFAULT_PREFERENCES } = useUserPreferences()
  const [localPrefs, setLocalPrefs] = useState(preferences)
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    updatePreferences(localPrefs)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleReset = () => {
    setLocalPrefs(DEFAULT_PREFERENCES)
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-xl z-50 overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <span>&#9881;</span> Einstellungen
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl"
          >
            &times;
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Success message */}
          {saved && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-2 rounded-lg">
              Einstellungen gespeichert
            </div>
          )}

          {/* Work Type Section */}
          <section className="space-y-3">
            <h3 className="font-medium text-gray-900 border-b pb-2">Arbeitstyp</h3>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Standard-Arbeitstyp</label>
              <select
                value={localPrefs.defaultWorkType}
                onChange={(e) => setLocalPrefs({ ...localPrefs, defaultWorkType: e.target.value as WorkType })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="dacharbeiten">Dacharbeiten (+1m SUVA)</option>
                <option value="fassadenarbeiten">Fassadenarbeiten (bis Traufe)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Standard-Gerustart</label>
              <select
                value={localPrefs.defaultScaffoldType}
                onChange={(e) => setLocalPrefs({ ...localPrefs, defaultScaffoldType: e.target.value as ScaffoldType })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="arbeitsgeruest">Arbeitsgerust (Standard)</option>
                <option value="schutzgeruest">Schutzgerust (Dacharbeiten)</option>
                <option value="fanggeruest">Fanggerust (Absturzsicherung)</option>
              </select>
            </div>
          </section>

          {/* System Section */}
          <section className="space-y-3">
            <h3 className="font-medium text-gray-900 border-b pb-2">Gerustsystem</h3>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Bevorzugtes System</label>
              <select
                value={localPrefs.defaultSystem}
                onChange={(e) => setLocalPrefs({ ...localPrefs, defaultSystem: e.target.value as ScaffoldingSystem })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="blitz70">Layher Blitz 70 (Standard)</option>
                <option value="allround">Layher Allround (Industriell)</option>
                <option value="combined">Blitz + Allround Kombination</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                Blitz: Schneller Aufbau, leichte Lasten. Allround: Hohere Tragfahigkeit, flexibel.
              </p>
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Standard-Breitenklasse</label>
              <select
                value={localPrefs.defaultWidthClass}
                onChange={(e) => setLocalPrefs({ ...localPrefs, defaultWidthClass: e.target.value as WidthClass })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="W06">W06 - 0.60m (Schmal)</option>
                <option value="W09">W09 - 0.90m (Standard)</option>
                <option value="W12">W12 - 1.20m (Breit)</option>
              </select>
            </div>
          </section>

          {/* Material Section */}
          <section className="space-y-3">
            <h3 className="font-medium text-gray-900 border-b pb-2">Material</h3>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Bevorzugte Bodenhohe</label>
              <select
                value={localPrefs.defaultFloorHeight}
                onChange={(e) => setLocalPrefs({ ...localPrefs, defaultFloorHeight: e.target.value as FloorHeight })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="2.5">2.5m Boden (Leichter)</option>
                <option value="3.0">3.0m Boden (Standard)</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                2.5m Boden sind leichter zu handhaben, 3.0m bieten mehr Arbeitshohe.
              </p>
            </div>
          </section>

          {/* Building Defaults */}
          <section className="space-y-3">
            <h3 className="font-medium text-gray-900 border-b pb-2">Gebaude-Annahmen</h3>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Standard-Dachform</label>
              <select
                value={localPrefs.defaultRoofForm}
                onChange={(e) => setLocalPrefs({ ...localPrefs, defaultRoofForm: e.target.value as RoofForm })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                <option value="satteldach">Satteldach</option>
                <option value="walmdach">Walmdach</option>
                <option value="flach">Flachdach</option>
              </select>
            </div>
          </section>

          {/* Actions */}
          <div className="pt-4 border-t flex gap-3">
            <button
              onClick={handleSave}
              className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Speichern
            </button>
            <button
              onClick={handleReset}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Zurucksetzen
            </button>
          </div>

          {/* Info */}
          <p className="text-xs text-gray-400 text-center">
            Einstellungen werden lokal im Browser gespeichert.
          </p>
        </div>
      </div>
    </>
  )
}
