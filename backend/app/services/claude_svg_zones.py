"""
Claude API SVG Generator für Zone-basierte Gebäudeschnitte.

Features:
- Timeout: 90 Sekunden für Claude API
- Caching: SQLite-basiert, SVGs werden nach Generierung gespeichert
- Logging: Detaillierte Logs für Debugging
"""

import hashlib
import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional

# Logging konfigurieren
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Anthropic SDK
ANTHROPIC_AVAILABLE = False
anthropic_client = None

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    logger.warning("Anthropic SDK nicht installiert")

# Cache-Datenbank Pfad
CACHE_DB_PATH = Path(__file__).parent.parent / "data" / "claude_svg_cache.db"


def _init_cache_db():
    """Initialisiert die Cache-Datenbank"""
    CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(CACHE_DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS svg_cache (
            cache_key TEXT PRIMARY KEY,
            svg_type TEXT,
            egid TEXT,
            address TEXT,
            svg_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    logger.info(f"Cache DB initialisiert: {CACHE_DB_PATH}")


def _get_cached_svg(cache_key: str) -> Optional[str]:
    """Holt SVG aus Cache"""
    try:
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT svg_content FROM svg_cache WHERE cache_key = ?", (cache_key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            logger.info(f"Cache HIT: {cache_key[:50]}...")
            return row[0]
        logger.info(f"Cache MISS: {cache_key[:50]}...")
        return None
    except Exception as e:
        logger.error(f"Cache read error: {e}")
        return None


def _save_to_cache(cache_key: str, svg_type: str, egid: Optional[str], address: str, svg_content: str):
    """Speichert SVG im Cache"""
    try:
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO svg_cache (cache_key, svg_type, egid, address, svg_content)
            VALUES (?, ?, ?, ?, ?)
        """, (cache_key, svg_type, egid, address, svg_content))
        conn.commit()
        conn.close()
        logger.info(f"Cache SAVE: {cache_key[:50]}... ({len(svg_content)} chars)")
    except Exception as e:
        logger.error(f"Cache save error: {e}")


def _init_client():
    """Initialisiert den Anthropic Client mit Timeout"""
    global anthropic_client
    if ANTHROPIC_AVAILABLE and anthropic_client is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            # Timeout auf 90 Sekunden setzen
            anthropic_client = anthropic.Anthropic(
                api_key=api_key,
                timeout=90.0  # 90 Sekunden Timeout
            )
            logger.info("Anthropic Client initialisiert (timeout=90s)")
        else:
            logger.warning("ANTHROPIC_API_KEY nicht gesetzt")


def _call_claude(prompt: str, max_tokens: int = 8000) -> Optional[str]:
    """Ruft Claude API auf und extrahiert SVG"""
    _init_client()

    if not ANTHROPIC_AVAILABLE or anthropic_client is None:
        logger.error("Anthropic SDK not available or no API key")
        return None

    start_time = time.time()
    logger.info(f"Claude API Call gestartet (max_tokens={max_tokens})...")

    try:
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        elapsed = time.time() - start_time
        response_text = message.content[0].text
        logger.info(f"Claude API Response: {len(response_text)} chars in {elapsed:.1f}s")
        logger.info(f"Tokens: input={message.usage.input_tokens}, output={message.usage.output_tokens}")

        # SVG aus der Antwort extrahieren
        if '<svg' in response_text and '</svg>' in response_text:
            start = response_text.find('<svg')
            end = response_text.find('</svg>') + 6
            svg = response_text[start:end]
            logger.info(f"SVG extrahiert: {len(svg)} chars")
            return svg

        logger.warning("Kein SVG in Claude Response gefunden")
        logger.debug(f"Response preview: {response_text[:500]}...")
        return None

    except anthropic.APITimeoutError as e:
        elapsed = time.time() - start_time
        logger.error(f"Claude API TIMEOUT nach {elapsed:.1f}s: {e}")
        return None
    except anthropic.APIError as e:
        elapsed = time.time() - start_time
        logger.error(f"Claude API ERROR nach {elapsed:.1f}s: {e}")
        return None
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"Claude API EXCEPTION nach {elapsed:.1f}s: {e}")
        return None


def _generate_cache_key(svg_type: str, address: str, egid: Optional[int], zones: list) -> str:
    """Generiert einen eindeutigen Cache-Key"""
    data = {
        "type": svg_type,
        "address": address,
        "egid": egid,
        "zones": zones
    }
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()


def generate_cross_section_with_zones(
    address: str,
    egid: Optional[int],
    width_m: float,
    floors: int,
    zones: list,
    svg_width: int = 800,
    svg_height: int = 600
) -> Optional[str]:
    """
    Generiert professionellen Gebäudeschnitt mit Höhenzonen via Claude API.
    Mit Caching - generierte SVGs werden gespeichert.
    """
    # Cache initialisieren
    _init_cache_db()

    # Cache-Key generieren
    cache_key = _generate_cache_key("cross-section", address, egid, zones)

    # Aus Cache laden
    cached = _get_cached_svg(cache_key)
    if cached:
        return cached

    logger.info(f"Generiere Cross-Section für: {address}")
    logger.info(f"Zonen-Input: {zones}")

    # Zonen-Text aufbereiten und vorhandene Typen sammeln
    zones_text = ""
    max_height = 0
    present_zone_types = set()

    for zone in zones:
        # Höhe aus verschiedenen möglichen Feldnamen extrahieren
        zone_height = (
            zone.get('building_height_m') or
            zone.get('traufhoehe_m') or
            zone.get('eave_height_m') or
            0
        )
        first_height = (
            zone.get('first_height_m') or
            zone.get('firsthoehe_m') or
            zone_height
        )
        max_height = max(max_height, first_height, zone_height)
        zone_type = zone.get('type', 'hauptgebaeude')
        present_zone_types.add(zone_type)
        zone_name = zone.get('name', 'Zone')
        description = zone.get('description', '')
        special = zone.get('special_scaffold', False)

        zones_text += f"""
   - **{zone_name}** (Typ: {zone_type})
     - Gebäudehöhe: {zone_height:.1f}m, Firsthöhe: {first_height:.1f}m
     - {description}{"" if not special else " - **Spezialgerüst erforderlich**"}"""

    num_layers = int(max_height / 2.0) + 1

    # Dynamische Zone-Typen Beschreibung (nur vorhandene Typen!)
    zone_type_descriptions = []
    if 'arkade' in present_zone_types:
        zone_type_descriptions.append("- arkade = Rechteck mit Rundbögen, Schraffur")
    if 'hauptgebaeude' in present_zone_types or not present_zone_types:
        zone_type_descriptions.append("- hauptgebaeude = Rechteck mit Geschosslinien und Giebeldach, Schraffur")
    if 'kuppel' in present_zone_types:
        zone_type_descriptions.append("- kuppel = Ellipse mit `url(#copper)` Gradient")
    if 'turm' in present_zone_types:
        zone_type_descriptions.append("- turm = Hoher schmaler Rechteck mit Spitzdach, Schraffur")

    zone_types_text = "\n   ".join(zone_type_descriptions) if zone_type_descriptions else "- hauptgebaeude = Rechteck mit Schraffur"

    prompt = f"""Du bist ein Experte für TECHNISCHE Architekturzeichnungen im SVG-Format.

## KRITISCHE REGEL

Zeichne NUR die Gebäudeteile die in "Höhenzonen" aufgelistet sind!
- KEINE zusätzlichen Elemente hinzufügen (keine Kuppeln, Türme, etc. wenn nicht in Daten)
- KEINE künstlerische Interpretation - NUR was in den Daten steht

## WICHTIG: STIL

TECHNISCH-PROFESSIONELL, NICHT künstlerisch!
- Hintergrund: REINWEISS (#FFFFFF) - KEIN Himmel, KEIN Gradient
- Gebäude: NUR Schraffur-Pattern, KEINE Vollfarben
- Perspektive: 2D Frontalansicht (Orthogonalprojektion)
- Farben: Nur Graustufen + wenige Akzentfarben für Gerüst

## Aufgabe

Erstelle einen **Gebäudeschnitt** als SVG.

## Gebäudedaten

- Adresse: {address}
- EGID: {egid or '-'}
- Geschosse: {floors}
- Breite: {width_m:.1f} m
- Maximale Höhe: {max_height:.1f} m

## Höhenzonen (NUR DIESE ZEICHNEN!)
{zones_text}

## Darstellung der Zone-Typen (NUR die oben genannten!)

   {zone_types_text}

## Anforderungen

1. **Weisser Hintergrund** - `<rect width="100%" height="100%" fill="white"/>`
2. **Terrain unten** - Horizontale Linie bei Y=90% mit `url(#ground)` Pattern
3. **Gebäude mit Schraffur** - `fill="url(#hatch)"` für alle Gebäudeteile
4. **Dachform** - Einfaches Satteldach (Dreieck) bei hauptgebaeude, KEINE Kuppel wenn nicht in Daten!
5. **Gerüst links und rechts** - Ständer #0066CC, Riegel, Beläge #8B4513
6. **Verankerungen** - Rote gestrichelte Linien #CC0000
7. **Höhenskala links** - Beschriftung von ±0.00 bis +{max_height:.0f}m in 5m Schritten
8. **Lagenbeschriftung rechts** - 1. Lage bis {num_layers}. Lage (alle 2m)

## SVG-Patterns (PFLICHT!)

```xml
<defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
</defs>
```

## Farben (STRIKT!)
- Hintergrund: #FFFFFF (weiss)
- Hauptlinien: #333333 (dunkelgrau)
- Gebäude: url(#hatch) Schraffur
- Gerüst: #0066CC (blau)
- Anker: #CC0000 (rot, gestrichelt)
- Belag: #8B4513 (braun)
- Text: #333333

## Output

SVG mit viewBox="0 0 {svg_width} {svg_height}". NUR SVG, keine Erklärungen.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}">
"""

    svg = _call_claude(prompt)

    # Im Cache speichern
    if svg:
        _save_to_cache(cache_key, "cross-section", str(egid) if egid else None, address, svg)

    return svg


def generate_elevation_with_zones(
    address: str,
    egid: Optional[int],
    width_m: float,
    floors: int,
    zones: list,
    svg_width: int = 800,
    svg_height: int = 600
) -> Optional[str]:
    """
    Generiert professionelle Fassadenansicht mit Höhenzonen via Claude API.
    Mit Caching - generierte SVGs werden gespeichert.
    """
    # Cache initialisieren
    _init_cache_db()

    # Cache-Key generieren
    cache_key = _generate_cache_key("elevation", address, egid, zones)

    # Aus Cache laden
    cached = _get_cached_svg(cache_key)
    if cached:
        return cached

    logger.info(f"Generiere Elevation für: {address}")
    logger.info(f"Zonen-Input: {zones}")

    # Zonen-Text aufbereiten und vorhandene Typen sammeln
    zones_text = ""
    max_height = 0
    present_zone_types = set()

    for zone in zones:
        # Höhe aus verschiedenen möglichen Feldnamen extrahieren
        zone_height = (
            zone.get('building_height_m') or
            zone.get('traufhoehe_m') or
            zone.get('eave_height_m') or
            0
        )
        first_height = (
            zone.get('first_height_m') or
            zone.get('firsthoehe_m') or
            zone_height
        )
        max_height = max(max_height, first_height, zone_height)
        zone_type = zone.get('type', 'hauptgebaeude')
        present_zone_types.add(zone_type)
        zone_name = zone.get('name', 'Zone')
        description = zone.get('description', '')
        special = zone.get('special_scaffold', False)

        zones_text += f"""
   - **{zone_name}** (Typ: {zone_type})
     - Gebäudehöhe: {zone_height:.1f}m, Firsthöhe: {first_height:.1f}m
     - {description}{"" if not special else " - **Spezialgerüst erforderlich**"}"""

    num_layers = int(max_height / 2.0) + 1

    # Dynamische Zone-Typen Beschreibung (nur vorhandene Typen!)
    zone_type_descriptions = []
    if 'arkade' in present_zone_types:
        zone_type_descriptions.append("- arkade = Rechteck mit Rundbögen, Schraffur-Füllung")
    if 'hauptgebaeude' in present_zone_types or not present_zone_types:
        zone_type_descriptions.append("- hauptgebaeude = Rechteck mit Geschosslinien und Giebeldach, Schraffur")
    if 'kuppel' in present_zone_types:
        zone_type_descriptions.append("- kuppel = Ellipse mit `url(#copper)` Gradient")
    if 'turm' in present_zone_types:
        zone_type_descriptions.append("- turm = Hoher schmaler Rechteck mit Spitzdach, Schraffur")

    zone_types_text = "\n   ".join(zone_type_descriptions) if zone_type_descriptions else "- hauptgebaeude = Rechteck mit Schraffur"

    prompt = f"""Du bist ein Experte für TECHNISCHE Architekturzeichnungen im SVG-Format.

## KRITISCHE REGEL

Zeichne NUR die Gebäudeteile die in "Höhenzonen" aufgelistet sind!
- KEINE zusätzlichen Elemente hinzufügen (keine Kuppeln, Türme, etc. wenn nicht in Daten)
- KEINE künstlerische Interpretation - NUR was in den Daten steht

## WICHTIG: STIL

TECHNISCH-PROFESSIONELL, NICHT künstlerisch!
- Hintergrund: REINWEISS (#FFFFFF) - KEIN Himmel, KEIN blauer Gradient!
- Gebäude: NUR Schraffur-Pattern, KEINE Vollfarben
- Perspektive: 2D Frontalansicht (Orthogonalprojektion)
- Farben: Graustufen + wenige Akzentfarben (nur Gerüst blau)

## Aufgabe

Erstelle eine **Fassadenansicht** (Elevation) als SVG.

## Gebäudedaten

- Adresse: {address}
- EGID: {egid or '-'}
- Geschosse: {floors}
- Fassadenbreite: {width_m:.1f} m
- Maximale Höhe: {max_height:.1f} m

## Höhenzonen (NUR DIESE ZEICHNEN!)
{zones_text}

## Darstellung der Zone-Typen (NUR die oben genannten!)

   {zone_types_text}

## Anforderungen

1. **Weisser Hintergrund** - `<rect width="100%" height="100%" fill="white"/>`
2. **Terrain unten** - Horizontale Linie bei Y=85% mit `url(#ground)` Pattern
3. **Frontalansicht** - 2D, keine Perspektive, keine 3D-Effekte
4. **Gebäude mit Schraffur** - `fill="url(#hatch)"` für alle Gebäudeteile
5. **Dachform** - Einfaches Satteldach (Dreieck) bei hauptgebaeude, KEINE Kuppel wenn nicht in Daten!
6. **Gerüst VOR Fassade** - Ständer #0066CC (vertikale Linien), Beläge #8B4513
7. **Verankerungen** - Gestrichelte Linien #CC0000, alle 4m vertikal
8. **Höhenskala links** - Beschriftung ±0.00 bis +{max_height:.0f}m in 5m Schritten
9. **Lagenbeschriftung rechts** - 1. Lage bis {num_layers}. Lage (alle 2m Höhe)

## SVG-Patterns (PFLICHT!)

```xml
<defs>
    <pattern id="hatch" patternUnits="userSpaceOnUse" width="8" height="8">
      <path d="M0,0 l8,8 M-2,6 l4,4 M6,-2 l4,4" stroke="#999" stroke-width="0.5"/>
    </pattern>
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="10">
      <path d="M0,10 L10,0 M10,10 L20,0" stroke="#666" stroke-width="0.5"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
</defs>
```

## Farben (STRIKT!)
- Hintergrund: #FFFFFF (weiss) - KEIN Himmel!
- Hauptlinien: #333333 (dunkelgrau)
- Gebäude: url(#hatch) Schraffur
- Gerüst: #0066CC (blau)
- Anker: #CC0000 (rot, gestrichelt)
- Belag: #8B4513 (braun)
- Text: #333333

## Output

SVG mit viewBox="0 0 {svg_width} {svg_height}". NUR SVG, keine Erklärungen.

<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}">
"""

    svg = _call_claude(prompt)

    # Im Cache speichern
    if svg:
        _save_to_cache(cache_key, "elevation", str(egid) if egid else None, address, svg)

    return svg


def is_available() -> bool:
    """Prüft ob Claude API verfügbar ist"""
    _init_client()
    return ANTHROPIC_AVAILABLE and anthropic_client is not None


def clear_cache(egid: Optional[str] = None, address: Optional[str] = None):
    """Löscht Cache-Einträge"""
    try:
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()
        if egid:
            cursor.execute("DELETE FROM svg_cache WHERE egid = ?", (egid,))
        elif address:
            cursor.execute("DELETE FROM svg_cache WHERE address = ?", (address,))
        else:
            cursor.execute("DELETE FROM svg_cache")
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"Cache cleared: {deleted} entries")
        return deleted
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return 0
