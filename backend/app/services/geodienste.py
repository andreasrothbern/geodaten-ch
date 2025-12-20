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
                'index': i + 1,
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
) -> tuple[Optional[float], str]:
    """
    Gebäudehöhe schätzen basierend auf verfügbaren Daten

    Args:
        floors: Anzahl Geschosse (aus GWR)
        building_category_code: Gebäudekategorie-Code (aus GWR)
        area_m2: Gebäudefläche (für Plausibilität)
        manual_height: Manuell eingegebene Höhe

    Returns:
        Tuple (Höhe in Metern, Quelle der Schätzung)
    """
    # Manuelle Eingabe hat Priorität
    if manual_height and manual_height > 0:
        return (manual_height, "manual")

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


def calculate_scaffolding_data(
    geometry: BuildingGeometry,
    floors: Optional[int] = None,
    building_category_code: Optional[int] = None,
    manual_height: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Gerüstbau-relevante Daten berechnen

    Args:
        geometry: Gebäudegeometrie aus WFS
        floors: Anzahl Geschosse (aus GWR)
        building_category_code: Gebäudekategorie (aus GWR)
        manual_height: Manuell eingegebene Höhe

    Returns:
        Dictionary mit Gerüstbau-Daten
    """
    # Höhe bestimmen (mit Fallback-Kette)
    height, height_source = estimate_building_height(
        floors=floors,
        building_category_code=building_category_code,
        manual_height=manual_height,
    )

    # Gerüstfläche berechnen (Umfang × Höhe)
    if height:
        scaffold_area = geometry.perimeter_m * height
    else:
        scaffold_area = None

    # Seitenlängen nach Größe sortieren
    sides_sorted = sorted(
        geometry.sides,
        key=lambda s: s['length_m'],
        reverse=True
    )

    # Hauptseiten identifizieren (längste Seiten)
    main_sides = [s for s in sides_sorted if s['length_m'] > 3.0]

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
            "height_source": height_source,
            "floors": floors,
        },
        "scaffolding": {
            "facade_length_total_m": geometry.facade_length_total_m,
            "estimated_scaffold_area_m2": round(scaffold_area, 1) if scaffold_area else None,
            "number_of_sides": len(geometry.sides),
            "main_sides_count": len(main_sides),
        },
        "sides": sides_sorted,
        "polygon": {
            "coordinates": geometry.polygon,
            "coordinate_system": "LV95 (EPSG:2056)",
        },
    }
