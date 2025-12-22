import { useState } from 'react'

interface FassadeAusmass {
  name: string
  fassade: {
    laenge_m: number
    hoehe_traufe_m: number
    ist_giebel: boolean
    hoehe_first_m?: number
    giebel_hoehe_m?: number
  }
  ausmass: {
    laenge_m: number
    hoehe_m: number
    flaeche_m2: number
  }
  zuschlaege: {
    fassadenabstand_m: number
    geruest_breite_m: number
    stirnseitig_m: number
    hoehe_m: number
  }
}

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
  adresse: {
    eingabe: string
    gefunden: string
  }
  gebaeude: {
    egid: number | null
    laenge_m: number
    breite_m: number
    hoehe_traufe_m: number
    hoehe_first_m: number | null
    dachform: string
  }
  ausmass: {
    fassaden: FassadeAusmass[]
    zusammenfassung: {
      anzahl_fassaden: number
      anzahl_ecken: number
      fassaden_flaeche_m2: number
      eck_zuschlag_m2: number
      total_ausmass_m2: number
    }
  }
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
  feldaufteilung: {
    facade_length_m: number
    field_count: number
    fields: number[]
    total_length_m: number
    gap_m: number
  }
}

interface AusmassCardProps {
  address: string
  coordinates?: { lv95_e: number; lv95_n: number }
  apiUrl: string
  onExport?: (data: AusmassData) => void
  cachedData?: AusmassData | null
  loading?: boolean
  onRefetch?: (dachform: string, breitenklasse: string) => void
}

export function AusmassCard({ onExport, cachedData, loading: externalLoading, onRefetch }: AusmassCardProps) {
  const [dachform, setDachform] = useState('satteldach')
  const [breitenklasse, setBreitenklasse] = useState('W09')
  const [showDetails, setShowDetails] = useState(false)

  // Use cached data from parent
  const data = cachedData
  const loading = externalLoading

  const handleDachformChange = (newDachform: string) => {
    setDachform(newDachform)
    if (onRefetch) {
      onRefetch(newDachform, breitenklasse)
    }
  }

  const handleBreitenklasseChange = (newBreitenklasse: string) => {
    setBreitenklasse(newBreitenklasse)
    if (onRefetch) {
      onRefetch(dachform, newBreitenklasse)
    }
  }

  if (loading) {
    return (
      <div className="card text-center py-8">
        <div className="animate-spin w-8 h-8 border-4 border-red-600 border-t-transparent rounded-full mx-auto mb-2"></div>
        <p className="text-gray-500">Berechne NPK 114 Ausmass...</p>
      </div>
    )
  }

  if (!data) return null

  const { ausmass, material, feldaufteilung, gebaeude } = data

  return (
    <div className="card space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <span>📐</span> NPK 114 Ausmass
        </h3>
        <div className="flex gap-2">
          <select
            value={dachform}
            onChange={(e) => handleDachformChange(e.target.value)}
            className="px-2 py-1 text-sm border rounded-lg"
          >
            <option value="flach">Flachdach</option>
            <option value="satteldach">Satteldach</option>
            <option value="walmdach">Walmdach</option>
          </select>
          <select
            value={breitenklasse}
            onChange={(e) => handleBreitenklasseChange(e.target.value)}
            className="px-2 py-1 text-sm border rounded-lg"
          >
            <option value="W06">W06 (0.6m)</option>
            <option value="W09">W09 (0.9m)</option>
            <option value="W12">W12 (1.2m)</option>
          </select>
        </div>
      </div>

      {/* Hauptkennzahlen */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-red-50 rounded-lg p-4 text-center">
          <p className="text-sm text-red-600 font-medium">Gerüstfläche</p>
          <p className="text-2xl font-bold text-red-900">
            {ausmass.zusammenfassung.total_ausmass_m2.toFixed(0)} m²
          </p>
          <p className="text-xs text-red-500">inkl. Eckzuschlag</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-4 text-center">
          <p className="text-sm text-blue-600 font-medium">Materialteile</p>
          <p className="text-2xl font-bold text-blue-900">
            {material.zusammenfassung.total_stueck.toLocaleString()}
          </p>
          <p className="text-xs text-blue-500">Stück</p>
        </div>
        <div className="bg-amber-50 rounded-lg p-4 text-center">
          <p className="text-sm text-amber-600 font-medium">Gesamtgewicht</p>
          <p className="text-2xl font-bold text-amber-900">
            {material.zusammenfassung.total_gewicht_tonnen.toFixed(1)} t
          </p>
          <p className="text-xs text-amber-500">{material.zusammenfassung.gewicht_pro_m2_kg.toFixed(1)} kg/m²</p>
        </div>
        <div className="bg-green-50 rounded-lg p-4 text-center">
          <p className="text-sm text-green-600 font-medium">Felder</p>
          <p className="text-2xl font-bold text-green-900">
            {feldaufteilung.field_count}
          </p>
          <p className="text-xs text-green-500">{feldaufteilung.fields.join(' + ')}m</p>
        </div>
      </div>

      {/* Fassaden-Tabelle */}
      <div>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-3"
        >
          <span className={`transform transition-transform ${showDetails ? 'rotate-90' : ''}`}>▶</span>
          Fassaden-Details ({ausmass.zusammenfassung.anzahl_fassaden} Fassaden)
        </button>

        {showDetails && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100">
                  <th className="px-3 py-2 text-left">Fassade</th>
                  <th className="px-3 py-2 text-right">Länge</th>
                  <th className="px-3 py-2 text-right">Höhe</th>
                  <th className="px-3 py-2 text-right">Ausmass L</th>
                  <th className="px-3 py-2 text-right">Ausmass H</th>
                  <th className="px-3 py-2 text-right font-bold">Fläche</th>
                </tr>
              </thead>
              <tbody>
                {ausmass.fassaden.map((f: FassadeAusmass, i: number) => (
                  <tr key={i} className="border-b hover:bg-gray-50">
                    <td className="px-3 py-2">
                      {f.name}
                      {f.fassade.ist_giebel && (
                        <span className="ml-1 px-1.5 py-0.5 bg-amber-100 text-amber-700 text-xs rounded">
                          Giebel
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right font-mono">{f.fassade.laenge_m.toFixed(1)} m</td>
                    <td className="px-3 py-2 text-right font-mono">
                      {f.fassade.hoehe_traufe_m.toFixed(1)} m
                      {f.fassade.hoehe_first_m && (
                        <span className="text-amber-600 text-xs ml-1">
                          (First: {f.fassade.hoehe_first_m.toFixed(1)}m)
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-gray-500">{f.ausmass.laenge_m.toFixed(1)} m</td>
                    <td className="px-3 py-2 text-right font-mono text-gray-500">{f.ausmass.hoehe_m.toFixed(1)} m</td>
                    <td className="px-3 py-2 text-right font-mono font-bold">{f.ausmass.flaeche_m2.toFixed(1)} m²</td>
                  </tr>
                ))}
                <tr className="bg-gray-50 font-bold">
                  <td className="px-3 py-2" colSpan={5}>Eckzuschlag ({ausmass.zusammenfassung.anzahl_ecken} Ecken)</td>
                  <td className="px-3 py-2 text-right font-mono">+{ausmass.zusammenfassung.eck_zuschlag_m2.toFixed(1)} m²</td>
                </tr>
                <tr className="bg-red-50 font-bold text-red-900">
                  <td className="px-3 py-2" colSpan={5}>TOTAL AUSMASS</td>
                  <td className="px-3 py-2 text-right font-mono text-lg">{ausmass.zusammenfassung.total_ausmass_m2.toFixed(1)} m²</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* NPK 114 Formel Info */}
      <div className="bg-blue-50 rounded-lg p-4 text-sm">
        <p className="font-medium text-blue-800 mb-2">NPK 114 D/2012 Berechnung:</p>
        <div className="grid grid-cols-2 gap-2 text-blue-700">
          <p>Ausmasslänge: LA = LS + L + LS</p>
          <p>Ausmasshöhe: HA = H + 1.0m</p>
          <p>LS (stirnseitig) = {ausmass.fassaden[0]?.zuschlaege.stirnseitig_m.toFixed(2)}m</p>
          <p>Giebel: H = Traufe + (First × 0.5)</p>
        </div>
      </div>

      {/* Gebäudedaten */}
      <div className="grid grid-cols-4 gap-3 text-sm">
        <div className="bg-white border rounded-lg p-3 text-center">
          <p className="text-gray-500">Länge</p>
          <p className="font-semibold">{gebaeude.laenge_m.toFixed(1)} m</p>
        </div>
        <div className="bg-white border rounded-lg p-3 text-center">
          <p className="text-gray-500">Breite</p>
          <p className="font-semibold">{gebaeude.breite_m.toFixed(1)} m</p>
        </div>
        <div className="bg-white border rounded-lg p-3 text-center">
          <p className="text-gray-500">Traufhöhe</p>
          <p className="font-semibold">{gebaeude.hoehe_traufe_m.toFixed(1)} m</p>
        </div>
        <div className="bg-white border rounded-lg p-3 text-center">
          <p className="text-gray-500">Dachform</p>
          <p className="font-semibold capitalize">{gebaeude.dachform}</p>
        </div>
      </div>

      {/* Export Button */}
      {onExport && (
        <div className="flex justify-end">
          <button
            onClick={() => onExport(data)}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center gap-2"
          >
            <span>📄</span> Exportieren
          </button>
        </div>
      )}
    </div>
  )
}
