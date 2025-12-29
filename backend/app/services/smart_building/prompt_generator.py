# backend/app/services/smart_building/prompt_generator.py
"""
Unified Prompt Generator
========================

Generiert einheitliche Prompts aus BuildingDataBundle.

IDENTISCHER Prompt für:
- SVG-Export (Claude.ai)
- Automatische SVG-Generierung (Claude API)

Features:
- Strukturierter Aufbau nach Export_Prompt_Claude.md Template
- Dynamische Abschnitte basierend auf verfügbaren Daten
- Erweiterbar für neue SVG-Typen (z.B. Umgebungsplan)
- Hanglage-Hinweise bei erkanntem Gefälle
- Nachbargebäude-Info (TODO)
"""

import json
from enum import Enum
from typing import Optional, List
from datetime import datetime

from .models import BuildingDataBundle, ZoneInfo, DataQuality


class SVGType(str, Enum):
    """Verfügbare SVG-Typen"""
    GRUNDRISS = "grundriss"
    ANSICHT = "ansicht"
    SCHNITT = "schnitt"
    UMGEBUNG = "umgebung"  # NEU: Umgebungsplan mit Nachbarn, Hanglage
    ALL = "all"  # Alle 3 Standard-SVGs


class UnifiedPromptGenerator:
    """
    Generiert einheitliche Prompts für SVG-Erstellung.

    Verwendung:
        generator = get_prompt_generator()
        prompt = generator.generate(bundle, svg_type=SVGType.ALL)
    """

    def generate(
        self,
        bundle: BuildingDataBundle,
        svg_type: SVGType = SVGType.ALL,
        include_style_guide: bool = True,
        include_examples: bool = False,
    ) -> str:
        """
        Generiert den vollständigen Prompt.

        Args:
            bundle: Gesammelte Gebäudedaten
            svg_type: Welche SVGs generiert werden sollen
            include_style_guide: Style-Vorgaben einschliessen
            include_examples: Beispiel-Code einschliessen

        Returns:
            Vollständiger Prompt-String
        """
        sections = []

        # 1. Header
        sections.append(self._header(svg_type))

        # 2. Gebäude-Identifikation
        sections.append(self._identification_section(bundle))

        # 3. Recherche-Anweisung (falls nötig)
        if self._needs_research(bundle):
            sections.append(self._research_instruction(bundle))

        # 4. Geometrische Basisdaten
        sections.append(self._geometry_section(bundle))

        # 5. Terrain & Hanglage
        if bundle.terrain:
            sections.append(self._terrain_section(bundle))

        # 6. Dach-Daten
        if bundle.roof_type:
            sections.append(self._roof_section(bundle))

        # 7. Höhenzonen
        sections.append(self._zones_section(bundle))

        # 8. Fassaden
        if bundle.sides:
            sections.append(self._facades_section(bundle))

        # 9. Zugänge (SUVA)
        if bundle.access_points:
            sections.append(self._access_section(bundle))

        # 10. Umgebung/Nachbarn (TODO)
        if bundle.neighbors:
            sections.append(self._neighbors_section(bundle))

        # 11. Style-Guide
        if include_style_guide:
            sections.append(self._style_guide())

        # 12. SVG-spezifische Anforderungen
        sections.append(self._svg_requirements(bundle, svg_type))

        # 13. Output-Format
        sections.append(self._output_format(svg_type))

        # 14. Warnungen/Hinweise
        if bundle.warnings:
            sections.append(self._warnings_section(bundle))

        # 15. Footer
        sections.append(self._footer())

        return "\n\n".join(sections)

    def _header(self, svg_type: SVGType) -> str:
        """Prompt-Header"""
        type_names = {
            SVGType.GRUNDRISS: "Grundriss (Draufsicht)",
            SVGType.ANSICHT: "Fassadenansicht (Elevation)",
            SVGType.SCHNITT: "Gebäudeschnitt (Querschnitt)",
            SVGType.UMGEBUNG: "Umgebungsplan (Kontext)",
            SVGType.ALL: "Grundriss + Fassadenansicht + Gebäudeschnitt",
        }
        return f"""# SVG-Generierung: {type_names.get(svg_type, 'Gebäude-Visualisierung')}

Erstelle technische Architekturzeichnungen für die Gerüstplanung.
Folge den unten aufgeführten Daten und Style-Vorgaben EXAKT."""

    def _identification_section(self, bundle: BuildingDataBundle) -> str:
        """Gebäude-Identifikation"""
        lines = ["## 1. Gebäude-Identifikation"]

        lines.append(f"- **Adresse:** {bundle.address_matched or bundle.address_input or 'Unbekannt'}")
        lines.append(f"- **EGID:** {bundle.egid or '-'}")

        if bundle.lv95_e and bundle.lv95_n:
            lines.append(f"- **Koordinaten (LV95):** E {bundle.lv95_e:.0f}, N {bundle.lv95_n:.0f}")

        lines.append(f"- **Gebäudename:** {bundle.building_name or 'RECHERCHIEREN'}")
        lines.append(f"- **Gebäudetyp:** {bundle.building_type or self._infer_building_type(bundle)}")

        if bundle.architectural_style:
            lines.append(f"- **Baustil:** {bundle.architectural_style}")

        if bundle.construction_year:
            lines.append(f"- **Baujahr:** {bundle.construction_year}")

        lines.append(f"- **Komplexität:** {bundle.complexity.upper()}")

        return "\n".join(lines)

    def _needs_research(self, bundle: BuildingDataBundle) -> bool:
        """Prüft ob Recherche-Anweisung nötig"""
        return (
            not bundle.building_name or
            bundle.complexity == "complex" or
            bundle.has_extreme_height_diff()
        )

    def _research_instruction(self, bundle: BuildingDataBundle) -> str:
        """Recherche-Anweisung für Claude"""
        return """## 2. RECHERCHE-ANWEISUNG

> **WICHTIG:** Falls Gebäudename oder Baustil nicht bekannt:
> 1. Suche das Gebäude anhand Adresse/EGID/Koordinaten
> 2. Identifiziere den korrekten Gebäudenamen
> 3. Bestimme Gebäudetyp und Baustil
> 4. Ermittle charakteristische Architekturmerkmale
> 5. Validiere die Höhenzonen gegen recherchierte Informationen
> **Erst danach mit der SVG-Erstellung beginnen.**"""

    def _geometry_section(self, bundle: BuildingDataBundle) -> str:
        """Geometrische Basisdaten"""
        lines = ["## 3. Geometrische Basisdaten"]

        lines.append("### Dimensionen")
        lines.append(f"- **Traufhöhe:** {bundle.traufhoehe_m:.1f} m" if bundle.traufhoehe_m else "- **Traufhöhe:** nicht verfügbar")
        lines.append(f"- **Firsthöhe:** {bundle.firsthoehe_m:.1f} m" if bundle.firsthoehe_m else "- **Firsthöhe:** nicht verfügbar")
        lines.append(f"- **Geschosse:** {bundle.gwr_floors or bundle.floors_estimated or '-'}")
        lines.append(f"- **Grundfläche:** {bundle.footprint_area_m2:.0f} m²" if bundle.footprint_area_m2 else "- **Grundfläche:** -")

        if bundle.polygon:
            lines.append("")
            lines.append("### Polygon")

            if len(bundle.polygon) > 10:
                lines.append(f"> **HINWEIS:** Komplexes Polygon mit {len(bundle.polygon)} Punkten")
                lines.append(f"> → Vereinfachte rechteckige Darstellung empfohlen")
                if bundle.bbox_width_m and bundle.bbox_depth_m:
                    lines.append(f"- **Bounding Box:** {bundle.bbox_width_m:.1f}m × {bundle.bbox_depth_m:.1f}m")
            else:
                lines.append(f"- **Eckpunkte:** {len(bundle.polygon)}")

            lines.append(f"- **Umfang:** {bundle.perimeter_m:.1f} m" if bundle.perimeter_m else "")

        return "\n".join(lines)

    def _terrain_section(self, bundle: BuildingDataBundle) -> str:
        """Terrain-Daten und Hanglage"""
        t = bundle.terrain
        lines = ["## 4. Terrain (swissALTI3D)"]

        ref = t.reference_height_m
        lines.append(f"- **Terrain-Höhe:** {ref:.1f} m ü.M.")
        lines.append(f"- **Referenzpunkt:** Haupteingang = ±0.00 = {ref:.1f} m ü.M.")

        if t.is_sloped and t.slope_m:
            lines.append("")
            lines.append(f"### ⚠️ HANGLAGE ERKANNT: {t.slope_m:.1f}m Differenz!")
            lines.append("")
            lines.append("**Auswirkungen auf Gerüst:**")
            lines.append("- Unterschiedliche Gerüsthöhen je Fassade nötig")
            lines.append("- Ausgleichsspindeln/Fussplatten für Niveauunterschiede")
            lines.append("- Beachte SUVA-Vorschriften für Hanggerüste")

            if t.facade_heights:
                lines.append("")
                lines.append("**Terrain-Höhen pro Fassade:**")
                for direction, height in t.facade_heights.items():
                    diff = height - ref
                    lines.append(f"- {direction}: {height:.1f} m ü.M. ({diff:+.1f}m)")
        else:
            lines.append("- **Hanglage:** Nein (eben)")

        return "\n".join(lines)

    def _roof_section(self, bundle: BuildingDataBundle) -> str:
        """Dach-Daten"""
        lines = ["## 5. Dach-Analyse"]

        lines.append(f"- **Dachform:** {bundle.roof_type}")
        if bundle.roof_angle_deg:
            lines.append(f"- **Dachneigung:** {bundle.roof_angle_deg:.0f}°")
        if bundle.roof_orientation:
            lines.append(f"- **First-Ausrichtung:** {bundle.roof_orientation}")
        if bundle.roof_area_m2:
            lines.append(f"- **Dachfläche:** {bundle.roof_area_m2:.0f} m²")

        conf_pct = bundle.roof_confidence * 100
        lines.append(f"- **Konfidenz:** {conf_pct:.0f}%")

        return "\n".join(lines)

    def _zones_section(self, bundle: BuildingDataBundle) -> str:
        """Höhenzonen"""
        lines = ["## 6. Höhenzonen"]

        if not bundle.zones:
            lines.append("Keine Zonen definiert (einfaches Gebäude mit 1 Zone)")
            return "\n".join(lines)

        # Tabelle
        lines.append("")
        lines.append("| Zone | Typ | Höhe | Traufe | Gerüst |")
        lines.append("|------|-----|------|--------|--------|")

        for z in bundle.zones:
            height = z.gebaeudehoehe_m or z.firsthoehe_m or "-"
            trauf = f"{z.traufhoehe_m:.1f}m" if z.traufhoehe_m else "-"
            height_str = f"{height:.1f}m" if isinstance(height, (int, float)) else height

            if z.sonderkonstruktion:
                geruest = "Sonderkonstruktion"
            elif z.beruesten:
                geruest = "Standard"
            else:
                geruest = "Nein"

            lines.append(f"| {z.name} | {z.zone_type} | {height_str} | {trauf} | {geruest} |")

        # Legende
        lines.append("")
        lines.append("### Zone-Typen Legende")
        lines.append("- **hauptgebaeude** = Rechteckiger Hauptkörper mit Schraffur")
        lines.append("- **arkade** = Niedriger Bereich mit Rundbogen")
        lines.append("- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)")
        lines.append("- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)")
        lines.append("- **anbau** = Niedrigerer Anbau am Hauptgebäude")
        lines.append("- **innenhof** = Nicht einrüsten (Freifläche)")

        return "\n".join(lines)

    def _facades_section(self, bundle: BuildingDataBundle) -> str:
        """Fassaden-Daten"""
        lines = ["## 7. Fassaden"]

        lines.append("")
        lines.append("| Seite | Länge (m) | Richtung |")
        lines.append("|-------|-----------|----------|")

        for i, s in enumerate(bundle.sides[:8]):  # Max 8 Fassaden anzeigen
            idx = s.get('index', i + 1)
            length = s.get('length_m', 0)
            direction = s.get('direction', '?')
            lines.append(f"| {idx} | {length:.1f} | {direction} |")

        if len(bundle.sides) > 8:
            lines.append(f"| ... | ({len(bundle.sides) - 8} weitere) | ... |")

        # Längste Fassade
        if bundle.sides:
            longest = max(s.get('length_m', 0) for s in bundle.sides)
            lines.append(f"\n- **Längste Fassade:** {longest:.1f} m")

        return "\n".join(lines)

    def _access_section(self, bundle: BuildingDataBundle) -> str:
        """Gerüst-Zugänge (SUVA)"""
        lines = ["## 8. Gerüst-Zugänge (SUVA)"]

        if bundle.suva_compliant:
            lines.append("✅ SUVA-konform (max. 50m Fluchtweg)")
        else:
            lines.append(f"⚠️ SUVA-Warnung: Fluchtweg {bundle.max_escape_distance_m:.1f}m > 50m!")

        lines.append("")
        lines.append("| Zugang | Fassade | Position | Grund |")
        lines.append("|--------|---------|----------|-------|")

        for a in bundle.access_points:
            pos_pct = f"{a.position_percent * 100:.0f}%"
            lines.append(f"| {a.id} | {a.fassade_id} | {pos_pct} | {a.reason or '-'} |")

        return "\n".join(lines)

    def _neighbors_section(self, bundle: BuildingDataBundle) -> str:
        """Nachbargebäude (TODO)"""
        lines = ["## 9. Nachbargebäude"]

        if not bundle.neighbors:
            lines.append("Keine Nachbargebäude-Daten verfügbar.")
            return "\n".join(lines)

        for n in bundle.neighbors:
            lines.append(f"- {n.direction}: {n.distance_m:.1f}m entfernt")
            if n.blocks_facade:
                lines.append(f"  → Blockiert Fassade {n.blocks_facade}")

        return "\n".join(lines)

    def _style_guide(self) -> str:
        """SVG Style-Vorgaben"""
        return """## 10. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur für Aussenflächen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur für Schnittflächen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR für Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebäude-Aussenfläche | url(#hatch) | Fassade + Grundriss |
| Schnittfläche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Gerüst-Ständer | #0066CC (blau) | Alle SVGs |
| Beläge | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBÄUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    ┌─────────┐                        ┌─────────┐
    │░░░░░░░░░│ ← Fassade             │█│     │█│ ← Schnittfläche
    │░░░░░░░░░│   (alles sichtbar      │ │     │ │   (dicht schraffiert)
    │░░░░░░░░░│    von aussen)         │ │     │ │
    └─────────┘                        │ │     │ │ ← Innenraum (LEER!)
                                       └─┴─────┴─┘

░░░ = lockere Schraffur            █ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```"""

    def _svg_requirements(self, bundle: BuildingDataBundle, svg_type: SVGType) -> str:
        """SVG-spezifische Anforderungen"""
        lines = ["## 11. Anforderungen pro SVG"]

        terrain_ref = "±0.00"
        if bundle.terrain:
            terrain_ref = f"±0.00 = {bundle.terrain.reference_height_m:.1f} m ü.M."

        if svg_type in [SVGType.GRUNDRISS, SVGType.ALL]:
            lines.append("""
### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebäudeumriss, Wandstärken, Fassadenlängen
- **Schraffur:** url(#hatch) für Mauern
- **Gerüstzone:** Rechteckige Hülle mit 1m Abstand
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung""")

            if len(bundle.zones) > 1:
                lines.append("- **Zonen:** Farblich unterscheiden, Innenhöfe markieren")

        if svg_type in [SVGType.ANSICHT, SVGType.ALL]:
            lines.append(f"""
### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht von AUSSEN, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenfläche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenräume sichtbar!
- **Schraffur:** url(#hatch) für alle Fassadenflächen
- **Terrain-Linie:** bei {terrain_ref}
- **Gerüst:** VOR der Fassade (Ständer blau, Beläge braun)
- **Höhenskala:** Links (±0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)""")

        if svg_type in [SVGType.SCHNITT, SVGType.ALL]:
            lines.append(f"""
### SVG 3: Gebäudeschnitt (Querschnitt)
- **Perspektive:** Gebäude AUFGESCHNITTEN entlang Schnittlinie A-A
- **Zeigt:** Innenräume, Konstruktion, Raumhöhen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenräume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei {terrain_ref} mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Gerüst:** Links und rechts (Ständer + Beläge)
- **Schnittmarkierung:** A-A""")

        if svg_type == SVGType.UMGEBUNG:
            lines.append("""
### SVG 4: Umgebungsplan (Kontext)
- **Perspektive:** Vogelperspektive, grösserer Massstab
- **Zeigt:** Gebäude im Kontext mit Nachbarn
- **Terrain:** Höhenlinien bei Hanglage
- **Nachbarn:** Schematisch mit Höhenangabe
- **Zugänge:** Markiert mit Z1, Z2, etc.
- **Strassen:** Falls relevant für Gerüstzugang""")

        return "\n".join(lines)

    def _output_format(self, svg_type: SVGType) -> str:
        """Output-Format Anweisung"""
        if svg_type == SVGType.ALL:
            return """## 12. Output

Erstelle **3 separate SVGs**, jeweils mit `viewBox="0 0 700 480"`:

1. **grundriss.svg** - Draufsicht mit Gebäudeumriss und Gerüstzone
2. **fassadenansicht.svg** - Aussenansicht, vordere Elemente verdecken hintere
3. **gebaeudeschnitt.svg** - Aufgeschnitten, Innenräume sichtbar und LEER

**NUR SVG-Code**, keine Erklärungen. Trenne die SVGs mit Kommentar:
`<!-- SVG 1: Grundriss -->`"""

        else:
            return f"""## 12. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: {svg_type.value}

**NUR SVG-Code**, keine Erklärungen."""

    def _warnings_section(self, bundle: BuildingDataBundle) -> str:
        """Warnungen und Hinweise"""
        lines = ["## ⚠️ Warnungen"]

        for w in bundle.warnings:
            lines.append(f"- {w}")

        return "\n".join(lines)

    def _footer(self) -> str:
        """Prompt-Footer"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""---

*Generiert mit Gerüstplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: {ts}*
*https://cooperative-commitment-production.up.railway.app*"""

    def _infer_building_type(self, bundle: BuildingDataBundle) -> str:
        """Leitet Gebäudetyp aus GWR-Kategorie ab"""
        if not bundle.gwr_category:
            return "Gebäude"

        cat = bundle.gwr_category.lower()

        if 'kirche' in cat or 'religiös' in cat:
            return "Sakralbau"
        if 'öffentlich' in cat or 'verwaltung' in cat:
            return "Öffentliches Gebäude"
        if 'mehrfamilien' in cat:
            return "Mehrfamilienhaus"
        if 'einfamilien' in cat:
            return "Einfamilienhaus"
        if 'gewerbe' in cat or 'industrie' in cat:
            return "Gewerbe/Industrie"
        if 'landwirtschaft' in cat:
            return "Landwirtschaftsgebäude"

        return "Wohngebäude"


# Singleton
_generator_instance: Optional[UnifiedPromptGenerator] = None


def get_prompt_generator() -> UnifiedPromptGenerator:
    """Gibt die Singleton-Instanz zurück"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = UnifiedPromptGenerator()
    return _generator_instance
