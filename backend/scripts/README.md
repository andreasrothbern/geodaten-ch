# swissBUILDINGS3D Import

Dieses Script importiert Gebäudehöhen aus swissBUILDINGS3D 3.0 Beta in eine lokale SQLite-Datenbank.

## Warum swissBUILDINGS3D?

swissBUILDINGS3D enthält gemessene 3D-Gebäudemodelle mit exakten Höhenangaben. Die Daten stammen aus LiDAR-Messungen und sind genauer als Schätzungen basierend auf Geschosszahlen.

**Version 3.0 Beta** enthält den EGID (Eidg. Gebäudeidentifikator), was eine direkte Zuordnung ermöglicht.

## Verfügbare Kantone (Stand Dezember 2025)

Gebäude mit EGID sind verfügbar für:
- AG, AI, AR, **BE**, BL, BS, FR, GL, JU, LU, NE, SG, SH, SO, SZ, TG
- Stadt Zürich

## Download

1. Besuche: https://www.swisstopo.admin.ch/de/landschaftmodell-swissbuildings3d-3-0-beta
2. Wähle den gewünschten Kanton
3. Lade die Daten im CityGML-Format herunter
4. Entpacke die ZIP-Datei

## Import

```bash
# Ins Backend-Verzeichnis wechseln
cd backend

# Virtuelle Umgebung aktivieren
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Import ausführen
python scripts/import_building_heights.py pfad/zur/datei.gml --canton BE
```

### Unterstützte Formate

- **CityGML** (.gml, .xml) - Standard von swisstopo
- **GeoPackage** (.gpkg) - Falls verfügbar (benötigt `fiona`)
- **CSV** - Manuell exportiert mit Spalten EGID,HEIGHT_M

### Optionen

```bash
python scripts/import_building_heights.py --help

# Statistiken anzeigen
python scripts/import_building_heights.py --stats

# Import mit Versionsangabe
python scripts/import_building_heights.py data.gml --canton BE --version 3.0
```

## Datenbank-Struktur

Die Daten werden in `app/data/building_heights.db` gespeichert:

```sql
CREATE TABLE building_heights (
    egid INTEGER PRIMARY KEY,
    height_m REAL NOT NULL,
    height_type TEXT,  -- 'measured', 'estimated', 'lidar'
    source TEXT,       -- z.B. 'swissBUILDINGS3D_3.0_BE'
    updated_at TIMESTAMP
);
```

## API-Endpoints

Nach dem Import sind die Höhendaten über die API verfügbar:

```bash
# Statistiken
GET /api/v1/heights/stats

# Höhe für EGID abrufen
GET /api/v1/heights/2242547
```

Die Gerüstbau-Berechnung verwendet automatisch die Datenbank, falls Höhendaten vorhanden sind.

## Fallback-Kette für Gebäudehöhen

1. **Manuell eingegeben** - Höchste Priorität
2. **swissBUILDINGS3D** - Gemessene Höhe aus Datenbank
3. **Berechnet aus Geschossen** - GWR-Daten × Geschosshöhe
4. **Standard nach Kategorie** - EFH: 8m, MFH: 12m, etc.
5. **Allgemeiner Standard** - 10m

## Lizenz

swissBUILDINGS3D 3.0 Beta: Open Government Data (OGD)
- Freie Nutzung
- Quellenangabe erforderlich: © swisstopo
