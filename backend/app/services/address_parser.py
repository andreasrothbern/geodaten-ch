"""
Adress-Range Parser
====================

Parst Adress-Bereiche wie:
- "Knospenweg 2-10, Bern" → [2, 4, 6, 8, 10]
- "Kramgasse 27/29, Bern" → [27, 29]
- "Hauptstrasse 46-50, Zürich" → [46, 48, 50]

Unterstützte Formate:
- Range mit Bindestrich: "2-10" (erkennt gerade/ungerade automatisch)
- Explizite Liste: "27/29" oder "27, 29"
- Einzelne Nummer: "15"
"""

import re
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum

# NEU 13.01.2026 17:00: DuckDB-kompatible Connection
from app.config import get_building_3d_connection, BUILDING_3D_DB_PATH

logger = logging.getLogger(__name__)


def _point_in_polygon(px: float, py: float, polygon: List) -> bool:
    """
    Prüft ob ein Punkt innerhalb eines Polygons liegt (Ray-Casting Algorithmus).

    Funktioniert ohne externe Dependencies (kein shapely nötig).

    Args:
        px, py: Punkt-Koordinaten
        polygon: Liste von [x, y] Koordinaten

    Returns:
        True wenn Punkt im Polygon liegt
    """
    n = len(polygon)
    if n < 3:
        return False

    inside = False
    j = n - 1

    for i in range(n):
        # Koordinaten extrahieren (unterstützt [x,y] und {"x":..., "y":...})
        if isinstance(polygon[i], dict):
            xi, yi = polygon[i].get('x', polygon[i].get(0, 0)), polygon[i].get('y', polygon[i].get(1, 0))
            xj, yj = polygon[j].get('x', polygon[j].get(0, 0)), polygon[j].get('y', polygon[j].get(1, 0))
        else:
            xi, yi = polygon[i][0], polygon[i][1]
            xj, yj = polygon[j][0], polygon[j][1]

        # Ray-Casting: Zähle Kreuzungen
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside

        j = i

    return inside


def _lookup_egid_by_coordinates(e: float, n: float, tolerance_m: float = 10.0) -> Optional[int]:
    """
    Sucht die swissBUILDINGS3D EGID per Koordinaten-Lookup in building_3d.duckdb.

    BUG-015 FIX 11.01.2026: Verwendet jetzt Point-in-Polygon Check statt nur
    nächstes Zentrum. Bei Reihenhäusern liegt der Hauseingang (Geocoding-Koordinate)
    oft näher am Nachbar-Zentrum als am eigenen Gebäude-Zentrum.

    NEU 13.01.2026 17:00: Nutzt jetzt get_building_3d_connection() (DuckDB/SQLite).

    WICHTIG: Diese Funktion setzt voraus, dass das Tile bereits geladen ist!
    Siehe _ensure_tile_loaded() für den Tile-Preload.

    Strategie:
    1. Alle Kandidaten im Suchradius laden (mit Polygon)
    2. Point-in-Polygon Check: Liegt die Koordinate im Gebäudepolygon?
    3. Falls Match: Diese EGID zurückgeben (korrekt!)
    4. Falls kein Match: Fallback auf nächstes Zentrum (mit Warnung)

    Args:
        e: LV95 Ost-Koordinate (Geocoding = Hauseingang)
        n: LV95 Nord-Koordinate
        tolerance_m: Suchradius in Metern (default: 10m)

    Returns:
        EGID als int oder None wenn nicht gefunden
    """
    if not BUILDING_3D_DB_PATH.exists():
        logger.debug(f'building_3d DB nicht gefunden: {BUILDING_3D_DB_PATH}')
        return None

    try:
        conn = get_building_3d_connection()
        cursor = conn.cursor()

        # FIX BUG-015: Alle Kandidaten im Radius laden (nicht nur nächstes)
        cursor.execute('''
            SELECT egid, ST_AsGeoJSON(geom) as polygon, center_e, center_n,
                   (center_e - ?) * (center_e - ?) + (center_n - ?) * (center_n - ?) as dist_sq
            FROM buildings_3d
            WHERE center_e BETWEEN ? AND ?
              AND center_n BETWEEN ? AND ?
            ORDER BY dist_sq
        ''', (e, e, n, n, e - tolerance_m, e + tolerance_m, n - tolerance_m, n + tolerance_m))

        candidates = cursor.fetchall()
        conn.close()

        if not candidates:
            logger.debug(f'Keine Gebäude im Radius {tolerance_m}m um ({e:.1f}, {n:.1f})')
            return None

        # Schritt 1: Point-in-Polygon Check für alle Kandidaten
        for row in candidates:
            egid, polygon_json, center_e, center_n, dist_sq = row

            if not polygon_json:
                continue

            try:
                geojson = json.loads(polygon_json) if isinstance(polygon_json, str) else polygon_json
                # ST_AsGeoJSON liefert {"type": "Polygon", "coordinates": [[[x,y], ...]]}
                if isinstance(geojson, dict) and 'coordinates' in geojson:
                    polygon = geojson['coordinates'][0]
                else:
                    polygon = geojson  # Fallback für altes Format
            except (json.JSONDecodeError, TypeError, KeyError, IndexError):
                continue

            # Prüfe ob Punkt im Polygon liegt
            if _point_in_polygon(e, n, polygon):
                dist = dist_sq ** 0.5
                logger.info(f'[BUG-015 FIX] Point-in-Polygon Match: ({e:.1f}, {n:.1f}) → EGID {egid} (center_dist={dist:.1f}m)')
                return egid

        # Schritt 2: Kein Polygon-Match gefunden
        # FIX 12.01.2026 BUG-018: KEIN Fallback auf nächstes Zentrum!
        # Bei Multi-Adress-Lookup führt Fallback zu falschen EGIDs.
        # Stattdessen None zurückgeben → fetch_building_polygon_for_coordinates wird aufgerufen.
        first = candidates[0]
        dist = first[4] ** 0.5

        logger.warning(
            f'[BUG-018] Kein Polygon-Match für ({e:.1f}, {n:.1f}). '
            f'Kein Fallback - fetch_building_polygon_for_coordinates wird aufgerufen. '
            f'Nächstes Zentrum wäre EGID {first[0]} (dist={dist:.1f}m). '
            f'Geprüft: {len(candidates)} Kandidaten.'
        )
        return None

    except Exception as ex:
        logger.error(f'building_3d.db Lookup-Fehler: {ex}')
        return None




class AddressRangeType(str, Enum):
    """Typ des Adress-Bereichs."""
    SINGLE = "single"           # Einzelne Hausnummer
    RANGE = "range"             # Bereich (2-10)
    EXPLICIT = "explicit"       # Explizite Liste (27/29)


@dataclass
class ParsedAddressRange:
    """Ergebnis des Adress-Parsings."""
    street: str
    city: str
    postal_code: Optional[str] = None

    # Hausnummern
    numbers: List[str] = field(default_factory=list)
    range_type: AddressRangeType = AddressRangeType.SINGLE

    # Original-Input
    original_input: str = ""
    raw_number_part: str = ""

    def get_full_addresses(self) -> List[str]:
        """Generiert vollständige Adressen für jede Hausnummer."""
        addresses = []
        for nr in self.numbers:
            if self.postal_code:
                addresses.append(f"{self.street} {nr}, {self.postal_code} {self.city}")
            else:
                addresses.append(f"{self.street} {nr}, {self.city}")
        return addresses


def parse_address_range(address: str) -> ParsedAddressRange:
    """
    Parst eine Adresse mit möglichem Hausnummern-Bereich.

    Args:
        address: Vollständige Adresse wie "Knospenweg 2-10, 3006 Bern"

    Returns:
        ParsedAddressRange mit allen erkannten Hausnummern

    Examples:
        >>> parse_address_range("Knospenweg 2-10, Bern")
        ParsedAddressRange(street="Knospenweg", numbers=["2","4","6","8","10"], ...)

        >>> parse_address_range("Kramgasse 27/29, 3011 Bern")
        ParsedAddressRange(street="Kramgasse", numbers=["27","29"], ...)
    """
    result = ParsedAddressRange(
        street="",
        city="",
        original_input=address
    )

    # Normalisieren
    address = address.strip()

    # Strasse und Ort trennen (am Komma)
    parts = [p.strip() for p in address.split(",")]

    if len(parts) < 2:
        # Kein Komma - versuche anders zu parsen
        logger.warning(f"Adresse ohne Komma: {address}")
        result.street = address
        result.city = ""
        return result

    street_part = parts[0]
    city_part = parts[1] if len(parts) > 1 else ""

    # PLZ und Ort trennen
    plz_match = re.match(r'^(\d{4})\s+(.+)$', city_part)
    if plz_match:
        result.postal_code = plz_match.group(1)
        result.city = plz_match.group(2)
    else:
        result.city = city_part

    # Strasse und Hausnummer trennen
    street_number_match = re.match(
        r'^(.+?)\s+(\d+(?:\s*[-/,]\s*\d+)*)$',
        street_part
    )

    if street_number_match:
        result.street = street_number_match.group(1)
        number_part = street_number_match.group(2)
        result.raw_number_part = number_part

        # Hausnummern parsen
        result.numbers, result.range_type = _parse_number_range(number_part)
    else:
        # Keine Hausnummer erkannt
        result.street = street_part
        result.numbers = []
        result.range_type = AddressRangeType.SINGLE

    return result


def _parse_number_range(number_str: str) -> Tuple[List[str], AddressRangeType]:
    """
    Parst einen Hausnummern-String.

    Args:
        number_str: "2-10", "27/29", "15", etc.

    Returns:
        Tuple von (Liste der Nummern, Typ)
    """
    number_str = number_str.strip()

    # Fall 1: Bereich mit Bindestrich (2-10)
    range_match = re.match(r'^(\d+)\s*-\s*(\d+)$', number_str)
    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2))

        if start > end:
            start, end = end, start

        # Schritt ermitteln (gerade/ungerade oder alle)
        step = _determine_step(start, end)

        numbers = [str(n) for n in range(start, end + 1, step)]
        return numbers, AddressRangeType.RANGE

    # Fall 2: Explizite Liste mit Slash (27/29)
    slash_match = re.match(r'^(\d+)\s*/\s*(\d+)$', number_str)
    if slash_match:
        numbers = [slash_match.group(1), slash_match.group(2)]
        return numbers, AddressRangeType.EXPLICIT

    # Fall 3: Explizite Liste mit Komma (27, 29, 31)
    if ',' in number_str:
        numbers = [n.strip() for n in number_str.split(',') if n.strip().isdigit()]
        return numbers, AddressRangeType.EXPLICIT

    # Fall 4: Einzelne Nummer
    if number_str.isdigit():
        return [number_str], AddressRangeType.SINGLE

    # Fall 5: Nummer mit Suffix (15a, 15b)
    suffix_match = re.match(r'^(\d+)([a-zA-Z]?)$', number_str)
    if suffix_match:
        return [number_str], AddressRangeType.SINGLE

    logger.warning(f"Konnte Hausnummer nicht parsen: {number_str}")
    return [number_str], AddressRangeType.SINGLE


def _determine_step(start: int, end: int) -> int:
    """
    Bestimmt den Schritt für einen Nummernbereich.

    In der Schweiz: Gerade Nummern auf einer Strassenseite,
    ungerade auf der anderen. Bei "2-10" sind das die geraden.
    Bei "1-9" die ungeraden.

    Args:
        start: Startnummer
        end: Endnummer

    Returns:
        Schritt (1 oder 2)
    """
    # Wenn Start und End gleiche Parität haben → Schritt 2
    if start % 2 == end % 2:
        return 2

    # Unterschiedliche Parität → alle Nummern
    # (z.B. "1-4" = 1, 2, 3, 4)
    return 1


# Singleton instance
_address_parser_service = None


class AddressParserService:
    """Service für Adress-Parsing mit Geocoding-Integration."""

    def __init__(self):
        self._swisstopo = None

    def _get_swisstopo(self):
        """Lazy-load SwisstopoService."""
        if self._swisstopo is None:
            from app.services.swisstopo import SwisstopoService
            self._swisstopo = SwisstopoService()
        return self._swisstopo

    def _normalize_street(self, street: str) -> str:
        """Normalisiert Strassennamen für Vergleich."""
        street = street.lower().strip()
        # Gängige Abkürzungen vereinheitlichen
        street = re.sub(r'\bstr\.?\b', 'strasse', street)
        street = re.sub(r'\bstr$', 'strasse', street)
        # Umlaute normalisieren
        street = street.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue')
        street = street.replace('ss', 'ss')  # ß → ss bereits in Daten
        return street

    def _normalize_city(self, city: str) -> str:
        """Normalisiert Ortsnamen für Vergleich."""
        city = city.lower().strip()
        # PLZ entfernen falls vorhanden
        city = re.sub(r'^\d{4}\s+', '', city)
        return city

    def _validate_geocode_match(self, parsed: ParsedAddressRange, matched_address: str) -> bool:
        """
        Validiert ob die gematche Adresse zur angeforderten passt.

        Args:
            parsed: Die geparste Original-Adresse
            matched_address: Die von swisstopo zurückgegebene Adresse

        Returns:
            True wenn Match gültig (gleiche Strasse und Stadt)
        """
        if not matched_address:
            return False

        # Matched address parsen (Format: "Strassenname Nr PLZ Ort")
        # Beispiel: "Knospenweg 9 3027 Bern"
        match = re.match(r'^(.+?)\s+\d+[a-zA-Z]?\s+\d{4}\s+(.+)$', matched_address)
        if not match:
            # Alternatives Format ohne PLZ
            match = re.match(r'^(.+?)\s+\d+[a-zA-Z]?\s+(.+)$', matched_address)

        if not match:
            logger.warning(f"Konnte matched_address nicht parsen: {matched_address}")
            return False

        matched_street = match.group(1)
        matched_city = match.group(2)

        # Normalisieren und vergleichen
        requested_street = self._normalize_street(parsed.street)
        matched_street_norm = self._normalize_street(matched_street)

        requested_city = self._normalize_city(parsed.city)
        matched_city_norm = self._normalize_city(matched_city)

        # Strasse muss übereinstimmen
        if requested_street != matched_street_norm:
            logger.debug(f"Strasse stimmt nicht: '{requested_street}' != '{matched_street_norm}'")
            return False

        # Stadt muss übereinstimmen (oder Teil davon sein, z.B. "Bern" in "Bern-Bümpliz")
        if requested_city not in matched_city_norm and matched_city_norm not in requested_city:
            logger.debug(f"Stadt stimmt nicht: '{requested_city}' != '{matched_city_norm}'")
            return False

        return True

    def parse(self, address: str) -> ParsedAddressRange:
        """Parst eine Adresse (ohne Geocoding)."""
        return parse_address_range(address)

    async def resolve_to_egids(self, address: str) -> dict:
        """
        Parst Adresse und löst alle Hausnummern zu EGIDs auf.

        Args:
            address: Adresse mit Range wie "Knospenweg 2-10, Bern"

        Returns:
            Dict mit:
            - parsed: ParsedAddressRange Info
            - buildings: Liste von {address, egid, coordinates, ...}
            - errors: Fehlgeschlagene Lookups
        """
        parsed = parse_address_range(address)
        swisstopo = self._get_swisstopo()

        buildings = []
        errors = []

        for full_address in parsed.get_full_addresses():
            try:
                # 1. Geocode to get coordinates
                geo_result = await swisstopo.geocode(full_address)

                if not geo_result:
                    errors.append({
                        "address": full_address,
                        "error": "Adresse nicht gefunden"
                    })
                    continue

                # 2. Validate matched address - must match requested street and city
                if not self._validate_geocode_match(parsed, geo_result.matched_address):
                    logger.warning(
                        f"Geocoding-Match ungültig: '{full_address}' → '{geo_result.matched_address}'"
                    )
                    errors.append({
                        "address": full_address,
                        "error": f"Adresse existiert nicht (Match: {geo_result.matched_address})"
                    })
                    continue

                # 3. Get EGID - prefer swissBUILDINGS3D over GWR
                e = geo_result.coordinates.lv95_e
                n = geo_result.coordinates.lv95_n

                # BUG-015 FIX 11.01.2026: Point-in-Polygon Check bei Reihenhäusern
                # Schritt 1: Versuche Lookup in building_3d.db (schnell, ~1ms)
                swissbuildings_egid = _lookup_egid_by_coordinates(e, n, tolerance_m=10.0)

                # Schritt 2: Falls nicht gefunden → Point-in-Polygon direkt im Tile
                # FIX 31.01.2026: skip_prefetch entfernt - Fetcher hat keine Side-Effects mehr
                if swissbuildings_egid is None:
                    logger.info(f"[BUG-015] Keine Daten in building_3d.db für ({e:.1f}, {n:.1f}) - prüfe Tile...")
                    from app.services.swissbuildings3d_fetcher import fetch_building_polygon_for_coordinates
                    result = await fetch_building_polygon_for_coordinates(e, n)
                    if result and result.get('egid'):
                        swissbuildings_egid = int(result.get('egid'))

                logger.info(f"[DEBUG] Lookup for ({e:.1f}, {n:.1f}): swissbuildings_egid={swissbuildings_egid}")

                if swissbuildings_egid:
                    buildings.append({
                        "address": full_address,
                        "matched_address": geo_result.matched_address,
                        "egid": str(swissbuildings_egid),
                        "egid_source": "swissBUILDINGS3D",
                        "coordinates": {
                            "lv95_e": e,
                            "lv95_n": n,
                        },
                    })
                else:
                    # Fallback to GWR identify_buildings
                    building_list = await swisstopo.identify_buildings(e, n)
                    if building_list and building_list[0].egid:
                        building = building_list[0]
                        buildings.append({
                            "address": full_address,
                            "matched_address": geo_result.matched_address,
                            "egid": str(building.egid),
                            "egid_source": "GWR",
                            "coordinates": {
                                "lv95_e": e,
                                "lv95_n": n,
                            },
                        })
                    else:
                        errors.append({
                            "address": full_address,
                            "error": "Kein EGID gefunden (weder swissBUILDINGS3D noch GWR)"
                        })

            except Exception as e:
                logger.error(f"Geocoding-Fehler für {full_address}: {e}")
                errors.append({
                    "address": full_address,
                    "error": str(e)
                })

        return {
            "parsed": {
                "street": parsed.street,
                "city": parsed.city,
                "postal_code": parsed.postal_code,
                "numbers": parsed.numbers,
                "range_type": parsed.range_type.value,
                "original_input": parsed.original_input,
            },
            "buildings": buildings,
            "building_count": len(buildings),
            "errors": errors,
            "error_count": len(errors),
        }


def get_address_parser() -> AddressParserService:
    """Gibt Singleton-Instanz des AddressParserService zurück."""
    global _address_parser_service
    if _address_parser_service is None:
        _address_parser_service = AddressParserService()
    return _address_parser_service
