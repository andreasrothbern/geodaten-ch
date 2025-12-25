"""
Claude API SVG Generator für Zone-basierte Gebäudeschnitte.

Features:
- Timeout: 90 Sekunden für Claude API
- Caching: SQLite-basiert, SVGs werden nach Generierung gespeichert
- Logging: Detaillierte Logs für Debugging
- Prompt-Selektor: Unterscheidet einfache und komplexe Gebäude

Version: 2.0 (mit Prompt-Selektor System)
Datum: 25.12.2025
"""

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

# Prompt-Selektor importieren
try:
    from app.services.svg_prompts import (
        get_elevation_prompt,
        get_cross_section_prompt,
        get_prompt_metadata,
        detect_building_complexity,
        BuildingComplexity,
    )
    PROMPT_SELECTOR_AVAILABLE = True
    logger.info("Prompt-Selektor System geladen")
except ImportError as e:
    PROMPT_SELECTOR_AVAILABLE = False
    logger.warning(f"Prompt-Selektor nicht verfügbar: {e}")

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


def _save_to_cache(cache_key: str, svg_type: str, egid: Optional[str], address: str,
                   svg_content: str, complexity: str = "unknown"):
    """Speichert SVG im Cache"""
    try:
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO svg_cache (cache_key, svg_type, egid, address, svg_content, complexity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cache_key, svg_type, egid, address, svg_content, complexity))
        conn.commit()
        conn.close()
        logger.info(f"Cache SAVE: {cache_key[:50]}... ({len(svg_content)} chars, complexity={complexity})")
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


def _generate_cache_key(svg_type: str, address: str, egid: Optional[int], zones: list,
                        building_data: Optional[dict] = None) -> str:
    """Generiert einen eindeutigen Cache-Key"""
    data = {
        "type": svg_type,
        "address": address,
        "egid": egid,
        "zones": zones,
        "v": "2.0"  # Version für Cache-Invalidierung bei Prompt-Änderungen
    }
    if building_data:
        # Relevante Felder für Komplexitäts-Erkennung
        data["gkat"] = building_data.get("gkat") or building_data.get("building_category_code")
        data["area"] = building_data.get("area_m2")
        data["sides"] = building_data.get("sides")
    json_str = json.dumps(data, sort_keys=True)
    return hashlib.md5(json_str.encode()).hexdigest()


def _prepare_building_data(
    address: str,
    egid: Optional[int],
    width_m: float,
    floors: int,
    zones: list,
    building_data: Optional[dict] = None
) -> Dict[str, Any]:
    """Bereitet building_data für Prompt-Selektor vor"""

    # Basis-Daten
    data = {
        "address": address,
        "adresse": address,
        "egid": egid,
        "width_m": width_m,
        "fassadenbreite_m": width_m,
        "facade_length_m": width_m,
        "floors": floors,
        "geschosse": floors,
        "gastw": floors,
    }

    # Zusätzliche Daten übernehmen wenn vorhanden
    if building_data:
        data.update({
            "gkat": building_data.get("gkat") or building_data.get("building_category_code"),
            "building_category_code": building_data.get("building_category_code") or building_data.get("gkat"),
            "area_m2": building_data.get("area_m2") or building_data.get("garea"),
            "garea": building_data.get("garea") or building_data.get("area_m2"),
            "sides": building_data.get("sides") or building_data.get("polygon_points", 4),
            "polygon_points": building_data.get("polygon_points") or building_data.get("sides", 4),
        })

    # Höhen aus Zonen extrahieren
    if zones:
        max_height = 0
        for zone in zones:
            h = (zone.get('gebaeudehoehe_m') or zone.get('firsthoehe_m') or
                 zone.get('first_height_m') or zone.get('building_height_m', 0))
            if h > max_height:
                max_height = h

        if max_height > 0:
            data["hoehe_m"] = max_height
            data["gebaeudehoehe_m"] = max_height

    return data


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

    Verwendet den Prompt-Selektor um zwischen einfachen und komplexen
    Gebäuden zu unterscheiden.

    Args:
        address: Gebäudeadresse
        egid: Eidg. Gebäudeidentifikator (optional)
        width_m: Gebäudebreite in Metern
        floors: Anzahl Geschosse
        zones: Liste der Höhenzonen
        svg_width: SVG-Breite in Pixel
        svg_height: SVG-Höhe in Pixel
        building_data: Zusätzliche Gebäudedaten (gkat, area_m2, sides)

    Returns:
        SVG-String oder None bei Fehler
    """
    # Cache initialisieren
    _init_cache_db()

    # Cache-Key generieren
    cache_key = _generate_cache_key("cross-section", address, egid, zones, building_data)

    # Aus Cache laden
    cached = _get_cached_svg(cache_key)
    if cached:
        return cached

    logger.info(f"Generiere Cross-Section für: {address}")
    logger.info(f"Zonen-Input: {zones}")

    # Building-Data für Prompt-Selektor vorbereiten
    prepared_data = _prepare_building_data(address, egid, width_m, floors, zones, building_data)

    # Komplexität ermitteln und loggen
    complexity = "unknown"
    if PROMPT_SELECTOR_AVAILABLE:
        metadata = get_prompt_metadata(zones, prepared_data)
        complexity = metadata.get("complexity", "unknown")
        logger.info(f"Gebäude-Komplexität: {complexity}")
        logger.info(f"Prompt-Metadata: {metadata}")

        # Prompt vom Selektor generieren
        prompt = get_cross_section_prompt(zones, prepared_data, None)
    else:
        # Fallback: Einfacher Prompt (ohne Kuppel-Referenzen)
        logger.warning("Prompt-Selektor nicht verfügbar, verwende Fallback")
        prompt = _generate_fallback_cross_section_prompt(
            address, egid, width_m, floors, zones, svg_width, svg_height
        )

    svg = _call_claude(prompt)

    # Im Cache speichern
    if svg:
        _save_to_cache(cache_key, "cross-section", str(egid) if egid else None,
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

    Verwendet den Prompt-Selektor um zwischen einfachen und komplexen
    Gebäuden zu unterscheiden.

    Args:
        address: Gebäudeadresse
        egid: Eidg. Gebäudeidentifikator (optional)
        width_m: Fassadenbreite in Metern
        floors: Anzahl Geschosse
        zones: Liste der Höhenzonen
        svg_width: SVG-Breite in Pixel
        svg_height: SVG-Höhe in Pixel
        building_data: Zusätzliche Gebäudedaten (gkat, area_m2, sides)

    Returns:
        SVG-String oder None bei Fehler
    """
    # Cache initialisieren
    _init_cache_db()

    # Cache-Key generieren
    cache_key = _generate_cache_key("elevation", address, egid, zones, building_data)

    # Aus Cache laden
    cached = _get_cached_svg(cache_key)
    if cached:
        return cached

    logger.info(f"Generiere Elevation für: {address}")
    logger.info(f"Zonen-Input: {zones}")

    # Building-Data für Prompt-Selektor vorbereiten
    prepared_data = _prepare_building_data(address, egid, width_m, floors, zones, building_data)

    # Komplexität ermitteln und loggen
    complexity = "unknown"
    if PROMPT_SELECTOR_AVAILABLE:
        metadata = get_prompt_metadata(zones, prepared_data)
        complexity = metadata.get("complexity", "unknown")
        logger.info(f"Gebäude-Komplexität: {complexity}")
        logger.info(f"Prompt-Metadata: {metadata}")

        # Prompt vom Selektor generieren
        prompt = get_elevation_prompt(zones, prepared_data, None)
    else:
        # Fallback: Einfacher Prompt (ohne Kuppel-Referenzen)
        logger.warning("Prompt-Selektor nicht verfügbar, verwende Fallback")
        prompt = _generate_fallback_elevation_prompt(
            address, egid, width_m, floors, zones, svg_width, svg_height
        )

    svg = _call_claude(prompt)

    # Im Cache speichern
    if svg:
        _save_to_cache(cache_key, "elevation", str(egid) if egid else None,
                       address, svg, complexity)

    return svg


def _generate_fallback_cross_section_prompt(
    address: str, egid: Optional[int], width_m: float, floors: int,
    zones: list, svg_width: int, svg_height: int
) -> str:
    """Fallback-Prompt wenn Prompt-Selektor nicht verfügbar"""

    max_height = 10
    for zone in zones:
        h = (zone.get('gebaeudehoehe_m') or zone.get('firsthoehe_m') or
             zone.get('first_height_m') or zone.get('building_height_m', 0))
        if h > max_height:
            max_height = h

    return f"""Erstelle einen technischen Gebäudeschnitt als SVG.

KRITISCH: Dies ist ein EINFACHES Gebäude. KEINE Kuppeln, KEINE Türme, KEINE Arkaden!

Gebäude: {address}, {floors} Geschosse, {width_m:.1f}m breit, {max_height:.1f}m hoch

Zeichne:
- Weisser Hintergrund
- Rechteckiges Gebäude mit Satteldach (Dreieck)
- Schraffur-Muster für Füllung
- Gerüst links und rechts (blau #0066CC)
- Höhenskala links (0 bis +{max_height:.0f}m)

SVG viewBox="0 0 {svg_width} {svg_height}". NUR SVG, keine Erklärungen."""


def _generate_fallback_elevation_prompt(
    address: str, egid: Optional[int], width_m: float, floors: int,
    zones: list, svg_width: int, svg_height: int
) -> str:
    """Fallback-Prompt wenn Prompt-Selektor nicht verfügbar"""

    max_height = 10
    for zone in zones:
        h = (zone.get('gebaeudehoehe_m') or zone.get('firsthoehe_m') or
             zone.get('first_height_m') or zone.get('building_height_m', 0))
        if h > max_height:
            max_height = h

    return f"""Erstelle eine technische Fassadenansicht als SVG.

KRITISCH: Dies ist ein EINFACHES Gebäude. KEINE Kuppeln, KEINE Türme, KEINE Arkaden!

Gebäude: {address}, {floors} Geschosse, {width_m:.1f}m breit, {max_height:.1f}m hoch

Zeichne:
- Weisser Hintergrund (KEIN Himmel!)
- Rechteckiges Gebäude mit Satteldach (Dreieck)
- Schraffur-Muster für Füllung
- Gerüst vor der Fassade (blau #0066CC)
- Höhenskala links (0 bis +{max_height:.0f}m)
- Lagenbeschriftung rechts

SVG viewBox="0 0 {svg_width} {svg_height}". NUR SVG, keine Erklärungen."""


def is_available() -> bool:
    """Prüft ob Claude API verfügbar ist"""
    _init_client()
    return ANTHROPIC_AVAILABLE and anthropic_client is not None


def clear_cache(egid: Optional[str] = None, address: Optional[str] = None):
    """Löscht Cache-Einträge"""
    try:
        _init_cache_db()
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()
        if egid:
            cursor.execute("DELETE FROM svg_cache WHERE egid = ?", (egid,))
        elif address:
            cursor.execute("DELETE FROM svg_cache WHERE address LIKE ?", (f"%{address}%",))
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


def get_cache_stats() -> Dict[str, Any]:
    """Gibt Cache-Statistiken zurück"""
    try:
        _init_cache_db()
        conn = sqlite3.connect(str(CACHE_DB_PATH))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM svg_cache")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT complexity, COUNT(*) FROM svg_cache GROUP BY complexity")
        by_complexity = dict(cursor.fetchall())

        cursor.execute("SELECT svg_type, COUNT(*) FROM svg_cache GROUP BY svg_type")
        by_type = dict(cursor.fetchall())

        conn.close()

        return {
            "total_entries": total,
            "by_complexity": by_complexity,
            "by_type": by_type
        }
    except Exception as e:
        logger.error(f"Cache stats error: {e}")
        return {"error": str(e)}
