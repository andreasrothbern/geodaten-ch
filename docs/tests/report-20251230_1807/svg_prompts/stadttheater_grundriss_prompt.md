# SVG-Prompt: Stadttheater - Grundriss

## Verwendung

Dieser Prompt ist **identisch** mit dem Prompt der von der Claude API verwendet wird.
Kopiere ihn zu Claude.ai um das SVG zu generieren und vergleiche das Ergebnis.

---

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
