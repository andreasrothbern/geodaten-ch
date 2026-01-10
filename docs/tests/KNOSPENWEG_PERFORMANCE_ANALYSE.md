# Performance-Analyse: Knospenweg Multi-Adresse (04.01.2026)

## Zusammenfassung

| Metrik | Ergebnis | Bewertung |
|--------|----------|-----------|
| **Knospenweg 2-10** | 5 Gebäude gefunden | ✅ Korrekt |
| **Knospenweg 1-9** | 5 Gebäude gefunden | ✅ Korrekt |
| **DB-Lookup Zeit** | 0.06-0.5ms pro EGID | ✅ Hervorragend |
| **Koordinaten-Range** | 0.16ms für 9 Gebäude | ✅ Hervorragend |
| **API Response Zeit** | 5-56s | ⚠️ Zu langsam |

## Test-Ergebnisse

### 1. Address Resolution API

**Endpoint:** `GET /api/v1/geruestbau/address/resolve?address=Knospenweg 2-10, Bern`

```json
{
  "parsed": {
    "street": "Knospenweg",
    "city": "Bern",
    "numbers": ["2", "4", "6", "8", "10"]
  },
  "buildings": [
    {"address": "Knospenweg 2", "egid": "1243788"},
    {"address": "Knospenweg 4", "egid": "1243790"},
    {"address": "Knospenweg 6", "egid": "1243792"},
    {"address": "Knospenweg 8", "egid": "1243794"},
    {"address": "Knospenweg 10", "egid": "1243797"}
  ],
  "building_count": 5
}
```

**Response Zeit:** ~5.96s (erster Aufruf)

### 2. DB-Performance (Direkter Zugriff)

Alle 10 Knospenweg-Gebäude sind in `building_3d.db` gespeichert (via tile_prefetch):

| EGID | Adresse | Traufhöhe | Firsthöhe | Polygon | Lookup |
|------|---------|-----------|-----------|---------|--------|
| 1243787 | Knospenweg 1 | 5.49m | 8.24m | 11 Punkte | 0.50ms |
| 1243788 | Knospenweg 2 | 5.53m | 7.57m | 9 Punkte | 0.10ms |
| 1243789 | Knospenweg 3 | 5.48m | 8.24m | 6 Punkte | 0.10ms |
| 1243790 | Knospenweg 4 | 5.58m | 7.62m | 8 Punkte | 0.13ms |
| 1243791 | Knospenweg 5 | 5.50m | 8.26m | 10 Punkte | 0.09ms |
| 1243792 | Knospenweg 6 | 5.54m | 7.58m | 8 Punkte | 0.07ms |
| 1243793 | Knospenweg 7 | 5.51m | 8.27m | 7 Punkte | 0.06ms |
| 1243794 | Knospenweg 8 | 5.69m | 7.73m | 10 Punkte | 0.06ms |
| 1243795 | Knospenweg 9 | 5.49m | 8.26m | 8 Punkte | 0.06ms |
| 1243797 | Knospenweg 10 | 5.74m | 7.78m | 10 Punkte | 0.06ms |

**DB-Gesamtstatistik:**
- Total Gebäude in DB: 92,223
- Koordinaten-Range-Lookup (50m x 40m): 0.16ms für 9 Gebäude

### 3. Performance-Engpässe

Die API-Response-Zeit von 5-56s ist durch externe API-Aufrufe verursacht:

| API | Zweck | Geschätzte Zeit |
|-----|-------|-----------------|
| swisstopo Geocoding | Adresse → Koordinaten | ~1-2s pro Adresse |
| Sonnendach.ch | Dachdaten | ~10-30s |
| GWR/BFS | Gebäudekategorie | ~0.5s |

**Problem:** Für Multi-Adresse werden 5 separate Geocoding-Aufrufe gemacht!

## Empfehlungen

### Kurzfristig

1. **Batch-Geocoding:** Alle Adressen in einem API-Aufruf geocodieren
2. **Sonnendach parallel:** Dachdaten im Hintergrund laden (nicht blockierend)
3. **Response-Caching:** API-Responses für häufige Adressen cachen

### Mittelfristig

1. **EGID in DB mit Adresse verknüpfen:** Adress-Lookup aus lokaler DB statt swisstopo API
2. **Sonnendach-Daten vorberechnen:** Bei erstem Tile-Import auch Sonnendach-Daten laden

### Langfristig

1. **Tile-Prefetching:** Nachbar-Tiles im Hintergrund laden
2. **Adress-Index:** Lokalen Adress-Index aufbauen für schnelle Suche

## Datenintegrität

Das swissBUILDINGS3D Tile für Knospenweg (Bern) enthält alle 10 Gebäude:
- **Tile wurde heruntergeladen:** 1x (beim ersten Aufruf)
- **Tile wird nicht erneut geladen:** ✅ Daten sind in DB persistiert
- **Höhendaten korrekt:** Traufhöhe 5.5-5.7m, Firsthöhe 7.6-8.3m (typisch für Reihenhäuser)

## Test-Kommandos

```bash
# Address Resolution Test
curl "http://localhost:8000/api/v1/geruestbau/address/resolve?address=Knospenweg%202-10,%20Bern"

# Single Building Test
curl "http://localhost:8000/api/v1/geruestbau/configurator/facades?address=Knospenweg%203,%20Bern"

# DB Performance Test (HINWEIS: Tabelle jetzt buildings_3d in building_3d.db)
python -c "
import sqlite3
conn = sqlite3.connect('backend/app/data/building_3d.db')
cursor = conn.cursor()
cursor.execute('SELECT egid, traufhoehe_m, firsthoehe_m FROM buildings_3d WHERE egid = ?', ('1243789',))
print(cursor.fetchone())
"
```
