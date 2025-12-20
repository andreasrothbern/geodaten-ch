"""
Pydantic Models für die Geodaten API
=====================================
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# Basis-Modelle
# ============================================================================

class Coordinates(BaseModel):
    """Koordinaten in verschiedenen Systemen"""
    lv95_e: float = Field(..., description="LV95 Ost (EPSG:2056)")
    lv95_n: float = Field(..., description="LV95 Nord (EPSG:2056)")
    wgs84_lon: Optional[float] = Field(None, description="WGS84 Längengrad")
    wgs84_lat: Optional[float] = Field(None, description="WGS84 Breitengrad")
    
    class Config:
        json_schema_extra = {
            "example": {
                "lv95_e": 2600000,
                "lv95_n": 1199000,
                "wgs84_lon": 7.4474,
                "wgs84_lat": 46.9480
            }
        }


# ============================================================================
# Adress-Modelle
# ============================================================================

class AddressSearchResult(BaseModel):
    """Ergebnis einer Adresssuche"""
    label: str = Field(..., description="Formatierte Adresse")
    street: Optional[str] = Field(None, description="Strassenname")
    house_number: Optional[str] = Field(None, description="Hausnummer")
    postal_code: Optional[str] = Field(None, description="PLZ")
    city: Optional[str] = Field(None, description="Ort")
    canton: Optional[str] = Field(None, description="Kanton (Kürzel)")
    coordinates: Coordinates
    feature_id: Optional[str] = Field(None, description="swisstopo Feature-ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "label": "Bundesplatz 3, 3011 Bern",
                "street": "Bundesplatz",
                "house_number": "3",
                "postal_code": "3011",
                "city": "Bern",
                "canton": "BE",
                "coordinates": {
                    "lv95_e": 600423.19,
                    "lv95_n": 199521.05,
                    "wgs84_lon": 7.4442,
                    "wgs84_lat": 46.9468
                }
            }
        }


class GeocodingResult(BaseModel):
    """Ergebnis einer Geokodierung"""
    input_address: str
    matched_address: str
    confidence: float = Field(..., ge=0, le=1, description="Konfidenz 0-1")
    coordinates: Coordinates
    
    class Config:
        json_schema_extra = {
            "example": {
                "input_address": "Bundesplatz 3, Bern",
                "matched_address": "Bundesplatz 3, 3011 Bern",
                "confidence": 0.95,
                "coordinates": {
                    "lv95_e": 600423.19,
                    "lv95_n": 199521.05
                }
            }
        }


# ============================================================================
# Gebäude-Modelle
# ============================================================================

class BuildingInfo(BaseModel):
    """Gebäudeinformationen aus dem GWR"""
    egid: int = Field(..., description="Eidg. Gebäudeidentifikator")
    address: str = Field(..., description="Vollständige Adresse")
    street: Optional[str] = None
    house_number: Optional[str] = None
    postal_code: Optional[int] = None
    city: Optional[str] = None
    canton: Optional[str] = None
    
    # Gebäudeeigenschaften
    construction_year: Optional[int] = Field(None, description="Baujahr")
    building_category: Optional[str] = Field(None, description="Gebäudekategorie")
    building_category_code: Optional[int] = Field(None, description="Kategorie-Code")
    building_class: Optional[str] = Field(None, description="Gebäudeklasse")
    building_status: Optional[str] = Field(None, description="Status (bestehend, etc.)")
    
    # Dimensionen
    floors: Optional[int] = Field(None, description="Anzahl Geschosse")
    apartments: Optional[int] = Field(None, description="Anzahl Wohnungen")
    area_m2: Optional[int] = Field(None, description="Gebäudefläche in m²")
    
    # Energie
    heating_type: Optional[str] = Field(None, description="Heizungsart")
    heating_energy: Optional[str] = Field(None, description="Energieträger Heizung")
    hot_water_energy: Optional[str] = Field(None, description="Energieträger Warmwasser")
    
    # Geometrie
    coordinates: Optional[Coordinates] = None
    geometry: Optional[Dict[str, Any]] = Field(None, description="GeoJSON Geometrie")
    
    # Metadaten
    last_update: Optional[str] = Field(None, description="Letzte Aktualisierung")
    
    class Config:
        json_schema_extra = {
            "example": {
                "egid": 190365,
                "address": "Höchistrasse 25, 6174 Sörenberg",
                "street": "Höchistrasse",
                "house_number": "25",
                "postal_code": 6174,
                "city": "Flühli",
                "canton": "LU",
                "construction_year": 1999,
                "building_category": "Einfamilienhaus",
                "building_category_code": 1020,
                "floors": 1,
                "apartments": 1,
                "area_m2": 127,
                "heating_type": "Wärmepumpe",
                "heating_energy": "Elektrizität"
            }
        }


# ============================================================================
# System-Modelle
# ============================================================================

class HealthResponse(BaseModel):
    """Health Check Response"""
    status: str = "healthy"
    service: str = "geodaten-api"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Fehler-Response"""
    error: str
    status_code: int
    detail: Optional[str] = None


# ============================================================================
# Lookup-Modelle
# ============================================================================

class LookupResult(BaseModel):
    """Kombiniertes Lookup-Ergebnis"""
    address: GeocodingResult
    buildings: List[BuildingInfo]
    buildings_count: int
