# PROJEKT_KONTEXT.md
# Gerüstplanung Schweiz - Gemeinsamer Kontext
# ============================================
# Diese Datei wird von Claude.ai UND Claude IDE gelesen.
# Änderungen hier synchronisieren den Wissensstand beider Systeme.

## 🎯 Aktuelles Projekt

**Objekt:** Bundeshaus Bern (Parlamentsgebäude)
**Adresse:** Bundesplatz 3, 3003 Bern
**Status:** In Entwicklung - Fokus auf Grunddaten & SVG-Generierung

---

## 📊 Datenquellen

### SwissBuildings3D (aktuell verwendet)
- **Firsthöhe:** 62.6 m (= Kuppelspitze)
- **Traufhöhe:** 14.5 m ⚠️ PROBLEM: Dies ist vermutlich der Arkaden-Wert!

### Realistische Höhenzonen Bundeshaus
| Gebäudeteil | Traufhöhe | Firsthöhe | Bemerkung |
|-------------|-----------|-----------|-----------|
| Arkaden (Verbindungen) | ~14 m | – | ← SwissBuildings3D Wert |
| Bundeshaus West/Ost | 15–18 m | 20–22 m | 3-4 Stockwerke |
| Parlamentsgebäude | 22–25 m | 28–32 m | Hauptfassaden |
| Ecktürme Süd | – | 35–38 m | 2 Türme |
| Hauptkuppel | – | 62–64 m | Mit Laterne |

### Gebäudedimensionen
- **Gesamtlänge:** ca. 300 m (West + Parlament + Ost)
- **Parlamentsgebäude:** ca. 90 m Länge, 60 m Tiefe
- **Material:** Berner Sandstein, Kupferkuppel

---

## ⚙️ Douglas-Peucker Parameter

```python
# Aktuelle Konfiguration
SIMPLIFY_EPSILON = 2.0          # Meter - Toleranz für Punktreduktion
COLLINEAR_ANGLE_TOLERANCE = 5.0  # Grad - für kollineare Punkte
MIN_SEGMENT_LENGTH = 1.5         # Meter - minimale Segmentlänge
```

### Empfehlungen je Gebäudegrösse
| Gebäudetyp | EPSILON | ANGLE_TOL | Bemerkung |
|------------|---------|-----------|-----------|
| EFH (10×12m) | 0.5–1.0 | 3–5° | Wenig Vereinfachung nötig |
| MFH/Gewerbe | 1.0–2.0 | 5–8° | Standard |
| Grossprojekt (Bundeshaus) | 2.0–3.0 | 5–10° | Starke Vereinfachung |

---

## 📐 NPK 114 Konstanten

```python
# Zuschläge gemäss NPK 114 D/2012
FASSADENABSTAND_LF = 0.30        # m
GERUESTGANGBREITE_LG = 0.70      # m (für W09)
STIRNSEITIGER_ABSCHLUSS_LS = 1.00 # m (= LF + LG)
HOEHENZUSCHLAG = 1.00            # m über Arbeitshöhe
MIN_AUSMASSLAENGE = 2.5          # m
MIN_AUSMASSHOEHE = 4.0           # m

# Formeln
# LA = LS + L + LS (beidseitiger Abschluss)
# HA = H + Höhenzuschlag
# A = LA × HA
# Giebel: H_mittel = H_Traufe + (H_Giebel × 0.5)
```

---

## 🔧 Layher Blitz 70 System

### Feldlängen (m)
`3.07, 2.57, 2.07, 1.57, 1.09, 0.73`

### Rahmenhöhen (m)
`2.00, 1.50, 1.00, 0.50`

### Richtwerte
- **Gewicht:** 18–22 kg/m² Gerüstfläche
- **Lastklasse:** 3 (200 kg/m²)
- **Breitenklasse:** W09 (0.90 m)
- **Verankerung:** alle 4 m horizontal, alle 4 m vertikal

---

## 📁 App-Struktur (Railway)

**URL:** https://cooperative-commitment-production.up.railway.app/

### Geplante Komponenten
```
/api
  /geocode          - Adresse → Koordinaten
  /buildings        - SwissBuildings3D Abfrage
  /simplify         - Douglas-Peucker Anwendung
  /calculate        - NPK 114 Berechnung
  /svg              - SVG-Generierung

/frontend
  - Adresseingabe
  - Kartenansicht
  - Parameter-Slider (EPSILON, ANGLE_TOL)
  - SVG-Vorschau
  - Export (SVG, PNG, PDF)
```

---

## 🖼️ SVG-Outputs (Ziel)

### 1. Grundriss (Draufsicht)
- Gebäudepolygon (vereinfacht)
- Gerüstbelag (blau, transparent)
- Ständerpositionen (Punkte)
- Verankerungen (rot)
- Zugänge (gelb)
- Massstab, Nordpfeil, Legende

### 2. Ansicht (Elevation/Fassadenansicht)
- Fassadensilhouette mit Dach
- Gerüstlagen nummeriert
- Höhenkoten
- Verankerungspunkte
- Verschiedene Höhenzonen berücksichtigen!

### 3. Schnitt (Querschnitt)
- Gebäudeprofil mit Dach/Kuppel
- Gerüst auf beiden Seiten
- Terrain-Linie
- Massstab

---

## ✅ Offene Aufgaben

### Priorität 1 (Aktuell)
- [ ] Höhenzonen aus SwissBuildings3D extrahieren
- [ ] Douglas-Peucker in App integrieren
- [ ] SVG-Grundriss mit vereinfachtem Polygon

### Priorität 2
- [ ] SVG-Ansicht mit korrekten Höhenzonen
- [ ] SVG-Schnitt durch Hauptgebäude
- [ ] NPK 114 Berechnung in App

### Priorität 3
- [ ] Materialberechnung Layher Blitz 70
- [ ] Export als Word/PDF
- [ ] 3D-Visualisierung (optional)

---

## 🔄 Letzte Änderungen

| Datum | Änderung | Von |
|-------|----------|-----|
| 2024-12-24 | Datei erstellt, Bundeshaus-Höhenproblem dokumentiert | Claude.ai |
| | | |

---

## 📝 Notizen für Claude IDE

Bei Änderungen an dieser Datei:
1. Datum und Änderung in "Letzte Änderungen" eintragen
2. Bei neuen Parametern: auch in config.py übernehmen
3. Bei API-Änderungen: Struktur oben aktualisieren

## 📝 Notizen für Claude.ai

- Code-Review: Einfach Code in Chat einfügen oder Datei hochladen
- Screenshots der App-Outputs helfen bei der Analyse
- Diese Datei liegt in Project Knowledge unter /mnt/project/
