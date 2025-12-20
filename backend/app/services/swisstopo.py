"""
swisstopo API Adapter
======================

Adapter für die swisstopo REST API (api3.geo.admin.ch)
"""

import httpx
from typing import Optional, List, Dict, Any
import asyncio

from app.models.schemas import (
    AddressSearchResult,
    BuildingInfo,
    GeocodingResult,
    Coordinates
)


# Gebäudekategorie-Mapping (GWR Codes)
BUILDING_CATEGORIES = {
    1010: "Provisorische Unterkunft",
    1020: "Einfamilienhaus",
    1030: "Mehrfamilienhaus",
    1040: "Wohngebäude mit Nebennutzung",
    1060: "Gebäude mit teilweiser Wohnnutzung",
    1080: "Gebäude ohne Wohnnutzung",
}

# Heizungsart-Mapping (GWR Codes)
HEATING_TYPES = {
    7400: "Keine",
    7410: "Wärmepumpe",
    7420: "Thermische Solaranlage",
    7430: "Heizkessel",
    7431: "Heizkessel mit Brenner",
    7432: "Heizkessel ohne Brenner",
    7433: "Wärmetauscher",
    7434: "Elektrospeicher",
    7435: "Elektrische Direktheizung",
    7436: "Wärmekraftkopplung",
    7440: "Fernwärme",
    7450: "Einzelofenheizung",
    7499: "Andere",
}

# Energieträger-Mapping (GWR Codes)
ENERGY_SOURCES = {
    7500: "Keine",
    7501: "Luft",
    7510: "Erdwärme",
    7511: "Erdregister",
    7512: "Erdwärmesonde",
    7513: "Wasser (Grundwasser, etc.)",
    7520: "Gas",
    7530: "Heizöl",
    7540: "Holz",
    7541: "Holzschnitzel",
    7542: "Pellets",
    7543: "Stückholz",
    7550: "Abwärme",
    7560: "Elektrizität",
    7570: "Sonne (thermisch)",
    7580: "Fernwärme",
    7598: "Unbestimmt",
    7599: "Andere",
}


class SwisstopoService:
    """Service für swisstopo API Zugriff"""
    
    BASE_URL = "https://api3.geo.admin.ch"
    GWR_LAYER = "ch.bfs.gebaeude_wohnungs_register"
    
    def __init__(self):
        self.timeout = httpx.Timeout(15.0, connect=5.0)
    
    async def _request(self, endpoint: str, params: Dict = None) -> Dict:
        """HTTP Request an swisstopo API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.BASE_URL}{endpoint}"
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    
    # ========================================================================
    # Adresssuche
    # ========================================================================
    
    async def search_address(self, query: str, limit: int = 5) -> List[AddressSearchResult]:
        """Adresssuche über SearchServer"""
        params = {
            "searchText": query,
            "type": "locations",
            "origins": "address",
            "limit": limit,
        }
        
        data = await self._request("/rest/services/api/SearchServer", params)
        results = []
        
        for item in data.get("results", []):
            attrs = item.get("attrs", {})
            
            # Koordinaten extrahieren
            coords = Coordinates(
                lv95_e=attrs.get("y", attrs.get("x", 0)),  # swisstopo: y=E, x=N
                lv95_n=attrs.get("x", attrs.get("y", 0)),
                wgs84_lon=attrs.get("lon"),
                wgs84_lat=attrs.get("lat"),
            )
            
            # Label parsen für Details
            label = attrs.get("label", "").replace("<b>", "").replace("</b>", "")
            detail = attrs.get("detail", "")
            
            results.append(AddressSearchResult(
                label=label,
                street=None,  # Müsste aus Label geparst werden
                house_number=str(attrs.get("num", "")) if attrs.get("num") else None,
                postal_code=detail.split()[1] if len(detail.split()) > 1 else None,
                city=detail.split()[2] if len(detail.split()) > 2 else None,
                canton=detail.split()[-1].upper() if detail else None,
                coordinates=coords,
                feature_id=attrs.get("featureId"),
            ))
        
        return results
    
    async def geocode(self, address: str) -> Optional[GeocodingResult]:
        """Geokodierung einer Adresse"""
        results = await self.search_address(address, limit=1)
        
        if not results:
            return None
        
        best = results[0]
        
        return GeocodingResult(
            input_address=address,
            matched_address=best.label,
            confidence=0.9 if best.feature_id else 0.7,
            coordinates=best.coordinates,
        )
    
    # ========================================================================
    # Gebäudedaten
    # ========================================================================
    
    async def get_building_by_egid(self, egid: int, include_geometry: bool = False) -> Optional[BuildingInfo]:
        """Gebäude per EGID abrufen"""
        params = {
            "layer": self.GWR_LAYER,
            "searchText": str(egid),
            "searchField": "egid",
            "returnGeometry": str(include_geometry).lower(),
            "contains": "false",
        }
        
        data = await self._request("/rest/services/api/MapServer/find", params)
        results = data.get("results", [])
        
        if not results:
            return None
        
        return self._parse_building(results[0], include_geometry)
    
    async def identify_buildings(self, x: float, y: float, tolerance: int = 10) -> List[BuildingInfo]:
        """Gebäude an Koordinate identifizieren"""
        params = {
            "geometryType": "esriGeometryPoint",
            "geometry": f"{x},{y}",
            "mapExtent": "0,0,100,100",
            "imageDisplay": "100,100,100",
            "tolerance": str(tolerance),
            "layers": f"all:{self.GWR_LAYER}",
            "returnGeometry": "true",
        }
        
        data = await self._request("/rest/services/api/MapServer/identify", params)
        results = []
        
        for item in data.get("results", []):
            building = self._parse_building(item, include_geometry=True)
            if building:
                results.append(building)
        
        return results
    
    async def search_buildings(self, query: str, limit: int = 10) -> List[BuildingInfo]:
        """Gebäude per Textsuche finden"""
        params = {
            "searchText": query,
            "type": "featuresearch",
            "features": self.GWR_LAYER,
            "limit": limit,
        }
        
        data = await self._request("/rest/services/api/SearchServer", params)
        results = []
        
        for item in data.get("results", []):
            attrs = item.get("attrs", {})
            feature_id = attrs.get("featureId", attrs.get("feature_id"))
            
            if feature_id:
                # Detaildaten abrufen
                try:
                    building = await self._get_feature_details(feature_id)
                    if building:
                        results.append(building)
                except:
                    # Fallback: Basis-Infos aus Suchergebnis
                    coords = Coordinates(
                        lv95_e=attrs.get("y", 0),
                        lv95_n=attrs.get("x", 0),
                        wgs84_lon=attrs.get("lon"),
                        wgs84_lat=attrs.get("lat"),
                    )
                    results.append(BuildingInfo(
                        egid=int(feature_id.split("_")[0]) if "_" in str(feature_id) else 0,
                        address=attrs.get("label", ""),
                        coordinates=coords,
                    ))
        
        return results
    
    async def _get_feature_details(self, feature_id: str) -> Optional[BuildingInfo]:
        """Feature-Details per ID abrufen"""
        endpoint = f"/rest/services/api/MapServer/{self.GWR_LAYER}/{feature_id}"
        params = {"returnGeometry": "true"}
        
        data = await self._request(endpoint, params)
        feature = data.get("feature", {})
        
        if not feature:
            return None
        
        return self._parse_building({"attributes": feature.get("attributes", {}), 
                                      "geometry": feature.get("geometry")}, 
                                     include_geometry=True)
    
    def _parse_building(self, item: Dict, include_geometry: bool = False) -> Optional[BuildingInfo]:
        """Parsing eines GWR-Datensatzes"""
        attrs = item.get("attributes", {})
        
        if not attrs:
            return None
        
        # Koordinaten
        coords = None
        if attrs.get("gkode") and attrs.get("gkodn"):
            coords = Coordinates(
                lv95_e=float(attrs.get("gkode", 0)),
                lv95_n=float(attrs.get("gkodn", 0)),
            )
        
        # Geometrie
        geometry = None
        if include_geometry and item.get("geometry"):
            geometry = item.get("geometry")
        
        # Adresse zusammenbauen
        street_parts = []
        if attrs.get("strname"):
            street = attrs["strname"]
            if isinstance(street, list):
                street = street[0] if street else ""
            street_parts.append(street)
        if attrs.get("deinr"):
            street_parts.append(str(attrs["deinr"]))
        
        address_parts = []
        if street_parts:
            address_parts.append(" ".join(street_parts))
        if attrs.get("dplz4"):
            address_parts.append(str(attrs["dplz4"]))
        if attrs.get("ggdename"):
            address_parts.append(attrs["ggdename"])
        
        address = ", ".join(address_parts) if address_parts else f"EGID {attrs.get('egid', 'unbekannt')}"
        
        # Street name extrahieren
        street_name = attrs.get("strname")
        if isinstance(street_name, list):
            street_name = street_name[0] if street_name else None
        
        return BuildingInfo(
            egid=int(attrs.get("egid", 0)),
            address=address,
            street=street_name,
            house_number=str(attrs.get("deinr")) if attrs.get("deinr") else None,
            postal_code=int(attrs.get("dplz4")) if attrs.get("dplz4") else None,
            city=attrs.get("ggdename") or attrs.get("dplzname"),
            canton=attrs.get("gdekt"),
            construction_year=int(attrs.get("gbauj")) if attrs.get("gbauj") else None,
            building_category=BUILDING_CATEGORIES.get(attrs.get("gkat")),
            building_category_code=attrs.get("gkat"),
            building_status="bestehend" if attrs.get("gstat") == 1004 else str(attrs.get("gstat")),
            floors=int(attrs.get("gastw")) if attrs.get("gastw") else None,
            apartments=int(attrs.get("ganzwhg")) if attrs.get("ganzwhg") else None,
            area_m2=int(attrs.get("garea")) if attrs.get("garea") else None,
            heating_type=HEATING_TYPES.get(attrs.get("gwaerzh1")),
            heating_energy=ENERGY_SOURCES.get(attrs.get("genh1")),
            hot_water_energy=ENERGY_SOURCES.get(attrs.get("genw1")),
            coordinates=coords,
            geometry=geometry,
            last_update=attrs.get("gexpdat"),
        )
