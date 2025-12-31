# Gerüstbau-App Schnellstart

## 1. Branch erstellen

```bash
cd geodaten-ch
git checkout main
git pull origin main
git checkout -b feature/geruestbau-app
```

## 2. Gerüstbau-App Ordner erstellen

```bash
mkdir -p geruestbau-app/src/{components,pages,hooks,api,types,utils,stores}
mkdir -p geruestbau-app/src/components/{ui,layout,projects,geodata,photos,scaffold}
mkdir -p geruestbau-app/public/icons
```

## 3. Dateien erstellen

Siehe `GERUESTBAU_APP_SETUP.md` für vollständigen Inhalt:

### Basis-Dateien (geruestbau-app/)
- `package.json`
- `vite.config.ts`
- `tailwind.config.js`
- `postcss.config.js`
- `tsconfig.json`
- `tsconfig.node.json`
- `index.html`
- `Dockerfile`
- `nginx.conf`

### Source-Dateien (geruestbau-app/src/)
- `main.tsx`
- `App.tsx`
- `index.css`
- `api/client.ts`
- `api/geruestbau.ts`
- `types/project.ts`
- `components/layout/Header.tsx`
- `components/layout/BottomNav.tsx`
- `pages/HomePage.tsx`
- `pages/NewProjectPage.tsx`
- `pages/ProjectsPage.tsx`
- `pages/ProjectDetailPage.tsx`

### Backend-Erweiterung (backend/app/)
- `models/geruestbau.py`
- `routers/geruestbau.py`
- `services/geruestbau/__init__.py`
- `services/geruestbau/project_service.py`

### CI/CD
- `.github/workflows/ci.yml`

## 4. Dependencies installieren

```bash
cd geruestbau-app
npm install
```

## 5. Lokal testen

```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Gerüstbau-App
cd geruestbau-app
npm run dev
# → http://localhost:3001
```

## 6. Commit & Push

```bash
git add .
git commit -m "feat(geruestbau): Initial PWA setup with project management"
git push origin feature/geruestbau-app
```

## 7. Pull Request erstellen

1. GitHub → Repository → "Compare & pull request"
2. Titel: `feat(geruestbau): Initial PWA setup`
3. Beschreibung: Was wurde hinzugefügt
4. CI/CD läuft automatisch
5. Nach Review → Merge

## Datei-Referenz

Alle vollständigen Dateiinhalte sind in:
**`docs/GERUESTBAU_APP_SETUP.md`**
