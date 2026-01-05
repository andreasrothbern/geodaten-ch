# Gerüstbau-App: Konzept für Projektverwaltung und Datenerfassung

> **⚠️ DEPRECATED (04.01.2026)**
>
> Dieses Dokument ist veraltet. Die hier beschriebene Datenbank-Struktur mit separaten
> Tabellen (PROJECT, BUILDING_DATA, ZONE) wurde NICHT implementiert.
>
> **Aktuelle Architektur:**
> - `geruestbau.db` verwendet JSON-Spalten (`building_data`, `buildings`)
> - Siehe `POLYGON_DATENFLUSS.md` für aktuelle Architektur
> - Grunddaten vs. Enrichment-Trennung siehe `project_service.py`

## Version 1.0 | Dezember 2025 (DEPRECATED)

---

## Executive Summary

Diese App unterstützt Gerüstbauer von der **Ausschreibungserfassung** bis zur **Offertenerstellung**. Der Workflow integriert:
- Foto-basierte Gebäudeerfassung
- Automatische Geodaten-Anreicherung (geodaten-ch API)
- KI-gestützte Fassadenanalyse
- Interaktive Gerüstplanung
- Export in Industriestandards (IFC, DXF)

---

## Inhaltsverzeichnis

1. [Workflow-Übersicht](#1-workflow-übersicht)
2. [Modul 1: Ausschreibungserfassung](#2-modul-1-ausschreibungserfassung)
3. [Modul 2: Geodaten-Anreicherung](#3-modul-2-geodaten-anreicherung)
4. [Modul 3: Foto-Upload & Analyse](#4-modul-3-foto-upload--analyse)
5. [Modul 4: Daten-Kontrolle & Ergänzung](#5-modul-4-daten-kontrolle--ergänzung)
6. [Modul 5: Fassaden-Auswahl](#6-modul-5-fassaden-auswahl)
7. [Modul 6: Gerüst-Editor](#7-modul-6-gerüst-editor)
8. [Modul 7: Material-Zusammenstellung](#8-modul-7-material-zusammenstellung)
9. [Modul 8: Export & Offerte](#9-modul-8-export--offerte)
10. [Technische Architektur](#10-technische-architektur)
11. [API-Spezifikationen](#11-api-spezifikationen)
12. [Datenmodell](#12-datenmodell)

---

## 1. Workflow-Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        GERÜSTBAU-APP WORKFLOW                               │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │    1     │    │    2     │    │    3     │    │    4     │
  │ ERFASSUNG│───▶│ GEODATEN │───▶│  FOTOS   │───▶│ KONTROLLE│
  │          │    │   API    │    │ ANALYSE  │    │          │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘
       │                                               │
       │  ┌─────────────────────────────────────────┐  │
       │  │ Ausschreibung:                          │  │
       │  │ • PDF-Upload                            │  │
       │  │ • Foto von Aushang                      │  │
       │  │ • Manuelle Eingabe                      │  │
       │  │ • simap.ch Import                       │  │
       │  └─────────────────────────────────────────┘  │
       │                                               │
       ▼                                               ▼
  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │    5     │    │    6     │    │    7     │    │    8     │
  │ FASSADEN │───▶│  GERÜST  │───▶│ MATERIAL │───▶│  EXPORT  │
  │ AUSWAHL  │    │  EDITOR  │    │  LISTE   │    │ OFFERTE  │
  └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │ • PDF Offerte   │
                                              │ • IFC Export    │
                                              │ • DXF Export    │
                                              │ • LayPLAN XML   │
                                              └─────────────────┘
```

### Projekt-Status-Flow

```
ENTWURF → ERFASST → ANGEREICHERT → GEPRÜFT → GEPLANT → OFFERIERT → BEAUFTRAGT
   │         │           │            │          │          │           │
   └─────────┴───────────┴────────────┴──────────┴──────────┴───────────┘
                              Projekt kann jederzeit
                              bearbeitet werden
```

---

## 2. Modul 1: Ausschreibungserfassung

### 2.1 Erfassungsmethoden

| Methode | Beschreibung | Datenqualität |
|---------|--------------|---------------|
| **PDF-Upload** | Ausschreibungsdokument hochladen | ⭐⭐⭐⭐⭐ |
| **Foto-Scan** | Foto von Aushang/Brief | ⭐⭐⭐⭐ |
| **simap.ch Import** | Direktimport via API | ⭐⭐⭐⭐⭐ |
| **Manuelle Eingabe** | Formular ausfüllen | ⭐⭐⭐ |
| **E-Mail Forward** | E-Mail an app@firma.ch | ⭐⭐⭐⭐ |

### 2.2 UI-Design: Erfassungsscreen

```
┌─────────────────────────────────────────────────────────────┐
│  ← Zurück          NEUES PROJEKT           [Speichern]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                     │    │
│  │     📄 PDF hier ablegen oder klicken zum Upload     │    │
│  │                                                     │    │
│  │     ────────── oder ──────────                      │    │
│  │                                                     │    │
│  │     📷 Foto aufnehmen    🔗 simap.ch Import         │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  EXTRAHIERTE DATEN (editierbar):                            │
│                                                             │
│  Projektname:    [Gerüst Kirche St. Peter und Paul    ]     │
│  Adresse:        [Rathausgasse 2, 3011 Bern           ]     │
│  Auftraggeber:   [Christkatholische Kirchgemeinde     ]     │
│                                                             │
│  Ausschreibungs-Nr: [2024-BER-12345                   ]     │
│  Eingabefrist:      [15.01.2025                       ]     │
│  Projektstart:      [01.03.2025                       ]     │
│  Projektende:       [30.06.2025                       ]     │
│                                                             │
│  Beschreibung:                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Fassadengerüst für Renovationsarbeiten an der      │    │
│  │ Westfassade inkl. Turm. Höhe ca. 55m.              │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  [ ] Dringend    [ ] Sonderkonstruktion erforderlich        │
│                                                             │
│           [Geodaten abrufen →]                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 OCR-Extraktion aus Fotos/PDFs

```python
class AusschreibungExtractor:
    """Extrahiert strukturierte Daten aus Ausschreibungen."""
    
    EXTRACTION_PROMPT = """
    Analysiere diese Ausschreibung und extrahiere:
    
    1. Adresse des Objekts
    2. Auftraggeber (Name, Kontakt)
    3. Projektbeschreibung
    4. Termine (Eingabefrist, Ausführungszeitraum)
    5. Besondere Anforderungen
    6. Geschätzte Gerüstfläche (falls angegeben)
    
    Antworte im JSON-Format:
    {
        "adresse": "...",
        "auftraggeber": {...},
        "beschreibung": "...",
        "termine": {...},
        "anforderungen": [...],
        "geschaetzte_flaeche_m2": null
    }
    """
    
    async def extract_from_pdf(self, pdf_bytes: bytes) -> dict:
        """Extrahiert Daten aus PDF."""
        text = extract_text_from_pdf(pdf_bytes)
        return await self._analyze_with_claude(text)
    
    async def extract_from_image(self, image_bytes: bytes) -> dict:
        """Extrahiert Daten aus Foto (OCR + Analyse)."""
        return await claude_vision_api(
            image_bytes, 
            self.EXTRACTION_PROMPT
        )
```

---

## 3. Modul 2: Geodaten-Anreicherung

### 3.1 Automatische Datenanreicherung

Nach Eingabe der Adresse werden automatisch folgende Daten abgerufen:

```
┌─────────────────────────────────────────────────────────────┐
│  GEODATEN-ANREICHERUNG                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Adresse: Rathausgasse 2, 3011 Bern                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  🔄 Daten werden abgerufen...                       │    │
│  │                                                     │    │
│  │  ✅ swisstopo Geocoding         (0.2s)             │    │
│  │  ✅ GWR Gebäudedaten            (0.4s)             │    │
│  │  ✅ swissBUILDINGS3D Höhen      (0.3s)             │    │
│  │  ✅ geodienste.ch Polygon       (0.5s)             │    │
│  │  ✅ swissALTI3D Terrain         (0.2s)             │    │
│  │  🔄 Gebäuderecherche...         (läuft)            │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ERGEBNIS:                                                  │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  Gebäudename:     Kirche St. Peter und Paul                 │
│  Gebäudetyp:      Christkatholische Kathedralkirche         │
│  Baustil:         Neugotik                                  │
│  Baujahr:         1864                                      │
│  EGID:            191821074                                 │
│                                                             │
│  ┌─────────────────┬─────────────────┬─────────────────┐    │
│  │ Grundfläche     │ Traufhöhe       │ Firsthöhe       │    │
│  │ 1'099 m²        │ 46.4 m          │ 54.6 m          │    │
│  └─────────────────┴─────────────────┴─────────────────┘    │
│                                                             │
│  HÖHENZONEN (4 erkannt):                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Zone            │ Typ        │ Höhe    │ Gerüst     │    │
│  ├─────────────────┼────────────┼─────────┼────────────┤    │
│  │ Westturm        │ turm       │ 54.6m   │ Sonder     │    │
│  │ Kirchenschiff   │ hauptgeb.  │ 25.0m   │ Standard   │    │
│  │ Chor            │ anbau      │ 18.0m   │ Standard   │    │
│  │ Seitenschiffe   │ anbau      │ 12.0m   │ Standard   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ⚠️ Hinweis: Turm erfordert Sonderkonstruktion (>50m)       │
│                                                             │
│           [Daten übernehmen →]                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 API-Integration

```python
class GeoDataService:
    """Integration mit geodaten-ch API."""
    
    BASE_URL = "https://cooperative-commitment-production.up.railway.app"
    
    async def enrich_project(self, address: str) -> BuildingBundle:
        """
        Ruft alle verfügbaren Geodaten für eine Adresse ab.
        """
        response = await self.client.post(
            f"{self.BASE_URL}/api/v1/building/smart",
            json={"address": address}
        )
        return BuildingBundle(**response.json())
    
    async def get_svg_prompt(
        self, 
        egid: str, 
        view_direction: str = "W"
    ) -> str:
        """
        Generiert SVG-Prompt für spezifische Ansicht.
        """
        response = await self.client.get(
            f"{self.BASE_URL}/api/v1/building/{egid}/svg-prompt",
            params={"direction": view_direction}
        )
        return response.json()["prompt"]
```

---

## 4. Modul 3: Foto-Upload & Analyse

### 4.1 Foto-Erfassung vor Ort

```
┌─────────────────────────────────────────────────────────────┐
│  ← Zurück       FOTOS ERFASSEN        [3 Fotos]  [Weiter →] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PROJEKT: Kirche St. Peter und Paul                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                     │    │
│  │                    📷                               │    │
│  │                                                     │    │
│  │           Foto aufnehmen oder hochladen             │    │
│  │                                                     │    │
│  │    [Kamera]    [Galerie]    [Drohne importieren]   │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ERFASSTE FOTOS:                                            │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ 📷      │  │ 📷      │  │ 📷      │  │   +     │        │
│  │         │  │         │  │         │  │         │        │
│  │ [IMG 1] │  │ [IMG 2] │  │ [IMG 3] │  │  Mehr   │        │
│  ├─────────┤  ├─────────┤  ├─────────┤  │ hinzu-  │        │
│  │ West    │  │ Süd-West│  │ Süd     │  │ fügen   │        │
│  │ ✅ anal.│  │ ✅ anal.│  │ ✅ anal.│  │         │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  ANALYSE FOTO 1:                                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                                                     │    │
│  │  Blickrichtung: WEST (W)              Konfidenz: 95%│    │
│  │                                                     │    │
│  │  Erkannte Elemente:                                 │    │
│  │  ✓ Turm (frontal, zentral)                          │    │
│  │  ✓ Hauptportal                                      │    │
│  │  ✓ Strebebögen (links/rechts)                       │    │
│  │  ✓ Spitzbogenfenster                                │    │
│  │                                                     │    │
│  │  Geschätzte Fassadenfläche: ~850 m²                 │    │
│  │                                                     │    │
│  │  GPS: 46.9481° N, 7.4517° E                         │    │
│  │  Aufnahmezeit: 30.12.2025, 14:32                    │    │
│  │                                                     │    │
│  │  [Diese Ansicht für SVG verwenden]                  │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Foto-Analyse-Algorithmus

```python
class PhotoAnalyzer:
    """Analysiert Baustellenfotos für Blickrichtung und Elemente."""
    
    async def analyze_photo(
        self, 
        image_bytes: bytes,
        building_data: BuildingBundle
    ) -> PhotoAnalysis:
        """
        Analysiert ein Foto und bestimmt Blickrichtung.
        
        Kombiniert:
        1. EXIF GPS-Daten (falls vorhanden)
        2. Claude Vision Analyse
        3. Gebäudedaten-Abgleich
        """
        
        # 1. EXIF-Daten extrahieren
        exif = self._extract_exif(image_bytes)
        gps_direction = None
        
        if exif.get('gps_position'):
            # Berechne Richtung vom Fotografen zum Gebäude
            gps_direction = calculate_bearing(
                exif['gps_position'],
                (building_data.lv95_e, building_data.lv95_n)
            )
        
        # 2. Vision-Analyse
        vision_prompt = f"""
        Analysiere dieses Foto der {building_data.building_name}.
        
        Bekannte Gebäudedaten:
        - Turm-Position: Westen
        - Chor-Position: Osten  
        - Baustil: {building_data.architectural_style}
        - Höhenzonen: {[z['name'] for z in building_data.zones]}
        
        Bestimme:
        1. Blickrichtung (N, NO, O, SO, S, SW, W, NW)
        2. Sichtbare architektonische Elemente
        3. Sichtbare Fassaden/Zonen
        4. Geschätzte sichtbare Fassadenfläche
        5. Besondere Merkmale für Gerüstplanung (Vorsprünge, Balkone, etc.)
        
        Antworte im JSON-Format.
        """
        
        vision_result = await claude_vision_api(image_bytes, vision_prompt)
        
        # 3. Ergebnis kombinieren
        if gps_direction:
            # GPS hat Priorität, aber prüfe Konsistenz
            if self._directions_match(gps_direction, vision_result['direction']):
                confidence = 0.98
            else:
                # Warnung: GPS und Vision stimmen nicht überein
                confidence = 0.75
            direction = gps_direction
        else:
            direction = vision_result['direction']
            confidence = vision_result.get('confidence', 0.85)
        
        return PhotoAnalysis(
            direction=direction,
            confidence=confidence,
            detected_elements=vision_result['elements'],
            visible_zones=vision_result['zones'],
            estimated_area_m2=vision_result.get('area'),
            exif_data=exif,
            timestamp=datetime.now()
        )
    
    def _directions_match(self, d1: str, d2: str) -> bool:
        """Prüft ob zwei Richtungen kompatibel sind (±22.5°)."""
        directions = ['N', 'NO', 'O', 'SO', 'S', 'SW', 'W', 'NW']
        idx1 = directions.index(d1)
        idx2 = directions.index(d2)
        diff = abs(idx1 - idx2)
        return diff <= 1 or diff >= 7  # Nachbar-Richtungen ok
```

### 4.3 Multi-Foto-Erfassung

```python
class ProjectPhotoSet:
    """Verwaltet alle Fotos eines Projekts."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.photos: List[PhotoAnalysis] = []
    
    def get_coverage_map(self) -> dict:
        """
        Zeigt welche Fassaden bereits fotografiert wurden.
        
        Returns:
            {
                'N': {'covered': True, 'photos': [photo_1]},
                'O': {'covered': False, 'photos': []},
                'S': {'covered': True, 'photos': [photo_2, photo_3]},
                'W': {'covered': True, 'photos': [photo_4]},
            }
        """
        coverage = {d: {'covered': False, 'photos': []} for d in 
                   ['N', 'NO', 'O', 'SO', 'S', 'SW', 'W', 'NW']}
        
        for photo in self.photos:
            direction = photo.direction
            coverage[direction]['covered'] = True
            coverage[direction]['photos'].append(photo)
        
        return coverage
    
    def get_missing_directions(self) -> List[str]:
        """Gibt fehlende Fassaden-Fotos zurück."""
        coverage = self.get_coverage_map()
        return [d for d, v in coverage.items() 
                if not v['covered'] and d in ['N', 'O', 'S', 'W']]
```

---

## 5. Modul 4: Daten-Kontrolle & Ergänzung

### 5.1 Kontroll-Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  ← Zurück        DATEN PRÜFEN         [Speichern] [Weiter→] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PROJEKT: Gerüst Kirche St. Peter und Paul                  │
│  Status: ⚠️ Prüfung erforderlich                            │
│                                                             │
│  ═══════════════════════════════════════════════════════════│
│                                                             │
│  DATENQUELLEN-ÜBERSICHT:                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Quelle              │ Status │ Qualität │ Aktion   │    │
│  ├─────────────────────┼────────┼──────────┼──────────┤    │
│  │ Ausschreibung       │ ✅     │ ⭐⭐⭐⭐⭐ │ [Ansehen]│    │
│  │ swisstopo           │ ✅     │ ⭐⭐⭐⭐⭐ │ [Ansehen]│    │
│  │ GWR                 │ ✅     │ ⭐⭐⭐⭐   │ [Ansehen]│    │
│  │ swissBUILDINGS3D    │ ⚠️     │ ⭐⭐⭐     │ [Prüfen] │    │
│  │ Fotos vor Ort       │ ✅     │ ⭐⭐⭐⭐⭐ │ [Ansehen]│    │
│  │ Manuelle Ergänzung  │ ❌     │ —        │ [Eingeben]│   │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ═══════════════════════════════════════════════════════════│
│                                                             │
│  ⚠️ PRÜFPUNKTE:                                             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ⚠️ Höhendaten prüfen                                │    │
│  │                                                     │    │
│  │ swissBUILDINGS3D meldet: 46.4m Traufhöhe            │    │
│  │ Foto-Analyse schätzt:    ~55m (Turmspitze sichtbar) │    │
│  │                                                     │    │
│  │ → Die API misst nur die Dachtraufe, nicht den Turm  │    │
│  │                                                     │    │
│  │ Turm-Höhe manuell bestätigen:                       │    │
│  │ [54.6] m  ✅ Aus Zonendaten übernommen              │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ✅ Grundfläche plausibel                            │    │
│  │    GWR: 1'099 m² ≈ Polygon: 1'095 m²               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ⚠️ Fassadenfläche berechnen                         │    │
│  │                                                     │    │
│  │ Automatische Berechnung:                            │    │
│  │ • West (Turm):        8m × 55m = 440 m²            │    │
│  │ • West (Kirchenschiff): 20m × 25m = 500 m²         │    │
│  │ • Gesamt West:        ~940 m²                      │    │
│  │                                                     │    │
│  │ [Übernehmen] [Manuell anpassen]                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ═══════════════════════════════════════════════════════════│
│                                                             │
│  MANUELLE ERGÄNZUNGEN:                                      │
│                                                             │
│  Besondere Hindernisse:                                     │
│  [x] Strebebögen (erfordern Aussparungen)                   │
│  [ ] Balkone                                                │
│  [ ] Markisen                                               │
│  [x] Denkmalschutz (schonende Verankerung)                  │
│                                                             │
│  Zufahrt:                                                   │
│  [x] LKW-Zufahrt möglich (Rathausgasse)                     │
│  [ ] Kran erforderlich                                      │
│  [ ] Eingeschränkte Arbeitszeiten                           │
│                                                             │
│  Notizen:                                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Strebebögen an Westfassade beachten. Absprache mit │    │
│  │ Denkmalpflege erforderlich für Verankerung.        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Validierungslogik

```python
class DataValidator:
    """Validiert und prüft Projektdaten auf Konsistenz."""
    
    def validate_project(self, project: Project) -> ValidationResult:
        """
        Führt alle Validierungen durch.
        """
        issues = []
        
        # 1. Höhen-Konsistenz
        height_check = self._validate_heights(project)
        if not height_check.valid:
            issues.extend(height_check.issues)
        
        # 2. Flächen-Plausibilität
        area_check = self._validate_areas(project)
        if not area_check.valid:
            issues.extend(area_check.issues)
        
        # 3. Foto-Abdeckung
        photo_check = self._validate_photo_coverage(project)
        if not photo_check.valid:
            issues.extend(photo_check.issues)
        
        # 4. Pflichtfelder
        required_check = self._validate_required_fields(project)
        if not required_check.valid:
            issues.extend(required_check.issues)
        
        return ValidationResult(
            valid=len([i for i in issues if i.severity == 'error']) == 0,
            issues=issues,
            completeness=self._calculate_completeness(project)
        )
    
    def _validate_heights(self, project: Project) -> CheckResult:
        """Prüft Höhendaten auf Konsistenz."""
        issues = []
        
        # Vergleiche API-Höhen mit Zonen-Höhen
        api_first = project.building_data.firsthoehe_m
        max_zone = max(z.gebaeudehoehe_m for z in project.building_data.zones)
        
        if max_zone > api_first * 1.2:
            issues.append(ValidationIssue(
                field='zones',
                severity='warning',
                message=f'Zone-Höhe ({max_zone}m) > API-First ({api_first}m)',
                suggestion='Höchste Zone manuell prüfen'
            ))
        
        # Vergleiche mit Foto-Schätzung
        if project.photos:
            photo_estimate = max(p.estimated_height for p in project.photos 
                               if p.estimated_height)
            if photo_estimate and abs(photo_estimate - max_zone) > 5:
                issues.append(ValidationIssue(
                    field='height',
                    severity='info',
                    message=f'Foto-Schätzung ({photo_estimate}m) weicht ab',
                    suggestion='Vor-Ort-Messung empfohlen'
                ))
        
        return CheckResult(len(issues) == 0, issues)
```

---

## 6. Modul 5: Fassaden-Auswahl

### 6.1 Interaktive Fassaden-Auswahl

```
┌─────────────────────────────────────────────────────────────┐
│  ← Zurück       FASSADEN AUSWÄHLEN              [Weiter →]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Welche Fassaden sollen eingerüstet werden?                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                     GRUNDRISS                       │    │
│  │                                                     │    │
│  │                        N                            │    │
│  │                        ↑                            │    │
│  │                                                     │    │
│  │               ┌───────────────┐                     │    │
│  │               │ Seitenschiff  │ ← [N] ☐             │    │
│  │     ┌────┐    ├───────────────┤    ┌────────┐       │    │
│  │ [W] │Turm│    │  Kirchenschiff│    │  Chor  │ [O] ☐ │    │
│  │ ☑   │    │    │               │    │        │       │    │
│  │     └────┘    ├───────────────┤    └────────┘       │    │
│  │               │ Seitenschiff  │ ← [S] ☐             │    │
│  │               └───────────────┘                     │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  AUSGEWÄHLTE FASSADEN:                                      │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  ☑ WEST (Turm + Portal)                                     │
│    ├─ Zone: Westturm (54.6m) - Sonderkonstruktion          │
│    ├─ Zone: Hauptportal (25.0m) - Standard                 │
│    ├─ Fläche: ~940 m²                                      │
│    ├─ Foto: IMG_001.jpg ✅                                  │
│    └─ [Details bearbeiten]                                 │
│                                                             │
│  ☐ NORD                                                     │
│  ☐ OST                                                      │
│  ☐ SÜD                                                      │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  ZUSAMMENFASSUNG:                                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Ausgewählte Fassaden:    1                          │    │
│  │ Gesamtfläche:            ~940 m²                    │    │
│  │ Max. Höhe:               54.6 m                     │    │
│  │ Sonderkonstruktion:      Ja (Turm)                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  [Alle auswählen]  [Auswahl aufheben]                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Fassaden-Foto-Verknüpfung

```
┌─────────────────────────────────────────────────────────────┐
│  FASSADE WEST - Details                          [Schließen]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────────┐     │
│  │                      │  │ ZONEN:                   │     │
│  │   [FOTO WEST]        │  │                          │     │
│  │                      │  │ ☑ Westturm      54.6m    │     │
│  │   📷 IMG_001.jpg     │  │   Sonderkonstruktion     │     │
│  │                      │  │                          │     │
│  │   Blickrichtung: W   │  │ ☑ Hauptportal   25.0m    │     │
│  │   Konfidenz: 95%     │  │   Standard               │     │
│  │                      │  │                          │     │
│  └──────────────────────┘  │ ☐ Seitenschiff  12.0m    │     │
│                            │   (nicht sichtbar)       │     │
│  [Anderes Foto wählen]     │                          │     │
│  [Foto aufnehmen]          └──────────────────────────┘     │
│                                                             │
│  BESONDERHEITEN:                                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [x] Strebebögen - Aussparungen erforderlich         │    │
│  │ [x] Denkmalschutz - schonende Verankerung           │    │
│  │ [ ] Balkon/Erker                                    │    │
│  │ [ ] Markise/Sonnenschutz                            │    │
│  │ [+] Weitere Besonderheit hinzufügen                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  MASSE (aus Analyse + manuell):                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Breite Turm:       8.0 m    [Bearbeiten]            │    │
│  │ Höhe Turm:         54.6 m   [Bearbeiten]            │    │
│  │ Breite Portal:     20.0 m   [Bearbeiten]            │    │
│  │ Höhe Portal:       25.0 m   [Bearbeiten]            │    │
│  │ ─────────────────────────────────────────           │    │
│  │ Fassadenfläche:    940 m²   (berechnet)             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│           [SVG-Vorschau generieren]                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Modul 6: Gerüst-Editor

### 7.1 Interaktiver Gerüst-Editor

```
┌─────────────────────────────────────────────────────────────┐
│  ← Zurück          GERÜST-EDITOR               [Speichern]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────────────────────┐ ┌────────────────┐  │
│  │                                    │ │ WERKZEUGE:     │  │
│  │    [SVG FASSADENANSICHT WEST]      │ │                │  │
│  │                                    │ │ 🔧 Feld +/-    │  │
│  │         ┌───┐                      │ │ 📏 Lage +/-    │  │
│  │         │ T │  ← Turm              │ │ 🚪 Zugang      │  │
│  │         │ U │    54.6m             │ │ ⚓ Verankerung │  │
│  │         │ R │                      │ │ 📐 Konsole     │  │
│  │         │ M │                      │ │ 🔲 Aussparung  │  │
│  │    ┌────┴───┴────┐                 │ │                │  │
│  │    │  PORTAL     │                 │ │ ─────────────  │  │
│  │    │  25.0m      │                 │ │                │  │
│  │    │             │                 │ │ SYSTEM:        │  │
│  │    └─────────────┘                 │ │ Layher Blitz   │  │
│  │    ═══════════════  Terrain        │ │ W09 (0.73m)    │  │
│  │                                    │ │                │  │
│  │    [Zoom +] [Zoom -] [Fit]         │ │ [Ändern]       │  │
│  │                                    │ │                │  │
│  └────────────────────────────────────┘ └────────────────┘  │
│                                                             │
│  GERÜST-KONFIGURATION:                                      │
│  ═══════════════════════════════════════════════════════════│
│                                                             │
│  Zone: Westturm                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Felder:     4 × 2.57m = 10.28m (Bedarf: 8.0m) ✅    │    │
│  │ Lagen:      27 × 2.0m = 54.0m (Bedarf: 54.6m) ⚠️    │    │
│  │ Konsolen:   2 (oben für Spitze)                     │    │
│  │ Zugänge:    Z1 (Feld 2), Z2 (Feld 4)                │    │
│  │ Verank.:    36 Stk (4m-Raster)                      │    │
│  │                                                     │    │
│  │ [+ Lage hinzufügen] → 28 Lagen = 56.0m ✅           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Zone: Hauptportal                                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Felder:     8 × 2.57m = 20.56m (Bedarf: 20.0m) ✅   │    │
│  │ Lagen:      12 × 2.0m = 24.0m (Bedarf: 25.0m) ⚠️    │    │
│  │ Zugänge:    Z3 (Feld 4)                             │    │
│  │ Verank.:    24 Stk (4m-Raster)                      │    │
│  │                                                     │    │
│  │ [+ Lage hinzufügen] → 13 Lagen = 26.0m ✅           │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ⚠️ SONDERKONSTRUKTION:                                     │
│  Turm erfordert Sondermassnahmen (>50m). Statik prüfen!     │
│                                                             │
│  [Gerüst validieren]        [Weiter zu Materialliste →]     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Gerüst-Berechnungslogik

```python
class ScaffoldCalculator:
    """Berechnet Gerüstkonfiguration basierend auf Fassadendaten."""
    
    def __init__(self, system: ScaffoldSystem = ScaffoldSystem.LAYHER_BLITZ):
        self.system = system
        self.field_width = system.field_width  # 2.57m
        self.level_height = system.level_height  # 2.0m
        self.bay_width = system.bay_width  # W09 = 0.73m
    
    def calculate_for_zone(self, zone: Zone) -> ScaffoldConfig:
        """
        Berechnet Gerüstkonfiguration für eine Zone.
        """
        # Felder berechnen (aufrunden)
        fields = math.ceil(zone.width_m / self.field_width)
        actual_width = fields * self.field_width
        
        # Lagen berechnen (aufrunden + 1 für Arbeitsplatz)
        levels = math.ceil(zone.height_m / self.level_height) + 1
        actual_height = levels * self.level_height
        
        # Verankerungen (4m-Raster)
        anchors_h = math.ceil(actual_width / 4)
        anchors_v = math.ceil(actual_height / 4)
        total_anchors = anchors_h * anchors_v
        
        # Zugänge (mind. alle 40m, SUVA-konform)
        access_points = self._calculate_access_points(actual_width)
        
        return ScaffoldConfig(
            zone=zone,
            fields=fields,
            levels=levels,
            actual_width=actual_width,
            actual_height=actual_height,
            anchors=total_anchors,
            access_points=access_points,
            requires_special=zone.height_m > 50 or zone.sonderkonstruktion
        )
    
    def _calculate_access_points(self, width: float) -> List[AccessPoint]:
        """Berechnet Zugangspunkte gemäss SUVA."""
        points = []
        
        # Mindestens ein Zugang
        points.append(AccessPoint(position=width * 0.1))
        
        # Weitere alle 40m
        current = 40
        while current < width - 5:
            points.append(AccessPoint(position=current))
            current += 40
        
        return points
```

---

## 8. Modul 7: Material-Zusammenstellung

### 8.1 Automatische Materialliste

```
┌─────────────────────────────────────────────────────────────┐
│  ← Zurück         MATERIALLISTE               [Exportieren] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PROJEKT: Gerüst Kirche St. Peter und Paul                  │
│  System: Layher Blitz 70 | Breite: W09 (0.73m)              │
│                                                             │
│  ═══════════════════════════════════════════════════════════│
│                                                             │
│  ZUSAMMENFASSUNG:                                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Gerüstfläche:           1'940 m²                    │    │
│  │ Fassaden:               1 (West)                    │    │
│  │ Max. Höhe:              56.0 m                      │    │
│  │ Sonderkonstruktion:     Ja (Turm)                   │    │
│  │                                                     │    │
│  │ Geschätztes Gewicht:    ~45 t                       │    │
│  │ Geschätzte LKW-Fahrten: 3-4                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ═══════════════════════════════════════════════════════════│
│                                                             │
│  MATERIALLISTE:                                             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Artikel-Nr │ Bezeichnung          │ Menge │ Einheit │    │
│  ├────────────┼──────────────────────┼───────┼─────────┤    │
│  │ 5701.000   │ Vertikalrahmen 2.0m  │   440 │ Stk     │    │
│  │ 5702.000   │ Vertikalrahmen 1.0m  │    44 │ Stk     │    │
│  │ 5711.257   │ Geländerholm 2.57m   │   880 │ Stk     │    │
│  │ 5712.257   │ Diagonale 2.57m      │   440 │ Stk     │    │
│  │ 5720.257   │ Stahlbelag 2.57m     │   528 │ Stk     │    │
│  │ 5730.257   │ Bordbrett 2.57m      │   440 │ Stk     │    │
│  │ 5740.000   │ Fussplatte           │    48 │ Stk     │    │
│  │ 5750.000   │ Spindelstütze        │    48 │ Stk     │    │
│  │ 5760.000   │ Gerüstanker          │    60 │ Stk     │    │
│  │ 5770.000   │ Aufstiegsleiter      │    12 │ Stk     │    │
│  │ 5780.000   │ Konsole 0.73m        │    16 │ Stk     │    │
│  │ 5790.000   │ Schutzgitter         │   120 │ m²      │    │
│  │ ...        │ ...                  │   ... │ ...     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  [Vollständige Liste anzeigen (87 Positionen)]              │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  EXPORT-OPTIONEN:                                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [📄 Excel]  [📄 PDF]  [🔗 LayPLAN XML]             │    │
│  │                                                     │    │
│  │ [ ] Mit Preisen (aus Preisliste 2025)               │    │
│  │ [ ] Mit Gewichten                                   │    │
│  │ [ ] Gruppiert nach Zone                             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│           [Weiter zu Offerte →]                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Material-Berechnungslogik

```python
class MaterialCalculator:
    """Berechnet Materialbedarf aus Gerüstkonfiguration."""
    
    def __init__(self, catalog: MaterialCatalog):
        self.catalog = catalog
    
    def calculate_material_list(
        self, 
        config: ScaffoldConfig
    ) -> MaterialList:
        """
        Berechnet vollständige Materialliste.
        """
        items = []
        
        # Vertikalrahmen
        frames_per_field = config.levels * 2  # Links + Rechts
        total_frames = frames_per_field * (config.fields + 1)
        items.append(MaterialItem(
            article_nr="5701.000",
            name="Vertikalrahmen 2.0m",
            quantity=total_frames,
            unit="Stk"
        ))
        
        # Geländerholme (3 pro Feld: oben, mitte, unten)
        rails = config.fields * config.levels * 3
        items.append(MaterialItem(
            article_nr="5711.257",
            name="Geländerholm 2.57m",
            quantity=rails,
            unit="Stk"
        ))
        
        # Diagonalen (1 pro Feld)
        diagonals = config.fields * config.levels
        items.append(MaterialItem(
            article_nr="5712.257",
            name="Diagonale 2.57m",
            quantity=diagonals,
            unit="Stk"
        ))
        
        # Beläge (1.2 pro Feld für Überlappung)
        platforms = int(config.fields * config.levels * 1.2)
        items.append(MaterialItem(
            article_nr="5720.257",
            name="Stahlbelag 2.57m",
            quantity=platforms,
            unit="Stk"
        ))
        
        # ... weitere Positionen ...
        
        return MaterialList(
            project_id=config.project_id,
            items=items,
            total_weight_kg=self._calculate_weight(items),
            created_at=datetime.now()
        )
```

---

## 9. Modul 8: Export & Offerte

### 9.1 Export-Formate

```
┌─────────────────────────────────────────────────────────────┐
│  ← Zurück         EXPORT & OFFERTE            [Abschließen] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  PROJEKT: Gerüst Kirche St. Peter und Paul                  │
│  Status: ✅ Bereit für Export                               │
│                                                             │
│  ═══════════════════════════════════════════════════════════│
│                                                             │
│  DOKUMENTE ERSTELLEN:                                       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 📄 OFFERTE (PDF)                                    │    │
│  │                                                     │    │
│  │ Vorlage: [Standard ▼]                               │    │
│  │                                                     │    │
│  │ Inhalt:                                             │    │
│  │ [x] Deckblatt mit Projektdaten                      │    │
│  │ [x] Fassadenansicht (SVG)                           │    │
│  │ [x] Gerüstbeschreibung                              │    │
│  │ [x] Materialliste (zusammengefasst)                 │    │
│  │ [x] Preiskalkulation                                │    │
│  │ [ ] Detaillierte Stückliste                         │    │
│  │ [x] AGB                                             │    │
│  │                                                     │    │
│  │ [📄 Offerte generieren]                             │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 📐 CAD-EXPORT                                       │    │
│  │                                                     │    │
│  │ Format:                                             │    │
│  │ ( ) DXF (AutoCAD kompatibel)                        │    │
│  │ (•) IFC (Open BIM Standard)                         │    │
│  │ ( ) LayPLAN XML                                     │    │
│  │                                                     │    │
│  │ Inhalt:                                             │    │
│  │ [x] Gebäudekontur                                   │    │
│  │ [x] Gerüststruktur                                  │    │
│  │ [x] Verankerungspunkte                              │    │
│  │ [ ] Materialtabelle                                 │    │
│  │                                                     │    │
│  │ [📐 CAD-Export generieren]                          │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 📊 WEITERE EXPORTE                                  │    │
│  │                                                     │    │
│  │ [📊 Excel Materialliste]                            │    │
│  │ [📷 Fotos-Paket (ZIP)]                              │    │
│  │ [📋 Montage-Checkliste]                             │    │
│  │ [📑 Statik-Unterlagen (wenn vorhanden)]             │    │
│  │                                                     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ═══════════════════════════════════════════════════════════│
│                                                             │
│  GENERIERTE DOKUMENTE:                                      │
│                                                             │
│  ✅ Offerte_StPeterPaul_2025-001.pdf     [⬇️] [📧] [🖨️]   │
│  ✅ Fassade_West_SVG.svg                  [⬇️] [📧]        │
│  ✅ Export_IFC.ifc                        [⬇️]             │
│  ✅ Materialliste.xlsx                    [⬇️] [📧]        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 IFC-Export

```python
class IFCExporter:
    """Exportiert Gerüstplanung in IFC-Format (Open BIM)."""
    
    def export_scaffold(
        self, 
        project: Project,
        scaffold: ScaffoldConfig
    ) -> bytes:
        """
        Erstellt IFC-Datei mit Gebäude und Gerüst.
        """
        import ifcopenshell
        
        # Neues IFC-Modell
        ifc = ifcopenshell.file(schema="IFC4")
        
        # Projekt-Kontext
        project_ifc = ifc.createIfcProject(
            ifcopenshell.guid.new(),
            Name=project.name
        )
        
        # Site
        site = ifc.createIfcSite(
            ifcopenshell.guid.new(),
            Name=project.address,
            RefLatitude=self._to_ifc_coords(project.lat),
            RefLongitude=self._to_ifc_coords(project.lon)
        )
        
        # Gebäude
        building = ifc.createIfcBuilding(
            ifcopenshell.guid.new(),
            Name=project.building_data.building_name
        )
        
        # Gerüst als IfcElementAssembly
        scaffold_assembly = ifc.createIfcElementAssembly(
            ifcopenshell.guid.new(),
            Name=f"Gerüst {project.name}",
            AssemblyPlace="SITE",
            PredefinedType="ACCESSORY_ASSEMBLY"
        )
        
        # Einzelne Gerüstelemente
        for level in range(scaffold.levels):
            for field in range(scaffold.fields):
                # Vertikalrahmen
                frame = self._create_frame(ifc, level, field, scaffold)
                
                # Belag
                platform = self._create_platform(ifc, level, field, scaffold)
                
                # Zur Assembly hinzufügen
                ifc.createIfcRelAggregates(
                    ifcopenshell.guid.new(),
                    RelatingObject=scaffold_assembly,
                    RelatedObjects=[frame, platform]
                )
        
        # Verankerungen
        for anchor in scaffold.anchors:
            anchor_elem = self._create_anchor(ifc, anchor)
            # ...
        
        return ifc.to_string().encode()
```

### 9.3 LayPLAN XML Export

```python
class LayPLANExporter:
    """Exportiert Gerüstplanung in LayPLAN XML-Format."""
    
    def export(self, scaffold: ScaffoldConfig) -> str:
        """
        Erstellt LayPLAN-kompatible XML.
        """
        root = ET.Element("LayPLAN_Project")
        root.set("version", "3.0")
        
        # Projektinfo
        project_elem = ET.SubElement(root, "Project")
        ET.SubElement(project_elem, "Name").text = scaffold.project_name
        ET.SubElement(project_elem, "System").text = "Layher_Blitz_70"
        
        # Gerüststruktur
        structure = ET.SubElement(root, "Structure")
        
        for zone in scaffold.zones:
            zone_elem = ET.SubElement(structure, "Zone")
            zone_elem.set("name", zone.name)
            
            # Felder
            fields_elem = ET.SubElement(zone_elem, "Fields")
            for i, field in enumerate(zone.fields):
                field_elem = ET.SubElement(fields_elem, "Field")
                field_elem.set("index", str(i))
                field_elem.set("width", str(field.width))
                field_elem.set("levels", str(field.levels))
            
            # Verankerungen
            anchors_elem = ET.SubElement(zone_elem, "Anchors")
            for anchor in zone.anchors:
                anchor_elem = ET.SubElement(anchors_elem, "Anchor")
                anchor_elem.set("x", str(anchor.x))
                anchor_elem.set("y", str(anchor.y))
                anchor_elem.set("type", anchor.type)
        
        # Materialliste
        materials = ET.SubElement(root, "MaterialList")
        for item in scaffold.material_list.items:
            mat_elem = ET.SubElement(materials, "Item")
            mat_elem.set("article_nr", item.article_nr)
            mat_elem.set("quantity", str(item.quantity))
        
        return ET.tostring(root, encoding="unicode", xml_declaration=True)
```

---

## 10. Technische Architektur

### 10.1 System-Architektur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GERÜSTBAU-APP                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                               FRONTEND                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Web App    │  │  Mobile iOS  │  │Mobile Android│  │   Desktop    │    │
│  │   (React)    │  │   (Swift)    │  │   (Kotlin)   │  │  (Electron)  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ REST API / GraphQL
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API GATEWAY                                      │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Authentication │ Rate Limiting │ Request Routing │ Caching          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  PROJECT SERVICE │  │  GEODATA SERVICE │  │    AI SERVICE    │
│                  │  │                  │  │                  │
│  • CRUD Projekte │  │  • swisstopo API │  │  • Claude Vision │
│  • Status-Mgmt   │  │  • GWR API       │  │  • OCR           │
│  • Validierung   │  │  • geodienste.ch │  │  • SVG-Generier. │
│                  │  │  • Caching       │  │  • Analyse       │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATENBANK-LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  PostgreSQL  │  │    Redis     │  │     S3       │  │  Elasticsearch│   │
│  │  (Projekte)  │  │   (Cache)    │  │   (Fotos)    │  │   (Suche)    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXTERNE SERVICES                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  geodaten-ch │  │  Claude API  │  │   simap.ch   │  │   E-Mail     │    │
│  │     API      │  │   (Anthrop.) │  │ (Ausschreib.)│  │   Service    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Tech Stack

| Komponente | Technologie | Begründung |
|------------|-------------|------------|
| **Frontend Web** | React + TypeScript | Komponenten-basiert, typsicher |
| **Frontend Mobile** | React Native | Code-Sharing mit Web |
| **Backend API** | FastAPI (Python) | Async, schnell, auto-docs |
| **Datenbank** | PostgreSQL + PostGIS | Geo-Daten-Support |
| **Cache** | Redis | Schneller Geodaten-Cache |
| **File Storage** | S3 / MinIO | Skalierbare Foto-Speicherung |
| **AI/ML** | Claude API | Vision + Text-Analyse |
| **CAD-Export** | ifcopenshell, ezdxf | IFC + DXF Generierung |

---

## 11. API-Spezifikationen

### 11.1 Projekt-Endpoints

```yaml
openapi: 3.0.0
info:
  title: Gerüstbau-App API
  version: 1.0.0

paths:
  /api/v1/projects:
    get:
      summary: Liste aller Projekte
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: [draft, captured, enriched, reviewed, planned, quoted, commissioned]
      responses:
        200:
          description: Projekt-Liste
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/ProjectSummary'
    
    post:
      summary: Neues Projekt erstellen
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                name:
                  type: string
                address:
                  type: string
                tender_document:
                  type: string
                  format: binary
      responses:
        201:
          description: Projekt erstellt
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Project'

  /api/v1/projects/{id}/photos:
    post:
      summary: Foto hochladen und analysieren
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                photo:
                  type: string
                  format: binary
                analyze:
                  type: boolean
                  default: true
      responses:
        201:
          description: Foto hochgeladen
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PhotoAnalysis'

  /api/v1/projects/{id}/scaffold:
    get:
      summary: Aktuelle Gerüstkonfiguration
    put:
      summary: Gerüstkonfiguration aktualisieren
    
  /api/v1/projects/{id}/export:
    post:
      summary: Export generieren
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                format:
                  type: string
                  enum: [pdf_quote, ifc, dxf, layplan_xml, excel]
                options:
                  type: object
      responses:
        200:
          description: Export-Datei
          content:
            application/octet-stream:
              schema:
                type: string
                format: binary
```

### 11.2 Geodaten-Integration

```yaml
  /api/v1/geodata/enrich:
    post:
      summary: Adresse mit Geodaten anreichern
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required:
                - address
              properties:
                address:
                  type: string
                  example: "Rathausgasse 2, 3011 Bern"
      responses:
        200:
          description: Angereicherte Gebäudedaten
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BuildingBundle'

  /api/v1/geodata/svg-prompt:
    post:
      summary: SVG-Prompt für Ansicht generieren
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                egid:
                  type: string
                direction:
                  type: string
                  enum: [N, NO, O, SO, S, SW, W, NW]
                include_scaffold:
                  type: boolean
      responses:
        200:
          description: SVG-Generierungs-Prompt
```

---

## 12. Datenmodell

### 12.1 Entity-Relationship-Diagramm

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    PROJECT      │       │  BUILDING_DATA  │       │      ZONE       │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id              │───────│ project_id      │───────│ building_id     │
│ name            │       │ egid            │       │ name            │
│ status          │       │ address         │       │ zone_type       │
│ address         │       │ building_name   │       │ height_m        │
│ client_id       │       │ building_type   │       │ width_m         │
│ deadline        │       │ style           │       │ area_m2         │
│ created_at      │       │ year_built      │       │ requires_special│
│ updated_at      │       │ polygon         │       └─────────────────┘
└─────────────────┘       │ traufhoehe_m    │
        │                 │ firsthoehe_m    │
        │                 │ terrain_height  │
        │                 └─────────────────┘
        │
        │       ┌─────────────────┐       ┌─────────────────┐
        │       │     PHOTO       │       │  PHOTO_ANALYSIS │
        │       ├─────────────────┤       ├─────────────────┤
        └───────│ project_id      │───────│ photo_id        │
                │ file_path       │       │ direction       │
                │ taken_at        │       │ confidence      │
                │ gps_lat         │       │ detected_elems  │
                │ gps_lon         │       │ visible_zones   │
                │ exif_data       │       │ estimated_area  │
                └─────────────────┘       └─────────────────┘

        │       ┌─────────────────┐       ┌─────────────────┐
        │       │    SCAFFOLD     │       │ SCAFFOLD_ZONE   │
        │       ├─────────────────┤       ├─────────────────┤
        └───────│ project_id      │───────│ scaffold_id     │
                │ system_type     │       │ zone_id         │
                │ total_area_m2   │       │ fields          │
                │ max_height_m    │       │ levels          │
                │ requires_special│       │ access_points   │
                │ status          │       │ anchors         │
                └─────────────────┘       └─────────────────┘

        │       ┌─────────────────┐       ┌─────────────────┐
        │       │ MATERIAL_LIST   │       │  MATERIAL_ITEM  │
        │       ├─────────────────┤       ├─────────────────┤
        └───────│ project_id      │───────│ list_id         │
                │ scaffold_id     │       │ article_nr      │
                │ total_weight_kg │       │ name            │
                │ created_at      │       │ quantity        │
                └─────────────────┘       │ unit            │
                                          │ weight_kg       │
                                          └─────────────────┘

        │       ┌─────────────────┐
        │       │     EXPORT      │
        │       ├─────────────────┤
        └───────│ project_id      │
                │ format          │
                │ file_path       │
                │ created_at      │
                │ created_by      │
                └─────────────────┘
```

### 12.2 Projekt-Status-Enum

```python
class ProjectStatus(Enum):
    DRAFT = "draft"              # Entwurf, noch nicht vollständig
    CAPTURED = "captured"        # Ausschreibung erfasst
    ENRICHED = "enriched"        # Geodaten abgerufen
    REVIEWED = "reviewed"        # Daten geprüft und ergänzt
    PLANNED = "planned"          # Gerüst konfiguriert
    QUOTED = "quoted"            # Offerte erstellt
    COMMISSIONED = "commissioned" # Auftrag erteilt
    IN_PROGRESS = "in_progress"  # In Ausführung
    COMPLETED = "completed"      # Abgeschlossen
    CANCELLED = "cancelled"      # Storniert
```

---

## Anhang A: Glossar

| Begriff | Bedeutung |
|---------|-----------|
| **EGID** | Eidgenössischer Gebäudeidentifikator |
| **GWR** | Gebäude- und Wohnungsregister |
| **IFC** | Industry Foundation Classes (BIM-Standard) |
| **Lage** | Horizontale Ebene eines Gerüsts (2.0m Höhe) |
| **Feld** | Vertikaler Abschnitt eines Gerüsts (2.57m Breite) |
| **SUVA** | Schweizerische Unfallversicherungsanstalt |
| **Traufhöhe** | Höhe der Dachtraufe |
| **Firsthöhe** | Höhe des Dachfirsts |

---

## Anhang B: Nächste Schritte

### Phase 1 (MVP) - Q1 2025
- [ ] Basis-Projekterfassung
- [ ] geodaten-ch Integration
- [ ] Foto-Upload mit manueller Richtungszuweisung
- [ ] Einfache Materialliste
- [ ] PDF-Offerte-Export

### Phase 2 - Q2 2025
- [ ] KI-basierte Foto-Analyse
- [ ] Interaktiver Gerüst-Editor
- [ ] IFC-Export
- [ ] Mobile App (iOS/Android)

### Phase 3 - Q3 2025
- [ ] simap.ch Integration
- [ ] LayPLAN-Export
- [ ] Erweiterte Statistiken
- [ ] Multi-Mandanten-Fähigkeit

---

*Dokument erstellt: 30.12.2025*
*Version: 1.0*
*Autor: geodaten-ch Projekt*

---

# ANHANG: Prompt-Anpassungen für richtungsspezifische SVG-Generierung

## Konzept: Ansichts-Parameter im Prompt

Um SVGs aus einer spezifischen Blickrichtung zu generieren, muss der Prompt um folgende Abschnitte erweitert werden:

### Neue Prompt-Sektion: ANSICHT-SPEZIFIKATION

```markdown
## ANSICHT-SPEZIFIKATION

### Gewählte Ansicht: [RICHTUNG]
- **Blickrichtung:** Betrachter steht im [RICHTUNG], schaut nach [GEGENRICHTUNG]
- **Hauptelemente sichtbar:** [Liste der sichtbaren Elemente]

### Verdeckungslogik
[Diagramm welche Elemente vorne/hinten sind]

**SICHTBAR:**
1. [Element 1]
2. [Element 2]

**VERDECKT (nicht zeichnen!):**
1. [Element 3]
2. [Element 4]
```

### Richtungs-Mapping

| Richtung | Betrachter steht | Schaut nach | Typisch sichtbar |
|----------|-----------------|-------------|------------------|
| N | Norden | Süden | Südfassade, Südliche Anbauten |
| O | Osten | Westen | Westfassade, Chor (bei Kirchen) |
| S | Süden | Norden | Nordfassade, Nördliche Anbauten |
| W | Westen | Osten | Ostfassade, Turm (bei Kirchen) |
| NO | Nordosten | Südwesten | SW-Ecke, 2 Fassaden |
| SO | Südosten | Nordwesten | NW-Ecke, 2 Fassaden |
| SW | Südwesten | Nordosten | NO-Ecke, 2 Fassaden |
| NW | Nordwesten | Südosten | SO-Ecke, 2 Fassaden |

### Implementierung im Backend

```python
def generate_direction_specific_prompt(
    building_data: BuildingBundle,
    direction: str,
    photo_analysis: Optional[PhotoAnalysis] = None
) -> str:
    """
    Generiert einen richtungsspezifischen SVG-Prompt.
    
    Args:
        building_data: Gebäudedaten aus geodaten-ch API
        direction: Blickrichtung (N, NO, O, SO, S, SW, W, NW)
        photo_analysis: Optional - Analyse des Vor-Ort-Fotos
    
    Returns:
        Vollständiger Prompt für SVG-Generierung
    """
    
    # Basis-Prompt laden
    base_prompt = load_base_prompt(building_data)
    
    # Richtungsspezifische Sektion generieren
    direction_section = generate_direction_section(
        building_data=building_data,
        direction=direction,
        photo_analysis=photo_analysis
    )
    
    # Verdeckungslogik für diese Richtung
    visibility = calculate_visibility(
        zones=building_data.zones,
        polygon=building_data.polygon,
        direction=direction
    )
    
    # Sichtbare Elemente für SVG
    visible_elements = format_visible_elements(visibility)
    
    # Prompt zusammensetzen
    full_prompt = f"""
{base_prompt}

## 2. ANSICHT-SPEZIFIKATION

### Gewählte Ansicht: {direction} ({DIRECTION_NAMES[direction]})
- **Blickrichtung:** Betrachter steht im {direction}, schaut nach {OPPOSITE_DIRECTION[direction]}
{f"- **Foto-Referenz:** Basierend auf Vor-Ort-Foto, Konfidenz {photo_analysis.confidence:.0%}" if photo_analysis else ""}

### Sichtbare Elemente
{visible_elements['visible']}

### Verdeckte Elemente (NICHT ZEICHNEN!)
{visible_elements['hidden']}

### Zeichenreihenfolge (hinten nach vorne)
{visible_elements['draw_order']}

{generate_svg_layout_for_direction(direction, building_data)}
"""
    
    return full_prompt


def calculate_visibility(
    zones: List[Zone],
    polygon: List[Tuple[float, float]],
    direction: str
) -> dict:
    """
    Berechnet welche Gebäudeteile aus einer Richtung sichtbar sind.
    
    Verwendet vereinfachte 2.5D-Logik:
    - Sortiert Zonen nach Entfernung zum Betrachter
    - Prüft Überlappungen in der Projektion
    """
    
    # Richtungsvektor
    dir_vector = DIRECTION_VECTORS[direction]
    
    # Zonen nach Entfernung sortieren (näher = später zeichnen)
    sorted_zones = sorted(
        zones,
        key=lambda z: dot_product(z.centroid, dir_vector),
        reverse=True  # Weiter weg zuerst
    )
    
    visible = []
    hidden = []
    draw_order = []
    
    for zone in sorted_zones:
        # Projizierte Bounding Box berechnen
        projected_bbox = project_zone(zone, direction)
        
        # Prüfen ob von bereits sichtbaren Zonen verdeckt
        is_hidden = False
        for visible_zone in visible:
            if is_occluded(projected_bbox, visible_zone.projected_bbox):
                is_hidden = True
                break
        
        if is_hidden:
            hidden.append(zone)
        else:
            visible.append(zone)
            draw_order.append(zone.name)
    
    return {
        'visible': visible,
        'hidden': hidden,
        'draw_order': list(reversed(draw_order))  # Hinten zuerst
    }
```

### Beispiel: Kirche St. Peter und Paul

#### Ansicht WEST (wie im Foto)
```markdown
## ANSICHT-SPEZIFIKATION

### Gewählte Ansicht: WEST (W)
- **Blickrichtung:** Betrachter steht im Westen, schaut nach Osten
- **Foto-Referenz:** Basierend auf Vor-Ort-Foto, Konfidenz 95%

### Sichtbare Elemente
1. ✅ Westturm (54.6m) - FRONTAL, DOMINANT
2. ✅ Hauptportal (12m) - Unter dem Turm
3. ✅ Strebebögen - Links und rechts vom Turm
4. ⚠️ Seitenschiffe (12m) - Teilweise sichtbar, seitlich

### Verdeckte Elemente (NICHT ZEICHNEN!)
1. ❌ Kirchenschiff (25m) - Hinter Turm verdeckt
2. ❌ Chor (18m) - Ganz hinten, nicht sichtbar

### Zeichenreihenfolge (hinten nach vorne)
1. Seitenschiffe (zuerst, im Hintergrund)
2. Strebebögen
3. Westturm (zuletzt, im Vordergrund)
```

#### Ansicht SÜD (alternatives Beispiel)
```markdown
## ANSICHT-SPEZIFIKATION

### Gewählte Ansicht: SÜD (S)
- **Blickrichtung:** Betrachter steht im Süden, schaut nach Norden

### Sichtbare Elemente
1. ✅ Südliches Seitenschiff (12m) - FRONTAL
2. ✅ Kirchenschiff-Dach (25m) - Dahinter sichtbar
3. ✅ Westturm (54.6m) - Links im Bild, teilweise
4. ✅ Rosettenfenster - Im Querhaus

### Verdeckte Elemente (NICHT ZEICHNEN!)
1. ❌ Nördliches Seitenschiff - Hinter Kirchenschiff
2. ❌ Hauptportal - Auf Westseite

### Zeichenreihenfolge (hinten nach vorne)
1. Kirchenschiff (Dach sichtbar)
2. Westturm (links, teilweise)
3. Südliches Seitenschiff (frontal)
```
