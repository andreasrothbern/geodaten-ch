# SVG-Prompt: Hotel Schweizerhof - Grundriss

## Verwendung

Dieser Prompt ist **identisch** mit dem Prompt der von der Claude API verwendet wird.
Kopiere ihn zu Claude.ai um das SVG zu generieren und vergleiche das Ergebnis.

---

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
