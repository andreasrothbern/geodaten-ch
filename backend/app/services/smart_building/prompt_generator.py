# backend/app/services/smart_building/prompt_generator.py
"""
Unified Prompt Generator
========================

Generiert einheitliche Prompts aus BuildingDataBundle.

IDENTISCHER Prompt fuer:
- SVG-Export (Claude.ai)
- Automatische SVG-Generierung (Claude API)

Features:
- Strukturierter Aufbau nach Template-Vorgaben
- Dynamische Abschnitte basierend auf verfuegbaren Daten
- Erweiterbar fuer neue SVG-Typen (z.B. Umgebungsplan)
- Hanglage-Hinweise bei erkanntem Gefaelle
- Gebaeudeform-Hinweise (U-Form, L-Form, etc.)
- SVG-Hints pro Typ (grundriss, ansicht, schnitt)

Template-Referenz:
==================
Die Templates liegen unter: prompts/
- base_template.md      - Haupt-Vorlage (Dokumentation)
- sections/zones.md     - Hoehenzonen-Beschreibung
- sections/style_guide.md - SVG Style-Vorgaben
- sections/requirements.md - Anforderungen pro SVG-Typ

Die Templates dienen als Referenz. Der Generator implementiert
die Logik programmatisch fuer dynamische Daten.
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
    QUERSCHNITT = "querschnitt"      # NEU: Querschnitt A-A (quer durch Gebaeude)
    LAENGSSCHNITT = "laengsschnitt"  # NEU: Laengsschnitt B-B (laengs durch Gebaeude)
    UMGEBUNG = "umgebung"            # Umgebungsplan mit Nachbarn, Hanglage
    ALL = "all"                      # Alle 4 Standard-SVGs
    # Deprecated alias (fuer Abwaertskompatibilitaet)
    SCHNITT = "querschnitt"          # Alias -> QUERSCHNITT


class UnifiedPromptGenerator:
    """
    Generiert einheitliche Prompts für SVG-Erstellung.

    Verwendung:
        generator = get_prompt_generator()
        prompt = generator.generate(bundle, svg_type=SVGType.ALL)

    Quick Wins (30.12.2025):
    - Proportionen-Berechnung (viewBox 700×480)
    - Gerüst-Spezifikation (Layher Blitz 70)
    - Innenhof-Koordinaten (U-Form)
    """

    # ViewBox Konstanten (Quick Win #1)
    VIEWBOX_WIDTH = 700
    VIEWBOX_HEIGHT = 480
    OFFSET_LEFT = 100    # Höhenskala
    OFFSET_BOTTOM = 60   # Terrain
    OFFSET_RIGHT = 50    # Lagenbeschriftung
    OFFSET_TOP = 40      # Titel

    # Dachform-Mapping: Technischer Wert -> Lesbare Beschreibung für Claude
    ROOF_TYPE_LABELS = {
        "flachdach": "Flachdach (horizontal, keine Neigung)",
        "pultdach": "Pultdach (einseitig geneigt)",
        "satteldach": "Satteldach (zwei geneigte Flächen, First in der Mitte)",
        "satteldach_mit_turm": "Satteldach mit Kirchturm (Hauptdach + hoher Turm mit Spitzhelm)",
        "walmdach": "Walmdach (vier geneigte Flächen)",
        "mansarddach": "Mansarddach (gebrochene Dachflächen, steiler unten)",
        "kuppel": "Kuppeldach (halbrund, typisch für repräsentative Gebäude)",
        "unknown": "Unbekannt (Standard-Satteldach annehmen)",
    }

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

        # Header (kein Abschnitt im Prompt)
        sections.append(self._header(svg_type))

        # ## 1. Gebaeude-Identifikation
        sections.append(self._identification_section(bundle))

        # ## 2. Recherche-Anweisung (optional - nur wenn Daten fehlen)
        if self._needs_research(bundle):
            sections.append(self._research_instruction(bundle))

        # ## 3. Geometrische Basisdaten
        sections.append(self._geometry_section(bundle))

        # ## 4. Terrain (optional)
        if bundle.terrain:
            sections.append(self._terrain_section(bundle))

        # ## 5. Dach-Analyse (optional)
        if bundle.roof_type:
            sections.append(self._roof_section(bundle))

        # ## 6. Hoehenzonen
        sections.append(self._zones_section(bundle))

        # ## 7. Fassaden (optional)
        if bundle.sides:
            sections.append(self._facades_section(bundle))

        # ## 8. Geruest-Zugaenge (optional)
        if bundle.access_points:
            sections.append(self._access_section(bundle))

        # ## 9. Nachbargebaeude (optional)
        if bundle.neighbors:
            sections.append(self._neighbors_section(bundle))

        # ## 10. Proportionen (Quick Win #1)
        sections.append(self._proportions_section(bundle))

        # ## 11. Gerüst-Spezifikation (Quick Win #3)
        sections.append(self._scaffolding_spec_section())

        # ## 12. Style-Guide
        if include_style_guide:
            sections.append(self._style_guide())

        # ## 13. Anforderungen pro SVG
        sections.append(self._svg_requirements(bundle, svg_type))

        # ## 14. Output
        sections.append(self._output_format(svg_type))

        # Warnungen (optional, nicht nummeriert)
        if bundle.warnings:
            sections.append(self._warnings_section(bundle))

        # Footer (nicht nummeriert)
        sections.append(self._footer())

        return "\n\n".join(sections)

    def _header(self, svg_type: SVGType) -> str:
        """Prompt-Header"""
        type_names = {
            SVGType.GRUNDRISS: "Grundriss (Draufsicht)",
            SVGType.ANSICHT: "Fassadenansicht (Elevation)",
            SVGType.QUERSCHNITT: "Querschnitt A-A (quer durch Gebaeude)",
            SVGType.LAENGSSCHNITT: "Laengsschnitt B-B (laengs durch Gebaeude)",
            SVGType.UMGEBUNG: "Umgebungsplan (Kontext)",
            SVGType.ALL: "Grundriss + Ansicht + Querschnitt + Laengsschnitt",
        }
        return f"""# SVG-Generierung: {type_names.get(svg_type, 'Gebaeude-Visualisierung')}

Erstelle technische Architekturzeichnungen fuer die Geruestplanung.
Folge den unten aufgefuehrten Daten und Style-Vorgaben EXAKT."""

    def _identification_section(self, bundle: BuildingDataBundle) -> str:
        """Gebaeude-Identifikation"""
        lines = ["## 1. Gebaeude-Identifikation"]

        lines.append(f"- **Adresse:** {bundle.address_matched or bundle.address_input or 'Unbekannt'}")
        lines.append(f"- **EGID:** {bundle.egid or '-'}")

        if bundle.lv95_e and bundle.lv95_n:
            lines.append(f"- **Koordinaten (LV95):** E {bundle.lv95_e:.0f}, N {bundle.lv95_n:.0f}")

        # Gebaeudename: Nie "RECHERCHIEREN" - sinnvoller Fallback
        if bundle.building_name:
            lines.append(f"- **Gebaeudename:** {bundle.building_name}")
        elif bundle.building_type:
            lines.append(f"- **Gebaeudename:** {bundle.building_type} ({bundle.address_matched})")
        else:
            addr_short = (bundle.address_matched or bundle.address_input or "").split(",")[0]
            lines.append(f"- **Gebaeudename:** Gebaeude {addr_short}")
        lines.append(f"- **Gebaeudetyp:** {bundle.building_type or self._infer_building_type(bundle)}")

        if bundle.architectural_style:
            lines.append(f"- **Baustil:** {bundle.architectural_style}")

        if bundle.construction_year:
            lines.append(f"- **Baujahr:** {bundle.construction_year}")

        lines.append(f"- **Komplexitaet:** {bundle.complexity.upper()}")

        return "\n".join(lines)

    def _needs_research(self, bundle: BuildingDataBundle) -> bool:
        """Prueft ob Recherche-Anweisung noetig

        Bekannte Gebaeude (research_confidence >= 1.0) brauchen KEINE Recherche!
        Die Anweisung erscheint nur wenn:
        - Kein Gebaeudename vorhanden UND
        - Keine bekannten Daten vorhanden sind
        """
        # Bekannte Gebaeude haben alle Daten - keine Recherche noetig
        if hasattr(bundle, 'research_confidence') and bundle.research_confidence >= 1.0:
            return False

        # Bekannte Zonen bedeuten bekanntes Gebaeude
        if hasattr(bundle, '_known_zones') and bundle._known_zones:
            return False

        # Recherche nur wenn kein Name bekannt
        return not bundle.building_name

    def _research_instruction(self, bundle: BuildingDataBundle) -> str:
        """Recherche-Anweisung fuer Claude"""
        return """## 2. RECHERCHE-ANWEISUNG

> **WICHTIG:** Falls Gebaeudename oder Baustil nicht bekannt:
> 1. Suche das Gebaeude anhand Adresse/EGID/Koordinaten
> 2. Identifiziere den korrekten Gebaeudenamen
> 3. Bestimme Gebaeudetyp und Baustil
> 4. Ermittle charakteristische Architekturmerkmale
> 5. Validiere die Hoehenzonen gegen recherchierte Informationen
> **Erst danach mit der SVG-Erstellung beginnen.**"""

    def _geometry_section(self, bundle: BuildingDataBundle) -> str:
        """Geometrische Basisdaten"""
        lines = ["## 3. Geometrische Basisdaten"]

        lines.append("### Dimensionen")
        lines.append(f"- **Traufhoehe:** {bundle.traufhoehe_m:.1f} m" if bundle.traufhoehe_m else "- **Traufhoehe:** nicht verfuegbar")
        lines.append(f"- **Firsthoehe:** {bundle.firsthoehe_m:.1f} m" if bundle.firsthoehe_m else "- **Firsthoehe:** nicht verfuegbar")
        lines.append(f"- **Geschosse:** {bundle.gwr_floors or bundle.floors_estimated or '-'}")
        lines.append(f"- **Grundflaeche:** {bundle.footprint_area_m2:.0f} m2" if bundle.footprint_area_m2 else "- **Grundflaeche:** -")

        if bundle.polygon:
            lines.append("")
            lines.append("### Polygon")

            if len(bundle.polygon) > 10:
                lines.append(f"> **HINWEIS:** Komplexes Polygon mit {len(bundle.polygon)} Punkten")
                lines.append(f"> -> Vereinfachte rechteckige Darstellung empfohlen")
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
        lines.append(f"- **Terrain-Hoehe:** {ref:.1f} m ue.M.")
        lines.append(f"- **Referenzpunkt:** Haupteingang = +/-0.00 = {ref:.1f} m ue.M.")

        if t.is_sloped and t.slope_m:
            lines.append("")
            lines.append(f"### [!] HANGLAGE ERKANNT: {t.slope_m:.1f}m Differenz!")
            lines.append("")
            lines.append("**Auswirkungen auf Geruest:**")
            lines.append("- Unterschiedliche Geruesthoehen je Fassade noetig")
            lines.append("- Ausgleichsspindeln/Fussplatten fuer Niveauunterschiede")
            lines.append("- Beachte SUVA-Vorschriften fuer Hanggerueste")

            if t.facade_heights:
                lines.append("")
                lines.append("**Terrain-Hoehen pro Fassade:**")
                for direction, height in t.facade_heights.items():
                    diff = height - ref
                    lines.append(f"- {direction}: {height:.1f} m ue.M. ({diff:+.1f}m)")
        else:
            lines.append("- **Hanglage:** Nein (eben)")

        return "\n".join(lines)

    def _roof_section(self, bundle: BuildingDataBundle) -> str:
        """Dach-Daten"""
        lines = ["## 5. Dach-Analyse"]

        # Dachform mit lesbarer Beschreibung für Claude
        roof_label = self.ROOF_TYPE_LABELS.get(
            bundle.roof_type or "unknown",
            f"{bundle.roof_type} (unbekannter Typ)"
        )
        lines.append(f"- **Dachform:** {roof_label}")
        if bundle.roof_angle_deg:
            lines.append(f"- **Dachneigung:** {bundle.roof_angle_deg:.0f}°")
        if bundle.roof_orientation:
            lines.append(f"- **First-Ausrichtung:** {bundle.roof_orientation}")
        if bundle.roof_area_m2:
            lines.append(f"- **Dachflaeche:** {bundle.roof_area_m2:.0f} m2")

        conf_pct = bundle.roof_confidence * 100
        lines.append(f"- **Konfidenz:** {conf_pct:.0f}%")

        return "\n".join(lines)

    def _zones_section(self, bundle: BuildingDataBundle) -> str:
        """Hoehenzonen - KRITISCH fuer korrekte SVG-Generierung"""
        lines = ["## 6. Hoehenzonen"]

        # === NEU 30.12.2025: GEBAEUDEFORM (Top 3 Verbesserung #2) ===
        # Ohne diese Info wird ein U-Form Gebaeude als Rechteck gezeichnet!
        if bundle.building_shape:
            lines.append("")
            lines.append(f"### [!] GEBAEUDEFORM: {bundle.building_shape.upper()}")
            if bundle.building_shape_description:
                lines.append(f"> {bundle.building_shape_description}")
            lines.append("")

        # === NEU 30.12.2025: SPEZIELLE FEATURES (Top 3 Verbesserung #1) ===
        # Ohne diese Info fehlt z.B. der Ehrenhof im Grundriss!
        if bundle.special_features:
            lines.append("### Spezielle Architektur-Elemente")
            for feature in bundle.special_features:
                lines.append(f"- **{feature}**")
            lines.append("")

        # === NEU: TURM-KONFIGURATION ===
        # Wichtig für Kirchen und andere Gebäude mit Türmen
        if bundle.tower_config:
            tc = bundle.tower_config
            lines.append("### Turm-Konfiguration")
            lines.append(f"- **Anzahl Türme:** {tc.get('count', 1)}")
            lines.append(f"- **Position:** {tc.get('position', 'unbekannt')}")
            lines.append(f"- **Form:** {tc.get('form', 'unbekannt')}")
            if tc.get('height_m'):
                lines.append(f"- **Höhe:** {tc.get('height_m')}m")
            lines.append("")

        # === Quick Win #4: INNENHOF-KOORDINATEN ===
        courtyard_bbox = self._calculate_courtyard_bbox(bundle)
        if courtyard_bbox:
            lines.append("### [!] INNENHOF-KOORDINATEN (nicht einrüsten!)")
            lines.append(f"- **E-Bereich:** {courtyard_bbox['min_e']:.0f} - {courtyard_bbox['max_e']:.0f}")
            lines.append(f"- **N-Bereich:** {courtyard_bbox['min_n']:.0f} - {courtyard_bbox['max_n']:.0f}")
            lines.append(f"- **Fläche:** {courtyard_bbox['area_m2']:.0f} m²")
            lines.append("> **WICHTIG:** Innenhof als FREIFLÄCHE markieren, NICHT einrüsten!")
            lines.append("")

        if not bundle.zones:
            lines.append("Keine Zonen definiert (einfaches Gebaeude mit 1 Zone)")
            return "\n".join(lines)

        # === HOEHEN PRO ZONE (Top 3 Verbesserung #3) ===
        # Tabelle mit ALLEN Hoehenwerten fuer korrekte Proportionen
        lines.append("### Hoehen pro Zone (KRITISCH fuer Proportionen!)")
        lines.append("")

        # Prüfe ob mindestens eine Zone eine Position hat
        has_positions = any(z.position for z in bundle.zones)

        if has_positions:
            lines.append("| Zone | Typ | Traufhoehe | Firsthoehe | Position (Ansicht) | Geruest |")
            lines.append("|------|-----|------------|------------|-------------------|---------|")
        else:
            lines.append("| Zone | Typ | Traufhoehe | Firsthoehe | Gebaeudehoehe | Geruest |")
            lines.append("|------|-----|------------|------------|---------------|---------|")

        for z in bundle.zones:
            trauf = f"{z.traufhoehe_m:.1f}m" if z.traufhoehe_m else "-"
            first = f"{z.firsthoehe_m:.1f}m" if z.firsthoehe_m else "-"
            gebaeude = f"{z.gebaeudehoehe_m:.1f}m" if z.gebaeudehoehe_m else "-"

            if z.sonderkonstruktion:
                geruest = "Sonderkonstruktion"
            elif z.beruesten:
                geruest = "Standard"
            else:
                geruest = "Nein"

            # Position für Ansicht (wichtig für Claude)
            if has_positions:
                pos = z.position.upper() if z.position else "-"
                lines.append(f"| {z.name} | {z.zone_type} | {trauf} | {first} | {pos} | {geruest} |")
            else:
                lines.append(f"| {z.name} | {z.zone_type} | {trauf} | {first} | {gebaeude} | {geruest} |")

        # Hoehen-Zusammenfassung fuer schnellen Ueberblick
        lines.append("")
        lines.append("**Hoehen-Zusammenfassung:**")
        for i, z in enumerate(bundle.zones, 1):
            height = z.gebaeudehoehe_m or z.firsthoehe_m or z.traufhoehe_m
            if height:
                lines.append(f"- Zone {i} ({z.name}): **{height:.1f}m**")

        # Legende
        lines.append("")
        lines.append("### Zone-Typen Legende")
        lines.append("- **hauptgebaeude** = Rechteckiger Hauptkoerper mit Schraffur")
        lines.append("- **arkade** = Niedriger Bereich mit Rundbogen")
        lines.append("- **kuppel** = Halbkreis mit Kupfer-Gradient (EINZIGER Gradient!)")
        lines.append("- **turm** = Schmaler, hoher Turm (oft Sonderkonstruktion)")
        lines.append("- **anbau** = Niedrigerer Anbau am Hauptgebaeude")
        lines.append("- **innenhof** = Nicht einruesten (Freiflaeche, LEER lassen!)")

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

        # Laengste Fassade
        if bundle.sides:
            longest = max(s.get('length_m', 0) for s in bundle.sides)
            lines.append(f"\n- **Laengste Fassade:** {longest:.1f} m")

        return "\n".join(lines)

    def _access_section(self, bundle: BuildingDataBundle) -> str:
        """Geruest-Zugaenge (SUVA)"""
        lines = ["## 8. Geruest-Zugaenge (SUVA)"]

        if bundle.suva_compliant:
            lines.append("[OK] SUVA-konform (max. 50m Fluchtweg)")
        else:
            lines.append(f"[!] SUVA-Warnung: Fluchtweg {bundle.max_escape_distance_m:.1f}m > 50m!")

        lines.append("")
        lines.append("| Zugang | Fassade | Position | Grund |")
        lines.append("|--------|---------|----------|-------|")

        for a in bundle.access_points:
            pos_pct = f"{a.position_percent * 100:.0f}%"
            lines.append(f"| {a.id} | {a.fassade_id} | {pos_pct} | {a.reason or '-'} |")

        return "\n".join(lines)

    def _neighbors_section(self, bundle: BuildingDataBundle) -> str:
        """Nachbargebaeude (TODO)"""
        lines = ["## 9. Nachbargebaeude"]

        if not bundle.neighbors:
            lines.append("Keine Nachbargebaeude-Daten verfuegbar.")
            return "\n".join(lines)

        for n in bundle.neighbors:
            lines.append(f"- {n.direction}: {n.distance_m:.1f}m entfernt")
            if n.blocks_facade:
                lines.append(f"  -> Blockiert Fassade {n.blocks_facade}")

        return "\n".join(lines)

    def _style_guide(self) -> str:
        """SVG Style-Vorgaben"""
        return """## 12. SVG Style-Vorgaben (KRITISCH!)

```xml
<defs>
  <!-- LOCKERE Schraffur fuer Aussenflaechen -->
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
    <path d="M0,0 l8,8" stroke="#999" stroke-width="0.5"/>
  </pattern>

  <!-- DICHTE Schraffur fuer Schnittflaechen -->
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4">
    <path d="M0,0 l4,4 M0,4 l4,-4" stroke="#666" stroke-width="0.8"/>
  </pattern>

  <!-- Terrain/Boden -->
  <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
    <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
  </pattern>

  <!-- Kupfer-Gradient NUR fuer Kuppeln -->
  <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#7CB9A5"/>
    <stop offset="100%" style="stop-color:#4A8A77"/>
  </linearGradient>
</defs>
```

| Element | Farbe/Fill | Verwendung |
|---------|------------|------------|
| Hintergrund | #FFFFFF (weiss) | Alle SVGs |
| Gebaeude-Aussenflaeche | url(#hatch) | Fassade + Grundriss |
| Schnittflaeche | url(#cut-hatch) | NUR im Schnitt! |
| Innenraum | #FFFFFF (weiss, LEER) | NUR im Schnitt! |
| Kuppel | url(#copper) Gradient | Einziger Gradient! |
| Geruest-Staender | #0066CC (blau) | Alle SVGs |
| Belaege | #8B4513 (braun) | Alle SVGs |
| Verankerungen | #CC0000 gestrichelt | Ansicht + Schnitt |

### KRITISCHE UNTERSCHEIDUNG: Fassade vs. Schnitt

```
FASSADENANSICHT                    GEBAEUDESCHNITT
================                    ===============
Blick von AUSSEN                   Blick in SCHNITTEBENE

    +---------+                        +---------+
    |#########| <- Fassade             |@|     |@| <- Schnittflaeche
    |#########|   (alles sichtbar      | |     | |   (dicht schraffiert)
    |#########|    von aussen)         | |     | |
    +---------+                        | |     | | <- Innenraum (LEER!)
                                       +-+-----+-+

### = lockere Schraffur            @ = dichte Schnitt-Schraffur
      url(#hatch)                       url(#cut-hatch)
                                     = weiss (Innenraum)
```"""

    def _svg_requirements(self, bundle: BuildingDataBundle, svg_type: SVGType) -> str:
        """SVG-spezifische Anforderungen"""
        lines = ["## 13. Anforderungen pro SVG"]

        terrain_ref = "+/-0.00"
        if bundle.terrain:
            terrain_ref = f"+/-0.00 = {bundle.terrain.reference_height_m:.1f} m ue.M."

        if svg_type in [SVGType.GRUNDRISS, SVGType.ALL]:
            lines.append("""
### SVG 1: Grundriss (Draufsicht)
- **Perspektive:** Vogelperspektive, Blick von oben
- **Zeigt:** Gebaeudeumriss, Wandstaerken, Fassadenlaengen
- **Schraffur:** url(#hatch) fuer Mauern
- **Geruestzone:** OFFSET-KONTUR mit 1m Abstand (folgt der Gebaeudeform!)
  - Bei Kreuzform → Geruestzone ist auch kreuzfoermig
  - Bei U-Form → Geruestzone folgt der U-Form (Innenhof FREI lassen!)
  - KEINE rechteckige Bounding Box um komplexe Gebaeude!
- **Elemente:** Nordpfeil, Massstab, Fassaden-Beschriftung""")

            # SVG-Hints fuer Grundriss (NEU 30.12.2025)
            if bundle.svg_hints and bundle.svg_hints.get("grundriss"):
                lines.append(f"\n> **[!] WICHTIG:** {bundle.svg_hints['grundriss']}")

            if len(bundle.zones) > 1:
                lines.append("- **Zonen:** Farblich unterscheiden, Innenhoefe markieren")

        if svg_type in [SVGType.ANSICHT, SVGType.ALL]:
            # Bevorzugte Blickrichtung (wenn definiert)
            view_direction = ""
            if bundle.preferred_view:
                view_direction = f" von {bundle.preferred_view.get('direction', 'Sueden').upper()}"
                view_desc = bundle.preferred_view.get('description', '')
                view_reason = bundle.preferred_view.get('reason', '')

            lines.append(f"""
### SVG 2: Fassadenansicht (Elevation)
- **Perspektive:** Frontalansicht{view_direction}, orthogonal (2D)
- **Zeigt:** NUR die sichtbare Aussenflaeche
- **WICHTIG - Verdeckungsregel:**
  - Vordere Elemente VERDECKEN hintere Elemente
  - KEINE Innenraeume sichtbar!
- **Schraffur:** url(#hatch) fuer alle Fassadenflaechen
- **Terrain-Linie:** bei {terrain_ref}
- **Geruest:** VOR der Fassade (Staender blau, Belaege braun)
- **Hoehenskala:** Links (+/-0.00, +Traufe, +First)
- **Lagenbeschriftung:** Rechts (1. Lage, 2. Lage, ...)""")

            # Bevorzugte Ansichtsrichtung (NEU 30.12.2025)
            if bundle.preferred_view:
                lines.append(f"\n> **[!] ANSICHTSRICHTUNG:** {bundle.preferred_view.get('description', 'Standard')}")
                if bundle.preferred_view.get('reason'):
                    lines.append(f"> Grund: {bundle.preferred_view['reason']}")

            # SVG-Hints fuer Ansicht (NEU 30.12.2025)
            if bundle.svg_hints and bundle.svg_hints.get("ansicht"):
                lines.append(f"\n> **[!] WICHTIG:** {bundle.svg_hints['ansicht']}")

        if svg_type in [SVGType.QUERSCHNITT, SVGType.SCHNITT, SVGType.ALL]:
            lines.append(f"""
### SVG 3: Querschnitt A-A (quer durch Gebaeude)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Schnittlinie A-A (QUER)
- **Schnittebene:** Quer durch Hauptgebaeude/Kirchenschiff
- **Zeigt:** Seitenschiffe, Mittelschiff, Gewoelbestruktur, Raumhoehen
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei {terrain_ref} mit url(#ground) Pattern
- **Geschossdecken:** Horizontale Linien
- **Geruest:** Links und rechts (Staender + Belaege)
- **Schnittmarkierung:** A-A (quer)""")

            # SVG-Hints fuer Querschnitt (NEU 30.12.2025)
            if bundle.svg_hints and bundle.svg_hints.get("querschnitt"):
                lines.append(f"\n> **[!] WICHTIG:** {bundle.svg_hints['querschnitt']}")
            elif bundle.svg_hints and bundle.svg_hints.get("schnitt"):
                # Fallback auf altes "schnitt" Feld
                lines.append(f"\n> **[!] WICHTIG:** {bundle.svg_hints['schnitt']}")

        if svg_type in [SVGType.LAENGSSCHNITT, SVGType.ALL]:
            # Finde die hoechste Zone (meist Turm)
            max_height = 0
            max_zone_name = "Gebaeude"
            for z in bundle.zones:
                h = z.gebaeudehoehe_m or z.firsthoehe_m or 0
                if h > max_height:
                    max_height = h
                    max_zone_name = z.name

            lines.append(f"""
### SVG 4: Laengsschnitt B-B (laengs durch Gebaeude)
- **Perspektive:** Gebaeude AUFGESCHNITTEN entlang Laengsachse B-B
- **Schnittebene:** Laengs durch Hauptachse (z.B. West-Ost bei Kirchen)
- **Zeigt:** ALLE Hoehenzonen in einer Ansicht!
- **KRITISCH:** Turm/Kuppel vollstaendig darstellen (Geruesthoehe bis {max_height:.1f}m)
- **Elemente:** Glockengeschoss, Geschossdecken, Triumphbogen, Apsis, Gewoelbe
- **WICHTIG - Schraffur-Regel:**
  - Geschnittene Mauern = DICHTE Schraffur url(#cut-hatch)
  - Innenraeume = WEISS/LEER (KEINE Schraffur!)
- **Terrain-Linie:** bei {terrain_ref} mit url(#ground) Pattern
- **Geruest:** Komplette Einruestung inkl. Turm/Sonderkonstruktion
- **Schnittmarkierung:** B-B (laengs)""")

            # SVG-Hints fuer Laengsschnitt (NEU 30.12.2025)
            if bundle.svg_hints and bundle.svg_hints.get("laengsschnitt"):
                lines.append(f"\n> **[!] WICHTIG:** {bundle.svg_hints['laengsschnitt']}")

        if svg_type == SVGType.UMGEBUNG:
            lines.append("""
### SVG 5: Umgebungsplan (Kontext)
- **Perspektive:** Vogelperspektive, groesserer Massstab
- **Zeigt:** Gebaeude im Kontext mit Nachbarn
- **Terrain:** Hoehenlinien bei Hanglage
- **Nachbarn:** Schematisch mit Hoehenangabe
- **Zugaenge:** Markiert mit Z1, Z2, etc.
- **Strassen:** Falls relevant fuer Geruestzugang""")

        return "\n".join(lines)

    def _output_format(self, svg_type: SVGType) -> str:
        """Output-Format Anweisung"""
        if svg_type == SVGType.ALL:
            return """## 14. Output

Erstelle **4 separate SVGs**, jeweils mit `viewBox="0 0 700 480"`:

1. **grundriss.svg** - Draufsicht mit Gebaeudeumriss und Geruestzone (kreuzfoermig!)
2. **fassadenansicht.svg** - Aussenansicht, vordere Elemente verdecken hintere
3. **querschnitt_A-A.svg** - Quer durch Gebaeude (Gewoelbe, Seitenschiffe)
4. **laengsschnitt_B-B.svg** - Laengs durch Gebaeude (Turm, Schiff, Chor) - KRITISCH!

**Dateinamen-Konvention:**
`{egid}_{ansicht}_{version}.svg`
Beispiel: `191821074_laengsschnitt_v1.svg`

**NUR SVG-Code**, keine Erklaerungen. Trenne die SVGs mit Kommentar:
`<!-- SVG 1: Grundriss -->`
`<!-- SVG 2: Fassadenansicht -->`
`<!-- SVG 3: Querschnitt A-A -->`
`<!-- SVG 4: Laengsschnitt B-B -->`"""

        else:
            return f"""## 14. Output

Erstelle **1 SVG** mit `viewBox="0 0 700 480"`:
- Typ: {svg_type.value}

**NUR SVG-Code**, keine Erklaerungen."""

    def _warnings_section(self, bundle: BuildingDataBundle) -> str:
        """Warnungen und Hinweise"""
        lines = ["## [!] Warnungen"]

        for w in bundle.warnings:
            lines.append(f"- {w}")

        return "\n".join(lines)

    def _footer(self) -> str:
        """Prompt-Footer"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f"""---

*Generiert mit Geruestplanung Schweiz App v3.0 - SmartBuildingService*
*Zeitstempel: {ts}*
*https://cooperative-commitment-production.up.railway.app*"""

    def _infer_building_type(self, bundle: BuildingDataBundle) -> str:
        """Leitet Gebaeudetyp aus GWR-Kategorie und Hoehendaten ab

        WICHTIG: Bei extremer Hoehendifferenz (First - Trauf > 15m) wird
        Sakralbau/Turmbau angenommen, da dies typisch fuer Kirchen ist.
        """
        # 1. ZUERST: Extreme Hoehendifferenz pruefen (hoechste Prioritaet!)
        # Wenn First 45m hoeher als Traufe -> sehr wahrscheinlich Kirche mit Turm
        if bundle.has_extreme_height_diff():
            height_diff = (bundle.firsthoehe_m or 0) - (bundle.traufhoehe_m or 0)
            if height_diff > 30:  # Sehr grosse Differenz
                return "Sakralbau (Kirche mit Turm)"
            elif height_diff > 15:  # Moderate Differenz
                return "Turmbau/Sakralbau"

        # 2. Dann: Hat Turm-Zonen?
        if bundle.has_towers:
            return "Turmbau"

        # 3. Dann: GWR-Kategorie auswerten
        if bundle.gwr_category:
            cat = bundle.gwr_category.lower()

            if 'kirche' in cat or 'religioes' in cat:
                return "Sakralbau"
            if 'oeffentlich' in cat or 'verwaltung' in cat:
                return "Oeffentliches Gebaeude"
            if 'mehrfamilien' in cat:
                return "Mehrfamilienhaus"
            if 'einfamilien' in cat:
                return "Einfamilienhaus"
            if 'gewerbe' in cat or 'industrie' in cat:
                return "Gewerbe/Industrie"
            if 'landwirtschaft' in cat:
                return "Landwirtschaftsgebaeude"

        # 4. Default: Nur wenn keine anderen Indikatoren
        if bundle.gwr_category:
            return "Wohngebaeude"

        return "Gebaeude"

    def _proportions_section(self, bundle: BuildingDataBundle) -> str:
        """Quick Win #1: Proportionen-Berechnung für viewBox 700×480"""
        lines = ["## 10. Proportionen (für viewBox 700×480)"]

        # Zeichenfläche berechnen
        draw_width = self.VIEWBOX_WIDTH - self.OFFSET_LEFT - self.OFFSET_RIGHT  # 550px
        draw_height = self.VIEWBOX_HEIGHT - self.OFFSET_TOP - self.OFFSET_BOTTOM  # 380px

        # Gebäudehöhe bestimmen (höchste Zone oder First)
        max_height = bundle.firsthoehe_m or bundle.traufhoehe_m or 10.0
        if bundle.zones:
            zone_heights = [z.gebaeudehoehe_m or z.firsthoehe_m or z.traufhoehe_m or 0 for z in bundle.zones]
            if zone_heights:
                max_height = max(max_height, max(zone_heights))

        # Gebäudebreite aus Polygon-BoundingBox
        building_width = bundle.bbox_width_m or 30.0

        # Massstab berechnen (1m = X Pixel)
        scale_height = draw_height / max_height if max_height > 0 else 1.0
        scale_width = draw_width / building_width if building_width > 0 else 1.0
        scale = min(scale_height, scale_width)  # Passender Massstab

        lines.append("")
        lines.append(f"- **Massstab:** 1m = {scale:.1f}px (ca. 1:{int(1000/scale)})")
        lines.append(f"- **Zeichenfläche:** {draw_width}px × {draw_height}px")
        lines.append(f"- **Gebäudehöhe:** {max_height:.1f}m = {max_height * scale:.0f}px")
        lines.append(f"- **Gebäudebreite:** {building_width:.1f}m = {building_width * scale:.0f}px")
        lines.append("")
        lines.append("**Offsets:**")
        lines.append(f"- Links: {self.OFFSET_LEFT}px (Höhenskala)")
        lines.append(f"- Unten: {self.OFFSET_BOTTOM}px (Terrain)")
        lines.append(f"- Rechts: {self.OFFSET_RIGHT}px (Lagenbeschriftung)")
        lines.append(f"- Oben: {self.OFFSET_TOP}px (Titel)")

        # Zonen-Höhen in Pixeln
        if bundle.zones and len(bundle.zones) > 1:
            lines.append("")
            lines.append("**Zonen-Höhen in Pixeln:**")
            for z in bundle.zones:
                h = z.gebaeudehoehe_m or z.firsthoehe_m or z.traufhoehe_m
                if h:
                    lines.append(f"- {z.name}: {h:.1f}m = {h * scale:.0f}px")

        return "\n".join(lines)

    def _scaffolding_spec_section(self) -> str:
        """Quick Win #3: Layher Blitz 70 Gerüst-Spezifikation"""
        return """## 11. Gerüst-Spezifikation (Layher Blitz 70)

| Parameter | Wert | Bedeutung |
|-----------|------|-----------|
| **Feldbreite** | 2.57m | Standard-Feldlänge |
| **Lagenhöhe** | 2.0m | Vertikaler Abstand |
| **Ständerabstand** | 3.07m | Max. Ständerabstand |
| **Fassadenabstand** | 0.30m | Abstand zur Fassade |
| **Breitenklasse** | W09 (0.70m) | Gangbreite |

**Für SVG-Zeichnung:**
- Ständer alle 2.57m (oder kürzer bei Ecken)
- Beläge auf jeder Lagenhöhe (2.0m)
- Gerüst 0.30m VOR der Fassade
- Verankerungen alle 4m horizontal/vertikal"""

    def _calculate_courtyard_bbox(self, bundle: BuildingDataBundle) -> Optional[dict]:
        """Quick Win #4: Innenhof-BoundingBox für U-Form berechnen"""
        if not bundle.polygon or len(bundle.polygon) < 6:
            return None

        # Nur bei U-Form oder komplexer Form
        if not bundle.building_shape or bundle.building_shape.lower() not in ['u-form', 'h-form', 'komplex']:
            return None

        try:
            from shapely.geometry import Polygon as ShapelyPolygon

            poly = ShapelyPolygon(bundle.polygon)
            if not poly.is_valid:
                return None

            convex_hull = poly.convex_hull
            courtyard = convex_hull.difference(poly)

            if courtyard.is_empty or courtyard.area < 10:  # Min 10m² für Innenhof
                return None

            # BoundingBox des Innenhofs
            minx, miny, maxx, maxy = courtyard.bounds
            return {
                "min_e": minx,
                "max_e": maxx,
                "min_n": miny,
                "max_n": maxy,
                "area_m2": courtyard.area,
            }
        except Exception:
            return None


# Singleton
_generator_instance: Optional[UnifiedPromptGenerator] = None


def get_prompt_generator() -> UnifiedPromptGenerator:
    """Gibt die Singleton-Instanz zurueck"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = UnifiedPromptGenerator()
    return _generator_instance
