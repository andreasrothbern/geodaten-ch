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
from fastapi.responses import JSONResponse, Response
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
            coordinates={
                "lv95_e": geo.coordinates.lv95_e,
                "lv95_n": geo.coordinates.lv95_n,
            },
        )

        # 4b. Auto-Refresh: Höhen aktualisieren wenn unvollständig
        if scaffolding_data.get("needs_height_refresh"):
            try:
                from app.services.height_fetcher import fetch_height_for_coordinates
                # Höhen von swissBUILDINGS3D abrufen (asynchron im Hintergrund)
                egid_to_refresh = building.egid if building else geometry.egid
                refresh_result = await fetch_height_for_coordinates(
                    e=geo.coordinates.lv95_e,
                    n=geo.coordinates.lv95_n,
                    egid=egid_to_refresh
                )
                # Bei Erfolg: Daten neu berechnen
                if refresh_result.get("success"):
                    scaffolding_data = calculate_scaffolding_data(
                        geometry=geometry,
                        floors=building.floors if building else None,
                        building_category_code=building.building_category_code if building else None,
                        manual_height=height,
                        coordinates={
                            "lv95_e": geo.coordinates.lv95_e,
                            "lv95_n": geo.coordinates.lv95_n,
                        },
                    )
                    scaffolding_data["height_refreshed"] = True
            except Exception as refresh_error:
                # Fehler beim Refresh ignorieren - vorhandene Daten verwenden
                print(f"Height refresh failed: {refresh_error}")
                scaffolding_data["height_refresh_error"] = str(refresh_error)

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


@app.get("/api/v1/heights/{egid}",
         tags=["Höhendaten"])
async def get_height_for_egid(egid: int):
    """
    Gebäudehöhe für eine EGID aus der Datenbank abrufen.

    **Hinweis:** Diese Route muss nach den spezifischen Routes definiert sein,
    da {egid} sonst Pfade wie "3d-tiles" matchen würde.
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


# ============================================================================
# Layher Materialkatalog
# ============================================================================

@app.get("/api/v1/catalog/systems",
         tags=["Materialkatalog"])
async def get_scaffold_systems():
    """
    Alle verfügbaren Gerüstsysteme abrufen.

    Liefert Layher Blitz 70, Allround und weitere Systeme.
    """
    try:
        from app.services.layher_catalog import get_catalog_service
        service = get_catalog_service()
        return service.get_systems()
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Materialkatalog nicht verfügbar")


@app.get("/api/v1/catalog/systems/{system_id}",
         tags=["Materialkatalog"])
async def get_scaffold_system(system_id: str):
    """
    Details zu einem Gerüstsystem abrufen.

    Inkl. verfügbare Feldlängen und Rahmenhöhen.

    **Beispiel:** `/api/v1/catalog/systems/blitz70`
    """
    try:
        from app.services.layher_catalog import get_catalog_service
        service = get_catalog_service()
        system = service.get_system(system_id)
        if not system:
            raise HTTPException(status_code=404, detail=f"System '{system_id}' nicht gefunden")
        return system
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Materialkatalog nicht verfügbar")


@app.get("/api/v1/catalog/materials/{system_id}",
         tags=["Materialkatalog"])
async def get_materials(
    system_id: str,
    category: Optional[str] = Query(None, description="Kategorie: frame, ledger, deck, diagonal, base, anchor")
):
    """
    Materialien für ein Gerüstsystem abrufen.

    Optional nach Kategorie filtern.

    **Beispiel:** `/api/v1/catalog/materials/blitz70?category=frame`
    """
    try:
        from app.services.layher_catalog import get_catalog_service
        service = get_catalog_service()
        return service.get_materials(system_id, category)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Materialkatalog nicht verfügbar")


@app.get("/api/v1/catalog/load-classes",
         tags=["Materialkatalog"])
async def get_load_classes():
    """
    Lastklassen nach EN 12811 abrufen.

    Klasse 1-6 mit Nutzlast und typischer Anwendung.
    """
    try:
        from app.services.layher_catalog import get_catalog_service
        service = get_catalog_service()
        return service.get_load_classes()
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Materialkatalog nicht verfügbar")


@app.get("/api/v1/catalog/estimate",
         tags=["Materialkatalog"])
async def estimate_material_quantities(
    system_id: str = Query("blitz70", description="Gerüstsystem: blitz70 oder allround"),
    area_m2: float = Query(..., description="Gerüstfläche in m²")
):
    """
    Materialmenge basierend auf Gerüstfläche schätzen.

    Verwendet Richtwerte pro 100m² Gerüstfläche.

    **Beispiel:** `/api/v1/catalog/estimate?system_id=blitz70&area_m2=460`
    """
    try:
        from app.services.layher_catalog import get_catalog_service
        service = get_catalog_service()

        estimates = service.estimate_material_quantities(system_id, area_m2)

        # Gesamtgewicht berechnen
        total_weight = sum(e["total_weight_kg"] or 0 for e in estimates)
        total_pieces = sum(e["quantity_typical"] for e in estimates)

        return {
            "system_id": system_id,
            "scaffold_area_m2": area_m2,
            "materials": estimates,
            "summary": {
                "total_pieces": total_pieces,
                "total_weight_kg": round(total_weight, 1),
                "total_weight_tons": round(total_weight / 1000, 2),
                "weight_per_m2_kg": round(total_weight / area_m2, 1) if area_m2 > 0 else 0
            }
        }
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Materialkatalog nicht verfügbar")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/catalog/field-layout",
         tags=["Materialkatalog"])
async def calculate_field_layout(
    system_id: str = Query("blitz70", description="Gerüstsystem"),
    facade_length: float = Query(..., description="Fassadenlänge in Metern")
):
    """
    Optimale Feldaufteilung für eine Fassadenlänge berechnen.

    **Beispiel:** `/api/v1/catalog/field-layout?facade_length=12.5`
    """
    try:
        from app.services.layher_catalog import get_catalog_service
        service = get_catalog_service()
        return service.calculate_field_layout(system_id, facade_length)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Materialkatalog nicht verfügbar")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/catalog/frames-for-height",
         tags=["Materialkatalog"])
async def calculate_frames_for_height(
    system_id: str = Query("blitz70", description="Gerüstsystem"),
    height: float = Query(..., description="Zielhöhe in Metern")
):
    """
    Optimale Rahmenkombination für eine Zielhöhe berechnen.

    **Beispiel:** `/api/v1/catalog/frames-for-height?height=7.5`
    """
    try:
        from app.services.layher_catalog import get_catalog_service
        service = get_catalog_service()
        frames = service.calculate_frames_for_height(system_id, height)

        # Gesamtgewicht
        total_weight = sum((f["weight_kg"] or 0) * f["quantity"] for f in frames)
        total_height = sum(f["height_m"] * f["quantity"] for f in frames)

        return {
            "system_id": system_id,
            "target_height_m": height,
            "frames": frames,
            "summary": {
                "total_height_m": round(total_height, 2),
                "total_weight_kg": round(total_weight, 1),
                "frame_count": sum(f["quantity"] for f in frames)
            }
        }
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Materialkatalog nicht verfügbar")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# NPK 114 Ausmass-Berechnung
# ============================================================================

@app.get("/api/v1/ausmass/gebaeude",
         tags=["NPK 114 Ausmass"])
async def berechne_ausmass_gebaeude(
    laenge_m: float = Query(..., description="Gebäudelänge (Traufseite bei Satteldach)"),
    breite_m: float = Query(..., description="Gebäudebreite (Giebelseite bei Satteldach)"),
    hoehe_traufe_m: float = Query(..., description="Traufhöhe in Metern"),
    hoehe_first_m: Optional[float] = Query(None, description="Firsthöhe (bei Satteldach/Walmdach)"),
    dachform: str = Query("flach", description="Dachform: flach, satteldach, walmdach"),
    breitenklasse: str = Query("W09", description="Breitenklasse: W06, W09, W12")
):
    """
    NPK 114 Ausmass für ein rechteckiges Gebäude berechnen.

    Berechnet Gerüstflächen nach Schweizer Norm NPK 114 D/2012.

    **Zuschläge:**
    - Fassadenabstand: 0.30 m
    - Gerüstbreite: 0.70 m (W09) / 1.00 m (W12)
    - Höhenzuschlag: +1.00 m
    - Eckzuschlag: LS × HA pro Ecke

    **Beispiel:** `?laenge_m=12&breite_m=10&hoehe_traufe_m=6.5&hoehe_first_m=10&dachform=satteldach`
    """
    try:
        from app.services.npk114_calculator import NPK114Calculator, WidthClass

        wk = WidthClass[breitenklasse]
        calc = NPK114Calculator(breitenklasse=wk)

        result = calc.berechne_rechteckiges_gebaeude(
            laenge_m=laenge_m,
            breite_m=breite_m,
            hoehe_traufe_m=hoehe_traufe_m,
            hoehe_first_m=hoehe_first_m,
            dachform=dachform
        )

        return {
            "eingabe": {
                "laenge_m": laenge_m,
                "breite_m": breite_m,
                "hoehe_traufe_m": hoehe_traufe_m,
                "hoehe_first_m": hoehe_first_m,
                "dachform": dachform,
                "breitenklasse": breitenklasse
            },
            "norm": "NPK 114 D/2012",
            **result.to_dict()
        }
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Ungültige Breitenklasse: {breitenklasse}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ausmass/fassade",
         tags=["NPK 114 Ausmass"])
async def berechne_ausmass_fassade(
    laenge_m: float = Query(..., description="Fassadenlänge in Metern"),
    hoehe_m: float = Query(..., description="Fassadenhöhe (Traufe) in Metern"),
    hoehe_first_m: Optional[float] = Query(None, description="Firsthöhe (bei Giebel)"),
    ist_giebel: bool = Query(False, description="Ist Giebelseite?"),
    breitenklasse: str = Query("W09", description="Breitenklasse: W06, W09, W12")
):
    """
    NPK 114 Ausmass für eine einzelne Fassade berechnen.

    **Formeln:**
    - Ausmasslänge: LA = LS + L + LS (min. 2.5 m)
    - Ausmasshöhe: HA = H + 1.0 m (min. 4.0 m)
    - Giebel: H_mittel = H_Traufe + (H_Giebel × 0.5)

    **Beispiel:** `?laenge_m=12&hoehe_m=6.5`
    """
    try:
        from app.services.npk114_calculator import NPK114Calculator, WidthClass

        wk = WidthClass[breitenklasse]
        calc = NPK114Calculator(breitenklasse=wk)

        fassade = calc.berechne_fassade(
            name="Fassade",
            laenge_m=laenge_m,
            hoehe_traufe_m=hoehe_m,
            hoehe_first_m=hoehe_first_m,
            ist_giebel=ist_giebel
        )

        return {
            "norm": "NPK 114 D/2012",
            **fassade.to_dict()
        }
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Ungültige Breitenklasse: {breitenklasse}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ausmass/von-adresse",
         tags=["NPK 114 Ausmass"])
async def berechne_ausmass_von_adresse(
    address: str = Query(..., min_length=5, description="Adresse"),
    hoehe_traufe_m: Optional[float] = Query(None, description="Manuelle Traufhöhe"),
    hoehe_first_m: Optional[float] = Query(None, description="Manuelle Firsthöhe"),
    dachform: str = Query("flach", description="Dachform: flach, satteldach, walmdach"),
    breitenklasse: str = Query("W09", description="Breitenklasse: W06, W09, W12")
):
    """
    NPK 114 Ausmass aus Geodaten berechnen.

    Kombiniert Gebäudedaten von geodaten API mit NPK 114 Berechnung.

    **Workflow:**
    1. Adresse geokodieren
    2. Gebäudedaten (Fläche, Geschosse) abrufen
    3. Dimensionen aus Fläche schätzen
    4. Höhe aus Geschossen oder manuell
    5. NPK 114 Ausmass berechnen

    **Beispiel:** `?address=Bundesplatz 3, 3011 Bern&dachform=satteldach`
    """
    try:
        import math
        from app.services.npk114_calculator import NPK114Calculator, WidthClass

        # 1. Adresse geokodieren
        geo = await swisstopo.geocode(address)
        if not geo:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")

        # 2. Gebäude suchen
        buildings = await swisstopo.identify_buildings(
            geo.coordinates.lv95_e,
            geo.coordinates.lv95_n,
            tolerance=15
        )
        building = buildings[0] if buildings else None

        # 3. Gebäudegeometrie abrufen (für Umfang)
        geometry = await geodienste.get_building_geometry(
            x=geo.coordinates.lv95_e,
            y=geo.coordinates.lv95_n,
            tolerance=50,
            egid=building.egid if building else None
        )

        # 4. Dimensionen bestimmen
        if geometry and geometry.sides:
            # Aus Geometrie: Längste zwei Seiten
            side_lengths = sorted([s['length_m'] for s in geometry.sides], reverse=True)
            laenge = side_lengths[0] if side_lengths else 10.0
            breite = side_lengths[1] if len(side_lengths) > 1 else laenge
        elif building and building.area_m2:
            # Aus Fläche: Quadratisch approximieren
            seite = math.sqrt(building.area_m2)
            laenge = breite = seite
        else:
            laenge = breite = 10.0

        # 5. Höhe bestimmen
        if hoehe_traufe_m is None:
            if building and building.floors:
                hoehe_traufe_m = building.floors * 2.8  # 2.8m pro Geschoss
            else:
                hoehe_traufe_m = 8.0  # Default EFH

        # 6. NPK 114 berechnen
        wk = WidthClass[breitenklasse]
        calc = NPK114Calculator(breitenklasse=wk)

        result = calc.berechne_rechteckiges_gebaeude(
            laenge_m=round(laenge, 1),
            breite_m=round(breite, 1),
            hoehe_traufe_m=hoehe_traufe_m,
            hoehe_first_m=hoehe_first_m,
            dachform=dachform
        )

        return {
            "adresse": {
                "eingabe": address,
                "gefunden": geo.matched_address,
                "koordinaten": {
                    "lv95_e": geo.coordinates.lv95_e,
                    "lv95_n": geo.coordinates.lv95_n
                }
            },
            "gebaeude": {
                "egid": building.egid if building else None,
                "geschosse": building.floors if building else None,
                "flaeche_m2": building.area_m2 if building else None,
                "laenge_geschaetzt_m": round(laenge, 1),
                "breite_geschaetzt_m": round(breite, 1),
                "quelle_dimensionen": "geometrie" if (geometry and geometry.sides) else "flaeche"
            },
            "eingabe": {
                "hoehe_traufe_m": hoehe_traufe_m,
                "hoehe_first_m": hoehe_first_m,
                "dachform": dachform,
                "breitenklasse": breitenklasse
            },
            "norm": "NPK 114 D/2012",
            **result.to_dict()
        }

    except KeyError:
        raise HTTPException(status_code=400, detail=f"Ungültige Breitenklasse: {breitenklasse}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ausmass/komplett",
         tags=["NPK 114 Ausmass"])
async def berechne_komplettes_ausmass(
    address: str = Query(..., min_length=5, description="Adresse"),
    system_id: str = Query("blitz70", description="Gerüstsystem: blitz70, allround"),
    hoehe_traufe_m: Optional[float] = Query(None, description="Manuelle Traufhöhe"),
    hoehe_first_m: Optional[float] = Query(None, description="Manuelle Firsthöhe"),
    dachform: str = Query("flach", description="Dachform: flach, satteldach, walmdach"),
    breitenklasse: str = Query("W09", description="Breitenklasse: W06, W09, W12")
):
    """
    Komplettes Gerüst-Ausmass inkl. Materialliste.

    Kombiniert NPK 114 Ausmass mit Materialschätzung.

    **Liefert:**
    - NPK 114 Ausmass aller Fassaden
    - Materialliste mit Mengen
    - Gesamtgewicht
    - Feldaufteilung

    **Beispiel:** `?address=Bundesplatz 3, 3011 Bern&system_id=blitz70&dachform=satteldach`
    """
    try:
        import math
        from app.services.npk114_calculator import NPK114Calculator, WidthClass
        from app.services.layher_catalog import get_catalog_service

        # 1. Adresse und Gebäude
        geo = await swisstopo.geocode(address)
        if not geo:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")

        buildings = await swisstopo.identify_buildings(
            geo.coordinates.lv95_e,
            geo.coordinates.lv95_n,
            tolerance=15
        )
        building = buildings[0] if buildings else None

        geometry = await geodienste.get_building_geometry(
            x=geo.coordinates.lv95_e,
            y=geo.coordinates.lv95_n,
            tolerance=50,
            egid=building.egid if building else None
        )

        # 2. Dimensionen
        if geometry and geometry.sides:
            side_lengths = sorted([s['length_m'] for s in geometry.sides], reverse=True)
            laenge = side_lengths[0] if side_lengths else 10.0
            breite = side_lengths[1] if len(side_lengths) > 1 else laenge
        elif building and building.area_m2:
            seite = math.sqrt(building.area_m2)
            laenge = breite = seite
        else:
            laenge = breite = 10.0

        # 3. Höhe
        if hoehe_traufe_m is None:
            if building and building.floors:
                hoehe_traufe_m = building.floors * 2.8
            else:
                hoehe_traufe_m = 8.0

        # 4. NPK 114 Ausmass
        wk = WidthClass[breitenklasse]
        calc = NPK114Calculator(breitenklasse=wk)
        ausmass = calc.berechne_rechteckiges_gebaeude(
            laenge_m=round(laenge, 1),
            breite_m=round(breite, 1),
            hoehe_traufe_m=hoehe_traufe_m,
            hoehe_first_m=hoehe_first_m,
            dachform=dachform
        )

        # 5. Material schätzen
        catalog = get_catalog_service()
        total_flaeche = ausmass.total_ausmass_m2
        material_schaetzung = catalog.estimate_material_quantities(system_id, total_flaeche)

        total_weight = sum(e["total_weight_kg"] or 0 for e in material_schaetzung)
        total_pieces = sum(e["quantity_typical"] for e in material_schaetzung)

        # 6. Feldaufteilung für längste Fassade
        feld_layout = catalog.calculate_field_layout(system_id, laenge)

        return {
            "adresse": {
                "eingabe": address,
                "gefunden": geo.matched_address
            },
            "gebaeude": {
                "egid": building.egid if building else None,
                "laenge_m": round(laenge, 1),
                "breite_m": round(breite, 1),
                "hoehe_traufe_m": hoehe_traufe_m,
                "hoehe_first_m": hoehe_first_m,
                "dachform": dachform
            },
            "ausmass": ausmass.to_dict(),
            "material": {
                "system": system_id,
                "liste": material_schaetzung,
                "zusammenfassung": {
                    "total_stueck": total_pieces,
                    "total_gewicht_kg": round(total_weight, 1),
                    "total_gewicht_tonnen": round(total_weight / 1000, 2),
                    "gewicht_pro_m2_kg": round(total_weight / total_flaeche, 1) if total_flaeche > 0 else 0
                }
            },
            "feldaufteilung": feld_layout
        }

    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Materialkatalog nicht verfügbar")
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Ungültiger Parameter: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SVG Visualisierung
# ============================================================================

@app.get("/api/v1/visualize/cross-section",
         tags=["Visualisierung"],
         response_class=Response)
async def visualize_cross_section(
    address: str,
    width: int = 700,
    height: int = 480
):
    """
    Generiert SVG-Schnittansicht für ein Gebäude.

    - **address**: Schweizer Adresse
    - **width**: SVG-Breite in Pixel (default: 700)
    - **height**: SVG-Höhe in Pixel (default: 480)

    Returns: SVG-Datei
    """
    from app.services.svg_generator import get_svg_generator, BuildingData

    try:
        # Gebäudedaten abrufen
        geo = await swisstopo.geocode(address)
        if not geo:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")

        buildings = await swisstopo.identify_buildings(
            geo.coordinates.lv95_e, geo.coordinates.lv95_n, tolerance=15
        )
        building = buildings[0] if buildings else None

        # Geometrie abrufen
        geometry = await geodienste.get_building_geometry(
            x=geo.coordinates.lv95_e,
            y=geo.coordinates.lv95_n,
            tolerance=50,
            egid=building.egid if building else None
        )

        # Dimensionen bestimmen
        if geometry and geometry.sides:
            side_lengths = sorted([s['length_m'] for s in geometry.sides], reverse=True)
            length_m = side_lengths[0]
            width_m = side_lengths[1] if len(side_lengths) > 1 else length_m
        elif building and building.area_m2:
            side = math.sqrt(building.area_m2)
            length_m = width_m = round(side, 1)
        else:
            length_m = width_m = 10.0

        # Höhe bestimmen
        eave_height_m = building.floors * 2.8 if building and building.floors else 8.0

        # Gemessene Höhe aus DB
        measured_height = None
        if building and building.egid:
            from app.services.height_db import get_building_height
            measured_height = get_building_height(building.egid)

        # BuildingData erstellen
        building_data = BuildingData(
            address=geo.matched_address,
            egid=building.egid if building else None,
            length_m=round(length_m, 1),
            width_m=round(width_m, 1),
            eave_height_m=round(eave_height_m, 1),
            ridge_height_m=round(eave_height_m + 3.5, 1) if building else None,  # Annahme Satteldach
            floors=building.floors if building else 3,
            roof_type="gable",
            area_m2=building.area_m2 if building else None,
            measured_height_m=measured_height
        )

        # SVG generieren
        generator = get_svg_generator()
        svg = generator.generate_cross_section(building_data, width, height)

        return Response(content=svg, media_type="image/svg+xml")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/visualize/elevation",
         tags=["Visualisierung"],
         response_class=Response)
async def visualize_elevation(
    address: str,
    width: int = 700,
    height: int = 480
):
    """
    Generiert SVG-Fassadenansicht für ein Gebäude.

    - **address**: Schweizer Adresse
    - **width**: SVG-Breite in Pixel (default: 700)
    - **height**: SVG-Höhe in Pixel (default: 480)

    Returns: SVG-Datei
    """
    from app.services.svg_generator import get_svg_generator, BuildingData

    try:
        # Gebäudedaten abrufen (gleiche Logik wie cross-section)
        geo = await swisstopo.geocode(address)
        if not geo:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")

        buildings = await swisstopo.identify_buildings(
            geo.coordinates.lv95_e, geo.coordinates.lv95_n, tolerance=15
        )
        building = buildings[0] if buildings else None

        geometry = await geodienste.get_building_geometry(
            x=geo.coordinates.lv95_e,
            y=geo.coordinates.lv95_n,
            tolerance=50,
            egid=building.egid if building else None
        )

        if geometry and geometry.sides:
            side_lengths = sorted([s['length_m'] for s in geometry.sides], reverse=True)
            length_m = side_lengths[0]
            width_m = side_lengths[1] if len(side_lengths) > 1 else length_m
        elif building and building.area_m2:
            side = math.sqrt(building.area_m2)
            length_m = width_m = round(side, 1)
        else:
            length_m = width_m = 10.0

        eave_height_m = building.floors * 2.8 if building and building.floors else 8.0

        building_data = BuildingData(
            address=geo.matched_address,
            egid=building.egid if building else None,
            length_m=round(length_m, 1),
            width_m=round(width_m, 1),
            eave_height_m=round(eave_height_m, 1),
            ridge_height_m=round(eave_height_m + 3.5, 1) if building else None,
            floors=building.floors if building else 3,
            roof_type="gable",
            area_m2=building.area_m2 if building else None,
        )

        generator = get_svg_generator()
        svg = generator.generate_elevation(building_data, width, height)

        return Response(content=svg, media_type="image/svg+xml")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/visualize/floor-plan",
         tags=["Visualisierung"],
         response_class=Response)
async def visualize_floor_plan(
    address: str,
    width: int = 600,
    height: int = 500
):
    """
    Generiert SVG-Grundriss für ein Gebäude.

    - **address**: Schweizer Adresse
    - **width**: SVG-Breite in Pixel (default: 600)
    - **height**: SVG-Höhe in Pixel (default: 500)

    Returns: SVG-Datei
    """
    from app.services.svg_generator import get_svg_generator, BuildingData

    try:
        geo = await swisstopo.geocode(address)
        if not geo:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")

        buildings = await swisstopo.identify_buildings(
            geo.coordinates.lv95_e, geo.coordinates.lv95_n, tolerance=15
        )
        building = buildings[0] if buildings else None

        geometry = await geodienste.get_building_geometry(
            x=geo.coordinates.lv95_e,
            y=geo.coordinates.lv95_n,
            tolerance=50,
            egid=building.egid if building else None
        )

        if geometry and geometry.sides:
            side_lengths = sorted([s['length_m'] for s in geometry.sides], reverse=True)
            length_m = side_lengths[0]
            width_m = side_lengths[1] if len(side_lengths) > 1 else length_m
        elif building and building.area_m2:
            side = math.sqrt(building.area_m2)
            length_m = width_m = round(side, 1)
        else:
            length_m = width_m = 10.0

        eave_height_m = building.floors * 2.8 if building and building.floors else 8.0

        building_data = BuildingData(
            address=geo.matched_address,
            egid=building.egid if building else None,
            length_m=round(length_m, 1),
            width_m=round(width_m, 1),
            eave_height_m=round(eave_height_m, 1),
            floors=building.floors if building else 3,
            roof_type="gable",
            area_m2=building.area_m2 if building else None,
        )

        generator = get_svg_generator()
        svg = generator.generate_floor_plan(building_data, width, height)

        return Response(content=svg, media_type="image/svg+xml")

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
