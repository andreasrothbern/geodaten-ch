# SVG-Generierung: Grundriss + Fassadenansicht + Gebäudeschnitt

> **Hinweis:** Ein Export-Button generiert Daten für alle 3 SVG-Typen.

## 1. Gebäude-Identifikation
- **Adresse:** [Strasse Nr, PLZ Ort]
- **EGID:** [Nummer]
- **Koordinaten (LV95):** E [Nummer], N [Nummer]
- **Gebäudename:** [Name oder "RECHERCHIEREN"]
- **Gebäudetyp:** [Kirche/Rathaus/Wohnhaus/Gewerbe/etc.]
- **Baustil:** [Neugotik/Barock/Klassizismus/Modern/etc. oder "RECHERCHIEREN"]
- **Baujahr:** [Jahr]
- **Komplexität:** [EINFACH | KOMPLEX (mehrere Zonen)]

## 2. RECHERCHE-ANWEISUNG
> Falls Gebäudename oder Baustil mit "RECHERCHIEREN" markiert:
> 1. Suche das Gebäude anhand Adresse/EGID/Koordinaten
> 2. Identifiziere den korrekten Gebäudenamen
> 3. Bestimme Gebäudetyp und Baustil
> 4. Ermittle charakteristische Architekturmerkmale
> 5. Kläre Turmkonfiguration (Anzahl, Position, Form)
> 6. Validiere Höhenzonen gegen recherchierte Informationen
> Erst danach mit der SVG-Erstellung beginnen.

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhöhe:** [m]
- **Firsthöhe:** [m]
- **Geschosse:** [Anzahl]
- **Grundfläche:** [m²]

### Dach-Analyse (Option C - heuristisch berechnet)
- **Dachform:** [Flachdach/Pultdach/Satteldach/Walmdach/Mansarddach]
- **Dachneigung:** [°]
- **First-Ausrichtung:** [O-W / N-S / etc.]
- **Dachfläche:** [m²]
- **Konfidenz:** [%] (hoch = verlässlich, niedrig = Schätzung)

### Turm/Kuppel (falls vorhanden)
- **Typ:** [Spitzhelm/Kuppel/Flach]
- **Neigung:** [°]

### Terrain (swissALTI3D)
- **Terrain-Höhe:** [m ü.M.] (Referenzpunkt am Gebäude)
- **Hanglage:** [Ja/Nein]
- **Min. Terrain:** [m ü.M.] (niedrigste Ecke)
- **Max. Terrain:** [m ü.M.] (höchste Ecke)
- **Terrain-Differenz:** [m] (Gefälle über Gebäudebreite)
- **Hinweis:** [Bei >1m: Unterschiedliche Gerüsthöhen je Fassade nötig]

### Polygon
[Koordinaten oder Seitenlängen mit Himmelsrichtungen]

## 4. GWR-Daten (Gebäude- und Wohnungsregister)
- **Gebäudekategorie:** [z.B. Mehrfamilienhaus, Kirche, Öffentliches Gebäude]
- **Baujahr:** [Jahr]
- **Geschosse (GWR):** [Anzahl]
- **Grundfläche (GWR):** [m²]

## 5. Höhenzonen
| Zone | Typ | Höhe | Traufe | Eingerüstet |
|------|-----|------|--------|-------------|
| [Name] | [hauptgebaeude/anbau/arkade/turm/kuppel/innenhof] | [m] | [m] | [Ja/Nein] |

### Zonen-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkörper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen (Erdgeschoss)
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebäude
- **innenhof** = Nicht einrüsten (Freifläche)

### Turmkonfiguration (falls vorhanden)
- **Anzahl:** [1/2/etc.]
- **Position:** [Zentral/West/Flankierend/etc.]
- **Form:** [Quadratisch/Rund/Oktogonal] mit [Spitzhelm/Kuppel/Flachdach]

## 6. Baustil-Merkmale
[Explizit angeben ODER "RECHERCHIEREN basierend auf Baustil"]
- **Fenster:** [Spitzbogen/Rundbogen/Rechteck/etc.]
- **Portal:** [Beschreibung]
- **Fassadengliederung:** [Strebepfeiler/Pilaster/Lisenen/etc.]
- **Dachdetails:** [Kreuz/Wetterfahne/Gauben/Fialen/etc.]
- **Besondere Elemente:** [Rosette/Erker/Balkon/etc.]

## 7. Fassaden (aus Polygon)
| Seite | Länge (m) | Richtung | Fläche (m²) |
|-------|-----------|----------|-------------|
| 1 | [m] | [N/E/S/W/etc.] | [m²] |

## 8. SVG Style-Vorgaben

```xml
<defs>
  <!-- Schraffur für Gebäude -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4" stroke="#999" stroke-width="0.5"/>
  </pattern>
  <!-- Kupfer-Gradient NUR für Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill |
|---------|------------|
| Hintergrund | #FFFFFF (weiss) |
| Gebäude | url(#hatch) Schraffur |
| Kuppel | url(#copper) Gradient |
| Gerüst-Ständer | #0066CC (blau) |
| Beläge | #8B4513 (braun) |
| Verankerungen | #CC0000 gestrichelt |

## 9. Anforderungen

### Für Grundriss:
- Polygon-Form des Gebäudes
- Fassaden beschriften (Länge + Richtung)
- Gerüstzone um das Gebäude (gelb)
- Zonen farblich unterscheiden
- Nordpfeil und Massstab

### Für Fassadenansicht:
- Orthogonale Frontalansicht
- Terrain-Linie bei ±0.00 (bzw. m ü.M. wenn Hanglage)
- Höhenzonen klar darstellen
- Baustil-typische Elemente zeigen
- Gerüst VOR der Fassade
- Höhenskala links, Lagenbeschriftung rechts

### Für Gebäudeschnitt:
- Frontalansicht (2D Orthogonalprojektion)
- Terrain-Linie bei ±0.00 (bzw. m ü.M. wenn Hanglage)
- Geschossdecken als horizontale Linien
- Höhenzonen mit unterschiedlichen Höhen
- Gerüst links und rechts
- Höhenskala links, Lagenbeschriftung rechts

## 10. Output

Erstelle **3 separate SVGs**, jeweils mit `viewBox="0 0 700 480"`:

1. **grundriss.svg** - Draufsicht mit Polygon und Gerüstzone
2. **fassadenansicht.svg** - Frontalansicht mit Gerüst
3. **gebaeudesschnitt.svg** - Querschnitt mit Geschossen

**NUR SVG-Code**, keine Erklärungen. Trenne die SVGs klar voneinander.

---

## Beispiel: Ausgefüllte Vorlage (Bundeshaus Bern)

```markdown
# SVG-Generierung: Fassadenansicht

## 1. Gebäude-Identifikation
- **Adresse:** Bundesplatz 3, 3011 Bern
- **EGID:** 2242547
- **Koordinaten (LV95):** E 2600450, N 1199830
- **Gebäudename:** Bundeshaus (Schweizer Parlamentsgebäude)
- **Gebäudetyp:** Parlamentsgebäude
- **Baustil:** Historismus (Neorenaissance)
- **Baujahr:** 1902
- **Komplexität:** KOMPLEX (mehrere Zonen)

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhöhe:** 14.5 m (Arkaden!)
- **Firsthöhe:** 62.6 m (Kuppel!)
- **Geschosse:** 4
- **Grundfläche:** 4200 m²

### Dach-Analyse
- **Dachform:** Mansarddach
- **Dachneigung:** 63°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 40% (komplex, Schätzung)

### Terrain (swissALTI3D)
- **Terrain-Höhe:** 543.1 m ü.M.
- **Hanglage:** Nein
- **Terrain-Differenz:** 0.5 m

## 4. GWR-Daten
- **Gebäudekategorie:** Öffentliches Gebäude
- **Baujahr:** 1902
- **Geschosse (GWR):** 4
- **Grundfläche (GWR):** 4200 m²

## 5. Höhenzonen
| Zone | Typ | Höhe | Traufe | Eingerüstet |
|------|-----|------|--------|-------------|
| Arkaden | arkade | 6 | 5 | Ja |
| Hauptgebäude | hauptgebaeude | 25 | 20 | Ja |
| Kuppel | kuppel | 64 | - | Nein (Spezialgerüst) |

## 6. Baustil-Merkmale
- **Fenster:** Rundbogen-Arkaden EG, Rechteckfenster OG
- **Portal:** Monumentaler Mittelrisalit
- **Fassadengliederung:** Pilaster, Gesimse
- **Dachdetails:** Kuppel mit Laterne, Patina (Kupfer)
- **Besondere Elemente:** Skulpturen, Schweizer Wappen
```