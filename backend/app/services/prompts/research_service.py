# backend/app/services/prompts/research_service.py
"""
Claude Research Service
========================

Dynamische Gebäude-Recherche via Claude API mit Caching.

Anstatt statischer Building-Hints wird Claude aufgefordert,
unbekannte Gebäude zu recherchieren. Die Ergebnisse werden
in der SQLite-Datenbank gecacht (30 Tage TTL).

Kosten:
- Pro Recherche: ca. $0.01-0.02 (Haiku)
- Gecachte Anfragen: $0.00

Verwendung:
    from app.services.prompts import get_research_service

    service = get_research_service()
    research = await service.get_building_research(
        adresse="Bundesplatz 3, 3011 Bern",
        egid="2242547",
        coordinates=(2600450, 1199830)
    )

Stand: 29.12.2025
"""

import os
import json
import hashlib
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# Datenbank-Pfad
DATA_DIR = Path(os.getenv("DATA_DIR", "app/data"))
DB_PATH = DATA_DIR / "building_contexts.db"

# Cache-Konfiguration
CACHE_TTL_DAYS = 30
RESEARCH_MODEL = "claude-3-haiku-20240307"  # Schnell und günstig für Recherche


@dataclass
class BuildingResearch:
    """Ergebnis einer Gebäude-Recherche"""
    # Identifikation
    egid: Optional[str] = None
    adresse: Optional[str] = None

    # Recherche-Ergebnisse
    building_name: Optional[str] = None
    building_type: Optional[str] = None  # Kirche, Rathaus, Wohnhaus, etc.
    architectural_style: Optional[str] = None  # Neugotik, Barock, Modern, etc.
    construction_year: Optional[int] = None

    # Höhenzonen-Hints
    suggested_zones: List[Dict[str, Any]] = field(default_factory=list)

    # Architektur-Merkmale
    tower_config: Optional[Dict[str, Any]] = None  # Anzahl, Position, Form
    special_features: List[str] = field(default_factory=list)  # Kuppel, Arkaden, etc.
    facade_style: Optional[str] = None  # Fensterformen, Portal, etc.

    # Meta
    source: str = "claude_research"  # "claude_research", "cache", "fallback"
    confidence: float = 0.8
    researched_at: Optional[str] = None

    def to_hints(self) -> str:
        """Konvertiert Research zu Building-Hints String für Prompt"""
        if not self.building_name and not self.building_type:
            return ""

        lines = []

        if self.building_name:
            lines.append(f"GEBÄUDE: {self.building_name}")

        if self.building_type:
            lines.append(f"Typ: {self.building_type}")

        if self.architectural_style:
            lines.append(f"Baustil: {self.architectural_style}")

        if self.construction_year:
            lines.append(f"Baujahr: {self.construction_year}")

        if self.tower_config:
            tc = self.tower_config
            tower_desc = f"Turm: {tc.get('count', 1)}x {tc.get('position', 'zentral')}"
            if tc.get('form'):
                tower_desc += f" ({tc['form']})"
            if tc.get('height_m'):
                tower_desc += f", ca. {tc['height_m']}m"
            lines.append(tower_desc)

        if self.special_features:
            lines.append(f"Besonderheiten: {', '.join(self.special_features)}")

        if self.suggested_zones:
            lines.append("\nVorgeschlagene Höhenzonen:")
            for zone in self.suggested_zones:
                zone_line = f"- {zone.get('name', 'Zone')}: "
                if zone.get('height_m'):
                    zone_line += f"{zone['height_m']}m"
                if zone.get('type'):
                    zone_line += f" ({zone['type']})"
                if zone.get('scaffolding') is False:
                    zone_line += " [Spezialgerüst]"
                lines.append(zone_line)

        return "\n".join(lines)


class ClaudeResearchService:
    """Service für dynamische Gebäude-Recherche via Claude API"""

    def __init__(self):
        self._ensure_table()
        self._client = None

    def _ensure_table(self):
        """Stellt sicher, dass die Cache-Tabelle existiert"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claude_research_cache (
                id TEXT PRIMARY KEY,
                egid TEXT,
                adresse TEXT,
                query_hash TEXT NOT NULL,
                research_type TEXT NOT NULL,
                response_json TEXT NOT NULL,
                tokens_used INTEGER,
                cost_usd REAL,
                model TEXT,
                created_at TEXT,
                expires_at TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_research_query
            ON claude_research_cache(query_hash)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_research_egid
            ON claude_research_cache(egid)
        """)

        conn.commit()
        conn.close()

    def _get_client(self):
        """Lazy-load Anthropic client"""
        if self._client is None:
            try:
                from anthropic import Anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    logger.warning("ANTHROPIC_API_KEY nicht gesetzt")
                    return None
                self._client = Anthropic(api_key=api_key)
            except ImportError:
                logger.warning("anthropic package nicht installiert")
                return None
        return self._client

    def _query_hash(self, adresse: str, egid: Optional[str]) -> str:
        """Erstellt Hash für Cache-Key"""
        key = f"{adresse or ''}|{egid or ''}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _get_cached(self, query_hash: str) -> Optional[BuildingResearch]:
        """Holt gecachte Recherche falls vorhanden und nicht abgelaufen"""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT response_json, expires_at
            FROM claude_research_cache
            WHERE query_hash = ? AND research_type = 'building_info'
            ORDER BY created_at DESC
            LIMIT 1
        """, (query_hash,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        # Expiration prüfen
        expires_at = datetime.fromisoformat(row['expires_at'])
        if datetime.now() > expires_at:
            logger.info(f"Cache expired for {query_hash}")
            return None

        try:
            data = json.loads(row['response_json'])
            research = BuildingResearch(**data)
            research.source = "cache"
            return research
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Cache parse error: {e}")
            return None

    def _save_to_cache(
        self,
        query_hash: str,
        research: BuildingResearch,
        egid: Optional[str],
        adresse: Optional[str],
        tokens_used: int = 0,
        cost_usd: float = 0.0
    ):
        """Speichert Recherche-Ergebnis im Cache"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        now = datetime.now()
        expires = now + timedelta(days=CACHE_TTL_DAYS)

        cache_id = f"research_{query_hash}_{now.strftime('%Y%m%d%H%M%S')}"

        cursor.execute("""
            INSERT OR REPLACE INTO claude_research_cache
            (id, egid, adresse, query_hash, research_type, response_json,
             tokens_used, cost_usd, model, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cache_id,
            egid,
            adresse,
            query_hash,
            "building_info",
            json.dumps(asdict(research), ensure_ascii=False),
            tokens_used,
            cost_usd,
            RESEARCH_MODEL,
            now.isoformat(),
            expires.isoformat()
        ))

        conn.commit()
        conn.close()
        logger.info(f"Research cached: {cache_id}")

    async def get_building_research(
        self,
        adresse: Optional[str] = None,
        egid: Optional[str] = None,
        coordinates: Optional[tuple] = None,
        gwr_data: Optional[Dict[str, Any]] = None,
        force_refresh: bool = False
    ) -> BuildingResearch:
        """
        Recherchiert Gebäude-Informationen.

        1. Prüft Cache
        2. Bei Miss: Claude API Recherche
        3. Speichert Ergebnis im Cache

        Args:
            adresse: Vollständige Adresse
            egid: EGID des Gebäudes
            coordinates: (E, N) LV95 Koordinaten
            gwr_data: Optionale GWR-Daten zur Verbesserung der Recherche
            force_refresh: Cache ignorieren

        Returns:
            BuildingResearch mit Gebäude-Informationen
        """
        query_hash = self._query_hash(adresse, egid)

        # 1. Cache prüfen (wenn nicht force_refresh)
        if not force_refresh:
            cached = self._get_cached(query_hash)
            if cached:
                logger.info(f"Cache hit for {adresse or egid}")
                return cached

        # 2. Claude API Recherche
        client = self._get_client()
        if not client:
            logger.warning("Claude client nicht verfügbar, verwende Fallback")
            return self._fallback_research(adresse, egid, gwr_data)

        try:
            research = await self._claude_research(
                client, adresse, egid, coordinates, gwr_data
            )

            # 3. Cache speichern
            self._save_to_cache(
                query_hash, research, egid, adresse,
                tokens_used=research.confidence * 1000,  # Approx
                cost_usd=0.01  # Approx für Haiku
            )

            return research

        except Exception as e:
            logger.error(f"Claude research failed: {e}")
            return self._fallback_research(adresse, egid, gwr_data)

    async def _claude_research(
        self,
        client,
        adresse: Optional[str],
        egid: Optional[str],
        coordinates: Optional[tuple],
        gwr_data: Optional[Dict[str, Any]]
    ) -> BuildingResearch:
        """Führt die eigentliche Claude-Recherche durch"""

        # Kontext aufbauen
        context_parts = []
        if adresse:
            context_parts.append(f"Adresse: {adresse}")
        if egid:
            context_parts.append(f"EGID: {egid}")
        if coordinates:
            context_parts.append(f"Koordinaten (LV95): E {coordinates[0]}, N {coordinates[1]}")
        if gwr_data:
            if gwr_data.get('building_category'):
                context_parts.append(f"GWR-Kategorie: {gwr_data['building_category']}")
            if gwr_data.get('construction_year'):
                context_parts.append(f"Baujahr (GWR): {gwr_data['construction_year']}")
            if gwr_data.get('floors'):
                context_parts.append(f"Geschosse (GWR): {gwr_data['floors']}")

        context = "\n".join(context_parts)

        prompt = f"""Recherchiere dieses Schweizer Gebäude und gib strukturierte Informationen zurück.

{context}

WICHTIG:
- Beachte die EXAKTE Hausnummer - verschiedene Hausnummern in derselben Strasse sind unterschiedliche Gebäude!
- Die GWR-Kategorie (falls angegeben) ist ein starker Hinweis auf den Gebäudetyp.
- Bei Strassen wie "Rathausgasse", "Münstergasse", "Kirchgasse" etc. kann das Gebäude an dieser Adresse
  ein ANDERES Gebäude sein als das namensgebende (z.B. Rathausgasse 2 ≠ Rathaus).

Aufgaben:
1. Identifiziere das EXAKTE Gebäude an dieser Hausnummer (Name, falls bekannt/historisch)
2. Bestimme den Gebäudetyp (Wohnhaus, Kirche, öffentliches Gebäude, etc.) - GWR-Kategorie beachten!
3. Ermittle den Baustil falls erkennbar (Neugotik, Barock, Klassizismus, Modern, etc.)
4. Beschreibe Türme/Kuppeln falls vorhanden (Anzahl, Position, ungefähre Höhe)
5. Liste besondere architektonische Merkmale
6. Schlage Höhenzonen vor falls das Gebäude komplex erscheint

Antworte NUR im folgenden JSON-Format:
{{
  "building_name": "Name oder null",
  "building_type": "Typ",
  "architectural_style": "Stil oder null",
  "construction_year": Jahr oder null,
  "tower_config": {{"count": Anzahl, "position": "zentral/west/flankierend", "form": "Spitzhelm/Kuppel/etc", "height_m": Höhe}} oder null,
  "special_features": ["Feature1", "Feature2"],
  "facade_style": "Beschreibung oder null",
  "suggested_zones": [
    {{"name": "Hauptgebäude", "type": "hauptgebaeude", "height_m": 20, "scaffolding": true}},
    {{"name": "Turm", "type": "turm", "height_m": 60, "scaffolding": false}}
  ],
  "confidence": 0.0-1.0
}}

Falls du das Gebäude nicht identifizieren kannst, setze confidence auf 0.3 und gib generische Werte basierend auf GWR-Daten zurück."""

        # Synchroner API-Aufruf (Anthropic SDK ist sync)
        import asyncio

        def _call_claude():
            return client.messages.create(
                model=RESEARCH_MODEL,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

        # In Thread ausführen für async compatibility
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _call_claude)

        # Response parsen
        try:
            content = response.content[0].text
            # JSON extrahieren (kann in Markdown-Block sein)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            research = BuildingResearch(
                egid=egid,
                adresse=adresse,
                building_name=data.get('building_name'),
                building_type=data.get('building_type'),
                architectural_style=data.get('architectural_style'),
                construction_year=data.get('construction_year'),
                tower_config=data.get('tower_config'),
                special_features=data.get('special_features', []),
                facade_style=data.get('facade_style'),
                suggested_zones=data.get('suggested_zones', []),
                source="claude_research",
                confidence=data.get('confidence', 0.7),
                researched_at=datetime.now().isoformat()
            )

            return research

        except (json.JSONDecodeError, IndexError, KeyError) as e:
            logger.error(f"Failed to parse Claude response: {e}")
            return self._fallback_research(adresse, egid, gwr_data)

    def _fallback_research(
        self,
        adresse: Optional[str],
        egid: Optional[str],
        gwr_data: Optional[Dict[str, Any]]
    ) -> BuildingResearch:
        """Fallback wenn Claude nicht verfügbar"""

        building_type = "Wohngebäude"
        if gwr_data:
            category = (gwr_data.get('building_category') or '').lower()
            if 'kirche' in category or 'religiös' in category:
                building_type = "Sakralbau"
            elif 'öffentlich' in category or 'verwaltung' in category:
                building_type = "Öffentliches Gebäude"
            elif 'mehrfamilien' in category:
                building_type = "Mehrfamilienhaus"
            elif 'einfamilien' in category:
                building_type = "Einfamilienhaus"
            elif 'gewerbe' in category or 'industrie' in category:
                building_type = "Gewerbe/Industrie"

        return BuildingResearch(
            egid=egid,
            adresse=adresse,
            building_type=building_type,
            construction_year=gwr_data.get('construction_year') if gwr_data else None,
            source="fallback",
            confidence=0.3,
            researched_at=datetime.now().isoformat()
        )

    def get_cache_stats(self) -> Dict[str, Any]:
        """Gibt Cache-Statistiken zurück"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM claude_research_cache")
        total = cursor.fetchone()[0]

        now = datetime.now().isoformat()
        cursor.execute(
            "SELECT COUNT(*) FROM claude_research_cache WHERE expires_at > ?",
            (now,)
        )
        valid = cursor.fetchone()[0]

        cursor.execute(
            "SELECT SUM(cost_usd), SUM(tokens_used) FROM claude_research_cache"
        )
        row = cursor.fetchone()
        total_cost = row[0] or 0.0
        total_tokens = row[1] or 0

        conn.close()

        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": total - valid,
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "cache_ttl_days": CACHE_TTL_DAYS
        }

    def clear_expired_cache(self) -> int:
        """Löscht abgelaufene Cache-Einträge"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        cursor.execute(
            "DELETE FROM claude_research_cache WHERE expires_at < ?",
            (now,)
        )
        deleted = cursor.rowcount

        conn.commit()
        conn.close()

        logger.info(f"Deleted {deleted} expired cache entries")
        return deleted


# Singleton-Instance
_research_service: Optional[ClaudeResearchService] = None


def get_research_service() -> ClaudeResearchService:
    """Gibt die Singleton-Instance des Research-Service zurück"""
    global _research_service
    if _research_service is None:
        _research_service = ClaudeResearchService()
    return _research_service
