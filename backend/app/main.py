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
from app.models.schemas import (
    AddressSearchResult,
    BuildingInfo,
    GeocodingResult,
    HealthResponse,
    ErrorResponse
)

# Services initialisieren
swisstopo = SwisstopoService()
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
