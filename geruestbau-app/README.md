# Gerüstbau App

Mobile-First PWA für Gerüstbau-Projekterfassung und Kalkulation.

## Tech Stack

| Komponente | Technologie |
|------------|-------------|
| Framework | React 18 + TypeScript |
| Build | Vite 5 |
| Styling | TailwindCSS 3 |
| Routing | React Router 6 |
| State | Zustand |
| Icons | Lucide React |
| PWA | vite-plugin-pwa |

## Entwicklung

### Voraussetzungen

- Node.js 20+
- npm 10+
- Backend läuft auf Port 8000

### Installation

```bash
cd geruestbau-app
npm install
```

### Lokale Entwicklung

```bash
# Terminal 1: Backend starten
cd ../backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Gerüstbau-App starten
cd geruestbau-app
npm run dev
```

Die App läuft auf **http://localhost:3001**

### Build

```bash
npm run build
```

Build-Output in `dist/`

### Tests

```bash
npm run test
```

## Projektstruktur

```
geruestbau-app/
├── src/
│   ├── api/                 # API Client
│   │   ├── client.ts        # Basis-Client
│   │   └── geruestbau.ts    # Gerüstbau-Endpoints
│   ├── components/
│   │   ├── layout/          # Header, BottomNav
│   │   ├── ui/              # Button, Card, Input
│   │   ├── projects/        # Projekt-Komponenten
│   │   ├── geodata/         # Geodaten-Anzeige
│   │   ├── photos/          # Foto-Upload/Analyse
│   │   └── scaffold/        # Gerüst-Editor
│   ├── pages/               # Seiten-Komponenten
│   ├── hooks/               # Custom Hooks
│   ├── stores/              # Zustand Stores
│   ├── types/               # TypeScript Types
│   ├── utils/               # Hilfsfunktionen
│   ├── App.tsx              # Haupt-App mit Routing
│   ├── main.tsx             # Entry Point
│   └── index.css            # Tailwind + Custom Styles
├── public/
│   ├── favicon.svg
│   └── icons/               # PWA Icons
├── package.json
├── vite.config.ts           # Vite + PWA Konfiguration
├── tailwind.config.js
├── tsconfig.json
├── Dockerfile               # Production Build
└── nginx.conf               # SPA Routing
```

## API-Integration

Die App nutzt die geodaten-ch Backend-API:

| Endpoint | Beschreibung |
|----------|--------------|
| `GET /api/v1/geruestbau/projects` | Projektliste |
| `POST /api/v1/geruestbau/projects` | Projekt erstellen |
| `POST /api/v1/geruestbau/projects/{id}/enrich` | Geodaten abrufen |
| `GET /api/v1/smart-building/data` | Gebäudedaten |

Siehe `src/api/geruestbau.ts` für alle Endpoints.

## Environment Variables

| Variable | Beschreibung | Default |
|----------|--------------|---------|
| `VITE_API_URL` | Backend API URL | `` (Proxy) |

Für Produktion:
```bash
VITE_API_URL=https://acceptable-trust-production.up.railway.app
```

## PWA Features

- Offline-Caching (Workbox)
- Installierbar auf iOS/Android
- API-Response Caching (24h)

## Deployment

Deployment erfolgt via Railway.app nach Merge zu `main`.

**Lokaler Docker-Test:**
```bash
docker build -t geruestbau-app .
docker run -p 8080:80 geruestbau-app
```

## Branching

```bash
# Feature-Branch erstellen
git checkout -b feature/geruestbau-[feature-name]

# Commit
git commit -m "feat(geruestbau): Beschreibung"

# Push + PR
git push origin feature/geruestbau-[feature-name]
```

## Weitere Dokumentation

- [Setup-Guide](../docs/geruestbau-app/GERUESTBAU_APP_SETUP.md)
- [Quickstart](../docs/geruestbau-app/QUICKSTART.md)
- [CLAUDE_GERUESTBAU.md](../CLAUDE_GERUESTBAU.md)
