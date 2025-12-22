"""
geodienste.ch WFS Adapter
==========================

Adapter für die amtliche Vermessung via geodienste.ch WFS
Liefert Gebäudegeometrien (Grundriss-Polygone)
"""

import httpx
import math
import xml.etree.ElementTree as ET
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class BuildingGeometry:
    """Gebäudegeometrie mit berechneten Massen"""
    egid: Optional[int]
    polygon: List[Tuple[float, float]]  # Liste von (x, y) Koordinaten
    bounding_box: Dict[str, float]  # min_x, min_y, max_x, max_y

    # Berechnete Werte
    perimeter_m: float  # Umfang in Metern
    area_m2: float  # Fläche in m²
    sides: List[Dict[str, Any]]  # Seitenlängen mit Start/End-Koordinaten

    # Abgeleitete Masse
    width_m: float  # Breite (Bounding Box)
    depth_m: float  # Tiefe (Bounding Box)
    estimated_height_m: Optional[float]  # Geschätzte Höhe

    # Gerüstbau-relevante Daten
    facade_length_total_m: float  # Gesamte Fassadenlänge


# Standard-Geschosshöhe für Schätzungen
FLOOR_HEIGHT_M = 3.0  # Durchschnittliche Geschosshöhe

# Gebäudekategorie -> typische Geschosshöhe
FLOOR_HEIGHTS_BY_CATEGORY = {
    1020: 2.8,   # Einfamilienhaus
    1030: 2.7,   # Mehrfamilienhaus
    1040: 2.8,   # Wohngebäude mit Nebennutzung
    1060: 3.5,   # Gebäude mit teilweiser Wohnnutzung (oft Gewerbe EG)
    1080: 4.0,   # Gebäude ohne Wohnnutzung (Gewerbe/Industrie)
}


class GeodiensteService:
    """Service für geodienste.ch WFS Zugriff"""

    WFS_BASE_URL = "https://geodienste.ch/db/av_0/deu"
    LAYER_BODENBEDECKUNG = "ms:LCSF"  # Bodenbedeckung (enthält Gebäude)

    def __init__(self):
        self.timeout = httpx.Timeout(20.0, connect=5.0)

    async def get_building_geometry(
        self,
        x: float,
        y: float,
        tolerance: int = 50,
        egid: Optional[int] = None
    ) -> Optional[BuildingGeometry]:
        """
        Gebäudegeometrie per Koordinate oder EGID abrufen

        Args:
            x: LV95 Ost-Koordinate (oder LV03)
            y: LV95 Nord-Koordinate (oder LV03)
            tolerance: Suchradius in Metern
            egid: Optional EGID zum Filtern

        Returns:
            BuildingGeometry mit Polygon und berechneten Massen
        """
        # Koordinaten in LV95 (EPSG:2056) konvertieren falls nötig
        # swisstopo liefert LV95 (2600xxx), WFS erwartet auch LV95
        if x < 2000000:
            # LV03 -> LV95 (ungefähre Konversion)
            x = x + 2000000
            y = y + 1000000

        # Bounding Box berechnen
        bbox = f"{x-tolerance},{y-tolerance},{x+tolerance},{y+tolerance}"

        params = {
            "SERVICE": "WFS",
            "VERSION": "1.1.0",
            "REQUEST": "GetFeature",
            "TYPENAME": self.LAYER_BODENBEDECKUNG,
            "BBOX": f"{bbox},EPSG:2056",
            "SRSNAME": "EPSG:2056",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.WFS_BASE_URL, params=params)
                response.raise_for_status()

                # GML parsen
                features = self._parse_gml_response(response.text)

                # Nach Gebäuden filtern (Art = "Gebaeude")
                buildings = [f for f in features if f.get("art") == "Gebaeude"]

                # Falls EGID angegeben, danach filtern
                if egid and buildings:
                    buildings = [b for b in buildings if b.get("gwr_egid") == egid]

                # Nächstes Gebäude zur Koordinate finden
                if not buildings:
                    return None

                # Das nächste Gebäude wählen (oder das mit der EGID)
                best_building = self._find_nearest_building(buildings, x, y)

                if not best_building or not best_building.get("polygon"):
                    return None

                # Geometrie berechnen
                return self._calculate_geometry(best_building)

        except Exception as e:
            print(f"WFS Error: {e}")
            return None

    def _parse_gml_response(self, xml_text: str) -> List[Dict]:
        """GML Response parsen"""
        features = []

        try:
            # Namespace handling
            namespaces = {
                'gml': 'http://www.opengis.net/gml',
                'ms': 'http://mapserver.gis.umn.edu/mapserver',
                'wfs': 'http://www.opengis.net/wfs',
            }

            root = ET.fromstring(xml_text)

            # Feature Members finden
            for member in root.findall('.//gml:featureMember', namespaces):
                lcsf = member.find('ms:LCSF', namespaces)
                if lcsf is None:
                    continue

                feature = {}

                # Attribute extrahieren
                for child in lcsf:
                    tag = child.tag.split('}')[-1]  # Namespace entfernen
                    if child.text:
                        feature[tag.lower()] = child.text

                # EGID konvertieren
                if feature.get('gwr_egid'):
                    try:
                        feature['gwr_egid'] = int(feature['gwr_egid'])
                    except:
                        pass

                # Polygon extrahieren
                polygon = self._extract_polygon(lcsf, namespaces)
                if polygon:
                    feature['polygon'] = polygon

                features.append(feature)

        except ET.ParseError as e:
            print(f"XML Parse Error: {e}")

        return features

    def _extract_polygon(self, element: ET.Element, namespaces: Dict) -> Optional[List[Tuple[float, float]]]:
        """Polygon-Koordinaten aus GML extrahieren"""
        # Nur das äussere Polygon (exterior) extrahieren
        exterior = element.find('.//gml:exterior', namespaces)
        if exterior is None:
            # Fallback: Suche in gesamtem Element
            exterior = element

        # LinearRing mit Koordinaten finden
        for pos_list in exterior.findall('.//gml:posList', namespaces):
            if pos_list.text:
                coords = pos_list.text.strip().split()
                polygon = []
                for i in range(0, len(coords) - 1, 2):
                    try:
                        x = float(coords[i])
                        y = float(coords[i + 1])
                        polygon.append((x, y))
                    except (ValueError, IndexError):
                        continue
                if polygon:
                    return polygon

        # Alternative: coordinates Element
        for coords_elem in exterior.findall('.//gml:coordinates', namespaces):
            if coords_elem.text:
                polygon = []
                for pair in coords_elem.text.strip().split():
                    parts = pair.split(',')
                    if len(parts) >= 2:
                        try:
                            x = float(parts[0])
                            y = float(parts[1])
                            polygon.append((x, y))
                        except ValueError:
                            continue
                if polygon:
                    return polygon

        return None

    def _find_nearest_building(
        self,
        buildings: List[Dict],
        x: float,
        y: float
    ) -> Optional[Dict]:
        """Nächstes Gebäude zur Koordinate finden"""
        if not buildings:
            return None

        def centroid_distance(building):
            polygon = building.get('polygon', [])
            if not polygon:
                return float('inf')
            cx = sum(p[0] for p in polygon) / len(polygon)
            cy = sum(p[1] for p in polygon) / len(polygon)
            return math.sqrt((cx - x) ** 2 + (cy - y) ** 2)

        return min(buildings, key=centroid_distance)

    def _calculate_geometry(self, building: Dict) -> BuildingGeometry:
        """Geometrie-Berechnungen durchführen"""
        polygon = building.get('polygon', [])

        # Bounding Box
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        bbox = {
            'min_x': min(xs),
            'max_x': max(xs),
            'min_y': min(ys),
            'max_y': max(ys),
        }

        # Breite und Tiefe aus Bounding Box
        width = bbox['max_x'] - bbox['min_x']
        depth = bbox['max_y'] - bbox['min_y']

        # Seitenlängen berechnen
        sides = []
        perimeter = 0.0

        for i in range(len(polygon)):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % len(polygon)]

            length = math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

            # Richtung berechnen (für Orientierung)
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            angle = math.degrees(math.atan2(dy, dx))

            # Himmelsrichtung bestimmen
            direction = self._angle_to_direction(angle)

            sides.append({
                'index': i,  # 0-basiert für Konsistenz mit SVG und Frontend
                'start': {'x': p1[0], 'y': p1[1]},
                'end': {'x': p2[0], 'y': p2[1]},
                'length_m': round(length, 2),
                'direction': direction,
                'angle_deg': round(angle, 1),
            })

            perimeter += length

        # Fläche berechnen (Shoelace-Formel)
        area = self._calculate_polygon_area(polygon)

        # EGID extrahieren
        egid = building.get('gwr_egid')

        return BuildingGeometry(
            egid=egid,
            polygon=polygon,
            bounding_box=bbox,
            perimeter_m=round(perimeter, 2),
            area_m2=round(area, 2),
            sides=sides,
            width_m=round(width, 2),
            depth_m=round(depth, 2),
            estimated_height_m=None,  # Wird später gesetzt
            facade_length_total_m=round(perimeter, 2),
        )

    def _calculate_polygon_area(self, polygon: List[Tuple[float, float]]) -> float:
        """Fläche eines Polygons berechnen (Shoelace-Formel)"""
        n = len(polygon)
        if n < 3:
            return 0.0

        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += polygon[i][0] * polygon[j][1]
            area -= polygon[j][0] * polygon[i][1]

        return abs(area) / 2.0

    def _angle_to_direction(self, angle: float) -> str:
        """Winkel in Himmelsrichtung umwandeln"""
        # Normalisieren auf 0-360
        angle = angle % 360
        if angle < 0:
            angle += 360

        directions = [
            (22.5, "O"),    # Ost
            (67.5, "NO"),   # Nordost
            (112.5, "N"),   # Nord
            (157.5, "NW"),  # Nordwest
            (202.5, "W"),   # West
            (247.5, "SW"),  # Südwest
            (292.5, "S"),   # Süd
            (337.5, "SO"),  # Südost
            (360, "O"),     # Ost
        ]

        for threshold, direction in directions:
            if angle < threshold:
                return direction
        return "O"


def estimate_building_height(
    floors: Optional[int],
    building_category_code: Optional[int] = None,
    area_m2: Optional[int] = None,
    manual_height: Optional[float] = None,
    egid: Optional[int] = None,
) -> tuple[Optional[float], str]:
    """
    Gebäudehöhe bestimmen mit Fallback-Kette:
    1. Manuelle Eingabe
    2. Datenbank (swissBUILDINGS3D)
    3. Berechnung aus Geschossen
    4. Standard nach Kategorie

    Args:
        floors: Anzahl Geschosse (aus GWR)
        building_category_code: Gebäudekategorie-Code (aus GWR)
        area_m2: Gebäudefläche (für Plausibilität)
        manual_height: Manuell eingegebene Höhe
        egid: Eidgenössischer Gebäudeidentifikator (für DB-Lookup)

    Returns:
        Tuple (Höhe in Metern, Quelle der Schätzung)
    """
    # 1. Manuelle Eingabe hat höchste Priorität
    if manual_height and manual_height > 0:
        return (manual_height, "manual")

    # 2. Datenbank-Lookup (swissBUILDINGS3D)
    if egid:
        try:
            from app.services.height_db import get_building_height
            db_result = get_building_height(egid)
            if db_result:
                return db_result
        except ImportError:
            pass  # height_db nicht verfügbar

    # Falls Geschosse bekannt
    if floors and floors > 0:
        # Geschosshöhe je nach Kategorie
        floor_height = FLOOR_HEIGHTS_BY_CATEGORY.get(
            building_category_code,
            FLOOR_HEIGHT_M
        )

        # Basishöhe = Geschosse × Geschosshöhe
        base_height = floors * floor_height

        # Dachaufbau schätzen (je nach Kategorie)
        if building_category_code in [1020, 1030, 1040]:  # Wohngebäude
            roof_height = 3.0
        elif building_category_code == 1080:  # Gewerbe/Industrie
            roof_height = 0.5
        else:
            roof_height = 2.0

        total_height = base_height + roof_height
        return (round(total_height, 1), "calculated_from_floors")

    # Fallback: Standard-Höhe basierend auf Gebäudekategorie
    DEFAULT_HEIGHTS = {
        1020: 8.0,   # Einfamilienhaus: ~2.5 Geschosse
        1030: 12.0,  # Mehrfamilienhaus: ~4 Geschosse
        1040: 10.0,  # Wohngebäude mit Nebennutzung
        1060: 15.0,  # Gebäude mit teilweiser Wohnnutzung (oft höher)
        1080: 8.0,   # Gebäude ohne Wohnnutzung
    }

    if building_category_code and building_category_code in DEFAULT_HEIGHTS:
        return (DEFAULT_HEIGHTS[building_category_code], "default_by_category")

    # Letzter Fallback: Allgemeine Standard-Höhe
    return (10.0, "default_standard")


def get_height_details(
    floors: Optional[int],
    building_category_code: Optional[int],
    manual_height: Optional[float],
    egid: Optional[int],
    manual_traufhoehe: Optional[float] = None,
    manual_firsthoehe: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Alle verfügbaren Höheninformationen sammeln.

    Args:
        floors: Anzahl Geschosse (aus GWR)
        building_category_code: Gebäudekategorie-Code (aus GWR)
        manual_height: Manuell eingegebene Gesamthöhe (deprecated)
        egid: Eidgenössischer Gebäudeidentifikator (für DB-Lookup)
        manual_traufhoehe: Manuell eingegebene Traufhöhe (überschreibt DB)
        manual_firsthoehe: Manuell eingegebene Firsthöhe (überschreibt DB)

    Returns:
        Dictionary mit geschätzter Höhe, gemessener Höhe und Quellen
    """
    result = {
        "estimated_height_m": None,
        "estimated_source": None,
        "measured_height_m": None,
        "measured_source": None,
        "active_height_m": None,  # Die tatsächlich verwendete Höhe
        "active_source": None,
        # Detaillierte Höhen aus swissBUILDINGS3D
        "traufhoehe_m": None,      # Dachhöhe min - Terrain
        "firsthoehe_m": None,      # Dachhöhe max - Terrain
        "gebaeudehoehe_m": None,   # Gesamthöhe
        # Flag für fehlende/veraltete Daten
        "needs_height_refresh": False,
        # Flag für manuelle Werte
        "manual_override": False,
    }

    # 1. Geschätzte Höhe berechnen (immer, wenn möglich)
    if floors and floors > 0:
        floor_height = FLOOR_HEIGHTS_BY_CATEGORY.get(
            building_category_code,
            FLOOR_HEIGHT_M
        )
        if building_category_code in [1020, 1030, 1040]:
            roof_height = 3.0
        elif building_category_code == 1080:
            roof_height = 0.5
        else:
            roof_height = 2.0
        result["estimated_height_m"] = round(floors * floor_height + roof_height, 1)
        result["estimated_source"] = "calculated_from_floors"
    elif building_category_code:
        DEFAULT_HEIGHTS = {
            1020: 8.0, 1030: 12.0, 1040: 10.0, 1060: 15.0, 1080: 8.0,
        }
        if building_category_code in DEFAULT_HEIGHTS:
            result["estimated_height_m"] = DEFAULT_HEIGHTS[building_category_code]
            result["estimated_source"] = "default_by_category"
        else:
            result["estimated_height_m"] = 10.0
            result["estimated_source"] = "default_standard"
    else:
        result["estimated_height_m"] = 10.0
        result["estimated_source"] = "default_standard"

    # 2. Gemessene Höhe aus Datenbank laden (falls verfügbar)
    measured_is_plausible = True
    if egid:
        try:
            from app.services.height_db import get_building_height, get_building_heights_detailed

            # Zuerst detaillierte Höhen versuchen
            detailed = get_building_heights_detailed(egid)
            if detailed:
                result["traufhoehe_m"] = detailed.get("traufhoehe_m")
                result["firsthoehe_m"] = detailed.get("firsthoehe_m")
                result["gebaeudehoehe_m"] = detailed.get("gebaeudehoehe_m")
                # Haupthöhe ist Gebäudehöhe oder Firsthöhe
                main_height = detailed.get("gebaeudehoehe_m") or detailed.get("firsthoehe_m")
                if main_height and main_height >= 2.0:
                    result["measured_height_m"] = main_height
                    result["measured_source"] = detailed.get("source", "database:swissBUILDINGS3D")

                # Prüfen ob Daten unvollständig sind (nur gebaeudehoehe, keine Trauf/First)
                has_gebaeudehoehe = detailed.get("gebaeudehoehe_m") is not None
                has_detailed = (detailed.get("traufhoehe_m") is not None or
                               detailed.get("firsthoehe_m") is not None)
                if has_gebaeudehoehe and not has_detailed:
                    result["needs_height_refresh"] = True
                    # Schätze Trauf/First aus Gesamthöhe (85% Traufe, 100% First)
                    gebaeudehoehe = detailed.get("gebaeudehoehe_m")
                    result["traufhoehe_m"] = round(gebaeudehoehe * 0.85, 1)
                    result["firsthoehe_m"] = round(gebaeudehoehe, 1)
                    result["heights_estimated"] = True  # Flag für Frontend
            else:
                # Fallback: Legacy-Höhe
                db_result = get_building_height(egid)
                if db_result and db_result[0] >= 2.0:
                    result["measured_height_m"] = db_result[0]
                    result["measured_source"] = db_result[1]

            # Plausibilitätsprüfung für measured_height_m
            if result["measured_height_m"] and result["estimated_height_m"]:
                ratio = result["measured_height_m"] / result["estimated_height_m"]
                if ratio < 0.4:
                    measured_is_plausible = False
                    result["measured_source"] = f"{result['measured_source']} (unplausibel: nur {ratio*100:.0f}% der geschätzten Höhe)"

            # Plausibilitätsprüfung für Trauf-/Firsthöhe
            # Prüft auf zwei Arten:
            # 1. Absolute Mindesthöhe (5m für bewohnte Gebäude)
            # 2. Mindesthöhe basierend auf GWR-Geschossen (2m pro Geschoss)
            # Bei Verstoß: Wahrscheinlich falsches Nebengebäude/Garage in DB gefunden
            is_implausible = False
            implausible_reason = ""

            if result["traufhoehe_m"]:
                # Prüfung 1: Absolute Mindesthöhe (5m)
                if result["traufhoehe_m"] < 5.0:
                    is_implausible = True
                    implausible_reason = f"< 5m Minimum ({result['traufhoehe_m']:.1f}m)"

                # Prüfung 2: Mindesthöhe basierend auf Geschossen
                # Mindestens 2m pro Geschoss (sehr konservativ)
                elif floors and floors >= 2:
                    min_height_by_floors = floors * 2.0
                    if result["traufhoehe_m"] < min_height_by_floors:
                        is_implausible = True
                        implausible_reason = f"{result['traufhoehe_m']:.1f}m < {min_height_by_floors:.0f}m ({floors} Geschosse × 2m)"

            if is_implausible:
                print(f"[WARNUNG] Unplausible Traufhöhe: {implausible_reason}")
                result["traufhoehe_m_original"] = result["traufhoehe_m"]
                result["traufhoehe_m"] = None
                result["firsthoehe_m_original"] = result.get("firsthoehe_m")
                result["firsthoehe_m"] = None
                result["height_data_implausible"] = True
                result["implausible_reason"] = implausible_reason
                measured_is_plausible = False
        except ImportError:
            pass

    # 3. Manuelle Traufhöhe/Firsthöhe anwenden (überschreibt DB-Werte)
    if manual_traufhoehe and manual_traufhoehe > 0:
        result["traufhoehe_m"] = manual_traufhoehe
        result["manual_override"] = True
    if manual_firsthoehe and manual_firsthoehe > 0:
        result["firsthoehe_m"] = manual_firsthoehe
        result["manual_override"] = True

    # Falls manuelle Werte gesetzt, aktualisiere auch measured_height_m
    if result["manual_override"]:
        # Verwende Firsthöhe als Haupthöhe (oder Traufhöhe falls kein First)
        if result["firsthoehe_m"]:
            result["measured_height_m"] = result["firsthoehe_m"]
            result["measured_source"] = "manual"
        elif result["traufhoehe_m"]:
            result["measured_height_m"] = result["traufhoehe_m"]
            result["measured_source"] = "manual"
        measured_is_plausible = True  # Manuelle Werte sind immer plausibel

    # 4. Aktive Höhe bestimmen (Priorität: manuell > gemessen (wenn plausibel) > geschätzt)
    if manual_height and manual_height > 0:
        result["active_height_m"] = manual_height
        result["active_source"] = "manual"
    elif result["manual_override"] and result["firsthoehe_m"]:
        result["active_height_m"] = result["firsthoehe_m"]
        result["active_source"] = "manual"
    elif result["measured_height_m"] and measured_is_plausible:
        result["active_height_m"] = result["measured_height_m"]
        result["active_source"] = result["measured_source"]
    else:
        result["active_height_m"] = result["estimated_height_m"]
        result["active_source"] = result["estimated_source"]

    return result


def calculate_scaffolding_data(
    geometry: BuildingGeometry,
    floors: Optional[int] = None,
    building_category_code: Optional[int] = None,
    manual_height: Optional[float] = None,
    coordinates: Optional[Dict[str, float]] = None,
    egid: Optional[int] = None,
    manual_traufhoehe: Optional[float] = None,
    manual_firsthoehe: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Gerüstbau-relevante Daten berechnen

    Args:
        geometry: Gebäudegeometrie aus WFS
        floors: Anzahl Geschosse (aus GWR)
        building_category_code: Gebäudekategorie (aus GWR)
        manual_height: Manuell eingegebene Höhe (deprecated)
        coordinates: LV95 Koordinaten für 3D Viewer Link
        egid: EGID aus GWR (hat Priorität über geometry.egid)
        manual_traufhoehe: Manuell eingegebene Traufhöhe
        manual_firsthoehe: Manuell eingegebene Firsthöhe

    Returns:
        Dictionary mit Gerüstbau-Daten
    """
    # EGID: Priorität hat der übergebene EGID (aus GWR), dann geometry.egid
    effective_egid = egid if egid is not None else geometry.egid

    # Höhendetails sammeln (geschätzt + gemessen)
    height_info = get_height_details(
        floors=floors,
        building_category_code=building_category_code,
        manual_height=manual_height,
        egid=effective_egid,
        manual_traufhoehe=manual_traufhoehe,
        manual_firsthoehe=manual_firsthoehe,
    )

    height = height_info["active_height_m"]

    # Gerüstfläche berechnen (Umfang × Höhe)
    if height:
        scaffold_area = geometry.perimeter_m * height
    else:
        scaffold_area = None

    # Hauptseiten identifizieren (längste Seiten)
    main_sides = [s for s in geometry.sides if s['length_m'] > 3.0]

    # 3D Viewer Link generieren
    viewer_3d_url = None
    if coordinates:
        e = coordinates.get('lv95_e')
        n = coordinates.get('lv95_n')
        if e and n:
            # LV95 Koordinaten brauchen volles Format (E: 2xxxxxx, N: 1xxxxxx)
            # Falls Koordinaten im verkürzten Format sind, Präfix hinzufügen
            e_full = e if e > 2000000 else e + 2000000
            n_full = n if n > 1000000 else n + 1000000
            # Neue URL-Format seit 2024 (center statt E/N)
            # 3D-Ansicht zeigt Gebäude automatisch - kein layers Parameter nötig
            viewer_3d_url = (
                f"https://map.geo.admin.ch/#/map?lang=de"
                f"&bgLayer=ch.swisstopo.pixelkarte-farbe"
                f"&center={e_full:.0f},{n_full:.0f}&z=12&3d=true"
            )

    return {
        "building": {
            "egid": geometry.egid,
            "footprint_area_m2": geometry.area_m2,
            "bounding_box": {
                "width_m": geometry.width_m,
                "depth_m": geometry.depth_m,
            },
        },
        "dimensions": {
            "perimeter_m": geometry.perimeter_m,
            "estimated_height_m": height,
            "height_source": height_info["active_source"],
            "floors": floors,
            # Separate Höhenangaben
            "height_estimated_m": height_info["estimated_height_m"],
            "height_estimated_source": height_info["estimated_source"],
            "height_measured_m": height_info["measured_height_m"],
            "height_measured_source": height_info["measured_source"],
            # Detaillierte Höhen aus swissBUILDINGS3D (für Gerüstbau)
            "traufhoehe_m": height_info.get("traufhoehe_m"),
            "firsthoehe_m": height_info.get("firsthoehe_m"),
            "gebaeudehoehe_m": height_info.get("gebaeudehoehe_m"),
        },
        "scaffolding": {
            "facade_length_total_m": geometry.facade_length_total_m,
            "estimated_scaffold_area_m2": round(scaffold_area, 1) if scaffold_area else None,
            "number_of_sides": len(geometry.sides),
            "main_sides_count": len(main_sides),
        },
        "sides": geometry.sides,  # Geometrische Reihenfolge beibehalten für SVG-Konsistenz
        "polygon": {
            "coordinates": geometry.polygon,
            "coordinate_system": "LV95 (EPSG:2056)",
        },
        "viewer_3d_url": viewer_3d_url,
        # Flag für automatische Höhenaktualisierung
        "needs_height_refresh": height_info.get("needs_height_refresh", False),
    }
