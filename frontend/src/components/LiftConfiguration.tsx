import { useState, useEffect } from 'react'

interface LiftType {
  id: string
  name: string
  description: string
  icon: string
}

interface LiftWidth {
  id: string
  width_m: number
  name: string
}

interface NpkPosition {
  position: string
  name: string
  unit: string
  quantity: number
  includes?: string
  note?: string
}

interface LiftCalculation {
  lift_type: string
  height_m: number
  width_m: number
  levels: number
  area_m2: number
  npk_positions: NpkPosition[]
  weight_estimate_kg: number
  notes: string
}

interface LiftConfigurationProps {
  apiUrl: string
  scaffoldHeight: number
  enabled: boolean
  onToggle: (enabled: boolean) => void
  onLiftCalculated?: (result: LiftCalculation | null) => void
}

export function LiftConfiguration({
  apiUrl,
  scaffoldHeight,
  enabled,
  onToggle,
  onLiftCalculated
}: LiftConfigurationProps) {
  const [liftTypes, setLiftTypes] = useState<LiftType[]>([])
  const [liftWidths, setLiftWidths] = useState<LiftWidth[]>([])
  const [selectedType, setSelectedType] = useState<string>('material')
  const [selectedWidth, setSelectedWidth] = useState<number>(1.35)
  const [calculation, setCalculation] = useState<LiftCalculation | null>(null)
  const [loading, setLoading] = useState(false)
  const [showDetails, setShowDetails] = useState(false)

  // Fetch lift types and widths on mount
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [typesRes, widthsRes] = await Promise.all([
          fetch(`${apiUrl}/api/v1/lift/types`),
          fetch(`${apiUrl}/api/v1/lift/widths`)
        ])
        if (typesRes.ok) setLiftTypes(await typesRes.json())
        if (widthsRes.ok) setLiftWidths(await widthsRes.json())
      } catch (err) {
        console.error('Failed to fetch lift data:', err)
      }
    }
    fetchData()
  }, [apiUrl])

  // Calculate lift when configuration changes
  useEffect(() => {
    if (!enabled || scaffoldHeight <= 0) {
      setCalculation(null)
      onLiftCalculated?.(null)
      return
    }

    const calculateLift = async () => {
      setLoading(true)
      try {
        const params = new URLSearchParams({
          lift_type: selectedType,
          height_m: scaffoldHeight.toString(),
          width_m: selectedWidth.toString()
        })
        const response = await fetch(`${apiUrl}/api/v1/lift/calculate?${params}`, {
          method: 'POST'
        })
        if (response.ok) {
          const result = await response.json()
          setCalculation(result)
          onLiftCalculated?.(result)
        }
      } catch (err) {
        console.error('Failed to calculate lift:', err)
      } finally {
        setLoading(false)
      }
    }

    const debounceTimer = setTimeout(calculateLift, 300)
    return () => clearTimeout(debounceTimer)
  }, [enabled, selectedType, selectedWidth, scaffoldHeight, apiUrl, onLiftCalculated])

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Header with Toggle */}
      <div
        className={`flex items-center justify-between p-4 cursor-pointer transition-colors ${
          enabled ? 'bg-indigo-50' : 'bg-gray-50 hover:bg-gray-100'
        }`}
        onClick={() => onToggle(!enabled)}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">{enabled ? '🛗' : '➖'}</span>
          <div>
            <h4 className="font-medium text-gray-900">Gerüstlift</h4>
            <p className="text-xs text-gray-500">
              {enabled
                ? `${selectedType === 'material' ? 'Materiallift' : selectedType === 'person' ? 'Personenlift' : 'Kombilift'}`
                : 'Klicken zum Aktivieren'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {enabled && calculation && (
            <div className="text-right text-sm">
              <p className="text-indigo-600 font-medium">{calculation.area_m2.toFixed(1)} m²</p>
              <p className="text-gray-500">{calculation.weight_estimate_kg.toFixed(0)} kg</p>
            </div>
          )}
          <div
            className={`w-12 h-6 rounded-full transition-colors flex items-center ${
              enabled ? 'bg-indigo-500' : 'bg-gray-300'
            }`}
          >
            <div
              className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                enabled ? 'translate-x-6' : 'translate-x-0.5'
              }`}
            />
          </div>
        </div>
      </div>

      {/* Configuration Panel */}
      {enabled && (
        <div className="p-4 border-t space-y-4 bg-white">
          {/* Lift Type Selection */}
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Lift-Typ</p>
            <div className="flex flex-wrap gap-2">
              {liftTypes.map((type) => (
                <button
                  key={type.id}
                  onClick={() => setSelectedType(type.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                    selectedType === type.id
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <span>{type.icon}</span>
                  <span>{type.name}</span>
                </button>
              ))}
            </div>
            {liftTypes.find(t => t.id === selectedType)?.description && (
              <p className="text-xs text-gray-500 mt-2">
                {liftTypes.find(t => t.id === selectedType)?.description}
              </p>
            )}
          </div>

          {/* Width Selection */}
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Breite</p>
            <div className="flex gap-2">
              {liftWidths.map((width) => (
                <button
                  key={width.id}
                  onClick={() => setSelectedWidth(width.width_m)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedWidth === width.width_m
                      ? 'bg-indigo-100 text-indigo-700 border-2 border-indigo-300'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200 border-2 border-transparent'
                  }`}
                >
                  {width.name}
                </button>
              ))}
            </div>
          </div>

          {/* Calculation Result */}
          {loading && (
            <div className="flex items-center justify-center py-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
              <span className="ml-2 text-gray-600">Berechne...</span>
            </div>
          )}

          {!loading && calculation && (
            <div className="bg-indigo-50 rounded-lg p-4 space-y-3">
              {/* Summary */}
              <div className="grid grid-cols-3 gap-3 text-center">
                <div>
                  <p className="text-xs text-indigo-600">Höhe</p>
                  <p className="font-bold text-indigo-900">{calculation.height_m.toFixed(1)} m</p>
                </div>
                <div>
                  <p className="text-xs text-indigo-600">Etagen</p>
                  <p className="font-bold text-indigo-900">{calculation.levels}</p>
                </div>
                <div>
                  <p className="text-xs text-indigo-600">Fläche</p>
                  <p className="font-bold text-indigo-900">{calculation.area_m2.toFixed(1)} m²</p>
                </div>
              </div>

              {/* NPK Details Toggle */}
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="w-full text-sm text-indigo-600 hover:underline flex items-center justify-center gap-1"
              >
                <span>NPK-Positionen {showDetails ? 'ausblenden' : 'anzeigen'}</span>
                <svg
                  className={`w-4 h-4 transition-transform ${showDetails ? 'rotate-180' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* NPK Positions */}
              {showDetails && (
                <div className="space-y-2 pt-2 border-t border-indigo-200">
                  {calculation.npk_positions.map((pos, idx) => (
                    <div key={idx} className="flex items-start justify-between text-sm">
                      <div>
                        <p className="font-mono text-xs text-indigo-700">{pos.position}</p>
                        <p className="text-gray-700">{pos.name}</p>
                        {pos.includes && (
                          <p className="text-xs text-gray-500">{pos.includes}</p>
                        )}
                      </div>
                      <p className="font-medium text-indigo-900">{pos.quantity} {pos.unit}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Notes */}
              {calculation.notes && calculation.notes !== 'Standardkonfiguration' && (
                <div className="pt-2 border-t border-indigo-200">
                  <p className="text-xs text-indigo-700">
                    <strong>Hinweis:</strong> {calculation.notes}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
