# PROJEKT_KONTEXT.md
# Gerüstplanung Schweiz - Gemeinsamer Kontext
# ============================================
# Diese Datei wird von Claude.ai UND Claude Code gelesen.
# Änderungen hier synchronisieren den Wissensstand beider Systeme.
# Technische Details: siehe geodaten-ch/CLAUDE.md

## 🎯 Aktuelles Projekt

**Objekt:** Bundeshaus Bern (Parlamentsgebäude)
**Adresse:** Bundesplatz 3, 3011 Bern
**Status:** Produktiv auf Railway.app

**App-URLs:**
- Frontend: https://cooperative-commitment-production.up.railway.app/
- Backend: https://acceptable-trust-production.up.railway.app/
- Mit Adresse: `?address=Bundesplatz%203,%203011%20Bern`

---

## ✅ Implementierter Funktionsumfang (Stand 29.12.2025)

| Feature | Status | Beschreibung |
|---------|--------|--------------|
| Adresssuche | ✅ | swisstopo API, Geokodierung |
| Gebäudedaten | ✅ | GWR via swisstopo (EGID, Geschosse, Fläche) |
| Gebäudegeometrie | ✅ | Polygon von geodienste.ch WFS |
| Höhendaten | ✅ | swissBUILDINGS3D (EGID + Koordinaten-Lookup) |
| **Terrain-Höhe** | ✅ | swissALTI3D (m ü.M.) mit Hanglage-Erkennung |
| **Dach-Analyse** | ✅ | Option C: Neigung, Form, Ausrichtung |
| Douglas-Peucker | ✅ | Polygon-Vereinfachung für Fassaden |
| SVG-Grundriss | ✅ | Interaktiv, klickbare Fassaden |
| SVG-Ansicht | ✅ | Fassadenansicht mit Gerüst + Zonen |
| SVG-Schnitt | ✅ | Querschnitt mit Höhenkoten + Zonen |
| Fassaden-Auswahl | ✅ | Multi-Select im Grundriss |
| NPK 114 Ausmass | ✅ | Berechnung nach Norm |
| Material-Schätzung | ✅ | Layher Blitz 70 Katalog |
| URL-Parameter | ✅ | `?address=...` für Direktaufruf |
| Compact-Modus | ✅ | Grösseres SVG im Gerüstbau-Tab |
| **Building Context** | ✅ | Höhenzonen für komplexe Gebäude |
| **Claude-Analyse** | ✅ | Auto-Erkennung bei extremer Höhendifferenz |
| **Orthofoto** | ✅ | Luftbild-Analyse für komplexe Gebäude |
| **Building Hints** | ✅ | Bekannte Gebäude (Bundeshaus, Münster) |
| **Einheitliches Prompt-System** | ✅ | v3.0 - Claude API immer für Schnitt/Ansicht |

---

## 🤖 Einheitliches Prompt-System v3.0 (29.12.2025)

Ersetzt statische Building-Hints durch dynamische Gebäude-Recherche.

**WICHTIG:** Der "Professional" Toggle wurde entfernt. Claude API wird jetzt IMMER für
Schnitt und Ansicht verwendet - identischer Prompt wie Export für Claude.ai.

### Komponenten

| Komponente | Datei | Funktion |
|------------|-------|----------|
| ResearchService | `prompts/research_service.py` | Claude Haiku für Gebäude-Recherche |
| PromptBuilder | `prompts/prompt_builder.py` | Template-basierter Prompt-Aufbau |
| claude_svg_zones | `claude_svg_zones.py` | Nutzt PromptBuilder (v3.0) |
| Vorlage | `docs/Export_Prompt_Claude.md` | Zentrale Dokumentation |

### Ablauf

```
Frontend Export-Button     Backend (automatisch)
         │                          │
         │                   use_claude=true (Default)
         └──────────┬───────────────┘
                    ▼
         ┌──────────────────┐
         │  PromptBuilder   │
         │  (einheitlich!)  │
         └──────────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │ Claude-Recherche │
         │ (Cache prüfen)   │
         └──────────────────┘
                    │
     ┌──────────────┼──────────────┐
     ▼              ▼              ▼
   HIT           MISS          FALLBACK
  (cached)    (Claude API)    (GWR-Daten)
     │              │              │
     └──────────────┼──────────────┘
                    ▼
      IDENTISCHER Prompt für
      Export UND SVG-Generierung
```

### Kosten

| Szenario | Kosten | Latenz |
|----------|--------|--------|
| Cache-Hit (30 Tage) | $0.00 | <100ms |
| Cache-Miss (Haiku) | ~$0.01-0.02 | 1-2s |
| Fallback (kein API) | $0.00 | <100ms |

### API-Endpunkte

```python
# Prompt generieren
GET /api/v1/prompt/generate?address=Bundesplatz%203&svg_type=all

# Cache-Statistiken
GET /api/v1/prompt/research/stats

# Abgelaufene Einträge löschen
POST /api/v1/prompt/research/clear-expired
```

---

## 📊 Datenquellen

### SwissBuildings3D - Höhenproblem bei komplexen Gebäuden

⚠️ **Bekanntes Problem:** Globaler Höhenwert oft nicht repräsentativ!

**Beispiel Bundeshaus:**
- SwissBuildings3D Traufhöhe: 14.5 m → Dies ist der Arkaden-Wert!
- Tatsächliche Parlamentsfassade: 22–25 m Traufe

### Realistische Höhenzonen Bundeshaus
| Gebäudeteil | Traufhöhe | Firsthöhe | Gerüsthöhe |
|-------------|-----------|-----------|------------|
| Arkaden (Verbindungen) | ~14 m | – | 15 m |
| Bundeshaus West/Ost | 15–18 m | 20–22 m | 19 m |
| Parlamentsgebäude | 22–25 m | 28–32 m | 26 m |
| Ecktürme Süd | – | 35–38 m | 36 m (Spezial) |
| Hauptkuppel | – | 62–64 m | Kuppelgerüst |

### Höhen-Lookup Strategie (implementiert)

```
1. Manuell eingegeben (Trauf-/Firsthöhe)
   ↓
2. EGID-Lookup (building_heights_detailed)
   ↓
3. Koordinaten-Lookup (±25m Toleranz)
   ↓
4. Geschätzt aus GWR (Geschosse × 3m)
   ↓
5. Standard nach Kategorie (EFH: 8m, MFH: 12m)
```

---

## ⚙️ Douglas-Peucker Parameter (aktuell im Code)

```python
# In geodienste.py
SIMPLIFY_EPSILON = 0.3           # Meter - Toleranz für Punktreduktion
COLLINEAR_ANGLE_TOLERANCE = 8.0  # Grad - für kollineare Segmente
MIN_SIDE_LENGTH = 1.0            # Meter - minimale Seitenlänge
```

### Empfehlungen je Gebäudegrösse
| Gebäudetyp | EPSILON | ANGLE_TOL | Bemerkung |
|------------|---------|-----------|-----------|
| EFH (10×12m) | 0.3–0.5 | 5–8° | Wenig Vereinfachung |
| MFH/Gewerbe | 0.5–1.0 | 8–10° | Standard |
| Grossprojekt (>50m) | 1.0–2.0 | 8–12° | Starke Vereinfachung |

---

## 📐 NPK 114 Konstanten (implementiert)

```python
# In npk114_calculator.py
FASSADENABSTAND_LF = 0.30        # m - Abstand Gebäude zu Gerüst
GERUESTGANGBREITE_LG = 0.70      # m - für W09
STIRNSEITIGER_ABSCHLUSS_LS = 1.00 # m - beidseitig
HOEHENZUSCHLAG = 1.00            # m - über Arbeitshöhe
MIN_AUSMASSLAENGE = 2.5          # m
MIN_AUSMASSHOEHE = 4.0           # m

# Formeln
# LA = LS + L + LS (beidseitiger Abschluss)
# HA = H + Höhenzuschlag
# A = LA × HA
# Giebel: H_mittel = H_Traufe + (H_First - H_Traufe) × 0.5
```

---

## 🔧 Layher Blitz 70 System (implementiert)

### Feldlängen (m)
`3.07, 2.57, 2.07, 1.57, 1.09, 0.73`

### Rahmenhöhen (m)
`2.00, 1.50, 1.00, 0.50`

### Richtwerte
| Parameter | Wert |
|-----------|------|
| Gewicht | 18–22 kg/m² Gerüstfläche |
| Lastklasse | 3 (200 kg/m²) |
| Breitenklasse | W09 (0.90 m) |
| Verankerung | alle 4 m horizontal, alle 4 m vertikal |

### Feldlängen-Verhältnis (UI-Slider)
- **0%**: Nur 2.57m Felder (mehr Flexibilität)
- **100%**: Nur 3.07m Felder (weniger Teile)
- **Standard: 50%**: Ausgewogen

---

## 📁 App-Architektur

```
geodaten-ch/
├── backend/                    # FastAPI + Python 3.11
│   └── app/
│       ├── main.py             # API Endpunkte
│       └── services/
│           ├── swisstopo.py    # Geokodierung, GWR
│           ├── geodienste.py   # Polygon, Douglas-Peucker
│           ├── svg_generator.py # SVG-Visualisierungen
│           ├── npk114_calculator.py # Ausmass-Berechnung
│           └── layher_catalog.py # Material-Schätzung
│
├── frontend/                   # React + Vite + TypeScript
│   └── src/
│       ├── App.tsx             # Haupt-App mit URL-Parameter
│       └── components/
│           ├── GrunddatenCard.tsx    # Gebäudedaten + SVGs
│           ├── ScaffoldingCard.tsx   # Gerüst-Konfiguration
│           ├── InteractiveFloorPlan.tsx # Klickbarer Grundriss
│           ├── AusmassCard.tsx       # NPK 114 Ausmass
│           └── MaterialCard.tsx      # Layher Material
│
└── Deployed on Railway.app (mit Volume für SQLite)
```

### Wichtige API-Endpunkte

```python
# Gerüstbau-Daten (Hauptendpoint)
GET /api/v1/scaffolding?address=Bundesplatz 3, 3011 Bern

# SVG-Visualisierungen
POST /api/v1/visualize/floor-plan  # Grundriss (compact mode)
GET  /api/v1/visualize/cross-section?address=...
GET  /api/v1/visualize/elevation?address=...

# Ausmass & Material
GET /api/v1/ausmass/komplett?address=...&system_id=blitz70
```

---

## 🚧 Offene Aufgaben

### Priorität 1 (Nächste Schritte)
- [ ] Lokale Höhen pro Fassade (Höhenzonen-Segmentierung)
- [ ] Gerüstkonfiguration → Berechnung (Arbeitstyp, Gerüstart)
- [ ] Breitenklassen-Auswahl (W06, W09, W12)

### Priorität 2
- [ ] Export als PDF/Word
- [ ] Lift-Integration (NPK 114.312)
- [ ] System-Kombinationen (Blitz + Allround)

### Priorität 3
- [ ] Custom Domain
- [ ] 3D-Visualisierung (optional)
- [ ] Mehrere Gebäude pro Projekt

---

## 🔄 Letzte Änderungen

| Datum | Änderung | Von |
|-------|----------|-----|
| 2025-12-29 | Einheitliches Prompt-System v3.0 - Professional Toggle entfernt | Claude Code |
| 2025-12-29 | Dynamisches Prompt-System (research_service + prompt_builder) | Claude Code |
| 2025-12-29 | Terrain-Höhe im Frontend + Claude API | Claude Code |
| 2025-12-29 | Dach-Daten (Neigung, Form) im Frontend | Claude Code |
| 2025-12-29 | Export Prompt erweitert (Terrain, Dach, Zonen) | Claude Code |
| 2025-12-28 | Building Hints für bekannte Gebäude | Claude Code |
| 2025-12-28 | Orthofoto-Service + Claude Vision | Claude Code |
| 2025-12-28 | Building Context System (Höhenzonen) | Claude Code |
| 2025-12-24 | URL-Parameter für Adresse, Compact-Modus SVG | Claude Code |
| 2025-12-24 | Douglas-Peucker Polygon-Vereinfachung | Claude Code |
| 2025-12-24 | PROJEKT_KONTEXT.md synchronisiert mit CLAUDE.md | Claude Code |
| 2024-12-24 | Datei erstellt, Bundeshaus-Höhenproblem dokumentiert | Claude.ai |

---

## 📝 Hinweise

### Für Claude Code (IDE)
- Technische Details: `geodaten-ch/CLAUDE.md`
- Bei Code-Änderungen: Status in CLAUDE.md aktualisieren
- Bei Parameter-Änderungen: beide Dateien synchron halten

### Für Claude.ai (Chat)
- Screenshots der App helfen bei der Analyse
- Code-Review: Datei hochladen oder einfügen
- Diese Datei liegt in Project Knowledge
