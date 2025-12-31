# Gerüstbau-App: Projekt-Import Feature

## Implementierungs-Guide für Claude IDE

### Übersicht

Das Projekt-Import Feature ermöglicht drei Wege zur Projekterfassung:
1. **Drag & Drop** - PDF oder Foto der Ausschreibung hochladen
2. **simap.ch Link** - URL einfügen und Daten automatisch auslesen
3. **Manuell** - Projektdaten direkt eingeben (Toggle-Panel)

---

## UI-Struktur (Step 1: Import)

```
┌─────────────────────────────────────────────────────────────┐
│  ← Zurück          Neues Projekt                            │
│  ════════════════════════════════════════ Schritt 1 von 3   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                      ☁️                              │   │
│  │                                                     │   │
│  │     PDF hier ablegen oder klicken zum Upload        │   │
│  │           PDF, JPG, PNG (max. 10 MB)                │   │
│  │                                                     │   │
│  │  ──────────────────── oder ────────────────────     │   │
│  │                                                     │   │
│  │     [📷 Foto aufnehmen]    [📄 Datei wählen]       │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  🔍  Gerüstbau-Ausschreibungen finden               │   │
│  │      simap.ch mit voreingestelltem Filter öffnen    │   │
│  │      [ simap.ch öffnen ↗ ]                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                        (blauer Hintergrund)                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  🔗  Projekt-Link einfügen                          │   │
│  │                                                     │   │
│  │  Kopiere den Link von simap.ch und füge ihn ein:   │   │
│  │  ┌───────────────────────────────────────────┐     │   │
│  │  │ https://simap.ch/de/project-detail/...  📋│     │   │
│  │  └───────────────────────────────────────────┘     │   │
│  │  ✓ simap.ch Link erkannt                           │   │
│  │                                                     │   │
│  │  [ ✨ Daten auslesen ]                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ──────────────────────── oder ────────────────────────    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ✏️  Manuell erfassen                            ⌄  │   │
│  │      Ohne Dokument                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Manuell erfassen (Toggle geöffnet)

```
┌─────────────────────────────────────────────────────────────┐
│  ✏️  Manuell erfassen                                   ⌃  │
│      Ohne Dokument                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Projektdaten                                               │
│                                                             │
│  Projekttitel *                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Adresse *                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│  ✨ Gebäudedaten werden automatisch geladen                 │
│                                                             │
│  Auftraggeber                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Eingabefrist              Verfahren                        │
│  ┌──────────────────┐     ┌──────────────────┐             │
│  │                  │     │ -- wählen --   ⌄ │             │
│  └──────────────────┘     └──────────────────┘             │
│                                                             │
│  Beschreibung                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│       [ Zurück ]                [ Weiter ]                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow-Übersicht

```
                    ┌─────────────────┐
                    │   STEP 1        │
                    │   Import        │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
   ┌───────────┐      ┌───────────┐      ┌───────────┐
   │  PDF/Foto │      │  simap.ch │      │  Manuell  │
   │  Upload   │      │   Link    │      │  (Toggle) │
   └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
         │                  │                   │
         ▼                  ▼                   │
   ┌───────────┐      ┌───────────┐             │
   │  Claude   │      │   URL     │             │
   │  Vision   │      │  Import   │             │
   └─────┬─────┘      └─────┬─────┘             │
         │                  │                   │
         └────────┬─────────┘                   │
                  ▼                             │
         ┌─────────────────┐                    │
         │   STEP 2        │                    │
         │   Daten prüfen  │◄───────────────────┘
         │   (vorausgefüllt)                    │
         └────────┬────────┘                    │
                  │                             │
                  ▼                             │
         ┌─────────────────┐                    │
         │   STEP 3        │◄───────────────────┘
         │   Geodaten +    │     (Manuell springt
         │   Abschluss     │      direkt hierher)
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │   ✓ Projekt     │
         │   erstellt!     │
         └─────────────────┘
```

---

## Komponenten-Struktur

### React Components (Frontend)

```
src/
├── pages/
│   └── projects/
│       └── NewProjectPage.tsx          # Haupt-Seite mit Step-Navigation
│
├── components/
│   └── projects/
│       ├── import/
│       │   ├── ImportStep.tsx          # Step 1 Container
│       │   ├── DropZone.tsx            # Drag & Drop + Buttons
│       │   ├── SimapSearchBox.tsx      # Blauer simap.ch Such-Box
│       │   ├── UrlImportBox.tsx        # Link einfügen + Auslesen
│       │   └── ManualEntryToggle.tsx   # Toggle mit vollem Formular
│       │
│       ├── review/
│       │   ├── ReviewStep.tsx          # Step 2 Container
│       │   ├── SourceBadge.tsx         # Quelle-Anzeige
│       │   └── ProjectDataForm.tsx     # Editierbares Formular
│       │
│       └── geodata/
│           ├── GeodataStep.tsx         # Step 3 Container
│           ├── GeodataLoader.tsx       # Loading-Animation
│           ├── BuildingDataCard.tsx    # EGID, Höhen, Fläche
│           └── AdditionalDocsUpload.tsx
│
├── hooks/
│   ├── useFileUpload.ts                # Drag & Drop Logic
│   ├── useUrlImport.ts                 # URL Parsing
│   └── useGeodata.ts                   # geodaten-ch API
│
└── types/
    └── project.ts                      # TypeScript Interfaces
```

---

## API Endpoints (Backend)

### 1. PDF/Foto Analyse
```
POST /api/v1/import/document
Content-Type: multipart/form-data
Body: { file: <PDF|Image> }

Response: {
  success: true,
  source: "pdf" | "photo",
  data: {
    title: "Gerüstarbeiten Fassadensanierung...",
    address: "Länggassstrasse 40, 3012 Bern",
    client: "Stadt Bern, Hochbau",
    deadline: "15.02.2025",
    procedure: "open",
    description: "Fassadengerüst für..."
  }
}
```

### 2. URL Import
```
POST /api/v1/import/url
Body: { url: "https://simap.ch/de/project-detail/..." }

Response: {
  success: true,
  source: "simap",
  source_id: "7bcbe557-5b96-4b74-8fa6-9067363aa4ca",
  data: { ... }  // Gleiche Struktur
}
```

### 3. Geodaten laden
```
GET /api/v1/building/by-address?address=Länggassstrasse+40,+3012+Bern

Response: {
  found: true,
  egid: "302145678",
  address: "Länggassstrasse 40, 3012 Bern",
  building_type: "Schulgebäude",
  year_built: 1965,
  floors: 4,
  eaves_height_m: 12.4,
  ridge_height_m: 16.2,
  ground_area_m2: 850
}
```

### 4. Projekt erstellen
```
POST /api/v1/projects
Body: {
  title: "...",
  address: "...",
  client: "...",
  deadline: "2025-02-15",
  procedure: "open",
  description: "...",
  source_type: "pdf" | "url" | "manual",
  source_url: "https://simap.ch/...",  // optional
  egid: "302145678",
  building_data: { ... }
}

Response: {
  id: "proj_abc123",
  created_at: "2025-01-01T12:00:00Z",
  ...
}
```

---

## Wichtige URLs & Codes

### simap.ch Gerüstbau-Filter
```
https://www.simap.ch/de?cpvCodes=["44212310","45262100"]&newestPubTypes=["tender"]&orderAddressCountryOnlySwitzerland=true
```

### CPV-Codes
| Code | Beschreibung |
|------|--------------|
| 44212310 | Gerüste (Material) |
| 45262100 | Gerüstbauarbeiten |

### geodaten-ch API (bestehend)
```
Base: https://cooperative-commitment-production.up.railway.app
Endpoint: /api/v1/building/smart
```

---

## Technische Details

### DropZone mit Kamera
```tsx
// DropZone.tsx
<input type="file" accept=".pdf,image/*" onChange={handleFile} />
<input type="file" accept="image/*" capture="environment" onChange={handleFile} />

<button onClick={() => cameraInput.click()}>
  <Camera /> Foto aufnehmen
</button>
<button onClick={() => fileInput.click()}>
  <File /> Datei wählen
</button>
```

### Toggle-Verhalten
```tsx
// ManualEntryToggle.tsx
const [isOpen, setIsOpen] = useState(false);

<button onClick={() => setIsOpen(!isOpen)}>
  <Pen /> Manuell erfassen
  <ChevronDown className={isOpen ? 'rotate-180' : ''} />
</button>

{isOpen && (
  <div className="border-t">
    <ProjectDataForm />
    <button onClick={onSubmit}>Weiter</button>
  </div>
)}
```

### URL-Erkennung
```typescript
const isSimapUrl = (url: string) => url.includes('simap.ch');

const extractProjectId = (url: string) => {
  const match = url.match(/project-detail\/([a-f0-9-]+)/i);
  return match?.[1] ?? null;
};
```

---

## Dateien

| Datei | Beschreibung |
|-------|--------------|
| `mockups/import_v2.html` | Interaktives Mockup (im Browser testbar) |
| `backend/app/services/importer/url_importer.py` | URL Import Service |
| `backend/app/routers/import_router.py` | FastAPI Endpoints |

---

## Nächste Schritte

- [ ] Frontend-Komponenten in React/TypeScript
- [ ] URL-Import Backend (simap.ch Scraping)
- [ ] Claude Vision Integration für PDF/Foto
- [ ] Mobile Testing (Kamera)
- [ ] Error Handling & Validation
- [ ] Loading States & Feedback
