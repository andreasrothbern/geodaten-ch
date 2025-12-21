"""
Geodaten Schweiz API
====================

REST API für Schweizer Geodaten (Gebäude, Adressen, Grundstücke)
Primäre Datenquelle: swisstopo / geo.admin.ch
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List

from app.services.swisstopo import SwisstopoService
from app.services.cache import CacheService
from app.services.geodienste import (
    GeodiensteService,
    calculate_scaffolding_data,
    estimate_building_height,
)
from app.models.schemas import (
    AddressSearchResult,
    BuildingInfo,
    GeocodingResult,
    HealthResponse,
    ErrorResponse
)

# Services initialisieren
swisstopo = SwisstopoService()
geodienste = GeodiensteService()
cache = CacheService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup und Shutdown Events"""
    # Startup
    cache.initialize()
    print("✅ Geodaten API gestartet")
    yield
    # Shutdown
    cache.close()
    print("👋 Geodaten API beendet")


# FastAPI App
app = FastAPI(
    title="Geodaten Schweiz API",
    description="""
    REST API für Schweizer Geodaten.
    
    ## Features
    - 🏠 Gebäudedaten (GWR) - Baujahr, Wohnungen, Heizung
    - 📍 Adresssuche und Geokodierung
    - 🗺️ Koordinaten-basierte Abfragen
    
    ## Datenquellen
    - swisstopo / geo.admin.ch (primär)
    - Eidg. Gebäude- und Wohnungsregister (GWR)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS für Frontend
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
]
# Railway Frontend URL hinzufügen
if os.getenv("FRONTEND_URL"):
    allowed_origins.append(os.getenv("FRONTEND_URL"))
# Fallback: alle railway.app Subdomains erlauben
allowed_origins.append("https://cooperative-commitment-production.up.railway.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health Check für Railway.app"""
    return HealthResponse(
        status="healthy",
        service="geodaten-api",
        version="1.0.0"
    )


@app.get("/", tags=["System"])
async def root():
    """API Info"""
    return {
        "name": "Geodaten Schweiz API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# ============================================================================
# Adresssuche
# ============================================================================

@app.get("/api/v1/address/search", 
         response_model=List[AddressSearchResult],
         tags=["Adressen"])
async def search_address(
    q: str = Query(..., min_length=3, description="Suchbegriff (min. 3 Zeichen)"),
    limit: int = Query(5, ge=1, le=20, description="Max. Anzahl Resultate")
):
    """
    Adresssuche in der Schweiz.
    
    Sucht nach Adressen und gibt Koordinaten + Metadaten zurück.
    
    **Beispiel:** `?q=Bundesplatz 3, Bern`
    """
    # Cache prüfen
    cache_key = f"address:{q}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        results = await swisstopo.search_address(q, limit=limit)
        
        # Cache speichern (24h)
        cache.set(cache_key, results, ttl_hours=24)
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/geocode",
         response_model=GeocodingResult,
         tags=["Adressen"])
async def geocode_address(
    address: str = Query(..., min_length=5, description="Vollständige Adresse")
):
    """
    Geokodierung einer Adresse.
    
    Gibt die Koordinaten (LV95 + WGS84) für eine Adresse zurück.
    
    **Beispiel:** `?address=Kramgasse 10, 3011 Bern`
    """
    cache_key = f"geocode:{address}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        result = await swisstopo.geocode(address)
        if not result:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")
        
        cache.set(cache_key, result, ttl_hours=24)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Gebäudedaten
# ============================================================================

@app.get("/api/v1/building/egid/{egid}",
         response_model=BuildingInfo,
         tags=["Gebäude"])
async def get_building_by_egid(
    egid: int,
    include_geometry: bool = Query(False, description="Geometrie inkludieren")
):
    """
    Gebäudedaten per EGID abrufen.
    
    Der EGID (Eidg. Gebäudeidentifikator) ist schweizweit eindeutig.
    
    **Beispiel:** `/api/v1/building/egid/190365`
    """
    cache_key = f"building:egid:{egid}:{include_geometry}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        result = await swisstopo.get_building_by_egid(egid, include_geometry)
        if not result:
            raise HTTPException(status_code=404, detail=f"Gebäude mit EGID {egid} nicht gefunden")
        
        cache.set(cache_key, result, ttl_hours=1)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/building/at",
         response_model=List[BuildingInfo],
         tags=["Gebäude"])
async def get_buildings_at_location(
    x: float = Query(..., description="LV95 Ost-Koordinate (E)"),
    y: float = Query(..., description="LV95 Nord-Koordinate (N)"),
    tolerance: int = Query(10, ge=1, le=100, description="Suchradius in Metern")
):
    """
    Gebäude an einer Koordinate finden.
    
    Verwendet LV95-Koordinaten (EPSG:2056).
    
    **Beispiel:** `?x=2600000&y=1199000&tolerance=20`
    """
    cache_key = f"building:at:{x}:{y}:{tolerance}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        results = await swisstopo.identify_buildings(x, y, tolerance)
        cache.set(cache_key, results, ttl_hours=1)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/building/search",
         response_model=List[BuildingInfo],
         tags=["Gebäude"])
async def search_buildings(
    q: str = Query(..., min_length=3, description="Suchbegriff (Adresse, Ort)"),
    limit: int = Query(10, ge=1, le=50, description="Max. Anzahl Resultate")
):
    """
    Gebäude per Textsuche finden.
    
    Durchsucht Adressen und Ortsnamen im GWR.
    
    **Beispiel:** `?q=Bundesplatz Bern&limit=5`
    """
    cache_key = f"building:search:{q}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        results = await swisstopo.search_buildings(q, limit=limit)
        cache.set(cache_key, results, ttl_hours=1)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Kombinierte Abfragen
# ============================================================================

@app.get("/api/v1/lookup",
         tags=["Kombiniert"])
async def lookup_address(
    address: str = Query(..., min_length=5, description="Adresse")
):
    """
    Komplette Abfrage: Adresse → Koordinaten → Gebäudedaten
    
    Kombiniert Geokodierung und Gebäudesuche in einem Request.
    
    **Beispiel:** `?address=Bundesplatz 3, 3011 Bern`
    """
    cache_key = f"lookup:{address}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    try:
        # 1. Geokodieren
        geo = await swisstopo.geocode(address)
        if not geo:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")
        
        # 2. Gebäude an Koordinate suchen
        buildings = await swisstopo.identify_buildings(
            geo.coordinates.lv95_e, 
            geo.coordinates.lv95_n,
            tolerance=15
        )
        
        result = {
            "address": geo,
            "buildings": buildings,
            "buildings_count": len(buildings)
        }
        
        cache.set(cache_key, result, ttl_hours=1)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Gerüstbau-Daten (Gebäudegeometrie)
# ============================================================================

@app.get("/api/v1/scaffolding",
         tags=["Gerüstbau"])
async def get_scaffolding_data(
    address: str = Query(..., min_length=5, description="Adresse"),
    egid: Optional[int] = Query(None, description="EGID (falls bekannt)"),
    height: Optional[float] = Query(None, description="Manuelle Gebäudehöhe in Metern"),
    refresh: bool = Query(False, description="Cache ignorieren und neu laden")
):
    """
    Gebäudegeometrie und Gerüstbau-relevante Daten abrufen.

    Liefert:
    - Exakten Grundriss (Polygon mit allen Eckpunkten)
    - Seitenlängen jeder Fassade
    - Gesamtumfang (für Gerüstmeter)
    - Geschätzte Gebäudehöhe
    - Geschätzte Gerüstfläche

    **Beispiel:** `?address=Bundesplatz 3, 3011 Bern`
    """
    cache_key = f"scaffolding:{address}:{egid}"

    # Cache nur verwenden wenn nicht refresh und keine manuelle Höhe
    if not refresh and not height:
        cached = cache.get(cache_key)
        if cached:
            return cached

    try:
        # 1. Adresse geokodieren
        geo = await swisstopo.geocode(address)
        if not geo:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")

        # 2. GWR-Daten abrufen (für Geschosse, Kategorie)
        buildings = await swisstopo.identify_buildings(
            geo.coordinates.lv95_e,
            geo.coordinates.lv95_n,
            tolerance=15
        )

        # Gebäude finden: bevorzugt per EGID, dann per Hausnummer, dann erstes
        building = None
        if egid:
            building = next((b for b in buildings if b.egid == egid), None)

        if not building and buildings:
            # Hausnummer aus der gesuchten Adresse extrahieren
            import re
            match = re.search(r'(\d+\w*)', address)
            if match:
                searched_number = match.group(1).lower()
                # Gebäude mit passender Hausnummer finden
                for b in buildings:
                    if b.house_number and b.house_number.lower() == searched_number:
                        building = b
                        break

        if not building and buildings:
            building = buildings[0]

        # 3. Gebäudegeometrie aus WFS abrufen
        geometry = await geodienste.get_building_geometry(
            x=geo.coordinates.lv95_e,
            y=geo.coordinates.lv95_n,
            tolerance=50,
            egid=egid or (building.egid if building else None)
        )

        if not geometry:
            raise HTTPException(
                status_code=404,
                detail="Gebäudegeometrie nicht gefunden. Möglicherweise keine AV-Daten für diesen Standort."
            )

        # 4. Gerüstbau-Daten berechnen
        scaffolding_data = calculate_scaffolding_data(
            geometry=geometry,
            floors=building.floors if building else None,
            building_category_code=building.building_category_code if building else None,
            manual_height=height,
        )

        # 5. Adress- und GWR-Infos hinzufügen
        result = {
            "address": {
                "input": address,
                "matched": geo.matched_address,
                "coordinates": {
                    "lv95_e": geo.coordinates.lv95_e,
                    "lv95_n": geo.coordinates.lv95_n,
                }
            },
            "gwr_data": {
                "egid": building.egid if building else geometry.egid,
                "building_category": building.building_category if building else None,
                "construction_year": building.construction_year if building else None,
                "floors": building.floors if building else None,
                "area_m2_gwr": building.area_m2 if building else None,
            },
            **scaffolding_data,
        }

        cache.set(cache_key, result, ttl_hours=24)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/scaffolding/by-egid/{egid}",
         tags=["Gerüstbau"])
async def get_scaffolding_by_egid(
    egid: int,
    height: Optional[float] = Query(None, description="Manuelle Gebäudehöhe in Metern")
):
    """
    Gebäudegeometrie per EGID abrufen.

    Schneller als Adresssuche, wenn EGID bekannt ist.

    **Beispiel:** `/api/v1/scaffolding/by-egid/2242547`
    """
    cache_key = f"scaffolding:egid:{egid}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        # 1. Gebäude per EGID aus GWR abrufen
        building = await swisstopo.get_building_by_egid(egid, include_geometry=True)

        if not building or not building.coordinates:
            raise HTTPException(status_code=404, detail=f"Gebäude mit EGID {egid} nicht gefunden")

        # 2. Geometrie aus WFS abrufen
        geometry = await geodienste.get_building_geometry(
            x=building.coordinates.lv95_e,
            y=building.coordinates.lv95_n,
            tolerance=50,
            egid=egid
        )

        if not geometry:
            raise HTTPException(
                status_code=404,
                detail="Gebäudegeometrie nicht verfügbar"
            )

        # 3. Gerüstbau-Daten berechnen
        scaffolding_data = calculate_scaffolding_data(
            geometry=geometry,
            floors=building.floors,
            building_category_code=building.building_category_code,
            manual_height=height,
        )

        result = {
            "address": {
                "matched": building.address,
                "coordinates": {
                    "lv95_e": building.coordinates.lv95_e,
                    "lv95_n": building.coordinates.lv95_n,
                }
            },
            "gwr_data": {
                "egid": building.egid,
                "building_category": building.building_category,
                "construction_year": building.construction_year,
                "floors": building.floors,
                "area_m2_gwr": building.area_m2,
            },
            **scaffolding_data,
        }

        cache.set(cache_key, result, ttl_hours=24)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Höhendatenbank
# ============================================================================

@app.get("/api/v1/heights/stats",
         tags=["System"])
async def get_height_database_stats():
    """
    Statistiken der Gebäudehöhen-Datenbank abrufen.

    Zeigt an, wie viele Gebäudehöhen aus swissBUILDINGS3D importiert wurden.
    """
    try:
        from app.services.height_db import get_database_stats
        return get_database_stats()
    except ImportError:
        return {"exists": False, "message": "Height database module not available"}


@app.get("/api/v1/heights/{egid}",
         tags=["System"])
async def get_height_for_egid(egid: int):
    """
    Gebäudehöhe für eine EGID aus der Datenbank abrufen.
    """
    try:
        from app.services.height_db import get_building_height
        result = get_building_height(egid)
        if result:
            return {
                "egid": egid,
                "height_m": result[0],
                "source": result[1],
                "found": True
            }
        return {
            "egid": egid,
            "found": False,
            "message": "Keine Höhendaten für dieses Gebäude"
        }
    except ImportError:
        raise HTTPException(status_code=503, detail="Height database not available")


@app.post("/api/v1/heights/fetch-on-demand",
          tags=["System"])
async def fetch_height_on_demand(
    e: float = Query(..., description="LV95 Easting (E-Koordinate)"),
    n: float = Query(..., description="LV95 Northing (N-Koordinate)"),
    egid: Optional[int] = Query(None, description="EGID für direkte Höhenabfrage")
):
    """
    Gebäudehöhe on-demand von swissBUILDINGS3D abrufen.

    Diese Funktion:
    1. Findet das passende Tile für die Koordinaten
    2. Lädt das Tile herunter und importiert alle Gebäudehöhen
    3. Gibt die Höhe für das angegebene Gebäude zurück

    **Wichtig:** Diese Operation kann einige Sekunden dauern, da das Tile
    (~10-50 MB) heruntergeladen und verarbeitet werden muss.

    **Beispiel:** `?e=2600000&n=1199000&egid=12345`
    """
    try:
        from app.services.height_fetcher import fetch_height_for_coordinates
        result = await fetch_height_for_coordinates(e, n, egid)
        return result
    except ImportError as ie:
        raise HTTPException(
            status_code=503,
            detail=f"Height fetcher service not available: {str(ie)}"
        )
    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching height: {str(ex)}"
        )


@app.get("/api/v1/heights/3d-tiles",
         tags=["Höhendaten"])
async def get_height_from_3d_tiles(
    lat: float = Query(..., description="WGS84 Latitude"),
    lon: float = Query(..., description="WGS84 Longitude"),
    max_distance: float = Query(100.0, description="Maximale Suchentfernung in Metern")
):
    """
    Gebäudehöhe aus 3D Tiles abrufen (koordinatenbasiert).

    Diese Funktion sucht das nächstgelegene Gebäude in den swissBUILDINGS3D 3D Tiles
    und gibt dessen gemessene Höhe zurück.

    **Vorteile:**
    - Keine EGID erforderlich
    - Direkte Koordinatensuche
    - Schnell (~1-2 Sekunden)

    **Einschränkungen:**
    - Nicht alle Gebiete der Schweiz sind abgedeckt (insb. städtische Zentren)
    - Genauigkeit abhängig von der Gebäudedichte im Tile

    **Beispiel:** `?lat=46.3131&lon=8.4476`
    """
    try:
        from app.services.tiles3d_fetcher import fetch_height_from_3d_tiles
        result = await fetch_height_from_3d_tiles(lat, lon, max_distance)
        return result
    except ImportError as ie:
        raise HTTPException(
            status_code=503,
            detail=f"3D Tiles service not available: {str(ie)}"
        )
    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching height from 3D Tiles: {str(ex)}"
        )


@app.get("/api/v1/heights/3d-tiles-lv95",
         tags=["Höhendaten"])
async def get_height_from_3d_tiles_lv95(
    e: float = Query(..., description="LV95 Easting (E-Koordinate)"),
    n: float = Query(..., description="LV95 Northing (N-Koordinate)"),
    max_distance: float = Query(100.0, description="Maximale Suchentfernung in Metern")
):
    """
    Gebäudehöhe aus 3D Tiles mit LV95-Koordinaten abrufen.

    Konvertiert LV95 zu WGS84 und sucht dann in den 3D Tiles.

    **Beispiel:** `?e=2679000&n=1247000`
    """
    try:
        from app.services.tiles3d_fetcher import fetch_height_from_3d_tiles_lv95
        result = await fetch_height_from_3d_tiles_lv95(e, n, max_distance)
        return result
    except ImportError as ie:
        raise HTTPException(
            status_code=503,
            detail=f"3D Tiles service not available: {str(ie)}"
        )
    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching height from 3D Tiles: {str(ex)}"
        )


# ============================================================================
# Error Handler
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Interner Serverfehler", "status_code": 500}
    )
