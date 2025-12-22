"""
Claude-basierter SVG Generator Service

Verwendet die Anthropic Claude API, um hochwertige SVG-Visualisierungen
für Gebäude zu generieren. Die SVGs werden gecached, um API-Kosten zu sparen.

Bei API-Fehlern (kein Guthaben, etc.) wird automatisch auf den
einfachen SVG-Generator zurückgefallen.
"""

import hashlib
import sqlite3
import os
from typing import Optional
from dataclasses import dataclass

# Anthropic SDK
ANTHROPIC_AVAILABLE = False
anthropic_client = None

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    pass

# Fallback Generator importieren
from app.services.svg_generator import SVGGenerator, BuildingData as FallbackBuildingData


@dataclass
class BuildingData:
    """Gebäudedaten für SVG-Generierung"""
    address: str
    egid: Optional[int] = None
    length_m: float = 10.0
    width_m: float = 10.0
    eave_height_m: float = 8.0
    ridge_height_m: Optional[float] = None
    floors: int = 3
    roof_type: str = "gable"  # flat, gable, hip
    area_m2: Optional[float] = None
    width_class: str = "W09"


class ClaudeSVGGenerator:
    """Generiert SVGs mittels Claude API mit Fallback auf einfachen Generator"""

    # Cache-Datenbank
    CACHE_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'svg_cache.db')

    # Claude Model
    MODEL = "claude-sonnet-4-20250514"

    def __init__(self):
        self._cache_available = False
        self._memory_cache = {}
        self._init_cache()
        self._init_client()
        self._fallback_generator = SVGGenerator()  # Fallback bei API-Fehler

    def _to_fallback_data(self, building: BuildingData) -> FallbackBuildingData:
        """Konvertiert BuildingData zu FallbackBuildingData"""
        return FallbackBuildingData(
            address=building.address,
            egid=building.egid,
            length_m=building.length_m,
            width_m=building.width_m,
            eave_height_m=building.eave_height_m,
            ridge_height_m=building.ridge_height_m,
            floors=building.floors,
            roof_type=building.roof_type,
            area_m2=building.area_m2,
            width_class=building.width_class,
        )

    def _init_client(self):
        """Initialisiert den Anthropic Client"""
        global anthropic_client
        if ANTHROPIC_AVAILABLE and anthropic_client is None:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if api_key:
                anthropic_client = anthropic.Anthropic(api_key=api_key)

    def _init_cache(self):
        """Initialisiert die Cache-Datenbank"""
        try:
            os.makedirs(os.path.dirname(self.CACHE_DB_PATH), exist_ok=True)
            conn = sqlite3.connect(self.CACHE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS svg_cache (
                    cache_key TEXT PRIMARY KEY,
                    svg_type TEXT NOT NULL,
                    svg_content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
            self._cache_available = True
        except Exception as e:
            print(f"Cache init error (will use in-memory): {e}")
            self._cache_available = False
            self._memory_cache = {}

    def _get_cache_key(self, building: BuildingData, svg_type: str) -> str:
        """Generiert einen Cache-Key basierend auf Gebäudedaten"""
        data = f"{building.address}|{building.length_m}|{building.width_m}|{building.eave_height_m}|{building.ridge_height_m}|{building.floors}|{building.roof_type}|{svg_type}"
        return hashlib.md5(data.encode()).hexdigest()

    def _get_cached_svg(self, cache_key: str) -> Optional[str]:
        """Holt SVG aus dem Cache"""
        # Memory Cache Fallback
        if not self._cache_available:
            return self._memory_cache.get(cache_key)

        try:
            conn = sqlite3.connect(self.CACHE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT svg_content FROM svg_cache WHERE cache_key = ?', (cache_key,))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception:
            return self._memory_cache.get(cache_key)

    def _cache_svg(self, cache_key: str, svg_type: str, svg_content: str):
        """Speichert SVG im Cache"""
        # Memory Cache Fallback
        if not self._cache_available:
            self._memory_cache[cache_key] = svg_content
            return

        try:
            conn = sqlite3.connect(self.CACHE_DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO svg_cache (cache_key, svg_type, svg_content)
                VALUES (?, ?, ?)
            ''', (cache_key, svg_type, svg_content))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Cache error: {e}")
            self._memory_cache[cache_key] = svg_content

    def _call_claude(self, prompt: str) -> Optional[str]:
        """Ruft Claude API auf und extrahiert SVG"""
        if not ANTHROPIC_AVAILABLE or anthropic_client is None:
            print("Anthropic SDK not available or no API key")
            return None

        try:
            message = anthropic_client.messages.create(
                model=self.MODEL,
                max_tokens=8000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # SVG aus der Antwort extrahieren
            if '<svg' in response_text and '</svg>' in response_text:
                start = response_text.find('<svg')
                end = response_text.find('</svg>') + 6
                return response_text[start:end]

            # Falls in Code-Block
            if '```svg' in response_text or '```xml' in response_text:
                lines = response_text.split('\n')
                svg_lines = []
                in_svg = False
                for line in lines:
                    if line.strip().startswith('```') and not in_svg:
                        in_svg = True
                        continue
                    elif line.strip() == '```' and in_svg:
                        break
                    elif in_svg:
                        svg_lines.append(line)
                svg_content = '\n'.join(svg_lines)
                if '<svg' in svg_content:
                    return svg_content

            return None

        except Exception as e:
            print(f"Claude API error: {e}")
            return None

    def clear_cache_for_address(self, address: str):
        """Löscht alle Cache-Einträge für eine Adresse"""
        try:
            conn = sqlite3.connect(self.CACHE_DB_PATH)
            cursor = conn.cursor()
            # Cache-Keys enthalten die Adresse im Hash, aber wir können nach Zeitstempel löschen
            # Einfacher: Alle Einträge älter als jetzt löschen die diese Adresse betreffen
            cursor.execute('DELETE FROM svg_cache WHERE cache_key LIKE ?', (f'%{address[:20]}%',))
            conn.commit()
            deleted = cursor.rowcount
            conn.close()
            print(f"Cache cleared: {deleted} entries for {address}")
            return deleted
        except Exception as e:
            print(f"Cache clear error: {e}")
            return 0

    def generate_cross_section(self, building: BuildingData, width: int = 700, height: int = 480, force_refresh: bool = False) -> Optional[str]:
        """Generiert Querschnitt-SVG via Claude"""
        cache_key = self._get_cache_key(building, f"cross_section_{width}x{height}")

        # Cache prüfen (ausser bei force_refresh)
        if not force_refresh:
            cached = self._get_cached_svg(cache_key)
            if cached:
                return cached

        ridge_h = building.ridge_height_m or building.eave_height_m
        roof_info = "Satteldach" if ridge_h > building.eave_height_m else "Flachdach"

        # Gebäudetyp basierend auf Grösse bestimmen
        area = building.area_m2 or (building.length_m * building.width_m)
        is_large_building = building.floors >= 4 or area >= 300
        building_type = "Mehrfamilienhaus" if is_large_building else "Einfamilienhaus"

        # Anzahl Verankerungspunkte basierend auf Höhe
        anchor_points = max(3, building.floors // 2 + 1)

        prompt = f"""Generiere ein professionelles SVG für einen Gebäude-Querschnitt mit Gerüstposition.

GEBÄUDEDATEN:
- Adresse: {building.address}
- Gebäudetyp: {building_type}
- Gebäudebreite (Giebelseite): {building.width_m:.1f} m
- Traufhöhe: {building.eave_height_m:.1f} m
- Firsthöhe: {ridge_h:.1f} m
- Geschosse: {building.floors}
- Dachform: {roof_info}
- Gerüst-Breitenklasse: {building.width_class}

SVG-ANFORDERUNGEN:
- Größe: {width}x{height} Pixel
- viewBox: 0 0 {width} {height}

INHALT (von links nach rechts):
1. Linkes Gerüst (gelb #fff3cd, Rahmen #ffc107, ca. 15-20px breit)
2. Gebäude im Schnitt (grau #e0e0e0 mit diagonaler Schraffur) - {building.floors} Geschosse sichtbar
3. Dach (braun #8b7355) - {"Flachdach" if is_large_building and roof_info == "Flachdach" else "Dreieck für Satteldach"}
4. Rechtes Gerüst (gleich wie links)
5. Verankerungspunkte (rote Kreise #dc3545, {anchor_points} pro Seite - vertikal verteilt)

BESCHRIFTUNGEN:
- Titel oben: "Gebäudeschnitt (Querschnitt) - {building_type}" + Adresse
- Höhenkoten rechts: ±0.00, Traufe +{building.eave_height_m:.1f}m{f", First +{ridge_h:.1f}m" if ridge_h > building.eave_height_m else ""}
- Breitenmass unten: {building.width_m:.1f} m
- Massstab unten rechts

WEITERE ELEMENTE:
- Höhenraster (gestrichelte horizontale Linien alle 5m)
- Geschosslinien im Gebäude andeuten ({building.floors} Etagen)
- NPK 114 Info-Box unten links (grün #e8f5e9)
- Legende oben rechts

STIL:
- Saubere technische Zeichnung
- Arial Schriftart
- Klare Linien, professionell
- Dezente Farben
- Bei {building_type}: entsprechende Proportionen

Antworte NUR mit dem SVG-Code, keine Erklärungen."""

        svg = self._call_claude(prompt)

        if svg:
            self._cache_svg(cache_key, "cross_section", svg)
            return svg

        # Fallback auf einfachen Generator
        print("Claude API fehlgeschlagen - verwende Fallback-Generator für cross_section")
        fallback_data = self._to_fallback_data(building)
        return self._fallback_generator.generate_cross_section(fallback_data, width, height)

    def generate_elevation(self, building: BuildingData, width: int = 700, height: int = 480, force_refresh: bool = False) -> Optional[str]:
        """Generiert Fassadenansicht-SVG via Claude"""
        cache_key = self._get_cache_key(building, f"elevation_{width}x{height}")

        if not force_refresh:
            cached = self._get_cached_svg(cache_key)
            if cached:
                return cached

        ridge_h = building.ridge_height_m or building.eave_height_m
        roof_info = "Satteldach" if ridge_h > building.eave_height_m else "Flachdach"

        # Fenster pro Geschoss berechnen
        windows_per_floor = max(3, int(building.length_m / 4))

        # Gebäudetyp und Eingänge basierend auf Grösse bestimmen
        area = building.area_m2 or (building.length_m * building.width_m)
        is_large_building = building.floors >= 4 or area >= 300

        # Anzahl Eingänge: 1 pro ~15m Fassadenlänge bei grossen Gebäuden
        if is_large_building:
            num_entrances = max(2, int(building.length_m / 15))
            building_type = "Mehrfamilienhaus"
            entrance_info = f"{num_entrances} Hauseingänge gleichmässig verteilt"
        else:
            num_entrances = 1
            building_type = "Einfamilienhaus"
            entrance_info = "1 Eingangstür in der Mitte"

        prompt = f"""Generiere ein professionelles SVG für eine Gebäude-Fassadenansicht (Traufseite) mit Gerüst.

GEBÄUDEDATEN:
- Adresse: {building.address}
- Gebäudetyp: {building_type}
- Fassadenlänge (Traufseite): {building.length_m:.1f} m
- Traufhöhe: {building.eave_height_m:.1f} m
- Firsthöhe: {ridge_h:.1f} m
- Geschosse: {building.floors}
- Dachform: {roof_info}
- Fenster pro Geschoss: ca. {windows_per_floor}
- Eingänge: {entrance_info}

SVG-ANFORDERUNGEN:
- Größe: {width}x{height} Pixel
- viewBox: 0 0 {width} {height}

INHALT:
1. Hintergrund: Himmel oben (#e3f2fd), Boden unten (#d4c4b0)
2. Gebäudefassade (hellgrau #e0e0e0)
3. Fenster (blau #4a90a4) - {windows_per_floor} pro Geschoss, gleichmässig verteilt
4. Hauseingänge (braun #5d4037) - {entrance_info}
5. Dach (braun #8b7355) - {"Flachdach für grosses MFH" if is_large_building and roof_info == "Flachdach" else roof_info}
6. Gerüst links und rechts (gelb #fff3cd, Rahmen #ffc107)
7. Verankerungspunkte (rot #dc3545) - mehr Punkte bei hohen Gebäuden

BESCHRIFTUNGEN:
- Titel: "Fassadenansicht (Traufseite)" + Adresse
- Höhenkoten rechts: ±0.00, Traufe +{building.eave_height_m:.1f}m{f", First +{ridge_h:.1f}m" if ridge_h > building.eave_height_m else ""}
- Längenmass unten: {building.length_m:.1f} m
- Gerüst-Beschriftung: "{building.width_class}"

WEITERE ELEMENTE:
- NPK 114 Info-Box
- Legende
- Massstab

STIL:
- Realistische Gebäudedarstellung für {building_type}
- Professionelle technische Zeichnung
- Arial Schriftart

Antworte NUR mit dem SVG-Code."""

        svg = self._call_claude(prompt)

        if svg:
            self._cache_svg(cache_key, "elevation", svg)
            return svg

        # Fallback auf einfachen Generator
        print("Claude API fehlgeschlagen - verwende Fallback-Generator für elevation")
        fallback_data = self._to_fallback_data(building)
        return self._fallback_generator.generate_elevation(fallback_data, width, height)

    def generate_floor_plan(self, building: BuildingData, width: int = 600, height: int = 500, force_refresh: bool = False) -> Optional[str]:
        """Generiert Grundriss-SVG via Claude"""
        cache_key = self._get_cache_key(building, f"floor_plan_{width}x{height}")

        if not force_refresh:
            cached = self._get_cached_svg(cache_key)
            if cached:
                return cached

        area = building.area_m2 or (building.length_m * building.width_m)
        perimeter = 2 * (building.length_m + building.width_m)

        # Gebäudetyp und Eingänge basierend auf Grösse bestimmen
        is_large_building = building.floors >= 4 or area >= 300
        building_type = "Mehrfamilienhaus" if is_large_building else "Einfamilienhaus"

        # Anzahl Eingänge
        if is_large_building:
            num_entrances = max(2, int(max(building.length_m, building.width_m) / 15))
            entrance_info = f"{num_entrances} Hauseingänge als kleine Rechtecke an der längsten Seite"
        else:
            num_entrances = 1
            entrance_info = "1 Eingang als kleines Rechteck"

        prompt = f"""Generiere ein professionelles SVG für einen Gebäude-Grundriss mit umlaufender Gerüstposition.

GEBÄUDEDATEN:
- Adresse: {building.address}
- Gebäudetyp: {building_type}
- Länge (Nord-Süd): {building.length_m:.1f} m
- Breite (Ost-West): {building.width_m:.1f} m
- Grundfläche: {area:.0f} m²
- Umfang: {perimeter:.0f} m
- Geschosse: {building.floors}
- Gerüst-Breitenklasse: {building.width_class}
- Eingänge: {entrance_info}

SVG-ANFORDERUNGEN:
- Größe: {width}x{height} Pixel
- viewBox: 0 0 {width} {height}
- Draufsicht (Vogelperspektive)

INHALT:
1. Gebäudegrundriss (Rechteck, grau #e0e0e0, mit Schraffur)
2. Umlaufendes Gerüst (gelber Rahmen #fff3cd um das Gebäude)
3. Verankerungspunkte an den Ecken und Seiten (rot #dc3545)
4. Hauseingänge: {entrance_info} (braun #5d4037)
5. Fassadenbeschriftungen: Nord, Süd, Ost, West mit Längenmassen

BESCHRIFTUNGEN:
- Titel: "Grundriss mit Gerüstposition - {building_type}" + Adresse
- Fläche in der Mitte: "{area:.0f} m²"
- "{building.floors} Geschosse" unter der Fläche
- Seitenlängen an den Kanten
- EGID: {building.egid or 'nicht verfügbar'}

WEITERE ELEMENTE:
- Nordpfeil oben rechts
- Massstab unten links
- NPK 114 Info-Box
- Legende
- Koordinatensystem-Hinweis: "LV95 (EPSG:2056)"

STIL:
- Klare Draufsicht
- Professionelle technische Plandarstellung für {building_type}
- Arial Schriftart

Antworte NUR mit dem SVG-Code."""

        svg = self._call_claude(prompt)

        if svg:
            self._cache_svg(cache_key, "floor_plan", svg)
            return svg

        # Fallback auf einfachen Generator
        print("Claude API fehlgeschlagen - verwende Fallback-Generator für floor_plan")
        fallback_data = self._to_fallback_data(building)
        return self._fallback_generator.generate_floor_plan(fallback_data, width, height)

    def is_available(self) -> bool:
        """Prüft ob der Service verfügbar ist"""
        return ANTHROPIC_AVAILABLE and anthropic_client is not None


# Singleton
_claude_generator: Optional[ClaudeSVGGenerator] = None


def get_claude_svg_generator() -> ClaudeSVGGenerator:
    """Hole Singleton-Instanz des Claude SVG-Generators"""
    global _claude_generator
    if _claude_generator is None:
        _claude_generator = ClaudeSVGGenerator()
    return _claude_generator
