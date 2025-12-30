# SVG-Generierung: Grundriss + Fassadenansicht + Gebäudeschnitt

Erstelle technische Architekturzeichnungen für die Gerüstplanung.
Folge den unten aufgeführten Daten und Style-Vorgaben EXAKT.

## 1. Gebäude-Identifikation
- **Adresse:** Bundesplatz 3 3011 Bern
- **EGID:** 2242547
- **Koordinaten (LV95):** E 600423, N 199521
- **Gebäudename:** Bundeshaus
- **Gebäudetyp:** Parlamentsgebäude
- **Baustil:** Neorenaissance / Historismus
- **Baujahr:** 1902
- **Komplexität:** COMPLEX

## 2. RECHERCHE-ANWEISUNG

> **WICHTIG:** Falls Gebäudename oder Baustil nicht bekannt:
> 1. Suche das Gebäude anhand Adresse/EGID/Koordinaten
> 2. Identifiziere den korrekten Gebäudenamen
> 3. Bestimme Gebäudetyp und Baustil
> 4. Ermittle charakteristische Architekturmerkmale
> 5. Validiere die Höhenzonen gegen recherchierte Informationen
> **Erst danach mit der SVG-Erstellung beginnen.**

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhöhe:** 53.2 m
- **Firsthöhe:** 62.6 m
- **Geschosse:** -
- **Grundfläche:** 3697 m²

### Polygon
> **HINWEIS:** Komplexes Polygon mit 26 Punkten
> → Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 80.2m × 71.0m
- **Umfang:** 310.0 m

## 4. Terrain (swissALTI3D)
- **Terrain-Höhe:** 543.1 m ü.M.
- **Referenzpunkt:** Haupteingang = ±0.00 = 543.1 m ü.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** pultdach
- **Dachneigung:** 15°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Höhenzonen

| Zone | Typ | Höhe | Traufe | Gerüst |
|------|-----|------|--------|--------|
| Arkaden | arkade | 6.0m | 6.0m | Standard |
| Hauptgebäude | hauptgebaeude | 30.0m | 25.0m | Standard |
| Kuppel | kuppel | 64.0m | 30.0m | Sonderkonstruktion |

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkörper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebäude
- **innenhof** = Nicht einrüsten (Freifläche)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 14.0 | O |
| 1 | 15.4 | N |
| 2 | 4.0 | W |
| 3 | 14.8 | N |
| 4 | 16.5 | O |
| 5 | 6.0 | N |
| 6 | 27.0 | O |
| 7 | 6.0 | S |
| ... | (17 weitere) | ... |

- **Längste Fassade:** 27.0 m

## 8. Gerüst-Zugänge (SUVA)
✅ SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | N | 93% | - |
| Z2 | N | 7% | - |
| Z3 | O | 42% | - |
| Z4 | O | 3% | - |
| Z5 | S | 47% | - |
| Z6 | W | 51% | - |
| Z7 | N | 93% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur für Aussenflächen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur für Schnittflächen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR für Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebäude-Aussenfläche | url(#hatch) | Fassade + Grundriss |
| Schnittfläche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Gerüst-Ständer | #0066CC (blau) | Alle SVGs |
| Beläge | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBÄUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    ┌─────────┐                        ┌─────────┐
    │░░░░░░░░░│ ← Fassade             │█│     │█│ ← Schnittfläche
    │░░░░░░░░░│   (alles sichtbar      │ │     │ │   (dicht schraffiert)
    │░░░░░░░░░│    von aussen)         │ │     │ │
    └─────────┘                        │ │     │ │ ← Innenraum (LEER!)
                                       └─┴─────┴─┘

░░░ = lockere Schraffur            █ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebäudeumriss, Wandstärken, Fassadenlängen
- **Schraffur:** url(#hatch) für Mauern
- **Gerüstzone:** Rechteckige Hülle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung
- **Zonen:** Farblich unterscheiden, Innenhöfe markieren

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenfläche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenräume sichtbar!
- **Schraffur:** url(#hatch) für alle Fassadenflächen
- **Terrain-Linie:** bei ±0.00 = 543.1 m ü.M.
- **Gerüst:** VOR der Fassade (Ständer blau, Beläge braun)
- **Höhenskala:** Links (±0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)

### SVG 3: Gebäudeschnitt (Querschnitt)
- **Perspektive:** Gebäude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenräume, Konstruktion, Raumhöhen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenräume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei ±0.00 = 543.1 m ü.M. mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Gerüst:** Links und rechts (Ständer + Beläge)
- **Schnittmarkierung:** A-A

## 12. Output

Erstelle **3 separate SVGs**, jeweils mit `viewBox="0 0 700 480"`:

1. **grundriss.svg** - Draufsicht mit Gebäudeumriss und Gerüstzone
2. **fassadenansicht.svg** - Aussenansicht, vordere Elemente verdecken hintere
3. **gebaeudeschnitt.svg** - Aufgeschnitten, Innenräume sichtbar und LEER

**NUR SVG-Code**, keine Erklärungen. Trenne die SVGs mit Kommentar:
`<!-- SVG 1: Grundriss -->`

---

*Generiert mit Gerüstplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 01:52*
*https://cooperative-commitment-production.up.railway.app*