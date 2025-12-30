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
