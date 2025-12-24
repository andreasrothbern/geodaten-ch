# Kontext: Materialbewirtschaftung Gerüstbau (Schweiz)

## Projekttyp
Praxis-Umsetzung für **Gruppenleiter-Kurs (GL 2025)** bei Polybau/Polybat. Dokumentation der Materialbewirtschaftung einer Gerüstbau-Baustelle mit allen relevanten Berechnungen, Zeichnungen und Sicherheitskonzepten.

---

## Relevante Normen und Grundlagen

### NPK 114 D/2012 – Arbeitsgerüste
Schweizer Norm für Ausmassberechnung von Gerüsten.

**Ausmassgrundsätze (Anhang 1-4):**
- Längen/Höhen: Meter [m], Genauigkeit 0.1 m
- Flächen: Quadratmeter [m²], Genauigkeit 0.01 m²
- Rundung: Kaufmännisch (0-4 ab, 5-9 auf)
- **Minimale Ausmasslänge:** LAmin ≥ 2.5 m
- **Minimale Ausmasshöhe:** HAmin ≥ 4.0 m

**Zuschläge für Fassadengerüst:**
| Bezeichnung | Formel | Wert |
|-------------|--------|------|
| Fassadenabstand | LF | 0.30 m |
| Gerüstgangbreite (bis 0.70m) | LG | 0.70 m |
| Gerüstgangbreite (0.71-1.00m) | LG | 1.00 m |
| Stirnseitiger Abschluss | LS = LF + LG | 1.00 m |
| Höhenzuschlag | - | +1.00 m über Arbeitshöhe |

**Ausmassformeln:**
```
Ausmasslänge: LA = LS + L + LS
Ausmasshöhe:  HA = H + 1.0 m
Fläche:       A = LA × HA
Giebel:       H_mittel = H_Traufe + (H_Giebel × 0.5)
Eckzuschlag:  A_Ecke = LS × HA (pro Ecke)
```

### SIA 118/222 – Allgemeine Bedingungen Gerüstbau
- Art. 1.1: Ausschreibungsunterlagen
- Art. 1.1.3: Leistungsverzeichnis (Gerüstart, Lastklasse, Termine, etc.)
- Art. 2.1: Ausmassbestimmungen

### SIA D 0243 – Beispiele zu Ausmassbestimmungen
Ergänzende Dokumentation mit Beispielzeichnungen und Korrekturen (Korigenda C1).

---

## Gerüstsystem: Layher Blitz 70 Stahl

### Systemdaten
- **Feldlängen:** 3.07 m, 2.57 m, 2.07 m, 1.57 m, 1.09 m, 0.73 m
- **Rahmenhöhen:** 2.00 m, 1.50 m, 1.00 m, 0.50 m
- **Belagbreite:** 0.32 m (3 Beläge = 0.96 m für W09)

### Lastklassen (EN 12811)
| Klasse | Nutzlast | Anwendung |
|--------|----------|-----------|
| 2 | 150 kg/m² | Leichte Arbeiten (Maler) |
| 3 | 200 kg/m² | Fassadenarbeiten, Dachdecker |
| 4 | 300 kg/m² | Maurerarbeiten |
| 5 | 450 kg/m² | Steinarbeiten |
| 6 | 600 kg/m² | Schwere Lasten |

### Breitenklassen
| Klasse | Breite | Anwendung |
|--------|--------|-----------|
| W06 | 0.60 m | Inspektionsgerüst |
| W09 | 0.90 m | Standard Fassadengerüst |
| W12 | 1.20 m | Maurergerüst |

---

## Materialberechnung – Referenzwerte Layher Blitz 70

### Richtwerte pro m² Gerüstfläche (ca.)
| Material | Menge/100m² | Gewicht/Stk |
|----------|-------------|-------------|
| Stellrahmen 2.00 m | 15-18 Stk | 18.5 kg |
| Stellrahmen 1.00 m | 4-6 Stk | 12.0 kg |
| Doppelgeländer 3.07 m | 20-24 Stk | 10.5 kg |
| Doppelgeländer 2.57 m | 10-12 Stk | 9.0 kg |
| Robustboden 3.07×0.32 m | 28-32 Stk | 19.5 kg |
| Robustboden 2.57×0.32 m | 14-18 Stk | 16.5 kg |
| Diagonale 3.07 m | 6-8 Stk | 5.5 kg |
| Fussplatte | 10-12 Stk | 2.5 kg |
| Fussspindel 0.40 m | 10-12 Stk | 3.0 kg |

### Gewichtsrichtwert
**Ca. 18-22 kg pro m² Gerüstfläche** (inkl. aller Komponenten)

Beispiel EFH 460 m²: ca. 9-10 Tonnen Gesamtgewicht

---

## Verankerung

### Verankerungsraster (Richtwerte)
- **Horizontal:** max. 4.0 m Abstand
- **Vertikal:** max. 4.0 m Abstand (jede 2. Lage)
- **Ecken:** Verstärkte Verankerung

### Verankerungstypen
| Typ | Anwendung |
|-----|-----------|
| Gerüsthalter kurz | Mauerwerk, Beton |
| Gerüsthalter lang | Grösserer Fassadenabstand |
| V-Anker | Aussteifung, Giebelbereich |
| Ringöse + Dübel | Befestigung am Gebäude |

---

## Personalbedarfsberechnung

### Montageleistung (3-Mann-Kolonne)
| Gerüstart | Leistung | Faktor Demontage |
|-----------|----------|------------------|
| Fassadengerüst Standard | 50-60 m²/h | 0.8 (20% schneller) |
| Giebelgerüst | 40-50 m²/h | 0.8 |
| Dachfanggerüst | 20-25 m/h | 0.8 |

### Zusatzzeiten
- Abladen/Bereitstellen: 1.0 h
- Verankerung/Kontrolle: 0.5 h
- Laden/Sichern: 1.0 h

### Formel Gesamtzeit
```
Montage:   T = (Fläche / Leistung) + Zusatzzeiten
Demontage: T = Montagezeit × 0.8
Mannstunden: Mh = Personen × Stunden
```

---

## Transportberechnung

### LKW-Nutzlasten (Schweiz)
| Fahrzeugtyp | Nutzlast | Einsatz |
|-------------|----------|---------|
| 2-Achser | 6-7 t | Kleinere Baustellen |
| 3-Achser | 12-14 t | Standard EFH |
| 4-Achser | 16-18 t | Grössere Objekte |
| Sattelzug | 24-26 t | Grossprojekte |

### Ladungssicherung
- Stellrahmen: Gebündelt mit Spanngurten
- Beläge: In Gitterboxen oder auf Paletten
- Kleinmaterial: In beschrifteten Kisten
- Antirutschmatten unter Ladung

---

## Umschlagplatz / Lagerung

### Platzbedarf (Richtwerte)
| Verwendung | Fläche |
|------------|--------|
| Stellrahmen | 0.03 m² pro Stk (gestapelt) |
| Beläge | 0.02 m² pro Stk (Palette) |
| Geländer | 0.02 m² pro Stk (gebündelt) |
| Kleinmaterial | Pauschal 5-10 m² |
| Reserve/Arbeitsbereich | +20% |

---

## Gewünschte Outputs / Dokumentation

### 1. Baustellenbeschrieb
- Objektdaten (Adresse, Bauherr, Bauleitung)
- Gebäudemasse (Grundriss, Traufhöhe, Firsthöhe, Dachform)
- Gerüstanforderungen (System, Lastklasse, Breitenklasse)
- Baustellensituation (Zufahrt, Terrain, Hindernisse)
- Termine (Montage, Vorhaltedauer, Demontage)

### 2. Ausmass
- **Zeichnung Grundriss:** Draufsicht mit Gerüst, Ständerpositionen, Verankerungen, Zugang
- **Zeichnung Schnitt/Ansicht:** Seitenansicht mit Lagen, Höhenkoten, Geländer, Beläge
- **Ausmassberechnung:** Nach NPK 114 mit allen Zuschlägen
- **Positionsliste:** Vollständiges NPK-Ausmass aller Positionen

### 3. Materialauszug
- Materialliste nach Kategorien (Rahmen, Geländer, Beläge, etc.)
- Artikelnummern, Mengen, Einzelgewichte
- **Gewichtszusammenfassung:** Total in kg und Tonnen

### 4. Personalbedarf
- Montagezeit detailliert nach Arbeitsschritten
- Demontagezeit
- Mannstunden-Berechnung

### 5. Logistik
- Materialtransport (Fahrzeug, Route, Ladungssicherung)
- Ablad (Ort, Verfahren, Absicherung)
- Umschlagplatz (Platzbedarf, Beschaffenheit)

### 6. Sicherheitskonzept
- Gefährdungsbeurteilung (Matrix)
- PSA-Anforderungen
- Organisatorische Massnahmen
- Technische Massnahmen

### 7. Anhänge
- **Anhang A:** Grundriss Gerüst (technische Zeichnung)
- **Anhang B:** Schnitt/Ansicht (technische Zeichnung)
- **Anhang C:** Gerüstkarte (ausfüllbares Formular nach BauAV/SUVA)
- **Anhang D:** Checkliste Materialkontrolle (für Anlieferung/Rücknahme)

### 8. Reflexion
- Planungsphase
- Ausführungsphase
- Erkenntnisse/Verbesserungspotential
- Persönliches Fazit

---

## Beispielrechnung: EFH 10×12m, Satteldach

### Gebäudedaten
- Grundriss: 10.0 m × 12.0 m
- Traufhöhe: 6.5 m
- Firsthöhe: 10.0 m
- Giebelhöhe: 3.5 m
- Dachneigung: ca. 35°

### Ausmass Fassadengerüst
```
Traufseiten (2×12m):
LA = 1.0 + 12.0 + 1.0 = 14.0 m
HA = 6.5 + 1.0 = 7.5 m
A = 14.0 × 7.5 = 105.00 m² × 2 = 210.00 m²

Giebelseiten (2×10m):
LA = 1.0 + 10.0 + 1.0 = 12.0 m
H_mittel = 6.5 + (3.5 × 0.5) = 8.25 m
HA = 8.25 + 1.0 = 9.3 m
A = 12.0 × 9.3 = 111.60 m² × 2 = 223.20 m²

Eckzuschläge (4×):
A = 1.0 × 7.5 = 7.50 m² × 4 = 30.00 m²

TOTAL: 463.20 m²
```

### Ergebnisse
- **Gerüstfläche:** 463.20 m²
- **Gesamtgewicht:** ca. 9.2 Tonnen
- **Montagezeit:** 8.5 h (3 Personen)
- **Demontagezeit:** 6.5 h (3 Personen)
- **Transport:** 1× 3-Achser LKW

---

## Dateiformate

### Technische Zeichnungen
- SVG für Vektorgrafiken (skalierbar)
- PNG für Einbettung in Word (min. 1200px Breite)
- PDF für Druck

### Dokumente
- DOCX für bearbeitbare Version
- PDF für Abgabe/Druck

### Zeichnungsinhalte
**Grundriss:**
- Gebäudeumriss (schraffiert)
- Gerüstbelag (Kontur)
- Ständerpositionen (Punkte)
- Verankerungen (Linien)
- Zugang markiert
- Masslinien
- Legende
- Nordpfeil

**Schnitt/Ansicht:**
- Gebäudeprofil mit Dach
- Gerüstlagen nummeriert
- Höhenkoten
- Beläge, Geländer, Diagonalen
- Verankerungen
- Fussplatten
- Terrain

**Gerüstkarte:**
- Firmenangaben
- Objektdaten
- Lastklasse (farbig hervorgehoben)
- Breitenklasse
- Zugänge
- Nutzungsbeschränkungen
- Freigabefeld mit Unterschrift/Stempel

**Checkliste:**
- Positionsnummern
- Materialbezeichnung
- Soll-Mengen (vorausgefüllt)
- Ist-Mengen (leer)
- OK/Mängel Checkboxen
- Bemerkungsfeld

---

## Firma (Beispiel)
**Lawil Gerüstbau AG**
Murtenstrasse 30
3202 Frauenkappelen
Tel. 031 920 00 30
west@lawil.ch | www.lawil.ch
(Einer der grössten CH-Gerüstbauer, arbeitet mit Layher)
