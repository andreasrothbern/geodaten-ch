"""
Building Hints Service
======================

Erkennt bekannte Gebäude und liefert spezifische Hinweise für die Claude-Analyse.
Diese Hints helfen Claude, die korrekten Zonen für komplexe Gebäude zu erkennen.

Verwendung:
    from app.services.building_hints import get_building_hints, is_known_building

    hints = get_building_hints(address, egid)
    if hints:
        gwr_data["building_name"] = hints["name"]
        gwr_data["building_hints"] = hints["hints"]

Stand: 28.12.2025
"""

from typing import Optional
import re


# Bekannte Gebäude mit spezifischen Zonen-Informationen
KNOWN_BUILDINGS = {
    # Bundeshaus Bern
    "bundeshaus": {
        "patterns": [
            r"Bundesplatz\s*3",
            r"egid.*2242547",
        ],
        "egids": [2242547],
        "name": "Bundeshaus (Schweizer Parlamentsgebäude)",
        "hints": """
BEKANNTES GEBÄUDE: Bundeshaus Bern (Schweizer Parlament)

Dieses Gebäude hat MEHRERE HÖHENZONEN:
1. **Arkaden/Laubengang** (Erdgeschoss): ca. 5-6m Höhe, Typ=arkade
2. **Hauptfassade** (Parlamentsgebäude): ca. 20-25m Höhe, Typ=hauptgebaeude
3. **Kuppel** (zentral): bis 64m Höhe, Typ=kuppel, sonderkonstruktion=true

Die gemessene Firsthöhe (62.6m) ist die KUPPELHÖHE, NICHT die Dachhöhe des Hauptgebäudes!

Du MUSST mindestens 3 Zonen erstellen:
- Zone 'Arkaden': traufhoehe_m=5, gebaeudehoehe_m=6, beruesten=true
- Zone 'Hauptgebäude': traufhoehe_m=20, firsthoehe_m=25, beruesten=true
- Zone 'Kuppel': gebaeudehoehe_m=64, sonderkonstruktion=true, beruesten=false (Spezialgerüst nötig)
""",
        "requires_orthofoto": True,
    },

    # Berner Münster
    "berner_muenster": {
        "patterns": [
            r"Münsterplatz\s*1",
            r"Muensterplatz\s*1",
        ],
        "egids": [1230337],
        "name": "Berner Münster (Gotische Kathedrale)",
        "hints": """
BEKANNTES GEBÄUDE: Berner Münster (Gotische Kathedrale, UNESCO Welterbe)

Dieses Gebäude hat MEHRERE HÖHENZONEN:
1. **Kirchenschiff** (Langhaus): ca. 25-28m Traufhöhe, gotisches Gewölbe, Typ=hauptgebaeude
2. **Chor** (Ostseite): ca. 25m Höhe, Typ=hauptgebaeude
3. **Turm** (Westseite): ca. 100m Höhe (höchster Kirchturm der Schweiz!), Typ=turm, sonderkonstruktion=true
4. **Seitenkapellen**: ca. 15m Höhe, Typ=anbau

Die gemessene Höhe spiegelt den TURM wider, NICHT das Kirchenschiff!

Du MUSST mindestens 3 Zonen erstellen:
- Zone 'Kirchenschiff': traufhoehe_m=20, firsthoehe_m=28, beruesten=true
- Zone 'Seitenkapellen': traufhoehe_m=12, firsthoehe_m=15, beruesten=true
- Zone 'Turm': gebaeudehoehe_m=100, sonderkonstruktion=true, beruesten=false (Spezialgerüst/Industriekletterer nötig)
""",
        "requires_orthofoto": True,
    },

    # St. Peter und Paul Kirche (Christkatholische Kathedrale)
    "st_peter_paul": {
        "patterns": [
            r"Rathausgasse\s*2",
        ],
        "egids": [191821074],
        "name": "St. Peter und Paul Bern (Christkatholische Kathedralkirche)",
        "hints": """
BEKANNTES GEBÄUDE: St. Peter und Paul Bern (Christkatholische Kathedralkirche)

Diese Kirche (erbaut 1858-1864) ist eine dreischiffige neogotische Basilika.
Architekten: Pierre Joseph Edouard Deperthes und Henri Maréchal (Reims/Frankreich).
Baustil: Dogmatische Neugotik (romanisch-frühgotische Formensprache).

**WICHTIG: EIN zentraler Westturm mit Spitzhelm (KEINE Doppeltürme!)**

Die Kirche hat folgende Zonen:
1. **Kirchenschiff**: Dreischiffige Basilika, ca. 18-22m Traufhöhe, Typ=hauptgebaeude
2. **Westturm**: EIN zentraler Turm, ca. 60m Höhe mit Spitzhelm, Typ=turm
3. **Chor/Apsis** (Ostseite): ca. 15m Höhe, Typ=anbau

Besonderheiten:
- 26 stützende monolithische Säulen im Innern
- Grösste Krypta der Schweiz unter der Kirche

Du MUSST mindestens 3 Zonen erstellen:
- Zone 'Kirchenschiff': traufhoehe_m=18, firsthoehe_m=22, beruesten=true
- Zone 'Westturm': gebaeudehoehe_m=60, sonderkonstruktion=true, beruesten=false (Spezialgerüst nötig)
- Zone 'Chor': traufhoehe_m=12, firsthoehe_m=15, beruesten=true
""",
        "requires_orthofoto": True,
    },

    # Bundeshaus West
    "bundeshaus_west": {
        "patterns": [
            r"Bundesgasse\s*3",
        ],
        "egids": [],
        "name": "Bundeshaus West (Verwaltungsgebäude)",
        "hints": """
BEKANNTES GEBÄUDE: Bundeshaus West

Verwaltungsgebäude mit einheitlicher Traufhöhe.
Mehrgeschossig mit repräsentativer Fassade.

Erstelle 1-2 Zonen basierend auf der Geometrie.
""",
        "requires_orthofoto": False,
    },

    # Historische Gebäude Berner Altstadt
    "kramgasse_haus": {
        "patterns": [
            r"Kramgasse\s*\d+",
            r"Gerechtigkeitsgasse\s*\d+",
            r"Marktgasse\s*\d+",
        ],
        "egids": [],
        "name": "Altstadthaus Bern (Laubenhaus)",
        "hints": """
TYPISCHES GEBÄUDE: Berner Altstadthaus (Laubenhaus)

Diese Gebäude haben oft:
1. **Lauben/Arkaden** (Erdgeschoss): ca. 3-4m Höhe, überdachter Gehweg
2. **Wohngeschosse**: 3-5 Geschosse à 3m
3. **Dachgeschoss**: Satteldach mit Gauben

Wenn das Polygon einfach ist (rechteckig), erstelle 1 Zone.
Bei L-Form oder Innenhof: mehrere Zonen.
""",
        "requires_orthofoto": False,  # Nur bei komplexer Geometrie
    },

    # Kirchen allgemein (als Fallback)
    "kirche_allgemein": {
        "patterns": [
            r"Kirche",
            r"Kathedrale",
            r"Münster",
            r"Kapelle",
        ],
        "egids": [],
        "category_codes": [1110],  # GWR-Kategorie: Religiöse Gebäude
        "name": "Kirchengebäude",
        "hints": """
GEBÄUDETYP: Kirchengebäude

Typische Zonen bei Kirchen:
1. **Kirchenschiff**: Hauptbaukörper
2. **Turm**: Oft deutlich höher als Schiff (Sonderkonstruktion!)
3. **Chor/Apsis**: Ostseite
4. **Sakristei**: Seitlicher Anbau

Achte auf die Höhendifferenz - der Turm ist meist separat zu erfassen.
""",
        "requires_orthofoto": True,
    },

    # Öffentliche Gebäude (Schulen, Verwaltung)
    "oeffentlich_allgemein": {
        "patterns": [],
        "egids": [],
        "category_codes": [1060, 1080, 1130],  # Bildung, Gesundheit, Museum
        "name": "Öffentliches Gebäude",
        "hints": """
GEBÄUDETYP: Öffentliches Gebäude (Schule, Spital, Museum)

Diese Gebäude haben oft:
1. **Haupttrakt**: Zentraler Baukörper
2. **Seitenflügel**: L- oder U-Form
3. **Eingangsbereich**: Oft mit Vordach oder Portal

Prüfe die Polygon-Form auf Anbauten und Flügel.
""",
        "requires_orthofoto": True,
    },
}


def get_building_hints(
    address: Optional[str] = None,
    egid: Optional[int] = None,
    building_category_code: Optional[int] = None
) -> Optional[dict]:
    """
    Sucht Building-Hints für ein bekanntes Gebäude.

    Args:
        address: Adresse des Gebäudes
        egid: EGID des Gebäudes
        building_category_code: GWR-Kategorie (gkat)

    Returns:
        Dict mit 'name', 'hints', 'requires_orthofoto' oder None
    """
    address_lower = (address or "").lower()

    for key, building in KNOWN_BUILDINGS.items():
        # 1. EGID-Match (höchste Priorität)
        if egid and egid in building.get("egids", []):
            return {
                "name": building["name"],
                "hints": building["hints"],
                "requires_orthofoto": building.get("requires_orthofoto", False),
                "match_type": "egid",
            }

        # 2. Pattern-Match auf Adresse
        for pattern in building.get("patterns", []):
            if re.search(pattern, address or "", re.IGNORECASE):
                return {
                    "name": building["name"],
                    "hints": building["hints"],
                    "requires_orthofoto": building.get("requires_orthofoto", False),
                    "match_type": "address_pattern",
                }

        # 3. Kategorie-Match (niedrigste Priorität, nur für generische Hints)
        if building_category_code and building_category_code in building.get("category_codes", []):
            return {
                "name": building["name"],
                "hints": building["hints"],
                "requires_orthofoto": building.get("requires_orthofoto", False),
                "match_type": "category",
            }

    return None


def is_known_building(
    address: Optional[str] = None,
    egid: Optional[int] = None
) -> bool:
    """
    Prüft ob ein Gebäude bekannt ist (hat spezifische Hints).

    Returns:
        True wenn bekannt, False sonst
    """
    hints = get_building_hints(address, egid)
    return hints is not None and hints.get("match_type") in ["egid", "address_pattern"]


def should_use_orthofoto(
    address: Optional[str] = None,
    egid: Optional[int] = None,
    is_complex: bool = False,
    building_category_code: Optional[int] = None
) -> bool:
    """
    Bestimmt ob die Orthofoto-Analyse verwendet werden soll.

    Orthofoto wird empfohlen bei:
    - Bekannten Gebäuden die es erfordern
    - Komplexen Gebäuden mit bestimmten Kategorien
    - Kirchen, öffentlichen Gebäuden

    Args:
        address: Adresse
        egid: EGID
        is_complex: Ist das Gebäude als komplex erkannt?
        building_category_code: GWR-Kategorie

    Returns:
        True wenn Orthofoto empfohlen
    """
    # 1. Bekanntes Gebäude?
    hints = get_building_hints(address, egid, building_category_code)
    if hints and hints.get("requires_orthofoto"):
        return True

    # 2. Komplexes Gebäude mit spezieller Kategorie?
    ORTHOFOTO_CATEGORIES = {1060, 1080, 1110, 1130}  # Bildung, Gesundheit, Kirchen, Museen
    if is_complex and building_category_code in ORTHOFOTO_CATEGORIES:
        return True

    return False
