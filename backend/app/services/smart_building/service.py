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
  - Gebäude-Recherche (Claude Sonnet)

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
import base64  # NEU 14.01.2026: Für WKB-Serialisierung im Cache
import logging
import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple, overload
import os

from .models import (
    BuildingDataBundle,
    DataSource,
    DataQuality,
    ZoneInfo,
    TerrainProfile,
    AccessPoint,
)
from .validation import validate_heights, validate_zone_consistency

# BuildingContext Integration - für konsistente Zonen zwischen Frontend und Prompt
from app.models.building_context import BuildingZone, ZoneType, BuildingContext

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

    def get_bundle_by_egid(self, egid: str) -> Optional[BuildingDataBundle]:
        """
        Holt Bundle aus Cache anhand der EGID.

        Dies ist die empfohlene Methode für project_service und andere Services,
        um Gebäudedaten abzurufen. Der Cache wird vom SmartBuildingService verwaltet.

        Args:
            egid: Eidgenössische Gebäudeidentifikation

        Returns:
            BuildingDataBundle oder None wenn nicht gefunden/expired

        Verwendung:
            service = get_smart_building_service()
            bundle = service.get_bundle_by_egid("2242547")
            if bundle:
                print(f"Gebäude: {bundle.building_name}")
        """
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT bundle_json, expires_at
            FROM smart_building_cache
            WHERE egid = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (str(egid),))

        row = cursor.fetchone()
        conn.close()

        if not row:
            logger.debug(f"No cached bundle for EGID {egid}")
            return None

        # Expiration prüfen
        expires_at = datetime.fromisoformat(row['expires_at'])
        if datetime.now() > expires_at:
            logger.info(f"Cache expired for EGID {egid}")
            return None

        try:
            data = json.loads(row['bundle_json'])
            bundle = self._dict_to_bundle(data)
            bundle.add_source(DataSource.CACHE)

            # FIX 14.01.2026 19:35: Refresh kritischer Felder aus building_3d DB
            # Alte Cache-Einträge haben keine has_3d_layers oder facade heights
            bundle = self._refresh_bundle_from_db(bundle, egid)

            logger.debug(f"Loaded bundle for EGID {egid} from cache (has_3d_layers={bundle.has_3d_layers})")
            return bundle
        except Exception as e:
            logger.warning(f"Cache parse error for EGID {egid}: {e}")
            return None

    def _refresh_bundle_from_db(self, bundle: BuildingDataBundle, egid: str) -> BuildingDataBundle:
        """
        FIX 14.01.2026 19:35: Refresh kritischer Felder aus building_3d DB.

        Alte Cache-Einträge (vor T2-T4 Implementation) haben keine:
        - has_3d_layers
        - facade_z_min/facade_z_max
        - facade_heights_source

        Diese werden hier aus der DB aufgefrischt.
        """
        try:
            from app.services.building_3d_service import get_building_3d_service
            building_3d_service = get_building_3d_service()
            building_data = building_3d_service.get_by_egid(str(egid))

            if building_data:
                # has_3d_layers immer aus DB (ist dort aktueller)
                bundle.has_3d_layers = building_data.get('has_3d_layers', 0) == 1

                # Facade heights nur wenn leer (aus Wall-Layer)
                if bundle.terrain and not bundle.terrain.facade_z_min and bundle.sides:
                    try:
                        from app.services.smart_building.wall_facade_matcher import get_wall_facade_matcher
                        matcher = get_wall_facade_matcher()
                        facade_heights = matcher.get_facade_heights(str(egid), bundle.sides)
                        if facade_heights:
                            # Konvertiere FacadeHeight zu Dict
                            z_min_dict = {}
                            z_max_dict = {}
                            for direction, fh in facade_heights.items():
                                z_min_dict[direction] = fh.z_min
                                z_max_dict[direction] = fh.z_max
                            if z_min_dict:
                                bundle.terrain.facade_z_min = z_min_dict
                                bundle.terrain.facade_z_max = z_max_dict
                                bundle.terrain.facade_heights_source = 'wall-layer'
                                logger.info(f"[REFRESH] Facade heights für EGID {egid} aus Wall-Layer geladen")
                    except Exception as e:
                        logger.debug(f"Wall-Layer facade heights nicht verfügbar: {e}")

                logger.debug(f"[REFRESH] Bundle für EGID {egid}: has_3d_layers={bundle.has_3d_layers}")
        except Exception as e:
            logger.debug(f"Bundle refresh für EGID {egid} fehlgeschlagen: {e}")

        return bundle

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
                "min_height_m": bundle.terrain.min_height_m,
                "max_height_m": bundle.terrain.max_height_m,
                "slope_m": bundle.terrain.slope_m,
                "slope_class": bundle.terrain.slope_class,
                "is_sloped": bundle.terrain.is_sloped,
                "requires_level_compensation": bundle.terrain.requires_level_compensation,
                "facade_heights": bundle.terrain.facade_heights,
                # NEU 14.01.2026 (T2): Fassaden-Höhen aus Wall-Layer
                "facade_z_min": bundle.terrain.facade_z_min,
                "facade_z_max": bundle.terrain.facade_z_max,
                "facade_heights_source": bundle.terrain.facade_heights_source,
            } if bundle.terrain else None,
            "roof_type": bundle.roof_type,
            "roof_angle_deg": bundle.roof_angle_deg,
            "roof_orientation": bundle.roof_orientation,
            # Sonnendach.ch Daten
            "roof_overhang_m": bundle.roof_overhang_m,
            "roof_surfaces": bundle.roof_surfaces,
            "roof_tilt_deg": bundle.roof_tilt_deg,
            "roof_azimuth_deg": bundle.roof_azimuth_deg,
            "sonnendach_available": bundle.sonnendach_available,
            "zones": [
                {
                    "id": z.id,
                    "name": z.name,
                    "zone_type": z.zone_type,
                    "traufhoehe_m": z.traufhoehe_m,
                    "firsthoehe_m": z.firsthoehe_m,
                    "gebaeudehoehe_m": z.gebaeudehoehe_m,
                    "position": z.position,  # Position für 3D-Darstellung
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
            # NEU 05.01.2026: Datenherkunft für UI-Feedback
            "research_source": bundle.research_source,
            "research_confidence": bundle.research_confidence,
            # FIX 12.01.2026: 3D-Layer Felder hinzufügen
            "has_3d_layers": bundle.has_3d_layers,
            "has_roof_geometry": bundle.has_roof_geometry,
            "roof_dach_min_m": bundle.roof_dach_min_m,
            "roof_dach_max_m": bundle.roof_dach_max_m,
            # NEU 14.01.2026: 3D-Dachgeometrie als Base64 für Cache
            "roof_geometry_wkb_base64": base64.b64encode(bundle.roof_geometry_wkb).decode('ascii') if bundle.roof_geometry_wkb else None,
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
            # Sonnendach.ch Daten
            roof_overhang_m=data.get("roof_overhang_m", 0.4),  # Standard 40cm
            roof_surfaces=data.get("roof_surfaces"),
            roof_tilt_deg=data.get("roof_tilt_deg"),
            roof_azimuth_deg=data.get("roof_azimuth_deg"),
            sonnendach_available=data.get("sonnendach_available", False),
            complexity=data.get("complexity", "simple"),
            warnings=data.get("warnings", []),
            # NEU 05.01.2026: Datenherkunft für UI-Feedback
            research_source=data.get("research_source", "cache"),
            research_confidence=data.get("research_confidence", 0.0),
            # FIX 14.01.2026 19:30: has_3d_layers wurde nicht aus Cache geladen!
            has_3d_layers=data.get("has_3d_layers", False),
        )

        # Terrain
        if data.get("terrain"):
            t = data["terrain"]
            bundle.terrain = TerrainProfile(
                reference_height_m=t.get("reference_height_m", 0),
                min_height_m=t.get("min_height_m"),
                max_height_m=t.get("max_height_m"),
                slope_m=t.get("slope_m"),
                slope_class=t.get("slope_class", "eben"),
                is_sloped=t.get("is_sloped", False),
                requires_level_compensation=t.get("requires_level_compensation", False),
                facade_heights=t.get("facade_heights", {}),
                # NEU 14.01.2026 (T2): Fassaden-Höhen aus Wall-Layer
                facade_z_min=t.get("facade_z_min", {}),
                facade_z_max=t.get("facade_z_max", {}),
                facade_heights_source=t.get("facade_heights_source", "global"),
            )

        # Zonen
        for z in data.get("zones", []):
            bundle.zones.append(ZoneInfo(
                id=z.get("id", "zone_1"),
                name=z.get("name", "Hauptgebäude"),
                zone_type=z.get("zone_type", "hauptgebaeude"),
                position=z.get("position"),  # Position für 3D-Darstellung
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

        # NEU 14.01.2026: 3D-Dachgeometrie aus Cache laden
        bundle.has_roof_geometry = data.get("has_roof_geometry", False)
        bundle.roof_dach_min_m = data.get("roof_dach_min_m")
        bundle.roof_dach_max_m = data.get("roof_dach_max_m")
        if data.get("roof_geometry_wkb_base64"):
            bundle.roof_geometry_wkb = base64.b64decode(data["roof_geometry_wkb_base64"])

        return bundle

    async def _get_address_lock(self, cache_key: str) -> asyncio.Lock:
        """Holt oder erstellt Lock für eine Adresse (thread-safe)"""
        async with self._global_lock:
            if cache_key not in self._address_locks:
                self._address_locks[cache_key] = asyncio.Lock()
            return self._address_locks[cache_key]

    async def collect_all_data(
        self,
        address: Union[str, List[str]],
        force_refresh: bool = False,
        include_research: bool = True,
        include_zones_analysis: bool = True,
        include_terrain: bool = True,
        include_neighbors: bool = False,  # TODO
    ) -> Union[BuildingDataBundle, List[BuildingDataBundle]]:
        """
        Sammelt alle verfügbaren Daten für ein oder mehrere Gebäude.

        NEU 11.01.2026: Rückwärtskompatible Multi-Adress-Unterstützung.
        Bei einer Liste von Adressen werden die _collect_* Methoden für
        jedes Gebäude aufgerufen, mit interner Cache-Prüfung.

        Args:
            address: Schweizer Adresse (String) oder Liste von Adressen
            force_refresh: Cache ignorieren
            include_research: Claude-Recherche für Gebäude-Identifikation
            include_zones_analysis: Claude-Analyse für komplexe Gebäude
            include_terrain: Terrain-Daten abrufen
            include_neighbors: Nachbargebäude analysieren (TODO)

        Returns:
            BuildingDataBundle (bei String) oder List[BuildingDataBundle] (bei Liste)

        Request-Deduplizierung:
            Bei parallelen Anfragen für dieselbe Adresse wartet die zweite
            Anfrage auf das Ergebnis der ersten (via asyncio.Lock).
            Dies verhindert doppelte API-Calls zu swisstopo/geodienste.ch.
        """
        # NEU 11.01.2026: Multi-Adress-Unterstützung
        if isinstance(address, list):
            return await self._collect_multi_building_data(
                addresses=address,
                force_refresh=force_refresh,
                include_research=include_research,
                include_zones_analysis=include_zones_analysis,
                include_terrain=include_terrain,
            )

        # Einzelne Adresse - REFACTORED 11.01.2026: Bundle-basiert wie Multi-Address
        cache_key = self._cache_key(address)

        # 1. Quick Cache Check (ohne Lock - read-only)
        if not force_refresh:
            cached = self._get_cached_bundle(cache_key)
            if cached:
                # FIX 13.01.2026: has_3d_layers immer frisch aus DB laden
                # Der Prefetch läuft async und kann das Flag nach dem Cache-Write setzen
                if cached.egid:
                    try:
                        from app.services.building_3d_service import get_building_3d_service
                        building_3d_service = get_building_3d_service()
                        building_3d_data = building_3d_service.get_by_egid(int(cached.egid))
                        if building_3d_data:
                            cached.has_3d_layers = building_3d_data.get('has_3d_layers', 0) == 1
                    except Exception as e:
                        logger.debug(f"has_3d_layers refresh failed: {e}")

                logger.info(
                    f"[SMART_BUILDING] Cache-Hit für: {address}\n"
                    f"  ├─ Gebäudename: {cached.building_name or 'unbekannt'}\n"
                    f"  ├─ Original Research-Quelle: {cached.research_source}\n"
                    f"  ├─ has_3d_layers: {cached.has_3d_layers}\n"
                    f"  └─ Zonen: {len(cached.zones)}"
                )
                return cached

        # 2. Request-Deduplizierung: Lock pro Adresse
        address_lock = await self._get_address_lock(cache_key)

        async with address_lock:
            # Double-Check nach Lock-Erwerb (andere Anfrage könnte fertig sein)
            if not force_refresh:
                cached = self._get_cached_bundle(cache_key)
                if cached:
                    # FIX 13.01.2026: has_3d_layers immer frisch aus DB laden
                    if cached.egid:
                        try:
                            from app.services.building_3d_service import get_building_3d_service
                            building_3d_service = get_building_3d_service()
                            building_3d_data = building_3d_service.get_by_egid(int(cached.egid))
                            if building_3d_data:
                                cached.has_3d_layers = building_3d_data.get('has_3d_layers', 0) == 1
                        except Exception:
                            pass
                    logger.info(f"Using cached bundle for {address} (waited for other request)")
                    return cached

            logger.info(f"Collecting data for {address} (holding lock)")

            # 3. Bundle erstellen und Geocoding
            bundle = BuildingDataBundle(
                address_input=address,
                collection_timestamp=datetime.now(),
            )
            await self._collect_geocoding(bundle)

            if not bundle.lv95_e or not bundle.lv95_n:
                logger.error(f"Geocoding failed for {address}, cannot proceed")
                bundle.add_error("Geocoding fehlgeschlagen - keine weiteren Daten verfügbar")
                return bundle

            # 4. Enrichment via _collect_* Methoden (wie Multi-Address)
            await self._collect_gwr_data(bundle)
            await self._collect_building_3d_data(bundle)
            if include_terrain:
                await self._collect_terrain_data(bundle)
            await self._collect_sonnendach_data(bundle)
            await self._calculate_roof_data(bundle)
            # FIX 12.01.2026: Research ZUERST aufrufen um _known_zones zu setzen
            # Dann erst Zonen erstellen (damit bekannte Gebäude korrekte Zonen bekommen)
            if include_research:
                await self._collect_research_data(bundle, force_refresh)
            if include_zones_analysis:
                self._create_default_zone(bundle)
            # 3D-Geometrie für komplexe Gebäude laden
            self._fetch_roof_geometry_for_complex(bundle)
            # FIX 14.01.2026: Nach dem Speichern der 3D-Daten NOCHMAL laden!
            # _fetch_roof_geometry_for_complex() speichert in DB, aber die Daten
            # wurden VOR dem Speichern gelesen (in _collect_building_3d_data).
            # TODO: Konsolidieren - fetch sollte Daten direkt ins Bundle schreiben
            self._load_roof_data_from_db(bundle)
            self._calculate_access_points(bundle)
            self._assess_data_quality(bundle)

            # 5. Cache speichern
            self._save_bundle_cache(cache_key, bundle)

            return bundle

    async def _collect_geocoding(self, bundle: BuildingDataBundle):
        """Schritt 1: Geocoding - fuellt Bundle mit Koordinaten"""
        try:
            from app.services.swisstopo import SwisstopoService
            swisstopo = SwisstopoService()

            geo = await swisstopo.geocode(bundle.address_input)
            if geo and geo.coordinates:
                bundle.lv95_e = geo.coordinates.lv95_e
                bundle.lv95_n = geo.coordinates.lv95_n
                bundle.address_matched = geo.matched_address
                if hasattr(geo, 'egid') and geo.egid:
                    bundle.egid = str(geo.egid)
                bundle.add_source(DataSource.SWISSTOPO_GEOCODING)

        except Exception as e:
            logger.error(f'Geocoding error for {bundle.address_input}: {e}')
            bundle.add_warning(f'Geocoding fehlgeschlagen: {str(e)}')

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

    async def _collect_building_3d_data(self, bundle: BuildingDataBundle):
        """Schritt 3+5 kombiniert: Polygon UND Höhen aus swissBUILDINGS3D

        OPTIMIERUNG (01.01.2026): Ein STAC-API-Aufruf statt zwei!
        swissBUILDINGS3D liefert in einem Feature sowohl:
        - Gebäudepolygon (geometry)
        - Höhendaten (DACHHOEHE, TRAUFHOEHE, GESAMTHOEHE)

        Fallback-Strategie für Höhen falls kein Polygon gefunden:
        1. EGID-Lookup in lokaler DB
        2. Koordinaten-Lookup in lokaler DB
        3. Geschätzt aus GWR-Daten (Geschosse × 3.2m)
        """
        if not bundle.lv95_e or not bundle.lv95_n:
            return

        try:
            from app.services.swissbuildings3d_fetcher import fetch_building_polygon_for_coordinates

            # EIN Aufruf für Polygon + Höhen
            result = await fetch_building_polygon_for_coordinates(
                e=bundle.lv95_e,
                n=bundle.lv95_n,
                tolerance_m=50.0
            )

            if result:
                # === POLYGON (vereinfacht für Fassaden-Auswahl) ===
                # Polygon is ALWAYS the original from swissBUILDINGS3D
                bundle.polygon = result.get("polygon")
                bundle.polygon_point_count = result.get("polygon_point_count")
                bundle.sides_from_simplified = result.get("sides_from_simplified", True)

                # Sides are calculated from on-the-fly simplified polygon
                bundle.sides = result.get("sides")
                bundle.perimeter_m = result.get("perimeter_m")
                bundle.footprint_area_m2 = bundle.footprint_area_m2 or result.get("area_m2")

                # === HÖHEN (aus demselben Feature) ===
                bundle.traufhoehe_m = result.get("traufhoehe_m")
                bundle.firsthoehe_m = result.get("firsthoehe_m")
                bundle.gebaeudehoehe_m = result.get("gebaeudehoehe_m")

                if bundle.traufhoehe_m or bundle.firsthoehe_m:
                    bundle.height_source = DataSource.SWISSBUILDINGS3D
                    bundle.height_quality = DataQuality.HIGH

                # === EGID (swissBUILDINGS3D als Primary Key) ===
                # BUG-013 FIX: GWR gruppiert Reihenhäuser unter einer EGID,
                # swissBUILDINGS3D hat separate EGIDs pro Segment
                swissbuildings_egid = result.get("egid")
                if swissbuildings_egid:
                    if bundle.egid and str(bundle.egid) != str(swissbuildings_egid):
                        bundle.gwr_egid = bundle.egid  # GWR EGID behalten
                        logger.info(f"EGID Update: GWR {bundle.egid} → swissBUILDINGS3D {swissbuildings_egid}")
                    bundle.egid = str(swissbuildings_egid)
                    
                    # FIX 12.01.2026: has_3d_layers direkt hier laden (nicht in _load_roof_data_from_db)
                    from app.services.building_3d_service import get_building_3d_service
                    building_3d_service = get_building_3d_service()
                    building_3d_data = building_3d_service.get_by_egid(int(swissbuildings_egid))
                    if building_3d_data:
                        bundle.has_3d_layers = building_3d_data.get('has_3d_layers', 0) == 1

                bundle.add_source(DataSource.SWISSBUILDINGS3D)
                original_pts = bundle.polygon_point_count or 0
                simplified_pts = result.get("polygon_simplified_point_count", 0)
                logger.info(
                    f"swissBUILDINGS3D: Polygon {original_pts} Punkte (→{simplified_pts} für Fassaden), "
                    f"Höhen: Trauf={bundle.traufhoehe_m}m, First={bundle.firsthoehe_m}m, "
                    f"Match-Distanz: {result.get('match_distance_m', 'N/A')}m"
                )

                # Bounding Box berechnen
                if bundle.polygon:
                    xs = [p[0] for p in bundle.polygon]
                    ys = [p[1] for p in bundle.polygon]
                    bundle.bbox_width_m = max(xs) - min(xs)
                    bundle.bbox_depth_m = max(ys) - min(ys)

                    # Polygon-Form-Analyse (U-Form, L-Form, etc.)
                    try:
                        from .polygon_analysis import enrich_bundle_with_shape_analysis
                        enrich_bundle_with_shape_analysis(bundle)
                        logger.debug(f"Shape: {bundle.building_shape}")
                    except Exception as shape_error:
                        logger.warning(f"Shape analysis failed: {shape_error}")

                # === DACH-DATEN aus building_roofs (NEU 11.01.2026) ===
                # Echte 3D-Daten aus Roof_solid Layer (gleicher Tile-Import!)
                print(f"[DEBUG] Vor _load_roof_data_from_db für EGID {bundle.egid}")
                self._load_roof_data_from_db(bundle)
                print(f"[DEBUG] Nach _load_roof_data_from_db, has_3d_layers={bundle.has_3d_layers}")

            else:
                bundle.add_warning("Gebäude nicht in swissBUILDINGS3D gefunden")

            # === FALLBACK für Höhen wenn nicht aus swissBUILDINGS3D ===
            if not bundle.traufhoehe_m and not bundle.firsthoehe_m:
                await self._fallback_height_lookup(bundle)

        except Exception as e:
            logger.error(f"Building 3D data error: {e}")
            bundle.add_warning(f"Gebäudedaten nicht verfügbar: {str(e)}")
            # Fallback auf Höhen-Schätzung
            await self._fallback_height_lookup(bundle)

    async def _fallback_height_lookup(self, bundle: BuildingDataBundle):
        """Fallback Höhen-Lookup wenn swissBUILDINGS3D keine Daten hat"""
        try:
            from app.services.geodienste import get_height_details

            egid_int = int(bundle.egid) if bundle.egid else None

            height_result = get_height_details(
                floors=bundle.gwr_floors,
                building_category_code=bundle.gwr_category_code,
                manual_height=None,
                egid=egid_int,
                lv95_e=bundle.lv95_e,
                lv95_n=bundle.lv95_n,
            )

            bundle.traufhoehe_m = height_result.get('traufhoehe_m')
            bundle.firsthoehe_m = height_result.get('firsthoehe_m')
            bundle.gebaeudehoehe_m = height_result.get('gebaeudehoehe_m')
            bundle.estimated_height_m = height_result.get('estimated_height_m')

            if height_result.get('measured_height_m'):
                bundle.height_source = DataSource.SWISSBUILDINGS3D
                bundle.height_quality = DataQuality.HIGH
            elif height_result.get('estimated_source') == 'calculated_from_floors':
                bundle.height_quality = DataQuality.MEDIUM
                bundle.add_warning(f"Höhe geschätzt aus {bundle.gwr_floors} Geschossen")
            else:
                bundle.height_quality = DataQuality.LOW
                bundle.add_warning(f"Höhe geschätzt: {height_result.get('estimated_source', 'Kategorie-Standard')}")

        except Exception as e:
            logger.warning(f"Fallback height lookup failed: {e}")

    def _load_roof_data_from_db(self, bundle: BuildingDataBundle):
        """
        NEU 11.01.2026: Lädt echte Dach-Daten aus building_roofs.

        Diese Daten kommen aus dem Roof_solid Layer (gleicher Tile-Import wie
        buildings_3d). Sie haben Vorrang vor berechneten Werten.

        Setzt:
        - roof_type (flachdach, satteldach, etc.)
        - roof_angle_deg
        - roof_orientation
        - roof_geometry_wkb (echte 3D-Geometrie)
        - roof_z_levels (für Analyse)
        - roof_dach_min_m / roof_dach_max_m (m ü.M.)
        """
        print(f"[ROOF_3D] _load_roof_data_from_db aufgerufen für EGID: {bundle.egid}")
        if not bundle.egid:
            print("[ROOF_3D] Kein EGID, return")
            return

        try:
            from app.services.roof_3d_service import get_roof_3d_service
            from app.services.building_3d_service import get_building_3d_service

            roof_service = get_roof_3d_service()
            building_service = get_building_3d_service()

            # 1. Versuche per EGID
            roof_data = roof_service.get_by_egid(str(bundle.egid))

            # 2. Falls nicht gefunden, über gebaeudeeinheit
            # FIX 12.01.2026: has_3d_layers aus building_3d laden
            building_data = building_service.get_by_egid(int(bundle.egid))
            if building_data:
                has_3d_raw = building_data.get('has_3d_layers', 0)
                bundle.has_3d_layers = has_3d_raw == 1
                print(f"[ROOF_3D] has_3d_layers für EGID {bundle.egid}: raw={has_3d_raw}, bundle={bundle.has_3d_layers}")
            
            if not roof_data:
                if building_data and building_data.get('gebaeudeeinheit'):
                    gebaeudeeinheit = building_data['gebaeudeeinheit']
                    bundle.roof_gebaeudeeinheit = gebaeudeeinheit
                    roof_data = roof_service.get_by_gebaeudeeinheit(gebaeudeeinheit)

            if not roof_data:
                logger.debug(f"[ROOF_3D] Keine Dach-Daten in DB für EGID {bundle.egid}")
                return

            # === Echte Dach-Daten übernehmen ===
            logger.info(
                f"[ROOF_3D] Echte Dach-Daten für EGID {bundle.egid}: "
                f"Form={roof_data.get('roof_form')}, "
                f"Orientierung={roof_data.get('roof_orientation')}, "
                f"has_geometry={roof_data.get('has_full_geometry')}"
            )

            # Dachform (primäre Quelle!)
            if roof_data.get('roof_form'):
                bundle.roof_type = roof_data['roof_form']
                bundle.roof_confidence = 0.95  # Hohe Konfidenz für echte Daten

            # FIX 11.01.2026 21:30 - 0.0 ist falsy, daher explizit None-Check
            # Neigung (0.0 ist gültig für Flachdächer!)
            if roof_data.get('roof_angle_deg') is not None:
                bundle.roof_angle_deg = roof_data['roof_angle_deg']

            # Orientierung (None ist gültig für Flachdächer ohne Orientierung)
            if roof_data.get('roof_orientation') is not None:
                bundle.roof_orientation = roof_data['roof_orientation']

            # Absolute Höhen (m ü.M.)
            bundle.roof_dach_min_m = roof_data.get('dach_min')
            bundle.roof_dach_max_m = roof_data.get('dach_max')

            # Z-Level Verteilung
            bundle.roof_z_levels = roof_data.get('z_levels')

            # Gebaeudeeinheit
            if roof_data.get('gebaeudeeinheit'):
                bundle.roof_gebaeudeeinheit = roof_data['gebaeudeeinheit']

            # 3D-Geometrie (für Frontend)
            if roof_data.get('has_full_geometry') and roof_data.get('geometry_wkb'):
                bundle.roof_geometry_wkb = roof_data['geometry_wkb']
                bundle.has_roof_geometry = True
                logger.info(f"[ROOF_3D] Echte 3D-Geometrie geladen für EGID {bundle.egid}")

                # FIX 14.01.2026 00:35: Falls roof_form fehlt aber Geometrie da ist → nachträglich analysieren
                if not roof_data.get('roof_form') and roof_data.get('geometry_wkb'):
                    try:
                        from shapely import wkb
                        from app.services.roof_form_detector import analyze_roof

                        geom = wkb.loads(roof_data['geometry_wkb'])
                        roof_analysis = analyze_roof(geom)

                        bundle.roof_type = roof_analysis.get('roof_form')
                        bundle.roof_angle_deg = roof_analysis.get('angle_deg')
                        bundle.roof_orientation = roof_analysis.get('orientation')
                        bundle.roof_confidence = roof_analysis.get('confidence', 0.8)
                        bundle.roof_z_levels = roof_analysis.get('z_levels')

                        logger.info(
                            f"[ROOF_3D] Nachträgliche Analyse für EGID {bundle.egid}: "
                            f"Form={bundle.roof_type}, Winkel={bundle.roof_angle_deg}°"
                        )
                    except Exception as e:
                        logger.warning(f"[ROOF_3D] Nachträgliche Analyse fehlgeschlagen: {e}")
            else:
                bundle.has_roof_geometry = False

        except Exception as e:
            logger.warning(f"[ROOF_3D] Fehler beim Laden der Dach-Daten: {e}")

    async def _collect_terrain_data(self, bundle: BuildingDataBundle):
        """Schritt 4: Terrain-Daten (Hanglage) - ENRICHMENT

        Sammelt Terrain-Daten und speichert sie in building_environment
        für persistentes Caching pro EGID.

        Hanglage-Klassifikation:
        - eben: < 0.5m
        - leicht: 0.5 - 1.5m (Stellspindeln reichen)
        - mittel: 1.5 - 3.0m (Ausgleichsrahmen nötig)
        - stark: > 3.0m (Spezielle Fundamentierung)
        """
        if not bundle.lv95_e or not bundle.lv95_n:
            logger.info(f"[TERRAIN] Skipping - no coordinates for {bundle.egid}")
            return

        logger.info(f"[TERRAIN] Starting collection for EGID {bundle.egid}")
        # Check cache first (building_environment)
        if bundle.egid:
            cached_terrain = self._load_terrain_from_environment(str(bundle.egid))
            if cached_terrain:
                bundle.terrain = cached_terrain
                bundle.add_source(DataSource.CACHE)
                logger.info(f"Terrain loaded from cache for EGID {bundle.egid}")

                # FIX 14.01.2026 17:10: Fassaden-Höhen auch bei gecachtem Terrain sammeln
                # Cache wurde vor T2-T4 erstellt → keine Fassaden-Höhen vorhanden
                # FIX 13.01.2026 23:50: Auch terrain_sampled→wall_layer Upgrade versuchen
                # wall_layer ist präziser als terrain_sampled, daher Upgrade-Versuch
                should_collect = (
                    not cached_terrain.facade_z_min or  # Keine Daten
                    cached_terrain.facade_heights_source == "global" or  # Nur Fallback
                    (cached_terrain.facade_heights_source == "terrain_sampled" and bundle.has_3d_layers)  # Upgrade möglich
                )
                if should_collect:
                    logger.info(f"[FACADE_HEIGHTS] Collecting for cached terrain, EGID {bundle.egid}, source={cached_terrain.facade_heights_source}, has_3d={bundle.has_3d_layers}")
                    await self._collect_facade_heights(bundle)
                    # Cache aktualisieren mit neuen Fassaden-Höhen (nur wenn besser)
                    if bundle.terrain.facade_heights_source == "wall_layer":
                        self._save_terrain_to_environment(bundle)
                        logger.info(f"[FACADE_HEIGHTS] Cache upgraded to wall_layer for EGID {bundle.egid}")
                return

        try:
            from app.services.terrain import get_terrain_service
            terrain_service = get_terrain_service()

            # Haupthöhe am Gebäudezentrum
            ref_height = await terrain_service.get_height(bundle.lv95_e, bundle.lv95_n)

            if ref_height is not None:
                bundle.terrain = TerrainProfile(reference_height_m=ref_height)
                bundle.add_source(DataSource.SWISSALTI3D)

                # Hanglage über alle Polygon-Punkte berechnen
                # OPTIMIERT 10.01.2026: Parallele API-Calls (~2.5s → ~0.3s)
                if bundle.polygon and len(bundle.polygon) >= 3:
                    # Sample max 8 Punkte für Performance
                    step = max(1, len(bundle.polygon) // 8)
                    sample_points = [bundle.polygon[i] for i in range(0, len(bundle.polygon), step)]

                    # Alle Höhen-Calls PARALLEL ausführen
                    height_tasks = [terrain_service.get_height(p[0], p[1]) for p in sample_points]
                    height_results = await asyncio.gather(*height_tasks, return_exceptions=True)
                    heights = [h for h in height_results if isinstance(h, (int, float))]

                    if heights:
                        bundle.terrain.min_height_m = min(heights)
                        bundle.terrain.max_height_m = max(heights)
                        slope_m = max(heights) - min(heights)
                        bundle.terrain.slope_m = slope_m
                        bundle.terrain.is_sloped = slope_m > 1.0

                        # Hanglage-Klassifikation
                        if slope_m < 0.5:
                            bundle.terrain.slope_class = "eben"
                        elif slope_m < 1.5:
                            bundle.terrain.slope_class = "leicht"
                            bundle.terrain.requires_level_compensation = True
                        elif slope_m < 3.0:
                            bundle.terrain.slope_class = "mittel"
                            bundle.terrain.requires_level_compensation = True
                        else:
                            bundle.terrain.slope_class = "stark"
                            bundle.terrain.requires_level_compensation = True

                        bundle.terrain.max_compensation_m = slope_m

                        if bundle.terrain.is_sloped:
                            bundle.add_warning(
                                f"Hanglage erkannt: {slope_m:.1f}m ({bundle.terrain.slope_class})"
                            )

                # NEU 14.01.2026: Fassaden-Höhen aus Wall-Layer (T2)
                # Fallback-Kette: 1. Wall-Layer → 2. Terrain-Sampling → 3. Global
                await self._collect_facade_heights(bundle)

                # Terrain in building_environment speichern (persistenter Cache pro EGID)
                if bundle.egid:
                    self._save_terrain_to_environment(bundle)

        except Exception as e:
            logger.error(f"Terrain error: {e}")
            bundle.add_warning(f"Terrain-Daten nicht verfügbar: {str(e)}")

    def _load_terrain_from_environment(self, egid: str) -> Optional[TerrainProfile]:
        """Lädt Terrain-Daten aus building_environment Cache."""
        try:
            from app.services.intelligent_db import IntelligentDBService
            db_service = IntelligentDBService()

            env = db_service.get_building_environment(egid)
            if env and env.terrain_data:
                t = env.terrain_data
                # Check if we have valid terrain data
                if t.get("height_m") is not None:
                    terrain = TerrainProfile(
                        reference_height_m=t.get("height_m", 0),
                        min_height_m=t.get("min_terrain_m"),
                        max_height_m=t.get("max_terrain_m"),
                        slope_m=t.get("slope_m"),
                        slope_class=t.get("slope_class", "eben"),
                        is_sloped=t.get("slope_m", 0) > 1.0 if t.get("slope_m") else False,
                        requires_level_compensation=t.get("requires_level_compensation", False),
                        # NEU 14.01.2026 (T2): Fassaden-Höhen aus Wall-Layer
                        facade_z_min=t.get("facade_z_min", {}),
                        facade_z_max=t.get("facade_z_max", {}),
                        facade_heights_source=t.get("facade_heights_source", "global"),
                    )
                    return terrain
            return None
        except Exception as e:
            logger.warning(f"Could not load terrain from cache: {e}")
            return None

    def _save_terrain_to_environment(self, bundle: BuildingDataBundle):
        """Speichert Terrain-Daten in building_environment für persistentes Caching."""
        try:
            from app.services.intelligent_db import IntelligentDBService
            db_service = IntelligentDBService()

            terrain_data = {
                "height_m": bundle.terrain.reference_height_m if bundle.terrain else None,
                "min_terrain_m": bundle.terrain.min_height_m if bundle.terrain else None,
                "max_terrain_m": bundle.terrain.max_height_m if bundle.terrain else None,
                "slope_m": bundle.terrain.slope_m if bundle.terrain else None,
                "slope_class": bundle.terrain.slope_class if bundle.terrain else "eben",
                "requires_level_compensation": bundle.terrain.requires_level_compensation if bundle.terrain else False,
                # NEU 14.01.2026 (T2): Fassaden-Höhen aus Wall-Layer
                "facade_z_min": bundle.terrain.facade_z_min if bundle.terrain else {},
                "facade_z_max": bundle.terrain.facade_z_max if bundle.terrain else {},
                "facade_heights_source": bundle.terrain.facade_heights_source if bundle.terrain else "global",
            }

            db_service.set_building_environment(
                egid=str(bundle.egid),
                surrounding_buildings=[],  # Werden dynamisch abgerufen
                blocked_facades=[],
                terrain_data=terrain_data
            )
            logger.info(f"Terrain saved for EGID {bundle.egid}: {bundle.terrain.slope_class}")
        except Exception as e:
            logger.warning(f"Could not save terrain to environment: {e}")

    async def _collect_facade_heights(self, bundle: BuildingDataBundle):
        """NEU 14.01.2026 (T2): Sammelt Fassaden-Höhen aus Wall-Layer.

        Fallback-Kette:
        1. Wall-Layer (höchste Präzision) - wenn has_3d_layers=True
        2. Terrain-Sampling (gute Präzision) - swissALTI3D pro Fassade
        3. Global (Fallback) - Referenz-Höhe für alle Fassaden

        Die Daten werden in TerrainProfile.facade_z_min/facade_z_max gespeichert.
        """
        if not bundle.terrain:
            return

        if not bundle.sides:
            # Keine Fassaden bekannt → Global-Fallback
            bundle.terrain.facade_heights_source = "global"
            return

        # STUFE 1: Wall-Layer Matching (wenn 3D-Daten verfügbar)
        logger.info(f"[FACADE-HEIGHTS] Check: has_3d_layers={bundle.has_3d_layers}, egid={bundle.egid}")
        if bundle.has_3d_layers and bundle.egid:
            try:
                from .wall_facade_matcher import get_wall_facade_matcher
                matcher = get_wall_facade_matcher()

                logger.info(f"[FACADE-HEIGHTS] Calling has_wall_data({bundle.egid})...")
                # Prüfen ob Wall-Daten vorhanden
                if matcher.has_wall_data(bundle.egid):
                    facade_heights = matcher.get_facade_heights(bundle.egid, bundle.sides)

                    if facade_heights:
                        # Übertragen in TerrainProfile
                        for direction, fh in facade_heights.items():
                            bundle.terrain.facade_z_min[direction] = fh.z_min
                            bundle.terrain.facade_z_max[direction] = fh.z_max

                        bundle.terrain.facade_heights_source = "wall_layer"
                        logger.info(
                            f"[FACADE-HEIGHTS] Wall-Layer: {len(facade_heights)} Fassaden "
                            f"für EGID {bundle.egid}"
                        )
                        return

            except Exception as e:
                logger.warning(f"[FACADE-HEIGHTS] Wall-Layer Fehler: {e}")

        # STUFE 2: Terrain-Sampling (swissALTI3D pro Fassaden-Startpunkt)
        try:
            from app.services.terrain import get_terrain_service
            terrain_service = get_terrain_service()

            sampled_count = 0
            # FIX 14.01.2026: Absolute Dachkanten-Höhe (gleich für alle Fassaden!)
            # Bei Hanglage ist das Dach horizontal, nur das Terrain variiert.
            absolute_dach_hoehe = None
            if bundle.terrain and bundle.terrain.reference_height_m and bundle.traufhoehe_m:
                absolute_dach_hoehe = bundle.terrain.reference_height_m + bundle.traufhoehe_m

            for side in bundle.sides:
                direction = side.get("direction", "?")
                start_point = side.get("start_point") or side.get("start", {})

                if isinstance(start_point, dict):
                    e = start_point.get("x") or start_point.get("e")
                    n = start_point.get("y") or start_point.get("n")
                elif isinstance(start_point, (list, tuple)) and len(start_point) >= 2:
                    e, n = start_point[0], start_point[1]
                else:
                    continue

                if e and n:
                    terrain_height = await terrain_service.get_height(e, n)
                    if terrain_height is not None:
                        bundle.terrain.facade_z_min[direction] = terrain_height
                        # FIX: z_max ist KONSTANT (absolute Dachkanten-Höhe)
                        if absolute_dach_hoehe:
                            bundle.terrain.facade_z_max[direction] = absolute_dach_hoehe
                        sampled_count += 1

            if sampled_count > 0:
                bundle.terrain.facade_heights_source = "terrain_sampled"
                # Log mit Höhendifferenz für Hanglage-Erkennung
                if bundle.terrain.facade_z_min:
                    min_terrain = min(bundle.terrain.facade_z_min.values())
                    max_terrain = max(bundle.terrain.facade_z_min.values())
                    height_diff = max_terrain - min_terrain
                    logger.info(
                        f"[FACADE-HEIGHTS] Terrain-Sampling: {sampled_count} Fassaden, "
                        f"Hanglage: {height_diff:.2f}m"
                    )
                return

        except Exception as e:
            logger.warning(f"[FACADE-HEIGHTS] Terrain-Sampling Fehler: {e}")

        # STUFE 3: Global-Fallback (alle Fassaden gleiche Höhe)
        bundle.terrain.facade_heights_source = "global"
        ref_height = bundle.terrain.reference_height_m
        absolute_dach_hoehe = ref_height + bundle.traufhoehe_m if bundle.traufhoehe_m else None
        for side in bundle.sides:
            direction = side.get("direction", "?")
            bundle.terrain.facade_z_min[direction] = ref_height
            if absolute_dach_hoehe:
                bundle.terrain.facade_z_max[direction] = absolute_dach_hoehe

        logger.info(f"[FACADE-HEIGHTS] Global-Fallback für {len(bundle.sides)} Fassaden")

    async def _calculate_roof_data(self, bundle: BuildingDataBundle):
        """Schritt 6: Dach-Analyse (berechnet) - NUR ALS FALLBACK!

        NEU 11.01.2026: Diese Methode wird nur ausgeführt wenn KEINE echten
        Dach-Daten aus building_roofs (Roof_solid Layer) vorhanden sind.

        Priorität:
        1. building_roofs (echte 3D-Daten) → bereits in _load_roof_data_from_db()
        2. Berechnet (diese Methode) → nur als Fallback
        """
        # Skip wenn bereits echte Dach-Daten vorhanden
        if bundle.roof_type and bundle.roof_confidence >= 0.9:
            logger.debug(
                f"[ROOF] Skip Berechnung - echte Daten vorhanden: "
                f"type={bundle.roof_type}, confidence={bundle.roof_confidence}"
            )
            return

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
                # Nur setzen wenn noch nicht vorhanden
                if not bundle.roof_type:
                    bundle.roof_type = result.roof_type.value if hasattr(result.roof_type, 'value') else str(result.roof_type)
                if not bundle.roof_angle_deg:
                    bundle.roof_angle_deg = result.roof_angle_deg
                if not bundle.roof_orientation:
                    bundle.roof_orientation = result.roof_orientation

                # Diese werden immer gesetzt (ergänzend)
                bundle.roof_area_m2 = result.roof_area_m2

                # Konfidenz nur setzen wenn noch keine echten Daten
                if bundle.roof_confidence < 0.9:
                    bundle.roof_confidence = result.confidence
                    bundle.add_source(DataSource.CALCULATED)
                    logger.info(f"[ROOF] Berechnet: type={bundle.roof_type}, angle={bundle.roof_angle_deg}°")

        except Exception as e:
            logger.error(f"Roof calculation error: {e}")

    async def _collect_sonnendach_data(self, bundle: BuildingDataBundle):
        """Schritt 6b: Ergänzende Dachgeometrie aus Sonnendach.ch (BFE) - ENRICHMENT

        NEU 11.01.2026: Diese Methode ist NUR für ERGÄNZENDE Daten zuständig!
        Echte Dach-Daten aus building_roofs (Roof_solid) haben VORRANG.

        Priorität der Datenquellen:
        1. building_roofs (Roof_solid Layer) → in _load_roof_data_from_db()
        2. Sonnendach.ch (diese Methode) → NUR ergänzend
        3. Berechnet (_calculate_roof_data) → Fallback

        Sonnendach.ch liefert ERGÄNZEND:
        - roof_surfaces: Dachflächen-Polygone mit Eignung
        - roof_tilt_deg: Neigung (Sonnendach-spezifisch)
        - roof_azimuth_deg: Ausrichtung (Sonnendach-spezifisch)
        - roof_overhang_m: Dachüberstand (NICHT in building_roofs!)

        ÜBERSCHREIBT NICHT (wenn aus building_roofs vorhanden):
        - roof_type
        - roof_angle_deg
        - roof_orientation

        Falls keine Daten: Standard-Dachüberstand 40cm wird verwendet.
        """
        if not bundle.lv95_e or not bundle.lv95_n:
            return

        try:
            from app.services.sonnendach_service import get_sonnendach_service

            sonnendach = get_sonnendach_service()
            analysis = await sonnendach.analyze_roof(bundle.lv95_e, bundle.lv95_n)

            if analysis.has_data and analysis.surfaces:
                bundle.sonnendach_available = True
                bundle.add_source(DataSource.SONNENDACH)

                # Dachflächen speichern
                bundle.roof_surfaces = [
                    {
                        "id": s.id,
                        "area_m2": s.area_m2,
                        "tilt_deg": s.tilt_degrees,
                        "azimuth_deg": s.azimuth_degrees,
                        "eignung": s.eignung,
                        "polygon": s.polygon,
                    }
                    for s in analysis.surfaces
                ]

                # === ENRICHMENT: Ergänzende Daten (NICHT überschreiben!) ===
                # NEU 11.01.2026: Echte Dach-Daten aus building_roofs haben Vorrang!

                # Neigung: Sonnendach-spezifisches Feld (immer setzen)
                if analysis.main_tilt_degrees:
                    bundle.roof_tilt_deg = analysis.main_tilt_degrees
                    # roof_angle_deg nur setzen wenn KEINE echten Daten (confidence < 0.9)
                    if bundle.roof_angle_deg is None or bundle.roof_confidence < 0.9:
                        bundle.roof_angle_deg = analysis.main_tilt_degrees
                        # Nur Konfidenz erhöhen wenn noch keine echten Daten
                        if bundle.roof_confidence < 0.9:
                            bundle.roof_confidence = 0.85  # Sonnendach ist gut, aber nicht so gut wie Roof_solid

                # Dachtyp: NUR setzen wenn KEINE echten Daten vorhanden!
                if analysis.roof_type and (not bundle.roof_type or bundle.roof_confidence < 0.9):
                    sonnendach_roof_type = analysis.roof_type
                    # Mapping: flat→flachdach, gabled→satteldach, hipped→walmdach
                    type_map = {
                        "flat": "flachdach",
                        "gabled": "satteldach",
                        "hipped": "walmdach",
                        "complex": "komplex",
                    }
                    bundle.roof_type = type_map.get(sonnendach_roof_type, bundle.roof_type)
                    logger.debug(f"[SONNENDACH] roof_type gesetzt: {bundle.roof_type}")

                # Azimut: Sonnendach-spezifisches Feld (immer setzen)
                # roof_orientation: NUR setzen wenn KEINE echten Daten!
                if analysis.main_orientation:
                    azimuth_deg = self._calculate_weighted_azimuth(analysis.surfaces)
                    if azimuth_deg is not None:
                        bundle.roof_azimuth_deg = azimuth_deg  # Immer setzen (Sonnendach-spezifisch)

                        # roof_orientation nur setzen wenn keine echten Daten
                        if not bundle.roof_orientation or bundle.roof_confidence < 0.9:
                            if (67.5 <= azimuth_deg < 112.5) or (247.5 <= azimuth_deg < 292.5):
                                bundle.roof_orientation = "O-W"
                            else:
                                bundle.roof_orientation = "N-S"
                            logger.info(f"Sonnendach Ausrichtung: {analysis.main_orientation} → "
                                       f"azimuth={azimuth_deg:.1f}° → {bundle.roof_orientation}")

                # Dachüberstand aus Polygon-Differenz berechnen
                overhang = self._calculate_roof_overhang(bundle, analysis.surfaces)
                if overhang is not None:
                    bundle.roof_overhang_m = overhang
                    logger.info(f"Dachüberstand aus Sonnendach berechnet: {overhang:.2f}m")

                logger.info(f"Sonnendach.ch: {len(analysis.surfaces)} Dachflächen, "
                           f"Typ={analysis.roof_type}, Neigung={analysis.main_tilt_degrees}°")
            else:
                logger.debug(f"Keine Sonnendach.ch Daten für E={bundle.lv95_e}, N={bundle.lv95_n}")
                # Standard-Dachüberstand bleibt bei 0.4m (Model-Default)

        except Exception as e:
            logger.warning(f"Sonnendach.ch error: {e}")
            # Standard-Dachüberstand bleibt bei 0.4m

    def _calculate_weighted_azimuth(self, surfaces: list) -> Optional[float]:
        """
        Berechnet flächen-gewichteten Durchschnitts-Azimut aus Sonnendach-Flächen.

        Args:
            surfaces: Liste von RoofSurface Objekten

        Returns:
            Azimut in Grad (0-360°) oder None
        """
        import math

        if not surfaces:
            return None

        total_weight = 0.0
        weighted_sum_sin = 0.0
        weighted_sum_cos = 0.0

        for surface in surfaces:
            azimuth = getattr(surface, 'azimuth_degrees', None)
            area = getattr(surface, 'area_m2', None)

            if azimuth is not None and area and area > 0:
                rad = math.radians(azimuth)
                weighted_sum_sin += area * math.sin(rad)
                weighted_sum_cos += area * math.cos(rad)
                total_weight += area

        if total_weight == 0:
            return None

        avg_azimuth = math.degrees(math.atan2(
            weighted_sum_sin / total_weight,
            weighted_sum_cos / total_weight
        ))

        # Normalisieren auf 0-360°
        if avg_azimuth < 0:
            avg_azimuth += 360

        return round(avg_azimuth, 1)

    def _calculate_roof_overhang(
        self,
        bundle: BuildingDataBundle,
        roof_surfaces: list
    ) -> Optional[float]:
        """
        Berechnet Dachüberstand aus Differenz zwischen Dach-Polygon und Gebäude-Polygon.

        Der Dachüberstand ist der Abstand zwischen der Gebäudekante und dem
        äussersten Punkt des Daches in derselben Richtung.

        Returns:
            Dachüberstand in Metern oder None wenn nicht berechenbar
        """
        if not bundle.polygon or not roof_surfaces:
            return None

        try:
            # Gebäude Bounding Box
            bldg_xs = [p[0] for p in bundle.polygon]
            bldg_ys = [p[1] for p in bundle.polygon]
            bldg_min_x, bldg_max_x = min(bldg_xs), max(bldg_xs)
            bldg_min_y, bldg_max_y = min(bldg_ys), max(bldg_ys)

            # Alle Dach-Polygone zu einer Bounding Box kombinieren
            roof_xs = []
            roof_ys = []
            for surface in roof_surfaces:
                polygon = surface.polygon if hasattr(surface, 'polygon') else surface.get('polygon', [])
                if polygon:
                    roof_xs.extend([p[0] for p in polygon])
                    roof_ys.extend([p[1] for p in polygon])

            if not roof_xs or not roof_ys:
                return None

            roof_min_x, roof_max_x = min(roof_xs), max(roof_xs)
            roof_min_y, roof_max_y = min(roof_ys), max(roof_ys)

            # Überhang in jede Richtung
            overhang_left = bldg_min_x - roof_min_x
            overhang_right = roof_max_x - bldg_max_x
            overhang_bottom = bldg_min_y - roof_min_y
            overhang_top = roof_max_y - bldg_max_y

            # Durchschnitt der positiven Überhänge (Dach ragt über Gebäude)
            overhangs = [o for o in [overhang_left, overhang_right, overhang_bottom, overhang_top] if o > 0]

            if overhangs:
                avg_overhang = sum(overhangs) / len(overhangs)
                # Plausibilitätsprüfung: 0.2m bis 1.5m ist realistisch
                if 0.2 <= avg_overhang <= 1.5:
                    return round(avg_overhang, 2)
                elif avg_overhang < 0.2:
                    return 0.3  # Minimum
                else:
                    return 1.0  # Maximum für normale Gebäude

            return None

        except Exception as e:
            logger.warning(f"Roof overhang calculation error: {e}")
            return None

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

    # ========================================================================
    # BuildingContext Integration - Konsistente Zonen für Frontend & Prompt
    # ========================================================================

    def _load_zones_from_building_context(self, egid: str) -> Optional[List[ZoneInfo]]:
        """
        Lädt validierte Zonen aus building_contexts.db.

        Wenn der Benutzer die Zonen im Frontend bearbeitet und gespeichert hat,
        werden diese Zonen hier geladen und für das Prompt verwendet.

        Returns:
            List[ZoneInfo] wenn validierte Zonen existieren, sonst None
        """
        if not egid:
            return None

        try:
            from app.services.building_context import get_building_context_service
            context_service = get_building_context_service()
            context = context_service.get_context(egid)

            if not context:
                return None

            # Nur validierte Kontexte verwenden
            if not context.validated_by_user:
                logger.debug(f"BuildingContext for {egid} exists but is not validated by user")
                return None

            if not context.zones:
                return None

            # BuildingZone → ZoneInfo konvertieren
            zones = []
            for bz in context.zones:
                zone = ZoneInfo(
                    id=bz.id,
                    name=bz.name,
                    zone_type=bz.type.value if isinstance(bz.type, ZoneType) else str(bz.type),
                    traufhoehe_m=bz.traufhoehe_m,
                    firsthoehe_m=bz.firsthoehe_m,
                    gebaeudehoehe_m=bz.gebaeudehoehe_m,
                    position=bz.position,  # NEU: Position für 3D-Darstellung
                    beruesten=bz.beruesten if bz.beruesten is not None else True,
                    sonderkonstruktion=bz.sonderkonstruktion if bz.sonderkonstruktion is not None else False,
                    confidence=bz.confidence if bz.confidence else 1.0,
                    source=DataSource.MANUAL,  # Aus BuildingContext = manuell validiert
                    notes=bz.notes,
                )
                zones.append(zone)

            logger.info(f"Loaded {len(zones)} validated zones from BuildingContext for EGID {egid}")
            return zones

        except Exception as e:
            logger.error(f"Error loading zones from BuildingContext: {e}")
            return None

    def _save_zones_to_building_context(self, bundle: BuildingDataBundle):
        """
        Speichert die Zonen aus dem Bundle in building_contexts.db.

        Dies stellt sicher, dass das Frontend dieselben Zonen anzeigt,
        die auch für das Prompt verwendet wurden.
        """
        if not bundle.egid or not bundle.zones:
            return

        try:
            from app.services.building_context import get_building_context_service
            context_service = get_building_context_service()

            # Prüfen ob bereits ein validierter Kontext existiert
            existing = context_service.get_context(bundle.egid)
            if existing and existing.validated_by_user:
                logger.debug(f"BuildingContext for {bundle.egid} already validated by user, not overwriting")
                return

            # ZoneInfo → BuildingZone konvertieren
            building_zones = []
            for zi in bundle.zones:
                # ZoneType enum aus string
                zone_type = ZoneType.HAUPTGEBAEUDE
                try:
                    zone_type = ZoneType(zi.zone_type)
                except ValueError:
                    # Fallback für unbekannte Typen
                    if "turm" in zi.zone_type.lower():
                        zone_type = ZoneType.TURM
                    elif "kuppel" in zi.zone_type.lower():
                        zone_type = ZoneType.KUPPEL
                    elif "arkade" in zi.zone_type.lower():
                        zone_type = ZoneType.ARKADE
                    elif "anbau" in zi.zone_type.lower():
                        zone_type = ZoneType.ANBAU

                bz = BuildingZone(
                    id=zi.id,
                    name=zi.name,
                    type=zone_type,
                    position=zi.position,  # NEU: Position für 3D-Darstellung
                    traufhoehe_m=zi.traufhoehe_m,
                    firsthoehe_m=zi.firsthoehe_m,
                    gebaeudehoehe_m=zi.gebaeudehoehe_m,
                    beruesten=zi.beruesten,
                    sonderkonstruktion=zi.sonderkonstruktion,
                    confidence=zi.confidence,
                    notes=zi.notes,
                )
                building_zones.append(bz)

            # BuildingContext erstellen oder aktualisieren
            from app.models.building_context import ComplexityLevel, ContextSource

            # Complexity zu enum konvertieren
            complexity_level = ComplexityLevel.SIMPLE
            if bundle.complexity:
                try:
                    complexity_level = ComplexityLevel(bundle.complexity)
                except ValueError:
                    pass

            context = BuildingContext(
                egid=bundle.egid,
                adresse=bundle.address_matched,
                building_name=bundle.building_name,
                zones=building_zones,
                complexity=complexity_level,
                has_height_variations=bundle.has_height_variations,
                has_towers=bundle.has_towers,
                has_annexes=bundle.has_annexes,
                validated_by_user=False,  # Nicht automatisch validiert - User muss bestätigen
                source=ContextSource.AUTO,  # Automatisch erstellt
            )

            context_service.save_context(context)
            logger.info(f"Saved {len(building_zones)} zones to BuildingContext for EGID {bundle.egid}")

        except Exception as e:
            logger.error(f"Error saving zones to BuildingContext: {e}")

    # ========================================================================

    def _create_default_zone(self, bundle: BuildingDataBundle):
        """Erstellt Standard-Zone(n) basierend auf Höhendaten

        PRIORITÄT:
        0. Validierte Zonen aus BuildingContext (User-editiert)
        1. Zonen aus bekannten Gebäuden (_known_zones)
        2. Kirchen-spezifische Zonen bei Sakralbauten
        3. Standard-Zonen bei extremer Höhendifferenz
        4. Einfache Zone für normale Gebäude

        Nach Erstellung werden die Zonen in BuildingContext gespeichert,
        damit das Frontend dieselben Daten anzeigt.
        """
        if bundle.zones:
            return  # Bereits Zonen vorhanden

        # 0. NEUE PRIORITÄT: Validierte Zonen aus BuildingContext laden
        # Falls der User die Zonen im Frontend editiert und gespeichert hat
        if bundle.egid:
            validated_zones = self._load_zones_from_building_context(bundle.egid)
            if validated_zones:
                bundle.zones = validated_zones
                logger.info(f"Using {len(validated_zones)} validated zones from BuildingContext")
                return

        # 1. Bekannte Gebäude-Zonen
        from .research_integration import create_zones_from_known_building
        if create_zones_from_known_building(bundle):
            # Zonen in BuildingContext speichern für Frontend-Konsistenz
            self._save_zones_to_building_context(bundle)
            return

        # 2. Kirchen-spezifische Zonen
        from .research_integration import create_church_zones
        if create_church_zones(bundle):
            # Zonen in BuildingContext speichern für Frontend-Konsistenz
            self._save_zones_to_building_context(bundle)
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

            # Zonen in BuildingContext speichern für Frontend-Konsistenz
            self._save_zones_to_building_context(bundle)

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

            # Zonen in BuildingContext speichern für Frontend-Konsistenz
            self._save_zones_to_building_context(bundle)

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

    # ========================================================================
    # Multi-Building Support (NEU 11.01.2026)
    # ========================================================================

    async def _collect_multi_building_data(
        self,
        addresses: List[str],
        force_refresh: bool = False,
        include_research: bool = True,
        include_zones_analysis: bool = True,
        include_terrain: bool = True,
    ) -> List[BuildingDataBundle]:
        """
        Sammelt Daten für mehrere Gebäude (z.B. "Knospenweg 4-6").

        Ablauf:
        1. Geocoding für alle Adressen (parallel)
        2. Centroid berechnen (für Tile-Download Optimierung)
        3. Für jedes Gebäude: _enrich_building() mit interner Cache-Prüfung
        4. Liste der Bundles zurückgeben

        Args:
            addresses: Liste von Adressen
            force_refresh: Cache ignorieren
            include_research: Claude-Recherche
            include_zones_analysis: Claude-Analyse
            include_terrain: Terrain-Daten

        Returns:
            List[BuildingDataBundle] für alle Gebäude
        """
        if not addresses:
            return []

        logger.info(f"[MULTI-BUILDING] Starte Datensammlung für {len(addresses)} Adressen")

        # Phase 1: Bundles erstellen und Geocoding durchfuehren
        bundles = []
        for addr in addresses:
            bundle = BuildingDataBundle(
                address_input=addr,
                collection_timestamp=datetime.now(),
            )
            await self._collect_geocoding(bundle)
            if bundle.lv95_e and bundle.lv95_n:
                bundles.append(bundle)
            else:
                logger.warning(f"Geocoding failed for {addr}")

        if not bundles:
            logger.error("[MULTI-BUILDING] Kein Geocoding erfolgreich")
            return []

        logger.info(f"[MULTI-BUILDING] {len(bundles)}/{len(addresses)} Adressen geocodiert")

        # Phase 2: Centroid berechnen aus allen Koordinaten
        centroid_e = sum(b.lv95_e for b in bundles) / len(bundles)
        centroid_n = sum(b.lv95_n for b in bundles) / len(bundles)
        logger.info(f"[MULTI-BUILDING] Centroid: E={centroid_e:.1f}, N={centroid_n:.1f}")

        # Phase 3: Tile laden mit Centroid (triggert Prefetch fuer alle Gebaeude)
        await self._ensure_tile_loaded(centroid_e, centroid_n)

        # Phase 4: Fuer jedes Bundle: Enrichment durchfuehren
        enriched_bundles = []
        for bundle in bundles:
            # Enrichment via bestehende Methoden
            await self._collect_gwr_data(bundle)
            await self._collect_building_3d_data(bundle)
            if include_terrain:
                await self._collect_terrain_data(bundle)
            await self._collect_sonnendach_data(bundle)
            await self._calculate_roof_data(bundle)
            # FIX 12.01.2026: Research ZUERST aufrufen um _known_zones zu setzen
            # Dann erst Zonen erstellen (damit bekannte Gebäude korrekte Zonen bekommen)
            if include_research:
                await self._collect_research_data(bundle, force_refresh)
            if include_zones_analysis:
                self._create_default_zone(bundle)
            # 3D-Geometrie für komplexe Gebäude laden
            self._fetch_roof_geometry_for_complex(bundle)
            self._calculate_access_points(bundle)
            self._assess_data_quality(bundle)
            cache_key = self._cache_key(bundle.address_input, bundle.egid)
            self._save_bundle_cache(cache_key, bundle)
            enriched_bundles.append(bundle)

        logger.info(f"[MULTI-BUILDING] {len(bundles)} Bundles erstellt")
        return bundles

    async def _ensure_tile_loaded(self, e: float, n: float):
        """Stellt sicher, dass das Tile für die Koordinaten geladen ist."""
        try:
            from app.services.swissbuildings3d_fetcher import fetch_building_polygon_for_coordinates
            # Dieser Aufruf triggert automatisch den Tile-Download und Prefetch
            await fetch_building_polygon_for_coordinates(e=e, n=n, tolerance_m=50.0)
        except Exception as e:
            logger.warning(f"Tile loading failed for E={e}, N={n}: {e}")

    def _fetch_roof_geometry_for_complex(self, bundle: BuildingDataBundle):
        """NEU 12.01.2026: Lädt ALLE 3D-Layer (Roof, Wall) für komplexe Gebäude on-demand.

        Wird UNABHÄNGIG von include_zones aufgerufen. Nutzt _needs_zones_analysis()
        um die Komplexität zu prüfen, sodass die Geometrie auch bei
        include_zones=false geladen wird (z.B. geruestbau-app).

        Geladene Layer:
        - Roof_solid → building_roofs.geometry_wkb
        - Wall → building_walls.geometry_wkb
        """
        # Nur für Gebäude mit EGID
        if not bundle.egid:
            return

        # Prüfe Komplexität über _needs_zones_analysis() ODER bereits gesetzte complexity
        # Das funktioniert auch wenn include_zones=false (geruestbau-app)
        is_complex = bundle.complexity == "complex" or self._needs_zones_analysis(bundle)
        if not is_complex:
            return

        try:
            from app.services.roof_3d_service import get_roof_3d_service

            roof_service = get_roof_3d_service()
            # NEU: Alle Layer laden (Roof_solid, Roof, Wall)
            result = roof_service.fetch_all_layers_on_demand(bundle.egid)

            if result['loaded_layers']:
                logger.info(
                    f"[COMPLEX] 3D-Layer für EGID {bundle.egid} geladen: {result['loaded_layers']}"
                )
            else:
                logger.debug(f"[COMPLEX] Keine 3D-Geometrie für EGID {bundle.egid} verfügbar")

        except Exception as e:
            logger.warning(f"[COMPLEX] Fehler beim Laden der 3D-Layer für {bundle.egid}: {e}")

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
                "coordinates": bundle.polygon,  # Original from swissBUILDINGS3D
                "coordinate_system": "LV95 (EPSG:2056)",
                "point_count": len(bundle.polygon),
                "sides_from_simplified": bundle.sides_from_simplified,
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
