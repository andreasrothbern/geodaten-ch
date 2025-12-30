# SVG-Prompt: Einsteinhaus - Schnitt

## Verwendung

Dieser Prompt ist **identisch** mit dem Prompt der von der Claude API verwendet wird.
Kopiere ihn zu Claude.ai um das SVG zu generieren und vergleiche das Ergebnis.

---

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
