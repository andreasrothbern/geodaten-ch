"""
Smart Photo Analyzer
====================

Intelligente Foto-Analyse für Gerüstbau-Projekte.
Erkennt automatisch den Bildtyp und extrahiert relevante Daten:
- Gebäudefotos: GPS, Dachform, Geschosse, Hindernisse
- Dokumente: OCR für Ausschreibungen
- Skizzen: Arbeitstyp, Masse, Kontext

Stand: 01.02.2026
"""

import os
import base64
import logging
import json
import re
import math
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from io import BytesIO

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# HEIC/HEIF support for iPhone photos
try:
    from pillow_heif import register_heif_opener
    import pillow_heif
    register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False
    pillow_heif = None

# piexif for HEIC EXIF parsing (Pillow's _getexif() doesn't work with HEIC)
try:
    import piexif
    PIEXIF_AVAILABLE = True
except ImportError:
    PIEXIF_AVAILABLE = False
    piexif = None

logger = logging.getLogger(__name__)

# Model for analysis
ANALYSIS_MODEL = "claude-sonnet-4-20250514"


@dataclass
class GpsData:
    """GPS-Daten aus EXIF"""
    lat: float
    lon: float
    altitude_m: Optional[float] = None
    # LV95 Koordinaten (berechnet)
    lv95_e: Optional[float] = None
    lv95_n: Optional[float] = None
    # Kompass-Richtung (falls verfügbar)
    compass_direction: Optional[float] = None  # 0-360°
    compass_direction_text: Optional[str] = None  # "N", "NE", etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lat": self.lat,
            "lon": self.lon,
            "altitude_m": self.altitude_m,
            "lv95_e": self.lv95_e,
            "lv95_n": self.lv95_n,
            "compass_direction": self.compass_direction,
            "compass_direction_text": self.compass_direction_text,
        }


@dataclass
class BuildingAnalysis:
    """Analyse eines Gebäudefotos"""
    floors_count: Optional[int] = None
    height_estimate_m: Optional[float] = None
    roof_type: Optional[str] = None  # flachdach, satteldach, walmdach, pultdach
    roof_angle_deg: Optional[float] = None
    facade_material: Optional[str] = None  # putz, holz, beton, glas, ziegel
    facade_direction: Optional[str] = None  # N, NE, E, SE, S, SW, W, NW
    visible_address: Optional[str] = None  # Hausnummer/Adresse im Bild
    obstacles: list = field(default_factory=list)  # ["baum_west", "balkon_2og"]
    windows_pattern: Optional[str] = None  # regular, irregular, mixed
    building_condition: Optional[str] = None  # gut, mittel, renovierungsbedürftig
    neighboring_buildings: Optional[str] = None  # freistehend, reihenhaus, anbau
    special_features: list = field(default_factory=list)  # ["erker", "loggia", "markise"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "floors_count": self.floors_count,
            "height_estimate_m": self.height_estimate_m,
            "roof_type": self.roof_type,
            "roof_angle_deg": self.roof_angle_deg,
            "facade_material": self.facade_material,
            "facade_direction": self.facade_direction,
            "visible_address": self.visible_address,
            "obstacles": self.obstacles,
            "windows_pattern": self.windows_pattern,
            "building_condition": self.building_condition,
            "neighboring_buildings": self.neighboring_buildings,
            "special_features": self.special_features,
        }


@dataclass
class TerrainAnalysis:
    """Terrain- und Umgebungs-Analyse aus Foto (NEU 01.02.2026)"""
    # Terrain/Hanglage
    slope_estimate: Optional[str] = None  # eben, leicht, mittel, stark
    slope_direction: Optional[str] = None  # N, S, E, W, bergauf, bergab
    ground_type: Optional[str] = None  # asphalt, kies, rasen, erde, pflaster

    # Zufahrt
    access_type: Optional[str] = None  # strasse, weg, eingeschraenkt, nicht_sichtbar
    access_width: Optional[str] = None  # lkw_moeglich, lieferwagen, nur_fussgaenger

    # Umgebung
    neighboring_distance: Optional[str] = None  # angrenzend, 2-5m, >5m, freistehend
    trees_nearby: bool = False
    power_lines: bool = False
    street_furniture: list = field(default_factory=list)  # laterne, hydrant, parkplatz

    # Gerüst-Hindernisse
    balconies_count: int = 0
    awnings_count: int = 0
    bay_windows: bool = False  # Erker
    overhangs: list = field(default_factory=list)  # dachvorsprung, vordach
    other_obstacles: list = field(default_factory=list)  # sonnenstoren, klimaanlage

    # Notizen
    scaffold_notes: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slope_estimate": self.slope_estimate,
            "slope_direction": self.slope_direction,
            "ground_type": self.ground_type,
            "access_type": self.access_type,
            "access_width": self.access_width,
            "neighboring_distance": self.neighboring_distance,
            "trees_nearby": self.trees_nearby,
            "power_lines": self.power_lines,
            "street_furniture": self.street_furniture,
            "balconies_count": self.balconies_count,
            "awnings_count": self.awnings_count,
            "bay_windows": self.bay_windows,
            "overhangs": self.overhangs,
            "other_obstacles": self.other_obstacles,
            "scaffold_notes": self.scaffold_notes,
            "confidence": self.confidence,
        }


@dataclass
class SketchAnalysis:
    """Analyse einer Skizze/Zeichnung"""
    sketch_type: Optional[str] = None  # grundriss, ansicht, schnitt, detail, situationsplan
    work_type: Optional[str] = None  # fassade, spengler, dach, komplett
    dimensions_found: Dict[str, float] = field(default_factory=dict)  # {"breite_m": 12, "hoehe_m": 8}
    notes_text: Optional[str] = None  # Handschriftliche Notizen
    address_found: Optional[str] = None
    address_required: bool = False  # True wenn keine Adresse erkennbar
    scale: Optional[str] = None  # "1:100", "1:50"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sketch_type": self.sketch_type,
            "work_type": self.work_type,
            "dimensions_found": self.dimensions_found,
            "notes_text": self.notes_text,
            "address_found": self.address_found,
            "address_required": self.address_required,
            "scale": self.scale,
        }


@dataclass
class SmartExtractionResult:
    """Erweitertes Ergebnis der intelligenten Foto-Analyse"""
    success: bool = False
    confidence: float = 0.0
    error: Optional[str] = None

    # Klassifizierung
    image_type: str = "unknown"  # building_photo, document, sketch, technical_plan, mixed

    # GPS aus EXIF
    gps_data: Optional[GpsData] = None

    # Timestamp aus EXIF
    photo_timestamp: Optional[str] = None

    # Gebäudefoto-Analyse
    building_analysis: Optional[BuildingAnalysis] = None

    # Skizze/Zeichnung-Analyse
    sketch_analysis: Optional[SketchAnalysis] = None

    # Terrain-Analyse (NEU 01.02.2026)
    terrain_analysis: Optional[TerrainAnalysis] = None

    # Suggested Data aus GWR (via identify_buildings, NEU 01.02.2026)
    suggested_egid: Optional[str] = None
    suggested_address: Optional[str] = None
    suggested_street: Optional[str] = None
    suggested_house_number: Optional[str] = None
    suggested_postal_code: Optional[int] = None
    suggested_city: Optional[str] = None
    suggested_floors: Optional[int] = None
    suggested_construction_year: Optional[int] = None
    suggested_building_category: Optional[str] = None

    # Dokument-Extraktion (bestehend)
    address: Optional[str] = None
    project_name: Optional[str] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    description: Optional[str] = None
    tender_number: Optional[str] = None
    submission_deadline: Optional[str] = None
    project_start: Optional[str] = None
    project_end: Optional[str] = None
    estimated_area_m2: Optional[float] = None
    requirements: list = field(default_factory=list)

    # Pre-loaded Building Data (wird später befüllt)
    preloaded_egid: Optional[str] = None
    preloaded_building_name: Optional[str] = None
    preloaded_address: Optional[str] = None
    preloaded_traufhoehe_m: Optional[float] = None
    preloaded_firsthoehe_m: Optional[float] = None
    preloaded_roof_type: Optional[str] = None
    preloaded_polygon: Optional[list] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "confidence": self.confidence,
            "error": self.error,
            "image_type": self.image_type,
            "gps_data": self.gps_data.to_dict() if self.gps_data else None,
            "photo_timestamp": self.photo_timestamp,
            "building_analysis": self.building_analysis.to_dict() if self.building_analysis else None,
            "sketch_analysis": self.sketch_analysis.to_dict() if self.sketch_analysis else None,
            "terrain_analysis": self.terrain_analysis.to_dict() if self.terrain_analysis else None,
            # Suggested Data aus GWR (NEU 01.02.2026)
            "suggested_egid": self.suggested_egid,
            "suggested_address": self.suggested_address,
            "suggested_street": self.suggested_street,
            "suggested_house_number": self.suggested_house_number,
            "suggested_postal_code": self.suggested_postal_code,
            "suggested_city": self.suggested_city,
            "suggested_floors": self.suggested_floors,
            "suggested_construction_year": self.suggested_construction_year,
            "suggested_building_category": self.suggested_building_category,
            # Legacy preloaded fields (deprecated, use suggested_* instead)
            "preloaded_egid": self.preloaded_egid,
            "preloaded_building_name": self.preloaded_building_name,
            "preloaded_address": self.preloaded_address,
            "preloaded_traufhoehe_m": self.preloaded_traufhoehe_m,
            "preloaded_firsthoehe_m": self.preloaded_firsthoehe_m,
            "preloaded_roof_type": self.preloaded_roof_type,
            "preloaded_polygon": self.preloaded_polygon,
        }

        # Dokument-Daten (für Kompatibilität mit bestehendem Frontend)
        result["data"] = {
            "address": self.address,
            "project_name": self.project_name,
            "client_name": self.client_name,
            "client_contact": self.client_contact,
            "description": self.description,
            "tender_number": self.tender_number,
            "submission_deadline": self.submission_deadline,
            "project_start": self.project_start,
            "project_end": self.project_end,
            "estimated_area_m2": self.estimated_area_m2,
            "requirements": self.requirements,
        } if self.success else None

        return result


class PhotoAnalyzer:
    """Intelligenter Foto-Analyzer für Gerüstbau-Projekte"""

    # ============ PROMPTS ============

    CLASSIFICATION_PROMPT = """
Analysiere dieses Bild und klassifiziere es.

Antworte NUR mit einem JSON-Objekt (keine Erklärung):

```json
{
    "image_type": "building_photo|document|sketch|technical_plan|mixed",
    "confidence": 0.95,
    "description": "Kurze Beschreibung was du siehst"
}
```

Typen:
- building_photo: Foto eines echten Gebäudes (Aussenfoto)
- document: Ausschreibung, Formular, gedruckter Text
- sketch: Handskizze, einfache Zeichnung
- technical_plan: Technische Zeichnung, CAD-Plan, Bauplan
- mixed: Kombination (z.B. Foto mit Text-Overlay)
"""

    BUILDING_PHOTO_PROMPT = """
Du analysierst ein Foto eines Gebäudes für ein Gerüstbau-Projekt.

Extrahiere alle erkennbaren Informationen. Antworte NUR mit JSON:

```json
{
    "floors_count": 4,
    "height_estimate_m": 12.0,
    "roof_type": "flachdach|satteldach|walmdach|pultdach|mansarddach|unbekannt",
    "roof_angle_deg": 30,
    "facade_material": "putz|holz|beton|glas|ziegel|metall|gemischt",
    "facade_direction": "N|NE|E|SE|S|SW|W|NW|unbekannt",
    "visible_address": "Heimstrasse 31" oder null,
    "obstacles": ["baum_vor_fassade", "balkon_2og", "markise", "leitung"],
    "windows_pattern": "regular|irregular|mixed",
    "building_condition": "gut|mittel|renovierungsbedürftig",
    "neighboring_buildings": "freistehend|reihenhaus|doppelhaus|blockrand",
    "special_features": ["erker", "loggia", "vordach", "garage_angebaut"],
    "confidence": 0.85
}
```

Hinweise:
- floors_count: Zähle sichtbare Vollgeschosse (nicht Dachgeschoss)
- height_estimate_m: Schätze Traufhöhe (Dachansatz) in Metern
- roof_angle_deg: 0° = Flachdach, ~30° = typisches Satteldach, ~45° = steiles Dach
- obstacles: Alles was Gerüstaufbau erschweren könnte
- Wenn unsicher, setze null statt zu raten
"""

    SKETCH_PROMPT = """
Du analysierst eine Skizze oder Zeichnung für ein Gerüstbau-Projekt.

Extrahiere alle erkennbaren Informationen. Antworte NUR mit JSON:

```json
{
    "sketch_type": "grundriss|ansicht|schnitt|detail|situationsplan|unbekannt",
    "work_type": "fassade|spengler|dach|komplett|unbekannt",
    "dimensions_found": {
        "breite_m": 12.5,
        "hoehe_m": 8.0,
        "tiefe_m": 10.0
    },
    "notes_text": "Handschriftliche Notizen falls lesbar",
    "address_found": "Strasse Nr, PLZ Ort" oder null,
    "scale": "1:100" oder null,
    "confidence": 0.7
}
```

Hinweise:
- work_type: Was für Arbeiten sind geplant?
  - fassade: Fassadenarbeiten (Malen, Verputzen)
  - spengler: Dachrinnen, Blecharbeiten
  - dach: Dacharbeiten (Ziegel, Isolation)
  - komplett: Vollständige Einrüstung
- Wenn keine Adresse erkennbar, setze address_found auf null
"""

    DOCUMENT_PROMPT = """
Du bist ein Experte für die Analyse von Bauausschreibungen und Gerüstbau-Projekten.

Analysiere das Dokument und extrahiere alle relevanten Informationen.

WICHTIG:
- Extrahiere nur Informationen, die explizit im Dokument stehen
- Wenn eine Information nicht vorhanden ist, setze den Wert auf null
- Datumsangaben im Format YYYY-MM-DD

Antworte NUR mit JSON:

```json
{
    "project_name": "Name des Projekts",
    "address": "Strasse Nr, PLZ Ort",
    "client_name": "Name des Auftraggebers",
    "client_contact": "Telefon oder E-Mail",
    "description": "Kurze Beschreibung der Arbeiten",
    "tender_number": "Ausschreibungs-Nummer",
    "submission_deadline": "YYYY-MM-DD",
    "project_start": "YYYY-MM-DD",
    "project_end": "YYYY-MM-DD",
    "estimated_area_m2": 150.0,
    "requirements": ["Sicherheitsanforderungen", "Zeitliche Vorgaben"],
    "confidence": 0.85
}
```
"""

    # NEU 01.02.2026: Erweiterter Prompt für Terrain- und Umgebungs-Analyse
    TERRAIN_ANALYSIS_PROMPT = """
Analysiere das Foto für Gerüstbau-Planung. Fokussiere auf TERRAIN, UMGEBUNG und HINDERNISSE.

Antworte NUR mit JSON:

```json
{
    "terrain": {
        "slope_estimate": "eben|leicht|mittel|stark",
        "slope_direction": "N|S|E|W|bergauf|bergab|nicht_erkennbar",
        "ground_type": "asphalt|kies|rasen|erde|pflaster|gemischt|nicht_sichtbar"
    },
    "access": {
        "type": "strasse|weg|eingeschraenkt|nicht_sichtbar",
        "width": "lkw_moeglich|lieferwagen|nur_fussgaenger|nicht_erkennbar"
    },
    "environment": {
        "neighboring_distance": "angrenzend|2-5m|>5m|freistehend",
        "trees_nearby": false,
        "power_lines": false,
        "street_furniture": []
    },
    "obstacles": {
        "balconies": 0,
        "awnings": 0,
        "bay_windows": false,
        "overhangs": [],
        "other": []
    },
    "scaffold_notes": "Besondere Hinweise fuer Geruestplanung",
    "confidence": 0.8
}
```

Hinweise:
- slope_estimate: Gelaendeneigung
  - eben: Kein sichtbarer Hoehenunterschied
  - leicht: Leichte Neigung, Stellspindeln reichen
  - mittel: Deutliche Neigung, Ausgleichsrahmen noetig
  - stark: Steiler Hang, spezielle Fundamentierung
- access.width: Kann LKW fuer Geruestmaterial zufahren?
- obstacles: Alles was Geruestaufbau beeinflusst
- overhangs: z.B. ["dachvorsprung_50cm", "vordach_eingang"]
- street_furniture: z.B. ["laterne", "hydrant", "parkplatz", "zaun"]
- other: z.B. ["sonnenstoren", "klimaanlage_aussen", "satellitenschuessel"]
- scaffold_notes: Wichtige Hinweise fuer den Geruestbauer
"""

    def __init__(self):
        self._client = None

    def _get_client(self):
        """Lazy-load Anthropic client"""
        if self._client is None:
            try:
                from anthropic import Anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    logger.warning("ANTHROPIC_API_KEY nicht gesetzt")
                    return None
                self._client = Anthropic(api_key=api_key)
            except ImportError:
                logger.warning("anthropic package nicht installiert")
                return None
        return self._client

    # ============ EXIF EXTRACTION ============

    def _extract_exif_from_heic(self, file_bytes: bytes) -> Tuple[Optional[GpsData], Optional[str]]:
        """
        Extrahiert GPS und Timestamp aus HEIC-Dateien mit piexif.

        HEIC-Dateien benötigen spezielle Behandlung:
        - Pillow's _getexif() funktioniert NICHT mit HEIC
        - pillow_heif speichert EXIF als raw bytes in info['exif']
        - piexif kann diese bytes parsen
        """
        if not HEIF_AVAILABLE or not PIEXIF_AVAILABLE:
            logger.warning("HEIC EXIF-Extraktion nicht möglich (pillow_heif oder piexif fehlt)")
            return None, None

        try:
            heif_file = pillow_heif.open_heif(BytesIO(file_bytes))
            exif_bytes = heif_file.info.get('exif')

            if not exif_bytes:
                logger.debug("HEIC: Keine EXIF-Daten gefunden")
                return None, None

            exif_dict = piexif.load(exif_bytes)

            # Extract timestamp
            timestamp = None
            if 'Exif' in exif_dict:
                dt = exif_dict['Exif'].get(piexif.ExifIFD.DateTimeOriginal)
                if dt:
                    timestamp = dt.decode() if isinstance(dt, bytes) else dt
                    # Format: "2026:02:01 14:30:00" -> "2026-02-01T14:30:00"
                    timestamp = timestamp.replace(':', '-', 2).replace(' ', 'T')

            # Extract GPS
            if 'GPS' not in exif_dict or not exif_dict['GPS']:
                logger.debug("HEIC: Keine GPS-Daten in EXIF")
                return None, timestamp

            gps = exif_dict['GPS']

            # Parse coordinates
            lat_dms = gps.get(piexif.GPSIFD.GPSLatitude)
            lat_ref = gps.get(piexif.GPSIFD.GPSLatitudeRef)
            lon_dms = gps.get(piexif.GPSIFD.GPSLongitude)
            lon_ref = gps.get(piexif.GPSIFD.GPSLongitudeRef)

            if not lat_dms or not lon_dms:
                return None, timestamp

            # Convert DMS to decimal
            lat_ref_str = lat_ref.decode() if isinstance(lat_ref, bytes) else lat_ref
            lon_ref_str = lon_ref.decode() if isinstance(lon_ref, bytes) else lon_ref
            lat = self._dms_tuple_to_decimal(lat_dms, lat_ref_str)
            lon = self._dms_tuple_to_decimal(lon_dms, lon_ref_str)

            if lat is None or lon is None:
                return None, timestamp

            # Extract altitude
            altitude = None
            alt_val = gps.get(piexif.GPSIFD.GPSAltitude)
            if alt_val:
                altitude = alt_val[0] / alt_val[1] if isinstance(alt_val, tuple) else float(alt_val)

            # Extract compass direction
            compass = None
            compass_text = None
            dir_val = gps.get(piexif.GPSIFD.GPSImgDirection)
            if dir_val:
                compass = dir_val[0] / dir_val[1] if isinstance(dir_val, tuple) else float(dir_val)
                compass_text = self._degrees_to_direction(compass)

            # Convert to LV95
            lv95_e, lv95_n = self._wgs84_to_lv95(lat, lon)

            gps_data = GpsData(
                lat=lat,
                lon=lon,
                altitude_m=altitude,
                lv95_e=lv95_e,
                lv95_n=lv95_n,
                compass_direction=compass,
                compass_direction_text=compass_text,
            )

            logger.info(f"HEIC EXIF extrahiert: GPS ({lat:.6f}, {lon:.6f}) → LV95 ({lv95_e:.1f}, {lv95_n:.1f})")
            return gps_data, timestamp

        except Exception as e:
            logger.warning(f"HEIC EXIF-Extraktion fehlgeschlagen: {e}")
            return None, None

    def _dms_tuple_to_decimal(self, dms: tuple, ref: str) -> Optional[float]:
        """Konvertiert piexif DMS-Tuple zu Dezimalgrad"""
        try:
            d = dms[0][0] / dms[0][1]
            m = dms[1][0] / dms[1][1]
            s = dms[2][0] / dms[2][1]
            decimal = d + m / 60 + s / 3600
            if ref in ['S', 'W']:
                decimal = -decimal
            return decimal
        except Exception:
            return None

    def _extract_exif(self, file_bytes: bytes, is_heic: bool = False) -> Tuple[Optional[GpsData], Optional[str]]:
        """
        Extrahiert GPS und Timestamp aus EXIF-Daten.

        Args:
            file_bytes: Bilddaten
            is_heic: True wenn HEIC-Format (braucht spezielle Behandlung)

        Returns:
            Tuple[GpsData oder None, Timestamp-String oder None]
        """
        # HEIC braucht spezielle Behandlung (Pillow's _getexif() funktioniert nicht)
        if is_heic:
            return self._extract_exif_from_heic(file_bytes)

        try:
            image = Image.open(BytesIO(file_bytes))
            exif_data = image._getexif()

            if not exif_data:
                logger.debug("Keine EXIF-Daten gefunden")
                return None, None

            # Parse EXIF tags
            exif = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                exif[tag] = value

            # Extract timestamp
            timestamp = exif.get('DateTimeOriginal') or exif.get('DateTime')
            if timestamp:
                # Format: "2026:02:01 14:30:00" -> "2026-02-01T14:30:00"
                timestamp = timestamp.replace(':', '-', 2).replace(' ', 'T')

            # Extract GPS
            gps_info = exif.get('GPSInfo')
            if not gps_info:
                logger.debug("Keine GPS-Daten in EXIF")
                return None, timestamp

            # Parse GPS tags
            gps = {}
            for tag_id, value in gps_info.items():
                tag = GPSTAGS.get(tag_id, tag_id)
                gps[tag] = value

            # Extract coordinates
            lat = self._convert_gps_to_degrees(gps.get('GPSLatitude'), gps.get('GPSLatitudeRef'))
            lon = self._convert_gps_to_degrees(gps.get('GPSLongitude'), gps.get('GPSLongitudeRef'))

            if lat is None or lon is None:
                return None, timestamp

            # Extract altitude
            altitude = None
            if 'GPSAltitude' in gps:
                alt_value = gps['GPSAltitude']
                if hasattr(alt_value, 'numerator'):
                    altitude = float(alt_value.numerator) / float(alt_value.denominator)
                else:
                    altitude = float(alt_value)

            # Extract compass direction (GPSImgDirection)
            compass = None
            compass_text = None
            if 'GPSImgDirection' in gps:
                dir_value = gps['GPSImgDirection']
                if hasattr(dir_value, 'numerator'):
                    compass = float(dir_value.numerator) / float(dir_value.denominator)
                else:
                    compass = float(dir_value)
                compass_text = self._degrees_to_direction(compass)

            # Convert to LV95
            lv95_e, lv95_n = self._wgs84_to_lv95(lat, lon)

            gps_data = GpsData(
                lat=lat,
                lon=lon,
                altitude_m=altitude,
                lv95_e=lv95_e,
                lv95_n=lv95_n,
                compass_direction=compass,
                compass_direction_text=compass_text,
            )

            logger.info(f"EXIF extrahiert: GPS ({lat:.6f}, {lon:.6f}) → LV95 ({lv95_e:.1f}, {lv95_n:.1f}), Kompass: {compass_text}")

            return gps_data, timestamp

        except Exception as e:
            logger.warning(f"EXIF-Extraktion fehlgeschlagen: {e}")
            return None, None

    def _convert_gps_to_degrees(self, coord, ref) -> Optional[float]:
        """Konvertiert GPS-Koordinaten von Grad/Minuten/Sekunden zu Dezimalgrad"""
        if coord is None:
            return None

        try:
            # coord ist tuple von (degrees, minutes, seconds)
            def to_float(val):
                if hasattr(val, 'numerator'):
                    return float(val.numerator) / float(val.denominator)
                return float(val)

            degrees = to_float(coord[0])
            minutes = to_float(coord[1])
            seconds = to_float(coord[2])

            decimal = degrees + minutes / 60 + seconds / 3600

            if ref in ['S', 'W']:
                decimal = -decimal

            return decimal
        except Exception as e:
            logger.warning(f"GPS-Konvertierung fehlgeschlagen: {e}")
            return None

    def _degrees_to_direction(self, degrees: float) -> str:
        """Konvertiert Grad zu Himmelsrichtung"""
        directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        index = round(degrees / 45) % 8
        return directions[index]

    def _wgs84_to_lv95(self, lat: float, lon: float) -> Tuple[float, float]:
        """
        Konvertiert WGS84 (lat/lon) zu LV95 (E/N).
        Approximation basierend auf swisstopo Formeln.
        """
        # Auxiliary values
        lat_aux = (lat * 3600 - 169028.66) / 10000
        lon_aux = (lon * 3600 - 26782.5) / 10000

        # LV95 East
        e = 2600072.37 + 211455.93 * lon_aux \
            - 10938.51 * lon_aux * lat_aux \
            - 0.36 * lon_aux * lat_aux**2 \
            - 44.54 * lon_aux**3

        # LV95 North
        n = 1200147.07 + 308807.95 * lat_aux \
            + 3745.25 * lon_aux**2 \
            + 76.63 * lat_aux**2 \
            - 194.56 * lon_aux**2 * lat_aux \
            + 119.79 * lat_aux**3

        return round(e, 2), round(n, 2)

    # ============ PRELOAD 3D DATA ============

    async def _preload_building_data(self, gps_data: GpsData) -> Dict[str, Any]:
        """
        Lädt 3D-Gebäudedaten basierend auf GPS-Koordinaten.

        Returns:
            Dict mit egid, address, traufhoehe_m, firsthoehe_m, roof_type, polygon
        """
        if not gps_data or not gps_data.lv95_e or not gps_data.lv95_n:
            return {}

        try:
            from app.services.smart_building import get_smart_building_service

            service = get_smart_building_service()

            # Collect data by coordinates
            bundle = await service.collect_all_data_by_coordinates(
                e=gps_data.lv95_e,
                n=gps_data.lv95_n,
                include_research=False,  # Skip Claude research for speed
                include_zones_analysis=False,
                include_terrain=True,
            )

            if bundle and bundle.egid:
                logger.info(f"Pre-Load erfolgreich: EGID {bundle.egid}, Adresse: {bundle.address_matched}")

                return {
                    "egid": bundle.egid,
                    "address": bundle.address_matched,
                    "building_name": bundle.building_name,
                    "traufhoehe_m": bundle.traufhoehe_m,
                    "firsthoehe_m": bundle.firsthoehe_m,
                    "roof_type": bundle.roof_type,
                    "polygon": bundle.polygon,
                }

            logger.warning(f"Kein Gebäude bei Koordinaten ({gps_data.lv95_e}, {gps_data.lv95_n}) gefunden")
            return {}

        except Exception as e:
            logger.warning(f"Pre-Load fehlgeschlagen: {e}")
            return {}

    # ============ GWR DATA LOOKUP ============

    async def _get_gwr_data_from_coordinates(self, gps_data: GpsData) -> Dict[str, Any]:
        """
        Holt GWR-Daten via identify_buildings() für Reverse Geocoding.

        NEU 01.02.2026: Ersetzt _preload_building_data() - nur leichtgewichtiger
        GWR-Lookup, keine vollständigen Geodaten.

        Returns:
            Dict mit suggested_* Feldern (egid, address, street, etc.)
        """
        if not gps_data or not gps_data.lv95_e or not gps_data.lv95_n:
            return {}

        try:
            from app.services.swisstopo import get_swisstopo_service

            service = get_swisstopo_service()

            # identify_buildings() liefert Liste von BuildingInfo
            buildings = await service.identify_buildings(
                x=gps_data.lv95_e,
                y=gps_data.lv95_n,
                tolerance=50  # 50m Toleranz für GPS-Ungenauigkeit
            )

            if not buildings:
                logger.warning(f"Kein Gebäude bei ({gps_data.lv95_e}, {gps_data.lv95_n}) gefunden")
                return {}

            # Erstes Gebäude nehmen (nächstes zur Koordinate)
            building = buildings[0]

            logger.info(f"GWR-Lookup: EGID {building.egid}, Adresse: {building.address}")

            return {
                "suggested_egid": str(building.egid) if building.egid else None,
                "suggested_address": building.address,
                "suggested_street": building.street,
                "suggested_house_number": building.house_number,
                "suggested_postal_code": building.postal_code,
                "suggested_city": building.city,
                "suggested_floors": building.floors,
                "suggested_construction_year": building.construction_year,
                "suggested_building_category": building.building_category,
            }

        except Exception as e:
            logger.warning(f"GWR-Lookup fehlgeschlagen: {e}")
            return {}

    # ============ TERRAIN ANALYSIS ============

    async def _analyze_terrain(self, client, file_bytes: bytes, filename: str) -> Optional[TerrainAnalysis]:
        """
        Analysiert Terrain und Umgebung aus dem Foto mit Claude.

        NEU 01.02.2026: Erweiterte Analyse für Gerüstbau-Planung.

        Returns:
            TerrainAnalysis oder None bei Fehler
        """
        try:
            image_base64 = base64.standard_b64encode(file_bytes).decode('utf-8')
            media_type = self._get_media_type(filename)

            response = client.messages.create(
                model=ANALYSIS_MODEL,
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": image_base64},
                        },
                        {"type": "text", "text": self.TERRAIN_ANALYSIS_PROMPT}
                    ]
                }]
            )

            text = response.content[0].text
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            json_str = json_match.group(1) if json_match else text.strip()
            data = json.loads(json_str)

            # Parse JSON response to TerrainAnalysis
            terrain = data.get('terrain', {})
            access = data.get('access', {})
            environment = data.get('environment', {})
            obstacles = data.get('obstacles', {})

            return TerrainAnalysis(
                # Terrain
                slope_estimate=terrain.get('slope_estimate'),
                slope_direction=terrain.get('slope_direction'),
                ground_type=terrain.get('ground_type'),
                # Access
                access_type=access.get('type'),
                access_width=access.get('width'),
                # Environment
                neighboring_distance=environment.get('neighboring_distance'),
                trees_nearby=environment.get('trees_nearby', False),
                power_lines=environment.get('power_lines', False),
                street_furniture=environment.get('street_furniture', []),
                # Obstacles
                balconies_count=obstacles.get('balconies', 0),
                awnings_count=obstacles.get('awnings', 0),
                bay_windows=obstacles.get('bay_windows', False),
                overhangs=obstacles.get('overhangs', []),
                other_obstacles=obstacles.get('other', []),
                # Notes
                scaffold_notes=data.get('scaffold_notes'),
                confidence=data.get('confidence', 0.5),
            )

        except Exception as e:
            logger.warning(f"Terrain-Analyse fehlgeschlagen: {e}")
            return None

    # ============ IMAGE HELPERS ============

    # IMPORTANT: Claude API only supports these image types
    SUPPORTED_IMAGE_TYPES = ('jpg', 'jpeg', 'png', 'gif', 'webp')
    CONVERTIBLE_TYPES = ('heic', 'heif')  # Will be converted to JPEG

    def _is_pdf(self, filename: str) -> bool:
        return filename.lower().endswith('.pdf')

    def _is_image(self, filename: str) -> bool:
        return filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif'))

    def _is_supported_format(self, filename: str) -> bool:
        """Check if file format is supported (PDF or image)"""
        ext = filename.lower().split('.')[-1]
        return ext == 'pdf' or ext in self.SUPPORTED_IMAGE_TYPES or ext in self.CONVERTIBLE_TYPES

    def _get_media_type(self, filename: str) -> str:
        """Get media type for Claude API. ONLY returns types Claude supports!"""
        ext = filename.lower().split('.')[-1]
        # Note: HEIC/HEIF are not supported by Claude - must be converted first
        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'pdf': 'application/pdf',
        }
        return mime_types.get(ext, 'image/jpeg')  # Default to JPEG (for converted HEIC)

    def _convert_heic_to_jpeg(self, file_bytes: bytes) -> Tuple[bytes, bool]:
        """
        Konvertiert HEIC zu JPEG.

        Returns:
            Tuple[bytes, bool]: (converted_bytes, success)
        """
        if not HEIF_AVAILABLE:
            logger.error("pillow-heif nicht installiert! HEIC-Support nicht verfügbar.")
            logger.error("Installation: pip install pillow-heif")
            return file_bytes, False

        try:
            image = Image.open(BytesIO(file_bytes))
            output = BytesIO()
            # Convert to RGB if necessary (HEIC might be RGBA)
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            image.save(output, format='JPEG', quality=90)
            logger.info(f"HEIC erfolgreich zu JPEG konvertiert ({len(file_bytes)} → {output.tell()} bytes)")
            return output.getvalue(), True
        except Exception as e:
            logger.error(f"HEIC-Konvertierung fehlgeschlagen: {e}")
            return file_bytes, False

    # ============ MAIN ANALYSIS ============

    async def analyze(
        self,
        file_bytes: bytes,
        filename: str,
        fallback_gps: Optional[Tuple[float, float]] = None
    ) -> SmartExtractionResult:
        """
        Analysiert ein Foto/Dokument intelligent.

        1. EXIF extrahieren (GPS, Timestamp)
        2. Bildtyp klassifizieren
        3. Typ-spezifische Analyse durchführen

        Args:
            file_bytes: Dateiinhalt
            filename: Dateiname für Typ-Erkennung
            fallback_gps: Optional (lat, lon) Fallback für iOS Safari (EXIF wird dort entfernt)

        Returns:
            SmartExtractionResult
        """
        # Validate file format FIRST
        if not self._is_supported_format(filename):
            ext = filename.lower().split('.')[-1]
            supported = ', '.join(list(self.SUPPORTED_IMAGE_TYPES) + list(self.CONVERTIBLE_TYPES) + ['pdf'])
            return SmartExtractionResult(
                success=False,
                error=f"Nicht unterstützter Dateityp: .{ext}. Unterstützte Formate: {supported}"
            )

        client = self._get_client()

        if not client:
            return SmartExtractionResult(
                success=False,
                error="Claude API nicht verfügbar (ANTHROPIC_API_KEY fehlt)"
            )

        result = SmartExtractionResult()

        try:
            # Handle PDF separately
            if self._is_pdf(filename):
                return await self._analyze_pdf(client, file_bytes)

            # Check if HEIC format (needs special handling for EXIF)
            is_heic = filename.lower().endswith(('.heic', '.heif'))

            # Step 1: Extract EXIF BEFORE conversion (HEIC loses EXIF when converted!)
            # FIX 01.02.2026: HEIC EXIF-Extraktion mit piexif VOR JPEG-Konvertierung
            gps_data, timestamp = self._extract_exif(file_bytes, is_heic=is_heic)

            # HEIC conversion for Claude (doesn't support HEIC directly)
            if is_heic:
                logger.info("Konvertiere HEIC zu JPEG...")
                converted_bytes, success = self._convert_heic_to_jpeg(file_bytes)
                if not success:
                    return SmartExtractionResult(
                        success=False,
                        error="HEIC-Konvertierung fehlgeschlagen. iPhone-Fotos werden unterstützt, aber pillow-heif muss installiert sein."
                    )
                file_bytes = converted_bytes
                filename = filename.rsplit('.', 1)[0] + '.jpg'
            result.gps_data = gps_data
            result.photo_timestamp = timestamp

            # Step 1a: Fallback GPS (iOS Safari entfernt EXIF bei capture="environment")
            if not gps_data and fallback_gps:
                lat, lon = fallback_gps
                lv95_e, lv95_n = self._wgs84_to_lv95(lat, lon)
                gps_data = GpsData(
                    lat=lat,
                    lon=lon,
                    lv95_e=lv95_e,
                    lv95_n=lv95_n,
                )
                result.gps_data = gps_data
                logger.info(f"GPS-Fallback verwendet: ({lat:.6f}, {lon:.6f}) → LV95 ({lv95_e:.1f}, {lv95_n:.1f})")

            # Step 1b: GWR-Lookup via identify_buildings() (leichtgewichtig)
            # NEU 01.02.2026: Nur Reverse Geocoding, keine vollständigen Geodaten
            if gps_data and gps_data.lv95_e and gps_data.lv95_n:
                logger.info(f"GPS gefunden, lade GWR-Daten für ({gps_data.lv95_e}, {gps_data.lv95_n})...")
                gwr_data = await self._get_gwr_data_from_coordinates(gps_data)
                if gwr_data:
                    # Neue suggested_* Felder befüllen
                    result.suggested_egid = gwr_data.get('suggested_egid')
                    result.suggested_address = gwr_data.get('suggested_address')
                    result.suggested_street = gwr_data.get('suggested_street')
                    result.suggested_house_number = gwr_data.get('suggested_house_number')
                    result.suggested_postal_code = gwr_data.get('suggested_postal_code')
                    result.suggested_city = gwr_data.get('suggested_city')
                    result.suggested_floors = gwr_data.get('suggested_floors')
                    result.suggested_construction_year = gwr_data.get('suggested_construction_year')
                    result.suggested_building_category = gwr_data.get('suggested_building_category')

                    # Legacy preloaded_* Felder für Kompatibilität
                    result.preloaded_egid = gwr_data.get('suggested_egid')
                    result.preloaded_address = gwr_data.get('suggested_address')

                    # Use suggested address if no other address found
                    if not result.address and result.suggested_address:
                        result.address = result.suggested_address

            # Step 2: Classify image
            image_type, classification_confidence = await self._classify_image(client, file_bytes, filename)
            result.image_type = image_type

            logger.info(f"Bildtyp erkannt: {image_type} (confidence: {classification_confidence})")

            # Step 3: Type-specific analysis
            if image_type == "building_photo":
                result.building_analysis = await self._analyze_building_photo(client, file_bytes, filename)
                result.confidence = result.building_analysis.floors_count is not None and 0.8 or 0.5

                # NEU 01.02.2026: Terrain-Analyse für Gerüstbau-Planung
                result.terrain_analysis = await self._analyze_terrain(client, file_bytes, filename)
                if result.terrain_analysis:
                    logger.info(f"Terrain-Analyse: Neigung={result.terrain_analysis.slope_estimate}, "
                                f"Zufahrt={result.terrain_analysis.access_type}")

                # Address from photo - nur setzen wenn noch keine Adresse vorhanden
                # FIX 01.02.2026: suggested_address aus GWR hat Priorität über visible_address
                if result.building_analysis.visible_address and not result.address:
                    result.address = result.building_analysis.visible_address

                result.success = True

            elif image_type == "document":
                doc_result = await self._analyze_document(client, file_bytes, filename)
                result.address = doc_result.get('address')
                result.project_name = doc_result.get('project_name')
                result.client_name = doc_result.get('client_name')
                result.client_contact = doc_result.get('client_contact')
                result.description = doc_result.get('description')
                result.tender_number = doc_result.get('tender_number')
                result.submission_deadline = doc_result.get('submission_deadline')
                result.project_start = doc_result.get('project_start')
                result.project_end = doc_result.get('project_end')
                result.estimated_area_m2 = doc_result.get('estimated_area_m2')
                result.requirements = doc_result.get('requirements', [])
                result.confidence = doc_result.get('confidence', 0.5)
                result.success = True

            elif image_type == "sketch":
                result.sketch_analysis = await self._analyze_sketch(client, file_bytes, filename)
                result.confidence = result.sketch_analysis.confidence if hasattr(result.sketch_analysis, 'confidence') else 0.6

                if result.sketch_analysis.address_found:
                    result.address = result.sketch_analysis.address_found

                result.success = True

            elif image_type == "technical_plan":
                # Treat like sketch for now
                result.sketch_analysis = await self._analyze_sketch(client, file_bytes, filename)
                result.confidence = 0.7
                result.success = True

            else:  # mixed or unknown
                # Try building photo first, then document
                result.building_analysis = await self._analyze_building_photo(client, file_bytes, filename)
                doc_result = await self._analyze_document(client, file_bytes, filename)

                if doc_result.get('address'):
                    result.address = doc_result.get('address')
                elif result.building_analysis.visible_address:
                    result.address = result.building_analysis.visible_address

                result.project_name = doc_result.get('project_name')
                result.confidence = 0.6
                result.success = True

            return result

        except Exception as e:
            logger.exception(f"Analyse fehlgeschlagen: {e}")
            return SmartExtractionResult(
                success=False,
                error=f"Analyse fehlgeschlagen: {str(e)}"
            )

    async def _classify_image(self, client, file_bytes: bytes, filename: str) -> Tuple[str, float]:
        """Klassifiziert den Bildtyp"""
        image_base64 = base64.standard_b64encode(file_bytes).decode('utf-8')
        media_type = self._get_media_type(filename)

        response = client.messages.create(
            model=ANALYSIS_MODEL,
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_base64},
                    },
                    {"type": "text", "text": self.CLASSIFICATION_PROMPT}
                ]
            }]
        )

        try:
            text = response.content[0].text
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            json_str = json_match.group(1) if json_match else text.strip()
            data = json.loads(json_str)
            return data.get('image_type', 'unknown'), data.get('confidence', 0.5)
        except Exception as e:
            logger.warning(f"Klassifizierung Parse-Fehler: {e}")
            return 'unknown', 0.3

    async def _analyze_building_photo(self, client, file_bytes: bytes, filename: str) -> BuildingAnalysis:
        """Analysiert ein Gebäudefoto"""
        image_base64 = base64.standard_b64encode(file_bytes).decode('utf-8')
        media_type = self._get_media_type(filename)

        response = client.messages.create(
            model=ANALYSIS_MODEL,
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_base64},
                    },
                    {"type": "text", "text": self.BUILDING_PHOTO_PROMPT}
                ]
            }]
        )

        try:
            text = response.content[0].text
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            json_str = json_match.group(1) if json_match else text.strip()
            data = json.loads(json_str)

            return BuildingAnalysis(
                floors_count=data.get('floors_count'),
                height_estimate_m=data.get('height_estimate_m'),
                roof_type=data.get('roof_type'),
                roof_angle_deg=data.get('roof_angle_deg'),
                facade_material=data.get('facade_material'),
                facade_direction=data.get('facade_direction'),
                visible_address=data.get('visible_address'),
                obstacles=data.get('obstacles', []),
                windows_pattern=data.get('windows_pattern'),
                building_condition=data.get('building_condition'),
                neighboring_buildings=data.get('neighboring_buildings'),
                special_features=data.get('special_features', []),
            )
        except Exception as e:
            logger.warning(f"Building-Analyse Parse-Fehler: {e}")
            return BuildingAnalysis()

    async def _analyze_sketch(self, client, file_bytes: bytes, filename: str) -> SketchAnalysis:
        """Analysiert eine Skizze/Zeichnung"""
        image_base64 = base64.standard_b64encode(file_bytes).decode('utf-8')
        media_type = self._get_media_type(filename)

        response = client.messages.create(
            model=ANALYSIS_MODEL,
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_base64},
                    },
                    {"type": "text", "text": self.SKETCH_PROMPT}
                ]
            }]
        )

        try:
            text = response.content[0].text
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            json_str = json_match.group(1) if json_match else text.strip()
            data = json.loads(json_str)

            return SketchAnalysis(
                sketch_type=data.get('sketch_type'),
                work_type=data.get('work_type'),
                dimensions_found=data.get('dimensions_found', {}),
                notes_text=data.get('notes_text'),
                address_found=data.get('address_found'),
                address_required=data.get('address_found') is None,
                scale=data.get('scale'),
            )
        except Exception as e:
            logger.warning(f"Sketch-Analyse Parse-Fehler: {e}")
            return SketchAnalysis(address_required=True)

    async def _analyze_document(self, client, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Analysiert ein Dokument (OCR)"""
        image_base64 = base64.standard_b64encode(file_bytes).decode('utf-8')
        media_type = self._get_media_type(filename)

        response = client.messages.create(
            model=ANALYSIS_MODEL,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_base64},
                    },
                    {"type": "text", "text": self.DOCUMENT_PROMPT}
                ]
            }]
        )

        try:
            text = response.content[0].text
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            json_str = json_match.group(1) if json_match else text.strip()
            return json.loads(json_str)
        except Exception as e:
            logger.warning(f"Document-Analyse Parse-Fehler: {e}")
            return {}

    async def _analyze_pdf(self, client, file_bytes: bytes) -> SmartExtractionResult:
        """Analysiert ein PDF-Dokument"""
        pdf_base64 = base64.standard_b64encode(file_bytes).decode('utf-8')

        try:
            response = client.beta.messages.create(
                model=ANALYSIS_MODEL,
                max_tokens=2000,
                betas=["pdfs-2024-09-25"],
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_base64},
                        },
                        {"type": "text", "text": self.DOCUMENT_PROMPT}
                    ]
                }]
            )

            text = response.content[0].text
            json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            json_str = json_match.group(1) if json_match else text.strip()
            data = json.loads(json_str)

            return SmartExtractionResult(
                success=True,
                confidence=data.get('confidence', 0.7),
                image_type="document",
                address=data.get('address'),
                project_name=data.get('project_name'),
                client_name=data.get('client_name'),
                client_contact=data.get('client_contact'),
                description=data.get('description'),
                tender_number=data.get('tender_number'),
                submission_deadline=data.get('submission_deadline'),
                project_start=data.get('project_start'),
                project_end=data.get('project_end'),
                estimated_area_m2=data.get('estimated_area_m2'),
                requirements=data.get('requirements', []),
            )

        except Exception as e:
            logger.error(f"PDF-Analyse fehlgeschlagen: {e}")
            return SmartExtractionResult(
                success=False,
                error=f"PDF-Analyse fehlgeschlagen: {str(e)}"
            )


# Singleton
_analyzer_instance = None


def get_photo_analyzer() -> PhotoAnalyzer:
    """Gibt Singleton-Instanz des PhotoAnalyzers zurück"""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = PhotoAnalyzer()
    return _analyzer_instance
