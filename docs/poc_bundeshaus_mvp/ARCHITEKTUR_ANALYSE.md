# POC Bundeshaus MVP - Architektur-Analyse

## Kritische Frage

**Soll die App die SVGs generieren, oder soll Claude AI die SVGs direkt erstellen?**

---

## Option A: App generiert SVG (aktueller Ansatz)

```
User → App → Backend holt Daten → svg_generator.py → SVG
```

### Vorteile
- **Deterministisch**: Gleiches Input = gleiches Output
- **Schnell**: <100ms Latenz
- **Keine API-Kosten**: Unbegrenzte SVGs generierbar
- **Offline-fähig**: Nach initialem Datenabruf

### Nachteile
- **Komplex zu programmieren**: Jedes Feature muss codiert werden
- **Keine semantische Verständnis**: Weiss nicht "das ist ein Turm"
- **Schwer skalierbar**: Bundeshaus braucht Speziallogik

### Aufwand für professionelle SVGs
| Feature | Aufwand | Komplexität |
|---------|---------|-------------|
| Ständerpositionen | 2h | Niedrig |
| Verankerungsraster | 2h | Niedrig |
| Zugangsmarkierungen | 1h | Niedrig |
| Höhenzonen-UI | 4h | Mittel |
| **Mehrere Gebäudezonen** | **8h+** | **Hoch** |
| **Semantische Elemente (Kuppel, Turm)** | **Nicht automatisierbar** | **Sehr hoch** |

---

## Option B: Claude AI generiert SVG

```
User → App → Backend holt Daten → Claude API + Kontext → SVG
```

### Vorteile
- **Semantisches Verständnis**: Erkennt Gebäudeteile aus Kontext
- **Flexibel**: Kann Sonderfälle handhaben (Kuppel, Türme)
- **Weniger Code**: Prompt statt 1000 Zeilen Generator
- **Qualität wie Bundeshaus-Beispiele**: Sofort professionell

### Nachteile
- **API-Kosten**: ~$0.03-0.10 pro SVG (Claude Sonnet)
- **Latenz**: 10-30 Sekunden pro SVG
- **Nicht deterministisch**: Kann bei gleichen Daten variieren
- **Online-abhängig**: Braucht Internet

### Kosten-Beispiel
| Nutzung | SVGs/Monat | Kosten |
|---------|------------|--------|
| Entwicklung | 100 | ~$10 |
| Produktiv (klein) | 500 | ~$50 |
| Produktiv (gross) | 5000 | ~$500 |

---

## Option C: Hybrid (Empfehlung)

```
Einfache Gebäude → App-Generator (schnell, kostenlos)
Komplexe Gebäude → Claude API (professionell, kostenpflichtig)
```

### Entscheidungslogik
```python
def choose_generator(building_data):
    # Komplexitäts-Indikatoren
    facade_count = len(building_data.sides)
    height_variance = max_height - min_height  # Falls Höhenzonen
    has_special_elements = user_marked_dome or user_marked_tower

    if facade_count <= 6 and not has_special_elements:
        return "app_generator"  # Schnell, kostenlos
    else:
        return "claude_api"  # Professionell
```

---

## POC-Scope: Was testen?

### Minimal Viable POC
1. **Kontext-Prompt erstellen**: JSON mit allen Gebäudedaten
2. **Claude API aufrufen**: Mit SVG-Generierungs-Anweisung
3. **Ergebnis vergleichen**: App-SVG vs. Claude-SVG

### Kontext-Struktur für Claude
```json
{
  "adresse": "Bundesplatz 3, 3011 Bern",
  "gebaeude": {
    "polygon": [[x,y], ...],
    "fassaden": [
      {"id": "F1", "laenge_m": 25.3, "richtung": "Nord", "hoehe_m": 18.0}
    ],
    "hoehe_traufe_m": 18.0,
    "hoehe_first_m": 22.0
  },
  "geruest": {
    "system": "Layher Blitz 70",
    "breitenklasse": "W09",
    "ausgewaehlte_fassaden": ["F1", "F2", "F4"]
  },
  "sonderelemente": [
    {"typ": "kuppel", "position": "mitte", "hoehe_m": 64}
  ]
}
```

### System-Prompt für Claude
```
Du bist ein SVG-Generator für Gerüstpläne.

Generiere technische SVG-Zeichnungen für Gerüstbau basierend auf den Gebäudedaten.

Regeln:
- Massstab automatisch berechnen
- Ständerpositionen alle 2.5-3m (Feldlänge)
- Verankerungen alle 4m horizontal/vertikal
- Schraffur für Gebäude (pattern id="hatch")
- Gerüst blau (pattern id="scaffold-pattern")
- Legende mit allen Elementen
- Nordpfeil und Massstab

Output: Nur SVG-Code, kein Markdown.
```

---

## Empfehlung

**Für den POC:**
1. ✅ Ständer/Verankerungen in App-Generator einbauen (niedrig hängend)
2. ✅ Claude API für komplexe Gebäude testen (Bundeshaus als Beispiel)
3. ⏳ Hybrid-Logik implementieren falls Claude-API funktioniert

**Langfristig:**
- Einfache Gebäude (80%): App-Generator
- Komplexe Gebäude (20%): Claude API mit Kontext

---

## Nächste Schritte

1. [ ] `svg_generator.py` erweitern: Ständer + Verankerungen
2. [ ] Claude API Endpoint erstellen: `/api/v1/visualize/claude-generate`
3. [ ] Kontext-Builder implementieren: Gebäudedaten → JSON
4. [ ] A/B-Vergleich: App-SVG vs. Claude-SVG für Bundeshaus
