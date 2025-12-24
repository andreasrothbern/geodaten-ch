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
    # Bounding Box dimensions (from polygon) for correct scaling
    bbox_width_m: Optional[float] = None
    bbox_depth_m: Optional[float] = None
    # Gebäude-Zonen für farbcodierte Darstellung
    zones: Optional[List[Dict[str, Any]]] = None
    # Zugänge (Treppen) - Liste von {id, fassade_id, position_percent, grund}
    zugaenge: Optional[List[Dict[str, Any]]] = None


# Farben für Zonen-Typen
ZONE_COLORS = {
    'hauptgebaeude': {'fill': '#e3f2fd', 'stroke': '#1976d2', 'label': 'Hauptgebäude'},
    'anbau': {'fill': '#e8f5e9', 'stroke': '#388e3c', 'label': 'Anbau'},
    'turm': {'fill': '#f3e5f5', 'stroke': '#7b1fa2', 'label': 'Turm'},
    'kuppel': {'fill': '#fff8e1', 'stroke': '#ffa000', 'label': 'Kuppel'},
    'arkade': {'fill': '#fff3e0', 'stroke': '#e65100', 'label': 'Arkade'},
    'vordach': {'fill': '#eceff1', 'stroke': '#546e7a', 'label': 'Vordach'},
    'treppenhaus': {'fill': '#fce4ec', 'stroke': '#c2185b', 'label': 'Treppenhaus'},
    'garage': {'fill': '#efebe9', 'stroke': '#5d4037', 'label': 'Garage'},
    'unknown': {'fill': '#f5f5f5', 'stroke': '#9e9e9e', 'label': 'Unbekannt'},
}


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

    def _svg_header_professional(self, width: int, height: int, title: str) -> str:
        """SVG-Header mit Patterns für professionelle Zeichnungen"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <title>{title}</title>
  <defs>
    <!-- Schraffur für Gebäude -->
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <!-- Gerüst-Füllung -->
    <pattern id="scaffold-pattern" patternUnits="userSpaceOnUse" width="10" height="10">
      <rect width="10" height="10" fill="rgba(0, 102, 204, 0.1)"/>
      <path d="M0,5 h10 M5,0 v10" stroke="rgba(0, 102, 204, 0.3)" stroke-width="0.5"/>
    </pattern>
    <!-- Pfeile für Masslinien -->
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#333"/>
    </marker>
    <marker id="arrow-start" markerWidth="10" markerHeight="10" refX="0" refY="3" orient="auto">
      <path d="M9,0 L9,6 L0,3 z" fill="#333"/>
    </marker>
  </defs>
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

    def _professional_title_block(
        self,
        x: int,
        y: int,
        width: int,
        title: str,
        subtitle: str = "",
        scale: str = "",
        system: str = "Layher Blitz 70"
    ) -> str:
        """
        Professioneller Titelblock für technische Zeichnungen.

        Args:
            x, y: Position (oben links)
            width: Breite des Blocks
            title: Haupttitel (z.B. "GRUNDRISS GERÜST")
            subtitle: Untertitel (z.B. Adresse)
            scale: Massstab (z.B. "1:100")
            system: Gerüstsystem (z.B. "Layher Blitz 70")
        """
        height = 70

        # Untertitel zusammenbauen
        info_parts = []
        if system:
            info_parts.append(f"Fassadengerüst {system}")
        if scale:
            info_parts.append(f"Massstab ca. {scale}")
        info_line = " | ".join(info_parts)

        return f'''
  <!-- Titelblock -->
  <g id="title-block">
    <rect x="{x}" y="{y}" width="{width}" height="{height}" fill="none" stroke="#333" stroke-width="1"/>
    <text x="{x + width/2}" y="{y + 30}" font-family="Arial, sans-serif" font-size="20" font-weight="bold" text-anchor="middle" fill="#1a365d">{title}</text>
    <text x="{x + width/2}" y="{y + 50}" font-family="Arial, sans-serif" font-size="12" text-anchor="middle" fill="#4a5568">{subtitle}</text>
    <text x="{x + width/2}" y="{y + 65}" font-family="Arial, sans-serif" font-size="10" text-anchor="middle" fill="#718096">{info_line}</text>
  </g>
'''

    def _professional_footer(
        self,
        x: int,
        y: int,
        width: int,
        project_name: str = "",
        project_address: str = "",
        company_name: str = "Lawil Gerüstbau AG",
        company_address: str = "Murtenstrasse 30, 3202 Frauenkappelen",
        author_name: str = "",
        author_role: str = "",
        date: str = "",
        document_id: str = ""
    ) -> str:
        """
        Professionelle Fusszeile mit Projekt-, Firmen- und Verfasserdaten.

        Aufgeteilt in 4 Spalten:
        - Projekt: Name und Adresse
        - Gerüstbauer: Firma und Adresse
        - Verfasser: Name und Funktion
        - Datum und Dokumentnummer
        """
        from datetime import datetime

        height = 60
        col_width = width / 4

        # Standardwerte
        if not date:
            date = datetime.now().strftime("%B %Y")

        svg = f'''
  <!-- Fusszeile -->
  <g id="footer">
    <rect x="{x}" y="{y}" width="{width}" height="{height}" fill="none" stroke="#333" stroke-width="1"/>
    <line x1="{x + col_width}" y1="{y}" x2="{x + col_width}" y2="{y + height}" stroke="#333" stroke-width="0.5"/>
    <line x1="{x + col_width*2}" y1="{y}" x2="{x + col_width*2}" y2="{y + height}" stroke="#333" stroke-width="0.5"/>
    <line x1="{x + col_width*3}" y1="{y}" x2="{x + col_width*3}" y2="{y + height}" stroke="#333" stroke-width="0.5"/>

    <!-- Spalte 1: Projekt -->
    <text x="{x + 10}" y="{y + 18}" font-family="Arial" font-size="10" font-weight="bold" fill="#333">Projekt:</text>
    <text x="{x + 10}" y="{y + 33}" font-family="Arial" font-size="10" fill="#333">{project_name}</text>
    <text x="{x + 10}" y="{y + 48}" font-family="Arial" font-size="9" fill="#666">{project_address}</text>

    <!-- Spalte 2: Gerüstbauer -->
    <text x="{x + col_width + 10}" y="{y + 18}" font-family="Arial" font-size="10" font-weight="bold" fill="#333">Gerüstbauer:</text>
    <text x="{x + col_width + 10}" y="{y + 33}" font-family="Arial" font-size="10" fill="#333">{company_name}</text>
    <text x="{x + col_width + 10}" y="{y + 48}" font-family="Arial" font-size="9" fill="#666">{company_address}</text>

    <!-- Spalte 3: Verfasser -->
    <text x="{x + col_width*2 + 10}" y="{y + 18}" font-family="Arial" font-size="10" font-weight="bold" fill="#333">Verfasser:</text>
    <text x="{x + col_width*2 + 10}" y="{y + 33}" font-family="Arial" font-size="10" fill="#333">{author_name}</text>
    <text x="{x + col_width*2 + 10}" y="{y + 48}" font-family="Arial" font-size="9" fill="#666">{author_role}</text>

    <!-- Spalte 4: Datum -->
    <text x="{x + col_width*3 + 10}" y="{y + 18}" font-family="Arial" font-size="10" font-weight="bold" fill="#333">Datum:</text>
    <text x="{x + col_width*3 + 10}" y="{y + 33}" font-family="Arial" font-size="10" fill="#333">{date}</text>
    <text x="{x + width - 10}" y="{y + 48}" font-family="Arial" font-size="12" font-weight="bold" text-anchor="end" fill="#1a365d">{document_id}</text>
  </g>
'''
        return svg

    def _north_arrow(self, x: int, y: int, size: int = 40) -> str:
        """
        Nordpfeil für Grundrisse.

        Args:
            x, y: Position
            size: Grösse des Pfeils
        """
        return f'''
  <!-- Nordpfeil -->
  <g transform="translate({x}, {y})">
    <text x="0" y="0" font-family="Arial" font-size="14" font-weight="bold" fill="#333">N</text>
    <line x1="7" y1="10" x2="7" y2="{size}" stroke="#333" stroke-width="2"/>
    <polygon points="7,{size} 3,{size-8} 11,{size-8}" fill="#333"/>
  </g>
'''

    def _height_scale(
        self,
        x: int,
        y: int,
        max_height_m: float,
        scale_px_per_m: float,
        interval_m: float = 2.0
    ) -> str:
        """
        Höhenkoten-Skala für Ansichten und Schnitte.

        Args:
            x, y: Position (unten links der Skala)
            max_height_m: Maximale Höhe in Metern
            scale_px_per_m: Pixel pro Meter
            interval_m: Intervall der Markierungen (default 2m)
        """
        svg = f'''
  <!-- Höhenskala -->
  <g id="height-scale">
    <line x1="{x}" y1="{y}" x2="{x}" y2="{y - max_height_m * scale_px_per_m}" stroke="#333" stroke-width="1"/>
'''
        # Markierungen
        current_height = 0
        while current_height <= max_height_m:
            mark_y = y - current_height * scale_px_per_m
            svg += f'    <line x1="{x-5}" y1="{mark_y}" x2="{x}" y2="{mark_y}" stroke="#333" stroke-width="1"/>\n'
            svg += f'    <text x="{x-8}" y="{mark_y + 3}" font-family="Arial" font-size="8" text-anchor="end" fill="#333">{current_height:.0f}m</text>\n'
            current_height += interval_m

        svg += '  </g>\n'
        return svg

    def _layer_labels(
        self,
        x: int,
        y_ground: int,
        layer_height_m: float,
        num_layers: int,
        scale_px_per_m: float
    ) -> str:
        """
        Lagenbeschriftung für Gerüst-Ansichten.

        Args:
            x: X-Position für Labels
            y_ground: Y-Position des Bodens
            layer_height_m: Höhe pro Lage in Metern
            num_layers: Anzahl Lagen
            scale_px_per_m: Pixel pro Meter
        """
        svg = '''
  <!-- Lagenbeschriftung -->
  <g id="layer-labels">
'''
        for i in range(num_layers):
            layer_num = i + 1
            layer_y = y_ground - (i * layer_height_m + layer_height_m / 2) * scale_px_per_m
            svg += f'    <text x="{x}" y="{layer_y}" font-family="Arial" font-size="9" fill="#0066cc">{layer_num}. Lage</text>\n'

        svg += '  </g>\n'
        return svg

    def _compact_legend(self, x: int, y: int) -> str:
        """Kompakte Legende für Fassaden-Auswahl (nur Klick-Hinweis)"""
        return f'''
  <!-- Kompakte Legende -->
  <g transform="translate({x}, {y})">
    <rect x="0" y="0" width="90" height="30" fill="{self.COLORS['legend_bg']}" stroke="{self.COLORS['legend_border']}" rx="3" opacity="0.9"/>
    <text x="45" y="12" text-anchor="middle" font-family="Arial" font-size="8" fill="{self.COLORS['text_light']}">Fassade anklicken</text>
    <text x="45" y="23" text-anchor="middle" font-family="Arial" font-size="8" fill="{self.COLORS['text_light']}">zum Auswählen</text>
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

    def generate_cross_section(self, building: BuildingData, width: int = 700, height: int = 480, professional: bool = False) -> str:
        """
        Generiert saubere technische Schnittansicht.
        Minimalistisch ohne dekorative Elemente.

        Args:
            professional: Wenn True, werden Schraffur-Patterns verwendet.
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

        # SVG Header - mit oder ohne Patterns
        if professional:
            svg = self._svg_header_professional(width, height, f"Gebäudeschnitt - {building.address}")
        else:
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
            building, scale, ground_y, margin, width, height, scaffold_width, draw_width, eave_h, ridge_h, professional
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
                                    draw_width: float, eave_h: float, ridge_h: float, professional: bool = False) -> str:
        """Zeichnet sauberen technischen Gebäudeschnitt."""
        svg = ""

        # Füllfarben für Gebäude und Gerüst
        building_fill = "url(#hatch)" if professional else "#e0e0e0"
        scaffold_fill = "url(#scaffold-pattern)" if professional else "#fff3cd"

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
        fill="{scaffold_fill}" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
'''
        # Verankerungen
        for h in [eave_h * 0.3, eave_h * 0.6, eave_h * 0.9]:
            cy = ground_y - h * scale
            svg += f'  <circle cx="{scaffold_left_x + scaffold_width/2}" cy="{cy}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Gebäude - einfacher Umriss mit Schraffur
        svg += f'''
  <!-- Gebäude -->
  <rect x="{building_x}" y="{ground_y - eave_height_px}" width="{building_width_px}" height="{eave_height_px}"
        fill="{building_fill}" stroke="#333" stroke-width="2"/>
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
        fill="{scaffold_fill}" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="2"/>
'''
        for h in [eave_h * 0.3, eave_h * 0.6, eave_h * 0.9]:
            cy = ground_y - h * scale
            svg += f'  <circle cx="{scaffold_right_x + scaffold_width/2}" cy="{cy}" r="4" fill="{self.COLORS["anchor"]}"/>\n'

        # Lagenbeschriftung (2m pro Lage) - links vom linken Gerüst
        layer_height_m = 2.0
        num_layers = int(ridge_h / layer_height_m) + 1
        svg += self._layer_labels(
            x=scaffold_left_x - 8,
            y_ground=ground_y,
            layer_height_m=layer_height_m,
            num_layers=min(num_layers, 15),
            scale_px_per_m=scale
        )

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

    def generate_elevation(self, building: BuildingData, width: int = 700, height: int = 480, professional: bool = False) -> str:
        """
        Generiert saubere technische Fassadenansicht.
        Minimalistisch ohne dekorative Elemente.

        Args:
            professional: Wenn True, werden Schraffur-Patterns verwendet.
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

        # Füllfarben für Gebäude und Gerüst
        building_fill = "url(#hatch)" if professional else "#e0e0e0"
        scaffold_fill = "url(#scaffold-pattern)" if professional else "#fff3cd"

        # SVG Header - mit oder ohne Patterns
        if professional:
            svg = self._svg_header_professional(width, height, f"Fassadenansicht - {building.address}")
        else:
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
        fill="{scaffold_fill}" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="1.5"/>
'''

        # Gebäude - einfacher Umriss mit Schraffur
        svg += f'''
  <!-- Gebäude -->
  <rect x="{building_x}" y="{ground_y - eave_height_px}" width="{building_width_px}" height="{eave_height_px}"
        fill="{building_fill}" stroke="#333" stroke-width="2"/>
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
        fill="{scaffold_fill}" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="1.5"/>
'''

        # Verankerungspunkte (3 Stück pro Seite)
        for ratio in [0.25, 0.5, 0.75]:
            anchor_y = ground_y - eave_h * ratio * scale
            svg += f'  <circle cx="{scaffold_left_x + scaffold_width/2}" cy="{anchor_y}" r="3" fill="{self.COLORS["anchor"]}"/>\n'
            svg += f'  <circle cx="{scaffold_right_x + scaffold_width/2}" cy="{anchor_y}" r="3" fill="{self.COLORS["anchor"]}"/>\n'

        # Lagenbeschriftung (2m pro Lage)
        layer_height_m = 2.0
        num_layers = int(ridge_h / layer_height_m) + 1
        svg += self._layer_labels(
            x=scaffold_left_x - 5,
            y_ground=ground_y,
            layer_height_m=layer_height_m,
            num_layers=min(num_layers, 15),  # Max 15 Lagen anzeigen
            scale_px_per_m=scale
        )

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

    def generate_floor_plan(self, building: BuildingData, width: int = 600, height: int = 500, compact: bool = False, professional: bool = False) -> str:
        """
        Generiert sauberen technischen Grundriss.
        Verwendet echte Polygon-Daten falls vorhanden.

        Args:
            compact: Wenn True, minimale Darstellung für Fassaden-Auswahl
                     (kein Titel, keine Info-Box, kleine Legende)
            professional: Wenn True, werden Schraffur-Patterns verwendet.
        """
        # Margins anpassen: compact = mehr Platz für Polygon
        if compact:
            margin = {'top': 20, 'right': 100, 'bottom': 40, 'left': 20}
        else:
            margin = {'top': 60, 'right': 160, 'bottom': 80, 'left': 50}

        draw_width = width - margin['left'] - margin['right']
        draw_height = height - margin['top'] - margin['bottom']

        # Dimensionen - Bounding Box wenn vorhanden, sonst Seitenlängen
        if building.bbox_width_m and building.bbox_depth_m:
            # Verwende Bounding Box Dimensionen für korrekte Skalierung
            poly_width = building.bbox_width_m
            poly_height = building.bbox_depth_m
        else:
            poly_width = building.length_m
            poly_height = building.width_m

        building_with_scaffold = max(poly_width, poly_height) + 6
        # Compact mode: mehr Skalierung (0.92 statt 0.85)
        scale_factor = 0.92 if compact else 0.85
        scale = min(draw_width, draw_height) / building_with_scaffold * scale_factor

        # Zentrieren
        center_x = margin['left'] + draw_width / 2
        center_y = margin['top'] + draw_height / 2

        # SVG Header - mit oder ohne Patterns
        if professional:
            svg = self._svg_header_professional(width, height, f"Grundriss - {building.address}")
        else:
            svg = self._svg_header(width, height, f"Grundriss - {building.address}")

        # Hintergrund
        svg += f'  <rect width="{width}" height="{height}" fill="#f8f9fa"/>\n'

        # Anzahl Seiten für Titel
        num_sides = len(building.sides) if building.sides else 4

        # Titel nur im Normal-Modus
        if not compact:
            shape_info = f" ({num_sides} Seiten)" if num_sides != 4 else ""
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
                building, scale, center_x, center_y, width, height, margin, compact, professional
            )
        else:
            svg += self._draw_rectangle_floor_plan(
                building, scale, center_x, center_y, width, height, margin, professional
            )

        # Legende - compact: kleine Version rechts oben
        if compact:
            svg += self._compact_legend(width - 95, 5)
        else:
            legend_items = [
                {'type': 'rect', 'fill': '#e0e0e0', 'stroke': '#333', 'label': 'Gebäude'},
                {'type': 'rect', 'fill': '#fff3cd', 'stroke': self.COLORS['scaffold_stroke'], 'label': f'Gerüst {building.width_class}'},
                {'type': 'circle', 'fill': self.COLORS['anchor'], 'label': 'Verankerung'},
            ]
            svg += self._legend(width - 155, 55, legend_items)

        # Gebäude Info - nur im Normal-Modus
        if not compact:
            svg += self._building_info_box(margin['left'], height - 65, building)

        # Massstab
        if compact:
            svg += self._scale_bar(20, height - 15, scale, 10)
        else:
            svg += self._scale_bar(width - 140, height - 35, scale, 10)

        # Nordpfeil
        svg += self._north_arrow(width - 25, height - 25)

        # Koordinaten-Info - nur im Normal-Modus
        if not compact:
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
                                   width: int, height: int, margin: dict,
                                   compact: bool = False, professional: bool = False) -> str:
        """Zeichnet Grundriss mit echtem Polygon.

        Args:
            compact: Im Compact-Modus kleinere Labels, keine Richtungsangabe
            professional: Wenn True, werden Schraffur-Patterns verwendet.
        """
        svg = ""
        coords = building.polygon_coordinates
        sides = building.sides or []

        # Füllfarben für Gebäude und Gerüst
        building_fill = "url(#hatch)" if professional else "#e0e0e0"
        scaffold_fill = "url(#scaffold-pattern)" if professional else "#fff3cd"

        if not coords or len(coords) < 3:
            return self._draw_rectangle_floor_plan(building, scale, center_x, center_y, width, height, margin, professional)

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
        fill="{scaffold_fill}" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="1.5" rx="2"/>
'''

        # Innerer Bereich (Gebäude-Polygon - Hintergrund)
        svg += f'''
  <!-- Gebäude-Polygon Hintergrund -->
  <polygon points="{points_str}"
           fill="{building_fill}" stroke="none"/>
'''

        # Zonen-Overlays zeichnen (falls vorhanden)
        zones = building.zones or []
        if zones:
            svg += '  <!-- Gebäude-Zonen -->\n'
            for zone in zones:
                zone_type = zone.get('type', 'unknown')
                zone_name = zone.get('name', 'Zone')
                zone_indices = zone.get('polygon_point_indices', [])
                beruesten = zone.get('beruesten', True)
                zone_color = ZONE_COLORS.get(zone_type, ZONE_COLORS['unknown'])

                # Zone nur zeichnen wenn Indizes vorhanden und Zone eingerüstet wird
                if zone_indices and len(zone_indices) >= 3:
                    # Sub-Polygon aus Indizes erstellen
                    zone_coords = [coords[idx] for idx in zone_indices if idx < len(coords)]
                    if len(zone_coords) >= 3:
                        zone_svg_points = [to_svg(c[0], c[1]) for c in zone_coords]
                        zone_points_str = " ".join([f"{p[0]:.1f},{p[1]:.1f}" for p in zone_svg_points])

                        # Zone-Polygon mit Farbe
                        fill_color = zone_color['fill'] if beruesten else '#f5f5f5'
                        stroke_color = zone_color['stroke'] if beruesten else '#bdbdbd'
                        opacity = '0.7' if beruesten else '0.4'

                        svg += f'''  <polygon points="{zone_points_str}"
           fill="{fill_color}" fill-opacity="{opacity}"
           stroke="{stroke_color}" stroke-width="2" stroke-dasharray="5,3"/>
'''
                        # Zone-Label im Zentrum
                        zone_center_x = sum(p[0] for p in zone_svg_points) / len(zone_svg_points)
                        zone_center_y = sum(p[1] for p in zone_svg_points) / len(zone_svg_points)
                        height_m = zone.get('gebaeudehoehe_m', 0)

                        svg += f'''  <text x="{zone_center_x:.1f}" y="{zone_center_y:.1f}"
        font-size="10" font-weight="bold" fill="{stroke_color}"
        text-anchor="middle" dominant-baseline="middle">{zone_name}</text>
  <text x="{zone_center_x:.1f}" y="{zone_center_y + 12:.1f}"
        font-size="8" fill="{stroke_color}"
        text-anchor="middle">{height_m:.1f}m</text>
'''

        # Direction-to-Index Mapping für Fassaden erstellen
        direction_to_indices: Dict[str, List[int]] = {}
        for i, side in enumerate(sides):
            direction = side.get('direction', '')
            side_index = side.get('index', i)
            if direction:
                if direction not in direction_to_indices:
                    direction_to_indices[direction] = []
                direction_to_indices[direction].append(side_index)

        # Facade-to-Zone Mapping erstellen
        facade_to_zone: Dict[int, Dict[str, Any]] = {}
        for zone in zones:
            zone_type = zone.get('type', 'unknown')
            zone_name = zone.get('name', 'Zone')
            zone_color = ZONE_COLORS.get(zone_type, ZONE_COLORS['unknown'])
            beruesten = zone.get('beruesten', True)
            # fassaden_ids enthält Richtungsstrings wie ['N', 'E', 'S']
            fassaden_ids = zone.get('fassaden_ids', [])
            for direction in fassaden_ids:
                # Alle Fassaden mit dieser Richtung der Zone zuordnen
                for idx in direction_to_indices.get(direction, []):
                    facade_to_zone[idx] = {
                        'type': zone_type,
                        'name': zone_name,
                        'color': zone_color,
                        'beruesten': beruesten
                    }

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

            # Zone-basierte Farbe ermitteln
            zone_info = facade_to_zone.get(side_index)
            if zone_info:
                stroke_color = zone_info['color']['stroke']
                stroke_width = 4 if zone_info['beruesten'] else 2
            else:
                stroke_color = self.COLORS['building_stroke']
                stroke_width = 3

            # Fassaden-Segment als klickbare Linie
            svg += f'''  <line x1="{svg_start[0]:.1f}" y1="{svg_start[1]:.1f}" x2="{svg_end[0]:.1f}" y2="{svg_end[1]:.1f}"
        class="facade-segment"
        data-facade-index="{side_index}"
        data-facade-length="{length:.2f}"
        data-facade-direction="{direction}"
        stroke="{stroke_color}" stroke-width="{stroke_width}" stroke-linecap="round"/>
'''

        # Ständerpositionen entlang der Fassaden (alle 2.57m = Standard-Feldlänge)
        FIELD_LENGTH = 2.57  # Layher Blitz 70 Standard-Feldlänge
        SCAFFOLD_OFFSET = 0.35  # Abstand Gebäude zu Gerüst (30cm + halbe Gangbreite)
        svg += '  <!-- Gerüst-Ständer -->\n'

        for i, side in enumerate(sides):
            side_index = side.get('index', i)
            length = side.get('length_m', 0)

            # Nur Ständer zeichnen wenn Fassade lang genug
            if length < 1.0:
                continue

            # Segment-Koordinaten
            if i < len(coords) - 1:
                start = coords[i]
                end = coords[i + 1]
            else:
                start = coords[i]
                end = coords[0]

            # Richtungsvektor und Normale berechnen
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            seg_len = (dx**2 + dy**2)**0.5
            if seg_len == 0:
                continue

            # Einheitsvektor entlang Fassade
            ux = dx / seg_len
            uy = dy / seg_len
            # Normale nach aussen (für Gerüst-Offset)
            nx = -uy
            ny = ux

            # Anzahl Felder berechnen
            num_fields = max(1, int(length / FIELD_LENGTH))
            actual_field_len = length / num_fields

            # Ständer an jedem Feldende platzieren (inkl. Start und Ende)
            for field_idx in range(num_fields + 1):
                # Position entlang der Fassade
                t = field_idx * actual_field_len
                pos_x = start[0] + ux * t + nx * SCAFFOLD_OFFSET
                pos_y = start[1] + uy * t + ny * SCAFFOLD_OFFSET

                svg_pos = to_svg(pos_x, pos_y)

                # Ständer als kleiner Kreis mit Kreuz
                svg += f'''  <circle cx="{svg_pos[0]:.1f}" cy="{svg_pos[1]:.1f}" r="3"
          fill="#ef4444" stroke="#991b1b" stroke-width="1"
          class="scaffold-post" data-facade="{side_index}" data-field="{field_idx}"/>
'''

        # Seiten-Beschriftungen
        svg += '  <!-- Fassaden-Beschriftungen -->\n'

        # Compact: kleinere Labels, weniger Offset
        min_length_for_label = 1.0 if compact else 0.5
        font_size_main = 8 if compact else 9
        font_size_sub = 7 if compact else 8
        label_offset_factor = 1.0 if compact else 1.5

        for i, side in enumerate(sides):
            if side.get('length_m', 0) < min_length_for_label:
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
                label_x = svg_mid[0] + nx * scale * label_offset_factor
                label_y = svg_mid[1] - ny * scale * label_offset_factor
            else:
                label_x, label_y = svg_mid

            # Höhe aus Side-Daten (pro Fassade)
            traufhoehe = side.get('traufhoehe_m')
            height_str = f"H:{traufhoehe:.1f}m" if traufhoehe else ""

            # Compact: nur Index + Länge + Höhe, Normal: Index + Richtung + Länge + Höhe
            if compact:
                svg += f'  <text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle" font-family="Arial" font-size="{font_size_main}" font-weight="bold" fill="{self.COLORS["text"]}" data-label-for="{side_index}">[{side_index+1}]</text>\n'
                svg += f'  <text x="{label_x:.1f}" y="{label_y + 9:.1f}" text-anchor="middle" font-family="Arial" font-size="{font_size_sub}" fill="{self.COLORS["text_light"]}">{length:.1f}m</text>\n'
                if height_str:
                    svg += f'  <text x="{label_x:.1f}" y="{label_y + 17:.1f}" text-anchor="middle" font-family="Arial" font-size="{font_size_sub}" fill="{self.COLORS["dimension"]}">{height_str}</text>\n'
            else:
                svg += f'  <text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle" font-family="Arial" font-size="{font_size_main}" font-weight="bold" fill="{self.COLORS["text"]}" data-label-for="{side_index}">[{side_index+1}] {direction}</text>\n'
                svg += f'  <text x="{label_x:.1f}" y="{label_y + 10:.1f}" text-anchor="middle" font-family="Arial" font-size="{font_size_sub}" fill="{self.COLORS["text_light"]}">{length:.1f}m</text>\n'
                if height_str:
                    svg += f'  <text x="{label_x:.1f}" y="{label_y + 19:.1f}" text-anchor="middle" font-family="Arial" font-size="{font_size_sub}" fill="{self.COLORS["dimension"]}">{height_str}</text>\n'

        # Verankerungspunkte: An Ecken + alle 4m entlang der Fassade
        ANCHOR_SPACING = 4.0  # Meter zwischen Verankerungen
        svg += '  <!-- Verankerungspunkte -->\n'

        # Ecken-Verankerungen
        for i, (px, py) in enumerate(svg_points[:-1]):
            svg += f'''  <g class="anchor-point corner">
    <circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="{self.COLORS["anchor"]}" stroke="#1e40af" stroke-width="1"/>
    <line x1="{px - 3:.1f}" y1="{py:.1f}" x2="{px + 3:.1f}" y2="{py:.1f}" stroke="white" stroke-width="1.5"/>
    <line x1="{px:.1f}" y1="{py - 3:.1f}" x2="{px:.1f}" y2="{py + 3:.1f}" stroke="white" stroke-width="1.5"/>
  </g>
'''

        # Zwischen-Verankerungen entlang langer Fassaden
        for i, side in enumerate(sides):
            length = side.get('length_m', 0)
            if length <= ANCHOR_SPACING:
                continue

            # Segment-Koordinaten
            if i < len(coords) - 1:
                start = coords[i]
                end = coords[i + 1]
            else:
                start = coords[i]
                end = coords[0]

            dx = end[0] - start[0]
            dy = end[1] - start[1]
            seg_len = (dx**2 + dy**2)**0.5
            if seg_len == 0:
                continue

            ux = dx / seg_len
            uy = dy / seg_len

            # Anzahl Zwischenverankerungen
            num_anchors = int(length / ANCHOR_SPACING)
            if num_anchors > 1:
                spacing = length / num_anchors
                for anchor_idx in range(1, num_anchors):
                    t = anchor_idx * spacing
                    pos_x = start[0] + ux * t
                    pos_y = start[1] + uy * t
                    svg_pos = to_svg(pos_x, pos_y)

                    svg += f'''  <g class="anchor-point intermediate">
    <circle cx="{svg_pos[0]:.1f}" cy="{svg_pos[1]:.1f}" r="4" fill="{self.COLORS["anchor"]}" stroke="#3b82f6" stroke-width="1"/>
    <line x1="{svg_pos[0] - 2:.1f}" y1="{svg_pos[1]:.1f}" x2="{svg_pos[0] + 2:.1f}" y2="{svg_pos[1]:.1f}" stroke="white" stroke-width="1"/>
  </g>
'''

        # Zugänge (Treppen) zeichnen
        zugaenge = building.zugaenge or []
        if zugaenge:
            svg += '  <!-- Gerüst-Zugänge -->\n'

            # Direction-to-Facade Mapping
            direction_to_facade: Dict[str, Dict[str, Any]] = {}
            for i, side in enumerate(sides):
                direction = side.get('direction', '')
                if direction and direction not in direction_to_facade:
                    # Speichere erste Fassade dieser Richtung
                    if i < len(coords) - 1:
                        start = coords[i]
                        end = coords[i + 1]
                    else:
                        start = coords[i]
                        end = coords[0]
                    direction_to_facade[direction] = {
                        'start': start,
                        'end': end,
                        'length': side.get('length_m', 0)
                    }

            for zugang in zugaenge:
                zugang_id = zugang.get('id', 'Z?')
                fassade_id = zugang.get('fassade_id', '')
                position_percent = zugang.get('position_percent', 0.5)

                facade_data = direction_to_facade.get(fassade_id)
                if not facade_data:
                    continue

                start = facade_data['start']
                end = facade_data['end']

                # Position auf der Fassade berechnen
                pos_x = start[0] + (end[0] - start[0]) * position_percent
                pos_y = start[1] + (end[1] - start[1]) * position_percent

                # Normale für Offset nach aussen
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                length = (dx**2 + dy**2)**0.5
                if length > 0:
                    nx = -dy / length
                    ny = dx / length
                    # Zugang leicht nach aussen versetzen
                    pos_x += nx * 0.8
                    pos_y += ny * 0.8

                svg_pos = to_svg(pos_x, pos_y)

                # Zugang als gelbes Rechteck mit Beschriftung
                svg += f'''  <g class="zugang" id="zugang-{zugang_id}">
    <rect x="{svg_pos[0] - 8:.1f}" y="{svg_pos[1] - 12:.1f}" width="16" height="24"
          fill="#FFC107" stroke="#F57F17" stroke-width="1.5" rx="2"/>
    <text x="{svg_pos[0]:.1f}" y="{svg_pos[1] + 3:.1f}"
          font-family="Arial" font-size="9" font-weight="bold"
          text-anchor="middle" fill="#333">{zugang_id}</text>
  </g>
'''

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
                                    width: int, height: int, margin: dict, professional: bool = False) -> str:
        """Zeichnet rechteckigen Grundriss (Fallback)."""
        svg = ""

        # Füllfarben für Gebäude und Gerüst
        building_fill = "url(#hatch)" if professional else "#e0e0e0"
        scaffold_fill = "url(#scaffold-pattern)" if professional else "#fff3cd"

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
        fill="{scaffold_fill}" stroke="{self.COLORS['scaffold_stroke']}" stroke-width="1.5" rx="2"/>
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
        fill="{building_fill}" stroke="{self.COLORS['building_stroke']}" stroke-width="2"/>
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

    # ========================================================================
    # PROFESSIONAL MODE - Hochwertige SVGs für Ausdrucke
    # ========================================================================

    def generate_professional_floor_plan(
        self,
        building: BuildingData,
        project_name: str = "",
        project_address: str = "",
        author_name: str = "",
        author_role: str = "",
        width: int = 1200,
        height: int = 900
    ) -> str:
        """
        Generiert professionellen Grundriss im Stil der Claude.ai-Vorlagen.

        - Grosses Format (1200×900)
        - Schraffur-Pattern für Gebäude
        - Gerüst mit Ständerpunkten
        - Professioneller Titelblock + Fusszeile
        - Detaillierte Legende
        - Nordpfeil und Massstab
        """
        margin = {'top': 100, 'right': 250, 'bottom': 90, 'left': 80}
        draw_width = width - margin['left'] - margin['right']
        draw_height = height - margin['top'] - margin['bottom']

        # Dimensionen
        if building.bbox_width_m and building.bbox_depth_m:
            poly_width = building.bbox_width_m
            poly_height = building.bbox_depth_m
        else:
            poly_width = building.length_m
            poly_height = building.width_m

        # Skalierung mit Gerüst-Offset (3m pro Seite)
        scaffold_offset_m = 3.0
        total_width = poly_width + 2 * scaffold_offset_m
        total_height = poly_height + 2 * scaffold_offset_m

        scale = min(draw_width / total_width, draw_height / total_height) * 0.85

        # Zentrieren
        center_x = margin['left'] + draw_width / 2
        center_y = margin['top'] + draw_height / 2

        # Massstab berechnen (für Anzeige)
        meters_per_100px = 100 / scale
        if meters_per_100px < 5:
            scale_text = "1:50"
        elif meters_per_100px < 10:
            scale_text = "1:100"
        elif meters_per_100px < 25:
            scale_text = "1:200"
        else:
            scale_text = f"1:{int(meters_per_100px * 10)}"

        # SVG starten
        svg = self._svg_header_professional(width, height, f"Grundriss Gerüst - {building.address}")

        # Hintergrund
        svg += f'  <rect width="{width}" height="{height}" fill="white"/>\n'

        # Titelblock
        svg += self._professional_title_block(
            x=20, y=20, width=width - 40,
            title=f"GRUNDRISS GERÜST - {building.address.upper()[:50]}",
            subtitle=project_name or "Fassadengerüst",
            scale=scale_text,
            system="Layher Blitz 70"
        )

        # Zeichenbereich
        svg += self._draw_professional_floor_plan_content(
            building, scale, center_x, center_y, scaffold_offset_m
        )

        # Legende
        svg += self._professional_legend(width - 230, margin['top'] + 20)

        # Nordpfeil
        svg += self._north_arrow(60, height - 150, size=50)

        # Massstab
        svg += self._scale_bar(margin['left'], height - 110, scale, 20)

        # Fusszeile
        svg += self._professional_footer(
            x=20, y=height - 80, width=width - 40,
            project_name=project_name or "Gerüstprojekt",
            project_address=project_address or building.address,
            author_name=author_name,
            author_role=author_role,
            document_id="Grundriss"
        )

        svg += self._svg_footer()
        return svg

    def _draw_professional_floor_plan_content(
        self,
        building: BuildingData,
        scale: float,
        center_x: float,
        center_y: float,
        scaffold_offset_m: float
    ) -> str:
        """Zeichnet den Inhalt des professionellen Grundrisses."""
        svg = ""
        coords = building.polygon_coordinates
        sides = building.sides or []

        if not coords or len(coords) < 3:
            # Fallback auf Rechteck
            return self._draw_professional_rectangle_floor_plan(
                building, scale, center_x, center_y, scaffold_offset_m
            )

        # Koordinaten zentrieren
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        center_geo_x = (min_x + max_x) / 2
        center_geo_y = (min_y + max_y) / 2

        def to_svg(gx, gy):
            sx = center_x + (gx - center_geo_x) * scale
            sy = center_y - (gy - center_geo_y) * scale
            return sx, sy

        # SVG-Punkte
        svg_points = [to_svg(c[0], c[1]) for c in coords]
        points_str = " ".join([f"{p[0]:.1f},{p[1]:.1f}" for p in svg_points])

        # Bounding Box für Gerüst
        svg_xs = [p[0] for p in svg_points]
        svg_ys = [p[1] for p in svg_points]
        scaffold_px = scaffold_offset_m * scale

        bbox_min_x = min(svg_xs) - scaffold_px
        bbox_max_x = max(svg_xs) + scaffold_px
        bbox_min_y = min(svg_ys) - scaffold_px
        bbox_max_y = max(svg_ys) + scaffold_px

        # Gerüst-Zone (blau, mit Pattern)
        svg += f'''
  <!-- Gerüst-Zone -->
  <rect x="{bbox_min_x}" y="{bbox_min_y}"
        width="{bbox_max_x - bbox_min_x}" height="{bbox_max_y - bbox_min_y}"
        fill="url(#scaffold-pattern)" stroke="#0066CC" stroke-width="1.5" rx="2"/>
'''

        # Gebäude-Polygon (mit Schraffur)
        svg += f'''
  <!-- Gebäude -->
  <polygon points="{points_str}"
           fill="url(#hatch)" stroke="#333" stroke-width="2"/>
'''

        # Ständerpositionen (alle 2.5-3m entlang des Gerüsts)
        svg += '  <!-- Ständerpositionen -->\n'
        field_length_m = 2.57  # Layher Blitz Standard
        for i, side in enumerate(sides):
            if side['length_m'] < 1.0:
                continue

            start_geo = (side['start']['x'], side['start']['y'])
            end_geo = (side['end']['x'], side['end']['y'])

            # Normalen-Vektor für Offset nach aussen
            dx = end_geo[0] - start_geo[0]
            dy = end_geo[1] - start_geo[1]
            length = (dx**2 + dy**2)**0.5
            if length < 0.1:
                continue

            # Normalisieren und um 90° drehen (nach aussen)
            nx = -dy / length
            ny = dx / length

            # Offset nach aussen (1m vom Gebäude)
            offset_m = 1.0
            start_offset = (start_geo[0] + nx * offset_m, start_geo[1] + ny * offset_m)
            end_offset = (end_geo[0] + nx * offset_m, end_geo[1] + ny * offset_m)

            # Ständer entlang der Linie
            num_fields = max(1, int(side['length_m'] / field_length_m))
            for j in range(num_fields + 1):
                t = j / max(1, num_fields)
                px = start_offset[0] + t * (end_offset[0] - start_offset[0])
                py = start_offset[1] + t * (end_offset[1] - start_offset[1])
                sx, sy = to_svg(px, py)
                svg += f'  <circle cx="{sx:.1f}" cy="{sy:.1f}" r="4" fill="#0066CC"/>\n'

        # Verankerungspunkte (rot, an den Ecken)
        svg += '  <!-- Verankerungen -->\n'
        for i, (sx, sy) in enumerate(svg_points):
            # Versetzt nach aussen
            if i < len(svg_points) - 1:
                next_p = svg_points[i + 1]
            else:
                next_p = svg_points[0]
            if i > 0:
                prev_p = svg_points[i - 1]
            else:
                prev_p = svg_points[-1]

            # Richtung nach aussen (Durchschnitt der beiden Normalen)
            dx1 = sx - prev_p[0]
            dy1 = sy - prev_p[1]
            dx2 = next_p[0] - sx
            dy2 = next_p[1] - sy

            # Vereinfacht: Offset diagonal
            offset_px = 15
            svg += f'  <line x1="{sx:.1f}" y1="{sy:.1f}" x2="{sx + offset_px:.1f}" y2="{sy:.1f}" stroke="#CC0000" stroke-width="2"/>\n'

        # Fassaden-Labels
        svg += '  <!-- Fassaden-Labels -->\n'
        for i, side in enumerate(sides):
            if side['length_m'] < 2.0:
                continue

            mid_geo_x = (side['start']['x'] + side['end']['x']) / 2
            mid_geo_y = (side['start']['y'] + side['end']['y']) / 2
            mx, my = to_svg(mid_geo_x, mid_geo_y)

            # Label mit Richtung
            direction = side.get('direction', '')
            label = f"F{i+1}: {side['length_m']:.1f}m ({direction})"

            svg += f'  <text x="{mx:.1f}" y="{my:.1f}" text-anchor="middle" font-family="Arial" font-size="10" fill="#333">{label}</text>\n'

        return svg

    def _draw_professional_rectangle_floor_plan(
        self,
        building: BuildingData,
        scale: float,
        center_x: float,
        center_y: float,
        scaffold_offset_m: float
    ) -> str:
        """Fallback: Rechteckiger Grundriss für Gebäude ohne Polygon."""
        svg = ""

        building_w = building.length_m * scale
        building_h = building.width_m * scale
        scaffold_px = scaffold_offset_m * scale

        bx = center_x - building_w / 2
        by = center_y - building_h / 2

        # Gerüst-Zone
        svg += f'''
  <!-- Gerüst-Zone -->
  <rect x="{bx - scaffold_px}" y="{by - scaffold_px}"
        width="{building_w + 2*scaffold_px}" height="{building_h + 2*scaffold_px}"
        fill="url(#scaffold-pattern)" stroke="#0066CC" stroke-width="1.5" rx="2"/>
'''

        # Gebäude
        svg += f'''
  <!-- Gebäude -->
  <rect x="{bx}" y="{by}" width="{building_w}" height="{building_h}"
        fill="url(#hatch)" stroke="#333" stroke-width="2"/>
'''

        # Ständer entlang der Kanten
        svg += '  <!-- Ständerpositionen -->\n'
        field_length_px = 2.57 * scale
        offset = scaffold_px * 0.4

        # Oben
        for x in range(int(bx - offset), int(bx + building_w + offset), int(field_length_px)):
            svg += f'  <circle cx="{x}" cy="{by - offset}" r="4" fill="#0066CC"/>\n'
        # Unten
        for x in range(int(bx - offset), int(bx + building_w + offset), int(field_length_px)):
            svg += f'  <circle cx="{x}" cy="{by + building_h + offset}" r="4" fill="#0066CC"/>\n'
        # Links
        for y in range(int(by - offset), int(by + building_h + offset), int(field_length_px)):
            svg += f'  <circle cx="{bx - offset}" cy="{y}" r="4" fill="#0066CC"/>\n'
        # Rechts
        for y in range(int(by - offset), int(by + building_h + offset), int(field_length_px)):
            svg += f'  <circle cx="{bx + building_w + offset}" cy="{y}" r="4" fill="#0066CC"/>\n'

        # Masse
        svg += f'''
  <!-- Masse -->
  <text x="{center_x}" y="{by - scaffold_px - 10}" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold">{building.length_m:.1f} m</text>
  <text x="{bx - scaffold_px - 10}" y="{center_y}" text-anchor="middle" font-family="Arial" font-size="12" font-weight="bold" transform="rotate(-90, {bx - scaffold_px - 10}, {center_y})">{building.width_m:.1f} m</text>
'''

        return svg

    def _professional_legend(self, x: int, y: int) -> str:
        """Professionelle Legende mit allen Elementen."""
        return f'''
  <!-- Legende -->
  <rect x="{x}" y="{y}" width="200" height="180" fill="#f9f9f9" stroke="#333" stroke-width="1"/>
  <text x="{x + 10}" y="{y + 20}" font-family="Arial" font-size="12" font-weight="bold">Legende</text>

  <rect x="{x + 10}" y="{y + 32}" width="20" height="12" fill="url(#hatch)" stroke="#333"/>
  <text x="{x + 35}" y="{y + 42}" font-family="Arial" font-size="10">Gebäude</text>

  <rect x="{x + 10}" y="{y + 50}" width="20" height="12" fill="url(#scaffold-pattern)" stroke="#0066CC"/>
  <text x="{x + 35}" y="{y + 60}" font-family="Arial" font-size="10">Gerüst (Belag)</text>

  <circle cx="{x + 20}" cy="{y + 78}" r="4" fill="#0066CC"/>
  <text x="{x + 35}" y="{y + 82}" font-family="Arial" font-size="10">Ständer</text>

  <line x1="{x + 10}" y1="{y + 98}" x2="{x + 30}" y2="{y + 98}" stroke="#CC0000" stroke-width="2"/>
  <text x="{x + 35}" y="{y + 102}" font-family="Arial" font-size="10">Verankerung</text>

  <rect x="{x + 10}" y="{y + 112}" width="20" height="12" fill="#FFCC00" stroke="#333"/>
  <text x="{x + 35}" y="{y + 122}" font-family="Arial" font-size="10">Zugang</text>

  <text x="{x + 10}" y="{y + 145}" font-family="Arial" font-size="9" fill="#666">LF = 0.30 m | LG = 0.70 m</text>
  <text x="{x + 10}" y="{y + 160}" font-family="Arial" font-size="9" fill="#666">Breitenklasse: W09 (0.90 m)</text>
  <text x="{x + 10}" y="{y + 175}" font-family="Arial" font-size="9" fill="#666">Lastklasse: 3 (200 kg/m²)</text>
'''


# Singleton
_svg_generator: Optional[SVGGenerator] = None


def get_svg_generator() -> SVGGenerator:
    """Hole Singleton-Instanz des SVG-Generators"""
    global _svg_generator
    if _svg_generator is None:
        _svg_generator = SVGGenerator()
    return _svg_generator
