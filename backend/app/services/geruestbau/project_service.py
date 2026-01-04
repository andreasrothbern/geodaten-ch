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
from ..geodata_service import get_geodata_service, BuildingGeodata


class ProjectService:
    """Service für Gerüstbau-Projekt-Verwaltung."""

    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent / "data" / "geruestbau.db"
        self.swisstopo = SwisstopoService()
        self.geodata_service = get_geodata_service()
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

        cursor.execute('''
            INSERT INTO projects (id, name, address, status, egid, client_name,
                                  client_contact, deadline, description, building_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    async def get_project_with_geodata(self, project_id: str) -> Optional[ProjectWithGeodata]:
        """Projekt mit Geodaten aus Cache abrufen."""
        project = await self.get_project(project_id)
        if not project:
            return None

        geodata = None
        if project.egid:
            cached = self.geodata_service.get_by_egid(project.egid)
            if cached:
                geodata = cached.to_dict()

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
        """Projekt mit Geodaten anreichern via SmartBuildingService.

        Nutzt den zentralen SmartBuildingService (10-Schritte Pipeline) statt
        manueller API-Aufrufe. Das stellt sicher, dass alle Daten konsistent
        gesammelt und gecacht werden.
        """
        project = await self.get_project(project_id)
        if not project:
            return None

        building_data = {}
        egid = None

        try:
            # SmartBuildingService für konsistente Datensammlung nutzen
            from app.services.smart_building import get_smart_building_service

            smart_service = get_smart_building_service()
            bundle = await smart_service.collect_all_data(
                address=project.address,
                force_refresh=False,  # Cache nutzen wenn vorhanden
                include_research=False,  # Keine Claude-Recherche für Enrichment
                include_zones_analysis=False,
                include_terrain=True,
            )

            if bundle:
                egid = bundle.egid

                # Geodaten strukturieren
                building_data["geocode"] = {
                    "coordinates": {
                        "e": bundle.lv95_e,
                        "n": bundle.lv95_n,
                    },
                }

                if bundle.gwr_floors or bundle.gwr_category:
                    building_data["gwr"] = {
                        "egid": egid,
                        "address": bundle.address_matched or project.address,
                        "floors": bundle.gwr_floors,
                        "category": bundle.gwr_category,
                    }

                if bundle.polygon:
                    building_data["polygon"] = bundle.polygon

                building_data["heights"] = {
                    "traufhoehe_m": bundle.traufhoehe_m,
                    "firsthoehe_m": bundle.firsthoehe_m,
                    "gebaeudehoehe_m": bundle.gebaeudehoehe_m,
                    "source": bundle.height_source or "swissBUILDINGS3D",
                }

                building_data["geometry"] = {
                    "perimeter_m": bundle.perimeter_m,
                    "area_m2": bundle.footprint_area_m2,
                    "sides_count": len(bundle.sides) if bundle.sides else 0,
                }

                # Geodaten im zentralen Cache speichern (für getProject)
                if egid and bundle.lv95_e and bundle.lv95_n:
                    geodata = BuildingGeodata(
                        egid=str(egid),
                        address=bundle.address_matched or project.address,
                        polygon=bundle.polygon,
                        traufhoehe_m=bundle.traufhoehe_m,
                        firsthoehe_m=bundle.firsthoehe_m,
                        gebaeudehoehe_m=bundle.gebaeudehoehe_m,
                        area_m2=bundle.footprint_area_m2,
                        perimeter_m=bundle.perimeter_m,
                        center_e=bundle.lv95_e,
                        center_n=bundle.lv95_n,
                        coord_e=bundle.lv95_e,
                        coord_n=bundle.lv95_n,
                    )
                    self.geodata_service.save(geodata)
                    print(f"[Gerüstbau] Geodaten für EGID {egid} im Cache gespeichert")

        except Exception as e:
            print(f"[Gerüstbau] Fehler bei Geodaten-Anreicherung: {e}")
            import traceback
            traceback.print_exc()

        building_data["enriched_at"] = datetime.utcnow().isoformat()

        # Projekt aktualisieren
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE projects
            SET egid = ?, building_data = ?, status = ?, updated_at = ?
            WHERE id = ?
        ''', (
            egid,
            json.dumps(building_data),
            ProjectStatus.ENRICHED.value,
            datetime.utcnow().isoformat(),
            project_id
        ))
        conn.commit()
        conn.close()

        # Mit Geodaten zurückgeben (für sofortige Nutzung im Frontend)
        return await self.get_project_with_geodata(project_id)

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
        """SQLite Row zu Project Model konvertieren."""
        return Project(
            id=row['id'],
            name=row['name'],
            address=row['address'],
            status=ProjectStatus(row['status']),
            egid=row['egid'],
            client_name=row['client_name'],
            client_contact=row['client_contact'],
            deadline=datetime.fromisoformat(row['deadline']) if row['deadline'] else None,
            description=row['description'],
            building_data=json.loads(row['building_data']) if row['building_data'] else None,
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )
