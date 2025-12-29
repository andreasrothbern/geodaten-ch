# SVG-Generierung: Fassadenansicht (Elevation)

## 1. Gebäude-Identifikation
- **Adresse:** Rathausgasse 2, 3011 Bern
- **EGID:** 191821074
- **Gebäudename:** St. Peter und Paul (Christkatholische Kathedralkirche)
- **Gebäudetyp:** Kirche (dreischiffige Basilika)
- **Baustil:** Neugotik / Neoromanik
- **Baujahr:** 1858-1864
- **Architekt:** Pierre Joseph Edouard Deperthes

## 2. RECHERCHE-ANWEISUNG
> **Falls Gebäudename unbekannt:** Recherchiere zuerst das Gebäude anhand
> der Adresse/EGID und identifiziere:
> - Korrekten Gebäudenamen
> - Gebäudetyp und Baustil
> - Charakteristische Architekturmerkmale
> - Turmkonfiguration (Anzahl, Position, Form)
> Erst danach mit der SVG-Erstellung beginnen.

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhöhe:** 9.3m (Seitenschiffe), 18.0m (Hauptschiff)
- **Firsthöhe:** 54.6m (Turmspitze)
- **Geschosse:** 1 (Kirchenraum)
- **Grundfläche:** 1099 m²

### Dachformen
- **Hauptschiff:** Satteldach, ca. 45°
- **Seitenschiffe:** Pultdächer
- **Turm:** Spitzhelm (Pyramide), ca. 70°

### Terrain
- **Hanglage:** Leicht (Richtung Aare/Süd)
- **Referenzpunkt:** Hauptportal = ±0.00

### Polygon (47 Punkte)
[Fassadenlängen wie geliefert]

## 4. Höhenzonen
| Zone | Typ | Höhe | Traufe | Eingerüstet |
|------|-----|------|--------|-------------|
| Seitenschiffe | anbau | 18.0m | 9.3m | Ja |
| Hauptschiff | hauptgebaeude | 22.0m | 18.0m | Ja |
| Westturm | turm | 54.6m | - | Nein [Sonderkonstruktion] |

### Turmkonfiguration
- **Anzahl:** 1 (EIN zentraler Westturm)
- **Position:** Mittig an Westfassade
- **Form:** Quadratischer Schaft mit oktogonalem Spitzhelm

## 5. Baustil-Merkmale (Neugotik)
- **Fenster:** Spitzbogenfenster mit Masswerk
- **Portal:** Spitzbogenportal mit Wimperg und Kreuzblume
- **Rosette:** Rundfenster über Portal
- **Strebepfeiler:** An Seitenschiffen und Turm
- **Fialen:** An Turmecken (Balustrade)
- **Turmabschluss:** Spitzhelm mit Kreuz
- **Gliederung:** Horizontale Gesimse, vertikale Lisenen

## 6. SVG Style-Vorgaben
```xml
<defs>
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4" stroke="#999" stroke-width="0.5"/>
  </pattern>
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill |
|---------|------------|
| Hintergrund | #FFFFFF |
| Gebäude | url(#hatch) |
| Kuppel | url(#copper) - NUR bei Kuppeln! |
| Gerüst-Ständer | #0066CC |
| Beläge | #8B4513 |
| Verankerungen | #CC0000 gestrichelt |

## 7. Anforderungen Fassadenansicht
- Orthogonale Frontalansicht (Westfassade)
- Terrain-Linie bei ±0.00
- **Verschiedene Höhenzonen klar darstellen**
- Neugotische Architekturelemente zeigen
- Gerüst VOR der Fassade (nur eingerüstete Zonen)
- Höhenskala links, Lagenbeschriftung rechts
- Turm als Sonderkonstruktion kennzeichnen

## 8. Output
SVG mit `viewBox="0 0 700 480"`. NUR SVG-Code, keine Erklärungen.