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
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

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


@app.get("/debug/libraries", tags=["System"])
async def debug_libraries():
    """Debug: Zeigt verfügbare Bibliotheken für Dokumentgenerierung"""
    result = {
        "docx": False,
        "cairosvg": False,
        "svglib": False,
        "reportlab": False,
        "pillow": False,
    }

    try:
        import docx
        result["docx"] = True
    except ImportError:
        pass

    try:
        import cairosvg
        result["cairosvg"] = True
    except ImportError:
        pass

    try:
        from svglib.svglib import svg2rlg
        result["svglib"] = True
    except ImportError:
        pass

    try:
        from reportlab.graphics import renderPM
        result["reportlab"] = True
    except ImportError:
        pass

    try:
        from PIL import Image
        result["pillow"] = True
    except ImportError:
        pass

    return result


# ============================================================================
# Cache Management
# ============================================================================

@app.get("/api/v1/cache/stats", tags=["System"])
async def get_cache_stats():
    """Zeigt Cache-Statistiken für Daten"""
    from app.services.data_cache import get_cache_stats as get_data_cache_stats

    return {
        "data_cache": get_data_cache_stats()
    }


@app.delete("/api/v1/cache/svg", tags=["System"])
async def clear_svg_cache():
    """SVG-Cache wurde entfernt (einfacher Generator ohne Cache)"""
    return {
        "success": True,
        "deleted_entries": 0,
        "message": "SVG cache not used (simple generator without caching)"
    }


@app.delete("/api/v1/cache/data", tags=["System"])
async def clear_data_cache():
    """Löscht den Daten-Cache (Gebäude, Ausmass)"""
    from app.services.data_cache import clear_cache

    deleted = clear_cache()

    return {
        "success": True,
        "deleted_entries": deleted,
        "message": f"Data cache cleared. {deleted} entries deleted."
    }


@app.delete("/api/v1/cache/all", tags=["System"])
async def clear_all_caches():
    """Löscht alle Caches (Daten)"""
    from app.services.data_cache import clear_cache

    data_deleted = clear_cache()

    return {
        "success": True,
        "data_deleted": data_deleted,
        "message": f"Data cache cleared: {data_deleted} entries"
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
# Complete Data Endpoint (All data at once, cached)
# ============================================================================

@app.get("/api/v1/data/complete",
         tags=["Daten"])
async def get_complete_data(
    address: str = Query(..., min_length=5, description="Adresse"),
    system_id: str = Query("blitz70", description="Gerüstsystem"),
    dachform: str = Query("satteldach", description="Dachform"),
    breitenklasse: str = Query("W09", description="Breitenklasse"),
    force_refresh: bool = Query(False, description="Cache ignorieren")
):
    """
    Alle Daten für eine Adresse auf einmal abrufen.

    Liefert gecached:
    - Gebäudedaten (GWR)
    - Geometrie und Dimensionen
    - Scaffolding-Daten
    - NPK 114 Ausmass
    - Materialliste

    **Verwende diesen Endpoint für effizientes Laden.**
    Ein Aufruf, alle Daten - kein Neuladen bei Tab-Wechsel.
    """
    import math
    from app.services.data_cache import get_cached_data, set_cached_data, CachedAddressData, fetch_and_cache_complete_data
    from app.services.npk114_calculator import NPK114Calculator, WidthClass
    from app.services.layher_catalog import get_catalog_service
    import time

    try:
        # Check cache first
        cached = get_cached_data(address)
        if cached and not force_refresh:
            # Build complete response from cache
            pass
        else:
            # Fetch and cache basic data
            cached = await fetch_and_cache_complete_data(
                address, swisstopo, geodienste, force_refresh=force_refresh
            )

        # Now compute ausmass and material (these depend on user inputs)
        laenge = cached.length_m
        breite = cached.width_m
        hoehe_traufe = cached.eave_height_m
        hoehe_first = cached.ridge_height_m

        # NPK 114 Ausmass
        wk = WidthClass[breitenklasse]
        calc = NPK114Calculator(breitenklasse=wk)
        ausmass = calc.berechne_rechteckiges_gebaeude(
            laenge_m=laenge,
            breite_m=breite,
            hoehe_traufe_m=hoehe_traufe,
            hoehe_first_m=hoehe_first,
            dachform=dachform
        )

        # Material
        catalog = get_catalog_service()
        total_flaeche = ausmass.total_ausmass_m2
        material_liste = catalog.estimate_material_quantities(system_id, total_flaeche)
        feldaufteilung = catalog.calculate_field_layout(system_id, laenge)

        # Material summary
        total_stueck = sum(m['quantity_typical'] for m in material_liste)
        total_gewicht = sum(m['total_weight_kg'] or 0 for m in material_liste)

        # Build complete response
        return {
            "address": {
                "input": address,
                "matched": cached.address_matched,
                "coordinates": {
                    "lv95_e": cached.lv95_e,
                    "lv95_n": cached.lv95_n
                }
            },
            "building": {
                "egid": cached.egid,
                "floors": cached.floors,
                "area_m2": cached.area_m2,
                "category": cached.building_category,
                "construction_year": cached.construction_year
            },
            "dimensions": {
                "length_m": laenge,
                "width_m": breite,
                "perimeter_m": cached.perimeter_m,
                "eave_height_m": hoehe_traufe,
                "ridge_height_m": hoehe_first,
                "traufhoehe_m": cached.traufhoehe_m,
                "firsthoehe_m": cached.firsthoehe_m,
                "gebaeudehoehe_m": cached.gebaeudehoehe_m
            },
            "geometry": {
                "sides": cached.sides,
                "polygon_coordinates": cached.polygon_coordinates
            },
            "ausmass": ausmass.to_dict(),
            "material": {
                "system": system_id,
                "liste": material_liste,
                "zusammenfassung": {
                    "total_stueck": total_stueck,
                    "total_gewicht_kg": total_gewicht,
                    "total_gewicht_tonnen": round(total_gewicht / 1000, 2),
                    "gewicht_pro_m2_kg": round(total_gewicht / total_flaeche, 1) if total_flaeche > 0 else 0
                }
            },
            "feldaufteilung": feldaufteilung,
            "viewer_3d_url": cached.viewer_3d_url,
            "parameters": {
                "dachform": dachform,
                "breitenklasse": breitenklasse,
                "system_id": system_id
            },
            "cached": not force_refresh,
            "cached_at": cached.cached_at
        }

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Ungültiger Parameter: {e}")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Gerüstbau-Daten (Gebäudegeometrie)
# ============================================================================

@app.get("/api/v1/scaffolding",
         tags=["Gerüstbau"])
async def get_scaffolding_data(
    address: str = Query(..., min_length=5, description="Adresse"),
    egid: Optional[int] = Query(None, description="EGID (falls bekannt)"),
    height: Optional[float] = Query(None, description="Manuelle Gebäudehöhe in Metern (deprecated, use traufhoehe/firsthoehe)"),
    traufhoehe: Optional[float] = Query(None, description="Manuelle Traufhöhe in Metern"),
    firsthoehe: Optional[float] = Query(None, description="Manuelle Firsthöhe in Metern"),
    refresh: bool = Query(False, description="Cache ignorieren und neu laden"),
    work_type: str = Query("dacharbeiten", description="Arbeitstyp: dacharbeiten (First+1m) oder fassadenarbeiten (Traufe)"),
    scaffold_type: str = Query("arbeitsgeruest", description="Gerüstart: arbeitsgeruest, schutzgeruest, fanggeruest")
):
    """
    Gebäudegeometrie und Gerüstbau-relevante Daten abrufen.

    Liefert:
    - Exakten Grundriss (Polygon mit allen Eckpunkten)
    - Seitenlängen jeder Fassade
    - Gesamtumfang (für Gerüstmeter)
    - Geschätzte Gebäudehöhe
    - Geschätzte Gerüstfläche

    **Arbeitstyp:**
    - `dacharbeiten`: Gerüsthöhe = Firsthöhe + 1.0m (SUVA Vorschrift)
    - `fassadenarbeiten`: Gerüsthöhe = Traufhöhe (Unterdach)

    **Gerüstart:**
    - `arbeitsgeruest`: Standard für Fassadenarbeiten (NPK 114.1xx)
    - `schutzgeruest`: Absturzsicherung bei Dacharbeiten (NPK 114.2xx)
    - `fanggeruest`: Auffangen von Material/Personen (NPK 114.3xx)

    **Beispiel:** `?address=Bundesplatz 3, 3011 Bern&work_type=dacharbeiten`
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
        effective_egid = building.egid if building else None
        scaffolding_data = calculate_scaffolding_data(
            geometry=geometry,
            floors=building.floors if building else None,
            building_category_code=building.building_category_code if building else None,
            manual_height=height,
            coordinates={
                "lv95_e": geo.coordinates.lv95_e,
                "lv95_n": geo.coordinates.lv95_n,
                "wgs84_lat": geo.coordinates.wgs84_lat,
                "wgs84_lon": geo.coordinates.wgs84_lon,
            },
            egid=effective_egid,
            manual_traufhoehe=traufhoehe,
            manual_firsthoehe=firsthoehe,
        )
        dims = scaffolding_data.get("dimensions", {})

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
                            "wgs84_lat": geo.coordinates.wgs84_lat,
                            "wgs84_lon": geo.coordinates.wgs84_lon,
                        },
                        egid=building.egid if building else None,
                        manual_traufhoehe=traufhoehe,
                        manual_firsthoehe=firsthoehe,
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
            # Gerüstkonfiguration
            "configuration": {
                "work_type": work_type,
                "scaffold_type": scaffold_type,
            },
            **scaffolding_data,
        }

        cache.set(cache_key, result, ttl_hours=24)

        # Also populate shared cache for document generation
        try:
            from app.services.data_cache import CachedAddressData, set_cached_data
            import time

            # Get dimensions from scaffolding data
            dims = scaffolding_data.get("dimensions", {})
            bounding = scaffolding_data.get("building", {}).get("bounding_box", {})

            shared_data = CachedAddressData(
                address_input=address,
                address_matched=geo.matched_address,
                cached_at=time.time(),
                lv95_e=geo.coordinates.lv95_e,
                lv95_n=geo.coordinates.lv95_n,
                egid=building.egid if building else (geometry.egid if geometry else None),
                floors=building.floors if building else None,
                area_m2=building.area_m2 if building else None,
                building_category=building.building_category if building else None,
                construction_year=building.construction_year if building else None,
                length_m=bounding.get("depth_m", 10.0),
                width_m=bounding.get("width_m", 10.0),
                eave_height_m=dims.get("traufhoehe_m") or dims.get("estimated_height_m", 8.0),
                ridge_height_m=dims.get("firsthoehe_m"),
                perimeter_m=dims.get("perimeter_m", 40.0),
                traufhoehe_m=dims.get("traufhoehe_m"),
                firsthoehe_m=dims.get("firsthoehe_m"),
                gebaeudehoehe_m=dims.get("gebaeudehoehe_m"),
                sides=scaffolding_data.get("sides", []),
                polygon_coordinates=scaffolding_data.get("polygon", {}).get("coordinates", []),
                viewer_3d_url=result.get("viewer_3d_url")
            )
            set_cached_data(shared_data)
        except Exception as cache_err:
            print(f"Failed to populate shared cache: {cache_err}")

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
            egid=building.egid,
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
        from app.services.npk114_calculator import NPK114Calculator, WidthClass
        from app.services.layher_catalog import get_catalog_service
        from app.services.data_cache import get_cached_data, fetch_and_cache_complete_data

        # Try to use cached data first
        cached = get_cached_data(address)
        if not cached:
            # Fetch and cache if not available
            cached = await fetch_and_cache_complete_data(address, swisstopo, geodienste)

        # Use cached dimensions
        laenge = cached.length_m
        breite = cached.width_m

        # Use provided height or cached
        if hoehe_traufe_m is None:
            hoehe_traufe_m = cached.eave_height_m
        if hoehe_first_m is None:
            hoehe_first_m = cached.ridge_height_m

        # Auto-detect roof type from heights if using default
        if dachform == "flach" and hoehe_first_m and hoehe_first_m > hoehe_traufe_m:
            dachform = "satteldach"

        # NPK 114 Ausmass
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
                "gefunden": cached.address_matched
            },
            "gebaeude": {
                "egid": cached.egid,
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
    height: int = 480,
    traufhoehe: Optional[float] = Query(None, description="Manuelle Traufhöhe in Metern"),
    firsthoehe: Optional[float] = Query(None, description="Manuelle Firsthöhe in Metern")
):
    """
    Generiert SVG-Schnittansicht für ein Gebäude.

    - **address**: Schweizer Adresse
    - **width**: SVG-Breite in Pixel (default: 700)
    - **height**: SVG-Höhe in Pixel (default: 480)
    - **traufhoehe**: Manuelle Traufhöhe (überschreibt DB)
    - **firsthoehe**: Manuelle Firsthöhe (überschreibt DB)

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

        # Höhe bestimmen - Priorität: manuell > swissBUILDINGS3D > Geschosse
        eave_height_m = (building.floors or 3) * 2.8 if building else 8.0
        ridge_height_m = eave_height_m + 3.5  # Default für Satteldach

        # Gemessene Höhe aus swissBUILDINGS3D DB
        if building and building.egid:
            from app.services.height_db import get_building_heights_detailed
            heights = get_building_heights_detailed(building.egid)
            if heights:
                if heights.get("traufhoehe_m"):
                    eave_height_m = heights["traufhoehe_m"]
                if heights.get("firsthoehe_m"):
                    ridge_height_m = heights["firsthoehe_m"]
                measured_height_m = heights.get("gebaeudehoehe_m")
                if measured_height_m and not heights.get("traufhoehe_m") and not heights.get("firsthoehe_m"):
                    eave_height_m = measured_height_m * 0.85
                    ridge_height_m = measured_height_m

        # Manuelle Werte überschreiben DB-Werte
        if traufhoehe and traufhoehe > 0:
            eave_height_m = traufhoehe
        if firsthoehe and firsthoehe > 0:
            ridge_height_m = firsthoehe

        # Auto-detect roof type from heights
        roof_type = "flat" if (ridge_height_m is None or ridge_height_m <= eave_height_m) else "gable"

        # BuildingData erstellen
        building_data = BuildingData(
            address=geo.matched_address,
            egid=building.egid if building else None,
            length_m=round(length_m, 1),
            width_m=round(width_m, 1),
            eave_height_m=round(eave_height_m, 1),
            ridge_height_m=round(ridge_height_m, 1) if ridge_height_m else None,
            floors=building.floors if building else 3,
            roof_type=roof_type,
            area_m2=building.area_m2 if building else None,
        )

        # SVG generieren
        generator = get_svg_generator()
        svg = generator.generate_cross_section(building_data, width, height)

        if not svg:
            raise HTTPException(status_code=503, detail="SVG-Generierung fehlgeschlagen")

        return Response(content=svg, media_type="image/svg+xml")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Visualization error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Visualization error: {str(e)}")


@app.get("/api/v1/visualize/elevation",
         tags=["Visualisierung"],
         response_class=Response)
async def visualize_elevation(
    address: str,
    width: int = 700,
    height: int = 480,
    traufhoehe: Optional[float] = Query(None, description="Manuelle Traufhöhe in Metern"),
    firsthoehe: Optional[float] = Query(None, description="Manuelle Firsthöhe in Metern")
):
    """
    Generiert SVG-Fassadenansicht für ein Gebäude.

    - **address**: Schweizer Adresse
    - **width**: SVG-Breite in Pixel (default: 700)
    - **height**: SVG-Höhe in Pixel (default: 480)
    - **traufhoehe**: Manuelle Traufhöhe (überschreibt DB)
    - **firsthoehe**: Manuelle Firsthöhe (überschreibt DB)

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

        eave_height_m = (building.floors or 3) * 2.8 if building else 8.0
        ridge_height_m = eave_height_m + 3.5

        if building and building.egid:
            from app.services.height_db import get_building_heights_detailed
            heights = get_building_heights_detailed(building.egid)
            if heights:
                if heights.get("traufhoehe_m"):
                    eave_height_m = heights["traufhoehe_m"]
                if heights.get("firsthoehe_m"):
                    ridge_height_m = heights["firsthoehe_m"]
                gebaeudehoehe = heights.get("gebaeudehoehe_m")
                if gebaeudehoehe and not heights.get("traufhoehe_m") and not heights.get("firsthoehe_m"):
                    eave_height_m = gebaeudehoehe * 0.85
                    ridge_height_m = gebaeudehoehe

        # Manuelle Werte überschreiben DB-Werte
        if traufhoehe and traufhoehe > 0:
            eave_height_m = traufhoehe
        if firsthoehe and firsthoehe > 0:
            ridge_height_m = firsthoehe

        # Auto-detect roof type from heights
        roof_type = "flat" if (ridge_height_m is None or ridge_height_m <= eave_height_m) else "gable"

        building_data = BuildingData(
            address=geo.matched_address,
            egid=building.egid if building else None,
            length_m=round(length_m, 1),
            width_m=round(width_m, 1),
            eave_height_m=round(eave_height_m, 1),
            ridge_height_m=round(ridge_height_m, 1) if ridge_height_m else None,
            floors=building.floors if building else 3,
            roof_type=roof_type,
            area_m2=building.area_m2 if building else None,
        )

        generator = get_svg_generator()
        svg = generator.generate_elevation(building_data, width, height)

        if not svg:
            raise HTTPException(status_code=503, detail="SVG-Generierung fehlgeschlagen")

        return Response(content=svg, media_type="image/svg+xml")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FloorPlanRequest(BaseModel):
    """Request body für floor-plan mit vorberechneten Daten"""
    address: str
    sides: List[Dict[str, Any]]
    polygon_coordinates: List[List[float]]
    # Gebäudedaten für NPK-Anzeige
    eave_height_m: Optional[float] = None
    floors: Optional[int] = None
    area_m2: Optional[float] = None
    width: int = 600
    height: int = 500


@app.post("/api/v1/visualize/floor-plan",
         tags=["Visualisierung"],
         response_class=Response)
async def visualize_floor_plan_post(request: FloorPlanRequest):
    """
    Generiert SVG-Grundriss mit übergebenen Geometrie-Daten.

    Verwendet die gleichen sides/polygon Daten wie die Tabelle.
    """
    from app.services.svg_generator import get_svg_generator, BuildingData

    try:
        sides_data = request.sides
        polygon_coords = request.polygon_coordinates

        if not sides_data or not polygon_coords:
            raise HTTPException(status_code=400, detail="sides und polygon_coordinates erforderlich")

        # Dimensionen aus sides berechnen
        side_lengths = sorted([s['length_m'] for s in sides_data], reverse=True)
        length_m = side_lengths[0] if side_lengths else 10.0
        width_m = side_lengths[1] if len(side_lengths) > 1 else length_m

        building_data = BuildingData(
            address=request.address,
            egid=None,
            length_m=round(length_m, 1),
            width_m=round(width_m, 1),
            eave_height_m=request.eave_height_m or 8.0,
            floors=request.floors or 3,
            roof_type="flat",
            area_m2=request.area_m2,
            polygon_coordinates=polygon_coords,
            sides=sides_data,
        )

        generator = get_svg_generator()
        svg = generator.generate_floor_plan(building_data, request.width, request.height)

        if not svg:
            raise HTTPException(status_code=503, detail="SVG-Generierung fehlgeschlagen")

        return Response(content=svg, media_type="image/svg+xml")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/visualize/floor-plan",
         tags=["Visualisierung"],
         response_class=Response,
         deprecated=True)
async def visualize_floor_plan_get(
    address: str,
    width: int = 600,
    height: int = 500,
    traufhoehe: Optional[float] = Query(None, description="Manuelle Traufhöhe (nicht verwendet für Grundriss)"),
    firsthoehe: Optional[float] = Query(None, description="Manuelle Firsthöhe (nicht verwendet für Grundriss)")
):
    """
    DEPRECATED: Verwende POST mit sides/polygon Daten für konsistente Ergebnisse.

    Generiert SVG-Grundriss für ein Gebäude (holt eigene Daten).
    Hinweis: traufhoehe/firsthoehe werden akzeptiert aber nicht verwendet (Grundriss ist 2D).
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

        # Polygon und Seiten-Daten erfassen
        polygon_coords = None
        sides_data = None

        if geometry and geometry.sides:
            side_lengths = sorted([s['length_m'] for s in geometry.sides], reverse=True)
            length_m = side_lengths[0]
            width_m = side_lengths[1] if len(side_lengths) > 1 else length_m
            # Polygon-Koordinaten und Seiten für echte Darstellung
            if hasattr(geometry, 'polygon') and geometry.polygon:
                polygon_coords = [[p[0], p[1]] for p in geometry.polygon]
            sides_data = geometry.sides
        elif building and building.area_m2:
            side = math.sqrt(building.area_m2)
            length_m = width_m = round(side, 1)
        else:
            length_m = width_m = 10.0

        eave_height_m = (building.floors or 3) * 2.8 if building else 8.0
        ridge_height_m = None

        if building and building.egid:
            from app.services.height_db import get_building_heights_detailed
            heights = get_building_heights_detailed(building.egid)
            if heights:
                if heights.get("traufhoehe_m"):
                    eave_height_m = heights["traufhoehe_m"]
                if heights.get("firsthoehe_m"):
                    ridge_height_m = heights["firsthoehe_m"]
                gebaeudehoehe = heights.get("gebaeudehoehe_m")
                if gebaeudehoehe and not heights.get("traufhoehe_m"):
                    eave_height_m = gebaeudehoehe * 0.85

        # Manuelle Werte überschreiben DB-Werte
        if traufhoehe and traufhoehe > 0:
            eave_height_m = traufhoehe
        if firsthoehe and firsthoehe > 0:
            ridge_height_m = firsthoehe

        building_data = BuildingData(
            address=geo.matched_address,
            egid=building.egid if building else None,
            length_m=round(length_m, 1),
            width_m=round(width_m, 1),
            eave_height_m=round(eave_height_m, 1),
            ridge_height_m=round(ridge_height_m, 1) if ridge_height_m else None,
            floors=building.floors if building else 3,
            roof_type="flat",  # Grundriss zeigt keine Dachform
            area_m2=building.area_m2 if building else None,
            polygon_coordinates=polygon_coords,
            sides=sides_data,
        )

        generator = get_svg_generator()
        svg = generator.generate_floor_plan(building_data, width, height)

        if not svg:
            raise HTTPException(status_code=503, detail="SVG-Generierung fehlgeschlagen")

        return Response(content=svg, media_type="image/svg+xml")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Dokumentgenerierung (Materialbewirtschaftung)
# ============================================================================

@app.get("/api/v1/document/materialbewirtschaftung",
         tags=["Dokumentgenerierung"],
         response_class=Response)
async def generate_materialbewirtschaftung_document(
    address: str = Query(..., min_length=5, description="Schweizer Adresse"),
    author_name: str = Query("Teilnehmer GL 2025", description="Name des Verfassers"),
    project_description: str = Query("Fassadensanierung", description="Beschreibung des Bauvorhabens"),
    include_reflexion: bool = Query(True, description="Reflexions-Vorlage inkludieren")
):
    """
    Generiert ein Word-Dokument (.docx) für die Materialbewirtschaftung.

    Das Dokument enthält:
    1. Baustellenbeschrieb (Objektdaten, Gebäudemasse, Anforderungen)
    2. Ausmass nach NPK 114
    3. Materialauszug (Layher Blitz 70)
    4. Personalbedarf
    5. Dokumentation Baustelle (inkl. Sicherheitskonzept)
    6. Reflexion (Vorlage zum Ausfüllen)
    7. Anhang (Gerüstkarte, Checkliste)

    **Beispiel:** `?address=Bundesplatz 3, 3011 Bern&author_name=Max Muster`

    Returns: Word-Dokument (.docx)
    """
    from app.services.document_generator import get_document_generator, BuildingData
    from app.services.data_cache import fetch_and_cache_complete_data

    try:
        # Use cached data (fetches if not cached)
        cached = await fetch_and_cache_complete_data(address, swisstopo, geodienste)

        # Build document data from cache
        building_data = BuildingData(
            address=cached.address_matched,
            egid=cached.egid,
            length_m=cached.length_m,
            width_m=cached.width_m,
            eave_height_m=cached.eave_height_m,
            ridge_height_m=cached.ridge_height_m or (cached.eave_height_m + 3.5),
            floors=cached.floors or 2,
            building_category=cached.building_category or "Einfamilienhaus",
            construction_year=cached.construction_year,
            area_m2=cached.area_m2,
            roof_type="satteldach" if (cached.ridge_height_m and cached.ridge_height_m > cached.eave_height_m) else "flachdach",
            lv95_e=cached.lv95_e,
            lv95_n=cached.lv95_n
        )

        # 7. SVG-Visualisierungen generieren
        from app.services.svg_generator import get_svg_generator, BuildingData as SVGBuildingData
        svg_generator = get_svg_generator()

        # Auto-detect roof type
        svg_roof_type = "gable" if (cached.ridge_height_m and cached.ridge_height_m > cached.eave_height_m) else "flat"

        svg_building_data = SVGBuildingData(
            address=cached.address_matched,
            egid=cached.egid,
            length_m=cached.length_m,
            width_m=cached.width_m,
            eave_height_m=cached.eave_height_m,
            ridge_height_m=cached.ridge_height_m or cached.eave_height_m,
            floors=cached.floors or 2,
            roof_type=svg_roof_type,
            area_m2=cached.area_m2,
        )

        # SVGs generieren
        svg_floor_plan = svg_generator.generate_floor_plan(svg_building_data)
        svg_cross_section = svg_generator.generate_cross_section(svg_building_data)
        svg_elevation = svg_generator.generate_elevation(svg_building_data)

        # 8. Dokument generieren (SVGs werden via Pillow zu PNG konvertiert)
        generator = get_document_generator()
        docx_bytes = generator.generate_word_document(
            building=building_data,
            author_name=author_name,
            project_description=project_description,
            include_reflexion_template=include_reflexion,
            svg_floor_plan=svg_floor_plan,
            svg_cross_section=svg_cross_section,
            svg_elevation=svg_elevation
        )

        # Dateiname erstellen
        safe_address = cached.address_matched.replace(",", "").replace(" ", "_")[:50]
        filename = f"Materialbewirtschaftung_{safe_address}.docx"

        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Dokumentgenerierung nicht verfügbar. Bitte 'pip install python-docx' ausführen. Fehler: {str(e)}"
        )
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
