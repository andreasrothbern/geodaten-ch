# Bundeshaus Bern - Showcase Beispiel

Dieses Showcase demonstriert die Anwendung der NPK 114 Gerüstberechnung auf ein komplexes Gebäude mit mehreren Höhenzonen.

## Objektdaten

| Merkmal | Wert |
|---------|------|
| **Adresse** | Bundesplatz 3, 3011 Bern |
| **EGID** | 2242547 |
| **Grundfläche** | 3'697 m² |
| **Umfang** | 320 m |
| **Bounding Box** | 80m x 72m |
| **Gebäudeform** | T-Form mit Kuppel |

## Höhenzonen

Das Bundeshaus hat **drei unterschiedliche Höhenzonen**, die für die Gerüstplanung separat betrachtet werden müssen:

| Zone | Bereich | Traufhöhe | Firsthöhe |
|------|---------|-----------|-----------|
| **Zone 1** | Ost-/Westflügel | 20m | 25m |
| **Zone 2** | Mittelbau | 30m | 35m |
| **Zone 3** | Kuppel | 35m (Ansatz) | 64m (Laterne) |

## Visualisierungen

### 1. Grundriss mit Gerüstposition
`bundeshaus_grundriss.svg`

Zeigt:
- Gebäudeumriss (vereinfacht)
- Gerüstpositionen (orange)
- Verankerungspunkte (rot)
- Zugang
- Massstab

### 2. Querschnitt (Ost-West)
`bundeshaus_schnitt.svg`

Zeigt:
- Höhenstaffelung West/Mitte/Ost
- Kuppel mit Laterne
- Gerüstpositionen an Flügeln
- Höhenkoten

### 3. Ansicht Südfassade
`bundeshaus_ansicht.svg`

Zeigt:
- Fassadengliederung
- Kuppel und Laterne
- Gerüstbeispiel am Zentralbau
- Verankerungsraster

## NPK 114 Berechnung

Für ein Gebäude mit mehreren Höhenzonen wie das Bundeshaus sind **separate Ausmasse** erforderlich:

### Zone 1: Westflügel (Beispiel)
```
Fassadenlänge: 100m
Ausmasslänge: LA = 1.0 + 100.0 + 1.0 = 102.0m
Ausmasshöhe:  HA = 20.0 + 1.0 = 21.0m
Fläche:       A = 102.0 × 21.0 = 2'142.0 m²
```

### Zone 2: Mittelbau Süd
```
Fassadenlänge: 80m
Ausmasslänge: LA = 1.0 + 80.0 + 1.0 = 82.0m
Ausmasshöhe:  HA = 30.0 + 1.0 = 31.0m
Fläche:       A = 82.0 × 31.0 = 2'542.0 m²
```

### Zone 3: Kuppelbereich
Sonderfall - Hängegerüst oder Spezialgerüst erforderlich.
Nicht nach Standard-NPK 114 berechenbar.

## Herausforderungen komplexer Gebäude

1. **Mehrere Höhenzonen**: Separate Berechnung pro Zone
2. **Komplexe Grundrisse**: 175 Polygonpunkte (Vereinfachung nötig)
3. **Sonderkonstruktionen**: Kuppel, Türme, Erker
4. **Denkmalschutz**: Besondere Anforderungen an Verankerung

## 3D Viewer

Das Bundeshaus kann im swisstopo 3D Viewer betrachtet werden:

[Bundeshaus im 3D Viewer öffnen](https://map.geo.admin.ch/?lang=de&topic=ech&bgLayer=ch.swisstopo.pixelkarte-farbe&layers=ch.swisstopo.swissbuildings3d&E=600423&N=199521&zoom=10&3d=true)

## Dateien

- `bundeshaus_grundriss.svg` - Grundriss mit Gerüst
- `bundeshaus_schnitt.svg` - Querschnitt Ost-West
- `bundeshaus_ansicht.svg` - Ansicht Südfassade

---

*Erstellt für GL 2025 Kurs - Materialbewirtschaftung Gerüstbau*
