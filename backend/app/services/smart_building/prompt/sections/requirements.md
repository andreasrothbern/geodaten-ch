# SVG-Anforderungen pro Typ

## SVG 1: Grundriss (Draufsicht)

- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** Rechteckige Huelle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung
- **Bei mehreren Zonen:** Farblich unterscheiden, Innenhoefe markieren

### Gebaeudeform beachten!
- **U-Form:** Ehrenhof in der Mitte als Freiflaeche (NICHT schraffieren)
- **L-Form:** Deutliche Ecke, beide Fluegel zeigen
- **Kreuzform:** Langhaus + Querhaus unterscheiden

## SVG 2: Fassadenansicht (Elevation)

- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenraeume sichtbar!
- **Schraffur:** url(#hatch) fuer alle Fassadenflaechen
- **Terrain-Linie:** bei +/-0.00 (bzw. m ue.M.)
- **Geruest:** VOR der Fassade (Staender blau, Belaege braun)
- **Hoehenskala:** Links (+/-0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)

### Hoehenzonen beachten!
- Jede Zone mit korrekter Hoehe darstellen
- Kuppeln mit Kupfer-Gradient
- Arkaden mit Rundboegen

## SVG 3: Gebaeudeschnitt (Querschnitt)

- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenraeume, Konstruktion, Raumhoehen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei +/-0.00 mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Geruest:** Links und rechts (Staender + Belaege)
- **Schnittmarkierung:** A-A

### Alle Hoehenzonen zeigen!
- Jede Zone mit korrekter Hoehe
- Unterschiedliche Wandstaerken moeglich
- Dachkonstruktion andeuten

## SVG 4: Umgebungsplan (optional)

- **Perspektive:** Vogelperspektive, groesserer Massstab
- **Zeigt:** Gebaeude im Kontext mit Nachbarn
- **Terrain:** Hoehenlinien bei Hanglage
- **Nachbarn:** Schematisch mit Hoehenangabe
- **Zugaenge:** Markiert mit Z1, Z2, etc.
- **Strassen:** Falls relevant fuer Geruestzugang

## Output-Format

```xml
<!-- viewBox fuer alle SVGs -->
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <!-- Inhalt -->
</svg>
```

**NUR SVG-Code**, keine Erklaerungen. Trenne die SVGs mit Kommentar:
`<!-- SVG 1: Grundriss -->`
