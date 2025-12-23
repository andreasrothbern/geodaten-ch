"""
Layher Catalog Service

Stellt Zugriff auf Layher Gerüstmaterial-Daten bereit.
- Systeme (Blitz 70, Allround)
- Materialien mit Artikelnummern und Gewichten
- Richtwerte pro 100m² Gerüstfläche
- Optimale Feldlängen-Berechnung
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional
from functools import lru_cache

# Datenbankpfad
DB_PATH = Path(__file__).parent.parent / "data" / "layher_catalog.db"


class LayherCatalogService:
    """Service für Layher Materialkatalog"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        if not self.db_path.exists():
            raise FileNotFoundError(f"Layher-Katalog nicht gefunden: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Erstellt eine Datenbankverbindung"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # === Systeme ===

    def get_systems(self) -> list[dict]:
        """Hole alle verfügbaren Gerüstsysteme"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM systems ORDER BY name")
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_system(self, system_id: str) -> Optional[dict]:
        """Hole ein spezifisches System"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM systems WHERE id = ?", (system_id,))
            row = cursor.fetchone()
            if row:
                result = self._row_to_dict(row)
                result["field_lengths"] = json.loads(result.get("field_lengths_json", "[]"))
                result["frame_heights"] = json.loads(result.get("frame_heights_json", "[]"))
                return result
            return None

    # === Materialien ===

    def get_materials(self, system_id: str, category_id: Optional[str] = None) -> list[dict]:
        """Hole Materialien für ein System, optional gefiltert nach Kategorie"""
        with self._get_connection() as conn:
            if category_id:
                cursor = conn.execute("""
                    SELECT m.*, c.name_de as category_name
                    FROM materials m
                    JOIN material_categories c ON m.category_id = c.id
                    WHERE m.system_id = ? AND m.category_id = ?
                    ORDER BY c.sort_order, m.article_number
                """, (system_id, category_id))
            else:
                cursor = conn.execute("""
                    SELECT m.*, c.name_de as category_name
                    FROM materials m
                    JOIN material_categories c ON m.category_id = c.id
                    WHERE m.system_id = ?
                    ORDER BY c.sort_order, m.article_number
                """, (system_id,))
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_material(self, article_number: str) -> Optional[dict]:
        """Hole ein spezifisches Material per Artikelnummer"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT m.*, c.name_de as category_name, s.name as system_name
                FROM materials m
                JOIN material_categories c ON m.category_id = c.id
                JOIN systems s ON m.system_id = s.id
                WHERE m.article_number = ?
            """, (article_number,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def get_materials_by_length(self, system_id: str, category_id: str, length_m: float) -> list[dict]:
        """Hole Materialien einer bestimmten Länge"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM materials
                WHERE system_id = ? AND category_id = ? AND length_m = ?
                ORDER BY article_number
            """, (system_id, category_id, length_m))
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # === Richtwerte ===

    def get_reference_values(self, system_id: str) -> list[dict]:
        """Hole Richtwerte pro 100m² für ein System"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT r.*, m.name_de as material_name, m.weight_kg, c.name_de as category_name
                FROM reference_values r
                JOIN materials m ON r.article_number = m.article_number
                JOIN material_categories c ON r.category_id = c.id
                WHERE r.system_id = ?
                ORDER BY c.sort_order, r.id
            """, (system_id,))
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # === Lastklassen ===

    def get_load_classes(self) -> list[dict]:
        """Hole alle Lastklassen"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM load_classes ORDER BY class_number")
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_load_class(self, class_number: int) -> Optional[dict]:
        """Hole eine spezifische Lastklasse"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM load_classes WHERE class_number = ?",
                (class_number,)
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    # === Breitenklassen ===

    def get_width_classes(self) -> list[dict]:
        """Hole alle Breitenklassen"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM width_classes ORDER BY width_m")
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    # === Berechnungshilfen ===

    def find_optimal_field_length(self, system_id: str, required_length: float) -> float:
        """
        Finde die optimale Feldlänge für eine gegebene Anforderung.

        Verwendet die grösste Feldlänge, die <= required_length ist.
        """
        system = self.get_system(system_id)
        if not system:
            raise ValueError(f"System nicht gefunden: {system_id}")

        field_lengths = sorted(system["field_lengths"], reverse=True)

        for length in field_lengths:
            if length <= required_length + 0.1:  # 10cm Toleranz
                return length

        # Falls keine passt, kleinste Länge
        return field_lengths[-1]

    def calculate_field_layout(self, system_id: str, facade_length: float) -> dict:
        """
        Berechne optimale Feldaufteilung für eine Fassadenlänge.

        Returns:
            dict mit fields (Liste der Feldlängen), total_length, gap
        """
        system = self.get_system(system_id)
        if not system:
            raise ValueError(f"System nicht gefunden: {system_id}")

        field_lengths = sorted(system["field_lengths"], reverse=True)
        fields = []
        remaining = facade_length

        while remaining > 0.5:  # Mindestens 50cm übrig
            placed = False
            for length in field_lengths:
                if length <= remaining + 0.1:
                    fields.append(length)
                    remaining -= length
                    placed = True
                    break

            if not placed:
                # Keine passende Länge, kleinste nehmen
                fields.append(field_lengths[-1])
                remaining -= field_lengths[-1]

        total_length = sum(fields)
        gap = total_length - facade_length

        return {
            "fields": fields,
            "field_count": len(fields),
            "total_length_m": round(total_length, 2),
            "facade_length_m": facade_length,
            "gap_m": round(gap, 2)
        }

    def calculate_frames_for_height(self, system_id: str, target_height: float) -> list[dict]:
        """
        Berechne optimale Rahmenkombination für eine Zielhöhe.

        Returns:
            Liste mit Rahmentypen und Mengen
        """
        system = self.get_system(system_id)
        if not system:
            raise ValueError(f"System nicht gefunden: {system_id}")

        frame_heights = sorted(system["frame_heights"], reverse=True)
        result = {}
        remaining = target_height

        while remaining > 0.1:  # 10cm Toleranz
            placed = False
            for height in frame_heights:
                if height <= remaining + 0.1:
                    result[height] = result.get(height, 0) + 1
                    remaining -= height
                    placed = True
                    break

            if not placed:
                break

        # In Liste umwandeln mit Materialinfo
        frames = []
        materials = self.get_materials(system_id, "frame")
        for height, count in sorted(result.items(), reverse=True):
            # Passendes Material finden
            material = next((m for m in materials if m.get("height_m") == height), None)
            frames.append({
                "height_m": height,
                "quantity": count,
                "article_number": material["article_number"] if material else None,
                "name": material["name_de"] if material else f"Rahmen {height}m",
                "weight_kg": material["weight_kg"] if material else None
            })

        return frames

    def estimate_material_quantities(self, system_id: str, scaffold_area_m2: float) -> list[dict]:
        """
        Schätze Materialmengen basierend auf Richtwerten.

        Args:
            system_id: System-ID (blitz70 oder allround)
            scaffold_area_m2: Gerüstfläche in m²

        Returns:
            Liste mit geschätzten Mengen pro Material
        """
        reference_values = self.get_reference_values(system_id)
        factor = scaffold_area_m2 / 100  # Richtwerte sind pro 100m²

        estimates = []
        for ref in reference_values:
            qty_min = int(ref["quantity_per_100m2_min"] * factor)
            qty_max = int(ref["quantity_per_100m2_max"] * factor)
            qty_typical = int(ref["quantity_per_100m2_typical"] * factor)

            estimates.append({
                "article_number": ref["article_number"],
                "name": ref["material_name"],
                "category": ref["category_name"],
                "quantity_min": qty_min,
                "quantity_max": qty_max,
                "quantity_typical": qty_typical,
                "weight_per_piece_kg": ref["weight_kg"],
                "total_weight_kg": round(qty_typical * ref["weight_kg"], 1) if ref["weight_kg"] else None,
                "notes": ref.get("notes")
            })

        return estimates

    def estimate_combined_system_quantities(
        self,
        scaffold_area_m2: float,
        blitz_ratio: float = 0.7
    ) -> dict:
        """
        Schätze Materialmengen für kombiniertes System (Blitz + Allround).

        Verwendung: Blitz 70 für Standard-Bereiche, Allround für
        Verstärkungen, komplexe Ecken, oder höhere Lasten.

        Args:
            scaffold_area_m2: Gerüstfläche in m²
            blitz_ratio: Anteil Blitz 70 (0.0-1.0), Rest ist Allround
                        Default 0.7 = 70% Blitz, 30% Allround

        Returns:
            dict mit separaten Listen pro System und Gesamtübersicht
        """
        allround_ratio = 1.0 - blitz_ratio

        blitz_area = scaffold_area_m2 * blitz_ratio
        allround_area = scaffold_area_m2 * allround_ratio

        # Materialien für beide Systeme berechnen
        blitz_materials = self.estimate_material_quantities("blitz70", blitz_area) if blitz_area > 0 else []
        allround_materials = self.estimate_material_quantities("allround", allround_area) if allround_area > 0 else []

        # Gesamtgewichte berechnen
        blitz_weight = sum(m["total_weight_kg"] or 0 for m in blitz_materials)
        allround_weight = sum(m["total_weight_kg"] or 0 for m in allround_materials)
        total_weight = blitz_weight + allround_weight

        blitz_pieces = sum(m["quantity_typical"] for m in blitz_materials)
        allround_pieces = sum(m["quantity_typical"] for m in allround_materials)
        total_pieces = blitz_pieces + allround_pieces

        return {
            "system": "combined",
            "blitz_ratio": blitz_ratio,
            "allround_ratio": allround_ratio,
            "blitz": {
                "system_id": "blitz70",
                "area_m2": round(blitz_area, 1),
                "materials": blitz_materials,
                "total_pieces": blitz_pieces,
                "total_weight_kg": round(blitz_weight, 1)
            },
            "allround": {
                "system_id": "allround",
                "area_m2": round(allround_area, 1),
                "materials": allround_materials,
                "total_pieces": allround_pieces,
                "total_weight_kg": round(allround_weight, 1)
            },
            "combined_summary": {
                "total_area_m2": scaffold_area_m2,
                "total_pieces": total_pieces,
                "total_weight_kg": round(total_weight, 1),
                "total_weight_tonnen": round(total_weight / 1000, 2),
                "weight_per_m2_kg": round(total_weight / scaffold_area_m2, 1) if scaffold_area_m2 > 0 else 0
            },
            "hinweis": (
                f"Kombination: {int(blitz_ratio*100)}% Blitz 70 ({blitz_area:.0f} m²) + "
                f"{int(allround_ratio*100)}% Allround ({allround_area:.0f} m²)"
            )
        }

    def get_system_info(self, system_id: str) -> dict:
        """
        Hole detaillierte System-Informationen für UI-Anzeige.

        Returns:
            dict mit Charakteristiken, Vorteilen, Anwendungen
        """
        systems_info = {
            "blitz70": {
                "id": "blitz70",
                "name": "Layher Blitz 70",
                "kurz": "Standard-Fassadengerüst",
                "beschreibung": "Schnellbaugerüst für Standard-Fassadenarbeiten. "
                               "Einfacher Aufbau durch Fallkopfverriegelung.",
                "vorteile": [
                    "Schneller Auf- und Abbau",
                    "Leichte Bauteile",
                    "Wirtschaftlich für Wohnbau",
                    "Bewährtes System"
                ],
                "anwendungen": [
                    "Fassadenarbeiten (Malen, Verputzen)",
                    "Wärmedämmung",
                    "Dacharbeiten EFH/MFH",
                    "Renovationen"
                ],
                "lastklasse": "3-4 (200-300 kg/m²)",
                "max_feldlaenge_m": 3.07,
                "typisches_gewicht_kg_m2": 28
            },
            "allround": {
                "id": "allround",
                "name": "Layher Allround",
                "kurz": "Universalgerüst für hohe Anforderungen",
                "beschreibung": "Modulgerüst mit Rosettensystem. Flexibel für "
                               "komplexe Geometrien und hohe Lasten.",
                "vorteile": [
                    "Höhere Tragfähigkeit",
                    "Flexible Winkel (alle 45°)",
                    "Anpassbar um Hindernisse",
                    "Für Industriebauten geeignet"
                ],
                "anwendungen": [
                    "Industriegerüste",
                    "Komplexe Fassaden",
                    "Traggerüste (Betonarbeiten)",
                    "Gebäude mit Vorsprüngen/Rohren"
                ],
                "lastklasse": "4-6 (300-600 kg/m²)",
                "max_feldlaenge_m": 3.07,
                "typisches_gewicht_kg_m2": 35
            },
            "combined": {
                "id": "combined",
                "name": "Blitz + Allround Kombination",
                "kurz": "Optimierte Kombination beider Systeme",
                "beschreibung": "Blitz 70 für Standardbereiche, Allround für "
                               "Verstärkungen und komplexe Zonen. Kostenoptimiert.",
                "vorteile": [
                    "Kosteneffizient",
                    "Flexibel einsetzbar",
                    "Beste Eigenschaften beider Systeme",
                    "Anpassbar an Gebäudegeometrie"
                ],
                "anwendungen": [
                    "Gebäude mit Erkern/Vorsprüngen",
                    "Teilweise höhere Lasten nötig",
                    "Kostensensitive Projekte",
                    "Dach + Fassade kombiniert"
                ],
                "lastklasse": "3-6 (je nach Zone)",
                "max_feldlaenge_m": 3.07,
                "typisches_gewicht_kg_m2": 30
            }
        }
        return systems_info.get(system_id, systems_info["blitz70"])

    def calculate_total_weight(self, material_list: list[dict]) -> dict:
        """
        Berechne Gesamtgewicht einer Materialliste.

        Args:
            material_list: Liste mit {"article_number": ..., "quantity": ...}

        Returns:
            dict mit Gesamtgewicht und Details
        """
        total_weight = 0
        details = []

        for item in material_list:
            material = self.get_material(item["article_number"])
            if material:
                weight = material["weight_kg"] * item["quantity"]
                total_weight += weight
                details.append({
                    "article_number": item["article_number"],
                    "name": material["name_de"],
                    "quantity": item["quantity"],
                    "weight_per_piece_kg": material["weight_kg"],
                    "total_weight_kg": round(weight, 1)
                })

        return {
            "items": details,
            "total_weight_kg": round(total_weight, 1),
            "total_weight_tons": round(total_weight / 1000, 2)
        }

    # === Hilfsmethoden ===

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Konvertiert sqlite3.Row zu dict"""
        return dict(row) if row else {}


# Singleton-Instanz
_catalog_service: Optional[LayherCatalogService] = None


def get_catalog_service() -> LayherCatalogService:
    """Hole Singleton-Instanz des Catalog-Service"""
    global _catalog_service
    if _catalog_service is None:
        _catalog_service = LayherCatalogService()
    return _catalog_service


# === Convenience-Funktionen ===

@lru_cache(maxsize=32)
def get_system_field_lengths(system_id: str) -> list[float]:
    """Hole verfügbare Feldlängen für ein System (gecached)"""
    service = get_catalog_service()
    system = service.get_system(system_id)
    return system["field_lengths"] if system else []


@lru_cache(maxsize=32)
def get_system_frame_heights(system_id: str) -> list[float]:
    """Hole verfügbare Rahmenhöhen für ein System (gecached)"""
    service = get_catalog_service()
    system = service.get_system(system_id)
    return system["frame_heights"] if system else []
