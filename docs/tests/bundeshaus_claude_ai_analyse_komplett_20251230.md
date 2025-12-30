# Prompt-Qualitaets-Analyse: Bundeshaus SVG-Generierung

## Kontext

Wir entwickeln eine App fuer Geruestplanung in der Schweiz. Die App generiert automatisch Prompts fuer Claude API, um technische SVG-Zeichnungen (Grundriss, Ansicht, Schnitt) zu erstellen.

**Ziele dieser Analyse:**
1. Identifikation von Schwaechen im Prompt und in der Datengewinnung
2. **VERGLEICH:** Du (Claude.ai) sollst selbst SVGs generieren und mit den API-Ergebnissen vergleichen
3. **ERKLAERUNG:** Warum produziert dasselbe Prompt ueber Claude API andere Ergebnisse als hier in Claude.ai?

---

## WICHTIG: Deine Aufgaben

### Aufgabe 1: Eigene SVGs generieren
Generiere basierend auf dem Prompt in Teil 1 deine eigenen SVGs:
- Grundriss
- Fassadenansicht
- Gebaeudeschnitt

### Aufgabe 2: Vergleich
Vergleiche deine SVGs mit den API-generierten SVGs in Teil 3:
- Was machst du anders?
- Was ist besser/schlechter?
- Welche architektonischen Details erkennst du, die die API nicht dargestellt hat?

### Aufgabe 3: Erklaerung API vs. Chat
Erklaere, warum dasselbe Prompt unterschiedliche Ergebnisse liefert:
- Claude API (Sonnet) vs. Claude.ai Chat
- One-Shot vs. iteratives Arbeiten
- Kontextwissen vs. nur Prompt-Daten

---

# TEIL 1: DAS GENERIERTE PROMPT (INPUT AN CLAUDE API)

```markdown
# SVG-Generierung: Grundriss + Fassadenansicht + Gebaeudeschnitt

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT.

## 1. Gebaeude-Identifikation
- **Adresse:** Bundesplatz 3 3011 Bern
- **EGID:** 2242547
- **Koordinaten (LV95):** E 600423, N 199521
- **Gebaeudename:** Bundeshaus
- **Gebaeudetyp:** Parlamentsgebaeude
- **Baustil:** Neorenaissance / Historismus
- **Baujahr:** 1902
- **Komplexitaet:** COMPLEX

## 3. Geometrische Basisdaten
### Dimensionen
- **Traufhoehe:** 53.2 m
- **Firsthoehe:** 62.6 m
- **Geschosse:** -
- **Grundflaeche:** 3697 m2

### Polygon
> **HINWEIS:** Komplexes Polygon mit 26 Punkten
> -> Vereinfachte rechteckige Darstellung empfohlen
- **Bounding Box:** 80.2m x 71.0m
- **Umfang:** 310.0 m

## 4. Terrain (swissALTI3D)
- **Terrain-Hoehe:** 543.1 m ue.M.
- **Referenzpunkt:** Haupteingang = +/-0.00 = 543.1 m ue.M.
- **Hanglage:** Nein (eben)

## 5. Dach-Analyse
- **Dachform:** kuppel
- **Dachneigung:** 15 deg
- **First-Ausrichtung:** N-S
- **Konfidenz:** 50%

## 6. Hoehenzonen

| Zone | Typ | Hoehe | Traufe | Geruest |
|------|-----|------|--------|--------|
| Arkaden | arkade | 6.0m | 6.0m | Standard |
| Hauptgebaeude | hauptgebaeude | 30.0m | 25.0m | Standard |
| Kuppel | kuppel | 64.0m | 30.0m | Sonderkonstruktion |

### Zone-Typen Legende
- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur
- **arkade** = Niedriger Bereich mit Rundbogen
- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)
- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)
- **anbau** = Niedrigerer Anbau am Hauptgebaeude
- **innenhof** = Nicht einruesten (Freiflaeche)

## 7. Fassaden

| Seite | Laenge (m) | Richtung |
|-------|-----------|----------|
| 0 | 14.0 | O |
| 1 | 15.4 | N |
| 2 | 4.0 | W |
| 3 | 14.8 | N |
| 4 | 16.5 | O |
| 5 | 6.0 | N |
| 6 | 27.0 | O |
| 7 | 6.0 | S |
| ... | (17 weitere) | ... |

- **Laengste Fassade:** 27.0 m

## 8. Geruest-Zugaenge (SUVA)
[OK] SUVA-konform (max. 50m Fluchtweg)

| Zugang | Fassade | Position |
|--------|---------|----------|
| Z1 | N | 93% |
| Z2 | N | 7% |
| Z3 | O | 42% |
| Z4 | O | 3% |
| Z5 | S | 47% |
| Z6 | W | 51% |
| Z7 | N | 93% |

## 10. SVG Style-Vorgaben (KRITISCH!)

[... Style-Definitionen mit Patterns und Farben ...]

## 11. Anforderungen pro SVG

### SVG 1: Grundriss (Draufsicht)
- Vogelperspektive, Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- Nordpfeil, Massstab, Fassaden-Beschriftung
- Zonen farblich unterscheiden, Innenhoefe markieren

### SVG 2: Fassadenansicht (Elevation)
- Frontalansicht von AUSSEN, orthogonal (2D)
- NUR sichtbare Aussenflaeche
- Geruest VOR der Fassade

### SVG 3: Gebaeudeschnitt (Querschnitt)
- Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A
- Geschnittene Mauern = DICHTE Schraffur
- Innenraeume = WEISS/LEER
```

---

# TEIL 2: DATENQUELLEN

Unsere App sammelt Daten aus folgenden Quellen:

| Quelle | Daten | Wert | Status |
|--------|-------|------|--------|
| **swisstopo API** | Geocoding, Koordinaten | E 600423, N 199521 | OK |
| **GWR (via swisstopo)** | EGID | 2242547 | OK |
| **GWR (via swisstopo)** | Baujahr | 1902 | OK |
| **GWR (via swisstopo)** | Geschosse | - (fehlt!) | PROBLEM |
| **swissBUILDINGS3D** | Traufhoehe | 53.2 m | FRAGWUERDIG |
| **swissBUILDINGS3D** | Firsthoehe | 62.6 m | OK (Kuppel) |
| **geodienste.ch WFS** | Polygon | 26 Punkte | OK |
| **geodienste.ch WFS** | Grundflaeche | 3697 m2 | OK |
| **swissALTI3D** | Terrain-Hoehe | 543.1 m ue.M. | OK |
| **known_buildings.py** | Name, Zonen, Typ | Bundeshaus | MANUELL |

### Bekannte Probleme:

1. **Traufhoehe 53.2m** - Das ist NICHT die Traufe des Hauptgebaeudes (ca. 25m), sondern vermutlich die Kuppel-Unterkante
2. **Geschosse fehlen** - GWR liefert keine Geschosszahl fuer das Bundeshaus
3. **Polygon = 1 Stueck** - Kein separates Polygon fuer Ehrenhof/Seitenfluegel

---

# TEIL 3: DIE GENERIERTEN SVGs (OUTPUT VON CLAUDE API)

## SVG 1: Grundriss

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <rect width="700" height="480" fill="#FFFFFF"/>

  <text x="350" y="25" text-anchor="middle" font-family="Arial" font-size="16" font-weight="bold">GRUNDRISS - Bundeshaus Bern</text>
  <text x="350" y="40" text-anchor="middle" font-family="Arial" font-size="10">EGID: 2242547 | LV95: E 600423, N 199521</text>

  <!-- Geruest-Huelle -->
  <rect x="190" y="80" width="320" height="290" fill="none" stroke="#0066CC" stroke-width="2" stroke-dasharray="5,5"/>

  <!-- Hauptgebaeude -->
  <rect x="200" y="90" width="300" height="270" fill="url(#hatch)" stroke="#000" stroke-width="2"/>

  <!-- Arkaden -->
  <rect x="210" y="100" width="280" height="30" fill="url(#hatch)" stroke="#000" stroke-width="1"/>
  <text x="350" y="118" text-anchor="middle" font-family="Arial" font-size="8">ARKADEN (6.0m)</text>

  <!-- Kuppel -->
  <circle cx="350" cy="235" r="40" fill="url(#copper)" stroke="#000" stroke-width="2"/>
  <text x="350" y="240" text-anchor="middle" font-family="Arial" font-size="8" fill="white">KUPPEL (64.0m)</text>

  <!-- Geruest-Zugaenge Z1-Z6 -->
  <circle cx="350" cy="85" r="3" fill="#0066CC"/>
  <text x="350" y="75" text-anchor="middle" font-family="Arial" font-size="7" fill="#0066CC">Z1</text>

  <!-- Nordpfeil -->
  <g transform="translate(580,120)">
    <path d="M0,20 L0,0 M-5,5 L0,0 L5,5" stroke="#000" stroke-width="2" fill="none"/>
    <text x="10" y="12" font-family="Arial" font-size="12" font-weight="bold">N</text>
  </g>

  <!-- Legende -->
  <g transform="translate(30,300)">
    <rect x="0" y="0" width="120" height="100" fill="none" stroke="#666"/>
    <text x="60" y="15" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">HOEHENZONEN</text>
    <rect x="10" y="25" width="15" height="10" fill="url(#hatch)"/>
    <text x="30" y="32" font-family="Arial" font-size="8">Hauptgebaeude (30.0m)</text>
    <circle cx="17.5" cy="50" r="7.5" fill="url(#copper)"/>
    <text x="30" y="52" font-family="Arial" font-size="8">Kuppel (64.0m)</text>
  </g>
</svg>
```

## SVG 2: Fassadenansicht

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
  </defs>

  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Titel -->
  <text x="300" y="30" font-family="Arial" font-size="14" text-anchor="middle" font-weight="bold">Bundeshaus - Fassadenansicht Sued</text>

  <!-- Terrain -->
  <rect x="50" y="380" width="600" height="50" fill="url(#ground)"/>
  <line x1="50" y1="380" x2="550" y2="380" stroke="#666" stroke-width="1"/>

  <!-- Arkaden mit Boegen -->
  <rect x="100" y="340" width="400" height="40" fill="url(#hatch)" stroke="#333" stroke-width="1"/>
  <circle cx="120" cy="360" r="15" fill="none" stroke="#333" stroke-width="1"/>
  <circle cx="160" cy="360" r="15" fill="none" stroke="#333" stroke-width="1"/>
  <!-- ... weitere Boegen ... -->

  <!-- Hauptgebaeude -->
  <rect x="100" y="160" width="400" height="180" fill="url(#hatch)" stroke="#333" stroke-width="1"/>

  <!-- Fenster (3 Reihen) -->
  <rect x="120" y="180" width="15" height="25" fill="#FFFFFF" stroke="#333" stroke-width="0.5"/>
  <!-- ... weitere Fenster ... -->

  <!-- Kuppel -->
  <ellipse cx="300" cy="160" rx="80" ry="60" fill="url(#copper)" stroke="#333" stroke-width="1"/>
  <ellipse cx="300" cy="120" rx="20" ry="15" fill="url(#copper)" stroke="#333" stroke-width="1"/>

  <!-- Geruest (blaue Staender) -->
  <line x1="85" y1="380" x2="85" y2="140" stroke="#0066CC" stroke-width="2"/>
  <!-- ... weitere Staender ... -->

  <!-- Belaege (braun) -->
  <rect x="85" y="150" width="430" height="3" fill="#8B4513"/>
  <!-- ... weitere Belaege ... -->

  <!-- Verankerungen (rot gestrichelt) -->
  <line x1="85" y1="300" x2="100" y2="300" stroke="#CC0000" stroke-width="1" stroke-dasharray="3,2"/>

  <!-- Hoehenskala links -->
  <text x="25" y="385" font-family="Arial" font-size="8" text-anchor="end">+/-0.00</text>
  <text x="25" y="165" font-family="Arial" font-size="8" text-anchor="end">+53.2m</text>
  <text x="25" y="110" font-family="Arial" font-size="8" text-anchor="end">+62.6m</text>

  <!-- Lagenbeschriftung rechts -->
  <text x="550" y="375" font-family="Arial" font-size="8">1. Lage</text>
  <text x="550" y="155" font-family="Arial" font-size="8">12. Lage</text>
</svg>
```

## SVG 3: Gebaeudeschnitt

```svg
<svg viewBox="0 0 700 480" xmlns="http://www.w3.org/2000/svg">
  <defs>
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

  <rect width="700" height="480" fill="#FFFFFF"/>

  <!-- Titel -->
  <text x="350" y="25" text-anchor="middle" font-family="Arial" font-size="14" font-weight="bold">GEBAEUDESCHNITT A-A - Bundeshaus</text>

  <!-- Terrain -->
  <rect x="50" y="400" width="600" height="20" fill="url(#ground)"/>
  <line x1="50" y1="400" x2="650" y2="400" stroke="#333" stroke-width="1"/>

  <!-- Hoehenskala -->
  <text x="40" y="405" text-anchor="end" font-family="Arial" font-size="8" fill="#666">+/-0.00</text>
  <text x="40" y="340" text-anchor="end" font-family="Arial" font-size="8" fill="#666">+6.0</text>
  <text x="40" y="200" text-anchor="end" font-family="Arial" font-size="8" fill="#666">+30.0</text>
  <text x="40" y="80" text-anchor="end" font-family="Arial" font-size="8" fill="#666">+64.0</text>

  <!-- Arkaden - geschnittene Mauern -->
  <rect x="100" y="340" width="20" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="580" y="340" width="20" height="60" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Hauptgebaeude - geschnittene Aussenmauern -->
  <rect x="150" y="200" width="25" height="200" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>
  <rect x="525" y="200" width="25" height="200" fill="url(#cut-hatch)" stroke="#333" stroke-width="1"/>

  <!-- Innenraum (WEISS/LEER) -->
  <rect x="175" y="200" width="350" height="200" fill="#FFFFFF" stroke="#333" stroke-width="1"/>

  <!-- Geschossdecken -->
  <line x1="175" y1="370" x2="525" y2="370" stroke="#333" stroke-width="1"/>
  <line x1="175" y1="340" x2="525" y2="340" stroke="#333" stroke-width="1"/>
  <line x1="175" y1="310" x2="525" y2="310" stroke="#333" stroke-width="1"/>
  <!-- ... weitere Decken ... -->

  <!-- Kuppel mit Kupfer-Gradient -->
  <path d="M 250,200 A 100,100 0 0,1 450,200 L 425,200 A 75,75 0 0,0 275,200 Z" fill="url(#copper)" stroke="#333" stroke-width="1"/>

  <!-- Kuppel-Innenraum (WEISS) -->
  <path d="M 275,200 A 75,75 0 0,1 425,200 L 425,200 L 275,200 Z" fill="#FFFFFF"/>

  <!-- Geruest links -->
  <g stroke="#0066CC" stroke-width="2" fill="none">
    <line x1="70" y1="70" x2="70" y2="420"/>
    <line x1="90" y1="70" x2="90" y2="420"/>
  </g>
  <!-- Belaege -->
  <line x1="70" y1="390" x2="90" y2="390" stroke="#8B4513" stroke-width="3"/>
  <!-- Verankerungen -->
  <line x1="90" y1="300" x2="150" y2="300" stroke="#CC0000" stroke-dasharray="3,3"/>

  <!-- Schnittmarkierung -->
  <circle cx="100" cy="450" r="10" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <text x="100" y="455" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold">A</text>
  <circle cx="600" cy="450" r="10" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
  <text x="600" y="455" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold">A</text>

  <!-- Legende -->
  <g transform="translate(520, 60)">
    <rect x="0" y="0" width="120" height="80" fill="#FFFFFF" stroke="#333" stroke-width="1"/>
    <text x="5" y="15" font-family="Arial" font-size="10" font-weight="bold">LEGENDE</text>
    <rect x="5" y="20" width="15" height="8" fill="url(#cut-hatch)"/>
    <text x="25" y="28" font-family="Arial" font-size="8">Schnittflaeche</text>
    <line x1="5" y1="35" x2="20" y2="35" stroke="#8B4513" stroke-width="3"/>
    <text x="25" y="38" font-family="Arial" font-size="8">Geruestbelag</text>
    <line x1="5" y1="45" x2="20" y2="45" stroke="#CC0000" stroke-dasharray="2,2"/>
    <text x="25" y="48" font-family="Arial" font-size="8">Verankerung</text>
    <rect x="5" y="55" width="15" height="8" fill="url(#copper)"/>
    <text x="25" y="63" font-family="Arial" font-size="8">Kuppel</text>
  </g>
</svg>
```

---

# TEIL 4: ANALYSE-AUFGABEN

Bitte analysiere die obigen Daten und beantworte:

## A. Prompt-Qualitaet

1. **Datenluecken:**
   - Welche wichtigen Informationen fehlen im Prompt?
   - Welche Daten sind fragwuerdig oder inkonsistent?
   - Warum zeigt die Hoehenskala "+53.2m" statt der korrekten Zonen-Hoehen?

2. **Strukturelle Schwaechen:**
   - Ist die Prompt-Struktur optimal fuer Claude?
   - Sind die Anweisungen klar genug?
   - Werden die Zonen-Daten (Arkaden 6m, Hauptgebaeude 30m, Kuppel 64m) korrekt verwendet?

3. **Fehlende architektonische Details:**
   - Was muesste Claude ueber das Bundeshaus wissen, um bessere SVGs zu generieren?
   - Welche Bauteile sind nicht beschrieben (z.B. Ehrenhof, Seitenfluegel, Westfluegel, Ostfluegel)?

## B. Datengewinnung

1. **swissBUILDINGS3D Problem:**
   - Die gemessene Traufhoehe ist 53.2m - das ist NICHT die Hauptgebaeude-Traufe!
   - Woher kommt dieser Wert? (Vermutlich Kuppel-Unterkante)
   - Wie koennen wir die Hoehen PRO ZONE automatisch ermitteln?

2. **Polygon-Interpretation:**
   - Das Polygon hat 26 Punkte - wie koennen wir daraus die Gebaeudestruktur ableiten?
   - Kann man aus dem Polygon den Ehrenhof erkennen?
   - Sollten wir das Polygon in Teil-Polygone zerlegen?

3. **Recherche-Erweiterung:**
   - Welche zusaetzlichen Datenquellen koennten helfen?
   - Was sollte die Claude-Recherche (Haiku) zusaetzlich liefern?

## C. SVG-Qualitaet

1. **Grundriss:**
   - Wird der Ehrenhof dargestellt?
   - Sind die Zonen korrekt positioniert?
   - Fehlen Bauteile?

2. **Ansicht:**
   - Stimmen die Proportionen (Arkaden vs. Hauptgebaeude vs. Kuppel)?
   - Ist die Fensteranordnung plausibel?
   - Fehlen architektonische Details (Risalite, Giebel, Skulpturen)?

3. **Schnitt:**
   - Sind die Geschosshoehen plausibel?
   - Ist die Kuppel-Konstruktion korrekt dargestellt?
   - Fehlt etwas Wichtiges?

## D. Konkrete Verbesserungsvorschlaege

1. **Fuer known_buildings.py:**
   - Welche zusaetzlichen Attribute sollten wir speichern?
   - Beispiel: `ehrenhof_position`, `seitenfluegel`, `risalite`?

2. **Fuer die Claude-Recherche:**
   - Welche Fragen sollte Claude Haiku beantworten?
   - Beispiel: "Hat das Gebaeude einen Innenhof? Wo sind die Haupteingaenge?"

3. **Fuer die Prompt-Struktur:**
   - Welche neuen Abschnitte waeren hilfreich?
   - Beispiel: "Architektonische Besonderheiten", "Nicht-rechteckige Elemente"?

---

# TEIL 5: ERWARTETES AUSGABEFORMAT

Bitte antworte mit:

## 1. DEINE EIGENEN SVGs

Generiere basierend auf dem Prompt in Teil 1 deine eigenen SVGs.
Nutze dein Wissen ueber das Bundeshaus (Parlamentsgebaeude der Schweiz):
- Ehrenhof auf der Suedseite
- Seitenfluegel (Ost/West)
- Kuppel ueber dem Nationalratssaal
- Arkaden im Erdgeschoss

Zeige die SVGs hier:

### Dein Grundriss:
```svg
[Dein SVG-Code hier]
```

### Deine Fassadenansicht:
```svg
[Dein SVG-Code hier]
```

### Dein Gebaeudeschnitt:
```svg
[Dein SVG-Code hier]
```

---

## 2. VERGLEICH: API-SVGs vs. Deine SVGs

Erstelle eine Vergleichstabelle:

| Aspekt | API-generiert (Teil 3) | Dein SVG | Bewertung |
|--------|------------------------|----------|-----------|
| Ehrenhof dargestellt? | Nein/Ja | Nein/Ja | API besser/Claude besser |
| Seitenfluegel erkennbar? | ... | ... | ... |
| Kuppel-Proportionen | ... | ... | ... |
| Arkaden-Darstellung | ... | ... | ... |
| Fensteranordnung | ... | ... | ... |
| Architektonische Details | ... | ... | ... |
| Gesamteindruck | ... | ... | ... |

---

## 3. ERKLAERUNG: Warum unterschiedliche Ergebnisse?

Erklaere die Unterschiede zwischen:

### A. Claude API (Sonnet) vs. Claude.ai Chat

| Faktor | Claude API | Claude.ai Chat |
|--------|------------|----------------|
| Kontext | Nur Prompt | Prompt + Vorwissen + Iteration |
| Feedback | Keins (One-Shot) | Visuelles Feedback moeglich |
| Iteration | Keine | Mehrere Durchlaeufe moeglich |
| Wissen | Nur Prompt-Daten | Architektur-Wissen abrufbar |

### B. Was fehlt dem API-Prompt?

Liste konkret auf, welche Informationen im Prompt fehlen, die du (Claude.ai) aus deinem Wissen ergaenzen kannst:

1. **Architektonisches Wissen:**
   - z.B. "Das Bundeshaus hat einen U-foermigen Grundriss mit Ehrenhof"

2. **Proportions-Wissen:**
   - z.B. "Die Kuppel ist ca. 1/3 der Gebaeudebreite"

3. **Detail-Wissen:**
   - z.B. "Die Arkaden haben 7 Bogen auf jeder Seite"

### C. Wie koennte die App dieses Wissen automatisch beschaffen?

Schlage vor:
- Welche Recherche-Fragen sollte Claude Haiku stellen?
- Welche Datenquellen koennten helfen?
- Was sollte in known_buildings.py stehen?

---

## 4. Schwaechen-Tabelle

| Kategorie | Problem | Auswirkung | Prioritaet |
|-----------|---------|------------|------------|
| Daten | Traufhoehe 53.2m falsch | Falsche Proportionen in Ansicht | P1 |
| Prompt | Ehrenhof nicht beschrieben | Fehlt im Grundriss | P1 |
| ... | ... | ... | ... |

---

## 5. Konkrete Verbesserungen

### Fuer known_buildings.py:
```python
"2242547": {
    # Bestehende Felder...

    # NEUE Felder (basierend auf deiner Analyse):
    "grundriss_form": "U-foermig",
    "ehrenhof": {
        "position": "sued",
        "breite_m": 30,
        "tiefe_m": 20,
        "offen_nach": "sued",
    },
    "fluegel": [
        {"name": "Westfluegel", "laenge_m": 40, "geschosse": 4},
        {"name": "Ostfluegel", "laenge_m": 40, "geschosse": 4},
        {"name": "Mittelbau", "laenge_m": 50, "geschosse": 4, "hat_kuppel": True},
    ],
    "arkaden": {
        "anzahl_boegen": 7,
        "seite": "nord",
        "hoehe_m": 6,
    },
    # ...
}
```

### Fuer Prompt-Erweiterung:
```markdown
## NEUER ABSCHNITT: Architektonische Struktur

### Grundrissform
- U-foermiger Grundriss mit Ehrenhof nach Sueden

### Ehrenhof
- Position: Suedseite, offen zum Bundesplatz
- Breite: ~30m
- Tiefe: ~20m
- NICHT eingeruesten (Freiflaeche)

### Fluegel
- Westfluegel: 40m Laenge, 4 Geschosse
- Ostfluegel: 40m Laenge, 4 Geschosse
- Mittelbau mit Kuppel: 50m Laenge

### Arkaden
- Nordfassade: 7 Rundbogen
- Hoehe: 6m
- Charakteristisch fuer Neorenaissance

### Kuppel
- Ueber dem Nationalratssaal (Mittelbau)
- Durchmesser: ~15m
- Hoehe ueber Traufe: ~35m
- Kupferverkleidung (gruenlich patiniert)
```

---

## 6. Fazit

Beantworte abschliessend:

1. **Ist der aktuelle Prompt ausreichend fuer gute SVGs?**
   - Ja/Nein, weil...

2. **Was sind die 3 wichtigsten Verbesserungen?**
   - 1. ...
   - 2. ...
   - 3. ...

3. **Kann die App jemals so gute SVGs wie Claude.ai Chat produzieren?**
   - Ja/Nein, weil...
   - Was waere noetig?

---

*Generiert: 30.12.2025*
*App: Geruestplanung Schweiz v3.0*
*API: https://acceptable-trust-production.up.railway.app*
