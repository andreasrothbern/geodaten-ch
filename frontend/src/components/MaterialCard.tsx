import { useState, useEffect } from 'react'

interface MaterialItem {
  article_number: string
  name: string
  category: string
  quantity_per_100m2: number
  quantity_typical: number
  unit_weight_kg: number | null
  total_weight_kg: number | null
}

interface MaterialEstimate {
  system_id: string
  scaffold_area_m2: number
  materials: MaterialItem[]
  summary: {
    total_pieces: number
    total_weight_kg: number
    total_weight_tons: number
    weight_per_m2_kg: number
  }
}

interface MaterialCardProps {
  scaffoldAreaM2: number
  systemId?: string
  apiUrl: string
}

const CATEGORY_ICONS: Record<string, string> = {
  frame: '🔲',
  ledger: '➖',
  deck: '🟫',
  diagonal: '╲',
  base: '🔳',
  anchor: '⚓',
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

export function MaterialCard({ scaffoldAreaM2, systemId = 'blitz70', apiUrl }: MaterialCardProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<MaterialEstimate | null>(null)
  const [selectedSystem, setSelectedSystem] = useState(systemId)
  const [showAllItems, setShowAllItems] = useState(false)

  const fetchMaterial = async () => {
    if (scaffoldAreaM2 <= 0) return

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(
        `${apiUrl}/api/v1/catalog/estimate?system_id=${selectedSystem}&area_m2=${scaffoldAreaM2}`
      )

      if (!response.ok) {
        throw new Error('Fehler beim Laden der Materialliste')
      }

      const result = await response.json()
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unbekannter Fehler')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMaterial()
  }, [scaffoldAreaM2, selectedSystem])

  if (loading) {
    return (
      <div className="card text-center py-6">
        <p className="text-gray-500">Lade Materialliste...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card bg-red-50 border-red-200">
        <p className="text-red-700">Fehler: {error}</p>
      </div>
    )
  }

  if (!data) return null

  // Group by category
  const byCategory = data.materials.reduce((acc, item) => {
    const cat = item.category || 'other'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(item)
    return acc
  }, {} as Record<string, MaterialItem[]>)

  const categories = Object.keys(byCategory)
  const displayCategories = showAllItems ? categories : categories.slice(0, 4)

  return (
    <div className="card space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span>📦</span> Materialliste
        </h3>
        <select
          value={selectedSystem}
          onChange={(e) => setSelectedSystem(e.target.value)}
          className="px-3 py-1.5 text-sm border rounded-lg"
        >
          <option value="blitz70">Layher Blitz 70</option>
          <option value="allround">Layher Allround</option>
        </select>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Gerüstfläche</p>
          <p className="text-xl font-bold">{data.scaffold_area_m2.toFixed(0)} m²</p>
        </div>
        <div className="bg-amber-50 rounded-lg p-4 text-center">
          <p className="text-sm text-amber-600">Materialteile</p>
          <p className="text-xl font-bold text-amber-900">{data.summary.total_pieces.toLocaleString()}</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-4 text-center">
          <p className="text-sm text-blue-600">Gewicht</p>
          <p className="text-xl font-bold text-blue-900">{data.summary.total_weight_tons.toFixed(1)} t</p>
        </div>
      </div>

      {/* Material by Category */}
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

      {categories.length > 4 && (
        <button
          onClick={() => setShowAllItems(!showAllItems)}
          className="text-sm text-red-600 hover:underline"
        >
          {showAllItems ? 'Weniger anzeigen' : `Alle ${categories.length} Kategorien anzeigen`}
        </button>
      )}

      {/* Weight per m² info */}
      <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-600">
        <p>
          <strong>Gewicht pro m² Gerüstfläche:</strong> {data.summary.weight_per_m2_kg.toFixed(1)} kg/m²
        </p>
        <p className="text-xs mt-1">
          Richtwerte basierend auf Layher {selectedSystem === 'blitz70' ? 'Blitz 70' : 'Allround'} Systemgerüst
        </p>
      </div>
    </div>
  )
}
