#!/usr/bin/env python3
"""Update project_service.py for multi-building support."""

from pathlib import Path

service_path = Path(__file__).parent.parent / "app" / "services" / "geruestbau" / "project_service.py"

content = service_path.read_text(encoding="utf-8")

# 1. Add BuildingEntry to imports
old_import = """from ...models.geruestbau import (
    Project, ProjectCreate, ProjectUpdate, ProjectStatus, ProjectWithGeodata,
    PhotoAnalysis, ScaffoldConfig, ScaffoldZone
)"""

new_import = """from ...models.geruestbau import (
    Project, ProjectCreate, ProjectUpdate, ProjectStatus, ProjectWithGeodata,
    PhotoAnalysis, ScaffoldConfig, ScaffoldZone, BuildingEntry
)"""

if old_import in content:
    content = content.replace(old_import, new_import)
    print("[OK] BuildingEntry Import hinzugefuegt")
else:
    print("[SKIP] Import bereits vorhanden oder veraendert")

# 2. Update create_project to save buildings
old_create = """        cursor.execute('''
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
        ))"""

new_create = """        # Buildings als JSON serialisieren (Multi-Building Support)
        buildings_json = None
        if data.buildings:
            buildings_json = json.dumps([b.model_dump() for b in data.buildings])
            # Falls kein EGID gesetzt, nehme das erste Gebaeude
            if not egid and data.buildings:
                egid = data.buildings[0].egid

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
        ))"""

if old_create in content:
    content = content.replace(old_create, new_create)
    print("[OK] create_project fuer Multi-Building aktualisiert")
else:
    print("[SKIP] create_project Pattern nicht gefunden")

# 3. Update _row_to_project to load buildings
old_row_to_project = """    def _row_to_project(self, row) -> Project:
        \"\"\"SQLite Row zu Project Model konvertieren.\"\"\"
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
        )"""

new_row_to_project = """    def _row_to_project(self, row) -> Project:
        \"\"\"SQLite Row zu Project Model konvertieren.\"\"\"
        # Buildings aus JSON laden (Multi-Building Support)
        buildings = []
        buildings_col = row['buildings'] if 'buildings' in row.keys() else None
        if buildings_col:
            try:
                buildings_data = json.loads(buildings_col)
                buildings = [BuildingEntry(**b) for b in buildings_data]
            except (json.JSONDecodeError, TypeError):
                pass

        # ScaffoldConfig aus JSON laden
        config = None
        config_col = row['scaffold_config'] if 'scaffold_config' in row.keys() else None
        if config_col:
            try:
                config = ScaffoldConfig(**json.loads(config_col))
            except (json.JSONDecodeError, TypeError):
                pass

        return Project(
            id=row['id'],
            name=row['name'],
            address=row['address'],
            status=ProjectStatus(row['status']),
            egid=row['egid'],
            buildings=buildings,
            config=config,
            client_name=row['client_name'],
            client_contact=row['client_contact'],
            deadline=datetime.fromisoformat(row['deadline']) if row['deadline'] else None,
            description=row['description'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )"""

if old_row_to_project in content:
    content = content.replace(old_row_to_project, new_row_to_project)
    print("[OK] _row_to_project fuer Multi-Building aktualisiert")
else:
    print("[SKIP] _row_to_project Pattern nicht gefunden")

# Write the updated file
service_path.write_text(content, encoding="utf-8")
print("\n[DONE] project_service.py aktualisiert")
