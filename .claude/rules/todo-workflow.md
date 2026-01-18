# TODO-Workflow Regel

## PFLICHT bei jeder TODO-Liste

Bei JEDER neuen TODO-Liste die erstellt wird, MÜSSEN die ersten fünf Einträge sein:

### 1. Analyse Use Case (IMMER ZUERST!)

- Was ist das Ziel?
- Welche Daten werden benötigt?
- Welche bestehenden Komponenten sind betroffen?
- Welche Abhängigkeiten gibt es?
- Gibt es bereits ähnliche Implementierungen?

### 2. Implementierungsplan erstellen

- Welche Schritte sind nötig?
- In welcher Reihenfolge?
- Welche Dateien werden geändert?

### 3. Schema-Änderungen definieren

- Welche Datenbank-Tabellen betroffen?
- Welche neuen Felder/Tabellen?
- Migration nötig?

### 4. Data-Flow E2E aufzeigen

- Woher kommen die Daten?
- Wie fliessen sie durch das System?
- Wo werden sie gespeichert?
- Wie erreichen sie das Frontend?

### 5. Review und Genehmigung durch Benutzer einholen

**KEINE Implementierung ohne explizite Genehmigung!**

Der Benutzer muss:
- Die Analyse reviewen
- Den Implementierungsplan verstehen
- Die Schema-Änderungen bestätigen
- Den Data-Flow nachvollziehen
- Explizit bestätigen (z.B. "Ja, so machen")

## Beispiel einer korrekten TODO-Liste

```
1. [pending] Analyse Use Case: [Beschreibung]
2. [pending] Implementierungsplan erstellen
3. [pending] Schema-Änderungen definieren
4. [pending] Data-Flow E2E aufzeigen
5. [pending] Review und Genehmigung durch Benutzer einholen
6. [pending] ... weitere Implementierungs-Schritte
```

## VERBOTEN

- Implementierung starten bevor Punkt 1-5 abgeschlossen sind
- TODO-Liste ohne diese 5 Pflicht-Punkte
- Annahmen über Architektur ohne Benutzer-Bestätigung
- Code schreiben vor expliziter Genehmigung
