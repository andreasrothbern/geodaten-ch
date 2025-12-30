# Formatting Rules

## Sprache & Encoding

| Aspekt | Regel | Beispiel |
|--------|-------|----------|
| **Umlaute** | äöü verwenden | Höhe, Gebäude, Zürich |
| **NICHT** | ae/oe/ue vermeiden | ~~Hoehe~~, ~~Gebaeude~~ |
| **Encoding** | UTF-8 für alle Dateien | - |
| **Zeilenenden** | LF (Unix-Style) | - |

## Sonderzeichen (erlaubt)

- Pfeile: →, ←, ↑, ↓
- Status: ✅, ❌, ⚠️, 🔴, 🟡, 🟢
- Mathematik: ±, ×, ÷, ≈, ≤, ≥
- Schweiz-spezifisch: m ü.M., CHF

## Dokumentation

- **Sprache:** Deutsch
- **Markdown:** GitHub-Flavored
- **Tabellen:** Pipe-Syntax mit Alignment
- **Code-Blöcke:** Mit Sprach-Tag (```python, ```typescript)

## Code

| Sprache | Style | Variablen |
|---------|-------|-----------|
| Python | PEP 8 | snake_case |
| TypeScript | ESLint + Prettier | camelCase |
| SQL | UPPERCASE Keywords | snake_case |

## Kommentare

- **Code-Kommentare:** Englisch (internationale Lesbarkeit)
- **Docstrings:** Deutsch oder Englisch (konsistent pro Datei)
- **TODO/FIXME:** Englisch mit Datum

```python
# Good: Calculate building height from floors
# Bad: Berechne Gebäudehöhe aus Geschossen

def calculate_height(floors: int) -> float:
    """Berechnet die Gebäudehöhe aus der Geschosszahl."""
    return floors * 3.2
```

## Git Commits

- **Format:** `type(scope): description`
- **Types:** feat, fix, chore, docs, refactor, test
- **Sprache:** Englisch
- **Beispiele:**
  - `feat(smart-building): add height validation`
  - `fix(known-buildings): correct Einsteinhaus zone height`
  - `docs(claude): add formatting rules`

## Dateinamen

| Typ | Format | Beispiel |
|-----|--------|----------|
| Python | snake_case | `smart_building.py` |
| TypeScript | camelCase oder kebab | `BuildingCard.tsx` |
| Markdown | UPPERCASE oder kebab | `README.md`, `smart-building.md` |
| Config | lowercase | `.env`, `package.json` |
