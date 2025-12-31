"""Gerüstbau Project Service - Projekt-Verwaltung mit geodaten-ch Integration."""

import uuid
import sqlite3
import json
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from ...models.geruestbau import (
    Project, ProjectCreate, ProjectUpdate, ProjectStatus,
    PhotoAnalysis, ScaffoldConfig, ScaffoldZone
)
from ..swisstopo import SwisstopoService
from ..geodienste import GeodiensteService
from ..height_db import HeightDBService


class ProjectService:
    """Service für Gerüstbau-Projekt-Verwaltung."""

    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent / "data" / "geruestbau.db"
        self.swisstopo = SwisstopoService()
        self.geodienste = GeodiensteService()
        self.height_db = HeightDBService()
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

        conn.commit()
        conn.close()

    async def create_project(self, data: ProjectCreate) -> Project:
        """Neues Projekt erstellen."""
        project_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO projects (id, name, address, status, client_name,
                                  client_contact, deadline, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            project_id,
            data.name,
            data.address,
            ProjectStatus.DRAFT.value,
            data.client_name,
            data.client_contact,
            data.deadline.isoformat() if data.deadline else None,
            data.description,
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

    async def enrich_with_geodata(self, project_id: str) -> Optional[Project]:
        """Projekt mit Geodaten anreichern via geodaten-ch Services."""
        project = await self.get_project(project_id)
        if not project:
            return None

        building_data = {}

        try:
            # 1. Adresse geocodieren
            geocode_result = await self.swisstopo.geocode(project.address)
            if geocode_result:
                building_data["geocode"] = {
                    "coordinates": {
                        "e": geocode_result.coordinates_lv95[0] if geocode_result.coordinates_lv95 else None,
                        "n": geocode_result.coordinates_lv95[1] if geocode_result.coordinates_lv95 else None,
                    },
                    "lat": geocode_result.lat,
                    "lon": geocode_result.lon,
                }

                # 2. GWR-Daten abrufen
                egid = geocode_result.egid
                if egid:
                    gwr_data = await self.swisstopo.get_building_by_egid(egid)
                    if gwr_data:
                        building_data["gwr"] = {
                            "egid": egid,
                            "address": project.address,
                            "floors": gwr_data.get("gastw"),
                            "category": gwr_data.get("gkat"),
                            "year_built": gwr_data.get("gbauj"),
                        }

                # 3. Gebäudepolygon abrufen
                if geocode_result.coordinates_lv95:
                    polygon = await self.geodienste.get_building_polygon(
                        geocode_result.coordinates_lv95[0],
                        geocode_result.coordinates_lv95[1]
                    )
                    if polygon:
                        building_data["polygon"] = polygon

                # 4. Höhendaten abrufen
                if egid:
                    height_data = self.height_db.get_height_by_egid(int(egid))
                    if height_data:
                        building_data["heights"] = {
                            "traufhoehe_m": height_data.get("traufhoehe_m"),
                            "firsthoehe_m": height_data.get("firsthoehe_m"),
                            "gebaeudehoehe_m": height_data.get("gebaeudehoehe_m"),
                            "source": "swissBUILDINGS3D",
                        }

        except Exception as e:
            print(f"[Gerüstbau] Fehler bei Geodaten-Anreicherung: {e}")

        building_data["enriched_at"] = datetime.utcnow().isoformat()

        # Projekt aktualisieren
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE projects
            SET egid = ?, building_data = ?, status = ?, updated_at = ?
            WHERE id = ?
        ''', (
            building_data.get("gwr", {}).get("egid"),
            json.dumps(building_data),
            ProjectStatus.ENRICHED.value,
            datetime.utcnow().isoformat(),
            project_id
        ))
        conn.commit()
        conn.close()

        return await self.get_project(project_id)

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
