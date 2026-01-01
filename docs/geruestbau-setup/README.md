# Gerüstbau-App - Komplettes Entwicklungspaket

## Version 1.0 | 31. Dezember 2025

---

## 🎯 Übersicht

Dieses Paket enthält alle Mockups und Spezifikationen für die Gerüstbau-App zur Übergabe an Claude IDE.

### Was ist die Gerüstbau-App?

Eine Anwendung für Schweizer Gerüstbauer, die den Workflow von der Ausschreibung bis zur Offerte automatisiert:

- **Geodaten-Integration**: Automatische 3D-Gebäudedaten von swisstopo
- **Intelligente Konfiguration**: Gerüst-Editor mit Layher Blitz System
- **Export-Formate**: PDF-Offerte, DXF, IFC, LayPLAN XML

---

## 📁 Inhalt des Pakets

### Mockups (HTML)

```
mockups/
├── projects_dashboard.html    # Meine Projekte Übersicht
├── project_detail.html        # Projekt-Detail mit Workflow
├── import_v2.html             # Smart Import (Adresse/PDF/simap)
├── facade_selection.html      # Fassaden auswählen + Fotos
├── scaffold_complete.html     # Gerüst-Konfigurator (3 Tabs)
└── project_export.html        # Export & Offerte
```

### Spezifikationen (Markdown)

```
├── SCAFFOLD_CONFIGURATOR_SPEC.md   # Frontend-Spezifikation
├── GEODATEN_CH_REFACTORING.md      # Backend-Refactoring
└── README.md                       # Diese Datei
```

---

## 🔗 User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     MEINE PROJEKTE                              │
│                   projects_dashboard.html                       │
└─────────────────────────────┬───────────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            │                                   │
            ▼                                   ▼
     [+] Neues Projekt                   Projekt öffnen
            │                                   │
            ▼                                   ▼
┌───────────────────┐               ┌───────────────────┐
│    1. IMPORT      │               │  PROJECT DETAIL   │
│   import_v2.html  │               │ project_detail    │
│                   │               │                   │
│ • Adresse eingeben│               │ • Workflow-Steps  │
│ • PDF hochladen   │               │ • Dokumente       │
│ • simap.ch Import │               │ • Aktivitäten     │
│ • Geodaten laden  │               │                   │
└─────────┬─────────┘               └─────────┬─────────┘
          │                                   │
          ▼                                   │
┌───────────────────┐                         │
│   2. FASSADEN     │◀────────────────────────┤
│ facade_selection  │                         │
│                   │                         │
│ • Seiten wählen   │                         │
│ • Fotos zuordnen  │                         │
│ • Hindernisse     │                         │
└─────────┬─────────┘                         │
          │                                   │
          ▼                                   │
┌───────────────────┐                         │
│    3. GERÜST      │◀────────────────────────┤
│ scaffold_complete │                         │
│                   │                         │
│ • Übersicht-Tab   │                         │
│ • Editor-Tab      │                         │
│ • 3D-Tab          │                         │
└─────────┬─────────┘                         │
          │                                   │
          ▼                                   │
┌───────────────────┐                         │
│   4. DOKUMENTE    │◀────────────────────────┤
│  (in project_     │                         │
│   detail.html)    │                         │
│                   │                         │
│ • Fotos hochladen │                         │
│ • PDFs anhängen   │                         │
└─────────┬─────────┘                         │
          │                                   │
          ▼                                   │
┌───────────────────┐                         │
│    5. EXPORT      │◀────────────────────────┘
│  project_export   │
│                   │
│ • PDF-Offerte     │
│ • DXF / IFC       │
│ • LayPLAN XML     │
│ • E-Mail senden   │
└───────────────────┘
```

---

## 📋 Workflow-Schritte

| # | Schritt | Mockup | Beschreibung |
|---|---------|--------|--------------|
| 1 | **Import** | `import_v2.html` | Adresse eingeben, Geodaten automatisch laden |
| 2 | **Fassaden** | `facade_selection.html` | Seiten auswählen, Fotos mit GPS zuordnen |
| 3 | **Gerüst** | `scaffold_complete.html` | Konfigurieren, bearbeiten, 3D-Vorschau |
| 4 | **Dokumente** | `project_detail.html` | Fotos und Dateien hochladen |
| 5 | **Export** | `project_export.html` | Offerte generieren, CAD exportieren |

---

## 🛠 Technische Spezifikationen

### Frontend (SCAFFOLD_CONFIGURATOR_SPEC.md)

- **Framework**: React + TypeScript
- **Styling**: Tailwind CSS
- **3D-Bibliothek**: IFC.js / xeokit (empfohlen)
- **State Management**: Zustand
- **SVG**: Dynamisch, responsive

### Backend Refactoring (GEODATEN_CH_REFACTORING.md)

**Neue Datenquellen:**
| Quelle | Daten |
|--------|-------|
| swissBUILDINGS3D 3.0 | 3D-Geometrie, Höhen, Dachform |
| Sonnendach.ch | Dachflächen, Neigung |
| GWR via swisstopo | EGID, Baujahr, Attribute |
| swissALTI3D | Terrain, Gefälle |

**Zu prüfende Altlasten:**
- `gwr_madd_service.py` - Prüfen ob noch benötigt
- `geodienste_wfs.py` - Hat nie funktioniert

**Behalten:**
- `known_buildings.py` - Qualitative Daten für Prompts/ML

---

## 📱 Mockup-Features

### projects_dashboard.html
- Quick Stats (Projekte, Status)
- Filter-Tabs (Alle, In Arbeit, Offerten, Archiv)
- Projekt-Karten mit Progress-Anzeige
- FAB für neues Projekt
- Bottom Navigation

### project_detail.html
- Projekt-Header mit Status
- 5-Step Workflow (klickbar)
- Gesperrte Schritte bis Vorgänger erledigt
- Projektdaten-Übersicht
- Dokumente & Fotos Bereich
- Aktivitäten-Log
- Gefahrenzone (Löschen)

### import_v2.html
- Smart Import (Adresse, PDF, simap.ch)
- Drag & Drop
- Automatische Geodaten-Anreicherung
- Live-Vorschau

### facade_selection.html
- Interaktiver SVG-Grundriss
- Foto-Upload mit GPS-Erkennung
- Hindernisse markieren (Balkone, etc.)
- Fassaden-Karten

### scaffold_complete.html
- **Tab 1: Übersicht** - System, Arbeitstyp, Zusammenfassung
- **Tab 2: Editor** - Karussell, Grid-Editor, Tools
- **Tab 3: 3D** - Visualisierung, View-Presets

### project_export.html
- Offerte-Generator mit Vorlagen
- CAD-Export (DXF, IFC, LayPLAN, Excel)
- E-Mail-Versand
- Dokument-Historie

---

## 🚀 Implementierungs-Reihenfolge

### Phase 1: Backend (geodaten-ch)
1. swissBUILDINGS3D Service implementieren
2. Sonnendach.ch Service implementieren
3. BuildingBundle aktualisieren
4. Altlasten prüfen und aufräumen

### Phase 2: Frontend Grundstruktur
1. Projekt-Dashboard
2. Projekt-Detail mit Workflow
3. Navigation und Routing

### Phase 3: Import-Flow
1. Smart Import Komponente
2. Geodaten-Integration

### Phase 4: Fassaden-Auswahl
1. SVG-Grundriss
2. Foto-Upload mit GPS

### Phase 5: Gerüst-Konfigurator
1. Übersicht-Tab
2. Editor-Tab mit Karussell
3. 3D-Tab (Platzhalter → später IFC.js)

### Phase 6: Export
1. PDF-Offerte Generator
2. CAD-Export (DXF, IFC)
3. E-Mail-Integration

---

## 📞 Kontext

- **Projekt**: geodaten-ch (https://github.com/andreasrothbern/geodaten-ch)
- **Hosting**: Railway.app
- **API**: swisstopo REST API
- **Gerüst-System**: Layher Blitz 70
- **Zielmarkt**: Schweizer Gerüstbauer

---

## 📝 Offene Punkte

1. **3D-Bibliothek**: IFC.js/xeokit empfohlen, finale Entscheidung nach Evaluation
2. **Offline-Fähigkeit**: LocalStorage + PWA später
3. **Multi-Mandanten**: Vorerst Single-Tenant
4. **SVG-Qualität**: Mit echten 3D-Daten aus swissBUILDINGS3D verbessern

---

*Erstellt: 31.12.2025*
*Für: Claude IDE Übergabe*
