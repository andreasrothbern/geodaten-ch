import { useState } from 'react'

interface MaterialItem {
  article_number: string
  name: string
  category: string
  quantity_per_100m2: number
  quantity_typical: number
  unit_weight_kg: number | null
  total_weight_kg: number | null
}

interface AusmassData {
  material: {
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
}

interface MaterialCardProps {
  ausmassData: AusmassData
  onBack?: () => void
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

export function MaterialCard({ ausmassData, onBack }: MaterialCardProps) {
  const [showAllItems, setShowAllItems] = useState(false)

  if (!ausmassData?.material) return null

  const { material, ausmass } = ausmassData
  const scaffoldAreaM2 = ausmass.zusammenfassung.total_ausmass_m2

  // Group by category
  const byCategory = material.liste.reduce((acc, item) => {
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
        <span className="px-3 py-1.5 text-sm bg-gray-100 rounded-lg">
          Layher {material.system === 'blitz70' ? 'Blitz 70' : 'Allround'}
        </span>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Gerüstfläche</p>
          <p className="text-xl font-bold">{scaffoldAreaM2.toFixed(0)} m2</p>
        </div>
        <div className="bg-amber-50 rounded-lg p-4 text-center">
          <p className="text-sm text-amber-600">Materialteile</p>
          <p className="text-xl font-bold text-amber-900">{material.zusammenfassung.total_stueck.toLocaleString()}</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-4 text-center">
          <p className="text-sm text-blue-600">Gewicht</p>
          <p className="text-xl font-bold text-blue-900">{material.zusammenfassung.total_gewicht_tonnen.toFixed(1)} t</p>
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
          <strong>Gewicht pro m² Gerüstfläche:</strong> {material.zusammenfassung.gewicht_pro_m2_kg.toFixed(1)} kg/m²
        </p>
        <p className="text-xs mt-1">
          Richtwerte basierend auf Layher {material.system === 'blitz70' ? 'Blitz 70' : 'Allround'} Systemgerüst
        </p>
      </div>

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
