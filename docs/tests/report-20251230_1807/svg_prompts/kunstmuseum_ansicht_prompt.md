# SVG-Prompt: Kunstmuseum - Ansicht

## Verwendung

Dieser Prompt ist **identisch** mit dem Prompt der von der Claude API verwendet wird.
Kopiere ihn zu Claude.ai um das SVG zu generieren und vergleiche das Ergebnis.

---

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
