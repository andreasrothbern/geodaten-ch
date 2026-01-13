# Formatierung & Sprache

## Umlaute & Sonderzeichen

**WICHTIG:** Immer echte Umlaute verwenden!

| Richtig | Falsch |
|---------|--------|
| äöü | ae/oe/ue |
| ÄÖÜ | Ae/Oe/Ue |
| ß | ss |

**Erlaubte Sonderzeichen:**
- Pfeile: →, ←, ↑, ↓
- Symbole: ✅, ❌, ⚠️, ±
- Klammern: (), [], {}

## Encoding

| Einstellung | Wert |
|-------------|------|
| Datei-Encoding | UTF-8 |
| Zeilenenden | LF (Unix-Style) |
| BOM | Nein |

## Sprache

| Kontext | Sprache |
|---------|---------|
| Dokumentation | Deutsch |
| Code-Kommentare | Englisch |
| Commit-Messages | Englisch |
| Variablen/Funktionen | Englisch |

## Markdown

- **Standard:** GitHub-Flavored Markdown
- **Diagramme:** ASCII-Art oder Mermaid
- **Tabellen:** Pipe-Syntax mit Alignment
- **Code:** Fenced Code Blocks mit Sprache

## Code-Stil

### Python
- PEP 8 Konvention
- Type Hints für alle Funktionen
- Docstrings für öffentliche APIs
- Variablen: `snake_case`

### TypeScript
- ESLint + Prettier Konfiguration
- Variablen: `camelCase`
- Komponenten: `PascalCase`
- Interfaces: `PascalCase` mit `I`-Prefix optional

## Änderungs-Dokumentation (WICHTIG!)

Bei **ALLEN** Änderungen (Code, Dokumentation, Konfiguration) **IMMER Datum UND Uhrzeit** angeben!

### Format

```
DD.MM.YYYY HH:MM
```

**Beispiele:**
- `NEU 13.01.2026 14:30:` DuckDB-Migration
- `FIX 12.01.2026 03:15:` Point-in-Polygon Check
- `Stand 13.01.2026 15:45` (in Überschriften)

### In Code-Kommentaren

**Format:** `TAG DD.MM.YYYY HH:MM - Kurzbeschreibung`

**Tags:**
- `FIX` - Bugfix
- `NEU` - Neues Feature
- `TODO` - Noch zu erledigen
- `WICHTIG` - Kritische Stelle

```python
# FIX 10.01.2026 18:30 - Math.max(5, radius) für blocked-facades
const effectiveRadius = Math.max(5, neighborsRadius);

# NEU 05.01.2026 14:15 - Zonen-Daten für komplexe Gebäude
zones?: BuildingZone[];
```

### In Dokumentation (Markdown)

**Format:** `**NEU DD.MM.YYYY HH:MM:**` oder `(Stand DD.MM.YYYY HH:MM)`

```markdown
## Übersicht (Stand 13.01.2026 14:30)

**NEU 13.01.2026 14:30:** Das Backend MUSS mit `USE_DUCKDB=true` gestartet werden!

> **Änderung 12.01.2026 03:15:** Point-in-Polygon Check implementiert.
```

### Warum Uhrzeit?

- Bei mehreren Änderungen am gleichen Tag ist die **Reihenfolge erkennbar**
- Erleichtert Debugging und Code-Review
- Korreliert mit Git-Commits (`git log --format="%h %ci %s"`)
- Zeigt **wie aktuell** eine Information ist

---

## Commits

**Format:** `type(scope): description`

**Types:**
- `feat` - Neue Features
- `fix` - Bugfixes
- `docs` - Dokumentation
- `refactor` - Refactoring
- `test` - Tests
- `chore` - Wartung

**Beispiele:**
```
feat(smart-building): add height validation
fix(svg): correct zone colors
docs: update CLAUDE.md formatting rules
```
