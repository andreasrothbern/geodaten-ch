# HYBRID_WORKFLOW.md - Claude.ai Integration für professionelle SVGs

> **Version:** 1.0
> **Datum:** 25.12.2025
> **Status:** Empfohlene Architektur nach PoC-Analyse

---

## Hintergrund: PoC-Erkenntnisse

### Das Problem

| Wir haben | Wir produzieren |
|-----------|-----------------|
| ✅ Alle Daten (Polygon, Höhen, Zonen) | ❌ "Technisches Diagramm" |
| ✅ Claude erkennt Zonen korrekt | ❌ Nicht "Architekturzeichnung" |

### Warum regelbasierte Generierung nicht reicht

```
REGELBASIERT                      INTERAKTIV (Claude.ai)
────────────                      ──────────────────────

if zone == 'arkade':              "Ich sehe dass die Arkaden
  draw_rect(x, y, w, h)            niedriger sind. Ich zeichne
  fill = '#E8F5E9'                 sie mit Bögen und Schatten,
                                   passend zur Architektur..."

→ Mechanisch                      → Gestalterisch
→ One-Shot                        → Iterativ mit Feedback
→ Blind                           → "Sieht" das Ergebnis
```

### Lösung: Hybrid-Workflow

Die App sammelt und strukturiert die Daten perfekt.
Claude.ai generiert die professionellen Grafiken interaktiv.

---

## Workflow-Übersicht

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         HYBRID-WORKFLOW                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐      │
│   │             │         │             │         │             │      │
│   │  GEODATEN   │────────▶│   EXPORT    │────────▶│  CLAUDE.AI  │      │
│   │    APP      │         │   BUTTON    │         │  INTERAKTIV │      │
│   │             │         │             │         │             │      │
│   └─────────────┘         └─────────────┘         └─────────────┘      │
│                                                                         │
│   • Adresse eingeben       • JSON + Prompt        • SVG generieren     │
│   • Daten aggregieren      • In Clipboard         • Feedback geben     │
│   • Zonen analysieren      • Claude.ai öffnen     • Iterieren          │
│   • Gerüst berechnen                              • Exportieren        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Implementierung

### 1. Backend: Export-Service

**Datei:** `backend/app/services/export_for_claude.py`

```python
from app.services.export_for_claude import export_building_for_claude, to_clipboard_text

# API-Endpoint
@router.get("/api/v1/export/claude/{egid}")
async def export_for_claude(egid: str, format: str = "clipboard"):
    """
    Exportiert Gebäudedaten für Claude.ai
    
    Formate:
    - clipboard: Prompt + JSON (für Copy-Paste)
    - json: Nur strukturierte Daten
    - markdown: Formatiert mit Tabellen
    """
    # Daten sammeln
    building = await get_building_data(egid)
    scaffolding = await calculate_scaffolding(egid)
    context = await get_building_context(egid)
    
    # Export erstellen
    export = export_building_for_claude(
        gebaeude_data=building,
        polygon=building['polygon'],
        zonen=context.get('zones', []),
        fassaden=scaffolding['fassaden'],
        geruest_config=scaffolding['config'],
        zugaenge=context.get('zugaenge', []),
        ausmasse=scaffolding['ausmasse'],
        material=scaffolding['material']
    )
    
    return create_export_response(export, format)
```

### 2. Frontend: Export-Button

**Datei:** `frontend/src/components/ExportForClaude.tsx`

```tsx
import { ExportForClaude, useExportData } from './ExportForClaude';

// In der Hauptkomponente
function BuildingView({ buildingData, scaffoldingData, contextData }) {
  const exportData = useExportData(buildingData, scaffoldingData, contextData);
  
  return (
    <div>
      {/* ... andere Komponenten ... */}
      
      {exportData && (
        <ExportForClaude 
          data={exportData}
          className="mt-4"
        />
      )}
    </div>
  );
}
```

### 3. Prompt-Template

**Datei:** `docs/CLAUDE_SVG_PROMPT.md`

Das Template wird automatisch mit den Daten kombiniert und enthält:
- Klare Anweisungen für SVG-Erstellung
- Gewünschte Ausgaben (Grundriss, Schnitt, Ansicht)
- Stil-Vorgaben und Farbschema
- Wichtige Regeln
- Iterativen Workflow

---

## Datenstruktur des Exports

```json
{
  "export_version": "1.0",
  "export_datum": "2025-12-25T10:30:00",
  
  "gebaeude": {
    "adresse": "Bundesplatz 3, 3011 Bern",
    "egid": "1230564",
    "gkat": 1040,
    "gkat_text": "Gebäude mit Nebennutzung",
    "garea": 4850,
    "gastw": 4,
    "gbauj": 1902
  },
  
  "polygon": [
    [600423.19, 199521.05],
    [600450.32, 199521.05],
    // ... 26 Punkte total
  ],
  
  "zonen": [
    {
      "id": "zone_arkade",
      "name": "Arkaden",
      "typ": "arkade",
      "gebaeudehoehe_m": 14.5,
      "fassaden_ids": ["S"],
      "farbe": "#E8F5E9",
      "beruesten": true
    },
    {
      "id": "zone_parlament",
      "name": "Parlamentsgebäude",
      "typ": "hauptgebaeude",
      "gebaeudehoehe_m": 25.0,
      "fassaden_ids": ["N", "E", "W"],
      "farbe": "#E3F2FD",
      "beruesten": true
    }
    // ...
  ],
  
  "fassaden": [
    {
      "id": "N",
      "name": "Nord",
      "laenge_m": 65.0,
      "ausrichtung_grad": 0,
      "hoehe_m": 25.0,
      "ausmass_m2": 1690.0
    }
    // ...
  ],
  
  "geruest": {
    "system": "Layher Blitz 70",
    "breitenklasse": "W09",
    "gesamthoehe_m": 26.0,
    "gesamtflaeche_m2": 5200.0,
    "anzahl_lagen": 13,
    "verankerung_raster_h_m": 4.0,
    "verankerung_raster_v_m": 4.0
  },
  
  "zugaenge": [
    {
      "id": "Z1",
      "fassade_id": "W",
      "position_percent": 0.5,
      "grund": "Stirnseite West"
    }
    // ...
  ],
  
  "prompt_hinweise": [
    "Komplexes Gebäude mit 5 Höhenzonen",
    "Kuppel vorhanden - nicht mit Standgerüst einrüstbar",
    "Grosse Höhenvariation: 14.5m bis 64.0m"
  ]
}
```

---

## Benutzer-Workflow

### Schritt 1: Daten in App sammeln

1. User gibt Adresse ein (z.B. "Bundesplatz 3, Bern")
2. App lädt Gebäudedaten (GWR, Polygon, Höhen)
3. App analysiert Zonen (automatisch oder mit Claude)
4. App berechnet Gerüst (NPK 114, Material)

### Schritt 2: Export für Claude.ai

1. User klickt **"Export für Claude.ai"**
2. App zeigt Zusammenfassung der Daten
3. User klickt **"Kopieren & Claude.ai öffnen"**
4. Prompt + JSON werden in Zwischenablage kopiert
5. Claude.ai öffnet sich in neuem Tab

### Schritt 3: SVG-Generierung in Claude.ai

1. User fügt kopierten Text ein (Ctrl+V)
2. Claude.ai generiert **Grundriss**
3. User gibt Feedback ("Masslinien grösser", "Legende links")
4. Claude.ai iteriert
5. Nach Freigabe: **Schnitt**
6. Nach Freigabe: **Ansicht**

### Schritt 4: Export der Ergebnisse

1. User kopiert fertige SVGs aus Claude.ai
2. Optional: Upload zurück in App
3. Optional: PDF-Export mit Titelblock

---

## Vorteile des Hybrid-Ansatzes

| Aspekt | Regelbasiert | Hybrid |
|--------|--------------|--------|
| **Datenqualität** | ✅ Perfekt | ✅ Perfekt (aus App) |
| **SVG-Qualität** | ❌ Technisch | ✅ Professionell |
| **Iteration** | ❌ Keine | ✅ Unbegrenzt |
| **Kosten** | ✅ Keine | ⚠️ Claude.ai Nutzung |
| **Geschwindigkeit** | ✅ Sofort | ⚠️ ~5-10 Min pro Gebäude |
| **Komplexe Gebäude** | ❌ Limitiert | ✅ Flexibel |

---

## Dateien

| Datei | Pfad | Beschreibung |
|-------|------|--------------|
| Export-Service | `backend/app/services/export_for_claude.py` | Python-Service für Datenexport |
| Prompt-Template | `docs/CLAUDE_SVG_PROMPT.md` | Optimiertes Prompt für Claude.ai |
| React-Component | `frontend/src/components/ExportForClaude.tsx` | Export-Button mit UI |
| Diese Doku | `docs/HYBRID_WORKFLOW.md` | Workflow-Dokumentation |

---

## Nächste Schritte

1. **Integration in Frontend**
   - ExportForClaude Component einbinden
   - Nach Gerüst-Berechnung anzeigen

2. **API-Endpoint erstellen**
   - `/api/v1/export/claude/{egid}`
   - Verschiedene Formate (clipboard, json, markdown)

3. **Testen mit Bundeshaus**
   - Export generieren
   - In Claude.ai einfügen
   - SVGs erstellen und bewerten

4. **Optional: SVG-Upload**
   - Fertige SVGs zurück in App laden
   - Mit Projekt verknüpfen

---

*Erstellt nach PoC-Analyse vom 25.12.2025*
