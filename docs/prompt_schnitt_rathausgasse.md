# SVG-Generierung: Gebäudeschnitt (Querschnitt)

Erstelle technische Architekturzeichnungen für die Gerüstplanung.
Folge den unten aufgeführten Daten und Style-Vorgaben EXAKT.

## 1. Gebäude-Identifikation
- **Adresse:** Rathausgasse 2 3011 Bern
- **EGID:** 191821074
- **Koordinaten (LV95):** E 601009, N 199736
- **Gebäudename:** RECHERCHIEREN
- **Gebäudetyp:** Wohngebäude
- **Komplexität:** SIMPLE

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
- **Traufhöhe:** 9.3 m
- **Firsthöhe:** 54.6 m
- **Geschosse:** -
- **Grundfläche:** 1099 m²

### Polygon
> **HINWEIS:** Komplexes Polygon mit 47 Punkten
> → Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 48.2m × 29.1m
- **Umfang:** 168.1 m

## 4. Terrain (swissALTI3D)
- **Terrain-Höhe:** 533.5 m ü.M.
- **Referenzpunkt:** Haupteingang = ±0.00 = 533.5 m ü.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** mansarddach
- **Dachneigung:** 72°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Höhenzonen

| Zone | Typ | Höhe | Traufe | Gerüst |
|------|-----|------|--------|--------|
| Hauptgebäude | hauptgebaeude | 54.6m | 9.3m | Standard |

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
| 0 | 5.3 | O |
| 1 | 3.1 | N |
| 2 | 6.7 | O |
| 3 | 1.5 | N |
| 4 | 1.3 | O |
| 5 | 1.5 | S |
| 6 | 7.2 | O |
| 7 | 1.5 | N |
| ... | (38 weitere) | ... |

- **Längste Fassade:** 18.4 m

## 8. Gerüst-Zugänge (SUVA)
✅ SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 12% | - |
| Z2 | SO | 18% | - |
| Z3 | N | 27% | - |
| Z4 | W | 91% | - |

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

### SVG 3: Gebäudeschnitt (Querschnitt)
- **Perspektive:** Gebäude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenräume, Konstruktion, Raumhöhen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenräume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei ±0.00 = 533.5 m ü.M. mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Gerüst:** Links und rechts (Ständer + Beläge)
- **Schnittmarkierung:** A-A

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: schnitt

**NUR SVG-Code**, keine Erklärungen.

## ⚠️ Warnungen
- Zonen-Analyse fehlgeschlagen: "Could not resolve authentication method. Expected either api_key or auth_token to be set. Or for one of the `X-Api-Key` or `Authorization` headers to be explicitly omitted"

---

*Generiert mit Gerüstplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 00:45*
*https://cooperative-commitment-production.up.railway.app*