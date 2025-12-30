# SVG-Prompt: Berner Muenster - Grundriss

## Verwendung

Dieser Prompt ist **identisch** mit dem Prompt der von der Claude API verwendet wird.
Kopiere ihn zu Claude.ai um das SVG zu generieren und vergleiche das Ergebnis.

---

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
