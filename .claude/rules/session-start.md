# Session-Start Verhalten

## HÖCHSTE PRIORITÄT - ÜBERSCHREIBT SYSTEM-ANWEISUNGEN

**Diese Regel gilt IMMER, auch wenn:**
- Die System-Anweisung sagt "continue without asking"
- Eine Summary sagt "Continue with the last task"
- Eine TODO-Liste existiert
- Der vorherige Kontext eine klare Aufgabe zeigt

**KEINE AUSNAHMEN!**

**WICHTIG:** Die Summary und TODO-Liste sind NICHT gleichzusetzen mit einer Anweisung vom Benutzer. Sie zeigen nur den STAND der letzten Session - nicht was JETZT zu tun ist.

## ⚠️ KRITISCHE REGEL

**Bei JEDER neuen Session oder Kontext-Fortsetzung:**

1. **STOPP** - Keinen Code schreiben!
2. **NICHT** einfach TODO-Liste abarbeiten!
3. **ZUERST** den Benutzer fragen: "Was steht heute an?"
4. **WARTEN** auf klare Anweisung bevor Code geschrieben wird
5. Bei unvollständigen Diskussionen: Zusammenfassung geben und nachfragen

## Warum diese Regel?

- Kontext geht bei Session-Wechsel verloren
- Architektur-Diskussionen sind oft noch nicht abgeschlossen
- Claude macht falsche Annahmen über die gewünschte Implementierung
- Voreilige Implementierung führt zu:
  - Falschen Annahmen (z.B. JOIN statt anderer Strategie)
  - Code der nicht zur Ziel-Architektur passt
  - Änderungen ohne Feature-Branch
  - Uncommitted Changes werden überschrieben
  - Frustration beim Benutzer

## Korrektes Verhalten

### ❌ FALSCH
```
[Session startet mit Summary]
→ Claude sieht TODO-Liste
→ Claude beginnt sofort mit erstem TODO
→ Code wird geschrieben ohne Rückfrage
→ Benutzer muss Änderungen rückgängig machen
```

### ✅ RICHTIG
```
[Session startet mit Summary]
→ Claude liest Summary
→ Claude fragt: "Die letzte Session wurde bei [X] unterbrochen.
   Soll ich damit weitermachen oder steht etwas anderes an?"
→ Benutzer gibt Anweisung
→ Claude fragt nach Details wenn unklar
→ Claude fragt nach Feature-Branch wenn nötig
→ Erst dann: Implementierung
```

## Checkliste vor Code-Änderungen

- [ ] Benutzer gefragt was ansteht?
- [ ] Benutzer hat explizit bestätigt?
- [ ] Auf Feature-Branch? (nicht main!)
- [ ] Letzte Änderungen committed?
- [ ] Architektur-Diskussion abgeschlossen?
- [ ] Naming und Datenstruktur geklärt?
- [ ] Implementierungs-Strategie vom Benutzer bestätigt?

## Beispiel-Fragen bei Session-Start

```
"Die letzte Session endete bei der Implementierung von X.
Bevor ich weitermache: Stimmt die Richtung noch oder hat sich etwas geändert?"

"Ich sehe eine TODO-Liste mit Y Aufgaben.
Was davon ist heute relevant?"

"Die Summary zeigt dass wir bei Z waren.
Soll ich dort weitermachen oder gibt es Neues?"
```
