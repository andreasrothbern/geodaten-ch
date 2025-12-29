/**
 * Grunddaten Card Component
 *
 * Displays all base data from APIs:
 * - Address and coordinates
 * - GWR data (EGID, floors, area, etc.)
 * - Height data (estimated + measured from swissBUILDINGS3D)
 * - Building visualization (cross-section, elevation, floor plan)
 * - Manual height input option for Traufe and First
 */

import { useState, useEffect, useCallback } from 'react'
import type { ScaffoldingData, BuildingContext } from '../types'
import { ServerSVG, preloadAllSvgs } from './BuildingVisualization/ServerSVG'

/**
 * Generiert einen strukturierten Prompt für Claude.ai
 * Enthält alle Gebäudedaten für hochwertige SVG-Generierung
 * Inkl. Gebäude-Identifikation und RECHERCHE-ANWEISUNG
 *
 * Generiert Anforderungen für ALLE 3 SVG-Typen in einem Prompt.
 */
function generateClaudePrompt(
  data: ScaffoldingData,
  buildingContext?: BuildingContext | null
): string {
  const { dimensions, gwr_data, building, address, polygon, sides, roof } = data
  const zones = buildingContext?.zones || []
  const isComplex = buildingContext?.complexity === 'complex' || zones.length > 1
  const terrain = address?.terrain

  // Gebäudetyp aus GWR-Kategorie ableiten
  const getGebaeudetype = (): string => {
    const category = gwr_data?.building_category?.toLowerCase() || ''
    if (category.includes('kirche') || category.includes('religiös')) return 'Kirche/Sakralbau'
    if (category.includes('öffentlich') || category.includes('verwaltung')) return 'Öffentliches Gebäude'
    if (category.includes('mehrfamilien')) return 'Mehrfamilienhaus'
    if (category.includes('einfamilien')) return 'Einfamilienhaus'
    if (category.includes('gewerbe') || category.includes('industrie')) return 'Gewerbe/Industrie'
    if (category.includes('landwirtschaft')) return 'Landwirtschaftsgebäude'
    if (isComplex) return 'Komplexes Gebäude (RECHERCHIEREN)'
    return 'Wohngebäude'
  }

  // Gebäudename aus Context oder "RECHERCHIEREN"
  const buildingName = buildingContext?.building_name || 'RECHERCHIEREN'
  const needsResearch = buildingName === 'RECHERCHIEREN' || isComplex

  return `# SVG-Generierung: Grundriss + Fassadenansicht + Gebäudeschnitt

## 1. Gebäude-Identifikation

- **Adresse:** ${address?.matched || 'Unbekannt'}
- **EGID:** ${building?.egid || gwr_data?.egid || '-'}
- **Koordinaten (LV95):** E ${address?.coordinates?.lv95_e?.toFixed(0) || '-'}, N ${address?.coordinates?.lv95_n?.toFixed(0) || '-'}
- **Gebäudename:** ${buildingName}
- **Gebäudetyp:** ${getGebaeudetype()}
- **Baustil:** ${isComplex ? 'RECHERCHIEREN' : 'Standard (nicht relevant)'}
- **Baujahr:** ${gwr_data?.construction_year || '-'}
- **Komplexität:** ${isComplex ? 'KOMPLEX (mehrere Zonen)' : 'EINFACH'}

${needsResearch ? `## 2. RECHERCHE-ANWEISUNG

> **WICHTIG:** Falls Gebäudename oder Baustil mit "RECHERCHIEREN" markiert:
> 1. Suche das Gebäude anhand Adresse/EGID/Koordinaten
> 2. Identifiziere den korrekten Gebäudenamen
> 3. Bestimme Gebäudetyp und Baustil (z.B. Neugotik, Barock, Klassizismus, Modern)
> 4. Ermittle charakteristische Architekturmerkmale (Fensterformen, Portal, Türme)
> 5. Kläre Turmkonfiguration (Anzahl, Position, Form) falls vorhanden
> 6. Validiere die unten angegebenen Höhenzonen gegen recherchierte Informationen
> **Erst danach mit der SVG-Erstellung beginnen.**

` : ''}## 3. Geometrische Basisdaten

### Dimensionen
- **Traufhöhe:** ${dimensions?.traufhoehe_m?.toFixed(1) || 'unbekannt'} m
- **Firsthöhe:** ${dimensions?.firsthoehe_m?.toFixed(1) || 'unbekannt'} m
- **Geschosse:** ${dimensions?.floors || gwr_data?.floors || '-'}
- **Grundfläche:** ${building?.footprint_area_m2?.toFixed(0) || gwr_data?.area_m2_gwr?.toFixed(0) || '-'} m²

${roof ? `### Dach-Analyse (heuristisch berechnet)
- **Dachform:** ${roof.roof_type}
- **Dachneigung:** ${roof.roof_angle_deg?.toFixed(0) || '-'}°
- **First-Ausrichtung:** ${roof.roof_orientation || '-'}
- **Dachfläche:** ${roof.roof_area_m2?.toFixed(0) || '-'} m²
- **Konfidenz:** ${(roof.confidence * 100).toFixed(0)}% ${roof.confidence < 0.5 ? '(niedrig = Schätzung)' : '(hoch = verlässlich)'}
` : ''}
### Terrain (swissALTI3D)
${terrain ? `- **Terrain-Höhe:** ${terrain.terrain_height_m?.toFixed(1)} m ü.M.
- **Hanglage:** ${terrain.terrain_slope_m && terrain.terrain_slope_m > 1 ? `Ja (${terrain.terrain_slope_m.toFixed(1)}m Differenz - unterschiedliche Gerüsthöhen nötig!)` : 'Nein'}` : '- Keine Terrain-Daten verfügbar'}

### Polygon
- **Eckpunkte:** ${polygon?.coordinates?.length || 0}
- **Koordinatensystem:** LV95 (EPSG:2056)

## 4. GWR-Daten (Gebäude- und Wohnungsregister)
- **Gebäudekategorie:** ${gwr_data?.building_category || '-'}
- **Baujahr:** ${gwr_data?.construction_year || '-'}
- **Geschosse (GWR):** ${gwr_data?.floors || '-'}
- **Grundfläche (GWR):** ${gwr_data?.area_m2_gwr?.toFixed(0) || '-'} m²

## 5. Höhenzonen
${zones.length > 0 ? `
| Zone | Typ | Höhe | Traufe | Eingerüstet |
|------|-----|------|--------|-------------|
${zones.map(z => `| ${z.name} | ${z.type} | ${z.gebaeudehoehe_m?.toFixed(1) || '?'}m | ${z.traufhoehe_m?.toFixed(1) || '-'}m | ${z.beruesten !== false ? 'Ja' : 'Nein'} |`).join('\n')}

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkörper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen (Erdgeschoss)
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebäude
- **innenhof** = Nicht einrüsten (Freifläche)
` : 'Keine Zonen definiert (einfaches Gebäude mit 1 Zone)'}

${isComplex ? `## 6. Baustil-Merkmale
> **RECHERCHIEREN basierend auf Gebäudetyp und Baujahr:**
- **Fenster:** [Spitzbogen/Rundbogen/Rechteck/etc.]
- **Portal:** [Beschreibung]
- **Fassadengliederung:** [Strebepfeiler/Pilaster/Lisenen/etc.]
- **Dachdetails:** [Kreuz/Wetterfahne/Gauben/Fialen/etc.]
- **Besondere Elemente:** [Rosette/Erker/Balkon/etc.]

` : ''}## 7. Fassaden (aus Polygon)
${sides && sides.length > 0 ? `
| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
${sides.map((s, i) => `| ${s.index ?? i + 1} | ${s.length_m?.toFixed(1)} | ${s.direction || '?'} |`).join('\n')}` : 'Keine Seitendaten verfügbar'}

## 8. SVG Style-Vorgaben

\`\`\`xml
<defs>
  <!-- Schraffur für Gebäude -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4" stroke="#999" stroke-width="0.5"/>
  </pattern>
  <!-- Kupfer-Gradient NUR für Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
\`\`\`

| Element | Farbe/Fill |
|---------|------------|
| Hintergrund | #FFFFFF (weiss) |
| Gebäude | url(#hatch) Schraffur |
| Kuppel | url(#copper) Gradient |
| Gerüst-Ständer | #0066CC (blau) |
| Beläge | #8B4513 (braun) |
| Verankerungen | #CC0000 gestrichelt |

## 9. Anforderungen

### Für Grundriss (SVG 1):
- Polygon-Form des Gebäudes (Draufsicht)
- Fassaden beschriften (Länge + Richtung)
- Gerüstzone um das Gebäude (gelb, 1m Abstand)
- Nordpfeil und Massstab
${isComplex ? '- Zonen farblich unterscheiden\n- Innenhöfe markieren' : ''}

### Für Fassadenansicht (SVG 2):
- Orthogonale Frontalansicht (2D)
- Terrain-Linie bei ±0.00 (oder m ü.M. bei Hanglage)
${isComplex ? `- WICHTIG: Verschiedene Höhenzonen darstellen!
- Arkaden unten: Bögen/Rundbögen
- Hauptfassade: Fensterreihen
- Kuppel oben: Halbkreis mit copper-Gradient (EINZIGER Gradient!)
- Keine zusätzlichen Elemente erfinden!` : '- Fensterreihen pro Geschoss (angedeutet)\n- Satteldach als Dreieck'}
- Gerüst VOR der Fassade (Ständer blau, Beläge braun)
- Höhenskala links, Lagenbeschriftung rechts

### Für Gebäudeschnitt (SVG 3):
- Querschnitt durch Gebäude (2D Orthogonalprojektion)
- Terrain-Linie bei ±0.00
- Geschossdecken als horizontale Linien
${isComplex ? `- WICHTIG: Verschiedene Höhen pro Zone darstellen!
- Arkaden: Niedrig (~${zones.find(z => z.type === 'arkade')?.gebaeudehoehe_m?.toFixed(1) || '6'}m)
- Hauptgebäude: Mittel
- Kuppel: Hoch mit Halbkreis-Kontur` : '- Dachform: Satteldach mit Traufe und First'}
- Gerüst links und rechts (Ständer + Beläge)
- Höhenskala links, Lagenbeschriftung rechts

## 10. Output

Erstelle **3 separate SVGs**, jeweils mit \`viewBox="0 0 700 480"\`:

1. **grundriss.svg** - Draufsicht mit Polygon und Gerüstzone
2. **fassadenansicht.svg** - Frontalansicht mit Gerüst
3. **gebaeudesschnitt.svg** - Querschnitt mit Geschossen

**NUR SVG-Code**, keine Erklärungen. Trenne die SVGs klar voneinander.

---

*Generiert mit Gerüstplanung Schweiz App - https://cooperative-commitment-production.up.railway.app*`
}

export interface ManualHeights {
  traufhoehe_m?: number
  firsthoehe_m?: number
}

interface GrunddatenCardProps {
  data: ScaffoldingData
  apiUrl: string
  onFetchMeasuredHeight?: () => void
  fetchingHeight?: boolean
  onHeightChange?: (heights: ManualHeights) => void
  onProceedToGeruestbau?: () => void
}

export function GrunddatenCard({
  data,
  apiUrl,
  onFetchMeasuredHeight,
  fetchingHeight = false,
  onHeightChange,
  onProceedToGeruestbau
}: GrunddatenCardProps) {
  const [manualTraufe, setManualTraufe] = useState<string>('')
  const [manualFirst, setManualFirst] = useState<string>('')
  const [activeVizTab, setActiveVizTab] = useState<'cross-section' | 'elevation' | 'floor-plan'>('floor-plan')
  const [professionalMode, setProfessionalMode] = useState(false)
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null)
  const [loadingExport, setLoadingExport] = useState(false)
  const { dimensions, gwr_data, building, address } = data

  // Export prompt to clipboard for Claude.ai (with building context/zones)
  const handleExportPrompt = useCallback(async () => {
    setLoadingExport(true)
    setCopyFeedback('Lade...')

    let buildingContext: BuildingContext | null = null

    // Try to load building context if EGID is available
    const egid = building?.egid || gwr_data?.egid
    if (egid) {
      try {
        const response = await fetch(
          `${apiUrl}/api/v1/building/context/${egid}?create_if_missing=true&analyze_if_complex=true`
        )
        if (response.ok) {
          const contextData = await response.json()
          buildingContext = contextData.context || null
        }
      } catch (err) {
        console.warn('Could not load building context:', err)
      }
    }

    const prompt = generateClaudePrompt(data, buildingContext)

    try {
      await navigator.clipboard.writeText(prompt)
      setCopyFeedback('✓ Kopiert!')
      setTimeout(() => setCopyFeedback(null), 2000)
    } catch (err) {
      // Fallback: Open in new window
      const blob = new Blob([prompt], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setCopyFeedback('Geöffnet')
      setTimeout(() => setCopyFeedback(null), 2000)
    }

    setLoadingExport(false)
  }, [data, apiUrl, building?.egid, gwr_data?.egid])

  // Initialize manual inputs with current values if they exist
  useEffect(() => {
    if (dimensions.traufhoehe_m && !manualTraufe) {
      setManualTraufe(dimensions.traufhoehe_m.toFixed(1))
    }
    if (dimensions.firsthoehe_m && !manualFirst) {
      setManualFirst(dimensions.firsthoehe_m.toFixed(1))
    }
  }, [dimensions.traufhoehe_m, dimensions.firsthoehe_m])

  const handleManualHeightSubmit = () => {
    const traufe = parseFloat(manualTraufe)
    const first = parseFloat(manualFirst)

    if (onHeightChange) {
      const heights: ManualHeights = {}
      if (!isNaN(traufe) && traufe > 0) {
        heights.traufhoehe_m = traufe
      }
      if (!isNaN(first) && first > 0) {
        heights.firsthoehe_m = first
      }
      if (Object.keys(heights).length > 0) {
        onHeightChange(heights)
      }
    }
  }

  // Check if measured height exists
  const hasMeasuredHeight = dimensions.traufhoehe_m !== null || dimensions.firsthoehe_m !== null

  // Preload all SVG visualizations when component mounts
  useEffect(() => {
    if (data.address?.matched && apiUrl) {
      preloadAllSvgs(data.address.matched, apiUrl)
    }
  }, [data.address?.matched, apiUrl])

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
          {/* Terrain-Höhe (m ü.M.) */}
          {address?.terrain?.terrain_height_m && (
            <div className="col-span-2">
              <span className="text-gray-500">Terrain-Höhe:</span>
              <span className="ml-2 font-medium">
                {address.terrain.terrain_height_m.toFixed(1)} m ü.M.
              </span>
              {address.terrain.terrain_slope_m && address.terrain.terrain_slope_m > 1.0 && (
                <span className="ml-2 px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-xs">
                  Hanglage ({address.terrain.terrain_slope_m.toFixed(1)}m Differenz)
                </span>
              )}
            </div>
          )}
        </div>
      </section>

      {/* GWR Data */}
      <section className="space-y-2">
        <h4 className="font-medium text-gray-700">GWR-Daten (Gebäude- und Wohnungsregister)</h4>
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
            <p className="text-gray-500 text-xs">Grundfläche</p>
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
          <h4 className="font-medium text-gray-700">Höhendaten</h4>
          {!hasMeasuredHeight && onFetchMeasuredHeight && (
            <button
              onClick={onFetchMeasuredHeight}
              disabled={fetchingHeight}
              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {fetchingHeight ? 'Lade...' : 'Höhe aus swissBUILDINGS3D abrufen'}
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Estimated Height */}
          <div className={`rounded-lg p-4 ${hasMeasuredHeight ? 'bg-gray-100' : 'bg-yellow-50 border border-yellow-200'}`}>
            <p className="text-xs text-gray-500 mb-1">Geschätzte Höhe</p>
            <p className="text-2xl font-bold text-gray-700">
              {dimensions.height_estimated_m?.toFixed(1) || '-'} m
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {dimensions.height_estimated_source || 'Aus Geschossen berechnet'}
            </p>
          </div>

          {/* Traufhöhe */}
          <div className={`rounded-lg p-4 ${dimensions.traufhoehe_m ? 'bg-green-50 border border-green-200' : 'bg-gray-100'}`}>
            <p className={`text-xs mb-1 ${dimensions.traufhoehe_m ? 'text-green-600' : 'text-gray-500'}`}>
              Traufhöhe {dimensions.traufhoehe_m ? '(gemessen)' : '(nicht verfügbar)'}
            </p>
            <p className={`text-2xl font-bold ${dimensions.traufhoehe_m ? 'text-green-700' : 'text-gray-400'}`}>
              {dimensions.traufhoehe_m?.toFixed(1) || '-'} m
            </p>
            {dimensions.traufhoehe_m && (
              <p className="text-xs text-green-500 mt-1">swissBUILDINGS3D</p>
            )}
          </div>

          {/* Firsthöhe */}
          <div className={`rounded-lg p-4 ${dimensions.firsthoehe_m ? 'bg-green-50 border border-green-200' : 'bg-gray-100'}`}>
            <p className={`text-xs mb-1 ${dimensions.firsthoehe_m ? 'text-green-600' : 'text-gray-500'}`}>
              Firsthöhe {dimensions.firsthoehe_m ? '(gemessen)' : '(nicht verfügbar)'}
            </p>
            <p className={`text-2xl font-bold ${dimensions.firsthoehe_m ? 'text-green-700' : 'text-gray-400'}`}>
              {dimensions.firsthoehe_m?.toFixed(1) || '-'} m
            </p>
            {dimensions.firsthoehe_m && (
              <p className="text-xs text-green-500 mt-1">swissBUILDINGS3D</p>
            )}
          </div>
        </div>

        {/* Manual Height Input for Traufe and First */}
        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          <p className="text-sm text-gray-600 font-medium">
            Manuelle Höheneingabe (falls Daten falsch oder nicht verfügbar)
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Traufhöhe (m)</label>
              <input
                type="number"
                step="0.1"
                min="1"
                max="100"
                value={manualTraufe}
                onChange={(e) => setManualTraufe(e.target.value)}
                placeholder={dimensions.traufhoehe_m?.toFixed(1) || 'z.B. 8.5'}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Firsthöhe (m)</label>
              <input
                type="number"
                step="0.1"
                min="1"
                max="100"
                value={manualFirst}
                onChange={(e) => setManualFirst(e.target.value)}
                placeholder={dimensions.firsthoehe_m?.toFixed(1) || 'z.B. 12.0'}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm"
              />
            </div>
          </div>
          <button
            onClick={handleManualHeightSubmit}
            disabled={(!manualTraufe || parseFloat(manualTraufe) <= 0) && (!manualFirst || parseFloat(manualFirst) <= 0)}
            className="w-full md:w-auto px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors text-sm"
          >
            Höhen übernehmen
          </button>
          <p className="text-xs text-gray-400">
            Hinweis: Manuelle Eingaben überschreiben die gemessenen Werte für die Berechnung.
          </p>
        </div>

        {/* Current Active Height */}
        {dimensions.estimated_height_m && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-blue-600">Aktive Höhe für Berechnung</p>
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

      {/* Roof Data (Dach-Daten) */}
      {data.roof && (
        <section className="space-y-3">
          <h4 className="font-medium text-gray-700">Dach-Daten (berechnet)</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className={`rounded-lg p-4 ${data.roof.confidence > 0.5 ? 'bg-emerald-50 border border-emerald-200' : 'bg-yellow-50 border border-yellow-200'}`}>
              <p className="text-xs text-gray-500 mb-1">Dachform</p>
              <p className="font-medium capitalize">
                {data.roof.roof_type === 'flachdach' && '▭ Flachdach'}
                {data.roof.roof_type === 'pultdach' && '◢ Pultdach'}
                {data.roof.roof_type === 'satteldach' && '△ Satteldach'}
                {data.roof.roof_type === 'walmdach' && '⬠ Walmdach'}
                {data.roof.roof_type === 'mansarddach' && '⬡ Mansarddach'}
                {data.roof.roof_type === 'unknown' && '? Unbekannt'}
              </p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-xs text-gray-500 mb-1">Dachneigung</p>
              <p className="font-medium">
                {data.roof.roof_angle_deg !== null
                  ? `${data.roof.roof_angle_deg.toFixed(0)}°`
                  : '-'}
              </p>
            </div>
            {data.roof.roof_orientation && (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-xs text-gray-500 mb-1">Firstausrichtung</p>
                <p className="font-medium">{data.roof.roof_orientation}</p>
              </div>
            )}
            {data.roof.roof_area_m2 && (
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-xs text-gray-500 mb-1">Dachfläche</p>
                <p className="font-medium">{data.roof.roof_area_m2.toFixed(0)} m²</p>
              </div>
            )}
          </div>
          {data.roof.confidence < 0.5 && (
            <p className="text-xs text-yellow-600">
              Geringe Konfidenz ({(data.roof.confidence * 100).toFixed(0)}%) - Werte heuristisch berechnet
            </p>
          )}
        </section>
      )}

      {/* Key figures */}
      <section className="space-y-3">
        <h4 className="font-medium text-gray-700">Kennzahlen</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 rounded-lg p-4 text-center">
            <p className="text-sm text-blue-600 font-medium">Fassadenlänge</p>
            <p className="text-2xl font-bold text-blue-900">
              {dimensions.perimeter_m?.toFixed(1) || '-'} m
            </p>
          </div>
          <div className="bg-purple-50 rounded-lg p-4 text-center">
            <p className="text-sm text-purple-600 font-medium">Grundfläche</p>
            <p className="text-2xl font-bold text-purple-900">
              {building?.footprint_area_m2?.toFixed(0) || '-'} m2
            </p>
          </div>
          {data.viewer_3d_url && (
            <div className="bg-indigo-50 rounded-lg p-4 text-center">
              <p className="text-sm text-indigo-600 font-medium">3D Ansicht</p>
              <a
                href={data.viewer_3d_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block mt-2 px-3 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                3D Viewer
              </a>
            </div>
          )}
        </div>
      </section>

      {/* Building Visualization - Server-generated SVGs */}
      {data.address?.matched && (
        <section className="space-y-3">
          <h4 className="font-medium text-gray-700">Gebäude-Visualisierung</h4>
          <div className="bg-white rounded-lg border shadow-sm">
            {/* Header with tabs */}
            <div className="flex items-center justify-between border-b px-4 py-2">
              <div className="flex gap-1">
                {[
                  { id: 'floor-plan' as const, label: 'Grundriss', icon: '📋' },
                  { id: 'cross-section' as const, label: 'Schnitt', icon: '📐' },
                  { id: 'elevation' as const, label: 'Ansicht', icon: '🏛️' }
                ].map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveVizTab(tab.id)}
                    className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                      activeVizTab === tab.id
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {tab.icon} {tab.label}
                  </button>
                ))}
              </div>

              {/* Professional Toggle + Download Button */}
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <span className="text-xs text-gray-500">Professional</span>
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={professionalMode}
                      onChange={(e) => setProfessionalMode(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-8 h-4 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-red-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-red-600"></div>
                  </div>
                </label>
                <a
                  href={`${apiUrl}/api/v1/visualize/${activeVizTab}?address=${encodeURIComponent(data.address.matched)}&width=1000&height=700${dimensions.traufhoehe_m ? `&traufhoehe=${dimensions.traufhoehe_m}` : ''}${dimensions.firsthoehe_m ? `&firsthoehe=${dimensions.firsthoehe_m}` : ''}${professionalMode ? '&professional=true' : ''}${professionalMode && (activeVizTab === 'cross-section' || activeVizTab === 'elevation') ? '&use_claude=true' : ''}`}
                  download={`${activeVizTab}_${data.address.matched.replace(/[^a-zA-Z0-9]/g, '_')}.svg`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition-colors"
                >
                  SVG
                </a>
                {/* Export für Claude.ai - generiert alle 3 SVGs */}
                <button
                  onClick={handleExportPrompt}
                  disabled={loadingExport}
                  className={`text-xs px-2 py-1 rounded transition-colors flex items-center gap-1 ${
                    loadingExport
                      ? 'bg-purple-200 text-purple-500 cursor-wait'
                      : 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                  }`}
                  title="Prompt für Claude.ai kopieren - generiert Grundriss + Ansicht + Schnitt"
                >
                  {copyFeedback || '🤖 Export für Claude.ai'}
                </button>
              </div>
            </div>

            {/* Visualization */}
            <div className="p-4 flex justify-center">
              <ServerSVG
                type={activeVizTab}
                address={data.address.matched}
                apiUrl={apiUrl}
                width={650}
                height={activeVizTab === 'floor-plan' ? 450 : 400}
                traufhoehe={dimensions.traufhoehe_m || undefined}
                firsthoehe={dimensions.firsthoehe_m || undefined}
                professional={professionalMode}
              />
            </div>
          </div>
        </section>
      )}

      {/* Polygon info */}
      {data.polygon?.coordinates && (
        <section className="pt-2 border-t text-sm text-gray-500">
          <p>
            Polygon mit {data.polygon.coordinates.length} Eckpunkten |{' '}
            Koordinatensystem: {data.polygon.coordinate_system}
          </p>
        </section>
      )}

      {/* Proceed to Gerüstbau Button */}
      <section className="pt-4 border-t">
        {dimensions.traufhoehe_m && dimensions.firsthoehe_m ? (
          <button
            onClick={onProceedToGeruestbau}
            className="w-full py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium flex items-center justify-center gap-2"
          >
            <span>Weiter zu Gerüstbau</span>
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        ) : (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
            <p className="text-yellow-800 font-medium">
              Höhendaten erforderlich
            </p>
            <p className="text-yellow-600 text-sm mt-1">
              Bitte Trauf- und Firsthöhe aus swissBUILDINGS3D abrufen oder manuell eingeben, um fortzufahren.
            </p>
          </div>
        )}
      </section>
    </div>
  )
}
