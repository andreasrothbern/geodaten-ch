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
        # NEU: Gebäudeform für korrekten Grundriss
        "building_shape": "U-Form mit Ehrenhof",
        "building_shape_description": "Das Gebäude hat eine U-Form mit offener Seite nach Süden. Der Ehrenhof (Innenhof) ist NICHT zu überdachen und bleibt frei.",
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
        # NEU: Hinweise für SVG-Generierung
        "svg_hints": {
            "grundriss": "U-Form zeichnen! Ehrenhof in der Mitte als Freifläche markieren (NICHT schraffieren).",
            "ansicht": "Kuppel zentral, Arkaden im Erdgeschoss, 3 verschiedene Höhenzonen beachten.",
            "schnitt": "Zeige alle 3 Höhenzonen: Arkaden 6m, Hauptgebäude 25m, Kuppel bis 64m."
        },
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
        # NEU: Gebäudeform
        "building_shape": "Kreuzform (Basilika)",
        "building_shape_description": "Klassische Basilika-Form: Langhaus (Kirchenschiff) mit niedrigeren Seitenschiffen, Querhaus (Transept), Chor im Osten, Turm an der Westfassade.",
        # ANSICHT-KONFIGURATION: Von Westen mit Turm zentriert
        "preferred_view": {
            "direction": "west",
            "description": "Westfassade mit zentriertem Turm",
            "reason": "Der neugotische Westturm (54.6m) ist das Hauptmerkmal der Kirche und sollte im Mittelpunkt der Ansicht stehen.",
        },
        "zones": [
            {
                "name": "Westturm",
                "zone_type": "turm",
                "traufhoehe_m": 25.0,  # Turm startet ueber Kirchenschiff
                "firsthoehe_m": 54.6,
                "beruesten": True,
                "sonderkonstruktion": True,
                "position": "zentral",  # Turm ist zentriert in der Westansicht
            },
            {
                "name": "Kirchenschiff",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 18.0,
                "firsthoehe_m": 25.0,
                "beruesten": True,
                "sonderkonstruktion": False,
                "position": "links_rechts_vom_turm",  # Flanken den Turm
            },
            {
                "name": "Seitenschiffe",
                "zone_type": "anbau",
                "traufhoehe_m": 9.0,
                "firsthoehe_m": 12.0,
                "beruesten": True,
                "sonderkonstruktion": False,
                "position": "aussen",  # Aeussere Flanken
            },
            {
                "name": "Chor",
                "zone_type": "anbau",
                "traufhoehe_m": 12.0,
                "firsthoehe_m": 18.0,
                "beruesten": True,
                "sonderkonstruktion": False,
                "position": "verdeckt",  # Hinter dem Hauptschiff, in Westansicht nicht sichtbar
            },
        ],
        "tower_config": {
            "count": 1,
            "position": "zentral (Westfassade)",
            "form": "Spitzhelm (neugotisch)",
            "height_m": 54.6,
        },
        "special_features": ["Gotische Fenster", "Spitzhelm", "Sandstein-Fassade", "Rosettenfenster", "Portal"],
        # SVG-Hinweise für korrekte Darstellung
        "svg_hints": {
            "grundriss": "Kreuzform zeichnen! Westturm links (quadratisch), Kirchenschiff laenglich, Seitenschiffe schmaler, Chor rechts. Norden nach oben.",
            "ansicht": "WESTANSICHT - ANORDNUNG IM SVG (von links nach rechts): [1] Seitenschiff links (12m hoch) | [2] TURM IN DER MITTE (54.6m mit Spitzhelm) | [3] Seitenschiff rechts (12m hoch). Das Kirchenschiff (25m) ist HINTER dem Turm und teilweise verdeckt. Der Turm muss EXAKT in der horizontalen Mitte des SVG stehen (x=350 bei viewBox 700)!",
            "schnitt": "Querschnitt Ost-West: Turm LINKS (54.6m), Kirchenschiff RECHTS (25m). Basilika-Profil zeigen: Hohes Mittelschiff mit niedrigen Seitenschiffen."
        },
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
    # FIX 30.12.2025: Zone-Hoehe korrigiert (war 12-16m, API sagt 22-26m)
    "1234567": {  # Beispiel-EGID
        "egid": "1234567",
        "building_name": "Einsteinhaus",
        "building_type": "Museum / Wohnhaus",
        "architectural_style": "Barock",
        "construction_year": 1720,
        "complexity": "simple",
        "roof_type": "satteldach",
        "zones": [
            {
                "name": "Hauptgebaeude",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 22.0,  # Korrigiert von 12.0 (API: 22.3m)
                "firsthoehe_m": 26.0,  # Korrigiert von 16.0 (API: 26.2m)
                "beruesten": True,
                "sonderkonstruktion": False,
            },
        ],
        "special_features": ["Laubengang", "Historische Fassade", "Einstein-Wohnung 2. Stock"],
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
    # BERN - Weitere wichtige Gebaeude
    # ========================================

    # Kunstmuseum Bern (Hodlerstrasse 8)
    # HINWEIS: swissBUILDINGS3D liefert falsche Hoehen (7.9m) - hier korrigiert!
    "kunstmuseum_bern": {
        "egid": None,  # EGID muss noch recherchiert werden
        "building_name": "Kunstmuseum Bern",
        "building_type": "Museum",
        "architectural_style": "Neorenaissance / Moderne",
        "construction_year": 1879,
        "complexity": "complex",
        "roof_type": "flachdach",
        # KRITISCH: API-Hoehen sind FALSCH - manueller Override
        "height_override": {
            "enabled": True,
            "reason": "swissBUILDINGS3D misst nur Nebengebaeude (6.7m/7.9m). Reale Hoehen manuell erfasst.",
            "traufhoehe_m": 15.0,
            "firsthoehe_m": 18.0,
        },
        "zones": [
            {
                "name": "Altbau",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 15.0,
                "firsthoehe_m": 18.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Neubau (Stettler)",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 12.0,
                "firsthoehe_m": 15.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Erweiterung",
                "zone_type": "anbau",
                "traufhoehe_m": 8.0,
                "firsthoehe_m": 10.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
        ],
        "special_features": ["Saeulenfassade", "Oberlicht-Saele", "Skulpturenhof"],
    },

    # Kornhaus Bern (Kornhausplatz 18)
    "kornhaus_bern": {
        "egid": None,
        "building_name": "Kornhaus",
        "building_type": "Kulturzentrum / Restaurant",
        "architectural_style": "Barock",
        "construction_year": 1718,
        "complexity": "complex",
        "roof_type": "mansarddach",
        "zones": [
            {
                "name": "Arkaden",
                "zone_type": "arkade",
                "traufhoehe_m": 5.0,
                "firsthoehe_m": 5.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Hauptbau",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 18.0,
                "firsthoehe_m": 25.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Dachreiter",
                "zone_type": "turm",
                "traufhoehe_m": 25.0,
                "firsthoehe_m": 32.0,
                "beruesten": True,
                "sonderkonstruktion": True,
            },
        ],
        "special_features": ["Barocke Fassade", "Arkaden", "Kellergewoelbe"],
    },

    # Hauptbahnhof Bern (Bahnhofplatz 10)
    "hauptbahnhof_bern": {
        "egid": None,
        "building_name": "Hauptbahnhof Bern",
        "building_type": "Bahnhof",
        "architectural_style": "Moderne / Brutalismus",
        "construction_year": 1974,
        "complexity": "complex",
        "roof_type": "flachdach",
        "zones": [
            {
                "name": "Baldachin",
                "zone_type": "arkade",
                "traufhoehe_m": 8.0,
                "firsthoehe_m": 12.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Bahnhofshalle",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 18.0,
                "firsthoehe_m": 22.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Bueroturm",
                "zone_type": "turm",
                "traufhoehe_m": 30.0,
                "firsthoehe_m": 40.0,
                "beruesten": True,
                "sonderkonstruktion": True,
            },
        ],
        "special_features": ["Glasfassade", "Unterfuehrung", "Baldachin"],
    },

    # Stadttheater Bern (Theaterplatz 7)
    "stadttheater_bern": {
        "egid": None,
        "building_name": "Konzert Theater Bern",
        "building_type": "Theater / Oper",
        "architectural_style": "Neobarock",
        "construction_year": 1903,
        "complexity": "complex",
        "roof_type": "walmdach",  # Fix P2: Theater hat Walmdach, nicht Kuppel
        "zones": [
            {
                "name": "Foyer",
                "zone_type": "anbau",
                "traufhoehe_m": 10.0,
                "firsthoehe_m": 12.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Zuschauerhaus",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 18.0,
                "firsthoehe_m": 22.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Buehnenturm",
                "zone_type": "turm",
                "traufhoehe_m": 22.0,
                "firsthoehe_m": 32.0,
                "beruesten": True,
                "sonderkonstruktion": True,
            },
        ],
        "tower_config": {
            "count": 1,
            "position": "zentral (Buehne)",
            "form": "Buehnenturm",
            "height_m": 32.0,
        },
        "special_features": ["Buehnenturm", "Barocke Fassade", "Kuppel"],
    },

    # Bernisches Historisches Museum (Helvetiaplatz 5)
    "historisches_museum_bern": {
        "egid": None,
        "building_name": "Bernisches Historisches Museum",
        "building_type": "Museum",
        "architectural_style": "Historismus (Schloss)",
        "construction_year": 1894,
        "complexity": "complex",
        "roof_type": "satteldach_mit_turm",
        "zones": [
            {
                "name": "Hauptbau",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 25.0,
                "firsthoehe_m": 35.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Seitenfluegel",
                "zone_type": "anbau",
                "traufhoehe_m": 18.0,
                "firsthoehe_m": 25.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Eckturm",
                "zone_type": "turm",
                "traufhoehe_m": 35.0,
                "firsthoehe_m": 50.0,
                "beruesten": True,
                "sonderkonstruktion": True,
            },
        ],
        "tower_config": {
            "count": 4,
            "position": "Ecken",
            "form": "Spitzdach",
            "height_m": 50.0,
        },
        "special_features": ["Schlossarchitektur", "Ecktuerme", "Einstein-Museum"],
    },

    # Hotel Schweizerhof Bern (Marktgasse 67 / Bahnhofplatz 11)
    "hotel_schweizerhof_bern": {
        "egid": None,
        "building_name": "Hotel Schweizerhof Bern",
        "building_type": "Hotel",
        "architectural_style": "Historismus",
        "construction_year": 1859,
        "complexity": "moderate",
        "roof_type": "mansarddach",
        "zones": [
            {
                "name": "Hauptgebaeude",
                "zone_type": "hauptgebaeude",
                "traufhoehe_m": 18.0,
                "firsthoehe_m": 25.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
            {
                "name": "Dachaufbau",
                "zone_type": "anbau",
                "traufhoehe_m": 25.0,
                "firsthoehe_m": 30.0,
                "beruesten": True,
                "sonderkonstruktion": False,
            },
        ],
        "special_features": ["Historische Fassade", "Mansarddach", "Grandhotel"],
    },

    # ========================================
    # WEITERE STAEDTE
    # ========================================

    # Grossmuenster Zuerich (Beispiel)
    # "..." : { ... }
}

# Alias-Mapping: Adresse → EGID
ADDRESS_TO_EGID: Dict[str, str] = {
    # Bundeshaus
    "bundesplatz 3, 3011 bern": "2242547",
    "bundesplatz 3, bern": "2242547",
    # St. Peter und Paul
    "rathausgasse 2, 3011 bern": "191821074",
    "rathausgasse 2, bern": "191821074",
    # Berner Muenster
    "münsterplatz 1, 3011 bern": "1230337",
    "münsterplatz 1, bern": "1230337",
    "muensterplatz 1, 3011 bern": "1230337",
    "muensterplatz 1, bern": "1230337",
    # Einsteinhaus
    "kramgasse 49, 3011 bern": "1234567",
    "kramgasse 49, bern": "1234567",
    # Zytglogge
    "kramgasse 52, 3011 bern": "1017961",
    "kramgasse 52, bern": "1017961",
    # ========================================
    # Neue Gebaeude (BUG-002 Fix 30.12.2025)
    # ========================================
    # Kunstmuseum Bern
    "hodlerstrasse 8, 3011 bern": "kunstmuseum_bern",
    "hodlerstrasse 8, bern": "kunstmuseum_bern",
    # Kornhaus
    "kornhausplatz 18, 3011 bern": "kornhaus_bern",
    "kornhausplatz 18, bern": "kornhaus_bern",
    # Hauptbahnhof Bern
    "bahnhofplatz 10, 3011 bern": "hauptbahnhof_bern",
    "bahnhofplatz 10, bern": "hauptbahnhof_bern",
    # Stadttheater / Konzert Theater Bern
    "theaterplatz 7, 3011 bern": "stadttheater_bern",
    "theaterplatz 7, bern": "stadttheater_bern",
    # Bernisches Historisches Museum
    "helvetiaplatz 5, 3005 bern": "historisches_museum_bern",
    "helvetiaplatz 5, bern": "historisches_museum_bern",
    # Hotel Schweizerhof
    "bahnhofplatz 11, 3011 bern": "hotel_schweizerhof_bern",
    "bahnhofplatz 11, bern": "hotel_schweizerhof_bern",
}


def _normalize_address(address: str) -> str:
    """Normalisiert eine Adresse fuer Vergleiche.

    Entfernt Satzzeichen und doppelte Leerzeichen.
    """
    import re
    # Lowercase und strip
    addr = address.lower().strip()
    # Kommas, Punkte etc. entfernen
    addr = re.sub(r'[,.\-;:]', ' ', addr)
    # Doppelte Leerzeichen entfernen
    addr = re.sub(r'\s+', ' ', addr)
    return addr.strip()


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

    # 2. Adress-Suche (mit verbessertem Matching)
    if address:
        normalized = _normalize_address(address)

        # Exakte Übereinstimmung (nach Normalisierung)
        for addr_pattern, building_id in ADDRESS_TO_EGID.items():
            pattern_normalized = _normalize_address(addr_pattern)
            if normalized == pattern_normalized:
                return KNOWN_BUILDINGS.get(building_id)

        # Teilübereinstimmung (nach Normalisierung)
        for addr_pattern, building_id in ADDRESS_TO_EGID.items():
            pattern_normalized = _normalize_address(addr_pattern)
            if pattern_normalized in normalized or normalized in pattern_normalized:
                return KNOWN_BUILDINGS.get(building_id)

    return None


def get_all_known_egids() -> List[str]:
    """Gibt alle bekannten EGIDs zurück"""
    return list(KNOWN_BUILDINGS.keys())


def is_known_building(egid: Optional[str] = None, address: Optional[str] = None) -> bool:
    """Prüft ob ein Gebäude bekannt ist"""
    return get_known_building(egid=egid, address=address) is not None
