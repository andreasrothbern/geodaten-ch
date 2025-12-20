#!/usr/bin/env python3
"""
swissBUILDINGS3D Import Script
==============================

Importiert Gebäudehöhen aus swissBUILDINGS3D 3.0 Beta Daten in die SQLite-Datenbank.

Unterstützte Formate:
- CityGML (.gml, .xml)
- GeoPackage (.gpkg) - falls verfügbar
- CSV (manuell exportiert)

Verwendung:
    python import_building_heights.py <input_file> [--canton BE] [--version 3.0]

Download der Daten:
    1. Besuche: https://www.swisstopo.admin.ch/de/landschaftmodell-swissbuildings3d-3-0-beta
    2. Lade die Daten für den gewünschten Kanton herunter
    3. Entpacke die ZIP-Datei
    4. Führe dieses Script aus
"""

import argparse
import sys
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Generator, Tuple, Optional

# Zum Backend-Verzeichnis navigieren
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
sys.path.insert(0, str(backend_dir))

from app.services.height_db import (
    init_database,
    bulk_insert_heights,
    log_import,
    get_database_stats
)


def parse_citygml(file_path: Path) -> Generator[Tuple[int, float], None, None]:
    """
    CityGML-Datei parsen und EGID + Höhe extrahieren.

    swissBUILDINGS3D 3.0 Beta verwendet CityGML 2.0 Format.
    Gebäude haben gml:id mit EGID und 3D-Geometrie.

    Yields:
        Tuple (egid, height_m)
    """
    print(f"Parsing CityGML: {file_path.name}")

    # CityGML Namespaces
    namespaces = {
        'core': 'http://www.opengis.net/citygml/2.0',
        'bldg': 'http://www.opengis.net/citygml/building/2.0',
        'gml': 'http://www.opengis.net/gml',
        'gen': 'http://www.opengis.net/citygml/generics/2.0',
    }

    try:
        # Iteratives Parsing für große Dateien
        context = ET.iterparse(str(file_path), events=('end',))

        count = 0
        for event, elem in context:
            # Building-Elemente finden
            if elem.tag.endswith('}Building') or elem.tag == 'Building':

                egid = None
                height = None

                # EGID aus gml:id oder Attribut extrahieren
                gml_id = elem.get('{http://www.opengis.net/gml}id', '')
                if not gml_id:
                    gml_id = elem.get('id', '')

                # EGID aus ID extrahieren (Format: EGID_1234567 oder ähnlich)
                egid_match = re.search(r'EGID[_-]?(\d+)', gml_id, re.IGNORECASE)
                if egid_match:
                    egid = int(egid_match.group(1))
                else:
                    # Versuche reine Zahl zu finden
                    num_match = re.search(r'(\d{6,8})', gml_id)
                    if num_match:
                        egid = int(num_match.group(1))

                # Alternativ: EGID als genericAttribute
                for attr in elem.findall('.//gen:stringAttribute', namespaces):
                    name = attr.get('name', '')
                    if 'egid' in name.lower():
                        try:
                            value = attr.find('gen:value', namespaces)
                            if value is not None and value.text:
                                egid = int(value.text)
                        except ValueError:
                            pass

                # Höhe extrahieren
                # 1. Versuche measuredHeight
                measured_height = elem.find('.//bldg:measuredHeight', namespaces)
                if measured_height is not None and measured_height.text:
                    try:
                        height = float(measured_height.text)
                    except ValueError:
                        pass

                # 2. Fallback: Höhe aus Geometrie berechnen
                if height is None:
                    height = _extract_height_from_geometry(elem, namespaces)

                # 3. Fallback: genericAttribute "Hoehe"
                if height is None:
                    for attr in elem.findall('.//gen:doubleAttribute', namespaces):
                        name = attr.get('name', '')
                        if 'hoehe' in name.lower() or 'height' in name.lower():
                            try:
                                value = attr.find('gen:value', namespaces)
                                if value is not None and value.text:
                                    height = float(value.text)
                                    break
                            except ValueError:
                                pass

                # Wenn beide Werte gefunden, yielden
                if egid and height and height > 0:
                    count += 1
                    if count % 1000 == 0:
                        print(f"  ... {count} Gebäude verarbeitet")
                    yield (egid, height)

                # Speicher freigeben
                elem.clear()

        print(f"  Fertig: {count} Gebäude extrahiert")

    except ET.ParseError as e:
        print(f"XML Parse Error: {e}")
        raise


def _extract_height_from_geometry(building_elem, namespaces: dict) -> Optional[float]:
    """
    Gebäudehöhe aus 3D-Koordinaten berechnen (max Z - min Z).
    """
    z_values = []

    # Alle posList Elemente durchsuchen
    for pos_list in building_elem.findall('.//gml:posList', namespaces):
        if pos_list.text:
            coords = pos_list.text.strip().split()
            # Jeder dritte Wert ist Z-Koordinate (X Y Z X Y Z ...)
            for i in range(2, len(coords), 3):
                try:
                    z_values.append(float(coords[i]))
                except (ValueError, IndexError):
                    pass

    # Einzelne pos Elemente
    for pos in building_elem.findall('.//gml:pos', namespaces):
        if pos.text:
            parts = pos.text.strip().split()
            if len(parts) >= 3:
                try:
                    z_values.append(float(parts[2]))
                except ValueError:
                    pass

    if z_values:
        return max(z_values) - min(z_values)

    return None


def parse_csv(file_path: Path) -> Generator[Tuple[int, float], None, None]:
    """
    CSV-Datei mit EGID und Höhe parsen.

    Erwartetes Format:
        EGID,HEIGHT_M
        1234567,12.5
        ...

    Oder mit Header-Zeile (wird automatisch erkannt).
    """
    import csv

    print(f"Parsing CSV: {file_path.name}")

    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=',')

        # Header erkennen
        first_row = next(reader)
        egid_col = None
        height_col = None

        for i, col in enumerate(first_row):
            col_lower = col.lower().strip()
            if 'egid' in col_lower:
                egid_col = i
            elif 'height' in col_lower or 'hoehe' in col_lower or 'höhe' in col_lower:
                height_col = i

        # Wenn kein Header, erste Zeile als Daten behandeln
        if egid_col is None:
            egid_col = 0
            height_col = 1
            # Erste Zeile erneut verarbeiten
            try:
                egid = int(first_row[egid_col])
                height = float(first_row[height_col])
                if egid > 0 and height > 0:
                    yield (egid, height)
            except (ValueError, IndexError):
                pass  # War wohl doch ein Header

        count = 0
        for row in reader:
            try:
                egid = int(row[egid_col])
                height = float(row[height_col])
                if egid > 0 and height > 0:
                    count += 1
                    yield (egid, height)
            except (ValueError, IndexError):
                continue

        print(f"  Fertig: {count} Gebäude extrahiert")


def parse_geopackage(file_path: Path) -> Generator[Tuple[int, float], None, None]:
    """
    GeoPackage-Datei parsen (benötigt fiona/geopandas).
    """
    try:
        import fiona
    except ImportError:
        print("FEHLER: fiona ist nicht installiert.")
        print("Installiere mit: pip install fiona")
        sys.exit(1)

    print(f"Parsing GeoPackage: {file_path.name}")

    with fiona.open(file_path) as src:
        count = 0
        for feature in src:
            props = feature.get('properties', {})

            # EGID finden
            egid = None
            for key in ['EGID', 'egid', 'GWR_EGID', 'gwr_egid']:
                if key in props and props[key]:
                    try:
                        egid = int(props[key])
                        break
                    except ValueError:
                        pass

            # Höhe finden
            height = None
            for key in ['HEIGHT', 'height', 'HOEHE', 'hoehe', 'measuredHeight', 'MEASURED_HEIGHT']:
                if key in props and props[key]:
                    try:
                        height = float(props[key])
                        break
                    except ValueError:
                        pass

            # Fallback: Höhe aus Geometrie
            if height is None:
                geom = feature.get('geometry')
                if geom:
                    height = _height_from_geom(geom)

            if egid and height and height > 0:
                count += 1
                if count % 1000 == 0:
                    print(f"  ... {count} Gebäude verarbeitet")
                yield (egid, height)

        print(f"  Fertig: {count} Gebäude extrahiert")


def _height_from_geom(geom: dict) -> Optional[float]:
    """Höhe aus GeoJSON-Geometrie extrahieren"""
    z_values = []

    def extract_z(coords):
        if isinstance(coords, (list, tuple)):
            if len(coords) >= 3 and all(isinstance(c, (int, float)) for c in coords):
                z_values.append(coords[2])
            else:
                for c in coords:
                    extract_z(c)

    coords = geom.get('coordinates', [])
    extract_z(coords)

    if z_values:
        return max(z_values) - min(z_values)
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Importiert Gebäudehöhen aus swissBUILDINGS3D in die Datenbank',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
    python import_building_heights.py swissbuildings3d_BE.gml --canton BE
    python import_building_heights.py heights.csv --canton ZH --version 3.0
    python import_building_heights.py buildings.gpkg --canton BE

Download der Daten:
    https://www.swisstopo.admin.ch/de/landschaftmodell-swissbuildings3d-3-0-beta
        """
    )

    parser.add_argument('input_file', type=Path, help='Eingabedatei (GML, CSV, GPKG)')
    parser.add_argument('--canton', type=str, default='CH', help='Kanton (z.B. BE, ZH)')
    parser.add_argument('--version', type=str, default='3.0', help='Daten-Version')
    parser.add_argument('--stats', action='store_true', help='Nur Statistiken anzeigen')
    parser.add_argument('--batch-size', type=int, default=5000, help='Batch-Größe für Insert')

    args = parser.parse_args()

    # Statistiken anzeigen
    if args.stats:
        stats = get_database_stats()
        print("\n=== Datenbank-Statistiken ===")
        if not stats.get('exists'):
            print("Datenbank existiert noch nicht.")
        else:
            print(f"Anzahl Gebäude: {stats.get('records', 0):,}")
            print(f"Größe: {stats.get('db_size_mb', 0)} MB")
            if stats.get('sources'):
                print("\nQuellen:")
                for source, count in stats['sources'].items():
                    print(f"  - {source}: {count:,}")
            if stats.get('recent_imports'):
                print("\nLetzte Imports:")
                for imp in stats['recent_imports']:
                    print(f"  - {imp['date']}: {imp['file']} ({imp['records']:,} Gebäude)")
        return

    # Datei prüfen
    if not args.input_file.exists():
        print(f"FEHLER: Datei nicht gefunden: {args.input_file}")
        sys.exit(1)

    # Datenbank initialisieren
    init_database()

    # Parser auswählen
    suffix = args.input_file.suffix.lower()
    if suffix in ['.gml', '.xml']:
        parser_func = parse_citygml
    elif suffix == '.csv':
        parser_func = parse_csv
    elif suffix == '.gpkg':
        parser_func = parse_geopackage
    else:
        print(f"FEHLER: Unbekanntes Dateiformat: {suffix}")
        print("Unterstützt: .gml, .xml, .csv, .gpkg")
        sys.exit(1)

    # Daten importieren
    print(f"\n=== Import: {args.input_file.name} ===")
    print(f"Kanton: {args.canton}")
    print(f"Version: {args.version}\n")

    source = f"swissBUILDINGS3D_{args.version}_{args.canton}"
    batch = []
    total_count = 0

    try:
        for egid, height in parser_func(args.input_file):
            batch.append((egid, height))

            if len(batch) >= args.batch_size:
                bulk_insert_heights(batch, source)
                total_count += len(batch)
                print(f"  {total_count:,} Gebäude importiert...")
                batch = []

        # Restliche Daten
        if batch:
            bulk_insert_heights(batch, source)
            total_count += len(batch)

        # Import protokollieren
        log_import(
            source_file=args.input_file.name,
            canton=args.canton,
            records=total_count,
            version=args.version
        )

        print(f"\n✅ Import abgeschlossen!")
        print(f"   {total_count:,} Gebäude importiert")

        # Statistiken anzeigen
        stats = get_database_stats()
        print(f"   Datenbank enthält jetzt {stats.get('records', 0):,} Gebäude")

    except Exception as e:
        print(f"\n❌ FEHLER beim Import: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
