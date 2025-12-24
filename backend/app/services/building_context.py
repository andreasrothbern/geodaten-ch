"""
Building Context Service

Verwaltet Gebäude-Kontexte mit Höhenzonen für komplexe Gebäude.
Integriert Claude AI für die Analyse komplexer Strukturen.

Siehe: docs/poc_bundeshaus_mvp/BUILDING_CONTEXT.md
"""

import json
import math
import sqlite3
import os
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

from app.models.building_context import (
    BuildingContext, BuildingZone, ZoneType,
    ComplexityLevel, ContextSource
)
from app.services.access_calculator import calculate_access_points

logger = logging.getLogger(__name__)

# Datenbank-Pfad (Railway Volume oder lokal)
DATA_DIR = Path(os.getenv("DATA_DIR", "app/data"))
DB_PATH = DATA_DIR / "building_contexts.db"


class BuildingContextService:
    """Service für Gebäude-Kontext-Management"""

    # Komplexe Gebäudekategorien (GWR gkat)
    COMPLEX_CATEGORIES = [
        1040,  # Gebäude mit Nebennutzung
        1060,  # Gebäude für Bildung/Kultur
        1080,  # Gebäude für Gesundheit
        1110,  # Kirchen und religiöse Gebäude
        1130,  # Museen, Bibliotheken
        1212,  # Industrie
    ]

    def __init__(self):
        self._ensure_db()

    def _ensure_db(self):
        """Erstellt die Datenbank und Tabellen falls nicht vorhanden"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS building_contexts (
                egid TEXT PRIMARY KEY,
                adresse TEXT,
                context_json TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'auto',
                complexity TEXT NOT NULL DEFAULT 'simple',
                confidence REAL NOT NULL DEFAULT 1.0,
                validated INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Index für schnelle Suche
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_contexts_source
            ON building_contexts(source)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_contexts_complexity
            ON building_contexts(complexity)
        """)

        conn.commit()
        conn.close()
        logger.info(f"Building contexts DB initialized at {DB_PATH}")

    def get_context(self, egid: str) -> Optional[BuildingContext]:
        """Lädt einen Kontext aus der Datenbank"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute(
            "SELECT context_json FROM building_contexts WHERE egid = ?",
            (egid,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            try:
                data = json.loads(row[0])
                return BuildingContext(**data)
            except Exception as e:
                logger.error(f"Error parsing context for {egid}: {e}")
                return None
        return None

    def save_context(self, context: BuildingContext) -> bool:
        """Speichert einen Kontext in der Datenbank"""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()

            context.updated_at = datetime.utcnow()
            context_json = context.model_dump_json()

            cursor.execute("""
                INSERT OR REPLACE INTO building_contexts
                (egid, adresse, context_json, source, complexity, confidence, validated, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                context.egid,
                context.adresse,
                context_json,
                context.source.value,
                context.complexity.value,
                context.confidence,
                1 if context.validated_by_user else 0,
                context.created_at.isoformat(),
                context.updated_at.isoformat()
            ))

            conn.commit()
            conn.close()
            logger.info(f"Saved context for EGID {context.egid}")
            return True

        except Exception as e:
            logger.error(f"Error saving context for {context.egid}: {e}")
            return False

    def delete_context(self, egid: str) -> bool:
        """Löscht einen Kontext"""
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM building_contexts WHERE egid = ?", (egid,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            logger.error(f"Error deleting context for {egid}: {e}")
            return False

    def detect_complexity(
        self,
        polygon: list[dict],
        gwr_data: Optional[dict] = None,
        area_m2: Optional[float] = None
    ) -> ComplexityLevel:
        """
        Erkennt die Komplexität eines Gebäudes.

        Kriterien für "komplex":
        - Polygon hat >12 Ecken
        - Grundfläche >1000m²
        - Gebäudekategorie ist speziell (Kirche, öffentlich)
        - Hat konkave Abschnitte (Einbuchtungen)
        """
        num_vertices = len(polygon)

        # Fläche berechnen falls nicht angegeben
        if area_m2 is None:
            area_m2 = self._calculate_polygon_area(polygon)

        # Bounding Box berechnen
        if polygon:
            xs = [p.get('x', p.get('e', p[0] if isinstance(p, (list, tuple)) else 0)) for p in polygon]
            ys = [p.get('y', p.get('n', p[1] if isinstance(p, (list, tuple)) else 0)) for p in polygon]
            bbox_width = max(xs) - min(xs) if xs else 0
            bbox_height = max(ys) - min(ys) if ys else 0
            aspect_ratio = bbox_width / bbox_height if bbox_height > 0 else 1
        else:
            aspect_ratio = 1

        # Kategorie prüfen
        gkat = gwr_data.get('gkat') if gwr_data else None
        is_complex_category = gkat in self.COMPLEX_CATEGORIES if gkat else False

        # Konkave Abschnitte prüfen
        has_concave = self._has_concave_sections(polygon) if polygon else False

        # Entscheidungslogik
        is_simple = (
            num_vertices <= 6 and
            (area_m2 or 0) < 300 and
            0.3 < aspect_ratio < 3.0 and
            not is_complex_category and
            not has_concave
        )

        is_complex = (
            num_vertices > 12 or
            (area_m2 or 0) > 1000 or
            is_complex_category or
            has_concave
        )

        if is_simple:
            return ComplexityLevel.SIMPLE
        elif is_complex:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.MODERATE

    def create_auto_context(
        self,
        egid: str,
        adresse: Optional[str],
        polygon: list[dict],
        height_data: dict,
        gwr_data: Optional[dict] = None
    ) -> BuildingContext:
        """
        Erstellt automatisch einen einfachen Kontext für ein Gebäude.
        Verwendet für einfache Gebäude ohne Claude-Analyse.
        """
        # Fassaden aus Polygon ableiten
        fassaden = self._extract_fassaden(polygon)
        fassaden_ids = [f['richtung'] for f in fassaden]

        # Höhen extrahieren
        traufhoehe = height_data.get('traufhoehe_m')
        firsthoehe = height_data.get('firsthoehe_m')
        gebaeudehoehe = height_data.get('gebaeudehoehe_m') or traufhoehe or 8.0

        # Eine Zone für das gesamte Gebäude
        zone = BuildingZone(
            id="zone_1",
            name="Hauptgebäude",
            type=ZoneType.HAUPTGEBAEUDE,
            polygon_point_indices=list(range(len(polygon))),
            traufhoehe_m=traufhoehe,
            firsthoehe_m=firsthoehe,
            gebaeudehoehe_m=gebaeudehoehe,
            fassaden_ids=fassaden_ids,
            beruesten=True,
            sonderkonstruktion=False,
            confidence=1.0
        )

        # Komplexität bestimmen
        area_m2 = gwr_data.get('garea') if gwr_data else None
        complexity = self.detect_complexity(polygon, gwr_data, area_m2)

        # Zugänge automatisch berechnen
        zugaenge = []
        zugaenge_hinweise = []
        try:
            # Fassaden für access_calculator formatieren
            access_fassaden = [
                {'id': f['richtung'], 'laenge_m': f['laenge']}
                for f in fassaden
            ]
            access_result = calculate_access_points(access_fassaden)
            zugaenge = [
                {
                    'id': z.id,
                    'fassade_id': z.fassade_id,
                    'position_percent': z.position_percent,
                    'grund': z.grund or 'Automatisch berechnet'
                }
                for z in access_result.zugaenge
            ]
            if not access_result.suva_konform:
                zugaenge_hinweise.append(
                    f"Fluchtweg {access_result.max_fluchtweg_m:.1f}m > 50m (SUVA)"
                )
        except Exception as e:
            logger.warning(f"Access calculation failed: {e}")

        context = BuildingContext(
            egid=egid,
            adresse=adresse,
            zones=[zone],
            complexity=complexity,
            has_height_variations=False,
            has_setbacks=False,
            has_towers=False,
            has_annexes=False,
            has_special_features=False,
            zugaenge=zugaenge,
            zugaenge_hinweise=zugaenge_hinweise,
            source=ContextSource.AUTO,
            confidence=1.0,
            validated_by_user=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        return context

    async def analyze_with_claude(
        self,
        egid: str,
        adresse: Optional[str],
        polygon: list[dict],
        height_data: dict,
        gwr_data: Optional[dict] = None,
        include_orthofoto: bool = False
    ) -> BuildingContext:
        """
        Analysiert ein komplexes Gebäude mit Claude AI.

        Sendet Polygon, Höhen und Metadaten an Claude und erhält
        eine strukturierte Zonen-Analyse zurück.
        """
        import anthropic

        # Polygon-Eigenschaften berechnen
        num_vertices = len(polygon)
        area_m2 = self._calculate_polygon_area(polygon)
        perimeter_m = self._calculate_perimeter(polygon)

        # Bounding Box
        xs = [p.get('x', p.get('e', p[0] if isinstance(p, (list, tuple)) else 0)) for p in polygon]
        ys = [p.get('y', p.get('n', p[1] if isinstance(p, (list, tuple)) else 0)) for p in polygon]
        bbox_width = max(xs) - min(xs) if xs else 0
        bbox_height = max(ys) - min(ys) if ys else 0

        # Prompt erstellen
        prompt = self._create_analysis_prompt(
            polygon=polygon,
            num_vertices=num_vertices,
            area_m2=area_m2,
            perimeter_m=perimeter_m,
            bbox_width=bbox_width,
            bbox_height=bbox_height,
            height_data=height_data,
            gwr_data=gwr_data,
            egid=egid,
            adresse=adresse
        )

        # Claude API aufrufen
        try:
            client = anthropic.Anthropic()

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # JSON aus Response extrahieren
            context = self._parse_claude_response(
                response_text,
                egid=egid,
                adresse=adresse
            )

            return context

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            # Fallback auf Auto-Context
            return self.create_auto_context(
                egid, adresse, polygon, height_data, gwr_data
            )

    def _create_analysis_prompt(
        self,
        polygon: list[dict],
        num_vertices: int,
        area_m2: float,
        perimeter_m: float,
        bbox_width: float,
        bbox_height: float,
        height_data: dict,
        gwr_data: Optional[dict],
        egid: str,
        adresse: Optional[str]
    ) -> str:
        """Erstellt den Analyse-Prompt für Claude"""

        # Polygon als JSON formatieren
        polygon_json = json.dumps(polygon, indent=2)

        # GWR-Daten extrahieren
        gkat = gwr_data.get('gkat', 'unbekannt') if gwr_data else 'unbekannt'
        gkat_text = self._get_gkat_text(gkat) if gkat != 'unbekannt' else 'unbekannt'
        gastw = gwr_data.get('gastw', 'unbekannt') if gwr_data else 'unbekannt'
        gbauj = gwr_data.get('gbauj', 'unbekannt') if gwr_data else 'unbekannt'
        garea = gwr_data.get('garea', 'unbekannt') if gwr_data else 'unbekannt'

        # Höhendaten
        traufhoehe = height_data.get('traufhoehe_m', 'nicht verfügbar')
        firsthoehe = height_data.get('firsthoehe_m', 'nicht verfügbar')
        gebaeudehoehe = height_data.get('gebaeudehoehe_m', 'nicht verfügbar')

        return f"""Du analysierst ein Schweizer Gebäude für die Gerüstplanung.

## Eingabedaten

### Grundriss-Polygon (LV95 Koordinaten)
```json
{polygon_json}
```

### Polygon-Eigenschaften
- Anzahl Ecken: {num_vertices}
- Grundfläche: {area_m2:.1f} m²
- Umfang: {perimeter_m:.1f} m
- Bounding Box: {bbox_width:.1f}m × {bbox_height:.1f}m

### Verfügbare Höhendaten
- Globale Traufhöhe: {traufhoehe} m (swissBUILDINGS3D)
- Globale Firsthöhe: {firsthoehe} m
- Globale Gebäudehöhe: {gebaeudehoehe} m

### Gebäude-Metadaten (GWR)
- EGID: {egid}
- Adresse: {adresse or 'nicht verfügbar'}
- Kategorie: {gkat} ({gkat_text})
- Geschosse: {gastw}
- Baujahr: {gbauj}
- Grundfläche (GWR): {garea} m²

## Deine Aufgabe

Analysiere das Gebäude und teile es in Höhenzonen auf.

### Schritt 1: Form analysieren und Zonen erkennen

**Einfache Gebäude (1 Zone):**
- Rechteckig oder leicht unregelmässig
- Keine signifikanten Höhenunterschiede zu erwarten

**L-förmige Gebäude (2 Zonen):**
- Erkennbar an zwei länglichen Abschnitten im 90°-Winkel
- Hauptflügel (Zone 1) und Seitenflügel/Anbau (Zone 2)
- Höhe: Anbau oft 1-2 Geschosse niedriger

**U-förmige Gebäude (3 Zonen):**
- Erkennbar an drei Flügeln um einen Innenhof
- Mittelbau (Zone 1) und zwei Seitenflügel (Zone 2, 3)

**Gebäude mit Türmen/Erkern:**
- Vorstehende Eckelemente als separate Zone
- Typisch bei älteren Gebäuden, Kirchen, öffentlichen Bauten

**T-förmige Gebäude (2 Zonen):**
- Hauptriegel und querstehendes Element

### Schritt 2: Zonen identifizieren
Für jede Zone bestimme:
1. **Welche Polygon-Punkte** gehören dazu (als Indizes 0, 1, 2, ...)
2. **Geschätzte Höhe** basierend auf:
   - Globale Höhe als Basis
   - Kategorie-spezifische Anpassungen
   - Proportionale Schätzung bei Anbauten
3. **Typ** der Zone

### Höhen-Schätzung Richtlinien
| Situation | Schätzung |
|-----------|-----------|
| Einfaches Gebäude | Globale Höhe verwenden |
| Anbau/Garage | 60-80% der Haupthöhe oder 3-5m |
| Turm (Kirche) | 2-3× Schiffhöhe |
| Arkaden/Laubengang | 4-5m |
| Kuppel | Firsthöhe + 50-100% |

### Schritt 3: Confidence bewerten
- 0.9-1.0: Sehr sicher (einfache Geometrie, klare Struktur)
- 0.7-0.9: Sicher (typische Struktur erkannt)
- 0.5-0.7: Unsicher (Annahmen getroffen)
- <0.5: Sehr unsicher (User-Validierung empfohlen)

## Output-Format

Antworte NUR mit validem JSON (kein Markdown, keine Erklärung):

{{
  "complexity": "simple|moderate|complex",
  "zones": [
    {{
      "id": "zone_1",
      "name": "Hauptgebäude",
      "type": "hauptgebaeude|anbau|turm|kuppel|arkade|vordach|treppenhaus|garage|unknown",
      "polygon_point_indices": [0, 1, 2, 3],
      "traufhoehe_m": 12.5,
      "firsthoehe_m": 15.0,
      "gebaeudehoehe_m": 15.0,
      "fassaden_ids": ["N", "E", "S", "W"],
      "beruesten": true,
      "sonderkonstruktion": false,
      "confidence": 0.9,
      "notes": null
    }}
  ],
  "zone_adjacency": {{
    "zone_1": ["zone_2"]
  }},
  "has_height_variations": false,
  "has_setbacks": false,
  "has_towers": false,
  "has_annexes": false,
  "has_special_features": false,
  "overall_confidence": 0.9,
  "reasoning": "Kurze Begründung der Analyse",

  "zugaenge": [
    {{
      "id": "Z1",
      "fassade_id": "W",
      "position_percent": 0.5,
      "grund": "Stirnseite West"
    }},
    {{
      "id": "Z2",
      "fassade_id": "E",
      "position_percent": 0.5,
      "grund": "Stirnseite Ost"
    }}
  ],
  "zugaenge_hinweise": []
}}

## Aufgabe 2: Zugänge empfehlen

Basierend auf der Gebäudestruktur, empfehle Positionen für Gerüst-Zugänge (Treppen).

### SUVA-Vorschriften (Schweiz)
- **Max. 50m Fluchtweg** zum nächsten Abstieg
- **Mindestens 2 Zugänge** pro Gerüst
- Anzahl = max(2, ceil(Umfang / 50))

### Platzierungs-Regeln
1. An Gebäudeecken bevorzugt (mehr Platz)
2. An Stirnseiten bei rechteckigen Gebäuden
3. Ein Zugang pro Flügel bei L/U-Form
4. Nicht vor Haupteingängen bei öffentlichen Gebäuden

### Zugang-Felder
- `id`: "Z1", "Z2", etc.
- `fassade_id`: Fassaden-Richtung ("N", "E", "S", "W")
- `position_percent`: 0.0 (Start) bis 1.0 (Ende) auf der Fassade
- `grund`: Begründung für die Position

## Wichtige Regeln

1. Bei einfachen rechteckigen Gebäuden: NUR 1 Zone erstellen
2. Bei L-/U-/T-Form: Erstelle separate Zonen für jeden Gebäudeteil
3. Erfinde KEINE Höhen ohne Grundlage - nutze die globale Höhe als Basis
4. `polygon_point_indices` müssen gültige Indizes sein (0 bis {num_vertices - 1})
5. Jeder Polygon-Punkt sollte zu genau einer Zone gehören
6. `fassaden_ids` basieren auf der Ausrichtung: N, NE, E, SE, S, SW, W, NW
7. Bei mehreren Zonen: Jede Richtung nur EINER Zone zuordnen

### Beispiel: L-förmiges Gebäude mit 8 Ecken

```
     N
     │
 ┌───┴───┐
 │ Zone1 │  ← Hauptflügel (Punkte 0-3)
 │       ├─────┐
 └───────┤Zone2│  ← Anbau (Punkte 4-7)
         └─────┘
```

Ergebnis:
- Zone 1: polygon_point_indices=[0,1,2,3], fassaden_ids=["N", "W"]
- Zone 2: polygon_point_indices=[4,5,6,7], fassaden_ids=["S", "E"]
"""

    def _parse_claude_response(
        self,
        response_text: str,
        egid: str,
        adresse: Optional[str]
    ) -> BuildingContext:
        """Parst die Claude-Response und erstellt einen BuildingContext"""
        try:
            # JSON extrahieren (falls in Markdown-Block)
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            data = json.loads(response_text)

            # Zonen parsen
            zones = []
            for z in data.get('zones', []):
                zone = BuildingZone(
                    id=z.get('id', 'zone_1'),
                    name=z.get('name', 'Hauptgebäude'),
                    type=ZoneType(z.get('type', 'hauptgebaeude')),
                    polygon_point_indices=z.get('polygon_point_indices'),
                    sub_polygon=z.get('sub_polygon'),
                    traufhoehe_m=z.get('traufhoehe_m'),
                    firsthoehe_m=z.get('firsthoehe_m'),
                    gebaeudehoehe_m=z.get('gebaeudehoehe_m', 10.0),
                    fassaden_ids=z.get('fassaden_ids', []),
                    beruesten=z.get('beruesten', True),
                    sonderkonstruktion=z.get('sonderkonstruktion', False),
                    confidence=z.get('confidence', 0.8),
                    notes=z.get('notes')
                )
                zones.append(zone)

            context = BuildingContext(
                egid=egid,
                adresse=adresse,
                zones=zones,
                zone_adjacency=data.get('zone_adjacency'),
                complexity=ComplexityLevel(data.get('complexity', 'moderate')),
                has_height_variations=data.get('has_height_variations', False),
                has_setbacks=data.get('has_setbacks', False),
                has_towers=data.get('has_towers', False),
                has_annexes=data.get('has_annexes', False),
                has_special_features=data.get('has_special_features', False),
                zugaenge=data.get('zugaenge', []),
                zugaenge_hinweise=data.get('zugaenge_hinweise', []),
                source=ContextSource.CLAUDE,
                confidence=data.get('overall_confidence', 0.8),
                validated_by_user=False,
                reasoning=data.get('reasoning'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            return context

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.error(f"Response was: {response_text[:500]}")
            raise ValueError(f"Could not parse Claude response: {e}")

    def _extract_fassaden(self, polygon: list[dict]) -> list[dict]:
        """Extrahiert Fassaden aus einem Polygon"""
        fassaden = []
        n = len(polygon)

        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]

            # Koordinaten extrahieren
            x1 = p1.get('x', p1.get('e', p1[0] if isinstance(p1, (list, tuple)) else 0))
            y1 = p1.get('y', p1.get('n', p1[1] if isinstance(p1, (list, tuple)) else 0))
            x2 = p2.get('x', p2.get('e', p2[0] if isinstance(p2, (list, tuple)) else 0))
            y2 = p2.get('y', p2.get('n', p2[1] if isinstance(p2, (list, tuple)) else 0))

            # Länge und Winkel berechnen
            dx = x2 - x1
            dy = y2 - y1
            laenge = math.sqrt(dx * dx + dy * dy)
            winkel = math.degrees(math.atan2(dy, dx))

            # Himmelsrichtung ableiten
            if -22.5 <= winkel < 22.5:
                richtung = "E"
            elif 22.5 <= winkel < 67.5:
                richtung = "NE"
            elif 67.5 <= winkel < 112.5:
                richtung = "N"
            elif 112.5 <= winkel < 157.5:
                richtung = "NW"
            elif winkel >= 157.5 or winkel < -157.5:
                richtung = "W"
            elif -157.5 <= winkel < -112.5:
                richtung = "SW"
            elif -112.5 <= winkel < -67.5:
                richtung = "S"
            else:
                richtung = "SE"

            fassaden.append({
                "id": f"F{i + 1}",
                "start": {"x": x1, "y": y1},
                "end": {"x": x2, "y": y2},
                "laenge": round(laenge, 2),
                "winkel": round(winkel, 1),
                "richtung": richtung
            })

        return fassaden

    def _calculate_polygon_area(self, polygon: list[dict]) -> float:
        """Berechnet die Fläche eines Polygons (Shoelace-Formel)"""
        n = len(polygon)
        if n < 3:
            return 0.0

        area = 0.0
        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]

            x1 = p1.get('x', p1.get('e', p1[0] if isinstance(p1, (list, tuple)) else 0))
            y1 = p1.get('y', p1.get('n', p1[1] if isinstance(p1, (list, tuple)) else 0))
            x2 = p2.get('x', p2.get('e', p2[0] if isinstance(p2, (list, tuple)) else 0))
            y2 = p2.get('y', p2.get('n', p2[1] if isinstance(p2, (list, tuple)) else 0))

            area += x1 * y2 - x2 * y1

        return abs(area) / 2.0

    def _calculate_perimeter(self, polygon: list[dict]) -> float:
        """Berechnet den Umfang eines Polygons"""
        n = len(polygon)
        if n < 2:
            return 0.0

        perimeter = 0.0
        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]

            x1 = p1.get('x', p1.get('e', p1[0] if isinstance(p1, (list, tuple)) else 0))
            y1 = p1.get('y', p1.get('n', p1[1] if isinstance(p1, (list, tuple)) else 0))
            x2 = p2.get('x', p2.get('e', p2[0] if isinstance(p2, (list, tuple)) else 0))
            y2 = p2.get('y', p2.get('n', p2[1] if isinstance(p2, (list, tuple)) else 0))

            dx = x2 - x1
            dy = y2 - y1
            perimeter += math.sqrt(dx * dx + dy * dy)

        return perimeter

    def _has_concave_sections(self, polygon: list[dict]) -> bool:
        """Prüft ob ein Polygon konkave Abschnitte hat"""
        n = len(polygon)
        if n < 4:
            return False

        # Kreuzprodukte berechnen
        cross_products = []
        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]
            p3 = polygon[(i + 2) % n]

            x1 = p1.get('x', p1.get('e', p1[0] if isinstance(p1, (list, tuple)) else 0))
            y1 = p1.get('y', p1.get('n', p1[1] if isinstance(p1, (list, tuple)) else 0))
            x2 = p2.get('x', p2.get('e', p2[0] if isinstance(p2, (list, tuple)) else 0))
            y2 = p2.get('y', p2.get('n', p2[1] if isinstance(p2, (list, tuple)) else 0))
            x3 = p3.get('x', p3.get('e', p3[0] if isinstance(p3, (list, tuple)) else 0))
            y3 = p3.get('y', p3.get('n', p3[1] if isinstance(p3, (list, tuple)) else 0))

            # Kreuzprodukt der Vektoren (p2-p1) und (p3-p2)
            cross = (x2 - x1) * (y3 - y2) - (y2 - y1) * (x3 - x2)
            cross_products.append(cross)

        # Wenn alle Kreuzprodukte das gleiche Vorzeichen haben → konvex
        # Sonst → konkav
        positive = sum(1 for c in cross_products if c > 0)
        negative = sum(1 for c in cross_products if c < 0)

        return positive > 0 and negative > 0

    def _get_gkat_text(self, gkat: int) -> str:
        """Gibt den Text zur Gebäudekategorie zurück"""
        categories = {
            1020: "Provisorische Unterkunft",
            1021: "Einfamilienhaus",
            1025: "Mehrfamilienhaus (2 Whg)",
            1030: "Mehrfamilienhaus",
            1040: "Gebäude mit Nebennutzung",
            1060: "Bildung/Kultur",
            1080: "Gesundheit",
            1110: "Kirche/Religiös",
            1130: "Museum/Bibliothek",
            1212: "Industrie"
        }
        return categories.get(gkat, f"Kategorie {gkat}")


# Singleton-Instanz
_service_instance: Optional[BuildingContextService] = None


def get_building_context_service() -> BuildingContextService:
    """Gibt die Singleton-Instanz des Services zurück"""
    global _service_instance
    if _service_instance is None:
        _service_instance = BuildingContextService()
    return _service_instance
