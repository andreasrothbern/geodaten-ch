# backend/app/services/smart_building/service.py
"""
SmartBuildingService - Orchestriert alle Datenquellen.

Sammelt PARALLEL alle Daten die für Gerüstplanung benötigt werden:

PHASE 1 (sequentiell - MUSS zuerst):
  - Geocoding (Adresse → Koordinaten, EGID)

PHASE 2 (parallel - brauchen nur Koordinaten):
  - GWR-Daten (Kategorie, Geschosse, Fläche)
  - Höhendaten (swissBUILDINGS3D)
  - Polygon & Fassaden (geodienste.ch)
  - Terrain (swissALTI3D, Hanglage)

PHASE 3 (parallel - brauchen Phase 2 Ergebnisse):
  - Dach-Analyse (berechnet aus Höhen + Polygon)
  - Gebäude-Recherche (Claude Haiku)

PHASE 4 (sequentiell - braucht alles):
  - Zonen-Analyse (Claude Sonnet - nur bei komplexen Gebäuden)

PHASE 5 (synchron - schnelle Berechnungen):
  - SUVA Zugangspunkte
  - Qualitätsbewertung

CACHING:
  - BuildingDataBundle wird für 24h in SQLite gecacht
  - Bei erneutem Aufruf: ~50ms statt ~3-5s
"""

import asyncio
import logging
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import os

from .models import (
    BuildingDataBundle,
    DataSource,
    DataQuality,
    ZoneInfo,
    TerrainProfile,
    AccessPoint,
)

logger = logging.getLogger(__name__)

# Datenbank
DATA_DIR = Path(os.getenv("DATA_DIR", "app/data"))
DB_PATH = DATA_DIR / "building_contexts.db"

# Cache TTL
BUNDLE_CACHE_TTL_HOURS = 24  # Bundle-Cache für 24 Stunden


class SmartBuildingService:
    """
    Zentraler Service für Gebäudedaten-Sammlung.

    Verwendung:
        service = get_smart_building_service()
        bundle = await service.collect_all_data("Bundesplatz 3, 3011 Bern")
        prompt = service.generate_prompt(bundle, svg_type="all")

    Request-Deduplizierung:
        Parallele Anfragen für dieselbe Adresse werden dedupliziert.
        Nur eine Anfrage wird tatsächlich ausgeführt, andere warten auf das Ergebnis.
    """

    def __init__(self):
        self._ensure_tables()
        self._services_cache = {}
        # Request-Deduplizierung: Locks pro Adresse verhindern doppelte API-Calls
        self._address_locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()  # Für Lock-Erstellung

    def _ensure_tables(self):
        """Erstellt Cache-Tabelle für Bundles"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smart_building_cache (
                cache_key TEXT PRIMARY KEY,
                address TEXT,
                egid TEXT,
                bundle_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                version TEXT DEFAULT '1.0'
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_smart_cache_address
            ON smart_building_cache(address)
        """)

        conn.commit()
        conn.close()

    def _cache_key(self, address: str, egid: Optional[str] = None) -> str:
        """Generiert Cache-Key"""
        key = f"{address}|{egid or ''}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _get_cached_bundle(self, cache_key: str) -> Optional[BuildingDataBundle]:
        """Holt Bundle aus Cache"""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT bundle_json, expires_at
            FROM smart_building_cache
            WHERE cache_key = ?
        """, (cache_key,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Expiration prüfen
        expires_at = datetime.fromisoformat(row['expires_at'])
        if datetime.now() > expires_at:
            logger.info(f"Cache expired for {cache_key}")
            return None

        try:
            data = json.loads(row['bundle_json'])
            bundle = self._dict_to_bundle(data)
            bundle.add_source(DataSource.CACHE)
            return bundle
        except Exception as e:
            logger.warning(f"Cache parse error: {e}")
            return None

    def _save_bundle_cache(self, cache_key: str, bundle: BuildingDataBundle):
        """Speichert Bundle im Cache"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        now = datetime.now()
        expires = now + timedelta(hours=BUNDLE_CACHE_TTL_HOURS)

        bundle_dict = self._bundle_to_dict(bundle)

        cursor.execute("""
            INSERT OR REPLACE INTO smart_building_cache
            (cache_key, address, egid, bundle_json, created_at, expires_at, version)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            cache_key,
            bundle.address_matched,
            bundle.egid,
            json.dumps(bundle_dict, ensure_ascii=False, default=str),
            now.isoformat(),
            expires.isoformat(),
            "1.0"
        ))

        conn.commit()
        conn.close()

    def _bundle_to_dict(self, bundle: BuildingDataBundle) -> Dict[str, Any]:
        """Konvertiert Bundle zu Dictionary (für JSON)"""
        return {
            "egid": bundle.egid,
            "address_input": bundle.address_input,
            "address_matched": bundle.address_matched,
            "lv95_e": bundle.lv95_e,
            "lv95_n": bundle.lv95_n,
            "building_name": bundle.building_name,
            "building_type": bundle.building_type,
            "architectural_style": bundle.architectural_style,
            "construction_year": bundle.construction_year,
            "gwr_category": bundle.gwr_category,
            "gwr_category_code": bundle.gwr_category_code,
            "gwr_floors": bundle.gwr_floors,
            "gwr_area_m2": bundle.gwr_area_m2,
            "polygon": bundle.polygon,
            "sides": bundle.sides,
            "perimeter_m": bundle.perimeter_m,
            "footprint_area_m2": bundle.footprint_area_m2,
            "bbox_width_m": bundle.bbox_width_m,
            "bbox_depth_m": bundle.bbox_depth_m,
            "traufhoehe_m": bundle.traufhoehe_m,
            "firsthoehe_m": bundle.firsthoehe_m,
            "gebaeudehoehe_m": bundle.gebaeudehoehe_m,
            "height_source": bundle.height_source.value if bundle.height_source else None,
            "terrain": {
                "reference_height_m": bundle.terrain.reference_height_m,
                "slope_m": bundle.terrain.slope_m,
                "is_sloped": bundle.terrain.is_sloped,
                "facade_heights": bundle.terrain.facade_heights,
            } if bundle.terrain else None,
            "roof_type": bundle.roof_type,
            "roof_angle_deg": bundle.roof_angle_deg,
            "roof_orientation": bundle.roof_orientation,
            "zones": [
                {
                    "id": z.id,
                    "name": z.name,
                    "zone_type": z.zone_type,
                    "traufhoehe_m": z.traufhoehe_m,
                    "firsthoehe_m": z.firsthoehe_m,
                    "gebaeudehoehe_m": z.gebaeudehoehe_m,
                    "beruesten": z.beruesten,
                    "sonderkonstruktion": z.sonderkonstruktion,
                    "confidence": z.confidence,
                }
                for z in bundle.zones
            ],
            "complexity": bundle.complexity,
            "access_points": [
                {"id": a.id, "fassade_id": a.fassade_id, "position_percent": a.position_percent}
                for a in bundle.access_points
            ],
            "data_sources": [s.value for s in bundle.data_sources],
            "warnings": bundle.warnings,
            "collection_timestamp": bundle.collection_timestamp.isoformat() if bundle.collection_timestamp else None,
        }

    def _dict_to_bundle(self, data: Dict[str, Any]) -> BuildingDataBundle:
        """Konvertiert Dictionary zurück zu Bundle"""
        bundle = BuildingDataBundle(
            egid=data.get("egid"),
            address_input=data.get("address_input"),
            address_matched=data.get("address_matched"),
            lv95_e=data.get("lv95_e"),
            lv95_n=data.get("lv95_n"),
            building_name=data.get("building_name"),
            building_type=data.get("building_type"),
            architectural_style=data.get("architectural_style"),
            construction_year=data.get("construction_year"),
            gwr_category=data.get("gwr_category"),
            gwr_category_code=data.get("gwr_category_code"),
            gwr_floors=data.get("gwr_floors"),
            gwr_area_m2=data.get("gwr_area_m2"),
            polygon=data.get("polygon"),
            sides=data.get("sides"),
            perimeter_m=data.get("perimeter_m"),
            footprint_area_m2=data.get("footprint_area_m2"),
            bbox_width_m=data.get("bbox_width_m"),
            bbox_depth_m=data.get("bbox_depth_m"),
            traufhoehe_m=data.get("traufhoehe_m"),
            firsthoehe_m=data.get("firsthoehe_m"),
            gebaeudehoehe_m=data.get("gebaeudehoehe_m"),
            roof_type=data.get("roof_type"),
            roof_angle_deg=data.get("roof_angle_deg"),
            roof_orientation=data.get("roof_orientation"),
            complexity=data.get("complexity", "simple"),
            warnings=data.get("warnings", []),
        )

        # Terrain
        if data.get("terrain"):
            t = data["terrain"]
            bundle.terrain = TerrainProfile(
                reference_height_m=t.get("reference_height_m", 0),
                slope_m=t.get("slope_m"),
                is_sloped=t.get("is_sloped", False),
                facade_heights=t.get("facade_heights", {}),
            )

        # Zonen
        for z in data.get("zones", []):
            bundle.zones.append(ZoneInfo(
                id=z.get("id", "zone_1"),
                name=z.get("name", "Hauptgebäude"),
                zone_type=z.get("zone_type", "hauptgebaeude"),
                traufhoehe_m=z.get("traufhoehe_m"),
                firsthoehe_m=z.get("firsthoehe_m"),
                gebaeudehoehe_m=z.get("gebaeudehoehe_m"),
                beruesten=z.get("beruesten", True),
                sonderkonstruktion=z.get("sonderkonstruktion", False),
                confidence=z.get("confidence", 0.8),
            ))

        # Zugänge
        for a in data.get("access_points", []):
            bundle.access_points.append(AccessPoint(
                id=a.get("id", "Z1"),
                fassade_id=a.get("fassade_id", "N"),
                position_percent=a.get("position_percent", 0.5),
                reason=a.get("reason", ""),
            ))

        # Data Sources
        for s in data.get("data_sources", []):
            try:
                bundle.data_sources.append(DataSource(s))
            except ValueError:
                pass

        return bundle

    async def _get_address_lock(self, cache_key: str) -> asyncio.Lock:
        """Holt oder erstellt Lock für eine Adresse (thread-safe)"""
        async with self._global_lock:
            if cache_key not in self._address_locks:
                self._address_locks[cache_key] = asyncio.Lock()
            return self._address_locks[cache_key]

    async def collect_all_data(
        self,
        address: str,
        force_refresh: bool = False,
        include_research: bool = True,
        include_zones_analysis: bool = True,
        include_terrain: bool = True,
        include_neighbors: bool = False,  # TODO
    ) -> BuildingDataBundle:
        """
        Sammelt alle verfügbaren Daten für ein Gebäude.

        Args:
            address: Schweizer Adresse
            force_refresh: Cache ignorieren
            include_research: Claude-Recherche für Gebäude-Identifikation
            include_zones_analysis: Claude-Analyse für komplexe Gebäude
            include_terrain: Terrain-Daten abrufen
            include_neighbors: Nachbargebäude analysieren (TODO)

        Returns:
            BuildingDataBundle mit allen gesammelten Daten

        Request-Deduplizierung:
            Bei parallelen Anfragen für dieselbe Adresse wartet die zweite
            Anfrage auf das Ergebnis der ersten (via asyncio.Lock).
            Dies verhindert doppelte API-Calls zu swisstopo/geodienste.ch.
        """
        cache_key = self._cache_key(address)

        # 1. Quick Cache Check (ohne Lock - read-only)
        if not force_refresh:
            cached = self._get_cached_bundle(cache_key)
            if cached:
                logger.info(f"Using cached bundle for {address}")
                return cached

        # 2. Request-Deduplizierung: Lock pro Adresse
        address_lock = await self._get_address_lock(cache_key)

        async with address_lock:
            # Double-Check nach Lock-Erwerb (andere Anfrage könnte fertig sein)
            if not force_refresh:
                cached = self._get_cached_bundle(cache_key)
                if cached:
                    logger.info(f"Using cached bundle for {address} (waited for other request)")
                    return cached

            logger.info(f"Collecting data for {address} (holding lock)")

            # 3. Neues Bundle erstellen
            bundle = BuildingDataBundle(
                address_input=address,
                collection_timestamp=datetime.now(),
            )

            # 4. Daten sammeln (OPTIMIERT: Parallelisierung wo möglich)

            # PHASE 1: Geocoding MUSS zuerst (liefert Koordinaten + EGID)
            await self._collect_geocoding(bundle)

            if not bundle.lv95_e or not bundle.lv95_n:
                logger.error(f"Geocoding failed for {address}, cannot proceed")
                bundle.add_error("Geocoding fehlgeschlagen - keine weiteren Daten verfügbar")
                return bundle

            # PHASE 2a: GWR zuerst (setzt EGID, die Heights braucht)
            await self._collect_gwr_data(bundle)

            # PHASE 2b: Parallel - Heights braucht EGID von GWR
            phase2_tasks = [
                self._collect_height_data(bundle),
                self._collect_polygon_data(bundle),
            ]
            if include_terrain:
                phase2_tasks.append(self._collect_terrain_data(bundle))

            await asyncio.gather(*phase2_tasks, return_exceptions=True)
            logger.info(f"Phase 2 complete: GWR, Heights, Polygon, Terrain")

            # PHASE 3: Parallel - brauchen Ergebnisse aus Phase 2
            phase3_tasks = [
                self._calculate_roof_data(bundle),  # braucht Höhen + Polygon
            ]
            if include_research:
                phase3_tasks.append(self._collect_research_data(bundle, force_refresh))  # braucht GWR

            await asyncio.gather(*phase3_tasks, return_exceptions=True)
            logger.info(f"Phase 3 complete: Roof, Research")

            # PHASE 4: Sequentiell - braucht alles vorher
            if include_zones_analysis and self._needs_zones_analysis(bundle):
                await self._collect_zones_analysis(bundle)
            else:
                self._create_default_zone(bundle)

            # PHASE 5: Berechnungen (synchron, schnell)
            self._calculate_access_points(bundle)

            if include_neighbors:
                await self._collect_neighbor_data(bundle)

            # 5. Qualität bewerten
            self._assess_data_quality(bundle)

            # 6. Cache speichern
            self._save_bundle_cache(cache_key, bundle)

            logger.info(f"Collected data from {len(bundle.data_sources)} sources for {address}")
            return bundle

    async def _collect_geocoding(self, bundle: BuildingDataBundle):
        """Schritt 1: Geocoding"""
        try:
            from app.services.swisstopo import SwisstopoService
            swisstopo = SwisstopoService()

            geo = await swisstopo.geocode(bundle.address_input)
            if geo:
                bundle.address_matched = geo.matched_address
                bundle.lv95_e = geo.coordinates.lv95_e
                bundle.lv95_n = geo.coordinates.lv95_n
                bundle.add_source(DataSource.SWISSTOPO_GEOCODING)

                # EGID aus Geocoding (falls vorhanden)
                if hasattr(geo, 'egid') and geo.egid:
                    bundle.egid = str(geo.egid)
            else:
                bundle.add_error(f"Geocoding fehlgeschlagen für: {bundle.address_input}")

        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            bundle.add_error(f"Geocoding-Fehler: {str(e)}")

    async def _collect_gwr_data(self, bundle: BuildingDataBundle):
        """Schritt 2: GWR-Daten"""
        if not bundle.lv95_e or not bundle.lv95_n:
            return

        try:
            from app.services.swisstopo import SwisstopoService
            swisstopo = SwisstopoService()

            buildings = await swisstopo.identify_buildings(
                bundle.lv95_e, bundle.lv95_n, tolerance=15
            )

            if buildings:
                building = buildings[0]
                bundle.egid = str(building.egid) if building.egid else bundle.egid
                bundle.gwr_floors = building.floors
                bundle.gwr_area_m2 = building.area_m2
                bundle.gwr_category = building.building_category
                bundle.gwr_category_code = building.building_category_code
                bundle.footprint_area_m2 = building.area_m2  # BuildingInfo hat area_m2, nicht footprint_area_m2
                bundle.add_source(DataSource.SWISSTOPO_GWR)

        except Exception as e:
            logger.error(f"GWR error: {e}")
            bundle.add_warning(f"GWR-Daten nicht verfügbar: {str(e)}")

    async def _collect_height_data(self, bundle: BuildingDataBundle):
        """Schritt 3: Höhendaten aus swissBUILDINGS3D

        Nutzt die vollständige Lookup-Strategie aus geodienste.py:
        1. EGID-Lookup (building_heights_detailed)
        2. EGID-Legacy (building_heights)
        3. Koordinaten-Lookup (building_heights_by_coord)
        4. Geschätzt aus GWR-Daten (Geschosse × Geschosshöhe)
        5. Standard nach Kategorie (EFH: 8m, MFH: 12m, etc.)

        Falls lokal keine Daten: On-Demand Import via STAC API.
        """
        try:
            from app.services.geodienste import get_height_details

            # EGID als int konvertieren
            egid_int = None
            if bundle.egid:
                try:
                    egid_int = int(bundle.egid)
                except (ValueError, TypeError):
                    pass

            # Vollständige Höhen-Lookup-Strategie aus geodienste.py nutzen
            height_result = get_height_details(
                floors=bundle.gwr_floors,
                building_category_code=bundle.gwr_category_code,
                manual_height=None,
                egid=egid_int,
                lv95_e=bundle.lv95_e,
                lv95_n=bundle.lv95_n,
            )

            # Ergebnisse übernehmen
            bundle.traufhoehe_m = height_result.get('traufhoehe_m')
            bundle.firsthoehe_m = height_result.get('firsthoehe_m')
            bundle.gebaeudehoehe_m = height_result.get('gebaeudehoehe_m')
            bundle.estimated_height_m = height_result.get('estimated_height_m')

            # Quelle bestimmen
            if height_result.get('measured_height_m'):
                bundle.height_source = DataSource.SWISSBUILDINGS3D
                bundle.height_quality = DataQuality.HIGH
                bundle.add_source(DataSource.SWISSBUILDINGS3D)
            elif height_result.get('estimated_source') == 'calculated_from_floors':
                bundle.height_quality = DataQuality.MEDIUM
            else:
                bundle.height_quality = DataQuality.LOW

            # On-Demand Import falls keine gemessenen Höhen gefunden
            if not height_result.get('measured_height_m') and bundle.lv95_e and bundle.lv95_n:
                try:
                    from app.services.height_fetcher import fetch_height_for_coordinates
                    logger.info(f"On-demand Höhen-Import für E={bundle.lv95_e}, N={bundle.lv95_n}")

                    result = await fetch_height_for_coordinates(
                        e=bundle.lv95_e,
                        n=bundle.lv95_n,
                        egid=egid_int
                    )

                    if result.get("success") and result.get("heights"):
                        heights = result["heights"]
                        bundle.traufhoehe_m = heights.get('traufhoehe_m')
                        bundle.firsthoehe_m = heights.get('firsthoehe_m')
                        bundle.gebaeudehoehe_m = heights.get('gebaeudehoehe_m')
                        bundle.height_source = DataSource.SWISSBUILDINGS3D
                        bundle.height_quality = DataQuality.HIGH
                        bundle.add_source(DataSource.SWISSBUILDINGS3D)
                        logger.info(f"On-demand Import erfolgreich: {result.get('imported_count', 0)} Gebäude")
                    elif result.get("status") == "already_exists" and result.get("heights"):
                        heights = result["heights"]
                        bundle.traufhoehe_m = heights.get('traufhoehe_m')
                        bundle.firsthoehe_m = heights.get('firsthoehe_m')
                        bundle.gebaeudehoehe_m = heights.get('gebaeudehoehe_m')
                        bundle.height_source = DataSource.SWISSBUILDINGS3D
                        bundle.height_quality = DataQuality.HIGH
                        bundle.add_source(DataSource.SWISSBUILDINGS3D)
                except Exception as fetch_error:
                    logger.warning(f"On-demand Höhen-Import fehlgeschlagen: {fetch_error}")

            # Warning falls nur geschätzte Höhe
            if not bundle.traufhoehe_m and not bundle.firsthoehe_m:
                bundle.add_warning(f"Höhe geschätzt: {height_result.get('estimated_source', 'unknown')}")

        except Exception as e:
            logger.error(f"Height data error: {e}")
            bundle.add_warning(f"Höhendaten nicht verfügbar: {str(e)}")

    async def _collect_terrain_data(self, bundle: BuildingDataBundle):
        """Schritt 4: Terrain-Daten (Hanglage)"""
        if not bundle.lv95_e or not bundle.lv95_n:
            return

        try:
            from app.services.terrain import get_terrain_service
            terrain_service = get_terrain_service()

            # Haupthöhe am Gebäudezentrum
            ref_height = await terrain_service.get_height(bundle.lv95_e, bundle.lv95_n)

            if ref_height is not None:
                bundle.terrain = TerrainProfile(reference_height_m=ref_height)
                bundle.add_source(DataSource.SWISSALTI3D)

                # TODO: Profil um das Gebäude für Hanglage-Erkennung
                # Wenn Polygon verfügbar, 4 Eckpunkte abfragen
                if bundle.polygon and len(bundle.polygon) >= 4:
                    heights = []
                    for point in bundle.polygon[:4]:  # Erste 4 Ecken
                        h = await terrain_service.get_height(point[0], point[1])
                        if h:
                            heights.append(h)

                    if heights:
                        bundle.terrain.min_height_m = min(heights)
                        bundle.terrain.max_height_m = max(heights)
                        bundle.terrain.slope_m = max(heights) - min(heights)
                        bundle.terrain.is_sloped = bundle.terrain.slope_m > 1.0

                        if bundle.terrain.is_sloped:
                            bundle.add_warning(
                                f"Hanglage erkannt: {bundle.terrain.slope_m:.1f}m Höhendifferenz"
                            )

        except Exception as e:
            logger.error(f"Terrain error: {e}")
            bundle.add_warning(f"Terrain-Daten nicht verfügbar: {str(e)}")

    async def _collect_polygon_data(self, bundle: BuildingDataBundle):
        """Schritt 5: Polygon und Fassaden"""
        if not bundle.lv95_e or not bundle.lv95_n:
            return

        try:
            from app.services.geodienste import GeodiensteService
            geodienste = GeodiensteService()

            geometry = await geodienste.get_building_geometry(
                x=bundle.lv95_e,
                y=bundle.lv95_n,
                tolerance=50,
                egid=int(bundle.egid) if bundle.egid else None
            )

            if geometry:
                bundle.polygon = geometry.polygon
                bundle.sides = geometry.sides
                bundle.perimeter_m = geometry.perimeter_m
                bundle.footprint_area_m2 = bundle.footprint_area_m2 or geometry.area_m2  # Aus Polygon falls GWR fehlt
                bundle.polygon_simplified = getattr(geometry, 'simplified', False)  # Optional
                bundle.add_source(DataSource.GEODIENSTE_WFS)

                # Bounding Box berechnen
                if bundle.polygon:
                    xs = [p[0] for p in bundle.polygon]
                    ys = [p[1] for p in bundle.polygon]
                    bundle.bbox_width_m = max(xs) - min(xs)
                    bundle.bbox_depth_m = max(ys) - min(ys)

        except Exception as e:
            logger.error(f"Polygon error: {e}")
            bundle.add_warning(f"Gebäudegeometrie nicht verfügbar: {str(e)}")

    async def _calculate_roof_data(self, bundle: BuildingDataBundle):
        """Schritt 6: Dach-Analyse (berechnet)"""
        try:
            from app.services.roof import get_roof_service
            roof_service = get_roof_service()

            result = roof_service.calculate(
                traufhoehe_m=bundle.traufhoehe_m,
                firsthoehe_m=bundle.firsthoehe_m,
                building_depth_m=bundle.bbox_depth_m,
                polygon=bundle.polygon
            )

            if result:
                bundle.roof_type = result.roof_type.value if hasattr(result.roof_type, 'value') else str(result.roof_type)
                bundle.roof_angle_deg = result.roof_angle_deg
                bundle.roof_orientation = result.roof_orientation
                bundle.roof_area_m2 = result.roof_area_m2
                bundle.roof_confidence = result.confidence
                bundle.add_source(DataSource.CALCULATED)

        except Exception as e:
            logger.error(f"Roof calculation error: {e}")

    async def _collect_research_data(self, bundle: BuildingDataBundle, force_refresh: bool = False):
        """Schritt 7: Gebäude-Recherche (bekannte Gebäude + Claude)"""
        from .research_integration import collect_building_research
        await collect_building_research(bundle, force_refresh)

    def _needs_zones_analysis(self, bundle: BuildingDataBundle) -> bool:
        """Prüft ob eine detaillierte Zonen-Analyse nötig ist"""
        # Bekannte Gebäude haben bereits korrekte Zonen - keine Analyse nötig!
        if hasattr(bundle, '_known_zones') and bundle._known_zones:
            return False

        # Extreme Höhendifferenz
        if bundle.has_extreme_height_diff():
            return True

        # Komplexe Gebäudekategorie
        complex_cats = [1040, 1060, 1080, 1110, 1130, 1212]
        if bundle.gwr_category_code in complex_cats:
            return True

        # Grosses Gebäude
        if bundle.footprint_area_m2 and bundle.footprint_area_m2 > 1000:
            return True

        # Komplexes Polygon
        if bundle.polygon and len(bundle.polygon) > 12:
            return True

        return False

    async def _collect_zones_analysis(self, bundle: BuildingDataBundle):
        """Schritt 8: Zonen-Analyse via Claude Sonnet"""
        try:
            from app.services.building_context import get_building_context_service
            context_service = get_building_context_service()

            # Polygon für Analyse vorbereiten
            polygon_dicts = []
            if bundle.polygon:
                for p in bundle.polygon:
                    polygon_dicts.append({"e": p[0], "n": p[1]})

            height_data = {
                "traufhoehe_m": bundle.traufhoehe_m,
                "firsthoehe_m": bundle.firsthoehe_m,
                "gebaeudehoehe_m": bundle.gebaeudehoehe_m,
            }

            gwr_data = {
                "gkat": bundle.gwr_category_code,
                "gastw": bundle.gwr_floors,
                "gbauj": bundle.construction_year,
                "garea": bundle.gwr_area_m2,
                "building_name": bundle.building_name,
            }

            terrain_data = None
            if bundle.terrain:
                terrain_data = {
                    "terrain_height_m": bundle.terrain.reference_height_m,
                    "terrain_slope_m": bundle.terrain.slope_m,
                }

            context = await context_service.analyze_with_claude(
                egid=bundle.egid or "unknown",
                adresse=bundle.address_matched,
                polygon=polygon_dicts,
                height_data=height_data,
                gwr_data=gwr_data,
                terrain_data=terrain_data,
                include_orthofoto=False  # Kann später aktiviert werden
            )

            if context and context.zones:
                bundle.zones = []
                for z in context.zones:
                    bundle.zones.append(ZoneInfo(
                        id=z.id,
                        name=z.name,
                        zone_type=z.type.value if hasattr(z.type, 'value') else str(z.type),
                        traufhoehe_m=z.traufhoehe_m,
                        firsthoehe_m=z.firsthoehe_m,
                        gebaeudehoehe_m=z.gebaeudehoehe_m,
                        fassaden_ids=z.fassaden_ids or [],
                        polygon_point_indices=z.polygon_point_indices,
                        beruesten=z.beruesten,
                        sonderkonstruktion=z.sonderkonstruktion,
                        confidence=z.confidence,
                        source=DataSource.CLAUDE_ANALYSIS,
                    ))

                bundle.complexity = context.complexity.value if hasattr(context.complexity, 'value') else str(context.complexity)
                bundle.has_height_variations = context.has_height_variations
                bundle.has_towers = context.has_towers
                bundle.has_annexes = context.has_annexes
                bundle.analysis_confidence = context.confidence
                bundle.add_source(DataSource.CLAUDE_ANALYSIS)

                # Zugänge übernehmen
                if context.zugaenge:
                    for z in context.zugaenge:
                        bundle.access_points.append(AccessPoint(
                            id=z.get('id', 'Z1'),
                            fassade_id=z.get('fassade_id', 'N'),
                            position_percent=z.get('position_percent', 0.5),
                            reason=z.get('grund', ''),
                        ))

        except Exception as e:
            logger.error(f"Zones analysis error: {e}")
            bundle.add_warning(f"Zonen-Analyse fehlgeschlagen: {str(e)}")
            self._create_default_zone(bundle)

    def _create_default_zone(self, bundle: BuildingDataBundle):
        """Erstellt Standard-Zone(n) basierend auf Höhendaten

        PRIORITÄT:
        1. Zonen aus bekannten Gebäuden (_known_zones)
        2. Kirchen-spezifische Zonen bei Sakralbauten
        3. Standard-Zonen bei extremer Höhendifferenz
        4. Einfache Zone für normale Gebäude
        """
        if bundle.zones:
            return  # Bereits Zonen vorhanden

        # 1. Bekannte Gebäude-Zonen
        from .research_integration import create_zones_from_known_building
        if create_zones_from_known_building(bundle):
            return

        # 2. Kirchen-spezifische Zonen
        from .research_integration import create_church_zones
        if create_church_zones(bundle):
            return

        # Prüfe auf extreme Höhendifferenz (typisch für Kirchen mit Turm)
        if bundle.has_extreme_height_diff():
            height_diff = (bundle.firsthoehe_m or 0) - (bundle.traufhoehe_m or 0)

            # Zone 1: Hauptgebäude (Kirchenschiff, Gebäudekörper)
            hauptgebaeude = ZoneInfo(
                id="zone_1",
                name="Hauptgebäude",
                zone_type="hauptgebaeude",
                traufhoehe_m=bundle.traufhoehe_m,
                firsthoehe_m=bundle.traufhoehe_m,  # Traufhöhe als "First" des Hauptgebäudes
                gebaeudehoehe_m=bundle.traufhoehe_m,
                beruesten=True,
                sonderkonstruktion=False,
                confidence=0.7,
                source=DataSource.CALCULATED,
                notes=f"Automatisch aus Höhendifferenz ({height_diff:.1f}m) abgeleitet"
            )
            bundle.zones.append(hauptgebaeude)

            # Zone 2: Turm (bei sehr grosser Differenz wahrscheinlich Kirchturm)
            turm = ZoneInfo(
                id="zone_2",
                name="Turm",
                zone_type="turm",
                traufhoehe_m=bundle.traufhoehe_m,  # Turm startet bei Traufhöhe
                firsthoehe_m=bundle.firsthoehe_m,
                gebaeudehoehe_m=bundle.firsthoehe_m,
                beruesten=True,
                sonderkonstruktion=True,  # Türme brauchen oft Sonderkonstruktion
                confidence=0.6,
                source=DataSource.CALCULATED,
                notes=f"Turm erkannt aus extremer Höhendifferenz ({height_diff:.1f}m)"
            )
            bundle.zones.append(turm)

            bundle.complexity = "complex"
            bundle.has_towers = True
            bundle.has_height_variations = True

            logger.info(f"Automatisch 2 Zonen erstellt: Hauptgebäude ({bundle.traufhoehe_m:.1f}m) + Turm ({bundle.firsthoehe_m:.1f}m)")

        else:
            # Einfaches Gebäude: 1 Zone
            zone = ZoneInfo(
                id="zone_1",
                name="Hauptgebäude",
                zone_type="hauptgebaeude",
                traufhoehe_m=bundle.traufhoehe_m,
                firsthoehe_m=bundle.firsthoehe_m,
                gebaeudehoehe_m=bundle.gebaeudehoehe_m or bundle.estimated_height_m,
                beruesten=True,
                sonderkonstruktion=False,
                confidence=1.0,
                source=DataSource.CALCULATED,
            )
            bundle.zones.append(zone)
            bundle.complexity = "simple"

    def _calculate_access_points(self, bundle: BuildingDataBundle):
        """Berechnet Gerüst-Zugänge nach SUVA"""
        if bundle.access_points:
            return  # Bereits aus Analyse

        try:
            from app.services.access_calculator import calculate_access_points

            if bundle.sides:
                fassaden = [
                    {"id": s.get("direction", f"F{i}"), "laenge_m": s.get("length_m", 10)}
                    for i, s in enumerate(bundle.sides)
                ]

                result = calculate_access_points(fassaden)

                for z in result.zugaenge:
                    bundle.access_points.append(AccessPoint(
                        id=z.id,
                        fassade_id=z.fassade_id,
                        position_percent=z.position_percent,
                        reason=z.grund or "Automatisch berechnet",
                        suva_compliant=result.suva_konform,
                        max_escape_distance_m=result.max_fluchtweg_m,
                    ))

                bundle.suva_compliant = result.suva_konform
                bundle.max_escape_distance_m = result.max_fluchtweg_m

        except Exception as e:
            logger.warning(f"Access calculation failed: {e}")

    async def _collect_neighbor_data(self, bundle: BuildingDataBundle):
        """Schritt 9: Nachbargebäude (TODO)"""
        # TODO: Implementierung für Nachbargebäude-Erkennung
        pass

    def _assess_data_quality(self, bundle: BuildingDataBundle):
        """Bewertet die Gesamtqualität der gesammelten Daten"""
        quality_scores = []

        # Geocoding
        if bundle.address_matched:
            quality_scores.append(1.0)
        else:
            quality_scores.append(0.0)

        # Höhendaten
        if bundle.height_quality == DataQuality.HIGH:
            quality_scores.append(1.0)
        elif bundle.height_quality == DataQuality.MEDIUM:
            quality_scores.append(0.7)
        else:
            quality_scores.append(0.3)

        # Polygon
        if bundle.polygon:
            quality_scores.append(1.0 if len(bundle.polygon) >= 4 else 0.5)
        else:
            quality_scores.append(0.0)

        # Zonen
        if bundle.zones:
            avg_conf = sum(z.confidence for z in bundle.zones) / len(bundle.zones)
            quality_scores.append(avg_conf)

        # Gesamtqualität
        if quality_scores:
            avg = sum(quality_scores) / len(quality_scores)
            if avg >= 0.8:
                bundle.overall_quality = DataQuality.HIGH
            elif avg >= 0.5:
                bundle.overall_quality = DataQuality.MEDIUM
            else:
                bundle.overall_quality = DataQuality.LOW

    def bundle_to_scaffolding_response(
        self,
        bundle: BuildingDataBundle,
        work_type: str = "dacharbeiten",
        scaffold_type: str = "arbeitsgeruest"
    ) -> Dict[str, Any]:
        """
        Konvertiert BuildingDataBundle zum /api/v1/scaffolding Response-Format.

        Ermöglicht nahtlose Integration ohne Frontend-Änderungen.
        """
        # Aktive Höhe bestimmen
        active_height = bundle.get_active_height() or 10.0

        # Gerüsthöhe basierend auf Arbeitstyp
        if work_type == "dacharbeiten":
            geruesthoehe = (bundle.firsthoehe_m or active_height) + 1.0
        else:
            geruesthoehe = bundle.traufhoehe_m or active_height

        # Umfang und Fläche berechnen
        perimeter = bundle.perimeter_m or 40.0
        scaffold_area = perimeter * geruesthoehe

        # Terrain-Daten
        terrain_data = None
        if bundle.terrain:
            terrain_data = {
                "terrain_height_m": bundle.terrain.reference_height_m,
                "elevation_model": "COMB",
                "min_terrain_m": bundle.terrain.min_height_m,
                "max_terrain_m": bundle.terrain.max_height_m,
                "terrain_slope_m": bundle.terrain.slope_m,
            }

        # Dach-Daten
        roof_data = None
        if bundle.roof_type:
            roof_data = {
                "roof_type": bundle.roof_type,
                "roof_angle_deg": bundle.roof_angle_deg,
                "roof_orientation": bundle.roof_orientation,
                "roof_area_m2": bundle.roof_area_m2,
                "confidence": bundle.roof_confidence,
            }

        # Polygon-Daten
        polygon_data = None
        if bundle.polygon:
            polygon_data = {
                "coordinates": bundle.polygon,
                "coordinate_system": "LV95 (EPSG:2056)",
            }

        # Response aufbauen
        return {
            "address": {
                "input": bundle.address_input,
                "matched": bundle.address_matched,
                "coordinates": {
                    "lv95_e": bundle.lv95_e,
                    "lv95_n": bundle.lv95_n,
                },
                "terrain": terrain_data,
            },
            "gwr_data": {
                "egid": bundle.egid,
                "building_category": bundle.gwr_category,
                "construction_year": bundle.construction_year or (
                    bundle.gwr_category_code  # Fallback
                ),
                "floors": bundle.gwr_floors,
                "area_m2_gwr": bundle.gwr_area_m2,
            },
            "configuration": {
                "work_type": work_type,
                "scaffold_type": scaffold_type,
            },
            "roof": roof_data,
            "building": {
                "egid": bundle.egid,
                "name": bundle.building_name,
                "type": bundle.building_type,
                "style": bundle.architectural_style,
                "footprint_area_m2": bundle.footprint_area_m2 or bundle.gwr_area_m2,
                "bounding_box": {
                    "width_m": bundle.bbox_width_m,
                    "depth_m": bundle.bbox_depth_m,
                },
            },
            "dimensions": {
                "traufhoehe_m": bundle.traufhoehe_m,
                "firsthoehe_m": bundle.firsthoehe_m,
                "gebaeudehoehe_m": bundle.gebaeudehoehe_m,
                "estimated_height_m": bundle.estimated_height_m or active_height,
                "height_source": bundle.height_source.value if bundle.height_source else "unknown",
                "floors": bundle.gwr_floors or bundle.floors_estimated,
                "perimeter_m": perimeter,
                "geruesthoehe_m": geruesthoehe,
            },
            "polygon": polygon_data,
            "sides": bundle.sides or [],
            "viewer_3d_url": (
                f"https://3d.geo.admin.ch/#/embed?egid={bundle.egid}"
                if bundle.egid else None
            ),
            "geruestflaeche_m2": scaffold_area,
            # SmartService-spezifische Daten
            "smart_building": {
                "bundle_cached": True,
                "data_sources": [s.value for s in bundle.data_sources],
                "overall_quality": bundle.overall_quality.value if bundle.overall_quality else "unknown",
                "complexity": bundle.complexity,
                "zones_count": len(bundle.zones),
                "research": {
                    "building_name": bundle.building_name,
                    "building_type": bundle.building_type,
                    "architectural_style": bundle.architectural_style,
                    "confidence": bundle.research_confidence,
                },
                "warnings": bundle.warnings,
                "errors": bundle.errors,
            }
        }


# Singleton
_service_instance: Optional[SmartBuildingService] = None


def get_smart_building_service() -> SmartBuildingService:
    """Gibt die Singleton-Instanz zurück"""
    global _service_instance
    if _service_instance is None:
        _service_instance = SmartBuildingService()
    return _service_instance
