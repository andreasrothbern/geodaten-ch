"""
SVG Generator Service

Generiert saubere technische SVG-Visualisierungen für Gebäude:
- Schnittansicht (Cross-Section)
- Fassadenansicht (Elevation)
- Grundriss (Floor Plan)

Design-Philosophie:
- Minimalistisch und technisch korrekt
- Fokus auf Masse und Proportionen
- Keine dekorativen Elemente (Fenster, Türen)
- Klare Höhenkoten und Bemaßung
- NPK 114 Info-Box
"""

from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field


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
    width_class: str = "W09"
    # Polygon data for irregular buildings
    polygon_coordinates: Optional[List[List[float]]] = None  # [[x,y], [x,y], ...]
    sides: Optional[List[Dict[str, Any]]] = None  # [{length_m, direction, ...}, ...]


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

    def _svg_header(self, width: int, height: int, title: str) -> str:
        """SVG-Header - einfach ohne Patterns für maximale Kompatibilität"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <title>{title}</title>
'''

    def _svg_footer(self) -> str:
        return '</svg>'

    def _legend(self, x: int, y: int, items: List[dict], width: int = 140) -> str:
        """Generiert Legende mit einfachen Farben"""
        height = 25 + len(items) * 20
        svg = f'''
  <!-- Legende -->
  <g transform="translate({x}, {y})">
    <rect x="0" y="0" width="{width}" height="{height}" fill="{self.COLORS['legend_bg']}" stroke="{self.COLORS['legend_border']}" rx="4"/>
    <text x="10" y="18" font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="{self.COLORS['text']}">Legende</text>
'''
        for i, item in enumerate(items):
            item_y = 30 + i * 20
            if item['type'] == 'circle':
                svg += f'    <circle cx="20" cy="{item_y + 6}" r="4" fill="{item["fill"]}"/>\n'
            else:
                # Alle anderen (rect, pattern) als einfache Rechtecke
                fill_color = item.get('fill', item.get('color', '#e0e0e0'))
                svg += f'    <rect x="10" y="{item_y}" width="20" height="12" fill="{fill_color}" stroke="{item.get("stroke", "#333")}"/>\n'
            svg += f'    <text x="35" y="{item_y + 10}" font-family="Arial" font-size="9" fill="{self.COLORS["text"]}">{item["label"]}</text>\n'

        svg += '  </g>\n'
        return svg

    def _building_info_box(self, x: int, y: int, building: BuildingData) -> str:
        """Gebäude Info-Box mit Dimensionen"""
        ridge_info = f" | First: {building.ridge_height_m:.1f}m" if building.ridge_height_m and building.ridge_height_m > building.eave_height_m else ""
        return f'''
  <!-- Gebäude Info -->
  <g transform="translate({x}, {y})">
    <rect x="0" y="0" width="280" height="50" fill="{self.COLORS['npk_bg']}" stroke="{self.COLORS['npk_border']}" rx="4"/>
    <text x="10" y="15" font-family="Arial" font-size="10" font-weight="bold" fill="{self.COLORS['npk_text']}">Gebäudedaten:</text>
    <text x="10" y="30" font-family="Arial" font-size="9" fill="{self.COLORS['text']}">Traufe: {building.eave_height_m:.1f}m{ridge_info}</text>
    <text x="10" y="43" font-family="Arial" font-size="9" fill="{self.COLORS['text']}">Geschosse: {building.floors or '—'} | L×B: {building.length_m:.1f}m × {building.width_m:.1f}m</text>
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
        Generiert saubere technische Schnittansicht.
        Minimalistisch ohne dekorative Elemente.
        """
        margin = {'top': 60, 'right': 130, 'bottom': 80, 'left': 60}
        draw_width = width - margin['left'] - margin['right']
        draw_height = height - margin['top'] - margin['bottom']

        # Höhen
        eave_h = building.eave_height_m
        ridge_h = building.ridge_height_m or eave_h
        max_height = max(eave_h, ridge_h)

        # Skalierung
        building_width_with_scaffold = building.width_m + 8
        scale_x = draw_width / building_width_with_scaffold
        scale_y = draw_height / (max_height + 5)
        scale = min(scale_x, scale_y)

        # Positionen
        ground_y = margin['top'] + draw_height
        scaffold_width = 15

        svg = self._svg_header(width, height, f"Gebäudeschnitt - {building.address}")

        # Hintergrund
        svg += f'  <rect width="{width}" height="{height}" fill="#f8f9fa"/>\n'

        # Titel
        svg += f'''
  <text x="{width/2}" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="#333">
    Gebäudeschnitt (Querschnitt)
  </text>
  <text x="{width/2}" y="42" text-anchor="middle" font-family="Arial" font-size="10" fill="#666">
    {building.address}
  </text>
'''

        # Höhenraster
        grid_step = 5 if max_height <= 20 else 10
        for h in range(grid_step, int(max_height) + grid_step, grid_step):
            y_pos = ground_y - h * scale
            if y_pos > margin['top']:
                svg += f'  <line x1="{margin["left"]}" y1="{y_pos}" x2="{width - margin["right"]}" y2="{y_pos}" stroke="#e0e0e0" stroke-width="0.5"/>\n'
                svg += f'  <text x="{margin["left"] - 5}" y="{y_pos + 3}" text-anchor="end" font-family="Arial" font-size="8" fill="#999">{h}m</text>\n'

        # Bodenlinie
        svg += f'  <line x1="{margin["left"] - 20}" y1="{ground_y}" x2="{width - margin["right"] + 20}" y2="{ground_y}" stroke="#333" stroke-width="2"/>\n'
        svg += f'  <text x="{margin["left"] - 5}" y="{ground_y + 4}" text-anchor="end" font-family="Arial" font-size="8" fill="#333">0m</text>\n'

        # Gebäude zeichnen
        svg += self._draw_simple_cross_section(
            building, scale, ground_y, margin, width, height, scaffold_width, draw_width, eave_h, ridge_h
        )

        # Legende
        legend_items = [
            {'type': 'rect', 'fill': '#e0e0e0', 'stroke': '#333', 'label': 'Gebäude'},
            {'type': 'rect', 'fill': '#fff3cd', 'stroke': self.COLORS['scaffold_stroke'], 'label': f'Gerüst {building.width_class}'},
            {'type': 'circle', 'fill': self.COLORS['anchor'], 'label': 'Verankerung'},
        ]
        svg += self._legend(width - 155, 55, legend_items)

        # Gebäude Info
        svg += self._building_info_box(margin['left'], height - 65, building)

        # Massstab
        svg += self._scale_bar(width - 140, height - 35, scale, 10)

        svg += self._svg_footer()
        return svg

    def _draw_simple_cross_section(self, building: BuildingData, scale: float, ground_y: float,
                                    margin: dict, width: int, height: int, scaffold_width: float,
                                    draw_width: float, eave_h: float, ridge_h: float) -> str:
        """Zeichnet sauberen technischen Gebäudeschnitt."""
        svg = ""

        building_x = margin['left'] + (draw_width - building.width_m * scale) / 2
        building_width_px = building.width_m * scale
        eave_height_px = eave_h * scale
        ridge_height_px = ridge_h * scale
        scaffold_height_px = ridge_height_px + 20

        # Gerüst links
        scaffold_left_x = building_x - scaffold_width - 15
        svg += f'''
  <!-- Gerüst links -->
  <rect x="{scaffold_left_x}" y="{ground_y - scaffold_height_px}" width="{scaffold_width}" height="{scaffold_height_px}"
        fill="#fff3cd" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
'''
        # Verankerungen
        for h in [eave_h * 0.3, eave_h * 0.6, eave_h * 0.9]:
            cy = ground_y - h * scale
            svg += f'  <circle cx="{scaffold_left_x + scaffold_width/2}" cy="{cy}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Gebäude - einfacher Umriss mit Schraffur
        svg += f'''
  <!-- Gebäude -->
  <rect x="{building_x}" y="{ground_y - eave_height_px}" width="{building_width_px}" height="{eave_height_px}"
        fill="#e0e0e0" stroke="#333" stroke-width="2"/>
'''

        # Dach
        if ridge_h > eave_h:
            svg += f'''
  <!-- Dach -->
  <polygon points="{building_x},{ground_y - eave_height_px} {building_x + building_width_px/2},{ground_y - ridge_height_px} {building_x + building_width_px},{ground_y - eave_height_px}"
           fill="#8b7355" stroke="#333" stroke-width="2"/>
'''

        # Gerüst rechts
        scaffold_right_x = building_x + building_width_px + 15
        svg += f'''
  <!-- Gerüst rechts -->
  <rect x="{scaffold_right_x}" y="{ground_y - scaffold_height_px}" width="{scaffold_width}" height="{scaffold_height_px}"
        fill="#fff3cd" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
'''
        for h in [eave_h * 0.3, eave_h * 0.6, eave_h * 0.9]:
            cy = ground_y - h * scale
            svg += f'  <circle cx="{scaffold_right_x + scaffold_width/2}" cy="{cy}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Höhenkoten - durchgehende gestrichelte Linien
        line_start = scaffold_left_x - 20
        line_end = width - margin['right'] + 40
        svg += f'''
  <!-- Höhenkoten -->
  <g font-family="Arial" font-size="10">
    <!-- Terrain -->
    <line x1="{line_start}" y1="{ground_y}" x2="{line_end}" y2="{ground_y}" stroke="#333" stroke-width="1"/>
    <text x="{line_end + 5}" y="{ground_y + 4}">±0.00</text>

    <!-- Traufe -->
    <line x1="{line_start}" y1="{ground_y - eave_height_px}" x2="{line_end}" y2="{ground_y - eave_height_px}"
          stroke="#0066cc" stroke-width="0.75" stroke-dasharray="6,3"/>
    <text x="{line_end + 5}" y="{ground_y - eave_height_px + 4}" fill="#0066cc">+{eave_h:.1f} m (Traufe)</text>
'''
        if ridge_h > eave_h:
            svg += f'''
    <!-- First -->
    <line x1="{line_start}" y1="{ground_y - ridge_height_px}" x2="{line_end}" y2="{ground_y - ridge_height_px}"
          stroke="#cc0000" stroke-width="0.75" stroke-dasharray="6,3"/>
    <text x="{line_end + 5}" y="{ground_y - ridge_height_px + 4}" fill="#cc0000" font-weight="bold">+{ridge_h:.1f} m (First)</text>
'''
        svg += '  </g>\n'

        # Breitenmass
        dim_y = ground_y + 25
        svg += f'''
  <!-- Breitenmass -->
  <g stroke="#333" stroke-width="1" font-family="Arial" font-size="11">
    <line x1="{building_x}" y1="{dim_y}" x2="{building_x + building_width_px}" y2="{dim_y}"/>
    <line x1="{building_x}" y1="{dim_y - 5}" x2="{building_x}" y2="{dim_y + 5}"/>
    <line x1="{building_x + building_width_px}" y1="{dim_y - 5}" x2="{building_x + building_width_px}" y2="{dim_y + 5}"/>
    <text x="{building_x + building_width_px/2}" y="{dim_y + 18}" text-anchor="middle" font-weight="bold">{building.width_m:.1f} m</text>
  </g>
'''

        return svg

    def generate_elevation(self, building: BuildingData, width: int = 700, height: int = 480) -> str:
        """
        Generiert saubere technische Fassadenansicht.
        Minimalistisch ohne dekorative Elemente.
        """
        margin = {'top': 60, 'right': 130, 'bottom': 80, 'left': 60}
        draw_width = width - margin['left'] - margin['right']
        draw_height = height - margin['top'] - margin['bottom']

        # Höhen
        eave_h = building.eave_height_m
        ridge_h = building.ridge_height_m or eave_h
        max_height = max(eave_h, ridge_h)

        # Skalierung
        scale_x = draw_width / (building.length_m + 8)
        scale_y = draw_height / (max_height + 5)
        scale = min(scale_x, scale_y)

        # Positionen
        ground_y = margin['top'] + draw_height
        building_x = margin['left'] + (draw_width - building.length_m * scale) / 2
        building_width_px = building.length_m * scale
        eave_height_px = eave_h * scale
        ridge_height_px = ridge_h * scale
        scaffold_width = 15

        svg = self._svg_header(width, height, f"Fassadenansicht - {building.address}")

        # Hintergrund
        svg += f'  <rect width="{width}" height="{height}" fill="#f8f9fa"/>\n'

        # Titel
        svg += f'''
  <text x="{width/2}" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="#333">
    Fassadenansicht (Traufseite)
  </text>
  <text x="{width/2}" y="42" text-anchor="middle" font-family="Arial" font-size="10" fill="#666">
    {building.address}
  </text>
'''

        # Höhenraster
        grid_step = 5 if max_height <= 20 else 10
        for h in range(grid_step, int(max_height) + grid_step, grid_step):
            y_pos = ground_y - h * scale
            if y_pos > margin['top']:
                svg += f'  <line x1="{margin["left"]}" y1="{y_pos}" x2="{width - margin["right"]}" y2="{y_pos}" stroke="#e0e0e0" stroke-width="0.5"/>\n'
                svg += f'  <text x="{margin["left"] - 5}" y="{y_pos + 3}" text-anchor="end" font-family="Arial" font-size="8" fill="#999">{h}m</text>\n'

        # Bodenlinie
        svg += f'  <line x1="{margin["left"] - 20}" y1="{ground_y}" x2="{width - margin["right"] + 20}" y2="{ground_y}" stroke="#333" stroke-width="2"/>\n'
        svg += f'  <text x="{margin["left"] - 5}" y="{ground_y + 4}" text-anchor="end" font-family="Arial" font-size="8" fill="#333">0m</text>\n'

        # Gerüst links
        scaffold_left_x = building_x - scaffold_width - 12
        scaffold_height_px = ridge_height_px + 15
        svg += f'''
  <!-- Gerüst links -->
  <rect x="{scaffold_left_x}" y="{ground_y - scaffold_height_px}" width="{scaffold_width}" height="{scaffold_height_px}"
        fill="#fff3cd" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="1.5"/>
'''

        # Gebäude - einfacher Umriss mit Schraffur
        svg += f'''
  <!-- Gebäude -->
  <rect x="{building_x}" y="{ground_y - eave_height_px}" width="{building_width_px}" height="{eave_height_px}"
        fill="#e0e0e0" stroke="#333" stroke-width="2"/>
'''

        # Dach
        if ridge_h > eave_h and building.roof_type in ['gable', None]:
            svg += f'''
  <!-- Dach -->
  <polygon points="{building_x - 8},{ground_y - eave_height_px} {building_x + building_width_px/2},{ground_y - ridge_height_px} {building_x + building_width_px + 8},{ground_y - eave_height_px}"
           fill="#8b7355" stroke="#333" stroke-width="2"/>
'''
        elif building.roof_type == 'flat':
            svg += f'''
  <!-- Flachdach -->
  <rect x="{building_x - 3}" y="{ground_y - eave_height_px - 4}" width="{building_width_px + 6}" height="4"
        fill="#888" stroke="#333" stroke-width="1"/>
'''

        # Gerüst rechts
        scaffold_right_x = building_x + building_width_px + 12
        svg += f'''
  <!-- Gerüst rechts -->
  <rect x="{scaffold_right_x}" y="{ground_y - scaffold_height_px}" width="{scaffold_width}" height="{scaffold_height_px}"
        fill="#fff3cd" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="1.5"/>
'''

        # Verankerungspunkte (3 Stück pro Seite)
        for ratio in [0.25, 0.5, 0.75]:
            anchor_y = ground_y - eave_h * ratio * scale
            svg += f'  <circle cx="{scaffold_left_x + scaffold_width/2}" cy="{anchor_y}" r="3" fill="{self.COLORS["anchor"]}"/>\n'
            svg += f'  <circle cx="{scaffold_right_x + scaffold_width/2}" cy="{anchor_y}" r="3" fill="{self.COLORS["anchor"]}"/>\n'

        # Höhenkoten rechts
        kote_x = width - margin['right'] + 10
        svg += f'''
  <!-- Höhenkoten -->
  <g font-family="Arial" font-size="9">
    <line x1="{kote_x}" y1="{ground_y}" x2="{kote_x + 25}" y2="{ground_y}" stroke="#333" stroke-width="0.5"/>
    <text x="{kote_x + 30}" y="{ground_y + 3}">±0.00</text>

    <line x1="{kote_x}" y1="{ground_y - eave_height_px}" x2="{kote_x + 25}" y2="{ground_y - eave_height_px}"
          stroke="#0066cc" stroke-width="0.5" stroke-dasharray="3,2"/>
    <text x="{kote_x + 30}" y="{ground_y - eave_height_px + 3}" fill="#0066cc">+{eave_h:.1f}m Traufe</text>
'''
        if ridge_h > eave_h:
            svg += f'''
    <line x1="{kote_x}" y1="{ground_y - ridge_height_px}" x2="{kote_x + 25}" y2="{ground_y - ridge_height_px}"
          stroke="#cc0000" stroke-width="0.5" stroke-dasharray="3,2"/>
    <text x="{kote_x + 30}" y="{ground_y - ridge_height_px + 3}" fill="#cc0000" font-weight="bold">+{ridge_h:.1f}m First</text>
'''
        svg += '  </g>\n'

        # Breitenmass unten
        dim_y = ground_y + 25
        svg += f'''
  <!-- Breitenmass -->
  <g stroke="#333" stroke-width="1">
    <line x1="{building_x}" y1="{dim_y}" x2="{building_x + building_width_px}" y2="{dim_y}"/>
    <line x1="{building_x}" y1="{dim_y - 5}" x2="{building_x}" y2="{dim_y + 5}"/>
    <line x1="{building_x + building_width_px}" y1="{dim_y - 5}" x2="{building_x + building_width_px}" y2="{dim_y + 5}"/>
  </g>
  <text x="{building_x + building_width_px/2}" y="{dim_y + 15}" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">{building.length_m:.1f} m</text>
'''

        # Legende
        legend_items = [
            {'type': 'rect', 'fill': '#e0e0e0', 'stroke': '#333', 'label': 'Gebäude'},
            {'type': 'rect', 'fill': '#fff3cd', 'stroke': self.COLORS['scaffold_stroke'], 'label': f'Gerüst {building.width_class}'},
            {'type': 'circle', 'fill': self.COLORS['anchor'], 'label': 'Verankerung'},
        ]
        svg += self._legend(width - 155, 55, legend_items)

        # Gebäude Info
        svg += self._building_info_box(margin['left'], height - 65, building)

        # Massstab
        svg += self._scale_bar(width - 140, height - 35, scale, 10)

        svg += self._svg_footer()
        return svg

    def generate_floor_plan(self, building: BuildingData, width: int = 600, height: int = 500) -> str:
        """
        Generiert sauberen technischen Grundriss.
        Verwendet echte Polygon-Daten falls vorhanden.
        """
        margin = {'top': 60, 'right': 160, 'bottom': 80, 'left': 50}
        draw_width = width - margin['left'] - margin['right']
        draw_height = height - margin['top'] - margin['bottom']

        # Dimensionen
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

        # Anzahl Seiten für Titel
        num_sides = len(building.sides) if building.sides else 4
        shape_info = f" ({num_sides} Seiten)" if num_sides != 4 else ""

        # Titel
        svg += f'''
  <text x="{width/2}" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="bold" fill="#333">
    Grundriss mit Gerüstposition{shape_info}
  </text>
  <text x="{width/2}" y="42" text-anchor="middle" font-family="Arial" font-size="10" fill="#666">
    {building.address}
  </text>
'''

        # Gebäude zeichnen - Polygon wenn vorhanden, sonst Rechteck
        if building.polygon_coordinates and len(building.polygon_coordinates) >= 3:
            svg += self._draw_polygon_floor_plan(
                building, scale, center_x, center_y, width, height, margin
            )
        else:
            svg += self._draw_rectangle_floor_plan(
                building, scale, center_x, center_y, width, height, margin
            )

        # Legende
        legend_items = [
            {'type': 'rect', 'fill': '#e0e0e0', 'stroke': '#333', 'label': 'Gebäude'},
            {'type': 'rect', 'fill': '#fff3cd', 'stroke': self.COLORS['scaffold_stroke'], 'label': f'Gerüst {building.width_class}'},
            {'type': 'circle', 'fill': self.COLORS['anchor'], 'label': 'Verankerung'},
        ]
        svg += self._legend(width - 155, 55, legend_items)

        # Gebäude Info
        svg += self._building_info_box(margin['left'], height - 65, building)

        # Massstab
        svg += self._scale_bar(30, height - 35, scale, 10)

        # Nordpfeil
        svg += self._north_arrow(width - 40, height - 50)

        # Koordinaten-Info
        area = building.area_m2 or (building.length_m * building.width_m)
        svg += f'''
  <text x="{width/2}" y="{height - 10}" text-anchor="middle" font-family="Arial" font-size="9" fill="{self.COLORS['text_light']}">
    LV95 (EPSG:2056){f' | EGID: {building.egid}' if building.egid else ''} | Fläche: {area:.0f} m²
  </text>
'''

        svg += self._svg_footer()
        return svg

    def _draw_polygon_floor_plan(self, building: BuildingData, scale: float,
                                   center_x: float, center_y: float,
                                   width: int, height: int, margin: dict) -> str:
        """Zeichnet Grundriss mit echtem Polygon."""
        svg = ""
        coords = building.polygon_coordinates
        sides = building.sides or []

        if not coords or len(coords) < 3:
            return self._draw_rectangle_floor_plan(building, scale, center_x, center_y, width, height, margin)

        # Koordinaten in Meter umrechnen (von LV95)
        # LV95 Koordinaten sind in Metern, wir müssen sie zentrieren
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        center_geo_x = (min_x + max_x) / 2
        center_geo_y = (min_y + max_y) / 2

        # Umrechnung: Geo-Koordinaten -> SVG-Koordinaten
        # Y-Achse invertieren (SVG hat Y nach unten)
        def to_svg(gx, gy):
            sx = center_x + (gx - center_geo_x) * scale
            sy = center_y - (gy - center_geo_y) * scale  # Y invertiert
            return sx, sy

        # Polygon-Punkte für SVG
        svg_points = [to_svg(c[0], c[1]) for c in coords]
        points_str = " ".join([f"{p[0]:.1f},{p[1]:.1f}" for p in svg_points])

        # Scaffold zone (offset polygon)
        scaffold_offset = 1.0 * scale  # 1m Abstand

        # Vereinfachte Scaffold-Zone: Bounding box + offset
        svg_xs = [p[0] for p in svg_points]
        svg_ys = [p[1] for p in svg_points]
        bbox_min_x = min(svg_xs) - scaffold_offset - 10
        bbox_max_x = max(svg_xs) + scaffold_offset + 10
        bbox_min_y = min(svg_ys) - scaffold_offset - 10
        bbox_max_y = max(svg_ys) + scaffold_offset + 10

        # Gerüst-Zone (als Rechteck um das Polygon)
        svg += f'''
  <!-- Gerüst-Zone -->
  <rect x="{bbox_min_x}" y="{bbox_min_y}"
        width="{bbox_max_x - bbox_min_x}" height="{bbox_max_y - bbox_min_y}"
        fill="#fff3cd" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="1.5" rx="2"/>
'''

        # Innerer Bereich (Gebäude-Polygon - Hintergrund)
        svg += f'''
  <!-- Gebäude-Polygon Hintergrund -->
  <polygon points="{points_str}"
           fill="#e0e0e0" stroke="none"/>
'''

        # Klickbare Fassaden-Segmente (einzeln für Interaktivität)
        svg += '  <!-- Klickbare Fassaden-Segmente -->\n'
        svg += '''  <style>
    .facade-segment { cursor: pointer; transition: stroke 0.2s, stroke-width 0.2s; }
    .facade-segment:hover { stroke: #2563eb; stroke-width: 5; }
    .facade-segment.selected { stroke: #dc2626; stroke-width: 5; }
  </style>
'''
        for i, side in enumerate(sides):
            # Segment-Koordinaten berechnen
            if i < len(coords) - 1:
                start = coords[i]
                end = coords[i + 1]
            else:
                start = coords[i]
                end = coords[0]

            svg_start = to_svg(start[0], start[1])
            svg_end = to_svg(end[0], end[1])
            length = side.get('length_m', 0)
            direction = side.get('direction', '')
            side_index = side.get('index', i)  # Index aus side-Objekt für Konsistenz

            # Fassaden-Segment als klickbare Linie
            svg += f'''  <line x1="{svg_start[0]:.1f}" y1="{svg_start[1]:.1f}" x2="{svg_end[0]:.1f}" y2="{svg_end[1]:.1f}"
        class="facade-segment"
        data-facade-index="{side_index}"
        data-facade-length="{length:.2f}"
        data-facade-direction="{direction}"
        stroke="{self.COLORS['building_stroke']}" stroke-width="3" stroke-linecap="round"/>
'''

        # Seiten-Beschriftungen
        svg += '  <!-- Fassaden-Beschriftungen -->\n'
        for i, side in enumerate(sides):
            if side.get('length_m', 0) < 0.5:  # Sehr kurze Seiten überspringen
                continue

            # Mittelpunkt der Seite berechnen
            if i < len(coords) - 1:
                start = coords[i]
                end = coords[i + 1]
            else:
                start = coords[i]
                end = coords[0]

            mid_x = (start[0] + end[0]) / 2
            mid_y = (start[1] + end[1]) / 2
            svg_mid = to_svg(mid_x, mid_y)

            length = side.get('length_m', 0)
            direction = side.get('direction', '')
            side_index = side.get('index', i)  # Index aus side-Objekt

            # Label Position (leicht nach aussen versetzt)
            # Normaler Vektor zur Seite berechnen
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            seg_len = (dx**2 + dy**2)**0.5
            if seg_len > 0:
                nx = -dy / seg_len  # Normal (nach aussen)
                ny = dx / seg_len
                label_x = svg_mid[0] + nx * scale * 1.5
                label_y = svg_mid[1] - ny * scale * 1.5
            else:
                label_x, label_y = svg_mid

            # Index-Nummer an jeder Fassade (0-basiert intern, 1-basiert angezeigt)
            svg += f'  <text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle" font-family="Arial" font-size="9" font-weight="bold" fill="{self.COLORS["text"]}" data-label-for="{side_index}">[{side_index+1}] {direction}</text>\n'
            svg += f'  <text x="{label_x:.1f}" y="{label_y + 10:.1f}" text-anchor="middle" font-family="Arial" font-size="8" fill="{self.COLORS["text_light"]}">{length:.1f}m</text>\n'

        # Verankerungspunkte an allen Polygon-Ecken
        svg += '  <!-- Verankerungspunkte -->\n'
        for i, (px, py) in enumerate(svg_points[:-1]):  # Letzter Punkt = erster Punkt
            svg += f'  <circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Fläche und Info in der Mitte
        area = building.area_m2 or 0
        perimeter = sum(s.get('length_m', 0) for s in sides) if sides else 0
        svg += f'''
  <text x="{center_x}" y="{center_y - 8}" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" fill="{self.COLORS['text']}">{area:.0f} m²</text>
  <text x="{center_x}" y="{center_y + 8}" text-anchor="middle" font-family="Arial" font-size="9" fill="{self.COLORS['text_light']}">Umfang: {perimeter:.1f} m</text>
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
        fill="#fff3cd" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="1.5" rx="2"/>
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
        fill="#e0e0e0" stroke="{self.COLORS['building_stroke']}" stroke-width="2"/>
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
