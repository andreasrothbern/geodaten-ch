# backend/app/services/smart_building/research_integration.py
"""
Integration von bekannten Gebäuden und Claude-Recherche.

Dieses Modul wird von service.py verwendet um:
1. Bekannte Gebäude zuerst zu prüfen (kostenlos, sofort)
2. Claude Research API als Fallback zu nutzen
"""

import logging
from typing import Optional, Dict, Any, List

from .models import BuildingDataBundle, DataSource, ZoneInfo

logger = logging.getLogger(__name__)


async def collect_building_research(
    bundle: BuildingDataBundle,
    force_refresh: bool = False
) -> None:
    """
    Sammelt Gebäude-Informationen.

    PRIORITÄT:
    1. Bekannte Gebäude (known_buildings.py) - sofort, kostenlos
    2. Claude Research API - wenn nicht bekannt

    Args:
        bundle: BuildingDataBundle das befüllt wird
        force_refresh: Cache ignorieren
    """
    # 1. ZUERST: Bekannte Gebäude prüfen (kostenlos, sofort)
    try:
        from .known_buildings import get_known_building

        known = get_known_building(egid=bundle.egid, address=bundle.address_matched)
        if known:
            bundle.building_name = known.get("building_name")
            bundle.building_type = known.get("building_type")
            bundle.architectural_style = known.get("architectural_style")
            bundle.construction_year = known.get("construction_year") or bundle.construction_year
            bundle.research_confidence = 1.0  # 100% Konfidenz für bekannte Gebäude
            bundle.add_source(DataSource.MANUAL)

            # Zonen aus bekannten Gebäuden für spätere Verwendung speichern
            if known.get("zones"):
                bundle._known_zones = known["zones"]
                bundle.complexity = known.get("complexity", "complex")
                bundle.has_towers = any(z.get("zone_type") == "turm" for z in known["zones"])

            logger.info(f"Bekanntes Gebäude erkannt: {bundle.building_name}")
            return  # Fertig, keine Claude-Recherche nötig

    except Exception as e:
        logger.warning(f"Known buildings lookup failed: {e}")

    # 2. Claude Research API (wenn nicht bekannt)
    try:
        from app.services.prompts import get_research_service
        research_service = get_research_service()

        gwr_data = {
            "building_category": bundle.gwr_category,
            "construction_year": bundle.construction_year,
            "floors": bundle.gwr_floors,
        }

        research = await research_service.get_building_research(
            adresse=bundle.address_matched,
            egid=bundle.egid,
            coordinates=(bundle.lv95_e, bundle.lv95_n) if bundle.lv95_e else None,
            gwr_data=gwr_data,
            force_refresh=force_refresh
        )

        if research:
            bundle.building_name = research.building_name
            bundle.building_type = research.building_type
            bundle.architectural_style = research.architectural_style
            bundle.construction_year = research.construction_year or bundle.construction_year
            bundle.research_confidence = research.confidence

            if research.source == "claude_research":
                bundle.add_source(DataSource.CLAUDE_RESEARCH)
            elif research.source == "cache":
                bundle.add_source(DataSource.CACHE)

            # Vorgeschlagene Zonen für spätere Analyse
            if research.suggested_zones:
                bundle._research_zones = research.suggested_zones

    except Exception as e:
        logger.error(f"Research error: {e}")
        bundle.add_warning(f"Gebäude-Recherche fehlgeschlagen: {str(e)}")


def create_zones_from_known_building(bundle: BuildingDataBundle) -> bool:
    """
    Erstellt Zonen aus bekannten Gebäude-Daten.

    Args:
        bundle: BuildingDataBundle

    Returns:
        True wenn Zonen erstellt wurden, False sonst
    """
    if not hasattr(bundle, '_known_zones') or not bundle._known_zones:
        return False

    bundle.zones = []
    for i, z in enumerate(bundle._known_zones):
        zone = ZoneInfo(
            id=f"zone_{i+1}",
            name=z.get("name", f"Zone {i+1}"),
            zone_type=z.get("zone_type", "hauptgebaeude"),
            traufhoehe_m=z.get("traufhoehe_m"),
            firsthoehe_m=z.get("firsthoehe_m"),
            gebaeudehoehe_m=z.get("gebaeudehoehe_m") or z.get("firsthoehe_m"),
            beruesten=z.get("beruesten", True),
            sonderkonstruktion=z.get("sonderkonstruktion", False),
            confidence=1.0,  # Bekannte Gebäude haben 100% Konfidenz
            source=DataSource.MANUAL,
        )
        bundle.zones.append(zone)

    logger.info(f"Erstellt {len(bundle.zones)} Zonen aus bekannten Gebäude-Daten")
    return True


def create_church_zones(bundle: BuildingDataBundle) -> bool:
    """
    Erstellt verbesserte Zonen für Kirchen.

    Bei Kirchen ist die gemessene Traufhöhe oft die Höhe der Seitenschiffe,
    nicht des Kirchenschiffs. Diese Funktion korrigiert das.

    Args:
        bundle: BuildingDataBundle

    Returns:
        True wenn Zonen erstellt wurden, False sonst
    """
    if not bundle.has_extreme_height_diff():
        return False

    # Nur für Sakralbauten oder unbekannte Gebäude mit extremer Höhendifferenz
    building_type = (bundle.building_type or "").lower()
    is_church = any(word in building_type for word in ["kirche", "sakral", "kathedrale", "münster"])

    if not is_church and bundle.building_name:
        return False  # Kein Sakralbau und bekannter Name → Standard-Zonen

    height_diff = (bundle.firsthoehe_m or 0) - (bundle.traufhoehe_m or 0)

    # Kirchen-spezifische Höhenschätzung:
    # - Seitenschiffe: gemessene Traufhöhe (oft die niedrigste)
    # - Kirchenschiff: ca. 2x Seitenschiffe oder 40-50% der Firsthöhe
    # - Turm: Firsthöhe

    trauf = bundle.traufhoehe_m or 10
    first = bundle.firsthoehe_m or 50

    # Schätzung Kirchenschiff-Höhe: zwischen Seitenschiff und Turm
    kirchenschiff_hoehe = max(trauf * 2, first * 0.4)
    kirchenschiff_hoehe = min(kirchenschiff_hoehe, first * 0.5)  # Max 50% der Firsthöhe

    bundle.zones = []

    # Zone 1: Seitenschiffe (niedrigste Traufe)
    bundle.zones.append(ZoneInfo(
        id="zone_1",
        name="Seitenschiffe",
        zone_type="anbau",
        traufhoehe_m=trauf,
        firsthoehe_m=trauf + 3,  # Kleines Dach
        gebaeudehoehe_m=trauf + 3,
        beruesten=True,
        sonderkonstruktion=False,
        confidence=0.6,
        source=DataSource.CALCULATED,
        notes=f"Geschätzt als niedrigste gemessene Traufe"
    ))

    # Zone 2: Kirchenschiff (Hauptschiff)
    bundle.zones.append(ZoneInfo(
        id="zone_2",
        name="Kirchenschiff",
        zone_type="hauptgebaeude",
        traufhoehe_m=kirchenschiff_hoehe,
        firsthoehe_m=kirchenschiff_hoehe + 5,
        gebaeudehoehe_m=kirchenschiff_hoehe + 5,
        beruesten=True,
        sonderkonstruktion=False,
        confidence=0.5,
        source=DataSource.CALCULATED,
        notes=f"Geschätzt aus Höhendifferenz ({height_diff:.1f}m)"
    ))

    # Zone 3: Turm
    bundle.zones.append(ZoneInfo(
        id="zone_3",
        name="Turm",
        zone_type="turm",
        traufhoehe_m=kirchenschiff_hoehe,
        firsthoehe_m=first,
        gebaeudehoehe_m=first,
        beruesten=True,
        sonderkonstruktion=True,
        confidence=0.7,
        source=DataSource.CALCULATED,
        notes=f"Turm erkannt aus extremer Höhendifferenz ({height_diff:.1f}m)"
    ))

    bundle.complexity = "complex"
    bundle.has_towers = True
    bundle.has_height_variations = True

    logger.info(f"Kirchen-Zonen erstellt: Seitenschiff ({trauf:.1f}m), Kirchenschiff ({kirchenschiff_hoehe:.1f}m), Turm ({first:.1f}m)")
    return True
