/**
 * Export-Funktionen für Gerüstdaten
 */

interface FassadeExport {
  name: string
  laenge_m: number
  hoehe_m: number
  flaeche_m2: number
}

interface MaterialExport {
  artikel_nr: string
  bezeichnung: string
  kategorie: string
  menge: number
  gewicht_kg: number | null
}

interface ExportData {
  adresse: string
  datum: string
  gebaeude: {
    egid?: number
    laenge_m: number
    breite_m: number
    hoehe_traufe_m: number
    hoehe_first_m?: number
    dachform: string
  }
  ausmass: {
    fassaden: FassadeExport[]
    eck_zuschlag_m2: number
    total_m2: number
  }
  material: {
    system: string
    liste: MaterialExport[]
    total_stueck: number
    total_gewicht_kg: number
  }
}

/**
 * Export als CSV (Excel-kompatibel)
 */
export function exportToCSV(data: ExportData): void {
  const lines: string[] = []

  // Header Info
  lines.push('Gerüstausmass nach NPK 114 D/2012')
  lines.push('')
  lines.push(`Adresse;${data.adresse}`)
  lines.push(`Datum;${data.datum}`)
  lines.push(`EGID;${data.gebaeude.egid || '-'}`)
  lines.push('')

  // Gebäudedaten
  lines.push('GEBÄUDEDATEN')
  lines.push(`Länge;${data.gebaeude.laenge_m};m`)
  lines.push(`Breite;${data.gebaeude.breite_m};m`)
  lines.push(`Traufhöhe;${data.gebaeude.hoehe_traufe_m};m`)
  if (data.gebaeude.hoehe_first_m) {
    lines.push(`Firsthöhe;${data.gebaeude.hoehe_first_m};m`)
  }
  lines.push(`Dachform;${data.gebaeude.dachform}`)
  lines.push('')

  // Ausmass
  lines.push('AUSMASS NPK 114')
  lines.push('Fassade;Länge (m);Höhe (m);Fläche (m²)')
  data.ausmass.fassaden.forEach(f => {
    lines.push(`${f.name};${f.laenge_m.toFixed(1)};${f.hoehe_m.toFixed(1)};${f.flaeche_m2.toFixed(2)}`)
  })
  lines.push(`Eckzuschlag;;;${data.ausmass.eck_zuschlag_m2.toFixed(2)}`)
  lines.push(`TOTAL;;;${data.ausmass.total_m2.toFixed(2)}`)
  lines.push('')

  // Material
  lines.push(`MATERIALLISTE (${data.material.system})`)
  lines.push('Art.-Nr.;Bezeichnung;Kategorie;Menge;Gewicht (kg)')
  data.material.liste.forEach(m => {
    lines.push(`${m.artikel_nr};${m.bezeichnung};${m.kategorie};${m.menge};${m.gewicht_kg?.toFixed(1) || '-'}`)
  })
  lines.push('')
  lines.push(`Total Stück;;${data.material.total_stueck}`)
  lines.push(`Total Gewicht;;;${data.material.total_gewicht_kg.toFixed(1)};kg`)

  // Download
  const csv = lines.join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `geruest_ausmass_${data.datum.replace(/\./g, '-')}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

/**
 * Export als PDF (vereinfachte Text-Version)
 */
export function exportToPDF(data: ExportData): void {
  // Erstelle einen druckbaren HTML-Inhalt
  const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Gerüstausmass - ${data.adresse}</title>
  <style>
    body { font-family: Arial, sans-serif; font-size: 11px; padding: 20px; }
    h1 { font-size: 16px; color: #333; margin-bottom: 5px; }
    h2 { font-size: 13px; color: #666; margin-top: 20px; margin-bottom: 10px; border-bottom: 1px solid #ddd; }
    .header { margin-bottom: 20px; }
    .info { color: #666; margin-bottom: 5px; }
    table { width: 100%; border-collapse: collapse; margin: 10px 0; }
    th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }
    th { background: #f5f5f5; font-weight: bold; }
    td.number { text-align: right; font-family: monospace; }
    .total { font-weight: bold; background: #fff0f0; }
    .footer { margin-top: 30px; font-size: 9px; color: #999; border-top: 1px solid #ddd; padding-top: 10px; }
    @media print { body { padding: 0; } }
  </style>
</head>
<body>
  <div class="header">
    <h1>Gerüstausmass nach NPK 114 D/2012</h1>
    <p class="info"><strong>Adresse:</strong> ${data.adresse}</p>
    <p class="info"><strong>Datum:</strong> ${data.datum}</p>
    ${data.gebaeude.egid ? `<p class="info"><strong>EGID:</strong> ${data.gebaeude.egid}</p>` : ''}
  </div>

  <h2>Gebäudedaten</h2>
  <table>
    <tr><td>Länge</td><td class="number">${data.gebaeude.laenge_m.toFixed(1)} m</td></tr>
    <tr><td>Breite</td><td class="number">${data.gebaeude.breite_m.toFixed(1)} m</td></tr>
    <tr><td>Traufhöhe</td><td class="number">${data.gebaeude.hoehe_traufe_m.toFixed(1)} m</td></tr>
    ${data.gebaeude.hoehe_first_m ? `<tr><td>Firsthöhe</td><td class="number">${data.gebaeude.hoehe_first_m.toFixed(1)} m</td></tr>` : ''}
    <tr><td>Dachform</td><td>${data.gebaeude.dachform}</td></tr>
  </table>

  <h2>Ausmass (NPK 114)</h2>
  <table>
    <tr><th>Fassade</th><th>Länge</th><th>Höhe</th><th>Fläche</th></tr>
    ${data.ausmass.fassaden.map(f => `
      <tr>
        <td>${f.name}</td>
        <td class="number">${f.laenge_m.toFixed(1)} m</td>
        <td class="number">${f.hoehe_m.toFixed(1)} m</td>
        <td class="number">${f.flaeche_m2.toFixed(2)} m²</td>
      </tr>
    `).join('')}
    <tr>
      <td colspan="3">Eckzuschlag</td>
      <td class="number">${data.ausmass.eck_zuschlag_m2.toFixed(2)} m²</td>
    </tr>
    <tr class="total">
      <td colspan="3"><strong>TOTAL AUSMASS</strong></td>
      <td class="number"><strong>${data.ausmass.total_m2.toFixed(2)} m²</strong></td>
    </tr>
  </table>

  <h2>Materialliste (${data.material.system})</h2>
  <table>
    <tr><th>Art.-Nr.</th><th>Bezeichnung</th><th>Menge</th><th>Gewicht</th></tr>
    ${data.material.liste.slice(0, 20).map(m => `
      <tr>
        <td>${m.artikel_nr}</td>
        <td>${m.bezeichnung}</td>
        <td class="number">${m.menge}</td>
        <td class="number">${m.gewicht_kg ? m.gewicht_kg.toFixed(1) + ' kg' : '-'}</td>
      </tr>
    `).join('')}
    ${data.material.liste.length > 20 ? `<tr><td colspan="4">... und ${data.material.liste.length - 20} weitere Artikel</td></tr>` : ''}
    <tr class="total">
      <td colspan="2"><strong>TOTAL</strong></td>
      <td class="number"><strong>${data.material.total_stueck} Stk</strong></td>
      <td class="number"><strong>${data.material.total_gewicht_kg.toFixed(0)} kg</strong></td>
    </tr>
  </table>

  <div class="footer">
    <p>Erstellt mit Geodaten Schweiz | Daten: swisstopo, BFS/GWR | NPK 114 D/2012</p>
    <p>Materialliste basiert auf Richtwerten, tatsächliche Mengen können abweichen.</p>
  </div>
</body>
</html>
  `

  // Öffne neues Fenster zum Drucken
  const printWindow = window.open('', '_blank')
  if (printWindow) {
    printWindow.document.write(html)
    printWindow.document.close()
    printWindow.print()
  }
}

/**
 * Konvertiere API-Daten in Export-Format
 */
export function prepareExportData(apiData: any): ExportData {
  const now = new Date()
  const datum = now.toLocaleDateString('de-CH')

  return {
    adresse: apiData.adresse?.gefunden || apiData.adresse?.eingabe || '',
    datum,
    gebaeude: {
      egid: apiData.gebaeude?.egid,
      laenge_m: apiData.gebaeude?.laenge_m || 0,
      breite_m: apiData.gebaeude?.breite_m || 0,
      hoehe_traufe_m: apiData.gebaeude?.hoehe_traufe_m || 0,
      hoehe_first_m: apiData.gebaeude?.hoehe_first_m,
      dachform: apiData.gebaeude?.dachform || 'unbekannt'
    },
    ausmass: {
      fassaden: (apiData.ausmass?.fassaden || []).map((f: any) => ({
        name: f.name,
        laenge_m: f.ausmass?.laenge_m || 0,
        hoehe_m: f.ausmass?.hoehe_m || 0,
        flaeche_m2: f.ausmass?.flaeche_m2 || 0
      })),
      eck_zuschlag_m2: apiData.ausmass?.zusammenfassung?.eck_zuschlag_m2 || 0,
      total_m2: apiData.ausmass?.zusammenfassung?.total_ausmass_m2 || 0
    },
    material: {
      system: apiData.material?.system || 'unbekannt',
      liste: (apiData.material?.liste || []).map((m: any) => ({
        artikel_nr: m.article_number,
        bezeichnung: m.name,
        kategorie: m.category,
        menge: m.quantity_typical,
        gewicht_kg: m.total_weight_kg
      })),
      total_stueck: apiData.material?.zusammenfassung?.total_stueck || 0,
      total_gewicht_kg: apiData.material?.zusammenfassung?.total_gewicht_kg || 0
    }
  }
}
