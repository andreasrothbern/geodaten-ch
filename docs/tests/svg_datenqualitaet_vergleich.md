# Datenqualitäts-Vergleich: SVG-Prompts vs. API-Daten

## Übersicht

Diese Analyse vergleicht die Daten, die für die SVG-Generierung verwendet werden (Prompts), mit den tatsächlichen API-Daten aus `building_comparison_results.json`.

**Zentrale Frage:** Sind die Daten im Prompt ausreichend und korrekt für qualitativ hochwertige SVGs?

---

## 1. Höhendaten-Konsistenz

### Problem: Traufhöhe vs. Zonenhöhen

| Gebäude | API Traufe | API First | Max. Zone | Konsistent? |
|---------|------------|-----------|-----------|-------------|
| Bundeshaus | 53.2m | 62.6m | 64.0m | ⚠️ Zone > First |
| St. Peter und Paul | 46.4m | 54.6m | 54.6m | ✅ |
| Berner Münster | 25.7m | 30.3m | 100.3m | ✅ Turm separat |
| Einsteinhaus | 22.3m | 26.2m | 16.0m | ❌ Zone < Traufe! |
| Hotel Schweizerhof | 23.1m | 27.2m | 30.0m | ⚠️ Zone > First |
| Hauptbahnhof | 31.3m | 36.8m | 40.0m | ⚠️ Zone > First |
| Kornhaus | 22.3m | 26.2m | 32.0m | ⚠️ Zone > First |
| Konzert Theater | 15.1m | 17.7m | 32.0m | ⚠️ Zone > First |
| Kunstmuseum | 6.7m | 7.9m | 18.0m | ❌ Massive Differenz! |
| Hist. Museum | 44.0m | 51.8m | 50.0m | ✅ |

### Analyse

**Problem 1: swissBUILDINGS3D misst nur EINEN Höhenwert**
- Die API-Traufhöhe ist oft die Hauptgebäude-Traufe
- Türme, Kuppeln, Dachreiter werden nicht separat gemessen
- Die Zonenhöhen in `known_buildings.py` sind manuell und oft HÖHER als API-First

**Problem 2: Einsteinhaus - Zone niedriger als API**
```
API:   Traufe 22.3m, First 26.2m
Zone:  Hauptgebäude 12.0m - 16.0m (!)
```
→ Die manuelle Zone ist FALSCH oder bezieht sich auf etwas anderes

**Problem 3: Kunstmuseum - Massive Differenz**
```
API:   Traufe 6.7m, First 7.9m (nur ein Gebäudeteil!)
Zonen: Altbau 15-18m, Neubau 12-15m, Erweiterung 8-10m
```
→ Die API misst nur einen kleinen Teil, die Zonen sind realistischer

### Auswirkung auf SVG-Qualität

| Szenario | SVG-Qualität |
|----------|--------------|
| API-Höhe = Zone-Höhe | ✅ Korrekte Proportionen |
| API-Höhe < Zone-Höhe | ⚠️ Zonen-Höhen realistischer, aber inkonsistent |
| API-Höhe > Zone-Höhe | ❌ Fehlerhafte Zonen-Definition |

---

## 2. Zonen-Analyse pro Gebäude

### Bundeshaus ✅

| Aspekt | API-Daten | Prompt-Zonen | SVG-Qualität |
|--------|-----------|--------------|--------------|
| Arkaden | - | 6.0m | ✅ Korrekt |
| Hauptgebäude | Traufe 53.2m | 25-30m | ⚠️ Manuell korrigiert |
| Kuppel | First 62.6m | 30-64m | ✅ Korrekt |

**Bewertung:** Die manuellen Zonen sind BESSER als die API-Daten, da sie die Architektur korrekt abbilden.

### St. Peter und Paul ✅

| Aspekt | API-Daten | Prompt-Zonen | SVG-Qualität |
|--------|-----------|--------------|--------------|
| Kirchenschiff | - | 18-25m | ✅ Realistisch |
| Seitenschiffe | - | 9-12m | ✅ Niedriger als Hauptschiff |
| Chor | - | 12-18m | ✅ Zwischen Seiten und Haupt |
| Westturm | First 54.6m | 25-54.6m | ✅ Korrekt |

**Bewertung:** 4 Zonen perfekt differenziert!

### Berner Münster ✅

| Aspekt | API-Daten | Prompt-Zonen | SVG-Qualität |
|--------|-----------|--------------|--------------|
| Kirchenschiff | Traufe 25.7m | 22-28m | ✅ Passt |
| Seitenkapellen | - | 12-15m | ✅ Niedriger |
| Turm | - | 28-100.3m | ✅ Höchster CH-Kirchturm! |

**Bewertung:** Turm korrekt als 100.3m erfasst - exzellent!

### Einsteinhaus ⚠️

| Aspekt | API-Daten | Prompt-Zonen | SVG-Qualität |
|--------|-----------|--------------|--------------|
| Hauptgebäude | 22.3-26.2m | 12-16m | ❌ Zone zu niedrig! |

**Problem:** Die Zone (16m) ist niedriger als die API-Traufhöhe (22.3m)!

**Empfehlung:** Zone korrigieren auf:
```python
"zones": [{"name": "Hauptgebäude", "traufe": 22.0, "first": 26.0}]
```

### Hotel Schweizerhof ✅

| Aspekt | API-Daten | Prompt-Zonen | SVG-Qualität |
|--------|-----------|--------------|--------------|
| Hauptgebäude | 23.1m | 18-25m | ✅ OK |
| Dachaufbau | - | 25-30m | ✅ Mansarddach |

**Bewertung:** Zonen plausibel für Historismus-Hotel

### Hauptbahnhof ✅

| Aspekt | API-Daten | Prompt-Zonen | SVG-Qualität |
|--------|-----------|--------------|--------------|
| Baldachin | - | 8-12m | ✅ Niedriges Vordach |
| Bahnhofshalle | 31.3m | 18-22m | ⚠️ Zone niedriger |
| Büroturm | - | 30-40m | ✅ Höher als API-First |

**Bewertung:** Zonen architektonisch sinnvoll

### Kornhaus ✅

| Aspekt | API-Daten | Prompt-Zonen | SVG-Qualität |
|--------|-----------|--------------|--------------|
| Arkaden | - | 5m | ✅ Barock-Arkaden |
| Hauptbau | 22.3m | 18-25m | ✅ Passt |
| Dachreiter | - | 25-32m | ✅ Über First |

**Bewertung:** Barockes Kornhaus korrekt erfasst

### Konzert Theater ⚠️

| Aspekt | API-Daten | Prompt-Zonen | SVG-Qualität |
|--------|-----------|--------------|--------------|
| Foyer | - | 10-12m | ✅ Niedriger Eingangsbereich |
| Zuschauerhaus | 15.1m | 18-22m | ⚠️ Zone höher als API |
| Bühnenturm | - | 22-32m | ✅ Typisch für Theater |

**Problem:** API-Traufhöhe (15.1m) vs. Zuschauerhaus (18-22m)
→ API misst vermutlich nur einen Teil

### Kunstmuseum ⚠️

| Aspekt | API-Daten | Prompt-Zonen | SVG-Qualität |
|--------|-----------|--------------|--------------|
| API-Höhe | 6.7-7.9m | - | ❌ Viel zu niedrig! |
| Altbau | - | 15-18m | ✅ Realistisch |
| Neubau (Stettler) | - | 12-15m | ✅ Realistisch |
| Erweiterung | - | 8-10m | ✅ Niedriger |

**Kritisches Problem:** Die API-Höhe (7.9m) ist FALSCH!
→ Vermutlich nur ein Nebengebäude oder Eingang gemessen
→ Die manuellen Zonen sind korrekt

### Historisches Museum ✅

| Aspekt | API-Daten | Prompt-Zonen | SVG-Qualität |
|--------|-----------|--------------|--------------|
| Hauptbau | 44.0m | 25-35m | ⚠️ Zone niedriger |
| Seitenflügel | - | 18-25m | ✅ Niedriger |
| Eckturm | - | 35-50m | ✅ Höher als Hauptbau |

**Bewertung:** Schlossartiges Gebäude gut erfasst

---

## 3. Fehlende Daten für SVG-Generierung

### Was im Prompt FEHLT, aber für gute SVGs nötig wäre:

| Fehlendes Element | Auswirkung | Priorität |
|-------------------|------------|-----------|
| **Grundrissform** (U, L, H, rechteckig) | Falsche Gebäudesilhouette | 🔴 Hoch |
| **Ehrenhof/Innenhof** Position | Fehlt im Grundriss | 🔴 Hoch |
| **Flügel-Differenzierung** | Keine West/Ost-Unterscheidung | 🟡 Mittel |
| **Arkaden-Anzahl** | Generische Darstellung | 🟢 Niedrig |
| **Fensterachsen** | Ungenaue Fassade | 🟢 Niedrig |
| **Geschosshöhen** | Ungenaue Schnitte | 🟡 Mittel |

### Was im Prompt VORHANDEN und KORREKT ist:

| Element | Status | Qualität |
|---------|--------|----------|
| Gebäudename | ✅ 10/10 | Perfekt |
| Baustil | ✅ 10/10 | Perfekt |
| Baujahr | ✅ 10/10 | Perfekt |
| Zonen-Typen | ✅ 10/10 | Perfekt |
| Zonen-Höhen | ⚠️ 8/10 | Meist korrekt |
| Polygon | ✅ 10/10 | Vorhanden |
| Terrain | ✅ 10/10 | Perfekt |
| Gerüst-Zugänge | ✅ 10/10 | SUVA-konform |

---

## 4. SVG-Qualitätsprognose pro Gebäude

| Gebäude | Daten-Qualität | Erwartete SVG-Qualität | Hauptproblem |
|---------|----------------|------------------------|--------------|
| Bundeshaus | 85% | ⭐⭐⭐⭐ | U-Form fehlt |
| St. Peter und Paul | 95% | ⭐⭐⭐⭐⭐ | - |
| Berner Münster | 95% | ⭐⭐⭐⭐⭐ | - |
| Einsteinhaus | 70% | ⭐⭐⭐ | Zone-Höhe falsch |
| Hotel Schweizerhof | 85% | ⭐⭐⭐⭐ | - |
| Hauptbahnhof | 80% | ⭐⭐⭐⭐ | Komplexe Struktur |
| Kornhaus | 90% | ⭐⭐⭐⭐⭐ | - |
| Konzert Theater | 80% | ⭐⭐⭐⭐ | API-Höhe fraglich |
| Kunstmuseum | 75% | ⭐⭐⭐ | API-Höhe FALSCH |
| Hist. Museum | 85% | ⭐⭐⭐⭐ | - |

---

## 5. Konkrete Datenprobleme

### Problem 1: Einsteinhaus Zone-Höhe

```python
# AKTUELL (FALSCH):
"zones": [{"name": "Hauptgebäude", "traufe": 12.0, "first": 16.0}]

# KORREKT:
"zones": [{"name": "Hauptgebäude", "traufe": 22.0, "first": 26.0}]
```

### Problem 2: Kunstmuseum API-Höhe

```
API liefert:     Traufe 6.7m, First 7.9m
Realität:        Altbau ~18m, Neubau ~15m

Ursache: API misst falsches Gebäude oder nur einen Teil
Lösung:  Manuellen Override in known_buildings.py
```

### Problem 3: Inkonsistenz Zone > API-First

Bei 5 Gebäuden ist die maximale Zonenhöhe HÖHER als der API-First:
- Bundeshaus: Zone 64m > First 62.6m
- Hotel Schweizerhof: Zone 30m > First 27.2m
- Hauptbahnhof: Zone 40m > First 36.8m
- Kornhaus: Zone 32m > First 26.2m
- Konzert Theater: Zone 32m > First 17.7m

**Interpretation:** Die manuellen Zonen sind oft KORREKTER als die API-Daten, da sie architektonisches Wissen einbeziehen (Türme, Dachreiter, etc.).

---

## 6. Empfehlungen

### Sofort umsetzen (P1)

| # | Massnahme | Aufwand |
|---|-----------|---------|
| 1 | Einsteinhaus Zone-Höhe korrigieren | 5 Min |
| 2 | Kunstmuseum: API-Höhe als "unreliable" markieren | 10 Min |

### Mittelfristig (P2)

| # | Massnahme | Aufwand |
|---|-----------|---------|
| 3 | Grundrissform zu known_buildings hinzufügen | 2 Std |
| 4 | Ehrenhof-Daten für Bundeshaus | 30 Min |
| 5 | Höhen-Validierung: Zone vs. API | 4 Std |

### Langfristig (P3)

| # | Massnahme | Aufwand |
|---|-----------|---------|
| 6 | Automatische Höhen-Plausibilitätsprüfung | 1 Tag |
| 7 | Polygon-Analyse für Grundrissform | 2 Tage |

---

## 7. Fazit

### Stärken ✅

1. **Zonen-Erkennung funktioniert** - Alle 10 Gebäude haben sinnvolle Zonen
2. **Architektonisches Wissen** - Manuell besser als automatisch
3. **Performance** - 299ms Durchschnitt ist exzellent
4. **100% Erkennungsrate** - Alle Namen korrekt

### Schwächen ⚠️

1. **API-Höhen unzuverlässig** - swissBUILDINGS3D misst nur Hauptgebäude
2. **Keine Grundrissform** - U-Form, L-Form etc. fehlt
3. **Inkonsistenz Zone/API** - 5 von 10 Gebäuden haben Zone > API-First
4. **Einsteinhaus** - Zone-Höhe definitiv falsch

### Gesamtbewertung

```
┌────────────────────────────────────────────────────────┐
│  DATENQUALITÄT FÜR SVG-GENERIERUNG                    │
│                                                        │
│  Gebäude-Identifikation:  ██████████████████████ 100% │
│  Zonen-Typen:             ██████████████████████ 100% │
│  Zonen-Höhen:             ████████████████░░░░░░  80% │
│  Architektur-Details:     ████████████░░░░░░░░░░  60% │
│                                                        │
│  GESAMT:                  ████████████████░░░░░░  85% │
│                                                        │
│  ✅ GUT FÜR GERÜSTPLANUNG                             │
│  ⚠️ VERBESSERUNGSPOTENTIAL BEI DETAILS               │
└────────────────────────────────────────────────────────┘
```

---

*Analyse erstellt: 30. Dezember 2025*
*Datenquellen: building_comparison_results.json, building_comparison_prompt.md*
*Für: Gerüstplanung Schweiz App v3.0*
