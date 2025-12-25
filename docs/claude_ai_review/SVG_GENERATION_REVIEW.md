# Claude SVG Generation Review

## Aufgabe für Claude.ai

Bitte prüfe ob die Parameter und Request-Daten korrekt sind für die SVG-Generierung.

---

## 1. Verfügbare Gebäudedaten (EGID 2242547 - Bundeshaus Bern)

```json
{
  "egid": 2242547,
  "address": "Bundesplatz 3, 3011, Bern",
  "building_category": "Gebäude mit teilweiser Wohnnutzung",
  "area_m2": 3697,
  "dimensions": {
    "perimeter_m": 310.04,
    "traufhoehe_m": 14.53,
    "firsthoehe_m": 62.57,
    "gebaeudehoehe_m": 62.57,
    "height_source": "database:swissBUILDINGS3D_3.0"
  },
  "sides": 25,
  "facade_length_total_m": 310.04
}
```

---

## 2. Aktueller Claude API Prompt (Elevation) - AKTUALISIERT 25.12.2025

```
Du bist ein Experte für TECHNISCHE Architekturzeichnungen im SVG-Format.

## KRITISCHE REGEL

Zeichne NUR die Gebäudeteile die in "Höhenzonen" aufgelistet sind!
- KEINE zusätzlichen Elemente hinzufügen (keine Kuppeln, Türme, etc. wenn nicht in Daten)
- KEINE künstlerische Interpretation - NUR was in den Daten steht

## WICHTIG: STIL

TECHNISCH-PROFESSIONELL, NICHT künstlerisch!
- Hintergrund: REINWEISS (#FFFFFF) - KEIN Himmel, KEIN blauer Gradient!
- Gebäude: NUR Schraffur-Pattern, KEINE Vollfarben
- Perspektive: 2D Frontalansicht (Orthogonalprojektion)
- Farben: Graustufen + wenige Akzentfarben (nur Gerüst blau)

## Aufgabe

Erstelle eine **Fassadenansicht** (Elevation) als SVG.

## Gebäudedaten

- Adresse: Bundesplatz 3 3011 Bern
- EGID: 2242547
- Geschosse: 3
- Fassadenbreite: 27.0 m
- Maximale Höhe: 62.6 m   <-- JETZT KORREKT aus Zonen-Daten

## Höhenzonen (NUR DIESE ZEICHNEN!)

   - **Gebäude** (Typ: hauptgebaeude)
     - Gebäudehöhe: 14.5m, Firsthöhe: 62.6m
     - 3 Geschosse

## Darstellung der Zone-Typen (NUR die oben genannten!)

   - hauptgebaeude = Rechteck mit Geschosslinien und Giebeldach, Schraffur

## Anforderungen

1. **Weisser Hintergrund** - `<rect width="100%" height="100%" fill="white"/>`
2. **Terrain unten** - Horizontale Linie bei Y=85% mit `url(#ground)` Pattern
3. **Frontalansicht** - 2D, keine Perspektive, keine 3D-Effekte
4. **Gebäude mit Schraffur** - `fill="url(#hatch)"` für alle Gebäudeteile
5. **Dachform** - Einfaches Satteldach (Dreieck) bei hauptgebaeude, KEINE Kuppel wenn nicht in Daten!
6. **Gerüst VOR Fassade** - Ständer #0066CC (vertikale Linien), Beläge #8B4513
7. **Verankerungen** - Gestrichelte Linien #CC0000, alle 4m vertikal
8. **Höhenskala links** - Beschriftung ±0.00 bis +63m in 5m Schritten
9. **Lagenbeschriftung rechts** - 1. Lage bis 32. Lage (alle 2m Höhe)

## SVG-Patterns (PFLICHT!)

<defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
</defs>

## Farben (STRIKT!)
- Hintergrund: #FFFFFF (weiss) - KEIN Himmel!
- Hauptlinien: #333333 (dunkelgrau)
- Gebäude: url(#hatch) Schraffur
- Gerüst: #0066CC (blau)
- Anker: #CC0000 (rot, gestrichelt)
- Belag: #8B4513 (braun)
- Text: #333333

## Output

SVG mit viewBox="0 0 700 480". NUR SVG, keine Erklärungen.
```

---

## 3. Identifizierte Probleme

### Problem 1: Zonen-Feldnamen Mismatch
- **BuildingZone Model** verwendet: `traufhoehe_m`, `firsthoehe_m`
- **claude_svg_zones.py** suchte: `building_height_m`, `eave_height_m`
- **Status**: ✅ BEHOBEN (sucht jetzt beide Varianten)

### Problem 2: Zonen werden nicht aus scaffolding-Daten übernommen
- Die `dimensions.traufhoehe_m` aus der API wird nicht in die Zonen übertragen
- Wenn keine Building Context Zonen existieren, wird eine Fallback-Zone erstellt
- Diese Fallback-Zone sollte die korrekten Höhen aus der API haben
- **Status**: ✅ BEHOBEN (Fallback-Zone enthält jetzt `building_height_m` und `first_height_m`)

### Problem 3: Höhenskala zeigt nur "+0.00"
- `max_height` wird aus Zonen berechnet
- Wenn Zonen keine Höhen haben → max_height = 0
- Ergebnis: Höhenskala zeigt "+0.00" statt "+62.0"
- **Status**: ✅ BEHOBEN (durch Fix von Problem 1 + 2)

### Problem 4: Kuppel bei nicht-komplexen Gebäuden (NEU 25.12.2025)
- **Symptom**: Einfache Gebäude (z.B. Wohnhaus) werden mit Kuppel gezeichnet
- **Ursache**: Der Prompt listete alle möglichen Zone-Typen auf (arkade, hauptgebaeude, kuppel)
- Claude interpretierte dies als "zeichne alle diese Elemente" statt "das sind die möglichen Typen"
- **Screenshot**: `2025-12-25 09_29_19-nicht_komplex.png` zeigt Gebäude mit falscher Kuppel
- **Status**: ✅ BEHOBEN
  - Prompt enthält jetzt "KRITISCHE REGEL" am Anfang
  - Zone-Typen werden dynamisch aus den tatsächlichen Daten generiert
  - Nur vorhandene Typen werden im Prompt beschrieben
  - Expliziter Hinweis: "KEINE Kuppel wenn nicht in Daten!"

---

## 4. Referenz-SVG Analyse (anhang_b_ansicht.svg)

**Korrekte Elemente:**
- Weisser Hintergrund (`fill="white"`)
- Schraffur-Pattern für Gebäude (`url(#hatch)`)
- Höhenskala: ±0.00 bis +64.0 mit Beschriftungen alle 10m
- Lagenbeschriftung: 1. Lage bis 9. Lage
- Terrain-Linie mit Ground-Pattern
- Legende-Box
- Gerüst nur in Blau (#0066CC)

**Farbpalette (strikt):**
| Element | Farbe | Code |
|---------|-------|------|
| Hintergrund | Weiss | #FFFFFF |
| Gebäude | Schraffur | url(#hatch) |
| Linien | Dunkelgrau | #333333 |
| Gerüst | Blau | #0066CC |
| Verankerung | Rot | #CC0000 |
| Beläge | Braun | #8B4513 |
| Kuppel | Gradient | url(#copper) |

---

## 5. Fragen an Claude.ai

1. **Sind die Prompt-Anweisungen klar genug?**
   - Ist der Stil-Abschnitt präzise genug um künstlerische Interpretationen zu verhindern?

2. **Fehlen wichtige Daten im Prompt?**
   - Sollten wir die tatsächlichen Höhenwerte (14.53m Traufe, 62.57m First) explizit im Prompt übergeben?

3. **Wie können wir die Höhenskala garantieren?**
   - Sollten wir die Skala-Werte als explizite Liste übergeben?
   - Beispiel: "Höhenskala: 0, 10, 20, 30, 40, 50, 60m"

4. **Ist die Pattern-Definition korrekt?**
   - Werden die SVG-Patterns korrekt übernommen?

5. **Verbesserungsvorschläge?**
   - Was würde die SVG-Qualität verbessern?

---

## 6. Gewünschtes Ergebnis

Ein SVG das aussieht wie `anhang_b_ansicht.svg`:
- Technisch-professionell
- Weisser Hintergrund
- Schraffierte Gebäudeflächen
- Korrekte Höhenskala (±0.00 bis +62.0m)
- Lagenbeschriftung (1. Lage bis 31. Lage bei 62m Höhe)
- Gerüst mit blauen Ständern
- Kupferfarbene Kuppel als einziger Gradient
