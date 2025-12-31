# Gerüstbau-App Setup Guide

## Für Claude Code / IDE

Dieses Dokument beschreibt das Setup der neuen Gerüstbau-App als Mobile-First PWA im bestehenden geodaten-ch Repository.

---

## Branching-Strategie

**WICHTIG: Immer auf einem Feature-Branch arbeiten!**

```bash
# 1. Aktuellen main holen
git checkout main
git pull origin main

# 2. Feature-Branch erstellen
git checkout -b feature/geruestbau-app

# 3. Nach Änderungen committen
git add .
git commit -m "feat(geruestbau): [Beschreibung]"

# 4. Branch pushen
git push origin feature/geruestbau-app

# 5. Pull Request erstellen auf GitHub
# → CI/CD Pipeline läuft automatisch
# → Nach Review: Merge to main
```

### Commit-Konventionen

```
feat(geruestbau): Neue Funktion
fix(geruestbau): Bugfix
docs(geruestbau): Dokumentation
refactor(geruestbau): Code-Refactoring
test(geruestbau): Tests hinzugefügt
```

---

## Projektstruktur (Ziel)

```
geodaten-ch/
├── backend/                        # BESTEHEND - erweitern
│   ├── app/
│   │   ├── main.py                # Router hinzufügen
│   │   ├── models/
│   │   │   ├── building.py        # Bestehend
│   │   │   └── geruestbau.py      # NEU
│   │   ├── routers/               # NEU: Router-Struktur
│   │   │   ├── __init__.py
│   │   │   ├── geodata.py         # Bestehende Endpoints auslagern
│   │   │   └── geruestbau.py      # NEU
│   │   ├── services/
│   │   │   ├── swisstopo.py       # Bestehend
│   │   │   ├── geodienste.py      # Bestehend
│   │   │   └── geruestbau/        # NEU
│   │   │       ├── __init__.py
│   │   │       ├── project_service.py
│   │   │       ├── photo_analyzer.py
│   │   │       └── scaffold_calc.py
│   │   └── data/
│   │       └── geruestbau.db      # NEU: SQLite für Projekte
│   ├── tests/                     # NEU: Tests
│   │   └── test_geruestbau.py
│   └── requirements.txt           # Erweitern
│
├── frontend/                       # BESTEHEND - keine Änderungen
│   └── ...                        # Qualitätskontrolle-App
│
├── geruestbau-app/                 # NEU: Mobile-First PWA
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   └── Loading.tsx
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── BottomNav.tsx
│   │   │   │   └── PageContainer.tsx
│   │   │   ├── projects/
│   │   │   │   ├── ProjectList.tsx
│   │   │   │   ├── ProjectCard.tsx
│   │   │   │   └── ProjectForm.tsx
│   │   │   ├── geodata/
│   │   │   │   ├── AddressSearch.tsx
│   │   │   │   ├── BuildingInfo.tsx
│   │   │   │   └── MapPreview.tsx
│   │   │   ├── photos/
│   │   │   │   ├── PhotoCapture.tsx
│   │   │   │   ├── PhotoGallery.tsx
│   │   │   │   └── PhotoAnalysis.tsx
│   │   │   └── scaffold/
│   │   │       ├── ScaffoldEditor.tsx
│   │   │       ├── ZoneConfig.tsx
│   │   │       └── MaterialList.tsx
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   ├── ProjectsPage.tsx
│   │   │   ├── ProjectDetailPage.tsx
│   │   │   ├── NewProjectPage.tsx
│   │   │   ├── PhotosPage.tsx
│   │   │   └── ScaffoldPage.tsx
│   │   ├── hooks/
│   │   │   ├── useProjects.ts
│   │   │   ├── useGeodata.ts
│   │   │   ├── useCamera.ts
│   │   │   └── useOffline.ts
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   ├── geodata.ts
│   │   │   └── geruestbau.ts
│   │   ├── stores/
│   │   │   └── projectStore.ts
│   │   ├── types/
│   │   │   ├── index.ts
│   │   │   ├── project.ts
│   │   │   ├── building.ts
│   │   │   └── scaffold.ts
│   │   └── utils/
│   │       ├── formatting.ts
│   │       └── validation.ts
│   ├── public/
│   │   ├── manifest.json
│   │   ├── sw.js
│   │   ├── icons/
│   │   │   ├── icon-192.png
│   │   │   └── icon-512.png
│   │   └── favicon.svg
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── Dockerfile
│
├── docs/
│   ├── GERUESTBAU_APP_SETUP.md    # Diese Datei
│   └── GERUESTBAU_API.md          # API-Dokumentation
│
├── .github/
│   └── workflows/
│       └── ci.yml                 # CI/CD Pipeline
│
├── CLAUDE.md                       # Erweitern
└── README.md                       # Erweitern
```

---

## Phase 1: PWA Grundgerüst erstellen

### Schritt 1.1: Ordner und Basis-Setup

```bash
# Im Repository-Root
mkdir -p geruestbau-app/src/{components,pages,hooks,api,types,utils,stores}
mkdir -p geruestbau-app/src/components/{ui,layout,projects,geodata,photos,scaffold}
mkdir -p geruestbau-app/public/icons

cd geruestbau-app
```

### Schritt 1.2: package.json erstellen

```json
{
  "name": "geruestbau-app",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "zustand": "^4.4.7",
    "lucide-react": "^0.294.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.16",
    "eslint": "^8.55.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.5",
    "postcss": "^8.4.32",
    "tailwindcss": "^3.3.6",
    "typescript": "^5.3.2",
    "vite": "^5.0.8",
    "vite-plugin-pwa": "^0.17.4",
    "vitest": "^1.1.0"
  }
}
```

### Schritt 1.3: vite.config.ts

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'icons/*.png'],
      manifest: {
        name: 'Gerüstbau App',
        short_name: 'Gerüstbau',
        description: 'Mobile App für Gerüstbau-Projekterfassung',
        theme_color: '#dc2626',
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'portrait',
        start_url: '/',
        icons: [
          {
            src: 'icons/icon-192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'icons/icon-512.png',
            sizes: '512x512',
            type: 'image/png'
          }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/api\.geodaten-ch\.railway\.app\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 // 24 hours
              }
            }
          }
        ]
      }
    })
  ],
  server: {
    port: 3001,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

### Schritt 1.4: tailwind.config.js

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#fef2f2',
          100: '#fee2e2',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

### Schritt 1.5: index.html

```html
<!DOCTYPE html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <meta name="theme-color" content="#dc2626" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="default" />
    <link rel="apple-touch-icon" href="/icons/icon-192.png" />
    <title>Gerüstbau App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

### Schritt 1.6: TypeScript Configs

**tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

**tsconfig.node.json:**
```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

---

## Phase 2: Backend-Erweiterung

### Schritt 2.1: Neue Models (backend/app/models/geruestbau.py)

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ProjectStatus(str, Enum):
    DRAFT = "draft"
    CAPTURED = "captured"
    ENRICHED = "enriched"
    REVIEWED = "reviewed"
    PLANNED = "planned"
    QUOTED = "quoted"
    COMMISSIONED = "commissioned"

class ProjectCreate(BaseModel):
    name: str
    address: str
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    deadline: Optional[datetime] = None
    description: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[ProjectStatus] = None
    client_name: Optional[str] = None
    description: Optional[str] = None

class Project(BaseModel):
    id: str
    name: str
    address: str
    status: ProjectStatus
    egid: Optional[str] = None
    client_name: Optional[str] = None
    client_contact: Optional[str] = None
    deadline: Optional[datetime] = None
    description: Optional[str] = None
    building_data: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

class PhotoUpload(BaseModel):
    project_id: str
    direction: Optional[str] = None  # N, NO, O, SO, S, SW, W, NW

class PhotoAnalysis(BaseModel):
    photo_id: str
    direction: str
    confidence: float
    detected_elements: List[str]
    visible_zones: List[str]
    estimated_area_m2: Optional[float] = None

class ScaffoldZone(BaseModel):
    name: str
    zone_type: str  # turm, hauptgebaeude, anbau
    height_m: float
    width_m: float
    fields: int
    levels: int
    requires_special: bool = False

class ScaffoldConfig(BaseModel):
    project_id: str
    system: str = "Layher Blitz 70"
    bay_width: str = "W09"
    zones: List[ScaffoldZone]
    total_area_m2: float
    total_anchors: int
    access_points: int
```

### Schritt 2.2: Neuer Router (backend/app/routers/geruestbau.py)

```python
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
import uuid
from datetime import datetime

from ..models.geruestbau import (
    Project, ProjectCreate, ProjectUpdate, ProjectStatus,
    PhotoAnalysis, ScaffoldConfig
)
from ..services.geruestbau.project_service import ProjectService

router = APIRouter(prefix="/api/v1/geruestbau", tags=["Gerüstbau"])

project_service = ProjectService()

@router.get("/projects", response_model=List[Project])
async def list_projects(status: ProjectStatus = None):
    """Liste aller Projekte, optional gefiltert nach Status."""
    return await project_service.list_projects(status)

@router.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate):
    """Neues Projekt erstellen."""
    return await project_service.create_project(project)

@router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str):
    """Projekt-Details abrufen."""
    project = await project_service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project

@router.put("/projects/{project_id}", response_model=Project)
async def update_project(project_id: str, update: ProjectUpdate):
    """Projekt aktualisieren."""
    project = await project_service.update_project(project_id, update)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Projekt löschen."""
    success = await project_service.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return {"status": "deleted"}

@router.post("/projects/{project_id}/enrich")
async def enrich_project(project_id: str):
    """Projekt mit Geodaten anreichern (GWR, Höhen, Polygon)."""
    project = await project_service.enrich_with_geodata(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    return project

@router.post("/projects/{project_id}/photos")
async def upload_photo(project_id: str, file: UploadFile = File(...)):
    """Foto hochladen."""
    return await project_service.upload_photo(project_id, file)

@router.post("/projects/{project_id}/photos/{photo_id}/analyze")
async def analyze_photo(project_id: str, photo_id: str) -> PhotoAnalysis:
    """Foto mit Claude Vision analysieren (Blickrichtung erkennen)."""
    return await project_service.analyze_photo(project_id, photo_id)

@router.get("/projects/{project_id}/scaffold", response_model=ScaffoldConfig)
async def get_scaffold_config(project_id: str):
    """Aktuelle Gerüst-Konfiguration abrufen."""
    return await project_service.get_scaffold_config(project_id)

@router.put("/projects/{project_id}/scaffold", response_model=ScaffoldConfig)
async def update_scaffold_config(project_id: str, config: ScaffoldConfig):
    """Gerüst-Konfiguration aktualisieren."""
    return await project_service.update_scaffold_config(project_id, config)

@router.post("/projects/{project_id}/export")
async def export_project(project_id: str, format: str = "pdf"):
    """Projekt exportieren (pdf, ifc, dxf, xlsx)."""
    return await project_service.export_project(project_id, format)```

### Schritt 2.3: main.py erweitern

In `backend/app/main.py` den neuen Router einbinden:

```python
# Am Anfang der Datei hinzufügen:
from app.routers import geruestbau

# Nach den bestehenden Routen hinzufügen:
app.include_router(geruestbau.router)
```

### Schritt 2.4: Project Service (backend/app/services/geruestbau/project_service.py)

```python
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
    
    async def enrich_with_geodata(self, project_id: str) -> Optional[Project]:
        """Projekt mit Geodaten anreichern."""
        project = await self.get_project(project_id)
        if not project:
            return None
        
        # 1. Adresse geocodieren
        geocode_result = await self.swisstopo.geocode(project.address)
        if not geocode_result:
            return project
        
        # 2. GWR-Daten abrufen
        egid = geocode_result.get('egid')
        gwr_data = None
        if egid:
            gwr_data = await self.swisstopo.get_building_by_egid(egid)
        
        # 3. Gebäudepolygon abrufen
        polygon = None
        if geocode_result.get('coordinates'):
            polygon = await self.geodienste.get_building_polygon(
                geocode_result['coordinates']['e'],
                geocode_result['coordinates']['n']
            )
        
        # 4. Höhendaten abrufen
        height_data = None
        if egid:
            height_data = await self.height_db.get_height_by_egid(egid)
        
        # 5. Daten zusammenführen
        building_data = {
            "geocode": geocode_result,
            "gwr": gwr_data,
            "polygon": polygon,
            "heights": height_data,
            "enriched_at": datetime.utcnow().isoformat()
        }
        
        # 6. Projekt aktualisieren
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
        
        return await self.get_project(project_id)
    
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
```

---

## Phase 3: Frontend-Komponenten

### Schritt 3.1: Main Entry Point (src/main.tsx)

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
```

### Schritt 3.2: App.tsx mit Routing

```tsx
import { Routes, Route } from 'react-router-dom'
import { BottomNav } from './components/layout/BottomNav'
import { Header } from './components/layout/Header'
import HomePage from './pages/HomePage'
import ProjectsPage from './pages/ProjectsPage'
import NewProjectPage from './pages/NewProjectPage'
import ProjectDetailPage from './pages/ProjectDetailPage'

function App() {
  return (
    <div className="min-h-screen bg-gray-50 pb-16">
      <Header />
      <main className="container mx-auto px-4 py-4 max-w-lg">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/new" element={<NewProjectPage />} />
          <Route path="/projects/:id" element={<ProjectDetailPage />} />
          <Route path="/projects/:id/photos" element={<div>Fotos</div>} />
          <Route path="/projects/:id/scaffold" element={<div>Gerüst</div>} />
        </Routes>
      </main>
      <BottomNav />
    </div>
  )
}

export default App
```

### Schritt 3.3: index.css (Tailwind)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    -webkit-tap-highlight-color: transparent;
  }
  
  body {
    @apply antialiased text-gray-900;
  }
}

@layer components {
  .btn-primary {
    @apply bg-primary-600 text-white px-4 py-3 rounded-lg font-medium 
           active:bg-primary-700 transition-colors w-full;
  }
  
  .btn-secondary {
    @apply bg-gray-200 text-gray-800 px-4 py-3 rounded-lg font-medium 
           active:bg-gray-300 transition-colors;
  }
  
  .input-field {
    @apply w-full px-4 py-3 border border-gray-300 rounded-lg 
           focus:ring-2 focus:ring-primary-500 focus:border-transparent
           outline-none transition-all;
  }
  
  .card {
    @apply bg-white rounded-xl shadow-sm border border-gray-100 p-4;
  }
}
```

### Schritt 3.4: Layout-Komponenten

**src/components/layout/Header.tsx:**
```tsx
import { useLocation } from 'react-router-dom'

const titles: Record<string, string> = {
  '/': 'Gerüstbau',
  '/projects': 'Projekte',
  '/projects/new': 'Neues Projekt',
}

export function Header() {
  const location = useLocation()
  const title = titles[location.pathname] || 'Gerüstbau'
  
  return (
    <header className="bg-primary-600 text-white px-4 py-4 sticky top-0 z-50">
      <h1 className="text-xl font-semibold text-center">{title}</h1>
    </header>
  )
}
```

**src/components/layout/BottomNav.tsx:**
```tsx
import { NavLink } from 'react-router-dom'
import { Home, FolderOpen, PlusCircle, Settings } from 'lucide-react'

export function BottomNav() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex flex-col items-center py-2 px-4 ${
      isActive ? 'text-primary-600' : 'text-gray-500'
    }`
  
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
      <div className="flex justify-around max-w-lg mx-auto">
        <NavLink to="/" className={linkClass}>
          <Home size={24} />
          <span className="text-xs mt-1">Home</span>
        </NavLink>
        <NavLink to="/projects" className={linkClass}>
          <FolderOpen size={24} />
          <span className="text-xs mt-1">Projekte</span>
        </NavLink>
        <NavLink to="/projects/new" className={linkClass}>
          <PlusCircle size={24} />
          <span className="text-xs mt-1">Neu</span>
        </NavLink>
        <NavLink to="/settings" className={linkClass}>
          <Settings size={24} />
          <span className="text-xs mt-1">Einstellungen</span>
        </NavLink>
      </div>
    </nav>
  )
}
```

### Schritt 3.5: API Client (src/api/client.ts)

```typescript
const API_BASE = import.meta.env.VITE_API_URL || ''

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`)
  }
  
  return response.json()
}

export const api = {
  get: <T>(endpoint: string) => request<T>(endpoint),
  
  post: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  put: <T>(endpoint: string, data: unknown) =>
    request<T>(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  delete: <T>(endpoint: string) =>
    request<T>(endpoint, { method: 'DELETE' }),
}
```

### Schritt 3.6: Gerüstbau API (src/api/geruestbau.ts)

```typescript
import { api } from './client'
import type { Project, ProjectCreate } from '../types/project'

export const geruestbauApi = {
  // Projekte
  listProjects: () => 
    api.get<Project[]>('/api/v1/geruestbau/projects'),
  
  getProject: (id: string) => 
    api.get<Project>(`/api/v1/geruestbau/projects/${id}`),
  
  createProject: (data: ProjectCreate) => 
    api.post<Project>('/api/v1/geruestbau/projects', data),
  
  updateProject: (id: string, data: Partial<Project>) => 
    api.put<Project>(`/api/v1/geruestbau/projects/${id}`, data),
  
  deleteProject: (id: string) => 
    api.delete(`/api/v1/geruestbau/projects/${id}`),
  
  // Geodaten
  enrichProject: (id: string) => 
    api.post<Project>(`/api/v1/geruestbau/projects/${id}/enrich`, {}),
  
  // Fotos
  uploadPhoto: async (projectId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch(
      `/api/v1/geruestbau/projects/${projectId}/photos`,
      { method: 'POST', body: formData }
    )
    return response.json()
  },
  
  analyzePhoto: (projectId: string, photoId: string) =>
    api.post(`/api/v1/geruestbau/projects/${projectId}/photos/${photoId}/analyze`, {}),
}
```

### Schritt 3.7: Types (src/types/project.ts)

```typescript
export type ProjectStatus = 
  | 'draft' 
  | 'captured' 
  | 'enriched' 
  | 'reviewed' 
  | 'planned' 
  | 'quoted' 
  | 'commissioned'

export interface Project {
  id: string
  name: string
  address: string
  status: ProjectStatus
  egid?: string
  client_name?: string
  client_contact?: string
  deadline?: string
  description?: string
  building_data?: BuildingData
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  address: string
  client_name?: string
  client_contact?: string
  deadline?: string
  description?: string
}

export interface BuildingData {
  geocode?: {
    coordinates: { e: number; n: number }
    lat: number
    lon: number
  }
  gwr?: {
    egid: string
    address: string
    floors: number
    category: string
    year_built?: number
  }
  polygon?: {
    type: string
    coordinates: number[][][]
  }
  heights?: {
    traufhoehe_m?: number
    firsthoehe_m?: number
    gebaeudehoehe_m?: number
    source: string
  }
}
```

### Schritt 3.8: Pages

**src/pages/HomePage.tsx:**
```tsx
import { Link } from 'react-router-dom'
import { FolderPlus, List, BarChart3 } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div className="text-center py-8">
        <div className="w-20 h-20 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <span className="text-4xl">🏗️</span>
        </div>
        <h2 className="text-2xl font-bold text-gray-900">Gerüstbau App</h2>
        <p className="text-gray-500 mt-2">Projekterfassung und Kalkulation</p>
      </div>
      
      <div className="grid gap-4">
        <Link to="/projects/new" className="card flex items-center gap-4">
          <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
            <FolderPlus className="text-primary-600" size={24} />
          </div>
          <div>
            <h3 className="font-semibold">Neues Projekt</h3>
            <p className="text-sm text-gray-500">Ausschreibung erfassen</p>
          </div>
        </Link>
        
        <Link to="/projects" className="card flex items-center gap-4">
          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
            <List className="text-blue-600" size={24} />
          </div>
          <div>
            <h3 className="font-semibold">Meine Projekte</h3>
            <p className="text-sm text-gray-500">Übersicht und Status</p>
          </div>
        </Link>
        
        <Link to="/stats" className="card flex items-center gap-4">
          <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
            <BarChart3 className="text-green-600" size={24} />
          </div>
          <div>
            <h3 className="font-semibold">Statistiken</h3>
            <p className="text-sm text-gray-500">Auswertungen</p>
          </div>
        </Link>
      </div>
    </div>
  )
}
```

**src/pages/NewProjectPage.tsx:**
```tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { geruestbauApi } from '../api/geruestbau'

export default function NewProjectPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    name: '',
    address: '',
    client_name: '',
    description: '',
  })
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    
    try {
      const project = await geruestbauApi.createProject(form)
      // Automatisch Geodaten abrufen
      await geruestbauApi.enrichProject(project.id)
      navigate(`/projects/${project.id}`)
    } catch (error) {
      console.error('Fehler beim Erstellen:', error)
      alert('Fehler beim Erstellen des Projekts')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Projektname *
        </label>
        <input
          type="text"
          className="input-field"
          placeholder="z.B. Gerüst Kirche St. Peter"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Adresse *
        </label>
        <input
          type="text"
          className="input-field"
          placeholder="Strasse Nr, PLZ Ort"
          value={form.address}
          onChange={(e) => setForm({ ...form, address: e.target.value })}
          required
        />
        <p className="text-xs text-gray-500 mt-1">
          Geodaten werden automatisch abgerufen
        </p>
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Auftraggeber
        </label>
        <input
          type="text"
          className="input-field"
          placeholder="Name / Firma"
          value={form.client_name}
          onChange={(e) => setForm({ ...form, client_name: e.target.value })}
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Beschreibung
        </label>
        <textarea
          className="input-field min-h-[100px]"
          placeholder="Projektdetails..."
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
      </div>
      
      <button
        type="submit"
        className="btn-primary mt-6"
        disabled={loading || !form.name || !form.address}
      >
        {loading ? 'Wird erstellt...' : 'Projekt erstellen'}
      </button>
    </form>
  )
}
```

---

## Phase 4: CI/CD Pipeline

### .github/workflows/ci.yml

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # Backend Tests
  backend-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx
      
      - name: Run tests
        run: pytest tests/ -v
  
  # Frontend Tests (bestehendes Frontend)
  frontend-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        run: npm ci
      
      - name: Type check
        run: npm run build
  
  # Gerüstbau App Tests
  geruestbau-test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: geruestbau-app
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: geruestbau-app/package-lock.json
      
      - name: Install dependencies
        run: npm ci
      
      - name: Lint
        run: npm run lint
      
      - name: Type check
        run: npm run build
      
      - name: Run tests
        run: npm run test -- --run

  # Deploy only on main after all tests pass
  deploy:
    needs: [backend-test, frontend-test, geruestbau-test]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    
    steps:
      - name: Deploy to Railway
        run: |
          echo "Deployment triggered via Railway GitHub integration"
          # Railway deploys automatically on push to main
```

---

## Phase 5: Dockerfile für Gerüstbau-App

**geruestbau-app/Dockerfile:**
```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Dependencies
COPY package*.json ./
RUN npm ci

# Build
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config for SPA
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**geruestbau-app/nginx.conf:**
```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA routing - all routes to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
}
```

---

## Schnellstart-Befehle

### Lokale Entwicklung starten

```bash
# 1. Feature-Branch erstellen
git checkout -b feature/geruestbau-app

# 2. Backend starten (Terminal 1)
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Gerüstbau-App starten (Terminal 2)
cd geruestbau-app
npm install
npm run dev
# → http://localhost:3001

# 4. Änderungen committen
git add .
git commit -m "feat(geruestbau): Initial PWA setup"
git push origin feature/geruestbau-app

# 5. Pull Request auf GitHub erstellen
# → CI/CD Pipeline läuft automatisch
# → Nach Review: Merge to main
```

---

## Checkliste für Claude Code

- [ ] Branch `feature/geruestbau-app` erstellen
- [ ] `geruestbau-app/` Ordner mit PWA-Setup erstellen
- [ ] Backend-Router und Services hinzufügen
- [ ] CI/CD Pipeline (.github/workflows/ci.yml) erstellen
- [ ] Lokale Tests durchführen
- [ ] Pull Request erstellen
- [ ] Nach Merge: Railway deployed automatisch

---

## Wichtige URLs nach Deployment

| Service | URL |
|---------|-----|
| API | https://api.geodaten-ch.railway.app |
| Frontend (QA) | https://geodaten-ch.railway.app |
| **Gerüstbau App** | https://geruestbau.railway.app |
| API Docs | https://api.geodaten-ch.railway.app/docs |

---

*Erstellt: 31.12.2025*
*Für: Claude Code / IDE Integration*
