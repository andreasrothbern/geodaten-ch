"""Gerüstbau Project Service - Projekt-Verwaltung mit geodaten-ch Integration."""

import uuid
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

from ...models.geruestbau import (
    Project, ProjectCreate, ProjectUpdate, ProjectStatus,
    ProjectWithGeodata, ProjectWithGeruestbaudata,
    PhotoAnalysis, ScaffoldConfig, ScaffoldZone
)
from ..swisstopo import SwisstopoService
from ..swissbuildings3d_service import get_swissbuildings3d_service
from ..smart_building import get_smart_building_service
# NEU 14.01.2026 13:15: Verwende DATA_DIR aus config für Railway Volume
from app.config import GERUESTBAU_DB_PATH, BUILDING_CONTEXTS_DB_PATH


class ProjectService:
    """Service für Gerüstbau-Projekt-Verwaltung."""

    def __init__(self):
        # NEU 14.01.2026 13:15: Nutze zentrale Pfade aus config.py für Railway Volume
        self.db_path = GERUESTBAU_DB_PATH
        self.contexts_db_path = BUILDING_CONTEXTS_DB_PATH
        self.swisstopo = SwisstopoService()
        self._init_db()

    def _init_db(self):
        """Datenbank initialisieren."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                egid TEXT,
                client_name TEXT,
                client_contact TEXT,
                deadline TEXT,
                description TEXT,
                building_data TEXT,
                scaffold_config TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photos (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                file_path TEXT,
                direction TEXT,
                analysis TEXT,
                created_at TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        ''')

        # DB-Migrationen: Fehlende Spalten hinzufügen
        # (für bestehende DBs die vor verschiedenen Features erstellt wurden)
        cursor.execute("PRAGMA table_info(projects)")
        columns = [col[1] for col in cursor.fetchall()]

        # Alle erwarteten Spalten die evtl. fehlen könnten
        migrations = {
            'description': 'TEXT',      # SIMAP-Import Feature
            'building_data': 'TEXT',    # Geodaten-Anreicherung (Legacy)
            'scaffold_config': 'TEXT',  # Gerüst-Konfiguration
            'buildings': 'TEXT',        # Multi-Building Support (JSON array)
            'geruestbaudata': 'TEXT',   # DEPRECATED - Single-Building Format
            # NEU 16.01.2026: buildings_data als Record<EGID, GeruestbauData>
            'buildings_data': 'TEXT',   # Multi-Building fähig: {"egid1": {...}, "egid2": {...}}
        }

        for col_name, col_type in migrations.items():
            if col_name not in columns:
                cursor.execute(f"ALTER TABLE projects ADD COLUMN {col_name} {col_type}")
                print(f"[Gerüstbau] DB-Migration: {col_name} Spalte hinzugefügt")

        conn.commit()
        conn.close()

    async def create_project(self, data: ProjectCreate) -> Project:
        """Neues Projekt erstellen."""
        project_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        # Building data als JSON serialisieren (optional)
        building_data_json = None
        egid = getattr(data, 'egid', None)  # EGID kann direkt im ProjectCreate sein

        # Falls building_data vorhanden (für erweiterte Projekt-Erstellung)
        building_data = getattr(data, 'building_data', None)
        if building_data:
            building_data_dict = building_data.model_dump() if hasattr(building_data, 'model_dump') else building_data
            building_data_json = json.dumps(building_data_dict)
            if hasattr(building_data, 'egid') and building_data.egid:
                egid = building_data.egid

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Optionale Felder mit getattr absichern (nicht alle sind im ProjectCreate Model)
        client_name = getattr(data, 'client_name', None)
        client_contact = getattr(data, 'client_contact', None)
        deadline = getattr(data, 'deadline', None)
        description = getattr(data, 'description', None)  # Nicht im Model, aber in DB

        # FIX 10.01.2026 21:30 - Multi-Building Support: buildings als JSON speichern
        buildings_json = None
        if hasattr(data, 'buildings') and data.buildings:
            buildings_list = [b.model_dump() if hasattr(b, 'model_dump') else b for b in data.buildings]
            buildings_json = json.dumps(buildings_list)
            # Falls kein egid gesetzt, erstes Building nehmen
            if not egid and len(data.buildings) > 0:
                first_building = data.buildings[0]
                egid = first_building.egid if hasattr(first_building, 'egid') else first_building.get('egid')

        cursor.execute('''
            INSERT INTO projects (id, name, address, status, egid, client_name,
                                  client_contact, deadline, description, building_data, buildings, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id,
            data.name,
            data.address,
            ProjectStatus.DRAFT.value,
            egid,
            client_name,
            client_contact,
            deadline,
            description,
            building_data_json,
            buildings_json,
            now, now
        ))

        conn.commit()
        conn.close()

        # NEU 16.01.2026: GeruestbauData automatisch speichern (inkl. 3D-Layer)
        # Das macht das Projekt-Öffnen schneller (Fast Path in get_project_with_data)
        if egid and data.address:
            try:
                await self.save_geruestbaudata_to_project(project_id, egid, data.address)
                logger.info(f"[PROJECT] GeruestbauData automatisch gespeichert für {project_id}")
            except Exception as e:
                # Fehler beim Speichern ist nicht kritisch - Fallback auf Legacy-Pfad
                logger.warning(f"[PROJECT] GeruestbauData konnte nicht gespeichert werden: {e}")

        return await self.get_project(project_id)

    async def get_project(self, project_id: str) -> Optional[Project]:
        """Projekt abrufen."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_project(row)

    async def save_geruestbaudata_to_project(
        self,
        project_id: str,
        egid: str,
        address: str,
        additional_egids: list[str] = None
    ) -> bool:
        """
        NEU 16.01.2026: Speichert GeruestbauData in buildings_data mit EGID als Key.

        Single-Building: {"egid": GeruestbauData}
        Multi-Building: {"egid1": GeruestbauData, "egid2": GeruestbauData, ...}

        Diese Methode wird beim Projekt-Erstellen aufgerufen und speichert:
        - Gebäude-Grunddaten (EGID, Polygon, Koordinaten)
        - Höhendaten (Trauf-, First-, Gebäudehöhe) - ALTLAST: sollte aus walls berechnet werden!
        - 3D-Layer (building_walls, building_roofs)
        - Terrain-Daten (Geländehöhe, Hanglage)
        - Zonen (bei komplexen Gebäuden)

        Args:
            project_id: Projekt-ID
            egid: EGID des ersten Gebäudes (alle Gebäude gleichwertig)
            address: Adresse für SmartBuildingService
            additional_egids: Weitere EGIDs für Multi-Building Projekte

        Returns:
            True wenn erfolgreich gespeichert
        """
        try:
            # 1. Bundle vom SmartBuildingService laden
            smart_service = get_smart_building_service()
            bundle = await smart_service.collect_all_data(
                address=address,
                force_refresh=False,
                include_research=True,
                include_zones_analysis=True,
                include_terrain=True
            )

            if not bundle or not bundle.egid:
                logger.warning(f"[PROJECT] Kein Bundle für {address}")
                return False

            # 2. Building Walls und Roofs aus DB laden
            building_walls = []
            building_roofs = []

            try:
                from app.services.layer_fetcher import get_layer_fetcher_service
                layer_fetcher = get_layer_fetcher_service()

                # Walls laden
                walls_raw = layer_fetcher.get_walls_for_building(bundle.egid)
                for wall in walls_raw:
                    coords_3d = None
                    wkb = wall.get('geometry_wkb')
                    if wkb:
                        try:
                            from shapely import wkb as shapely_wkb
                            geom = shapely_wkb.loads(wkb)
                            # FIX 16.01.2026: Nur exterior rings, keine Ring-Verschachtelung
                            # Frontend erwartet: [polygon][point] = [E, N, Z]
                            if hasattr(geom, 'geoms'):  # MultiPolygon
                                coords_3d = [
                                    list(g.exterior.coords)
                                    for g in geom.geoms
                                ]
                            elif hasattr(geom, 'exterior'):  # Polygon
                                coords_3d = [list(geom.exterior.coords)]
                            elif hasattr(geom, 'coords'):  # LineString
                                coords_3d = [list(geom.coords)]
                        except Exception:
                            pass

                    building_walls.append({
                        "gebaeudeeinheit": wall.get('gebaeudeeinheit', ''),
                        "egid": wall.get('egid'),
                        "z_min": wall.get('z_min'),
                        "z_max": wall.get('z_max'),
                        "geometry_type": wall.get('geometry_type'),
                        "coords_3d": coords_3d,
                    })

                # Roofs laden
                roofs_raw = layer_fetcher.get_roofs_for_building(bundle.egid)
                for roof in roofs_raw:
                    coords_3d = None
                    wkb = roof.get('geometry_wkb')
                    if wkb:
                        try:
                            from shapely import wkb as shapely_wkb
                            geom = shapely_wkb.loads(wkb)
                            # FIX 16.01.2026: Nur exterior rings, keine Ring-Verschachtelung
                            # Frontend erwartet: [polygon][point] = [E, N, Z]
                            if hasattr(geom, 'geoms'):  # MultiPolygon
                                coords_3d = [
                                    list(g.exterior.coords)
                                    for g in geom.geoms
                                ]
                            elif hasattr(geom, 'exterior'):  # Polygon
                                coords_3d = [list(geom.exterior.coords)]
                            elif hasattr(geom, 'coords'):  # LineString
                                coords_3d = [list(geom.coords)]
                        except Exception:
                            pass

                    building_roofs.append({
                        "gebaeudeeinheit": roof.get('gebaeudeeinheit', ''),
                        "egid": roof.get('egid'),
                        "dach_min": roof.get('dach_min'),
                        "dach_max": roof.get('dach_max'),
                        "roof_form": roof.get('roof_form'),
                        "roof_angle_deg": roof.get('roof_angle_deg'),
                        "roof_orientation": roof.get('roof_orientation'),
                        "geometry_type": roof.get('geometry_type'),
                        "coords_3d": coords_3d,
                    })

                logger.info(f"[PROJECT] 3D-Layer geladen: {len(building_walls)} walls, {len(building_roofs)} roofs")
            except Exception as e:
                logger.warning(f"[PROJECT] 3D-Layer konnten nicht geladen werden: {e}")

            # 3. GeruestbauData Struktur erstellen
            geruestbaudata = self._build_geruestbaudata(
                bundle, address, building_walls, building_roofs
            )

            # 4. buildings_data Record aufbauen (EGID als Key)
            buildings_data = {bundle.egid: geruestbaudata}

            # 5. Multi-Building: Weitere EGIDs laden
            if additional_egids:
                for add_egid in additional_egids:
                    if add_egid == egid:
                        continue  # Diese EGID bereits geladen
                    try:
                        add_data = await self._load_geruestbaudata_for_egid(add_egid)
                        if add_data:
                            buildings_data[add_egid] = add_data
                            logger.info(f"[PROJECT] Multi-Building: Daten für EGID {add_egid} geladen")
                    except Exception as e:
                        logger.warning(f"[PROJECT] Multi-Building: Fehler bei EGID {add_egid}: {e}")

            # 6. In Projekt speichern (buildings_data statt geruestbaudata)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE projects SET buildings_data = ?, updated_at = ? WHERE id = ?
            ''', (
                json.dumps(buildings_data),
                datetime.utcnow().isoformat(),
                project_id
            ))
            conn.commit()
            conn.close()

            egid_count = len(buildings_data)
            logger.info(f"[PROJECT] buildings_data für {project_id} gespeichert ({egid_count} Gebäude)")
            return True

        except Exception as e:
            logger.error(f"[PROJECT] Fehler beim Speichern von GeruestbauData: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _build_geruestbaudata(self, bundle, address: str, building_walls: list, building_roofs: list) -> dict:
        """Baut GeruestbauData-Struktur aus Bundle und 3D-Layern."""
        return {
            "building": {
                "egid": bundle.egid,
                "address": bundle.address_matched or address,
                "polygon": bundle.polygon,
                "polygon_simplified": None,  # Wird on-demand berechnet
                "center_e": bundle.lv95_e,
                "center_n": bundle.lv95_n,
                "perimeter_m": bundle.perimeter_m or 0,
                "area_m2": bundle.footprint_area_m2 or 0,
            },
            "heights": {
                # ALTLAST: Diese Werte sollten aus walls berechnet werden!
                # Siehe STREAMING_ARCHITECTURE.md L.11
                "traufhoehe_m": bundle.traufhoehe_m or 0,
                "firsthoehe_m": bundle.firsthoehe_m or 0,
                "gebaeudehoehe_m": bundle.gebaeudehoehe_m or 0,
                "terrain_height_m": bundle.terrain.reference_height_m if bundle.terrain else 0,
                "source": "swissBUILDINGS3D",
            },
            "walls": building_walls,
            "roofs": building_roofs,
            "terrain": {
                "height_m": bundle.terrain.reference_height_m if bundle.terrain else 0,
                "min_m": bundle.terrain.min_height_m if bundle.terrain else 0,
                "max_m": bundle.terrain.max_height_m if bundle.terrain else 0,
                "slope_m": bundle.terrain.slope_m if bundle.terrain else 0,
                "slope_class": bundle.terrain.slope_class if bundle.terrain else "eben",
                "requires_level_compensation": (bundle.terrain.slope_m or 0) > 0.5 if bundle.terrain else False,
            } if bundle.terrain else {
                "height_m": 0,
                "min_m": 0,
                "max_m": 0,
                "slope_m": 0,
                "slope_class": "eben",
                "requires_level_compensation": False,
            },
            "zones": [
                {
                    "id": z.id,
                    "name": z.name,
                    "zone_type": z.zone_type,
                    "position": getattr(z, 'position', None),
                    "traufhoehe_m": z.traufhoehe_m,
                    "firsthoehe_m": z.firsthoehe_m,
                    "gebaeudehoehe_m": getattr(z, 'gebaeudehoehe_m', None),
                    "beruesten": z.beruesten,
                    "sonderkonstruktion": z.sonderkonstruktion,
                    "confidence": z.confidence,
                }
                for z in bundle.zones
            ] if bundle.zones else [],
            "astra": None,  # ASTRA-Daten noch nicht implementiert
            "fetched_at": datetime.utcnow().isoformat(),
            "data_quality": "complete" if building_walls else "partial",
            "missing_data": [] if building_walls else ["building_walls", "building_roofs"],
        }

    async def _load_geruestbaudata_for_egid(self, egid: str) -> Optional[dict]:
        """Lädt GeruestbauData für eine einzelne EGID (für Multi-Building)."""
        try:
            # Versuche Adresse für EGID zu finden
            from ..building_3d_service import get_building_3d_service
            building_3d = get_building_3d_service()
            building = building_3d.get_by_egid(egid)

            if not building:
                logger.warning(f"[PROJECT] Kein Gebäude für EGID {egid} in building_3d.db")
                return None

            # Adresse aus Koordinaten ermitteln oder Fallback
            address = f"EGID {egid}"  # Fallback

            # SmartBuildingService für vollständige Daten
            smart_service = get_smart_building_service()
            bundle = await smart_service.collect_all_data(
                address=address,
                egid_override=egid,
                force_refresh=False,
                include_research=False,  # Schneller für Multi-Building
                include_zones_analysis=False,
                include_terrain=True
            )

            if not bundle:
                return None

            # 3D-Layer laden
            building_walls = []
            building_roofs = []
            try:
                from app.services.layer_fetcher import get_layer_fetcher_service
                layer_fetcher = get_layer_fetcher_service()
                walls_raw = layer_fetcher.get_walls_for_building(egid)
                roofs_raw = layer_fetcher.get_roofs_for_building(egid)

                # Walls verarbeiten
                for wall in walls_raw:
                    building_walls.append({
                        "gebaeudeeinheit": wall.get('gebaeudeeinheit', ''),
                        "egid": wall.get('egid'),
                        "z_min": wall.get('z_min'),
                        "z_max": wall.get('z_max'),
                        "geometry_type": wall.get('geometry_type'),
                        "coords_3d": None,  # Vereinfacht für Multi-Building
                    })

                # Roofs verarbeiten
                for roof in roofs_raw:
                    building_roofs.append({
                        "gebaeudeeinheit": roof.get('gebaeudeeinheit', ''),
                        "egid": roof.get('egid'),
                        "dach_min": roof.get('dach_min'),
                        "dach_max": roof.get('dach_max'),
                        "roof_form": roof.get('roof_form'),
                        "roof_angle_deg": roof.get('roof_angle_deg'),
                        "roof_orientation": roof.get('roof_orientation'),
                        "geometry_type": roof.get('geometry_type'),
                        "coords_3d": None,  # Vereinfacht für Multi-Building
                    })
            except Exception as e:
                logger.warning(f"[PROJECT] 3D-Layer für EGID {egid}: {e}")

            return self._build_geruestbaudata(bundle, address, building_walls, building_roofs)

        except Exception as e:
            logger.error(f"[PROJECT] Fehler beim Laden für EGID {egid}: {e}")
            return None

    async def get_project_with_data(self, project_id: str) -> Optional[ProjectWithGeruestbaudata]:
        """
        Projekt mit buildings_data abrufen.

        NEU 16.01.2026: buildings_data als Record<EGID, GeruestbauData>.
        Unterstützt Single- und Multi-Building Projekte.
        """
        project = await self.get_project(project_id)
        if not project:
            return None

        buildings_data = None
        geruestbaudata = None  # Legacy Fallback

        # buildings_data aus Projekt laden (NEU)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT buildings_data, geruestbaudata FROM projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            # Neues Format: buildings_data (Record mit EGID als Key)
            if row['buildings_data']:
                try:
                    buildings_data = json.loads(row['buildings_data'])
                    egid_count = len(buildings_data)
                    logger.info(f"[PROJECT] buildings_data geladen für {project_id} ({egid_count} Gebäude)")
                except json.JSONDecodeError:
                    logger.warning(f"[PROJECT] buildings_data JSON ungültig für {project_id}")

            # Legacy Fallback: geruestbaudata (Single-Building)
            if not buildings_data and row['geruestbaudata']:
                try:
                    geruestbaudata = json.loads(row['geruestbaudata'])
                    # Migration: Legacy zu buildings_data konvertieren
                    if geruestbaudata and geruestbaudata.get('building', {}).get('egid'):
                        egid = geruestbaudata['building']['egid']
                        buildings_data = {egid: geruestbaudata}
                        logger.info(f"[PROJECT] Legacy geruestbaudata zu buildings_data migriert für {project_id}")
                except json.JSONDecodeError:
                    logger.warning(f"[PROJECT] geruestbaudata JSON ungültig für {project_id}")

        return ProjectWithGeruestbaudata(
            **project.model_dump(),
            buildings_data=buildings_data,
            geruestbaudata=geruestbaudata  # Legacy für Rückwärtskompatibilität
        )

    async def list_projects(self, status: ProjectStatus = None) -> List[Project]:
        """Alle Projekte auflisten."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if status:
            cursor.execute('SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC',
                          (status.value,))
        else:
            cursor.execute('SELECT * FROM projects ORDER BY updated_at DESC')

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_project(row) for row in rows]

    async def update_project(self, project_id: str, update: ProjectUpdate) -> Optional[Project]:
        """Projekt aktualisieren."""
        project = await self.get_project(project_id)
        if not project:
            return None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        updates = []
        values = []

        if update.name is not None:
            updates.append("name = ?")
            values.append(update.name)
        if update.status is not None:
            updates.append("status = ?")
            values.append(update.status.value)
        if update.client_name is not None:
            updates.append("client_name = ?")
            values.append(update.client_name)
        if update.client_contact is not None:
            updates.append("client_contact = ?")
            values.append(update.client_contact)
        if update.description is not None:
            updates.append("description = ?")
            values.append(update.description)

        if updates:
            updates.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            values.append(project_id)

            cursor.execute(
                f"UPDATE projects SET {', '.join(updates)} WHERE id = ?",
                values
            )
            conn.commit()

        conn.close()
        return await self.get_project(project_id)

    async def delete_project(self, project_id: str) -> bool:
        """Projekt löschen."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('DELETE FROM photos WHERE project_id = ?', (project_id,))
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    async def upload_photo(self, project_id: str, file) -> dict:
        """Foto hochladen (Placeholder)."""
        # TODO: Implement file storage (S3/MinIO)
        photo_id = str(uuid.uuid4())
        return {
            "photo_id": photo_id,
            "project_id": project_id,
            "status": "uploaded",
            "message": "Foto-Upload noch nicht implementiert"
        }

    async def analyze_photo(self, project_id: str, photo_id: str) -> Optional[PhotoAnalysis]:
        """Foto analysieren (Placeholder)."""
        # TODO: Implement Claude Vision analysis
        return PhotoAnalysis(
            photo_id=photo_id,
            direction="N",
            confidence=0.0,
            detected_elements=[],
            visible_zones=[],
            estimated_area_m2=None
        )

    async def get_scaffold_config(self, project_id: str) -> Optional[ScaffoldConfig]:
        """Gerüst-Konfiguration abrufen."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT scaffold_config FROM projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        conn.close()

        if not row or not row['scaffold_config']:
            return None

        config_data = json.loads(row['scaffold_config'])
        return ScaffoldConfig(**config_data)

    async def update_scaffold_config(self, project_id: str, config: ScaffoldConfig) -> ScaffoldConfig:
        """Gerüst-Konfiguration speichern."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE projects SET scaffold_config = ?, updated_at = ? WHERE id = ?
        ''', (
            config.model_dump_json(),
            datetime.utcnow().isoformat(),
            project_id
        ))

        conn.commit()
        conn.close()
        return config

    async def export_project(self, project_id: str, format: str) -> dict:
        """Projekt exportieren (Placeholder)."""
        # TODO: Implement PDF/XLSX/IFC/DXF export
        return {
            "project_id": project_id,
            "format": format,
            "status": "pending",
            "message": f"{format.upper()}-Export noch nicht implementiert"
        }

    def _row_to_project(self, row) -> Project:
        """SQLite Row zu Project Model konvertieren.

        HINWEIS: building_data wird nicht mehr im Project gespeichert.
        Enrichment-Daten (Terrain, Hanglage) sind in building_contexts.db → building_environment.
        """
        # FIX 10.01.2026 21:35 - Multi-Building Support: buildings aus JSON parsen
        buildings = []
        buildings_json = row['buildings'] if 'buildings' in row.keys() else None
        if buildings_json:
            try:
                from ...models.geruestbau import BuildingEntry
                buildings_list = json.loads(buildings_json)
                buildings = [BuildingEntry(**b) for b in buildings_list]
            except (json.JSONDecodeError, TypeError, Exception) as e:
                print(f"[Gerüstbau] Fehler beim Parsen von buildings: {e}")

        return Project(
            id=row['id'],
            name=row['name'],
            address=row['address'],
            status=ProjectStatus(row['status']),
            egid=row['egid'],
            buildings=buildings,
            client_name=row['client_name'],
            client_contact=row['client_contact'],
            deadline=datetime.fromisoformat(row['deadline']) if row['deadline'] else None,
            description=row['description'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )
