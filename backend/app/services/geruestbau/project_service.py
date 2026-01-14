"""Gerüstbau Project Service - Projekt-Verwaltung mit geodaten-ch Integration."""

import uuid
import sqlite3
import json
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from ...models.geruestbau import (
    Project, ProjectCreate, ProjectUpdate, ProjectStatus, ProjectWithGeodata,
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
            'building_data': 'TEXT',    # Geodaten-Anreicherung
            'scaffold_config': 'TEXT',  # Gerüst-Konfiguration
            'buildings': 'TEXT',        # Multi-Building Support (JSON array)
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

    def _get_bundle_from_smart_service(self, egid: str) -> Optional[dict]:
        """
        Lädt BuildingDataBundle über den SmartBuildingService.

        Der SmartBuildingService verwaltet den Cache (building_contexts.db).
        Diese Methode ist ein Wrapper für die Integration mit dem project_service.

        Args:
            egid: Eidgenössische Gebäudeidentifikation

        Returns:
            Dict mit Bundle-Daten oder None
        """
        try:
            smart_service = get_smart_building_service()
            bundle = smart_service.get_bundle_by_egid(egid)

            if bundle is None:
                return None

            # Bundle zu Dict konvertieren (für Kompatibilität)
            return {
                'egid': bundle.egid,
                'address_matched': bundle.address_matched,
                'polygon': bundle.polygon,
                'sides': bundle.sides,
                'traufhoehe_m': bundle.traufhoehe_m,
                'firsthoehe_m': bundle.firsthoehe_m,
                'gebaeudehoehe_m': bundle.gebaeudehoehe_m,
                'footprint_area_m2': bundle.footprint_area_m2,
                'perimeter_m': bundle.perimeter_m,
                'lv95_e': bundle.lv95_e,
                'lv95_n': bundle.lv95_n,
                'terrain': {
                    'reference_height_m': bundle.terrain.reference_height_m,
                    'slope_m': bundle.terrain.slope_m,
                    'slope_class': getattr(bundle.terrain, 'slope_class', None),
                    # NEU 14.01.2026 18:00 - Fassaden-Höhen aus Wall-Layer (T2-T4)
                    'facade_z_min': bundle.terrain.facade_z_min,
                    'facade_z_max': bundle.terrain.facade_z_max,
                    'facade_heights_source': bundle.terrain.facade_heights_source,
                } if bundle.terrain else None,
                'zones': [
                    {
                        'id': z.id,
                        'name': z.name,
                        'zone_type': z.zone_type,
                        'traufhoehe_m': z.traufhoehe_m,
                        'firsthoehe_m': z.firsthoehe_m,
                    }
                    for z in bundle.zones
                ] if bundle.zones else None,
                'roof_type': bundle.roof_type,
                'roof_angle_deg': bundle.roof_angle_deg,
                'roof_orientation': bundle.roof_orientation,
                'complexity': bundle.complexity,
                'building_type': bundle.building_type,
                # NEU 14.01.2026 18:05 - 3D-Layer Flag für BuildingDataCard
                'has_3d_layers': bundle.has_3d_layers,
            }
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Error loading bundle for EGID {egid}: {e}")
            return None

    async def get_project_with_data(self, project_id: str) -> Optional[ProjectWithGeodata]:
        """
        Projekt mit Geodaten aus smart_building_cache abrufen.

        Verwendet den zentralen smart_building_cache (building_contexts.db),
        der alle Gebäudedaten enthält (Polygon, Höhen, Terrain, Zonen, etc.).
        """
        project = await self.get_project(project_id)
        if not project:
            return None

        geodata = None
        if project.egid:
            bundle = self._get_bundle_from_smart_service(project.egid)
            if bundle:
                # Bundle zu Geodata-Format konvertieren (kompatibel mit Frontend)
                geodata = {
                    'egid': bundle.get('egid'),
                    'address': bundle.get('address_matched'),
                    'polygon': bundle.get('polygon'),
                    'traufhoehe_m': bundle.get('traufhoehe_m'),
                    'firsthoehe_m': bundle.get('firsthoehe_m'),
                    'gebaeudehoehe_m': bundle.get('gebaeudehoehe_m'),
                    'area_m2': bundle.get('footprint_area_m2'),
                    'perimeter_m': bundle.get('perimeter_m'),
                    'center_e': bundle.get('lv95_e'),
                    'center_n': bundle.get('lv95_n'),
                    'coord_e': bundle.get('lv95_e'),
                    'coord_n': bundle.get('lv95_n'),
                    # Zusätzliche Felder aus dem Bundle
                    'sides': bundle.get('sides'),
                    'terrain': bundle.get('terrain'),
                    'zones': bundle.get('zones'),
                    'roof_type': bundle.get('roof_type'),
                    'roof_angle_deg': bundle.get('roof_angle_deg'),
                    'roof_orientation': bundle.get('roof_orientation'),
                    'complexity': bundle.get('complexity'),
                    'building_type': bundle.get('building_type'),
                }
                # NEU 14.01.2026 18:00 - Fassaden-Höhen direkt ins geodata (für BuildingDataCard)
                terrain = bundle.get('terrain')
                if terrain:
                    geodata['facade_z_min'] = terrain.get('facade_z_min')
                    geodata['facade_z_max'] = terrain.get('facade_z_max')
                    geodata['facade_heights_source'] = terrain.get('facade_heights_source')
                    geodata['terrain_height_m'] = terrain.get('reference_height_m')
                    geodata['slope_m'] = terrain.get('slope_m')
                    geodata['slope_class'] = terrain.get('slope_class')
                # NEU 14.01.2026 18:05 - 3D-Layer Flag
                geodata['has_3d_layers'] = bundle.get('has_3d_layers', False)

        return ProjectWithGeodata(
            **project.model_dump(),
            geodata=geodata
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

    async def enrich_with_geodata(self, project_id: str) -> Optional[ProjectWithGeodata]:
        """Projekt mit ZUSÄTZLICHEN Daten anreichern.

        Enrichment-Daten werden in building_contexts.db → building_environment
        gespeichert (pro EGID, nicht pro Projekt).

        Enrichment holt:
        - Terrain (Geländehöhe am Referenzpunkt)
        - Hanglage (Steigung über Gebäude-Polygon)
        - Zukünftig: Foto-Analyse, Zonen

        NICHT im Enrichment (dynamisch abgerufen):
        - Nachbar-Gebäude (API mit variablem Radius)
        """
        project = await self.get_project(project_id)
        if not project:
            return None

        egid = project.egid
        polygon = None
        terrain_data = None

        try:
            # Koordinaten und Polygon aus Projekt-Buildings oder Geodata holen
            coord_e, coord_n = None, None

            if project.buildings and len(project.buildings) > 0:
                # Multi-Adresse: Koordinaten aus erstem Gebäude
                first_building = project.buildings[0]
                if first_building.get('coordinates'):
                    coord_e = first_building['coordinates'].get('lv95_e')
                    coord_n = first_building['coordinates'].get('lv95_n')
                if not egid:
                    egid = first_building.get('egid')
                # Polygon aus building
                if first_building.get('polygon'):
                    polygon = first_building['polygon']

            # Fallback: Geodata über SmartBuildingService laden
            if not coord_e or not coord_n:
                if egid:
                    bundle = self._get_bundle_from_smart_service(egid)
                    if bundle:
                        coord_e = bundle.get('lv95_e')
                        coord_n = bundle.get('lv95_n')
                        # Koordinaten normalisieren (LV95)
                        if coord_e and coord_e < 2000000:
                            coord_e += 2000000
                        if coord_n and coord_n < 1000000:
                            coord_n += 1000000
                        if bundle.get('polygon') and not polygon:
                            polygon = bundle.get('polygon')

            # ENRICHMENT: Terrain + Hanglage
            if coord_e and coord_n:
                from app.services.terrain import get_terrain_service

                terrain_service = get_terrain_service()
                terrain_height = await terrain_service.get_height(coord_e, coord_n)

                terrain_data = {
                    "height_m": terrain_height,
                    "coordinates": {"e": coord_e, "n": coord_n},
                    "enriched_at": datetime.utcnow().isoformat(),
                }

                # Hanglage berechnen wenn Polygon vorhanden
                if polygon and len(polygon) >= 3:
                    terrain_info = await terrain_service.get_terrain_info(
                        coord_e, coord_n, polygon
                    )
                    if terrain_info:
                        terrain_data["min_terrain_m"] = terrain_info.min_terrain_m
                        terrain_data["max_terrain_m"] = terrain_info.max_terrain_m
                        terrain_data["slope_m"] = terrain_info.terrain_slope_m

                        # Hanglage-Klassifikation
                        if terrain_info.terrain_slope_m:
                            slope = terrain_info.terrain_slope_m
                            if slope < 0.5:
                                terrain_data["slope_class"] = "eben"
                            elif slope < 1.5:
                                terrain_data["slope_class"] = "leicht"
                            elif slope < 3.0:
                                terrain_data["slope_class"] = "mittel"
                            else:
                                terrain_data["slope_class"] = "stark"

                print(f"[Gerüstbau] Terrain für EGID {egid}: {terrain_height}m ü.M., Hanglage: {terrain_data.get('slope_m', 0):.1f}m")

        except Exception as e:
            print(f"[Gerüstbau] Fehler bei Enrichment: {e}")
            import traceback
            traceback.print_exc()

        # Terrain in building_environment speichern (pro EGID, nicht pro Projekt)
        if terrain_data and egid:
            from app.services.intelligent_db import IntelligentDBService
            db_service = IntelligentDBService()
            db_service.set_building_environment(
                egid=egid,
                surrounding_buildings=[],  # Wird dynamisch abgerufen
                blocked_facades=[],
                terrain_data=terrain_data
            )

        # Projekt-Status aktualisieren (KEIN building_data mehr!)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE projects
            SET status = ?, updated_at = ?
            WHERE id = ?
        ''', (
            ProjectStatus.ENRICHED.value,
            datetime.utcnow().isoformat(),
            project_id
        ))
        conn.commit()
        conn.close()

        # Mit Geodaten zurückgeben
        return await self.get_project_with_data(project_id)

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
