# backend/app/services/smart_building/validation.py
"""
Validierungsfunktionen für SmartBuildingService.

BUG-011: Höhen-Validierung
BUG-012: Zone/API-Konsistenz

Erstellt: 30.12.2025
"""

import logging
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .models import BuildingDataBundle

logger = logging.getLogger(__name__)

# Minimalhöhen nach Gebäudekategorie (GKAT)
MIN_HEIGHTS_BY_GKAT = {
    1020: 6,   # EFH
    1030: 9,   # MFH
    1040: 9,   # Wohngebäude mit Nebennutzung
    1060: 12,  # Gebäude für Bildung/Kultur (Schulen, Museen)
    1080: 12,  # Gebäude für Gesundheit
    1110: 15,  # Kirchen (Kirchenschiff typisch > 15m)
    1130: 12,  # Museen, Bibliotheken
    1212: 10,  # Industriegebäude
}


def validate_heights(bundle: "BuildingDataBundle") -> List[str]:
    """
    Prüft Höhendaten auf Plausibilität (BUG-011).

    Prüfungen:
    1. Minimalhöhe nach Gebäudekategorie
    2. Geschoss-Plausibilität (2.5-4.0m pro Geschoss)
    3. First > Traufe

    Args:
        bundle: BuildingDataBundle mit Höhendaten

    Returns:
        Liste von Warnungen (werden zu bundle.warnings hinzugefügt)
    """
    warnings = []

    # 1. Minimalhöhe nach GKAT
    if bundle.gwr_category_code and bundle.firsthoehe_m:
        min_h = MIN_HEIGHTS_BY_GKAT.get(bundle.gwr_category_code, 6)
        if bundle.firsthoehe_m < min_h:
            warning = (
                f"Firsthoehe {bundle.firsthoehe_m:.1f}m unplausibel niedrig "
                f"fuer GKAT {bundle.gwr_category_code} (erwartet >= {min_h}m)"
            )
            warnings.append(warning)
            logger.warning(f"Height validation: {warning}")

    # 2. Geschoss-Plausibilität
    if bundle.gwr_floors and bundle.firsthoehe_m:
        expected_min = bundle.gwr_floors * 2.5
        expected_max = bundle.gwr_floors * 4.5  # Etwas grosszügiger für Altbauten

        if bundle.firsthoehe_m < expected_min:
            warning = (
                f"Hoehe {bundle.firsthoehe_m:.1f}m passt nicht zu "
                f"{bundle.gwr_floors} Geschossen (erwartet >= {expected_min:.1f}m)"
            )
            warnings.append(warning)
            logger.warning(f"Height validation: {warning}")
        elif bundle.firsthoehe_m > expected_max:
            # Bei sehr hohen Gebäuden nicht warnen - könnte Turm sein
            if bundle.gwr_category_code not in [1110, 1060]:  # Kirchen, Kultur
                warning = (
                    f"Hoehe {bundle.firsthoehe_m:.1f}m sehr hoch fuer "
                    f"{bundle.gwr_floors} Geschosse (moeglicherweise Turm)"
                )
                warnings.append(warning)
                logger.info(f"Height validation: {warning}")

    # 3. First > Traufe prüfen
    if bundle.traufhoehe_m and bundle.firsthoehe_m:
        if bundle.firsthoehe_m < bundle.traufhoehe_m:
            warning = (
                f"Firsthoehe ({bundle.firsthoehe_m:.1f}m) kleiner als "
                f"Traufhoehe ({bundle.traufhoehe_m:.1f}m) - Daten inkonsistent!"
            )
            warnings.append(warning)
            logger.error(f"Height validation: {warning}")

    # Warnungen zum Bundle hinzufügen
    for w in warnings:
        bundle.add_warning(w)

    return warnings


def validate_zone_consistency(bundle: "BuildingDataBundle") -> List[str]:
    """
    Prüft Zone/API-Konsistenz (BUG-012).

    Prüfungen:
    1. Bei Gebäuden MIT Turm: Nur Turm-Zone mit API-Höhe vergleichen
    2. Bei Gebäuden OHNE Turm: Alle Zonen mit API-Höhe vergleichen
    3. Zone deutlich über First = möglich (Turm), aber warnen

    WICHTIG (P1 Fix 30.12.2025):
    Bei Kirchen ist die API-Traufhöhe oft die TURM-Höhe (z.B. 46m),
    während das Kirchenschiff nur 25m hoch ist. Das ist KORREKT!
    -> Keine Warnung für niedrigere Zonen wenn Turm vorhanden.

    Args:
        bundle: BuildingDataBundle mit Zonen

    Returns:
        Liste von Warnungen
    """
    warnings = []

    if not bundle.zones:
        return warnings

    # P1 Fix: Prüfe ob Gebäude einen Turm/Kuppel hat
    has_tower = any(z.zone_type in ["turm", "kuppel"] for z in bundle.zones)
    is_church = bundle.gwr_category_code == 1110 or (
        bundle.building_type and "kirche" in bundle.building_type.lower()
    )

    # Finde die höchste Zone (sollte dem API-First entsprechen)
    max_zone = max(bundle.zones, key=lambda z: z.firsthoehe_m or z.gebaeudehoehe_m or 0)
    max_zone_height = max_zone.firsthoehe_m or max_zone.gebaeudehoehe_m or 0

    for zone in bundle.zones:
        zone_first = zone.firsthoehe_m or zone.gebaeudehoehe_m or 0

        # 1. Zone unter Traufhöhe prüfen
        if bundle.traufhoehe_m and zone_first > 0:
            # P1 Fix: Bei Gebäuden mit Turm/Kuppel KEINE Warnung für niedrigere Zonen
            if has_tower or is_church:
                # Nur die höchste Zone (Turm) mit API vergleichen
                if zone == max_zone:
                    # Turm sollte ungefähr zur API-First passen
                    if bundle.firsthoehe_m and abs(zone_first - bundle.firsthoehe_m) > 10:
                        warning = (
                            f"Hoechste Zone '{zone.name}' ({zone_first:.1f}m) weicht stark "
                            f"von API-First ({bundle.firsthoehe_m:.1f}m) ab"
                        )
                        warnings.append(warning)
                        logger.warning(f"Zone validation: {warning}")
                # Andere Zonen (Kirchenschiff, Seitenschiffe) nicht warnen - die sind
                # absichtlich niedriger als der Turm!
            else:
                # Standard-Validierung für Gebäude OHNE Turm
                if zone_first < bundle.traufhoehe_m * 0.8:  # 20% Toleranz
                    warning = (
                        f"Zone '{zone.name}' ({zone_first:.1f}m) deutlich unter "
                        f"API-Traufhoehe ({bundle.traufhoehe_m:.1f}m) - Zone-Daten pruefen!"
                    )
                    warnings.append(warning)
                    logger.error(f"Zone validation: {warning}")

        # 2. Zone sehr hoch über First = möglicherweise Turm/Kuppel
        if bundle.firsthoehe_m and zone_first > 0:
            if zone_first > bundle.firsthoehe_m * 1.5:
                # Nur Info, kein Fehler - kann bei Türmen korrekt sein
                if zone.zone_type not in ["turm", "kuppel"]:
                    warning = (
                        f"Zone '{zone.name}' ({zone_first:.1f}m) deutlich ueber "
                        f"API-First ({bundle.firsthoehe_m:.1f}m) - als Turm/Kuppel klassifizieren?"
                    )
                    warnings.append(warning)
                    logger.info(f"Zone validation: {warning}")

    # Warnungen zum Bundle hinzufügen
    for w in warnings:
        bundle.add_warning(w)

    return warnings
