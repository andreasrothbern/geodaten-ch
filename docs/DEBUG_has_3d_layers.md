# Debug: has_3d_layers nicht in API Response

**Datum:** 12.01.2026
**Status:** ✅ GEFIXT

## Problem

Die API `/api/v1/smart-building/data` gab `has_3d_layers: null` zurück, obwohl die Datenbank den Wert `has_3d_layers: 1` enthielt.

### Beispiel (vor Fix)

```bash
# DB hat korrekte Daten:
sqlite3 building_3d.db "SELECT has_3d_layers FROM buildings_3d WHERE egid=2245881"
# → 1

# API gab None zurück:
curl "http://localhost:8000/api/v1/smart-building/data?address=Spitalgasse%2044,%20Bern"
# → "has_3d_layers": null
```

## Lösung (12.01.2026 21:30)

**Das eigentliche Problem:** Das Feld `has_3d_layers` war in der **`_bundle_to_dict()` Funktion in service.py** enthalten (Zeile 303), aber der API-Endpunkt in `main.py` baut eine **eigene Response-Struktur** und nutzt diese Funktion nicht!

### Fix in main.py

```python
# Zeile 3817-3823
# Dach (3D-Layer - NEU 11.01.2026)
"roof_dach_min_m": bundle.roof_dach_min_m,
"roof_dach_max_m": bundle.roof_dach_max_m,
"has_roof_geometry": bundle.has_roof_geometry,
"roof_gebaeudeeinheit": bundle.roof_gebaeudeeinheit,
# FIX 12.01.2026 21:30 - has_3d_layers fehlte in API-Response
"has_3d_layers": bundle.has_3d_layers,
```

### Verifizierung

```bash
# API gibt jetzt korrekt zurück:
curl "http://localhost:8000/api/v1/smart-building/data?address=Spitalgasse%2044,%20Bern&force_refresh=true"
# → "has_3d_layers": true
```

## Debug-Erkenntnisse

Die anfängliche Annahme war falsch: `_load_roof_data_from_db()` WURDE aufgerufen und setzte `bundle.has_3d_layers = True` korrekt. Das zeigten die Debug-Logs:

```
[DEBUG] Vor _load_roof_data_from_db für EGID 2245881
[ROOF_3D] _load_roof_data_from_db aufgerufen für EGID: 2245881
[ROOF_3D] has_3d_layers für EGID 2245881: raw=1, bundle=True
[DEBUG] Nach _load_roof_data_from_db, has_3d_layers=True
```

**Problem war:** Die Response-Struktur in main.py wurde unabhängig von `_bundle_to_dict()` aufgebaut und enthielt das Feld nicht.

## Betroffene Dateien

- `backend/app/main.py:3822` - ✅ **Gefixt** - Feld zur API-Response hinzugefügt
- `backend/app/services/smart_building/service.py:303` - War bereits korrekt (aber nicht genutzt)
- `backend/app/services/smart_building/models.py:207` - War bereits korrekt