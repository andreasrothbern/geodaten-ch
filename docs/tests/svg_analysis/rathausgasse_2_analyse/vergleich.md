# SVG-Vergleich: API vs. Claude.ai

## Gebäude: Kirche St. Peter und Paul
- **Adresse:** Rathausgasse 2, 3011 Bern
- **EGID:** 191821074
- **Komplexität:** COMPLEX (4 Zonen)
- **Datum:** 30.12.2025

---

## Übersicht

| SVG-Typ | API-Qualität | Claude.ai-Qualität | Gewinner |
|---------|--------------|-------------------|----------|
| Grundriss | ⭐⭐ (40%) | ⭐⭐⭐⭐⭐ (95%) | **Claude.ai** |
| Ansicht | ⭐⭐⭐⭐ (80%) | ⭐⭐⭐⭐⭐ (90%) | **Claude.ai** |
| Schnitt | ⭐⭐⭐⭐⭐ (90%) | ⭐⭐⭐⭐⭐ (92%) | **Gleich** |

---

## Detaillierter Vergleich

### 1. GRUNDRISS

| Aspekt | API-SVG | Claude.ai-SVG | Bewertung |
|--------|---------|---------------|-----------|
| **ViewBox** | 600×500 ❌ | 700×480 ✅ | Claude besser |
| **Format** | Interaktiv mit CSS | Technisch statisch | Claude besser |
| **Zonen-Darstellung** | Nur Polygon | Alle 4 Zonen separat | Claude besser |
| **Turm erkennbar** | ❌ Nein | ✅ Ja, mit Höhe | Claude besser |
| **Kirchenschiff** | ❌ Nicht differenziert | ✅ Zentral markiert | Claude besser |
| **Seitenschiffe** | ❌ Nicht erkennbar | ✅ Oben/Unten | Claude besser |
| **Chor** | ❌ Nicht erkennbar | ✅ Rechts markiert | Claude besser |
| **Nordpfeil** | ✅ Vorhanden | ✅ Vorhanden | Gleich |
| **Massstab** | ✅ 10m | ✅ 10m/20m | Gleich |
| **Gerüst-Zugänge** | ❌ Nicht markiert | ✅ Z1-Z4 markiert | Claude besser |

**Hauptproblem API:** Der Grundriss-Generator verwendet ein komplett anderes Format (interaktiv, falsches ViewBox) und zeigt keine Zonen-Unterscheidung.

### 2. FASSADENANSICHT

| Aspekt | API-SVG | Claude.ai-SVG | Bewertung |
|--------|---------|---------------|-----------|
| **ViewBox** | 700×480 ✅ | 700×480 ✅ | Gleich |
| **Proportionen** | ✅ Korrekt | ✅ Korrekt | Gleich |
| **Turm (54.6m)** | ✅ Dominant | ✅ Dominant | Gleich |
| **Kirchenschiff (25m)** | ✅ Sichtbar | ✅ Sichtbar | Gleich |
| **Seitenschiffe (12m)** | ✅ Links/Rechts | ✅ Links/Rechts | Gleich |
| **Chor (18m)** | ✅ Hinten | ✅ Hinten | Gleich |
| **Gotische Details** | ❌ Keine | ✅ Spitzbögen | Claude besser |
| **Gerüst-Lagen** | ✅ 27 Lagen | ✅ 27 Lagen | Gleich |
| **Höhenskala** | ✅ Links | ✅ Links | Gleich |
| **Verankerungen** | ✅ Rot gestrichelt | ✅ Rot gestrichelt | Gleich |

**Hauptunterschied:** Claude.ai zeigt gotische Architekturdetails (Spitzbögen), API nicht.

### 3. GEBÄUDESCHNITT

| Aspekt | API-SVG | Claude.ai-SVG | Bewertung |
|--------|---------|---------------|-----------|
| **ViewBox** | 700×480 ✅ | 700×480 ✅ | Gleich |
| **Schnittflächen** | ✅ Dicht schraffiert | ✅ Dicht schraffiert | Gleich |
| **Innenräume** | ✅ LEER/Weiss | ✅ LEER/Weiss | Gleich |
| **Turm-Innenraum** | ✅ Geschosse sichtbar | ✅ Geschosse sichtbar | Gleich |
| **Kirchenschiff** | ✅ Hoher Raum | ✅ Hoher Raum | Gleich |
| **Gewölbe** | ❌ Nicht angedeutet | ✅ Gestrichelt | Claude besser |
| **Gerüst links** | ✅ Bis 54.6m | ✅ Bis 54.6m | Gleich |
| **Gerüst rechts** | ✅ Bis Chor | ✅ Bis Chor | Gleich |
| **Zonenbeschriftung** | ✅ Unten | ✅ Unten | Gleich |
| **Schnittmarkierung A-A** | ✅ Rechts | ✅ Oben | Claude besser |

**Hauptunterschied:** Claude.ai deutet das gotische Gewölbe an.

---

## Kritische Probleme

### Problem 1: Grundriss-Generator inkompatibel

**Beobachtung:**
- API-Grundriss verwendet ViewBox 600×500 statt 700×480
- Interaktive CSS-Klassen (.facade-segment)
- Keine Zonen-Unterscheidung
- Format passt nicht zum Prompt

**Ursache:**
Der Grundriss wird offenbar von einem anderen SVG-Generator erzeugt, der nicht dem neuen Prompt-Format folgt.

**Auswirkung:**
- Grundriss ist für Gerüstplanung unbrauchbar
- Keine Erkennung von Turm, Kirchenschiff, Seitenschiffe, Chor
- Inkonsistentes Erscheinungsbild

### Problem 2: Fehlende architektonische Details

**Beobachtung:**
- Neugotik-Stil wird im Prompt erwähnt
- API-SVGs zeigen keine gotischen Elemente

**Ursache:**
Prompt enthält keinen Hinweis auf stil-spezifische Darstellung.

**Auswirkung:**
- SVGs sehen generisch aus
- Kirche nicht als Kirche erkennbar

### Problem 3: Zonen-Warnungen

**Beobachtung:**
```
Zone 'Kirchenschiff' (25.0m) deutlich unter API-Traufhöhe (46.4m)
Zone 'Seitenschiffe' (12.0m) deutlich unter API-Traufhöhe (46.4m)
Zone 'Chor' (18.0m) deutlich unter API-Traufhöhe (46.4m)
```

**Ursache:**
Die API-Traufhöhe (46.4m) bezieht sich auf den Turm, nicht auf das Kirchenschiff. Die Validierung vergleicht falsch.

**Auswirkung:**
- Unnötige Warnungen verwirren
- Zonen-Daten sind eigentlich korrekt

---

## Checklisten-Auswertung

### Grundriss
- [x] Gebäudeform korrekt (Kreuzform-Kirche)? **Claude: Ja, API: Nein**
- [ ] Innenhöfe als Freifläche markiert? **N/A - keine Innenhöfe**
- [x] Fassaden beschriftet? **Claude: Ja, API: Teilweise**
- [x] Nordpfeil vorhanden? **Beide: Ja**
- [x] Massstab korrekt? **Beide: Ja**

### Ansicht
- [x] Proportionen stimmen? **Beide: Ja**
- [x] Zonen erkennbar? **Beide: Ja**
- [x] Gerüst VOR der Fassade? **Beide: Ja**
- [x] Höhenskala links? **Beide: Ja**
- [x] Terrain-Linie unten? **Beide: Ja**

### Schnitt
- [x] Schnittflächen dicht schraffiert? **Beide: Ja**
- [x] Innenräume LEER (weiss)? **Beide: Ja**
- [x] Geschossdecken horizontal? **Beide: Ja**
- [x] Gerüst links und rechts? **Beide: Ja**

---

## Fazit

| Kategorie | Ergebnis |
|-----------|----------|
| **API-Stärke** | Ansicht und Schnitt sind gut |
| **API-Schwäche** | Grundriss ist unbrauchbar |
| **Claude.ai-Stärke** | Konsistente Qualität, architektonische Details |
| **Claude.ai-Schwäche** | Manuelle Generierung nötig |

**Empfehlung:** Grundriss-Generator muss auf das neue Format umgestellt werden.

---

*Analyse erstellt: 30.12.2025*
*Für: geodaten-ch Projekt*
