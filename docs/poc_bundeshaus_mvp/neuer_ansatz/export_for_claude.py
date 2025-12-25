# backend/app/services/export_for_claude.py
"""
Export-Service für Claude.ai Hybrid-Workflow.

Generiert strukturiertes JSON mit allen Gebäudedaten,
das in Claude.ai eingefügt werden kann für professionelle
SVG-Generierung.

Version: 1.0
Datum: 25.12.2025
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


# =============================================================================
# DATENMODELLE FÜR EXPORT
# =============================================================================

class ExportCoordinate(BaseModel):
    """LV95 Koordinate"""
    e: float  # Ost (Easting)
    n: float  # Nord (Northing)


class ExportFassade(BaseModel):
    """Fassaden-Daten für Export"""
    id: str                          # "N", "E", "S", "W" oder "F1", "F2"
    name: str                        # "Nord", "Ost", etc.
    laenge_m: float
    ausrichtung_grad: float          # 0=N, 90=E, 180=S, 270=W
    start_punkt: ExportCoordinate
    end_punkt: ExportCoordinate
    hoehe_m: float                   # Gerüsthöhe für diese Fassade
    ausmass_m2: float               # NPK 114 Ausmass


class ExportZone(BaseModel):
    """Gebäudezone für Export"""
    id: str
    name: str
    typ: str                         # hauptgebaeude, turm, arkade, etc.
    traufhoehe_m: Optional[float]
    firsthoehe_m: Optional[float]
    gebaeudehoehe_m: float
    fassaden_ids: List[str]
    farbe: str                       # Hex-Farbe für Darstellung
    beruesten: bool = True


class ExportZugang(BaseModel):
    """Gerüst-Zugang für Export"""
    id: str                          # "Z1", "Z2"
    fassade_id: str
    position_percent: float          # 0.0 - 1.0
    position_m: float
    grund: str


class ExportGeruest(BaseModel):
    """Gerüst-Konfiguration für Export"""
    system: str = "Layher Blitz 70"
    breitenklasse: str = "W09"
    fassadenabstand_m: float = 0.30
    feldlaengen_m: List[float]       # [3.07, 2.57, ...]
    rahmenhoehen_m: List[float]      # [2.00, 1.50, ...]
    anzahl_lagen: int
    gesamthoehe_m: float
    gesamtflaeche_m2: float
    verankerung_raster_h_m: float = 4.0
    verankerung_raster_v_m: float = 4.0


class ExportForClaude(BaseModel):
    """Vollständiger Export für Claude.ai"""
    
    # Meta
    export_version: str = "1.0"
    export_datum: str
    
    # Gebäude-Grunddaten
    gebaeude: Dict[str, Any]
    
    # Geometrie
    polygon: List[List[float]]       # [[e, n], [e, n], ...]
    polygon_vereinfacht: List[List[float]]  # Douglas-Peucker
    
    # Zonen und Fassaden
    zonen: List[ExportZone]
    fassaden: List[ExportFassade]
    
    # Gerüst
    geruest: ExportGeruest
    zugaenge: List[ExportZugang]
    
    # Berechnungen
    ausmasse: Dict[str, Any]         # NPK 114 Details
    material: Dict[str, Any]         # Layher Schätzung
    
    # Prompt-Hinweise
    prompt_hinweise: List[str]


# =============================================================================
# FARBEN FÜR ZONEN
# =============================================================================

ZONE_FARBEN = {
    "hauptgebaeude": "#E3F2FD",  # Hellblau
    "turm": "#FFF3E0",           # Hellorange
    "anbau": "#F3E5F5",          # Helllila
    "arkade": "#E8F5E9",         # Hellgrün
    "kuppel": "#FCE4EC",         # Hellrosa
    "vordach": "#FFF8E1",        # Hellgelb
    "garage": "#EFEBE9",         # Hellbraun
    "unknown": "#F5F5F5",        # Hellgrau
}


# =============================================================================
# HAUPTFUNKTION
# =============================================================================

def export_building_for_claude(
    gebaeude_data: dict,
    polygon: List[List[float]],
    polygon_vereinfacht: List[List[float]],
    zonen: List[dict],
    fassaden: List[dict],
    geruest_config: dict,
    zugaenge: List[dict],
    ausmasse: dict,
    material: dict
) -> ExportForClaude:
    """
    Erstellt einen vollständigen Export für Claude.ai.
    
    Args:
        gebaeude_data: GWR-Daten (egid, adresse, gkat, etc.)
        polygon: Original-Polygon als Liste von [e, n] Koordinaten
        polygon_vereinfacht: Vereinfachtes Polygon
        zonen: Liste der BuildingZone Dicts
        fassaden: Liste der Fassaden mit Geometrie
        geruest_config: Gerüst-Konfiguration
        zugaenge: Liste der Zugänge
        ausmasse: NPK 114 Ausmass-Berechnungen
        material: Material-Schätzung
    
    Returns:
        ExportForClaude Objekt
    """
    
    # Zonen mit Farben anreichern
    export_zonen = []
    for z in zonen:
        zone_typ = z.get('type', z.get('typ', 'unknown'))
        export_zonen.append(ExportZone(
            id=z.get('id', 'zone_1'),
            name=z.get('name', 'Hauptgebäude'),
            typ=zone_typ,
            traufhoehe_m=z.get('traufhoehe_m'),
            firsthoehe_m=z.get('firsthoehe_m'),
            gebaeudehoehe_m=z.get('gebaeudehoehe_m', 10.0),
            fassaden_ids=z.get('fassaden_ids', []),
            farbe=ZONE_FARBEN.get(zone_typ, ZONE_FARBEN['unknown']),
            beruesten=z.get('beruesten', True)
        ))
    
    # Fassaden konvertieren
    export_fassaden = []
    for f in fassaden:
        export_fassaden.append(ExportFassade(
            id=f.get('id', 'F1'),
            name=f.get('name', f.get('id', 'Fassade')),
            laenge_m=f.get('laenge_m', 0),
            ausrichtung_grad=f.get('ausrichtung_grad', 0),
            start_punkt=ExportCoordinate(
                e=f.get('start_e', f.get('start_coord', [0, 0])[0]),
                n=f.get('start_n', f.get('start_coord', [0, 0])[1])
            ),
            end_punkt=ExportCoordinate(
                e=f.get('end_e', f.get('end_coord', [0, 0])[0]),
                n=f.get('end_n', f.get('end_coord', [0, 0])[1])
            ),
            hoehe_m=f.get('hoehe_m', f.get('geruest_hoehe_m', 10.0)),
            ausmass_m2=f.get('ausmass_m2', 0)
        ))
    
    # Zugänge konvertieren
    export_zugaenge = []
    for z in zugaenge:
        export_zugaenge.append(ExportZugang(
            id=z.get('id', 'Z1'),
            fassade_id=z.get('fassade_id', 'N'),
            position_percent=z.get('position_percent', 0.5),
            position_m=z.get('position_m', 0),
            grund=z.get('grund', '')
        ))
    
    # Gerüst-Konfiguration
    export_geruest = ExportGeruest(
        system=geruest_config.get('system', 'Layher Blitz 70'),
        breitenklasse=geruest_config.get('breitenklasse', 'W09'),
        fassadenabstand_m=geruest_config.get('fassadenabstand_m', 0.30),
        feldlaengen_m=geruest_config.get('feldlaengen_m', [3.07, 2.57, 2.07]),
        rahmenhoehen_m=geruest_config.get('rahmenhoehen_m', [2.00, 1.50, 1.00]),
        anzahl_lagen=geruest_config.get('anzahl_lagen', 5),
        gesamthoehe_m=geruest_config.get('gesamthoehe_m', 10.0),
        gesamtflaeche_m2=geruest_config.get('gesamtflaeche_m2', 0),
        verankerung_raster_h_m=geruest_config.get('verankerung_raster_h_m', 4.0),
        verankerung_raster_v_m=geruest_config.get('verankerung_raster_v_m', 4.0)
    )
    
    # Prompt-Hinweise generieren
    prompt_hinweise = _generate_prompt_hints(
        gebaeude_data, export_zonen, export_fassaden, export_geruest
    )
    
    return ExportForClaude(
        export_version="1.0",
        export_datum=datetime.now().isoformat(),
        gebaeude=gebaeude_data,
        polygon=polygon,
        polygon_vereinfacht=polygon_vereinfacht,
        zonen=export_zonen,
        fassaden=export_fassaden,
        geruest=export_geruest,
        zugaenge=export_zugaenge,
        ausmasse=ausmasse,
        material=material,
        prompt_hinweise=prompt_hinweise
    )


def _generate_prompt_hints(
    gebaeude: dict,
    zonen: List[ExportZone],
    fassaden: List[ExportFassade],
    geruest: ExportGeruest
) -> List[str]:
    """Generiert kontextspezifische Hinweise für den Prompt."""
    
    hints = []
    
    # Gebäude-Komplexität
    if len(zonen) > 1:
        hints.append(f"Komplexes Gebäude mit {len(zonen)} Höhenzonen - unterschiedliche Höhen beachten")
    
    # Spezielle Zonen
    zone_typen = [z.typ for z in zonen]
    if 'turm' in zone_typen:
        hints.append("Türme vorhanden - evtl. Sonderkonstruktion (Hängegerüst) erwähnen")
    if 'kuppel' in zone_typen:
        hints.append("Kuppel vorhanden - nicht mit Standgerüst einrüstbar")
    if 'arkade' in zone_typen:
        hints.append("Arkaden vorhanden - niedrigere Höhe, Bögen darstellen")
    
    # Höhenvariationen
    hoehen = [z.gebaeudehoehe_m for z in zonen]
    if hoehen:
        max_h = max(hoehen)
        min_h = min(hoehen)
        if max_h - min_h > 5:
            hints.append(f"Grosse Höhenvariation: {min_h:.1f}m bis {max_h:.1f}m")
    
    # Gerüst-Umfang
    if geruest.gesamtflaeche_m2 > 500:
        hints.append(f"Grosses Gerüst ({geruest.gesamtflaeche_m2:.0f} m²) - mehrere Zugänge wichtig")
    
    # Polygon-Komplexität
    if gebaeude.get('polygon_punkte', 0) > 10:
        hints.append("Komplexer Grundriss - vereinfachtes Polygon für Übersicht verwenden")
    
    return hints


# =============================================================================
# EXPORT-FORMATE
# =============================================================================

def to_json(export: ExportForClaude, indent: int = 2) -> str:
    """Exportiert als formatiertes JSON."""
    return export.model_dump_json(indent=indent)


def to_markdown(export: ExportForClaude) -> str:
    """
    Exportiert als Markdown mit eingebettetem JSON.
    Optimiert für Copy-Paste in Claude.ai.
    """
    
    md = f"""# Gerüstplan-Daten für Claude.ai

## Gebäude

- **Adresse:** {export.gebaeude.get('adresse', 'Unbekannt')}
- **EGID:** {export.gebaeude.get('egid', '-')}
- **Kategorie:** {export.gebaeude.get('gkat_text', export.gebaeude.get('gkat', '-'))}
- **Grundfläche:** {export.gebaeude.get('garea', '-')} m²

## Zonen

| Zone | Typ | Höhe | Fassaden |
|------|-----|------|----------|
"""
    
    for z in export.zonen:
        fassaden_str = ", ".join(z.fassaden_ids) if z.fassaden_ids else "alle"
        md += f"| {z.name} | {z.typ} | {z.gebaeudehoehe_m:.1f}m | {fassaden_str} |\n"
    
    md += f"""
## Fassaden

| ID | Länge | Höhe | Ausmass |
|----|-------|------|---------|
"""
    
    for f in export.fassaden:
        md += f"| {f.id} ({f.name}) | {f.laenge_m:.1f}m | {f.hoehe_m:.1f}m | {f.ausmass_m2:.1f} m² |\n"
    
    md += f"""
## Gerüst-Konfiguration

- **System:** {export.geruest.system}
- **Breitenklasse:** {export.geruest.breitenklasse}
- **Gesamthöhe:** {export.geruest.gesamthoehe_m:.1f}m
- **Gesamtfläche:** {export.geruest.gesamtflaeche_m2:.1f} m²
- **Lagen:** {export.geruest.anzahl_lagen}
- **Verankerung:** {export.geruest.verankerung_raster_h_m}m × {export.geruest.verankerung_raster_v_m}m

## Zugänge

"""
    
    for z in export.zugaenge:
        md += f"- **{z.id}:** Fassade {z.fassade_id} bei {z.position_percent*100:.0f}% ({z.grund})\n"
    
    if export.prompt_hinweise:
        md += "\n## Hinweise\n\n"
        for h in export.prompt_hinweise:
            md += f"- {h}\n"
    
    md += f"""
## Vollständige Daten (JSON)

```json
{export.model_dump_json(indent=2)}
```

---

*Exportiert am {export.export_datum}*
"""
    
    return md


def to_clipboard_text(export: ExportForClaude) -> str:
    """
    Generiert Text optimiert für Clipboard.
    Enthält Prompt-Template + Daten.
    """
    
    prompt_template = get_prompt_template()
    data_json = export.model_dump_json(indent=2)
    
    return f"""{prompt_template}

## Gebäudedaten

```json
{data_json}
```
"""


# =============================================================================
# PROMPT-TEMPLATE
# =============================================================================

def get_prompt_template() -> str:
    """Gibt das Prompt-Template für Claude.ai zurück."""
    
    return """# Professionelle Gerüstpläne erstellen

Ich habe Gebäudedaten aus einer Geodaten-App exportiert. Bitte erstelle professionelle Gerüstpläne.

## Gewünschte Ausgaben

1. **Grundriss (Draufsicht)** - M 1:200
   - Gebäude-Polygon mit Zonen (farbcodiert)
   - Gerüstfläche (schraffiert, 30cm Abstand)
   - Ständerpositionen (Punkte)
   - Verankerungen (Kreise)
   - Zugänge (Z1, Z2, etc.)
   - Masslinien mit Beschriftung
   - Nordpfeil und Massstabsbalken
   - Legende

2. **Schnitt** - M 1:100
   - Gebäudeprofil mit Höhenzonen
   - Gerüst mit Lagen (L1, L2, etc.)
   - Terrain-Linie
   - Höhenkoten
   - Verankerungspunkte

3. **Ansicht Hauptfassade** - M 1:100
   - Fassade mit Gerüst
   - Felder (F1, F2, etc.) mit Längen
   - Lagen nummeriert
   - Verankerungsraster (4m × 4m)
   - Zugang markiert

## Stil-Anforderungen

- **Professionelle Architekturzeichnung**, nicht technisches Diagramm
- Klare Linien, lesbare Beschriftungen
- Farbcodierung für Zonen (siehe Daten)
- Druckfähig auf A3

## Wichtige Regeln

- Alle Masse aus den Daten übernehmen, NICHT erfinden
- Massstab einhalten
- Bei komplexen Gebäuden: Zonen unterschiedlich darstellen
- Zugänge gemäss SUVA (max. 50m Fluchtweg)

Bitte generiere die SVGs nacheinander. Ich gebe Feedback für Anpassungen.
"""


# =============================================================================
# API-ENDPOINT HELPER
# =============================================================================

def create_export_response(export: ExportForClaude, format: str = "json") -> dict:
    """
    Erstellt die API-Response für den Export-Endpoint.
    
    Args:
        export: ExportForClaude Objekt
        format: "json", "markdown", oder "clipboard"
    
    Returns:
        Dict mit content und metadata
    """
    
    if format == "markdown":
        content = to_markdown(export)
        content_type = "text/markdown"
    elif format == "clipboard":
        content = to_clipboard_text(export)
        content_type = "text/plain"
    else:
        content = to_json(export)
        content_type = "application/json"
    
    return {
        "content": content,
        "content_type": content_type,
        "export_version": export.export_version,
        "export_datum": export.export_datum,
        "gebaeude_adresse": export.gebaeude.get('adresse', ''),
        "gebaeude_egid": export.gebaeude.get('egid', ''),
        "zonen_count": len(export.zonen),
        "fassaden_count": len(export.fassaden),
        "zugaenge_count": len(export.zugaenge)
    }
