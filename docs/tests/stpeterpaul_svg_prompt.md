# SVG-Generierung: Grundriss + Fassadenansicht + Gebaeudeschnitt

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

Erstelle **3 separate SVGs**, jeweils mit `viewBox="0 0 700 480"`:

1. **grundriss.svg** - Draufsicht mit Gebaeudeumriss und Geruestzone
2. **fassadenansicht.svg** - Aussenansicht, vordere Elemente verdecken hintere
3. **gebaeudeschnitt.svg** - Aufgeschnitten, Innenraeume sichtbar und LEER

**NUR SVG-Code**, keine Erklaerungen. Trenne die SVGs mit Kommentar:
`<!-- SVG 1: Grundriss -->`

---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: 2025-12-30 10:55*
*https://cooperative-commitment-production.up.railway.app*
