// frontend/src/components/ExportForClaude.tsx
/**
 * Export-Button für Claude.ai Hybrid-Workflow
 * 
 * Funktionen:
 * - Exportiert Gebäudedaten als JSON
 * - Kopiert Prompt + Daten in Zwischenablage
 * - Öffnet optional Claude.ai in neuem Tab
 * 
 * Version: 1.0
 * Datum: 25.12.2025
 */

import React, { useState } from 'react';

// =============================================================================
// TYPES
// =============================================================================

interface ExportData {
  gebaeude: {
    adresse: string;
    egid: string;
    gkat?: number;
    gkat_text?: string;
    garea?: number;
    gastw?: number;
    gbauj?: number;
  };
  polygon: number[][];
  polygon_vereinfacht?: number[][];
  zonen: Zone[];
  fassaden: Fassade[];
  geruest: GeruestConfig;
  zugaenge: Zugang[];
  ausmasse?: Record<string, any>;
  material?: Record<string, any>;
}

interface Zone {
  id: string;
  name: string;
  typ: string;
  traufhoehe_m?: number;
  firsthoehe_m?: number;
  gebaeudehoehe_m: number;
  fassaden_ids: string[];
  farbe: string;
  beruesten: boolean;
}

interface Fassade {
  id: string;
  name: string;
  laenge_m: number;
  ausrichtung_grad: number;
  hoehe_m: number;
  ausmass_m2: number;
}

interface GeruestConfig {
  system: string;
  breitenklasse: string;
  gesamthoehe_m: number;
  gesamtflaeche_m2: number;
  anzahl_lagen: number;
}

interface Zugang {
  id: string;
  fassade_id: string;
  position_percent: number;
  grund: string;
}

interface ExportForClaudeProps {
  data: ExportData;
  disabled?: boolean;
  className?: string;
}

// =============================================================================
// PROMPT TEMPLATE
// =============================================================================

const PROMPT_TEMPLATE = `# Professionelle Gerüstpläne erstellen

Ich habe Gebäudedaten aus einer Schweizer Geodaten-App exportiert. Die Daten enthalten:
- Exaktes Gebäude-Polygon (amtliche Vermessung, ±10cm)
- Gemessene Höhendaten (swissBUILDINGS3D)
- Analysierte Höhenzonen
- Berechnete Gerüst-Konfiguration (NPK 114)

Bitte erstelle professionelle Gerüstpläne als SVG.

## Gewünschte Ausgaben

1. **Grundriss (Draufsicht)** - M 1:200
   - Gebäude-Polygon mit farbcodierten Zonen
   - Gerüstfläche (schraffiert, 30cm Abstand)
   - Ständerpositionen, Verankerungen, Zugänge
   - Masslinien, Nordpfeil, Legende

2. **Schnitt** - M 1:100
   - Gebäudeprofil mit Höhenzonen
   - Gerüst mit Lagen (L1, L2, etc.)
   - Höhenkoten

3. **Ansicht Hauptfassade** - M 1:100
   - Felder (F1, F2, etc.) mit Längen
   - Lagen nummeriert
   - Verankerungsraster (4m × 4m)

## Wichtige Regeln

- Alle Masse aus den Daten übernehmen, NICHTS erfinden
- Massstab einhalten
- Professionelle Architekturzeichnung, nicht technisches Diagramm
- Iterativ: Grundriss zuerst, dann Feedback, dann Schnitt, etc.

## Gebäudedaten

\`\`\`json
DATA_PLACEHOLDER
\`\`\`

Bitte beginne mit dem **Grundriss**.`;

// =============================================================================
// COMPONENT
// =============================================================================

export const ExportForClaude: React.FC<ExportForClaudeProps> = ({
  data,
  disabled = false,
  className = ''
}) => {
  const [copied, setCopied] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  // Generiere Export-Text
  const generateExportText = (): string => {
    const jsonData = JSON.stringify(data, null, 2);
    return PROMPT_TEMPLATE.replace('DATA_PLACEHOLDER', jsonData);
  };

  // Kopiere in Zwischenablage
  const handleCopy = async () => {
    try {
      const exportText = generateExportText();
      await navigator.clipboard.writeText(exportText);
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch (err) {
      console.error('Fehler beim Kopieren:', err);
      alert('Kopieren fehlgeschlagen. Bitte manuell kopieren.');
    }
  };

  // Öffne Claude.ai
  const handleOpenClaude = () => {
    window.open('https://claude.ai/new', '_blank');
  };

  // Kopiere und öffne Claude.ai
  const handleCopyAndOpen = async () => {
    await handleCopy();
    handleOpenClaude();
  };

  // Download als Datei
  const handleDownload = () => {
    const exportText = generateExportText();
    const blob = new Blob([exportText], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `geruest-export-${data.gebaeude.egid || 'building'}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Zusammenfassung der Daten
  const summary = {
    adresse: data.gebaeude.adresse || 'Unbekannt',
    zonen: data.zonen.length,
    fassaden: data.fassaden.length,
    zugaenge: data.zugaenge.length,
    flaeche: data.geruest.gesamtflaeche_m2?.toFixed(0) || '?',
    hoehe: data.geruest.gesamthoehe_m?.toFixed(1) || '?'
  };

  return (
    <div className={`export-for-claude ${className}`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white p-4 rounded-t-lg">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Export für Claude.ai
        </h3>
        <p className="text-sm text-purple-100 mt-1">
          Professionelle SVG-Pläne mit KI erstellen
        </p>
      </div>

      {/* Zusammenfassung */}
      <div className="bg-gray-50 p-4 border-x border-gray-200">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <div>
            <span className="text-gray-500">Adresse:</span>
            <span className="ml-1 font-medium">{summary.adresse}</span>
          </div>
          <div>
            <span className="text-gray-500">Zonen:</span>
            <span className="ml-1 font-medium">{summary.zonen}</span>
          </div>
          <div>
            <span className="text-gray-500">Fassaden:</span>
            <span className="ml-1 font-medium">{summary.fassaden}</span>
          </div>
          <div>
            <span className="text-gray-500">Zugänge:</span>
            <span className="ml-1 font-medium">{summary.zugaenge}</span>
          </div>
          <div>
            <span className="text-gray-500">Fläche:</span>
            <span className="ml-1 font-medium">{summary.flaeche} m²</span>
          </div>
          <div>
            <span className="text-gray-500">Höhe:</span>
            <span className="ml-1 font-medium">{summary.hoehe} m</span>
          </div>
        </div>
      </div>

      {/* Aktionen */}
      <div className="p-4 bg-white border border-gray-200 rounded-b-lg space-y-3">
        {/* Haupt-Button */}
        <button
          onClick={handleCopyAndOpen}
          disabled={disabled}
          className={`w-full py-3 px-4 rounded-lg font-medium text-white 
                     flex items-center justify-center gap-2 transition-all
                     ${disabled 
                       ? 'bg-gray-400 cursor-not-allowed' 
                       : 'bg-purple-600 hover:bg-purple-700 active:scale-98'}`}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                  d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
          </svg>
          Kopieren & Claude.ai öffnen
        </button>

        {/* Sekundäre Buttons */}
        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            disabled={disabled}
            className={`flex-1 py-2 px-3 rounded border text-sm font-medium
                       flex items-center justify-center gap-1 transition-all
                       ${copied 
                         ? 'bg-green-50 border-green-300 text-green-700' 
                         : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'}`}
          >
            {copied ? (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Kopiert!
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2" />
                </svg>
                Nur kopieren
              </>
            )}
          </button>

          <button
            onClick={handleDownload}
            disabled={disabled}
            className="flex-1 py-2 px-3 rounded border border-gray-300 bg-white 
                       text-gray-700 text-sm font-medium hover:bg-gray-50
                       flex items-center justify-center gap-1 transition-all"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download .md
          </button>
        </div>

        {/* Preview Toggle */}
        <button
          onClick={() => setShowPreview(!showPreview)}
          className="w-full py-2 text-sm text-gray-500 hover:text-gray-700 
                     flex items-center justify-center gap-1"
        >
          <svg className={`w-4 h-4 transition-transform ${showPreview ? 'rotate-180' : ''}`} 
               fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
          {showPreview ? 'Vorschau ausblenden' : 'Daten-Vorschau anzeigen'}
        </button>

        {/* Preview */}
        {showPreview && (
          <div className="mt-2 p-3 bg-gray-900 rounded-lg overflow-auto max-h-64">
            <pre className="text-xs text-gray-300 whitespace-pre-wrap">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Hinweis */}
      <p className="mt-2 text-xs text-gray-500 text-center">
        Der Export enthält alle Gebäudedaten und einen optimierten Prompt für Claude.ai
      </p>
    </div>
  );
};

// =============================================================================
// HOOK FÜR DATEN-AGGREGATION
// =============================================================================

/**
 * Hook um Export-Daten aus verschiedenen Quellen zu aggregieren
 */
export const useExportData = (
  buildingData: any,
  scaffoldingData: any,
  contextData: any
): ExportData | null => {
  if (!buildingData || !scaffoldingData) {
    return null;
  }

  // Zonen aus Context oder Default
  const zonen: Zone[] = contextData?.zones || [{
    id: 'zone_1',
    name: 'Hauptgebäude',
    typ: 'hauptgebaeude',
    gebaeudehoehe_m: buildingData.hoehe_m || 10,
    fassaden_ids: ['N', 'E', 'S', 'W'],
    farbe: '#E3F2FD',
    beruesten: true
  }];

  // Fassaden aus Scaffolding-Daten
  const fassaden: Fassade[] = scaffoldingData.fassaden?.map((f: any) => ({
    id: f.id || f.richtung,
    name: f.name || f.richtung,
    laenge_m: f.laenge_m || f.laenge,
    ausrichtung_grad: f.ausrichtung_grad || 0,
    hoehe_m: f.hoehe_m || scaffoldingData.gesamthoehe_m,
    ausmass_m2: f.ausmass_m2 || 0
  })) || [];

  // Zugänge aus Context oder berechnet
  const zugaenge: Zugang[] = contextData?.zugaenge || 
    scaffoldingData.zugaenge?.map((z: any) => ({
      id: z.id,
      fassade_id: z.fassade_id,
      position_percent: z.position_percent || 0.5,
      grund: z.grund || 'Automatisch'
    })) || [];

  return {
    gebaeude: {
      adresse: buildingData.adresse || '',
      egid: buildingData.egid || '',
      gkat: buildingData.gkat,
      gkat_text: buildingData.gkat_text,
      garea: buildingData.garea,
      gastw: buildingData.gastw,
      gbauj: buildingData.gbauj
    },
    polygon: buildingData.polygon || [],
    polygon_vereinfacht: buildingData.polygon_simplified || buildingData.polygon,
    zonen,
    fassaden,
    geruest: {
      system: 'Layher Blitz 70',
      breitenklasse: 'W09',
      gesamthoehe_m: scaffoldingData.gesamthoehe_m || 10,
      gesamtflaeche_m2: scaffoldingData.gesamtflaeche_m2 || 0,
      anzahl_lagen: scaffoldingData.anzahl_lagen || 5
    },
    zugaenge,
    ausmasse: scaffoldingData.ausmasse,
    material: scaffoldingData.material
  };
};

export default ExportForClaude;
