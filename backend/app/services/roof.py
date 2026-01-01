"""
Roof Calculation Service
=========================

Berechnet Dachdaten aus verfügbaren Gebäudeinformationen:
- Dachneigung (aus Trauf-/Firsthöhe und Gebäudetiefe)
- Dachform (Flach, Sattel, Walm, Pult)
- Dachausrichtung (aus Polygon-Geometrie)
- Dachfläche (geschätzt)

Option C: Heuristische Berechnung für einfache Gebäude.
Für komplexe Gebäude wird Option A (Sonnendach) oder B (swissBUILDINGS3D 3D) empfohlen.

Version: 1.0
Datum: 28.12.2025
"""

import math
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum


class RoofType(str, Enum):
    """Dachformen nach DIN 18065"""
    FLACHDACH = "flachdach"          # < 5° Neigung
    PULTDACH = "pultdach"            # Einseitig geneigt
    SATTELDACH = "satteldach"        # Zwei symmetrische Dachflächen
    WALMDACH = "walmdach"            # Vier geneigte Flächen
    MANSARDDACH = "mansarddach"      # Gebrochene Dachflächen
    ZELTDACH = "zeltdach"            # Pyramidenform
    UNKNOWN = "unbekannt"


class RoofOrientation(str, Enum):
    """Hauptausrichtung des Dachfirsts"""
    NORTH_SOUTH = "N-S"       # First verläuft Nord-Süd
    EAST_WEST = "O-W"         # First verläuft Ost-West
    NORTHEAST_SOUTHWEST = "NO-SW"
    NORTHWEST_SOUTHEAST = "NW-SO"


@dataclass
class RoofData:
    """Berechnete Dachdaten"""
    # Grunddaten
    roof_type: RoofType
    roof_angle_deg: float              # Dachneigung in Grad
    roof_orientation: RoofOrientation  # Firstausrichtung
    first_azimuth_deg: float           # Azimut des Firsts (0° = Nord)

    # Massen
    roof_area_m2: float                # Geschätzte Dachfläche
    roof_overhang_m: float             # Dachüberstand (Standard 0.5m)

    # Gerüstbau-relevant
    traufhoehe_m: float                # Absolute Traufhöhe (für 3D-Visualisierung)
    trauf_to_first_m: float            # Höhendifferenz Traufe-First
    scaffolding_height_m: float        # Gerüsthöhe (First + 1m)

    # Qualität
    data_source: str                   # "calculated", "estimated", "default"
    confidence: float                  # 0-1, Konfidenz der Berechnung

    def to_dict(self) -> Dict[str, Any]:
        return {
            "roof_type": self.roof_type.value,
            "roof_angle_deg": round(self.roof_angle_deg, 1),
            "roof_orientation": self.roof_orientation.value,
            "first_azimuth_deg": round(self.first_azimuth_deg, 1),
            "roof_area_m2": round(self.roof_area_m2, 1),
            "roof_overhang_m": self.roof_overhang_m,
            "traufhoehe_m": round(self.traufhoehe_m, 2),  # Für 3D-Visualisierung
            "trauf_to_first_m": round(self.trauf_to_first_m, 2),
            "scaffolding_height_m": round(self.scaffolding_height_m, 1),
            "data_source": self.data_source,
            "confidence": round(self.confidence, 2),
        }


# =============================================================================
# DACHNEIGUNG-BERECHNUNG
# =============================================================================

def calculate_roof_angle(
    traufhoehe_m: float,
    firsthoehe_m: float,
    building_depth_m: float,
    roof_type: RoofType = RoofType.SATTELDACH
) -> float:
    """
    Berechnet die Dachneigung aus Höhen und Gebäudetiefe.

    Formel für Satteldach:
        neigung = arctan((firsthoehe - traufhoehe) / (tiefe / 2))

    Args:
        traufhoehe_m: Traufhöhe in Metern
        firsthoehe_m: Firsthöhe in Metern
        building_depth_m: Gebäudetiefe in Metern (senkrecht zum First)
        roof_type: Dachform (beeinflusst Berechnungsformel)

    Returns:
        Dachneigung in Grad
    """
    if not firsthoehe_m or not traufhoehe_m or not building_depth_m:
        return 0.0

    # Höhendifferenz
    delta_h = firsthoehe_m - traufhoehe_m

    if delta_h <= 0:
        return 0.0  # Flachdach oder Fehler

    # Horizontale Distanz je nach Dachform
    if roof_type == RoofType.SATTELDACH:
        # Bei Satteldach: halbe Gebäudetiefe pro Seite
        horizontal_distance = building_depth_m / 2
    elif roof_type == RoofType.PULTDACH:
        # Bei Pultdach: volle Gebäudetiefe
        horizontal_distance = building_depth_m
    else:
        # Default: Satteldach-Annahme
        horizontal_distance = building_depth_m / 2

    if horizontal_distance <= 0:
        return 0.0

    # Neigungswinkel berechnen
    angle_rad = math.atan(delta_h / horizontal_distance)
    angle_deg = math.degrees(angle_rad)

    return angle_deg


def classify_roof_type(
    roof_angle_deg: float,
    traufhoehe_m: Optional[float] = None,
    firsthoehe_m: Optional[float] = None,
    polygon_aspect_ratio: Optional[float] = None
) -> RoofType:
    """
    Klassifiziert die Dachform basierend auf Neigung und Gebäudegeometrie.

    Args:
        roof_angle_deg: Berechnete Dachneigung
        traufhoehe_m: Traufhöhe (optional, für Plausibilität)
        firsthoehe_m: Firsthöhe (optional, für Plausibilität)
        polygon_aspect_ratio: Länge/Breite des Gebäudes (optional)

    Returns:
        RoofType Enum
    """
    # Flachdach: < 5°
    if roof_angle_deg < 5:
        return RoofType.FLACHDACH

    # Sehr steiles Dach: > 60° (untypisch, evtl. Mansarddach)
    if roof_angle_deg > 60:
        return RoofType.MANSARDDACH

    # Quadratisches Gebäude → eher Walm- oder Zeltdach
    if polygon_aspect_ratio and 0.8 < polygon_aspect_ratio < 1.25:
        if roof_angle_deg > 30:
            return RoofType.ZELTDACH
        else:
            return RoofType.WALMDACH

    # Längliches Gebäude → Satteldach
    if roof_angle_deg >= 15:
        return RoofType.SATTELDACH

    # Flaches geneigtes Dach → Pultdach
    if 5 <= roof_angle_deg < 15:
        return RoofType.PULTDACH

    return RoofType.UNKNOWN


# =============================================================================
# DACHAUSRICHTUNG AUS POLYGON
# =============================================================================

def calculate_roof_orientation(
    polygon: List[Tuple[float, float]],
    building_length_m: Optional[float] = None,
    building_width_m: Optional[float] = None
) -> Tuple[RoofOrientation, float]:
    """
    Berechnet die Firstausrichtung aus der Polygon-Geometrie.

    Annahme: Der First verläuft parallel zur längsten Seite des Gebäudes.

    Args:
        polygon: Liste von (E, N) Koordinaten in LV95
        building_length_m: Gebäudelänge (optional, falls bekannt)
        building_width_m: Gebäudebreite (optional, falls bekannt)

    Returns:
        Tuple von (RoofOrientation, Azimut in Grad)
    """
    if not polygon or len(polygon) < 3:
        return RoofOrientation.EAST_WEST, 90.0

    # Längste Seite finden
    max_length = 0
    longest_side_vector = (1, 0)  # Default: Ost-West

    for i in range(len(polygon)):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % len(polygon)]

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.sqrt(dx * dx + dy * dy)

        if length > max_length:
            max_length = length
            longest_side_vector = (dx, dy)

    # Azimut berechnen (0° = Nord, 90° = Ost)
    dx, dy = longest_side_vector

    # atan2 gibt Winkel im Bereich [-π, π] mit 0° = Ost
    angle_rad = math.atan2(dx, dy)  # Vertauscht für Nord-Orientierung
    azimuth_deg = math.degrees(angle_rad)

    # Normalisieren auf [0, 360)
    if azimuth_deg < 0:
        azimuth_deg += 360

    # First ist senkrecht zur längsten Seite
    first_azimuth = (azimuth_deg + 90) % 360

    # Klassifizierung
    if 337.5 <= azimuth_deg or azimuth_deg < 22.5:
        orientation = RoofOrientation.EAST_WEST  # First O-W
    elif 22.5 <= azimuth_deg < 67.5:
        orientation = RoofOrientation.NORTHWEST_SOUTHEAST
    elif 67.5 <= azimuth_deg < 112.5:
        orientation = RoofOrientation.NORTH_SOUTH  # First N-S
    elif 112.5 <= azimuth_deg < 157.5:
        orientation = RoofOrientation.NORTHEAST_SOUTHWEST
    elif 157.5 <= azimuth_deg < 202.5:
        orientation = RoofOrientation.EAST_WEST
    elif 202.5 <= azimuth_deg < 247.5:
        orientation = RoofOrientation.NORTHWEST_SOUTHEAST
    elif 247.5 <= azimuth_deg < 292.5:
        orientation = RoofOrientation.NORTH_SOUTH
    else:  # 292.5 <= azimuth_deg < 337.5
        orientation = RoofOrientation.NORTHEAST_SOUTHWEST

    return orientation, first_azimuth


# =============================================================================
# DACHFLÄCHE BERECHNUNG
# =============================================================================

def calculate_roof_area(
    ground_area_m2: float,
    roof_angle_deg: float,
    roof_type: RoofType = RoofType.SATTELDACH,
    overhang_m: float = 0.5
) -> float:
    """
    Berechnet die Dachfläche aus Grundfläche und Neigung.

    Formel: Dachfläche = Grundfläche / cos(neigung) * Faktor

    Args:
        ground_area_m2: Gebäudegrundfläche in m²
        roof_angle_deg: Dachneigung in Grad
        roof_type: Dachform
        overhang_m: Dachüberstand in Metern

    Returns:
        Geschätzte Dachfläche in m²
    """
    if roof_angle_deg <= 0:
        # Flachdach: Dachfläche ≈ Grundfläche + Rand für Überstand
        roof_perimeter_factor = 1.1  # ~10% Zuschlag für Attika
        return ground_area_m2 * roof_perimeter_factor

    # Neigung in Radianten
    angle_rad = math.radians(roof_angle_deg)

    # Grundfaktor: 1/cos(neigung) für geneigte Fläche
    slope_factor = 1 / math.cos(angle_rad)

    # Dachform-Faktor
    if roof_type == RoofType.SATTELDACH:
        # Satteldach: 2 geneigte Flächen
        form_factor = 1.0
    elif roof_type == RoofType.WALMDACH:
        # Walmdach: 4 geneigte Flächen (mehr Fläche durch Giebel)
        form_factor = 1.15
    elif roof_type == RoofType.PULTDACH:
        # Pultdach: 1 geneigte Fläche
        form_factor = 1.0
    elif roof_type == RoofType.ZELTDACH:
        # Zeltdach: 4 dreieckige Flächen
        form_factor = 1.1
    else:
        form_factor = 1.0

    # Berechnung
    roof_area = ground_area_m2 * slope_factor * form_factor

    return roof_area


# =============================================================================
# HAUPT-BERECHNUNGSFUNKTION
# =============================================================================

def calculate_roof_data(
    traufhoehe_m: Optional[float],
    firsthoehe_m: Optional[float],
    building_depth_m: Optional[float],
    building_length_m: Optional[float] = None,
    ground_area_m2: Optional[float] = None,
    polygon: Optional[List[Tuple[float, float]]] = None,
    floors: Optional[int] = None,
    building_category_code: Optional[int] = None
) -> RoofData:
    """
    Berechnet alle Dachdaten aus verfügbaren Gebäudeinformationen.

    Dies ist die Hauptfunktion für Option C (heuristische Berechnung).

    Args:
        traufhoehe_m: Traufhöhe aus swissBUILDINGS3D
        firsthoehe_m: Firsthöhe aus swissBUILDINGS3D
        building_depth_m: Gebäudetiefe (senkrecht zum First)
        building_length_m: Gebäudelänge (parallel zum First)
        ground_area_m2: Grundfläche in m²
        polygon: Gebäudepolygon [(E, N), ...]
        floors: Anzahl Geschosse (für Fallback-Schätzungen)
        building_category_code: GWR Kategorie-Code

    Returns:
        RoofData mit allen berechneten Werten
    """
    confidence = 0.0
    data_source = "default"

    # =========================================================================
    # SCHRITT 1: Höhendifferenz berechnen
    # =========================================================================

    trauf_to_first = 0.0

    if traufhoehe_m is not None and firsthoehe_m is not None:
        trauf_to_first = firsthoehe_m - traufhoehe_m
        data_source = "calculated"
        confidence += 0.4
    elif firsthoehe_m is not None:
        # Nur Firsthöhe bekannt → Traufe schätzen (85% der Firsthöhe)
        traufhoehe_m = firsthoehe_m * 0.85
        trauf_to_first = firsthoehe_m - traufhoehe_m
        data_source = "estimated"
        confidence += 0.2
    elif floors:
        # Aus Geschosszahl schätzen
        estimated_height = floors * 2.8 + 3.0  # Geschosse + Dach
        traufhoehe_m = floors * 2.8
        firsthoehe_m = estimated_height
        trauf_to_first = 3.0
        data_source = "estimated"
        confidence += 0.1
    else:
        # Default-Werte
        traufhoehe_m = 8.0
        firsthoehe_m = 11.0
        trauf_to_first = 3.0

    # =========================================================================
    # SCHRITT 2: Gebäudetiefe ermitteln
    # =========================================================================

    if building_depth_m is None:
        if polygon and len(polygon) >= 3:
            # Aus Polygon-Bounding-Box
            xs = [p[0] for p in polygon]
            ys = [p[1] for p in polygon]
            width = max(xs) - min(xs)
            depth = max(ys) - min(ys)
            building_depth_m = min(width, depth)  # Tiefe = kürzere Seite
            building_length_m = max(width, depth)
            confidence += 0.2
        elif ground_area_m2:
            # Aus Grundfläche (quadratisches Gebäude annehmen)
            building_depth_m = math.sqrt(ground_area_m2)
            building_length_m = building_depth_m
            confidence += 0.1
        else:
            # Default
            building_depth_m = 10.0
            building_length_m = 12.0

    # =========================================================================
    # SCHRITT 3: Dachneigung berechnen
    # =========================================================================

    roof_angle = calculate_roof_angle(
        traufhoehe_m=traufhoehe_m,
        firsthoehe_m=firsthoehe_m,
        building_depth_m=building_depth_m
    )

    if roof_angle > 0:
        confidence += 0.2

    # =========================================================================
    # SCHRITT 4: Dachform klassifizieren
    # =========================================================================

    aspect_ratio = None
    if building_length_m and building_depth_m and building_depth_m > 0:
        aspect_ratio = building_length_m / building_depth_m

    roof_type = classify_roof_type(
        roof_angle_deg=roof_angle,
        traufhoehe_m=traufhoehe_m,
        firsthoehe_m=firsthoehe_m,
        polygon_aspect_ratio=aspect_ratio
    )

    # Kategorie-basierte Anpassung
    if building_category_code:
        # Industriegebäude haben oft Flach- oder Sheddächer
        if building_category_code in [1080, 1212]:
            if roof_angle < 10:
                roof_type = RoofType.FLACHDACH
        # Einfamilienhäuser meist Satteldach
        elif building_category_code == 1020:
            if roof_type == RoofType.UNKNOWN:
                roof_type = RoofType.SATTELDACH

    # =========================================================================
    # SCHRITT 5: Dachausrichtung berechnen
    # =========================================================================

    if polygon and len(polygon) >= 3:
        orientation, azimuth = calculate_roof_orientation(polygon)
        confidence += 0.1
    else:
        orientation = RoofOrientation.EAST_WEST
        azimuth = 90.0

    # =========================================================================
    # SCHRITT 6: Dachfläche berechnen
    # =========================================================================

    if ground_area_m2:
        roof_area = calculate_roof_area(
            ground_area_m2=ground_area_m2,
            roof_angle_deg=roof_angle,
            roof_type=roof_type
        )
    elif building_length_m and building_depth_m:
        estimated_ground = building_length_m * building_depth_m
        roof_area = calculate_roof_area(
            ground_area_m2=estimated_ground,
            roof_angle_deg=roof_angle,
            roof_type=roof_type
        )
    else:
        roof_area = 120.0  # Default für Einfamilienhaus

    # =========================================================================
    # SCHRITT 7: Gerüsthöhe berechnen (SUVA: First + 1m)
    # =========================================================================

    scaffolding_height = (firsthoehe_m or 11.0) + 1.0

    # =========================================================================
    # Ergebnis zusammenstellen
    # =========================================================================

    return RoofData(
        roof_type=roof_type,
        roof_angle_deg=roof_angle,
        roof_orientation=orientation,
        first_azimuth_deg=azimuth,
        roof_area_m2=roof_area,
        roof_overhang_m=0.5,
        traufhoehe_m=traufhoehe_m or 8.0,  # Für 3D-Visualisierung
        trauf_to_first_m=trauf_to_first,
        scaffolding_height_m=scaffolding_height,
        data_source=data_source,
        confidence=min(confidence, 1.0)
    )


# =============================================================================
# SINGLETON SERVICE
# =============================================================================

class RoofService:
    """
    Service für Dach-Berechnungen.

    Verwendung:
        roof_service = get_roof_service()
        roof_data = roof_service.calculate(
            traufhoehe_m=12.5,
            firsthoehe_m=15.0,
            building_depth_m=10.0
        )
    """

    def calculate(
        self,
        traufhoehe_m: Optional[float] = None,
        firsthoehe_m: Optional[float] = None,
        building_depth_m: Optional[float] = None,
        building_length_m: Optional[float] = None,
        ground_area_m2: Optional[float] = None,
        polygon: Optional[List[Tuple[float, float]]] = None,
        floors: Optional[int] = None,
        building_category_code: Optional[int] = None
    ) -> RoofData:
        """Berechnet Dachdaten aus verfügbaren Gebäudeinformationen."""
        return calculate_roof_data(
            traufhoehe_m=traufhoehe_m,
            firsthoehe_m=firsthoehe_m,
            building_depth_m=building_depth_m,
            building_length_m=building_length_m,
            ground_area_m2=ground_area_m2,
            polygon=polygon,
            floors=floors,
            building_category_code=building_category_code
        )

    def estimate_from_heights_only(
        self,
        traufhoehe_m: float,
        firsthoehe_m: float
    ) -> Dict[str, Any]:
        """
        Schnelle Schätzung nur aus Höhen (ohne Polygon).

        Für Frontend-Anzeige wenn noch keine Geometrie geladen ist.
        """
        trauf_to_first = firsthoehe_m - traufhoehe_m

        # Typische Gebäudetiefe für CH: 10-12m
        estimated_depth = 10.0

        roof_angle = calculate_roof_angle(
            traufhoehe_m=traufhoehe_m,
            firsthoehe_m=firsthoehe_m,
            building_depth_m=estimated_depth
        )

        roof_type = classify_roof_type(roof_angle)

        return {
            "roof_type": roof_type.value,
            "roof_angle_deg": round(roof_angle, 1),
            "trauf_to_first_m": round(trauf_to_first, 2),
            "scaffolding_height_m": round(firsthoehe_m + 1.0, 1),
            "data_source": "quick_estimate",
            "confidence": 0.3
        }


# Singleton
_roof_service: Optional[RoofService] = None


def get_roof_service() -> RoofService:
    """Gibt die RoofService-Instanz zurück (Singleton)."""
    global _roof_service
    if _roof_service is None:
        _roof_service = RoofService()
    return _roof_service
