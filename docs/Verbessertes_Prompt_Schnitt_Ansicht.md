Hier ist das korrigierte Prompt mit klaren Unterscheidungen:
markdown# SVG-Generierung: Grundriss + Fassadenansicht + Gebäudeschnitt

## 1. Gebäude-Identifikation

- **Adresse:** Rathausgasse 2, 3011 Bern
- **EGID:** 191821074
- **Koordinaten (LV95):** E 601009, N 199736
- **Gebäudename:** RECHERCHIEREN
- **Gebäudetyp:** RECHERCHIEREN
- **Baustil:** RECHERCHIEREN
- **Baujahr:** 1864

## 2. RECHERCHE-ANWEISUNG

> **WICHTIG:** Falls Gebäudename, Gebäudetyp oder Baustil mit "RECHERCHIEREN" markiert:
> 1. Suche das Gebäude anhand Adresse/EGID/Koordinaten
> 2. Identifiziere den korrekten Gebäudenamen
> 3. Bestimme Gebäudetyp (Kirche, Rathaus, Wohnhaus, etc.)
> 4. Bestimme Baustil (Neugotik, Barock, Klassizismus, Modern, etc.)
> 5. Ermittle charakteristische Architekturmerkmale (Fensterformen, Portal, Türme)
> 6. Kläre Turmkonfiguration (Anzahl, Position, Form) falls vorhanden
> 7. Validiere die unten angegebenen Höhenzonen gegen recherchierte Informationen
     > **Erst danach mit der SVG-Erstellung beginnen.**

## 3. Geometrische Basisdaten

### Dimensionen
- **Traufhöhe:** 9.3 m
- **Firsthöhe:** 54.6 m
- **Geschosse:** -
- **Grundfläche:** 1099 m²

### Dach
- **Dachform:** Satteldach (Hauptschiff), Spitzhelm (Turm)
- **Dachneigung:** 45° (Schiff), 70° (Turm)

### Terrain
- **Terrain-Höhe:** 533.5 m ü.M.
- **Hanglage:** Nein
- **Referenzpunkt:** Haupteingang = ±0.00

## 4. Polygon-Daten

### Vereinfachte Bounding-Box
- **Länge (O-W):** ca. 50 m
- **Breite (N-S):** ca. 22 m

### Gerüstzone
- **Abstand:** 1.0 m um Gebäude
- **Darstellung:** Vereinfachte rechteckige Hülle um Gesamtgebäude
- **NICHT:** Exakte Offset-Kontur des komplexen Polygons

### Fassaden-Referenz (nur für Grössenangaben)
- Längste Fassade: 18.4 m (W)
- Gesamtumfang: ca. 180 m
- Hinweis: Bei >10 Polygon-Punkten vereinfachte Darstellung verwenden

## 5. Höhenzonen

| Zone | Typ | Höhe | Traufe | Eingerüstet |
|------|-----|------|--------|-------------|
| Seitenschiffe | anbau | 15 m | 9.3 m | Ja |
| Hauptschiff | hauptgebaeude | 22 m | 18 m | Ja |
| Westturm | turm | 54.6 m | - | Nein [Sonderkonstruktion] |

## 6. SVG Style-Vorgaben
```xml

  
    
  
  
    
  
  
    
    
  

```

| Element | Farbe/Fill |
|---------|------------|
| Hintergrund | #FFFFFF (weiss) |
| Gebäude-Aussenfläche | url(#hatch) - lockere Schraffur |
| Schnittfläche (Mauerwerk) | url(#cut-hatch) - dichte Schraffur |
| Innenraum | #FFFFFF (weiss, leer) |
| Kuppel | url(#copper) Gradient |
| Gerüst-Ständer | #0066CC (blau) |
| Beläge | #8B4513 (braun) |
| Verankerungen | #CC0000 gestrichelt |

## 7. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebäudeumriss, Raumaufteilung, Wandstärken
- **Gebäudeform:** Vereinfacht basierend auf Gebäudetyp (Basilika-Schema für Kirchen)
- **Gerüstzone:** Rechteckige Hülle mit 1m Abstand (KEINE Treppenstufen!)
- **Elemente:** Nordpfeil, Massstab, Fassadenlängen
- **Schraffur:** url(#hatch) für Mauern

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal
- **Zeigt:** NUR die sichtbare Aussenfläche
- **WICHTIG:**
    - Vordere Elemente VERDECKEN hintere Elemente
    - Turm verdeckt dahinterliegendes Hauptschiff
    - KEINE Innenräume sichtbar
    - KEINE Gewölbe sichtbar (nur von aussen erkennbare Dachform)
- **Elemente:**
    - Terrain-Linie bei ±0.00
    - Fassadengliederung (Fenster, Portal, Ornamente)
    - Dachform von aussen
    - Gerüst VOR der Fassade
    - Höhenskala links, Lagenbeschriftung rechts
- **Schraffur:** url(#hatch) für alle Fassadenflächen

### SVG 3: Gebäudeschnitt (Querschnitt)
- **Perspektive:** Gebäude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenräume, Konstruktion, Raumhöhen
- **WICHTIG:**
    - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
    - Innenräume = WEISS/LEER (keine Schraffur!)
    - Gewölbe, Decken, Böden sichtbar
    - Raumhöhen ablesbar
- **Elemente:**
    - Terrain-Linie bei ±0.00
    - Geschossdecken als horizontale Linien
    - Gewölbeformen im Innenraum
    - Krypta falls vorhanden
    - Gerüst links und rechts
    - Höhenskala links, Lagenbeschriftung rechts
    - Schnittmarkierung A-A
- **Schraffur:**
    - url(#cut-hatch) NUR für geschnittene Bauteile
    - Innenräume LEER lassen

## 8. Unterschied Fassade vs. Schnitt (WICHTIG!)
```
FASSADENANSICHT                    GEBÄUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE
                                   
    ┌─────────┐                        ┌─────────┐
    │░░░░░░░░░│ ← Fassade             │█│     │█│ ← Schnittfläche
    │░░░░░░░░░│   (alles sichtbar      │ │     │ │   (dicht schraffiert)
    │░░░░░░░░░│    von aussen)         │ │     │ │   
    └─────────┘                        │ │     │ │ ← Innenraum (LEER!)
                                       └─┴─────┴─┘
                                   
░░░ = lockere Schraffur            █ = dichte Schnitt-Schraffur
      (Aussenfläche)                   (geschnittenes Mauerwerk)
                                     = weiss (Innenraum)
```

## 9. Output

Erstelle **3 separate SVGs**, jeweils mit `viewBox="0 0 700 480"`:

1. **grundriss.svg** - Draufsicht mit vereinfachter Gebäudeform und rechteckiger Gerüstzone
2. **fassadenansicht.svg** - Aussenansicht, vordere Elemente verdecken hintere
3. **gebaeudesschnitt.svg** - Aufgeschnitten, Innenräume sichtbar und LEER

**NUR SVG-Code**, keine Erklärungen.

Zusammenfassung der wichtigsten Änderungen
BereichVorherNachherPolygon46 Fassaden-SegmenteBounding-Box + Hinweis "vereinfachen"GerüstzoneUnklarExplizit "rechteckige Hülle, KEINE Stufen"Fassade vs. SchnittNicht erklärtKlare Unterscheidung mit ASCII-GrafikSchraffurEine für allesZwei Typen: hatch (aussen) vs. cut-hatch (Schnitt)VerdeckungNicht erwähnt"Vorne verdeckt hinten" für FassadeInnenräumeNicht erwähnt"LEER lassen" im Schnitt
