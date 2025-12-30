# backend/app/services/smart_building/known_buildings.py
"""
Bekannte Gebäude mit vordefinierten Daten.

Diese Gebäude werden ohne Claude-Recherche erkannt und haben
korrekte Höhenzonen, Gebäudenamen und Architektur-Informationen.

Verwendung:
    from app.services.smart_building.known_buildings import get_known_building

    known = get_known_building(egid="191821074")
    if known:
        bundle.building_name = known["building_name"]
        ...

Stand: 30.12.2025
"""

from typing import Optional, Dict, Any, List

# Bekannte Gebäude mit korrekten Daten
# Key kann EGID oder Adresse sein
KNOWN_BUILDINGS: Dict[str, Dict[str, Any]] = {
    # ========================================
    # BERN
    # ========================================

    # Bundeshaus
    "2242547": {
        "egid": "2242547",
        "building_name": "Bundeshaus",
        "building_type": "Parlamentsgebaeude",
        "architectural_style": "Neorenaissance / Historismus",
        "construction_year": 1902,
        "complexity": "complex",
        "roof_type": "kuppel",  # Dachform-Override: Hauptmerkmal ist die Kuppel!
        "zones": [
            {
                "name": "Arkaden",
                "zone_type": "arkade",
                "traufhoehe_m": 6.0,
                "firsthoehe_m": 6.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Hauptgebäude",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 25.0,
                "firsthoehe_m": 30.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Kuppel",
                "zone_type": "kuppel",
                "traufhoehe_m": 30.0,
                "firsthoehe_m": 64.0,
                "beruesten": True,
                "sonderkonstruktion": True,
            },
        ],
        "tower_config": None,
        "special_features": ["Kuppel", "Arkaden", "Ehrenhof", "Skulpturen"],
    },

    # Kirche St. Peter und Paul (Rathausgasse 2)
    "191821074": {
        "egid": "191821074",
        "building_name": "Kirche St. Peter und Paul",
        "building_type": "Christkatholische Kathedralkirche",
        "architectural_style": "Neugotik",
        "construction_year": 1864,
        "complexity": "complex",
        "roof_type": "satteldach_mit_turm",  # Kirchendach mit Spitzhelm-Turm
        "zones": [
            {
                "name": "Kirchenschiff",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 18.0,  # Kirchenschiff ist HÖHER als die gemessene Traufe!
                "firsthoehe_m": 25.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Seitenschiffe",
                "zone_type": "anbau",
                "traufhoehe_m": 9.0,
                "firsthoehe_m": 12.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Turm",
                "zone_type": "turm",
                "traufhoehe_m": 25.0,  # Turm startet über Kirchenschiff
                "firsthoehe_m": 54.6,
                "beruesten": True,
                "sonderkonstruktion": True,
            },
        ],
        "tower_config": {
            "count": 1,
            "position": "zentral-west",
            "form": "Spitzhelm",
            "height_m": 54.6,
        },
        "special_features": ["Gotische Fenster", "Spitzhelm", "Sandstein-Fassade"],
    },

    # Berner Muenster
    "1230337": {
        "egid": "1230337",
        "building_name": "Berner Muenster",
        "building_type": "Reformierte Stadtkirche",
        "architectural_style": "Spaetgotik",
        "construction_year": 1421,  # Baubeginn, vollendet 1893
        "complexity": "complex",
        "roof_type": "satteldach_mit_turm",  # Gotisches Dach mit Kirchturm
        "zones": [
            {
                "name": "Kirchenschiff",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 22.0,
                "firsthoehe_m": 28.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Seitenkapellen",
                "zone_type": "anbau",
                "traufhoehe_m": 12.0,
                "firsthoehe_m": 15.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Turm",
                "zone_type": "turm",
                "traufhoehe_m": 28.0,
                "firsthoehe_m": 100.3,  # Höchster Kirchturm der Schweiz
                "beruesten": True,
                "sonderkonstruktion": True,
            },
        ],
        "tower_config": {
            "count": 1,
            "position": "west",
            "form": "Spitzhelm (offener Helm)",
            "height_m": 100.3,
        },
        "special_features": ["Jüngstes Gericht Portal", "Gotische Wasserspeier", "Chorumgang"],
    },

    # Einsteinhaus
    "1234567": {  # Beispiel-EGID
        "egid": "1234567",
        "building_name": "Einsteinhaus",
        "building_type": "Museum / Wohnhaus",
        "architectural_style": "Barock",
        "construction_year": 1720,
        "complexity": "simple",
        "zones": [
            {
                "name": "Hauptgebäude",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 12.0,
                "firsthoehe_m": 16.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
        ],
        "special_features": ["Laubengang", "Historische Fassade"],
    },

    # Zytglogge
    "1017961": {
        "egid": "1017961",
        "building_name": "Zytglogge",
        "building_type": "Uhrturm / Stadttor",
        "architectural_style": "Gotik / Renaissance",
        "construction_year": 1218,  # Erste Erwaehnung
        "complexity": "complex",
        "roof_type": "pyramidendach",  # Turm mit Pyramidendach
        "zones": [
            {
                "name": "Torhaus",
                "zone_type": "arkade",
                "traufhoehe_m": 8.0,
                "firsthoehe_m": 10.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Turm",
                "zone_type": "turm",
                "traufhoehe_m": 10.0,
                "firsthoehe_m": 54.0,
                "beruesten": True,
                "sonderkonstruktion": True,
            },
        ],
        "tower_config": {
            "count": 1,
            "position": "zentral",
            "form": "Pyramidendach mit Erkern",
            "height_m": 54.0,
        },
        "special_features": ["Astronomische Uhr", "Figurenspiel", "Durchfahrt"],
    },

    # ========================================
    # WEITERE STÄDTE
    # ========================================

    # Grossmünster Zürich (Beispiel)
    # "..." : { ... }
}

# Alias-Mapping: Adresse → EGID
ADDRESS_TO_EGID: Dict[str, str] = {
    "bundesplatz 3, 3011 bern": "2242547",
    "bundesplatz 3, bern": "2242547",
    "rathausgasse 2, 3011 bern": "191821074",
    "rathausgasse 2, bern": "191821074",
    "münsterplatz 1, 3011 bern": "1230337",
    "münsterplatz 1, bern": "1230337",
    "kramgasse 49, 3011 bern": "1234567",
}


def get_known_building(
    egid: Optional[str] = None,
    address: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Sucht ein bekanntes Gebäude nach EGID oder Adresse.

    Args:
        egid: EGID des Gebäudes
        address: Adresse des Gebäudes

    Returns:
        Dict mit Gebäudedaten oder None
    """
    # 1. Direkte EGID-Suche
    if egid and egid in KNOWN_BUILDINGS:
        return KNOWN_BUILDINGS[egid]

    # 2. Adress-Suche
    if address:
        normalized = address.lower().strip()

        # Exakte Übereinstimmung
        if normalized in ADDRESS_TO_EGID:
            egid = ADDRESS_TO_EGID[normalized]
            return KNOWN_BUILDINGS.get(egid)

        # Teilübereinstimmung
        for addr_pattern, egid in ADDRESS_TO_EGID.items():
            if addr_pattern in normalized or normalized in addr_pattern:
                return KNOWN_BUILDINGS.get(egid)

    return None


def get_all_known_egids() -> List[str]:
    """Gibt alle bekannten EGIDs zurück"""
    return list(KNOWN_BUILDINGS.keys())


def is_known_building(egid: Optional[str] = None, address: Optional[str] = None) -> bool:
    """Prüft ob ein Gebäude bekannt ist"""
    return get_known_building(egid=egid, address=address) is not None
