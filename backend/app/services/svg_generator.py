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
"""

from typing import Optional, List, Tuple
from dataclasses import dataclass
import math


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
    <text x="10" y="43" font-family="Arial" font-size="9" fill="{self.COLORS['text']}">Geschosse: {building.floors} | Breitenklasse: {building.width_class} | Fläche: {ausmass_m2:.0f} m²</text>
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
        Generiert Schnittansicht (Querschnitt durch Gebäude)
        """
        margin = {'top': 60, 'right': 130, 'bottom': 80, 'left': 60}
        draw_width = width - margin['left'] - margin['right']
        draw_height = height - margin['top'] - margin['bottom']

        # Höhen
        max_height = building.ridge_height_m or building.eave_height_m
        eave_h = building.eave_height_m
        ridge_h = building.ridge_height_m or eave_h

        # Skalierung
        building_width_with_scaffold = building.width_m + 6  # +3m pro Seite für Gerüst
        scale_x = draw_width / building_width_with_scaffold
        scale_y = draw_height / (max_height + 3)
        scale = min(scale_x, scale_y)

        # Positionen
        ground_y = margin['top'] + draw_height
        building_x = margin['left'] + (draw_width - building.width_m * scale) / 2
        building_width_px = building.width_m * scale
        eave_height_px = eave_h * scale
        ridge_height_px = ridge_h * scale
        scaffold_width = 18

        # Geschosshöhe
        floor_height = eave_height_px / building.floors

        svg = self._svg_header(width, height, f"Gebäudeschnitt - {building.address}")

        # Himmel
        svg += f'  <rect width="{width}" height="{ground_y}" fill="{self.COLORS["sky"]}"/>\n'

        # Boden
        svg += f'  <rect x="0" y="{ground_y}" width="{width}" height="{height - ground_y}" fill="{self.COLORS["ground"]}"/>\n'

        # Titel
        svg += f'''
  <text x="{width/2}" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="{self.COLORS['text']}">
    Gebäudeschnitt mit Gerüstposition
  </text>
  <text x="{width/2}" y="42" text-anchor="middle" font-family="Arial" font-size="11" fill="{self.COLORS['text_light']}">
    {building.address}
  </text>
'''

        # Höhenraster
        grid_heights = [h for h in [5, 10, 15, 20, 25, 30, 40] if h <= max_height + 5]
        for h in grid_heights:
            y_pos = ground_y - h * scale
            svg += f'  <line x1="{margin["left"]}" y1="{y_pos}" x2="{width - margin["right"]}" y2="{y_pos}" stroke="#ccc" stroke-width="0.5" stroke-dasharray="4,4"/>\n'
            svg += f'  <text x="{margin["left"] - 8}" y="{y_pos + 3}" text-anchor="end" font-family="Arial" font-size="9" fill="#999">{h}m</text>\n'

        # Bodenlinie
        svg += f'  <line x1="{margin["left"] - 20}" y1="{ground_y}" x2="{width - margin["right"] + 20}" y2="{ground_y}" stroke="#333" stroke-width="2"/>\n'

        # Linkes Gerüst
        scaffold_left_x = building_x - scaffold_width - 12
        scaffold_height_px = eave_height_px + 30
        svg += f'''
  <!-- Linkes Gerüst -->
  <rect x="{scaffold_left_x}" y="{ground_y - scaffold_height_px}" width="{scaffold_width}" height="{scaffold_height_px}" fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
  <text x="{scaffold_left_x + scaffold_width/2}" y="{ground_y - scaffold_height_px/2}" text-anchor="middle" font-family="Arial" font-size="8" fill="#996600" transform="rotate(-90, {scaffold_left_x + scaffold_width/2}, {ground_y - scaffold_height_px/2})">Gerüst {building.width_class}</text>
'''
        # Verankerungen links
        for ratio in [0.25, 0.5, 0.75]:
            cy = ground_y - eave_height_px * ratio
            svg += f'  <circle cx="{scaffold_left_x + scaffold_width/2}" cy="{cy}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Gebäude
        svg += f'''
  <!-- Gebäude -->
  <rect x="{building_x}" y="{ground_y - eave_height_px}" width="{building_width_px}" height="{eave_height_px}" fill="{self.COLORS['building']}" stroke="{self.COLORS['building_stroke']}" stroke-width="1.5"/>
'''

        # Fenster
        svg += f'  <rect x="{building_x + 15}" y="{ground_y - eave_height_px + 15}" width="{building_width_px - 30}" height="{eave_height_px - 30}" fill="url(#windows)"/>\n'

        # Geschosslinien
        for i in range(1, building.floors):
            y_floor = ground_y - floor_height * i
            svg += f'  <line x1="{building_x}" y1="{y_floor}" x2="{building_x + building_width_px}" y2="{y_floor}" stroke="#999" stroke-width="1"/>\n'

        # Dach
        if building.roof_type == 'gable' and ridge_h > eave_h:
            svg += f'''
  <!-- Dach (Satteldach) -->
  <polygon points="{building_x},{ground_y - eave_height_px} {building_x + building_width_px/2},{ground_y - ridge_height_px} {building_x + building_width_px},{ground_y - eave_height_px}" fill="url(#roof-pattern)" stroke="{self.COLORS['building_stroke']}" stroke-width="1.5"/>
'''
        elif building.roof_type == 'flat':
            svg += f'''
  <!-- Flachdach -->
  <rect x="{building_x - 5}" y="{ground_y - eave_height_px - 8}" width="{building_width_px + 10}" height="8" fill="#666" stroke="{self.COLORS['building_stroke']}"/>
'''

        # Rechtes Gerüst
        scaffold_right_x = building_x + building_width_px + 12
        svg += f'''
  <!-- Rechtes Gerüst -->
  <rect x="{scaffold_right_x}" y="{ground_y - scaffold_height_px}" width="{scaffold_width}" height="{scaffold_height_px}" fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
'''
        # Verankerungen rechts
        for ratio in [0.25, 0.5, 0.75]:
            cy = ground_y - eave_height_px * ratio
            svg += f'  <circle cx="{scaffold_right_x + scaffold_width/2}" cy="{cy}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Höhenkoten rechts
        svg += f'''
  <!-- Höhenkoten -->
  <g font-family="Arial" font-size="9">
    <line x1="{width - margin['right'] + 10}" y1="{ground_y}" x2="{width - margin['right'] + 35}" y2="{ground_y}" stroke="#333" stroke-width="0.5"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y + 3}" fill="#333">±0.00 m</text>

    <line x1="{width - margin['right'] + 10}" y1="{ground_y - eave_height_px}" x2="{width - margin['right'] + 35}" y2="{ground_y - eave_height_px}" stroke="{self.COLORS['dimension']}" stroke-width="0.5" stroke-dasharray="2,2"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y - eave_height_px + 3}" fill="{self.COLORS['dimension']}">Traufe {eave_h:.1f}m</text>
'''
        if ridge_h > eave_h:
            svg += f'''
    <line x1="{width - margin['right'] + 10}" y1="{ground_y - ridge_height_px}" x2="{width - margin['right'] + 35}" y2="{ground_y - ridge_height_px}" stroke="{self.COLORS['ridge']}" stroke-width="0.5" stroke-dasharray="2,2"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y - ridge_height_px + 3}" fill="{self.COLORS['ridge']}" font-weight="bold">First {ridge_h:.1f}m</text>
'''
        svg += '  </g>\n'

        # Breitenmass unten
        svg += f'''
  <!-- Breitenmass -->
  <g>
    <line x1="{building_x}" y1="{ground_y + 25}" x2="{building_x + building_width_px}" y2="{ground_y + 25}" stroke="#333" stroke-width="1"/>
    <line x1="{building_x}" y1="{ground_y + 18}" x2="{building_x}" y2="{ground_y + 32}" stroke="#333" stroke-width="1"/>
    <line x1="{building_x + building_width_px}" y1="{ground_y + 18}" x2="{building_x + building_width_px}" y2="{ground_y + 32}" stroke="#333" stroke-width="1"/>
    <text x="{building_x + building_width_px/2}" y="{ground_y + 45}" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold">{building.width_m:.1f} m</text>
  </g>
'''

        # Legende
        legend_items = [
            {'type': 'pattern', 'pattern': 'scaffold-pattern', 'stroke': self.COLORS['scaffold_stroke'], 'label': 'Fassadengerüst'},
            {'type': 'circle', 'fill': self.COLORS['anchor'], 'label': 'Verankerung'},
            {'type': 'pattern', 'pattern': 'roof-pattern', 'stroke': '#333', 'label': 'Dach'},
        ]
        svg += self._legend(width - 155, 55, legend_items)

        # NPK 114 Info
        ausmass_m2 = (building.width_m + 2) * (building.eave_height_m + 1) * 2  # Vereinfacht
        svg += self._npk_info_box(margin['left'], height - 65, building, ausmass_m2)

        # Massstab
        svg += self._scale_bar(width - 140, height - 35, scale, 10)

        svg += self._svg_footer()
        return svg

    def generate_elevation(self, building: BuildingData, width: int = 700, height: int = 480) -> str:
        """
        Generiert Fassadenansicht (Elevation)
        """
        margin = {'top': 60, 'right': 130, 'bottom': 80, 'left': 60}
        draw_width = width - margin['left'] - margin['right']
        draw_height = height - margin['top'] - margin['bottom']

        # Höhen
        max_height = building.ridge_height_m or building.eave_height_m
        eave_h = building.eave_height_m
        ridge_h = building.ridge_height_m or eave_h

        # Skalierung
        scale_x = draw_width / (building.length_m + 4)
        scale_y = draw_height / (max_height + 3)
        scale = min(scale_x, scale_y)

        # Positionen
        ground_y = margin['top'] + draw_height
        building_x = margin['left'] + (draw_width - building.length_m * scale) / 2
        building_width_px = building.length_m * scale
        eave_height_px = eave_h * scale
        ridge_height_px = ridge_h * scale

        svg = self._svg_header(width, height, f"Fassadenansicht - {building.address}")

        # Himmel
        svg += f'  <rect width="{width}" height="{ground_y}" fill="{self.COLORS["sky"]}"/>\n'

        # Boden
        svg += f'  <rect x="0" y="{ground_y}" width="{width}" height="{height - ground_y}" fill="{self.COLORS["ground"]}"/>\n'

        # Titel
        svg += f'''
  <text x="{width/2}" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="{self.COLORS['text']}">
    Fassadenansicht mit Gerüstposition
  </text>
  <text x="{width/2}" y="42" text-anchor="middle" font-family="Arial" font-size="11" fill="{self.COLORS['text_light']}">
    {building.address}
  </text>
'''

        # Bodenlinie
        svg += f'  <line x1="{margin["left"] - 20}" y1="{ground_y}" x2="{width - margin["right"] + 20}" y2="{ground_y}" stroke="#333" stroke-width="2"/>\n'

        # Gebäude
        svg += f'''
  <!-- Gebäude -->
  <rect x="{building_x}" y="{ground_y - eave_height_px}" width="{building_width_px}" height="{eave_height_px}" fill="{self.COLORS['building']}" stroke="{self.COLORS['building_stroke']}" stroke-width="1.5"/>
'''

        # Fenster
        svg += f'  <rect x="{building_x + 20}" y="{ground_y - eave_height_px + 20}" width="{building_width_px - 40}" height="{eave_height_px - 40}" fill="url(#windows)"/>\n'

        # Dach
        if building.roof_type == 'gable' and ridge_h > eave_h:
            svg += f'''
  <!-- Dach (Satteldach) -->
  <polygon points="{building_x - 10},{ground_y - eave_height_px} {building_x + building_width_px/2},{ground_y - ridge_height_px} {building_x + building_width_px + 10},{ground_y - eave_height_px}" fill="url(#roof-pattern)" stroke="{self.COLORS['building_stroke']}" stroke-width="1.5"/>
'''
        elif building.roof_type == 'flat':
            svg += f'''
  <!-- Flachdach -->
  <rect x="{building_x - 5}" y="{ground_y - eave_height_px - 8}" width="{building_width_px + 10}" height="8" fill="#666" stroke="{self.COLORS['building_stroke']}"/>
'''

        # Gerüst (vor Fassade)
        scaffold_width = 15
        scaffold_height_px = eave_height_px + 30
        scaffold_left_x = building_x - scaffold_width - 5
        scaffold_right_x = building_x + building_width_px + 5

        svg += f'''
  <!-- Gerüst links -->
  <rect x="{scaffold_left_x}" y="{ground_y - scaffold_height_px}" width="{scaffold_width}" height="{scaffold_height_px}" fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
  <text x="{scaffold_left_x + scaffold_width/2}" y="{ground_y - scaffold_height_px/2}" text-anchor="middle" font-family="Arial" font-size="7" fill="#996600" transform="rotate(-90, {scaffold_left_x + scaffold_width/2}, {ground_y - scaffold_height_px/2})">Gerüst {building.width_class}</text>

  <!-- Gerüst rechts -->
  <rect x="{scaffold_right_x}" y="{ground_y - scaffold_height_px}" width="{scaffold_width}" height="{scaffold_height_px}" fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
'''

        # Verankerungen
        for ratio in [0.25, 0.5, 0.75]:
            cy = ground_y - eave_height_px * ratio
            svg += f'  <circle cx="{scaffold_left_x + scaffold_width/2}" cy="{cy}" r="3" fill="{self.COLORS["anchor"]}"/>\n'
            svg += f'  <circle cx="{scaffold_right_x + scaffold_width/2}" cy="{cy}" r="3" fill="{self.COLORS["anchor"]}"/>\n'

        # Höhenkoten rechts
        svg += f'''
  <!-- Höhenkoten -->
  <g font-family="Arial" font-size="9">
    <line x1="{width - margin['right'] + 10}" y1="{ground_y}" x2="{width - margin['right'] + 35}" y2="{ground_y}" stroke="#333" stroke-width="0.5"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y + 3}" fill="#333">±0.00 m</text>

    <line x1="{width - margin['right'] + 10}" y1="{ground_y - eave_height_px}" x2="{width - margin['right'] + 35}" y2="{ground_y - eave_height_px}" stroke="{self.COLORS['dimension']}" stroke-width="0.5" stroke-dasharray="2,2"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y - eave_height_px + 3}" fill="{self.COLORS['dimension']}">Traufe {eave_h:.1f}m</text>
'''
        if ridge_h > eave_h:
            svg += f'''
    <line x1="{width - margin['right'] + 10}" y1="{ground_y - ridge_height_px}" x2="{width - margin['right'] + 35}" y2="{ground_y - ridge_height_px}" stroke="{self.COLORS['ridge']}" stroke-width="0.5" stroke-dasharray="2,2"/>
    <text x="{width - margin['right'] + 40}" y="{ground_y - ridge_height_px + 3}" fill="{self.COLORS['ridge']}" font-weight="bold">First {ridge_h:.1f}m</text>
'''
        svg += '  </g>\n'

        # Längenmass unten
        svg += f'''
  <!-- Längenmass -->
  <g>
    <line x1="{building_x}" y1="{ground_y + 25}" x2="{building_x + building_width_px}" y2="{ground_y + 25}" stroke="#333" stroke-width="1"/>
    <line x1="{building_x}" y1="{ground_y + 18}" x2="{building_x}" y2="{ground_y + 32}" stroke="#333" stroke-width="1"/>
    <line x1="{building_x + building_width_px}" y1="{ground_y + 18}" x2="{building_x + building_width_px}" y2="{ground_y + 32}" stroke="#333" stroke-width="1"/>
    <text x="{building_x + building_width_px/2}" y="{ground_y + 45}" text-anchor="middle" font-family="Arial" font-size="11" font-weight="bold">{building.length_m:.1f} m</text>
  </g>
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
        Generiert Grundriss mit Gerüstposition
        """
        margin = {'top': 60, 'right': 160, 'bottom': 80, 'left': 50}
        draw_width = width - margin['left'] - margin['right']
        draw_height = height - margin['top'] - margin['bottom']

        # Skalierung
        building_with_scaffold = max(building.length_m, building.width_m) + 6
        scale = min(draw_width, draw_height) / building_with_scaffold * 0.85

        # Zentrieren
        building_width_px = building.length_m * scale
        building_height_px = building.width_m * scale
        center_x = margin['left'] + draw_width / 2
        center_y = margin['top'] + draw_height / 2
        building_x = center_x - building_width_px / 2
        building_y = center_y - building_height_px / 2

        scaffold_offset = 1.0 * scale  # 1m Abstand
        scaffold_width = 0.9 * scale  # 0.9m Gerüstbreite

        svg = self._svg_header(width, height, f"Grundriss - {building.address}")

        # Hintergrund
        svg += f'  <rect width="{width}" height="{height}" fill="#f8f9fa"/>\n'

        # Titel
        svg += f'''
  <text x="{width/2}" y="25" text-anchor="middle" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="{self.COLORS['text']}">
    Grundriss mit Gerüstposition
  </text>
  <text x="{width/2}" y="42" text-anchor="middle" font-family="Arial" font-size="11" fill="{self.COLORS['text_light']}">
    {building.address}{f' | EGID: {building.egid}' if building.egid else ''}
  </text>
'''

        # Gerüst (umlaufend)
        svg += f'''
  <!-- Gerüst umlaufend -->
  <rect x="{building_x - scaffold_offset - scaffold_width}" y="{building_y - scaffold_offset - scaffold_width}"
        width="{building_width_px + 2*scaffold_offset + 2*scaffold_width}" height="{building_height_px + 2*scaffold_offset + 2*scaffold_width}"
        fill="url(#scaffold-pattern)" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="1.5" rx="2"/>
'''

        # Innerer Ausschnitt (Gebäudeabstand)
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

        # Verankerungspunkte (an Ecken und Mitten)
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
    <!-- Länge -->
    <line x1="{building_x}" y1="{building_y + building_height_px + dim_offset}" x2="{building_x + building_width_px}" y2="{building_y + building_height_px + dim_offset}"/>
    <line x1="{building_x}" y1="{building_y + building_height_px + dim_offset - 5}" x2="{building_x}" y2="{building_y + building_height_px + dim_offset + 5}"/>
    <line x1="{building_x + building_width_px}" y1="{building_y + building_height_px + dim_offset - 5}" x2="{building_x + building_width_px}" y2="{building_y + building_height_px + dim_offset + 5}"/>

    <!-- Breite -->
    <line x1="{building_x + building_width_px + dim_offset}" y1="{building_y}" x2="{building_x + building_width_px + dim_offset}" y2="{building_y + building_height_px}"/>
    <line x1="{building_x + building_width_px + dim_offset - 5}" y1="{building_y}" x2="{building_x + building_width_px + dim_offset + 5}" y2="{building_y}"/>
    <line x1="{building_x + building_width_px + dim_offset - 5}" y1="{building_y + building_height_px}" x2="{building_x + building_width_px + dim_offset + 5}" y2="{building_y + building_height_px}"/>
  </g>
  <text x="{center_x}" y="{building_y + building_height_px + dim_offset + 15}" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold">{building.length_m:.1f} m</text>
  <text x="{building_x + building_width_px + dim_offset + 15}" y="{center_y}" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" transform="rotate(90, {building_x + building_width_px + dim_offset + 15}, {center_y})">{building.width_m:.1f} m</text>
'''

        # Fläche im Gebäude
        area = building.area_m2 or (building.length_m * building.width_m)
        svg += f'''
  <text x="{center_x}" y="{center_y}" text-anchor="middle" font-family="Arial" font-size="11" fill="{self.COLORS['text_light']}">{area:.0f} m²</text>
'''

        # Legende
        legend_items = [
            {'type': 'pattern', 'pattern': 'building-hatch', 'stroke': '#333', 'label': 'Gebäude'},
            {'type': 'pattern', 'pattern': 'scaffold-pattern', 'stroke': self.COLORS['scaffold_stroke'], 'label': f'Gerüst {building.width_class}'},
            {'type': 'circle', 'fill': self.COLORS['anchor'], 'label': 'Verankerung'},
        ]
        svg += self._legend(width - 155, 55, legend_items)

        # NPK 114 Info
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


# Singleton
_svg_generator: Optional[SVGGenerator] = None


def get_svg_generator() -> SVGGenerator:
    """Hole Singleton-Instanz des SVG-Generators"""
    global _svg_generator
    if _svg_generator is None:
        _svg_generator = SVGGenerator()
    return _svg_generator
