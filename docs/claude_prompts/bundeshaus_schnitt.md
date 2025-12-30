# SVG Schnitt: Bundeshaus Bern

Kopiere diesen Prompt in Claude.ai um einen professionellen Gebäudeschnitt zu generieren.

---

## Prompt

Erstelle einen technischen Gebäudeschnitt als SVG für das Bundeshaus in Bern.

### Gebäudedaten

- **Adresse:** Bundesplatz 3, 3011 Bern
- **EGID:** 2242547
- **Koordinaten (LV95):** E 2600423, N 1199521
- **Gebäudename:** Bundeshaus (Schweizer Parlamentsgebäude)
- **Gebäudetyp:** Parlamentsgebäude
- **Baujahr:** 1902
- **Architekturstil:** Neorenaissance / Historismus

### Höhendaten

- **Terrain (m ü.M.):** 543.1
- **Traufhöhe:** 25.0 m (Hauptgebäude)
- **Firsthöhe:** 30.0 m (Hauptgebäude)
- **Kuppelhöhe:** 64.0 m (höchster Punkt)

### Höhenzonen (3 Zonen)

| Zone | Name | Typ | Traufhöhe | Firsthöhe | Sonderkonstruktion |
|------|------|-----|-----------|-----------|-------------------|
| 1 | Arkaden | arkade | 6.0 m | 6.0 m | Nein |
| 2 | Hauptgebäude | hauptgebaeude | 25.0 m | 30.0 m | Nein |
| 3 | Kuppel | kuppel | 30.0 m | 64.0 m | Ja |

### SVG-Anforderungen

**Format:** 800 x 600 px, viewBox="0 0 800 600"

**Stil:**
- Technische Architekturzeichnung (NICHT künstlerisch)
- Hintergrund: Weiss (#FFFFFF)
- Schnittflächen: Schraffur-Pattern (diagonal 45°)
- Hauptlinien: Dunkelgrau (#333333), 2px
- Gerüst-Elemente: Blau (#0066CC)
- Masslinien mit Pfeilen

**Inhalt:**
1. Terrain-Linie unten (±0.00 = 543.1 m ü.M.)
2. Alle 3 Zonen mit korrekten Höhen darstellen
3. Höhenskala links (0 bis 65m)
4. Lagenbeschriftung rechts (Lagen à 2m)
5. Geschosslinien andeuten
6. Kuppel als Schnitt zeigen (Hohlraum sichtbar)
7. Legende oben rechts
8. Massstab 1:200

**Patterns (in <defs>):**
```xml
<pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
  <path d="M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4" stroke="#999" stroke-width="0.5"/>
</pattern>
<pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="6" height="6">
  <path d="M0,6 L6,0" stroke="#333" stroke-width="1"/>
</pattern>
```

Generiere NUR das SVG, keine Erklärungen.
