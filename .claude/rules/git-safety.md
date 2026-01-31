# Git Safety Rules

## ⛔ VERBOTENE BEFEHLE

**Diese Befehle dürfen NIEMALS ausgeführt werden:**

```bash
# VERBOTEN - Löscht alle uncommitted Änderungen!
git reset --hard
git reset --hard HEAD
git reset --hard origin/master
git checkout -- .
git clean -fd

# VERBOTEN - Überschreibt Remote-History!
git push --force
git push -f
```

## ⚠️ WARUM?

Am 29.01.2026 wurde versehentlich ein `git reset --hard` ausgeführt, was **mehrere Tage Arbeit** gelöscht hat:
- Performance-Optimierungen für Tile-Prefetch
- Priorisiertes Laden (Objekt → Nachbarn → Rest)
- SSE-Streaming Verbesserungen

**Die Arbeit war NICHT committed und konnte NICHT wiederhergestellt werden!**

## ✅ ERLAUBTE ALTERNATIVEN

```bash
# Änderungen temporär sichern
git stash
git stash pop

# Einzelne Datei zurücksetzen (mit Bestätigung!)
git checkout -- <specific-file>  # NUR nach User-Bestätigung!

# Soft reset (behält Änderungen)
git reset --soft HEAD~1
```

## 📋 VOR JEDEM DESTRUKTIVEN GIT-BEFEHL

1. **STOPP** - Ist dieser Befehl wirklich nötig?
2. **FRAGEN** - User explizit um Bestätigung bitten
3. **BACKUP** - `git stash` oder manuelles Backup
4. **PRÜFEN** - `git status` zeigen, was verloren geht

## 🚨 BEI UNFALL

Falls versehentlich ausgeführt:
```bash
# Manchmal kann reflog helfen (nur bei committed changes)
git reflog
git reset --hard HEAD@{n}

# Bei uncommitted changes: VERLOREN!
# → User informieren, manuell wiederherstellen
```