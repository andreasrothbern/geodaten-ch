/**
 * FacadeSelectionPage - Select which facades to scaffold
 *
 * Shows building polygon with selectable facades.
 * User can toggle facades on/off before proceeding to configurator.
 */

import { useEffect, useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, Loader2, AlertCircle, Compass } from 'lucide-react'
import { geruestbauApi } from '../api/geruestbau'
import type { Project } from '../types/project'

const API_BASE = import.meta.env.VITE_API_URL || 'https://acceptable-trust-production.up.railway.app'

interface Side {
  index: number
  start: { x: number; y: number }
  end: { x: number; y: number }
  length_m: number
  direction: string
  angle_deg: number
}

interface SmartBuildingData {
  egid?: string
  address_matched?: string
  building_name?: string
  polygon?: number[][]
  sides?: Side[]
  traufhoehe_m?: number
  firsthoehe_m?: number
  perimeter_m?: number
  area_m2?: number
}

// Direction labels
const DIRECTION_LABELS: Record<string, string> = {
  'N': 'Nord',
  'NO': 'Nordost',
  'O': 'Ost',
  'SO': 'Südost',
  'S': 'Süd',
  'SW': 'Südwest',
  'W': 'West',
  'NW': 'Nordwest',
}

// Direction colors for visual distinction
const DIRECTION_COLORS: Record<string, string> = {
  'N': '#3B82F6',  // Blue
  'NO': '#6366F1', // Indigo
  'O': '#8B5CF6',  // Violet
  'SO': '#EC4899', // Pink
  'S': '#EF4444',  // Red
  'SW': '#F97316', // Orange
  'W': '#EAB308',  // Yellow
  'NW': '#22C55E', // Green
}

export default function FacadeSelectionPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [project, setProject] = useState<Project | null>(null)
  const [buildingData, setBuildingData] = useState<SmartBuildingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedFacades, setSelectedFacades] = useState<Set<number>>(new Set())

  // Load project and building data
  useEffect(() => {
    if (id) {
      loadData(id)
    }
  }, [id])

  const loadData = async (projectId: string) => {
    setLoading(true)
    setError(null)

    try {
      // Load project
      const proj = await geruestbauApi.getProject(projectId)
      setProject(proj)

      // Fetch fresh building data from SmartBuilding API
      const response = await fetch(
        `${API_BASE}/api/v1/smart-building/data?address=${encodeURIComponent(proj.address)}`
      )

      if (!response.ok) {
        throw new Error('Gebäudedaten konnten nicht geladen werden')
      }

      const data: SmartBuildingData = await response.json()
      setBuildingData(data)

      // Initially select all facades
      if (data.sides) {
        setSelectedFacades(new Set(data.sides.map(s => s.index)))
      }

    } catch (err) {
      console.error('Error loading data:', err)
      setError(err instanceof Error ? err.message : 'Fehler beim Laden')
    } finally {
      setLoading(false)
    }
  }

  // Toggle facade selection
  const toggleFacade = (index: number) => {
    setSelectedFacades(prev => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

  // Select all facades
  const selectAll = () => {
    if (buildingData?.sides) {
      setSelectedFacades(new Set(buildingData.sides.map(s => s.index)))
    }
  }

  // Deselect all facades
  const deselectAll = () => {
    setSelectedFacades(new Set())
  }

  // Calculate total length of selected facades
  const totalSelectedLength = useMemo(() => {
    if (!buildingData?.sides) return 0
    return buildingData.sides
      .filter(s => selectedFacades.has(s.index))
      .reduce((sum, s) => sum + s.length_m, 0)
  }, [buildingData, selectedFacades])

  // Calculate estimated scaffold area
  const estimatedArea = useMemo(() => {
    if (!buildingData?.traufhoehe_m) return 0
    return totalSelectedLength * buildingData.traufhoehe_m
  }, [totalSelectedLength, buildingData])

  // Generate SVG for building polygon
  const polygonSvg = useMemo(() => {
    if (!buildingData?.polygon || !buildingData?.sides) return null

    const polygon = buildingData.polygon
    const sides = buildingData.sides

    // Calculate bounds
    const xs = polygon.map(p => p[0])
    const ys = polygon.map(p => p[1])
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys)

    const width = maxX - minX
    const height = maxY - minY
    const padding = Math.max(width, height) * 0.15

    const viewBox = `${minX - padding} ${minY - padding} ${width + padding * 2} ${height + padding * 2}`

    // Create polygon path
    const pathData = polygon.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ') + ' Z'

    // Create side segments for selection
    const sideElements = sides.map((side) => {
      const isSelected = selectedFacades.has(side.index)
      const color = DIRECTION_COLORS[side.direction] || '#666'
      const midX = (side.start.x + side.end.x) / 2
      const midY = (side.start.y + side.end.y) / 2

      return (
        <g key={side.index} onClick={() => toggleFacade(side.index)} style={{ cursor: 'pointer' }}>
          {/* Side line */}
          <line
            x1={side.start.x}
            y1={side.start.y}
            x2={side.end.x}
            y2={side.end.y}
            stroke={isSelected ? color : '#ccc'}
            strokeWidth={isSelected ? width * 0.02 : width * 0.01}
            strokeLinecap="round"
          />
          {/* Selection indicator */}
          <circle
            cx={midX}
            cy={midY}
            r={width * 0.025}
            fill={isSelected ? color : '#fff'}
            stroke={color}
            strokeWidth={width * 0.005}
          />
          {/* Label */}
          <text
            x={midX}
            y={midY}
            dy={width * 0.06}
            textAnchor="middle"
            fontSize={width * 0.03}
            fill={isSelected ? '#333' : '#999'}
            fontWeight={isSelected ? 'bold' : 'normal'}
          >
            {side.direction} ({side.length_m.toFixed(1)}m)
          </text>
        </g>
      )
    })

    return (
      <svg viewBox={viewBox} className="w-full h-64 bg-gray-50 rounded-lg">
        {/* Transform to flip Y-axis (LV95 has Y increasing northward) */}
        <g transform={`translate(0, ${maxY + minY}) scale(1, -1)`}>
          {/* Building outline */}
          <path
            d={pathData}
            fill="#f3f4f6"
            stroke="#ddd"
            strokeWidth={width * 0.005}
          />
          {/* Selectable sides */}
          {sideElements}
        </g>
        {/* North arrow */}
        <g transform={`translate(${maxX + padding * 0.5}, ${minY + padding * 0.5})`}>
          <circle r={width * 0.04} fill="white" stroke="#333" strokeWidth={width * 0.003} />
          <text textAnchor="middle" dy={width * 0.015} fontSize={width * 0.03} fontWeight="bold">N</text>
        </g>
      </svg>
    )
  }, [buildingData, selectedFacades])

  // Proceed to configurator
  const handleContinue = () => {
    // Store selected facades in session storage for configurator
    const selectedSides = buildingData?.sides?.filter(s => selectedFacades.has(s.index)) || []
    sessionStorage.setItem('selectedFacades', JSON.stringify(selectedSides))
    navigate(`/configurator?projectId=${id}`)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-red-600 mx-auto mb-2" />
          <p className="text-gray-500">Lade Gebäudedaten...</p>
        </div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="p-4">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-red-800">Fehler</p>
            <p className="text-sm text-red-600">{error || 'Projekt nicht gefunden'}</p>
            <button
              onClick={() => navigate(-1)}
              className="mt-2 text-sm text-red-700 hover:underline"
            >
              Zurück
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="pb-24">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={() => navigate(`/projects/${id}`)}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-lg font-semibold">Fassaden auswählen</h1>
          <p className="text-sm text-gray-500">{project.name}</p>
        </div>
      </div>

      {/* Building Info */}
      <div className="card mb-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-medium">{buildingData?.building_name || project.name}</h2>
          <span className="text-xs text-gray-400">EGID: {buildingData?.egid || '–'}</span>
        </div>
        <p className="text-sm text-gray-500">{project.address}</p>
        {buildingData?.traufhoehe_m && (
          <div className="flex gap-4 mt-2 text-sm text-gray-600">
            <span>Traufhöhe: {buildingData.traufhoehe_m.toFixed(1)}m</span>
            {buildingData.firsthoehe_m && (
              <span>Firsthöhe: {buildingData.firsthoehe_m.toFixed(1)}m</span>
            )}
          </div>
        )}
      </div>

      {/* Polygon Visualization */}
      <div className="card mb-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium flex items-center gap-2">
            <Compass className="w-4 h-4" />
            Gebäudegrundriss
          </h3>
          <div className="flex gap-2">
            <button
              onClick={selectAll}
              className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200"
            >
              Alle
            </button>
            <button
              onClick={deselectAll}
              className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
            >
              Keine
            </button>
          </div>
        </div>

        {polygonSvg}

        <p className="text-xs text-gray-400 mt-2 text-center">
          Tippen Sie auf eine Fassade, um sie auszuwählen
        </p>
      </div>

      {/* Facade List */}
      <div className="card mb-4">
        <h3 className="font-medium mb-3">Fassaden ({buildingData?.sides?.length || 0})</h3>
        <div className="space-y-2">
          {buildingData?.sides?.map((side) => {
            const isSelected = selectedFacades.has(side.index)
            const color = DIRECTION_COLORS[side.direction] || '#666'

            return (
              <button
                key={side.index}
                onClick={() => toggleFacade(side.index)}
                className={`w-full flex items-center justify-between p-3 rounded-lg border transition-all ${
                  isSelected
                    ? 'border-green-300 bg-green-50'
                    : 'border-gray-200 bg-white hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <div className="text-left">
                    <p className="font-medium">
                      {DIRECTION_LABELS[side.direction] || side.direction}
                    </p>
                    <p className="text-sm text-gray-500">
                      {side.length_m.toFixed(1)} m
                    </p>
                  </div>
                </div>
                <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                  isSelected ? 'bg-green-500 text-white' : 'bg-gray-200'
                }`}>
                  {isSelected && <Check className="w-4 h-4" />}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Summary */}
      <div className="card bg-red-50 border-red-200">
        <h3 className="font-medium text-red-800 mb-2">Zusammenfassung</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-red-600">Ausgewählte Fassaden</p>
            <p className="text-xl font-bold text-red-800">{selectedFacades.size}</p>
          </div>
          <div>
            <p className="text-red-600">Gesamtlänge</p>
            <p className="text-xl font-bold text-red-800">{totalSelectedLength.toFixed(1)} m</p>
          </div>
          <div>
            <p className="text-red-600">Gerüsthöhe</p>
            <p className="text-xl font-bold text-red-800">{buildingData?.traufhoehe_m?.toFixed(1) || '–'} m</p>
          </div>
          <div>
            <p className="text-red-600">Geschätzte Fläche</p>
            <p className="text-xl font-bold text-red-800">{estimatedArea.toFixed(0)} m²</p>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-white border-t shadow-lg">
        <div className="max-w-lg mx-auto flex gap-3">
          <button
            onClick={() => navigate(`/projects/${id}`)}
            className="flex-1 btn-secondary"
          >
            Zurück
          </button>
          <button
            onClick={handleContinue}
            disabled={selectedFacades.size === 0}
            className="flex-1 btn-primary flex items-center justify-center gap-2"
          >
            Weiter
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
