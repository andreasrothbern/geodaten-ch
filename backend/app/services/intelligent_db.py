# backend/app/services/intelligent_db.py
"""
Intelligent Database Service

Erweiterte Datenbank-Services für:
- Smarte Suche (Name/Alias/Volltext)
- SVG-Caching (persistent)
- Umgebungsdaten-Cache

Version: 1.0
Datum: 29.12.2025
"""

import json
import sqlite3
import hashlib
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Datenbank-Pfad (Railway Volume oder lokal)
DATA_DIR = Path(os.getenv("DATA_DIR", "app/data"))
DB_PATH = DATA_DIR / "building_contexts.db"


# =============================================================================
# DATACLASSES
# =============================================================================

@dataclass
class SearchResult:
    """Suchergebnis für smarte Suche"""
    egid: Optional[str]
    adresse: Optional[str]
    name: Optional[str]
    score: float
    source: str  # "alias", "fts", "geocoding"
    coordinates: Optional[tuple] = None
    has_cached_data: bool = False
    has_cached_svgs: List[str] = field(default_factory=list)


@dataclass
class CachedSVG:
    """Gecachtes SVG"""
    id: str
    egid: str
    svg_type: str
    svg_content: str
    version: str
    generated_by: str
    created_at: str


@dataclass
class BuildingEnvironment:
    """Umgebungsdaten eines Gebäudes"""
    egid: str
    surrounding_buildings: List[Dict[str, Any]]
    blocked_facades: List[int]
    terrain_data: Optional[Dict[str, Any]]
    curves: List[Dict[str, Any]]
    updated_at: str


# =============================================================================
# DATABASE SERVICE
# =============================================================================

class IntelligentDBService:
    """Service für erweiterte DB-Funktionen (Suche, Cache, Umgebung)"""

    # SVG-Versionen für Cache-Invalidierung
    SVG_VERSION = "2.0"

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        """Erstellt die erweiterten Tabellen falls nicht vorhanden"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        # 1. Gebäude-Stammdaten erweitern (falls nicht existiert)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS buildings (
                egid TEXT PRIMARY KEY,
                adresse TEXT,
                plz INTEGER,
                ort TEXT,
                name TEXT,
                aliases TEXT,
                keywords TEXT,
                lv95_e REAL,
                lv95_n REAL,
                is_landmark INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # Index für Koordinaten-Suche
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_buildings_coords
            ON buildings(lv95_e, lv95_n)
        """)

        # 2. Volltext-Index (FTS5)
        # Prüfen ob FTS-Tabelle existiert
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='buildings_fts'
        """)
        if not cursor.fetchone():
            try:
                cursor.execute("""
                    CREATE VIRTUAL TABLE buildings_fts USING fts5(
                        name, aliases, keywords, adresse, ort,
                        content=buildings,
                        content_rowid=rowid
                    )
                """)
                logger.info("FTS5 table created")
            except sqlite3.OperationalError as e:
                logger.warning(f"Could not create FTS5 table: {e}")

        # 3. SVG-Cache Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS svg_cache (
                id TEXT PRIMARY KEY,
                egid TEXT NOT NULL,
                svg_type TEXT NOT NULL,
                svg_content TEXT NOT NULL,
                version TEXT DEFAULT '1.0',
                generated_by TEXT,
                prompt_hash TEXT,
                created_at TEXT,
                FOREIGN KEY (egid) REFERENCES buildings(egid)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_svg_cache_egid
            ON svg_cache(egid)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_svg_cache_type
            ON svg_cache(egid, svg_type)
        """)

        # 4. Umgebungsdaten-Cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS building_environment (
                egid TEXT PRIMARY KEY,
                surrounding_buildings TEXT,
                blocked_facades TEXT,
                terrain_data TEXT,
                curves TEXT,
                updated_at TEXT,
                FOREIGN KEY (egid) REFERENCES buildings(egid)
            )
        """)

        # 5. Claude-Recherche-Cache (NEU)
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
        logger.info(f"Intelligent DB tables initialized at {DB_PATH}")

    # =========================================================================
    # SMARTE SUCHE
    # =========================================================================

    def search_by_alias(self, query: str) -> Optional[SearchResult]:
        """Sucht nach exaktem Alias-Match"""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Exakter Name-Match
        cursor.execute("""
            SELECT egid, adresse, name, aliases, lv95_e, lv95_n
            FROM buildings
            WHERE LOWER(name) = LOWER(?)
        """, (query,))
        row = cursor.fetchone()

        if row:
            conn.close()
            return SearchResult(
                egid=row['egid'],
                adresse=row['adresse'],
                name=row['name'],
                score=1.0,
                source="alias",
                coordinates=(row['lv95_e'], row['lv95_n']) if row['lv95_e'] else None,
                has_cached_data=True
            )

        # Alias-Array durchsuchen
        cursor.execute("""
            SELECT egid, adresse, name, aliases, lv95_e, lv95_n
            FROM buildings
            WHERE aliases IS NOT NULL
        """)

        for row in cursor.fetchall():
            try:
                aliases = json.loads(row['aliases']) if row['aliases'] else []
                for alias in aliases:
                    if alias.lower() == query.lower():
                        conn.close()
                        return SearchResult(
                            egid=row['egid'],
                            adresse=row['adresse'],
                            name=row['name'],
                            score=0.95,
                            source="alias",
                            coordinates=(row['lv95_e'], row['lv95_n']) if row['lv95_e'] else None,
                            has_cached_data=True
                        )
            except json.JSONDecodeError:
                continue

        conn.close()
        return None

    def search_fts(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Volltext-Suche mit FTS5"""
        results = []

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # FTS5-Suche
            cursor.execute("""
                SELECT b.egid, b.adresse, b.name, b.lv95_e, b.lv95_n,
                       bm.rank
                FROM buildings_fts bm
                JOIN buildings b ON bm.rowid = b.rowid
                WHERE buildings_fts MATCH ?
                ORDER BY bm.rank
                LIMIT ?
            """, (query + "*", limit))

            for row in cursor.fetchall():
                # Score aus rank berechnen (niedriger rank = besser)
                score = 1.0 / (1.0 + abs(row['rank'] or 0))

                results.append(SearchResult(
                    egid=row['egid'],
                    adresse=row['adresse'],
                    name=row['name'],
                    score=min(score, 0.9),  # Max 0.9 für FTS (Alias ist besser)
                    source="fts",
                    coordinates=(row['lv95_e'], row['lv95_n']) if row['lv95_e'] else None,
                    has_cached_data=True
                ))

        except sqlite3.OperationalError as e:
            logger.warning(f"FTS search failed: {e}")
            # Fallback auf LIKE-Suche
            cursor.execute("""
                SELECT egid, adresse, name, lv95_e, lv95_n
                FROM buildings
                WHERE name LIKE ? OR adresse LIKE ? OR keywords LIKE ?
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))

            for row in cursor.fetchall():
                results.append(SearchResult(
                    egid=row['egid'],
                    adresse=row['adresse'],
                    name=row['name'],
                    score=0.5,
                    source="like",
                    coordinates=(row['lv95_e'], row['lv95_n']) if row['lv95_e'] else None,
                    has_cached_data=True
                ))

        conn.close()
        return results

    async def smart_search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """
        Smarte Suche nach Gebäuden.

        Reihenfolge:
        1. Exakte Alias-Matches ("Bundeshaus" → EGID)
        2. Volltext-Suche (FTS5)
        3. Fallback: Geocoding via swisstopo
        """
        results = []

        # 1. Alias-Match prüfen
        alias_match = self.search_by_alias(query)
        if alias_match:
            # SVG-Cache Status prüfen
            alias_match.has_cached_svgs = self.get_cached_svg_types(alias_match.egid)
            results.append(alias_match)

        # 2. FTS-Suche
        fts_results = self.search_fts(query)
        for r in fts_results:
            if r.egid not in [x.egid for x in results]:
                r.has_cached_svgs = self.get_cached_svg_types(r.egid)
                results.append(r)

        # 3. Geocoding-Fallback (nur wenn keine DB-Treffer)
        if not results:
            try:
                from app.services.swisstopo import get_swisstopo_service
                swisstopo = get_swisstopo_service()
                geo = await swisstopo.geocode_address(query)
                if geo:
                    results.append(SearchResult(
                        egid=geo.get('egid'),
                        adresse=geo.get('matched_address'),
                        name=None,
                        score=geo.get('confidence', 0.7),
                        source="geocoding",
                        coordinates=(geo.get('lv95_e'), geo.get('lv95_n')),
                        has_cached_data=False
                    ))
            except Exception as e:
                logger.warning(f"Geocoding fallback failed: {e}")

        return results[:limit]

    # =========================================================================
    # SVG CACHE
    # =========================================================================

    def get_svg_cache_key(
        self,
        egid: str,
        svg_type: str,
        version: str = None,
        selected_facades: Optional[List[int]] = None
    ) -> str:
        """Generiert einen eindeutigen Cache-Key für SVGs"""
        version = version or self.SVG_VERSION
        components = [egid, svg_type, version]

        if selected_facades:
            facades_str = "-".join(map(str, sorted(selected_facades)))
            components.append(f"facades:{facades_str}")

        return hashlib.sha256("|".join(components).encode()).hexdigest()[:16]

    def get_cached_svg(
        self,
        egid: str,
        svg_type: str,
        version: str = None
    ) -> Optional[CachedSVG]:
        """Lädt ein SVG aus dem Cache"""
        version = version or self.SVG_VERSION
        cache_key = self.get_svg_cache_key(egid, svg_type, version)

        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, egid, svg_type, svg_content, version, generated_by, created_at
            FROM svg_cache
            WHERE id = ?
        """, (cache_key,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return CachedSVG(
                id=row['id'],
                egid=row['egid'],
                svg_type=row['svg_type'],
                svg_content=row['svg_content'],
                version=row['version'],
                generated_by=row['generated_by'] or 'unknown',
                created_at=row['created_at']
            )
        return None

    def set_cached_svg(
        self,
        egid: str,
        svg_type: str,
        svg_content: str,
        generated_by: str = "auto",
        version: str = None,
        prompt_hash: str = None
    ) -> str:
        """Speichert ein SVG im Cache"""
        version = version or self.SVG_VERSION
        cache_key = self.get_svg_cache_key(egid, svg_type, version)

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO svg_cache
            (id, egid, svg_type, svg_content, version, generated_by, prompt_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cache_key,
            egid,
            svg_type,
            svg_content,
            version,
            generated_by,
            prompt_hash,
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

        logger.info(f"Cached SVG for {egid}/{svg_type} (key: {cache_key})")
        return cache_key

    def get_cached_svg_types(self, egid: str) -> List[str]:
        """Gibt alle gecachten SVG-Typen für ein Gebäude zurück"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DISTINCT svg_type FROM svg_cache
            WHERE egid = ? AND version = ?
        """, (egid, self.SVG_VERSION))

        types = [row[0] for row in cursor.fetchall()]
        conn.close()
        return types

    def invalidate_svg_cache(self, egid: str, svg_type: str = None) -> int:
        """Invalidiert den SVG-Cache für ein Gebäude"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        if svg_type:
            cursor.execute("""
                DELETE FROM svg_cache WHERE egid = ? AND svg_type = ?
            """, (egid, svg_type))
        else:
            cursor.execute("""
                DELETE FROM svg_cache WHERE egid = ?
            """, (egid,))

        count = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Invalidated {count} cached SVGs for {egid}")
        return count

    # =========================================================================
    # BUILDING ENVIRONMENT
    # =========================================================================

    def get_building_environment(self, egid: str) -> Optional[BuildingEnvironment]:
        """Lädt Umgebungsdaten aus dem Cache"""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM building_environment WHERE egid = ?
        """, (egid,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return BuildingEnvironment(
                egid=row['egid'],
                surrounding_buildings=json.loads(row['surrounding_buildings'] or '[]'),
                blocked_facades=json.loads(row['blocked_facades'] or '[]'),
                terrain_data=json.loads(row['terrain_data']) if row['terrain_data'] else None,
                curves=json.loads(row['curves'] or '[]'),
                updated_at=row['updated_at']
            )
        return None

    def set_building_environment(
        self,
        egid: str,
        surrounding_buildings: List[Dict[str, Any]],
        blocked_facades: List[int],
        terrain_data: Optional[Dict[str, Any]] = None,
        curves: List[Dict[str, Any]] = None
    ) -> bool:
        """Speichert Umgebungsdaten im Cache"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO building_environment
            (egid, surrounding_buildings, blocked_facades, terrain_data, curves, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            egid,
            json.dumps(surrounding_buildings),
            json.dumps(blocked_facades),
            json.dumps(terrain_data) if terrain_data else None,
            json.dumps(curves or []),
            datetime.utcnow().isoformat()
        ))

        conn.commit()
        conn.close()

        logger.info(f"Saved environment data for {egid}")
        return True

    # =========================================================================
    # CLAUDE RESEARCH CACHE
    # =========================================================================

    def get_research_cache(
        self,
        query_hash: str = None,
        egid: str = None,
        research_type: str = None
    ) -> Optional[Dict[str, Any]]:
        """Lädt Claude-Recherche aus dem Cache"""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if query_hash:
            cursor.execute("""
                SELECT * FROM claude_research_cache
                WHERE query_hash = ? AND (expires_at IS NULL OR expires_at > ?)
            """, (query_hash, datetime.utcnow().isoformat()))
        elif egid and research_type:
            cursor.execute("""
                SELECT * FROM claude_research_cache
                WHERE egid = ? AND research_type = ?
                AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at DESC LIMIT 1
            """, (egid, research_type, datetime.utcnow().isoformat()))
        else:
            conn.close()
            return None

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row['id'],
                'egid': row['egid'],
                'adresse': row['adresse'],
                'research_type': row['research_type'],
                'response': json.loads(row['response_json']),
                'tokens_used': row['tokens_used'],
                'cost_usd': row['cost_usd'],
                'model': row['model'],
                'created_at': row['created_at']
            }
        return None

    def set_research_cache(
        self,
        response: Dict[str, Any],
        research_type: str,
        egid: str = None,
        adresse: str = None,
        query_hash: str = None,
        tokens_used: int = None,
        cost_usd: float = None,
        model: str = None,
        ttl_hours: int = 24 * 30  # 30 Tage Default
    ) -> str:
        """Speichert Claude-Recherche im Cache"""
        # Hash generieren falls nicht angegeben
        if not query_hash:
            hash_content = json.dumps({
                'egid': egid,
                'adresse': adresse,
                'research_type': research_type
            }, sort_keys=True)
            query_hash = hashlib.sha256(hash_content.encode()).hexdigest()[:32]

        cache_id = f"{research_type}_{query_hash[:16]}"

        from datetime import timedelta
        expires_at = (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat()

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

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
            research_type,
            json.dumps(response),
            tokens_used,
            cost_usd,
            model,
            datetime.utcnow().isoformat(),
            expires_at
        ))

        conn.commit()
        conn.close()

        logger.info(f"Cached research for {research_type} (id: {cache_id})")
        return cache_id

    # =========================================================================
    # LANDMARK BUILDINGS (Bekannte Gebäude)
    # =========================================================================

    def add_landmark_building(
        self,
        egid: str,
        name: str,
        adresse: str,
        aliases: List[str] = None,
        keywords: str = None,
        lv95_e: float = None,
        lv95_n: float = None,
        plz: int = None,
        ort: str = None
    ) -> bool:
        """Fügt ein bekanntes Gebäude hinzu"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO buildings
            (egid, adresse, plz, ort, name, aliases, keywords, lv95_e, lv95_n,
             is_landmark, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (
            egid,
            adresse,
            plz,
            ort,
            name,
            json.dumps(aliases or []),
            keywords,
            lv95_e,
            lv95_n,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))

        conn.commit()

        # FTS-Index aktualisieren
        try:
            cursor.execute("""
                INSERT INTO buildings_fts(rowid, name, aliases, keywords, adresse, ort)
                SELECT rowid, name, aliases, keywords, adresse, ort
                FROM buildings WHERE egid = ?
            """, (egid,))
            conn.commit()
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not update FTS index: {e}")

        conn.close()
        logger.info(f"Added landmark building: {name} ({egid})")
        return True

    def seed_landmark_buildings(self):
        """Fügt bekannte Schweizer Gebäude als Seed-Daten hinzu"""
        landmarks = [
            {
                "egid": "2242547",
                "name": "Bundeshaus",
                "aliases": ["Parlamentsgebäude", "Swiss Parliament", "Bundeshaus Bern"],
                "adresse": "Bundesplatz 3, 3011 Bern",
                "keywords": "parlament bundesversammlung kuppel regierung schweiz",
                "plz": 3011,
                "ort": "Bern",
                "lv95_e": 2600450,
                "lv95_n": 1199830
            },
            {
                "egid": "1230337",
                "name": "Berner Münster",
                "aliases": ["Münster Bern", "Cathedral Bern", "Berner Dom"],
                "adresse": "Münsterplatz 1, 3011 Bern",
                "keywords": "kirche kathedrale gotik turm münster",
                "plz": 3011,
                "ort": "Bern",
                "lv95_e": 2600656,
                "lv95_n": 1199497
            },
            {
                "egid": "191821074",
                "name": "St. Peter und Paul",
                "aliases": ["St. Peter und Paul Bern", "Christkatholische Kathedrale", "Christkath Bern"],
                "adresse": "Rathausgasse 2, 3011 Bern",
                "keywords": "kirche christkatholisch neugotik westturm basilika kathedrale",
                "plz": 3011,
                "ort": "Bern",
                "lv95_e": 2600560,
                "lv95_n": 1199780
            },
            {
                "egid": "1017961",
                "name": "Zytglogge",
                "aliases": ["Zeitglockenturm", "Tour de l'Horloge"],
                "adresse": "Bim Zytglogge, 3011 Bern",
                "keywords": "turm uhr altstadt wahrzeichen mittelalter",
                "plz": 3011,
                "ort": "Bern",
                "lv95_e": 2600579,
                "lv95_n": 1199686
            }
        ]

        for landmark in landmarks:
            self.add_landmark_building(**landmark)

        logger.info(f"Seeded {len(landmarks)} landmark buildings")

    # =========================================================================
    # STATISTIKEN
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Gibt Statistiken zur Datenbank zurück"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        stats = {}

        # Buildings
        cursor.execute("SELECT COUNT(*) FROM buildings")
        stats['buildings_total'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM buildings WHERE is_landmark = 1")
        stats['buildings_landmarks'] = cursor.fetchone()[0]

        # SVG Cache
        cursor.execute("SELECT COUNT(*) FROM svg_cache")
        stats['svg_cache_total'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT egid) FROM svg_cache")
        stats['svg_cache_buildings'] = cursor.fetchone()[0]

        # Environment Cache
        cursor.execute("SELECT COUNT(*) FROM building_environment")
        stats['environment_cached'] = cursor.fetchone()[0]

        # Research Cache
        cursor.execute("SELECT COUNT(*) FROM claude_research_cache")
        stats['research_cached'] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT SUM(cost_usd) FROM claude_research_cache
        """)
        row = cursor.fetchone()
        stats['research_total_cost_usd'] = row[0] or 0.0

        # DB Grösse
        db_size = os.path.getsize(str(DB_PATH)) if DB_PATH.exists() else 0
        stats['db_size_mb'] = round(db_size / (1024 * 1024), 2)

        conn.close()
        return stats


# =============================================================================
# SINGLETON
# =============================================================================

_service_instance: Optional[IntelligentDBService] = None


def get_intelligent_db_service() -> IntelligentDBService:
    """Gibt die Singleton-Instanz des Services zurück"""
    global _service_instance
    if _service_instance is None:
        _service_instance = IntelligentDBService()
    return _service_instance
