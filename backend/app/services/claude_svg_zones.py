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

    # Zonen-Text aufbereiten
    zones_text = ""
    max_height = 0
    for zone in zones:
        zone_height = zone.get('building_height_m', zone.get('eave_height_m', 0))
        first_height = zone.get('first_height_m', zone_height)
        max_height = max(max_height, first_height, zone_height)
        zone_type = zone.get('type', 'standard')
        zone_name = zone.get('name', 'Zone')
        description = zone.get('description', '')
        special = zone.get('special_scaffold', False)

        zones_text += f"""
   - **{zone_name}** (Typ: {zone_type})
     - Gebäudehöhe: {zone_height:.1f}m, Firsthöhe: {first_height:.1f}m
     - {description}{"" if not special else " - **Spezialgerüst erforderlich**"}"""

    num_layers = int(max_height / 2.0) + 1

    prompt = f"""Du bist ein Experte für technische Architekturzeichnungen im SVG-Format.

## Aufgabe

Erstelle einen **Gebäudeschnitt** als SVG basierend auf den folgenden Daten.
Der Stil soll professionell, architektonisch, handgezeichnet wirkend sein.

## Gebäudedaten

- Adresse: {address}
- EGID: {egid or '-'}
- Geschosse: {floors}
- Breite (Schnitt): {width_m:.1f} m

## Höhenzonen
{zones_text}

## Wichtige Anforderungen

1. **NUR die Grafik** - Kein Titelblock, keine Fusszeile
2. **Alle {len(zones)} Zonen darstellen** mit korrekter Höhe
3. **Zone-Typen:**
   - arkade = niedrig mit Rundbögen, Säulen
   - hauptgebaeude = mit Geschossdecken, Fenster
   - kuppel = Ellipse mit Kupfer-Gradient (fill="url(#copper)"), Laterne oben
4. **Gerüst links und rechts** - Ständer (blau #0066CC), Riegel, Beläge (braun #8B4513)
5. **Verankerungen** - Rote Punkte (#CC0000) alle 4m vertikal
6. **Höhenskala links** - ±0.00 bis +{max_height:.0f}m
7. **Lagenbeschriftung** - 1. Lage bis {num_layers}. Lage

## SVG-Patterns (verwenden!)

```xml
<defs>
    <pattern id="hatch-cut" patternUnits="userSpaceOnUse" width="6" height="6">
      <path d="M0,0 l6,6 M-1,5 l3,3 M5,-1 l3,3" stroke="#333" stroke-width="0.8"/>
    </pattern>
    <pattern id="ground" patternUnits="userSpaceOnUse" width="20" height="15">
      <path d="M0,15 L10,0 M10,15 L20,0" stroke="#666" stroke-width="0.5"/>
      <circle cx="5" cy="10" r="1.5" fill="#888"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
</defs>
```

## Farben
- Gerüst: #0066CC (blau)
- Anker: #CC0000 (rot)
- Belag: #8B4513 (braun)
- Gebäude-Schnitt: fill="url(#hatch-cut)"
- Kuppel: fill="url(#copper)"
- Fenster: #87CEEB

## Output

Generiere ein vollständiges, valides SVG mit viewBox="0 0 {svg_width} {svg_height}".
Gib NUR das SVG aus, keine Erklärungen.

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

    # Zonen-Text aufbereiten
    zones_text = ""
    max_height = 0
    for zone in zones:
        zone_height = zone.get('building_height_m', zone.get('eave_height_m', 0))
        first_height = zone.get('first_height_m', zone_height)
        max_height = max(max_height, first_height, zone_height)
        zone_type = zone.get('type', 'standard')
        zone_name = zone.get('name', 'Zone')
        description = zone.get('description', '')
        special = zone.get('special_scaffold', False)

        zones_text += f"""
   - **{zone_name}** (Typ: {zone_type})
     - Gebäudehöhe: {zone_height:.1f}m, Firsthöhe: {first_height:.1f}m
     - {description}{"" if not special else " - **Spezialgerüst erforderlich**"}"""

    num_layers = int(max_height / 2.0) + 1

    prompt = f"""Du bist ein Experte für technische Architekturzeichnungen im SVG-Format.

## Aufgabe

Erstelle eine **Fassadenansicht** (Elevation) als SVG basierend auf den folgenden Daten.
Der Stil soll professionell, architektonisch, handgezeichnet wirkend sein.

## Gebäudedaten

- Adresse: {address}
- EGID: {egid or '-'}
- Geschosse: {floors}
- Fassadenbreite: {width_m:.1f} m

## Höhenzonen
{zones_text}

## Wichtige Anforderungen

1. **NUR die Grafik** - Kein Titelblock, keine Fusszeile
2. **Frontalansicht** der Fassade (nicht Schnitt!)
3. **Alle {len(zones)} Zonen darstellen** mit korrekter Höhe
4. **Zone-Typen visuell:**
   - arkade = Rundbogen-Arkaden mit Säulen, Sandstein-Farbe
   - hauptgebaeude = Fensterreihen pro Geschoss, Fassadendetails
   - kuppel = Kuppelform mit Kupfer-Gradient, Laterne oben, Tambour mit Fenstern
5. **Gerüst VOR der Fassade** - Ständer (blau #0066CC), Riegel, Beläge (braun #8B4513)
6. **Verankerungen** - Rote Punkte (#CC0000) alle 4m vertikal, alle 4m horizontal
7. **Höhenskala links** - ±0.00 bis +{max_height:.0f}m
8. **Lagenbeschriftung rechts** - 1. Lage bis {num_layers}. Lage

## SVG-Patterns (verwenden!)

```xml
<defs>
    <pattern id="sandstone" patternUnits="userSpaceOnUse" width="20" height="10">
      <rect width="20" height="10" fill="#E8DCC8"/>
      <path d="M0,5 h20 M10,0 v10" stroke="#D4C4A8" stroke-width="0.5"/>
    </pattern>
    <linearGradient id="copper" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#7CB9A5"/>
      <stop offset="100%" style="stop-color:#4A8A77"/>
    </linearGradient>
    <linearGradient id="sky" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#87CEEB"/>
      <stop offset="100%" style="stop-color:#E0F0FF"/>
    </linearGradient>
</defs>
```

## Farben
- Hintergrund: url(#sky) oder #F5F5F5
- Fassade: #E8DCC8 (Sandstein) oder url(#sandstone)
- Fenster: #4A5568 mit hellem Rahmen
- Kuppel: url(#copper)
- Gerüst: #0066CC (blau)
- Anker: #CC0000 (rot)
- Belag: #8B4513 (braun)

## Output

Generiere ein vollständiges, valides SVG mit viewBox="0 0 {svg_width} {svg_height}".
Gib NUR das SVG aus, keine Erklärungen.

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
