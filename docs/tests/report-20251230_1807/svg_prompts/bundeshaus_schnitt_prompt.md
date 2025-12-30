# SVG-Prompt: Bundeshaus - Schnitt

## Verwendung

Dieser Prompt ist **identisch** mit dem Prompt der von der Claude API verwendet wird.
Kopiere ihn zu Claude.ai um das SVG zu generieren und vergleiche das Ergebnis.

---

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
