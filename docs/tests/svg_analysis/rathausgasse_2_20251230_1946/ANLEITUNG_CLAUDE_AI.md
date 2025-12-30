# SVG-Analyse Auftrag: Kirche St. Peter und Paul

> **WICHTIG: Lies diese Anleitung KOMPLETT bevor du beginnst!**

---

## PHASE 1: EIGENE SVGs GENERIEREN (ZUERST!)

**STOPP! Schau dir die API-SVGs noch NICHT an!**

Lies NUR den Prompt (prompt.md) und generiere daraus **3 vollständige SVG-Dateien**:

### 1.1 Grundriss erstellen

Erstelle `grundriss_claude.svg`:
- ViewBox: `0 0 700 480`
- Zeige: Gebäudeumriss von oben, Gerüstzone, Nordpfeil, Massstab
- Schraffur für Mauern: url(#hatch)

**Gib mir den VOLLSTÄNDIGEN SVG-Code für den Grundriss.**

### 1.2 Ansicht erstellen

Erstelle `ansicht_claude.svg`:
- ViewBox: `0 0 700 480`
- Zeige: Fassade frontal, alle Zonen, Gerüst davor, Höhenskala links
- Hintergrund: Weiss (#FFFFFF)
- Gerüst: Blau (#0066CC)

**Gib mir den VOLLSTÄNDIGEN SVG-Code für die Ansicht.**

### 1.3 Schnitt erstellen

Erstelle `schnitt_claude.svg`:
- ViewBox: `0 0 700 480`
- Zeige: Gebäude aufgeschnitten, Innenräume LEER, Schnittflächen schraffiert
- Geschossdecken als horizontale Linien

**Gib mir den VOLLSTÄNDIGEN SVG-Code für den Schnitt.**

---

## PHASE 2: VERGLEICH MIT API-SVGs

**Jetzt darfst du die API-SVGs anschauen!**

Vergleiche deine 3 SVGs mit den 3 API-SVGs und fülle diese Tabelle aus:

| Aspekt | API-SVG | Dein SVG | Besser |
|--------|---------|----------|--------|
| **GRUNDRISS** | | | |
| Gebäudeform korrekt? | ja/nein | ja/nein | API/Claude/gleich |
| Proportionen? | | | |
| Beschriftungen? | | | |
| Nordpfeil? | | | |
| **ANSICHT** | | | |
| Zonen erkennbar? | | | |
| Höhen korrekt? | | | |
| Gerüst-Position? | | | |
| Höhenskala? | | | |
| **SCHNITT** | | | |
| Innenräume leer? | | | |
| Schnittflächen schraffiert? | | | |
| Geschossdecken? | | | |

---

## PHASE 3: ANALYSE & VERBESSERUNGEN

Für JEDEN Unterschied, dokumentiere:

```
### Problem: [Name]
- Was ist falsch: [Beschreibung]
- Ursache im Prompt: [Was fehlt oder ist unklar]
- Lösung: [Konkreter Prompt-Text der hinzugefügt werden sollte]
- SVG-Beispiel: [Code-Snippet]
```

---

## PHASE 4: DATEIEN ZUM DOWNLOAD ANBIETEN

**PFLICHT: Biete JEDE Datei einzeln zum Download an!**

Folgende Dateien müssen erstellt und zum Download angeboten werden:

1. `grundriss_claude.svg` - Dein generierter Grundriss
2. `ansicht_claude.svg` - Deine generierte Ansicht
3. `schnitt_claude.svg` - Dein generierter Schnitt
4. `vergleich.md` - Deine ausgefüllte Vergleichstabelle
5. `verbesserungen.md` - Deine Prompt-Verbesserungsvorschläge
6. `zusammenfassung.md` - Kurze Zusammenfassung der Analyse

---

## Gebäude-Daten

- **Adresse:** Rathausgasse 2, 3011 Bern
- **Gebäude:** Kirche St. Peter und Paul
- **Datum:** 2025-12-30 19:47

---

## Checkliste vor Abschluss

- [ ] 3 eigene SVGs generiert (grundriss, ansicht, schnitt)
- [ ] Vergleichstabelle ausgefüllt
- [ ] Mindestens 3 Verbesserungsvorschläge dokumentiert
- [ ] Alle 6 Dateien zum Download angeboten

---

**START JETZT MIT PHASE 1!**
