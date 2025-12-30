# Claude.ai SVG-Analyse: Kirche St. Peter und Paul

## Auftrag

Du erhältst einen **technischen Prompt** für die SVG-Generierung eines Schweizer Gebäudes.
Deine Aufgabe ist es:

1. **SVGs generieren** - Erstelle 3 SVGs (Grundriss, Ansicht, Schnitt) basierend auf dem Prompt
2. **Analyse durchführen** - Bewerte die Qualität der generierten SVGs
3. **Verbesserungen vorschlagen** - Identifiziere Probleme und schlage Lösungen vor
4. **Download bereitstellen** - Stelle alle Dateien zum Download bereit

---

## Gebäude-Information

- **Adresse:** Rathausgasse 2, 3011 Bern
- **Zeitstempel:** 2025-12-30 19:12

---

## Schritt 1: SVG-Generierung

Lies den Prompt in `prompt.md` und erstelle **3 separate SVG-Dateien**:

1. `grundriss.svg` - Draufsicht mit Gebäudeumriss und Gerüstzone
2. `ansicht.svg` - Fassadenansicht (Elevation) mit Gerüst
3. `schnitt.svg` - Gebäudeschnitt mit Innenräumen

**Wichtige Vorgaben:**
- ViewBox: `0 0 700 480`
- Hintergrund: Weiss (#FFFFFF)
- Gebäude: Schraffur-Pattern
- Gerüst: Blau (#0066CC)
- Keine künstlerische Interpretation!

---

## Schritt 2: Selbst-Analyse

Nach der SVG-Generierung, analysiere deine eigenen Ergebnisse:

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

## Schritt 3: Prompt-Verbesserungen

Basierend auf deiner Analyse, schlage konkrete Verbesserungen für den Prompt vor:

### Format für Verbesserungen

```markdown
### Problem: [Kurze Beschreibung]

**Beobachtung:** Was ist falsch oder fehlt?

**Ursache:** Warum ist das passiert?

**Lösung (Prompt-Änderung):**
```
[Vorgeschlagener neuer Prompt-Abschnitt]
```

**Beispiel-Code (SVG):**
```xml
[Korrigierter SVG-Code]
```
```

---

## Schritt 4: Download-Paket

Erstelle ein ZIP-Archiv mit folgenden Dateien:

```
kirche_st._peter_und_paul_svg_analyse/
├── grundriss.svg          # Generierter Grundriss
├── ansicht.svg            # Generierte Ansicht
├── schnitt.svg            # Generierter Schnitt
├── analyse.md             # Deine Analyse mit Checklisten
├── verbesserungen.md      # Prompt-Verbesserungsvorschläge
└── prompt_original.md     # Der ursprüngliche Prompt
```

---

## Bewertungskriterien

| Kriterium | Gewichtung |
|-----------|------------|
| Technische Korrektheit | 40% |
| Proportionen & Massstab | 25% |
| Style-Konformität | 20% |
| Vollständigkeit | 15% |

---

## Hinweise

1. **Keine Kreativität!** Halte dich strikt an den Prompt
2. **Frage bei Unklarheiten** statt zu raten
3. **Dokumentiere Annahmen** die du triffst
4. **Verwende die exakten Farben** aus dem Style-Guide

---

*Generiert mit Gerüstplanung Schweiz App*
*https://cooperative-commitment-production.up.railway.app*
