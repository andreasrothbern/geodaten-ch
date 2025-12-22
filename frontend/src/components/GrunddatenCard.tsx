/**
 * Grunddaten Card Component
 *
 * Displays all base data from APIs:
 * - Address and coordinates
 * - GWR data (EGID, floors, area, etc.)
 * - Height data (estimated + measured from swissBUILDINGS3D)
 * - Manual height input option
 */

import { useState } from 'react'
import type { ScaffoldingData } from '../types'

interface GrunddatenCardProps {
  data: ScaffoldingData
  onFetchMeasuredHeight?: () => void
  fetchingHeight?: boolean
  onHeightChange?: (height: number) => void
}

export function GrunddatenCard({
  data,
  onFetchMeasuredHeight,
  fetchingHeight = false,
  onHeightChange
}: GrunddatenCardProps) {
  const [manualHeight, setManualHeight] = useState<string>('')
  const { dimensions, gwr_data, building, address } = data

  const handleManualHeightSubmit = () => {
    const height = parseFloat(manualHeight)
    if (!isNaN(height) && height > 0 && onHeightChange) {
      onHeightChange(height)
      setManualHeight('')
    }
  }

  // Check if measured height exists
  const hasMeasuredHeight = dimensions.traufhoehe_m !== null || dimensions.firsthoehe_m !== null

  return (
    <div className="card space-y-6">
      <h3 className="text-lg font-semibold text-gray-800 border-b pb-2">
        Grunddaten
      </h3>

      {/* Address & Coordinates */}
      <section className="space-y-2">
        <h4 className="font-medium text-gray-700">Adresse</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500">Eingabe:</span>
            <span className="ml-2 font-medium">{address?.input || '-'}</span>
          </div>
          <div>
            <span className="text-gray-500">Gefunden:</span>
            <span className="ml-2 font-medium">{address?.matched || '-'}</span>
          </div>
          <div>
            <span className="text-gray-500">Koordinaten (LV95):</span>
            <span className="ml-2 font-mono text-xs">
              E: {address?.coordinates?.lv95_e?.toFixed(1) || '-'},
              N: {address?.coordinates?.lv95_n?.toFixed(1) || '-'}
            </span>
          </div>
        </div>
      </section>

      {/* GWR Data */}
      <section className="space-y-2">
        <h4 className="font-medium text-gray-700">GWR-Daten (Gebaude- und Wohnungsregister)</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="bg-gray-50 rounded p-3">
            <p className="text-gray-500 text-xs">EGID</p>
            <p className="font-medium">{gwr_data?.egid || '-'}</p>
          </div>
          <div className="bg-gray-50 rounded p-3">
            <p className="text-gray-500 text-xs">Geschosse</p>
            <p className="font-medium">{gwr_data?.floors || dimensions.floors || '-'}</p>
          </div>
          <div className="bg-gray-50 rounded p-3">
            <p className="text-gray-500 text-xs">Grundflache</p>
            <p className="font-medium">
              {building?.footprint_area_m2?.toFixed(0) || gwr_data?.area_m2_gwr?.toFixed(0) || '-'} m2
            </p>
          </div>
          <div className="bg-gray-50 rounded p-3">
            <p className="text-gray-500 text-xs">Kategorie</p>
            <p className="font-medium text-xs">{gwr_data?.building_category || '-'}</p>
          </div>
          {gwr_data?.construction_year && (
            <div className="bg-gray-50 rounded p-3">
              <p className="text-gray-500 text-xs">Baujahr</p>
              <p className="font-medium">{gwr_data.construction_year}</p>
            </div>
          )}
          <div className="bg-gray-50 rounded p-3">
            <p className="text-gray-500 text-xs">Umfang</p>
            <p className="font-medium">{dimensions.perimeter_m?.toFixed(1) || '-'} m</p>
          </div>
        </div>
      </section>

      {/* Height Data */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-gray-700">Hohendaten</h4>
          {!hasMeasuredHeight && onFetchMeasuredHeight && (
            <button
              onClick={onFetchMeasuredHeight}
              disabled={fetchingHeight}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {fetchingHeight ? 'Lade...' : 'Hohe aus swissBUILDINGS3D abrufen'}
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Estimated Height */}
          <div className={`rounded-lg p-4 ${hasMeasuredHeight ? 'bg-gray-100' : 'bg-yellow-50 border border-yellow-200'}`}>
            <p className="text-xs text-gray-500 mb-1">Geschatzte Hohe</p>
            <p className="text-2xl font-bold text-gray-700">
              {dimensions.height_estimated_m?.toFixed(1) || '-'} m
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {dimensions.height_estimated_source || 'Aus Geschossen berechnet'}
            </p>
          </div>

          {/* Measured Heights from swissBUILDINGS3D */}
          {hasMeasuredHeight ? (
            <>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-xs text-green-600 mb-1">Traufhohe (gemessen)</p>
                <p className="text-2xl font-bold text-green-700">
                  {dimensions.traufhoehe_m?.toFixed(1) || '-'} m
                </p>
                <p className="text-xs text-green-500 mt-1">swissBUILDINGS3D</p>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-xs text-green-600 mb-1">Firsthohe (gemessen)</p>
                <p className="text-2xl font-bold text-green-700">
                  {dimensions.firsthoehe_m?.toFixed(1) || '-'} m
                </p>
                <p className="text-xs text-green-500 mt-1">swissBUILDINGS3D</p>
              </div>
            </>
          ) : (
            <div className="col-span-2 bg-amber-50 border border-amber-200 rounded-lg p-4">
              <p className="text-amber-700 text-sm">
                Keine gemessenen Hohen verfugbar. Klicken Sie auf "Hohe aus swissBUILDINGS3D abrufen"
                oder geben Sie die Hohe manuell ein.
              </p>
            </div>
          )}
        </div>

        {/* Manual Height Input */}
        <div className="bg-gray-50 rounded-lg p-4">
          <p className="text-sm text-gray-600 mb-2">Manuelle Hoheneingabe (falls keine Daten verfugbar)</p>
          <div className="flex gap-2">
            <input
              type="number"
              step="0.1"
              min="1"
              max="100"
              value={manualHeight}
              onChange={(e) => setManualHeight(e.target.value)}
              placeholder="Hohe in Metern"
              className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
            <button
              onClick={handleManualHeightSubmit}
              disabled={!manualHeight || parseFloat(manualHeight) <= 0}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors"
            >
              Ubernehmen
            </button>
          </div>
        </div>

        {/* Current Active Height */}
        {dimensions.estimated_height_m && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-blue-600">Aktive Hohe fur Berechnung</p>
                <p className="text-xl font-bold text-blue-700">
                  {dimensions.estimated_height_m?.toFixed(1)} m
                </p>
              </div>
              <p className="text-xs text-blue-500">
                Quelle: {dimensions.height_source || 'unbekannt'}
              </p>
            </div>
          </div>
        )}
      </section>

      {/* 3D Viewer Link */}
      {data.viewer_3d_url && (
        <section className="pt-2 border-t">
          <a
            href={data.viewer_3d_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800 text-sm"
          >
            <span>3D-Ansicht in map.geo.admin.ch offnen</span>
            <span>↗</span>
          </a>
        </section>
      )}
    </div>
  )
}
