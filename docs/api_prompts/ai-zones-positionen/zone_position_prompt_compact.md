## RÄUMLICHE ZONE-POSITION (PFLICHTFELD)

Jede Zone in `suggested_zones` MUSS ein `position`-Feld enthalten, das die räumliche Anordnung relativ zum Hauptbaukörper beschreibt.

### Erlaubte Werte:

| position | Bedeutung | Beispiele |
|----------|-----------|-----------|
| `zentral` | Hauptbaukörper, Zentrum des Gebäudes | Kirchenschiff, Hauptgebäude, zentrale Kuppel |
| `links` | Links vom Zentrum (Betrachtersicht Hauptfassade) | Linker Turm, linker Flügel, linker Anbau |
| `rechts` | Rechts vom Zentrum (Betrachtersicht Hauptfassade) | Rechter Turm, rechter Flügel, rechter Anbau |
| `flankierend` | Symmetrisch beidseitig (PAAR!) | Doppeltürme, Seitenschiffe, Seitenflügel |
| `umlaufend` | Umgibt das Zentrum ringförmig | Arkaden, Kreuzgang, umlaufende Galerie |
| `hinten` | Hinter dem Hauptbaukörper | Chor, Apsis, Hintergebäude |
| `vorne` | Vor dem Hauptbaukörper | Vorhalle, Portikus, Narthex |

### Regeln:
1. **Mindestens eine Zone = `zentral`** (der Hauptbaukörper)
2. **`flankierend` NUR bei symmetrischen Paaren** (2 Türme, 2 Flügel)
3. **Betrachtersicht = Hauptfassade** (Eingangsseite, bei Kirchen meist West)

### Beispiel Kirche mit Doppeltürmen:
```json
{
  "suggested_zones": [
    {"name": "Kirchenschiff", "type": "hauptgebaeude", "height_m": 22, "scaffolding": true, "position": "zentral"},
    {"name": "Doppeltürme", "type": "turm", "height_m": 60, "scaffolding": false, "position": "flankierend"},
    {"name": "Seitenschiffe", "type": "anbau", "height_m": 12, "scaffolding": true, "position": "flankierend"},
    {"name": "Chor", "type": "anbau", "height_m": 18, "scaffolding": true, "position": "hinten"}
  ]
}
```

### Beispiel asymmetrisches Gebäude:
```json
{
  "suggested_zones": [
    {"name": "Hauptgebäude", "type": "hauptgebaeude", "height_m": 15, "scaffolding": true, "position": "zentral"},
    {"name": "Turm Nord", "type": "turm", "height_m": 35, "scaffolding": false, "position": "links"},
    {"name": "Anbau Süd", "type": "anbau", "height_m": 8, "scaffolding": true, "position": "rechts"}
  ]
}
```
