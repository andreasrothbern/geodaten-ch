#!/usr/bin/env python3
"""
Erstellt die Layher-Katalog SQLite Datenbank mit Materialdaten.

Datenquellen:
- Layher Blitz 70 Produktkatalog
- NPK 114 Richtwerte
- GL2025 Materialbewirtschaftung Dokumentation

Usage:
    python scripts/create_layher_catalog.py
"""

import sqlite3
import json
from pathlib import Path

# Datenbankpfad
DB_PATH = Path(__file__).parent.parent / "app" / "data" / "layher_catalog.db"


def create_schema(conn: sqlite3.Connection):
    """Erstellt das Datenbankschema"""
    cursor = conn.cursor()

    # Gerüstsysteme
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS systems (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            manufacturer TEXT DEFAULT 'Layher',
            field_lengths_json TEXT,
            frame_heights_json TEXT,
            deck_width_m REAL,
            max_load_class INTEGER,
            notes TEXT
        )
    """)

    # Lastklassen
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS load_classes (
            class_number INTEGER PRIMARY KEY,
            load_kg_per_m2 INTEGER NOT NULL,
            description_de TEXT,
            description_fr TEXT,
            typical_use TEXT
        )
    """)

    # Breitenklassen
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS width_classes (
            id TEXT PRIMARY KEY,
            width_m REAL NOT NULL,
            description_de TEXT,
            typical_use TEXT
        )
    """)

    # Materialkategorien
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS material_categories (
            id TEXT PRIMARY KEY,
            name_de TEXT NOT NULL,
            name_fr TEXT,
            sort_order INTEGER DEFAULT 0
        )
    """)

    # Materialien (Haupttabelle)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            article_number TEXT PRIMARY KEY,
            system_id TEXT NOT NULL REFERENCES systems(id),
            category_id TEXT NOT NULL REFERENCES material_categories(id),
            name_de TEXT NOT NULL,
            name_fr TEXT,
            length_m REAL,
            height_m REAL,
            width_m REAL,
            weight_kg REAL NOT NULL,
            load_class INTEGER,
            color TEXT,
            notes TEXT
        )
    """)

    # Richtwerte pro 100m² Gerüstfläche
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reference_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system_id TEXT NOT NULL REFERENCES systems(id),
            category_id TEXT NOT NULL REFERENCES material_categories(id),
            article_number TEXT REFERENCES materials(article_number),
            quantity_per_100m2_min INTEGER,
            quantity_per_100m2_max INTEGER,
            quantity_per_100m2_typical INTEGER,
            notes TEXT,
            UNIQUE(system_id, category_id, article_number)
        )
    """)

    # Montageleistung
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assembly_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scaffold_type TEXT NOT NULL,
            crew_size INTEGER DEFAULT 3,
            performance_m2_per_hour_min REAL,
            performance_m2_per_hour_max REAL,
            disassembly_factor REAL DEFAULT 0.8,
            notes TEXT
        )
    """)

    # Indizes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_system ON materials(system_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_category ON materials(category_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reference_system ON reference_values(system_id)")

    conn.commit()
    print("Schema erstellt")


def insert_base_data(conn: sqlite3.Connection):
    """Fügt Basisdaten ein (Lastklassen, Breitenklassen, Kategorien)"""
    cursor = conn.cursor()

    # Lastklassen nach EN 12811
    load_classes = [
        (1, 75, "Inspektionsgerüst", "Échafaudage d'inspection", "Leichte Inspektion"),
        (2, 150, "Leichte Arbeiten", "Travaux légers", "Maler, Verputzer"),
        (3, 200, "Fassadenarbeiten", "Travaux de façade", "Standard Fassade, Dachdecker"),
        (4, 300, "Maurerarbeiten", "Travaux de maçonnerie", "Maurer, mittlere Lasten"),
        (5, 450, "Steinarbeiten", "Travaux de pierre", "Naturstein, schwere Lasten"),
        (6, 600, "Schwere Lasten", "Charges lourdes", "Spezialanwendungen"),
    ]
    cursor.executemany(
        "INSERT OR REPLACE INTO load_classes VALUES (?, ?, ?, ?, ?)",
        load_classes
    )

    # Breitenklassen
    width_classes = [
        ("W06", 0.60, "Inspektionsgerüst", "Enge Platzverhältnisse"),
        ("W09", 0.90, "Standard Fassadengerüst", "Normalbreite"),
        ("W12", 1.20, "Maurergerüst", "Breitere Arbeitsfläche"),
    ]
    cursor.executemany(
        "INSERT OR REPLACE INTO width_classes VALUES (?, ?, ?, ?)",
        width_classes
    )

    # Materialkategorien
    categories = [
        ("frame", "Stellrahmen", "Cadres", 1),
        ("ledger", "Geländer/Riegel", "Garde-corps/Lisses", 2),
        ("deck", "Beläge", "Planchers", 3),
        ("diagonal", "Diagonalen", "Diagonales", 4),
        ("base", "Fussplatten/Spindeln", "Platines/Vérins", 5),
        ("anchor", "Verankerung", "Ancrage", 6),
        ("stair", "Treppen/Leitern", "Escaliers/Échelles", 7),
        ("protection", "Schutzgitter/Netze", "Grilles/Filets", 8),
        ("accessory", "Zubehör", "Accessoires", 9),
    ]
    cursor.executemany(
        "INSERT OR REPLACE INTO material_categories VALUES (?, ?, ?, ?)",
        categories
    )

    # Montageleistung (3-Mann-Kolonne)
    assembly_perf = [
        ("facade_standard", 3, 50, 60, 0.8, "Standard Fassadengerüst"),
        ("facade_gable", 3, 40, 50, 0.8, "Giebelgerüst"),
        ("roof_catch", 3, 20, 25, 0.8, "Dachfanggerüst (Laufmeter)"),
        ("complex", 3, 30, 40, 0.8, "Komplexe Geometrie"),
    ]
    cursor.executemany(
        "INSERT OR REPLACE INTO assembly_performance VALUES (NULL, ?, ?, ?, ?, ?, ?)",
        assembly_perf
    )

    conn.commit()
    print("Basisdaten eingefügt")


def insert_blitz70_system(conn: sqlite3.Connection):
    """Fügt Layher Blitz 70 System ein"""
    cursor = conn.cursor()

    # System
    system = {
        "id": "blitz70",
        "name": "Layher Blitz 70 Stahl",
        "manufacturer": "Layher",
        "field_lengths": [3.07, 2.57, 2.07, 1.57, 1.09, 0.73],
        "frame_heights": [2.00, 1.50, 1.00, 0.50],
        "deck_width_m": 0.32,
        "max_load_class": 6,
        "notes": "Standard Stahlrahmen-System"
    }

    cursor.execute("""
        INSERT OR REPLACE INTO systems
        (id, name, manufacturer, field_lengths_json, frame_heights_json, deck_width_m, max_load_class, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        system["id"],
        system["name"],
        system["manufacturer"],
        json.dumps(system["field_lengths"]),
        json.dumps(system["frame_heights"]),
        system["deck_width_m"],
        system["max_load_class"],
        system["notes"]
    ))

    conn.commit()
    print("Blitz 70 System eingefügt")


def insert_blitz70_materials(conn: sqlite3.Connection):
    """Fügt Layher Blitz 70 Materialien ein"""
    cursor = conn.cursor()

    materials = [
        # Stellrahmen (Vertikalrahmen)
        # Art.Nr, System, Kategorie, Name DE, Name FR, L, H, W, Gewicht, Lastklasse, Farbe, Notizen
        ("2622.200", "blitz70", "frame", "Stellrahmen 2.00m", "Cadre 2.00m", None, 2.00, 0.73, 18.5, 6, "verzinkt", None),
        ("2622.150", "blitz70", "frame", "Stellrahmen 1.50m", "Cadre 1.50m", None, 1.50, 0.73, 15.0, 6, "verzinkt", None),
        ("2622.100", "blitz70", "frame", "Stellrahmen 1.00m", "Cadre 1.00m", None, 1.00, 0.73, 12.0, 6, "verzinkt", None),
        ("2622.050", "blitz70", "frame", "Stellrahmen 0.50m", "Cadre 0.50m", None, 0.50, 0.73, 9.0, 6, "verzinkt", None),

        # Doppelgeländer (Horizontalriegel mit integriertem Geländer)
        ("2626.307", "blitz70", "ledger", "Doppelgeländer 3.07m", "Garde-corps double 3.07m", 3.07, None, None, 10.5, None, "verzinkt", None),
        ("2626.257", "blitz70", "ledger", "Doppelgeländer 2.57m", "Garde-corps double 2.57m", 2.57, None, None, 9.0, None, "verzinkt", None),
        ("2626.207", "blitz70", "ledger", "Doppelgeländer 2.07m", "Garde-corps double 2.07m", 2.07, None, None, 7.5, None, "verzinkt", None),
        ("2626.157", "blitz70", "ledger", "Doppelgeländer 1.57m", "Garde-corps double 1.57m", 1.57, None, None, 6.0, None, "verzinkt", None),
        ("2626.109", "blitz70", "ledger", "Doppelgeländer 1.09m", "Garde-corps double 1.09m", 1.09, None, None, 5.0, None, "verzinkt", None),
        ("2626.073", "blitz70", "ledger", "Doppelgeländer 0.73m", "Garde-corps double 0.73m", 0.73, None, None, 4.0, None, "verzinkt", None),

        # Robustböden (Beläge mit Durchstiegsklappe)
        ("2624.307", "blitz70", "deck", "Robustboden 3.07×0.32m", "Plancher robuste 3.07×0.32m", 3.07, None, 0.32, 19.5, 6, "Holz/Stahl", "Mit Durchstieg"),
        ("2624.257", "blitz70", "deck", "Robustboden 2.57×0.32m", "Plancher robuste 2.57×0.32m", 2.57, None, 0.32, 16.5, 6, "Holz/Stahl", None),
        ("2624.207", "blitz70", "deck", "Robustboden 2.07×0.32m", "Plancher robuste 2.07×0.32m", 2.07, None, 0.32, 13.5, 6, "Holz/Stahl", None),
        ("2624.157", "blitz70", "deck", "Robustboden 1.57×0.32m", "Plancher robuste 1.57×0.32m", 1.57, None, 0.32, 10.5, 6, "Holz/Stahl", None),
        ("2624.109", "blitz70", "deck", "Robustboden 1.09×0.32m", "Plancher robuste 1.09×0.32m", 1.09, None, 0.32, 8.0, 6, "Holz/Stahl", None),
        ("2624.073", "blitz70", "deck", "Robustboden 0.73×0.32m", "Plancher robuste 0.73×0.32m", 0.73, None, 0.32, 6.0, 6, "Holz/Stahl", None),

        # Stahlböden (leichter)
        ("2625.307", "blitz70", "deck", "Stahlboden 3.07×0.32m", "Plancher acier 3.07×0.32m", 3.07, None, 0.32, 14.0, 4, "verzinkt", None),
        ("2625.257", "blitz70", "deck", "Stahlboden 2.57×0.32m", "Plancher acier 2.57×0.32m", 2.57, None, 0.32, 12.0, 4, "verzinkt", None),

        # Diagonalen
        ("2628.307", "blitz70", "diagonal", "Diagonalstrebe 3.07m", "Diagonale 3.07m", 3.07, 2.00, None, 5.5, None, "verzinkt", "Mit Klauen"),
        ("2628.257", "blitz70", "diagonal", "Diagonalstrebe 2.57m", "Diagonale 2.57m", 2.57, 2.00, None, 5.0, None, "verzinkt", "Mit Klauen"),
        ("2628.207", "blitz70", "diagonal", "Diagonalstrebe 2.07m", "Diagonale 2.07m", 2.07, 2.00, None, 4.5, None, "verzinkt", "Mit Klauen"),

        # Fussplatten und Spindeln
        ("2620.000", "blitz70", "base", "Fussplatte 150×150mm", "Platine 150×150mm", None, None, 0.15, 2.5, None, "verzinkt", None),
        ("2620.040", "blitz70", "base", "Fussspindel 0.40m", "Vérin 0.40m", None, 0.40, None, 3.0, None, "verzinkt", "Verstellbar 0-40cm"),
        ("2620.060", "blitz70", "base", "Fussspindel 0.60m", "Vérin 0.60m", None, 0.60, None, 4.0, None, "verzinkt", "Verstellbar 0-60cm"),
        ("2620.080", "blitz70", "base", "Fussspindel 0.80m", "Vérin 0.80m", None, 0.80, None, 5.0, None, "verzinkt", "Verstellbar 0-80cm"),

        # Verankerung
        ("2630.050", "blitz70", "anchor", "Gerüsthalter kurz", "Fixation courte", 0.50, None, None, 1.5, None, "verzinkt", "Für Mauerwerk"),
        ("2630.080", "blitz70", "anchor", "Gerüsthalter lang", "Fixation longue", 0.80, None, None, 2.0, None, "verzinkt", "Grösserer Abstand"),
        ("2630.100", "blitz70", "anchor", "V-Anker", "Ancrage en V", 1.00, None, None, 3.0, None, "verzinkt", "Aussteifung"),
        ("2631.000", "blitz70", "anchor", "Ringöse M12", "Œillet M12", None, None, None, 0.3, None, "verzinkt", "Mit Dübel"),

        # Bordbretter
        ("2640.307", "blitz70", "protection", "Bordbrett 3.07m", "Plinthe 3.07m", 3.07, 0.15, None, 4.5, None, "Holz", None),
        ("2640.257", "blitz70", "protection", "Bordbrett 2.57m", "Plinthe 2.57m", 2.57, 0.15, None, 4.0, None, "Holz", None),

        # Stirngeländer
        ("2627.073", "blitz70", "ledger", "Stirngeländer 0.73m", "Garde-corps frontal 0.73m", 0.73, 1.00, None, 4.5, None, "verzinkt", "Abschluss"),

        # Konsolen (für breitere Beläge)
        ("2650.036", "blitz70", "accessory", "Konsolbelag 0.36m", "Console 0.36m", None, None, 0.36, 3.5, 3, "verzinkt", "Verbreiterung"),
        ("2650.073", "blitz70", "accessory", "Konsolbelag 0.73m", "Console 0.73m", None, None, 0.73, 5.5, 3, "verzinkt", "Verbreiterung"),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO materials
        (article_number, system_id, category_id, name_de, name_fr, length_m, height_m, width_m, weight_kg, load_class, color, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, materials)

    conn.commit()
    print(f"{len(materials)} Blitz 70 Materialien eingefügt")


def insert_reference_values(conn: sqlite3.Connection):
    """Fügt Richtwerte pro 100m² ein"""
    cursor = conn.cursor()

    # Richtwerte basierend auf NPK 114 und Praxiswerten
    # System, Kategorie, Art.Nr (optional), Min, Max, Typisch, Notizen
    reference_values = [
        # Stellrahmen
        ("blitz70", "frame", "2622.200", 15, 18, 16, "Hauptrahmen 2.00m"),
        ("blitz70", "frame", "2622.100", 4, 6, 5, "Ausgleichsrahmen"),

        # Doppelgeländer
        ("blitz70", "ledger", "2626.307", 20, 24, 22, "Hauptlänge"),
        ("blitz70", "ledger", "2626.257", 10, 12, 11, "Ergänzung"),
        ("blitz70", "ledger", "2626.207", 4, 6, 5, "Ergänzung"),

        # Beläge (3 Beläge nebeneinander für W09)
        ("blitz70", "deck", "2624.307", 28, 32, 30, "Mit Durchstieg"),
        ("blitz70", "deck", "2624.257", 14, 18, 16, None),

        # Diagonalen
        ("blitz70", "diagonal", "2628.307", 6, 8, 7, "Pro Feld eine"),

        # Fussplatten/Spindeln
        ("blitz70", "base", "2620.000", 10, 12, 11, None),
        ("blitz70", "base", "2620.040", 10, 12, 11, "Standard"),

        # Verankerung (4m Raster)
        ("blitz70", "anchor", "2630.050", 6, 8, 7, "Horizontalabstand 4m"),

        # Bordbretter
        ("blitz70", "protection", "2640.307", 10, 12, 11, "Auf allen Belägen"),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO reference_values
        (system_id, category_id, article_number, quantity_per_100m2_min, quantity_per_100m2_max, quantity_per_100m2_typical, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, reference_values)

    conn.commit()
    print(f"{len(reference_values)} Richtwerte eingefügt")


def insert_allround_system(conn: sqlite3.Connection):
    """Fügt Layher Allround System ein (Grundgerüst)"""
    cursor = conn.cursor()

    # System
    system = {
        "id": "allround",
        "name": "Layher Allround Aluminium",
        "manufacturer": "Layher",
        "field_lengths": [3.07, 2.57, 2.07, 1.57, 1.40, 1.09, 0.73],
        "frame_heights": [2.00, 1.50, 1.00, 0.50],
        "deck_width_m": 0.32,
        "max_load_class": 6,
        "notes": "Modulares Allround-System mit Rosettenkupplung"
    }

    cursor.execute("""
        INSERT OR REPLACE INTO systems
        (id, name, manufacturer, field_lengths_json, frame_heights_json, deck_width_m, max_load_class, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        system["id"],
        system["name"],
        system["manufacturer"],
        json.dumps(system["field_lengths"]),
        json.dumps(system["frame_heights"]),
        system["deck_width_m"],
        system["max_load_class"],
        system["notes"]
    ))

    # Grundlegende Allround-Materialien
    materials = [
        # Vertikalstiele
        ("0503.200", "allround", "frame", "Vertikalstiel 2.00m", "Montant 2.00m", None, 2.00, None, 8.5, 6, "Alu", "Mit 2 Rosetten"),
        ("0503.150", "allround", "frame", "Vertikalstiel 1.50m", "Montant 1.50m", None, 1.50, None, 6.5, 6, "Alu", "Mit 2 Rosetten"),
        ("0503.100", "allround", "frame", "Vertikalstiel 1.00m", "Montant 1.00m", None, 1.00, None, 4.5, 6, "Alu", "Mit 1 Rosette"),

        # Horizontalriegel
        ("0514.307", "allround", "ledger", "Horizontalriegel 3.07m", "Lisse 3.07m", 3.07, None, None, 6.5, None, "Alu", None),
        ("0514.257", "allround", "ledger", "Horizontalriegel 2.57m", "Lisse 2.57m", 2.57, None, None, 5.5, None, "Alu", None),
        ("0514.207", "allround", "ledger", "Horizontalriegel 2.07m", "Lisse 2.07m", 2.07, None, None, 4.5, None, "Alu", None),

        # Geländerholm
        ("0516.307", "allround", "ledger", "Geländerholm 3.07m", "Main courante 3.07m", 3.07, None, None, 5.0, None, "Alu", None),
        ("0516.257", "allround", "ledger", "Geländerholm 2.57m", "Main courante 2.57m", 2.57, None, None, 4.5, None, "Alu", None),

        # Beläge
        ("0508.307", "allround", "deck", "Alu-Boden 3.07×0.32m", "Plancher alu 3.07×0.32m", 3.07, None, 0.32, 11.0, 6, "Alu", None),
        ("0508.257", "allround", "deck", "Alu-Boden 2.57×0.32m", "Plancher alu 2.57×0.32m", 2.57, None, 0.32, 9.5, 6, "Alu", None),

        # Diagonalen
        ("0520.307", "allround", "diagonal", "Diagonale 3.07m", "Diagonale 3.07m", 3.07, 2.00, None, 4.0, None, "Alu", None),
        ("0520.257", "allround", "diagonal", "Diagonale 2.57m", "Diagonale 2.57m", 2.57, 2.00, None, 3.5, None, "Alu", None),

        # Fussplatten
        ("0500.000", "allround", "base", "Fussplatte 150×150mm", "Platine 150×150mm", None, None, 0.15, 2.0, None, "Alu", None),
        ("0500.040", "allround", "base", "Fussspindel 0.40m", "Vérin 0.40m", None, 0.40, None, 2.5, None, "Alu", None),
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO materials
        (article_number, system_id, category_id, name_de, name_fr, length_m, height_m, width_m, weight_kg, load_class, color, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, materials)

    conn.commit()
    print("Allround System mit Materialien eingefügt")


def verify_database(conn: sqlite3.Connection):
    """Verifiziert die Datenbank"""
    cursor = conn.cursor()

    print("\n=== Datenbank-Statistiken ===")

    cursor.execute("SELECT COUNT(*) FROM systems")
    print(f"Systeme: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM materials")
    print(f"Materialien: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM reference_values")
    print(f"Richtwerte: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM load_classes")
    print(f"Lastklassen: {cursor.fetchone()[0]}")

    print("\n=== Materialien pro System ===")
    cursor.execute("""
        SELECT s.name, COUNT(m.article_number) as count
        FROM systems s
        LEFT JOIN materials m ON s.id = m.system_id
        GROUP BY s.id
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} Artikel")

    print("\n=== Beispiel-Abfrage: Stellrahmen Blitz 70 ===")
    cursor.execute("""
        SELECT article_number, name_de, height_m, weight_kg
        FROM materials
        WHERE system_id = 'blitz70' AND category_id = 'frame'
        ORDER BY height_m DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} ({row[2]}m, {row[3]}kg)")


def main():
    """Hauptfunktion"""
    print(f"Erstelle Layher-Katalog Datenbank: {DB_PATH}")

    # Datenbank erstellen/überschreiben
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("Bestehende Datenbank gelöscht")

    conn = sqlite3.connect(DB_PATH)
    try:
        create_schema(conn)
        insert_base_data(conn)
        insert_blitz70_system(conn)
        insert_blitz70_materials(conn)
        insert_reference_values(conn)
        insert_allround_system(conn)
        verify_database(conn)
        print(f"\nDatenbank erfolgreich erstellt: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
