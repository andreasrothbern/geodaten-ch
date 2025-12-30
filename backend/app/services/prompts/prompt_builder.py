# backend/app/services/prompts/prompt_builder.py
"""
Prompt Builder
==============

Template-basierter Prompt-Aufbau für Claude SVG-Generierung.
Basiert auf docs/Export_Prompt_Claude.md als zentrale Vorlage.

Dieses Modul wird sowohl vom Backend (use_claude=true) als auch
vom Frontend (Export-Button → API) verwendet.

Verwendung:
    from app.services.prompts import get_prompt_builder

    builder = get_prompt_builder()
    prompt = await builder.build_svg_prompt(
        adresse="Bundesplatz 3, 3011 Bern",
        egid="2242547",
        dimensions={"traufhoehe_m": 14.5, "firsthoehe_m": 62.6},
        polygon=[[2600450, 1199830], ...],
        ...
    )

Stand: 29.12.2025
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .research_service import get_research_service, BuildingResearch

logger = logging.getLogger(__name__)


@dataclass
class PromptData:
    """Alle Daten die für den Prompt benötigt werden"""
    # Identifikation
    adresse: Optional[str] = None
    egid: Optional[str] = None
    coordinates: Optional[tuple] = None  # (E, N) LV95

    # Dimensionen
    traufhoehe_m: Optional[float] = None
    firsthoehe_m: Optional[float] = None
    floors: Optional[int] = None
    footprint_area_m2: Optional[float] = None

    # GWR-Daten
    gwr_category: Optional[str] = None
    gwr_construction_year: Optional[int] = None
    gwr_floors: Optional[int] = None
    gwr_area_m2: Optional[float] = None

    # Terrain
    terrain_height_m: Optional[float] = None
    terrain_slope_m: Optional[float] = None
    terrain_min_m: Optional[float] = None
    terrain_max_m: Optional[float] = None

    # Dach
    roof_type: Optional[str] = None
    roof_angle_deg: Optional[float] = None
    roof_orientation: Optional[str] = None
    roof_area_m2: Optional[float] = None
    roof_confidence: Optional[float] = None

    # Polygon
    polygon: Optional[List[List[float]]] = None
    sides: Optional[List[Dict[str, Any]]] = None

    # Zonen (falls bereits analysiert)
    zones: Optional[List[Dict[str, Any]]] = None

    # Recherche (dynamisch)
    research: Optional[BuildingResearch] = None


class PromptBuilder:
    """
    DEPRECATED: Verwende UnifiedPromptGenerator aus smart_building/ stattdessen.

    Diese Klasse wird nicht mehr verwendet. Alle Prompt-Generierung läuft
    jetzt über SmartBuildingService + UnifiedPromptGenerator für einheitliche
    Prompts bei Export UND automatischer SVG-Generierung.

    Migration:
        # Alt:
        from app.services.prompts import get_prompt_builder
        builder = get_prompt_builder()
        prompt = await builder.build_svg_prompt(...)

        # Neu:
        from app.services.smart_building import get_smart_building_service, get_prompt_generator
        service = get_smart_building_service()
        bundle = await service.collect_all_data(address)
        generator = get_prompt_generator()
        prompt = generator.generate(bundle, svg_type=SVGType.ALL)
    """

    def __init__(self):
        import warnings
        warnings.warn(
            "PromptBuilder ist deprecated. Verwende UnifiedPromptGenerator aus smart_building/.",
            DeprecationWarning,
            stacklevel=2
        )
        self.research_service = get_research_service()

    async def build_svg_prompt(
        self,
        adresse: Optional[str] = None,
        egid: Optional[str] = None,
        coordinates: Optional[tuple] = None,
        dimensions: Optional[Dict[str, Any]] = None,
        gwr_data: Optional[Dict[str, Any]] = None,
        terrain: Optional[Dict[str, Any]] = None,
        roof: Optional[Dict[str, Any]] = None,
        polygon: Optional[List[List[float]]] = None,
        sides: Optional[List[Dict[str, Any]]] = None,
        zones: Optional[List[Dict[str, Any]]] = None,
        svg_type: str = "all",  # "all", "grundriss", "ansicht", "schnitt"
        include_research: bool = True
    ) -> str:
        """
        Baut den vollständigen Prompt für SVG-Generierung.

        Args:
            adresse: Vollständige Adresse
            egid: EGID des Gebäudes
            coordinates: (E, N) LV95 Koordinaten
            dimensions: Dict mit traufhoehe_m, firsthoehe_m, floors
            gwr_data: GWR-Daten (category, construction_year, floors, area)
            terrain: Terrain-Daten (terrain_height_m, slope, min, max)
            roof: Dach-Daten (type, angle, orientation, area, confidence)
            polygon: Liste von [E, N] Koordinaten
            sides: Fassaden mit Länge und Richtung
            zones: Bereits analysierte Höhenzonen
            svg_type: Welche SVGs generiert werden sollen
            include_research: Dynamische Recherche durchführen

        Returns:
            Vollständiger Prompt-String
        """
        # Daten sammeln
        data = PromptData(
            adresse=adresse,
            egid=egid,
            coordinates=coordinates,
            polygon=polygon,
            sides=sides,
            zones=zones
        )

        # Dimensionen
        if dimensions:
            data.traufhoehe_m = dimensions.get('traufhoehe_m')
            data.firsthoehe_m = dimensions.get('firsthoehe_m')
            data.floors = dimensions.get('floors')
            data.footprint_area_m2 = dimensions.get('footprint_area_m2')

        # GWR-Daten
        if gwr_data:
            data.gwr_category = gwr_data.get('building_category')
            data.gwr_construction_year = gwr_data.get('construction_year')
            data.gwr_floors = gwr_data.get('floors')
            data.gwr_area_m2 = gwr_data.get('area_m2_gwr')

        # Terrain
        if terrain:
            data.terrain_height_m = terrain.get('terrain_height_m')
            data.terrain_slope_m = terrain.get('terrain_slope_m')
            data.terrain_min_m = terrain.get('terrain_min_m')
            data.terrain_max_m = terrain.get('terrain_max_m')

        # Dach
        if roof:
            data.roof_type = roof.get('roof_type')
            data.roof_angle_deg = roof.get('roof_angle_deg')
            data.roof_orientation = roof.get('roof_orientation')
            data.roof_area_m2 = roof.get('roof_area_m2')
            data.roof_confidence = roof.get('confidence')

        # Dynamische Recherche
        if include_research:
            data.research = await self.research_service.get_building_research(
                adresse=adresse,
                egid=egid,
                coordinates=coordinates,
                gwr_data=gwr_data
            )

        # Prompt aus Template bauen
        return self._render_template(data, svg_type)

    def _render_template(self, data: PromptData, svg_type: str) -> str:
        """Rendert das Template mit den Daten"""

        # Komplexität bestimmen
        is_complex = self._is_complex(data)

        # Gebäudeinfos aus Recherche oder Defaults
        building_name = "RECHERCHIEREN"
        building_type = self._get_building_type(data)
        architectural_style = "RECHERCHIEREN" if is_complex else "Standard (nicht relevant)"
        construction_year = data.gwr_construction_year or "-"

        if data.research and data.research.building_name:
            building_name = data.research.building_name
        if data.research and data.research.building_type:
            building_type = data.research.building_type
        if data.research and data.research.architectural_style:
            architectural_style = data.research.architectural_style
        if data.research and data.research.construction_year:
            construction_year = data.research.construction_year

        needs_research = building_name == "RECHERCHIEREN" or is_complex

        # SVG-Typ Beschreibung
        svg_type_desc = {
            "all": "Grundriss + Fassadenansicht + Gebäudeschnitt",
            "grundriss": "Grundriss",
            "ansicht": "Fassadenansicht",
            "schnitt": "Gebäudeschnitt"
        }.get(svg_type, svg_type)

        # Terrain-Referenz
        terrain_ref = "±0.00 (OK Terrain)"
        if data.terrain_height_m:
            terrain_ref = f"±0.00 = {data.terrain_height_m:.1f} m ü.M."

        # Prompt zusammenbauen
        prompt_parts = []

        # Header
        prompt_parts.append(f"# SVG-Generierung: {svg_type_desc}")
        prompt_parts.append("")

        # 1. Gebäude-Identifikation
        prompt_parts.append("## 1. Gebäude-Identifikation")
        prompt_parts.append("")
        prompt_parts.append(f"- **Adresse:** {data.adresse or 'Unbekannt'}")
        prompt_parts.append(f"- **EGID:** {data.egid or '-'}")
        if data.coordinates:
            prompt_parts.append(f"- **Koordinaten (LV95):** E {data.coordinates[0]:.0f}, N {data.coordinates[1]:.0f}")
        prompt_parts.append(f"- **Gebäudename:** {building_name}")
        prompt_parts.append(f"- **Gebäudetyp:** {building_type}")
        prompt_parts.append(f"- **Baustil:** {architectural_style}")
        prompt_parts.append(f"- **Baujahr:** {construction_year}")
        prompt_parts.append(f"- **Komplexität:** {'KOMPLEX (mehrere Zonen)' if is_complex else 'EINFACH'}")
        prompt_parts.append("")

        # 2. Recherche-Anweisung (wenn nötig)
        if needs_research:
            prompt_parts.append("## 2. RECHERCHE-ANWEISUNG")
            prompt_parts.append("")
            prompt_parts.append("> **WICHTIG:** Falls Gebäudename oder Baustil mit \"RECHERCHIEREN\" markiert:")
            prompt_parts.append("> 1. Suche das Gebäude anhand Adresse/EGID/Koordinaten")
            prompt_parts.append("> 2. Identifiziere den korrekten Gebäudenamen")
            prompt_parts.append("> 3. Bestimme Gebäudetyp und Baustil (z.B. Neugotik, Barock, Klassizismus, Modern)")
            prompt_parts.append("> 4. Ermittle charakteristische Architekturmerkmale (Fensterformen, Portal, Türme)")
            prompt_parts.append("> 5. Kläre Turmkonfiguration (Anzahl, Position, Form) falls vorhanden")
            prompt_parts.append("> 6. Validiere die unten angegebenen Höhenzonen gegen recherchierte Informationen")
            prompt_parts.append("> **Erst danach mit der SVG-Erstellung beginnen.**")
            prompt_parts.append("")

        # Recherche-Hints einfügen (falls vorhanden)
        if data.research and data.research.source != "fallback":
            hints = data.research.to_hints()
            if hints:
                prompt_parts.append("### Recherche-Ergebnis (gecacht)")
                prompt_parts.append("")
                prompt_parts.append(hints)
                prompt_parts.append("")

        # 3. Geometrische Basisdaten
        prompt_parts.append("## 3. Geometrische Basisdaten")
        prompt_parts.append("")
        prompt_parts.append("### Dimensionen")
        trauf_str = f"{data.traufhoehe_m:.1f} m" if data.traufhoehe_m else "unbekannt"
        first_str = f"{data.firsthoehe_m:.1f} m" if data.firsthoehe_m else "unbekannt"
        area_str = f"{data.footprint_area_m2:.0f} m²" if data.footprint_area_m2 else f"{data.gwr_area_m2} m²" if data.gwr_area_m2 else "-"
        prompt_parts.append(f"- **Traufhöhe:** {trauf_str}")
        prompt_parts.append(f"- **Firsthöhe:** {first_str}")
        prompt_parts.append(f"- **Geschosse:** {data.floors or data.gwr_floors or '-'}")
        prompt_parts.append(f"- **Grundfläche:** {area_str}")
        prompt_parts.append("")

        # Dach-Analyse
        if data.roof_type:
            prompt_parts.append("### Dach-Analyse (heuristisch berechnet)")
            roof_angle_str = f"{data.roof_angle_deg:.0f}°" if data.roof_angle_deg else "-"
            roof_area_str = f"{data.roof_area_m2:.0f} m²" if data.roof_area_m2 else "-"
            prompt_parts.append(f"- **Dachform:** {data.roof_type}")
            prompt_parts.append(f"- **Dachneigung:** {roof_angle_str}")
            prompt_parts.append(f"- **First-Ausrichtung:** {data.roof_orientation or '-'}")
            prompt_parts.append(f"- **Dachfläche:** {roof_area_str}")
            if data.roof_confidence:
                conf_text = "(niedrig = Schätzung)" if data.roof_confidence < 0.5 else "(hoch = verlässlich)"
                prompt_parts.append(f"- **Konfidenz:** {data.roof_confidence * 100:.0f}% {conf_text}")
            prompt_parts.append("")

        # Terrain
        prompt_parts.append("### Terrain (swissALTI3D)")
        if data.terrain_height_m:
            prompt_parts.append(f"- **Terrain-Höhe:** {data.terrain_height_m:.1f} m ü.M.")
            prompt_parts.append(f"- **Referenzpunkt:** Haupteingang = {terrain_ref}")
            if data.terrain_slope_m and data.terrain_slope_m > 1:
                prompt_parts.append(f"- **Hanglage:** Ja ({data.terrain_slope_m:.1f}m Differenz - unterschiedliche Gerüsthöhen nötig!)")
            else:
                prompt_parts.append("- **Hanglage:** Nein (eben)")
        else:
            prompt_parts.append("- Keine Terrain-Daten verfügbar")
        prompt_parts.append("")

        # Polygon-Daten
        prompt_parts.append("### Polygon-Daten")
        if data.polygon:
            polygon_points = len(data.polygon)
            if polygon_points > 10:
                prompt_parts.append(f"> **HINWEIS:** Komplexes Polygon mit {polygon_points} Punkten → **Vereinfachte Darstellung verwenden!**")
                prompt_parts.append("")
                # Bounding Box berechnen
                xs = [p[0] for p in data.polygon]
                ys = [p[1] for p in data.polygon]
                width = max(xs) - min(xs)
                depth = max(ys) - min(ys)
                prompt_parts.append("#### Vereinfachte Bounding-Box")
                prompt_parts.append(f"- **Länge (O-W):** ca. {width:.0f} m")
                prompt_parts.append(f"- **Breite (N-S):** ca. {depth:.0f} m")
            else:
                prompt_parts.append(f"- **Polygon-Punkte:** {polygon_points}")
        prompt_parts.append("")

        # Fassaden
        if data.sides and isinstance(data.sides, list) and len(data.sides) > 0:
            prompt_parts.append("### Fassaden")
            prompt_parts.append("| Seite | Länge (m) | Richtung |")
            prompt_parts.append("|-------|-----------|----------|")
            for i, side in enumerate(data.sides, 1):
                if isinstance(side, dict):
                    length = side.get('length_m', 0)
                    direction = side.get('direction', '-')
                    prompt_parts.append(f"| {i} | {length:.1f} | {direction} |")
            prompt_parts.append("")
        elif data.sides and isinstance(data.sides, int):
            # sides ist nur die Anzahl der Polygon-Punkte
            prompt_parts.append(f"### Polygon: {data.sides} Eckpunkte")
            prompt_parts.append("")

        # 4. GWR-Daten
        prompt_parts.append("## 4. GWR-Daten (Gebäude- und Wohnungsregister)")
        prompt_parts.append(f"- **Gebäudekategorie:** {data.gwr_category or '-'}")
        prompt_parts.append(f"- **Baujahr:** {data.gwr_construction_year or '-'}")
        prompt_parts.append(f"- **Geschosse (GWR):** {data.gwr_floors or '-'}")
        prompt_parts.append(f"- **Grundfläche (GWR):** {data.gwr_area_m2 or '-'} m²")
        prompt_parts.append("")

        # 5. Höhenzonen
        prompt_parts.append("## 5. Höhenzonen")
        prompt_parts.append("| Zone | Typ | Höhe | Traufe | Eingerüstet |")
        prompt_parts.append("|------|-----|------|--------|-------------|")

        zones_to_render = data.zones or []

        # Aus Recherche ergänzen falls keine Zonen definiert
        if not zones_to_render and data.research and data.research.suggested_zones:
            zones_to_render = data.research.suggested_zones

        # Fallback: Eine Standard-Zone
        if not zones_to_render:
            zones_to_render = [{
                "name": "Hauptgebäude",
                "type": "hauptgebaeude",
                "height_m": data.firsthoehe_m or 10,
                "traufhoehe_m": data.traufhoehe_m or 8,
                "scaffolding": True
            }]

        for zone in zones_to_render:
            name = zone.get('name', 'Zone')
            zone_type = zone.get('type', 'hauptgebaeude')
            height = zone.get('height_m') or zone.get('gebaeudehoehe_m') or '-'
            traufe = zone.get('traufhoehe_m', '-')
            scaffolding = "Ja" if zone.get('scaffolding', True) else "Nein (Spezialgerüst)"
            prompt_parts.append(f"| {name} | {zone_type} | {height} | {traufe} | {scaffolding} |")

        prompt_parts.append("")
        prompt_parts.append("### Zonen-Typen Legende")
        prompt_parts.append("- **hauptgebaeude** = Rechteckiger Hauptkörper mit Schraffur")
        prompt_parts.append("- **arkade** = Niedriger Bereich mit Rundbogen (Erdgeschoss)")
        prompt_parts.append("- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)")
        prompt_parts.append("- **turm** = Schmaler, hoher Turm (sonderkonstruktion)")
        prompt_parts.append("- **anbau** = Niedrigerer Anbau am Hauptgebäude")
        prompt_parts.append("- **innenhof** = Nicht einrüsten (Freifläche)")
        prompt_parts.append("")

        # Turmkonfiguration (aus Recherche)
        if data.research and data.research.tower_config:
            tc = data.research.tower_config
            prompt_parts.append("### Turmkonfiguration")
            prompt_parts.append(f"- **Anzahl:** {tc.get('count', 1)}")
            prompt_parts.append(f"- **Position:** {tc.get('position', 'zentral')}")
            prompt_parts.append(f"- **Form:** {tc.get('form', '-')}")
            if tc.get('height_m'):
                prompt_parts.append(f"- **Höhe:** ca. {tc['height_m']}m")
            prompt_parts.append("")

        # 6. Baustil-Merkmale (aus Recherche)
        prompt_parts.append("## 6. Baustil-Merkmale")
        if data.research and data.research.source != "fallback":
            if data.research.facade_style:
                prompt_parts.append(f"- **Fassadenstil:** {data.research.facade_style}")
            if data.research.special_features:
                prompt_parts.append(f"- **Besondere Elemente:** {', '.join(data.research.special_features)}")
        else:
            prompt_parts.append("- RECHERCHIEREN basierend auf Baustil")
        prompt_parts.append("")

        # 7. SVG Style-Vorgaben
        prompt_parts.append("## 7. SVG Style-Vorgaben")
        prompt_parts.append("")
        prompt_parts.append("```xml")
        prompt_parts.append("<defs>")
        prompt_parts.append("  <!-- Schraffur für Gebäude -->")
        prompt_parts.append("  <pattern id=\"hatch\" patternUnits=\"userSpaceOnUse\" width=\"8\" height=\"8\">")
        prompt_parts.append("    <path d=\"M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4\" stroke=\"#999\" stroke-width=\"0.5\"/>")
        prompt_parts.append("  </pattern>")
        prompt_parts.append("  <!-- Kupfer-Gradient NUR für Kuppeln -->")
        prompt_parts.append("  <linearGradient id=\"copper\" x1=\"0%\" y1=\"0%\" x2=\"0%\" y2=\"100%\">")
        prompt_parts.append("    <stop offset=\"0%\" style=\"stop-color:#7CB9A5\"/>")
        prompt_parts.append("    <stop offset=\"100%\" style=\"stop-color:#4A8A77\"/>")
        prompt_parts.append("  </linearGradient>")
        prompt_parts.append("</defs>")
        prompt_parts.append("```")
        prompt_parts.append("")
        prompt_parts.append("| Element | Farbe/Fill |")
        prompt_parts.append("|---------|------------|")
        prompt_parts.append("| Hintergrund | #FFFFFF (weiss) |")
        prompt_parts.append("| Gebäude | url(#hatch) Schraffur |")
        prompt_parts.append("| Kuppel | url(#copper) Gradient |")
        prompt_parts.append("| Gerüst-Ständer | #0066CC (blau) |")
        prompt_parts.append("| Beläge | #8B4513 (braun) |")
        prompt_parts.append("| Verankerungen | #CC0000 gestrichelt |")
        prompt_parts.append("")

        # 8. Anforderungen
        prompt_parts.append("## 8. Anforderungen")
        prompt_parts.append("")

        if svg_type in ["all", "grundriss"]:
            prompt_parts.append("### Für Grundriss:")
            prompt_parts.append("- Polygon-Form des Gebäudes")
            prompt_parts.append("- Fassaden beschriften (Länge + Richtung)")
            prompt_parts.append("- Gerüstzone um das Gebäude (gelb)")
            prompt_parts.append("- Zonen farblich unterscheiden")
            prompt_parts.append("- Nordpfeil und Massstab")
            prompt_parts.append("")

        if svg_type in ["all", "ansicht"]:
            prompt_parts.append("### Für Fassadenansicht:")
            prompt_parts.append("- Orthogonale Frontalansicht")
            prompt_parts.append(f"- Terrain-Linie bei {terrain_ref}")
            prompt_parts.append("- Höhenzonen klar darstellen")
            prompt_parts.append("- Baustil-typische Elemente zeigen")
            prompt_parts.append("- Gerüst VOR der Fassade")
            prompt_parts.append("- Höhenskala links, Lagenbeschriftung rechts")
            prompt_parts.append("")

        if svg_type in ["all", "schnitt"]:
            prompt_parts.append("### Für Gebäudeschnitt:")
            prompt_parts.append("- Frontalansicht (2D Orthogonalprojektion)")
            prompt_parts.append(f"- Terrain-Linie bei {terrain_ref}")
            prompt_parts.append("- Geschossdecken als horizontale Linien")
            prompt_parts.append("- Höhenzonen mit unterschiedlichen Höhen")
            prompt_parts.append("- Gerüst links und rechts")
            prompt_parts.append("- Höhenskala links, Lagenbeschriftung rechts")
            prompt_parts.append("")

        # 9. Output
        prompt_parts.append("## 9. Output")
        prompt_parts.append("")

        if svg_type == "all":
            prompt_parts.append("Erstelle **3 separate SVGs**, jeweils mit `viewBox=\"0 0 700 480\"`:")
            prompt_parts.append("")
            prompt_parts.append("1. **grundriss.svg** - Draufsicht mit Polygon und Gerüstzone")
            prompt_parts.append("2. **fassadenansicht.svg** - Frontalansicht mit Gerüst")
            prompt_parts.append("3. **gebaeudesschnitt.svg** - Querschnitt mit Geschossen")
        else:
            prompt_parts.append(f"Erstelle **1 SVG** mit `viewBox=\"0 0 700 480\"`:")
            prompt_parts.append("")
            prompt_parts.append(f"- **{svg_type}.svg**")

        prompt_parts.append("")
        prompt_parts.append("**NUR SVG-Code**, keine Erklärungen. Trenne die SVGs klar voneinander.")

        return "\n".join(prompt_parts)

    def _is_complex(self, data: PromptData) -> bool:
        """Bestimmt ob das Gebäude komplex ist"""

        # Höhendifferenz > 15m
        if data.traufhoehe_m and data.firsthoehe_m:
            if data.firsthoehe_m - data.traufhoehe_m > 15:
                return True

        # Viele Zonen
        if data.zones and len(data.zones) > 1:
            return True

        # Grosse Fläche
        area = data.footprint_area_m2 or data.gwr_area_m2 or 0
        if area > 1000:
            return True

        # Komplexes Polygon
        if data.polygon and len(data.polygon) > 12:
            return True

        # GWR-Kategorie
        category = (data.gwr_category or "").lower()
        complex_keywords = ['kirche', 'religiös', 'öffentlich', 'museum', 'schule', 'spital']
        if any(kw in category for kw in complex_keywords):
            return True

        # Recherche zeigt Komplexität
        if data.research:
            if data.research.tower_config:
                return True
            if data.research.suggested_zones and len(data.research.suggested_zones) > 1:
                return True

        return False

    def _get_building_type(self, data: PromptData) -> str:
        """Ermittelt Gebäudetyp aus GWR oder Recherche"""
        if data.research and data.research.building_type:
            return data.research.building_type

        category = (data.gwr_category or "").lower()

        if 'kirche' in category or 'religiös' in category:
            return "Kirche/Sakralbau"
        if 'öffentlich' in category or 'verwaltung' in category:
            return "Öffentliches Gebäude"
        if 'mehrfamilien' in category:
            return "Mehrfamilienhaus"
        if 'einfamilien' in category:
            return "Einfamilienhaus"
        if 'gewerbe' in category or 'industrie' in category:
            return "Gewerbe/Industrie"
        if 'landwirtschaft' in category:
            return "Landwirtschaftsgebäude"

        if self._is_complex(data):
            return "Komplexes Gebäude (RECHERCHIEREN)"

        return "Wohngebäude"


# Singleton-Instance
_prompt_builder: Optional[PromptBuilder] = None


def get_prompt_builder() -> PromptBuilder:
    """Gibt die Singleton-Instance des Prompt-Builders zurück"""
    global _prompt_builder
    if _prompt_builder is None:
        _prompt_builder = PromptBuilder()
    return _prompt_builder
