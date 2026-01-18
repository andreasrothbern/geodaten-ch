"""
Wall-Facade Matcher Service
============================

DEPRECATED 15.01.2026 (BUG-024):
    Diese Datei wird nicht mehr verwendet. Wall-Segmente werden jetzt direkt
    ans Frontend gesendet, wo geometrisches Matching durchgeführt wird.
    Siehe: docs/architecture/3D_LAYER_USAGE_3D_VIEW.md → BUG-024

    Kann nach vollständiger Migration gelöscht werden (505 Zeilen).

---

Matched Wall-Layer Geometrie (swissBUILDINGS3D) auf vereinfachte Fassaden (sides).

Ziel: Pro Fassade die korrekte z_min/z_max Höhe aus Wall-Layer extrahieren.

Ablauf:
1. Wall-Layer Daten für EGID laden (aus building_walls Tabelle)
2. Wall-Geometrie (WKB) → 2D-Linie (Basis der Wand) extrahieren
3. Matching: Für jede Side die passende Wall finden (Überlappung, Azimut)
4. facade_heights Dict erstellen: {"N": {"z_min": 541.0, "z_max": 550.0}, ...}

Version: 1.0 (13.01.2026)
DEPRECATED: 15.01.2026 (BUG-024)
"""

import math
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

# NEU 13.01.2026: DuckDB-Support via zentrale Config
from app.config import get_building_3d_connection, BUILDING_3D_DB_PATH, USE_DUCKDB

logger = logging.getLogger(__name__)

# Matching-Parameter
AZIMUTH_TOLERANCE_DEG = 30.0  # Toleranz für Richtungsvergleich
DISTANCE_TOLERANCE_M = 5.0    # Toleranz für Linien-Overlap (erhöht für konvexe Hülle)
MIN_OVERLAP_RATIO = 0.1       # Mindest-Überlappung (10%, reduziert weil Wall-Segmente oft kürzer)


@dataclass
class WallSegment:
    """Ein Wand-Segment aus dem Wall-Layer."""
    id: int
    gebaeudeeinheit: str
    egid: str
    z_min: float  # Terrain-Höhe (m ü.M.)
    z_max: float  # Wandoberkante (m ü.M.)
    height_m: float  # Wandhöhe (relativ)
    # 2D-Linie (Basis der Wand)
    start_e: float
    start_n: float
    end_e: float
    end_n: float
    length_m: float
    azimuth_deg: float  # Kantenrichtung
    normal_azimuth_deg: float = 0.0  # Fassadenrichtung (90° zur Kante)


@dataclass
class FacadeHeight:
    """Höhendaten für eine Fassade."""
    side_index: int
    side_direction: str
    z_min: float
    z_max: float
    height_m: float
    wall_id: Optional[int] = None
    confidence: float = 1.0


class WallFacadeMatcher:
    """
    Matched Wall-Layer Geometrie auf Fassaden (sides).

    Strategie:
    - Jede Wall hat eine 3D-Geometrie (Fläche)
    - Wir extrahieren die 2D-Basislinie (untere Kante)
    - Matching basiert auf: Azimut-Ähnlichkeit + Linien-Nähe + Überlappung
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

    def get_facade_heights(
        self,
        egid: str,
        sides: List[Dict[str, Any]]
    ) -> Dict[str, FacadeHeight]:
        """
        Berechnet Fassaden-Höhen aus Wall-Layer Daten.

        Args:
            egid: Gebäude-EGID
            sides: Liste von Fassaden aus Polygon-Vereinfachung

        Returns:
            Dict mit Fassaden-Höhen: {"N": FacadeHeight(...), "E": ...}
        """
        if not sides:
            return {}

        # 1. Wall-Segmente für EGID laden
        walls = self._load_wall_segments(egid)

        if not walls:
            logger.debug(f"[WALL-MATCH] Keine Wall-Daten für EGID {egid}")
            return {}

        logger.info(f"[WALL-MATCH] {len(walls)} Walls für EGID {egid}")

        # 2. Matching durchführen
        facade_heights = {}
        matched_walls = set()

        for side in sides:
            side_idx = side.get("index", 0)
            side_dir = side.get("direction", "?")

            # Finde beste Wall für diese Side
            best_match = self._find_best_wall_match(side, walls, matched_walls)

            if best_match:
                wall, confidence = best_match

                facade_heights[side_dir] = FacadeHeight(
                    side_index=side_idx,
                    side_direction=side_dir,
                    z_min=wall.z_min,
                    z_max=wall.z_max,
                    height_m=wall.height_m,
                    wall_id=wall.id,
                    confidence=confidence
                )

                matched_walls.add(wall.id)

                logger.debug(
                    f"[WALL-MATCH] Side {side_idx} ({side_dir}) → "
                    f"Wall {wall.id}: z_min={wall.z_min:.1f}, z_max={wall.z_max:.1f}, "
                    f"conf={confidence:.2f}"
                )

        return facade_heights

    def get_facade_heights_dict(
        self,
        egid: str,
        sides: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Vereinfachte Variante: Gibt nur z_min pro Richtung zurück.

        Für Kompatibilität mit TerrainProfile.facade_heights.

        Returns:
            {"N": 541.0, "E": 543.5, ...}  # z_min Werte
        """
        facade_heights = self.get_facade_heights(egid, sides)

        return {
            direction: fh.z_min
            for direction, fh in facade_heights.items()
        }

    def _load_wall_segments(self, egid: str) -> List[WallSegment]:
        """
        Lädt Wall-Segmente aus DB und extrahiert 2D-Linien.

        NEU 13.01.2026: Unterstützt DuckDB und SQLite via get_building_3d_connection().
        """
        if not BUILDING_3D_DB_PATH.exists():
            return []

        segments = []

        try:
            conn = get_building_3d_connection(read_only=True)
            cursor = conn.cursor()

            # FIX 14.01.2026: egid ist INTEGER in der Tabelle, nicht STRING
            # Konvertiere egid zu Integer für die Query
            try:
                egid_int = int(egid)
            except (ValueError, TypeError):
                logger.warning(f"[WALL-MATCH] Ungültige EGID: {egid}")
                conn.close()
                return []

            cursor.execute("""
                SELECT gebaeudeeinheit, egid, z_min, z_max, geometry_wkb
                FROM building_walls
                WHERE egid = ?
            """, (egid_int,))

            rows = cursor.fetchall()

            # DuckDB gibt Tuples zurück, SQLite mit row_factory gibt Row-Objekte zurück
            # Spalten-Indizes: 0=gebaeudeeinheit, 1=egid, 2=z_min, 3=z_max, 4=geometry_wkb
            for row in rows:
                if USE_DUCKDB:
                    gebaeudeeinheit, row_egid, z_min, z_max, geometry_wkb = row
                else:
                    gebaeudeeinheit = row['gebaeudeeinheit']
                    row_egid = row['egid']
                    z_min = row['z_min']
                    z_max = row['z_max']
                    geometry_wkb = row['geometry_wkb']

                if not geometry_wkb or not z_min or not z_max:
                    continue

                # WKB → Alle Basis-Linien extrahieren (mehrere pro MultiPolygon)
                base_lines = self._extract_base_lines_from_wkb(geometry_wkb)

                for line_data in base_lines:
                    start_e, start_n, end_e, end_n = line_data

                    # Länge und Azimut berechnen
                    dx = end_e - start_e
                    dy = end_n - start_n
                    length = math.sqrt(dx * dx + dy * dy)

                    if length < 1.0:  # Kurze Segmente ignorieren
                        continue

                    azimuth = math.degrees(math.atan2(dx, dy))
                    if azimuth < 0:
                        azimuth += 360

                    # Normalenrichtung (90° zur Kante)
                    normal_azimuth = (azimuth + 90) % 360

                    segments.append(WallSegment(
                        id=hash(gebaeudeeinheit) % 1000000,  # Pseudo-ID aus gebaeudeeinheit
                        gebaeudeeinheit=gebaeudeeinheit,
                        egid=str(row_egid),
                        z_min=z_min,
                        z_max=z_max,
                        height_m=z_max - z_min,
                        start_e=start_e,
                        start_n=start_n,
                        end_e=end_e,
                        end_n=end_n,
                        length_m=length,
                        azimuth_deg=azimuth,
                        normal_azimuth_deg=normal_azimuth
                    ))

            conn.close()

        except Exception as e:
            logger.error(f"[WALL-MATCH] DB-Fehler: {e}")

        return segments

    def _extract_base_lines_from_wkb(
        self,
        geometry_wkb: bytes
    ) -> List[Tuple[float, float, float, float]]:
        """
        Extrahiert 2D-Basislinien (untere Kanten) aus Wall-Geometrie.

        Wall-Geometrie ist typischerweise ein MultiPolygon mit vielen
        triangulierten Flächen. Wir:
        1. Sammeln alle Punkte
        2. Finden die Punkte nahe z_min (Basis-Ebene)
        3. Extrahieren die Kanten der konvexen Hülle

        Returns:
            Liste von (start_e, start_n, end_e, end_n) Tupeln
        """
        try:
            from shapely import wkb
            from shapely.geometry import MultiPolygon, Polygon, MultiPoint

            geom = wkb.loads(geometry_wkb)

            if geom.is_empty:
                return []

            # Alle Koordinaten sammeln (auch aus MultiPolygon)
            all_coords = []

            if isinstance(geom, MultiPolygon):
                for poly in geom.geoms:
                    if hasattr(poly, 'exterior'):
                        all_coords.extend(list(poly.exterior.coords))
            elif isinstance(geom, Polygon):
                if hasattr(geom, 'exterior'):
                    all_coords = list(geom.exterior.coords)
            elif hasattr(geom, 'coords'):
                all_coords = list(geom.coords)
            else:
                return []

            if len(all_coords) < 4:
                return []

            # Prüfen ob 3D-Koordinaten vorhanden
            if len(all_coords[0]) < 3:
                return []

            # Z-Werte analysieren
            z_vals = [c[2] for c in all_coords]
            z_min = min(z_vals)

            # Punkte nahe z_min finden (Basis-Ebene, Toleranz 0.5m)
            z_threshold = z_min + 0.5
            base_points_3d = [c for c in all_coords if c[2] <= z_threshold]

            if len(base_points_3d) < 3:
                return []

            # 2D-Projektion der Basis-Punkte
            base_points_2d = [(c[0], c[1]) for c in base_points_3d]

            # Konvexe Hülle berechnen (gibt die äußeren Kanten)
            try:
                hull = MultiPoint(base_points_2d).convex_hull

                if hull.is_empty or hull.geom_type == 'Point':
                    return []

                # Kanten aus der konvexen Hülle extrahieren
                if hull.geom_type == 'Polygon':
                    coords = list(hull.exterior.coords)
                elif hull.geom_type == 'LineString':
                    coords = list(hull.coords)
                else:
                    return []

                lines = []
                for i in range(len(coords) - 1):
                    p1, p2 = coords[i], coords[i + 1]
                    lines.append((p1[0], p1[1], p2[0], p2[1]))

                return lines

            except Exception as e:
                logger.debug(f"[WALL-MATCH] Konvexe-Hülle-Fehler: {e}")
                return []

        except Exception as e:
            logger.debug(f"[WALL-MATCH] WKB-Parsing-Fehler: {e}")
            return []

    def _find_best_wall_match(
        self,
        side: Dict[str, Any],
        walls: List[WallSegment],
        already_matched: set
    ) -> Optional[Tuple[WallSegment, float]]:
        """
        Findet die beste Wall für eine Side.

        Matching-Kriterien:
        1. Azimut-Ähnlichkeit (Richtung der Kante)
        2. Linien-Nähe (Abstand der Mittelpunkte)
        3. Längen-Überlappung

        Returns:
            (WallSegment, confidence) oder None
        """
        # Side-Daten extrahieren
        side_start = side.get("start_point", side.get("start", {}).values())
        side_end = side.get("end_point", side.get("end", {}).values())

        if isinstance(side_start, dict):
            side_start = [side_start.get("x"), side_start.get("y")]
            side_end = [side_end.get("x"), side_end.get("y")]

        side_start = list(side_start) if not isinstance(side_start, list) else side_start
        side_end = list(side_end) if not isinstance(side_end, list) else side_end

        # NEU 13.01.2026: Verwende normal_azimuth_deg (Fassadenrichtung) statt azimuth_deg (Kantenrichtung)
        side_azimuth = side.get("normal_azimuth_deg", side.get("azimuth_deg", 0))
        side_length = side.get("length_m", 0)

        # Mittelpunkt der Side
        side_mid_e = (side_start[0] + side_end[0]) / 2
        side_mid_n = (side_start[1] + side_end[1]) / 2

        best_wall = None
        best_score = 0.0

        for wall in walls:
            if wall.id in already_matched:
                continue

            # 1. Azimut-Differenz prüfen (basierend auf Normalenrichtung)
            # NEU 13.01.2026: Verwende normal_azimuth_deg für korrektes Fassaden-Matching
            azimuth_diff = abs(side_azimuth - wall.normal_azimuth_deg)
            if azimuth_diff > 180:
                azimuth_diff = 360 - azimuth_diff

            # Auch um 180° gedrehte Wände akzeptieren (Rückseite)
            if azimuth_diff > 90:
                azimuth_diff = 180 - azimuth_diff

            if azimuth_diff > AZIMUTH_TOLERANCE_DEG:
                continue

            # 2. Abstand der Mittelpunkte
            wall_mid_e = (wall.start_e + wall.end_e) / 2
            wall_mid_n = (wall.start_n + wall.end_n) / 2

            distance = math.sqrt(
                (side_mid_e - wall_mid_e)**2 +
                (side_mid_n - wall_mid_n)**2
            )

            # Maximaler Abstand = halbe Seitenlänge + Toleranz
            max_distance = (side_length / 2) + DISTANCE_TOLERANCE_M

            if distance > max_distance:
                continue

            # 3. Längen-Verhältnis
            length_ratio = min(side_length, wall.length_m) / max(side_length, wall.length_m)

            if length_ratio < MIN_OVERLAP_RATIO:
                continue

            # Score berechnen
            # NEU 13.01.2026: Gewichtung angepasst für Wall-Layer Matching
            # - Azimut ist wichtigstes Kriterium (Fassadenrichtung)
            # - Distanz weniger wichtig (Walls können segmentiert sein)
            # - Längen-Verhältnis am wenigsten wichtig (Wall-Segmente oft kürzer)
            azimuth_score = 1.0 - (azimuth_diff / AZIMUTH_TOLERANCE_DEG)
            distance_score = 1.0 - (distance / max_distance)
            length_score = length_ratio

            total_score = (azimuth_score * 0.6) + (distance_score * 0.3) + (length_score * 0.1)

            if total_score > best_score:
                best_score = total_score
                best_wall = wall

        # Score-Threshold reduziert: 0.3 statt 0.5
        if best_wall and best_score >= 0.3:
            return (best_wall, best_score)

        return None

    def has_wall_data(self, egid: str) -> bool:
        """
        Prüft ob Wall-Daten für EGID verfügbar sind.

        NEU 13.01.2026: Unterstützt DuckDB und SQLite.
        """
        if not BUILDING_3D_DB_PATH.exists():
            logger.debug(f"[WALL-MATCH] DB nicht gefunden: {BUILDING_3D_DB_PATH}")
            return False

        try:
            conn = get_building_3d_connection(read_only=True)
            cursor = conn.cursor()

            # DEBUG: Alle EGIDs in building_walls anzeigen (erste 5)
            try:
                cursor.execute("SELECT DISTINCT egid FROM building_walls LIMIT 5")
                sample_egids = [row[0] for row in cursor.fetchall()]
                logger.info(f"[WALL-MATCH] Sample EGIDs in building_walls: {sample_egids}")
            except Exception as e:
                logger.warning(f"[WALL-MATCH] Tabelle building_walls fehlt oder leer: {e}")
                conn.close()
                return False

            # FIX 14.01.2026: egid ist INTEGER in der Tabelle
            try:
                egid_int = int(egid)
            except (ValueError, TypeError):
                conn.close()
                return False

            cursor.execute(
                "SELECT COUNT(*) FROM building_walls WHERE egid = ?",
                (egid_int,)
            )
            count = cursor.fetchone()[0]
            conn.close()

            logger.info(f"[WALL-MATCH] has_wall_data({egid}): count={count}")
            return count > 0

        except Exception as e:
            logger.warning(f"[WALL-MATCH] has_wall_data Fehler: {e}")
            return False


# Singleton-Accessor
_service_instance = None


def get_wall_facade_matcher() -> WallFacadeMatcher:
    """Gibt die Singleton-Instanz des WallFacadeMatcher zurück."""
    global _service_instance
    if _service_instance is None:
        _service_instance = WallFacadeMatcher()
    return _service_instance
