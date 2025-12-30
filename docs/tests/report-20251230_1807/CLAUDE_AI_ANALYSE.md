# Claude.ai Analyse-Bundle: 20251230_1807

## ANWEISUNGEN FÜR CLAUDE.AI

Dieses Dokument enthält Test-Ergebnisse unserer SVG-Generierungs-Pipeline für Gerüstplanung.

### Deine Aufgaben:

**1. SVG-Generierung & Vergleich**
- Generiere für JEDES Gebäude die SVGs (Grundriss, Ansicht, Schnitt) basierend auf den mitgelieferten Prompts
- Vergleiche deine generierten SVGs mit den SVGs der Claude-API (unten aufgeführt)
- Dokumentiere Unterschiede: Was macht die API anders? Was ist besser/schlechter?

**2. Prompt-Analyse**
- Analysiere die SVG-Prompts: Was ist fehlerhaft, verbesserungswürdig, perfekt?
- Analysiere die Recherche-Prompts: Werden die richtigen Gebäudedaten erkannt?
- Identifiziere Inkonsistenzen zwischen Prompt und generiertem SVG

**3. Verbesserungsvorschläge**
- Erstelle konkrete, priorisierte Verbesserungsvorschläge für die Prompts
- Unterscheide: Quick Wins vs. größere Änderungen
- Berücksichtige die gesamte Pipeline (Recherche → Daten → SVG-Prompt → SVG)

### Ausgabe-Format:

Bitte strukturiere deine Analyse wie folgt:

```
## Gebäude: [Name]

### SVG-Vergleich
| Typ | API-Qualität | Deine Version | Unterschiede |
|-----|--------------|---------------|--------------|

### Prompt-Bewertung
- Stärken: ...
- Schwächen: ...
- Fehler: ...

### Verbesserungsvorschläge
1. ...
2. ...
```

---

## ÜBERSICHT TESTGEBÄUDE

| Nr | Gebäude | Komplexität | Status |
|----|---------|-------------|--------|
| 1 | Bundeshaus | complex | bekannt |
| 2 | Berner Muenster | complex | bekannt |
| 3 | St. Peter und Paul | complex | bekannt |
| 4 | Einsteinhaus | simple | bekannt |
| 5 | Kunstmuseum | complex | bekannt |
| 6 | Kornhaus | complex | bekannt |
| 7 | Hauptbahnhof | complex | bekannt |
| 8 | Stadttheater | complex | bekannt |
| 9 | Historisches Museum | complex | bekannt |
| 10 | Hotel Schweizerhof | moderate | bekannt |

---


================================================================================
# GEBÄUDE 1: Bundeshaus
================================================================================

## Adresse
Bundesplatz 3, 3011 Bern

## EGID
2242547

## Recherche-Ergebnis (aus Pipeline)

- **Gebäudename:** Bundeshaus
- **Gebäudetyp:** Parlamentsgebaeude
- **Architekturstil:** Neorenaissance / Historismus
- **Baujahr:** 1902
- **Komplexität:** complex
- **Traufhöhe:** 53.2 m
- **Firsthöhe:** 62.6 m

### Erkannte Zonen

**Zone 1: Arkaden**
- Typ: arkade
- Traufhöhe: 6.0 m
- Firsthöhe: 6.0 m
- Sonderkonstruktion: Nein

**Zone 2: Hauptgebäude**
- Typ: hauptgebaeude
- Traufhöhe: 25.0 m
- Firsthöhe: 30.0 m
- Sonderkonstruktion: Nein

**Zone 3: Kuppel**
- Typ: kuppel
- Traufhöhe: 30.0 m
- Firsthöhe: 64.0 m
- Sonderkonstruktion: Ja


--------------------------------------------------------------------------------
## GRUNDRISS-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Grundriss (Draufsicht)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Bundesplatz 3 3011 Bern
- **EGID:** 2242547
- **Koordinaten (LV95):** E 600423, N 199521
- **Gebaeudename:** Bundeshaus
- **Gebaeudetyp:** Parlamentsgebaeude
- **Baustil:** Neorenaissance / Historismus
- **Baujahr:** 1902
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 53.2 m
- **Firsthoehe:** 62.6 m
- **Geschosse:** -
- **Grundflaeche:** 3697 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 26 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 80.2m × 71.0m
- **Umfang:** 310.0 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 543.1 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 543.1 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** kuppel
- **Dachneigung:** 15°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Arkaden | arkade | 6.0m | 6.0m | 6.0m | Standard |
| Hauptgebäude | hauptgebaeude | 25.0m | 30.0m | 30.0m | Standard |
| Kuppel | kuppel | 30.0m | 64.0m | 64.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Arkaden): **6.0m**
- Zone 2 (Hauptgebäude): **30.0m**
- Zone 3 (Kuppel): **64.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

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

- **Laengste Fassade:** 27.0 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

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
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** Rechteckige Huelle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung
- **Zonen:** Farblich unterscheiden, Innenhoefe markieren

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: grundriss

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Arkaden' (6.0m) deutlich unter API-Traufhoehe (53.2m) - Zone-Daten pruefen!
- Zone 'Hauptgebäude' (30.0m) deutlich unter API-Traufhoehe (53.2m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## GRUNDRISS-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Titel -->
  <text x="20" y="30" font-family="Arial" font-size="16" font-weight="bold" fill="#000">GRUNDRISS (Draufsicht) - Bundeshaus</text>
  <text x="20" y="50" font-family="Arial" font-size="12" fill="#666">Bundesplatz 3, 3011 Bern | EGID: 2242547 | 80.2m × 71.0m</text>

  <!-- Geruestzone (äussere Begrenzung mit 1m Abstand) -->
  <rect x="100" y="90" width="410" height="290" fill="none" stroke="#0066CC" stroke-width="2" stroke-dasharray="5,5"/>
  <text x="105" y="105" font-family="Arial" font-size="10" fill="#0066CC">Gerüstzone (+1m)</text>

  <!-- Zone 1: Arkaden (Umrandung des Hauptgebäudes) -->
  <rect x="120" y="110" width="370" height="250" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <text x="125" y="125" font-family="Arial" font-size="10" fill="#000">Arkaden (6.0m)</text>

  <!-- Zone 2: Hauptgebäude -->
  <rect x="150" y="140" width="310" height="190" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <text x="155" y="155" font-family="Arial" font-size="10" fill="#000">Hauptgebäude (30.0m)</text>

  <!-- Zone 3: Kuppel (zentral) -->
  <circle cx="305" cy="235" r="50" fill="url(#copper)" stroke="#333" stroke-width="2"/>
  <text x="270" y="240" font-family="Arial" font-size="10" fill="#000">Kuppel (64.0m)</text>

  <!-- Fassadenlängen -->
  <!-- Nord -->
  <line x1="120" y1="100" x2="490" y2="100" stroke="#000" stroke-width="1"/>
  <text x="300" y="95" font-family="Arial" font-size="9" text-anchor="middle" fill="#000">71.0m (N)</text>

  <!-- Ost -->
  <line x1="500" y1="110" x2="500" y2="360" stroke="#000" stroke-width="1"/>
  <text x="505" y="235" font-family="Arial" font-size="9" text-anchor="middle" fill="#000" transform="rotate(90, 505, 235)">80.2m (O)</text>

  <!-- Süd -->
  <line x1="120" y1="370" x2="490" y2="370" stroke="#000" stroke-width="1"/>
  <text x="300" y="385" font-family="Arial" font-size="9" text-anchor="middle" fill="#000">71.0m (S)</text>

  <!-- West -->
  <line x1="110" y1="110" x2="110" y2="360" stroke="#000" stroke-width="1"/>
  <text x="105" y="235" font-family="Arial" font-size="9" text-anchor="middle" fill="#000" transform="rotate(-90, 105, 235)">80.2m (W)</text>

  <!-- Gerüst-Zugänge -->
  <!-- Z1 - Nord 93% -->
  <circle cx="456" cy="110" r="4" fill="#CC0000"/>
  <text x="460" y="108" font-family="Arial" font-size="8" fill="#CC0000">Z1</text>

  <!-- Z2 - Nord 7% -->
  <circle cx="145" cy="110" r="4" fill="#CC0000"/>
  <text x="149" y="108" font-family="Arial" font-size="8" fill="#CC0000">Z2</text>

  <!-- Z3 - Ost 42% -->
  <circle cx="490" cy="215" r="4" fill="#CC0000"/>
  <text x="494" y="218" font-family="Arial" font-size="8" fill="#CC0000">Z3</text>

  <!-- Z4 - Ost 3% -->
  <circle cx="490" cy="118" r="4" fill="#CC0000"/>
  <text x="494" y="121" font-family="Arial" font-size="8" fill="#CC0000">Z4</text>

  <!-- Z5 - Süd 47% -->
  <circle cx="287" cy="360" r="4" fill="#CC0000"/>
  <text x="291" y="363" font-family="Arial" font-size="8" fill="#CC0000">Z5</text>

  <!-- Z6 - West 51% -->
  <circle cx="120" cy="238" r="4" fill="#CC0000"/>
  <text x="124" y="241" font-family="Arial" font-size="8" fill="#CC0000">Z6</text>

  <!-- Nordpfeil -->
  <g transform="translate(580, 120)">
    <path d="M0,20 L-8,5 L-3,5 L-3,-15 L3,-15 L3,5 L8,5 Z" fill="#000"/>
    <text x="0" y="35" font-family="Arial" font-size="10" text-anchor="middle" fill="#000">N</text>
  </g>

  <!-- Maßstab -->
  <g transform="translate(550, 380)">
    <line x1="0" y1="0" x2="50" y2="0" stroke="#000" stroke-width="2"/>
    <line x1="0" y1="-3" x2="0" y2="3" stroke="#000" stroke-width="1"/>
    <line x1="50" y1="-3" x2="50" y2="3" stroke="#000" stroke-width="1"/>
    <text x="25" y="-8" font-family="Arial" font-size="9" text-anchor="middle" fill="#000">10m</text>
  </g>

  <!-- Legende -->
  <g transform="translate(20, 400)">
    <text x="0" y="0" font-family="Arial" font-size="12" font-weight="bold" fill="#000">Legende:</text>
    <rect x="0" y="10" width="15" height="10" fill="url(#hatch)" stroke="#333"/>
    <text x="20" y="19" font-family="Arial" font-size="10" fill="#000">Gebäudewände</text>
    <circle cx="7" cy="35" r="3" fill="#CC0000"/>
    <text x="20" y="39" font-family="Arial" font-size="10" fill="#000">Gerüst-Zugänge</text>
    <circle cx="7" cy="50" r="8" fill="url(#copper)" stroke="#333"/>
    <text x="20" y="54" font-family="Arial" font-size="10" fill="#000">Kuppel</text>
    <rect x="0" y="60" width="15" height="10" fill="none" stroke="#0066CC" stroke-dasharray="2,2"/>
    <text x="20" y="69" font-family="Arial" font-size="10" fill="#000">Gerüstzone</text>
  </g>

  <!-- Zusatzinfos -->
  <text x="520" y="450" font-family="Arial" font-size="8" fill="#666">Grundfläche: 3697 m²</text>
  <text x="520" y="460" font-family="Arial" font-size="8" fill="#666">Umfang: 310.0 m</text>
  <text x="520" y="470" font-family="Arial" font-size="8" fill="#666">Komplexität: COMPLEX</text>
</svg>
```


--------------------------------------------------------------------------------
## ANSICHT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Fassadenansicht (Elevation)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Bundesplatz 3 3011 Bern
- **EGID:** 2242547
- **Koordinaten (LV95):** E 600423, N 199521
- **Gebaeudename:** Bundeshaus
- **Gebaeudetyp:** Parlamentsgebaeude
- **Baustil:** Neorenaissance / Historismus
- **Baujahr:** 1902
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 53.2 m
- **Firsthoehe:** 62.6 m
- **Geschosse:** -
- **Grundflaeche:** 3697 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 26 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 80.2m × 71.0m
- **Umfang:** 310.0 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 543.1 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 543.1 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** kuppel
- **Dachneigung:** 15°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Arkaden | arkade | 6.0m | 6.0m | 6.0m | Standard |
| Hauptgebäude | hauptgebaeude | 25.0m | 30.0m | 30.0m | Standard |
| Kuppel | kuppel | 30.0m | 64.0m | 64.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Arkaden): **6.0m**
- Zone 2 (Hauptgebäude): **30.0m**
- Zone 3 (Kuppel): **64.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

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

- **Laengste Fassade:** 27.0 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

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
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenraeume sichtbar!
- **Schraffur:** url(#hatch) fuer alle Fassadenflaechen
- **Terrain-Linie:** bei +/-0.00 = 543.1 m ue.M.
- **Geruest:** VOR der Fassade (Staender blau, Belaege braun)
- **Hoehenskala:** Links (+/-0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: ansicht

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Arkaden' (6.0m) deutlich unter API-Traufhoehe (53.2m) - Zone-Daten pruefen!
- Zone 'Hauptgebäude' (30.0m) deutlich unter API-Traufhoehe (53.2m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## ANSICHT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
    
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
    
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>
  
  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>
  
  <!-- Terrain -->
  <rect x="0" y="400" width="700" height="80" fill="url(#ground)" stroke="#333" stroke-width="1"/>
  
  <!-- Arkaden (Zone 1: 6.0m) -->
  <rect x="120" y="340" width="350" height="60" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
  
  <!-- Arkaden-Bögen -->
  <path d="M135,400 A10,10 0 0,0 155,400 M170,400 A10,10 0 0,0 190,400 M205,400 A10,10 0 0,0 225,400 M240,400 A10,10 0 0,0 260,400 M275,400 A10,10 0 0,0 295,400 M310,400 A10,10 0 0,0 330,400 M345,400 A10,10 0 0,0 365,400 M380,400 A10,10 0 0,0 400,400 M415,400 A10,10 0 0,0 435,400 M450,400 A10,10 0 0,0 470,400" stroke="#000" stroke-width="1" fill="none"/>
  
  <!-- Hauptgebäude (Zone 2: 30.0m) -->
  <rect x="150" y="100" width="290" height="240" fill="url(#hatch)" stroke="#000" stroke-width="2"/>
  
  <!-- Fensterreihen Hauptgebäude -->
  <g stroke="#000" stroke-width="1" fill="none">
    <!-- 1. Obergeschoss -->
    <rect x="165" y="115" width="15" height="20"/>
    <rect x="190" y="115" width="15" height="20"/>
    <rect x="215" y="115" width="15" height="20"/>
    <rect x="240" y="115" width="15" height="20"/>
    <rect x="265" y="115" width="15" height="20"/>
    <rect x="290" y="115" width="15" height="20"/>
    <rect x="315" y="115" width="15" height="20"/>
    <rect x="340" y="115" width="15" height="20"/>
    <rect x="365" y="115" width="15" height="20"/>
    <rect x="390" y="115" width="15" height="20"/>
    <rect x="415" y="115" width="15" height="20"/>
    
    <!-- 2. Obergeschoss -->
    <rect x="165" y="150" width="15" height="20"/>
    <rect x="190" y="150" width="15" height="20"/>
    <rect x="215" y="150" width="15" height="20"/>
    <rect x="240" y="150" width="15" height="20"/>
    <rect x="265" y="150" width="15" height="20"/>
    <rect x="290" y="150" width="15" height="20"/>
    <rect x="315" y="150" width="15" height="20"/>
    <rect x="340" y="150" width="15" height="20"/>
    <rect x="365" y="150" width="15" height="20"/>
    <rect x="390" y="150" width="15" height="20"/>
    <rect x="415" y="150" width="15" height="20"/>
    
    <!-- 3. Obergeschoss -->
    <rect x="165" y="185" width="15" height="20"/>
    <rect x="190" y="185" width="15" height="20"/>
    <rect x="215" y="185" width="15" height="20"/>
    <rect x="240" y="185" width="15" height="20"/>
    <rect x="265" y="185" width="15" height="20"/>
    <rect x="290" y="185" width="15" height="20"/>
    <rect x="315" y="185" width="15" height="20"/>
    <rect x="340" y="185" width="15" height="20"/>
    <rect x="365" y="185" width="15" height="20"/>
    <rect x="390" y="185" width="15" height="20"/>
    <rect x="415" y="185" width="15" height="20"/>
    
    <!-- Erdgeschoss große Fenster -->
    <rect x="165" y="250" width="20" height="35"/>
    <rect x="200" y="250" width="20" height="35"/>
    <rect x="235" y="250" width="20" height="35"/>
    <rect x="270" y="250" width="20" height="35"/>
    <rect x="305" y="250" width="20" height="35"/>
    <rect x="340" y="250" width="20" height="35"/>
    <rect x="375" y="250" width="20" height="35"/>
    <rect x="410" y="250" width="20" height="35"/>
  </g>
  
  <!-- Kuppel (Zone 3: 64.0m) -->
  <path d="M 220,100 A75,75 0 0,1 370,100 L370,100 Z" fill="url(#copper)" stroke="#000" stroke-width="2"/>
  
  <!-- Kuppel-Laterne -->
  <rect x="285" y="40" width="20" height="60" fill="url(#copper)" stroke="#000" stroke-width="1"/>
  <polygon points="280,40 305,40 295,25 290,25" fill="url(#copper)" stroke="#000" stroke-width="1"/>
  
  <!-- Gerüst-Ständer -->
  <g stroke="#0066CC" stroke-width="3">
    <line x1="90" y1="420" x2="90" y2="90"/>
    <line x1="130" y1="420" x2="130" y2="90"/>
    <line x1="170" y1="420" x2="170" y2="90"/>
    <line x1="210" y1="420" x2="210" y2="90"/>
    <line x1="250" y1="420" x2="250" y2="90"/>
    <line x1="290" y1="420" x2="290" y2="90"/>
    <line x1="330" y1="420" x2="330" y2="90"/>
    <line x1="370" y1="420" x2="370" y2="90"/>
    <line x1="410" y1="420" x2="410" y2="90"/>
    <line x1="450" y1="420" x2="450" y2="90"/>
    <line x1="490" y1="420" x2="490" y2="90"/>
  </g>
  
  <!-- Gerüst-Beläge -->
  <g stroke="#8B4513" stroke-width="2" fill="#8B4513">
    <!-- 1. Lage -->
    <rect x="85" y="380" width="410" height="4"/>
    <!-- 2. Lage -->
    <rect x="85" y="340" width="410" height="4"/>
    <!-- 3. Lage -->
    <rect x="85" y="300" width="410" height="4"/>
    <!-- 4. Lage -->
    <rect x="85" y="260" width="410" height="4"/>
    <!-- 5. Lage -->
    <rect x="85" y="220" width="410" height="4"/>
    <!-- 6. Lage -->
    <rect x="85" y="180" width="410" height="4"/>
    <!-- 7. Lage -->
    <rect x="85" y="140" width="410" height="4"/>
    <!-- 8. Lage -->
    <rect x="85" y="100" width="410" height="4"/>
  </g>
  
  <!-- Verankerungen -->
  <g stroke="#CC0000" stroke-width="1" stroke-dasharray="3,3">
    <line x1="130" y1="320" x2="150" y2="320"/>
    <line x1="170" y1="280" x2="190" y2="280"/>
    <line x1="210" y1="240" x2="230" y2="240"/>
    <line x1="250" y1="200" x2="270" y2="200"/>
    <line x1="290" y1="160" x2="310" y2="160"/>
    <line x1="330" y1="160" x2="350" y2="160"/>
    <line x1="370" y1="200" x2="390" y2="200"/>
    <line x1="410" y1="240" x2="430" y2="240"/>
    <line x1="450" y1="280" x2="470" y2="280"/>
  </g>
  
  <!-- Höhenskala -->
  <g font-family="Arial" font-size="10" fill="#000">
    <line x1="50" y1="400" x2="60" y2="400" stroke="#000" stroke-width="1"/>
    <text x="45" y="405" text-anchor="end">+/-0.00</text>
    
    <line x1="50" y1="340" x2="60" y2="340" stroke="#000" stroke-width="1"/>
    <text x="45" y="345" text-anchor="end">+6.0m</text>
    
    <line x1="50" y1="100" x2="60" y2="100" stroke="#000" stroke-width="1"/>
    <text x="45" y="105" text-anchor="end">+30.0m</text>
    
    <line x1="50" y1="25" x2="60" y2="25" stroke="#000" stroke-width="1"/>
    <text x="45" y="30" text-anchor="end">+64.0m</text>
  </g>
  
  <!-- Lagenbeschriftung -->
  <g font-family="Arial" font-size="9" fill="#0066CC">
    <text x="520" y="385" text-anchor="start">1. Lage</text>
    <text x="520" y="345" text-anchor="start">2. Lage</text>
    <text x="520" y="305" text-anchor="start">3. Lage</text>
    <text x="520" y="265" text-anchor="start">4. Lage</text>
    <text x="520" y="225" text-anchor="start">5. Lage</text>
    <text x="520" y="185" text-anchor="start">6. Lage</text>
    <text x="520" y="145" text-anchor="start">7. Lage</text>
    <text x="520" y="105" text-anchor="start">8. Lage</text>
  </g>
  
  <!-- Titel -->
  <text x="350" y="25" font-family="Arial" font-size="14" font-weight="bold" text-anchor="middle" fill="#000">
    FASSADENANSICHT - Bundeshaus Bern
  </text>
  
  <text x="350" y="45" font-family="Arial" font-size="10" text-anchor="middle" fill="#666">
    EGID: 2242547 | Bundesplatz 3, 3011 Bern | M 1:500
  </text>
</svg>
```


--------------------------------------------------------------------------------
## SCHNITT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Gebaeudeschnitt (Querschnitt)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Bundesplatz 3 3011 Bern
- **EGID:** 2242547
- **Koordinaten (LV95):** E 600423, N 199521
- **Gebaeudename:** Bundeshaus
- **Gebaeudetyp:** Parlamentsgebaeude
- **Baustil:** Neorenaissance / Historismus
- **Baujahr:** 1902
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 53.2 m
- **Firsthoehe:** 62.6 m
- **Geschosse:** -
- **Grundflaeche:** 3697 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 26 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 80.2m × 71.0m
- **Umfang:** 310.0 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 543.1 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 543.1 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** kuppel
- **Dachneigung:** 15°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Arkaden | arkade | 6.0m | 6.0m | 6.0m | Standard |
| Hauptgebäude | hauptgebaeude | 25.0m | 30.0m | 30.0m | Standard |
| Kuppel | kuppel | 30.0m | 64.0m | 64.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Arkaden): **6.0m**
- Zone 2 (Hauptgebäude): **30.0m**
- Zone 3 (Kuppel): **64.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

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

- **Laengste Fassade:** 27.0 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

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
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 3: Gebaeudeschnitt (Querschnitt)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenraeume, Konstruktion, Raumhoehen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei +/-0.00 = 543.1 m ue.M. mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Geruest:** Links und rechts (Staender + Belaege)
- **Schnittmarkierung:** A-A

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: schnitt

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Arkaden' (6.0m) deutlich unter API-Traufhoehe (53.2m) - Zone-Daten pruefen!
- Zone 'Hauptgebäude' (30.0m) deutlich unter API-Traufhoehe (53.2m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## SCHNITT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Terrain-Linie -->
  <rect x="0" y="410" width="700" height="70" fill="url(#ground)"/>
  <line x1="0" y1="410" x2="700" y2="410" stroke="#333" stroke-width="1"/>

  <!-- Arkaden (Zone 1) - Links -->
  <rect x="80" y="350" width="15" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="95" y="350" width="80" height="60" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="175" y="350" width="15" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Arkaden Rundbogen -->
  <path d="M 95 350 A 40 40 0 0 1 175 350" fill="none" stroke="#333" stroke-width="1"/>

  <!-- Arkaden (Zone 1) - Rechts -->
  <rect x="510" y="350" width="15" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="525" y="350" width="80" height="60" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="605" y="350" width="15" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Arkaden Rundbogen -->
  <path d="M 525 350 A 40 40 0 0 1 605 350" fill="none" stroke="#333" stroke-width="1"/>

  <!-- Hauptgebäude (Zone 2) -->
  <rect x="190" y="230" width="15" height="180" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="205" y="230" width="290" height="180" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="495" y="230" width="15" height="180" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Geschossdecken -->
  <line x1="205" y1="350" x2="495" y2="350" stroke="#333" stroke-width="0.5"/>
  <line x1="205" y1="320" x2="495" y2="320" stroke="#333" stroke-width="0.5"/>
  <line x1="205" y1="290" x2="495" y2="290" stroke="#333" stroke-width="0.5"/>
  <line x1="205" y1="260" x2="495" y2="260" stroke="#333" stroke-width="0.5"/>

  <!-- Kuppel (Zone 3) -->
  <path d="M 250 230 A 100 100 0 0 1 450 230 L 450 240 A 90 90 0 0 0 260 240 Z" fill="url(#copper)" stroke="#333" stroke-width="1"/>
  <circle cx="350" cy="230" r="100" fill="url(#copper)" stroke="#333" stroke-width="1"/>

  <!-- Gerüst links -->
  <g id="scaffold-left">
    <!-- Vertikale Ständer -->
    <line x1="40" y1="410" x2="40" y2="120" stroke="#0066CC" stroke-width="3"/>
    <line x1="60" y1="410" x2="60" y2="120" stroke="#0066CC" stroke-width="3"/>
    
    <!-- Horizontale Beläge -->
    <rect x="35" y="380" width="30" height="3" fill="#8B4513"/>
    <rect x="35" y="350" width="30" height="3" fill="#8B4513"/>
    <rect x="35" y="320" width="30" height="3" fill="#8B4513"/>
    <rect x="35" y="290" width="30" height="3" fill="#8B4513"/>
    <rect x="35" y="260" width="30" height="3" fill="#8B4513"/>
    <rect x="35" y="230" width="30" height="3" fill="#8B4513"/>
    <rect x="35" y="200" width="30" height="3" fill="#8B4513"/>
    <rect x="35" y="170" width="30" height="3" fill="#8B4513"/>
    <rect x="35" y="140" width="30" height="3" fill="#8B4513"/>

    <!-- Verankerungen -->
    <line x1="65" y1="350" x2="80" y2="350" stroke="#CC0000" stroke-width="1" stroke-dasharray="3,3"/>
    <line x1="65" y1="290" x2="190" y2="290" stroke="#CC0000" stroke-width="1" stroke-dasharray="3,3"/>
    <line x1="65" y1="230" x2="250" y2="230" stroke="#CC0000" stroke-width="1" stroke-dasharray="3,3"/>
  </g>

  <!-- Gerüst rechts -->
  <g id="scaffold-right">
    <!-- Vertikale Ständer -->
    <line x1="640" y1="410" x2="640" y2="120" stroke="#0066CC" stroke-width="3"/>
    <line x1="660" y1="410" x2="660" y2="120" stroke="#0066CC" stroke-width="3"/>
    
    <!-- Horizontale Beläge -->
    <rect x="635" y="380" width="30" height="3" fill="#8B4513"/>
    <rect x="635" y="350" width="30" height="3" fill="#8B4513"/>
    <rect x="635" y="320" width="30" height="3" fill="#8B4513"/>
    <rect x="635" y="290" width="30" height="3" fill="#8B4513"/>
    <rect x="635" y="260" width="30" height="3" fill="#8B4513"/>
    <rect x="635" y="230" width="30" height="3" fill="#8B4513"/>
    <rect x="635" y="200" width="30" height="3" fill="#8B4513"/>
    <rect x="635" y="170" width="30" height="3" fill="#8B4513"/>
    <rect x="635" y="140" width="30" height="3" fill="#8B4513"/>

    <!-- Verankerungen -->
    <line x1="635" y1="350" x2="620" y2="350" stroke="#CC0000" stroke-width="1" stroke-dasharray="3,3"/>
    <line x1="635" y1="290" x2="510" y2="290" stroke="#CC0000" stroke-width="1" stroke-dasharray="3,3"/>
    <line x1="635" y1="230" x2="450" y2="230" stroke="#CC0000" stroke-width="1" stroke-dasharray="3,3"/>
  </g>

  <!-- Schnittmarkierung -->
  <text x="20" y="30" font-family="Arial" font-size="14" font-weight="bold" fill="#333">A</text>
  <text x="660" y="30" font-family="Arial" font-size="14" font-weight="bold" fill="#333">A</text>
  <line x1="30" y1="30" x2="650" y2="30" stroke="#333" stroke-width="1" marker-end="url(#arrowhead)"/>

  <!-- Höhenmarkierungen -->
  <text x="10" y="415" font-family="Arial" font-size="10" fill="#666">±0.00</text>
  <text x="10" y="355" font-family="Arial" font-size="10" fill="#666">6.0m</text>
  <text x="10" y="235" font-family="Arial" font-size="10" fill="#666">30.0m</text>
  <text x="10" y="135" font-family="Arial" font-size="10" fill="#666">64.0m</text>

  <!-- Titel -->
  <text x="350" y="460" font-family="Arial" font-size="12" text-anchor="middle" fill="#333">GEBÄUDESCHNITT A-A</text>
  <text x="350" y="475" font-family="Arial" font-size="10" text-anchor="middle" fill="#666">Bundeshaus - Bundesplatz 3, 3011 Bern</text>
</svg>
```


================================================================================
# GEBÄUDE 2: Berner Muenster
================================================================================

## Adresse
Muensterplatz 1, 3011 Bern

## EGID
1230337

## Recherche-Ergebnis (aus Pipeline)

- **Gebäudename:** Berner Muenster
- **Gebäudetyp:** Reformierte Stadtkirche
- **Architekturstil:** Spaetgotik
- **Baujahr:** 1421
- **Komplexität:** complex
- **Traufhöhe:** 25.7 m
- **Firsthöhe:** 30.3 m

### Erkannte Zonen

**Zone 1: Kirchenschiff**
- Typ: hauptgebaeude
- Traufhöhe: 22.0 m
- Firsthöhe: 28.0 m
- Sonderkonstruktion: Nein

**Zone 2: Seitenkapellen**
- Typ: anbau
- Traufhöhe: 12.0 m
- Firsthöhe: 15.0 m
- Sonderkonstruktion: Nein

**Zone 3: Turm**
- Typ: turm
- Traufhöhe: 28.0 m
- Firsthöhe: 100.3 m
- Sonderkonstruktion: Ja


--------------------------------------------------------------------------------
## GRUNDRISS-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Grundriss (Draufsicht)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Münsterplatz 1 3011 Bern
- **EGID:** 1230337
- **Koordinaten (LV95):** E 600948, N 199582
- **Gebaeudename:** Berner Muenster
- **Gebaeudetyp:** Reformierte Stadtkirche
- **Baustil:** Spaetgotik
- **Baujahr:** 1421
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 25.7 m
- **Firsthoehe:** 30.3 m
- **Geschosse:** 1
- **Grundflaeche:** 2604 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 33 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 87.7m × 41.1m
- **Umfang:** 252.0 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 535.4 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 535.4 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach_mit_turm
- **Dachneigung:** 13°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Kirchenschiff | hauptgebaeude | 22.0m | 28.0m | 28.0m | Standard |
| Seitenkapellen | anbau | 12.0m | 15.0m | 15.0m | Standard |
| Turm | turm | 28.0m | 100.3m | 100.3m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Kirchenschiff): **28.0m**
- Zone 2 (Seitenkapellen): **15.0m**
- Zone 3 (Turm): **100.3m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 2.2 | NO |
| 1 | 8.8 | N |
| 2 | 6.0 | NO |
| 3 | 2.4 | SO |
| 4 | 51.8 | O |
| 5 | 4.2 | S |
| 6 | 4.9 | O |
| 7 | 2.1 | N |
| ... | (24 weitere) | ... |

- **Laengste Fassade:** 51.8 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 26% | - |
| Z2 | O | 74% | - |
| Z3 | O | 74% | - |
| Z4 | S | 12% | - |
| Z5 | W | 92% | - |
| Z6 | N | 2% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** Rechteckige Huelle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung
- **Zonen:** Farblich unterscheiden, Innenhoefe markieren

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: grundriss

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Hoehe 30.3m sehr hoch fuer 1 Geschosse (moeglicherweise Turm)
- Zone 'Seitenkapellen' (15.0m) deutlich unter API-Traufhoehe (25.7m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## GRUNDRISS-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Titel -->
  <text x="350" y="25" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#333">
    GRUNDRISS - Berner Münster
  </text>
  <text x="350" y="40" text-anchor="middle" font-family="Arial" font-size="10" fill="#666">
    Münsterplatz 1, 3011 Bern | EGID: 1230337
  </text>

  <!-- Gerüstzone (äußerer Rahmen mit 1m Abstand) -->
  <rect x="150" y="80" width="400" height="280" fill="none" stroke="#0066CC" stroke-width="2" stroke-dasharray="5,5"/>
  <text x="155" y="95" font-family="Arial" font-size="8" fill="#0066CC">Gerüstzone</text>

  <!-- Zone 1: Kirchenschiff (Hauptgebäude) -->
  <rect x="170" y="100" width="320" height="160" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <text x="330" y="185" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" fill="#333">
    Kirchenschiff
  </text>
  <text x="330" y="195" text-anchor="middle" font-family="Arial" font-size="8" fill="#666">
    H = 28.0m
  </text>

  <!-- Zone 2: Seitenkapellen (Anbauten) -->
  <rect x="170" y="260" width="120" height="80" fill="url(#hatch)" stroke="#333" stroke-width="1.5"/>
  <text x="230" y="305" text-anchor="middle" font-family="Arial" font-size="8" fill="#333">
    Seitenkapelle
  </text>
  <text x="230" y="315" text-anchor="middle" font-family="Arial" font-size="7" fill="#666">
    H = 15.0m
  </text>

  <rect x="370" y="260" width="120" height="80" fill="url(#hatch)" stroke="#333" stroke-width="1.5"/>
  <text x="430" y="305" text-anchor="middle" font-family="Arial" font-size="8" fill="#333">
    Seitenkapelle
  </text>
  <text x="430" y="315" text-anchor="middle" font-family="Arial" font-size="7" fill="#666">
    H = 15.0m
  </text>

  <!-- Zone 3: Turm -->
  <rect x="310" y="100" width="40" height="40" fill="url(#hatch)" stroke="#333" stroke-width="3"/>
  <text x="330" y="120" text-anchor="middle" font-family="Arial" font-size="8" font-weight="bold" fill="#333">
    Turm
  </text>
  <text x="330" y="130" text-anchor="middle" font-family="Arial" font-size="7" fill="#666">
    H = 100.3m
  </text>
  <text x="355" y="120" font-family="Arial" font-size="6" fill="#CC0000">
    Sonderkonstruktion
  </text>

  <!-- Gerüst-Zugänge -->
  <circle cx="470" cy="160" r="4" fill="#0066CC"/>
  <text x="475" y="165" font-family="Arial" font-size="8" fill="#0066CC">Z1</text>
  
  <circle cx="470" cy="220" r="4" fill="#0066CC"/>
  <text x="475" y="225" font-family="Arial" font-size="8" fill="#0066CC">Z2/Z3</text>

  <circle cx="250" cy="345" r="4" fill="#0066CC"/>
  <text x="255" y="350" font-family="Arial" font-size="8" fill="#0066CC">Z4</text>

  <circle cx="175" cy="110" r="4" fill="#0066CC"/>
  <text x="180" y="115" font-family="Arial" font-size="8" fill="#0066CC">Z6</text>

  <circle cx="175" cy="340" r="4" fill="#0066CC"/>
  <text x="180" y="345" font-family="Arial" font-size="8" fill="#0066CC">Z5</text>

  <!-- Fassadenlängen -->
  <!-- Ost (längste Fassade 51.8m) -->
  <line x1="490" y1="100" x2="490" y2="340" stroke="#666" stroke-width="1"/>
  <text x="495" y="220" font-family="Arial" font-size="8" fill="#666">51.8m</text>
  <text x="495" y="230" font-family="Arial" font-size="7" fill="#666">(Ost)</text>

  <!-- West -->
  <line x1="150" y1="100" x2="150" y2="340" stroke="#666" stroke-width="1"/>
  <text x="130" y="220" font-family="Arial" font-size="8" fill="#666" text-anchor="end">West</text>

  <!-- Nord -->
  <line x1="170" y1="80" x2="490" y2="80" stroke="#666" stroke-width="1"/>
  <text x="330" y="75" text-anchor="middle" font-family="Arial" font-size="8" fill="#666">Nord</text>

  <!-- Süd -->
  <line x1="170" y1="360" x2="490" y2="360" stroke="#666" stroke-width="1"/>
  <text x="330" y="375" text-anchor="middle" font-family="Arial" font-size="8" fill="#666">Süd</text>

  <!-- Nordpfeil -->
  <g transform="translate(600,100)">
    <path d="M0,0 L-5,15 L0,12 L5,15 Z" fill="#333"/>
    <text x="0" y="25" text-anchor="middle" font-family="Arial" font-size="8" fill="#333">N</text>
  </g>

  <!-- Maßstab -->
  <g transform="translate(50,400)">
    <line x1="0" y1="0" x2="50" y2="0" stroke="#333" stroke-width="2"/>
    <line x1="0" y1="-3" x2="0" y2="3" stroke="#333" stroke-width="1"/>
    <line x1="50" y1="-3" x2="50" y2="3" stroke="#333" stroke-width="1"/>
    <text x="25" y="15" text-anchor="middle" font-family="Arial" font-size="8" fill="#333">10m</text>
  </g>

  <!-- Gebäudedaten -->
  <g transform="translate(520,400)">
    <text x="0" y="0" font-family="Arial" font-size="8" fill="#666">Grundfläche: 2604 m²</text>
    <text x="0" y="12" font-family="Arial" font-size="8" fill="#666">Umfang: 252.0 m</text>
    <text x="0" y="24" font-family="Arial" font-size="8" fill="#666">Baujahr: 1421</text>
    <text x="0" y="36" font-family="Arial" font-size="8" fill="#666">Spätgotik</text>
  </g>

  <!-- Koordinaten -->
  <text x="20" y="470" font-family="Arial" font-size="8" fill="#999">
    LV95: E 600948, N 199582 | Terrain: 535.4 m ü.M.
  </text>
</svg>
```


--------------------------------------------------------------------------------
## ANSICHT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Fassadenansicht (Elevation)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Münsterplatz 1 3011 Bern
- **EGID:** 1230337
- **Koordinaten (LV95):** E 600948, N 199582
- **Gebaeudename:** Berner Muenster
- **Gebaeudetyp:** Reformierte Stadtkirche
- **Baustil:** Spaetgotik
- **Baujahr:** 1421
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 25.7 m
- **Firsthoehe:** 30.3 m
- **Geschosse:** 1
- **Grundflaeche:** 2604 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 33 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 87.7m × 41.1m
- **Umfang:** 252.0 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 535.4 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 535.4 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach_mit_turm
- **Dachneigung:** 13°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Kirchenschiff | hauptgebaeude | 22.0m | 28.0m | 28.0m | Standard |
| Seitenkapellen | anbau | 12.0m | 15.0m | 15.0m | Standard |
| Turm | turm | 28.0m | 100.3m | 100.3m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Kirchenschiff): **28.0m**
- Zone 2 (Seitenkapellen): **15.0m**
- Zone 3 (Turm): **100.3m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 2.2 | NO |
| 1 | 8.8 | N |
| 2 | 6.0 | NO |
| 3 | 2.4 | SO |
| 4 | 51.8 | O |
| 5 | 4.2 | S |
| 6 | 4.9 | O |
| 7 | 2.1 | N |
| ... | (24 weitere) | ... |

- **Laengste Fassade:** 51.8 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 26% | - |
| Z2 | O | 74% | - |
| Z3 | O | 74% | - |
| Z4 | S | 12% | - |
| Z5 | W | 92% | - |
| Z6 | N | 2% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenraeume sichtbar!
- **Schraffur:** url(#hatch) fuer alle Fassadenflaechen
- **Terrain-Linie:** bei +/-0.00 = 535.4 m ue.M.
- **Geruest:** VOR der Fassade (Staender blau, Belaege braun)
- **Hoehenskala:** Links (+/-0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: ansicht

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Hoehe 30.3m sehr hoch fuer 1 Geschosse (moeglicherweise Turm)
- Zone 'Seitenkapellen' (15.0m) deutlich unter API-Traufhoehe (25.7m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## ANSICHT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
    
    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>
    
    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
    
    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>
  
  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>
  
  <!-- Terrain-Linie bei +/-0.00 -->
  <line x1="50" y1="400" x2="650" y2="400" stroke="#666" stroke-width="2"/>
  <pattern id="ground-fill" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>
  <rect x="50" y="400" width="600" height="80" fill="url(#ground-fill)"/>
  
  <!-- Seitenkapellen Links (15.0m) -->
  <rect x="120" y="325" width="80" height="75" fill="url(#hatch)" stroke="#000" stroke-width="1"/>
  <!-- Dach Seitenkapelle Links -->
  <polygon points="115,325 125,315 195,315 205,325" fill="url(#hatch)" stroke="#000" stroke-width="1"/>
  
  <!-- Kirchenschiff Hauptgebäude (28.0m) -->
  <rect x="200" y="260" width="200" height="140" fill="url(#hatch)" stroke="#000" stroke-width="1"/>
  <!-- Satteldach Kirchenschiff -->
  <polygon points="195,260 300,230 405,260" fill="url(#hatch)" stroke="#000" stroke-width="1"/>
  
  <!-- Seitenkapellen Rechts (15.0m) -->
  <rect x="400" y="325" width="80" height="75" fill="url(#hatch)" stroke="#000" stroke-width="1"/>
  <!-- Dach Seitenkapelle Rechts -->
  <polygon points="395,325 405,315 475,315 485,325" fill="url(#hatch)" stroke="#000" stroke-width="1"/>
  
  <!-- Turm (100.3m) -->
  <rect x="270" y="50" width="60" height="210" fill="url(#hatch)" stroke="#000" stroke-width="1"/>
  <!-- Turmspitze -->
  <polygon points="270,50 300,20 330,50" fill="url(#hatch)" stroke="#000" stroke-width="1"/>
  
  <!-- Gerüst Kirchenschiff -->
  <!-- Vertikale Ständer -->
  <line x1="190" y1="260" x2="190" y2="410" stroke="#0066CC" stroke-width="3"/>
  <line x1="240" y1="260" x2="240" y2="410" stroke="#0066CC" stroke-width="3"/>
  <line x1="300" y1="260" x2="300" y2="410" stroke="#0066CC" stroke-width="3"/>
  <line x1="360" y1="260" x2="360" y2="410" stroke="#0066CC" stroke-width="3"/>
  <line x1="410" y1="260" x2="410" y2="410" stroke="#0066CC" stroke-width="3"/>
  
  <!-- Horizontale Beläge -->
  <rect x="185" y="370" width="230" height="4" fill="#8B4513"/>
  <rect x="185" y="340" width="230" height="4" fill="#8B4513"/>
  <rect x="185" y="310" width="230" height="4" fill="#8B4513"/>
  <rect x="185" y="280" width="230" height="4" fill="#8B4513"/>
  
  <!-- Gerüst Seitenkapellen -->
  <line x1="110" y1="315" x2="110" y2="410" stroke="#0066CC" stroke-width="3"/>
  <line x1="210" y1="315" x2="210" y2="410" stroke="#0066CC" stroke-width="3"/>
  <rect x="105" y="360" width="110" height="4" fill="#8B4513"/>
  
  <line x1="490" y1="315" x2="490" y2="410" stroke="#0066CC" stroke-width="3"/>
  <line x1="390" y1="315" x2="390" y2="410" stroke="#0066CC" stroke-width="3"/>
  <rect x="385" y="360" width="110" height="4" fill="#8B4513"/>
  
  <!-- Turm Sondergerüst -->
  <line x1="260" y1="50" x2="260" y2="410" stroke="#0066CC" stroke-width="3"/>
  <line x1="340" y1="50" x2="340" y2="410" stroke="#0066CC" stroke-width="3"/>
  <rect x="255" y="80" width="90" height="4" fill="#8B4513"/>
  <rect x="255" y="120" width="90" height="4" fill="#8B4513"/>
  <rect x="255" y="160" width="90" height="4" fill="#8B4513"/>
  <rect x="255" y="200" width="90" height="4" fill="#8B4513"/>
  <rect x="255" y="240" width="90" height="4" fill="#8B4513"/>
  
  <!-- Verankerungen -->
  <line x1="190" y1="300" x2="200" y2="300" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>
  <line x1="240" y1="320" x2="250" y2="320" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>
  <line x1="300" y1="280" x2="310" y2="280" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>
  <line x1="360" y1="320" x2="370" y2="320" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>
  <line x1="410" y1="300" x2="400" y2="300" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>
  
  <!-- Höhenskala Links -->
  <line x1="30" y1="400" x2="40" y2="400" stroke="#000" stroke-width="1"/>
  <text x="25" y="405" font-family="Arial" font-size="10" text-anchor="end">±0.00</text>
  
  <line x1="30" y1="325" x2="40" y2="325" stroke="#000" stroke-width="1"/>
  <text x="25" y="330" font-family="Arial" font-size="10" text-anchor="end">+15.0m</text>
  
  <line x1="30" y1="260" x2="40" y2="260" stroke="#000" stroke-width="1"/>
  <text x="25" y="265" font-family="Arial" font-size="10" text-anchor="end">+28.0m</text>
  
  <line x1="30" y1="50" x2="40" y2="50" stroke="#000" stroke-width="1"/>
  <text x="25" y="55" font-family="Arial" font-size="10" text-anchor="end">+100.3m</text>
  
  <!-- Lagenbeschriftung Rechts -->
  <text x="520" y="375" font-family="Arial" font-size="10">1. Lage</text>
  <text x="520" y="345" font-family="Arial" font-size="10">2. Lage</text>
  <text x="520" y="315" font-family="Arial" font-size="10">3. Lage</text>
  <text x="520" y="285" font-family="Arial" font-size="10">4. Lage</text>
  
  <!-- Titel -->
  <text x="350" y="30" font-family="Arial" font-size="14" font-weight="bold" text-anchor="middle">Fassadenansicht Ost - Berner Münster</text>
  <text x="350" y="45" font-family="Arial" font-size="10" text-anchor="middle">Münsterplatz 1, 3011 Bern - EGID: 1230337</text>
</svg>
```


--------------------------------------------------------------------------------
## SCHNITT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Gebaeudeschnitt (Querschnitt)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Münsterplatz 1 3011 Bern
- **EGID:** 1230337
- **Koordinaten (LV95):** E 600948, N 199582
- **Gebaeudename:** Berner Muenster
- **Gebaeudetyp:** Reformierte Stadtkirche
- **Baustil:** Spaetgotik
- **Baujahr:** 1421
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 25.7 m
- **Firsthoehe:** 30.3 m
- **Geschosse:** 1
- **Grundflaeche:** 2604 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 33 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 87.7m × 41.1m
- **Umfang:** 252.0 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 535.4 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 535.4 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach_mit_turm
- **Dachneigung:** 13°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Kirchenschiff | hauptgebaeude | 22.0m | 28.0m | 28.0m | Standard |
| Seitenkapellen | anbau | 12.0m | 15.0m | 15.0m | Standard |
| Turm | turm | 28.0m | 100.3m | 100.3m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Kirchenschiff): **28.0m**
- Zone 2 (Seitenkapellen): **15.0m**
- Zone 3 (Turm): **100.3m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 2.2 | NO |
| 1 | 8.8 | N |
| 2 | 6.0 | NO |
| 3 | 2.4 | SO |
| 4 | 51.8 | O |
| 5 | 4.2 | S |
| 6 | 4.9 | O |
| 7 | 2.1 | N |
| ... | (24 weitere) | ... |

- **Laengste Fassade:** 51.8 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 26% | - |
| Z2 | O | 74% | - |
| Z3 | O | 74% | - |
| Z4 | S | 12% | - |
| Z5 | W | 92% | - |
| Z6 | N | 2% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 3: Gebaeudeschnitt (Querschnitt)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenraeume, Konstruktion, Raumhoehen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei +/-0.00 = 535.4 m ue.M. mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Geruest:** Links und rechts (Staender + Belaege)
- **Schnittmarkierung:** A-A

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: schnitt

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Hoehe 30.3m sehr hoch fuer 1 Geschosse (moeglicherweise Turm)
- Zone 'Seitenkapellen' (15.0m) deutlich unter API-Traufhoehe (25.7m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## SCHNITT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
  </defs>
  
  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>
  
  <!-- Terrain/Boden -->
  <rect x="0" y="380" width="700" height="20" fill="url(#ground)" stroke="#333" stroke-width="1"/>
  
  <!-- Seitenkapelle links - Schnittfläche -->
  <rect x="80" y="320" width="15" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  <rect x="95" y="320" width="80" height="60" fill="#FFFFFF" stroke="#333" stroke-width="2"/>
  <rect x="175" y="320" width="15" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Kirchenschiff - Hauptgebäude -->
  <rect x="190" y="240" width="15" height="140" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  <rect x="205" y="240" width="180" height="140" fill="#FFFFFF" stroke="#333" stroke-width="2"/>
  <rect x="385" y="240" width="15" height="140" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Kirchenschiff Dach -->
  <polygon points="190,240 295,210 400,240" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Seitenkapelle rechts - Schnittfläche -->
  <rect x="400" y="320" width="15" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  <rect x="415" y="320" width="80" height="60" fill="#FFFFFF" stroke="#333" stroke-width="2"/>
  <rect x="495" y="320" width="15" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Turm -->
  <rect x="530" y="80" width="15" height="300" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  <rect x="545" y="80" width="40" height="300" fill="#FFFFFF" stroke="#333" stroke-width="2"/>
  <rect x="585" y="80" width="15" height="300" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  <polygon points="530,80 565,60 600,80" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Geschossdecken -->
  <line x1="95" y1="350" x2="175" y2="350" stroke="#666" stroke-width="1"/>
  <line x1="205" y1="300" x2="385" y2="300" stroke="#666" stroke-width="1"/>
  <line x1="415" y1="350" x2="495" y2="350" stroke="#666" stroke-width="1"/>
  <line x1="545" y1="200" x2="585" y2="200" stroke="#666" stroke-width="1"/>
  <line x1="545" y1="280" x2="585" y2="280" stroke="#666" stroke-width="1"/>
  
  <!-- Gerüst links -->
  <!-- Stehbolzen -->
  <line x1="30" y1="380" x2="30" y2="180" stroke="#0066CC" stroke-width="3"/>
  <line x1="50" y1="380" x2="50" y2="180" stroke="#0066CC" stroke-width="3"/>
  <!-- Beläge -->
  <rect x="25" y="330" width="30" height="3" fill="#8B4513"/>
  <rect x="25" y="280" width="30" height="3" fill="#8B4513"/>
  <rect x="25" y="230" width="30" height="3" fill="#8B4513"/>
  <rect x="25" y="180" width="30" height="3" fill="#8B4513"/>
  <!-- Verankerungen -->
  <line x1="55" y1="320" x2="80" y2="320" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>
  <line x1="55" y1="270" x2="80" y2="270" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>
  
  <!-- Gerüst rechts -->
  <!-- Stehbolzen -->
  <line x1="630" y1="380" x2="630" y2="50" stroke="#0066CC" stroke-width="3"/>
  <line x1="650" y1="380" x2="650" y2="50" stroke="#0066CC" stroke-width="3"/>
  <!-- Beläge -->
  <rect x="625" y="330" width="30" height="3" fill="#8B4513"/>
  <rect x="625" y="280" width="30" height="3" fill="#8B4513"/>
  <rect x="625" y="230" width="30" height="3" fill="#8B4513"/>
  <rect x="625" y="180" width="30" height="3" fill="#8B4513"/>
  <rect x="625" y="130" width="30" height="3" fill="#8B4513"/>
  <rect x="625" y="80" width="30" height="3" fill="#8B4513"/>
  <!-- Verankerungen -->
  <line x1="625" y1="320" x2="600" y2="320" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>
  <line x1="625" y1="270" x2="600" y2="270" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>
  <line x1="625" y1="150" x2="600" y2="150" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>
  
  <!-- Höhenkoten -->
  <line x1="10" y1="380" x2="15" y2="380" stroke="#333" stroke-width="1"/>
  <text x="5" y="385" font-family="Arial" font-size="10" text-anchor="end">±0.00</text>
  
  <line x1="10" y1="240" x2="15" y2="240" stroke="#333" stroke-width="1"/>
  <text x="5" y="245" font-family="Arial" font-size="10" text-anchor="end">+28.0m</text>
  
  <line x1="10" y1="80" x2="15" y2="80" stroke="#333" stroke-width="1"/>
  <text x="5" y="85" font-family="Arial" font-size="10" text-anchor="end">+100.3m</text>
  
  <!-- Schnittmarkierung -->
  <text x="350" y="30" font-family="Arial" font-size="14" text-anchor="middle" font-weight="bold">SCHNITT A-A</text>
  <text x="350" y="45" font-family="Arial" font-size="12" text-anchor="middle">Berner Münster - Querschnitt</text>
  
  <!-- Zonenbezeichnungen -->
  <text x="135" y="350" font-family="Arial" font-size="9" text-anchor="middle">Seitenkapelle</text>
  <text x="295" y="310" font-family="Arial" font-size="9" text-anchor="middle">Kirchenschiff</text>
  <text x="455" y="350" font-family="Arial" font-size="9" text-anchor="middle">Seitenkapelle</text>
  <text x="565" y="190" font-family="Arial" font-size="9" text-anchor="middle" transform="rotate(-90, 565, 190)">Turm</text>
  
  <!-- Massstab -->
  <line x1="550" y1="450" x2="600" y2="450" stroke="#333" stroke-width="2"/>
  <line x1="550" y1="445" x2="550" y2="455" stroke="#333" stroke-width="1"/>
  <line x1="600" y1="445" x2="600" y2="455" stroke="#333" stroke-width="1"/>
  <text x="575" y="440" font-family="Arial" font-size="10" text-anchor="middle">10m</text>
</svg>
```


================================================================================
# GEBÄUDE 3: St. Peter und Paul
================================================================================

## Adresse
Rathausgasse 2, 3011 Bern

## EGID
191821074

## Recherche-Ergebnis (aus Pipeline)

- **Gebäudename:** Kirche St. Peter und Paul
- **Gebäudetyp:** Christkatholische Kathedralkirche
- **Architekturstil:** Neugotik
- **Baujahr:** 1864
- **Komplexität:** complex
- **Traufhöhe:** 46.4 m
- **Firsthöhe:** 54.6 m

### Erkannte Zonen

**Zone 1: Kirchenschiff**
- Typ: hauptgebaeude
- Traufhöhe: 18.0 m
- Firsthöhe: 25.0 m
- Sonderkonstruktion: Nein

**Zone 2: Seitenschiffe**
- Typ: anbau
- Traufhöhe: 9.0 m
- Firsthöhe: 12.0 m
- Sonderkonstruktion: Nein

**Zone 3: Chor**
- Typ: anbau
- Traufhöhe: 12.0 m
- Firsthöhe: 18.0 m
- Sonderkonstruktion: Nein

**Zone 4: Westturm**
- Typ: turm
- Traufhöhe: 25.0 m
- Firsthöhe: 54.6 m
- Sonderkonstruktion: Ja


--------------------------------------------------------------------------------
## GRUNDRISS-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Grundriss (Draufsicht)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Rathausgasse 2 3011 Bern
- **EGID:** 191821074
- **Koordinaten (LV95):** E 601009, N 199736
- **Gebaeudename:** Kirche St. Peter und Paul
- **Gebaeudetyp:** Christkatholische Kathedralkirche
- **Baustil:** Neugotik
- **Baujahr:** 1864
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 46.4 m
- **Firsthoehe:** 54.6 m
- **Geschosse:** -
- **Grundflaeche:** 1099 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 47 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 48.2m × 29.1m
- **Umfang:** 168.1 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 533.5 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 533.5 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach_mit_turm
- **Dachneigung:** 29°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Kirchenschiff | hauptgebaeude | 18.0m | 25.0m | 25.0m | Standard |
| Seitenschiffe | anbau | 9.0m | 12.0m | 12.0m | Standard |
| Chor | anbau | 12.0m | 18.0m | 18.0m | Standard |
| Westturm | turm | 25.0m | 54.6m | 54.6m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Kirchenschiff): **25.0m**
- Zone 2 (Seitenschiffe): **12.0m**
- Zone 3 (Chor): **18.0m**
- Zone 4 (Westturm): **54.6m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

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

- **Laengste Fassade:** 18.4 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 12% | - |
| Z2 | SO | 18% | - |
| Z3 | N | 27% | - |
| Z4 | W | 91% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** Rechteckige Huelle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung
- **Zonen:** Farblich unterscheiden, Innenhoefe markieren

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: grundriss

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Kirchenschiff' (25.0m) deutlich unter API-Traufhoehe (46.4m) - Zone-Daten pruefen!
- Zone 'Seitenschiffe' (12.0m) deutlich unter API-Traufhoehe (46.4m) - Zone-Daten pruefen!
- Zone 'Chor' (18.0m) deutlich unter API-Traufhoehe (46.4m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## GRUNDRISS-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>

<!-- Hintergrund -->
<rect width="700" height="480" fill="#FFFFFF"/>

<!-- Titel -->
<text x="350" y="25" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#000">
  GRUNDRISS - Kirche St. Peter und Paul
</text>
<text x="350" y="45" text-anchor="middle" font-family="Arial" font-size="12" fill="#666">
  Rathausgasse 2, 3011 Bern | EGID: 191821074
</text>

<!-- Geruest-Umriss (1m Abstand) -->
<rect x="150" y="90" width="400" height="280" fill="none" stroke="#0066CC" stroke-width="2" stroke-dasharray="5,5"/>

<!-- Zone 4: Westturm (54.6m) -->
<rect x="160" y="100" width="60" height="40" fill="url(#hatch)" stroke="#000" stroke-width="2"/>
<text x="190" y="125" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" fill="#000">TURM</text>
<text x="190" y="135" text-anchor="middle" font-family="Arial" font-size="8" fill="#000">54.6m</text>

<!-- Zone 1: Kirchenschiff (25.0m) -->
<rect x="220" y="100" width="200" height="60" fill="url(#hatch)" stroke="#000" stroke-width="2"/>
<text x="320" y="125" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="#000">KIRCHENSCHIFF</text>
<text x="320" y="140" text-anchor="middle" font-family="Arial" font-size="10" fill="#000">25.0m</text>

<!-- Zone 2: Seitenschiffe links (12.0m) -->
<rect x="220" y="160" width="200" height="40" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
<text x="320" y="175" text-anchor="middle" font-family="Arial" font-size="10" fill="#000">SEITENSCHIFF</text>
<text x="320" y="185" text-anchor="middle" font-family="Arial" font-size="8" fill="#000">12.0m</text>

<!-- Zone 2: Seitenschiffe rechts (12.0m) -->
<rect x="220" y="60" width="200" height="40" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
<text x="320" y="75" text-anchor="middle" font-family="Arial" font-size="10" fill="#000">SEITENSCHIFF</text>
<text x="320" y="85" text-anchor="middle" font-family="Arial" font-size="8" fill="#000">12.0m</text>

<!-- Zone 3: Chor (18.0m) -->
<rect x="420" y="100" width="120" height="60" fill="url(#hatch)" stroke="#000" stroke-width="2"/>
<text x="480" y="125" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold" fill="#000">CHOR</text>
<text x="480" y="140" text-anchor="middle" font-family="Arial" font-size="9" fill="#000">18.0m</text>

<!-- Geruest-Staender -->
<circle cx="160" cy="100" r="3" fill="#0066CC"/>
<circle cx="220" cy="100" r="3" fill="#0066CC"/>
<circle cx="320" cy="100" r="3" fill="#0066CC"/>
<circle cx="420" cy="100" r="3" fill="#0066CC"/>
<circle cx="540" cy="100" r="3" fill="#0066CC"/>

<circle cx="160" cy="160" r="3" fill="#0066CC"/>
<circle cx="220" cy="160" r="3" fill="#0066CC"/>
<circle cx="320" cy="160" r="3" fill="#0066CC"/>
<circle cx="420" cy="160" r="3" fill="#0066CC"/>
<circle cx="540" cy="160" r="3" fill="#0066CC"/>

<circle cx="160" cy="200" r="3" fill="#0066CC"/>
<circle cx="220" cy="200" r="3" fill="#0066CC"/>
<circle cx="320" cy="200" r="3" fill="#0066CC"/>
<circle cx="420" cy="200" r="3" fill="#0066CC"/>
<circle cx="540" cy="200" r="3" fill="#0066CC"/>

<!-- Geruest-Zugaenge -->
<rect x="535" y="120" width="15" height="20" fill="#00CC00" stroke="#000" stroke-width="1"/>
<text x="547" y="132" text-anchor="middle" font-family="Arial" font-size="8" font-weight="bold" fill="#000">Z1</text>
<text x="547" y="145" text-anchor="middle" font-family="Arial" font-size="6" fill="#000">OST</text>

<rect x="500" y="195" width="20" height="15" fill="#00CC00" stroke="#000" stroke-width="1"/>
<text x="510" y="205" text-anchor="middle" font-family="Arial" font-size="8" font-weight="bold" fill="#000">Z2</text>
<text x="510" y="215" text-anchor="middle" font-family="Arial" font-size="6" fill="#000">SO</text>

<rect x="280" y="85" width="20" height="15" fill="#00CC00" stroke="#000" stroke-width="1"/>
<text x="290" y="95" text-anchor="middle" font-family="Arial" font-size="8" font-weight="bold" fill="#000">Z3</text>
<text x="290" y="105" text-anchor="middle" font-family="Arial" font-size="6" fill="#000">N</text>

<rect x="140" y="150" width="15" height="20" fill="#00CC00" stroke="#000" stroke-width="1"/>
<text x="147" y="162" text-anchor="middle" font-family="Arial" font-size="8" font-weight="bold" fill="#000">Z4</text>
<text x="147" y="175" text-anchor="middle" font-family="Arial" font-size="6" fill="#000">W</text>

<!-- Fassadenlaengen -->
<line x1="160" y1="220" x2="220" y2="220" stroke="#000" stroke-width="1"/>
<text x="190" y="235" text-anchor="middle" font-family="Arial" font-size="9" fill="#000">12.0m</text>

<line x1="220" y1="220" x2="420" y2="220" stroke="#000" stroke-width="1"/>
<text x="320" y="235" text-anchor="middle" font-family="Arial" font-size="9" fill="#000">40.0m</text>

<line x1="420" y1="220" x2="540" y2="220" stroke="#000" stroke-width="1"/>
<text x="480" y="235" text-anchor="middle" font-family="Arial" font-size="9" fill="#000">24.0m</text>

<line x1="550" y1="100" x2="550" y2="160" stroke="#000" stroke-width="1"/>
<text x="565" y="130" font-family="Arial" font-size="9" fill="#000">12.0m</text>

<!-- Nordpfeil -->
<g transform="translate(600, 120)">
  <line x1="0" y1="0" x2="0" y2="-30" stroke="#000" stroke-width="2" marker-end="url(#arrow)"/>
  <text x="10" y="-10" font-family="Arial" font-size="12" font-weight="bold" fill="#000">N</text>
</g>

<defs>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="0" refY="3" orient="auto" markerUnits="strokeWidth">
    <path d="M0,0 L0,6 L9,3 z" fill="#000"/>
  </marker>
</defs>

<!-- Massstab -->
<g transform="translate(50, 400)">
  <line x1="0" y1="0" x2="50" y2="0" stroke="#000" stroke-width="2"/>
  <line x1="0" y1="-5" x2="0" y2="5" stroke="#000" stroke-width="1"/>
  <line x1="50" y1="-5" x2="50" y2="5" stroke="#000" stroke-width="1"/>
  <text x="25" y="20" text-anchor="middle" font-family="Arial" font-size="10" fill="#000">10m</text>
</g>

<!-- Gebaeudedaten -->
<text x="50" y="320" font-family="Arial" font-size="10" font-weight="bold" fill="#000">GEBÄUDEDATEN:</text>
<text x="50" y="335" font-family="Arial" font-size="9" fill="#000">Grundfläche: 1099 m²</text>
<text x="50" y="350" font-family="Arial" font-size="9" fill="#000">Umfang: 168.1 m</text>
<text x="50" y="365" font-family="Arial" font-size="9" fill="#000">Bounding Box: 48.2m × 29.1m</text>

<!-- Legende -->
<text x="50" y="450" font-family="Arial" font-size="10" font-weight="bold" fill="#000">LEGENDE:</text>
<rect x="120" y="442" width="12" height="8" fill="url(#hatch)" stroke="#000" stroke-width="0.5"/>
<text x="140" y="449" font-family="Arial" font-size="9" fill="#000">Gebäude</text>
<circle cx="200" cy="446" r="3" fill="#0066CC"/>
<text x="210" y="449" font-family="Arial" font-size="9" fill="#000">Gerüst</text>
<rect x="250" y="442" width="12" height="8" fill="#00CC00" stroke="#000" stroke-width="0.5"/>
<text x="270" y="449" font-family="Arial" font-size="9" fill="#000">Zugang</text>

</svg>
```


--------------------------------------------------------------------------------
## ANSICHT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Fassadenansicht (Elevation)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Rathausgasse 2 3011 Bern
- **EGID:** 191821074
- **Koordinaten (LV95):** E 601009, N 199736
- **Gebaeudename:** Kirche St. Peter und Paul
- **Gebaeudetyp:** Christkatholische Kathedralkirche
- **Baustil:** Neugotik
- **Baujahr:** 1864
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 46.4 m
- **Firsthoehe:** 54.6 m
- **Geschosse:** -
- **Grundflaeche:** 1099 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 47 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 48.2m × 29.1m
- **Umfang:** 168.1 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 533.5 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 533.5 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach_mit_turm
- **Dachneigung:** 29°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Kirchenschiff | hauptgebaeude | 18.0m | 25.0m | 25.0m | Standard |
| Seitenschiffe | anbau | 9.0m | 12.0m | 12.0m | Standard |
| Chor | anbau | 12.0m | 18.0m | 18.0m | Standard |
| Westturm | turm | 25.0m | 54.6m | 54.6m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Kirchenschiff): **25.0m**
- Zone 2 (Seitenschiffe): **12.0m**
- Zone 3 (Chor): **18.0m**
- Zone 4 (Westturm): **54.6m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

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

- **Laengste Fassade:** 18.4 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 12% | - |
| Z2 | SO | 18% | - |
| Z3 | N | 27% | - |
| Z4 | W | 91% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenraeume sichtbar!
- **Schraffur:** url(#hatch) fuer alle Fassadenflaechen
- **Terrain-Linie:** bei +/-0.00 = 533.5 m ue.M.
- **Geruest:** VOR der Fassade (Staender blau, Belaege braun)
- **Hoehenskala:** Links (+/-0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: ansicht

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Kirchenschiff' (25.0m) deutlich unter API-Traufhoehe (46.4m) - Zone-Daten pruefen!
- Zone 'Seitenschiffe' (12.0m) deutlich unter API-Traufhoehe (46.4m) - Zone-Daten pruefen!
- Zone 'Chor' (18.0m) deutlich unter API-Traufhoehe (46.4m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## ANSICHT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 480">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Terrain-Linie -->
  <line x1="80" y1="400" x2="620" y2="400" stroke="#333" stroke-width="2"/>
  <rect x="80" y="400" width="540" height="80" fill="url(#ground)"/>

  <!-- Hauptkirchenschiff (25.0m) -->
  <rect x="200" y="280" width="200" height="120" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Dach Hauptschiff -->
  <polygon points="200,280 300,240 400,280" fill="url(#hatch)" stroke="#333" stroke-width="2"/>

  <!-- Seitenschiffe links (12.0m) -->
  <rect x="150" y="352" width="50" height="48" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <polygon points="150,352 175,340 200,352" fill="url(#hatch)" stroke="#333" stroke-width="2"/>

  <!-- Seitenschiffe rechts (12.0m) -->
  <rect x="400" y="352" width="50" height="48" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <polygon points="400,352 425,340 450,352" fill="url(#hatch)" stroke="#333" stroke-width="2"/>

  <!-- Chor (18.0m) -->
  <rect x="450" y="328" width="80" height="72" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <polygon points="450,328 490,308 530,328" fill="url(#hatch)" stroke="#333" stroke-width="2"/>

  <!-- Westturm (54.6m) -->
  <rect x="120" y="182" width="80" height="218" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Turmspitze -->
  <polygon points="120,182 160,120 200,182" fill="url(#hatch)" stroke="#333" stroke-width="2"/>

  <!-- Geruest Hauptfassade -->
  <!-- Vertikale Staender -->
  <line x1="185" y1="400" x2="185" y2="240" stroke="#0066CC" stroke-width="3"/>
  <line x1="215" y1="400" x2="215" y2="240" stroke="#0066CC" stroke-width="3"/>
  <line x1="285" y1="400" x2="285" y2="240" stroke="#0066CC" stroke-width="3"/>
  <line x1="315" y1="400" x2="315" y2="240" stroke="#0066CC" stroke-width="3"/>
  <line x1="385" y1="400" x2="385" y2="240" stroke="#0066CC" stroke-width="3"/>
  <line x1="415" y1="400" x2="415" y2="240" stroke="#0066CC" stroke-width="3"/>

  <!-- Horizontale Belaege -->
  <rect x="185" y="390" width="230" height="4" fill="#8B4513"/>
  <rect x="185" y="365" width="230" height="4" fill="#8B4513"/>
  <rect x="185" y="340" width="230" height="4" fill="#8B4513"/>
  <rect x="185" y="315" width="230" height="4" fill="#8B4513"/>
  <rect x="185" y="290" width="230" height="4" fill="#8B4513"/>
  <rect x="185" y="265" width="230" height="4" fill="#8B4513"/>
  <rect x="185" y="240" width="230" height="4" fill="#8B4513"/>

  <!-- Geruest Turm (Sonderkonstruktion) -->
  <!-- Vertikale Staender Turm -->
  <line x1="105" y1="400" x2="105" y2="120" stroke="#0066CC" stroke-width="4"/>
  <line x1="135" y1="400" x2="135" y2="120" stroke="#0066CC" stroke-width="4"/>
  <line x1="165" y1="400" x2="165" y2="120" stroke="#0066CC" stroke-width="4"/>
  <line x1="195" y1="400" x2="195" y2="120" stroke="#0066CC" stroke-width="4"/>
  <line x1="215" y1="400" x2="215" y2="120" stroke="#0066CC" stroke-width="4"/>

  <!-- Horizontale Belaege Turm -->
  <rect x="105" y="120" width="110" height="4" fill="#8B4513"/>
  <rect x="105" y="150" width="110" height="4" fill="#8B4513"/>
  <rect x="105" y="180" width="110" height="4" fill="#8B4513"/>
  <rect x="105" y="210" width="110" height="4" fill="#8B4513"/>
  <rect x="105" y="240" width="110" height="4" fill="#8B4513"/>
  <rect x="105" y="270" width="110" height="4" fill="#8B4513"/>
  <rect x="105" y="300" width="110" height="4" fill="#8B4513"/>
  <rect x="105" y="330" width="110" height="4" fill="#8B4513"/>
  <rect x="105" y="360" width="110" height="4" fill="#8B4513"/>
  <rect x="105" y="390" width="110" height="4" fill="#8B4513"/>

  <!-- Verankerungen -->
  <line x1="200" y1="350" x2="215" y2="350" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="300" y1="320" x2="315" y2="320" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="400" y1="350" x2="415" y2="350" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="120" y1="300" x2="105" y2="300" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="120" y1="200" x2="105" y2="200" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>

  <!-- Hoehenskala links -->
  <line x1="60" y1="120" x2="60" y2="400" stroke="#333" stroke-width="1"/>
  <line x1="55" y1="400" x2="65" y2="400" stroke="#333" stroke-width="1"/>
  <line x1="55" y1="280" x2="65" y2="280" stroke="#333" stroke-width="1"/>
  <line x1="55" y1="240" x2="65" y2="240" stroke="#333" stroke-width="1"/>
  <line x1="55" y1="120" x2="65" y2="120" stroke="#333" stroke-width="1"/>

  <text x="45" y="405" font-family="Arial, sans-serif" font-size="10" text-anchor="end" fill="#333">±0.00</text>
  <text x="45" y="285" font-family="Arial, sans-serif" font-size="10" text-anchor="end" fill="#333">+25.0m</text>
  <text x="45" y="245" font-family="Arial, sans-serif" font-size="10" text-anchor="end" fill="#333">+32.0m</text>
  <text x="45" y="125" font-family="Arial, sans-serif" font-size="10" text-anchor="end" fill="#333">+54.6m</text>

  <!-- Lagenbeschriftung rechts -->
  <text x="640" y="395" font-family="Arial, sans-serif" font-size="10" fill="#333">1. Lage</text>
  <text x="640" y="370" font-family="Arial, sans-serif" font-size="10" fill="#333">2. Lage</text>
  <text x="640" y="345" font-family="Arial, sans-serif" font-size="10" fill="#333">3. Lage</text>
  <text x="640" y="320" font-family="Arial, sans-serif" font-size="10" fill="#333">4. Lage</text>
  <text x="640" y="295" font-family="Arial, sans-serif" font-size="10" fill="#333">5. Lage</text>
  <text x="640" y="270" font-family="Arial, sans-serif" font-size="10" fill="#333">6. Lage</text>
  <text x="640" y="245" font-family="Arial, sans-serif" font-size="10" fill="#333">7. Lage</text>

  <!-- Titel -->
  <text x="350" y="30" font-family="Arial, sans-serif" font-size="16" font-weight="bold" text-anchor="middle" fill="#333">Fassadenansicht Süd - Kirche St. Peter und Paul</text>
  <text x="350" y="50" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#666">Rathausgasse 2, 3011 Bern - EGID: 191821074</text>
</svg>
```


--------------------------------------------------------------------------------
## SCHNITT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Gebaeudeschnitt (Querschnitt)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Rathausgasse 2 3011 Bern
- **EGID:** 191821074
- **Koordinaten (LV95):** E 601009, N 199736
- **Gebaeudename:** Kirche St. Peter und Paul
- **Gebaeudetyp:** Christkatholische Kathedralkirche
- **Baustil:** Neugotik
- **Baujahr:** 1864
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 46.4 m
- **Firsthoehe:** 54.6 m
- **Geschosse:** -
- **Grundflaeche:** 1099 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 47 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 48.2m × 29.1m
- **Umfang:** 168.1 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 533.5 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 533.5 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach_mit_turm
- **Dachneigung:** 29°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Kirchenschiff | hauptgebaeude | 18.0m | 25.0m | 25.0m | Standard |
| Seitenschiffe | anbau | 9.0m | 12.0m | 12.0m | Standard |
| Chor | anbau | 12.0m | 18.0m | 18.0m | Standard |
| Westturm | turm | 25.0m | 54.6m | 54.6m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Kirchenschiff): **25.0m**
- Zone 2 (Seitenschiffe): **12.0m**
- Zone 3 (Chor): **18.0m**
- Zone 4 (Westturm): **54.6m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

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

- **Laengste Fassade:** 18.4 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 12% | - |
| Z2 | SO | 18% | - |
| Z3 | N | 27% | - |
| Z4 | W | 91% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 3: Gebaeudeschnitt (Querschnitt)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenraeume, Konstruktion, Raumhoehen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei +/-0.00 = 533.5 m ue.M. mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Geruest:** Links und rechts (Staender + Belaege)
- **Schnittmarkierung:** A-A

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: schnitt

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Kirchenschiff' (25.0m) deutlich unter API-Traufhoehe (46.4m) - Zone-Daten pruefen!
- Zone 'Seitenschiffe' (12.0m) deutlich unter API-Traufhoehe (46.4m) - Zone-Daten pruefen!
- Zone 'Chor' (18.0m) deutlich unter API-Traufhoehe (46.4m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## SCHNITT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 480">
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>

<!-- Hintergrund -->
<rect width="700" height="480" fill="#FFFFFF"/>

<!-- Terrain-Linie -->
<rect x="0" y="420" width="700" height="60" fill="url(#ground)" stroke="#666" stroke-width="1"/>

<!-- Westturm (links) -->
<!-- Geschnittene Mauern -->
<rect x="120" y="70" width="15" height="350" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
<rect x="180" y="70" width="15" height="350" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
<!-- Innenraum Turm -->
<rect x="135" y="70" width="45" height="350" fill="#FFFFFF" stroke="none"/>

<!-- Seitenschiff links -->
<!-- Geschnittene Mauern -->
<rect x="195" y="290" width="15" height="130" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
<rect x="250" y="290" width="15" height="130" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
<!-- Innenraum Seitenschiff -->
<rect x="210" y="290" width="40" height="130" fill="#FFFFFF" stroke="none"/>
<!-- Dach Seitenschiff -->
<polygon points="210,290 230,270 250,290" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

<!-- Kirchenschiff (Hauptgebäude) -->
<!-- Geschnittene Mauern -->
<rect x="265" y="220" width="15" height="200" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
<rect x="420" y="220" width="15" height="200" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
<!-- Innenraum Kirchenschiff -->
<rect x="280" y="220" width="140" height="200" fill="#FFFFFF" stroke="none"/>
<!-- Dach Kirchenschiff -->
<polygon points="280,220 350,180 420,220" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

<!-- Seitenschiff rechts -->
<!-- Geschnittene Mauern -->
<rect x="435" y="290" width="15" height="130" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
<rect x="490" y="290" width="15" height="130" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
<!-- Innenraum Seitenschiff -->
<rect x="450" y="290" width="40" height="130" fill="#FFFFFF" stroke="none"/>
<!-- Dach Seitenschiff -->
<polygon points="450,290 470,270 490,290" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

<!-- Chor (rechts) -->
<!-- Geschnittene Mauern -->
<rect x="505" y="260" width="15" height="160" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
<rect x="560" y="260" width="15" height="160" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
<!-- Innenraum Chor -->
<rect x="520" y="260" width="40" height="160" fill="#FFFFFF" stroke="none"/>
<!-- Dach Chor -->
<polygon points="520,260 540,240 560,260" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

<!-- Geschossdecken -->
<line x1="135" y1="320" x2="180" y2="320" stroke="#333" stroke-width="1"/>
<line x1="135" y1="270" x2="180" y2="270" stroke="#333" stroke-width="1"/>
<line x1="135" y1="220" x2="180" y2="220" stroke="#333" stroke-width="1"/>
<line x1="135" y1="170" x2="180" y2="170" stroke="#333" stroke-width="1"/>
<line x1="135" y1="120" x2="180" y2="120" stroke="#333" stroke-width="1"/>

<!-- Gerüst links -->
<line x1="80" y1="70" x2="80" y2="420" stroke="#0066CC" stroke-width="3"/>
<line x1="100" y1="70" x2="100" y2="420" stroke="#0066CC" stroke-width="3"/>
<!-- Beläge links -->
<line x1="80" y1="120" x2="100" y2="120" stroke="#8B4513" stroke-width="4"/>
<line x1="80" y1="170" x2="100" y2="170" stroke="#8B4513" stroke-width="4"/>
<line x1="80" y1="220" x2="100" y2="220" stroke="#8B4513" stroke-width="4"/>
<line x1="80" y1="270" x2="100" y2="270" stroke="#8B4513" stroke-width="4"/>
<line x1="80" y1="320" x2="100" y2="320" stroke="#8B4513" stroke-width="4"/>
<line x1="80" y1="370" x2="100" y2="370" stroke="#8B4513" stroke-width="4"/>

<!-- Gerüst rechts -->
<line x1="600" y1="240" x2="600" y2="420" stroke="#0066CC" stroke-width="3"/>
<line x1="620" y1="240" x2="620" y2="420" stroke="#0066CC" stroke-width="3"/>
<!-- Beläge rechts -->
<line x1="600" y1="290" x2="620" y2="290" stroke="#8B4513" stroke-width="4"/>
<line x1="600" y1="340" x2="620" y2="340" stroke="#8B4513" stroke-width="4"/>
<line x1="600" y1="390" x2="620" y2="390" stroke="#8B4513" stroke-width="4"/>

<!-- Verankerungen -->
<line x1="100" y1="150" x2="120" y2="150" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
<line x1="100" y1="250" x2="120" y2="250" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
<line x1="575" y1="310" x2="600" y2="310" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>

<!-- Schnittmarkierung A-A -->
<text x="50" y="50" font-family="Arial" font-size="16" font-weight="bold" fill="#333">A</text>
<text x="630" y="50" font-family="Arial" font-size="16" font-weight="bold" fill="#333">A</text>
<line x1="60" y1="40" x2="630" y2="40" stroke="#333" stroke-width="1" marker-end="url(#arrow)"/>

<!-- Höhenangaben -->
<text x="30" y="80" font-family="Arial" font-size="10" fill="#333">+54.6m</text>
<text x="30" y="230" font-family="Arial" font-size="10" fill="#333">+25.0m</text>
<text x="30" y="300" font-family="Arial" font-size="10" fill="#333">+12.0m</text>
<text x="30" y="430" font-family="Arial" font-size="10" fill="#333">±0.00</text>

<!-- Titel -->
<text x="350" y="25" font-family="Arial" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">Gebäudeschnitt A-A</text>
<text x="350" y="460" font-family="Arial" font-size="10" text-anchor="middle" fill="#666">Kirche St. Peter und Paul, Rathausgasse 2, 3011 Bern</text>
</svg>
```


================================================================================
# GEBÄUDE 4: Einsteinhaus
================================================================================

## Adresse
Kramgasse 49, 3011 Bern

## EGID
1230393

## Recherche-Ergebnis (aus Pipeline)

- **Gebäudename:** Einsteinhaus
- **Gebäudetyp:** Museum / Wohnhaus
- **Architekturstil:** Barock
- **Baujahr:** 1720
- **Komplexität:** simple
- **Traufhöhe:** 22.3 m
- **Firsthöhe:** 26.2 m

### Erkannte Zonen

**Zone 1: Hauptgebaeude**
- Typ: hauptgebaeude
- Traufhöhe: 22.0 m
- Firsthöhe: 26.0 m
- Sonderkonstruktion: Nein


--------------------------------------------------------------------------------
## GRUNDRISS-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Grundriss (Draufsicht)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Kramgasse 49 3011 Bern
- **EGID:** 1230393
- **Koordinaten (LV95):** E 600864, N 199640
- **Gebaeudename:** Einsteinhaus
- **Gebaeudetyp:** Museum / Wohnhaus
- **Baustil:** Barock
- **Baujahr:** 1720
- **Komplexitaet:** SIMPLE

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 22.3 m
- **Firsthoehe:** 26.2 m
- **Geschosse:** 5
- **Grundflaeche:** 147 m2

### Polygon
- **Eckpunkte:** 8
- **Umfang:** 68.0 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 537.7 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 537.7 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach
- **Dachneigung:** 16°
- **First-Ausrichtung:** O-W
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Hauptgebaeude | hauptgebaeude | 22.0m | 26.0m | 26.0m | Standard |

**Hoehen-Zusammenfassung:**
- Zone 1 (Hauptgebaeude): **26.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 5.0 | O |
| 1 | 21.2 | S |
| 2 | 1.7 | O |
| 3 | 5.5 | S |
| 4 | 7.3 | W |
| 5 | 6.2 | N |
| 6 | 21.1 | N |

- **Laengste Fassade:** 21.2 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | S | 91% | - |
| Z2 | N | 19% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** Rechteckige Huelle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: grundriss

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Hoehe 26.2m sehr hoch fuer 5 Geschosse (moeglicherweise Turm)

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## GRUNDRISS-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 480">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Titel -->
  <text x="350" y="25" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold">GRUNDRISS - Einsteinhaus</text>
  <text x="350" y="45" text-anchor="middle" font-family="Arial" font-size="12">Kramgasse 49, 3011 Bern | EGID: 1230393</text>

  <!-- Geruestzone (aeussere Begrenzung) -->
  <rect x="200" y="100" width="300" height="250" fill="none" stroke="#0066CC" stroke-width="2" stroke-dasharray="5,5"/>
  <text x="350" y="95" text-anchor="middle" font-family="Arial" font-size="10" fill="#0066CC">Gerüstzone (1m Abstand)</text>

  <!-- Gebaeude-Grundriss (8 Eckpunkte) -->
  <path d="M220,120 L270,120 L270,140 L290,140 L290,260 L250,260 L250,320 L220,320 Z" 
        fill="url(#hatch)" stroke="#333" stroke-width="2"/>

  <!-- Fassaden-Beschriftungen -->
  <!-- Seite 0: 5.0m O -->
  <text x="275" y="135" font-family="Arial" font-size="9" text-anchor="middle">5.0m</text>
  <text x="285" y="135" font-family="Arial" font-size="8" fill="#666">O</text>

  <!-- Seite 1: 21.2m S -->
  <text x="255" y="275" font-family="Arial" font-size="9" text-anchor="middle">21.2m</text>
  <text x="275" y="275" font-family="Arial" font-size="8" fill="#666">S</text>

  <!-- Seite 2: 1.7m O -->
  <text x="275" y="150" font-family="Arial" font-size="9" text-anchor="middle">1.7m</text>

  <!-- Seite 3: 5.5m S -->
  <text x="270" y="205" font-family="Arial" font-size="9" text-anchor="middle">5.5m</text>

  <!-- Seite 4: 7.3m W -->
  <text x="235" y="295" font-family="Arial" font-size="9" text-anchor="middle">7.3m</text>
  <text x="225" y="295" font-family="Arial" font-size="8" fill="#666">W</text>

  <!-- Seite 5: 6.2m N -->
  <text x="235" y="110" font-family="Arial" font-size="9" text-anchor="middle">6.2m</text>

  <!-- Seite 6: 21.1m N -->
  <text x="245" y="115" font-family="Arial" font-size="9" text-anchor="middle">21.1m</text>
  <text x="265" y="115" font-family="Arial" font-size="8" fill="#666">N</text>

  <!-- Geruest-Zugaenge -->
  <!-- Z1: Süd 91% -->
  <circle cx="285" cy="250" r="4" fill="#CC0000"/>
  <text x="295" y="255" font-family="Arial" font-size="10" fill="#CC0000">Z1</text>

  <!-- Z2: Nord 19% -->
  <circle cx="235" cy="125" r="4" fill="#CC0000"/>
  <text x="245" y="130" font-family="Arial" font-size="10" fill="#CC0000">Z2</text>

  <!-- Geruest-Staender (vereinfacht) -->
  <rect x="195" y="115" width="4" height="4" fill="#0066CC"/>
  <rect x="495" y="115" width="4" height="4" fill="#0066CC"/>
  <rect x="195" y="345" width="4" height="4" fill="#0066CC"/>
  <rect x="495" y="345" width="4" height="4" fill="#0066CC"/>

  <!-- Nordpfeil -->
  <g transform="translate(550,150)">
    <path d="M0,-20 L-8,0 L-3,0 L-3,20 L3,20 L3,0 L8,0 Z" fill="#333"/>
    <text x="0" y="35" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold">N</text>
  </g>

  <!-- Massstab -->
  <g transform="translate(50,400)">
    <line x1="0" y1="0" x2="100" y2="0" stroke="#333" stroke-width="2"/>
    <line x1="0" y1="-5" x2="0" y2="5" stroke="#333" stroke-width="2"/>
    <line x1="50" y1="-3" x2="50" y2="3" stroke="#333" stroke-width="1"/>
    <line x1="100" y1="-5" x2="100" y2="5" stroke="#333" stroke-width="2"/>
    <text x="50" y="20" text-anchor="middle" font-family="Arial" font-size="10">10m</text>
  </g>

  <!-- Gebaeudedaten -->
  <g transform="translate(520,300)">
    <text x="0" y="0" font-family="Arial" font-size="11" font-weight="bold">Gebäudedaten:</text>
    <text x="0" y="15" font-family="Arial" font-size="10">Grundfläche: 147 m²</text>
    <text x="0" y="30" font-family="Arial" font-size="10">Umfang: 68.0 m</text>
    <text x="0" y="45" font-family="Arial" font-size="10">Geschosse: 5</text>
    <text x="0" y="60" font-family="Arial" font-size="10">Traufhöhe: 22.3 m</text>
    <text x="0" y="75" font-family="Arial" font-size="10">Firsthöhe: 26.2 m</text>
    <text x="0" y="90" font-family="Arial" font-size="10">Baujahr: 1720</text>
    <text x="0" y="105" font-family="Arial" font-size="10">Baustil: Barock</text>
  </g>

  <!-- Koordinaten -->
  <text x="20" y="460" font-family="Arial" font-size="9" fill="#666">LV95: E 600864, N 199640 | Höhe: 537.7 m ü.M.</text>
</svg>
```


--------------------------------------------------------------------------------
## ANSICHT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Fassadenansicht (Elevation)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Kramgasse 49 3011 Bern
- **EGID:** 1230393
- **Koordinaten (LV95):** E 600864, N 199640
- **Gebaeudename:** Einsteinhaus
- **Gebaeudetyp:** Museum / Wohnhaus
- **Baustil:** Barock
- **Baujahr:** 1720
- **Komplexitaet:** SIMPLE

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 22.3 m
- **Firsthoehe:** 26.2 m
- **Geschosse:** 5
- **Grundflaeche:** 147 m2

### Polygon
- **Eckpunkte:** 8
- **Umfang:** 68.0 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 537.7 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 537.7 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach
- **Dachneigung:** 16°
- **First-Ausrichtung:** O-W
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Hauptgebaeude | hauptgebaeude | 22.0m | 26.0m | 26.0m | Standard |

**Hoehen-Zusammenfassung:**
- Zone 1 (Hauptgebaeude): **26.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 5.0 | O |
| 1 | 21.2 | S |
| 2 | 1.7 | O |
| 3 | 5.5 | S |
| 4 | 7.3 | W |
| 5 | 6.2 | N |
| 6 | 21.1 | N |

- **Laengste Fassade:** 21.2 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | S | 91% | - |
| Z2 | N | 19% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenraeume sichtbar!
- **Schraffur:** url(#hatch) fuer alle Fassadenflaechen
- **Terrain-Linie:** bei +/-0.00 = 537.7 m ue.M.
- **Geruest:** VOR der Fassade (Staender blau, Belaege braun)
- **Hoehenskala:** Links (+/-0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: ansicht

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Hoehe 26.2m sehr hoch fuer 5 Geschosse (moeglicherweise Turm)

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## ANSICHT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Terrain-Linie -->
  <rect x="100" y="400" width="400" height="30" fill="url(#ground)" stroke="#666" stroke-width="1"/>
  <line x1="100" y1="400" x2="500" y2="400" stroke="#333" stroke-width="2"/>

  <!-- Hauptgebaeude (21.2m breit, 26.0m hoch) -->
  <rect x="150" y="140" width="300" height="260" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Satteldach (16° Neigung, First O-W) -->
  <polygon points="150,140 225,120 375,120 450,140" fill="url(#hatch)" stroke="#333" stroke-width="2"/>

  <!-- Geruest vor Fassade -->
  <!-- Vertikale Staender -->
  <line x1="130" y1="400" x2="130" y2="100" stroke="#0066CC" stroke-width="3"/>
  <line x1="200" y1="400" x2="200" y2="100" stroke="#0066CC" stroke-width="3"/>
  <line x1="270" y1="400" x2="270" y2="100" stroke="#0066CC" stroke-width="3"/>
  <line x1="340" y1="400" x2="340" y2="100" stroke="#0066CC" stroke-width="3"/>
  <line x1="410" y1="400" x2="410" y2="100" stroke="#0066CC" stroke-width="3"/>
  <line x1="470" y1="400" x2="470" y2="100" stroke="#0066CC" stroke-width="3"/>

  <!-- Horizontale Belaege -->
  <rect x="130" y="390" width="340" height="4" fill="#8B4513"/>
  <rect x="130" y="350" width="340" height="4" fill="#8B4513"/>
  <rect x="130" y="310" width="340" height="4" fill="#8B4513"/>
  <rect x="130" y="270" width="340" height="4" fill="#8B4513"/>
  <rect x="130" y="230" width="340" height="4" fill="#8B4513"/>
  <rect x="130" y="190" width="340" height="4" fill="#8B4513"/>
  <rect x="130" y="150" width="340" height="4" fill="#8B4513"/>
  <rect x="130" y="110" width="340" height="4" fill="#8B4513"/>

  <!-- Verankerungen -->
  <line x1="150" y1="370" x2="180" y2="370" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="150" y1="290" x2="180" y2="290" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="150" y1="210" x2="180" y2="210" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="420" y1="370" x2="450" y2="370" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="420" y1="290" x2="450" y2="290" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="420" y1="210" x2="450" y2="210" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>

  <!-- Zugang Z1 Süd (91% Position) -->
  <rect x="420" y="395" width="15" height="10" fill="#FFD700" stroke="#333"/>
  <text x="438" y="404" font-family="Arial" font-size="8" fill="#333">Z1</text>

  <!-- Hoehenskala links -->
  <line x1="80" y1="100" x2="80" y2="430" stroke="#333" stroke-width="1"/>
  <line x1="75" y1="400" x2="85" y2="400" stroke="#333" stroke-width="1"/>
  <line x1="75" y1="140" x2="85" y2="140" stroke="#333" stroke-width="1"/>
  <line x1="75" y1="120" x2="85" y2="120" stroke="#333" stroke-width="1"/>

  <text x="70" y="405" font-family="Arial" font-size="10" fill="#333" text-anchor="end">+/-0.00</text>
  <text x="70" y="145" font-family="Arial" font-size="10" fill="#333" text-anchor="end">+22.0</text>
  <text x="70" y="125" font-family="Arial" font-size="10" fill="#333" text-anchor="end">+26.0</text>

  <!-- Lagenbeschriftung rechts -->
  <text x="520" y="385" font-family="Arial" font-size="10" fill="#333">1. Lage</text>
  <text x="520" y="345" font-family="Arial" font-size="10" fill="#333">2. Lage</text>
  <text x="520" y="305" font-family="Arial" font-size="10" fill="#333">3. Lage</text>
  <text x="520" y="265" font-family="Arial" font-size="10" fill="#333">4. Lage</text>
  <text x="520" y="225" font-family="Arial" font-size="10" fill="#333">5. Lage</text>
  <text x="520" y="185" font-family="Arial" font-size="10" fill="#333">6. Lage</text>
  <text x="520" y="145" font-family="Arial" font-size="10" fill="#333">7. Lage</text>

  <!-- Titel -->
  <text x="300" y="30" font-family="Arial" font-size="16" font-weight="bold" fill="#333" text-anchor="middle">FASSADENANSICHT SÜD</text>
  <text x="300" y="50" font-family="Arial" font-size="12" fill="#333" text-anchor="middle">Kramgasse 49, 3011 Bern - Einsteinhaus</text>
  <text x="300" y="470" font-family="Arial" font-size="10" fill="#666" text-anchor="middle">Massstab 1:200 - Fassadenlänge: 21.2m</text>
</svg>
```


--------------------------------------------------------------------------------
## SCHNITT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Gebaeudeschnitt (Querschnitt)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Kramgasse 49 3011 Bern
- **EGID:** 1230393
- **Koordinaten (LV95):** E 600864, N 199640
- **Gebaeudename:** Einsteinhaus
- **Gebaeudetyp:** Museum / Wohnhaus
- **Baustil:** Barock
- **Baujahr:** 1720
- **Komplexitaet:** SIMPLE

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 22.3 m
- **Firsthoehe:** 26.2 m
- **Geschosse:** 5
- **Grundflaeche:** 147 m2

### Polygon
- **Eckpunkte:** 8
- **Umfang:** 68.0 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 537.7 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 537.7 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach
- **Dachneigung:** 16°
- **First-Ausrichtung:** O-W
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Hauptgebaeude | hauptgebaeude | 22.0m | 26.0m | 26.0m | Standard |

**Hoehen-Zusammenfassung:**
- Zone 1 (Hauptgebaeude): **26.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 5.0 | O |
| 1 | 21.2 | S |
| 2 | 1.7 | O |
| 3 | 5.5 | S |
| 4 | 7.3 | W |
| 5 | 6.2 | N |
| 6 | 21.1 | N |

- **Laengste Fassade:** 21.2 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | S | 91% | - |
| Z2 | N | 19% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 3: Gebaeudeschnitt (Querschnitt)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenraeume, Konstruktion, Raumhoehen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei +/-0.00 = 537.7 m ue.M. mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Geruest:** Links und rechts (Staender + Belaege)
- **Schnittmarkierung:** A-A

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: schnitt

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Hoehe 26.2m sehr hoch fuer 5 Geschosse (moeglicherweise Turm)

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## SCHNITT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Terrain-Linie -->
  <rect x="0" y="400" width="700" height="20" fill="url(#ground)" stroke="#666" stroke-width="1"/>

  <!-- Fundament -->
  <rect x="200" y="390" width="300" height="20" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Hauptgebäude - Außenwände (Schnittflächen) -->
  <!-- Linke Außenwand -->
  <rect x="200" y="180" width="20" height="220" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Rechte Außenwand -->
  <rect x="480" y="180" width="20" height="220" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Innenwände (Schnittflächen) -->
  <rect x="280" y="180" width="15" height="220" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="405" y="180" width="15" height="220" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Geschossdecken -->
  <rect x="200" y="356" width="300" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="200" y="312" width="300" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="200" y="268" width="300" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="200" y="224" width="300" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="200" y="180" width="300" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Dachkonstruktion -->
  <polygon points="200,180 350,140 500,180" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Innenräume (weiß/leer) -->
  <rect x="220" y="188" width="60" height="36" fill="#FFFFFF"/>
  <rect x="295" y="188" width="110" height="36" fill="#FFFFFF"/>
  <rect x="420" y="188" width="60" height="36" fill="#FFFFFF"/>

  <rect x="220" y="232" width="60" height="36" fill="#FFFFFF"/>
  <rect x="295" y="232" width="110" height="36" fill="#FFFFFF"/>
  <rect x="420" y="232" width="60" height="36" fill="#FFFFFF"/>

  <rect x="220" y="276" width="60" height="36" fill="#FFFFFF"/>
  <rect x="295" y="276" width="110" height="36" fill="#FFFFFF"/>
  <rect x="420" y="276" width="60" height="36" fill="#FFFFFF"/>

  <rect x="220" y="320" width="60" height="36" fill="#FFFFFF"/>
  <rect x="295" y="320" width="110" height="36" fill="#FFFFFF"/>
  <rect x="420" y="320" width="60" height="36" fill="#FFFFFF"/>

  <rect x="220" y="364" width="60" height="36" fill="#FFFFFF"/>
  <rect x="295" y="364" width="110" height="36" fill="#FFFFFF"/>
  <rect x="420" y="364" width="60" height="36" fill="#FFFFFF"/>

  <!-- Gerüst links -->
  <!-- Ständer -->
  <rect x="150" y="140" width="6" height="260" fill="#0066CC"/>
  <rect x="170" y="140" width="6" height="260" fill="#0066CC"/>

  <!-- Beläge -->
  <rect x="148" y="180" width="30" height="4" fill="#8B4513"/>
  <rect x="148" y="224" width="30" height="4" fill="#8B4513"/>
  <rect x="148" y="268" width="30" height="4" fill="#8B4513"/>
  <rect x="148" y="312" width="30" height="4" fill="#8B4513"/>
  <rect x="148" y="356" width="30" height="4" fill="#8B4513"/>

  <!-- Gerüst rechts -->
  <!-- Ständer -->
  <rect x="524" y="140" width="6" height="260" fill="#0066CC"/>
  <rect x="544" y="140" width="6" height="260" fill="#0066CC"/>

  <!-- Beläge -->
  <rect x="522" y="180" width="30" height="4" fill="#8B4513"/>
  <rect x="522" y="224" width="30" height="4" fill="#8B4513"/>
  <rect x="522" y="268" width="30" height="4" fill="#8B4513"/>
  <rect x="522" y="312" width="30" height="4" fill="#8B4513"/>
  <rect x="522" y="356" width="30" height="4" fill="#8B4513"/>

  <!-- Verankerungen -->
  <line x1="178" y1="200" x2="200" y2="200" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,4"/>
  <line x1="178" y1="244" x2="200" y2="244" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,4"/>
  <line x1="178" y1="288" x2="200" y2="288" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,4"/>
  <line x1="178" y1="332" x2="200" y2="332" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,4"/>

  <line x1="522" y1="200" x2="500" y2="200" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,4"/>
  <line x1="522" y1="244" x2="500" y2="244" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,4"/>
  <line x1="522" y1="288" x2="500" y2="288" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,4"/>
  <line x1="522" y1="332" x2="500" y2="332" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,4"/>

  <!-- Maßlinien -->
  <g stroke="#666" fill="#666" font-family="Arial" font-size="10">
    <!-- Gesamthöhe -->
    <line x1="580" y1="140" x2="580" y2="400" stroke-width="1"/>
    <line x1="575" y1="140" x2="585" y2="140" stroke-width="1"/>
    <line x1="575" y1="400" x2="585" y2="400" stroke-width="1"/>
    <text x="590" y="275" transform="rotate(90 590 275)" text-anchor="middle">26.0m</text>

    <!-- Traufhöhe -->
    <line x1="560" y1="180" x2="560" y2="400" stroke-width="1"/>
    <line x1="555" y1="180" x2="565" y2="180" stroke-width="1"/>
    <line x1="555" y1="400" x2="565" y2="400" stroke-width="1"/>
    <text x="570" y="295" transform="rotate(90 570 295)" text-anchor="middle">22.0m</text>

    <!-- Geschosshöhen -->
    <text x="120" y="290" text-anchor="middle">5. OG</text>
    <text x="120" y="334" text-anchor="middle">4. OG</text>
    <text x="120" y="378" text-anchor="middle">3. OG</text>
    <text x="120" y="422" text-anchor="middle">2. OG</text>
    <text x="120" y="466" text-anchor="middle">EG</text>
  </g>

  <!-- Schnittmarkierung -->
  <g stroke="#333" fill="#333" font-family="Arial" font-size="12" font-weight="bold">
    <circle cx="100" cy="50" r="15" fill="none" stroke-width="2"/>
    <text x="100" y="55" text-anchor="middle">A</text>
    <circle cx="600" cy="50" r="15" fill="none" stroke-width="2"/>
    <text x="600" y="55" text-anchor="middle">A</text>
    <line x1="115" y1="50" x2="585" y2="50" stroke-width="1" marker-end="url(#arrowhead)"/>
  </g>

  <!-- Titel -->
  <text x="350" y="30" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold" fill="#333">
    Gebäudeschnitt A-A - Einsteinhaus, Kramgasse 49
  </text>

  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="0" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#333"/>
    </marker>
  </defs>
</svg>
```


================================================================================
# GEBÄUDE 5: Kunstmuseum
================================================================================

## Adresse
Hodlerstrasse 8, 3011 Bern

## EGID
2247274

## Recherche-Ergebnis (aus Pipeline)

- **Gebäudename:** Kunstmuseum Bern
- **Gebäudetyp:** Museum
- **Architekturstil:** Neorenaissance / Moderne
- **Baujahr:** 1879
- **Komplexität:** complex
- **Traufhöhe:** 15.0 m
- **Firsthöhe:** 18.0 m

### Erkannte Zonen

**Zone 1: Altbau**
- Typ: hauptgebaeude
- Traufhöhe: 15.0 m
- Firsthöhe: 18.0 m
- Sonderkonstruktion: Nein

**Zone 2: Neubau (Stettler)**
- Typ: hauptgebaeude
- Traufhöhe: 12.0 m
- Firsthöhe: 15.0 m
- Sonderkonstruktion: Nein

**Zone 3: Erweiterung**
- Typ: anbau
- Traufhöhe: 8.0 m
- Firsthöhe: 10.0 m
- Sonderkonstruktion: Nein


--------------------------------------------------------------------------------
## GRUNDRISS-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Grundriss (Draufsicht)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Hodlerstrasse 8 3011 Bern
- **EGID:** 2247274
- **Koordinaten (LV95):** E 600391, N 199983
- **Gebaeudename:** Kunstmuseum Bern
- **Gebaeudetyp:** Museum
- **Baustil:** Neorenaissance / Moderne
- **Baujahr:** 1879
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 15.0 m
- **Firsthoehe:** 18.0 m
- **Geschosse:** -
- **Grundflaeche:** 1190 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 11 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 50.3m × 48.3m
- **Umfang:** 145.2 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 531.1 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 531.1 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** flachdach
- **Dachneigung:** 3°
- **First-Ausrichtung:** NO-SW
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Altbau | hauptgebaeude | 15.0m | 18.0m | 18.0m | Standard |
| Neubau (Stettler) | hauptgebaeude | 12.0m | 15.0m | 15.0m | Standard |
| Erweiterung | anbau | 8.0m | 10.0m | 10.0m | Standard |

**Hoehen-Zusammenfassung:**
- Zone 1 (Altbau): **18.0m**
- Zone 2 (Neubau (Stettler)): **15.0m**
- Zone 3 (Erweiterung): **10.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 1.1 | SO |
| 1 | 11.7 | NO |
| 2 | 2.6 | SO |
| 3 | 10.8 | NO |
| 4 | 1.7 | NW |
| 5 | 8.8 | NO |
| 6 | 36.9 | SO |
| 7 | 32.3 | SW |
| ... | (2 weitere) | ... |

- **Laengste Fassade:** 36.9 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | NO | 94% | - |
| Z2 | SO | 99% | - |
| Z3 | NW | 2% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** Rechteckige Huelle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung
- **Zonen:** Farblich unterscheiden, Innenhoefe markieren

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: grundriss

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Firsthoehe 7.9m unplausibel niedrig fuer GKAT 1060 (erwartet >= 12m)
- Hoehen-Override aktiv: swissBUILDINGS3D misst nur Nebengebaeude (6.7m/7.9m). Reale Hoehen manuell erfasst.
- Zone 'Erweiterung' (10.0m) deutlich unter API-Traufhoehe (15.0m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## GRUNDRISS-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>
  
  <!-- Titel -->
  <text x="50" y="30" font-family="Arial" font-size="16" font-weight="bold">GRUNDRISS - Kunstmuseum Bern</text>
  <text x="50" y="45" font-family="Arial" font-size="10">Hodlerstrasse 8, 3011 Bern - EGID: 2247274</text>

  <!-- Zone 1: Altbau (Hauptgebaeude) -->
  <rect x="200" y="100" width="120" height="150" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <text x="255" y="180" font-family="Arial" font-size="10" text-anchor="middle" fill="#000">Altbau</text>
  <text x="255" y="195" font-family="Arial" font-size="8" text-anchor="middle" fill="#666">H: 18.0m</text>

  <!-- Zone 2: Neubau (Stettler) -->
  <rect x="320" y="120" width="100" height="110" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <text x="370" y="175" font-family="Arial" font-size="10" text-anchor="middle" fill="#000">Neubau</text>
  <text x="370" y="190" font-family="Arial" font-size="8" text-anchor="middle" fill="#666">H: 15.0m</text>

  <!-- Zone 3: Erweiterung (Anbau) -->
  <rect x="240" y="250" width="80" height="60" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <text x="280" y="285" font-family="Arial" font-size="10" text-anchor="middle" fill="#000">Erweiterung</text>
  <text x="280" y="300" font-family="Arial" font-size="8" text-anchor="middle" fill="#666">H: 10.0m</text>

  <!-- Geruestzone (1m Abstand) -->
  <rect x="190" y="90" width="240" height="230" fill="none" stroke="#0066CC" stroke-width="1" stroke-dasharray="5,5"/>
  <text x="195" y="85" font-family="Arial" font-size="8" fill="#0066CC">Gerüstzone</text>

  <!-- Fassadenlaengen -->
  <!-- NO Fassade -->
  <line x1="200" y1="95" x2="420" y2="95" stroke="#666" stroke-width="1"/>
  <text x="310" y="90" font-family="Arial" font-size="8" text-anchor="middle" fill="#666">Fassade NO - 36.9m</text>

  <!-- SO Fassade -->
  <line x1="425" y1="100" x2="425" y2="310" stroke="#666" stroke-width="1"/>
  <text x="435" y="205" font-family="Arial" font-size="8" fill="#666">SO - 32.3m</text>

  <!-- SW Fassade -->
  <line x1="200" y1="315" x2="420" y2="315" stroke="#666" stroke-width="1"/>
  <text x="310" y="330" font-family="Arial" font-size="8" text-anchor="middle" fill="#666">SW - 36.9m</text>

  <!-- NW Fassade -->
  <line x1="195" y1="100" x2="195" y2="310" stroke="#666" stroke-width="1"/>
  <text x="175" y="205" font-family="Arial" font-size="8" fill="#666" transform="rotate(-90, 175, 205)">NW - 32.3m</text>

  <!-- Geruest-Zugaenge -->
  <circle cx="395" cy="100" r="3" fill="#CC0000"/>
  <text x="400" y="105" font-family="Arial" font-size="8" fill="#CC0000">Z1</text>

  <circle cx="420" cy="300" r="3" fill="#CC0000"/>
  <text x="425" y="305" font-family="Arial" font-size="8" fill="#CC0000">Z2</text>

  <circle cx="200" cy="105" r="3" fill="#CC0000"/>
  <text x="175" y="110" font-family="Arial" font-size="8" fill="#CC0000">Z3</text>

  <!-- Nordpfeil -->
  <g transform="translate(600, 120)">
    <line x1="0" y1="0" x2="0" y2="-25" stroke="#333" stroke-width="2" marker-end="url(#arrow)"/>
    <text x="5" y="-10" font-family="Arial" font-size="10" fill="#333">N</text>
    <defs>
      <marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="3" orient="auto">
        <polygon points="0 0, 10 3, 0 6" fill="#333"/>
      </marker>
    </defs>
  </g>

  <!-- Massstab -->
  <g transform="translate(50, 400)">
    <line x1="0" y1="0" x2="50" y2="0" stroke="#333" stroke-width="2"/>
    <line x1="0" y1="-3" x2="0" y2="3" stroke="#333" stroke-width="1"/>
    <line x1="50" y1="-3" x2="50" y2="3" stroke="#333" stroke-width="1"/>
    <text x="25" y="15" font-family="Arial" font-size="8" text-anchor="middle">10m</text>
    <text x="25" y="-10" font-family="Arial" font-size="8" text-anchor="middle">Massstab 1:500</text>
  </g>

  <!-- Legende -->
  <g transform="translate(500, 200)">
    <text x="0" y="0" font-family="Arial" font-size="12" font-weight="bold">Legende</text>
    
    <rect x="0" y="10" width="15" height="10" fill="url(#hatch)" stroke="#333"/>
    <text x="20" y="20" font-family="Arial" font-size="9">Gebäudemauern</text>
    
    <line x1="0" y1="30" x2="15" y2="30" stroke="#0066CC" stroke-dasharray="3,3"/>
    <text x="20" y="35" font-family="Arial" font-size="9">Gerüstzone</text>
    
    <circle cx="7" cy="45" r="2" fill="#CC0000"/>
    <text x="20" y="50" font-family="Arial" font-size="9">Gerüst-Zugang</text>
    
    <text x="0" y="70" font-family="Arial" font-size="8" fill="#666">Grundfläche: 1190 m²</text>
    <text x="0" y="85" font-family="Arial" font-size="8" fill="#666">Umfang: 145.2 m</text>
    <text x="0" y="100" font-family="Arial" font-size="8" fill="#666">Terrain: 531.1 m ü.M.</text>
  </g>

  <!-- Koordinaten -->
  <text x="50" y="460" font-family="Arial" font-size="8" fill="#666">LV95: E 600391, N 199983</text>
  <text x="300" y="460" font-family="Arial" font-size="8" fill="#666">Baujahr: 1879 - Neorenaissance/Moderne</text>
</svg>
```


--------------------------------------------------------------------------------
## ANSICHT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Fassadenansicht (Elevation)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Hodlerstrasse 8 3011 Bern
- **EGID:** 2247274
- **Koordinaten (LV95):** E 600391, N 199983
- **Gebaeudename:** Kunstmuseum Bern
- **Gebaeudetyp:** Museum
- **Baustil:** Neorenaissance / Moderne
- **Baujahr:** 1879
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 15.0 m
- **Firsthoehe:** 18.0 m
- **Geschosse:** -
- **Grundflaeche:** 1190 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 11 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 50.3m × 48.3m
- **Umfang:** 145.2 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 531.1 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 531.1 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** flachdach
- **Dachneigung:** 3°
- **First-Ausrichtung:** NO-SW
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Altbau | hauptgebaeude | 15.0m | 18.0m | 18.0m | Standard |
| Neubau (Stettler) | hauptgebaeude | 12.0m | 15.0m | 15.0m | Standard |
| Erweiterung | anbau | 8.0m | 10.0m | 10.0m | Standard |

**Hoehen-Zusammenfassung:**
- Zone 1 (Altbau): **18.0m**
- Zone 2 (Neubau (Stettler)): **15.0m**
- Zone 3 (Erweiterung): **10.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 1.1 | SO |
| 1 | 11.7 | NO |
| 2 | 2.6 | SO |
| 3 | 10.8 | NO |
| 4 | 1.7 | NW |
| 5 | 8.8 | NO |
| 6 | 36.9 | SO |
| 7 | 32.3 | SW |
| ... | (2 weitere) | ... |

- **Laengste Fassade:** 36.9 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | NO | 94% | - |
| Z2 | SO | 99% | - |
| Z3 | NW | 2% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenraeume sichtbar!
- **Schraffur:** url(#hatch) fuer alle Fassadenflaechen
- **Terrain-Linie:** bei +/-0.00 = 531.1 m ue.M.
- **Geruest:** VOR der Fassade (Staender blau, Belaege braun)
- **Hoehenskala:** Links (+/-0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: ansicht

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Firsthoehe 7.9m unplausibel niedrig fuer GKAT 1060 (erwartet >= 12m)
- Hoehen-Override aktiv: swissBUILDINGS3D misst nur Nebengebaeude (6.7m/7.9m). Reale Hoehen manuell erfasst.
- Zone 'Erweiterung' (10.0m) deutlich unter API-Traufhoehe (15.0m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## ANSICHT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Terrain/Boden -->
  <rect x="80" y="400" width="600" height="80" fill="url(#ground)"/>
  
  <!-- Terrain-Linie bei +/-0.00 -->
  <line x1="80" y1="400" x2="680" y2="400" stroke="#333" stroke-width="2"/>

  <!-- Zone 3: Erweiterung (10.0m) - links -->
  <rect x="100" y="300" width="120" height="100" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Zone 2: Neubau (15.0m) - mitte -->
  <rect x="220" y="250" width="200" height="150" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Zone 1: Altbau (18.0m) - rechts (höchster Teil) -->
  <rect x="420" y="220" width="180" height="180" fill="url(#hatch)" stroke="#333" stroke-width="2"/>

  <!-- Dachlinien (Flachdach 3°) -->
  <line x1="100" y1="300" x2="220" y2="300" stroke="#333" stroke-width="1"/>
  <line x1="220" y1="250" x2="420" y2="250" stroke="#333" stroke-width="1"/>
  <line x1="420" y1="220" x2="600" y2="220" stroke="#333" stroke-width="1"/>

  <!-- Geruest Zone 3 -->
  <!-- Staender -->
  <rect x="90" y="270" width="3" height="130" fill="#0066CC"/>
  <rect x="130" y="270" width="3" height="130" fill="#0066CC"/>
  <rect x="170" y="270" width="3" height="130" fill="#0066CC"/>
  <rect x="210" y="270" width="3" height="130" fill="#0066CC"/>
  
  <!-- Belaege -->
  <rect x="90" y="340" width="123" height="4" fill="#8B4513"/>
  <rect x="90" y="320" width="123" height="4" fill="#8B4513"/>
  <rect x="90" y="300" width="123" height="4" fill="#8B4513"/>
  <rect x="90" y="280" width="123" height="4" fill="#8B4513"/>

  <!-- Geruest Zone 2 -->
  <!-- Staender -->
  <rect x="210" y="220" width="3" height="180" fill="#0066CC"/>
  <rect x="250" y="220" width="3" height="180" fill="#0066CC"/>
  <rect x="290" y="220" width="3" height="180" fill="#0066CC"/>
  <rect x="330" y="220" width="3" height="180" fill="#0066CC"/>
  <rect x="370" y="220" width="3" height="180" fill="#0066CC"/>
  <rect x="410" y="220" width="3" height="180" fill="#0066CC"/>
  
  <!-- Belaege -->
  <rect x="210" y="380" width="203" height="4" fill="#8B4513"/>
  <rect x="210" y="360" width="203" height="4" fill="#8B4513"/>
  <rect x="210" y="340" width="203" height="4" fill="#8B4513"/>
  <rect x="210" y="320" width="203" height="4" fill="#8B4513"/>
  <rect x="210" y="300" width="203" height="4" fill="#8B4513"/>
  <rect x="210" y="280" width="203" height="4" fill="#8B4513"/>
  <rect x="210" y="260" width="203" height="4" fill="#8B4513"/>
  <rect x="210" y="240" width="203" height="4" fill="#8B4513"/>

  <!-- Geruest Zone 1 -->
  <!-- Staender -->
  <rect x="410" y="190" width="3" height="210" fill="#0066CC"/>
  <rect x="450" y="190" width="3" height="210" fill="#0066CC"/>
  <rect x="490" y="190" width="3" height="210" fill="#0066CC"/>
  <rect x="530" y="190" width="3" height="210" fill="#0066CC"/>
  <rect x="570" y="190" width="3" height="210" fill="#0066CC"/>
  <rect x="610" y="190" width="3" height="210" fill="#0066CC"/>
  
  <!-- Belaege -->
  <rect x="410" y="380" width="203" height="4" fill="#8B4513"/>
  <rect x="410" y="360" width="203" height="4" fill="#8B4513"/>
  <rect x="410" y="340" width="203" height="4" fill="#8B4513"/>
  <rect x="410" y="320" width="203" height="4" fill="#8B4513"/>
  <rect x="410" y="300" width="203" height="4" fill="#8B4513"/>
  <rect x="410" y="280" width="203" height="4" fill="#8B4513"/>
  <rect x="410" y="260" width="203" height="4" fill="#8B4513"/>
  <rect x="410" y="240" width="203" height="4" fill="#8B4513"/>
  <rect x="410" y="220" width="203" height="4" fill="#8B4513"/>
  <rect x="410" y="200" width="203" height="4" fill="#8B4513"/>

  <!-- Verankerungen -->
  <line x1="220" y1="340" x2="240" y2="340" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>
  <line x1="420" y1="300" x2="440" y2="300" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>
  <line x1="420" y1="260" x2="440" y2="260" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,2"/>

  <!-- Hoehenskala links -->
  <line x1="50" y1="200" x2="50" y2="420" stroke="#333" stroke-width="1"/>
  <line x1="45" y1="400" x2="55" y2="400" stroke="#333" stroke-width="1"/>
  <line x1="45" y1="250" x2="55" y2="250" stroke="#333" stroke-width="1"/>
  <line x1="45" y1="220" x2="55" y2="220" stroke="#333" stroke-width="1"/>
  
  <text x="35" y="405" font-family="Arial" font-size="10" text-anchor="end">+/-0.00</text>
  <text x="35" y="255" font-family="Arial" font-size="10" text-anchor="end">+15.0m</text>
  <text x="35" y="225" font-family="Arial" font-size="10" text-anchor="end">+18.0m</text>

  <!-- Lagenbeschriftung rechts -->
  <text x="640" y="390" font-family="Arial" font-size="10">1. Lage</text>
  <text x="640" y="370" font-family="Arial" font-size="10">2. Lage</text>
  <text x="640" y="350" font-family="Arial" font-size="10">3. Lage</text>
  <text x="640" y="330" font-family="Arial" font-size="10">4. Lage</text>
  <text x="640" y="310" font-family="Arial" font-size="10">5. Lage</text>
  <text x="640" y="290" font-family="Arial" font-size="10">6. Lage</text>
  <text x="640" y="270" font-family="Arial" font-size="10">7. Lage</text>
  <text x="640" y="250" font-family="Arial" font-size="10">8. Lage</text>
  <text x="640" y="230" font-family="Arial" font-size="10">9. Lage</text>

  <!-- Titel -->
  <text x="350" y="30" font-family="Arial" font-size="14" font-weight="bold" text-anchor="middle">FASSADENANSICHT - Kunstmuseum Bern</text>
  <text x="350" y="45" font-family="Arial" font-size="10" text-anchor="middle">Hodlerstrasse 8, 3011 Bern - EGID: 2247274</text>
  
  <!-- Zonenbeschriftung -->
  <text x="160" y="430" font-family="Arial" font-size="9" text-anchor="middle">Erweiterung (10.0m)</text>
  <text x="320" y="430" font-family="Arial" font-size="9" text-anchor="middle">Neubau (15.0m)</text>
  <text x="510" y="430" font-family="Arial" font-size="9" text-anchor="middle">Altbau (18.0m)</text>

</svg>
```


--------------------------------------------------------------------------------
## SCHNITT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Gebaeudeschnitt (Querschnitt)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Hodlerstrasse 8 3011 Bern
- **EGID:** 2247274
- **Koordinaten (LV95):** E 600391, N 199983
- **Gebaeudename:** Kunstmuseum Bern
- **Gebaeudetyp:** Museum
- **Baustil:** Neorenaissance / Moderne
- **Baujahr:** 1879
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 15.0 m
- **Firsthoehe:** 18.0 m
- **Geschosse:** -
- **Grundflaeche:** 1190 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 11 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 50.3m × 48.3m
- **Umfang:** 145.2 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 531.1 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 531.1 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** flachdach
- **Dachneigung:** 3°
- **First-Ausrichtung:** NO-SW
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Altbau | hauptgebaeude | 15.0m | 18.0m | 18.0m | Standard |
| Neubau (Stettler) | hauptgebaeude | 12.0m | 15.0m | 15.0m | Standard |
| Erweiterung | anbau | 8.0m | 10.0m | 10.0m | Standard |

**Hoehen-Zusammenfassung:**
- Zone 1 (Altbau): **18.0m**
- Zone 2 (Neubau (Stettler)): **15.0m**
- Zone 3 (Erweiterung): **10.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 1.1 | SO |
| 1 | 11.7 | NO |
| 2 | 2.6 | SO |
| 3 | 10.8 | NO |
| 4 | 1.7 | NW |
| 5 | 8.8 | NO |
| 6 | 36.9 | SO |
| 7 | 32.3 | SW |
| ... | (2 weitere) | ... |

- **Laengste Fassade:** 36.9 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | NO | 94% | - |
| Z2 | SO | 99% | - |
| Z3 | NW | 2% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 3: Gebaeudeschnitt (Querschnitt)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenraeume, Konstruktion, Raumhoehen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei +/-0.00 = 531.1 m ue.M. mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Geruest:** Links und rechts (Staender + Belaege)
- **Schnittmarkierung:** A-A

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: schnitt

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Firsthoehe 7.9m unplausibel niedrig fuer GKAT 1060 (erwartet >= 12m)
- Hoehen-Override aktiv: swissBUILDINGS3D misst nur Nebengebaeude (6.7m/7.9m). Reale Hoehen manuell erfasst.
- Zone 'Erweiterung' (10.0m) deutlich unter API-Traufhoehe (15.0m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## SCHNITT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Titel -->
  <text x="350" y="25" text-anchor="middle" font-size="14" font-weight="bold">GEBÄUDESCHNITT A-A</text>
  <text x="350" y="42" text-anchor="middle" font-size="11">Kunstmuseum Bern - Hodlerstrasse 8</text>

  <!-- Terrain-Linie -->
  <rect x="50" y="400" width="600" height="30" fill="url(#ground)"/>
  <line x1="50" y1="400" x2="650" y2="400" stroke="#333" stroke-width="2"/>

  <!-- Zone 1: Altbau (18.0m) -->
  <!-- Geschnittene Mauern -->
  <rect x="100" y="220" width="15" height="180" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="235" y="220" width="15" height="180" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <!-- Decken -->
  <rect x="115" y="340" width="120" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="115" y="280" width="120" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="115" y="220" width="120" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <!-- Dach -->
  <polygon points="100,220 175,200 250,220 235,220 175,205 115,220" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Zone 2: Neubau Stettler (15.0m) -->
  <!-- Geschnittene Mauern -->
  <rect x="280" y="250" width="15" height="150" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="415" y="250" width="15" height="150" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <!-- Decken -->
  <rect x="295" y="350" width="120" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="295" y="300" width="120" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="295" y="250" width="120" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Zone 3: Erweiterung (10.0m) -->
  <!-- Geschnittene Mauern -->
  <rect x="460" y="320" width="15" height="80" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="575" y="320" width="15" height="80" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <!-- Decken -->
  <rect x="475" y="360" width="100" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="475" y="320" width="100" height="8" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Geruest links -->
  <!-- Staender -->
  <rect x="40" y="180" width="8" height="220" fill="#0066CC"/>
  <rect x="52" y="180" width="8" height="220" fill="#0066CC"/>
  <rect x="64" y="180" width="8" height="220" fill="#0066CC"/>
  <rect x="76" y="180" width="8" height="220" fill="#0066CC"/>
  <!-- Belaege -->
  <rect x="35" y="190" width="50" height="6" fill="#8B4513"/>
  <rect x="35" y="220" width="50" height="6" fill="#8B4513"/>
  <rect x="35" y="250" width="50" height="6" fill="#8B4513"/>
  <rect x="35" y="280" width="50" height="6" fill="#8B4513"/>
  <rect x="35" y="310" width="50" height="6" fill="#8B4513"/>
  <rect x="35" y="340" width="50" height="6" fill="#8B4513"/>
  <rect x="35" y="370" width="50" height="6" fill="#8B4513"/>

  <!-- Geruest rechts -->
  <!-- Staender -->
  <rect x="610" y="180" width="8" height="220" fill="#0066CC"/>
  <rect x="622" y="180" width="8" height="220" fill="#0066CC"/>
  <rect x="634" y="180" width="8" height="220" fill="#0066CC"/>
  <rect x="646" y="180" width="8" height="220" fill="#0066CC"/>
  <!-- Belaege -->
  <rect x="605" y="190" width="50" height="6" fill="#8B4513"/>
  <rect x="605" y="220" width="50" height="6" fill="#8B4513"/>
  <rect x="605" y="250" width="50" height="6" fill="#8B4513"/>
  <rect x="605" y="280" width="50" height="6" fill="#8B4513"/>
  <rect x="605" y="310" width="50" height="6" fill="#8B4513"/>
  <rect x="605" y="340" width="50" height="6" fill="#8B4513"/>
  <rect x="605" y="370" width="50" height="6" fill="#8B4513"/>

  <!-- Verankerungen -->
  <line x1="85" y1="250" x2="100" y2="250" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="85" y1="320" x2="100" y2="320" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="590" y1="280" x2="610" y2="280" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="590" y1="350" x2="610" y2="350" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>

  <!-- Höhenangaben -->
  <line x1="25" y1="400" x2="25" y2="200" stroke="#333" stroke-width="1"/>
  <line x1="20" y1="400" x2="30" y2="400" stroke="#333" stroke-width="1"/>
  <line x1="20" y1="320" x2="30" y2="320" stroke="#333" stroke-width="1"/>
  <line x1="20" y1="250" x2="30" y2="250" stroke="#333" stroke-width="1"/>
  <line x1="20" y1="200" x2="30" y2="200" stroke="#333" stroke-width="1"/>

  <text x="15" y="405" text-anchor="middle" font-size="10">0.0</text>
  <text x="15" y="325" text-anchor="middle" font-size="10">10.0</text>
  <text x="15" y="255" text-anchor="middle" font-size="10">15.0</text>
  <text x="15" y="205" text-anchor="middle" font-size="10">18.0</text>

  <!-- Schnittmarkierung -->
  <circle cx="80" cy="450" r="15" fill="none" stroke="#333" stroke-width="2"/>
  <text x="80" y="455" text-anchor="middle" font-size="12" font-weight="bold">A</text>

  <circle cx="620" cy="450" r="15" fill="none" stroke="#333" stroke-width="2"/>
  <text x="620" y="455" text-anchor="middle" font-size="12" font-weight="bold">A</text>

  <!-- Legende -->
  <text x="550" y="80" font-size="12" font-weight="bold">LEGENDE:</text>
  <rect x="550" y="90" width="15" height="10" fill="url(#cut-hatch)"/>
  <text x="570" y="99" font-size="10">Schnittfläche</text>
  <rect x="550" y="105" width="15" height="10" fill="#0066CC"/>
  <text x="570" y="114" font-size="10">Gerüst-Ständer</text>
  <rect x="550" y="120" width="15" height="6" fill="#8B4513"/>
  <text x="570" y="128" font-size="10">Beläge</text>
  <line x1="550" y1="135" x2="565" y2="135" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
  <text x="570" y="139" font-size="10">Verankerung</text>

  <!-- Zonenbeschriftung -->
  <text x="175" y="180" text-anchor="middle" font-size="11" font-weight="bold">ALTBAU</text>
  <text x="175" y="195" text-anchor="middle" font-size="9">18.0m</text>

  <text x="350" y="240" text-anchor="middle" font-size="11" font-weight="bold">NEUBAU</text>
  <text x="350" y="255" text-anchor="middle" font-size="9">15.0m</text>

  <text x="525" y="310" text-anchor="middle" font-size="11" font-weight="bold">ERWEITERUNG</text>
  <text x="525" y="325" text-anchor="middle" font-size="9">10.0m</text>
</svg>
```


================================================================================
# GEBÄUDE 6: Kornhaus
================================================================================

## Adresse
Kornhausplatz 18, 3011 Bern

## EGID
1230631

## Recherche-Ergebnis (aus Pipeline)

- **Gebäudename:** Kornhaus
- **Gebäudetyp:** Kulturzentrum / Restaurant
- **Architekturstil:** Barock
- **Baujahr:** 1718
- **Komplexität:** complex
- **Traufhöhe:** 22.3 m
- **Firsthöhe:** 26.2 m

### Erkannte Zonen

**Zone 1: Arkaden**
- Typ: arkade
- Traufhöhe: 5.0 m
- Firsthöhe: 5.0 m
- Sonderkonstruktion: Nein

**Zone 2: Hauptbau**
- Typ: hauptgebaeude
- Traufhöhe: 18.0 m
- Firsthöhe: 25.0 m
- Sonderkonstruktion: Nein

**Zone 3: Dachreiter**
- Typ: turm
- Traufhöhe: 25.0 m
- Firsthöhe: 32.0 m
- Sonderkonstruktion: Ja


--------------------------------------------------------------------------------
## GRUNDRISS-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Grundriss (Draufsicht)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Kornhausplatz 18 3011 Bern
- **EGID:** 1230631
- **Koordinaten (LV95):** E 600646, N 199751
- **Gebaeudename:** Kornhaus
- **Gebaeudetyp:** Kulturzentrum / Restaurant
- **Baustil:** Barock
- **Baujahr:** 1718
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 22.3 m
- **Firsthoehe:** 26.2 m
- **Geschosse:** 4
- **Grundflaeche:** 1275 m2

### Polygon
- **Eckpunkte:** 10
- **Umfang:** 168.6 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 539.3 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 539.3 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** mansarddach
- **Dachneigung:** 7°
- **First-Ausrichtung:** O-W
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Arkaden | arkade | 5.0m | 5.0m | 5.0m | Standard |
| Hauptbau | hauptgebaeude | 18.0m | 25.0m | 25.0m | Standard |
| Dachreiter | turm | 25.0m | 32.0m | 32.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Arkaden): **5.0m**
- Zone 2 (Hauptbau): **25.0m**
- Zone 3 (Dachreiter): **32.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 19.3 | N |
| 1 | 3.8 | W |
| 2 | 20.7 | N |
| 3 | 3.8 | O |
| 4 | 19.2 | N |
| 5 | 21.2 | O |
| 6 | 59.3 | S |
| 7 | 19.1 | W |
| ... | (1 weitere) | ... |

- **Laengste Fassade:** 59.3 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | W | 24% | - |
| Z2 | N | 81% | - |
| Z3 | S | 29% | - |
| Z4 | W | 24% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** Rechteckige Huelle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung
- **Zonen:** Farblich unterscheiden, Innenhoefe markieren

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: grundriss

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Hoehe 26.2m sehr hoch fuer 4 Geschosse (moeglicherweise Turm)
- Zone 'Arkaden' (5.0m) deutlich unter API-Traufhoehe (22.3m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:07*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## GRUNDRISS-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Titel -->
  <text x="350" y="25" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold">GRUNDRISS - KORNHAUS BERN</text>
  <text x="350" y="45" text-anchor="middle" font-family="Arial" font-size="12">Kornhausplatz 18, 3011 Bern | EGID: 1230631</text>

  <!-- Geruestzone (1m Abstand) -->
  <rect x="180" y="80" width="340" height="280" fill="none" stroke="#0066CC" stroke-width="2" stroke-dasharray="5,5"/>
  <text x="185" y="95" font-family="Arial" font-size="10" fill="#0066CC">Gerüstzone</text>

  <!-- Zone 1: Arkaden (Westseite) -->
  <rect x="200" y="100" width="40" height="240" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <text x="220" y="225" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">ARKADEN</text>
  <text x="220" y="235" text-anchor="middle" font-family="Arial" font-size="8">5.0m</text>

  <!-- Zone 2: Hauptbau -->
  <rect x="240" y="100" width="240" height="240" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <text x="360" y="220" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold">HAUPTGEBÄUDE</text>
  <text x="360" y="235" text-anchor="middle" font-family="Arial" font-size="10">25.0m Höhe</text>

  <!-- Zone 3: Dachreiter (Zentral) -->
  <rect x="340" y="180" width="60" height="80" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  <text x="370" y="218" text-anchor="middle" font-family="Arial" font-size="8" font-weight="bold">DACHREITER</text>
  <text x="370" y="228" text-anchor="middle" font-family="Arial" font-size="7">32.0m</text>

  <!-- Fassadenbeschriftung -->
  <!-- Nord (oben) -->
  <line x1="240" y1="95" x2="480" y2="95" stroke="#666" stroke-width="1" marker-end="url(#arrow)"/>
  <text x="280" y="90" font-family="Arial" font-size="9">N: 19.3m</text>
  <text x="400" y="90" font-family="Arial" font-size="9">N: 19.2m</text>

  <!-- Ost (rechts) -->
  <line x1="485" y1="100" x2="485" y2="340" stroke="#666" stroke-width="1"/>
  <text x="490" y="180" font-family="Arial" font-size="9">O: 21.2m</text>

  <!-- Süd (unten) -->
  <line x1="200" y1="345" x2="480" y2="345" stroke="#666" stroke-width="1"/>
  <text x="340" y="360" font-family="Arial" font-size="9">S: 59.3m</text>

  <!-- West (links) -->
  <line x1="195" y1="100" x2="195" y2="340" stroke="#666" stroke-width="1"/>
  <text x="150" y="220" font-family="Arial" font-size="9" transform="rotate(-90 150 220)">W: 19.1m</text>

  <!-- Gerüst-Zugänge -->
  <circle cx="200" cy="158" r="5" fill="#CC0000"/>
  <text x="180" y="155" font-family="Arial" font-size="8">Z1</text>

  <circle cx="432" cy="95" r="5" fill="#CC0000"/>
  <text x="435" y="92" font-family="Arial" font-size="8">Z2</text>

  <circle cx="282" cy="345" r="5" fill="#CC0000"/>
  <text x="285" y="355" font-family="Arial" font-size="8">Z3</text>

  <circle cx="200" cy="158" r="5" fill="#CC0000"/>
  <text x="180" y="170" font-family="Arial" font-size="8">Z4</text>

  <!-- Nordpfeil -->
  <g transform="translate(550, 120)">
    <line x1="0" y1="20" x2="0" y2="0" stroke="#333" stroke-width="2" marker-end="url(#arrow)"/>
    <text x="5" y="15" font-family="Arial" font-size="12" font-weight="bold">N</text>
  </g>

  <!-- Maßstab -->
  <g transform="translate(50, 400)">
    <line x1="0" y1="0" x2="100" y2="0" stroke="#333" stroke-width="2"/>
    <line x1="0" y1="-5" x2="0" y2="5" stroke="#333" stroke-width="2"/>
    <line x1="100" y1="-5" x2="100" y2="5" stroke="#333" stroke-width="2"/>
    <text x="50" y="15" text-anchor="middle" font-family="Arial" font-size="10">10m</text>
  </g>

  <!-- Legende -->
  <g transform="translate(520, 200)">
    <rect x="0" y="0" width="15" height="15" fill="url(#hatch)" stroke="#333"/>
    <text x="20" y="12" font-family="Arial" font-size="9">Gebäude</text>
    
    <rect x="0" y="20" width="15" height="15" fill="url(#cut-hatch)" stroke="#333"/>
    <text x="20" y="32" font-family="Arial" font-size="9">Dachreiter</text>
    
    <line x1="0" y1="45" x2="15" y2="45" stroke="#0066CC" stroke-width="2" stroke-dasharray="3,3"/>
    <text x="20" y="49" font-family="Arial" font-size="9">Gerüstzone</text>
    
    <circle cx="7" cy="60" r="3" fill="#CC0000"/>
    <text x="20" y="65" font-family="Arial" font-size="9">Zugang</text>
  </g>

  <!-- Gebäudedaten -->
  <text x="50" y="430" font-family="Arial" font-size="10">Grundfläche: 1275 m² | Umfang: 168.6 m | Baujahr: 1718</text>
  <text x="50" y="445" font-family="Arial" font-size="10">Koordinaten: E 600646, N 199751 | Höhe: 539.3 m ü.M.</text>
  <text x="50" y="460" font-family="Arial" font-size="10">Komplexität: COMPLEX | 10 Eckpunkte | 4 Geschosse</text>

  <!-- Pfeil-Marker Definition -->
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="#666"/>
    </marker>
  </defs>
</svg>
```


--------------------------------------------------------------------------------
## ANSICHT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Fassadenansicht (Elevation)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Kornhausplatz 18 3011 Bern
- **EGID:** 1230631
- **Koordinaten (LV95):** E 600646, N 199751
- **Gebaeudename:** Kornhaus
- **Gebaeudetyp:** Kulturzentrum / Restaurant
- **Baustil:** Barock
- **Baujahr:** 1718
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 22.3 m
- **Firsthoehe:** 26.2 m
- **Geschosse:** 4
- **Grundflaeche:** 1275 m2

### Polygon
- **Eckpunkte:** 10
- **Umfang:** 168.6 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 539.3 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 539.3 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** mansarddach
- **Dachneigung:** 7°
- **First-Ausrichtung:** O-W
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Arkaden | arkade | 5.0m | 5.0m | 5.0m | Standard |
| Hauptbau | hauptgebaeude | 18.0m | 25.0m | 25.0m | Standard |
| Dachreiter | turm | 25.0m | 32.0m | 32.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Arkaden): **5.0m**
- Zone 2 (Hauptbau): **25.0m**
- Zone 3 (Dachreiter): **32.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 19.3 | N |
| 1 | 3.8 | W |
| 2 | 20.7 | N |
| 3 | 3.8 | O |
| 4 | 19.2 | N |
| 5 | 21.2 | O |
| 6 | 59.3 | S |
| 7 | 19.1 | W |
| ... | (1 weitere) | ... |

- **Laengste Fassade:** 59.3 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | W | 24% | - |
| Z2 | N | 81% | - |
| Z3 | S | 29% | - |
| Z4 | W | 24% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenraeume sichtbar!
- **Schraffur:** url(#hatch) fuer alle Fassadenflaechen
- **Terrain-Linie:** bei +/-0.00 = 539.3 m ue.M.
- **Geruest:** VOR der Fassade (Staender blau, Belaege braun)
- **Hoehenskala:** Links (+/-0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: ansicht

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Hoehe 26.2m sehr hoch fuer 4 Geschosse (moeglicherweise Turm)
- Zone 'Arkaden' (5.0m) deutlich unter API-Traufhoehe (22.3m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:08*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## ANSICHT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>
  
  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>
  
  <!-- Terrain/Boden -->
  <rect x="0" y="380" width="700" height="20" fill="url(#ground)"/>
  <line x1="80" y1="380" x2="600" y2="380" stroke="#333" stroke-width="1.5"/>
  
  <!-- Arkaden Zone (5.0m) -->
  <!-- Rundbogen -->
  <g transform="translate(150,350)">
    <rect x="0" y="0" width="80" height="30" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
    <path d="M10,30 A10,10 0 0,1 30,30 M30,30 A10,10 0 0,1 50,30 M50,30 A10,10 0 0,1 70,30" fill="none" stroke="#333" stroke-width="1"/>
  </g>
  <g transform="translate(230,350)">
    <rect x="0" y="0" width="80" height="30" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
    <path d="M10,30 A10,10 0 0,1 30,30 M30,30 A10,10 0 0,1 50,30 M50,30 A10,10 0 0,1 70,30" fill="none" stroke="#333" stroke-width="1"/>
  </g>
  <g transform="translate(310,350)">
    <rect x="0" y="0" width="80" height="30" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
    <path d="M10,30 A10,10 0 0,1 30,30 M30,30 A10,10 0 0,1 50,30 M50,30 A10,10 0 0,1 70,30" fill="none" stroke="#333" stroke-width="1"/>
  </g>
  
  <!-- Hauptgebäude (25.0m) -->
  <rect x="150" y="180" width="240" height="170" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Mansarddach -->
  <polygon points="150,180 270,150 390,180" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Dachreiter/Turm (32.0m) -->
  <rect x="240" y="100" width="60" height="80" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <polygon points="240,100 270,80 300,100" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Fenster im Hauptgebäude -->
  <rect x="170" y="200" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="200" y="200" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="230" y="200" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="260" y="200" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="290" y="200" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="320" y="200" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="350" y="200" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  
  <rect x="170" y="240" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="200" y="240" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="230" y="240" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="260" y="240" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="290" y="240" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="320" y="240" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="350" y="240" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  
  <rect x="170" y="280" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="200" y="280" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="230" y="280" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="260" y="280" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="290" y="280" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="320" y="280" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="350" y="280" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  
  <rect x="170" y="320" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="200" y="320" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="230" y="320" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="260" y="320" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="290" y="320" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="320" y="320" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <rect x="350" y="320" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  
  <!-- Gerüst-Ständer -->
  <line x1="120" y1="380" x2="120" y2="80" stroke="#0066CC" stroke-width="3"/>
  <line x1="140" y1="380" x2="140" y2="80" stroke="#0066CC" stroke-width="3"/>
  <line x1="410" y1="380" x2="410" y2="80" stroke="#0066CC" stroke-width="3"/>
  <line x1="430" y1="380" x2="430" y2="80" stroke="#0066CC" stroke-width="3"/>
  
  <!-- Gerüst-Beläge -->
  <line x1="120" y1="365" x2="430" y2="365" stroke="#8B4513" stroke-width="4"/>
  <line x1="120" y1="315" x2="430" y2="315" stroke="#8B4513" stroke-width="4"/>
  <line x1="120" y1="265" x2="430" y2="265" stroke="#8B4513" stroke-width="4"/>
  <line x1="120" y1="215" x2="430" y2="215" stroke="#8B4513" stroke-width="4"/>
  <line x1="120" y1="165" x2="430" y2="165" stroke="#8B4513" stroke-width="4"/>
  <line x1="120" y1="115" x2="430" y2="115" stroke="#8B4513" stroke-width="4"/>
  
  <!-- Verankerungen -->
  <line x1="140" y1="200" x2="150" y2="200" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,3"/>
  <line x1="140" y1="240" x2="150" y2="240" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,3"/>
  <line x1="140" y1="280" x2="150" y2="280" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,3"/>
  <line x1="140" y1="320" x2="150" y2="320" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,3"/>
  
  <!-- Höhenskala links -->
  <line x1="50" y1="380" x2="50" y2="80" stroke="#333" stroke-width="1"/>
  <line x1="45" y1="380" x2="55" y2="380" stroke="#333" stroke-width="1"/>
  <line x1="45" y1="180" x2="55" y2="180" stroke="#333" stroke-width="1"/>
  <line x1="45" y1="150" x2="55" y2="150" stroke="#333" stroke-width="1"/>
  <line x1="45" y1="80" x2="55" y2="80" stroke="#333" stroke-width="1"/>
  
  <text x="30" y="385" font-family="Arial" font-size="10" fill="#333">+/-0.00</text>
  <text x="30" y="185" font-family="Arial" font-size="10" fill="#333">+22.3</text>
  <text x="30" y="155" font-family="Arial" font-size="10" fill="#333">+26.2</text>
  <text x="30" y="85" font-family="Arial" font-size="10" fill="#333">+32.0</text>
  
  <!-- Lagenbeschriftung rechts -->
  <text x="450" y="370" font-family="Arial" font-size="10" fill="#333">1. Lage</text>
  <text x="450" y="320" font-family="Arial" font-size="10" fill="#333">2. Lage</text>
  <text x="450" y="270" font-family="Arial" font-size="10" fill="#333">3. Lage</text>
  <text x="450" y="220" font-family="Arial" font-size="10" fill="#333">4. Lage</text>
  <text x="450" y="170" font-family="Arial" font-size="10" fill="#333">5. Lage</text>
  <text x="450" y="120" font-family="Arial" font-size="10" fill="#333">6. Lage</text>
  
  <!-- Titel -->
  <text x="350" y="30" font-family="Arial" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">FASSADENANSICHT - Kornhaus Bern</text>
  <text x="350" y="45" font-family="Arial" font-size="10" text-anchor="middle" fill="#666">Kornhausplatz 18, 3011 Bern | EGID: 1230631</text>
</svg>
```


--------------------------------------------------------------------------------
## SCHNITT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Gebaeudeschnitt (Querschnitt)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Kornhausplatz 18 3011 Bern
- **EGID:** 1230631
- **Koordinaten (LV95):** E 600646, N 199751
- **Gebaeudename:** Kornhaus
- **Gebaeudetyp:** Kulturzentrum / Restaurant
- **Baustil:** Barock
- **Baujahr:** 1718
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 22.3 m
- **Firsthoehe:** 26.2 m
- **Geschosse:** 4
- **Grundflaeche:** 1275 m2

### Polygon
- **Eckpunkte:** 10
- **Umfang:** 168.6 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 539.3 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 539.3 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** mansarddach
- **Dachneigung:** 7°
- **First-Ausrichtung:** O-W
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Arkaden | arkade | 5.0m | 5.0m | 5.0m | Standard |
| Hauptbau | hauptgebaeude | 18.0m | 25.0m | 25.0m | Standard |
| Dachreiter | turm | 25.0m | 32.0m | 32.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Arkaden): **5.0m**
- Zone 2 (Hauptbau): **25.0m**
- Zone 3 (Dachreiter): **32.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 19.3 | N |
| 1 | 3.8 | W |
| 2 | 20.7 | N |
| 3 | 3.8 | O |
| 4 | 19.2 | N |
| 5 | 21.2 | O |
| 6 | 59.3 | S |
| 7 | 19.1 | W |
| ... | (1 weitere) | ... |

- **Laengste Fassade:** 59.3 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | W | 24% | - |
| Z2 | N | 81% | - |
| Z3 | S | 29% | - |
| Z4 | W | 24% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 3: Gebaeudeschnitt (Querschnitt)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenraeume, Konstruktion, Raumhoehen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei +/-0.00 = 539.3 m ue.M. mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Geruest:** Links und rechts (Staender + Belaege)
- **Schnittmarkierung:** A-A

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: schnitt

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Hoehe 26.2m sehr hoch fuer 4 Geschosse (moeglicherweise Turm)
- Zone 'Arkaden' (5.0m) deutlich unter API-Traufhoehe (22.3m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:09*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## SCHNITT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect x="0" y="0" width="700" height="480" fill="#FFFFFF"/>

  <!-- Terrain-Linie -->
  <rect x="0" y="350" width="700" height="30" fill="url(#ground)"/>
  <line x1="0" y1="350" x2="700" y2="350" stroke="#333" stroke-width="2"/>

  <!-- Zone 1: Arkaden (links) -->
  <!-- Arkadenpfeiler (geschnitten) -->
  <rect x="120" y="290" width="20" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="160" y="290" width="20" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Arkadenbogen -->
  <path d="M 140 320 Q 150 300 160 320" fill="none" stroke="#333" stroke-width="2"/>
  
  <!-- Arkaden-Dach -->
  <rect x="110" y="280" width="80" height="10" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Zone 2: Hauptgebäude -->
  <!-- Außenwände (geschnitten) -->
  <rect x="200" y="120" width="15" height="230" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="485" y="120" width="15" height="230" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Innenraum (WEISS/LEER) -->
  <rect x="215" y="120" width="270" height="230" fill="#FFFFFF" stroke="none"/>
  
  <!-- Geschossdecken -->
  <line x1="215" y1="290" x2="485" y2="290" stroke="#333" stroke-width="1"/>
  <line x1="215" y1="235" x2="485" y2="235" stroke="#333" stroke-width="1"/>
  <line x1="215" y1="180" x2="485" y2="180" stroke="#333" stroke-width="1"/>
  
  <!-- Dach (Mansarddach mit 7° Neigung) -->
  <polygon points="200,120 215,105 485,105 500,120 485,120 215,120" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Zone 3: Dachreiter/Turm -->
  <!-- Turmwände (geschnitten) -->
  <rect x="320" y="50" width="12" height="70" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="368" y="50" width="12" height="70" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Turm-Innenraum (WEISS/LEER) -->
  <rect x="332" y="50" width="36" height="70" fill="#FFFFFF" stroke="none"/>
  
  <!-- Turmspitze -->
  <polygon points="320,50 350,30 380,50" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Gerüst links -->
  <g id="geruest-links">
    <!-- Vertikale Stänger -->
    <line x1="80" y1="50" x2="80" y2="360" stroke="#0066CC" stroke-width="3"/>
    <line x1="50" y1="50" x2="50" y2="360" stroke="#0066CC" stroke-width="3"/>
    
    <!-- Horizontale Beläge alle 2m -->
    <rect x="45" y="340" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="45" y="300" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="45" y="260" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="45" y="220" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="45" y="180" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="45" y="140" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="45" y="100" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="45" y="60" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    
    <!-- Verankerungen -->
    <line x1="85" y1="300" x2="200" y2="300" stroke="#CC0000" stroke-width="1" stroke-dasharray="4,2"/>
    <line x1="85" y1="220" x2="200" y2="220" stroke="#CC0000" stroke-width="1" stroke-dasharray="4,2"/>
    <line x1="85" y1="140" x2="200" y2="140" stroke="#CC0000" stroke-width="1" stroke-dasharray="4,2"/>
  </g>

  <!-- Gerüst rechts -->
  <g id="geruest-rechts">
    <!-- Vertikale Stänger -->
    <line x1="620" y1="50" x2="620" y2="360" stroke="#0066CC" stroke-width="3"/>
    <line x1="650" y1="50" x2="650" y2="360" stroke="#0066CC" stroke-width="3"/>
    
    <!-- Horizontale Beläge alle 2m -->
    <rect x="615" y="340" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="615" y="300" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="615" y="260" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="615" y="220" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="615" y="180" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="615" y="140" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="615" y="100" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    <rect x="615" y="60" width="40" height="4" fill="#8B4513" stroke="#333" stroke-width="0.5"/>
    
    <!-- Verankerungen -->
    <line x1="615" y1="300" x2="500" y2="300" stroke="#CC0000" stroke-width="1" stroke-dasharray="4,2"/>
    <line x1="615" y1="220" x2="500" y2="220" stroke="#CC0000" stroke-width="1" stroke-dasharray="4,2"/>
    <line x1="615" y1="140" x2="500" y2="140" stroke="#CC0000" stroke-width="1" stroke-dasharray="4,2"/>
  </g>

  <!-- Höhenmarkierungen -->
  <g id="hoehen" font-family="Arial" font-size="10" fill="#333">
    <text x="20" y="355">±0.00</text>
    <text x="20" y="285">+5.0m</text>
    <text x="20" y="125">+25.0m</text>
    <text x="20" y="55">+32.0m</text>
  </g>

  <!-- Schnittmarkierung -->
  <g id="schnitt" font-family="Arial" font-size="12" fill="#333">
    <text x="30" y="30">SCHNITT A-A</text>
    <text x="30" y="45">M 1:200</text>
  </g>

  <!-- Legende -->
  <g id="legende" font-family="Arial" font-size="8" fill="#333">
    <text x="520" y="400">Kornhaus - Barock 1718</text>
    <text x="520" y="415">Zone 1: Arkaden (5.0m)</text>
    <text x="520" y="425">Zone 2: Hauptbau (25.0m)</text>
    <text x="520" y="435">Zone 3: Dachreiter (32.0m)</text>
    <text x="520" y="450">Gerüst: Standard + Sonderkonstruktion</text>
  </g>
</svg>
```


================================================================================
# GEBÄUDE 7: Hauptbahnhof
================================================================================

## Adresse
Bahnhofplatz 10, 3011 Bern

## EGID
2241912

## Recherche-Ergebnis (aus Pipeline)

- **Gebäudename:** Hauptbahnhof Bern
- **Gebäudetyp:** Bahnhof
- **Architekturstil:** Moderne / Brutalismus
- **Baujahr:** 1974
- **Komplexität:** complex
- **Traufhöhe:** 31.3 m
- **Firsthöhe:** 36.8 m

### Erkannte Zonen

**Zone 1: Baldachin**
- Typ: arkade
- Traufhöhe: 8.0 m
- Firsthöhe: 12.0 m
- Sonderkonstruktion: Nein

**Zone 2: Bahnhofshalle**
- Typ: hauptgebaeude
- Traufhöhe: 18.0 m
- Firsthöhe: 22.0 m
- Sonderkonstruktion: Nein

**Zone 3: Bueroturm**
- Typ: turm
- Traufhöhe: 30.0 m
- Firsthöhe: 40.0 m
- Sonderkonstruktion: Ja


--------------------------------------------------------------------------------
## GRUNDRISS-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Grundriss (Draufsicht)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Bahnhofplatz 10 3011 Bern
- **EGID:** 2241912
- **Koordinaten (LV95):** E 600107, N 199722
- **Gebaeudename:** Hauptbahnhof Bern
- **Gebaeudetyp:** Bahnhof
- **Baustil:** Moderne / Brutalismus
- **Baujahr:** 1974
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 31.3 m
- **Firsthoehe:** 36.8 m
- **Geschosse:** 4
- **Grundflaeche:** 7713 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 26 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 75.2m × 207.9m
- **Umfang:** 530.7 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 540.9 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 540.9 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** flachdach
- **Dachneigung:** 3°
- **First-Ausrichtung:** O-W
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Baldachin | arkade | 8.0m | 12.0m | 12.0m | Standard |
| Bahnhofshalle | hauptgebaeude | 18.0m | 22.0m | 22.0m | Standard |
| Bueroturm | turm | 30.0m | 40.0m | 40.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Baldachin): **12.0m**
- Zone 2 (Bahnhofshalle): **22.0m**
- Zone 3 (Bueroturm): **40.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 3.4 | NO |
| 1 | 10.3 | N |
| 2 | 14.6 | O |
| 3 | 24.2 | NO |
| 4 | 28.0 | NO |
| 5 | 20.2 | N |
| 6 | 12.8 | N |
| 7 | 5.8 | O |
| ... | (17 weitere) | ... |

- **Laengste Fassade:** 74.8 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 89% | - |
| Z2 | NO | 71% | - |
| Z3 | N | 2% | - |
| Z4 | N | 58% | - |
| Z5 | S | 50% | - |
| Z6 | S | 68% | - |
| Z7 | S | 81% | - |
| Z8 | S | 40% | - |
| Z9 | W | 83% | - |
| Z10 | W | 83% | - |
| Z11 | N | 2% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** Rechteckige Huelle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung
- **Zonen:** Farblich unterscheiden, Innenhoefe markieren

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: grundriss

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Baldachin' (12.0m) deutlich unter API-Traufhoehe (31.3m) - Zone-Daten pruefen!
- Zone 'Bahnhofshalle' (22.0m) deutlich unter API-Traufhoehe (31.3m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:09*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## GRUNDRISS-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>
  
  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>
  
  <!-- Gerüstzone Umriss (1m Abstand) -->
  <rect x="98" y="78" width="504" height="204" fill="none" stroke="#0066CC" stroke-width="1" stroke-dasharray="3,3"/>
  
  <!-- Zone 1: Baldachin (Arkade) - links -->
  <rect x="100" y="80" width="150" height="80" fill="url(#hatch)" stroke="#333" stroke-width="1.5"/>
  <text x="175" y="125" text-anchor="middle" font-size="10" fill="#333">Baldachin</text>
  <text x="175" y="135" text-anchor="middle" font-size="8" fill="#666">12.0m</text>
  
  <!-- Rundbogen für Arkade -->
  <path d="M 100,140 Q 125,150 150,140" fill="none" stroke="#333" stroke-width="1"/>
  <path d="M 150,140 Q 175,150 200,140" fill="none" stroke="#333" stroke-width="1"/>
  <path d="M 200,140 Q 225,150 250,140" fill="none" stroke="#333" stroke-width="1"/>
  
  <!-- Zone 2: Bahnhofshalle (Hauptgebäude) - mitte -->
  <rect x="250" y="80" width="250" height="200" fill="url(#hatch)" stroke="#333" stroke-width="1.5"/>
  <text x="375" y="185" text-anchor="middle" font-size="12" fill="#333">Bahnhofshalle</text>
  <text x="375" y="195" text-anchor="middle" font-size="9" fill="#666">22.0m</text>
  
  <!-- Zone 3: Büroturm (rechts) -->
  <rect x="500" y="80" width="100" height="200" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <text x="550" y="185" text-anchor="middle" font-size="10" fill="#333">Büroturm</text>
  <text x="550" y="195" text-anchor="middle" font-size="8" fill="#666">40.0m</text>
  <text x="550" y="205" text-anchor="middle" font-size="7" fill="#CC0000">Sonderkonstruktion</text>
  
  <!-- Gerüst-Stände -->
  <circle cx="110" cy="90" r="2" fill="#0066CC"/>
  <circle cx="240" cy="90" r="2" fill="#0066CC"/>
  <circle cx="260" cy="90" r="2" fill="#0066CC"/>
  <circle cx="490" cy="90" r="2" fill="#0066CC"/>
  <circle cx="510" cy="90" r="2" fill="#0066CC"/>
  <circle cx="590" cy="90" r="2" fill="#0066CC"/>
  
  <circle cx="110" cy="270" r="2" fill="#0066CC"/>
  <circle cx="240" cy="270" r="2" fill="#0066CC"/>
  <circle cx="260" cy="270" r="2" fill="#0066CC"/>
  <circle cx="490" cy="270" r="2" fill="#0066CC"/>
  <circle cx="510" cy="270" r="2" fill="#0066CC"/>
  <circle cx="590" cy="270" r="2" fill="#0066CC"/>
  
  <!-- Beläge (braun) -->
  <rect x="105" y="85" width="140" height="4" fill="#8B4513"/>
  <rect x="255" y="85" width="240" height="4" fill="#8B4513"/>
  <rect x="505" y="85" width="90" height="4" fill="#8B4513"/>
  
  <!-- Fassadenlängen -->
  <line x1="100" y1="60" x2="250" y2="60" stroke="#666" stroke-width="0.5"/>
  <text x="175" y="55" text-anchor="middle" font-size="8" fill="#666">150m</text>
  
  <line x1="250" y1="60" x2="500" y2="60" stroke="#666" stroke-width="0.5"/>
  <text x="375" y="55" text-anchor="middle" font-size="8" fill="#666">250m</text>
  
  <line x1="500" y1="60" x2="600" y2="60" stroke="#666" stroke-width="0.5"/>
  <text x="550" y="55" text-anchor="middle" font-size="8" fill="#666">100m</text>
  
  <!-- Gerüst-Zugänge -->
  <rect x="580" y="120" width="8" height="12" fill="#0066CC"/>
  <text x="595" y="130" font-size="7" fill="#0066CC">Z1</text>
  
  <rect x="320" y="75" width="12" height="8" fill="#0066CC"/>
  <text x="330" y="70" font-size="7" fill="#0066CC">Z2</text>
  
  <rect x="120" y="75" width="12" height="8" fill="#0066CC"/>
  <text x="130" y="70" font-size="7" fill="#0066CC">Z3</text>
  
  <rect x="350" y="275" width="12" height="8" fill="#0066CC"/>
  <text x="360" y="290" font-size="7" fill="#0066CC">Z5</text>
  
  <rect x="110" y="180" width="8" height="12" fill="#0066CC"/>
  <text x="95" y="190" font-size="7" fill="#0066CC">Z9</text>
  
  <!-- Nordpfeil -->
  <g transform="translate(50,350)">
    <path d="M 0,-15 L -5,5 L 0,0 L 5,5 Z" fill="#333"/>
    <text x="0" y="20" text-anchor="middle" font-size="10" fill="#333">N</text>
  </g>
  
  <!-- Maßstab -->
  <g transform="translate(50,400)">
    <line x1="0" y1="0" x2="50" y2="0" stroke="#333" stroke-width="2"/>
    <line x1="0" y1="-3" x2="0" y2="3" stroke="#333" stroke-width="1"/>
    <line x1="50" y1="-3" x2="50" y2="3" stroke="#333" stroke-width="1"/>
    <text x="25" y="15" text-anchor="middle" font-size="8" fill="#333">50m</text>
  </g>
  
  <!-- Titel und Koordinaten -->
  <text x="350" y="30" text-anchor="middle" font-size="14" font-weight="bold" fill="#333">Hauptbahnhof Bern - Grundriss</text>
  <text x="350" y="45" text-anchor="middle" font-size="8" fill="#666">EGID: 2241912 | LV95: 600107/199722</text>
  
  <!-- Legende -->
  <g transform="translate(520,320)">
    <rect x="0" y="0" width="150" height="120" fill="none" stroke="#999" stroke-width="0.5"/>
    <text x="5" y="15" font-size="10" font-weight="bold" fill="#333">Legende:</text>
    
    <rect x="5" y="25" width="12" height="8" fill="url(#hatch)" stroke="#333" stroke-width="0.5"/>
    <text x="20" y="32" font-size="8" fill="#333">Gebäude</text>
    
    <circle cx="11" cy="45" r="2" fill="#0066CC"/>
    <text x="20" y="48" font-size="8" fill="#333">Gerüstständer</text>
    
    <rect x="5" y="55" width="12" height="3" fill="#8B4513"/>
    <text x="20" y="62" font-size="8" fill="#333">Beläge</text>
    
    <rect x="5" y="70" width="8" height="8" fill="#0066CC"/>
    <text x="20" y="77" font-size="8" fill="#333">Zugang</text>
    
    <text x="5" y="95" font-size="7" fill="#666">Grundfläche: 7713 m²</text>
    <text x="5" y="105" font-size="7" fill="#666">Umfang: 530.7 m</text>
    <text x="5" y="115" font-size="7" fill="#666">Max. Höhe: 40.0 m</text>
  </g>
</svg>
```


--------------------------------------------------------------------------------
## ANSICHT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Fassadenansicht (Elevation)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Bahnhofplatz 10 3011 Bern
- **EGID:** 2241912
- **Koordinaten (LV95):** E 600107, N 199722
- **Gebaeudename:** Hauptbahnhof Bern
- **Gebaeudetyp:** Bahnhof
- **Baustil:** Moderne / Brutalismus
- **Baujahr:** 1974
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 31.3 m
- **Firsthoehe:** 36.8 m
- **Geschosse:** 4
- **Grundflaeche:** 7713 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 26 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 75.2m × 207.9m
- **Umfang:** 530.7 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 540.9 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 540.9 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** flachdach
- **Dachneigung:** 3°
- **First-Ausrichtung:** O-W
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Baldachin | arkade | 8.0m | 12.0m | 12.0m | Standard |
| Bahnhofshalle | hauptgebaeude | 18.0m | 22.0m | 22.0m | Standard |
| Bueroturm | turm | 30.0m | 40.0m | 40.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Baldachin): **12.0m**
- Zone 2 (Bahnhofshalle): **22.0m**
- Zone 3 (Bueroturm): **40.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 3.4 | NO |
| 1 | 10.3 | N |
| 2 | 14.6 | O |
| 3 | 24.2 | NO |
| 4 | 28.0 | NO |
| 5 | 20.2 | N |
| 6 | 12.8 | N |
| 7 | 5.8 | O |
| ... | (17 weitere) | ... |

- **Laengste Fassade:** 74.8 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 89% | - |
| Z2 | NO | 71% | - |
| Z3 | N | 2% | - |
| Z4 | N | 58% | - |
| Z5 | S | 50% | - |
| Z6 | S | 68% | - |
| Z7 | S | 81% | - |
| Z8 | S | 40% | - |
| Z9 | W | 83% | - |
| Z10 | W | 83% | - |
| Z11 | N | 2% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenraeume sichtbar!
- **Schraffur:** url(#hatch) fuer alle Fassadenflaechen
- **Terrain-Linie:** bei +/-0.00 = 540.9 m ue.M.
- **Geruest:** VOR der Fassade (Staender blau, Belaege braun)
- **Hoehenskala:** Links (+/-0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: ansicht

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Baldachin' (12.0m) deutlich unter API-Traufhoehe (31.3m) - Zone-Daten pruefen!
- Zone 'Bahnhofshalle' (22.0m) deutlich unter API-Traufhoehe (31.3m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:10*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## ANSICHT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Terrain-Linie -->
  <line x1="80" y1="400" x2="620" y2="400" stroke="#666" stroke-width="2"/>
  <rect x="80" y="400" width="540" height="60" fill="url(#ground)"/>

  <!-- Zone 1: Baldachin (arkade) - 12.0m -->
  <path d="M100,400 L180,400 L180,280 Q180,260 200,260 L260,260 Q280,260 280,280 L280,400 L360,400 L360,280 Q360,260 380,260 L440,260 Q460,260 460,280 L460,400 L540,400 L540,320 L100,320 Z" fill="url(#hatch)" stroke="#333" stroke-width="1"/>

  <!-- Zone 2: Bahnhofshalle (hauptgebaeude) - 22.0m -->
  <rect x="120" y="180" width="400" height="140" fill="url(#hatch)" stroke="#333" stroke-width="1"/>

  <!-- Zone 3: Bueroturm (turm) - 40.0m -->
  <rect x="280" y="40" width="140" height="140" fill="url(#hatch)" stroke="#333" stroke-width="1"/>

  <!-- Geruest Zone 1 (Baldachin) -->
  <!-- Staender -->
  <line x1="90" y1="400" x2="90" y2="300" stroke="#0066CC" stroke-width="3"/>
  <line x1="180" y1="400" x2="180" y2="300" stroke="#0066CC" stroke-width="3"/>
  <line x1="360" y1="400" x2="360" y2="300" stroke="#0066CC" stroke-width="3"/>
  <line x1="460" y1="400" x2="460" y2="300" stroke="#0066CC" stroke-width="3"/>
  <line x1="550" y1="400" x2="550" y2="300" stroke="#0066CC" stroke-width="3"/>
  
  <!-- Belaege Zone 1 -->
  <line x1="90" y1="380" x2="550" y2="380" stroke="#8B4513" stroke-width="4"/>
  <line x1="90" y1="350" x2="550" y2="350" stroke="#8B4513" stroke-width="4"/>
  <line x1="90" y1="320" x2="550" y2="320" stroke="#8B4513" stroke-width="4"/>

  <!-- Geruest Zone 2 (Bahnhofshalle) -->
  <!-- Staender -->
  <line x1="110" y1="320" x2="110" y2="160" stroke="#0066CC" stroke-width="3"/>
  <line x1="200" y1="320" x2="200" y2="160" stroke="#0066CC" stroke-width="3"/>
  <line x1="350" y1="320" x2="350" y2="160" stroke="#0066CC" stroke-width="3"/>
  <line x1="440" y1="320" x2="440" y2="160" stroke="#0066CC" stroke-width="3"/>
  <line x1="530" y1="320" x2="530" y2="160" stroke="#0066CC" stroke-width="3"/>

  <!-- Belaege Zone 2 -->
  <line x1="110" y1="300" x2="530" y2="300" stroke="#8B4513" stroke-width="4"/>
  <line x1="110" y1="260" x2="530" y2="260" stroke="#8B4513" stroke-width="4"/>
  <line x1="110" y1="220" x2="530" y2="220" stroke="#8B4513" stroke-width="4"/>
  <line x1="110" y1="180" x2="530" y2="180" stroke="#8B4513" stroke-width="4"/>

  <!-- Geruest Zone 3 (Bueroturm - Sonderkonstruktion) -->
  <!-- Staender -->
  <line x1="270" y1="180" x2="270" y2="20" stroke="#0066CC" stroke-width="3"/>
  <line x1="320" y1="180" x2="320" y2="20" stroke="#0066CC" stroke-width="3"/>
  <line x1="380" y1="180" x2="380" y2="20" stroke="#0066CC" stroke-width="3"/>
  <line x1="430" y1="180" x2="430" y2="20" stroke="#0066CC" stroke-width="3"/>

  <!-- Belaege Zone 3 -->
  <line x1="270" y1="160" x2="430" y2="160" stroke="#8B4513" stroke-width="4"/>
  <line x1="270" y1="120" x2="430" y2="120" stroke="#8B4513" stroke-width="4"/>
  <line x1="270" y1="80" x2="430" y2="80" stroke="#8B4513" stroke-width="4"/>
  <line x1="270" y1="40" x2="430" y2="40" stroke="#8B4513" stroke-width="4"/>

  <!-- Verankerungen -->
  <line x1="180" y1="280" x2="200" y2="280" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="360" y1="280" x2="350" y2="280" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="460" y1="280" x2="440" y2="280" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="520" y1="180" x2="500" y2="180" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="280" y1="180" x2="270" y2="180" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>
  <line x1="420" y1="40" x2="430" y2="40" stroke="#CC0000" stroke-width="2" stroke-dasharray="5,5"/>

  <!-- Hoehenskala links -->
  <g font-family="Arial" font-size="12" fill="#333">
    <line x1="60" y1="400" x2="70" y2="400" stroke="#333" stroke-width="1"/>
    <text x="55" y="405" text-anchor="end">±0.00</text>
    
    <line x1="60" y1="320" x2="70" y2="320" stroke="#333" stroke-width="1"/>
    <text x="55" y="325" text-anchor="end">+12.0</text>
    
    <line x1="60" y1="180" x2="70" y2="180" stroke="#333" stroke-width="1"/>
    <text x="55" y="185" text-anchor="end">+22.0</text>
    
    <line x1="60" y1="40" x2="70" y2="40" stroke="#333" stroke-width="1"/>
    <text x="55" y="45" text-anchor="end">+40.0</text>
  </g>

  <!-- Lagenbeschriftung rechts -->
  <g font-family="Arial" font-size="11" fill="#333">
    <text x="560" y="385" text-anchor="start">1. Lage</text>
    <text x="560" y="355" text-anchor="start">2. Lage</text>
    <text x="560" y="325" text-anchor="start">3. Lage</text>
    <text x="560" y="305" text-anchor="start">4. Lage</text>
    <text x="560" y="265" text-anchor="start">5. Lage</text>
    <text x="560" y="225" text-anchor="start">6. Lage</text>
    <text x="560" y="185" text-anchor="start">7. Lage</text>
    <text x="560" y="165" text-anchor="start">8. Lage</text>
    <text x="560" y="125" text-anchor="start">9. Lage</text>
    <text x="560" y="85" text-anchor="start">10. Lage</text>
    <text x="560" y="45" text-anchor="start">11. Lage</text>
  </g>

  <!-- Titel -->
  <text x="350" y="25" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold" fill="#333">Fassadenansicht - Hauptbahnhof Bern</text>
</svg>
```


--------------------------------------------------------------------------------
## SCHNITT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Gebaeudeschnitt (Querschnitt)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Bahnhofplatz 10 3011 Bern
- **EGID:** 2241912
- **Koordinaten (LV95):** E 600107, N 199722
- **Gebaeudename:** Hauptbahnhof Bern
- **Gebaeudetyp:** Bahnhof
- **Baustil:** Moderne / Brutalismus
- **Baujahr:** 1974
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 31.3 m
- **Firsthoehe:** 36.8 m
- **Geschosse:** 4
- **Grundflaeche:** 7713 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 26 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 75.2m × 207.9m
- **Umfang:** 530.7 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 540.9 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 540.9 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** flachdach
- **Dachneigung:** 3°
- **First-Ausrichtung:** O-W
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Baldachin | arkade | 8.0m | 12.0m | 12.0m | Standard |
| Bahnhofshalle | hauptgebaeude | 18.0m | 22.0m | 22.0m | Standard |
| Bueroturm | turm | 30.0m | 40.0m | 40.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Baldachin): **12.0m**
- Zone 2 (Bahnhofshalle): **22.0m**
- Zone 3 (Bueroturm): **40.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 3.4 | NO |
| 1 | 10.3 | N |
| 2 | 14.6 | O |
| 3 | 24.2 | NO |
| 4 | 28.0 | NO |
| 5 | 20.2 | N |
| 6 | 12.8 | N |
| 7 | 5.8 | O |
| ... | (17 weitere) | ... |

- **Laengste Fassade:** 74.8 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 89% | - |
| Z2 | NO | 71% | - |
| Z3 | N | 2% | - |
| Z4 | N | 58% | - |
| Z5 | S | 50% | - |
| Z6 | S | 68% | - |
| Z7 | S | 81% | - |
| Z8 | S | 40% | - |
| Z9 | W | 83% | - |
| Z10 | W | 83% | - |
| Z11 | N | 2% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 3: Gebaeudeschnitt (Querschnitt)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenraeume, Konstruktion, Raumhoehen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei +/-0.00 = 540.9 m ue.M. mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Geruest:** Links und rechts (Staender + Belaege)
- **Schnittmarkierung:** A-A

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: schnitt

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Baldachin' (12.0m) deutlich unter API-Traufhoehe (31.3m) - Zone-Daten pruefen!
- Zone 'Bahnhofshalle' (22.0m) deutlich unter API-Traufhoehe (31.3m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:10*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## SCHNITT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Terrain-Linie -->
  <rect x="0" y="350" width="700" height="15" fill="url(#ground)" stroke="#666" stroke-width="1"/>

  <!-- Zone 1: Baldachin (Arkade) - 12.0m -->
  <g>
    <!-- Geschnittene Mauern -->
    <rect x="80" y="290" width="15" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
    <rect x="185" y="290" width="15" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
    <!-- Rundbogen -->
    <path d="M95,290 Q140,270 185,290" fill="none" stroke="#333" stroke-width="2"/>
    <!-- Geschossdecke -->
    <line x1="95" y1="350" x2="185" y2="350" stroke="#333" stroke-width="1"/>
  </g>

  <!-- Zone 2: Bahnhofshalle (Hauptgebaeude) - 22.0m -->
  <g>
    <!-- Geschnittene Mauern -->
    <rect x="200" y="240" width="20" height="110" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
    <rect x="480" y="240" width="20" height="110" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
    <!-- Dach -->
    <line x1="220" y1="240" x2="480" y2="240" stroke="#333" stroke-width="2"/>
    <!-- Geschossdecken -->
    <line x1="220" y1="280" x2="480" y2="280" stroke="#333" stroke-width="1"/>
    <line x1="220" y1="315" x2="480" y2="315" stroke="#333" stroke-width="1"/>
    <line x1="220" y1="350" x2="480" y2="350" stroke="#333" stroke-width="1"/>
  </g>

  <!-- Zone 3: Bueroturm - 40.0m -->
  <g>
    <!-- Geschnittene Mauern -->
    <rect x="520" y="150" width="20" height="200" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
    <rect x="620" y="150" width="20" height="200" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
    <!-- Dach -->
    <line x1="540" y1="150" x2="620" y2="150" stroke="#333" stroke-width="2"/>
    <!-- Geschossdecken -->
    <line x1="540" y1="200" x2="620" y2="200" stroke="#333" stroke-width="1"/>
    <line x1="540" y1="250" x2="620" y2="250" stroke="#333" stroke-width="1"/>
    <line x1="540" y1="300" x2="620" y2="300" stroke="#333" stroke-width="1"/>
    <line x1="540" y1="350" x2="620" y2="350" stroke="#333" stroke-width="1"/>
  </g>

  <!-- Geruest Links -->
  <g>
    <!-- Staender -->
    <line x1="50" y1="140" x2="50" y2="360" stroke="#0066CC" stroke-width="3"/>
    <line x1="50" y1="140" x2="75" y2="140" stroke="#0066CC" stroke-width="2"/>
    <!-- Belaege -->
    <rect x="45" y="180" width="35" height="4" fill="#8B4513"/>
    <rect x="45" y="220" width="35" height="4" fill="#8B4513"/>
    <rect x="45" y="260" width="35" height="4" fill="#8B4513"/>
    <rect x="45" y="300" width="35" height="4" fill="#8B4513"/>
    <rect x="45" y="340" width="35" height="4" fill="#8B4513"/>
    <!-- Verankerung -->
    <line x1="75" y1="200" x2="80" y2="200" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
  </g>

  <!-- Geruest Mitte -->
  <g>
    <!-- Staender -->
    <line x1="170" y1="140" x2="170" y2="360" stroke="#0066CC" stroke-width="3"/>
    <line x1="170" y1="140" x2="195" y2="140" stroke="#0066CC" stroke-width="2"/>
    <!-- Belaege -->
    <rect x="165" y="180" width="35" height="4" fill="#8B4513"/>
    <rect x="165" y="220" width="35" height="4" fill="#8B4513"/>
    <rect x="165" y="260" width="35" height="4" fill="#8B4513"/>
    <rect x="165" y="300" width="35" height="4" fill="#8B4513"/>
    <rect x="165" y="340" width="35" height="4" fill="#8B4513"/>
  </g>

  <!-- Geruest Rechts (Sonderkonstruktion fuer Turm) -->
  <g>
    <!-- Staender -->
    <line x1="650" y1="130" x2="650" y2="360" stroke="#0066CC" stroke-width="4"/>
    <line x1="650" y1="130" x2="675" y2="130" stroke="#0066CC" stroke-width="3"/>
    <!-- Belaege -->
    <rect x="645" y="160" width="35" height="4" fill="#8B4513"/>
    <rect x="645" y="190" width="35" height="4" fill="#8B4513"/>
    <rect x="645" y="220" width="35" height="4" fill="#8B4513"/>
    <rect x="645" y="250" width="35" height="4" fill="#8B4513"/>
    <rect x="645" y="280" width="35" height="4" fill="#8B4513"/>
    <rect x="645" y="310" width="35" height="4" fill="#8B4513"/>
    <rect x="645" y="340" width="35" height="4" fill="#8B4513"/>
    <!-- Verankerung -->
    <line x1="645" y1="180" x2="620" y2="180" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
    <line x1="645" y1="280" x2="620" y2="280" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
  </g>

  <!-- Schnittmarkierung -->
  <g>
    <text x="30" y="400" font-family="Arial" font-size="14" font-weight="bold" fill="#333">A</text>
    <line x1="40" y1="395" x2="660" y2="395" stroke="#333" stroke-width="1" stroke-dasharray="5,5"/>
    <text x="670" y="400" font-family="Arial" font-size="14" font-weight="bold" fill="#333">A</text>
  </g>

  <!-- Hoehenkoten -->
  <g font-family="Arial" font-size="10" fill="#333">
    <text x="10" y="355">±0.00</text>
    <text x="10" y="295">+12.0m</text>
    <text x="10" y="245">+22.0m</text>
    <text x="10" y="155">+40.0m</text>
  </g>

  <!-- Titel -->
  <text x="350" y="30" font-family="Arial" font-size="16" font-weight="bold" text-anchor="middle" fill="#333">
    GEBÄUDESCHNITT A-A
  </text>
  <text x="350" y="50" font-family="Arial" font-size="12" text-anchor="middle" fill="#666">
    Hauptbahnhof Bern - Bahnhofplatz 10, 3011 Bern
  </text>

  <!-- Legende -->
  <g font-family="Arial" font-size="9" fill="#333">
    <rect x="20" y="420" width="12" height="8" fill="url(#cut-hatch)"/>
    <text x="35" y="428">Schnittfläche</text>
    <line x1="120" y1="424" x2="135" y2="424" stroke="#0066CC" stroke-width="3"/>
    <text x="140" y="428">Gerüst</text>
    <line x1="200" y1="424" x2="215" y2="424" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
    <text x="220" y="428">Verankerung</text>
  </g>
</svg>
```


================================================================================
# GEBÄUDE 8: Stadttheater
================================================================================

## Adresse
Theaterplatz 7, 3011 Bern

## EGID
1230414

## Recherche-Ergebnis (aus Pipeline)

- **Gebäudename:** Konzert Theater Bern
- **Gebäudetyp:** Theater / Oper
- **Architekturstil:** Neobarock
- **Baujahr:** 1903
- **Komplexität:** complex
- **Traufhöhe:** 15.1 m
- **Firsthöhe:** 17.7 m

### Erkannte Zonen

**Zone 1: Foyer**
- Typ: anbau
- Traufhöhe: 10.0 m
- Firsthöhe: 12.0 m
- Sonderkonstruktion: Nein

**Zone 2: Zuschauerhaus**
- Typ: hauptgebaeude
- Traufhöhe: 18.0 m
- Firsthöhe: 22.0 m
- Sonderkonstruktion: Nein

**Zone 3: Buehnenturm**
- Typ: turm
- Traufhöhe: 22.0 m
- Firsthöhe: 32.0 m
- Sonderkonstruktion: Ja


--------------------------------------------------------------------------------
## GRUNDRISS-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Grundriss (Draufsicht)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Theaterplatz 7 3011 Bern
- **EGID:** 1230414
- **Koordinaten (LV95):** E 600689, N 199605
- **Gebaeudename:** Konzert Theater Bern
- **Gebaeudetyp:** Theater / Oper
- **Baustil:** Neobarock
- **Baujahr:** 1903
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 15.1 m
- **Firsthoehe:** 17.7 m
- **Geschosse:** 5
- **Grundflaeche:** 761 m2

### Polygon
- **Eckpunkte:** 8
- **Umfang:** 113.5 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 540.9 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 540.9 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** walmdach
- **Dachneigung:** 12°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Foyer | anbau | 10.0m | 12.0m | 12.0m | Standard |
| Zuschauerhaus | hauptgebaeude | 18.0m | 22.0m | 22.0m | Standard |
| Buehnenturm | turm | 22.0m | 32.0m | 32.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Foyer): **12.0m**
- Zone 2 (Zuschauerhaus): **22.0m**
- Zone 3 (Buehnenturm): **32.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 14.3 | O |
| 1 | 21.7 | O |
| 2 | 20.1 | S |
| 3 | 19.1 | W |
| 4 | 16.0 | W |
| 5 | 16.0 | N |
| 6 | 6.4 | N |

- **Laengste Fassade:** 21.7 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 21% | - |
| Z2 | W | 3% | - |
| Z3 | N | 92% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** Rechteckige Huelle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung
- **Zonen:** Farblich unterscheiden, Innenhoefe markieren

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: grundriss

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Foyer' (12.0m) deutlich unter API-Traufhoehe (15.1m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:11*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## GRUNDRISS-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Titel -->
  <text x="350" y="25" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold">
    GRUNDRISS - KONZERT THEATER BERN
  </text>
  <text x="350" y="45" text-anchor="middle" font-family="Arial" font-size="12">
    Theaterplatz 7, 3011 Bern | EGID: 1230414 | M 1:500
  </text>

  <!-- Geruestzone (äussere Begrenzung) -->
  <rect x="150" y="100" width="300" height="220" fill="none" stroke="#0066CC" stroke-width="2" stroke-dasharray="5,5"/>
  <text x="155" y="95" font-family="Arial" font-size="10" fill="#0066CC">Gerüstzone</text>

  <!-- Gebäude Zonen -->
  
  <!-- Zone 1: Foyer (Anbau, 12.0m) -->
  <rect x="170" y="120" width="80" height="60" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <text x="210" y="155" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">FOYER</text>
  <text x="210" y="165" text-anchor="middle" font-family="Arial" font-size="8">12.0m</text>

  <!-- Zone 2: Zuschauerhaus (Hauptgebäude, 22.0m) -->
  <rect x="250" y="120" width="120" height="100" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <text x="310" y="170" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold">ZUSCHAUERHAUS</text>
  <text x="310" y="180" text-anchor="middle" font-family="Arial" font-size="8">22.0m</text>

  <!-- Zone 3: Bühnenturm (Turm, 32.0m) -->
  <rect x="370" y="140" width="60" height="120" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
  <text x="400" y="200" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">BÜHNEN-</text>
  <text x="400" y="210" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">TURM</text>
  <text x="400" y="220" text-anchor="middle" font-family="Arial" font-size="8">32.0m</text>

  <!-- Fassadenlängen -->
  <!-- Fassade 0: 14.3m O -->
  <line x1="430" y1="140" x2="430" y2="180" stroke="#666" stroke-width="1"/>
  <text x="435" y="165" font-family="Arial" font-size="8">14.3m</text>

  <!-- Fassade 1: 21.7m O -->
  <line x1="430" y1="180" x2="430" y2="260" stroke="#666" stroke-width="1"/>
  <text x="435" y="225" font-family="Arial" font-size="8">21.7m</text>

  <!-- Fassade 2: 20.1m S -->
  <line x1="430" y1="260" x2="370" y2="260" stroke="#666" stroke-width="1"/>
  <text x="400" y="275" text-anchor="middle" font-family="Arial" font-size="8">20.1m</text>

  <!-- Fassade 3: 19.1m W -->
  <line x1="370" y1="260" x2="250" y2="260" stroke="#666" stroke-width="1"/>
  <text x="310" y="275" text-anchor="middle" font-family="Arial" font-size="8">19.1m</text>

  <!-- Fassade 4: 16.0m W -->
  <line x1="250" y1="220" x2="170" y2="220" stroke="#666" stroke-width="1"/>
  <text x="210" y="235" text-anchor="middle" font-family="Arial" font-size="8">16.0m</text>

  <!-- Fassade 5: 16.0m N -->
  <line x1="170" y1="180" x2="250" y2="180" stroke="#666" stroke-width="1"/>
  <text x="210" y="195" text-anchor="middle" font-family="Arial" font-size="8">16.0m</text>

  <!-- Fassade 6: 6.4m N -->
  <line x1="250" y1="120" x2="280" y2="120" stroke="#666" stroke-width="1"/>
  <text x="265" y="110" text-anchor="middle" font-family="Arial" font-size="8">6.4m</text>

  <!-- Gerüst-Zugänge -->
  <!-- Z1: Ost, 21% -->
  <circle cx="430" y="185" r="3" fill="#CC0000"/>
  <text x="435" y="190" font-family="Arial" font-size="8" fill="#CC0000">Z1</text>

  <!-- Z2: West, 3% -->
  <circle cx="170" y="183" r="3" fill="#CC0000"/>
  <text x="175" y="188" font-family="Arial" font-size="8" fill="#CC0000">Z2</text>

  <!-- Z3: Nord, 92% -->
  <circle cx="275" y="120" r="3" fill="#CC0000"/>
  <text x="280" y="125" font-family="Arial" font-size="8" fill="#CC0000">Z3</text>

  <!-- Nordpfeil -->
  <g transform="translate(550, 150)">
    <line x1="0" y1="0" x2="0" y2="-30" stroke="#333" stroke-width="2" marker-end="url(#arrowhead)"/>
    <text x="5" y="-10" font-family="Arial" font-size="12" font-weight="bold">N</text>
  </g>

  <!-- Pfeilspitze -->
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#333"/>
    </marker>
  </defs>

  <!-- Massstab -->
  <g transform="translate(50, 400)">
    <line x1="0" y1="0" x2="50" y2="0" stroke="#333" stroke-width="2"/>
    <line x1="0" y1="-5" x2="0" y2="5" stroke="#333" stroke-width="1"/>
    <line x1="50" y1="-5" x2="50" y2="5" stroke="#333" stroke-width="1"/>
    <text x="25" y="15" text-anchor="middle" font-family="Arial" font-size="10">25m</text>
    <text x="25" y="30" text-anchor="middle" font-family="Arial" font-size="8">M 1:500</text>
  </g>

  <!-- Legende -->
  <g transform="translate(500, 250)">
    <rect x="0" y="0" width="150" height="120" fill="none" stroke="#333" stroke-width="1"/>
    <text x="5" y="15" font-family="Arial" font-size="10" font-weight="bold">LEGENDE</text>
    
    <rect x="5" y="25" width="15" height="10" fill="url(#hatch)" stroke="#333"/>
    <text x="25" y="33" font-family="Arial" font-size="8">Gebäudemauern</text>
    
    <rect x="5" y="40" width="15" height="10" fill="none" stroke="#0066CC" stroke-dasharray="3,3"/>
    <text x="25" y="48" font-family="Arial" font-size="8">Gerüstzone</text>
    
    <circle cx="12" cy="60" r="3" fill="#CC0000"/>
    <text x="25" y="63" font-family="Arial" font-size="8">Gerüst-Zugang</text>
    
    <text x="5" y="80" font-family="Arial" font-size="8">Grundfläche: 761 m²</text>
    <text x="5" y="92" font-family="Arial" font-size="8">Umfang: 113.5 m</text>
    <text x="5" y="104" font-family="Arial" font-size="8">Eckpunkte: 8</text>
  </g>

  <!-- Technische Angaben -->
  <text x="50" y="460" font-family="Arial" font-size="8" fill="#666">
    Koordinaten LV95: E 600689, N 199605 | Terrain: 540.9 m ü.M. | Walmdach 12°
  </text>
</svg>
```


--------------------------------------------------------------------------------
## ANSICHT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Fassadenansicht (Elevation)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Theaterplatz 7 3011 Bern
- **EGID:** 1230414
- **Koordinaten (LV95):** E 600689, N 199605
- **Gebaeudename:** Konzert Theater Bern
- **Gebaeudetyp:** Theater / Oper
- **Baustil:** Neobarock
- **Baujahr:** 1903
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 15.1 m
- **Firsthoehe:** 17.7 m
- **Geschosse:** 5
- **Grundflaeche:** 761 m2

### Polygon
- **Eckpunkte:** 8
- **Umfang:** 113.5 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 540.9 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 540.9 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** walmdach
- **Dachneigung:** 12°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Foyer | anbau | 10.0m | 12.0m | 12.0m | Standard |
| Zuschauerhaus | hauptgebaeude | 18.0m | 22.0m | 22.0m | Standard |
| Buehnenturm | turm | 22.0m | 32.0m | 32.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Foyer): **12.0m**
- Zone 2 (Zuschauerhaus): **22.0m**
- Zone 3 (Buehnenturm): **32.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 14.3 | O |
| 1 | 21.7 | O |
| 2 | 20.1 | S |
| 3 | 19.1 | W |
| 4 | 16.0 | W |
| 5 | 16.0 | N |
| 6 | 6.4 | N |

- **Laengste Fassade:** 21.7 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 21% | - |
| Z2 | W | 3% | - |
| Z3 | N | 92% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenraeume sichtbar!
- **Schraffur:** url(#hatch) fuer alle Fassadenflaechen
- **Terrain-Linie:** bei +/-0.00 = 540.9 m ue.M.
- **Geruest:** VOR der Fassade (Staender blau, Belaege braun)
- **Hoehenskala:** Links (+/-0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: ansicht

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Foyer' (12.0m) deutlich unter API-Traufhoehe (15.1m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:11*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## ANSICHT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
    
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>
    
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
    
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>
  
  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>
  
  <!-- Terrain -->
  <rect x="80" y="380" width="500" height="20" fill="url(#ground)" stroke="#666" stroke-width="1"/>
  
  <!-- Zone 1: Foyer (12.0m) -->
  <rect x="80" y="260" width="120" height="120" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Zone 2: Zuschauerhaus (22.0m) - Hauptgebäude -->
  <rect x="200" y="160" width="200" height="220" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Dach Zone 2 - Walmdach -->
  <polygon points="195,160 205,140 395,140 405,160" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Zone 3: Bühnenturm (32.0m) -->
  <rect x="400" y="80" width="100" height="300" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Dach Zone 3 -->
  <polygon points="395,80 405,70 495,70 505,80" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Gerüst vor Foyer -->
  <!-- Vertikale Städer -->
  <line x1="70" y1="380" x2="70" y2="240" stroke="#0066CC" stroke-width="3"/>
  <line x1="210" y1="380" x2="210" y2="240" stroke="#0066CC" stroke-width="3"/>
  
  <!-- Horizontale Beläge Foyer -->
  <rect x="68" y="350" width="144" height="4" fill="#8B4513"/>
  <rect x="68" y="310" width="144" height="4" fill="#8B4513"/>
  <rect x="68" y="270" width="144" height="4" fill="#8B4513"/>
  <rect x="68" y="242" width="144" height="4" fill="#8B4513"/>
  
  <!-- Gerüst vor Zuschauerhaus -->
  <!-- Vertikale Städer -->
  <line x1="190" y1="380" x2="190" y2="140" stroke="#0066CC" stroke-width="3"/>
  <line x1="280" y1="380" x2="280" y2="140" stroke="#0066CC" stroke-width="3"/>
  <line x1="320" y1="380" x2="320" y2="140" stroke="#0066CC" stroke-width="3"/>
  <line x1="410" y1="380" x2="410" y2="140" stroke="#0066CC" stroke-width="3"/>
  
  <!-- Horizontale Beläge Zuschauerhaus -->
  <rect x="188" y="350" width="224" height="4" fill="#8B4513"/>
  <rect x="188" y="310" width="224" height="4" fill="#8B4513"/>
  <rect x="188" y="270" width="224" height="4" fill="#8B4513"/>
  <rect x="188" y="230" width="224" height="4" fill="#8B4513"/>
  <rect x="188" y="190" width="224" height="4" fill="#8B4513"/>
  <rect x="188" y="150" width="224" height="4" fill="#8B4513"/>
  
  <!-- Gerüst vor Bühnenturm - Sonderkonstruktion -->
  <!-- Vertikale Städer -->
  <line x1="390" y1="380" x2="390" y2="70" stroke="#0066CC" stroke-width="3"/>
  <line x1="450" y1="380" x2="450" y2="70" stroke="#0066CC" stroke-width="3"/>
  <line x1="510" y1="380" x2="510" y2="70" stroke="#0066CC" stroke-width="3"/>
  
  <!-- Horizontale Beläge Bühnenturm -->
  <rect x="388" y="350" width="124" height="4" fill="#8B4513"/>
  <rect x="388" y="310" width="124" height="4" fill="#8B4513"/>
  <rect x="388" y="270" width="124" height="4" fill="#8B4513"/>
  <rect x="388" y="230" width="124" height="4" fill="#8B4513"/>
  <rect x="388" y="190" width="124" height="4" fill="#8B4513"/>
  <rect x="388" y="150" width="124" height="4" fill="#8B4513"/>
  <rect x="388" y="110" width="124" height="4" fill="#8B4513"/>
  <rect x="388" y="82" width="124" height="4" fill="#8B4513"/>
  
  <!-- Verankerungen -->
  <line x1="210" y1="300" x2="200" y2="300" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
  <line x1="410" y1="280" x2="400" y2="280" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
  <line x1="410" y1="200" x2="400" y2="200" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
  <line x1="510" y1="250" x2="500" y2="250" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
  <line x1="510" y1="150" x2="500" y2="150" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
  
  <!-- Gerüst-Zugänge -->
  <!-- Z1: O, 21% -->
  <rect x="560" y="375" width="15" height="10" fill="#0066CC" stroke="#333"/>
  <text x="565" y="385" font-family="Arial" font-size="8" fill="#000">Z1</text>
  
  <!-- Z2: W, 3% -->
  <rect x="65" y="375" width="15" height="10" fill="#0066CC" stroke="#333"/>
  <text x="70" y="385" font-family="Arial" font-size="8" fill="#000">Z2</text>
  
  <!-- Z3: N, 92% -->
  <rect x="480" y="375" width="15" height="10" fill="#0066CC" stroke="#333"/>
  <text x="485" y="385" font-family="Arial" font-size="8" fill="#000">Z3</text>
  
  <!-- Höhenskala links -->
  <line x1="40" y1="380" x2="40" y2="70" stroke="#333" stroke-width="1"/>
  <line x1="35" y1="380" x2="45" y2="380" stroke="#333" stroke-width="1"/>
  <line x1="35" y1="260" x2="45" y2="260" stroke="#333" stroke-width="1"/>
  <line x1="35" y1="160" x2="45" y2="160" stroke="#333" stroke-width="1"/>
  <line x1="35" y1="80" x2="45" y2="80" stroke="#333" stroke-width="1"/>
  
  <text x="20" y="385" font-family="Arial" font-size="10" fill="#000">±0.00</text>
  <text x="15" y="265" font-family="Arial" font-size="10" fill="#000">+12.0m</text>
  <text x="15" y="165" font-family="Arial" font-size="10" fill="#000">+22.0m</text>
  <text x="15" y="85" font-family="Arial" font-size="10" fill="#000">+32.0m</text>
  
  <!-- Lagenbeschriftung rechts -->
  <text x="580" y="365" font-family="Arial" font-size="10" fill="#000">1. Lage</text>
  <text x="580" y="325" font-family="Arial" font-size="10" fill="#000">2. Lage</text>
  <text x="580" y="285" font-family="Arial" font-size="10" fill="#000">3. Lage</text>
  <text x="580" y="245" font-family="Arial" font-size="10" fill="#000">4. Lage</text>
  <text x="580" y="205" font-family="Arial" font-size="10" fill="#000">5. Lage</text>
  <text x="580" y="165" font-family="Arial" font-size="10" fill="#000">6. Lage</text>
  <text x="580" y="125" font-family="Arial" font-size="10" fill="#000">7. Lage</text>
  <text x="580" y="95" font-family="Arial" font-size="10" fill="#000">8. Lage</text>
  
  <!-- Titel -->
  <text x="350" y="30" font-family="Arial" font-size="14" font-weight="bold" fill="#000" text-anchor="middle">Fassadenansicht - Konzert Theater Bern</text>
  <text x="350" y="45" font-family="Arial" font-size="10" fill="#000" text-anchor="middle">Theaterplatz 7, 3011 Bern - EGID: 1230414</text>
  
  <!-- Nordpfeil -->
  <g transform="translate(620, 100)">
    <line x1="0" y1="0" x2="0" y2="-20" stroke="#333" stroke-width="2" marker-end="url(#arrowhead)"/>
    <text x="5" y="-5" font-family="Arial" font-size="8" fill="#000">N</text>
  </g>
  
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="0" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#333"/>
    </marker>
  </defs>
</svg>
```


--------------------------------------------------------------------------------
## SCHNITT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Gebaeudeschnitt (Querschnitt)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Theaterplatz 7 3011 Bern
- **EGID:** 1230414
- **Koordinaten (LV95):** E 600689, N 199605
- **Gebaeudename:** Konzert Theater Bern
- **Gebaeudetyp:** Theater / Oper
- **Baustil:** Neobarock
- **Baujahr:** 1903
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 15.1 m
- **Firsthoehe:** 17.7 m
- **Geschosse:** 5
- **Grundflaeche:** 761 m2

### Polygon
- **Eckpunkte:** 8
- **Umfang:** 113.5 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 540.9 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 540.9 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** walmdach
- **Dachneigung:** 12°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Foyer | anbau | 10.0m | 12.0m | 12.0m | Standard |
| Zuschauerhaus | hauptgebaeude | 18.0m | 22.0m | 22.0m | Standard |
| Buehnenturm | turm | 22.0m | 32.0m | 32.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Foyer): **12.0m**
- Zone 2 (Zuschauerhaus): **22.0m**
- Zone 3 (Buehnenturm): **32.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 14.3 | O |
| 1 | 21.7 | O |
| 2 | 20.1 | S |
| 3 | 19.1 | W |
| 4 | 16.0 | W |
| 5 | 16.0 | N |
| 6 | 6.4 | N |

- **Laengste Fassade:** 21.7 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 21% | - |
| Z2 | W | 3% | - |
| Z3 | N | 92% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 3: Gebaeudeschnitt (Querschnitt)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenraeume, Konstruktion, Raumhoehen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei +/-0.00 = 540.9 m ue.M. mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Geruest:** Links und rechts (Staender + Belaege)
- **Schnittmarkierung:** A-A

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: schnitt

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Foyer' (12.0m) deutlich unter API-Traufhoehe (15.1m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:12*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## SCHNITT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>

<!-- Hintergrund -->
<rect width="700" height="480" fill="#FFFFFF"/>

<!-- Titel -->
<text x="350" y="25" font-family="Arial" font-size="16" font-weight="bold" text-anchor="middle" fill="#000">Konzert Theater Bern - Gebäudeschnitt A-A</text>
<text x="350" y="40" font-family="Arial" font-size="10" text-anchor="middle" fill="#666">Theaterplatz 7, 3011 Bern</text>

<!-- Terrain-Linie -->
<rect x="60" y="370" width="580" height="20" fill="url(#ground)" stroke="#666" stroke-width="1"/>
<text x="50" y="385" font-family="Arial" font-size="9" text-anchor="end" fill="#000">±0.00</text>

<!-- Zone 1: Foyer (Anbau) - 12.0m -->
<g>
  <!-- Schnittflaeche - linke Wand -->
  <rect x="80" y="290" width="15" height="80" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Innenraum (LEER/WEISS) -->
  <rect x="95" y="290" width="120" height="80" fill="#FFFFFF" stroke="none"/>
  
  <!-- Schnittflaeche - rechte Wand -->
  <rect x="215" y="290" width="15" height="80" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Dach (Walmdach 12°) -->
  <polygon points="75,290 120,270 190,270 235,290" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Geschossdecken -->
  <line x1="95" y1="330" x2="215" y2="330" stroke="#333" stroke-width="0.5"/>
  <line x1="95" y1="350" x2="215" y2="350" stroke="#333" stroke-width="0.5"/>
</g>

<!-- Zone 2: Zuschauerhaus (Hauptgebäude) - 22.0m -->
<g>
  <!-- Schnittflaeche - linke Wand -->
  <rect x="230" y="190" width="20" height="180" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Innenraum (LEER/WEISS) -->
  <rect x="250" y="190" width="200" height="180" fill="#FFFFFF" stroke="none"/>
  
  <!-- Schnittflaeche - rechte Wand -->
  <rect x="450" y="190" width="20" height="180" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Dach (Walmdach 12°) -->
  <polygon points="225,190 280,150 420,150 475,190" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Geschossdecken -->
  <line x1="250" y1="230" x2="450" y2="230" stroke="#333" stroke-width="0.5"/>
  <line x1="250" y1="270" x2="450" y2="270" stroke="#333" stroke-width="0.5"/>
  <line x1="250" y1="310" x2="450" y2="310" stroke="#333" stroke-width="0.5"/>
  <line x1="250" y1="350" x2="450" y2="350" stroke="#333" stroke-width="0.5"/>
</g>

<!-- Zone 3: Bühnenturm (Turm) - 32.0m -->
<g>
  <!-- Schnittflaeche - linke Wand -->
  <rect x="470" y="90" width="20" height="280" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Innenraum (LEER/WEISS) -->
  <rect x="490" y="90" width="120" height="280" fill="#FFFFFF" stroke="none"/>
  
  <!-- Schnittflaeche - rechte Wand -->
  <rect x="610" y="90" width="20" height="280" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Flaches Dach -->
  <rect x="465" y="85" width="170" height="10" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  
  <!-- Geschossdecken -->
  <line x1="490" y1="130" x2="610" y2="130" stroke="#333" stroke-width="0.5"/>
  <line x1="490" y1="170" x2="610" y2="170" stroke="#333" stroke-width="0.5"/>
  <line x1="490" y1="210" x2="610" y2="210" stroke="#333" stroke-width="0.5"/>
  <line x1="490" y1="250" x2="610" y2="250" stroke="#333" stroke-width="0.5"/>
  <line x1="490" y1="290" x2="610" y2="290" stroke="#333" stroke-width="0.5"/>
  <line x1="490" y1="330" x2="610" y2="330" stroke="#333" stroke-width="0.5"/>
</g>

<!-- Gerüst links -->
<g stroke="#0066CC" stroke-width="2" fill="none">
  <!-- Ständer -->
  <line x1="30" y1="80" x2="30" y2="380"/>
  <line x1="50" y1="80" x2="50" y2="380"/>
  
  <!-- Riegel -->
  <line x1="30" y1="100" x2="50" y2="100"/>
  <line x1="30" y1="140" x2="50" y2="140"/>
  <line x1="30" y1="180" x2="50" y2="180"/>
  <line x1="30" y1="220" x2="50" y2="220"/>
  <line x1="30" y1="260" x2="50" y2="260"/>
  <line x1="30" y1="300" x2="50" y2="300"/>
  <line x1="30" y1="340" x2="50" y2="340"/>
  
  <!-- Beläge -->
  <rect x="30" y="98" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
  <rect x="30" y="138" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
  <rect x="30" y="178" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
  <rect x="30" y="218" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
  <rect x="30" y="258" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
  <rect x="30" y="298" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
  <rect x="30" y="338" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
</g>

<!-- Gerüst rechts -->
<g stroke="#0066CC" stroke-width="2" fill="none">
  <!-- Ständer -->
  <line x1="650" y1="80" x2="650" y2="380"/>
  <line x1="670" y1="80" x2="670" y2="380"/>
  
  <!-- Riegel -->
  <line x1="650" y1="100" x2="670" y2="100"/>
  <line x1="650" y1="140" x2="670" y2="140"/>
  <line x1="650" y1="180" x2="670" y2="180"/>
  <line x1="650" y1="220" x2="670" y2="220"/>
  <line x1="650" y1="260" x2="670" y2="260"/>
  <line x1="650" y1="300" x2="670" y2="300"/>
  <line x1="650" y1="340" x2="670" y2="340"/>
  
  <!-- Beläge -->
  <rect x="650" y="98" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
  <rect x="650" y="138" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
  <rect x="650" y="178" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
  <rect x="650" y="218" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
  <rect x="650" y="258" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
  <rect x="650" y="298" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
  <rect x="650" y="338" width="20" height="4" fill="#8B4513" stroke="#8B4513"/>
</g>

<!-- Verankerungen -->
<line x1="50" y1="200" x2="80" y2="200" stroke="#CC0000" stroke-width="1" stroke-dasharray="3,2"/>
<line x1="50" y1="280" x2="80" y2="280" stroke="#CC0000" stroke-width="1" stroke-dasharray="3,2"/>
<line x1="650" y1="150" x2="630" y2="150" stroke="#CC0000" stroke-width="1" stroke-dasharray="3,2"/>
<line x1="650" y1="250" x2="630" y2="250" stroke="#CC0000" stroke-width="1" stroke-dasharray="3,2"/>

<!-- Höhenangaben -->
<g font-family="Arial" font-size="9" fill="#000">
  <text x="20" y="288" text-anchor="end">12.0m</text>
  <text x="20" y="188" text-anchor="end">22.0m</text>
  <text x="20" y="88" text-anchor="end">32.0m</text>
</g>

<!-- Schnittmarkierung -->
<g font-family="Arial" font-size="12" font-weight="bold" fill="#000">
  <circle cx="80" cy="60" r="12" fill="none" stroke="#000" stroke-width="1"/>
  <text x="80" y="65" text-anchor="middle">A</text>
  <circle cx="620" cy="60" r="12" fill="none" stroke="#000" stroke-width="1"/>
  <text x="620" y="65" text-anchor="middle">A</text>
</g>

<!-- Legende -->
<g font-family="Arial" font-size="8" fill="#333">
  <text x="60" y="420">Foyer</text>
  <text x="340" y="420">Zuschauerhaus</text>
  <text x="540" y="420">Bühnenturm</text>
  
  <rect x="60" y="435" width="15" height="8" fill="#0066CC"/>
  <text x="80" y="442">Gerüst</text>
  
  <rect x="150" y="435" width="15" height="8" fill="url(#cut-hatch)"/>
  <text x="170" y="442">Schnittfläche</text>
  
  <line x1="260" y1="439" x2="275" y2="439" stroke="#CC0000" stroke-width="1" stroke-dasharray="2,1"/>
  <text x="280" y="442">Verankerung</text>
</g>

<!-- Maßstab -->
<text x="560" y="465" font-family="Arial" font-size="9" fill="#666">Maßstab 1:200</text>
</svg>
```


================================================================================
# GEBÄUDE 9: Historisches Museum
================================================================================

## Adresse
Helvetiaplatz 5, 3005 Bern

## EGID
2243518

## Recherche-Ergebnis (aus Pipeline)

- **Gebäudename:** Bernisches Historisches Museum
- **Gebäudetyp:** Museum
- **Architekturstil:** Historismus (Schloss)
- **Baujahr:** 1894
- **Komplexität:** complex
- **Traufhöhe:** 44.0 m
- **Firsthöhe:** 51.8 m

### Erkannte Zonen

**Zone 1: Hauptbau**
- Typ: hauptgebaeude
- Traufhöhe: 25.0 m
- Firsthöhe: 35.0 m
- Sonderkonstruktion: Nein

**Zone 2: Seitenfluegel**
- Typ: anbau
- Traufhöhe: 18.0 m
- Firsthöhe: 25.0 m
- Sonderkonstruktion: Nein

**Zone 3: Eckturm**
- Typ: turm
- Traufhöhe: 35.0 m
- Firsthöhe: 50.0 m
- Sonderkonstruktion: Ja


--------------------------------------------------------------------------------
## GRUNDRISS-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Grundriss (Draufsicht)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Helvetiaplatz 5 3005 Bern
- **EGID:** 2243518
- **Koordinaten (LV95):** E 600810, N 199108
- **Gebaeudename:** Bernisches Historisches Museum
- **Gebaeudetyp:** Museum
- **Baustil:** Historismus (Schloss)
- **Baujahr:** 1894
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 44.0 m
- **Firsthoehe:** 51.8 m
- **Geschosse:** -
- **Grundflaeche:** 2115 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 36 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 93.9m × 71.8m
- **Umfang:** 397.4 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 535.3 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 535.3 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach_mit_turm
- **Dachneigung:** 12°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Hauptbau | hauptgebaeude | 25.0m | 35.0m | 35.0m | Standard |
| Seitenfluegel | anbau | 18.0m | 25.0m | 25.0m | Standard |
| Eckturm | turm | 35.0m | 50.0m | 50.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Hauptbau): **35.0m**
- Zone 2 (Seitenfluegel): **25.0m**
- Zone 3 (Eckturm): **50.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 22.7 | O |
| 1 | 6.8 | N |
| 2 | 3.4 | O |
| 3 | 19.2 | O |
| 4 | 4.1 | N |
| 5 | 5.8 | O |
| 6 | 3.1 | S |
| 7 | 9.1 | O |
| ... | (27 weitere) | ... |

- **Laengste Fassade:** 29.9 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | N | 9% | - |
| Z2 | NO | 9% | - |
| Z3 | O | 91% | - |
| Z4 | W | 55% | - |
| Z5 | SW | 7% | - |
| Z6 | N | 91% | - |
| Z7 | S | 32% | - |
| Z8 | W | 16% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** Rechteckige Huelle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung
- **Zonen:** Farblich unterscheiden, Innenhoefe markieren

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: grundriss

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Hauptbau' (35.0m) deutlich unter API-Traufhoehe (44.0m) - Zone-Daten pruefen!
- Zone 'Seitenfluegel' (25.0m) deutlich unter API-Traufhoehe (44.0m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:12*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## GRUNDRISS-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>

<!-- Hintergrund -->
<rect width="700" height="480" fill="#FFFFFF"/>

<!-- Titel -->
<text x="20" y="30" font-family="Arial" font-size="16" font-weight="bold">GRUNDRISS - Bernisches Historisches Museum</text>
<text x="20" y="50" font-family="Arial" font-size="12">Helvetiaplatz 5, 3005 Bern - EGID: 2243518</text>

<!-- Geruestzone (aeussere Grenze) -->
<rect x="100" y="100" width="420" height="280" fill="none" stroke="#0066CC" stroke-width="2" stroke-dasharray="5,5"/>
<text x="102" y="95" font-family="Arial" font-size="10" fill="#0066CC">Geruestzone (1m Abstand)</text>

<!-- Hauptbau (35m Hoehe) -->
<rect x="150" y="140" width="280" height="160" fill="url(#hatch)" stroke="#333" stroke-width="2"/>
<text x="280" y="225" font-family="Arial" font-size="12" font-weight="bold" text-anchor="middle">Hauptbau</text>
<text x="280" y="240" font-family="Arial" font-size="10" text-anchor="middle">35.0m</text>

<!-- Seitenfluegel links (25m Hoehe) -->
<rect x="110" y="180" width="40" height="80" fill="url(#hatch)" stroke="#666" stroke-width="1.5"/>
<text x="125" y="215" font-family="Arial" font-size="9" text-anchor="middle" transform="rotate(-90 125 215)">Seitenfluegel</text>
<text x="125" y="235" font-family="Arial" font-size="8" text-anchor="middle" transform="rotate(-90 125 235)">25.0m</text>

<!-- Seitenfluegel rechts (25m Hoehe) -->
<rect x="430" y="170" width="40" height="100" fill="url(#hatch)" stroke="#666" stroke-width="1.5"/>
<text x="455" y="215" font-family="Arial" font-size="9" text-anchor="middle" transform="rotate(90 455 215)">Seitenfluegel</text>
<text x="455" y="235" font-family="Arial" font-size="8" text-anchor="middle" transform="rotate(90 455 235)">25.0m</text>

<!-- Eckturm (50m Hoehe) -->
<rect x="480" y="120" width="30" height="40" fill="url(#hatch)" stroke="#000" stroke-width="2"/>
<text x="495" y="135" font-family="Arial" font-size="8" text-anchor="middle">Turm</text>
<text x="495" y="145" font-family="Arial" font-size="7" text-anchor="middle">50.0m</text>

<!-- Geruest-Zugaenge -->
<circle cx="290" cy="135" r="4" fill="#CC0000"/>
<text x="295" y="130" font-family="Arial" font-size="8" fill="#CC0000">Z1 (N)</text>

<circle cx="480" cy="145" r="4" fill="#CC0000"/>
<text x="485" y="140" font-family="Arial" font-size="8" fill="#CC0000">Z2 (NO)</text>

<circle cx="435" y="305" r="4" fill="#CC0000"/>
<text x="440" y="320" font-family="Arial" font-size="8" fill="#CC0000">Z3 (O)</text>

<circle cx="105" y="220" r="4" fill="#CC0000"/>
<text x="70" y="215" font-family="Arial" font-size="8" fill="#CC0000">Z4 (W)</text>

<circle cx="180" cy="305" r="4" fill="#CC0000"/>
<text x="155" y="320" font-family="Arial" font-size="8" fill="#CC0000">Z5 (SW)</text>

<circle cx="380" cy="135" r="4" fill="#CC0000"/>
<text x="385" y="130" font-family="Arial" font-size="8" fill="#CC0000">Z6 (N)</text>

<circle cx="310" cy="305" r="4" fill="#CC0000"/>
<text x="315" y="320" font-family="Arial" font-size="8" fill="#CC0000">Z7 (S)</text>

<circle cx="105" cy="160" r="4" fill="#CC0000"/>
<text x="70" y="155" font-family="Arial" font-size="8" fill="#CC0000">Z8 (W)</text>

<!-- Fassadenlaengen -->
<line x1="150" y1="125" x2="430" y2="125" stroke="#666" stroke-width="1"/>
<text x="290" y="120" font-family="Arial" font-size="9" text-anchor="middle">93.9m</text>

<line x1="85" y1="140" x2="85" y2="300" stroke="#666" stroke-width="1"/>
<text x="80" y="220" font-family="Arial" font-size="9" text-anchor="middle" transform="rotate(-90 80 220)">71.8m</text>

<!-- Nordpfeil -->
<g transform="translate(580,350)">
  <path d="M0,-20 L8,0 L0,20 L-8,0 Z" fill="#333"/>
  <text x="0" y="35" font-family="Arial" font-size="12" text-anchor="middle" font-weight="bold">N</text>
</g>

<!-- Massstab -->
<g transform="translate(540,420)">
  <line x1="0" y1="0" x2="100" y2="0" stroke="#333" stroke-width="2"/>
  <line x1="0" y1="-5" x2="0" y2="5" stroke="#333" stroke-width="2"/>
  <line x1="100" y1="-5" x2="100" y2="5" stroke="#333" stroke-width="2"/>
  <text x="50" y="-10" font-family="Arial" font-size="10" text-anchor="middle">20m</text>
</g>

<!-- Legende -->
<g transform="translate(20,330)">
  <text x="0" y="0" font-family="Arial" font-size="12" font-weight="bold">Legende:</text>
  <rect x="0" y="10" width="15" height="10" fill="url(#hatch)" stroke="#333"/>
  <text x="20" y="20" font-family="Arial" font-size="9">Gebaeudewand</text>
  <circle cx="7" cy="35" r="3" fill="#CC0000"/>
  <text x="20" y="40" font-family="Arial" font-size="9">Geruest-Zugang</text>
  <rect x="0" y="50" width="15" height="10" fill="none" stroke="#0066CC" stroke-dasharray="2,2"/>
  <text x="20" y="60" font-family="Arial" font-size="9">Geruestzone</text>
</g>

<!-- Gebaeudedaten -->
<g transform="translate(20,400)">
  <text x="0" y="0" font-family="Arial" font-size="10" font-weight="bold">Gebaeudedaten:</text>
  <text x="0" y="15" font-family="Arial" font-size="9">Grundflaeche: 2115 m²</text>
  <text x="0" y="30" font-family="Arial" font-size="9">Umfang: 397.4 m</text>
  <text x="0" y="45" font-family="Arial" font-size="9">Max. Hoehe: 51.8 m</text>
</g>

</svg>
```


--------------------------------------------------------------------------------
## ANSICHT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Fassadenansicht (Elevation)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Helvetiaplatz 5 3005 Bern
- **EGID:** 2243518
- **Koordinaten (LV95):** E 600810, N 199108
- **Gebaeudename:** Bernisches Historisches Museum
- **Gebaeudetyp:** Museum
- **Baustil:** Historismus (Schloss)
- **Baujahr:** 1894
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 44.0 m
- **Firsthoehe:** 51.8 m
- **Geschosse:** -
- **Grundflaeche:** 2115 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 36 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 93.9m × 71.8m
- **Umfang:** 397.4 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 535.3 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 535.3 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach_mit_turm
- **Dachneigung:** 12°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Hauptbau | hauptgebaeude | 25.0m | 35.0m | 35.0m | Standard |
| Seitenfluegel | anbau | 18.0m | 25.0m | 25.0m | Standard |
| Eckturm | turm | 35.0m | 50.0m | 50.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Hauptbau): **35.0m**
- Zone 2 (Seitenfluegel): **25.0m**
- Zone 3 (Eckturm): **50.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 22.7 | O |
| 1 | 6.8 | N |
| 2 | 3.4 | O |
| 3 | 19.2 | O |
| 4 | 4.1 | N |
| 5 | 5.8 | O |
| 6 | 3.1 | S |
| 7 | 9.1 | O |
| ... | (27 weitere) | ... |

- **Laengste Fassade:** 29.9 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | N | 9% | - |
| Z2 | NO | 9% | - |
| Z3 | O | 91% | - |
| Z4 | W | 55% | - |
| Z5 | SW | 7% | - |
| Z6 | N | 91% | - |
| Z7 | S | 32% | - |
| Z8 | W | 16% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenraeume sichtbar!
- **Schraffur:** url(#hatch) fuer alle Fassadenflaechen
- **Terrain-Linie:** bei +/-0.00 = 535.3 m ue.M.
- **Geruest:** VOR der Fassade (Staender blau, Belaege braun)
- **Hoehenskala:** Links (+/-0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: ansicht

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Hauptbau' (35.0m) deutlich unter API-Traufhoehe (44.0m) - Zone-Daten pruefen!
- Zone 'Seitenfluegel' (25.0m) deutlich unter API-Traufhoehe (44.0m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:13*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## ANSICHT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>
  
  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>
  
  <!-- Terrain-Linie -->
  <line x1="100" y1="400" x2="600" y2="400" stroke="#666" stroke-width="2"/>
  <pattern id="ground-fill" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>
  <rect x="100" y="400" width="500" height="60" fill="url(#ground-fill)"/>
  
  <!-- Seitenfluegel (25m hoch) -->
  <rect x="150" y="150" width="120" height="250" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
  
  <!-- Hauptbau (35m hoch) -->
  <rect x="270" y="50" width="180" height="350" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
  
  <!-- Eckturm (50m hoch) -->
  <rect x="450" y="0" width="80" height="400" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
  
  <!-- Satteldach Hauptbau -->
  <polygon points="270,50 360,30 450,50 450,50 270,50" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
  
  <!-- Satteldach Seitenfluegel -->
  <polygon points="150,150 235,130 270,150 270,150 150,150" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
  
  <!-- Turmspitze -->
  <polygon points="450,0 490,0 515,20 530,0 530,0 450,0" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
  
  <!-- Geruest Staender -->
  <g stroke="#0066CC" stroke-width="3">
    <!-- Seitenfluegel Geruest -->
    <line x1="130" y1="130" x2="130" y2="420"/>
    <line x1="160" y1="130" x2="160" y2="420"/>
    <line x1="200" y1="130" x2="200" y2="420"/>
    <line x1="240" y1="130" x2="240" y2="420"/>
    <line x1="290" y1="130" x2="290" y2="420"/>
    
    <!-- Hauptbau Geruest -->
    <line x1="250" y1="30" x2="250" y2="420"/>
    <line x1="300" y1="30" x2="300" y2="420"/>
    <line x1="350" y1="30" x2="350" y2="420"/>
    <line x1="400" y1="30" x2="400" y2="420"/>
    <line x1="470" y1="30" x2="470" y2="420"/>
    
    <!-- Turm Geruest -->
    <line x1="430" y1="0" x2="430" y2="420"/>
    <line x1="480" y1="0" x2="480" y2="420"/>
    <line x1="520" y1="0" x2="520" y2="420"/>
    <line x1="550" y1="0" x2="550" y2="420"/>
  </g>
  
  <!-- Geruest Belaege -->
  <g stroke="#8B4513" stroke-width="2" fill="#8B4513">
    <!-- 1. Lage -->
    <rect x="130" y="340" width="420" height="4"/>
    <!-- 2. Lage -->
    <rect x="130" y="280" width="420" height="4"/>
    <!-- 3. Lage -->
    <rect x="130" y="220" width="420" height="4"/>
    <!-- 4. Lage -->
    <rect x="130" y="160" width="420" height="4"/>
    <!-- 5. Lage -->
    <rect x="250" y="100" width="300" height="4"/>
    <!-- 6. Lage -->
    <rect x="250" y="40" width="300" height="4"/>
    <!-- 7. Lage (nur Turm) -->
    <rect x="430" y="20" width="120" height="4"/>
  </g>
  
  <!-- Verankerungen -->
  <g stroke="#CC0000" stroke-width="1.5" stroke-dasharray="3,3">
    <line x1="160" y1="320" x2="180" y2="320"/>
    <line x1="200" y1="260" x2="220" y2="260"/>
    <line x1="300" y1="200" x2="320" y2="200"/>
    <line x1="350" y1="140" x2="370" y2="140"/>
    <line x1="400" y1="80" x2="420" y2="80"/>
    <line x1="480" y1="180" x2="500" y2="180"/>
    <line x1="520" y1="100" x2="530" y2="100"/>
  </g>
  
  <!-- Hoehenskala links -->
  <g font-family="Arial" font-size="12" text-anchor="end">
    <line x1="90" y1="400" x2="95" y2="400" stroke="#000"/>
    <text x="85" y="405">+/-0.00</text>
    
    <line x1="90" y1="150" x2="95" y2="150" stroke="#000"/>
    <text x="85" y="155">+25.0m</text>
    
    <line x1="90" y1="50" x2="95" y2="50" stroke="#000"/>
    <text x="85" y="55">+35.0m</text>
    
    <line x1="90" y1="0" x2="95" y2="0" stroke="#000"/>
    <text x="85" y="5">+50.0m</text>
  </g>
  
  <!-- Lagenbeschriftung rechts -->
  <g font-family="Arial" font-size="11" text-anchor="start">
    <text x="570" y="345">1. Lage</text>
    <text x="570" y="285">2. Lage</text>
    <text x="570" y="225">3. Lage</text>
    <text x="570" y="165">4. Lage</text>
    <text x="570" y="105">5. Lage</text>
    <text x="570" y="45">6. Lage</text>
    <text x="570" y="25">7. Lage</text>
  </g>
  
  <!-- Titel -->
  <text x="350" y="30" font-family="Arial" font-size="14" font-weight="bold" text-anchor="middle">Fassadenansicht - Bernisches Historisches Museum</text>
  <text x="350" y="470" font-family="Arial" font-size="10" text-anchor="middle">Helvetiaplatz 5, 3005 Bern - EGID: 2243518</text>
</svg>
```


--------------------------------------------------------------------------------
## SCHNITT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Gebaeudeschnitt (Querschnitt)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Helvetiaplatz 5 3005 Bern
- **EGID:** 2243518
- **Koordinaten (LV95):** E 600810, N 199108
- **Gebaeudename:** Bernisches Historisches Museum
- **Gebaeudetyp:** Museum
- **Baustil:** Historismus (Schloss)
- **Baujahr:** 1894
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 44.0 m
- **Firsthoehe:** 51.8 m
- **Geschosse:** -
- **Grundflaeche:** 2115 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 36 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 93.9m × 71.8m
- **Umfang:** 397.4 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 535.3 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 535.3 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach_mit_turm
- **Dachneigung:** 12°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Hauptbau | hauptgebaeude | 25.0m | 35.0m | 35.0m | Standard |
| Seitenfluegel | anbau | 18.0m | 25.0m | 25.0m | Standard |
| Eckturm | turm | 35.0m | 50.0m | 50.0m | Sonderkonstruktion |

**Hoehen-Zusammenfassung:**
- Zone 1 (Hauptbau): **35.0m**
- Zone 2 (Seitenfluegel): **25.0m**
- Zone 3 (Eckturm): **50.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 22.7 | O |
| 1 | 6.8 | N |
| 2 | 3.4 | O |
| 3 | 19.2 | O |
| 4 | 4.1 | N |
| 5 | 5.8 | O |
| 6 | 3.1 | S |
| 7 | 9.1 | O |
| ... | (27 weitere) | ... |

- **Laengste Fassade:** 29.9 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | N | 9% | - |
| Z2 | NO | 9% | - |
| Z3 | O | 91% | - |
| Z4 | W | 55% | - |
| Z5 | SW | 7% | - |
| Z6 | N | 91% | - |
| Z7 | S | 32% | - |
| Z8 | W | 16% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 3: Gebaeudeschnitt (Querschnitt)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenraeume, Konstruktion, Raumhoehen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei +/-0.00 = 535.3 m ue.M. mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Geruest:** Links und rechts (Staender + Belaege)
- **Schnittmarkierung:** A-A

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: schnitt

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Zone 'Hauptbau' (35.0m) deutlich unter API-Traufhoehe (44.0m) - Zone-Daten pruefen!
- Zone 'Seitenfluegel' (25.0m) deutlich unter API-Traufhoehe (44.0m) - Zone-Daten pruefen!

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:13*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## SCHNITT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Terrain-Linie -->
  <rect x="0" y="410" width="700" height="70" fill="url(#ground)" stroke="#666" stroke-width="1"/>

  <!-- Gerüst links -->
  <!-- Staender -->
  <rect x="60" y="160" width="8" height="250" fill="#0066CC"/>
  <rect x="80" y="160" width="8" height="250" fill="#0066CC"/>
  
  <!-- Belaege -->
  <rect x="50" y="180" width="48" height="6" fill="#8B4513"/>
  <rect x="50" y="220" width="48" height="6" fill="#8B4513"/>
  <rect x="50" y="260" width="48" height="6" fill="#8B4513"/>
  <rect x="50" y="300" width="48" height="6" fill="#8B4513"/>
  <rect x="50" y="340" width="48" height="6" fill="#8B4513"/>
  <rect x="50" y="380" width="48" height="6" fill="#8B4513"/>

  <!-- Hauptbau (35m) - Seitenfluegel -->
  <!-- Äußere Wand links -->
  <rect x="100" y="270" width="20" height="140" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <!-- Innenraum -->
  <rect x="120" y="270" width="60" height="140" fill="#FFFFFF"/>
  <!-- Innenwand -->
  <rect x="180" y="270" width="15" height="140" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Hauptgebäude (35m) - Zentral -->
  <!-- Äußere Wand links -->
  <rect x="195" y="210" width="20" height="200" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <!-- Innenraum -->
  <rect x="215" y="210" width="120" height="200" fill="#FFFFFF"/>
  <!-- Innenwand -->
  <rect x="335" y="210" width="15" height="200" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Turm (50m) - Rechts -->
  <!-- Äußere Wand links -->
  <rect x="350" y="110" width="20" height="300" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <!-- Turmraum -->
  <rect x="370" y="110" width="50" height="300" fill="#FFFFFF"/>
  <!-- Äußere Wand rechts -->
  <rect x="420" y="110" width="20" height="300" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Geschossdecken im Hauptgebäude -->
  <line x1="195" y1="270" x2="350" y2="270" stroke="#333" stroke-width="1"/>
  <line x1="195" y1="330" x2="350" y2="330" stroke="#333" stroke-width="1"/>

  <!-- Geschossdecken im Turm -->
  <line x1="350" y1="180" x2="440" y2="180" stroke="#333" stroke-width="1"/>
  <line x1="350" y1="250" x2="440" y2="250" stroke="#333" stroke-width="1"/>
  <line x1="350" y1="320" x2="440" y2="320" stroke="#333" stroke-width="1"/>

  <!-- Dach Seitenfluegel -->
  <polygon points="100,270 110,250 180,250 195,270" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Dach Hauptgebäude -->
  <polygon points="195,210 225,180 325,180 350,210" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Dach Turm -->
  <polygon points="350,110 395,80 440,110" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Gerüst rechts -->
  <!-- Staender -->
  <rect x="500" y="80" width="8" height="330" fill="#0066CC"/>
  <rect x="520" y="80" width="8" height="330" fill="#0066CC"/>
  
  <!-- Belaege -->
  <rect x="490" y="100" width="48" height="6" fill="#8B4513"/>
  <rect x="490" y="140" width="48" height="6" fill="#8B4513"/>
  <rect x="490" y="180" width="48" height="6" fill="#8B4513"/>
  <rect x="490" y="220" width="48" height="6" fill="#8B4513"/>
  <rect x="490" y="260" width="48" height="6" fill="#8B4513"/>
  <rect x="490" y="300" width="48" height="6" fill="#8B4513"/>
  <rect x="490" y="340" width="48" height="6" fill="#8B4513"/>
  <rect x="490" y="380" width="48" height="6" fill="#8B4513"/>

  <!-- Verankerungen -->
  <line x1="88" y1="280" x2="100" y2="280" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,4"/>
  <line x1="88" y1="320" x2="100" y2="320" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,4"/>
  <line x1="490" y1="200" x2="440" y2="200" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,4"/>
  <line x1="490" y1="280" x2="440" y2="280" stroke="#CC0000" stroke-width="2" stroke-dasharray="4,4"/>

  <!-- Beschriftung -->
  <text x="20" y="35" font-family="Arial" font-size="18" font-weight="bold" fill="#333">GEBÄUDESCHNITT A-A</text>
  <text x="20" y="55" font-family="Arial" font-size="12" fill="#666">Bernisches Historisches Museum</text>
  
  <!-- Höhenangaben -->
  <text x="450" y="95" font-family="Arial" font-size="10" fill="#333">50.0m</text>
  <text x="280" y="195" font-family="Arial" font-size="10" fill="#333">35.0m</text>
  <text x="130" y="255" font-family="Arial" font-size="10" fill="#333">25.0m</text>
  
  <!-- Schnittmarkierung -->
  <text x="50" y="430" font-family="Arial" font-size="12" font-weight="bold" fill="#333">A</text>
  <text x="620" y="430" font-family="Arial" font-size="12" font-weight="bold" fill="#333">A</text>
  
  <!-- Referenzhöhe -->
  <line x1="30" y1="410" x2="40" y2="410" stroke="#333" stroke-width="1"/>
  <text x="5" y="415" font-family="Arial" font-size="8" fill="#333">±0.00</text>
</svg>
```


================================================================================
# GEBÄUDE 10: Hotel Schweizerhof
================================================================================

## Adresse
Bahnhofplatz 11, 3011 Bern

## EGID
1230691

## Recherche-Ergebnis (aus Pipeline)

- **Gebäudename:** Hotel Schweizerhof Bern
- **Gebäudetyp:** Hotel
- **Architekturstil:** Historismus
- **Baujahr:** 1859
- **Komplexität:** moderate
- **Traufhöhe:** 23.1 m
- **Firsthöhe:** 27.2 m

### Erkannte Zonen

**Zone 1: Hauptgebaeude**
- Typ: hauptgebaeude
- Traufhöhe: 18.0 m
- Firsthöhe: 25.0 m
- Sonderkonstruktion: Nein

**Zone 2: Dachaufbau**
- Typ: anbau
- Traufhöhe: 25.0 m
- Firsthöhe: 30.0 m
- Sonderkonstruktion: Nein


--------------------------------------------------------------------------------
## GRUNDRISS-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Grundriss (Draufsicht)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Bahnhofplatz 11 3011 Bern
- **EGID:** 1230691
- **Koordinaten (LV95):** E 600174, N 199743
- **Gebaeudename:** Hotel Schweizerhof Bern
- **Gebaeudetyp:** Hotel
- **Baustil:** Historismus
- **Baujahr:** 1859
- **Komplexitaet:** MODERATE

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 23.1 m
- **Firsthoehe:** 27.2 m
- **Geschosse:** 6
- **Grundflaeche:** 1591 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 14 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 40.0m × 68.5m
- **Umfang:** 187.2 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 540.9 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 540.9 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** mansarddach
- **Dachneigung:** 7°
- **First-Ausrichtung:** O-W
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Hauptgebaeude | hauptgebaeude | 18.0m | 25.0m | 25.0m | Standard |
| Dachaufbau | anbau | 25.0m | 30.0m | 30.0m | Standard |

**Hoehen-Zusammenfassung:**
- Zone 1 (Hauptgebaeude): **25.0m**
- Zone 2 (Dachaufbau): **30.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 4.5 | O |
| 1 | 7.8 | NO |
| 2 | 4.5 | N |
| 3 | 17.1 | O |
| 4 | 18.7 | S |
| 5 | 20.2 | SO |
| 6 | 7.2 | S |
| 7 | 15.2 | S |
| ... | (5 weitere) | ... |

- **Laengste Fassade:** 54.1 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 39% | - |
| Z2 | SO | 98% | - |
| Z3 | W | 4% | - |
| Z4 | N | 90% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** Rechteckige Huelle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung
- **Zonen:** Farblich unterscheiden, Innenhoefe markieren

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: grundriss

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Hoehe 27.2m sehr hoch fuer 6 Geschosse (moeglicherweise Turm)

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:14*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## GRUNDRISS-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Titel -->
  <text x="350" y="25" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold">GRUNDRISS - Hotel Schweizerhof Bern</text>
  <text x="350" y="40" text-anchor="middle" font-family="Arial" font-size="10">Bahnhofplatz 11, 3011 Bern - EGID: 1230691</text>

  <!-- Geruestzone (aeussere Begrenzung) -->
  <rect x="150" y="80" width="400" height="280" fill="none" stroke="#0066CC" stroke-width="1" stroke-dasharray="3,3"/>
  <text x="155" y="95" font-family="Arial" font-size="8" fill="#0066CC">Gerüstzone (1m Abstand)</text>

  <!-- Hauptgebäude Zone 1 (25.0m hoch) -->
  <rect x="160" y="90" width="250" height="180" fill="url(#hatch)" stroke="#000" stroke-width="2"/>
  <text x="285" y="185" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">Hauptgebäude</text>
  <text x="285" y="200" text-anchor="middle" font-family="Arial" font-size="8">H: 25.0m</text>

  <!-- Dachaufbau Zone 2 (30.0m hoch) -->
  <rect x="180" y="110" width="210" height="80" fill="url(#cut-hatch)" stroke="#000" stroke-width="2"/>
  <text x="285" y="150" text-anchor="middle" font-family="Arial" font-size="9" font-weight="bold">Dachaufbau</text>
  <text x="285" y="165" text-anchor="middle" font-family="Arial" font-size="7">H: 30.0m</text>

  <!-- Fassadenlängen Beschriftung -->
  <!-- Ostfassade -->
  <line x1="160" y1="85" x2="410" y2="85" stroke="#666" stroke-width="0.5"/>
  <text x="285" y="80" text-anchor="middle" font-family="Arial" font-size="8">68.5m (O)</text>

  <!-- Nordfassade -->
  <line x1="155" y1="90" x2="155" y2="270" stroke="#666" stroke-width="0.5"/>
  <text x="145" y="180" text-anchor="middle" font-family="Arial" font-size="8" transform="rotate(-90 145 180)">40.0m (N)</text>

  <!-- Südfassade -->
  <line x1="415" y1="90" x2="415" y2="270" stroke="#666" stroke-width="0.5"/>
  <text x="425" y="180" text-anchor="middle" font-family="Arial" font-size="8" transform="rotate(90 425 180)">40.0m (S)</text>

  <!-- Westfassade -->
  <line x1="160" y1="275" x2="410" y2="275" stroke="#666" stroke-width="0.5"/>
  <text x="285" y="285" text-anchor="middle" font-family="Arial" font-size="8">68.5m (W)</text>

  <!-- Gerüst-Zugänge -->
  <!-- Z1: Ostfassade 39% -->
  <circle cx="257" cy="90" r="4" fill="#CC0000"/>
  <text x="257" y="105" text-anchor="middle" font-family="Arial" font-size="7" fill="#CC0000">Z1</text>

  <!-- Z2: Südfassade 98% -->
  <circle cx="410" cy="266" r="4" fill="#CC0000"/>
  <text x="420" y="270" text-anchor="start" font-family="Arial" font-size="7" fill="#CC0000">Z2</text>

  <!-- Z3: Westfassade 4% -->
  <circle cx="167" cy="270" r="4" fill="#CC0000"/>
  <text x="167" y="280" text-anchor="middle" font-family="Arial" font-size="7" fill="#CC0000">Z3</text>

  <!-- Z4: Nordfassade 90% -->
  <circle cx="160" cy="126" r="4" fill="#CC0000"/>
  <text x="145" y="130" text-anchor="end" font-family="Arial" font-size="7" fill="#CC0000">Z4</text>

  <!-- Nordpfeil -->
  <g transform="translate(600,100)">
    <path d="M0,0 L10,20 L0,15 L-10,20 Z" fill="#000"/>
    <text x="0" y="35" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">N</text>
  </g>

  <!-- Maßstab -->
  <g transform="translate(50,400)">
    <line x1="0" y1="0" x2="100" y2="0" stroke="#000" stroke-width="2"/>
    <line x1="0" y1="-5" x2="0" y2="5" stroke="#000" stroke-width="1"/>
    <line x1="100" y1="-5" x2="100" y2="5" stroke="#000" stroke-width="1"/>
    <text x="50" y="15" text-anchor="middle" font-family="Arial" font-size="8">20m</text>
    <text x="50" y="25" text-anchor="middle" font-family="Arial" font-size="7">Maßstab 1:500</text>
  </g>

  <!-- Legende -->
  <g transform="translate(500,300)">
    <text x="0" y="0" font-family="Arial" font-size="10" font-weight="bold">Legende:</text>
    
    <rect x="0" y="10" width="15" height="10" fill="url(#hatch)" stroke="#000"/>
    <text x="20" y="18" font-family="Arial" font-size="8">Hauptgebäude</text>
    
    <rect x="0" y="25" width="15" height="10" fill="url(#cut-hatch)" stroke="#000"/>
    <text x="20" y="33" font-family="Arial" font-size="8">Dachaufbau</text>
    
    <line x1="0" y1="45" x2="15" y2="45" stroke="#0066CC" stroke-dasharray="3,3"/>
    <text x="20" y="48" font-family="Arial" font-size="8">Gerüstzone</text>
    
    <circle cx="7" cy="55" r="3" fill="#CC0000"/>
    <text x="20" y="58" font-family="Arial" font-size="8">Zugang</text>
  </g>

  <!-- Gebäudedaten -->
  <g transform="translate(50,300)">
    <text x="0" y="0" font-family="Arial" font-size="9" font-weight="bold">Gebäudedaten:</text>
    <text x="0" y="15" font-family="Arial" font-size="8">Grundfläche: 1591 m²</text>
    <text x="0" y="25" font-family="Arial" font-size="8">Geschosse: 6</text>
    <text x="0" y="35" font-family="Arial" font-size="8">Baujahr: 1859</text>
    <text x="0" y="45" font-family="Arial" font-size="8">Dachform: Mansarddach</text>
    <text x="0" y="55" font-family="Arial" font-size="8">Max. Höhe: 30.0m</text>
    <text x="0" y="65" font-family="Arial" font-size="8">Umfang: 187.2m</text>
  </g>

  <!-- Koordinaten -->
  <text x="50" y="460" font-family="Arial" font-size="8">LV95: E 600174, N 199743 | Höhe: 540.9 m ü.M.</text>
</svg>
```


--------------------------------------------------------------------------------
## ANSICHT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Fassadenansicht (Elevation)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Bahnhofplatz 11 3011 Bern
- **EGID:** 1230691
- **Koordinaten (LV95):** E 600174, N 199743
- **Gebaeudename:** Hotel Schweizerhof Bern
- **Gebaeudetyp:** Hotel
- **Baustil:** Historismus
- **Baujahr:** 1859
- **Komplexitaet:** MODERATE

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 23.1 m
- **Firsthoehe:** 27.2 m
- **Geschosse:** 6
- **Grundflaeche:** 1591 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 14 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 40.0m × 68.5m
- **Umfang:** 187.2 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 540.9 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 540.9 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** mansarddach
- **Dachneigung:** 7°
- **First-Ausrichtung:** O-W
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Hauptgebaeude | hauptgebaeude | 18.0m | 25.0m | 25.0m | Standard |
| Dachaufbau | anbau | 25.0m | 30.0m | 30.0m | Standard |

**Hoehen-Zusammenfassung:**
- Zone 1 (Hauptgebaeude): **25.0m**
- Zone 2 (Dachaufbau): **30.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 4.5 | O |
| 1 | 7.8 | NO |
| 2 | 4.5 | N |
| 3 | 17.1 | O |
| 4 | 18.7 | S |
| 5 | 20.2 | SO |
| 6 | 7.2 | S |
| 7 | 15.2 | S |
| ... | (5 weitere) | ... |

- **Laengste Fassade:** 54.1 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 39% | - |
| Z2 | SO | 98% | - |
| Z3 | W | 4% | - |
| Z4 | N | 90% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenraeume sichtbar!
- **Schraffur:** url(#hatch) fuer alle Fassadenflaechen
- **Terrain-Linie:** bei +/-0.00 = 540.9 m ue.M.
- **Geruest:** VOR der Fassade (Staender blau, Belaege braun)
- **Hoehenskala:** Links (+/-0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: ansicht

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Hoehe 27.2m sehr hoch fuer 6 Geschosse (moeglicherweise Turm)

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:14*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## ANSICHT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Terrain-Linie -->
  <line x1="100" y1="380" x2="600" y2="380" stroke="#666" stroke-width="2" fill="url(#ground)"/>
  <rect x="100" y="380" width="500" height="20" fill="url(#ground)"/>

  <!-- Zone 1: Hauptgebäude (25.0m hoch) -->
  <rect x="150" y="180" width="400" height="200" fill="url(#hatch)" stroke="#000" stroke-width="1"/>

  <!-- Zone 2: Dachaufbau (30.0m hoch, weitere 5m) -->
  <rect x="200" y="140" width="300" height="40" fill="url(#hatch)" stroke="#000" stroke-width="1"/>

  <!-- Mansarddach (7° Neigung) -->
  <polygon points="190,180 210,140 490,140 510,180" fill="url(#hatch)" stroke="#000" stroke-width="1"/>

  <!-- Gerüst-Ständer (vertikal, blau) -->
  <line x1="120" y1="100" x2="120" y2="390" stroke="#0066CC" stroke-width="3"/>
  <line x1="180" y1="100" x2="180" y2="390" stroke="#0066CC" stroke-width="3"/>
  <line x1="240" y1="100" x2="240" y2="390" stroke="#0066CC" stroke-width="3"/>
  <line x1="300" y1="100" x2="300" y2="390" stroke="#0066CC" stroke-width="3"/>
  <line x1="360" y1="100" x2="360" y2="390" stroke="#0066CC" stroke-width="3"/>
  <line x1="420" y1="100" x2="420" y2="390" stroke="#0066CC" stroke-width="3"/>
  <line x1="480" y1="100" x2="480" y2="390" stroke="#0066CC" stroke-width="3"/>
  <line x1="540" y1="100" x2="540" y2="390" stroke="#0066CC" stroke-width="3"/>
  <line x1="580" y1="100" x2="580" y2="390" stroke="#0066CC" stroke-width="3"/>

  <!-- Gerüst-Beläge (horizontal, braun) -->
  <line x1="120" y1="360" x2="580" y2="360" stroke="#8B4513" stroke-width="4"/>
  <line x1="120" y1="320" x2="580" y2="320" stroke="#8B4513" stroke-width="4"/>
  <line x1="120" y1="280" x2="580" y2="280" stroke="#8B4513" stroke-width="4"/>
  <line x1="120" y1="240" x2="580" y2="240" stroke="#8B4513" stroke-width="4"/>
  <line x1="120" y1="200" x2="580" y2="200" stroke="#8B4513" stroke-width="4"/>
  <line x1="120" y1="160" x2="580" y2="160" stroke="#8B4513" stroke-width="4"/>
  <line x1="120" y1="120" x2="580" y2="120" stroke="#8B4513" stroke-width="4"/>

  <!-- Verankerungen (gestrichelt, rot) -->
  <line x1="180" y1="340" x2="150" y2="340" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
  <line x1="300" y1="300" x2="270" y2="300" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
  <line x1="420" y1="260" x2="390" y2="260" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>
  <line x1="540" y1="220" x2="510" y2="220" stroke="#CC0000" stroke-width="2" stroke-dasharray="3,3"/>

  <!-- Fenster (vereinfacht) -->
  <rect x="170" y="200" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="210" y="200" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="250" y="200" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="290" y="200" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="330" y="200" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="370" y="200" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="410" y="200" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="450" y="200" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="490" y="200" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>

  <rect x="170" y="240" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="210" y="240" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="250" y="240" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="290" y="240" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="330" y="240" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="370" y="240" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="410" y="240" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="450" y="240" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>
  <rect x="490" y="240" width="15" height="20" fill="#FFFFFF" stroke="#000" stroke-width="0.5"/>

  <!-- Höhenskala links -->
  <line x1="80" y1="380" x2="85" y2="380" stroke="#000" stroke-width="1"/>
  <text x="75" y="385" font-family="Arial" font-size="10" text-anchor="end">±0.00</text>
  
  <line x1="80" y1="180" x2="85" y2="180" stroke="#000" stroke-width="1"/>
  <text x="75" y="185" font-family="Arial" font-size="10" text-anchor="end">+25.0m</text>
  
  <line x1="80" y1="140" x2="85" y2="140" stroke="#000" stroke-width="1"/>
  <text x="75" y="145" font-family="Arial" font-size="10" text-anchor="end">+30.0m</text>

  <!-- Höhen-Linie -->
  <line x1="80" y1="100" x2="80" y2="400" stroke="#000" stroke-width="1"/>

  <!-- Lagenbeschriftung rechts -->
  <text x="610" y="375" font-family="Arial" font-size="10">1. Lage</text>
  <text x="610" y="335" font-family="Arial" font-size="10">2. Lage</text>
  <text x="610" y="295" font-family="Arial" font-size="10">3. Lage</text>
  <text x="610" y="255" font-family="Arial" font-size="10">4. Lage</text>
  <text x="610" y="215" font-family="Arial" font-size="10">5. Lage</text>
  <text x="610" y="175" font-family="Arial" font-size="10">6. Lage</text>
  <text x="610" y="135" font-family="Arial" font-size="10">7. Lage</text>

  <!-- Titel -->
  <text x="350" y="30" font-family="Arial" font-size="14" font-weight="bold" text-anchor="middle">Fassadenansicht - Hotel Schweizerhof Bern</text>
  <text x="350" y="50" font-family="Arial" font-size="10" text-anchor="middle">Bahnhofplatz 11, 3011 Bern | EGID: 1230691</text>

  <!-- Zugänge -->
  <circle cx="250" cy="390" r="3" fill="#00CC00"/>
  <text x="250" y="410" font-family="Arial" font-size="8" text-anchor="middle">Z1</text>
  
  <circle cx="450" cy="390" r="3" fill="#00CC00"/>
  <text x="450" y="410" font-family="Arial" font-size="8" text-anchor="middle">Z2</text>
</svg>
```


--------------------------------------------------------------------------------
## SCHNITT-PROMPT
--------------------------------------------------------------------------------

```
# SVG-Generierung: Gebaeudeschnitt (Querschnitt)

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Bahnhofplatz 11 3011 Bern
- **EGID:** 1230691
- **Koordinaten (LV95):** E 600174, N 199743
- **Gebaeudename:** Hotel Schweizerhof Bern
- **Gebaeudetyp:** Hotel
- **Baustil:** Historismus
- **Baujahr:** 1859
- **Komplexitaet:** MODERATE

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 23.1 m
- **Firsthoehe:** 27.2 m
- **Geschosse:** 6
- **Grundflaeche:** 1591 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 14 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 40.0m × 68.5m
- **Umfang:** 187.2 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 540.9 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 540.9 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** mansarddach
- **Dachneigung:** 7°
- **First-Ausrichtung:** O-W
- **Konfidenz:** 50%

## 6. Hoehenzonen
### Hoehen pro Zone (KRITISCH fuer Proportionen!)

| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |
|------|-----|------------|------------|---------------|---------|
| Hauptgebaeude | hauptgebaeude | 18.0m | 25.0m | 25.0m | Standard |
| Dachaufbau | anbau | 25.0m | 30.0m | 30.0m | Standard |

**Hoehen-Zusammenfassung:**
- Zone 1 (Hauptgebaeude): **25.0m**
- Zone 2 (Dachaufbau): **30.0m**

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 4.5 | O |
| 1 | 7.8 | NO |
| 2 | 4.5 | N |
| 3 | 17.1 | O |
| 4 | 18.7 | S |
| 5 | 20.2 | SO |
| 6 | 7.2 | S |
| 7 | 15.2 | S |
| ... | (5 weitere) | ... |

- **Laengste Fassade:** 54.1 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 39% | - |
| Z2 | SO | 98% | - |
| Z3 | W | 4% | - |
| Z4 | N | 90% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```

## 11. Anforderungen pro SVG

### SVG 3: Gebaeudeschnitt (Querschnitt)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenraeume, Konstruktion, Raumhoehen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei +/-0.00 = 540.9 m ue.M. mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Geruest:** Links und rechts (Staender + Belaege)
- **Schnittmarkierung:** A-A

## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: schnitt

**NUR SVG-Code**, keine Erklaerungen.

## [!] Warnungen
- Hoehe 27.2m sehr hoch fuer 6 Geschosse (moeglicherweise Turm)

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 17:15*
*https://cooperative-commitment-production.up.railway.app*
```

--------------------------------------------------------------------------------
## SCHNITT-SVG (von Claude-API generiert)
--------------------------------------------------------------------------------

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- LOCKERE Schraffur fuer Aussenflaechen -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>

    <!-- DICHTE Schraffur fuer Schnittflaechen -->
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>

    <!-- Terrain/Boden -->
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>

    <!-- Kupfer-Gradient NUR fuer Kuppeln -->
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <!-- Hintergrund -->
  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Terrain/Boden Linie -->
  <rect x="0" y="420" width="700" height="30" fill="url(#ground)" stroke="#333" stroke-width="1"/>
  
  <!-- Terrain Referenz -->
  <text x="10" y="440" font-family="Arial" font-size="10" fill="#333">±0.00 = 540.9 m ü.M.</text>

  <!-- Geruest Links -->
  <g stroke="#0066CC" stroke-width="2" fill="none">
    <!-- Staender -->
    <line x1="80" y1="420" x2="80" y2="120"/>
    <line x1="120" y1="420" x2="120" y2="120"/>
    <line x1="100" y1="420" x2="100" y2="110"/>
    
    <!-- Belaege -->
    <rect x="80" y="380" width="40" height="3" fill="#8B4513"/>
    <rect x="80" y="320" width="40" height="3" fill="#8B4513"/>
    <rect x="80" y="260" width="40" height="3" fill="#8B4513"/>
    <rect x="80" y="200" width="40" height="3" fill="#8B4513"/>
    <rect x="80" y="140" width="40" height="3" fill="#8B4513"/>
    
    <!-- Querversteifungen -->
    <line x1="80" y1="380" x2="120" y2="380"/>
    <line x1="80" y1="320" x2="120" y2="320"/>
    <line x1="80" y1="260" x2="120" y2="260"/>
    <line x1="80" y1="200" x2="120" y2="200"/>
    <line x1="80" y1="140" x2="120" y2="140"/>
  </g>

  <!-- Geruest Rechts -->
  <g stroke="#0066CC" stroke-width="2" fill="none">
    <!-- Staender -->
    <line x1="580" y1="420" x2="580" y2="120"/>
    <line x1="620" y1="420" x2="620" y2="120"/>
    <line x1="600" y1="420" x2="600" y2="110"/>
    
    <!-- Belaege -->
    <rect x="580" y="380" width="40" height="3" fill="#8B4513"/>
    <rect x="580" y="320" width="40" height="3" fill="#8B4513"/>
    <rect x="580" y="260" width="40" height="3" fill="#8B4513"/>
    <rect x="580" y="200" width="40" height="3" fill="#8B4513"/>
    <rect x="580" y="140" width="40" height="3" fill="#8B4513"/>
    
    <!-- Querversteifungen -->
    <line x1="580" y1="380" x2="620" y2="380"/>
    <line x1="580" y1="320" x2="620" y2="320"/>
    <line x1="580" y1="260" x2="620" y2="260"/>
    <line x1="580" y1="200" x2="620" y2="200"/>
    <line x1="580" y1="140" x2="620" y2="140"/>
  </g>

  <!-- Hauptgebaeude - Geschnittene Aussenwaende (Zone 1: 25.0m) -->
  <!-- Linke Aussenwand -->
  <rect x="140" y="220" width="20" height="200" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Rechte Aussenwand -->
  <rect x="540" y="220" width="20" height="200" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>

  <!-- Dachaufbau - Geschnittene Waende (Zone 2: 30.0m) -->
  <!-- Linke Dachaufbau-Wand -->
  <rect x="200" y="140" width="15" height="80" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  
  <!-- Rechte Dachaufbau-Wand -->
  <rect x="485" y="140" width="15" height="80" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>

  <!-- Innenraeume (WEISS/LEER) -->
  <rect x="160" y="220" width="380" height="200" fill="#FFFFFF" stroke="none"/>
  <rect x="215" y="140" width="270" height="80" fill="#FFFFFF" stroke="none"/>

  <!-- Geschossdecken -->
  <g stroke="#333" stroke-width="1" fill="none">
    <line x1="140" y1="380" x2="560" y2="380"/> <!-- EG Decke -->
    <line x1="140" y1="350" x2="560" y2="350"/> <!-- 1. OG Decke -->
    <line x1="140" y1="320" x2="560" y2="320"/> <!-- 2. OG Decke -->
    <line x1="140" y1="290" x2="560" y2="290"/> <!-- 3. OG Decke -->
    <line x1="140" y1="260" x2="560" y2="260"/> <!-- 4. OG Decke -->
    <line x1="140" y1="230" x2="560" y2="230"/> <!-- 5. OG Decke -->
    <line x1="200" y1="200" x2="500" y2="200"/> <!-- Dachgeschoss Decke -->
  </g>

  <!-- Mansarddach -->
  <g stroke="#333" stroke-width="2" fill="url(#hatch)">
    <polygon points="200,140 215,220 485,220 500,140 350,120"/>
  </g>

  <!-- Verankerungen -->
  <g stroke="#CC0000" stroke-width="2" stroke-dasharray="5,3" fill="none">
    <line x1="120" y1="380" x2="140" y2="380"/>
    <line x1="120" y1="320" x2="140" y2="320"/>
    <line x1="120" y1="260" x2="140" y2="260"/>
    <line x1="120" y1="200" x2="200" y2="200"/>
    
    <line x1="580" y1="380" x2="560" y2="380"/>
    <line x1="580" y1="320" x2="560" y2="320"/>
    <line x1="580" y1="260" x2="560" y2="260"/>
    <line x1="580" y1="200" x2="500" y2="200"/>
  </g>

  <!-- Hoehen-Beschriftung -->
  <g font-family="Arial" font-size="10" fill="#333">
    <text x="50" y="320" transform="rotate(-90 50 320)">25.0m (Zone 1)</text>
    <text x="650" y="280" transform="rotate(-90 650 280)">30.0m (Zone 2)</text>
    
    <!-- Geschoss-Nummern -->
    <text x="30" y="425">UG</text>
    <text x="30" y="395">EG</text>
    <text x="30" y="365">1.OG</text>
    <text x="30" y="335">2.OG</text>
    <text x="30" y="305">3.OG</text>
    <text x="30" y="275">4.OG</text>
    <text x="30" y="245">5.OG</text>
    <text x="30" y="215">DG</text>
  </g>

  <!-- Titel und Schnittmarkierung -->
  <g font-family="Arial" font-size="12" font-weight="bold" fill="#333">
    <text x="300" y="30">GEBÄUDESCHNITT A-A</text>
    <text x="280" y="50">Hotel Schweizerhof Bern</text>
  </g>
  
  <g font-family="Arial" font-size="10" fill="#666">
    <text x="290" y="65">Bahnhofplatz 11, 3011 Bern</text>
    <text x="320" y="80">EGID: 1230691</text>
  </g>

  <!-- Schnittmarkierungen -->
  <g stroke="#CC0000" stroke-width="2" fill="#CC0000">
    <circle cx="140" cy="100" r="3"/>
    <text x="145" y="105" font-family="Arial" font-size="10" fill="#CC0000">A</text>
    <circle cx="560" cy="100" r="3"/>
    <text x="565" y="105" font-family="Arial" font-size="10" fill="#CC0000">A</text>
  </g>
</svg>
```


================================================================================
# ZUSAMMENFASSUNG & ANALYSE-AUFFORDERUNG
================================================================================

## Statistik

- **Getestete Gebäude:** 10
- **Generierte SVGs:** 30
- **Erfolgsrate:** 100.0%

## Bitte analysiere nun:

1. **Generiere die SVGs** basierend auf den Prompts oben
2. **Vergleiche** mit den API-generierten SVGs
3. **Bewerte** die Prompt-Qualität
4. **Erstelle** priorisierte Verbesserungsvorschläge

Fokussiere besonders auf:
- Proportionen und Maßstäbe
- Zonen-Darstellung (werden alle Zonen korrekt gezeichnet?)
- Technischer Zeichnungsstil (nicht künstlerisch!)
- Gerüst-Elemente (Ständer, Verankerungen, Zugänge)
- Beschriftungen und Lesbarkeit

---

*Generiert: 20251230_1807*
*Pipeline: SmartBuildingService + Claude Sonnet SVG-Generierung*
