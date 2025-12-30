# Komplette Prompt-Analyse: Kirche St. Peter und Paul

## Kontext

Wir entwickeln eine App fuer Geruestplanung in der Schweiz. Die App generiert automatisch Prompts fuer Claude API, um technische SVG-Zeichnungen (Grundriss, Ansicht, Schnitt) zu erstellen.

**Ziel dieser Analyse:**
1. Identifikation von Schwaechen im Prompt und in der Datengewinnung
2. Vergleich: Claude.ai (Chat) vs. Claude API (One-Shot)
3. Konkrete Verbesserungsvorschlaege

---

## Teil 1: Das generierte Prompt (Input an Claude API)

```markdown
# SVG-Generierung: Grundriss + Fassadenansicht + Gebaeudeschnitt

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Rathausgasse 2 3011 Bern
- **EGID:** 191821074
- **Koordinaten (LV95):** E 601009, N 199736
- **Gebaeudename:** Kirche St. Peter und Paul
- **Gebaeudetyp:** Christkatholische Kathedralkirche
- **Baustil:** Neugotik
- **Baujahr:** 1864
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 46.4 m
- **Firsthoehe:** 54.6 m
- **Geschosse:** -
- **Grundflaeche:** 1099 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 47 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 48.2m × 29.1m
- **Umfang:** 168.1 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 533.5 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 533.5 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** satteldach_mit_turm
- **Dachneigung:** 29°
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen

| Zone | Typ | Hoehe | Traufe | Geruest |
|------|-----|------|--------|--------|
| Kirchenschiff | hauptgebaeude | 25.0m | 18.0m | Standard |
| Seitenschiffe | anbau | 12.0m | 9.0m | Standard |
| Chor | anbau | 18.0m | 12.0m | Standard |
| Westturm | turm | 54.6m | 25.0m | Sonderkonstruktion |

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche)

## 7. Fassaden

| Seite | Länge (m) | Richtung |
|-------|-----------|----------|
| 0 | 5.3 | O |
| 1 | 3.1 | N |
| 2 | 6.7 | O |
| 3 | 1.5 | N |
| 4 | 1.3 | O |
| 5 | 1.5 | S |
| 6 | 7.2 | O |
| 7 | 1.5 | N |
| ... | (38 weitere) | ... |

- **Laengste Fassade:** 18.4 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position | Grund |
|--------|---------|----------|-------|
| Z1 | O | 12% | - |
| Z2 | SO | 18% | - |
| Z3 | N | 27% | - |
| Z4 | W | 91% | - |

## 10. SVG Style-Vorgaben (KRITISCH!)

[... Style-Vorgaben wie im Bundeshaus-Prompt ...]

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** Rechteckige Huelle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung
- **Zonen:** Farblich unterscheiden, Innenhoefe markieren

### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **Terrain-Linie:** bei +/-0.00 = 533.5 m ue.M.

### SVG 3: Gebaeudeschnitt (Querschnitt)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenraeume, Konstruktion, Raumhoehen
```

---

## Teil 2: Datenquellen

| Quelle | Daten | Status | Probleme |
|--------|-------|--------|----------|
| **swisstopo API** | Geocoding, Koordinaten | OK | - |
| **GWR (via swisstopo)** | EGID, Baujahr | OK | Geschosse fehlt |
| **swissBUILDINGS3D** | Trauf-/Firsthoehe | Fragwuerdig | 46.4m = nur Turm? |
| **geodienste.ch WFS** | Polygon (47 Punkte) | OK | Sehr komplex |
| **swissALTI3D** | Terrain-Hoehe | OK | - |
| **known_buildings.py** | Name, Zonen, Typ | Manuell | Kirchen-spezifisch |
| **Frontend Geruest-Tab** | Editierte Zonen | MISMATCH! | Nicht im Prompt! |

### KRITISCH: Mismatch Frontend vs. Prompt

Das Frontend (Geruest-Tab) zeigt andere Zonenwerte als das Prompt:

| Zone | Frontend (editierbar) | Prompt (an Claude API) |
|------|----------------------|------------------------|
| Kirchenschiff | Höhe 22m, Traufe 18m, First 22m | Höhe 25.0m, Traufe 18.0m |
| Westturm | Höhe 60m, Traufe 40m, First 55m | Höhe 54.6m, Traufe 25.0m |
| Chor | Höhe 15m, Traufe 12m, First 15m | Höhe 18.0m, Traufe 12.0m |
| Seitenschiffe | **FEHLT IM FRONTEND** | Höhe 12.0m, Traufe 9.0m |

**Problem:** Die im Frontend editierten/angezeigten Zonen werden NICHT an den Prompt uebergeben!

**Fehlende architektonische Beschreibungen im Prompt:**
- "Dreischiffige Basilika mit neugotischer Architektur" (aus Frontend)
- "Zentraler Westturm mit Spitzhelm - Spezialgerüst erforderlich"
- "Chor/Apsis mit niedrigerer Höhe als Hauptschiff"

### Bekannte Probleme

1. **Traufhoehe 46.4m:** Diese Hoehe ist unrealistisch fuer eine Kirche. Vermutlich wurde die Turmspitze als "Traufe" gemessen. Die tatsaechliche Traufhoehe des Kirchenschiffs liegt bei ca. 18m.

2. **47-Punkte-Polygon:** Sehr detailliertes Polygon, das die Strebepfeiler der neugotischen Kirche abbildet. Fuer Geruest-Zwecke zu granular.

3. **Geschosse fehlt:** Fuer Kirchen gibt es keine klare Geschoss-Definition.

4. **🔴 KRITISCH: Frontend-Zonen werden nicht verwendet:** Die im Gerüstbau-Tab angezeigten und editierbaren Zonen fliessen NICHT in das Prompt ein. Das Prompt verwendet stattdessen die Werte aus known_buildings.py (oder Claude-Recherche), die abweichen können.

---

## Teil 3: Die API-generierten SVGs

### SVG 1: Grundriss

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
<defs>
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>

<!-- Hintergrund -->
<rect width="700" height="480" fill="#FFFFFF"/>

<!-- Gerüstzone (äußere Hülle mit 1m Abstand) -->
<rect x="200" y="120" width="290" height="175" fill="none" stroke="#0066CC" stroke-width="2" stroke-dasharray="5,5"/>

<!-- Hauptgebäude: Kirchenschiff -->
<rect x="210" y="130" width="210" height="70" fill="url(#hatch)" stroke="#000" stroke-width="2"/>

<!-- Seitenschiffe -->
<rect x="210" y="200" width="210" height="40" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
<rect x="210" y="240" width="210" height="40" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>

<!-- Chor -->
<rect x="340" y="280" width="80" height="50" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>

<!-- Westturm -->
<rect x="240" y="100" width="20" height="30" fill="url(#hatch)" stroke="#000" stroke-width="2"/>

<!-- Gerüstzugänge -->
<circle cx="480" cy="165" r="4" fill="#CC0000"/>
<text x="490" y="169" font-family="Arial" font-size="10" fill="#CC0000">Z1</text>

<circle cx="450" cy="295" r="4" fill="#CC0000"/>
<text x="460" y="299" font-family="Arial" font-size="10" fill="#CC0000">Z2</text>

<circle cx="270" cy="125" r="4" fill="#CC0000"/>
<text x="280" y="129" font-family="Arial" font-size="10" fill="#CC0000">Z3</text>

<circle cx="205" cy="260" r="4" fill="#CC0000"/>
<text x="180" y="264" font-family="Arial" font-size="10" fill="#CC0000">Z4</text>

<!-- Titel -->
<text x="350" y="30" font-family="Arial" font-size="16" font-weight="bold" fill="#000" text-anchor="middle">Grundriss - Kirche St. Peter und Paul</text>
<text x="350" y="45" font-family="Arial" font-size="12" fill="#000" text-anchor="middle">Rathausgasse 2, 3011 Bern - EGID: 191821074</text>

</svg>
```

### SVG 2: Fassadenansicht

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
<defs>
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>
</defs>

<!-- Hintergrund -->
<rect width="700" height="480" fill="#FFFFFF"/>

<!-- Terrain-Linie -->
<rect x="0" y="370" width="700" height="110" fill="url(#ground)"/>
<line x1="80" y1="370" x2="580" y2="370" stroke="#000" stroke-width="2"/>

<!-- Seitenschiffe -->
<rect x="150" y="310" width="50" height="60" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
<polygon points="150,310 175,280 200,310" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>

<rect x="380" y="310" width="50" height="60" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
<polygon points="380,310 405,280 430,310" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>

<!-- Chor -->
<rect x="450" y="330" width="80" height="40" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>
<polygon points="450,330 490,300 530,330" fill="url(#hatch)" stroke="#000" stroke-width="1.5"/>

<!-- Kirchenschiff (Hauptgebäude) -->
<rect x="200" y="270" width="180" height="100" fill="url(#hatch)" stroke="#000" stroke-width="2"/>
<polygon points="200,270 290,220 380,270" fill="url(#hatch)" stroke="#000" stroke-width="2"/>

<!-- Westturm -->
<rect x="100" y="170" width="60" height="200" fill="url(#hatch)" stroke="#000" stroke-width="2"/>
<polygon points="100,170 130,140 160,170" fill="url(#hatch)" stroke="#000" stroke-width="2"/>

<!-- Gerüst Westturm -->
<line x1="80" y1="140" x2="80" y2="370" stroke="#0066CC" stroke-width="3"/>
<line x1="180" y1="140" x2="180" y2="370" stroke="#0066CC" stroke-width="3"/>
<rect x="80" y="150" width="100" height="3" fill="#8B4513"/>
<rect x="80" y="180" width="100" height="3" fill="#8B4513"/>

<!-- Höhenskala -->
<text x="45" y="375" text-anchor="end" font-size="10" fill="#000">±0.00</text>
<text x="45" y="275" text-anchor="end" font-size="10" fill="#000">+18.0</text>
<text x="45" y="225" text-anchor="end" font-size="10" fill="#000">+25.0</text>
<text x="45" y="145" text-anchor="end" font-size="10" fill="#000">+54.6</text>

<!-- Titel -->
<text x="350" y="30" text-anchor="middle" font-size="14" font-weight="bold" fill="#000">Kirche St. Peter und Paul - Südfassade</text>
<text x="350" y="50" text-anchor="middle" font-size="12" fill="#000">Rathausgasse 2, 3011 Bern - EGID: 191821074</text>

</svg>
```

### SVG 3: Gebaeudeschnitt

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
      <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
    </pattern>
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
  </defs>

  <!-- Terrain -->
  <rect x="0" y="400" width="700" height="80" fill="url(#ground)" stroke="#666" stroke-width="0.5"/>
  <line x1="0" y1="400" x2="700" y2="400" stroke="#333" stroke-width="1"/>
  <text x="10" y="415" font-family="Arial" font-size="10" fill="#666">+/-0.00 = 533.5 m ü.M.</text>

  <!-- Westturm (links) -->
  <rect x="100" y="182" width="80" height="218" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  <rect x="110" y="192" width="60" height="198" fill="#FFFFFF"/>

  <!-- Hauptschiff (Kirchenschiff) -->
  <rect x="240" y="250" width="220" height="150" fill="url(#cut-hatch)" stroke="#333" stroke-width="2"/>
  <rect x="250" y="260" width="200" height="130" fill="#FFFFFF"/>

  <!-- Hauptschiff Dach (Satteldach 29°) -->
  <path d="M240,250 L350,200 L460,250 Z" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Höhenangaben -->
  <text x="25" y="185" font-family="Arial" font-size="8" text-anchor="end" fill="#666">54.6m</text>
  <text x="25" y="253" font-family="Arial" font-size="8" text-anchor="end" fill="#666">25.0m</text>
  <text x="25" y="403" font-family="Arial" font-size="8" text-anchor="end" fill="#666">0.0m</text>

  <!-- Titel -->
  <text x="350" y="30" font-family="Arial" font-size="14" font-weight="bold" text-anchor="middle" fill="#333">Querschnitt A-A</text>
  <text x="350" y="45" font-family="Arial" font-size="10" text-anchor="middle" fill="#666">Kirche St. Peter und Paul, Rathausgasse 2, 3011 Bern</text>

</svg>
```

---

## Teil 4: Analyse-Aufgaben

Bitte analysiere die Daten und SVGs:

### A. Prompt-Qualitaet

1. **Datenluecken:**
   - Welche wichtigen Informationen fehlen im Prompt?
   - Welche Daten sind fragwuerdig oder inkonsistent?

2. **Strukturelle Schwaechen:**
   - Ist die Prompt-Struktur optimal fuer Claude?
   - Sind die Anweisungen klar genug?

3. **Fehlende architektonische Details:**
   - Was muesste Claude ueber die Kirche St. Peter und Paul wissen?
   - Welche Bauteile sind nicht beschrieben (z.B. Strebepfeiler, Spitzbogenfenster)?

### B. Datengewinnung

1. **swissBUILDINGS3D Problem:**
   - Die gemessene Traufhoehe ist 46.4m - das entspricht dem Turm, nicht dem Kirchenschiff
   - Wie koennen wir die Hoehen PRO ZONE besser ermitteln?

2. **Polygon-Interpretation:**
   - Das Polygon hat 47 Punkte - wie koennen wir daraus die Gebaeudestruktur ableiten?
   - Neugotische Strebepfeiler verursachen viele Polygon-Punkte

3. **Kirchen-spezifische Recherche:**
   - Welche zusaetzlichen Datenquellen koennten helfen?
   - Was sollte die Claude-Recherche (Haiku) zusaetzlich liefern?

### C. SVG-Qualitaet

1. **Grundriss:**
   - Ist die Darstellung der 4 Zonen korrekt?
   - Fehlen wichtige Elemente (Altar, Eingaenge, Strebepfeiler)?

2. **Ansicht:**
   - Entspricht die Proportionen der neugotischen Architektur?
   - Sind die Spitzbogenfenster erkennbar?

3. **Schnitt:**
   - Zeigt der Schnitt die typische Basilika-Struktur (Mittelschiff hoeher als Seitenschiffe)?
   - Sind die Gewoelbe angedeutet?

---

## Teil 5: Vergleichsaufgabe

### Claude.ai vs. Claude API

**Aufgabe:** Generiere dieselben 3 SVGs basierend auf dem obigen Prompt.

**Vergleiche dann:**

1. **Qualitaetsunterschiede:**
   - Welche SVG-Elemente sind bei Claude.ai besser/anders?
   - Wo weicht die API-Version ab?

2. **Ursachen-Analyse:**
   - Warum produziert Claude API ein anderes Ergebnis?
   - Liegt es am One-Shot vs. iterativen Ansatz?

3. **Prompt-Optimierung:**
   - Welche Aenderungen im Prompt wuerden die API-Qualitaet verbessern?
   - Braucht es mehr Kontext fuer neugotische Architektur?

---

## Teil 6: Erwartetes Ausgabeformat

Bitte antworte mit:

### 1. Schwaechen-Tabelle

| Kategorie | Problem | Auswirkung | Prioritaet |
|-----------|---------|------------|------------|
| Prompt | ... | ... | P1/P2/P3 |
| Daten | ... | ... | P1/P2/P3 |
| SVG | ... | ... | P1/P2/P3 |

### 2. Konkrete Verbesserungen

- **Fuer Prompt:** Code-Aenderungen oder neue Felder
- **Fuer Recherche:** Neue Datenquellen oder Abfragen
- **Fuer known_buildings.py:** Zusaetzliche Attribute fuer Kirchen

### 3. Deine eigenen SVGs

Generiere 3 SVGs basierend auf dem Prompt und erklaere die Unterschiede.

### 4. Kirchen-spezifische Empfehlungen

- Welche zusaetzlichen Zonen-Typen braucht es fuer Sakralbauten?
- Wie sollten Strebepfeiler im Polygon behandelt werden?
- Welche architektonischen Details sind fuer Geruest relevant?

### 5. 🔴 KRITISCH: Frontend-Zonen ins Prompt integrieren

**Aktuelles Problem:**
- Frontend zeigt editierbare Zonen (aus Claude-Analyse oder known_buildings.py)
- User kann Höhenwerte im Gerüstbau-Tab anpassen
- **ABER:** Diese Anpassungen fliessen NICHT in das Prompt fuer die SVG-Generierung!

**Konkrete Loesungsvorschlaege:**

```
Option A: Frontend-Zonen als Parameter an /api/v1/smart-building/svg uebergeben

POST /api/v1/smart-building/svg
{
  "address": "Rathausgasse 2, 3011 Bern",
  "svg_type": "all",
  "zones_override": [
    {"name": "Kirchenschiff", "type": "hauptgebaeude", "height_m": 22, "traufe_m": 18, "first_m": 22},
    {"name": "Westturm", "type": "turm", "height_m": 60, "traufe_m": 40, "first_m": 55, "sonderkonstruktion": true},
    {"name": "Chor", "type": "anbau", "height_m": 15, "traufe_m": 12, "first_m": 15}
  ]
}

Option B: Editierte Zonen in BuildingDataBundle cachen

- Wenn User Zonen editiert -> Cache im LocalStorage
- Bei SVG-Request: Editierte Zonen aus Cache laden
- In Prompt einfuegen statt known_buildings.py Daten

Option C: Zonen-Editor-Modus fuer SVG-Generierung

- "Mit diesen Zonen SVG generieren" Button im Frontend
- Uebergibt aktuelle Frontend-Zonen direkt an API
```

**Empfehlung:** Option A implementieren - ist am saubersten und erlaubt auch Batch-SVG-Generierung mit benutzerdefinierten Zonen.

---

*Generiert: 30.12.2025*
*App: Geruestplanung Schweiz v3.0 - SmartBuildingService*
*Gebaeude: Kirche St. Peter und Paul, Rathausgasse 2, 3011 Bern*
