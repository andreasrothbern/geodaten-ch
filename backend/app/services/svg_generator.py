"""
SVG Generator Service

Generiert professionelle SVG-Visualisierungen für Gebäude:
- Schnittansicht (Cross-Section)
- Fassadenansicht (Elevation)
- Grundriss (Floor Plan)

Stil basiert auf den Showcase-SVGs mit:
- Professionellen Schraffuren und Mustern
- NPK 114 Info-Box
- Legende
- Massskala
- Höhenkoten

Erweitert für komplexe Gebäudeformen:
- Polygon-Analyse zur Formbestimmung
- Mehrere Gebäudesektionen (L, T, U-Formen)
- Echte Polygon-Darstellung im Grundriss
"""

from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field
import math


@dataclass
class BuildingSection:
    """Einzelne Gebäudesektion für komplexe Formen"""
    name: str
    x: float
    y: float
    width: float
    height: float
    roof_type: str = "flat"  # flat, gable
    height_m: float = 10.0
    is_main: bool = False


@dataclass
class PolygonAnalysis:
    """Ergebnis der Polygon-Analyse"""
    is_complex: bool = False
    shape_type: str = "rectangle"  # rectangle, L, T, U, H, complex
    num_vertices: int = 4
    convexity: float = 1.0  # 1.0 = konvex, <1 = konkav
    bounding_box: Tuple[float, float, float, float] = (0, 0, 0, 0)  # minx, miny, maxx, maxy
    aspect_ratio: float = 1.0
    sections: List[BuildingSection] = field(default_factory=list)
    normalized_polygon: List[Tuple[float, float]] = field(default_factory=list)  # 0-1 normiert


@dataclass
class BuildingData:
    """Gebäudedaten für SVG-Generierung"""
    address: str
    egid: Optional[int] = None
    length_m: float = 10.0
    width_m: float = 10.0
    eave_height_m: float = 8.0
    ridge_height_m: Optional[float] = None
    floors: int = 3
    roof_type: str = "gable"  # flat, gable, hip
    area_m2: Optional[float] = None
    polygon: Optional[List[Tuple[float, float]]] = None
    width_class: str = "W09"
    measured_height_m: Optional[float] = None


class SVGGenerator:
    """Generiert professionelle SVG-Visualisierungen"""

    # Farben
    COLORS = {
        'sky': '#e3f2fd',
        'ground': '#d4c4b0',
        'building': '#e0e0e0',
        'building_stroke': '#333333',
        'roof': '#8b7355',
        'window': '#4a90a4',
        'scaffold': '#fff3cd',
        'scaffold_stroke': '#ffc107',
        'anchor': '#dc3545',
        'dimension': '#0066cc',
        'ridge': '#dc3545',
        'npk_bg': '#e8f5e9',
        'npk_border': '#4caf50',
        'npk_text': '#2e7d32',
        'legend_bg': '#ffffff',
        'legend_border': '#cccccc',
        'text': '#333333',
        'text_light': '#666666',
    }

    def __init__(self):
        pass

    def analyze_polygon(self, polygon: List[Tuple[float, float]]) -> PolygonAnalysis:
        """
        Analysiert ein Gebäude-Polygon und erkennt die Form.

        Gibt zurück:
        - Formtyp (rectangle, L, T, U, H, complex)
        - Konvexität
        - Gebäudesektionen für komplexe Formen
        """
        if not polygon or len(polygon) < 3:
            return PolygonAnalysis()

        # Bounding Box berechnen
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        width = max_x - min_x
        height = max_y - min_y

        if width == 0 or height == 0:
            return PolygonAnalysis()

        aspect_ratio = max(width, height) / min(width, height)

        # Polygon normalisieren (0-1 Bereich)
        normalized = [
            ((p[0] - min_x) / width, (p[1] - min_y) / height)
            for p in polygon
        ]

        # Konvexität berechnen (Fläche Polygon / Fläche konvexe Hülle)
        polygon_area = self._calculate_polygon_area(polygon)
        convex_hull = self._convex_hull(polygon)
        hull_area = self._calculate_polygon_area(convex_hull) if len(convex_hull) >= 3 else polygon_area
        convexity = polygon_area / hull_area if hull_area > 0 else 1.0

        # Formtyp erkennen
        num_vertices = len(polygon)
        shape_type = "rectangle"
        is_complex = False

        if num_vertices == 4 and convexity > 0.95:
            shape_type = "rectangle"
        elif num_vertices <= 6 and convexity > 0.9:
            shape_type = "rectangle"  # Nahezu rechteckig
        elif convexity < 0.7:
            # Stark konkav - wahrscheinlich L, T, U oder H
            is_complex = True
            shape_type = self._detect_shape_type(normalized, convexity, num_vertices)
        elif num_vertices > 6:
            is_complex = True
            shape_type = "complex"

        # Sektionen für komplexe Formen ableiten
        sections = []
        if is_complex:
            sections = self._extract_sections(normalized, shape_type, width, height)

        return PolygonAnalysis(
            is_complex=is_complex,
            shape_type=shape_type,
            num_vertices=num_vertices,
            convexity=convexity,
            bounding_box=(min_x, min_y, max_x, max_y),
            aspect_ratio=aspect_ratio,
            sections=sections,
            normalized_polygon=normalized
        )

    def _detect_shape_type(self, normalized: List[Tuple[float, float]], convexity: float, num_vertices: int) -> str:
        """Erkennt den Formtyp basierend auf dem normalisierten Polygon."""
        # Vereinfachte Heuristik basierend auf Anzahl Ecken und Konvexität
        if num_vertices == 6:
            return "L"  # Typische L-Form hat 6 Ecken
        elif num_vertices == 8:
            # Könnte T, U oder Rechteck mit Einbuchtung sein
            return "T"
        elif num_vertices == 10:
            return "U"
        elif num_vertices >= 12:
            return "H" if convexity < 0.5 else "complex"
        else:
            return "complex"

    def _extract_sections(self, normalized: List[Tuple[float, float]], shape_type: str,
                          real_width: float, real_height: float) -> List[BuildingSection]:
        """Extrahiert Gebäudesektionen aus dem Polygon."""
        sections = []

        # Für einfache Rechtecke: eine Sektion
        if shape_type == "rectangle":
            sections.append(BuildingSection(
                name="Hauptgebäude",
                x=0, y=0,
                width=real_width, height=real_height,
                is_main=True
            ))
            return sections

        # Für L-Form: 2 Sektionen
        if shape_type == "L":
            # Horizontaler Teil
            sections.append(BuildingSection(
                name="Hauptflügel",
                x=0, y=0,
                width=real_width * 0.6, height=real_height * 0.4,
                is_main=True
            ))
            # Vertikaler Teil
            sections.append(BuildingSection(
                name="Seitenflügel",
                x=0, y=real_height * 0.4,
                width=real_width * 0.4, height=real_height * 0.6
            ))
            return sections

        # Für T-Form: 3 Sektionen (wie Bundeshaus)
        if shape_type == "T":
            # Linker Flügel
            sections.append(BuildingSection(
                name="Westflügel",
                x=0, y=real_height * 0.3,
                width=real_width * 0.25, height=real_height * 0.4,
                height_m=25.0
            ))
            # Mittelbau
            sections.append(BuildingSection(
                name="Mittelbau",
                x=real_width * 0.25, y=0,
                width=real_width * 0.5, height=real_height,
                is_main=True,
                height_m=35.0,
                roof_type="dome"  # Sonderfall Kuppel
            ))
            # Rechter Flügel
            sections.append(BuildingSection(
                name="Ostflügel",
                x=real_width * 0.75, y=real_height * 0.3,
                width=real_width * 0.25, height=real_height * 0.4,
                height_m=25.0
            ))
            return sections

        # Für U-Form: 3 Sektionen
        if shape_type == "U":
            sections.append(BuildingSection(
                name="Linker Flügel",
                x=0, y=0,
                width=real_width * 0.3, height=real_height,
            ))
            sections.append(BuildingSection(
                name="Verbindungsbau",
                x=real_width * 0.3, y=real_height * 0.7,
                width=real_width * 0.4, height=real_height * 0.3,
                is_main=True
            ))
            sections.append(BuildingSection(
                name="Rechter Flügel",
                x=real_width * 0.7, y=0,
                width=real_width * 0.3, height=real_height,
            ))
            return sections

        # Fallback: Hauptgebäude
        sections.append(BuildingSection(
            name="Hauptgebäude",
            x=0, y=0,
            width=real_width, height=real_height,
            is_main=True
        ))
        return sections

    def _convex_hull(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Berechnet die konvexe Hülle (Graham Scan vereinfacht)."""
        if len(points) < 3:
            return points

        # Sortieren nach x, dann y
        sorted_points = sorted(points, key=lambda p: (p[0], p[1]))

        # Untere Hülle
        lower = []
        for p in sorted_points:
            while len(lower) >= 2 and self._cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)

        # Obere Hülle
        upper = []
        for p in reversed(sorted_points):
            while len(upper) >= 2 and self._cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)

        return lower[:-1] + upper[:-1]

    def _cross(self, o: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]) -> float:
        """Kreuzprodukt für konvexe Hülle."""
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def _calculate_polygon_area(self, polygon: List[Tuple[float, float]]) -> float:
        """Berechnet die Fläche eines Polygons (Shoelace-Formel)."""
        if len(polygon) < 3:
            return 0
        n = len(polygon)
        area = 0
        for i in range(n):
            j = (i + 1) % n
            area += polygon[i][0] * polygon[j][1]
            area -= polygon[j][0] * polygon[i][1]
        return abs(area) / 2

    def _svg_header(self, width: int, height: int, title: str) -> str:
        """SVG-Header mit Definitionen"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <title>{title}</title>

  <defs>
    <!-- Gebäude Schraffur -->
    <pattern id="building-hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M-2,2 l4,-4 M0,8 l8,-8 M6,10 l4,-4" stroke="#666" stroke-width="0.5" fill="none"/>
    </pattern>

    <!-- Fenster-Muster -->
    <pattern id="windows" patternUnits="userSpaceOnUse" width="20" height="25">
      <rect width="20" height="25" fill="#e8e8e8"/>
      <rect x="3" y="3" width="14" height="18" fill="{self.COLORS['window']}" stroke="#333" stroke-width="0.5"/>
    </pattern>

    <!-- Gerüst Schraffur -->
    <pattern id="scaffold-pattern" patternUnits="userSpaceOnUse" width="8" height="8">
      <rect width="8" height="8" fill="{self.COLORS['scaffold']}"/>
      <line x1="0" y1="8" x2="8" y2="0" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="0.5"/>
      <line x1="0" y1="0" x2="0" y2="8" stroke="#d4a005" stroke-width="0.3"/>
    </pattern>

    <!-- Dach Schraffur -->
    <pattern id="roof-pattern" patternUnits="userSpaceOnUse" width="10" height="10">
      <rect width="10" height="10" fill="{self.COLORS['roof']}"/>
      <line x1="0" y1="5" x2="10" y2="5" stroke="#7a6245" stroke-width="0.5"/>
    </pattern>
  </defs>
'''

    def _svg_footer(self) -> str:
        return '</svg>'

    def _legend(self, x: int, y: int, items: List[dict], width: int = 140) -> str:
        """Generiert Legende"""
        height = 25 + len(items) * 20
        svg = f'''
  <!-- Legende -->
  <g transform="translate({x}, {y})">
    <rect x="0" y="0" width="{width}" height="{height}" fill="{self.COLORS['legend_bg']}" stroke="{self.COLORS['legend_border']}" rx="4"/>
    <text x="10" y="18" font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="{self.COLORS['text']}">Legende</text>
'''
        for i, item in enumerate(items):
            item_y = 30 + i * 20
            if item['type'] == 'rect':
                svg += f'    <rect x="10" y="{item_y}" width="20" height="12" fill="{item["fill"]}" stroke="{item.get("stroke", "#333")}"/>\n'
            elif item['type'] == 'circle':
                svg += f'    <circle cx="20" cy="{item_y + 6}" r="4" fill="{item["fill"]}"/>\n'
            elif item['type'] == 'pattern':
                svg += f'    <rect x="10" y="{item_y}" width="20" height="12" fill="url(#{item["pattern"]})" stroke="{item.get("stroke", "#333")}"/>\n'
            svg += f'    <text x="35" y="{item_y + 10}" font-family="Arial" font-size="9" fill="{self.COLORS["text"]}">{item["label"]}</text>\n'

        svg += '  </g>\n'
        return svg

    def _npk_info_box(self, x: int, y: int, building: BuildingData, ausmass_m2: float) -> str:
        """NPK 114 Info-Box"""
        height_ausmass = building.eave_height_m + 1.0
        return f'''
  <!-- NPK 114 Info -->
  <g transform="translate({x}, {y})">
    <rect x="0" y="0" width="280" height="50" fill="{self.COLORS['npk_bg']}" stroke="{self.COLORS['npk_border']}" rx="4"/>
    <text x="10" y="15" font-family="Arial" font-size="10" font-weight="bold" fill="{self.COLORS['npk_text']}">NPK 114 Ausmass:</text>
    <text x="10" y="30" font-family="Arial" font-size="9" fill="{self.COLORS['text']}">Ausmasshöhe: {building.eave_height_m:.1f}m + 1.0m = {height_ausmass:.1f}m</text>
    <text x="10" y="43" font-family="Arial" font-size="9" fill="{self.COLORS['text']}">Geschosse: {building.floors or '—'} | Breitenklasse: {building.width_class} | Fläche: {ausmass_m2:.0f} m²</text>
  </g>
'''

    def _scale_bar(self, x: int, y: int, scale: float, meters: int = 10) -> str:
        """Massstab"""
        bar_width = meters * scale
        return f'''
  <!-- Massstab -->
  <g transform="translate({x}, {y})">
    <line x1="0" y1="0" x2="{bar_width}" y2="0" stroke="#333" stroke-width="2"/>
    <line x1="0" y1="-5" x2="0" y2="5" stroke="#333" stroke-width="2"/>
    <line x1="{bar_width}" y1="-5" x2="{bar_width}" y2="5" stroke="#333" stroke-width="2"/>
    <text x="{bar_width/2}" y="15" text-anchor="middle" font-family="Arial" font-size="9">{meters} m</text>
  </g>
'''

    def _north_arrow(self, x: int, y: int) -> str:
        """Nordpfeil"""
        return f'''
  <!-- Nordpfeil -->
  <g transform="translate({x}, {y})">
    <polygon points="0,-15 5,5 0,0 -5,5" fill="#333"/>
    <text x="0" y="15" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">N</text>
  </g>
'''

    def generate_cross_section(self, building: BuildingData, width: int = 700, height: int = 480) -> str:
        """
        Generiert Schnittansicht (Querschnitt durch Gebäude).
        Unterstützt komplexe Gebäudeformen mit mehreren Sektionen.
        """
        margin = {'top': 60, 'right': 130, 'bottom': 80, 'left': 60}
        draw_width = width - margin['left'] - margin['right']
        draw_height = height - margin['top'] - margin['bottom']

        # Polygon-Analyse für komplexe Formen
        analysis = None
        has_polygon = building.polygon and len(building.polygon) >= 3
        if has_polygon:
            analysis = self.analyze_polygon(building.polygon)

        # Höhen
        max_height = building.ridge_height_m or building.eave_height_m
        eave_h = building.eave_height_m
        ridge_h = building.ridge_height_m or eave_h

        # Für komplexe Gebäude: höchste Sektion ermitteln
        if analysis and analysis.is_complex and analysis.sections:
            max_section_height = max(s.height_m for s in analysis.sections if s.height_m)
            if max_section_height > max_height:
                max_height = max_section_height
                ridge_h = max_section_height

        # Skalierung
        building_width_with_scaffold = building.width_m + 6
        scale_x = draw_width / building_width_with_scaffold
        scale_y = draw_height / (max_height + 5)
        scale = min(scale_x, scale_y)

        # Positionen
        ground_y = margin['top'] + draw_height
        scaffold_width = 18

        svg = self._svg_header(width, height, f"Gebäudeschnitt - {building.address}")

        # Himmel
        svg += f'  <rect width="{width}" height="{ground_y}" fill="{self.COLORS["sky"]}"/>\n'

        # Boden
        svg += f'  <rect x="0" y="{ground_y}" width="{width}" height="{height - ground_y}" fill="{self.COLORS["ground"]}"/>\n'

        # Titel
        shape_info = f" ({analysis.shape_type})" if analysis and analysis.is_complex else ""
        svg += f'''
  <text x="{width/2}" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="{self.COLORS['text']}">
    Gebäudeschnitt mit Gerüstposition{shape_info}
  </text>
  <text x="{width/2}" y="42" text-anchor="middle" font-family="Arial" font-size="11" fill="{self.COLORS['text_light']}">
    {building.address}
  </text>
'''

        # Höhenraster mit mehr Stufen für hohe Gebäude
        grid_step = 5 if max_height < 30 else 10
        grid_heights = [h for h in range(grid_step, int(max_height) + grid_step, grid_step)]
        for h in grid_heights:
            y_pos = ground_y - h * scale
            if y_pos > margin['top']:
                svg += f'  <line x1="{margin["left"]}" y1="{y_pos}" x2="{width - margin["right"]}" y2="{y_pos}" stroke="#ddd" stroke-width="0.5" stroke-dasharray="4,4"/>\n'
                svg += f'  <text x="{margin["left"] - 8}" y="{y_pos + 3}" text-anchor="end" font-family="Arial" font-size="9" fill="#999">{h}m</text>\n'

        # Bodenlinie
        svg += f'  <line x1="{margin["left"] - 20}" y1="{ground_y}" x2="{width - margin["right"] + 20}" y2="{ground_y}" stroke="#333" stroke-width="2"/>\n'

        # Gebäude zeichnen - je nach Komplexität
        if analysis and analysis.is_complex and analysis.sections:
            svg += self._draw_complex_cross_section(
                building, analysis, scale, ground_y, margin, width, height, scaffold_width
            )
        else:
            svg += self._draw_simple_cross_section(
                building, scale, ground_y, margin, width, height, scaffold_width, draw_width, eave_h, ridge_h
            )

        # Legende
        legend_items = [
            {'type': 'pattern', 'pattern': 'scaffold-pattern', 'stroke': self.COLORS['scaffold_stroke'], 'label': 'Fassadengerüst'},
            {'type': 'circle', 'fill': self.COLORS['anchor'], 'label': 'Verankerung'},
            {'type': 'pattern', 'pattern': 'roof-pattern', 'stroke': '#333', 'label': 'Dach'},
        ]
        svg += self._legend(width - 155, 55, legend_items)

        # NPK 114 Info
        ausmass_m2 = (building.width_m + 2) * (building.eave_height_m + 1) * 2
        svg += self._npk_info_box(margin['left'], height - 65, building, ausmass_m2)

        # Massstab
        svg += self._scale_bar(width - 140, height - 35, scale, 10)

        svg += self._svg_footer()
        return svg

    def _draw_complex_cross_section(self, building: BuildingData, analysis: PolygonAnalysis,
                                     scale: float, ground_y: float, margin: dict,
                                     width: int, height: int, scaffold_width: float) -> str:
        """Zeichnet komplexen Gebäudeschnitt mit mehreren Sektionen."""
        svg = ""
        sections = analysis.sections
        min_x, min_y, max_x, max_y = analysis.bounding_box
        total_width = max_x - min_x

        # Gebäude zentrieren
        draw_width = width - margin['left'] - margin['right']
        building_start_x = margin['left'] + (draw_width - total_width * scale) / 2

        # Höchste Höhe ermitteln
        max_h = max(s.height_m for s in sections if s.height_m)

        # Jede Sektion zeichnen
        for section in sections:
            sec_x = building_start_x + section.x * scale
            sec_w = section.width * scale
            sec_h = (section.height_m or building.eave_height_m) * scale

            # Gebäudeteil
            svg += f'''
  <!-- {section.name} -->
  <rect x="{sec_x}" y="{ground_y - sec_h}" width="{sec_w}" height="{sec_h}"
        fill="{self.COLORS['building']}" stroke="{self.COLORS['building_stroke']}" stroke-width="1.5"/>
'''
            # Fenster
            if sec_w > 30 and sec_h > 30:
                svg += f'  <rect x="{sec_x + 10}" y="{ground_y - sec_h + 10}" width="{sec_w - 20}" height="{sec_h - 20}" fill="url(#windows)"/>\n'

            # Dach (Flachdach für Sektionen)
            svg += f'  <rect x="{sec_x - 2}" y="{ground_y - sec_h - 5}" width="{sec_w + 4}" height="5" fill="#999" stroke="{self.COLORS["building_stroke"]}"/>\n'

            # Beschriftung
            svg += f'  <text x="{sec_x + sec_w/2}" y="{ground_y - sec_h/2}" text-anchor="middle" font-family="Arial" font-size="9" fill="{self.COLORS["text"]}">{section.name}</text>\n'
            svg += f'  <text x="{sec_x + sec_w/2}" y="{ground_y - sec_h/2 + 12}" text-anchor="middle" font-family="Arial" font-size="8" fill="#666">H: {section.height_m:.0f}m</text>\n'

            # Höhenmarkierung für diese Sektion
            svg += f'  <line x1="{sec_x + sec_w + 5}" y1="{ground_y - sec_h}" x2="{width - margin["right"] + 35}" y2="{ground_y - sec_h}" stroke="{self.COLORS["dimension"]}" stroke-width="0.5" stroke-dasharray="2,2"/>\n'

        # Gerüst an den Aussenkanten
        leftmost_x = building_start_x
        rightmost_x = building_start_x + total_width * scale
        max_scaffold_h = max_h * scale + 30

        # Linkes Gerüst
        scaffold_left_x = leftmost_x - scaffold_width - 12
        svg += f'''
  <!-- Linkes Gerüst -->
  <rect x="{scaffold_left_x}" y="{ground_y - max_scaffold_h}" width="{scaffold_width}" height="{max_scaffold_h}"
        fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
'''
        for ratio in [0.25, 0.5, 0.75]:
            cy = ground_y - max_h * scale * ratio
            svg += f'  <circle cx="{scaffold_left_x + scaffold_width/2}" cy="{cy}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Rechtes Gerüst
        scaffold_right_x = rightmost_x + 12
        svg += f'''
  <!-- Rechtes Gerüst -->
  <rect x="{scaffold_right_x}" y="{ground_y - max_scaffold_h}" width="{scaffold_width}" height="{max_scaffold_h}"
        fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
'''
        for ratio in [0.25, 0.5, 0.75]:
            cy = ground_y - max_h * scale * ratio
            svg += f'  <circle cx="{scaffold_right_x + scaffold_width/2}" cy="{cy}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Höhenkoten rechts
        svg += f'''
  <!-- Höhenkoten -->
  <g font-family="Arial" font-size="9">
    <line x1="{width - margin['right'] + 10}" y1="{ground_y}" x2="{width - margin['right'] + 35}" y2="{ground_y}" stroke="#333" stroke-width="0.5"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y + 3}" fill="#333">±0.00 m</text>
'''
        # Höhenmarkierungen für jede eindeutige Höhe
        unique_heights = sorted(set(s.height_m for s in sections if s.height_m), reverse=True)
        for i, h in enumerate(unique_heights[:3]):  # Max 3 Höhen anzeigen
            y_pos = ground_y - h * scale
            color = self.COLORS['ridge'] if i == 0 else self.COLORS['dimension']
            label = "First" if i == 0 else "Traufe"
            svg += f'''
    <text x="{width - margin['right'] + 40}" y="{y_pos + 3}" fill="{color}" {"font-weight='bold'" if i == 0 else ""}>{label} {h:.1f}m</text>
'''
        svg += '  </g>\n'

        # Breitenmass
        svg += f'''
  <!-- Breitenmass -->
  <g>
    <line x1="{leftmost_x}" y1="{ground_y + 25}" x2="{rightmost_x}" y2="{ground_y + 25}" stroke="#333" stroke-width="1"/>
    <line x1="{leftmost_x}" y1="{ground_y + 18}" x2="{leftmost_x}" y2="{ground_y + 32}" stroke="#333" stroke-width="1"/>
    <line x1="{rightmost_x}" y1="{ground_y + 18}" x2="{rightmost_x}" y2="{ground_y + 32}" stroke="#333" stroke-width="1"/>
    <text x="{(leftmost_x + rightmost_x)/2}" y="{ground_y + 45}" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold">{total_width:.1f} m</text>
  </g>
'''

        return svg

    def _draw_simple_cross_section(self, building: BuildingData, scale: float, ground_y: float,
                                    margin: dict, width: int, height: int, scaffold_width: float,
                                    draw_width: float, eave_h: float, ridge_h: float) -> str:
        """Zeichnet professionellen Gebäudeschnitt im Showcase-Stil."""
        svg = ""

        building_x = margin['left'] + (draw_width - building.width_m * scale) / 2
        building_width_px = building.width_m * scale
        eave_height_px = eave_h * scale
        ridge_height_px = ridge_h * scale

        floors = building.floors if building.floors and building.floors > 0 else 3
        floor_height_m = eave_h / floors

        # Linkes Gerüst
        scaffold_left_x = building_x - scaffold_width - 15
        scaffold_height_px = ridge_height_px + 15
        svg += f'''
  <!-- Linkes Gerüst -->
  <rect x="{scaffold_left_x}" y="{ground_y - scaffold_height_px}" width="{scaffold_width}" height="{scaffold_height_px}" fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
  <text x="{scaffold_left_x + scaffold_width/2}" y="{ground_y - scaffold_height_px/2}" text-anchor="middle" font-family="Arial" font-size="8" fill="#996600" transform="rotate(-90, {scaffold_left_x + scaffold_width/2}, {ground_y - scaffold_height_px/2})">Gerüst {building.width_class}</text>
'''
        # Verankerungen mit echten Geschosshöhen
        for i in range(1, floors + 1):
            anchor_h = i * floor_height_m
            if anchor_h < eave_h:
                cy = ground_y - anchor_h * scale
                svg += f'  <circle cx="{scaffold_left_x + scaffold_width/2}" cy="{cy}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Gebäudekörper mit Schraffur
        svg += f'''
  <!-- Gebäude -->
  <rect x="{building_x}" y="{ground_y - eave_height_px}" width="{building_width_px}" height="{eave_height_px}" fill="url(#building-hatch)" stroke="{self.COLORS['building_stroke']}" stroke-width="1.5"/>
'''

        # Fensterbänder pro Geschoss
        window_margin = 20
        window_height = (eave_height_px - 20) / floors * 0.6
        for i in range(floors):
            window_y = ground_y - (i + 1) * (eave_height_px / floors) + window_margin / 2
            svg += f'  <rect x="{building_x + window_margin}" y="{window_y}" width="{building_width_px - 2*window_margin}" height="{window_height}" fill="url(#windows)"/>\n'

        # Geschosslinien
        for i in range(1, floors):
            y_floor = ground_y - (eave_height_px / floors) * i
            svg += f'  <line x1="{building_x}" y1="{y_floor}" x2="{building_x + building_width_px}" y2="{y_floor}" stroke="#666" stroke-width="1" stroke-dasharray="5,3"/>\n'

        # Dach mit realistischer Form
        if building.roof_type == 'gable' and ridge_h > eave_h:
            roof_overhang = 8  # Dachüberstand
            svg += f'''
  <!-- Dach (Satteldach) -->
  <polygon points="{building_x - roof_overhang},{ground_y - eave_height_px} {building_x + building_width_px/2},{ground_y - ridge_height_px} {building_x + building_width_px + roof_overhang},{ground_y - eave_height_px}" fill="url(#roof-pattern)" stroke="{self.COLORS['building_stroke']}" stroke-width="1.5"/>
  <!-- Dachstuhl angedeutet -->
  <line x1="{building_x + building_width_px*0.3}" y1="{ground_y - eave_height_px}" x2="{building_x + building_width_px/2}" y2="{ground_y - ridge_height_px*0.95}" stroke="#666" stroke-width="0.5"/>
  <line x1="{building_x + building_width_px*0.7}" y1="{ground_y - eave_height_px}" x2="{building_x + building_width_px/2}" y2="{ground_y - ridge_height_px*0.95}" stroke="#666" stroke-width="0.5"/>
'''
        elif building.roof_type == 'flat':
            svg += f'''
  <!-- Flachdach mit Attika -->
  <rect x="{building_x - 3}" y="{ground_y - eave_height_px - 10}" width="{building_width_px + 6}" height="10" fill="#888" stroke="{self.COLORS['building_stroke']}"/>
'''

        # Rechtes Gerüst
        scaffold_right_x = building_x + building_width_px + 15
        svg += f'''
  <!-- Rechtes Gerüst -->
  <rect x="{scaffold_right_x}" y="{ground_y - scaffold_height_px}" width="{scaffold_width}" height="{scaffold_height_px}" fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
'''
        for i in range(1, floors + 1):
            anchor_h = i * floor_height_m
            if anchor_h < eave_h:
                cy = ground_y - anchor_h * scale
                svg += f'  <circle cx="{scaffold_right_x + scaffold_width/2}" cy="{cy}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Höhenkoten mit durchgehenden gestrichelten Linien
        kote_start_x = scaffold_left_x - 10
        kote_end_x = width - margin['right'] + 35
        svg += f'''
  <!-- Höhenkoten -->
  <g font-family="Arial" font-size="9">
    <!-- Bodenlinie -->
    <line x1="{kote_start_x}" y1="{ground_y}" x2="{kote_end_x}" y2="{ground_y}" stroke="#333" stroke-width="0.5"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y + 3}" fill="#333">±0.00 m</text>

    <!-- Traufhöhe -->
    <line x1="{kote_start_x}" y1="{ground_y - eave_height_px}" x2="{kote_end_x}" y2="{ground_y - eave_height_px}" stroke="{self.COLORS['dimension']}" stroke-width="0.5" stroke-dasharray="4,4"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y - eave_height_px + 3}" fill="{self.COLORS['dimension']}">Traufe +{eave_h:.1f} m</text>
'''
        if ridge_h > eave_h:
            svg += f'''
    <!-- Firsthöhe -->
    <line x1="{kote_start_x}" y1="{ground_y - ridge_height_px}" x2="{kote_end_x}" y2="{ground_y - ridge_height_px}" stroke="{self.COLORS['ridge']}" stroke-width="0.5" stroke-dasharray="4,4"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y - ridge_height_px + 3}" fill="{self.COLORS['ridge']}" font-weight="bold">First +{ridge_h:.1f} m</text>
'''
        # Geschosshöhen anzeigen
        for i in range(1, min(floors, 4)):  # Max 3 Geschosse beschriften
            h = i * floor_height_m
            y_pos = ground_y - h * scale
            svg += f'    <text x="{margin["left"] - 25}" y="{y_pos + 3}" text-anchor="end" fill="#999" font-size="8">+{h:.1f}m</text>\n'

        svg += '  </g>\n'

        # Breitenmass mit Pfeilen
        dim_y = ground_y + 30
        svg += f'''
  <!-- Breitenmass -->
  <g stroke="#333" stroke-width="1">
    <line x1="{building_x}" y1="{dim_y}" x2="{building_x + building_width_px}" y2="{dim_y}"/>
    <line x1="{building_x}" y1="{dim_y - 8}" x2="{building_x}" y2="{dim_y + 8}"/>
    <line x1="{building_x + building_width_px}" y1="{dim_y - 8}" x2="{building_x + building_width_px}" y2="{dim_y + 8}"/>
    <!-- Pfeile -->
    <polygon points="{building_x},{dim_y} {building_x + 8},{dim_y - 3} {building_x + 8},{dim_y + 3}" fill="#333"/>
    <polygon points="{building_x + building_width_px},{dim_y} {building_x + building_width_px - 8},{dim_y - 3} {building_x + building_width_px - 8},{dim_y + 3}" fill="#333"/>
  </g>
  <text x="{building_x + building_width_px/2}" y="{dim_y + 18}" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold">{building.width_m:.1f} m</text>
'''

        # Gebäudelabel
        svg += f'''
  <text x="{building_x + building_width_px/2}" y="{ground_y - eave_height_px/2}" text-anchor="middle" font-family="Arial" font-size="10" fill="{self.COLORS['text_light']}">{floors} Geschosse</text>
'''

        return svg

    def generate_elevation(self, building: BuildingData, width: int = 700, height: int = 480) -> str:
        """
        Generiert professionelle Fassadenansicht im Showcase-Stil.
        """
        margin = {'top': 60, 'right': 130, 'bottom': 80, 'left': 60}
        draw_width = width - margin['left'] - margin['right']
        draw_height = height - margin['top'] - margin['bottom']

        # Höhen
        max_height = building.ridge_height_m or building.eave_height_m
        eave_h = building.eave_height_m
        ridge_h = building.ridge_height_m or eave_h

        # Skalierung
        scale_x = draw_width / (building.length_m + 6)
        scale_y = draw_height / (max_height + 5)
        scale = min(scale_x, scale_y)

        # Positionen
        ground_y = margin['top'] + draw_height
        building_x = margin['left'] + (draw_width - building.length_m * scale) / 2
        building_width_px = building.length_m * scale
        eave_height_px = eave_h * scale
        ridge_height_px = ridge_h * scale

        floors = building.floors if building.floors and building.floors > 0 else 3
        floor_height_m = eave_h / floors

        svg = self._svg_header(width, height, f"Fassadenansicht - {building.address}")

        # Himmel
        svg += f'  <rect width="{width}" height="{ground_y}" fill="{self.COLORS["sky"]}"/>\n'

        # Boden mit Beschriftung
        svg += f'''
  <rect x="0" y="{ground_y}" width="{width}" height="{height - ground_y}" fill="{self.COLORS["ground"]}"/>
  <text x="{width/2}" y="{ground_y + 15}" text-anchor="middle" font-family="Arial" font-size="10" fill="#666">Terrain</text>
'''

        # Titel
        svg += f'''
  <text x="{width/2}" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="{self.COLORS['text']}">
    Fassadenansicht (Traufseite)
  </text>
  <text x="{width/2}" y="42" text-anchor="middle" font-family="Arial" font-size="11" fill="{self.COLORS['text_light']}">
    {building.address}
  </text>
'''

        # Bodenlinie
        svg += f'  <line x1="{margin["left"] - 30}" y1="{ground_y}" x2="{width - margin["right"] + 30}" y2="{ground_y}" stroke="#333" stroke-width="2"/>\n'

        # Gebäudekörper
        svg += f'''
  <!-- Gebäude -->
  <rect x="{building_x}" y="{ground_y - eave_height_px}" width="{building_width_px}" height="{eave_height_px}" fill="{self.COLORS['building']}" stroke="{self.COLORS['building_stroke']}" stroke-width="1.5"/>
'''

        # Fenster pro Geschoss
        window_cols = max(3, int(building.length_m / 4))  # Ca. alle 4m ein Fenster
        window_w = (building_width_px - 40) / window_cols * 0.6
        window_spacing = (building_width_px - 40) / window_cols
        window_h = (eave_height_px / floors) * 0.5

        for floor in range(floors):
            floor_y = ground_y - (floor + 1) * (eave_height_px / floors) + 15
            for col in range(window_cols):
                wx = building_x + 20 + col * window_spacing + (window_spacing - window_w) / 2
                svg += f'  <rect x="{wx}" y="{floor_y}" width="{window_w}" height="{window_h}" fill="#4a90a4" stroke="#333" stroke-width="0.5"/>\n'

        # Eingang (Erdgeschoss Mitte)
        door_w = min(40, building_width_px * 0.15)
        door_h = min(eave_height_px / floors * 0.8, 60)
        door_x = building_x + building_width_px / 2 - door_w / 2
        svg += f'''
  <!-- Eingang -->
  <rect x="{door_x}" y="{ground_y - door_h}" width="{door_w}" height="{door_h}" fill="#5d4037" stroke="#333" stroke-width="1.5"/>
  <text x="{door_x + door_w/2}" y="{ground_y - door_h/2}" text-anchor="middle" font-family="Arial" font-size="7" fill="#fff">Eingang</text>
'''

        # Geschosslinien
        for i in range(1, floors):
            y_floor = ground_y - (eave_height_px / floors) * i
            svg += f'  <line x1="{building_x}" y1="{y_floor}" x2="{building_x + building_width_px}" y2="{y_floor}" stroke="#999" stroke-width="0.5" stroke-dasharray="5,5"/>\n'

        # Dach
        roof_overhang = 12
        if building.roof_type == 'gable' and ridge_h > eave_h:
            svg += f'''
  <!-- Dach (Satteldach) -->
  <polygon points="{building_x - roof_overhang},{ground_y - eave_height_px} {building_x + building_width_px/2},{ground_y - ridge_height_px} {building_x + building_width_px + roof_overhang},{ground_y - eave_height_px}" fill="url(#roof-pattern)" stroke="{self.COLORS['building_stroke']}" stroke-width="1.5"/>
'''
        elif building.roof_type == 'flat':
            svg += f'''
  <!-- Flachdach mit Attika -->
  <rect x="{building_x - 5}" y="{ground_y - eave_height_px - 10}" width="{building_width_px + 10}" height="10" fill="#888" stroke="{self.COLORS['building_stroke']}"/>
'''

        # Gerüst (vor Fassade)
        scaffold_width = 18
        scaffold_height_px = ridge_height_px + 20
        scaffold_left_x = building_x - scaffold_width - 10
        scaffold_right_x = building_x + building_width_px + 10

        svg += f'''
  <!-- Gerüst links -->
  <rect x="{scaffold_left_x}" y="{ground_y - scaffold_height_px}" width="{scaffold_width}" height="{scaffold_height_px}" fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
  <text x="{scaffold_left_x + scaffold_width/2}" y="{ground_y - scaffold_height_px/2}" text-anchor="middle" font-family="Arial" font-size="8" fill="#996600" transform="rotate(-90, {scaffold_left_x + scaffold_width/2}, {ground_y - scaffold_height_px/2})">Gerüst {building.width_class}</text>

  <!-- Gerüst rechts -->
  <rect x="{scaffold_right_x}" y="{ground_y - scaffold_height_px}" width="{scaffold_width}" height="{scaffold_height_px}" fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
'''

        # Verankerungen mit echten Geschosshöhen
        for i in range(1, floors + 1):
            anchor_h = i * floor_height_m
            if anchor_h < eave_h:
                cy = ground_y - anchor_h * scale
                svg += f'  <circle cx="{scaffold_left_x + scaffold_width/2}" cy="{cy}" r="4" fill="{self.COLORS["anchor"]}"/>\n'
                svg += f'  <circle cx="{scaffold_right_x + scaffold_width/2}" cy="{cy}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Höhenkoten mit durchgehenden Linien
        kote_start_x = scaffold_left_x - 15
        kote_end_x = width - margin['right'] + 35
        svg += f'''
  <!-- Höhenkoten -->
  <g font-family="Arial" font-size="9">
    <!-- Bodenlinie -->
    <line x1="{kote_start_x}" y1="{ground_y}" x2="{kote_end_x}" y2="{ground_y}" stroke="#333" stroke-width="0.5"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y + 3}" fill="#333">±0.00 m</text>

    <!-- Traufhöhe -->
    <line x1="{kote_start_x}" y1="{ground_y - eave_height_px}" x2="{kote_end_x}" y2="{ground_y - eave_height_px}" stroke="{self.COLORS['dimension']}" stroke-width="0.5" stroke-dasharray="4,4"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y - eave_height_px + 3}" fill="{self.COLORS['dimension']}">Traufe +{eave_h:.1f} m</text>
'''
        if ridge_h > eave_h:
            svg += f'''
    <!-- Firsthöhe -->
    <line x1="{kote_start_x}" y1="{ground_y - ridge_height_px}" x2="{kote_end_x}" y2="{ground_y - ridge_height_px}" stroke="{self.COLORS['ridge']}" stroke-width="0.5" stroke-dasharray="4,4"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y - ridge_height_px + 3}" fill="{self.COLORS['ridge']}" font-weight="bold">First +{ridge_h:.1f} m</text>
'''
        svg += '  </g>\n'

        # Längenmass mit Pfeilen
        dim_y = ground_y + 30
        svg += f'''
  <!-- Längenmass -->
  <g stroke="#333" stroke-width="1">
    <line x1="{building_x}" y1="{dim_y}" x2="{building_x + building_width_px}" y2="{dim_y}"/>
    <line x1="{building_x}" y1="{dim_y - 8}" x2="{building_x}" y2="{dim_y + 8}"/>
    <line x1="{building_x + building_width_px}" y1="{dim_y - 8}" x2="{building_x + building_width_px}" y2="{dim_y + 8}"/>
    <polygon points="{building_x},{dim_y} {building_x + 8},{dim_y - 3} {building_x + 8},{dim_y + 3}" fill="#333"/>
    <polygon points="{building_x + building_width_px},{dim_y} {building_x + building_width_px - 8},{dim_y - 3} {building_x + building_width_px - 8},{dim_y + 3}" fill="#333"/>
  </g>
  <text x="{building_x + building_width_px/2}" y="{dim_y + 18}" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold">{building.length_m:.1f} m (Traufseite)</text>
'''

        # Legende
        legend_items = [
            {'type': 'pattern', 'pattern': 'scaffold-pattern', 'stroke': self.COLORS['scaffold_stroke'], 'label': 'Fassadengerüst'},
            {'type': 'circle', 'fill': self.COLORS['anchor'], 'label': 'Verankerung'},
            {'type': 'pattern', 'pattern': 'roof-pattern', 'stroke': '#333', 'label': 'Dach'},
        ]
        svg += self._legend(width - 155, 55, legend_items)

        # NPK 114 Info
        ausmass_m2 = (building.length_m + 2) * (building.eave_height_m + 1)
        svg += self._npk_info_box(margin['left'], height - 65, building, ausmass_m2)

        # Massstab
        svg += self._scale_bar(width - 140, height - 35, scale, 10)

        svg += self._svg_footer()
        return svg

    def generate_floor_plan(self, building: BuildingData, width: int = 600, height: int = 500) -> str:
        """
        Generiert Grundriss mit Gerüstposition.
        Unterstützt sowohl Rechtecke als auch echte Polygon-Formen.
        """
        margin = {'top': 60, 'right': 160, 'bottom': 80, 'left': 50}
        draw_width = width - margin['left'] - margin['right']
        draw_height = height - margin['top'] - margin['bottom']

        # Polygon-Analyse falls vorhanden
        analysis = None
        has_polygon = building.polygon and len(building.polygon) >= 3
        if has_polygon:
            analysis = self.analyze_polygon(building.polygon)

        # Skalierung berechnen
        if has_polygon and analysis:
            min_x, min_y, max_x, max_y = analysis.bounding_box
            poly_width = max_x - min_x
            poly_height = max_y - min_y
        else:
            poly_width = building.length_m
            poly_height = building.width_m

        building_with_scaffold = max(poly_width, poly_height) + 6
        scale = min(draw_width, draw_height) / building_with_scaffold * 0.85

        # Zentrieren
        center_x = margin['left'] + draw_width / 2
        center_y = margin['top'] + draw_height / 2

        svg = self._svg_header(width, height, f"Grundriss - {building.address}")

        # Hintergrund
        svg += f'  <rect width="{width}" height="{height}" fill="#f8f9fa"/>\n'

        # Titel
        shape_info = f" ({analysis.shape_type})" if analysis and analysis.is_complex else ""
        svg += f'''
  <text x="{width/2}" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="{self.COLORS['text']}">
    Grundriss mit Gerüstposition{shape_info}
  </text>
  <text x="{width/2}" y="42" text-anchor="middle" font-family="Arial" font-size="11" fill="{self.COLORS['text_light']}">
    {building.address}{f' | EGID: {building.egid}' if building.egid else ''}
  </text>
'''

        # Gebäude zeichnen - je nach Polygon-Verfügbarkeit
        if has_polygon and analysis:
            svg += self._draw_polygon_floor_plan(
                building, analysis, scale, center_x, center_y, width, height
            )
        else:
            svg += self._draw_rectangle_floor_plan(
                building, scale, center_x, center_y, width, height, margin
            )

        # Legende
        legend_items = [
            {'type': 'pattern', 'pattern': 'building-hatch', 'stroke': '#333', 'label': 'Gebäude'},
            {'type': 'pattern', 'pattern': 'scaffold-pattern', 'stroke': self.COLORS['scaffold_stroke'], 'label': f'Gerüst {building.width_class}'},
            {'type': 'circle', 'fill': self.COLORS['anchor'], 'label': 'Verankerung'},
        ]
        svg += self._legend(width - 155, 55, legend_items)

        # NPK 114 Info
        area = building.area_m2 or (building.length_m * building.width_m)
        perimeter = 2 * (building.length_m + building.width_m)
        ausmass_m2 = (perimeter + 8) * (building.eave_height_m + 1)  # +8 für Ecken
        svg += self._npk_info_box(margin['left'], height - 65, building, ausmass_m2)

        # Massstab
        svg += self._scale_bar(30, height - 35, scale, 10)

        # Nordpfeil
        svg += self._north_arrow(width - 40, height - 50)

        # Koordinaten-Info
        svg += f'''
  <text x="{width/2}" y="{height - 10}" text-anchor="middle" font-family="Arial" font-size="9" fill="{self.COLORS['text_light']}">
    LV95 (EPSG:2056){f' | EGID: {building.egid}' if building.egid else ''} | Fläche: {area:.0f} m²
  </text>
'''

        svg += self._svg_footer()
        return svg

    def _draw_polygon_floor_plan(self, building: BuildingData, analysis: PolygonAnalysis,
                                  scale: float, center_x: float, center_y: float,
                                  width: int, height: int) -> str:
        """Zeichnet echten Polygon-Grundriss mit Gerüst."""
        svg = ""
        polygon = building.polygon

        # Bounding Box für Zentrierung
        min_x, min_y, max_x, max_y = analysis.bounding_box
        poly_width = max_x - min_x
        poly_height = max_y - min_y

        # Offset für Zentrierung
        offset_x = center_x - (poly_width * scale) / 2
        offset_y = center_y - (poly_height * scale) / 2

        # Polygon-Punkte transformieren (Y invertieren für SVG)
        def transform_point(p):
            x = (p[0] - min_x) * scale + offset_x
            y = (max_y - p[1]) * scale + offset_y  # Y invertieren
            return (x, y)

        transformed = [transform_point(p) for p in polygon]
        points_str = " ".join([f"{p[0]:.1f},{p[1]:.1f}" for p in transformed])

        # Gerüst-Offset (außen um Polygon)
        scaffold_offset = 1.5 * scale
        scaffold_width = 1.0 * scale

        # Vereinfachtes Gerüst als erweiterte Bounding-Box
        bbox_x = offset_x - scaffold_offset - scaffold_width
        bbox_y = offset_y - scaffold_offset - scaffold_width
        bbox_w = poly_width * scale + 2 * (scaffold_offset + scaffold_width)
        bbox_h = poly_height * scale + 2 * (scaffold_offset + scaffold_width)

        svg += f'''
  <!-- Gerüst (Bounding) -->
  <rect x="{bbox_x}" y="{bbox_y}" width="{bbox_w}" height="{bbox_h}"
        fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="1.5" rx="2"/>
'''

        # Hintergrund-Ausschnitt (etwas größer als Gebäude)
        inner_x = offset_x - scaffold_offset
        inner_y = offset_y - scaffold_offset
        inner_w = poly_width * scale + 2 * scaffold_offset
        inner_h = poly_height * scale + 2 * scaffold_offset
        svg += f'''
  <rect x="{inner_x}" y="{inner_y}" width="{inner_w}" height="{inner_h}" fill="#f8f9fa"/>
'''

        # Gebäude-Polygon
        svg += f'''
  <!-- Gebäude (echtes Polygon mit {analysis.num_vertices} Ecken) -->
  <polygon points="{points_str}" fill="url(#building-hatch)" stroke="{self.COLORS['building_stroke']}" stroke-width="2"/>
'''

        # Sektionen beschriften (bei komplexen Formen)
        if analysis.is_complex and analysis.sections:
            svg += "  <!-- Sektionen -->\n"
            for section in analysis.sections:
                # Sektion-Position transformieren
                sec_x = section.x * scale + offset_x + section.width * scale / 2
                sec_y = (poly_height - section.y - section.height / 2) * scale + offset_y
                svg += f'  <text x="{sec_x:.1f}" y="{sec_y:.1f}" text-anchor="middle" font-family="Arial" font-size="9" fill="{self.COLORS["text_light"]}">{section.name}</text>\n'
                if section.height_m:
                    svg += f'  <text x="{sec_x:.1f}" y="{sec_y + 12:.1f}" text-anchor="middle" font-family="Arial" font-size="8" fill="#666">H: {section.height_m:.0f}m</text>\n'

        # Verankerungspunkte an Polygon-Ecken
        svg += "  <!-- Verankerungspunkte -->\n"
        for p in transformed:
            # Offset nach außen für Gerüst-Position
            svg += f'  <circle cx="{p[0]}" cy="{p[1]}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Masse
        dim_offset = scaffold_offset + scaffold_width + 25
        svg += f'''
  <!-- Masse -->
  <g stroke="#333" stroke-width="0.5">
    <!-- Breite -->
    <line x1="{offset_x}" y1="{offset_y + poly_height * scale + dim_offset}" x2="{offset_x + poly_width * scale}" y2="{offset_y + poly_height * scale + dim_offset}"/>
    <line x1="{offset_x}" y1="{offset_y + poly_height * scale + dim_offset - 5}" x2="{offset_x}" y2="{offset_y + poly_height * scale + dim_offset + 5}"/>
    <line x1="{offset_x + poly_width * scale}" y1="{offset_y + poly_height * scale + dim_offset - 5}" x2="{offset_x + poly_width * scale}" y2="{offset_y + poly_height * scale + dim_offset + 5}"/>
    <!-- Tiefe -->
    <line x1="{offset_x + poly_width * scale + dim_offset}" y1="{offset_y}" x2="{offset_x + poly_width * scale + dim_offset}" y2="{offset_y + poly_height * scale}"/>
    <line x1="{offset_x + poly_width * scale + dim_offset - 5}" y1="{offset_y}" x2="{offset_x + poly_width * scale + dim_offset + 5}" y2="{offset_y}"/>
    <line x1="{offset_x + poly_width * scale + dim_offset - 5}" y1="{offset_y + poly_height * scale}" x2="{offset_x + poly_width * scale + dim_offset + 5}" y2="{offset_y + poly_height * scale}"/>
  </g>
  <text x="{center_x}" y="{offset_y + poly_height * scale + dim_offset + 15}" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">{poly_width:.1f} m</text>
  <text x="{offset_x + poly_width * scale + dim_offset + 15}" y="{center_y}" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" transform="rotate(90, {offset_x + poly_width * scale + dim_offset + 15}, {center_y})">{poly_height:.1f} m</text>
'''

        # Fläche im Zentrum
        area = building.area_m2 or self._calculate_polygon_area(polygon)
        svg += f'''
  <text x="{center_x}" y="{center_y}" text-anchor="middle" font-family="Arial" font-size="11" fill="{self.COLORS['text_light']}">{area:.0f} m²</text>
'''

        return svg

    def _draw_rectangle_floor_plan(self, building: BuildingData, scale: float,
                                    center_x: float, center_y: float,
                                    width: int, height: int, margin: dict) -> str:
        """Zeichnet rechteckigen Grundriss (Fallback)."""
        svg = ""

        building_width_px = building.length_m * scale
        building_height_px = building.width_m * scale
        building_x = center_x - building_width_px / 2
        building_y = center_y - building_height_px / 2

        scaffold_offset = 1.0 * scale
        scaffold_width = 0.9 * scale

        # Gerüst (umlaufend)
        svg += f'''
  <!-- Gerüst umlaufend -->
  <rect x="{building_x - scaffold_offset - scaffold_width}" y="{building_y - scaffold_offset - scaffold_width}"
        width="{building_width_px + 2*scaffold_offset + 2*scaffold_width}" height="{building_height_px + 2*scaffold_offset + 2*scaffold_width}"
        fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="1.5" rx="2"/>
'''

        # Innerer Ausschnitt
        svg += f'''
  <rect x="{building_x - scaffold_offset}" y="{building_y - scaffold_offset}"
        width="{building_width_px + 2*scaffold_offset}" height="{building_height_px + 2*scaffold_offset}"
        fill="#f8f9fa"/>
'''

        # Gebäude
        svg += f'''
  <!-- Gebäude -->
  <rect x="{building_x}" y="{building_y}" width="{building_width_px}" height="{building_height_px}"
        fill="url(#building-hatch)" stroke="{self.COLORS['building_stroke']}" stroke-width="2"/>
'''

        # Fassaden-Beschriftungen
        svg += f'''
  <!-- Fassaden-Beschriftungen -->
  <text x="{center_x}" y="{building_y - scaffold_offset - scaffold_width - 8}" text-anchor="middle" font-family="Arial" font-size="9" fill="{self.COLORS['text_light']}">Nord ({building.length_m:.1f}m)</text>
  <text x="{center_x}" y="{building_y + building_height_px + scaffold_offset + scaffold_width + 15}" text-anchor="middle" font-family="Arial" font-size="9" fill="{self.COLORS['text_light']}">Süd ({building.length_m:.1f}m)</text>
  <text x="{building_x - scaffold_offset - scaffold_width - 8}" y="{center_y}" text-anchor="middle" font-family="Arial" font-size="9" fill="{self.COLORS['text_light']}" transform="rotate(-90, {building_x - scaffold_offset - scaffold_width - 8}, {center_y})">West ({building.width_m:.1f}m)</text>
  <text x="{building_x + building_width_px + scaffold_offset + scaffold_width + 8}" y="{center_y}" text-anchor="middle" font-family="Arial" font-size="9" fill="{self.COLORS['text_light']}" transform="rotate(90, {building_x + building_width_px + scaffold_offset + scaffold_width + 8}, {center_y})">Ost ({building.width_m:.1f}m)</text>
'''

        # Verankerungspunkte
        anchor_positions = [
            (building_x - scaffold_offset - scaffold_width/2, building_y - scaffold_offset - scaffold_width/2),
            (building_x + building_width_px + scaffold_offset + scaffold_width/2, building_y - scaffold_offset - scaffold_width/2),
            (building_x - scaffold_offset - scaffold_width/2, building_y + building_height_px + scaffold_offset + scaffold_width/2),
            (building_x + building_width_px + scaffold_offset + scaffold_width/2, building_y + building_height_px + scaffold_offset + scaffold_width/2),
            (center_x, building_y - scaffold_offset - scaffold_width/2),
            (center_x, building_y + building_height_px + scaffold_offset + scaffold_width/2),
            (building_x - scaffold_offset - scaffold_width/2, center_y),
            (building_x + building_width_px + scaffold_offset + scaffold_width/2, center_y),
        ]

        svg += '  <!-- Verankerungspunkte -->\n'
        for ax, ay in anchor_positions:
            svg += f'  <circle cx="{ax}" cy="{ay}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Masse
        dim_offset = scaffold_offset + scaffold_width + 25
        svg += f'''
  <!-- Masse -->
  <g stroke="#333" stroke-width="0.5">
    <line x1="{building_x}" y1="{building_y + building_height_px + dim_offset}" x2="{building_x + building_width_px}" y2="{building_y + building_height_px + dim_offset}"/>
    <line x1="{building_x}" y1="{building_y + building_height_px + dim_offset - 5}" x2="{building_x}" y2="{building_y + building_height_px + dim_offset + 5}"/>
    <line x1="{building_x + building_width_px}" y1="{building_y + building_height_px + dim_offset - 5}" x2="{building_x + building_width_px}" y2="{building_y + building_height_px + dim_offset + 5}"/>
    <line x1="{building_x + building_width_px + dim_offset}" y1="{building_y}" x2="{building_x + building_width_px + dim_offset}" y2="{building_y + building_height_px}"/>
    <line x1="{building_x + building_width_px + dim_offset - 5}" y1="{building_y}" x2="{building_x + building_width_px + dim_offset + 5}" y2="{building_y}"/>
    <line x1="{building_x + building_width_px + dim_offset - 5}" y1="{building_y + building_height_px}" x2="{building_x + building_width_px + dim_offset + 5}" y2="{building_y + building_height_px}"/>
  </g>
  <text x="{center_x}" y="{building_y + building_height_px + dim_offset + 15}" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">{building.length_m:.1f} m</text>
  <text x="{building_x + building_width_px + dim_offset + 15}" y="{center_y}" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" transform="rotate(90, {building_x + building_width_px + dim_offset + 15}, {center_y})">{building.width_m:.1f} m</text>
'''

        # Fläche
        area = building.area_m2 or (building.length_m * building.width_m)
        svg += f'''
  <text x="{center_x}" y="{center_y}" text-anchor="middle" font-family="Arial" font-size="11" fill="{self.COLORS['text_light']}">{area:.0f} m²</text>
'''

        return svg


# Singleton
_svg_generator: Optional[SVGGenerator] = None


def get_svg_generator() -> SVGGenerator:
    """Hole Singleton-Instanz des SVG-Generators"""
    global _svg_generator
    if _svg_generator is None:
        _svg_generator = SVGGenerator()
    return _svg_generator
