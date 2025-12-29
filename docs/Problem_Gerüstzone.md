# Problem: Gerüstzone und Fassadenauswahl

**Status:** Gelöst - siehe [Plan_Intelligente_Architektur.md](./Plan_Intelligente_Architektur.md)

---

## Ursprüngliches Problem

Der Prompt lieferte nur Fassaden-Segmente (Länge + Richtung), aber keine Koordinaten.
Claude musste das Polygon selbst "zusammenbauen" - dabei entstanden Fehler bei komplexen Formen.

## Lösung

**Die Koordinaten sind bereits verfügbar!** geodienste.ch liefert echte LV95-Koordinaten.

---

## Neuer Workflow (Zusammenfassung)

### Phase 1: Grunddaten
1. **Smarte Suche**: "Bundeshaus" → Alias auflösen → EGID finden
2. **Cache prüfen**: Gebäude-Daten + SVGs bereits vorhanden? → Laden statt Claude-API
3. **Grundriss-SVG**: Für Fassadenauswahl anzeigen

### Phase 2: Fassadenauswahl
1. **Umgebung laden**: Angrenzende Gebäude via geodienste.ch WFS
2. **Blockierte Fassaden**: Automatisch erkennen (Abstand < 2m)
3. **Rundungen**: Erkennen und markieren (z.B. Bundeshaus Nordfassade)
4. **User-Auswahl**: Klick auf freie Fassaden

### Phase 3: Detailplanung
1. **Terrain-Daten**: Hanglage aus swissALTI3D
2. **Gefälle pro Fassade**: Für unterschiedliche Gerüsthöhen
3. **Spezialelemente**: Treppengerüst, Lift, Kamin, Solar

---

## Polygon-Koordinaten im Prompt

### Option A: Koordinaten-Tabelle (für einfache Polygone ≤15 Punkte)

```markdown
## Polygon-Koordinaten (relativ zu Punkt 0)

| Punkt | X (m) | Y (m) |
|-------|-------|-------|
| 0 | 0.00 | 0.00 |
| 1 | 12.50 | 0.00 |
| 2 | 12.50 | 8.30 |
| 3 | 0.00 | 8.30 |
```

### Option B: Vereinfachte Anweisung (für komplexe Polygone >15 Punkte)

```markdown
## Grundriss-Anweisung

> **WICHTIG:** Dieses Gebäude hat {n} Polygon-Punkte.
>
> 1. Verwende die **Bounding-Box** als Grundform: {width_m} × {depth_m} m
> 2. Gebäudetyp: {building_type}
> 3. Spezialform: {special_form} (z.B. "Rundung an Nordfassade")
```

---

## Datenhaltung

### Was wird gespeichert (SQLite)

| Tabelle | Inhalt | TTL |
|---------|--------|-----|
| `buildings` | Stammdaten + Alias/Keywords | Permanent |
| `building_contexts` | Zonen, Höhen (Claude-Analyse) | Permanent |
| `svg_cache` | Generierte SVGs | Permanent* |
| `building_environment` | Umgebung, blockierte Fassaden | 24h |

*SVGs werden bei Version-Upgrade invalidiert

### Smarte Suche

```
Eingabe: "Bundeshaus"
   │
   ├─> 1. Alias-Match in DB?
   │      └─> JA: EGID 2242547 gefunden
   │
   ├─> 2. FTS-Volltext-Suche
   │
   └─> 3. Fallback: Geocoding
```

---

## Verbesserte SVG-Prompts

Siehe: **[Verbessertes_Prompt_Schnitt_Ansicht.md](./Verbessertes_Prompt_Schnitt_Ansicht.md)**

### Wichtige Erkenntnisse

1. **RECHERCHE-ANWEISUNG**: Claude soll bekannte Gebäude zuerst recherchieren
2. **Fassade vs. Schnitt unterscheiden**:
   - Fassade: Aussenfläche, lockere Schraffur `url(#hatch)`
   - Schnitt: Schnittfläche dicht `url(#cut-hatch)`, Innenräume LEER
3. **Verdeckung**: Vorne verdeckt hinten (Turm vor Hauptschiff)
4. **Gerüstzone**: Rechteckige Hülle, KEINE Stufen

---

## Nächste Schritte

Siehe vollständigen Plan: **[Plan_Intelligente_Architektur.md](./Plan_Intelligente_Architektur.md)**

### Phase 1: Datenbank (Priorität: Hoch)
1. Neue Tabellen: `buildings`, `svg_cache`, `building_environment`
2. Search-Service + FTS5 Volltext-Suche
3. SVG-Cache-Service (persistent)

### Phase 2: Umgebung (Priorität: Hoch)
4. Environment-Service (Nachbargebäude)
5. Blockierte Fassaden erkennen

### Phase 3: Terrain/Rundung (Priorität: Mittel)
6. Terrain-Service (Hanglage pro Fassade)
7. Rundungserkennung (Bézier-Kurven)

### Phase 4: SVG-Prompts (Priorität: Mittel)
8. Zwei Schraffur-Typen implementieren
9. RECHERCHE-ANWEISUNG für komplexe Gebäude

### Phase 5: Frontend (Priorität: Niedrig)
10. Autocomplete-Suche
11. Interaktive Fassadenauswahl
