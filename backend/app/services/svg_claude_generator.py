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
        floors = building.floors or 3
        is_large_building = floors >= 4 or area >= 300
        building_type = "Mehrfamilienhaus" if is_large_building else "Einfamilienhaus"

        # Anzahl Verankerungspunkte basierend auf Höhe
        anchor_points = max(3, floors // 2 + 1)

        prompt = f"""Generiere ein professionelles SVG für einen Gebäude-Querschnitt mit Gerüstposition.

GEBÄUDEDATEN:
- Adresse: {building.address}
- Gebäudetyp: {building_type}
- Gebäudebreite (Giebelseite): {building.width_m:.1f} m
- Traufhöhe: {building.eave_height_m:.1f} m
- Firsthöhe: {ridge_h:.1f} m
- Geschosse: {floors}
- Dachform: {roof_info}
- Gerüst-Breitenklasse: {building.width_class}

SVG-TECHNISCHE ANFORDERUNGEN:
- Größe: {width}x{height} Pixel
- viewBox: 0 0 {width} {height}
- Verwende <defs> für Patterns:
  1. building-hatch: Diagonale Schraffur für Gebäudeschnitt
  2. scaffold-pattern: Gelbes Muster für Gerüst (#fff3cd mit #ffc107 Linien)

LAYOUT (Proportionen beachten):
- Hintergrund: Hellgrau #f8f9fa
- Boden-Linie bei ca. 80% der Höhe
- Gebäude zentriert mit Gerüst links und rechts
- Rechts Platz für Höhenkoten lassen

GEBÄUDE-DARSTELLUNG:
1. Schnittfläche mit Schraffur-Pattern (fill="url(#building-hatch)")
2. {floors} Geschosse durch horizontale Linien andeuten
3. Dach: {"Rechteck für Flachdach" if roof_info == "Flachdach" else "Dreieck für Satteldach"} (braun #8b7355)
4. Dicke Aussenlinien (stroke-width="1.5")

GERÜST:
1. Links und rechts vom Gebäude (ca. 15px breit)
2. fill="url(#scaffold-pattern)" mit #ffc107 Rahmen
3. {anchor_points} rote Verankerungspunkte pro Seite (Kreise r="3" fill="#dc3545")
4. Punkte vertikal gleichmässig verteilt

BESCHRIFTUNGEN (Arial, gut lesbar):
- Titel: "Gebäudeschnitt - {building_type}" (16px, fett, oben mittig)
- Untertitel: Adresse (11px, grau)
- Höhenkoten rechts mit gestrichelten Linien:
  * ±0.00 m (Terrain)
  * +{building.eave_height_m:.1f} m (Traufe)
  {f"* +{ridge_h:.1f} m (First) - rot hervorgehoben" if ridge_h > building.eave_height_m else ""}
- Breitenmass unten: {building.width_m:.1f} m mit Masspfeilen
- Massstab unten rechts

LEGENDE (oben rechts, weisser Kasten):
- Gerüst (gelb)
- Gebäudeschnitt (grau schraffiert)
- Verankerung (roter Kreis)

NPK 114 INFO-BOX (unten links, grün #e8f5e9):
- "NPK 114 D/2012"
- "Ausmass = Länge × Höhe"
- Breitenklasse: {building.width_class}

STIL:
- Technische Zeichnung wie Architekturplan
- Klare, saubere Linien
- Professionell und lesbar

Antworte NUR mit dem vollständigen SVG-Code."""

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
        floors = building.floors or 3
        is_large_building = floors >= 4 or area >= 300

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
- Fassadenlänge: {building.length_m:.1f} m
- Traufhöhe: {building.eave_height_m:.1f} m
- Firsthöhe: {ridge_h:.1f} m
- Geschosse: {floors}
- Dachform: {roof_info}
- Fenster pro Geschoss: {windows_per_floor}
- Eingänge: {entrance_info}

SVG-TECHNISCHE ANFORDERUNGEN:
- Größe: {width}x{height} Pixel
- viewBox: 0 0 {width} {height}
- Verwende <defs> für Patterns:
  1. windows-pattern: Fenster-Raster für Fassade
  2. scaffold-pattern: Gelbes Gerüst-Muster (#fff3cd mit #ffc107 Linien)

LAYOUT:
- Himmel oben (#e3f2fd, ca. 75% der Höhe)
- Boden/Strasse unten (#d4c4b0, ca. 15%)
- Gebäude zentriert, Gerüst links/rechts
- Platz rechts für Höhenkoten

FASSADEN-DARSTELLUNG:
1. Hauptkörper (#e0e0e0 bis #d8d8d8, mit leichtem Schatten)
2. Fenster: {windows_per_floor} pro Geschoss, blau #4a90a4 mit dunklem Rahmen
3. Eingang: {entrance_info} (braun #5d4037, grösser als Fenster)
4. Dach: {"Flachlinie für Flachdach" if roof_info == "Flachdach" else "Satteldach-Dreieck"} (braun #8b7355)
5. Geschosstrennung durch feine Linien andeuten

GERÜST (beidseitig):
1. Gerüst-Streifen links und rechts (ca. 15-20px breit)
2. fill="url(#scaffold-pattern)" mit gelb/orange Rahmen
3. Beschriftung vertikal: "{building.width_class}"
4. Rote Verankerungspunkte (Kreise r="3" fill="#dc3545")
5. Punkte vertikal alle 3-4m

BESCHRIFTUNGEN (Arial):
- Titel: "Fassadenansicht - {building_type}" (16px, fett, oben mittig)
- Untertitel: Adresse (11px, grau)
- Höhenkoten rechts mit gestrichelten Bezugslinien:
  * ±0.00 m (Terrain)
  * +{building.eave_height_m:.1f} m (Traufe)
  {f"* +{ridge_h:.1f} m (First) - rot hervorgehoben" if ridge_h > building.eave_height_m else ""}
- Längenmass unten: {building.length_m:.1f} m mit Masspfeilen
- Massstab unten

LEGENDE (oben rechts, weisser Kasten mit Rahmen):
- Fassadengerüst (gelb)
- Verankerung (roter Kreis)
- Eingang (braun)

NPK 114 INFO-BOX (unten, grün #e8f5e9):
- "NPK 114 D/2012 - Traufseite"
- "Ausmass: ({building.length_m:.1f} + 2×Zuschlag) × ({building.eave_height_m:.1f} + 1.0)"
- Breitenklasse: {building.width_class}

STIL:
- Professionelle Architektur-Zeichnung
- Realistische Proportionen
- Saubere Linien, lesbare Beschriftungen

Antworte NUR mit dem vollständigen SVG-Code."""

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
        floors = building.floors or 3

        # Gebäudetyp und Eingänge basierend auf Grösse bestimmen
        is_large_building = floors >= 4 or area >= 300
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
- Geschosse: {floors}
- Gerüst-Breitenklasse: {building.width_class}
- Eingänge: {entrance_info}

SVG-TECHNISCHE ANFORDERUNGEN:
- Größe: {width}x{height} Pixel
- viewBox: 0 0 {width} {height}
- Verwende <defs> für Patterns:
  1. building-hatch: Diagonale Schraffur für Gebäude
  2. scaffold-pattern: Gelbes Muster für Gerüst

LAYOUT (Draufsicht):
- Weisser/hellgrauer Hintergrund
- Gebäude zentriert (ca. 60% der Fläche)
- Umlaufendes Gerüst um Gebäude
- Platz für Beschriftungen an allen Seiten

GRUNDRISS-DARSTELLUNG:
1. Gebäude-Rechteck mit Schraffur (#e0e0e0, fill="url(#building-hatch)")
2. Dicke Aussenwände (stroke-width="2", #333)
3. Innenwände angedeutet (dünne Linien)
4. Eingänge: {entrance_info} als Öffnungen in der Wand (braun #5d4037)
5. Norden oben

GERÜST (umlaufend):
1. Gelber Streifen um das gesamte Gebäude (ca. 1m Abstand = 15-20px)
2. fill="url(#scaffold-pattern)" mit #ffc107 Rahmen
3. Verankerungspunkte an allen 4 Ecken + Zwischenpunkte
4. Rote Kreise (r="4" fill="#dc3545")

BESCHRIFTUNGEN (Arial):
- Titel: "Grundriss - {building_type}" (14px, fett, oben)
- Adresse als Untertitel (10px, grau)
- Fläche gross in der Gebäudemitte: "{area:.0f} m²" (18px, fett)
- "{floors} Geschosse" darunter (10px)
- EGID: {building.egid or '-'} (8px, grau)
- Seitenlängen aussen mit Masspfeilen:
  * Nord/Süd: {building.length_m:.1f} m
  * Ost/West: {building.width_m:.1f} m
- Himmelsrichtungen: N, S, O, W

ZUSÄTZLICHE ELEMENTE:
1. Nordpfeil (oben rechts, deutlich sichtbar)
2. Massstab-Balken (unten links): "5 m" oder "10 m"
3. Koordinaten-Hinweis: "LV95 (CH1903+)"

LEGENDE (unten rechts, weisser Kasten):
- Gebäudegrundriss (grau schraffiert)
- Gerüstzone (gelb)
- Verankerungspunkt (roter Kreis)
- Eingang (braun)

NPK 114 INFO-BOX (unten links, grün #e8f5e9):
- "NPK 114 D/2012"
- "Umfang: {perimeter:.0f} m"
- "Breitenklasse: {building.width_class}"

STIL:
- Technischer Lageplan / Bauplan
- Klare Linien, gute Lesbarkeit
- Professionell wie Architekturzeichnung

Antworte NUR mit dem vollständigen SVG-Code."""

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
