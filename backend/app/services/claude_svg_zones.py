"""
Claude API SVG Generator für Zone-basierte Gebäudeschnitte.

Version: 3.0 - Einheitliches Prompt-System
Datum: 29.12.2025

Verwendet den zentralen PromptBuilder (prompts/prompt_builder.py) für
identische Prompts bei Export UND automatischer SVG-Generierung.

Features:
- Einheitlicher Prompt für Export und API-Generierung
- Dynamische Gebäude-Recherche via Claude Haiku (gecacht)
- SVG-Caching in SQLite
- 90 Sekunden Timeout für Claude API
"""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

# Logging konfigurieren
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# PromptBuilder importieren (NEU - einheitliches System)
PROMPT_BUILDER_AVAILABLE = False
try:
    from app.services.prompts import get_prompt_builder
    PROMPT_BUILDER_AVAILABLE = True
    logger.info("PromptBuilder System geladen (einheitliche Prompts)")
except ImportError as e:
    logger.warning(f"PromptBuilder nicht verfügbar: {e}")

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
            complexity TEXT,
            prompt_version TEXT DEFAULT '3.0',
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
        # Nur Version 3.0 Cache verwenden (neue Prompts)
        cursor.execute(
            "SELECT svg_content FROM svg_cache WHERE cache_key = ? AND prompt_version = '3.0'",
            (cache_key,)
        )
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


def _save_to_cache(cache_key: str, svg_type: str, egid: Optional[str], address: str,
                   svg_content: str, complexity: str = "unknown"):
    """Speichert SVG im Cache"""
    try:
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO svg_cache
            (cache_key, svg_type, egid, address, svg_content, complexity, prompt_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, '3.0', CURRENT_TIMESTAMP)
        """, (cache_key, svg_type, egid, address, svg_content, complexity))
        conn.commit()
        conn.close()
        logger.info(f"SVG cached: {cache_key[:50]}... ({len(svg_content)} chars)")
    except Exception as e:
        logger.error(f"Cache write error: {e}")


def is_available() -> bool:
    """Prüft ob Claude API verfügbar ist"""
    return ANTHROPIC_AVAILABLE and os.getenv("ANTHROPIC_API_KEY") is not None


def _call_claude(prompt: str, timeout: int = 90) -> Optional[str]:
    """Ruft Claude API auf mit Timeout"""
    if not ANTHROPIC_AVAILABLE:
        logger.error("Anthropic SDK nicht verfügbar")
        return None

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY nicht gesetzt")
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)

        start_time = time.time()
        logger.info(f"Claude API Aufruf gestartet (timeout: {timeout}s)")
        logger.info(f"Prompt-Länge: {len(prompt)} chars")

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            timeout=timeout,
            messages=[{"role": "user", "content": prompt}]
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
        logger.error(f"Claude API ERROR: {e}")
        return None
    except Exception as e:
        logger.error(f"Claude API EXCEPTION: {e}")
        return None


def _generate_cache_key(svg_type: str, address: str, egid: Optional[int], zones: list,
                        building_data: Optional[dict] = None) -> str:
    """Generiert einen eindeutigen Cache-Key"""
    data = {
        "type": svg_type,
        "address": address,
        "egid": egid,
        "zones": zones,
        "v": "3.0"  # Version für Cache-Invalidierung bei Prompt-Änderungen
    }
    if building_data:
        # Relevante Felder für Komplexitäts-Erkennung
        data["gkat"] = building_data.get("gkat") or building_data.get("building_category_code")
        data["area"] = building_data.get("area_m2")
        data["terrain"] = building_data.get("terrain_height_m")
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()


async def _build_unified_prompt(
    svg_type: str,
    address: str,
    egid: Optional[int],
    width_m: float,
    floors: int,
    zones: list,
    building_data: Optional[dict] = None
) -> str:
    """
    Baut den einheitlichen Prompt via PromptBuilder.

    IDENTISCHER Prompt für Export UND automatische SVG-Generierung!
    """
    if not PROMPT_BUILDER_AVAILABLE:
        return _generate_fallback_prompt(svg_type, address, egid, width_m, floors, zones)

    builder = get_prompt_builder()

    # Dimensionen aus Zonen extrahieren
    max_height = 0
    max_trauf = 0
    for zone in zones:
        h = (zone.get('gebaeudehoehe_m') or zone.get('firsthoehe_m') or
             zone.get('first_height_m') or zone.get('building_height_m', 0))
        t = zone.get('traufhoehe_m', 0)
        if h > max_height:
            max_height = h
        if t > max_trauf:
            max_trauf = t

    dimensions = {
        "traufhoehe_m": max_trauf or (max_height * 0.85 if max_height else None),
        "firsthoehe_m": max_height or None,
        "floors": floors,
        "footprint_area_m2": building_data.get("area_m2") if building_data else None
    }

    # GWR-Daten
    gwr_data = None
    if building_data:
        gwr_data = {
            "building_category": building_data.get("building_category"),
            "construction_year": building_data.get("construction_year"),
            "floors": floors,
            "area_m2_gwr": building_data.get("area_m2")
        }

    # Terrain
    terrain = None
    if building_data and building_data.get("terrain_height_m"):
        terrain = {
            "terrain_height_m": building_data.get("terrain_height_m"),
            "terrain_slope_m": building_data.get("terrain_slope_m")
        }

    # Koordinaten
    coordinates = None
    if building_data:
        e = building_data.get("lv95_e")
        n = building_data.get("lv95_n")
        if e and n:
            coordinates = (e, n)

    # Polygon/Sides
    polygon = building_data.get("polygon") if building_data else None
    sides = building_data.get("sides") if building_data else None

    # Prompt generieren (inkl. dynamischer Recherche!)
    prompt = await builder.build_svg_prompt(
        adresse=address,
        egid=str(egid) if egid else None,
        coordinates=coordinates,
        dimensions=dimensions,
        gwr_data=gwr_data,
        terrain=terrain,
        roof=building_data.get("roof") if building_data else None,
        polygon=polygon,
        sides=sides,
        zones=zones,
        svg_type=svg_type,  # "schnitt" oder "ansicht"
        include_research=True  # Dynamische Recherche aktivieren!
    )

    return prompt


def _generate_fallback_prompt(
    svg_type: str,
    address: str,
    egid: Optional[int],
    width_m: float,
    floors: int,
    zones: list
) -> str:
    """Fallback-Prompt wenn PromptBuilder nicht verfügbar"""

    max_height = 10
    for zone in zones:
        h = (zone.get('gebaeudehoehe_m') or zone.get('firsthoehe_m') or
             zone.get('first_height_m') or zone.get('building_height_m', 0))
        if h > max_height:
            max_height = h

    svg_type_name = "Gebäudeschnitt" if svg_type == "schnitt" else "Fassadenansicht"

    return f"""# SVG-Generierung: {svg_type_name}

## Gebäude
- Adresse: {address}
- EGID: {egid or '-'}
- Breite: {width_m:.1f}m
- Höhe: {max_height:.1f}m
- Geschosse: {floors}

## Anforderungen
- Weisser Hintergrund (#FFFFFF)
- Gebäude mit Schraffur-Pattern (url(#hatch))
- Gerüst links und rechts (blau #0066CC)
- Höhenskala links (0 bis +{max_height:.0f}m)
- viewBox="0 0 700 480"

## Zonen
{json.dumps(zones, indent=2, ensure_ascii=False)}

Erstelle NUR den SVG-Code, keine Erklärungen.
"""


def generate_cross_section_with_zones(
    address: str,
    egid: Optional[int],
    width_m: float,
    floors: int,
    zones: list,
    svg_width: int = 800,
    svg_height: int = 600,
    building_data: Optional[dict] = None
) -> Optional[str]:
    """
    Generiert professionellen Gebäudeschnitt mit Höhenzonen via Claude API.

    Verwendet den EINHEITLICHEN PromptBuilder - identischer Prompt wie Export!

    Args:
        address: Gebäudeadresse
        egid: Eidg. Gebäudeidentifikator (optional)
        width_m: Gebäudebreite in Metern
        floors: Anzahl Geschosse
        zones: Liste der Höhenzonen
        svg_width: SVG-Breite in Pixel (für Kompatibilität, wird ignoriert)
        svg_height: SVG-Höhe in Pixel (für Kompatibilität, wird ignoriert)
        building_data: Zusätzliche Gebäudedaten (gkat, area_m2, terrain, etc.)

    Returns:
        SVG-String oder None bei Fehler
    """
    # Cache initialisieren
    _init_cache_db()

    # Cache-Key generieren
    cache_key = _generate_cache_key("schnitt", address, egid, zones, building_data)

    # Aus Cache laden
    cached = _get_cached_svg(cache_key)
    if cached:
        return cached

    logger.info(f"Generiere Schnitt für: {address}")
    logger.info(f"Zonen-Input: {zones}")

    # Einheitlichen Prompt generieren (async)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    prompt = loop.run_until_complete(
        _build_unified_prompt("schnitt", address, egid, width_m, floors, zones, building_data)
    )

    logger.info(f"Prompt generiert ({len(prompt)} chars)")

    # Claude API aufrufen
    svg = _call_claude(prompt)

    # Im Cache speichern
    if svg:
        complexity = "unified"  # Neues System
        _save_to_cache(cache_key, "schnitt", str(egid) if egid else None,
                       address, svg, complexity)

    return svg


def generate_elevation_with_zones(
    address: str,
    egid: Optional[int],
    width_m: float,
    floors: int,
    zones: list,
    svg_width: int = 800,
    svg_height: int = 600,
    building_data: Optional[dict] = None
) -> Optional[str]:
    """
    Generiert professionelle Fassadenansicht mit Höhenzonen via Claude API.

    Verwendet den EINHEITLICHEN PromptBuilder - identischer Prompt wie Export!

    Args:
        address: Gebäudeadresse
        egid: Eidg. Gebäudeidentifikator (optional)
        width_m: Fassadenbreite in Metern
        floors: Anzahl Geschosse
        zones: Liste der Höhenzonen
        svg_width: SVG-Breite in Pixel (für Kompatibilität, wird ignoriert)
        svg_height: SVG-Höhe in Pixel (für Kompatibilität, wird ignoriert)
        building_data: Zusätzliche Gebäudedaten (gkat, area_m2, terrain, etc.)

    Returns:
        SVG-String oder None bei Fehler
    """
    # Cache initialisieren
    _init_cache_db()

    # Cache-Key generieren
    cache_key = _generate_cache_key("ansicht", address, egid, zones, building_data)

    # Aus Cache laden
    cached = _get_cached_svg(cache_key)
    if cached:
        return cached

    logger.info(f"Generiere Ansicht für: {address}")
    logger.info(f"Zonen-Input: {zones}")

    # Einheitlichen Prompt generieren (async)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    prompt = loop.run_until_complete(
        _build_unified_prompt("ansicht", address, egid, width_m, floors, zones, building_data)
    )

    logger.info(f"Prompt generiert ({len(prompt)} chars)")

    # Claude API aufrufen
    svg = _call_claude(prompt)

    # Im Cache speichern
    if svg:
        complexity = "unified"  # Neues System
        _save_to_cache(cache_key, "ansicht", str(egid) if egid else None,
                       address, svg, complexity)

    return svg


def clear_svg_cache(egid: Optional[str] = None, svg_type: Optional[str] = None):
    """
    Löscht SVG-Cache Einträge.

    Args:
        egid: Nur für dieses Gebäude löschen (optional)
        svg_type: Nur diesen Typ löschen: 'schnitt', 'ansicht' (optional)
    """
    try:
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()

        if egid and svg_type:
            cursor.execute("DELETE FROM svg_cache WHERE egid = ? AND svg_type = ?", (egid, svg_type))
        elif egid:
            cursor.execute("DELETE FROM svg_cache WHERE egid = ?", (egid,))
        elif svg_type:
            cursor.execute("DELETE FROM svg_cache WHERE svg_type = ?", (svg_type,))
        else:
            cursor.execute("DELETE FROM svg_cache")

        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        logger.info(f"Cache gelöscht: {deleted} Einträge")
        return deleted
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return 0
