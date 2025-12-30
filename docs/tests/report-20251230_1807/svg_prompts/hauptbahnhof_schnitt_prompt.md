# SVG-Prompt: Hauptbahnhof - Schnitt

## Verwendung

Dieser Prompt ist **identisch** mit dem Prompt der von der Claude API verwendet wird.
Kopiere ihn zu Claude.ai um das SVG zu generieren und vergleiche das Ergebnis.

---

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
