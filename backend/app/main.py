"""
Geodaten Schweiz API
====================

REST API für Schweizer Geodaten (Gebäude, Adressen, Grundstücke)
Primäre Datenquelle: swisstopo / geo.admin.ch
"""

import os
from dotenv import load_dotenv

# .env Datei laden (für lokale Entwicklung)
load_dotenv()
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
         tags=["Gerüstbau"],
         deprecated=True)
async def get_scaffolding_data(
    address: str = Query(..., min_length=5, description="Adresse"),
    egid: Optional[int] = Query(None, description="EGID (falls bekannt)"),
    height: Optional[float] = Query(None, description="Manuelle Gebäudehöhe in Metern (deprecated, use traufhoehe/firsthoehe)"),
    traufhoehe: Optional[float] = Query(None, description="Manuelle Traufhöhe in Metern"),
    firsthoehe: Optional[float] = Query(None, description="Manuelle Firsthöhe in Metern"),
    refresh: bool = Query(False, description="Cache ignorieren und neu laden"),
    work_type: str = Query("dacharbeiten", description="Arbeitstyp: dacharbeiten (First+1m) oder fassadenarbeiten (Traufe)"),
    scaffold_type: str = Query("arbeitsgeruest", description="Gerüstart: arbeitsgeruest, schutzgeruest, fanggeruest"),
    simplify_epsilon: Optional[float] = Query(None, ge=0.1, le=3.0, description="Douglas-Peucker Vereinfachung (0.1-3.0m). Auto: EFH=0.3, MFH=0.8, Gross=1.5"),
    use_smart_service: bool = Query(True, description="SmartBuildingService nutzen (parallel, einheitlich)")
):
    """
    ⚠️ **DEPRECATED**: Bitte `/api/v1/smart-building/data` verwenden.

    Dieser Endpunkt wird für Abwärtskompatibilität beibehalten, aber nicht mehr aktiv weiterentwickelt.

    **Migration:**
    ```
    ALT: GET /api/v1/scaffolding?address=...
    NEU: GET /api/v1/smart-building/data?address=...&include_research=true&include_zones=true
    ```

    Liefert:
    - Exakten Grundriss (Polygon mit allen Eckpunkten)
    - Seitenlängen jeder Fassade
    - Gesamtumfang (für Gerüstmeter)
    - Gemessene/geschätzte Gebäudehöhe
    - Geschätzte Gerüstfläche
    - Gebäude-Identifikation (Name, Typ, Baustil)
    - Höhenzonen (bei komplexen Gebäuden)

    **Arbeitstyp:**
    - `dacharbeiten`: Gerüsthöhe = Firsthöhe + 1.0m (SUVA Vorschrift)
    - `fassadenarbeiten`: Gerüsthöhe = Traufhöhe (Unterdach)

    **Gerüstart:**
    - `arbeitsgeruest`: Standard für Fassadenarbeiten (NPK 114.1xx)
    - `schutzgeruest`: Absturzsicherung bei Dacharbeiten (NPK 114.2xx)
    - `fanggeruest`: Auffangen von Material/Personen (NPK 114.3xx)

    **Beispiel:** `?address=Bundesplatz 3, 3011 Bern&work_type=dacharbeiten`
    """

    # =================================================================
    # NEU: SmartBuildingService (Standard)
    # =================================================================
    if use_smart_service:
        try:
            from app.services.smart_building import get_smart_building_service

            service = get_smart_building_service()

            # Daten sammeln (parallel, gecacht)
            bundle = await service.collect_all_data(
                address=address,
                force_refresh=refresh,
                include_research=True,
                include_zones_analysis=True,
                include_terrain=True,
            )

            # Manuelle Höhen überschreiben
            if traufhoehe:
                bundle.traufhoehe_m = traufhoehe
            if firsthoehe:
                bundle.firsthoehe_m = firsthoehe
            if height:
                bundle.estimated_height_m = height

            # Response konvertieren
            result = service.bundle_to_scaffolding_response(
                bundle=bundle,
                work_type=work_type,
                scaffold_type=scaffold_type,
            )

            return result

        except Exception as smart_error:
            print(f"[SmartService] Fehler, Fallback zu Legacy: {smart_error}")
            import traceback
            traceback.print_exc()
            # Fallback zu Legacy-Code unten

    # =================================================================
    # LEGACY: Bisheriger Code (Fallback)
    # =================================================================
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
            egid=egid or (building.egid if building else None),
            simplify_epsilon=simplify_epsilon
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

        # 5. Terrain-Daten abrufen (swissALTI3D)
        terrain_data = None
        try:
            from app.services.terrain import get_terrain_service
            terrain_service = get_terrain_service()
            terrain_height = await terrain_service.get_height(
                geo.coordinates.lv95_e,
                geo.coordinates.lv95_n
            )
            if terrain_height is not None:
                terrain_data = {
                    "terrain_height_m": terrain_height,
                    "elevation_model": "COMB"
                }
                # Bei Polygon: Min/Max Höhe berechnen
                if geometry and geometry.polygon:
                    polygon_coords = [(p[0], p[1]) for p in geometry.polygon[:8]]  # Max 8 Punkte
                    terrain_info = await terrain_service.get_terrain_info(
                        geo.coordinates.lv95_e,
                        geo.coordinates.lv95_n,
                        polygon_coords
                    )
                    if terrain_info:
                        terrain_data["min_terrain_m"] = terrain_info.min_terrain_m
                        terrain_data["max_terrain_m"] = terrain_info.max_terrain_m
                        terrain_data["terrain_slope_m"] = terrain_info.terrain_slope_m
        except Exception as terrain_error:
            print(f"[Scaffolding] Terrain-Abfrage fehlgeschlagen: {terrain_error}")

        # 5b. Dachdaten berechnen (Option C: heuristische Berechnung)
        roof_data = None
        try:
            from app.services.roof import get_roof_service
            roof_service = get_roof_service()

            # Höhendaten aus scaffolding_data extrahieren
            heights = scaffolding_data.get("heights", {})
            dims = scaffolding_data.get("dimensions", {})

            roof_calc = roof_service.calculate(
                traufhoehe_m=heights.get("traufhoehe_m"),
                firsthoehe_m=heights.get("firsthoehe_m"),
                building_depth_m=dims.get("width_m"),  # Tiefe = kürzere Seite
                building_length_m=dims.get("length_m"),
                ground_area_m2=scaffolding_data.get("building", {}).get("area_m2"),
                polygon=geometry.polygon if geometry else None,
                floors=building.floors if building else None,
                building_category_code=building.building_category_code if building else None
            )
            roof_data = roof_calc.to_dict()
        except Exception as roof_error:
            print(f"[Scaffolding] Dach-Berechnung fehlgeschlagen: {roof_error}")

        # 6. Adress- und GWR-Infos hinzufügen
        result = {
            "address": {
                "input": address,
                "matched": geo.matched_address,
                "coordinates": {
                    "lv95_e": geo.coordinates.lv95_e,
                    "lv95_n": geo.coordinates.lv95_n,
                },
                "terrain": terrain_data,
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
            # Dachdaten (Option C: heuristische Berechnung)
            "roof": roof_data,
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
         tags=["Gerüstbau"],
         deprecated=True)
async def get_scaffolding_by_egid(
    egid: int,
    height: Optional[float] = Query(None, description="Manuelle Gebäudehöhe in Metern")
):
    """
    ⚠️ **DEPRECATED**: Bitte `/api/v1/smart-building/data` mit Adresse verwenden.

    Gebäudegeometrie per EGID abrufen.

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
# Building Context System (Höhenzonen für komplexe Gebäude)
# ============================================================================

from app.models.building_context import (
    BuildingContext, BuildingContextCreate, BuildingContextResponse,
    AnalyzeRequest, AnalyzeResponse, ComplexityLevel
)
from app.services.building_context import get_building_context_service


@app.get("/api/v1/building/context/{egid}",
         response_model=BuildingContextResponse,
         tags=["Building Context"])
async def get_building_context(
    egid: str,
    create_if_missing: bool = Query(False, description="Automatisch erstellen wenn nicht vorhanden"),
    analyze_if_complex: bool = Query(False, description="Claude-Analyse triggern wenn komplex")
):
    """
    Gebäude-Kontext abrufen.

    Der Kontext enthält Höhenzonen und Gebäudeteil-Informationen
    für komplexe Gebäude.

    **Beispiel:** `/api/v1/building/context/1234567`
    """
    service = get_building_context_service()

    # Existierenden Kontext suchen
    context = service.get_context(egid)

    if context:
        return BuildingContextResponse(
            status="found",
            context=context,
            needs_validation=not context.validated_by_user
        )

    if not create_if_missing:
        return BuildingContextResponse(
            status="not_found",
            needs_validation=False,
            message=f"Kein Kontext für EGID {egid} gefunden"
        )

    # Gebäudedaten laden für Auto-Context
    try:
        building = await swisstopo.get_building_by_egid(int(egid), include_geometry=True)
        if not building or not building.coordinates:
            return BuildingContextResponse(
                status="error",
                message=f"Gebäude mit EGID {egid} nicht gefunden"
            )

        geometry = await geodienste.get_building_geometry(
            x=building.coordinates.lv95_e,
            y=building.coordinates.lv95_n,
            tolerance=50,
            egid=int(egid)
        )

        if not geometry or not geometry.polygon:
            return BuildingContextResponse(
                status="error",
                message="Gebäudegeometrie nicht verfügbar"
            )

        # Polygon zu Liste von dicts konvertieren
        polygon = [{"x": p[0], "y": p[1]} for p in geometry.polygon]

        # Höhendaten aus Geometry
        height_data = {
            "traufhoehe_m": geometry.height_info.get("traufhoehe_m") if geometry.height_info else None,
            "firsthoehe_m": geometry.height_info.get("firsthoehe_m") if geometry.height_info else None,
            "gebaeudehoehe_m": geometry.height_info.get("gebaeudehoehe_m") if geometry.height_info else None,
        }

        # GWR-Daten
        gwr_data = {
            "gkat": building.building_category_code,
            "gastw": building.floors,
            "gbauj": building.construction_year,
            "garea": building.area_m2,
        }

        # Komplexität prüfen
        complexity = service.detect_complexity(polygon, gwr_data, building.area_m2)

        # Kontext erstellen
        if complexity == ComplexityLevel.COMPLEX and analyze_if_complex:
            # Claude-Analyse für komplexe Gebäude
            context = await service.analyze_with_claude(
                egid=egid,
                adresse=building.address,
                polygon=polygon,
                height_data=height_data,
                gwr_data=gwr_data
            )
        else:
            # Auto-Context für einfache/moderate Gebäude
            context = service.create_auto_context(
                egid=egid,
                adresse=building.address,
                polygon=polygon,
                height_data=height_data,
                gwr_data=gwr_data
            )

        # Speichern
        service.save_context(context)

        return BuildingContextResponse(
            status="created",
            context=context,
            needs_validation=context.source.value == "claude"
        )

    except Exception as e:
        return BuildingContextResponse(
            status="error",
            message=str(e)
        )


@app.post("/api/v1/building/context/{egid}/analyze",
          response_model=AnalyzeResponse,
          tags=["Building Context"])
async def analyze_building_context(
    egid: str,
    request: AnalyzeRequest
):
    """
    Claude-Analyse für komplexes Gebäude triggern.

    Analysiert das Gebäudepolygon und identifiziert Höhenzonen,
    Türme, Anbauten und andere Sonderelemente.

    **Kosten:** ~$0.03-0.05 pro Analyse
    """
    service = get_building_context_service()

    # Prüfen ob bereits analysiert
    existing = service.get_context(egid)
    if existing and not request.force_reanalyze:
        return AnalyzeResponse(
            status="already_exists",
            context=existing,
            message="Kontext existiert bereits. force_reanalyze=true zum Überschreiben."
        )

    try:
        # Gebäudedaten laden
        building = await swisstopo.get_building_by_egid(int(egid), include_geometry=True)
        if not building or not building.coordinates:
            return AnalyzeResponse(
                status="error",
                message=f"Gebäude mit EGID {egid} nicht gefunden"
            )

        geometry = await geodienste.get_building_geometry(
            x=building.coordinates.lv95_e,
            y=building.coordinates.lv95_n,
            tolerance=50,
            egid=int(egid)
        )

        if not geometry or not geometry.polygon:
            return AnalyzeResponse(
                status="error",
                message="Gebäudegeometrie nicht verfügbar"
            )

        polygon = [{"x": p[0], "y": p[1]} for p in geometry.polygon]

        # Höhendaten aus DB oder Schätzung holen
        from app.services.geodienste import get_height_details
        height_info = get_height_details(
            floors=building.floors,
            building_category_code=building.building_category_code,
            manual_height=None,
            egid=int(egid),
            lv95_e=building.coordinates.lv95_e,
            lv95_n=building.coordinates.lv95_n
        )

        height_data = {
            "traufhoehe_m": height_info.get("traufhoehe_m"),
            "firsthoehe_m": height_info.get("firsthoehe_m"),
            "gebaeudehoehe_m": height_info.get("gebaeudehoehe_m") or height_info.get("active_height_m") or geometry.estimated_height_m,
        }

        gwr_data = {
            "gkat": building.building_category_code,
            "gastw": building.floors,
            "gbauj": building.construction_year,
            "garea": building.area_m2,
        }

        # Claude-Analyse
        context = await service.analyze_with_claude(
            egid=egid,
            adresse=building.address,
            polygon=polygon,
            height_data=height_data,
            gwr_data=gwr_data,
            include_orthofoto=request.include_orthofoto
        )

        # Speichern
        service.save_context(context)

        return AnalyzeResponse(
            status="success",
            context=context,
            cost_estimate_usd=0.02
        )

    except Exception as e:
        return AnalyzeResponse(
            status="error",
            message=str(e)
        )


@app.put("/api/v1/building/context/{egid}",
         response_model=BuildingContextResponse,
         tags=["Building Context"])
async def update_building_context(
    egid: str,
    request: BuildingContextCreate
):
    """
    Gebäude-Kontext manuell aktualisieren.

    Erlaubt manuelle Korrekturen an den Höhenzonen.
    """
    service = get_building_context_service()

    existing = service.get_context(egid)
    if not existing:
        return BuildingContextResponse(
            status="not_found",
            message=f"Kein Kontext für EGID {egid} gefunden"
        )

    # Update mit neuen Zonen
    existing.zones = request.zones
    existing.validated_by_user = request.validated
    existing.source = existing.source  # Behalte ursprüngliche Quelle

    service.save_context(existing)

    return BuildingContextResponse(
        status="found",
        context=existing,
        needs_validation=False
    )


@app.delete("/api/v1/building/context/{egid}",
            tags=["Building Context"])
async def delete_building_context(egid: str):
    """
    Gebäude-Kontext löschen (Reset).
    """
    service = get_building_context_service()

    deleted = service.delete_context(egid)

    if deleted:
        return {"status": "deleted", "egid": egid}
    else:
        return {"status": "not_found", "egid": egid}


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

# ===========================================================================
# Terrain API (swissALTI3D)
# ===========================================================================

@app.get("/api/v1/terrain/height",
         tags=["Terrain"])
async def get_terrain_height(
    e: float = Query(..., description="LV95 Easting (E-Koordinate)"),
    n: float = Query(..., description="LV95 Northing (N-Koordinate)"),
):
    """
    Terrain-Höhe an einer Koordinate abrufen (swissALTI3D).

    Liefert die Geländehöhe in Metern über Meer (m ü.M.)
    aus dem hochpräzisen swissALTI3D Höhenmodell.

    **Beispiel:** `?e=2600948&n=1199582` → Münsterplatz Bern

    **Höhenmodell:** COMB (kombiniert DTM2 + DTM25)
    - DTM2: 2m Auflösung (LiDAR, hochpräzise)
    - DTM25: 25m Auflösung (DHM25)
    """
    try:
        from app.services.terrain import get_terrain_service
        terrain_service = get_terrain_service()
        height = await terrain_service.get_height(e, n)

        if height is None:
            raise HTTPException(
                status_code=404,
                detail="Keine Terrain-Daten für diese Koordinaten verfügbar"
            )

        return {
            "easting": e,
            "northing": n,
            "terrain_height_m": height,
            "elevation_model": "COMB",
            "source": "swissALTI3D"
        }
    except HTTPException:
        raise
    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler bei Terrain-Abfrage: {str(ex)}"
        )


@app.get("/api/v1/terrain/profile",
         tags=["Terrain"])
async def get_terrain_profile(
    start_e: float = Query(..., description="Start LV95 Easting"),
    start_n: float = Query(..., description="Start LV95 Northing"),
    end_e: float = Query(..., description="Ende LV95 Easting"),
    end_n: float = Query(..., description="Ende LV95 Northing"),
    nb_points: int = Query(10, ge=2, le=100, description="Anzahl Punkte"),
):
    """
    Terrain-Profil entlang einer Linie abrufen.

    Nützlich für:
    - Fassaden-Gefälle berechnen
    - Schnitt-Darstellung mit realistischem Gelände
    - Niveauausgleich für Gerüst

    **Beispiel:** Profil entlang der Bundeshaus-Fassade
    """
    try:
        from app.services.terrain import get_terrain_service
        terrain_service = get_terrain_service()
        profile = await terrain_service.get_profile(
            [(start_e, start_n), (end_e, end_n)],
            nb_points=nb_points
        )

        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Kein Terrain-Profil für diese Koordinaten verfügbar"
            )

        return {
            "start": {"easting": start_e, "northing": start_n},
            "end": {"easting": end_e, "northing": end_n},
            "points": [p.model_dump() for p in profile.points],
            "statistics": {
                "min_height_m": profile.min_height_m,
                "max_height_m": profile.max_height_m,
                "height_diff_m": profile.height_diff_m,
                "total_distance_m": profile.total_distance_m
            },
            "source": "swissALTI3D"
        }
    except HTTPException:
        raise
    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=f"Fehler bei Terrain-Profil-Abfrage: {str(ex)}"
        )


# ===========================================================================
# Materialkatalog
# ===========================================================================

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
    area_m2: float = Query(..., description="Gerüstfläche in m²"),
    short_field_ratio: float = Query(0.33, description="Anteil kurze Felder (2.57m): 0=nur 3.07m, 0.33=Standard, 1=nur 2.57m")
):
    """
    Materialmenge basierend auf Gerüstfläche schätzen.

    Verwendet Richtwerte pro 100m² Gerüstfläche.
    Der `short_field_ratio` Parameter steuert das Verhältnis von 2.57m zu 3.07m Elementen.

    **Beispiel:** `/api/v1/catalog/estimate?system_id=blitz70&area_m2=460&short_field_ratio=0.5`
    """
    try:
        from app.services.layher_catalog import get_catalog_service
        service = get_catalog_service()

        estimates = service.estimate_material_quantities(system_id, area_m2, short_field_ratio)

        # Gesamtgewicht berechnen
        total_weight = sum(e["total_weight_kg"] or 0 for e in estimates)
        total_pieces = sum(e["quantity_typical"] for e in estimates)

        return {
            "system_id": system_id,
            "scaffold_area_m2": area_m2,
            "short_field_ratio": short_field_ratio,
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


@app.get("/api/v1/catalog/estimate-combined",
         tags=["Materialkatalog"])
async def estimate_combined_system(
    area_m2: float = Query(..., description="Gerüstfläche in m²"),
    blitz_ratio: float = Query(0.7, description="Anteil Blitz 70 (0.0-1.0), Rest ist Allround"),
    short_field_ratio: float = Query(0.33, description="Anteil kurze Felder (2.57m): 0=nur 3.07m, 0.33=Standard, 1=nur 2.57m")
):
    """
    Materialschätzung für kombiniertes System (Blitz 70 + Allround).

    Für Gebäude mit gemischten Anforderungen:
    - Blitz 70 für Standardbereiche (wirtschaftlich)
    - Allround für Verstärkungen, Ecken, höhere Lasten

    **Beispiel:** `/api/v1/catalog/estimate-combined?area_m2=460&blitz_ratio=0.7&short_field_ratio=0.5`
    """
    try:
        from app.services.layher_catalog import get_catalog_service
        service = get_catalog_service()

        if not 0 <= blitz_ratio <= 1:
            raise ValueError("blitz_ratio muss zwischen 0 und 1 liegen")
        if not 0 <= short_field_ratio <= 1:
            raise ValueError("short_field_ratio muss zwischen 0 und 1 liegen")

        return service.estimate_combined_system_quantities(area_m2, blitz_ratio, short_field_ratio)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Materialkatalog nicht verfügbar")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/catalog/system-info/{system_id}",
         tags=["Materialkatalog"])
async def get_system_info(system_id: str):
    """
    Detaillierte Systeminformationen für UI-Anzeige.

    Liefert Beschreibung, Vorteile, Anwendungsgebiete, Lastklasse.

    **Systeme:** blitz70, allround, combined

    **Beispiel:** `/api/v1/catalog/system-info/blitz70`
    """
    try:
        from app.services.layher_catalog import get_catalog_service
        service = get_catalog_service()
        return service.get_system_info(system_id)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Materialkatalog nicht verfügbar")


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
# Gerüstlift (NPK 114.3xx)
# ============================================================================

@app.get("/api/v1/lift/types",
         tags=["Gerüstlift"])
async def get_lift_types():
    """
    Verfügbare Lift-Typen abrufen.

    - **Material**: Einfacher Lift für Material
    - **Person**: Für Personen zugelassen
    - **Kombilift**: Material und Personen (nicht gleichzeitig)
    """
    from app.services.lift_calculator import get_lift_calculator
    return get_lift_calculator().get_lift_types()


@app.get("/api/v1/lift/widths",
         tags=["Gerüstlift"])
async def get_lift_widths():
    """
    Verfügbare Lift-Breiten abrufen (Layher-kompatibel).
    """
    from app.services.lift_calculator import get_lift_calculator
    return get_lift_calculator().get_available_widths()


@app.post("/api/v1/lift/calculate",
          tags=["Gerüstlift"])
async def calculate_lift(
    lift_type: str = Query(..., description="Lift-Typ: material, person, combined"),
    height_m: float = Query(..., description="Gerüsthöhe in Metern"),
    width_m: float = Query(1.35, description="Lift-Breite in Metern"),
    levels: int = Query(0, description="Anzahl Etagen (0 = automatisch berechnen)")
):
    """
    Lift-Berechnung durchführen.

    Berechnet NPK-Positionen, Fläche und Gewichtsschätzung für einen Gerüstlift.

    **Beispiel:** `/api/v1/lift/calculate?lift_type=material&height_m=12&width_m=1.35`
    """
    from app.services.lift_calculator import get_lift_calculator, LiftConfiguration, LiftType

    try:
        lift_type_enum = LiftType(lift_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Ungültiger Lift-Typ: {lift_type}. Erlaubt: material, person, combined"
        )

    config = LiftConfiguration(
        lift_type=lift_type_enum,
        height_m=height_m,
        width_m=width_m,
        levels=levels
    )

    calculator = get_lift_calculator()
    result = calculator.calculate_lift(config)

    return {
        "lift_type": result.lift_type.value,
        "height_m": result.height_m,
        "width_m": result.width_m,
        "levels": result.levels,
        "area_m2": result.area_m2,
        "npk_positions": result.npk_positions,
        "weight_estimate_kg": result.weight_estimate_kg,
        "notes": result.notes
    }


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
    firsthoehe: Optional[float] = Query(None, description="Manuelle Firsthöhe in Metern"),
    professional: bool = Query(False, description="Professional Mode für Fallback-Generator"),
    auto_analyze: bool = Query(True, description="Auto-Claude-Analyse bei komplexen Gebäuden"),
    use_claude: bool = Query(True, description="Claude API für SVG-Generierung (unified prompt system)"),
    force_refresh: bool = Query(False, description="Cache ignorieren für frische Daten")
):
    """
    Generiert SVG-Schnittansicht für ein Gebäude.

    - **address**: Schweizer Adresse
    - **width**: SVG-Breite in Pixel (default: 700)
    - **height**: SVG-Höhe in Pixel (default: 480)
    - **traufhoehe**: Manuelle Traufhöhe (überschreibt DB)
    - **firsthoehe**: Manuelle Firsthöhe (überschreibt DB)
    - **auto_analyze**: Auto-Claude-Analyse bei komplexen Gebäuden (default: True)
    - **use_claude**: Claude API für SVG-Generierung (default: True, unified prompt system)
    - **force_refresh**: Cache ignorieren (default: False)

    **NEU:** Nutzt SmartBuildingService für einheitliche Datenpipeline und Caching.
    Bei manuellen Höhenangaben wird der Legacy-Pfad verwendet.

    Returns: SVG-Datei
    """
    from app.services.svg_generator import get_svg_generator, BuildingData
    from app.services.building_context import get_building_context_service, ComplexityLevel
    from app.services.claude_svg_zones import (
        generate_cross_section_with_zones,
        generate_svg_with_smart_service,
        is_available as claude_svg_available
    )

    try:
        # === SCHNELLER PFAD: SmartBuildingService (ohne manuelle Höhen) ===
        if use_claude and claude_svg_available() and not traufhoehe and not firsthoehe:
            svg = await generate_svg_with_smart_service(
                address=address,
                svg_type="schnitt",
                force_refresh=force_refresh,
            )
            if svg:
                return Response(content=svg, media_type="image/svg+xml")
            # Fallthrough zu Legacy-Pfad bei Fehler

        # === LEGACY PFAD: Manuelle Höhen oder Fallback-Generator ===
        # Gebäudedaten abrufen
        geo = await swisstopo.geocode(address)
        if not geo:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")

        buildings = await swisstopo.identify_buildings(
            geo.coordinates.lv95_e, geo.coordinates.lv95_n, tolerance=15
        )
        building = buildings[0] if buildings else None

        # Terrain-Daten für Hanglage-Erkennung
        terrain_data = None
        try:
            from app.services.terrain import get_terrain_service
            terrain_service = get_terrain_service()
            terrain_height = await terrain_service.get_height(
                geo.coordinates.lv95_e, geo.coordinates.lv95_n
            )
            if terrain_height is not None:
                terrain_data = {"terrain_height_m": terrain_height}
                # Terrain-Profil für Hanglage (TODO: 4 Eckpunkte)
        except Exception as terrain_error:
            print(f"[CrossSection] Terrain-Abfrage fehlgeschlagen: {terrain_error}")

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
        heights_data = {}

        # Gemessene Höhe aus swissBUILDINGS3D DB - zuerst per EGID, dann per Koordinaten
        from app.services.height_db import get_building_heights_detailed, get_building_height_by_coordinates
        heights = None

        # 1. EGID-basierter Lookup
        if building and building.egid:
            heights = get_building_heights_detailed(building.egid)

        # 2. Fallback: Koordinaten-basierter Lookup (für Gebäude ohne EGID wie Bundeshaus)
        if not heights and geo:
            heights = get_building_height_by_coordinates(
                e=geo.coordinates.lv95_e,
                n=geo.coordinates.lv95_n,
                tolerance_m=50.0
            )
            if heights:
                print(f"[HEIGHT] Koordinaten-Lookup: {heights.get('source')}, Distanz: {heights.get('distance_m')}m")

        if heights:
            heights_data = heights
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

        # === ZONEN LADEN/ERSTELLEN ===
        zones = None
        if building and building.egid:
            context_service = get_building_context_service()
            context = context_service.get_context(str(building.egid))

            if not context:
                # Polygon für Komplexitäts-Check vorbereiten
                polygon = []
                if geometry and geometry.polygon:
                    polygon = [{"x": p[0], "y": p[1]} for p in geometry.polygon]

                # Komplexität prüfen
                gwr_data = {
                    'gkat': building.building_category_code if building else None,
                    'garea': building.area_m2 if building else None,
                }
                complexity = context_service.detect_complexity(polygon, gwr_data, building.area_m2 if building else None)

                # Höhendifferenz prüfen (komplexe Gebäude haben oft grosse Differenz)
                height_diff = (ridge_height_m or 0) - (eave_height_m or 0)
                if height_diff > 15:
                    complexity = ComplexityLevel.COMPLEX

                # Building-Hints für bekannte Gebäude hinzufügen
                from app.services.building_hints import get_building_hints, should_use_orthofoto
                hints = get_building_hints(
                    address=geo.matched_address,
                    egid=building.egid,
                    building_category_code=building.building_category_code if building else None
                )
                if hints:
                    gwr_data["building_name"] = hints["name"]
                    gwr_data["building_hints"] = hints["hints"]
                    print(f"[HINTS] Erkannt: {hints['name']} (Match: {hints.get('match_type')})")

                # Orthofoto für komplexe/bekannte Gebäude
                use_orthofoto = should_use_orthofoto(
                    address=geo.matched_address,
                    egid=building.egid,
                    is_complex=(complexity == ComplexityLevel.COMPLEX),
                    building_category_code=building.building_category_code if building else None
                )

                if complexity == ComplexityLevel.COMPLEX and auto_analyze:
                    # Claude-Analyse für komplexe Gebäude
                    try:
                        print(f"[ANALYZE] Starte Claude-Analyse (Orthofoto: {use_orthofoto})")
                        context = await context_service.analyze_with_claude(
                            egid=str(building.egid),
                            adresse=geo.matched_address,
                            polygon=polygon,
                            height_data=heights_data,
                            gwr_data=gwr_data,
                            include_orthofoto=use_orthofoto,
                            terrain_data=terrain_data
                        )
                        context_service.save_context(context)
                    except Exception as e:
                        print(f"Claude analysis failed: {e}")
                        # Fallback auf Auto-Context
                        context = context_service.create_auto_context(
                            egid=str(building.egid),
                            adresse=geo.matched_address,
                            polygon=polygon,
                            height_data=heights_data,
                            gwr_data=gwr_data
                        )
                else:
                    # Auto-Context für einfache/moderate Gebäude
                    context = context_service.create_auto_context(
                        egid=str(building.egid),
                        adresse=geo.matched_address,
                        polygon=polygon,
                        height_data=heights_data,
                        gwr_data=gwr_data
                    )

            if context and context.zones and len(context.zones) > 1:
                zones = [z.model_dump() for z in context.zones]

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
            zones=zones,
        )

        # SVG generieren
        svg = None

        # Claude API für professionelle SVG-Generierung
        if use_claude and claude_svg_available():
            # Zonen für Claude vorbereiten
            claude_zones = []
            if zones:
                claude_zones = zones
            else:
                # Standard-Zone erstellen wenn keine Zonen vorhanden
                claude_zones = [{
                    "name": "Gebäude",
                    "type": "hauptgebaeude",
                    "building_height_m": eave_height_m,
                    "first_height_m": ridge_height_m or eave_height_m,
                    "description": f"{building.floors if building else 3} Geschosse"
                }]

            # building_data für Prompt-Selektor (Komplexitäts-Erkennung)
            svg_building_data = {
                'gkat': building.building_category_code if building else None,
                'area_m2': building.area_m2 if building else None,
                'sides': len(geometry.polygon) if geometry and geometry.polygon else 4,
                'geschosse': building.floors if building else 3,
                'adresse': geo.matched_address,
            }

            svg = await generate_cross_section_with_zones(
                address=geo.matched_address,
                egid=building.egid if building else None,
                width_m=round(length_m, 1),
                floors=building.floors if building else 3,
                zones=claude_zones,
                svg_width=width,
                svg_height=height,
                building_data=svg_building_data
            )

        # Fallback auf Standard-Generator
        if not svg:
            generator = get_svg_generator()
            svg = generator.generate_cross_section(building_data, width, height, professional=professional)

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
    firsthoehe: Optional[float] = Query(None, description="Manuelle Firsthöhe in Metern"),
    professional: bool = Query(False, description="Professional Mode für Fallback-Generator"),
    auto_analyze: bool = Query(True, description="Auto-Claude-Analyse bei komplexen Gebäuden"),
    use_claude: bool = Query(True, description="Claude API für SVG-Generierung (unified prompt system)"),
    force_refresh: bool = Query(False, description="Cache ignorieren für frische Daten")
):
    """
    Generiert SVG-Fassadenansicht für ein Gebäude.

    - **address**: Schweizer Adresse
    - **width**: SVG-Breite in Pixel (default: 700)
    - **height**: SVG-Höhe in Pixel (default: 480)
    - **traufhoehe**: Manuelle Traufhöhe (überschreibt DB)
    - **firsthoehe**: Manuelle Firsthöhe (überschreibt DB)
    - **auto_analyze**: Auto-Claude-Analyse bei komplexen Gebäuden (default: True)
    - **use_claude**: Claude API für SVG-Generierung (default: True, unified prompt system)
    - **force_refresh**: Cache ignorieren (default: False)

    **NEU:** Nutzt SmartBuildingService für einheitliche Datenpipeline und Caching.
    Bei manuellen Höhenangaben wird der Legacy-Pfad verwendet.

    Returns: SVG-Datei
    """
    from app.services.svg_generator import get_svg_generator, BuildingData
    from app.services.building_context import get_building_context_service, ComplexityLevel
    from app.services.claude_svg_zones import (
        generate_elevation_with_zones,
        generate_svg_with_smart_service,
        is_available as claude_svg_available
    )

    try:
        # === SCHNELLER PFAD: SmartBuildingService (ohne manuelle Höhen) ===
        if use_claude and claude_svg_available() and not traufhoehe and not firsthoehe:
            svg = await generate_svg_with_smart_service(
                address=address,
                svg_type="ansicht",
                force_refresh=force_refresh,
            )
            if svg:
                return Response(content=svg, media_type="image/svg+xml")
            # Fallthrough zu Legacy-Pfad bei Fehler

        # === LEGACY PFAD: Manuelle Höhen oder Fallback-Generator ===
        geo = await swisstopo.geocode(address)
        if not geo:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")

        buildings = await swisstopo.identify_buildings(
            geo.coordinates.lv95_e, geo.coordinates.lv95_n, tolerance=15
        )
        building = buildings[0] if buildings else None

        # Terrain-Daten für Hanglage-Erkennung
        terrain_data = None
        try:
            from app.services.terrain import get_terrain_service
            terrain_service = get_terrain_service()
            terrain_height = await terrain_service.get_height(
                geo.coordinates.lv95_e, geo.coordinates.lv95_n
            )
            if terrain_height is not None:
                terrain_data = {"terrain_height_m": terrain_height}
        except Exception as terrain_error:
            print(f"[Elevation] Terrain-Abfrage fehlgeschlagen: {terrain_error}")

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
        heights_data = {}

        # Gemessene Höhe aus swissBUILDINGS3D DB - zuerst per EGID, dann per Koordinaten
        from app.services.height_db import get_building_heights_detailed, get_building_height_by_coordinates
        heights = None

        # 1. EGID-basierter Lookup
        if building and building.egid:
            heights = get_building_heights_detailed(building.egid)

        # 2. Fallback: Koordinaten-basierter Lookup (für Gebäude ohne EGID wie Bundeshaus)
        if not heights and geo:
            heights = get_building_height_by_coordinates(
                e=geo.coordinates.lv95_e,
                n=geo.coordinates.lv95_n,
                tolerance_m=50.0
            )
            if heights:
                print(f"[HEIGHT] Koordinaten-Lookup (elevation): {heights.get('source')}, Distanz: {heights.get('distance_m')}m")

        if heights:
            heights_data = heights
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

        # === ZONEN LADEN/ERSTELLEN (Elevation) ===
        zones = None
        if building and building.egid:
            context_service = get_building_context_service()
            context = context_service.get_context(str(building.egid))

            if not context:
                # Polygon für Komplexitäts-Check vorbereiten
                polygon = []
                if geometry and geometry.polygon:
                    polygon = [{"x": p[0], "y": p[1]} for p in geometry.polygon]

                # Komplexität prüfen
                gwr_data = {
                    'gkat': building.building_category_code if building else None,
                    'garea': building.area_m2 if building else None,
                }
                complexity = context_service.detect_complexity(polygon, gwr_data, building.area_m2 if building else None)

                # Höhendifferenz prüfen (komplexe Gebäude haben oft grosse Differenz)
                height_diff = (ridge_height_m or 0) - (eave_height_m or 0)
                if height_diff > 15:
                    complexity = ComplexityLevel.COMPLEX

                # Building-Hints für bekannte Gebäude hinzufügen
                from app.services.building_hints import get_building_hints, should_use_orthofoto
                hints = get_building_hints(
                    address=geo.matched_address,
                    egid=building.egid,
                    building_category_code=building.building_category_code if building else None
                )
                if hints:
                    gwr_data["building_name"] = hints["name"]
                    gwr_data["building_hints"] = hints["hints"]
                    print(f"[HINTS] Erkannt (elevation): {hints['name']} (Match: {hints.get('match_type')})")

                # Orthofoto für komplexe/bekannte Gebäude
                use_orthofoto = should_use_orthofoto(
                    address=geo.matched_address,
                    egid=building.egid,
                    is_complex=(complexity == ComplexityLevel.COMPLEX),
                    building_category_code=building.building_category_code if building else None
                )

                if complexity == ComplexityLevel.COMPLEX and auto_analyze:
                    # Claude-Analyse für komplexe Gebäude
                    try:
                        print(f"[ANALYZE] Starte Claude-Analyse elevation (Orthofoto: {use_orthofoto})")
                        context = await context_service.analyze_with_claude(
                            egid=str(building.egid),
                            adresse=geo.matched_address,
                            polygon=polygon,
                            height_data=heights_data,
                            gwr_data=gwr_data,
                            include_orthofoto=use_orthofoto,
                            terrain_data=terrain_data
                        )
                        context_service.save_context(context)
                    except Exception as e:
                        print(f"Claude analysis failed: {e}")
                        # Fallback auf Auto-Context
                        context = context_service.create_auto_context(
                            egid=str(building.egid),
                            adresse=geo.matched_address,
                            polygon=polygon,
                            height_data=heights_data,
                            gwr_data=gwr_data
                        )
                else:
                    # Auto-Context für einfache/moderate Gebäude
                    context = context_service.create_auto_context(
                        egid=str(building.egid),
                        adresse=geo.matched_address,
                        polygon=polygon,
                        height_data=heights_data,
                        gwr_data=gwr_data
                    )

            if context and context.zones and len(context.zones) > 1:
                zones = [z.model_dump() for z in context.zones]

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
            zones=zones,
        )

        # SVG generieren
        svg = None

        # Claude API für professionelle SVG-Generierung
        if use_claude and claude_svg_available():
            # Zonen für Claude vorbereiten
            claude_zones = []
            if zones:
                claude_zones = zones
            else:
                # Standard-Zone erstellen wenn keine Zonen vorhanden
                claude_zones = [{
                    "name": "Gebäude",
                    "type": "hauptgebaeude",
                    "building_height_m": eave_height_m,
                    "first_height_m": ridge_height_m or eave_height_m,
                    "description": f"{building.floors if building else 3} Geschosse"
                }]

            # building_data für Prompt-Selektor (Komplexitäts-Erkennung)
            svg_building_data = {
                'gkat': building.building_category_code if building else None,
                'area_m2': building.area_m2 if building else None,
                'sides': len(geometry.polygon) if geometry and geometry.polygon else 4,
                'geschosse': building.floors if building else 3,
                'adresse': geo.matched_address,
            }

            svg = await generate_elevation_with_zones(
                address=geo.matched_address,
                egid=building.egid if building else None,
                width_m=round(length_m, 1),
                floors=building.floors if building else 3,
                zones=claude_zones,
                svg_width=width,
                svg_height=height,
                building_data=svg_building_data
            )

        # Fallback auf Standard-Generator
        if not svg:
            generator = get_svg_generator()
            svg = generator.generate_elevation(building_data, width, height, professional=professional)

        if not svg:
            raise HTTPException(status_code=503, detail="SVG-Generierung fehlgeschlagen")

        return Response(content=svg, media_type="image/svg+xml")

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Visualization error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/visualize/cache",
            tags=["Visualisierung"],
            summary="Claude SVG Cache löschen")
async def clear_visualization_cache(
    address: Optional[str] = Query(None, description="Optional: Nur Cache für diese Adresse löschen")
):
    """Löscht den Claude SVG Cache (für Cross-Section und Elevation)."""
    from app.services.claude_svg_zones import clear_cache
    deleted = clear_cache(address=address)
    return {"message": f"Cache gelöscht: {deleted} Einträge entfernt", "deleted_count": deleted}


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
    # Compact mode für Fassaden-Auswahl (weniger Elemente, mehr Platz für Polygon)
    compact: bool = False
    # Professional mode für hochwertige Ausdrucke (1200x900, Titelblock, Fusszeile)
    professional: bool = False
    # Zusätzliche Felder für Professional Mode
    project_name: Optional[str] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    # Gebäude-Zonen für farbcodierte Darstellung
    zones: Optional[List[Dict[str, Any]]] = None
    # Zugänge (Treppen) für Gerüst
    zugaenge: Optional[List[Dict[str, Any]]] = None


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

        # Bounding Box aus Polygon berechnen für korrekte Skalierung
        bbox_width = None
        bbox_depth = None
        if polygon_coords and len(polygon_coords) >= 3:
            xs = [p[0] for p in polygon_coords]
            ys = [p[1] for p in polygon_coords]
            bbox_width = max(xs) - min(xs)
            bbox_depth = max(ys) - min(ys)

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
            bbox_width_m=round(bbox_width, 1) if bbox_width else None,
            bbox_depth_m=round(bbox_depth, 1) if bbox_depth else None,
            zones=request.zones,
            zugaenge=request.zugaenge,
        )

        generator = get_svg_generator()

        # Professional Mode: gleiche Darstellung, aber mit Schraffur-Patterns
        # Kein Titelblock/Fusszeile - optimiert für mobile Darstellung
        svg = generator.generate_floor_plan(
            building_data,
            request.width,
            request.height,
            compact=request.compact,
            professional=request.professional
        )

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
    firsthoehe: Optional[float] = Query(None, description="Manuelle Firsthöhe (nicht verwendet für Grundriss)"),
    professional: bool = Query(False, description="Professional Mode mit Schraffur-Patterns")
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

        # Bounding Box Dimensionen für korrekte Skalierung
        bbox_width = None
        bbox_depth = None

        if geometry and geometry.sides:
            side_lengths = sorted([s['length_m'] for s in geometry.sides], reverse=True)
            length_m = side_lengths[0]
            width_m = side_lengths[1] if len(side_lengths) > 1 else length_m
            # Polygon-Koordinaten und Seiten für echte Darstellung
            if hasattr(geometry, 'polygon') and geometry.polygon:
                polygon_coords = [[p[0], p[1]] for p in geometry.polygon]
            sides_data = geometry.sides
            # Bounding Box aus Geometry (korrekte Skalierung)
            if hasattr(geometry, 'width_m') and hasattr(geometry, 'depth_m'):
                bbox_width = geometry.width_m
                bbox_depth = geometry.depth_m
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
            bbox_width_m=round(bbox_width, 1) if bbox_width else None,
            bbox_depth_m=round(bbox_depth, 1) if bbox_depth else None,
        )

        generator = get_svg_generator()
        svg = generator.generate_floor_plan(building_data, width, height, professional=professional)

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
# Smarte Suche & Intelligent DB
# ============================================================================

@app.get("/api/v1/search",
         tags=["Smarte Suche"])
async def smart_search(
    q: str = Query(..., min_length=2, description="Suchbegriff (Name, Alias oder Adresse)"),
    limit: int = Query(10, ge=1, le=50, description="Max. Anzahl Ergebnisse")
):
    """
    Smarte Gebäudesuche mit Alias-Unterstützung.

    **Reihenfolge:**
    1. Exakte Alias-Matches ("Bundeshaus" → EGID)
    2. Volltext-Suche (FTS5)
    3. Fallback: Geocoding via swisstopo

    **Beispiele:**
    - `/api/v1/search?q=Bundeshaus` → Findet Bundeshaus direkt
    - `/api/v1/search?q=Münster Bern` → Findet Berner Münster
    - `/api/v1/search?q=Kramgasse 10` → Geocoding-Fallback
    """
    from app.services.intelligent_db import get_intelligent_db_service

    db_service = get_intelligent_db_service()
    results = await db_service.smart_search(q, limit)

    return {
        "query": q,
        "total": len(results),
        "results": [
            {
                "egid": r.egid,
                "adresse": r.adresse,
                "name": r.name,
                "score": round(r.score, 3),
                "source": r.source,
                "coordinates": r.coordinates,
                "has_cached_data": r.has_cached_data,
                "has_cached_svgs": r.has_cached_svgs
            }
            for r in results
        ]
    }


@app.get("/api/v1/search/suggestions",
         tags=["Smarte Suche"])
async def search_suggestions(
    q: str = Query(..., min_length=2, description="Suchbegriff für Autocomplete"),
    limit: int = Query(5, ge=1, le=20, description="Max. Anzahl Vorschläge")
):
    """
    Autocomplete-Vorschläge für Suche.

    **Beispiel:** `/api/v1/search/suggestions?q=Bund`
    """
    from app.services.intelligent_db import get_intelligent_db_service

    db_service = get_intelligent_db_service()
    results = await db_service.smart_search(q, limit)

    suggestions = []
    for r in results:
        if r.name:
            suggestions.append({"text": r.name, "type": "name", "egid": r.egid})
        if r.adresse:
            suggestions.append({"text": r.adresse, "type": "adresse", "egid": r.egid})

    return {"suggestions": suggestions[:limit]}


@app.get("/api/v1/building/{egid}/environment",
         tags=["Smarte Suche"])
async def get_building_environment(
    egid: str,
    refresh: bool = Query(False, description="Cache ignorieren und neu laden")
):
    """
    Umgebungsdaten eines Gebäudes (Nachbarn, blockierte Fassaden).

    **Liefert:**
    - Nachbargebäude im Umkreis
    - Blockierte Fassaden (zu wenig Platz für Gerüst)
    - Terrain-Daten (Hanglage)
    - Erkannte Rundungen

    **Beispiel:** `/api/v1/building/2242547/environment`
    """
    from app.services.intelligent_db import get_intelligent_db_service

    db_service = get_intelligent_db_service()

    # Aus Cache laden wenn nicht refresh
    if not refresh:
        cached = db_service.get_building_environment(egid)
        if cached:
            return {
                "egid": cached.egid,
                "surrounding_buildings": cached.surrounding_buildings,
                "blocked_facades": cached.blocked_facades,
                "terrain_data": cached.terrain_data,
                "curves": cached.curves,
                "from_cache": True,
                "updated_at": cached.updated_at
            }

    # TODO: Live-Abfrage wenn nicht im Cache
    return {
        "egid": egid,
        "surrounding_buildings": [],
        "blocked_facades": [],
        "terrain_data": None,
        "curves": [],
        "from_cache": False,
        "message": "Live-Abfrage noch nicht implementiert"
    }


@app.get("/api/v1/building/{egid}/svg/{svg_type}",
         tags=["SVG Cache"],
         response_class=Response)
async def get_cached_svg(
    egid: str,
    svg_type: str,
    regenerate: bool = Query(False, description="SVG neu generieren")
):
    """
    SVG aus Cache laden oder generieren.

    **SVG-Typen:**
    - `grundriss` - Grundriss mit Polygon
    - `ansicht` - Frontalansicht
    - `schnitt` - Querschnitt

    **Beispiel:** `/api/v1/building/2242547/svg/ansicht`
    """
    from app.services.intelligent_db import get_intelligent_db_service

    db_service = get_intelligent_db_service()

    # Aus Cache laden
    if not regenerate:
        cached = db_service.get_cached_svg(egid, svg_type)
        if cached:
            return Response(
                content=cached.svg_content,
                media_type="image/svg+xml",
                headers={
                    "X-Cache": "HIT",
                    "X-Generated-By": cached.generated_by,
                    "X-Created-At": cached.created_at
                }
            )

    # TODO: SVG generieren wenn nicht im Cache
    raise HTTPException(
        status_code=404,
        detail=f"SVG {svg_type} für EGID {egid} nicht im Cache. Nutze /api/v1/visualize/* Endpoints."
    )


@app.post("/api/v1/building/{egid}/svg/{svg_type}",
          tags=["SVG Cache"])
async def save_svg_to_cache(
    egid: str,
    svg_type: str,
    svg_content: str = Query(..., description="SVG-Inhalt"),
    generated_by: str = Query("manual", description="Quelle: auto, claude_api, claude_ai, manual")
):
    """
    SVG im Cache speichern.

    **Beispiel:** Manuell erstelltes SVG cachen.
    """
    from app.services.intelligent_db import get_intelligent_db_service

    db_service = get_intelligent_db_service()
    cache_key = db_service.set_cached_svg(
        egid=egid,
        svg_type=svg_type,
        svg_content=svg_content,
        generated_by=generated_by
    )

    return {
        "status": "cached",
        "cache_key": cache_key,
        "egid": egid,
        "svg_type": svg_type
    }


@app.delete("/api/v1/building/{egid}/svg",
            tags=["SVG Cache"])
async def invalidate_svg_cache(
    egid: str,
    svg_type: Optional[str] = Query(None, description="Nur bestimmten Typ löschen")
):
    """
    SVG-Cache für ein Gebäude invalidieren.

    **Beispiel:** `/api/v1/building/2242547/svg?svg_type=ansicht`
    """
    from app.services.intelligent_db import get_intelligent_db_service

    db_service = get_intelligent_db_service()
    count = db_service.invalidate_svg_cache(egid, svg_type)

    return {
        "status": "invalidated",
        "egid": egid,
        "svg_type": svg_type or "all",
        "deleted_count": count
    }


@app.get("/api/v1/db/stats",
         tags=["System"])
async def get_intelligent_db_stats():
    """
    Statistiken der intelligenten Datenbank.

    **Liefert:**
    - Anzahl Gebäude (gesamt, Landmarks)
    - SVG-Cache Statistiken
    - Research-Cache Statistiken
    - Datenbank-Grösse
    """
    from app.services.intelligent_db import get_intelligent_db_service

    db_service = get_intelligent_db_service()
    return db_service.get_stats()


@app.post("/api/v1/db/seed-landmarks",
          tags=["System"])
async def seed_landmark_buildings():
    """
    Bekannte Schweizer Gebäude als Seed-Daten hinzufügen.

    **Fügt hinzu:**
    - Bundeshaus
    - Berner Münster
    - Kirche St. Peter und Paul
    - Zytglogge

    **Idempotent:** Kann mehrfach aufgerufen werden.
    """
    from app.services.intelligent_db import get_intelligent_db_service

    db_service = get_intelligent_db_service()
    db_service.seed_landmark_buildings()

    return {
        "status": "seeded",
        "message": "Landmark buildings added successfully"
    }


# ============================================================================
# Prompt Generation API (NEU 29.12.2025)
# ============================================================================

@app.get("/api/v1/prompt/generate",
         tags=["Prompt Generation"],
         summary="Generiert Claude-Prompt für SVG-Erstellung")
async def generate_claude_prompt(
    address: str,
    svg_type: str = Query("all", description="SVG-Typ: all, grundriss, ansicht, schnitt"),
    include_research: bool = Query(True, description="Dynamische Claude-Recherche durchführen"),
    force_refresh: bool = Query(False, description="Cache ignorieren")
):
    """
    Generiert einen strukturierten Prompt für Claude SVG-Generierung.

    Verwendet SmartBuildingService + UnifiedPromptGenerator für
    IDENTISCHE Prompts bei Export und automatischer SVG-Generierung.

    **Features:**
    - 10-Schritte Datenpipeline (Geocoding, GWR, Höhen, Terrain, etc.)
    - Automatische Turm-Erkennung bei extremer Höhendifferenz
    - Dynamische Gebäude-Recherche via Claude API (gecacht)
    - Höhenzonen für komplexe Gebäude

    **Kosten:**
    - Gecachtes Bundle: $0.00
    - Neues Bundle mit Recherche: ca. $0.01-0.02

    **Verwendung:**
    - Frontend Export-Button → Clipboard → Claude.ai
    - Backend SVG-Generierung → Identischer Prompt
    """
    try:
        from app.services.smart_building import get_smart_building_service, get_prompt_generator, SVGType

        # SVG-Typ parsen
        svg_type_enum = SVGType.ALL
        if svg_type.lower() == "grundriss":
            svg_type_enum = SVGType.GRUNDRISS
        elif svg_type.lower() == "ansicht":
            svg_type_enum = SVGType.ANSICHT
        elif svg_type.lower() == "schnitt":
            svg_type_enum = SVGType.SCHNITT

        # Daten sammeln via SmartBuildingService
        service = get_smart_building_service()
        bundle = await service.collect_all_data(
            address=address,
            force_refresh=force_refresh,
            include_research=include_research,
            include_zones_analysis=True,
            include_terrain=True
        )

        if not bundle.address_matched:
            raise HTTPException(status_code=404, detail="Adresse nicht gefunden")

        # Prompt generieren via UnifiedPromptGenerator
        generator = get_prompt_generator()
        prompt = generator.generate(
            bundle=bundle,
            svg_type=svg_type_enum,
            include_style_guide=True
        )

        return {
            "prompt": prompt,
            "address": bundle.address_matched,
            "egid": bundle.egid,
            "svg_type": svg_type,
            "research_included": include_research,
            "complexity": bundle.complexity,
            "zones_count": len(bundle.zones),
            "building_type": bundle.building_type,
            "data_sources": [s.value for s in bundle.data_sources]
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/prompt/research/stats",
         tags=["Prompt Generation"],
         summary="Statistiken des Recherche-Cache")
async def get_research_cache_stats():
    """
    Gibt Statistiken des Claude-Recherche-Cache zurück.

    **Informationen:**
    - Anzahl gecachter Einträge
    - Anzahl abgelaufener Einträge
    - Geschätzte Gesamtkosten
    - Token-Verbrauch
    """
    from app.services.prompts import get_research_service

    service = get_research_service()
    stats = service.get_cache_stats()

    return {
        "status": "ok",
        "cache": stats
    }


@app.post("/api/v1/prompt/research/clear-expired",
          tags=["Prompt Generation"],
          summary="Löscht abgelaufene Cache-Einträge")
async def clear_expired_research_cache():
    """
    Löscht abgelaufene Einträge aus dem Recherche-Cache.

    **Hinweis:** Cache-Einträge haben eine TTL von 30 Tagen.
    """
    from app.services.prompts import get_research_service

    service = get_research_service()
    deleted = service.clear_expired_cache()

    return {
        "status": "ok",
        "deleted_entries": deleted
    }


# ============================================================================
# SmartBuildingService API (NEU 29.12.2025)
# ============================================================================

@app.get("/api/v1/smart-building/data",
         tags=["Smart Building"],
         summary="Sammelt alle Gebäudedaten für Gerüstplanung")
async def get_smart_building_data(
    address: str,
    force_refresh: bool = Query(False, description="Cache ignorieren"),
    include_research: bool = Query(True, description="Claude-Recherche für Gebäude-Identifikation"),
    include_zones_analysis: bool = Query(True, description="Claude-Analyse für komplexe Gebäude"),
    include_terrain: bool = Query(True, description="Terrain-Daten (Hanglage) abrufen"),
):
    """
    Sammelt schrittweise alle verfügbaren Daten für ein Gebäude.

    **Datenquellen (10 Schritte):**
    1. Geocoding (Adresse → Koordinaten, EGID)
    2. GWR-Daten (Kategorie, Geschosse, Fläche)
    3. Höhendaten (swissBUILDINGS3D)
    4. Terrain (swissALTI3D, Hanglage-Erkennung)
    5. Polygon & Fassaden (geodienste.ch)
    6. Dach-Analyse (berechnet)
    7. Gebäude-Recherche (Claude Sonnet)
    8. Zonen-Analyse (Claude Sonnet - nur bei komplexen Gebäuden)
    9. SUVA Zugangspunkte (berechnet)
    10. Qualitätsbewertung

    **Cache:** 24 Stunden TTL

    **Kosten:**
    - Cache-Hit: $0.00
    - Recherche (Sonnet): ~$0.03-0.05
    - Zonen-Analyse (Sonnet): ~$0.05-0.10 (nur bei komplexen Gebäuden)
    """
    try:
        from app.services.smart_building import get_smart_building_service

        service = get_smart_building_service()
        bundle = await service.collect_all_data(
            address=address,
            force_refresh=force_refresh,
            include_research=include_research,
            include_zones_analysis=include_zones_analysis,
            include_terrain=include_terrain,
        )

        # Flache Struktur für Frontend SmartBuildingData Interface
        return {
            # Identifikation
            "egid": bundle.egid,
            "address_input": bundle.address_input,
            "address_matched": bundle.address_matched,
            "lv95_e": bundle.lv95_e,
            "lv95_n": bundle.lv95_n,

            # Gebäude-Identifikation (aus Recherche)
            "building_name": bundle.building_name,
            "building_type": bundle.building_type,
            "architectural_style": bundle.architectural_style,
            "construction_year": bundle.construction_year,

            # GWR-Daten
            "gwr_category": bundle.gwr_category,
            "gwr_category_code": bundle.gwr_category_code,
            "gwr_floors": bundle.gwr_floors,
            "gwr_area_m2": bundle.gwr_area_m2,

            # Geometrie
            "polygon": bundle.polygon,
            "polygon_simplified": bundle.polygon_simplified,
            "sides": bundle.sides,
            "perimeter_m": bundle.perimeter_m,
            "footprint_area_m2": bundle.footprint_area_m2,
            "bbox_width_m": bundle.bbox_width_m,
            "bbox_depth_m": bundle.bbox_depth_m,

            # Höhendaten
            "traufhoehe_m": bundle.traufhoehe_m,
            "firsthoehe_m": bundle.firsthoehe_m,
            "gebaeudehoehe_m": bundle.gebaeudehoehe_m,
            "height_source": bundle.height_source.value if bundle.height_source else None,
            "height_quality": bundle.height_quality.value if bundle.height_quality else None,
            "estimated_height_m": bundle.estimated_height_m,
            "floors_estimated": bundle.gwr_floors,

            # Terrain
            "terrain": {
                "reference_height_m": bundle.terrain.reference_height_m,
                "min_height_m": bundle.terrain.min_height_m,
                "max_height_m": bundle.terrain.max_height_m,
                "slope_m": bundle.terrain.slope_m,
                "is_sloped": bundle.terrain.is_sloped,
                "slope_direction": bundle.terrain.slope_direction,
                "requires_level_compensation": bundle.terrain.requires_level_compensation,
            } if bundle.terrain else None,

            # Dach
            "roof_type": bundle.roof_type,
            "roof_angle_deg": bundle.roof_angle_deg,
            "roof_orientation": bundle.roof_orientation,
            "roof_area_m2": bundle.roof_area_m2,
            "roof_confidence": bundle.roof_confidence,

            # Zonen
            "zones": [
                {
                    "id": z.id,
                    "name": z.name,
                    "zone_type": z.zone_type,
                    "traufhoehe_m": z.traufhoehe_m,
                    "firsthoehe_m": z.firsthoehe_m,
                    "gebaeudehoehe_m": z.gebaeudehoehe_m,
                    "fassaden_ids": z.fassaden_ids,
                    "beruesten": z.beruesten,
                    "sonderkonstruktion": z.sonderkonstruktion,
                    "confidence": z.confidence,
                    "source": z.source.value if z.source else None,
                    "notes": z.notes,
                }
                for z in bundle.zones
            ],
            "complexity": bundle.complexity,
            "has_height_variations": bundle.has_height_variations,
            "has_towers": bundle.has_towers,
            "has_annexes": bundle.has_annexes,
            "has_courtyards": bundle.has_courtyards,

            # Zugänge
            "access_points": [
                {
                    "id": a.id,
                    "fassade_id": a.fassade_id,
                    "position_percent": a.position_percent,
                    "reason": a.reason,
                    "suva_compliant": a.suva_compliant,
                }
                for a in bundle.access_points
            ],
            "suva_compliant": bundle.suva_compliant,

            # Meta
            "data_sources": [s.value for s in bundle.data_sources],
            "overall_quality": bundle.overall_quality.value if bundle.overall_quality else None,
            "research_confidence": bundle.research_confidence,
            "analysis_confidence": bundle.analysis_confidence,
            "warnings": bundle.warnings,
            "errors": bundle.errors,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/smart-building/prompt",
         tags=["Smart Building"],
         summary="Generiert einheitlichen Prompt aus SmartBuildingService")
async def get_smart_building_prompt(
    address: str,
    svg_type: str = Query("all", description="SVG-Typ: all, grundriss, ansicht, schnitt, umgebung"),
    force_refresh: bool = Query(False, description="Cache ignorieren"),
    include_style_guide: bool = Query(True, description="Style-Vorgaben im Prompt"),
):
    """
    Generiert einen einheitlichen Prompt für SVG-Erstellung.

    **WICHTIG:** Identischer Prompt für:
    - Export-Button → Claude.ai (manuell)
    - Claude API → Automatische SVG-Generierung

    **Vorteile gegenüber /api/v1/prompt/generate:**
    - Nutzt SmartBuildingService (einheitliche Datenpipeline)
    - Bundle-Caching (24h TTL)
    - Erweiterbar für Umgebungsplan
    - Strukturiertes BuildingDataBundle
    """
    try:
        from app.services.smart_building import (
            get_smart_building_service,
            get_prompt_generator,
            SVGType,
        )

        # SVG-Typ parsen
        svg_type_enum = SVGType.ALL
        if svg_type.lower() == "grundriss":
            svg_type_enum = SVGType.GRUNDRISS
        elif svg_type.lower() == "ansicht":
            svg_type_enum = SVGType.ANSICHT
        elif svg_type.lower() == "schnitt":
            svg_type_enum = SVGType.SCHNITT
        elif svg_type.lower() == "umgebung":
            svg_type_enum = SVGType.UMGEBUNG

        # Daten sammeln
        service = get_smart_building_service()
        bundle = await service.collect_all_data(
            address=address,
            force_refresh=force_refresh,
            include_research=True,
            include_zones_analysis=True,
            include_terrain=True,
        )

        # Prompt generieren
        generator = get_prompt_generator()
        prompt = generator.generate(
            bundle=bundle,
            svg_type=svg_type_enum,
            include_style_guide=include_style_guide,
        )

        return {
            "status": "ok",
            "prompt": prompt,
            "address": bundle.address_matched,
            "egid": bundle.egid,
            "svg_type": svg_type,
            "zones_count": len(bundle.zones),
            "complexity": bundle.complexity,
            "data_sources": [s.value for s in bundle.data_sources],
            "prompt_length": len(prompt),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/smart-building/cache/stats",
         tags=["Smart Building"],
         summary="Cache-Statistiken des SmartBuildingService")
async def get_smart_building_cache_stats():
    """
    Gibt Statistiken des BuildingDataBundle-Cache zurück.
    """
    try:
        import sqlite3
        from pathlib import Path
        import os

        DATA_DIR = Path(os.getenv("DATA_DIR", "app/data"))
        DB_PATH = DATA_DIR / "building_contexts.db"

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Anzahl Einträge
        cursor.execute("SELECT COUNT(*) FROM smart_building_cache")
        total = cursor.fetchone()[0]

        # Abgelaufene Einträge
        from datetime import datetime
        now = datetime.now().isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM smart_building_cache
            WHERE expires_at < ?
        """, (now,))
        expired = cursor.fetchone()[0]

        conn.close()

        return {
            "status": "ok",
            "cache": {
                "total_entries": total,
                "active_entries": total - expired,
                "expired_entries": expired,
                "ttl_hours": 24,
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "cache": {
                "total_entries": 0,
                "active_entries": 0,
                "expired_entries": 0,
            }
        }


@app.get("/api/v1/smart-building/svg",
         tags=["Smart Building"],
         summary="Generiert SVG via SmartBuildingService")
async def generate_smart_building_svg(
    address: str,
    svg_type: str = Query("schnitt", description="SVG-Typ: schnitt, ansicht, grundriss"),
    force_refresh: bool = Query(False, description="ALLE Caches ignorieren (Bundle, Recherche, SVG)"),
):
    """
    Generiert SVG mit vollständiger Cache-Kontrolle.

    **force_refresh=true umgeht ALLE Caches:**
    - SmartBuilding Bundle Cache (24h)
    - Claude Recherche Cache (30 Tage)
    - SVG Cache

    **Ideal für:**
    - Prompt-Entwicklung und Testing
    - Nach Änderungen an Prompt-Templates
    - Frische Daten nach Höhen-Import

    **Kosten bei force_refresh:**
    - Einfaches Gebäude: ~$0.05-0.10 (Sonnet + Sonnet)
    - Komplexes Gebäude: ~$0.10-0.20 (Sonnet + 2x Sonnet)
    """
    try:
        from app.services.claude_svg_zones import (
            generate_svg_with_smart_service,
            is_available,
        )

        if not is_available():
            raise HTTPException(
                status_code=503,
                detail="Claude API nicht verfügbar (ANTHROPIC_API_KEY fehlt)"
            )

        svg = await generate_svg_with_smart_service(
            address=address,
            svg_type=svg_type,
            force_refresh=force_refresh,
        )

        if not svg:
            raise HTTPException(
                status_code=500,
                detail="SVG-Generierung fehlgeschlagen"
            )

        return Response(
            content=svg,
            media_type="image/svg+xml",
            headers={
                "X-Force-Refresh": str(force_refresh),
                "X-SVG-Type": svg_type,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/smart-building/cache",
            tags=["Smart Building"],
            summary="Löscht alle SmartBuilding Caches")
async def clear_smart_building_cache(
    address: Optional[str] = Query(None, description="Nur für diese Adresse löschen"),
    cache_type: str = Query("all", description="all, bundle, research, svg"),
):
    """
    Löscht SmartBuilding Cache-Einträge.

    **cache_type:**
    - `all`: Alle Caches (Bundle + Research + SVG)
    - `bundle`: Nur BuildingDataBundle Cache
    - `research`: Nur Claude Recherche Cache
    - `svg`: Nur SVG Cache
    """
    try:
        import sqlite3
        from pathlib import Path
        import os

        DATA_DIR = Path(os.getenv("DATA_DIR", "app/data"))
        DB_PATH = DATA_DIR / "building_contexts.db"
        SVG_CACHE_PATH = DATA_DIR.parent / "services" / "claude_svg_cache.db"

        deleted = {"bundle": 0, "research": 0, "svg": 0}

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # Bundle Cache (Tabelle existiert evtl. noch nicht)
        if cache_type in ["all", "bundle"]:
            try:
                if address:
                    cursor.execute(
                        "DELETE FROM smart_building_cache WHERE address LIKE ?",
                        (f"%{address}%",)
                    )
                else:
                    cursor.execute("DELETE FROM smart_building_cache")
                deleted["bundle"] = cursor.rowcount
            except sqlite3.OperationalError:
                # Tabelle existiert noch nicht
                deleted["bundle"] = 0

        # Research Cache (Tabelle existiert evtl. noch nicht)
        if cache_type in ["all", "research"]:
            try:
                if address:
                    cursor.execute(
                        "DELETE FROM claude_research_cache WHERE adresse LIKE ?",
                        (f"%{address}%",)
                    )
                else:
                    cursor.execute("DELETE FROM claude_research_cache")
                deleted["research"] = cursor.rowcount
            except sqlite3.OperationalError:
                # Tabelle existiert noch nicht
                deleted["research"] = 0

        conn.commit()
        conn.close()

        # SVG Cache (separate Datenbank)
        if cache_type in ["all", "svg"]:
            try:
                from app.services.claude_svg_zones import clear_svg_cache
                if address:
                    # SVG Cache hat keine Adress-Suche, nur EGID
                    deleted["svg"] = 0
                else:
                    deleted["svg"] = clear_svg_cache()
            except Exception:
                deleted["svg"] = 0

        return {
            "status": "ok",
            "deleted": deleted,
            "total": sum(deleted.values()),
            "address_filter": address,
            "cache_type": cache_type,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
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
