# CLAUDE.md Erweiterung - Gerüstbau-App

> **Füge diesen Abschnitt zur bestehenden CLAUDE.md hinzu**

---

## Gerüstbau-App Module

### Neue Projektstruktur

```
geodaten-ch/
├── backend/                    # Bestehend + erweitert
│   ├── app/
│   │   ├── routers/
│   │   │   └── geruestbau.py  # NEU: /api/v1/geruestbau/*
│   │   ├── models/
│   │   │   └── geruestbau.py  # NEU: Project, Photo, Scaffold
│   │   └── services/
│   │       └── geruestbau/    # NEU: Business Logic
│   └── tests/
│       └── test_geruestbau.py
├── frontend/                   # Bestehend (Qualitätskontrolle)
├── geruestbau-app/            # NEU: Mobile-First PWA
│   ├── src/
│   ├── public/
│   └── Dockerfile
└── .github/workflows/ci.yml   # NEU: CI/CD Pipeline
```

### Branching-Workflow

**IMMER Feature-Branches verwenden!**

```bash
# Neuen Branch erstellen
git checkout -b feature/geruestbau-[feature-name]

# Commits mit Prefix
git commit -m "feat(geruestbau): Beschreibung"
git commit -m "fix(geruestbau): Bugfix"
git commit -m "test(geruestbau): Tests"

# Push und PR erstellen
git push origin feature/geruestbau-[feature-name]
# → PR auf GitHub erstellen
# → CI läuft automatisch
# → Nach Review mergen
```

### API-Endpunkte (neu)

```
# Projekte
GET    /api/v1/geruestbau/projects
POST   /api/v1/geruestbau/projects
GET    /api/v1/geruestbau/projects/{id}
PUT    /api/v1/geruestbau/projects/{id}
DELETE /api/v1/geruestbau/projects/{id}

# Geodaten-Anreicherung
POST   /api/v1/geruestbau/projects/{id}/enrich

# Fotos
POST   /api/v1/geruestbau/projects/{id}/photos
POST   /api/v1/geruestbau/projects/{id}/photos/{photo_id}/analyze

# Gerüst-Konfiguration
GET    /api/v1/geruestbau/projects/{id}/scaffold
PUT    /api/v1/geruestbau/projects/{id}/scaffold

# Export
POST   /api/v1/geruestbau/projects/{id}/export?format=pdf|ifc|dxf
```

### Lokale Entwicklung

```bash
# Backend (Port 8000)
cd backend && uvicorn app.main:app --reload

# Gerüstbau-App (Port 3001)
cd geruestbau-app && npm run dev

# Bestehendes Frontend (Port 3000)
cd frontend && npm run dev
```

### Tech Stack Gerüstbau-App

- **Framework:** React 18 + TypeScript
- **Build:** Vite 5
- **Styling:** TailwindCSS 3
- **Routing:** React Router 6
- **State:** Zustand
- **Icons:** Lucide React
- **PWA:** vite-plugin-pwa

### Wichtige Dateien

| Datei | Zweck |
|-------|-------|
| `geruestbau-app/vite.config.ts` | PWA-Konfiguration |
| `geruestbau-app/src/api/client.ts` | API-Client |
| `geruestbau-app/src/types/project.ts` | TypeScript Types |
| `backend/app/routers/geruestbau.py` | API-Router |
| `backend/app/services/geruestbau/` | Business Logic |
| `.github/workflows/ci.yml` | CI/CD Pipeline |

### Deployment (Railway)

Nach Merge zu `main` deployed Railway automatisch:

| Service | Domain |
|---------|--------|
| Backend | api.geodaten-ch.railway.app |
| Frontend (QA) | geodaten-ch.railway.app |
| Gerüstbau App | geruestbau.railway.app |

### Konzept-Dokument

Vollständiges Konzept: `docs/geruestbau_app_konzept.md`

Module im Konzept:
1. Ausschreibungserfassung
2. Geodaten-Anreicherung
3. Foto-Upload & Analyse
4. Daten-Kontrolle
5. Fassaden-Auswahl
6. Gerüst-Editor
7. Material-Zusammenstellung
8. Export & Offerte
