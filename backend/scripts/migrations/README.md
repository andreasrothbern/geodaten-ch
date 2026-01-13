# Datenbank-Migrationen

## Übersicht

Migrationen werden verwendet, um das DB-Schema zu erweitern, ohne bestehende Daten zu verlieren.

## Ausführung

```bash
cd backend
python scripts/migrations/001_add_3d_layers.py
```

## Verfügbare Migrationen

| Version | Beschreibung | Status |
|---------|--------------|--------|
| 001_add_3d_layers | 3D-Layer Tabellen (roofs, walls, floors) | ✅ |

## Migration 001: Add 3D Layers

**Datum:** 11.01.2026

**Änderungen:**

1. **buildings_3d** - 8 neue Spalten:
   - `objektart` - Gebäudetyp
   - `name_komplett` - Gebäudename
   - `gebaeude_nutzung` - Nutzungsart
   - `gebaeudeeinheit` - Verknüpfung zu anderen Layern
   - `roof_form` - Berechnete Dachform
   - `roof_form_confidence` - Konfidenz (0-1)
   - `roof_orientation` - First-Verlauf
   - `has_3d_layers` - Flag für erweiterte 3D-Daten

2. **building_roofs** - Neue Tabelle:
   - Dachgeometrie und berechnete Dachform
   - Z-Levels für Analyse
   - Optionale 3D-Geometrie (on-demand)

3. **building_walls** - Neue Tabelle:
   - 3D-Fassadengeometrie
   - Nur für komplexe Gebäude (on-demand)

4. **building_floors** - Neue Tabelle:
   - Exakter Grundriss
   - Nur für komplexe Gebäude (on-demand)

## Rollback

```bash
python scripts/migrations/001_add_3d_layers.py --rollback
```

**WARNUNG:** Rollback löscht die 3D-Layer Tabellen und deren Daten!