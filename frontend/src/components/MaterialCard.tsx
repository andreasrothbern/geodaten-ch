import { useState, useEffect } from 'react'

interface MaterialItem {
  article_number: string
  name: string
  category: string
  quantity_per_100m2?: number
  quantity_typical: number
  unit_weight_kg?: number | null
  weight_per_piece_kg?: number | null
  total_weight_kg: number | null
}

interface LiftData {
  lift_type: string
  height_m: number
  width_m: number
  levels: number
  area_m2: number
  npk_positions: { position: string; name: string; unit: string; quantity: number; includes?: string }[]
  weight_estimate_kg: number
  notes: string
}

interface AusmassData {
  material?: {
    system: string
    liste: MaterialItem[]
    zusammenfassung: {
      total_stueck: number
      total_gewicht_kg: number
      total_gewicht_tonnen: number
      gewicht_pro_m2_kg: number
    }
  }
  ausmass: {
    zusammenfassung: {
      total_ausmass_m2: number
    }
  }
  scaffolding_config?: {
    lift?: LiftData | null
  }
}

interface SystemInfo {
  id: string
  name: string
  kurz: string
  beschreibung: string
  vorteile: string[]
  anwendungen: string[]
  lastklasse: string
  max_feldlaenge_m: number
  typisches_gewicht_kg_m2: number
}

interface CombinedMaterialData {
  system: string
  blitz_ratio: number
  allround_ratio: number
  blitz: {
    system_id: string
    area_m2: number
    materials: MaterialItem[]
    total_pieces: number
    total_weight_kg: number
  }
  allround: {
    system_id: string
    area_m2: number
    materials: MaterialItem[]
    total_pieces: number
    total_weight_kg: number
  }
  combined_summary: {
    total_area_m2: number
    total_pieces: number
    total_weight_kg: number
    total_weight_tonnen: number
    weight_per_m2_kg: number
  }
  hinweis: string
}

type SystemId = 'blitz70' | 'allround' | 'combined'

interface MaterialCardProps {
  ausmassData: AusmassData
  apiUrl: string
  onBack?: () => void
}

const CATEGORY_ICONS: Record<string, string> = {
  frame: '🔲',
  ledger: '➖',
  deck: '🟫',
  diagonal: '╲',
  base: '🔳',
  anchor: '⚓',
  Rahmen: '🔲',
  Riegel: '➖',
  Beläge: '🟫',
  Diagonalen: '╲',
  Fussplatten: '🔳',
  Verankerung: '⚓',
  default: '📦'
}

const CATEGORY_NAMES: Record<string, string> = {
  frame: 'Rahmen',
  ledger: 'Riegel',
  deck: 'Beläge',
  diagonal: 'Diagonalen',
  base: 'Fussplatten',
  anchor: 'Verankerung'
}

const SYSTEM_LABELS: Record<SystemId, string> = {
  blitz70: 'Layher Blitz 70',
  allround: 'Layher Allround',
  combined: 'Blitz + Allround'
}

export function MaterialCard({ ausmassData, apiUrl, onBack }: MaterialCardProps) {
  const [showAllItems, setShowAllItems] = useState(false)
  const [selectedSystem, setSelectedSystem] = useState<SystemId>('blitz70')
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [materialData, setMaterialData] = useState<MaterialItem[] | null>(null)
  const [combinedData, setCombinedData] = useState<CombinedMaterialData | null>(null)
  const [blitzRatio, setBlitzRatio] = useState(0.7)
  const [summary, setSummary] = useState<{
    total_stueck: number
    total_gewicht_kg: number
    total_gewicht_tonnen: number
    gewicht_pro_m2_kg: number
  } | null>(null)
  const [showSystemInfo, setShowSystemInfo] = useState(false)

  if (!ausmassData?.ausmass) return null

  const scaffoldAreaM2 = ausmassData.ausmass.zusammenfassung.total_ausmass_m2

  // Fetch material data when system or ratio changes
  useEffect(() => {
    const fetchMaterials = async () => {
      setLoading(true)
      try {
        if (selectedSystem === 'combined') {
          const response = await fetch(
            `${apiUrl}/api/v1/catalog/estimate-combined?area_m2=${scaffoldAreaM2}&blitz_ratio=${blitzRatio}`
          )
          if (response.ok) {
            const data: CombinedMaterialData = await response.json()
            setCombinedData(data)
            setMaterialData(null)
            setSummary({
              total_stueck: data.combined_summary.total_pieces,
              total_gewicht_kg: data.combined_summary.total_weight_kg,
              total_gewicht_tonnen: data.combined_summary.total_weight_tonnen,
              gewicht_pro_m2_kg: data.combined_summary.weight_per_m2_kg
            })
          }
        } else {
          const response = await fetch(
            `${apiUrl}/api/v1/catalog/estimate?system_id=${selectedSystem}&area_m2=${scaffoldAreaM2}`
          )
          if (response.ok) {
            const data = await response.json()
            setMaterialData(data.materials)
            setCombinedData(null)
            setSummary({
              total_stueck: data.summary.total_pieces,
              total_gewicht_kg: data.summary.total_weight_kg,
              total_gewicht_tonnen: data.summary.total_weight_tons,
              gewicht_pro_m2_kg: data.summary.weight_per_m2_kg
            })
          }
        }
      } catch (err) {
        console.error('Failed to fetch materials:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchMaterials()
  }, [selectedSystem, blitzRatio, scaffoldAreaM2, apiUrl])

  // Fetch system info when system changes
  useEffect(() => {
    const fetchSystemInfo = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/v1/catalog/system-info/${selectedSystem}`)
        if (response.ok) {
          const data = await response.json()
          setSystemInfo(data)
        }
      } catch (err) {
        console.error('Failed to fetch system info:', err)
      }
    }

    fetchSystemInfo()
  }, [selectedSystem, apiUrl])

  // Use fetched data or fallback to ausmassData
  const displayMaterials = materialData || ausmassData.material?.liste || []
  const displaySummary = summary || ausmassData.material?.zusammenfassung || {
    total_stueck: 0,
    total_gewicht_kg: 0,
    total_gewicht_tonnen: 0,
    gewicht_pro_m2_kg: 0
  }

  // Group by category
  const byCategory = displayMaterials.reduce((acc, item) => {
    const cat = item.category || 'other'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(item)
    return acc
  }, {} as Record<string, MaterialItem[]>)

  const categories = Object.keys(byCategory)
  const displayCategories = showAllItems ? categories : categories.slice(0, 4)

  // Render material table for a list of materials
  const renderMaterialTable = (materials: MaterialItem[], title?: string) => {
    const grouped = materials.reduce((acc, item) => {
      const cat = item.category || 'other'
      if (!acc[cat]) acc[cat] = []
      acc[cat].push(item)
      return acc
    }, {} as Record<string, MaterialItem[]>)

    const cats = Object.keys(grouped)
    const displayCats = showAllItems ? cats : cats.slice(0, 4)

    return (
      <div className="space-y-3">
        {title && <h5 className="font-medium text-gray-700">{title}</h5>}
        {displayCats.map(category => (
          <div key={category} className="border rounded-lg overflow-hidden">
            <div className="bg-gray-50 px-4 py-2 font-medium flex items-center gap-2 text-sm">
              <span>{CATEGORY_ICONS[category] || CATEGORY_ICONS.default}</span>
              <span>{CATEGORY_NAMES[category] || category}</span>
              <span className="ml-auto text-xs text-gray-500">
                {grouped[category].length} Artikel
              </span>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="px-4 py-2 text-left">Art.-Nr.</th>
                  <th className="px-4 py-2 text-left">Bezeichnung</th>
                  <th className="px-4 py-2 text-right">Menge</th>
                  <th className="px-4 py-2 text-right">Gewicht</th>
                </tr>
              </thead>
              <tbody>
                {grouped[category].map((item, i) => (
                  <tr key={i} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs">{item.article_number}</td>
                    <td className="px-4 py-2">{item.name}</td>
                    <td className="px-4 py-2 text-right font-mono">{item.quantity_typical}</td>
                    <td className="px-4 py-2 text-right font-mono text-gray-500">
                      {item.total_weight_kg ? `${item.total_weight_kg.toFixed(1)} kg` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="card space-y-6">
      {/* Header with System Selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span>📦</span> Materialliste
        </h3>
        <div className="flex items-center gap-2">
          <select
            value={selectedSystem}
            onChange={(e) => setSelectedSystem(e.target.value as SystemId)}
            className="px-3 py-2 border border-gray-300 rounded-lg bg-white text-sm focus:ring-2 focus:ring-purple-500"
          >
            <option value="blitz70">Layher Blitz 70</option>
            <option value="allround">Layher Allround</option>
            <option value="combined">Blitz + Allround Kombination</option>
          </select>
          <button
            onClick={() => setShowSystemInfo(!showSystemInfo)}
            className="p-2 text-gray-500 hover:text-purple-600 transition-colors"
            title="System-Info anzeigen"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
        </div>
      </div>

      {/* System Info Panel */}
      {showSystemInfo && systemInfo && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 space-y-3">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="font-semibold text-purple-900">{systemInfo.name}</h4>
              <p className="text-sm text-purple-700">{systemInfo.kurz}</p>
            </div>
            <button
              onClick={() => setShowSystemInfo(false)}
              className="text-purple-400 hover:text-purple-600"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p className="text-sm text-purple-800">{systemInfo.beschreibung}</p>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium text-purple-900">Vorteile:</p>
              <ul className="list-disc list-inside text-purple-700 text-xs space-y-1">
                {systemInfo.vorteile.map((v, i) => <li key={i}>{v}</li>)}
              </ul>
            </div>
            <div>
              <p className="font-medium text-purple-900">Anwendungen:</p>
              <ul className="list-disc list-inside text-purple-700 text-xs space-y-1">
                {systemInfo.anwendungen.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </div>
          </div>
          <div className="flex gap-4 text-xs text-purple-600 pt-2 border-t border-purple-200">
            <span>Lastklasse: {systemInfo.lastklasse}</span>
            <span>Max. Feldlänge: {systemInfo.max_feldlaenge_m}m</span>
            <span>~{systemInfo.typisches_gewicht_kg_m2} kg/m²</span>
          </div>
        </div>
      )}

      {/* Combined System Ratio Slider */}
      {selectedSystem === 'combined' && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-orange-800">Systemaufteilung</span>
            <span className="text-sm text-orange-600">
              {Math.round(blitzRatio * 100)}% Blitz / {Math.round((1 - blitzRatio) * 100)}% Allround
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            value={blitzRatio * 100}
            onChange={(e) => setBlitzRatio(Number(e.target.value) / 100)}
            className="w-full h-2 bg-orange-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-orange-500 mt-1">
            <span>100% Allround</span>
            <span>100% Blitz</span>
          </div>
          {combinedData && (
            <p className="text-xs text-orange-600 mt-2">
              {combinedData.hinweis}
            </p>
          )}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
          <span className="ml-3 text-gray-600">Berechne Material...</span>
        </div>
      )}

      {/* Summary */}
      {!loading && displaySummary && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <p className="text-sm text-gray-600">Gerüstfläche</p>
            <p className="text-xl font-bold">{scaffoldAreaM2.toFixed(0)} m²</p>
          </div>
          <div className="bg-amber-50 rounded-lg p-4 text-center">
            <p className="text-sm text-amber-600">Materialteile</p>
            <p className="text-xl font-bold text-amber-900">{displaySummary.total_stueck.toLocaleString()}</p>
          </div>
          <div className="bg-blue-50 rounded-lg p-4 text-center">
            <p className="text-sm text-blue-600">Gewicht</p>
            <p className="text-xl font-bold text-blue-900">{displaySummary.total_gewicht_tonnen.toFixed(1)} t</p>
          </div>
        </div>
      )}

      {/* Material Lists */}
      {!loading && (
        <>
          {selectedSystem === 'combined' && combinedData ? (
            <div className="space-y-6">
              {/* Blitz Materials */}
              <div className="border-l-4 border-blue-500 pl-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-blue-900">Blitz 70 ({combinedData.blitz.area_m2.toFixed(0)} m²)</h4>
                  <span className="text-sm text-blue-600">{combinedData.blitz.total_weight_kg.toFixed(0)} kg</span>
                </div>
                {renderMaterialTable(combinedData.blitz.materials)}
              </div>

              {/* Allround Materials */}
              <div className="border-l-4 border-green-500 pl-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium text-green-900">Allround ({combinedData.allround.area_m2.toFixed(0)} m²)</h4>
                  <span className="text-sm text-green-600">{combinedData.allround.total_weight_kg.toFixed(0)} kg</span>
                </div>
                {renderMaterialTable(combinedData.allround.materials)}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {displayCategories.map(category => (
                <div key={category} className="border rounded-lg overflow-hidden">
                  <div className="bg-gray-50 px-4 py-2 font-medium flex items-center gap-2">
                    <span>{CATEGORY_ICONS[category] || CATEGORY_ICONS.default}</span>
                    <span>{CATEGORY_NAMES[category] || category}</span>
                    <span className="ml-auto text-sm text-gray-500">
                      {byCategory[category].length} Artikel
                    </span>
                  </div>
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 text-xs text-gray-500">
                      <tr>
                        <th className="px-4 py-2 text-left">Art.-Nr.</th>
                        <th className="px-4 py-2 text-left">Bezeichnung</th>
                        <th className="px-4 py-2 text-right">Menge</th>
                        <th className="px-4 py-2 text-right">Gewicht</th>
                      </tr>
                    </thead>
                    <tbody>
                      {byCategory[category].map((item, i) => (
                        <tr key={i} className="border-t hover:bg-gray-50">
                          <td className="px-4 py-2 font-mono text-xs">{item.article_number}</td>
                          <td className="px-4 py-2">{item.name}</td>
                          <td className="px-4 py-2 text-right font-mono">{item.quantity_typical}</td>
                          <td className="px-4 py-2 text-right font-mono text-gray-500">
                            {item.total_weight_kg ? `${item.total_weight_kg.toFixed(1)} kg` : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {categories.length > 4 && !loading && selectedSystem !== 'combined' && (
        <button
          onClick={() => setShowAllItems(!showAllItems)}
          className="text-sm text-purple-600 hover:underline"
        >
          {showAllItems ? 'Weniger anzeigen' : `Alle ${categories.length} Kategorien anzeigen`}
        </button>
      )}

      {/* Lift Section */}
      {ausmassData.scaffolding_config?.lift && (
        <div className="border rounded-lg overflow-hidden">
          <div className="bg-indigo-50 px-4 py-3 font-medium flex items-center gap-2">
            <span className="text-xl">🛗</span>
            <span className="text-indigo-900">Gerüstlift</span>
            <span className="ml-auto text-sm text-indigo-600">
              {ausmassData.scaffolding_config.lift.area_m2.toFixed(1)} m² | {ausmassData.scaffolding_config.lift.weight_estimate_kg.toFixed(0)} kg
            </span>
          </div>
          <div className="p-4 space-y-3">
            {/* Lift Summary */}
            <div className="grid grid-cols-4 gap-2 text-center text-sm">
              <div className="bg-indigo-50 rounded p-2">
                <p className="text-xs text-indigo-600">Typ</p>
                <p className="font-medium text-indigo-900">
                  {ausmassData.scaffolding_config.lift.lift_type === 'material' ? 'Material' :
                   ausmassData.scaffolding_config.lift.lift_type === 'person' ? 'Person' : 'Kombi'}
                </p>
              </div>
              <div className="bg-indigo-50 rounded p-2">
                <p className="text-xs text-indigo-600">Höhe</p>
                <p className="font-medium text-indigo-900">{ausmassData.scaffolding_config.lift.height_m.toFixed(1)}m</p>
              </div>
              <div className="bg-indigo-50 rounded p-2">
                <p className="text-xs text-indigo-600">Breite</p>
                <p className="font-medium text-indigo-900">{ausmassData.scaffolding_config.lift.width_m}m</p>
              </div>
              <div className="bg-indigo-50 rounded p-2">
                <p className="text-xs text-indigo-600">Etagen</p>
                <p className="font-medium text-indigo-900">{ausmassData.scaffolding_config.lift.levels}</p>
              </div>
            </div>

            {/* NPK Positions */}
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500">
                <tr>
                  <th className="px-4 py-2 text-left">NPK-Pos.</th>
                  <th className="px-4 py-2 text-left">Bezeichnung</th>
                  <th className="px-4 py-2 text-right">Menge</th>
                </tr>
              </thead>
              <tbody>
                {ausmassData.scaffolding_config.lift.npk_positions.map((pos, i) => (
                  <tr key={i} className="border-t hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs text-indigo-700">{pos.position}</td>
                    <td className="px-4 py-2">
                      {pos.name}
                      {pos.includes && <span className="text-xs text-gray-500 block">{pos.includes}</span>}
                    </td>
                    <td className="px-4 py-2 text-right font-mono">{pos.quantity} {pos.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Notes */}
            {ausmassData.scaffolding_config.lift.notes && ausmassData.scaffolding_config.lift.notes !== 'Standardkonfiguration' && (
              <p className="text-xs text-indigo-600 bg-indigo-50 p-2 rounded">
                <strong>Hinweis:</strong> {ausmassData.scaffolding_config.lift.notes}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Weight per m² info */}
      {!loading && displaySummary && (
        <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600">
          <p>
            <strong>Gewicht pro m² Gerüstfläche:</strong> {displaySummary.gewicht_pro_m2_kg.toFixed(1)} kg/m²
          </p>
          <p className="text-xs mt-1">
            Richtwerte basierend auf {SYSTEM_LABELS[selectedSystem]} Systemgerüst
          </p>
        </div>
      )}

      {/* Back Button */}
      {onBack && (
        <div className="flex items-center justify-between pt-4 border-t">
          <button
            onClick={onBack}
            className="px-4 py-2 text-gray-700 border rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
          >
            <span>←</span> Zurück zum Ausmass
          </button>
        </div>
      )}
    </div>
  )
}
