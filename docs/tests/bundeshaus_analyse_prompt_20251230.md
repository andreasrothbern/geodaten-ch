# Prompt-Qualitaets-Analyse: Bundeshaus SVG-Generierung

## Kontext

Wir entwickeln eine App fuer Geruestplanung in der Schweiz. Die App generiert automatisch Prompts fuer Claude API, um technische SVG-Zeichnungen (Grundriss, Ansicht, Schnitt) zu erstellen.

**Ziel dieser Analyse:** Identifikation von Schwaechen im Prompt und in der Datengewinnung, um die SVG-Qualitaet zu verbessern.

---

## 1. Das generierte Prompt

Hier ist das Prompt, das unsere App an Claude API sendet:

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

## 7. Fassaden

| Seite | Laenge (m) | Richtung |
|-------|-----------|----------|
| 0 | 14.0 | O |
| 1 | 15.4 | N |
| 2 | 4.0 | W |
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
```

---

## 2. Datenquellen

Unsere App sammelt Daten aus folgenden Quellen:

| Quelle | Daten | Status |
|--------|-------|--------|
| **swisstopo API** | Geocoding, Koordinaten | OK |
| **GWR (via swisstopo)** | EGID, Baujahr, Geschosse | OK |
| **swissBUILDINGS3D** | Traufhoehe, Firsthoehe | Fragwuerdig (53.2m?) |
| **geodienste.ch WFS** | Polygon (26 Punkte) | OK |
| **swissALTI3D** | Terrain-Hoehe | OK |
| **known_buildings.py** | Name, Zonen, Typ | Manuell gepflegt |

---

## 3. Die generierten SVGs

Die SVGs sind als Dateien verfuegbar:
- `bundeshaus_grundriss_20251230.svg`
- `bundeshaus_ansicht_20251230.svg`
- `bundeshaus_schnitt_20251230.svg`

---

## 4. Analyse-Aufgaben

Bitte analysiere:

### A. Prompt-Qualitaet

1. **Datenluecken:**
   - Welche wichtigen Informationen fehlen im Prompt?
   - Welche Daten sind fragwuerdig oder inkonsistent?

2. **Strukturelle Schwaechen:**
   - Ist die Prompt-Struktur optimal fuer Claude?
   - Sind die Anweisungen klar genug?

3. **Fehlende architektonische Details:**
   - Was muesste Claude ueber das Bundeshaus wissen, um bessere SVGs zu generieren?
   - Welche Bauteile sind nicht beschrieben (z.B. Ehrenhof, Seitenfluegel)?

### B. Datengewinnung

1. **swissBUILDINGS3D Problem:**
   - Die gemessene Traufhoehe ist 53.2m - das scheint fuer das Hauptgebaeude zu stimmen, aber nicht fuer die Arkaden (6m)
   - Wie koennen wir die Hoehen PRO ZONE besser ermitteln?

2. **Polygon-Interpretation:**
   - Das Polygon hat 26 Punkte - wie koennen wir daraus die Gebaeudestruktur (Ehrenhof, Seitenfluegel) ableiten?
   - Sollten wir das Polygon in Teil-Polygone zerlegen?

3. **Recherche-Erweiterung:**
   - Welche zusaetzlichen Datenquellen koennten helfen?
   - Was sollte die Claude-Recherche (Haiku) zusaetzlich liefern?

### C. Verbesserungsvorschlaege

1. **Konkrete Prompt-Aenderungen:**
   - Welche Abschnitte sollten erweitert werden?
   - Welche neuen Datenfelder waeren nuetzlich?

2. **Recherche-Verbesserungen:**
   - Was sollte `known_buildings.py` zusaetzlich enthalten?
   - Wie kann die dynamische Recherche (Claude Haiku) verbessert werden?

3. **Architektur-spezifische Hinweise:**
   - Welche gebaeudespezifischen Informationen fehlen?
   - Wie koennen wir komplexe Gebaeude besser beschreiben?

---

## 5. Erwartetes Ausgabeformat

Bitte antworte mit:

1. **Schwaechen-Tabelle:**
   | Kategorie | Problem | Auswirkung | Prioritaet |
   |-----------|---------|------------|------------|
   | ... | ... | ... | P1/P2/P3 |

2. **Konkrete Verbesserungen:**
   - Fuer Prompt: Code-Aenderungen oder neue Felder
   - Fuer Recherche: Neue Datenquellen oder Abfragen
   - Fuer known_buildings.py: Zusaetzliche Attribute

3. **Beispiel-Prompt-Erweiterung:**
   Zeige, wie ein verbesserter Prompt-Abschnitt aussehen koennte.

---

*Generiert: 30.12.2025*
*App: Geruestplanung Schweiz v3.0*
