# Claude.ai SVG-Analyse: Kirche St. Peter und Paul

## Auftrag

Du erhältst:
1. Einen **technischen Prompt** für die SVG-Generierung
2. **3 API-generierte SVGs** (grundriss_api.svg, ansicht_api.svg, schnitt_api.svg)

Deine Aufgabe ist es:

1. **Eigene SVGs generieren** - Erstelle 3 SVGs basierend auf dem Prompt
2. **Vergleichen** - Vergleiche deine SVGs mit den API-generierten
3. **Analysieren** - Identifiziere Unterschiede und Probleme
4. **Verbessern** - Schlage konkrete Prompt-Verbesserungen vor
5. **Download bereitstellen** - Stelle alle Dateien zum Download bereit

---

## Gebäude-Information

- **Adresse:** Rathausgasse 2, 3011 Bern
- **Zeitstempel:** 2025-12-30 19:36

---

## Schritt 1: Eigene SVGs generieren

Lies den Prompt in `prompt.md` und erstelle **3 separate SVG-Dateien**:

1. `grundriss_claude.svg` - Draufsicht mit Gebäudeumriss und Gerüstzone
2. `ansicht_claude.svg` - Fassadenansicht (Elevation) mit Gerüst
3. `schnitt_claude.svg` - Gebäudeschnitt mit Innenräumen

**Wichtige Vorgaben:**
- ViewBox: `0 0 700 480`
- Hintergrund: Weiss (#FFFFFF)
- Gebäude: Schraffur-Pattern url(#hatch)
- Gerüst: Blau (#0066CC)
- Keine künstlerische Interpretation!

---

## Schritt 2: Vergleich mit API-SVGs

Vergleiche deine generierten SVGs mit den API-generierten SVGs:

### Vergleichs-Tabelle

| Aspekt | API-SVG | Dein SVG | Bewertung |
|--------|---------|----------|-----------|
| **Grundriss** | | | |
| Gebäudeform | ___ | ___ | besser/gleich/schlechter |
| Proportionen | ___ | ___ | |
| Beschriftungen | ___ | ___ | |
| Gerüst-Zone | ___ | ___ | |
| **Ansicht** | | | |
| Zonen-Darstellung | ___ | ___ | |
| Höhen korrekt | ___ | ___ | |
| Gerüst-Position | ___ | ___ | |
| **Schnitt** | | | |
| Innenräume | ___ | ___ | |
| Schnittflächen | ___ | ___ | |

### Unterschiede dokumentieren

Für jeden signifikanten Unterschied:

```markdown
### Unterschied: [Beschreibung]

**API-SVG:** [Was die API generiert hat]
**Dein SVG:** [Was du generiert hast]
**Besser:** API / Claude.ai / Beide gleich
**Grund:** [Warum einer besser ist]
```

---

## Schritt 3: Selbst-Analyse

### Checkliste Grundriss
- [ ] Gebäudeform korrekt (rechteckig/U-Form/L-Form)?
- [ ] Innenhöfe als Freifläche markiert?
- [ ] Fassaden beschriftet?
- [ ] Nordpfeil vorhanden?
- [ ] Massstab korrekt?

### Checkliste Ansicht
- [ ] Proportionen stimmen (Höhe/Breite)?
- [ ] Zonen erkennbar (unterschiedliche Höhen)?
- [ ] Gerüst VOR der Fassade?
- [ ] Höhenskala links?
- [ ] Terrain-Linie unten?

### Checkliste Schnitt
- [ ] Schnittflächen dicht schraffiert?
- [ ] Innenräume LEER (weiss)?
- [ ] Geschossdecken horizontal?
- [ ] Gerüst links und rechts?

---

## Schritt 4: Prompt-Verbesserungen

Basierend auf dem Vergleich, schlage konkrete Verbesserungen vor:

### Format für Verbesserungen

```markdown
### Problem: [Kurze Beschreibung]

**Beobachtung:** Was ist falsch oder fehlt in beiden SVGs?

**Ursache:** Was fehlt im Prompt?

**Lösung (Prompt-Änderung):**
```
[Vorgeschlagener neuer Prompt-Abschnitt]
```

**Beispiel-Code (SVG):**
```xml
[Korrigierter SVG-Code-Ausschnitt]
```
```

---

## Schritt 5: Download-Paket

Erstelle ein ZIP-Archiv mit folgenden Dateien:

```
kirche_st._peter_und_paul_svg_analyse/
├── grundriss_claude.svg      # Dein generierter Grundriss
├── ansicht_claude.svg        # Deine generierte Ansicht
├── schnitt_claude.svg        # Dein generierter Schnitt
├── grundriss_api.svg         # API-generierter Grundriss (Kopie)
├── ansicht_api.svg           # API-generierte Ansicht (Kopie)
├── schnitt_api.svg           # API-generierter Schnitt (Kopie)
├── vergleich.md              # Deine Vergleichs-Analyse
├── verbesserungen.md         # Prompt-Verbesserungsvorschläge
└── prompt_original.md        # Der ursprüngliche Prompt
```

---

## Bewertungskriterien

| Kriterium | Gewichtung |
|-----------|------------|
| Technische Korrektheit | 30% |
| Vergleichs-Qualität | 25% |
| Prompt-Verbesserungen | 25% |
| Vollständigkeit | 20% |

---

## Hinweise

1. **Generiere ZUERST deine eigenen SVGs** bevor du die API-SVGs anschaust
2. **Dokumentiere alle Unterschiede** - auch kleine Details
3. **Sei kritisch** - auch gegenüber deinen eigenen SVGs
4. **Konkrete Lösungen** - Jede Kritik braucht einen Verbesserungsvorschlag

---

*Generiert mit Gerüstplanung Schweiz App*
*https://cooperative-commitment-production.up.railway.app*
